"""CMS DE-SynPUF raw tables → star schema transforms.

Builds 4 dimension tables (dim_date, dim_beneficiary, dim_provider, dim_diagnosis),
4 fact tables (fact_inpatient, fact_outpatient, fact_carrier, fact_pde), and a
unified view (fact_claim_line). All populate functions are idempotent.
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from cms_platform.common.config import Settings

logger = logging.getLogger(__name__)

# V2 swap point: partitioning strategy note — at V2, each fact table will be
# hash-partitioned by (claim_year, beneficiary_id_hash % N) so intra-shard
# joins never cross node boundaries.
_DDL_PATH = Path(__file__).parent.parent.parent.parent / "sql" / "schema" / "ddl.sql"


def _run_ddl(conn: duckdb.DuckDBPyConnection) -> None:
    """Execute the DDL file, creating all tables and views."""
    ddl = _DDL_PATH.read_text()
    conn.execute(ddl)


def _populate_dim_date(conn: duckdb.DuckDBPyConnection) -> None:
    """Pre-populate calendar dimension 2007-01-01 through 2011-12-31, idempotent."""
    conn.execute("""
        INSERT INTO dim_date (date_key, full_date, year, month, day, quarter, day_of_week)
        SELECT
            CAST(strftime(d::DATE, '%Y%m%d') AS INTEGER) AS date_key,
            d::DATE                                        AS full_date,
            EXTRACT(YEAR    FROM d)::SMALLINT              AS year,
            EXTRACT(MONTH   FROM d)::SMALLINT              AS month,
            EXTRACT(DAY     FROM d)::SMALLINT              AS day,
            EXTRACT(QUARTER FROM d)::SMALLINT              AS quarter,
            EXTRACT(DOW     FROM d)::SMALLINT              AS day_of_week
        FROM generate_series(DATE '2007-01-01', DATE '2011-12-31', INTERVAL '1 day') AS t(d)
        WHERE NOT EXISTS (
            SELECT 1 FROM dim_date
            WHERE date_key = CAST(strftime(d::DATE, '%Y%m%d') AS INTEGER)
        )
    """)


def _date_key_expr(col: str) -> str:
    """SQL expression: convert YYYYMMDD VARCHAR column to INTEGER date_key, NULL-safe."""
    return f"TRY_CAST({col} AS INTEGER)"


def _varchar_to_date_expr(col: str) -> str:
    """SQL expression: convert YYYYMMDD VARCHAR column to DATE, NULL-safe."""
    return (
        f"TRY_CAST(CASE WHEN LENGTH(NULLIF({col}, '')) = 8"
        f" THEN substr({col},1,4)||'-'||substr({col},5,2)||'-'||substr({col},7,2)"
        f" END AS DATE)"
    )


def _year_from_col(col: str) -> str:
    """SQL expression: extract SMALLINT year from a YYYYMMDD VARCHAR column."""
    return f"EXTRACT(YEAR FROM {_varchar_to_date_expr(col)})::SMALLINT"


def _populate_dim_beneficiary(conn: duckdb.DuckDBPyConnection) -> None:
    """Load dim_beneficiary from raw_beneficiary, one row per (desynpuf_id, claim_year)."""
    conn.execute(f"""
        INSERT INTO dim_beneficiary (
            bene_key, desynpuf_id, claim_year,
            birth_dt, death_dt,
            sex_cd, race_cd, esrd_ind,
            state_code, county_cd,
            hi_coverage_months, smi_coverage_months, hmo_coverage_months, plan_coverage_months,
            sp_alzheimer, sp_chf, sp_chrnkidn, sp_cncr, sp_copd, sp_depressn,
            sp_diabetes, sp_ischmcht, sp_osteoprs, sp_ra_oa, sp_strketia,
            medreimb_ip, medreimb_op, medreimb_car
        )
        SELECT
            ROW_NUMBER() OVER ()
                + COALESCE((SELECT MAX(bene_key) FROM dim_beneficiary), 0) AS bene_key,
            rb.DESYNPUF_ID,
            TRY_CAST(rb._claim_year AS SMALLINT),
            {_varchar_to_date_expr('rb.BENE_BIRTH_DT')},
            {_varchar_to_date_expr('rb.BENE_DEATH_DT')},
            TRY_CAST(rb.BENE_SEX_IDENT_CD     AS SMALLINT),
            TRY_CAST(rb.BENE_RACE_CD          AS SMALLINT),
            rb.BENE_ESRD_IND = '1',
            TRY_CAST(rb.SP_STATE_CODE         AS SMALLINT),
            TRY_CAST(rb.BENE_COUNTY_CD        AS SMALLINT),
            TRY_CAST(rb.BENE_HI_CVRAGE_TOT_MONS  AS SMALLINT),
            TRY_CAST(rb.BENE_SMI_CVRAGE_TOT_MONS AS SMALLINT),
            TRY_CAST(rb.BENE_HMO_CVRAGE_TOT_MONS AS SMALLINT),
            TRY_CAST(rb.PLAN_CVRG_MOS_NUM     AS SMALLINT),
            rb.SP_ALZHDMTA = '1',
            rb.SP_CHF      = '1',
            rb.SP_CHRNKIDN = '1',
            rb.SP_CNCR     = '1',
            rb.SP_COPD     = '1',
            rb.SP_DEPRESSN = '1',
            rb.SP_DIABETES = '1',
            rb.SP_ISCHMCHT = '1',
            rb.SP_OSTEOPRS = '1',
            rb.SP_RA_OA    = '1',
            rb.SP_STRKETIA = '1',
            TRY_CAST(rb.MEDREIMB_IP  AS DECIMAL(12,2)),
            TRY_CAST(rb.MEDREIMB_OP  AS DECIMAL(12,2)),
            TRY_CAST(rb.MEDREIMB_CAR AS DECIMAL(12,2))
        FROM raw_beneficiary rb
        WHERE NOT EXISTS (
            SELECT 1 FROM dim_beneficiary db
            WHERE db.desynpuf_id = rb.DESYNPUF_ID
              AND db.claim_year  = TRY_CAST(rb._claim_year AS SMALLINT)
        )
    """)


def _populate_dim_provider(conn: duckdb.DuckDBPyConnection) -> None:
    """Load distinct provider IDs from inpatient + outpatient claims."""
    conn.execute("""
        INSERT INTO dim_provider (provider_key, provider_id)
        SELECT
            ROW_NUMBER() OVER ()
                + COALESCE((SELECT MAX(provider_key) FROM dim_provider), 0),
            new_p.provider_id
        FROM (
            SELECT DISTINCT PRVDR_NUM AS provider_id FROM raw_inpatient
            WHERE NULLIF(PRVDR_NUM, '') IS NOT NULL
            UNION
            SELECT DISTINCT PRVDR_NUM FROM raw_outpatient
            WHERE NULLIF(PRVDR_NUM, '') IS NOT NULL
        ) AS new_p
        WHERE NOT EXISTS (
            SELECT 1 FROM dim_provider dp WHERE dp.provider_id = new_p.provider_id
        )
    """)


def _populate_dim_diagnosis(conn: duckdb.DuckDBPyConnection) -> None:
    """Load distinct ICD-9 diagnosis codes from all claim types."""
    conn.execute("""
        INSERT INTO dim_diagnosis (dx_key, icd9_code)
        SELECT
            ROW_NUMBER() OVER ()
                + COALESCE((SELECT MAX(dx_key) FROM dim_diagnosis), 0),
            all_dx.icd9_code
        FROM (
            SELECT DISTINCT ICD9_DGNS_CD_1 AS icd9_code
            FROM raw_inpatient  WHERE NULLIF(ICD9_DGNS_CD_1, '') IS NOT NULL
            UNION
            SELECT DISTINCT ICD9_DGNS_CD_1
            FROM raw_outpatient WHERE NULLIF(ICD9_DGNS_CD_1, '') IS NOT NULL
            UNION
            SELECT DISTINCT ICD9_DGNS_CD_1
            FROM raw_carrier    WHERE NULLIF(ICD9_DGNS_CD_1, '') IS NOT NULL
        ) AS all_dx
        WHERE NOT EXISTS (
            SELECT 1 FROM dim_diagnosis d WHERE d.icd9_code = all_dx.icd9_code
        )
    """)


def _populate_fact_inpatient(conn: duckdb.DuckDBPyConnection) -> None:
    """Load fact_inpatient from raw_inpatient, joined to dim_beneficiary + dim_provider."""
    yr = _year_from_col("ri.CLM_FROM_DT")
    conn.execute(f"""
        INSERT INTO fact_inpatient (
            claim_key, desynpuf_id, bene_key, provider_key,
            admit_date_key, discharge_date_key,
            claim_year, clm_id, drg_cd,
            clm_pmt_amt, bene_ip_ddctbl_amt, utilization_day_cnt, primary_dx
        )
        SELECT
            ROW_NUMBER() OVER ()
                + COALESCE((SELECT MAX(claim_key) FROM fact_inpatient), 0),
            ri.DESYNPUF_ID,
            db.bene_key,
            dp.provider_key,
            {_date_key_expr('ri.CLM_FROM_DT')},
            {_date_key_expr('ri.NCH_BENE_DSCHRG_DT')},
            {yr},
            ri.CLM_ID,
            NULLIF(ri.CLM_DRG_CD, ''),
            TRY_CAST(ri.CLM_PMT_AMT            AS DECIMAL(12,2)),
            TRY_CAST(ri.NCH_BENE_IP_DDCTBL_AMT AS DECIMAL(12,2)),
            TRY_CAST(ri.CLM_UTLZTN_DAY_CNT     AS SMALLINT),
            NULLIF(ri.ICD9_DGNS_CD_1, '')
        FROM raw_inpatient ri
        LEFT JOIN dim_beneficiary db
               ON db.desynpuf_id = ri.DESYNPUF_ID
              AND db.claim_year  = {yr}
        LEFT JOIN dim_provider dp
               ON dp.provider_id = ri.PRVDR_NUM
        WHERE NOT EXISTS (
            SELECT 1 FROM fact_inpatient fi WHERE fi.clm_id = ri.CLM_ID
        )
    """)


def _populate_fact_outpatient(conn: duckdb.DuckDBPyConnection) -> None:
    """Load fact_outpatient from raw_outpatient, joined to dim_beneficiary + dim_provider."""
    yr = _year_from_col("ro.CLM_FROM_DT")
    conn.execute(f"""
        INSERT INTO fact_outpatient (
            claim_key, desynpuf_id, bene_key, provider_key,
            service_date_key, claim_year, clm_id,
            clm_pmt_amt, bene_ptb_ddctbl_amt, primary_dx
        )
        SELECT
            ROW_NUMBER() OVER ()
                + COALESCE((SELECT MAX(claim_key) FROM fact_outpatient), 0),
            ro.DESYNPUF_ID,
            db.bene_key,
            dp.provider_key,
            {_date_key_expr('ro.CLM_FROM_DT')},
            {yr},
            ro.CLM_ID,
            TRY_CAST(ro.CLM_PMT_AMT             AS DECIMAL(12,2)),
            TRY_CAST(ro.NCH_BENE_PTB_DDCTBL_AMT AS DECIMAL(12,2)),
            NULLIF(ro.ICD9_DGNS_CD_1, '')
        FROM raw_outpatient ro
        LEFT JOIN dim_beneficiary db
               ON db.desynpuf_id = ro.DESYNPUF_ID
              AND db.claim_year  = {yr}
        LEFT JOIN dim_provider dp
               ON dp.provider_id = ro.PRVDR_NUM
        WHERE NOT EXISTS (
            SELECT 1 FROM fact_outpatient fo WHERE fo.clm_id = ro.CLM_ID
        )
    """)


def _populate_fact_carrier(conn: duckdb.DuckDBPyConnection) -> None:
    """Load fact_carrier from raw_carrier; sum LINE_NCH_PMT_AMT_1..13 per claim."""
    yr = _year_from_col("rc.CLM_FROM_DT")
    conn.execute(f"""
        INSERT INTO fact_carrier (
            claim_key, desynpuf_id, bene_key,
            service_date_key, claim_year, clm_id, total_pmt_amt, primary_dx
        )
        SELECT
            ROW_NUMBER() OVER ()
                + COALESCE((SELECT MAX(claim_key) FROM fact_carrier), 0),
            rc.DESYNPUF_ID,
            db.bene_key,
            {_date_key_expr('rc.CLM_FROM_DT')},
            {yr},
            rc.CLM_ID,
            (
                COALESCE(TRY_CAST(rc.LINE_NCH_PMT_AMT_1  AS DECIMAL(12,2)), 0) +
                COALESCE(TRY_CAST(rc.LINE_NCH_PMT_AMT_2  AS DECIMAL(12,2)), 0) +
                COALESCE(TRY_CAST(rc.LINE_NCH_PMT_AMT_3  AS DECIMAL(12,2)), 0) +
                COALESCE(TRY_CAST(rc.LINE_NCH_PMT_AMT_4  AS DECIMAL(12,2)), 0) +
                COALESCE(TRY_CAST(rc.LINE_NCH_PMT_AMT_5  AS DECIMAL(12,2)), 0) +
                COALESCE(TRY_CAST(rc.LINE_NCH_PMT_AMT_6  AS DECIMAL(12,2)), 0) +
                COALESCE(TRY_CAST(rc.LINE_NCH_PMT_AMT_7  AS DECIMAL(12,2)), 0) +
                COALESCE(TRY_CAST(rc.LINE_NCH_PMT_AMT_8  AS DECIMAL(12,2)), 0) +
                COALESCE(TRY_CAST(rc.LINE_NCH_PMT_AMT_9  AS DECIMAL(12,2)), 0) +
                COALESCE(TRY_CAST(rc.LINE_NCH_PMT_AMT_10 AS DECIMAL(12,2)), 0) +
                COALESCE(TRY_CAST(rc.LINE_NCH_PMT_AMT_11 AS DECIMAL(12,2)), 0) +
                COALESCE(TRY_CAST(rc.LINE_NCH_PMT_AMT_12 AS DECIMAL(12,2)), 0) +
                COALESCE(TRY_CAST(rc.LINE_NCH_PMT_AMT_13 AS DECIMAL(12,2)), 0)
            ),
            NULLIF(rc.ICD9_DGNS_CD_1, '')
        FROM raw_carrier rc
        LEFT JOIN dim_beneficiary db
               ON db.desynpuf_id = rc.DESYNPUF_ID
              AND db.claim_year  = {yr}
        WHERE NOT EXISTS (
            SELECT 1 FROM fact_carrier fc WHERE fc.clm_id = rc.CLM_ID
        )
    """)


def _populate_fact_pde(conn: duckdb.DuckDBPyConnection) -> None:
    """Load fact_pde from raw_pde, joined to dim_beneficiary via SRVC_DT year."""
    yr = _year_from_col("rp.SRVC_DT")
    conn.execute(f"""
        INSERT INTO fact_pde (
            pde_key, desynpuf_id, bene_key,
            service_date_key, claim_year, pde_id, prod_srvc_id,
            qty_dispensed, days_supply, patient_pay_amt, total_rx_cost
        )
        SELECT
            ROW_NUMBER() OVER ()
                + COALESCE((SELECT MAX(pde_key) FROM fact_pde), 0),
            rp.DESYNPUF_ID,
            db.bene_key,
            {_date_key_expr('rp.SRVC_DT')},
            {yr},
            rp.PDE_ID,
            NULLIF(rp.PROD_SRVC_ID, ''),
            TRY_CAST(rp.QTY_DSPNSD_NUM AS DECIMAL(10,2)),
            TRY_CAST(rp.DAYS_SUPLY_NUM AS SMALLINT),
            TRY_CAST(rp.PTNT_PAY_AMT  AS DECIMAL(12,2)),
            TRY_CAST(rp.TOT_RX_CST_AMT AS DECIMAL(12,2))
        FROM raw_pde rp
        LEFT JOIN dim_beneficiary db
               ON db.desynpuf_id = rp.DESYNPUF_ID
              AND db.claim_year  = {yr}
        WHERE NOT EXISTS (
            SELECT 1 FROM fact_pde fp WHERE fp.pde_id = rp.PDE_ID
        )
    """)


def build_star_schema(conn: duckdb.DuckDBPyConnection, settings: Settings) -> None:
    """Transform raw CMS tables into a clean star schema.

    Builds: dim_date, dim_beneficiary (SCD-lite), dim_provider, dim_diagnosis,
    fact_inpatient, fact_outpatient, fact_carrier, fact_pde,
    and the unified fact_claim_line view.

    Idempotent — safe to run multiple times; uses NOT EXISTS guards throughout.
    """
    logger.info("building star schema")
    _run_ddl(conn)
    _populate_dim_date(conn)
    _populate_dim_beneficiary(conn)
    _populate_dim_provider(conn)
    _populate_dim_diagnosis(conn)
    _populate_fact_inpatient(conn)
    _populate_fact_outpatient(conn)
    _populate_fact_carrier(conn)
    _populate_fact_pde(conn)
    logger.info("star schema build complete")
