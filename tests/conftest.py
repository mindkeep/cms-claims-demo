from pathlib import Path

import pytest

from cms_platform.common.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=str(tmp_path / "test.duckdb"),
        raw_data_dir=str(tmp_path / "raw"),
        manifests_dir=str(tmp_path / "manifests"),
    )
