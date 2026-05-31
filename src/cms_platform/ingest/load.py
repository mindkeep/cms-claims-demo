"""CMS DE-SynPUF CSV → DuckDB loader.

Loads raw CSV files into five DuckDB tables using explicit column schemas
(no type inference). All data columns are stored as VARCHAR in the raw layer.
Idempotent: a file that has already been loaded (identified by _source_file)
is skipped on re-runs.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import duckdb

from cms_platform.common.config import Settings
from cms_platform.common.db import get_connection
from cms_platform.ingest.download import file_names_for_sample

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Allowlisted table names — prevents SQL injection via the table parameter
# ---------------------------------------------------------------------------

_VALID_TABLES: frozenset[str] = frozenset(
    {"raw_beneficiary", "raw_inpatient", "raw_outpatient", "raw_carrier", "raw_pde"}
)

# ---------------------------------------------------------------------------
# Explicit column lists (no type inference — VARCHAR throughout)
# ---------------------------------------------------------------------------

_BENE_COLS: list[str] = [
    "DESYNPUF_ID",
    "BENE_BIRTH_DT",
    "BENE_DEATH_DT",
    "BENE_SEX_IDENT_CD",
    "BENE_RACE_CD",
    "BENE_ESRD_IND",
    "SP_STATE_CODE",
    "BENE_COUNTY_CD",
    "BENE_HI_CVRAGE_TOT_MONS",
    "BENE_SMI_CVRAGE_TOT_MONS",
    "BENE_HMO_CVRAGE_TOT_MONS",
    "PLAN_CVRG_MOS_NUM",
    "SP_ALZHDMTA",
    "SP_CHF",
    "SP_CHRNKIDN",
    "SP_CNCR",
    "SP_COPD",
    "SP_DEPRESSN",
    "SP_DIABETES",
    "SP_ISCHMCHT",
    "SP_OSTEOPRS",
    "SP_RA_OA",
    "SP_STRKETIA",
    "MEDREIMB_IP",
    "BENRES_IP",
    "PPPYMT_IP",
    "MEDREIMB_OP",
    "BENRES_OP",
    "PPPYMT_OP",
    "MEDREIMB_CAR",
    "BENRES_CAR",
    "PPPYMT_CAR",
]

_INPATIENT_COLS: list[str] = [
    "DESYNPUF_ID",
    "CLM_ID",
    "SEGMENT",
    "CLM_FROM_DT",
    "CLM_THRU_DT",
    "PRVDR_NUM",
    "AT_PHYSN_NPI",
    "OP_PHYSN_NPI",
    "OT_PHYSN_NPI",
    "CLM_PMT_AMT",
    "NCH_PRMRY_PYR_CLM_PD_AMT",
    "NCH_BENE_IP_DDCTBL_AMT",
    "NCH_BENE_PTA_COINSRNC_LBLTY_AM",
    "NCH_BENE_BLOOD_DDCTBL_LBLTY_AM",
    "CLM_UTLZTN_DAY_CNT",
    "NCH_BENE_DSCHRG_DT",
    "CLM_DRG_CD",
    *[f"ICD9_DGNS_CD_{i}" for i in range(1, 11)],
    *[f"ICD9_PRCDR_CD_{i}" for i in range(1, 7)],
    *[f"HCPCS_CD_{i}" for i in range(1, 46)],
]

_OUTPATIENT_COLS: list[str] = [
    "DESYNPUF_ID",
    "CLM_ID",
    "SEGMENT",
    "CLM_FROM_DT",
    "CLM_THRU_DT",
    "PRVDR_NUM",
    "AT_PHYSN_NPI",
    "OP_PHYSN_NPI",
    "OT_PHYSN_NPI",
    "NCH_BENE_BLOOD_DDCTBL_LBLTY_AM",
    "CLM_PMT_AMT",
    "NCH_PRMRY_PYR_CLM_PD_AMT",
    "NCH_BENE_PTB_DDCTBL_AMT",
    "NCH_BENE_PTB_COINSRNC_AMT",
    "ADMTNG_ICD9_DGNS_CD",
    *[f"ICD9_DGNS_CD_{i}" for i in range(1, 11)],
    *[f"ICD9_PRCDR_CD_{i}" for i in range(1, 7)],
    *[f"HCPCS_CD_{i}" for i in range(1, 46)],
]

_CARRIER_COLS: list[str] = [
    "DESYNPUF_ID",
    "CLM_ID",
    "CLM_FROM_DT",
    "CLM_THRU_DT",
    *[f"ICD9_DGNS_CD_{i}" for i in range(1, 3)],
    *[f"HCPCS_CD_{i}" for i in range(1, 14)],
    *[f"LINE_NCH_PMT_AMT_{i}" for i in range(1, 14)],
    *[f"LINE_BENE_PTB_DDCTBL_AMT_{i}" for i in range(1, 14)],
    *[f"LINE_BENE_PRMRY_PYR_PD_AMT_{i}" for i in range(1, 14)],
    *[f"LINE_COINSRNC_AMT_{i}" for i in range(1, 14)],
    *[f"LINE_ALOWD_CHRG_AMT_{i}" for i in range(1, 14)],
    *[f"LINE_PRCSG_IND_CD_{i}" for i in range(1, 14)],
    *[f"LINE_PLACE_OF_SRVC_CD_{i}" for i in range(1, 14)],
]

_PDE_COLS: list[str] = [
    "DESYNPUF_ID",
    "PDE_ID",
    "SRVC_DT",
    "PROD_SRVC_ID",
    "QTY_DSPNSD_NUM",
    "DAYS_SUPLY_NUM",
    "PTNT_PAY_AMT",
    "TOT_RX_CST_AMT",
]

# ---------------------------------------------------------------------------
# DDL helpers
# ---------------------------------------------------------------------------


def _col_ddl(cols: list[str], extras: list[str]) -> str:
    """Build a comma-separated list of 'col VARCHAR' definitions."""
    all_cols = cols + extras
    return ",\n    ".join(f"{c} VARCHAR" for c in all_cols)


def _ensure_raw_tables(conn: duckdb.DuckDBPyConnection) -> None:
    """CREATE TABLE IF NOT EXISTS for all 5 raw tables."""
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS raw_beneficiary (
            {_col_ddl(_BENE_COLS, ["_claim_year", "_source_file"])}
        )
    """)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS raw_inpatient (
            {_col_ddl(_INPATIENT_COLS, ["_source_file"])}
        )
    """)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS raw_outpatient (
            {_col_ddl(_OUTPATIENT_COLS, ["_source_file"])}
        )
    """)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS raw_carrier (
            {_col_ddl(_CARRIER_COLS, ["_source_file"])}
        )
    """)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS raw_pde (
            {_col_ddl(_PDE_COLS, ["_source_file"])}
        )
    """)


# ---------------------------------------------------------------------------
# CSV loading helpers
# ---------------------------------------------------------------------------


def _claim_year_from_filename(csv_name: str) -> str:
    """Extract the 4-digit claim year (2008/2009/2010) from a CSV filename."""
    match = re.search(r"(2008|2009|2010)", csv_name)
    if match:
        return match.group(1)
    raise ValueError(f"Cannot determine claim year from filename: {csv_name!r}")


def _load_csv(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    path: Path,
    cols: list[str],
    extra_literals: dict[str, str] | None = None,
) -> None:
    """Idempotently load *path* into *table*.

    Skips the file if ``_source_file`` already contains this path.
    Uses DuckDB's ``read_csv`` with ``all_varchar=true`` — no type inference.
    """
    if table not in _VALID_TABLES:
        raise ValueError(f"Unknown table: {table!r}")

    source_file = str(path)

    # Idempotency check
    row = conn.execute(
        f"SELECT COUNT(*) FROM {table} WHERE _source_file = ?",
        [source_file],
    ).fetchone()
    count: int = int(row[0]) if row is not None else 0
    if count > 0:
        return

    # Build SELECT projection — CSV columns cast to VARCHAR, then literals
    csv_select = ", ".join(f"CAST({c} AS VARCHAR) AS {c}" for c in cols)
    literal_select = ""
    if extra_literals:
        literal_parts = [f"'{v}' AS {k}" for k, v in extra_literals.items()]
        literal_select = ", " + ", ".join(literal_parts)
    literal_select += f", '{source_file}' AS _source_file"

    # ignore_errors=true: SynPUF source data contains malformed rows; silently skip them
    conn.execute(f"""
        INSERT INTO {table}
        SELECT {csv_select}{literal_select}
        FROM read_csv(
            '{path}',
            header=true,
            all_varchar=true,
            ignore_errors=true
        )
    """)

    # Log rows inserted for this file
    inserted = conn.execute(
        f"SELECT COUNT(*) FROM {table} WHERE _source_file = ?", [source_file]
    ).fetchone()
    inserted_count = int(inserted[0]) if inserted else 0
    logger.info("loaded file=%s table=%s rows=%d", path.name, table, inserted_count)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_subsamples(subsamples: list[int], settings: Settings) -> None:
    """Load CMS CSV files for *subsamples* into DuckDB raw tables.

    Uses explicit column schemas — no type inference. Idempotent: re-running
    with the same subsamples does not duplicate rows.
    """
    # V2 swap point: replace chunked CSV reader with a Kafka consumer here
    conn = get_connection(settings)
    _ensure_raw_tables(conn)

    raw_dir = Path(settings.raw_data_dir)

    for n in subsamples:
        sample_dir = raw_dir / f"sample_{n}"
        for zip_name in file_names_for_sample(n):
            csv_name = zip_name.removesuffix(".zip") + ".csv"
            path = sample_dir / csv_name

            if not path.exists():
                continue

            name_lower = csv_name.lower()

            if "beneficiary" in name_lower:
                year = _claim_year_from_filename(csv_name)
                _load_csv(
                    conn,
                    "raw_beneficiary",
                    path,
                    _BENE_COLS,
                    extra_literals={"_claim_year": year},
                )
            elif "inpatient" in name_lower:
                _load_csv(conn, "raw_inpatient", path, _INPATIENT_COLS)
            elif "outpatient" in name_lower:
                _load_csv(conn, "raw_outpatient", path, _OUTPATIENT_COLS)
            elif "carrier" in name_lower:
                _load_csv(conn, "raw_carrier", path, _CARRIER_COLS)
            elif "prescription" in name_lower:
                _load_csv(conn, "raw_pde", path, _PDE_COLS)

    conn.close()


def main() -> None:
    settings = Settings()
    load_subsamples(settings.subsamples, settings)
