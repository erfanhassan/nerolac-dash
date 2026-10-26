"""Nerolac Dash Automated SAP SFTP Landing Folder Watcher Daemon.

Architecture Compliance:
1. Monitors secure SFTP landing folders using Paramiko for daily 2:00 AM SAP batch drops:
   - FAGLL03: Financial G/L Account Line Items (Finance Actuals)
   - VA05: Sales Order List / Customer Orders (SCM Sales)
   - MB52: Material Stock / Warehouse Storage (Inventory)
   - ME2L: Purchasing Documents per Vendor (Procurement Register)
2. Enforces SHA-256 cryptographic verification before triggering downstream ingestion pipelines.
3. Automatically isolates corrupted, truncated, or incomplete file transfers to quarantine.
4. Retrieves credentials dynamically from HashiCorp / Azure Vault (zero plaintext secrets).
"""

from __future__ import annotations

import asyncio
import io
import logging
import shutil
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import paramiko

from src.backend.config.vault import get_vault_client
from src.backend.etl.file_verifier import (
    FileVerifier,
    SAPReportType,
    VerificationResult,
    VerificationStatus,
    identify_report_type,
)

logger = logging.getLogger("nerolac.etl.sftp_watcher")

# Standard SAP batch drop reports scheduled for daily 2:00 AM ingestion
TARGET_SAP_REPORTS = [
    SAPReportType.FAGLL03,
    SAPReportType.VA05,
    SAPReportType.MB52,
    SAPReportType.ME2L,
]


@dataclass
class SFTPWatcherConfig:
    """Configuration parameters for SAP SFTP Landing Zone daemon."""

    host: str = "sftp.dhaka.nerolacbd.com"
    port: int = 22
    username: str = "sap_nerolac_svc"
    password: str | None = None
    private_key: str | None = None
    remote_landing_dir: str = "/landing"
    remote_processed_dir: str = "/processed"
    remote_quarantine_dir: str = "/quarantine"
    local_staging_dir: Path = Path("/tmp/nerolac_etl/staging")
    local_processed_dir: Path = Path("/tmp/nerolac_etl/processed")
    local_quarantine_dir: Path = Path("/tmp/nerolac_etl/quarantine")
    target_reports: list[SAPReportType] = field(default_factory=lambda: list(TARGET_SAP_REPORTS))
    batch_drop_hour: int = 2  # 02:00 AM
    batch_drop_minute: int = 0
    poll_interval_seconds: float = 60.0
    connection_timeout: int = 30
    auto_quarantine: bool = True
    delete_remote_after_download: bool = False

    @classmethod
    def from_vault(cls, **overrides: Any) -> SFTPWatcherConfig:
        """Create configuration loading credentials dynamically from HashiCorp Vault."""
        vault = get_vault_client()
        creds = vault.get_sftp_credentials()
        params: dict[str, Any] = {
            "host": creds.get("host") or "sftp.dhaka.nerolacbd.com",
            "username": creds.get("user") or "sap_nerolac_svc",
            "private_key": creds.get("private_key"),
        }
        params.update(overrides)
        return cls(**params)


@dataclass
class BatchProcessingResult:
    """Outcome of an SAP batch drop discovery, download, verification, and disposition."""

    filename: str
    report_type: SAPReportType
    status: VerificationStatus
    is_valid: bool
    remote_path: str
    local_staging_path: Path
    local_final_path: Path | None
    verification: VerificationResult
    processed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ingestion_triggered: bool = False
    error: str | None = None


def load_paramiko_private_key(key_str: str) -> paramiko.PKey:
    """Parse private key string into appropriate Paramiko PKey instance."""
    key_file = io.StringIO(key_str.strip())
    # Try Ed25519 first (recommended corporate baseline)
    try:
        return paramiko.Ed25519Key.from_private_key(key_file)
    except Exception:
        pass

    # Try RSA
    key_file.seek(0)
    try:
        return paramiko.RSAKey.from_private_key(key_file)
    except Exception:
        pass

    # Try ECDSA
    key_file.seek(0)
    try:
        return paramiko.ECDSAKey.from_private_key(key_file)
    except Exception as exc:
        raise ValueError(f"Unable to parse Paramiko private key: {exc}") from exc


class ParamikoSFTPClientAdapter:
    """Manages Paramiko SSH and SFTP client sessions."""

    def __init__(self, config: SFTPWatcherConfig) -> None:
        self.config = config
        self._ssh_client: paramiko.SSHClient | None = None
        self._sftp_client: paramiko.SFTPClient | None = None

    def connect(self) -> paramiko.SFTPClient:
        """Establish authenticated SSH/SFTP connection to the SAP landing server."""
        if self._sftp_client is not None:
            return self._sftp_client

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        pkey: paramiko.PKey | None = None
        if self.config.private_key and "PRIVATE KEY" in self.config.private_key:
            try:
                pkey = load_paramiko_private_key(self.config.private_key)
            except Exception as exc:
                logger.warning("Could not parse private key from Vault: %s. Trying password.", exc)

        logger.info(
            "Connecting to SAP SFTP server %s:%d as user '%s'...",
            self.config.host,
            self.config.port,
            self.config.username,
        )

        ssh.connect(
            hostname=self.config.host,
            port=self.config.port,
            username=self.config.username,
            password=self.config.password,
            pkey=pkey,
            timeout=self.config.connection_timeout,
            look_for_keys=False,
            allow_agent=False,
        )

        self._ssh_client = ssh
        self._sftp_client = ssh.open_sftp()
        logger.info("SFTP session established with %s", self.config.host)
        return self._sftp_client

    def disconnect(self) -> None:
        """Cleanly close SFTP and SSH connections."""
        if self._sftp_client:
            try:
                self._sftp_client.close()
            except Exception:
                pass
            self._sftp_client = None

        if self._ssh_client:
            try:
                self._ssh_client.close()
            except Exception:
                pass
            self._ssh_client = None

    def listdir(self, remote_path: str) -> list[str]:
        """List filenames in remote directory."""
        client = self.connect()
        try:
            return client.listdir(remote_path)
        except OSError as exc:
            logger.warning("Remote path '%s' not accessible: %s", remote_path, exc)
            return []

    def get(self, remote_path: str, local_path: str) -> None:
        """Download remote file to local filesystem."""
        client = self.connect()
        client.get(remote_path, local_path)

    def rename(self, oldpath: str, newpath: str) -> None:
        """Rename or move remote file."""
        client = self.connect()
        client.rename(oldpath, newpath)

    def remove(self, remote_path: str) -> None:
        """Delete remote file."""
        client = self.connect()
        client.remove(remote_path)

    def file_exists(self, remote_path: str) -> bool:
        """Check if remote file exists."""
        client = self.connect()
        try:
            client.stat(remote_path)
            return True
        except OSError:
            return False


class SAPSFTPWatcher:
    """Automated SFTP Landing Folder Watcher Daemon for SAP ERP Daily Batches.

    Monitors landing zone for:
    - FAGLL03: Finance Actuals
    - VA05: Sales Order List
    - MB52: Material Inventory
    - ME2L: Procurement Register
    """

    def __init__(
        self,
        config: SFTPWatcherConfig | None = None,
        verifier: FileVerifier | None = None,
        sftp_client: Any | None = None,
        ingestion_callback: (
            Callable[[BatchProcessingResult], Coroutine[Any, Any, None]] | None
        ) = None,
    ) -> None:
        self.config = config or SFTPWatcherConfig.from_vault()
        self.verifier = verifier or FileVerifier(
            quarantine_dir=self.config.local_quarantine_dir,
            require_checksum=True,
        )
        self.sftp_client: Any = sftp_client or ParamikoSFTPClientAdapter(self.config)
        self.ingestion_callback = ingestion_callback

        # Ensure local working directories exist
        self.config.local_staging_dir.mkdir(parents=True, exist_ok=True)
        self.config.local_processed_dir.mkdir(parents=True, exist_ok=True)
        self.config.local_quarantine_dir.mkdir(parents=True, exist_ok=True)

    def _is_target_batch_file(self, filename: str) -> bool:
        """Determine if a file is a target SAP report drop."""
        name_lower = filename.lower()
        # Ignore checksum companions and temporary write files during initial scan
        if name_lower.endswith((".sha256", ".sha256sum", ".chk", ".tmp", ".part")):
            return False

        report_type = identify_report_type(filename)
        return report_type in self.config.target_reports

    def _find_remote_companion_checksum(
        self,
        landing_dir: str,
        filename: str,
        available_files: list[str],
    ) -> str | None:
        """Locate companion checksum filename in remote listing if present."""
        stem = Path(filename).stem
        candidates = [
            f"{filename}.sha256",
            f"{filename}.sha256sum",
            f"{filename}.chk",
            f"{stem}.sha256",
            f"{stem}.chk",
        ]
        available_set = set(available_files)
        for cand in candidates:
            if cand in available_set:
                return cand
        return None

    def scan_landing_zone(self) -> list[BatchProcessingResult]:
        """Scan landing zone, download files, verify checksums, and quarantine corrupt drops."""
        results: list[BatchProcessingResult] = []
        landing_dir = self.config.remote_landing_dir

        try:
            remote_files = self.sftp_client.listdir(landing_dir)
        except Exception as exc:
            logger.error("Failed to list remote landing directory '%s': %s", landing_dir, exc)
            return results

        target_files = [f for f in remote_files if self._is_target_batch_file(f)]
        if not target_files:
            logger.info("No new target SAP batch drops found in '%s'", landing_dir)
            return results

        logger.info(
            "Found %d SAP batch drops in '%s': %s",
            len(target_files),
            landing_dir,
            target_files,
        )

        for filename in target_files:
            report_type = identify_report_type(filename)
            remote_file_path = f"{landing_dir.rstrip('/')}/{filename}"
            local_staging_file = self.config.local_staging_dir / filename

            # 1. Check for remote companion checksum file
            remote_chk_name = self._find_remote_companion_checksum(
                landing_dir, filename, remote_files
            )
            local_chk_file: Path | None = None

            if remote_chk_name:
                remote_chk_path = f"{landing_dir.rstrip('/')}/{remote_chk_name}"
                local_chk_file = self.config.local_staging_dir / remote_chk_name
                try:
                    self.sftp_client.get(remote_chk_path, str(local_chk_file))
                    logger.debug("Downloaded companion checksum: %s", remote_chk_name)
                except Exception as exc:
                    logger.warning(
                        "Failed to download remote companion checksum '%s': %s",
                        remote_chk_name,
                        exc,
                    )

            # 2. Download the data file to local staging
            try:
                self.sftp_client.get(remote_file_path, str(local_staging_file))
                logger.info("Downloaded SAP drop '%s' to staging", filename)
            except Exception as exc:
                err_msg = f"Failed to download remote file '{remote_file_path}': {exc}"
                logger.error(err_msg)
                # Mark as corrupted/incomplete due to download failure
                res = BatchProcessingResult(
                    filename=filename,
                    report_type=report_type,
                    status=VerificationStatus.INCOMPLETE,
                    is_valid=False,
                    remote_path=remote_file_path,
                    local_staging_path=local_staging_file,
                    local_final_path=None,
                    verification=VerificationResult(
                        file_path=local_staging_file,
                        report_type=report_type,
                        status=VerificationStatus.INCOMPLETE,
                        is_valid=False,
                        calculated_sha256="",
                        error_message=err_msg,
                    ),
                    error=err_msg,
                )
                results.append(res)
                continue

            # 3. Cryptographic SHA-256 and Transfer Integrity Verification
            verification = self.verifier.verify_file(
                file_path=local_staging_file,
                auto_quarantine=self.config.auto_quarantine,
            )

            if verification.is_valid:
                # 4a. Valid Drop: move to processed storage
                local_final = self.config.local_processed_dir / filename
                if local_staging_file.is_file():
                    shutil.move(str(local_staging_file), str(local_final))

                # Move companion checksum to processed if exists
                if local_chk_file and local_chk_file.is_file():
                    dest_chk = self.config.local_processed_dir / local_chk_file.name
                    shutil.move(str(local_chk_file), str(dest_chk))

                # Handle remote file disposition
                if self.config.delete_remote_after_download:
                    try:
                        self.sftp_client.remove(remote_file_path)
                    except Exception as exc:
                        logger.warning(
                            "Could not delete remote file '%s': %s", remote_file_path, exc
                        )
                elif self.config.remote_processed_dir:
                    try:
                        dest_remote = f"{self.config.remote_processed_dir.rstrip('/')}/{filename}"
                        self.sftp_client.rename(remote_file_path, dest_remote)
                    except Exception as exc:
                        logger.debug("Could not rename remote file to processed: %s", exc)

                res = BatchProcessingResult(
                    filename=filename,
                    report_type=report_type,
                    status=VerificationStatus.VALID,
                    is_valid=True,
                    remote_path=remote_file_path,
                    local_staging_path=local_staging_file,
                    local_final_path=local_final,
                    verification=verification,
                )
                results.append(res)
                logger.info("SAP drop '%s' verified VALID and staged for ingestion.", filename)

            else:
                # 4b. Corrupted or Incomplete Drop: Quarantined
                logger.critical(
                    "ALERT: SAP batch drop '%s' failed verification [%s]. Quarantined to %s.",
                    filename,
                    verification.status.value,
                    verification.quarantine_path,
                )

                # Move remote corrupted file to remote quarantine folder if configured
                if self.config.remote_quarantine_dir:
                    try:
                        rem_q = self.config.remote_quarantine_dir.rstrip("/")
                        dest_quarantine = f"{rem_q}/{filename}"
                        self.sftp_client.rename(remote_file_path, dest_quarantine)
                    except Exception as exc:
                        logger.debug("Could not move remote file to remote quarantine: %s", exc)

                res = BatchProcessingResult(
                    filename=filename,
                    report_type=report_type,
                    status=verification.status,
                    is_valid=False,
                    remote_path=remote_file_path,
                    local_staging_path=local_staging_file,
                    local_final_path=verification.quarantine_path,
                    verification=verification,
                    error=verification.error_message,
                )
                results.append(res)

        return results

    def poll_once(self) -> list[BatchProcessingResult]:
        """Perform a single discovery and verification cycle."""
        return self.scan_landing_zone()

    async def run_daemon(
        self,
        stop_event: asyncio.Event | None = None,
        max_iterations: int | None = None,
    ) -> list[BatchProcessingResult]:
        """Run the automated SFTP landing watcher daemon loop."""
        logger.info(
            "Starting SAP SFTP Landing Zone Daemon [Target Reports: %s, Drop Time: %02d:%02d UTC]",
            [r.value for r in self.config.target_reports],
            self.config.batch_drop_hour,
            self.config.batch_drop_minute,
        )

        all_results: list[BatchProcessingResult] = []
        iterations = 0

        while True:
            if stop_event and stop_event.is_set():
                logger.info("Stop signal received; shutting down SFTP watcher daemon.")
                break

            try:
                cycle_results = self.scan_landing_zone()
                all_results.extend(cycle_results)

                # Trigger downstream ingestion callbacks for valid files
                for res in cycle_results:
                    if res.is_valid and self.ingestion_callback:
                        try:
                            await self.ingestion_callback(res)
                            res.ingestion_triggered = True
                        except Exception as exc:
                            logger.error("Ingestion callback error for %s: %s", res.filename, exc)
            except Exception as exc:
                logger.error("Unexpected error in SFTP watcher cycle: %s", exc, exc_info=True)

            iterations += 1
            if max_iterations is not None and iterations >= max_iterations:
                break

            # Sleep until next polling interval or until stop_event fires
            if stop_event:
                try:
                    await asyncio.wait_for(
                        stop_event.wait(), timeout=self.config.poll_interval_seconds
                    )
                    break
                except asyncio.TimeoutError:
                    pass
            else:
                await asyncio.sleep(self.config.poll_interval_seconds)

        self.sftp_client.disconnect()
        return all_results
