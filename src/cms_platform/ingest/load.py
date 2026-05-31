from cms_platform.common.config import Settings


def load_subsamples(subsamples: list[int], settings: Settings) -> None:
    """Stream CMS CSV files for the given subsamples into DuckDB raw tables.

    Uses explicit typed schemas derived from the data dictionary — no type
    inference. Reads in chunks so a single file never fully loads into memory.
    # V2 swap point: replace chunked CSV reader with a Kafka consumer here
    Implemented in WP1.
    """
    raise NotImplementedError("WP1")


def main() -> None:
    settings = Settings()
    load_subsamples(settings.subsamples, settings)
