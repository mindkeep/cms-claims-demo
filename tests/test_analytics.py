"""Tests for cms_platform.analytics.queries — WP3 analytical SQL library."""

from __future__ import annotations

from pathlib import Path

import duckdb
import polars as pl
import pytest

from cms_platform.common.config import Settings

# ---------------------------------------------------------------------------
# Minimal synthetic CSV data (reused from test_schema.py constants)
# ---------------------------------------------------------------------------

_BENE_HEADER = (
    "DESYNPUF_ID,BENE_BIRTH_DT,BENE_DEATH_DT,BENE_SEX_IDENT_CD,BENE_RACE_CD,"
    "BENE_ESRD_IND,SP_STATE_CODE,BENE_COUNTY_CD,BENE_HI_CVRAGE_TOT_MONS,"
    "BENE_SMI_CVRAGE_TOT_MONS,BENE_HMO_CVRAGE_TOT_MONS,PLAN_CVRG_MOS_NUM,"
    "SP_ALZHDMTA,SP_CHF,SP_CHRNKIDN,SP_CNCR,SP_COPD,SP_DEPRESSN,SP_DIABETES,"
    "SP_ISCHMCHT,SP_OSTEOPRS,SP_RA_OA,SP_STRKETIA,MEDREIMB_IP,BENRES_IP,"
    "PPPYMT_IP,MEDREIMB_OP,BENRES_OP,PPPYMT_OP,MEDREIMB_CAR,BENRES_CAR,PPPYMT_CAR"
)
# sp_diabetes = '1' (TRUE) so care_gap query will find this beneficiary
_BENE_ROW = (
    "BENE_001,19300101,,,1,2,N,10,12,12,0,12,2,1,1,2,2,1,1,2,1,2,2,1000,0,0,500,0,0,200,0,0"
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
_INPATIENT_ROW = (
    "BENE_001,CLM_IP_001,1,20080101,20080105,PRVDR_001,N001,,,5000,0,250,0,0,5,20080105,470,"
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
_OUTPATIENT_ROW = (
    "BENE_001,CLM_OP_001,1,20080201,20080201,PRVDR_002,N001,,,0,200,0,50,0,,"
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
_CARRIER_COLS_COUNT = 4 + 2 + 13 + 13 * 7
_CARRIER_ROW = "BENE_001,CLM_CAR_001,20080301,20080301" + "," * (_CARRIER_COLS_COUNT - 1)

_PDE_HEADER = (
    "DESYNPUF_ID,PDE_ID,SRVC_DT,PROD_SRVC_ID,QTY_DSPNSD_NUM,DAYS_SUPLY_NUM,"
    "PTNT_PAY_AMT,TOT_RX_CST_AMT"
)
_PDE_ROW = "BENE_001,PDE_001,20080115,RX001,30,30,10,50"


def _write_sample_csvs(sample_dir: Path) -> None:
    """Write minimal synthetic CSVs matching all 8 SynPUF file types."""
    sample_dir.mkdir(parents=True, exist_ok=True)
    n = int(sample_dir.name.split("_")[1])

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
# Fixture: fully loaded star schema connection
# ---------------------------------------------------------------------------

@pytest.fixture
def star_conn(tmp_path: Path) -> duckdb.DuckDBPyConnection:
    """DuckDB connection with raw tables loaded and star schema built."""
    from cms_platform.common.db import get_connection
    from cms_platform.ingest.load import load_subsamples
    from cms_platform.schema.transforms import build_star_schema

    raw_dir = tmp_path / "raw"
    _write_sample_csvs(raw_dir / "sample_1")

    settings = Settings(
        db_path=str(tmp_path / "test.duckdb"),
        raw_data_dir=str(raw_dir),
        manifests_dir=str(tmp_path / "manifests"),
    )
    load_subsamples([1], settings)
    # build_star_schema closes its own connection; open a fresh one after
    conn = get_connection(settings)
    build_star_schema(conn, settings)
    return conn


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_readmission_30day_returns_dataframe(
    star_conn: duckdb.DuckDBPyConnection,
) -> None:
    """readmission_30day returns a pl.DataFrame with expected columns."""
    from cms_platform.analytics.queries import readmission_30day

    df = readmission_30day(star_conn)
    assert isinstance(df, pl.DataFrame)
    expected_cols = {"claim_year", "total_admissions", "readmissions", "readmission_rate_pct"}
    assert expected_cols.issubset(set(df.columns)), (
        f"Missing columns: {expected_cols - set(df.columns)}"
    )


def test_cohort_segmentation_returns_dataframe(
    star_conn: duckdb.DuckDBPyConnection,
) -> None:
    """cohort_segmentation returns a pl.DataFrame with expected columns."""
    from cms_platform.analytics.queries import cohort_segmentation

    df = cohort_segmentation(star_conn)
    assert isinstance(df, pl.DataFrame)
    expected_cols = {
        "claim_year",
        "total_beneficiaries",
        "diabetes_cohort",
        "chf_cohort",
        "copd_cohort",
        "cancer_cohort",
        "avg_comorbidities",
        "max_comorbidities",
    }
    assert expected_cols.issubset(set(df.columns)), (
        f"Missing columns: {expected_cols - set(df.columns)}"
    )


def test_cost_benchmarking_returns_dataframe(
    star_conn: duckdb.DuckDBPyConnection,
) -> None:
    """cost_benchmarking returns a pl.DataFrame with expected columns."""
    from cms_platform.analytics.queries import cost_benchmarking

    df = cost_benchmarking(star_conn)
    assert isinstance(df, pl.DataFrame)
    expected_cols = {"claim_year", "avg_cost", "p50_cost", "p90_cost", "p99_cost"}
    assert expected_cols.issubset(set(df.columns)), (
        f"Missing columns: {expected_cols - set(df.columns)}"
    )


def test_care_gap_detection_returns_dataframe(
    star_conn: duckdb.DuckDBPyConnection,
) -> None:
    """care_gap_detection returns a pl.DataFrame with expected columns."""
    from cms_platform.analytics.queries import care_gap_detection

    df = care_gap_detection(star_conn)
    assert isinstance(df, pl.DataFrame)
    expected_cols = {
        "claim_year",
        "diabetic_beneficiaries",
        "with_care_gap",
        "care_gap_rate_pct",
    }
    assert expected_cols.issubset(set(df.columns)), (
        f"Missing columns: {expected_cols - set(df.columns)}"
    )


def test_utilization_trends_returns_dataframe(
    star_conn: duckdb.DuckDBPyConnection,
) -> None:
    """utilization_trends returns a pl.DataFrame with expected columns."""
    from cms_platform.analytics.queries import utilization_trends

    df = utilization_trends(star_conn)
    assert isinstance(df, pl.DataFrame)
    expected_cols = {"claim_year", "claim_type", "claim_count", "total_cost"}
    assert expected_cols.issubset(set(df.columns)), (
        f"Missing columns: {expected_cols - set(df.columns)}"
    )


def test_utilization_trends_has_all_claim_types(
    star_conn: duckdb.DuckDBPyConnection,
) -> None:
    """utilization_trends result includes all 4 claim types."""
    from cms_platform.analytics.queries import utilization_trends

    df = utilization_trends(star_conn)
    found_types = set(df["claim_type"].to_list())
    expected_types = {"inpatient", "outpatient", "carrier", "pde"}
    assert found_types == expected_types, (
        f"Expected claim types {expected_types}, got {found_types}"
    )
