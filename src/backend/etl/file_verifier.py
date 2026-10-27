"""Nerolac Dash ETL File Verification & SHA-256 Checksum Engine.

Enforces:
1. Cryptographic SHA-256 checksum validation for SAP batch drops (FAGLL03, VA05, MB52, ME2L).
2. Transfer integrity, non-emptiness, and 25MB NFR quota validation before ingestion.
3. Automated quarantine handling for corrupted, truncated, or incomplete file uploads.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

logger = logging.getLogger("nerolac.etl.file_verifier")


class SAPReportType(str, Enum):
    """Supported SAP ERP operational batch reports."""

    FAGLL03 = "FAGLL03"  # Financial G/L Account Line Items (Finance Actuals)
    VA05 = "VA05"  # Sales Order List / Customer Orders (SCM Sales)
    MB52 = "MB52"  # Warehouse Material Stock / Inventory
    ME2L = "ME2L"  # Purchase Orders by Vendor (Procurement Register)
    UNKNOWN = "UNKNOWN"  # Unrecognized file type


class VerificationStatus(str, Enum):
    """File transfer integrity and verification outcome statuses."""

    VALID = "VALID"
    CORRUPTED = "CORRUPTED"
    INCOMPLETE = "INCOMPLETE"
    MISSING_CHECKSUM = "MISSING_CHECKSUM"
    EMPTY_FILE = "EMPTY_FILE"
    EXCEEDS_SIZE_LIMIT = "EXCEEDS_SIZE_LIMIT"
    QUARANTINED = "QUARANTINED"
    UNSUPPORTED = "UNSUPPORTED"
    NOT_FOUND = "NOT_FOUND"


REPORT_TYPE_PATTERN = re.compile(
    r"(?:^|[_\-.])(FAGLL03|VA05|MB52|ME2L)(?:[_\-.]|$)",
    re.IGNORECASE,
)

HEX_SHA256_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")


def identify_report_type(file_name: str | Path) -> SAPReportType:
    """Identify the SAP batch report type from the filename.

    Recognizes standard SAP drop nomenclature:
    - FAGLL03_20261027_020000.csv -> SAPReportType.FAGLL03
    - VA05_DAILY_SALES.csv        -> SAPReportType.VA05
    - MB52_INVENTORY_STOCK.csv    -> SAPReportType.MB52
    - ME2L_PO_REGISTER.csv        -> SAPReportType.ME2L
    """
    name = Path(file_name).name
    match = REPORT_TYPE_PATTERN.search(name)
    if match:
        code = match.group(1).upper()
        try:
            return SAPReportType(code)
        except ValueError:
            return SAPReportType.UNKNOWN
    return SAPReportType.UNKNOWN


@dataclass
class QuarantineMetadata:
    """Audit record saved alongside quarantined corrupt or incomplete drops."""

    original_filename: str
    original_path: str
    quarantine_path: str
    quarantined_at: str
    reason: str
    status: str
    report_type: str
    file_size_bytes: int
    calculated_sha256: str
    expected_sha256: str | None

    def to_json(self) -> str:
        """Serialize quarantine metadata to formatted JSON."""
        return json.dumps(asdict(self), indent=2)


@dataclass
class VerificationResult:
    """Detailed result of SHA-256 checksum and integrity verification."""

    file_path: Path
    report_type: SAPReportType
    status: VerificationStatus
    is_valid: bool
    calculated_sha256: str
    expected_sha256: str | None = None
    file_size_bytes: int = 0
    quarantine_path: Path | None = None
    metadata_path: Path | None = None
    error_message: str | None = None
    verified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class FileVerifier:
    """Enterprise Checksum Engine & File Quarantine Handler for SAP SFTP drops."""

    # Default 25MB NFR quota per threat model (THREAT-SFTP-D01)
    DEFAULT_MAX_FILE_SIZE = 25 * 1024 * 1024

    # Default streaming buffer chunk size (64KB)
    DEFAULT_CHUNK_SIZE = 65536

    INCOMPLETE_EXTENSIONS = (
        ".part",
        ".tmp",
        ".crdownload",
        ".download",
        ".uploading",
        ".partial",
    )

    ALLOWED_EXTENSIONS = (
        ".csv",
        ".dat",
        ".txt",
        ".tsv",
        ".xlsx",
    )

    def __init__(
        self,
        quarantine_dir: Path | str = "/tmp/nerolac_etl/quarantine",  # nosec B108
        max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        require_checksum: bool = True,
    ) -> None:
        self.quarantine_dir = Path(quarantine_dir)
        self.max_file_size_bytes = max_file_size_bytes
        self.chunk_size = chunk_size
        self.require_checksum = require_checksum

    def compute_sha256(self, file_path: Path | str) -> str:
        """Compute cryptographic SHA-256 checksum using chunked streaming."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Cannot compute hash: file '{path}' does not exist.")

        hasher = hashlib.sha256()
        with path.open("rb") as f:
            while chunk := f.read(self.chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest().lower()

    def find_companion_checksum_file(self, file_path: Path | str) -> Path | None:
        """Locate companion .sha256 or .chk file for a given batch drop."""
        path = Path(file_path)
        parent = path.parent
        name = path.name
        stem = path.stem

        candidates = [
            parent / f"{name}.sha256",
            parent / f"{name}.sha256sum",
            parent / f"{name}.chk",
            parent / f"{stem}.sha256",
            parent / f"{stem}.chk",
        ]

        for cand in candidates:
            if cand.is_file():
                return cand
        return None

    def read_companion_checksum(self, file_path: Path | str) -> str | None:
        """Read and extract expected SHA-256 hash from companion checksum file."""
        companion = self.find_companion_checksum_file(file_path)
        if not companion:
            return None

        try:
            content = companion.read_text(encoding="utf-8").strip()
            # Standard sha256sum format: "<hash>  <filename>" or just "<hash>"
            parts = content.split()
            for part in parts:
                clean_part = part.strip().strip("*").lower()
                if HEX_SHA256_PATTERN.match(clean_part):
                    return clean_part
        except Exception as exc:
            logger.warning("Failed to parse companion checksum file %s: %s", companion, exc)

        return None

    def write_companion_checksum(
        self,
        file_path: Path | str,
        checksum: str | None = None,
    ) -> Path:
        """Generate and save companion .sha256 file for testing or export pipelines."""
        path = Path(file_path)
        hash_val = checksum or self.compute_sha256(path)
        companion_path = path.parent / f"{path.name}.sha256"
        companion_path.write_text(f"{hash_val}  {path.name}\n", encoding="utf-8")
        return companion_path

    def quarantine_file(
        self,
        file_path: Path | str,
        reason: str,
        status: VerificationStatus = VerificationStatus.QUARANTINED,
        calculated_hash: str = "",
        expected_hash: str | None = None,
        report_type: SAPReportType | None = None,
    ) -> tuple[Path, Path]:
        """Move corrupted or incomplete file into the quarantine directory with audit metadata."""
        src_path = Path(file_path)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

        if report_type is None:
            report_type = identify_report_type(src_path)

        # Unique quarantine destination preventing collisions
        timestamp_slug = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        unique_token = uuid.uuid4().hex[:8]
        dest_filename = (
            f"{src_path.stem}_QUARANTINED_{timestamp_slug}_{unique_token}{src_path.suffix}"
        )
        quarantine_dest = self.quarantine_dir / dest_filename

        # Move the source file safely
        if src_path.is_file():
            shutil.move(str(src_path), str(quarantine_dest))
            file_size = quarantine_dest.stat().st_size
        else:
            file_size = 0

        # Create companion quarantine metadata audit file
        metadata = QuarantineMetadata(
            original_filename=src_path.name,
            original_path=str(src_path.resolve()),
            quarantine_path=str(quarantine_dest.resolve()),
            quarantined_at=datetime.now(timezone.utc).isoformat(),
            reason=reason,
            status=status.value,
            report_type=report_type.value,
            file_size_bytes=file_size,
            calculated_sha256=calculated_hash,
            expected_sha256=expected_hash,
        )
        meta_dest = self.quarantine_dir / f"{dest_filename}.quarantine_meta.json"
        meta_dest.write_text(metadata.to_json(), encoding="utf-8")

        # Also remove or quarantine companion .sha256 file if present
        companion = self.find_companion_checksum_file(src_path)
        if companion and companion.is_file():
            try:
                companion_dest = self.quarantine_dir / f"{dest_filename}.sha256"
                shutil.move(str(companion), str(companion_dest))
            except Exception as exc:
                logger.debug("Could not move companion checksum file: %s", exc)

        logger.warning(
            "QUARANTINE ENFORCED: %s moved to %s. Reason: %s",
            src_path.name,
            quarantine_dest,
            reason,
        )

        return quarantine_dest, meta_dest

    def verify_file(
        self,
        file_path: Path | str,
        expected_sha256: str | None = None,
        auto_quarantine: bool = True,
        quarantine_reason: str | None = None,
    ) -> VerificationResult:
        """Execute full transfer integrity and cryptographic SHA-256 verification."""
        path = Path(file_path)
        report_type = identify_report_type(path)

        # 1. Existence Check
        if not path.is_file():
            return VerificationResult(
                file_path=path,
                report_type=report_type,
                status=VerificationStatus.NOT_FOUND,
                is_valid=False,
                calculated_sha256="",
                error_message=f"File not found: '{path}'",
            )

        # 2. Incomplete Transfer File Extension Check
        name_lower = path.name.lower()
        if any(name_lower.endswith(ext) for ext in self.INCOMPLETE_EXTENSIONS):
            err_msg = f"Incomplete file transfer detected from temporary extension: '{path.name}'"
            quarantine_path = None
            meta_path = None
            if auto_quarantine:
                quarantine_path, meta_path = self.quarantine_file(
                    path,
                    reason=quarantine_reason or err_msg,
                    status=VerificationStatus.INCOMPLETE,
                    report_type=report_type,
                )
            return VerificationResult(
                file_path=path,
                report_type=report_type,
                status=VerificationStatus.INCOMPLETE,
                is_valid=False,
                calculated_sha256="",
                quarantine_path=quarantine_path,
                metadata_path=meta_path,
                error_message=err_msg,
            )

        # 3. File Size Checks
        file_size = path.stat().st_size
        if file_size == 0:
            err_msg = f"Zero-byte empty file detected: '{path.name}'"
            quarantine_path = None
            meta_path = None
            if auto_quarantine:
                quarantine_path, meta_path = self.quarantine_file(
                    path,
                    reason=quarantine_reason or err_msg,
                    status=VerificationStatus.EMPTY_FILE,
                    report_type=report_type,
                )
            return VerificationResult(
                file_path=path,
                report_type=report_type,
                status=VerificationStatus.EMPTY_FILE,
                is_valid=False,
                calculated_sha256="",
                file_size_bytes=0,
                quarantine_path=quarantine_path,
                metadata_path=meta_path,
                error_message=err_msg,
            )

        if file_size > self.max_file_size_bytes:
            err_msg = (
                f"File size {file_size} bytes exceeds maximum threshold of "
                f"{self.max_file_size_bytes} bytes (25MB quota)."
            )
            calc_hash = self.compute_sha256(path)
            quarantine_path = None
            meta_path = None
            if auto_quarantine:
                quarantine_path, meta_path = self.quarantine_file(
                    path,
                    reason=quarantine_reason or err_msg,
                    status=VerificationStatus.EXCEEDS_SIZE_LIMIT,
                    calculated_hash=calc_hash,
                    report_type=report_type,
                )
            return VerificationResult(
                file_path=path,
                report_type=report_type,
                status=VerificationStatus.EXCEEDS_SIZE_LIMIT,
                is_valid=False,
                calculated_sha256=calc_hash,
                file_size_bytes=file_size,
                quarantine_path=quarantine_path,
                metadata_path=meta_path,
                error_message=err_msg,
            )

        # 4. Compute Streaming Cryptographic SHA-256
        calc_hash = self.compute_sha256(path)

        # 5. Determine Expected SHA-256 Checksum
        exp_hash = expected_sha256
        if not exp_hash:
            exp_hash = self.read_companion_checksum(path)

        if not exp_hash:
            if self.require_checksum:
                err_msg = f"Missing companion checksum (.sha256) for SAP batch file: '{path.name}'"
                quarantine_path = None
                meta_path = None
                if auto_quarantine:
                    quarantine_path, meta_path = self.quarantine_file(
                        path,
                        reason=quarantine_reason or err_msg,
                        status=VerificationStatus.MISSING_CHECKSUM,
                        calculated_hash=calc_hash,
                        report_type=report_type,
                    )
                return VerificationResult(
                    file_path=path,
                    report_type=report_type,
                    status=VerificationStatus.MISSING_CHECKSUM,
                    is_valid=False,
                    calculated_sha256=calc_hash,
                    file_size_bytes=file_size,
                    quarantine_path=quarantine_path,
                    metadata_path=meta_path,
                    error_message=err_msg,
                )
            else:
                # Checksum optional mode: calculate hash without validation
                return VerificationResult(
                    file_path=path,
                    report_type=report_type,
                    status=VerificationStatus.VALID,
                    is_valid=True,
                    calculated_sha256=calc_hash,
                    file_size_bytes=file_size,
                )

        # 6. Compare Calculated vs Expected Hash
        exp_clean = exp_hash.strip().lower()
        calc_clean = calc_hash.strip().lower()

        if calc_clean != exp_clean:
            err_msg = (
                f"SHA-256 Checksum Mismatch! File '{path.name}' is corrupted or tampered. "
                f"Calculated: {calc_clean}, Expected: {exp_clean}"
            )
            quarantine_path = None
            meta_path = None
            if auto_quarantine:
                quarantine_path, meta_path = self.quarantine_file(
                    path,
                    reason=quarantine_reason or err_msg,
                    status=VerificationStatus.CORRUPTED,
                    calculated_hash=calc_clean,
                    expected_hash=exp_clean,
                    report_type=report_type,
                )
            return VerificationResult(
                file_path=path,
                report_type=report_type,
                status=VerificationStatus.CORRUPTED,
                is_valid=False,
                calculated_sha256=calc_clean,
                expected_sha256=exp_clean,
                file_size_bytes=file_size,
                quarantine_path=quarantine_path,
                metadata_path=meta_path,
                error_message=err_msg,
            )

        # 7. File is Fully Valid
        logger.info(
            "INTEGRITY VERIFIED: %s (%s) matches SHA-256 [%s]",
            path.name,
            report_type.value,
            calc_clean,
        )
        return VerificationResult(
            file_path=path,
            report_type=report_type,
            status=VerificationStatus.VALID,
            is_valid=True,
            calculated_sha256=calc_clean,
            expected_sha256=exp_clean,
            file_size_bytes=file_size,
        )
