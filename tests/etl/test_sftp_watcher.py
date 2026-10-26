"""Unit and Integration Test Suite for SAP SFTP Watcher and Checksum Engine.

Verifies:
1. Monitoring of SFTP landing folders for daily 2:00 AM SAP batch drops:
   - FAGLL03 (Finance Actuals)
   - VA05 (Sales Orders)
   - MB52 (Material Inventory)
   - ME2L (Procurement Register)
2. Accurate cryptographic SHA-256 validation (detects valid vs corrupted uploads).
3. Automated quarantine handling for corrupted, truncated, or incomplete drops.
4. Downstream ingestion pipeline triggering strictly upon verified integrity.
5. Graceful daemon lifecycle and shutdown.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from src.backend.config.vault import DEFAULT_FALLBACK_SECRETS
from src.backend.etl.file_verifier import (
    FileVerifier,
    SAPReportType,
    VerificationStatus,
    identify_report_type,
)
from src.backend.etl.sftp_watcher import (
    BatchProcessingResult,
    SAPSFTPWatcher,
    SFTPWatcherConfig,
)


class SyntheticRemoteSFTPClient:
    """In-memory and filesystem synthetic SFTP adapter simulating SAP server drops."""

    def __init__(self, remote_root: Path) -> None:
        self.remote_root = remote_root
        self.connected = False
        self.landing_dir = self.remote_root / "landing"
        self.processed_dir = self.remote_root / "processed"
        self.quarantine_dir = self.remote_root / "quarantine"

        self.landing_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

    def connect(self) -> Any:
        self.connected = True
        return self

    def disconnect(self) -> None:
        self.connected = False

    def _resolve(self, remote_path: str) -> Path:
        rel = remote_path.lstrip("/")
        return self.remote_root / rel

    def listdir(self, remote_path: str) -> list[str]:
        target = self._resolve(remote_path)
        if not target.is_dir():
            return []
        return [p.name for p in target.iterdir()]

    def get(self, remote_path: str, local_path: str) -> None:
        src = self._resolve(remote_path)
        if not src.is_file():
            raise FileNotFoundError(f"Remote file not found: {remote_path}")
        dest = Path(local_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(src.read_bytes())

    def rename(self, oldpath: str, newpath: str) -> None:
        src = self._resolve(oldpath)
        dest = self._resolve(newpath)
        dest.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dest)

    def remove(self, remote_path: str) -> None:
        src = self._resolve(remote_path)
        if src.is_file():
            src.unlink()

    def file_exists(self, remote_path: str) -> bool:
        return self._resolve(remote_path).exists()


class TestFileVerifier:
    """Test suite for SHA-256 checksum engine, report classification, and quarantine."""

    def test_identify_sap_report_types(self) -> None:
        assert identify_report_type("FAGLL03_20261027_020000.csv") == SAPReportType.FAGLL03
        assert identify_report_type("SAP_FAGLL03_GL_ACTUALS.txt") == SAPReportType.FAGLL03
        assert identify_report_type("VA05_SALES_ORDERS_2026.csv") == SAPReportType.VA05
        assert identify_report_type("MB52_WAREHOUSE_STOCK.dat") == SAPReportType.MB52
        assert identify_report_type("ME2L_PO_REGISTER.csv") == SAPReportType.ME2L
        assert identify_report_type("UNRECOGNIZED_REPORT_XYZ.csv") == SAPReportType.UNKNOWN

    def test_streaming_sha256_computation(self, tmp_path: Path) -> None:
        test_file = tmp_path / "sample.csv"
        content = b"depot_id,account_id,amount\nDEPOT_01,GL_1001,50000.00\n"
        test_file.write_bytes(content)

        verifier = FileVerifier(quarantine_dir=tmp_path / "quarantine")
        sha256_hash = verifier.compute_sha256(test_file)

        import hashlib

        expected = hashlib.sha256(content).hexdigest()
        assert len(sha256_hash) == 64
        assert sha256_hash == expected

    def test_valid_file_with_companion_checksum(self, tmp_path: Path) -> None:
        test_file = tmp_path / "FAGLL03_20261027_020000.csv"
        test_file.write_text("actual_id,amount\n1,12000.00\n", encoding="utf-8")

        verifier = FileVerifier(quarantine_dir=tmp_path / "quarantine")
        verifier.write_companion_checksum(test_file)

        result = verifier.verify_file(test_file)

        assert result.is_valid is True
        assert result.status == VerificationStatus.VALID
        assert result.report_type == SAPReportType.FAGLL03
        assert result.quarantine_path is None
        assert result.calculated_sha256 == result.expected_sha256

    def test_valid_file_with_explicit_expected_checksum(self, tmp_path: Path) -> None:
        test_file = tmp_path / "VA05_SALES.csv"
        test_file.write_text("order_id,sku_id,qty\n101,SKU_RED,50\n", encoding="utf-8")

        verifier = FileVerifier(quarantine_dir=tmp_path / "quarantine")
        actual_hash = verifier.compute_sha256(test_file)

        result = verifier.verify_file(test_file, expected_sha256=actual_hash)
        assert result.is_valid is True
        assert result.status == VerificationStatus.VALID
        assert result.report_type == SAPReportType.VA05

    def test_corrupted_file_detection_and_quarantine(self, tmp_path: Path) -> None:
        test_file = tmp_path / "MB52_STOCK.csv"
        test_file.write_text("material_code,stock_qty\nMAT_001,500\n", encoding="utf-8")

        quarantine_dir = tmp_path / "quarantine"
        verifier = FileVerifier(quarantine_dir=quarantine_dir)

        # Write wrong expected checksum (tampered or corrupted drop)
        tampered_hash = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        verifier.write_companion_checksum(test_file, checksum=tampered_hash)

        result = verifier.verify_file(test_file, auto_quarantine=True)

        assert result.is_valid is False
        assert result.status == VerificationStatus.CORRUPTED
        assert "SHA-256 Checksum Mismatch" in (result.error_message or "")
        assert result.quarantine_path is not None
        assert result.quarantine_path.is_file()
        assert not test_file.exists(), "Original corrupted file must be moved to quarantine"

        # Verify companion quarantine metadata file was generated
        assert result.metadata_path is not None
        assert result.metadata_path.is_file()
        meta_content = json.loads(result.metadata_path.read_text(encoding="utf-8"))
        assert meta_content["status"] == "CORRUPTED"
        assert meta_content["original_filename"] == "MB52_STOCK.csv"
        assert meta_content["expected_sha256"] == tampered_hash
        assert meta_content["calculated_sha256"] == result.calculated_sha256

    def test_incomplete_file_transfer_quarantine(self, tmp_path: Path) -> None:
        quarantine_dir = tmp_path / "quarantine"
        test_file = tmp_path / "ME2L_PROCUREMENT.csv.tmp"
        test_file.write_text("partial data...", encoding="utf-8")

        verifier = FileVerifier(quarantine_dir=quarantine_dir)
        result = verifier.verify_file(test_file, auto_quarantine=True)

        assert result.is_valid is False
        assert result.status == VerificationStatus.INCOMPLETE
        assert result.quarantine_path is not None
        assert result.quarantine_path.is_file()
        assert not test_file.exists()

    def test_zero_byte_empty_file_quarantine(self, tmp_path: Path) -> None:
        quarantine_dir = tmp_path / "quarantine"
        test_file = tmp_path / "FAGLL03_EMPTY.csv"
        test_file.touch()

        verifier = FileVerifier(quarantine_dir=quarantine_dir)
        result = verifier.verify_file(test_file, auto_quarantine=True)

        assert result.is_valid is False
        assert result.status == VerificationStatus.EMPTY_FILE
        assert result.quarantine_path is not None
        assert result.quarantine_path.is_file()
        assert not test_file.exists()

    def test_max_file_size_exceeded_quarantine(self, tmp_path: Path) -> None:
        quarantine_dir = tmp_path / "quarantine"
        test_file = tmp_path / "VA05_OVERSIZED.csv"
        test_file.write_bytes(b"A" * 2000)

        # Set max quota artificially low (1000 bytes)
        verifier = FileVerifier(quarantine_dir=quarantine_dir, max_file_size_bytes=1000)
        result = verifier.verify_file(test_file, auto_quarantine=True)

        assert result.is_valid is False
        assert result.status == VerificationStatus.EXCEEDS_SIZE_LIMIT
        assert result.quarantine_path is not None
        assert not test_file.exists()

    def test_missing_checksum_when_required(self, tmp_path: Path) -> None:
        quarantine_dir = tmp_path / "quarantine"
        test_file = tmp_path / "ME2L_NO_CHECKSUM.csv"
        test_file.write_text("data,without,checksum\n", encoding="utf-8")

        verifier = FileVerifier(quarantine_dir=quarantine_dir, require_checksum=True)
        result = verifier.verify_file(test_file, auto_quarantine=True)

        assert result.is_valid is False
        assert result.status == VerificationStatus.MISSING_CHECKSUM
        assert result.quarantine_path is not None


class TestSFTPWatcher:
    """Test suite for SFTP landing folder watcher daemon and synthetic drops."""

    @pytest.fixture
    def sftp_env(self, tmp_path: Path) -> tuple[SyntheticRemoteSFTPClient, SFTPWatcherConfig]:
        remote_root = tmp_path / "remote_sftp"
        synthetic_sftp = SyntheticRemoteSFTPClient(remote_root)

        config = SFTPWatcherConfig(
            host="sftp.dhaka.nerolacbd.com",
            port=22,
            username="sap_nerolac_svc",
            remote_landing_dir="/landing",
            remote_processed_dir="/processed",
            remote_quarantine_dir="/quarantine",
            local_staging_dir=tmp_path / "local_staging",
            local_processed_dir=tmp_path / "local_processed",
            local_quarantine_dir=tmp_path / "local_quarantine",
            batch_drop_hour=2,
            batch_drop_minute=0,
            poll_interval_seconds=0.1,
            auto_quarantine=True,
        )
        return synthetic_sftp, config

    def test_vault_config_retrieval(self) -> None:
        config = SFTPWatcherConfig.from_vault()
        assert config.host == DEFAULT_FALLBACK_SECRETS["SAP_SFTP_HOST"]
        assert config.username == DEFAULT_FALLBACK_SECRETS["SAP_SFTP_USER"]
        assert config.private_key == DEFAULT_FALLBACK_SECRETS["SAP_SFTP_PRIVATE_KEY"]

    def test_scan_landing_zone_processes_valid_and_quarantines_corrupted(
        self,
        sftp_env: tuple[SyntheticRemoteSFTPClient, SFTPWatcherConfig],
    ) -> None:
        sftp_client, config = sftp_env
        verifier = FileVerifier(quarantine_dir=config.local_quarantine_dir)
        watcher = SAPSFTPWatcher(config=config, verifier=verifier, sftp_client=sftp_client)

        landing_path = sftp_client.landing_dir

        # 1. Drop a VALID FAGLL03 file with companion checksum
        fagll03_file = landing_path / "FAGLL03_20261027_020000.csv"
        fagll03_content = "actual_id,depot_id,amount\n1,DEPOT_01,150000.00\n"
        fagll03_file.write_text(fagll03_content, encoding="utf-8")
        verifier.write_companion_checksum(fagll03_file)

        # 2. Drop a VALID VA05 file with companion checksum
        va05_file = landing_path / "VA05_20261027_020000.csv"
        va05_content = "sale_id,depot_id,sku_id,qty\n1,DEPOT_01,SKU_RED,250\n"
        va05_file.write_text(va05_content, encoding="utf-8")
        verifier.write_companion_checksum(va05_file)

        # 3. Drop a CORRUPTED MB52 file (checksum mismatch)
        mb52_file = landing_path / "MB52_20261027_020000.csv"
        mb52_content = "material_code,qty\nMAT_PIGMENT,999\n"
        mb52_file.write_text(mb52_content, encoding="utf-8")
        # Write corrupted expected checksum
        verifier.write_companion_checksum(
            mb52_file,
            checksum="0000000000000000000000000000000000000000000000000000000000000000",
        )

        # 4. Drop an UNRELATED file (should be ignored by watcher)
        unrelated = landing_path / "NOTES_MEETING_2026.txt"
        unrelated.write_text("random office notes\n", encoding="utf-8")

        # Execute landing zone scan
        results = watcher.scan_landing_zone()

        # Should discover the 3 target SAP batch drops (ignoring the unrelated file)
        assert len(results) == 3
        res_by_name = {r.filename: r for r in results}

        # Assert FAGLL03 Valid
        fagll_res = res_by_name["FAGLL03_20261027_020000.csv"]
        assert fagll_res.is_valid is True
        assert fagll_res.status == VerificationStatus.VALID
        assert fagll_res.local_final_path is not None
        assert fagll_res.local_final_path.is_file()
        assert (config.local_processed_dir / "FAGLL03_20261027_020000.csv").exists()

        # Assert VA05 Valid
        va05_res = res_by_name["VA05_20261027_020000.csv"]
        assert va05_res.is_valid is True
        assert va05_res.status == VerificationStatus.VALID
        assert (config.local_processed_dir / "VA05_20261027_020000.csv").exists()

        # Assert MB52 Corrupted and Quarantined
        mb52_res = res_by_name["MB52_20261027_020000.csv"]
        assert mb52_res.is_valid is False
        assert mb52_res.status == VerificationStatus.CORRUPTED
        assert mb52_res.local_final_path is not None
        assert mb52_res.local_final_path.is_file()
        assert "QUARANTINED" in mb52_res.local_final_path.name
        # Staging file is cleared
        assert not (config.local_staging_dir / "MB52_20261027_020000.csv").exists()
        # Remote file moved to remote quarantine
        assert (sftp_client.quarantine_dir / "MB52_20261027_020000.csv").exists()

    async def test_ingestion_callback_triggers_only_on_valid_drops(
        self,
        sftp_env: tuple[SyntheticRemoteSFTPClient, SFTPWatcherConfig],
    ) -> None:
        sftp_client, config = sftp_env
        verifier = FileVerifier(quarantine_dir=config.local_quarantine_dir)

        triggered_reports: list[str] = []

        async def mock_ingestion_pipeline(res: BatchProcessingResult) -> None:
            triggered_reports.append(res.filename)

        watcher = SAPSFTPWatcher(
            config=config,
            verifier=verifier,
            sftp_client=sftp_client,
            ingestion_callback=mock_ingestion_pipeline,
        )

        landing_path = sftp_client.landing_dir

        # Valid ME2L procurement register
        me2l_file = landing_path / "ME2L_20261027_020000.csv"
        me2l_content = "po_num,vendor,amount\nPO_101,SUPPLIER_DHAKA,85000\n"
        me2l_file.write_text(me2l_content, encoding="utf-8")
        verifier.write_companion_checksum(me2l_file)

        # Corrupted FAGLL03 file
        fagll_corrupt = landing_path / "FAGLL03_CORRUPTED.csv"
        fagll_corrupt.write_text("bad data", encoding="utf-8")
        verifier.write_companion_checksum(
            fagll_corrupt,
            checksum="badbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadb",
        )

        # Run 1 iteration of daemon
        await watcher.run_daemon(max_iterations=1)

        # Ingestion pipeline must ONLY have been triggered for valid ME2L
        assert "ME2L_20261027_020000.csv" in triggered_reports
        assert "FAGLL03_CORRUPTED.csv" not in triggered_reports

    async def test_daemon_lifecycle_and_graceful_shutdown(
        self,
        sftp_env: tuple[SyntheticRemoteSFTPClient, SFTPWatcherConfig],
    ) -> None:
        sftp_client, config = sftp_env
        verifier = FileVerifier(quarantine_dir=config.local_quarantine_dir)
        watcher = SAPSFTPWatcher(config=config, verifier=verifier, sftp_client=sftp_client)

        stop_event = asyncio.Event()

        # Schedule stop signal after short delay
        async def trigger_stop() -> None:
            await asyncio.sleep(0.05)
            stop_event.set()

        asyncio.create_task(trigger_stop())

        # Daemon should cleanly terminate upon stop_event
        results = await watcher.run_daemon(stop_event=stop_event)
        assert isinstance(results, list)
        assert sftp_client.connected is False
