from pathlib import Path

from cms_platform.common.config import Settings


def download_subsamples(subsamples: list[int], settings: Settings) -> list[Path]:
    """Fetch CMS DE-SynPUF CSV files for the given subsample numbers.

    Downloads to settings.raw_data_dir, verifies 8 files per subsample,
    writes provenance JSON to settings.manifests_dir. Idempotent — skips
    files already present. Implemented in WP1.
    """
    raise NotImplementedError("WP1")


def main() -> None:
    settings = Settings()
    download_subsamples(settings.subsamples, settings)
