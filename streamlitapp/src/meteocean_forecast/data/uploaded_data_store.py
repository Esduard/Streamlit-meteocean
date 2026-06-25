"""
Persistent storage for uploaded meteocean data.

See docs/adr/0002-canonical-dataset-for-exogenous-features.md for the design
this module implements: a staging table of raw per-(plat_id, time) rows is the
source of truth, and the canonical dataset (averaged across platforms per
hourly timestamp) is always *derived* from staging, never mutated in place.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import IO

import pandas as pd

from meteocean_forecast.features.raw_xlsx_reader import EXPECTED_COLUMNS, read_raw_xlsx

UploadedFileLike = Path | str | IO[bytes]

_NUMERIC_COLUMNS: list[str] = [c for c in EXPECTED_COLUMNS if c not in ("time", "plat_id")]

_STAGING_FILENAME = "staging_data.parquet"
_CANONICAL_FILENAME = "canonical_dataset.parquet"
_UPLOAD_LOG_FILENAME = "upload_log.json"


@dataclass(frozen=True)
class UploadLogEntry:
    original_filename: str
    plat_id: str
    days_covered: tuple[str, ...]
    uploaded_at: datetime
    row_count: int


@dataclass(frozen=True)
class RejectedFile:
    filename: str
    reason: str


@dataclass(frozen=True)
class IngestResult:
    accepted: tuple[UploadLogEntry, ...]
    rejected: tuple[RejectedFile, ...]


def _filename_of(file: UploadedFileLike) -> str:
    name = getattr(file, "name", None)
    if name:
        return Path(name).name
    return Path(str(file)).name


def _derive_canonical(staging: pd.DataFrame) -> pd.DataFrame:
    if staging.empty:
        return pd.DataFrame(columns=["time", *_NUMERIC_COLUMNS])
    canonical = (
        staging.groupby("time", as_index=False)[_NUMERIC_COLUMNS]
        .mean()
        .sort_values("time")
        .reset_index(drop=True)
    )
    return canonical


class UploadedDataStore:
    """
    Owns the upload -> staging -> canonical-dataset -> upload-log lifecycle.

    Construct against a writable directory (see path_utils.get_app_data_dir()).
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._staging_path = self._base_dir / _STAGING_FILENAME
        self._canonical_path = self._base_dir / _CANONICAL_FILENAME
        self._log_path = self._base_dir / _UPLOAD_LOG_FILENAME

    def ingest_files(self, files: list[UploadedFileLike]) -> IngestResult:
        accepted: list[UploadLogEntry] = []
        rejected: list[RejectedFile] = []
        new_rows: list[pd.DataFrame] = []

        for file in files:
            filename = _filename_of(file)
            if not filename.lower().endswith(".xlsx"):
                rejected.append(
                    RejectedFile(filename=filename, reason="Only .xlsx files are supported.")
                )
                continue
            try:
                df = read_raw_xlsx(file)
                plat_ids = df["plat_id"].unique()
                if len(plat_ids) != 1:
                    raise ValueError(
                        f"Expected exactly one platform per file, found "
                        f"{len(plat_ids)}: {sorted(str(p) for p in plat_ids)}"
                    )
                plat_id = str(plat_ids[0])
                days_covered = tuple(sorted({ts.date().isoformat() for ts in df["time"]}))
                new_rows.append(df)
                accepted.append(
                    UploadLogEntry(
                        original_filename=filename,
                        plat_id=plat_id,
                        days_covered=days_covered,
                        uploaded_at=datetime.now(),
                        row_count=len(df),
                    )
                )
            except Exception as exc:
                rejected.append(RejectedFile(filename=filename, reason=str(exc)))

        if new_rows:
            staging = self._load_staging()
            frames = [staging, *new_rows] if not staging.empty else new_rows
            combined = pd.concat(frames, ignore_index=True)
            combined = combined.drop_duplicates(subset=["plat_id", "time"], keep="last")
            combined = combined.sort_values(["time", "plat_id"]).reset_index(drop=True)
            self._save_staging(combined)
            self._save_canonical(_derive_canonical(combined))
            self._append_log(accepted)

        return IngestResult(accepted=tuple(accepted), rejected=tuple(rejected))

    def load_canonical_dataset(self) -> pd.DataFrame:
        if not self._canonical_path.exists():
            return pd.DataFrame(columns=["time", *_NUMERIC_COLUMNS])
        return pd.read_parquet(self._canonical_path)

    def latest_canonical_timestamp(self) -> datetime | None:
        canonical = self.load_canonical_dataset()
        if canonical.empty:
            return None
        return pd.Timestamp(canonical["time"].max()).to_pydatetime()

    def upload_log(self) -> list[UploadLogEntry]:
        if not self._log_path.exists():
            return []
        raw = json.loads(self._log_path.read_text())
        return [
            UploadLogEntry(
                original_filename=entry["original_filename"],
                plat_id=entry["plat_id"],
                days_covered=tuple(entry["days_covered"]),
                uploaded_at=datetime.fromisoformat(entry["uploaded_at"]),
                row_count=entry["row_count"],
            )
            for entry in raw["uploads"]
        ]

    def _load_staging(self) -> pd.DataFrame:
        if not self._staging_path.exists():
            return pd.DataFrame(columns=EXPECTED_COLUMNS)
        return pd.read_parquet(self._staging_path)

    def _save_staging(self, df: pd.DataFrame) -> None:
        df.to_parquet(self._staging_path, index=False)

    def _save_canonical(self, df: pd.DataFrame) -> None:
        df.to_parquet(self._canonical_path, index=False)

    def _append_log(self, new_entries: list[UploadLogEntry]) -> None:
        existing = self.upload_log()
        combined = existing + new_entries
        latest = self.latest_canonical_timestamp()
        payload = {
            "uploads": [
                {**asdict(entry), "uploaded_at": entry.uploaded_at.isoformat()}
                for entry in combined
            ],
            "latest_canonical_timestamp": latest.isoformat() if latest is not None else None,
        }
        self._log_path.write_text(json.dumps(payload, indent=2))
