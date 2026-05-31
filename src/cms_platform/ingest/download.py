"""CMS DE-SynPUF download module.

Downloads zip files from the CMS public server, extracts CSVs, and writes
provenance manifests. All operations are idempotent — already-present files
are skipped without re-downloading.
"""

from __future__ import annotations

import io
import json
import logging
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

import httpx

from cms_platform.common.config import Settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

_FILE_TEMPLATES: list[str] = [
    "DE1_0_2008_Beneficiary_Summary_File_Sample_{n}.zip",
    "DE1_0_2009_Beneficiary_Summary_File_Sample_{n}.zip",
    "DE1_0_2010_Beneficiary_Summary_File_Sample_{n}.zip",
    "DE1_0_2008_to_2010_Inpatient_Claims_Sample_{n}.zip",
    "DE1_0_2008_to_2010_Outpatient_Claims_Sample_{n}.zip",
    "DE1_0_2008_to_2010_Carrier_Claims_Sample_{n}A.zip",
    "DE1_0_2008_to_2010_Carrier_Claims_Sample_{n}B.zip",
    "DE1_0_2008_to_2010_Prescription_Drug_Events_Sample_{n}.zip",
]


def file_names_for_sample(sample_n: int) -> list[str]:
    """Return the 8 canonical zip filenames for subsample *sample_n* (1–20)."""
    if not 1 <= sample_n <= 20:
        raise ValueError(f"sample_n must be 1–20, got {sample_n}")
    return [t.replace("{n}", str(sample_n)) for t in _FILE_TEMPLATES]


# ---------------------------------------------------------------------------
# Manifest types
# ---------------------------------------------------------------------------

class _ManifestFile(TypedDict):
    name: str
    path: str


class _Manifest(TypedDict):
    sample: int
    downloaded_at: str
    files: list[_ManifestFile]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_csv(zip_bytes: bytes, dest: Path) -> None:
    """Extract the first CSV member from *zip_bytes* to *dest*."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        csv_members = [m for m in zf.namelist() if m.lower().endswith(".csv")]
        if not csv_members:
            raise ValueError(f"No CSV found inside zip (members: {zf.namelist()})")
        if len(csv_members) > 1:
            logger.warning(
                "zip %s contains %d CSVs; loading only %s",
                dest.name,
                len(csv_members),
                csv_members[0],
            )
        member = csv_members[0]
        # Extract to parent dir
        zf.extract(member, path=dest.parent)
        extracted = dest.parent / member
        if extracted != dest:
            extracted.rename(dest)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def download_subsamples(subsamples: list[int], settings: Settings) -> list[Path]:
    """Fetch CMS DE-SynPUF CSV files for the given subsample numbers.

    Downloads to ``settings.raw_data_dir/sample_{n}/``, extracts CSVs,
    and writes provenance JSON to ``settings.manifests_dir/sample_{n}.json``.
    Idempotent — skips files already present on disk.

    Returns a list of Paths to all CSV files (existing + newly downloaded).
    """
    raw_dir = Path(settings.raw_data_dir)
    manifests_dir = Path(settings.manifests_dir)
    manifests_dir.mkdir(parents=True, exist_ok=True)

    all_paths: list[Path] = []

    with httpx.Client(timeout=300.0) as client:
        for n in subsamples:
            sample_dir = raw_dir / f"sample_{n}"
            sample_dir.mkdir(parents=True, exist_ok=True)

            manifest_files: list[_ManifestFile] = []
            any_downloaded = False

            for zip_name in file_names_for_sample(n):
                csv_name = zip_name.removesuffix(".zip") + ".csv"
                dest = sample_dir / csv_name

                if dest.exists():
                    logger.info("skip existing file=%s", dest)
                else:
                    url = f"{settings.cms_synpuf_base_url}/{zip_name}"
                    resp = client.get(url)
                    resp.raise_for_status()
                    _extract_csv(resp.content, dest)
                    any_downloaded = True

                all_paths.append(dest)
                manifest_files.append(_ManifestFile(name=csv_name, path=str(dest)))

            manifest_path = manifests_dir / f"sample_{n}.json"
            if any_downloaded or not manifest_path.exists():
                manifest: _Manifest = {
                    "sample": n,
                    "downloaded_at": datetime.now(tz=UTC).isoformat(),
                    "files": manifest_files,
                }
                manifest_path.write_text(json.dumps(manifest, indent=2))
                logger.info("manifest written path=%s", manifest_path)
            else:
                logger.info(
                    "manifest unchanged (all files already present) path=%s",
                    manifest_path,
                )

    return all_paths


def main() -> None:
    settings = Settings()
    download_subsamples(settings.subsamples, settings)
