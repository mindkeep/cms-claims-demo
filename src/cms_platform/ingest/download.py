"""Download pre-generated Synthea CSV data from MITRE's sample data repository.

Synthea (https://synthea.mitre.org) is an open-source synthetic patient
generator by MITRE. We use their published 1 000-patient CSV dataset so the
project runs without requiring a local Java/Synthea installation.

TODO(future-source): support running Synthea locally for custom patient counts:
    java -jar synthea-with-dependencies.jar -p <N> --exporter.csv.export true
TODO(future-source): support Blue Button 2.0 FHIR API for real Medicare data.
"""

from __future__ import annotations

import json
import logging
import zipfile
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

import httpx

from cms_platform.common.config import Settings

logger = logging.getLogger(__name__)


def download_synthea_data(settings: Settings) -> Path:
    """Download the Synthea sample CSV zip and extract to data/raw/synthea/.

    Idempotent: if patients.csv already exists in the target directory, skips
    the download and returns the directory path immediately.

    Returns the directory containing extracted CSV files.
    """
    data_dir = Path(settings.raw_data_dir) / "synthea"
    data_dir.mkdir(parents=True, exist_ok=True)

    if (data_dir / "patients.csv").exists():
        logger.info("Synthea data already present at %s — skipping download", data_dir)
        return data_dir

    logger.info("Downloading Synthea sample data from %s", settings.synthea_data_url)
    with httpx.Client(follow_redirects=True, timeout=120) as client:
        response = client.get(settings.synthea_data_url)
        response.raise_for_status()

    with zipfile.ZipFile(BytesIO(response.content)) as zf:
        csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
        for name in csv_names:
            # Flatten: write only the basename (no subdirectory nesting)
            dest = data_dir / Path(name).name
            dest.write_bytes(zf.read(name))
            logger.info("Extracted %s → %s", name, dest)

    _write_manifest(data_dir, settings.synthea_data_url, csv_names)
    return data_dir


def _write_manifest(data_dir: Path, url: str, csv_names: list[str]) -> None:
    manifest = {
        "source_url": url,
        "downloaded_at": datetime.now(UTC).isoformat(),
        "files": [Path(n).name for n in csv_names],
    }
    manifests_dir = data_dir.parent.parent / "manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    (manifests_dir / "synthea.json").write_text(json.dumps(manifest, indent=2))


def main() -> None:
    from cms_platform.common.config import get_settings
    from cms_platform.common.logging import configure_logging

    settings = get_settings()
    configure_logging(settings.log_level)
    download_synthea_data(settings)
