"""Tests for cms_platform.ingest.download and cms_platform.ingest.load."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cms_platform.common.config import Settings

# ---------------------------------------------------------------------------
# Helpers shared between download and load tests
# ---------------------------------------------------------------------------

def _make_zip_bytes(csv_name: str, csv_content: str) -> bytes:
    """Build a real in-memory zip containing one CSV member."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr(csv_name, csv_content)
    return buf.getvalue()


def _make_zip_response(zip_name: str) -> MagicMock:
    """Return a mock httpx Response whose .content is a valid zip."""
    csv_name = zip_name.replace(".zip", ".csv")
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.content = _make_zip_bytes(csv_name, "header\nrow\n")
    return resp


def _patch_httpx(settings: Settings, subsamples: list[int]) -> list[Path]:
    """Call download_subsamples with a mocked httpx.Client."""
    from cms_platform.ingest.download import download_subsamples

    mock_http = MagicMock()
    mock_http.get.side_effect = lambda url, **_kwargs: _make_zip_response(url.split("/")[-1])

    with patch("cms_platform.ingest.download.httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        return download_subsamples(subsamples, settings)


# ---------------------------------------------------------------------------
# download.py — file_names_for_sample
# ---------------------------------------------------------------------------

def test_file_names_for_sample_1() -> None:
    from cms_platform.ingest.download import file_names_for_sample

    names = file_names_for_sample(1)
    assert len(names) == 8
    assert "DE1_0_2008_Beneficiary_Summary_File_Sample_1.zip" in names
    assert "DE1_0_2008_to_2010_Carrier_Claims_Sample_1A.zip" in names
    assert "DE1_0_2008_to_2010_Carrier_Claims_Sample_1B.zip" in names
    assert "DE1_0_2008_to_2010_Prescription_Drug_Events_Sample_1.zip" in names


def test_file_names_for_sample_20() -> None:
    from cms_platform.ingest.download import file_names_for_sample

    names = file_names_for_sample(20)
    assert len(names) == 8
    assert "DE1_0_2008_Beneficiary_Summary_File_Sample_20.zip" in names
    assert "DE1_0_2008_to_2010_Carrier_Claims_Sample_20A.zip" in names
    assert "DE1_0_2008_to_2010_Carrier_Claims_Sample_20B.zip" in names
    assert "DE1_0_2008_to_2010_Inpatient_Claims_Sample_20.zip" in names


# ---------------------------------------------------------------------------
# download.py — download_subsamples
# ---------------------------------------------------------------------------

def test_download_skips_existing_files(settings: Settings) -> None:
    """Pre-create all 8 CSVs; httpx.Client.get must never be called."""
    from cms_platform.ingest.download import file_names_for_sample

    sample_dir = Path(settings.raw_data_dir) / "sample_1"
    sample_dir.mkdir(parents=True, exist_ok=True)
    for zip_name in file_names_for_sample(1):
        csv_name = zip_name.replace(".zip", ".csv")
        (sample_dir / csv_name).write_text("header\nrow\n")

    mock_http = MagicMock()

    with patch("cms_platform.ingest.download.httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        from cms_platform.ingest.download import download_subsamples

        download_subsamples([1], settings)

    mock_http.get.assert_not_called()


def test_download_writes_manifest(settings: Settings) -> None:
    """Mock httpx; verify manifest JSON has correct structure."""
    _patch_httpx(settings, [1])

    manifest_path = Path(settings.manifests_dir) / "sample_1.json"
    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text())
    assert data["sample"] == 1
    assert "downloaded_at" in data
    assert len(data["files"]) == 8
    assert all("name" in f and "path" in f for f in data["files"])


def test_download_returns_csv_paths(settings: Settings) -> None:
    """Mock httpx; returned paths must all exist and end with .csv."""
    paths = _patch_httpx(settings, [1])

    assert len(paths) == 8
    for p in paths:
        assert p.suffix == ".csv", f"Expected .csv suffix, got {p.suffix}"
        assert p.exists(), f"Expected {p} to exist on disk"


# ---------------------------------------------------------------------------
# load.py — synthetic CSV fixtures
# ---------------------------------------------------------------------------

_BENE_HEADER = (
    "DESYNPUF_ID,BENE_BIRTH_DT,BENE_DEATH_DT,BENE_SEX_IDENT_CD,BENE_RACE_CD,"
    "BENE_ESRD_IND,SP_STATE_CODE,BENE_COUNTY_CD,BENE_HI_CVRAGE_TOT_MONS,"
    "BENE_SMI_CVRAGE_TOT_MONS,BENE_HMO_CVRAGE_TOT_MONS,PLAN_CVRG_MOS_NUM,"
    "SP_ALZHDMTA,SP_CHF,SP_CHRNKIDN,SP_CNCR,SP_COPD,SP_DEPRESSN,SP_DIABETES,"
    "SP_ISCHMCHT,SP_OSTEOPRS,SP_RA_OA,SP_STRKETIA,MEDREIMB_IP,BENRES_IP,"
    "PPPYMT_IP,MEDREIMB_OP,BENRES_OP,PPPYMT_OP,MEDREIMB_CAR,BENRES_CAR,PPPYMT_CAR"
)
_BENE_ROW = (
    "B001,19300101,,,1,2,N,10,12,12,0,12,2,1,1,2,2,1,2,2,1,2,2,1000,0,0,500,0,0,200,0,0"
)

_INPATIENT_HEADER = (
    "DESYNPUF_ID,CLM_ID,SEGMENT,CLM_FROM_DT,CLM_THRU_DT,PRVDR_NUM,AT_PHYSN_NPI,"
    "OP_PHYSN_NPI,OT_PHYSN_NPI,CLM_PMT_AMT,NCH_PRMRY_PYR_CLM_PD_AMT,"
    "NCH_BENE_IP_DDCTBL_AMT,NCH_BENE_PTA_COINSRNC_LBLTY_AM,NCH_BENE_BLOOD_DDCTBL_LBLTY_AM,"
    "CLM_UTLZTN_DAY_CNT,NCH_BENE_DSCHRG_DT,CLM_DRG_CD,"
    "ICD9_DGNS_CD_1,ICD9_DGNS_CD_2,ICD9_DGNS_CD_3,ICD9_DGNS_CD_4,ICD9_DGNS_CD_5,"
    "ICD9_DGNS_CD_6,ICD9_DGNS_CD_7,ICD9_DGNS_CD_8,ICD9_DGNS_CD_9,ICD9_DGNS_CD_10,"
    "ICD9_PRCDR_CD_1,ICD9_PRCDR_CD_2,ICD9_PRCDR_CD_3,ICD9_PRCDR_CD_4,"
    "ICD9_PRCDR_CD_5,ICD9_PRCDR_CD_6,"
    "HCPCS_CD_1,HCPCS_CD_2,HCPCS_CD_3,HCPCS_CD_4,HCPCS_CD_5,HCPCS_CD_6,"
    "HCPCS_CD_7,HCPCS_CD_8,HCPCS_CD_9,HCPCS_CD_10,HCPCS_CD_11,HCPCS_CD_12,"
    "HCPCS_CD_13,HCPCS_CD_14,HCPCS_CD_15,HCPCS_CD_16,HCPCS_CD_17,HCPCS_CD_18,"
    "HCPCS_CD_19,HCPCS_CD_20,HCPCS_CD_21,HCPCS_CD_22,HCPCS_CD_23,HCPCS_CD_24,"
    "HCPCS_CD_25,HCPCS_CD_26,HCPCS_CD_27,HCPCS_CD_28,HCPCS_CD_29,HCPCS_CD_30,"
    "HCPCS_CD_31,HCPCS_CD_32,HCPCS_CD_33,HCPCS_CD_34,HCPCS_CD_35,HCPCS_CD_36,"
    "HCPCS_CD_37,HCPCS_CD_38,HCPCS_CD_39,HCPCS_CD_40,HCPCS_CD_41,HCPCS_CD_42,"
    "HCPCS_CD_43,HCPCS_CD_44,HCPCS_CD_45"
)
# 17 fixed cols + 10 ICD9_DGNS + 6 ICD9_PRCDR + 45 HCPCS = 78 total
_INPATIENT_ROW = (
    "B001,C001,1,20080101,20080105,P001,N001,,,5000,0,0,0,0,5,20080105,470,"
    + ",".join([""] * 16)
    + ","
    + ",".join([""] * 45)
)

_OUTPATIENT_HEADER = (
    "DESYNPUF_ID,CLM_ID,SEGMENT,CLM_FROM_DT,CLM_THRU_DT,PRVDR_NUM,AT_PHYSN_NPI,"
    "OP_PHYSN_NPI,OT_PHYSN_NPI,NCH_BENE_BLOOD_DDCTBL_LBLTY_AM,CLM_PMT_AMT,"
    "NCH_PRMRY_PYR_CLM_PD_AMT,NCH_BENE_PTB_DDCTBL_AMT,NCH_BENE_PTB_COINSRNC_AMT,"
    "ADMTNG_ICD9_DGNS_CD,"
    "ICD9_DGNS_CD_1,ICD9_DGNS_CD_2,ICD9_DGNS_CD_3,ICD9_DGNS_CD_4,ICD9_DGNS_CD_5,"
    "ICD9_DGNS_CD_6,ICD9_DGNS_CD_7,ICD9_DGNS_CD_8,ICD9_DGNS_CD_9,ICD9_DGNS_CD_10,"
    "ICD9_PRCDR_CD_1,ICD9_PRCDR_CD_2,ICD9_PRCDR_CD_3,ICD9_PRCDR_CD_4,"
    "ICD9_PRCDR_CD_5,ICD9_PRCDR_CD_6,"
    "HCPCS_CD_1,HCPCS_CD_2,HCPCS_CD_3,HCPCS_CD_4,HCPCS_CD_5,HCPCS_CD_6,"
    "HCPCS_CD_7,HCPCS_CD_8,HCPCS_CD_9,HCPCS_CD_10,HCPCS_CD_11,HCPCS_CD_12,"
    "HCPCS_CD_13,HCPCS_CD_14,HCPCS_CD_15,HCPCS_CD_16,HCPCS_CD_17,HCPCS_CD_18,"
    "HCPCS_CD_19,HCPCS_CD_20,HCPCS_CD_21,HCPCS_CD_22,HCPCS_CD_23,HCPCS_CD_24,"
    "HCPCS_CD_25,HCPCS_CD_26,HCPCS_CD_27,HCPCS_CD_28,HCPCS_CD_29,HCPCS_CD_30,"
    "HCPCS_CD_31,HCPCS_CD_32,HCPCS_CD_33,HCPCS_CD_34,HCPCS_CD_35,HCPCS_CD_36,"
    "HCPCS_CD_37,HCPCS_CD_38,HCPCS_CD_39,HCPCS_CD_40,HCPCS_CD_41,HCPCS_CD_42,"
    "HCPCS_CD_43,HCPCS_CD_44,HCPCS_CD_45"
)
# 15 fixed + 10 ICD9_DGNS + 6 ICD9_PRCDR + 45 HCPCS = 76 total
_OUTPATIENT_ROW = (
    "B001,C002,1,20080201,20080201,P002,N001,,,0,200,0,0,0,,"
    + ",".join([""] * 10)
    + ","
    + ",".join([""] * 6)
    + ","
    + ",".join([""] * 45)
)

_CARRIER_HEADER = (
    "DESYNPUF_ID,CLM_ID,CLM_FROM_DT,CLM_THRU_DT,"
    "ICD9_DGNS_CD_1,ICD9_DGNS_CD_2,"
    "HCPCS_CD_1,HCPCS_CD_2,HCPCS_CD_3,HCPCS_CD_4,HCPCS_CD_5,HCPCS_CD_6,"
    "HCPCS_CD_7,HCPCS_CD_8,HCPCS_CD_9,HCPCS_CD_10,HCPCS_CD_11,HCPCS_CD_12,HCPCS_CD_13,"
    "LINE_NCH_PMT_AMT_1,LINE_NCH_PMT_AMT_2,LINE_NCH_PMT_AMT_3,LINE_NCH_PMT_AMT_4,"
    "LINE_NCH_PMT_AMT_5,LINE_NCH_PMT_AMT_6,LINE_NCH_PMT_AMT_7,LINE_NCH_PMT_AMT_8,"
    "LINE_NCH_PMT_AMT_9,LINE_NCH_PMT_AMT_10,LINE_NCH_PMT_AMT_11,LINE_NCH_PMT_AMT_12,"
    "LINE_NCH_PMT_AMT_13,"
    "LINE_BENE_PTB_DDCTBL_AMT_1,LINE_BENE_PTB_DDCTBL_AMT_2,LINE_BENE_PTB_DDCTBL_AMT_3,"
    "LINE_BENE_PTB_DDCTBL_AMT_4,LINE_BENE_PTB_DDCTBL_AMT_5,LINE_BENE_PTB_DDCTBL_AMT_6,"
    "LINE_BENE_PTB_DDCTBL_AMT_7,LINE_BENE_PTB_DDCTBL_AMT_8,LINE_BENE_PTB_DDCTBL_AMT_9,"
    "LINE_BENE_PTB_DDCTBL_AMT_10,LINE_BENE_PTB_DDCTBL_AMT_11,LINE_BENE_PTB_DDCTBL_AMT_12,"
    "LINE_BENE_PTB_DDCTBL_AMT_13,"
    "LINE_BENE_PRMRY_PYR_PD_AMT_1,LINE_BENE_PRMRY_PYR_PD_AMT_2,"
    "LINE_BENE_PRMRY_PYR_PD_AMT_3,LINE_BENE_PRMRY_PYR_PD_AMT_4,"
    "LINE_BENE_PRMRY_PYR_PD_AMT_5,LINE_BENE_PRMRY_PYR_PD_AMT_6,"
    "LINE_BENE_PRMRY_PYR_PD_AMT_7,LINE_BENE_PRMRY_PYR_PD_AMT_8,"
    "LINE_BENE_PRMRY_PYR_PD_AMT_9,LINE_BENE_PRMRY_PYR_PD_AMT_10,"
    "LINE_BENE_PRMRY_PYR_PD_AMT_11,LINE_BENE_PRMRY_PYR_PD_AMT_12,"
    "LINE_BENE_PRMRY_PYR_PD_AMT_13,"
    "LINE_COINSRNC_AMT_1,LINE_COINSRNC_AMT_2,LINE_COINSRNC_AMT_3,LINE_COINSRNC_AMT_4,"
    "LINE_COINSRNC_AMT_5,LINE_COINSRNC_AMT_6,LINE_COINSRNC_AMT_7,LINE_COINSRNC_AMT_8,"
    "LINE_COINSRNC_AMT_9,LINE_COINSRNC_AMT_10,LINE_COINSRNC_AMT_11,LINE_COINSRNC_AMT_12,"
    "LINE_COINSRNC_AMT_13,"
    "LINE_ALOWD_CHRG_AMT_1,LINE_ALOWD_CHRG_AMT_2,LINE_ALOWD_CHRG_AMT_3,"
    "LINE_ALOWD_CHRG_AMT_4,LINE_ALOWD_CHRG_AMT_5,LINE_ALOWD_CHRG_AMT_6,"
    "LINE_ALOWD_CHRG_AMT_7,LINE_ALOWD_CHRG_AMT_8,LINE_ALOWD_CHRG_AMT_9,"
    "LINE_ALOWD_CHRG_AMT_10,LINE_ALOWD_CHRG_AMT_11,LINE_ALOWD_CHRG_AMT_12,"
    "LINE_ALOWD_CHRG_AMT_13,"
    "LINE_PRCSG_IND_CD_1,LINE_PRCSG_IND_CD_2,LINE_PRCSG_IND_CD_3,LINE_PRCSG_IND_CD_4,"
    "LINE_PRCSG_IND_CD_5,LINE_PRCSG_IND_CD_6,LINE_PRCSG_IND_CD_7,LINE_PRCSG_IND_CD_8,"
    "LINE_PRCSG_IND_CD_9,LINE_PRCSG_IND_CD_10,LINE_PRCSG_IND_CD_11,LINE_PRCSG_IND_CD_12,"
    "LINE_PRCSG_IND_CD_13,"
    "LINE_PLACE_OF_SRVC_CD_1,LINE_PLACE_OF_SRVC_CD_2,LINE_PLACE_OF_SRVC_CD_3,"
    "LINE_PLACE_OF_SRVC_CD_4,LINE_PLACE_OF_SRVC_CD_5,LINE_PLACE_OF_SRVC_CD_6,"
    "LINE_PLACE_OF_SRVC_CD_7,LINE_PLACE_OF_SRVC_CD_8,LINE_PLACE_OF_SRVC_CD_9,"
    "LINE_PLACE_OF_SRVC_CD_10,LINE_PLACE_OF_SRVC_CD_11,LINE_PLACE_OF_SRVC_CD_12,"
    "LINE_PLACE_OF_SRVC_CD_13"
)
# 4 fixed + 2 ICD9 + 13 HCPCS + 13*7 line-level = 110 cols
_CARRIER_COLS_COUNT = 4 + 2 + 13 + 13 * 7
_CARRIER_ROW = "B001,C003,20080301,20080301" + "," * (_CARRIER_COLS_COUNT - 1)

_PDE_HEADER = (
    "DESYNPUF_ID,PDE_ID,SRVC_DT,PROD_SRVC_ID,QTY_DSPNSD_NUM,DAYS_SUPLY_NUM,"
    "PTNT_PAY_AMT,TOT_RX_CST_AMT"
)
_PDE_ROW = "B001,P001,20080115,RX001,30,30,10,50"


def _write_sample_files(raw_dir: Path, sample_n: int) -> None:
    """Write minimal synthetic CSVs for all 8 files in sample_n."""
    sample_dir = raw_dir / f"sample_{sample_n}"
    sample_dir.mkdir(parents=True, exist_ok=True)

    n = sample_n
    bene_content = f"{_BENE_HEADER}\n{_BENE_ROW}\n"
    ip_content = f"{_INPATIENT_HEADER}\n{_INPATIENT_ROW}\n"
    op_content = f"{_OUTPATIENT_HEADER}\n{_OUTPATIENT_ROW}\n"
    car_content = f"{_CARRIER_HEADER}\n{_CARRIER_ROW}\n"
    pde_content = f"{_PDE_HEADER}\n{_PDE_ROW}\n"

    files = {
        f"DE1_0_2008_Beneficiary_Summary_File_Sample_{n}.csv": bene_content,
        f"DE1_0_2009_Beneficiary_Summary_File_Sample_{n}.csv": bene_content,
        f"DE1_0_2010_Beneficiary_Summary_File_Sample_{n}.csv": bene_content,
        f"DE1_0_2008_to_2010_Inpatient_Claims_Sample_{n}.csv": ip_content,
        f"DE1_0_2008_to_2010_Outpatient_Claims_Sample_{n}.csv": op_content,
        f"DE1_0_2008_to_2010_Carrier_Claims_Sample_{n}A.csv": car_content,
        f"DE1_0_2008_to_2010_Carrier_Claims_Sample_{n}B.csv": car_content,
        f"DE1_0_2008_to_2010_Prescription_Drug_Events_Sample_{n}.csv": pde_content,
    }
    for fname, content in files.items():
        (sample_dir / fname).write_text(content)


# ---------------------------------------------------------------------------
# load.py tests
# ---------------------------------------------------------------------------

@pytest.fixture
def loaded_settings(settings: Settings) -> Settings:
    """Settings with synthetic CSVs pre-written for sample 1."""
    _write_sample_files(Path(settings.raw_data_dir), 1)
    return settings


def test_load_creates_raw_tables(loaded_settings: Settings) -> None:
    from cms_platform.common.db import get_connection
    from cms_platform.ingest.load import load_subsamples

    load_subsamples([1], loaded_settings)
    conn = get_connection(loaded_settings)
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()
    }
    conn.close()
    expected = {"raw_beneficiary", "raw_inpatient", "raw_outpatient", "raw_carrier", "raw_pde"}
    for tbl in expected:
        assert tbl in tables, f"Missing table: {tbl}"


def test_load_raw_beneficiary_row_count(loaded_settings: Settings) -> None:
    from cms_platform.common.db import get_connection
    from cms_platform.ingest.load import load_subsamples

    load_subsamples([1], loaded_settings)
    conn = get_connection(loaded_settings)
    count = conn.execute("SELECT COUNT(*) FROM raw_beneficiary").fetchone()
    conn.close()
    assert count is not None
    assert count[0] == 3, f"Expected 3 rows (3 bene files × 1 row), got {count[0]}"


def test_load_idempotent(loaded_settings: Settings) -> None:
    from cms_platform.common.db import get_connection
    from cms_platform.ingest.load import load_subsamples

    load_subsamples([1], loaded_settings)
    load_subsamples([1], loaded_settings)
    conn = get_connection(loaded_settings)
    count = conn.execute("SELECT COUNT(*) FROM raw_beneficiary").fetchone()
    conn.close()
    assert count is not None
    assert count[0] == 3, f"Idempotency failed: expected 3 rows, got {count[0]}"


def test_load_source_file_column(loaded_settings: Settings) -> None:
    from cms_platform.common.db import get_connection
    from cms_platform.ingest.load import load_subsamples

    load_subsamples([1], loaded_settings)
    conn = get_connection(loaded_settings)
    rows = conn.execute("SELECT DISTINCT _source_file FROM raw_beneficiary").fetchall()
    conn.close()
    source_files = {row[0] for row in rows}
    assert all("Beneficiary" in sf for sf in source_files), (
        f"Expected 'Beneficiary' in all _source_file values, got: {source_files}"
    )


# ---------------------------------------------------------------------------
# download.py — file_names_for_sample range validation
# ---------------------------------------------------------------------------

def test_file_names_rejects_invalid_sample() -> None:
    from cms_platform.ingest.download import file_names_for_sample
    with pytest.raises(ValueError, match="1–20"):
        file_names_for_sample(0)
    with pytest.raises(ValueError, match="1–20"):
        file_names_for_sample(21)
