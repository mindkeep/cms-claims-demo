"""Synthea raw tables → star schema transforms.

Populates dim_date, dim_patient, dim_provider, dim_condition_code,
fact_encounter, fact_condition, fact_medication. All functions are idempotent.

V2 swap point: at V2, each fact table will be hash-partitioned by
(year, patient_key % N) so intra-shard joins never cross node boundaries.
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from cms_platform.common.config import Settings

logger = logging.getLogger(__name__)

_DDL_PATH = Path(__file__).parent.parent.parent.parent / "sql" / "schema" / "ddl.sql"


def _run_ddl(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(_DDL_PATH.read_text())


def _date_key(col: str) -> str:
    """INTEGER date key from a DATE column."""
    return f"CAST(strftime({col}, '%Y%m%d') AS INTEGER)"


def _to_date(col: str) -> str:
    """DATE from an ISO-8601 string column; handles both date and datetime forms."""
    return f"TRY_CAST(substr({col}, 1, 10) AS DATE)"


def _populate_dim_date(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("""
        INSERT INTO dim_date (date_key, full_date, year, month, day, quarter, day_of_week)
        SELECT
            CAST(strftime(d::DATE, '%Y%m%d') AS INTEGER),
            d::DATE,
            EXTRACT(YEAR    FROM d)::SMALLINT,
            EXTRACT(MONTH   FROM d)::SMALLINT,
            EXTRACT(DAY     FROM d)::SMALLINT,
            EXTRACT(QUARTER FROM d)::SMALLINT,
            EXTRACT(DOW     FROM d)::SMALLINT
        FROM generate_series(DATE '2000-01-01', DATE '2030-12-31', INTERVAL '1 day') AS t(d)
        WHERE NOT EXISTS (
            SELECT 1 FROM dim_date
            WHERE date_key = CAST(strftime(d::DATE, '%Y%m%d') AS INTEGER)
        )
    """)


def _populate_dim_patient(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(f"""
        INSERT INTO dim_patient (
            patient_key, patient_id, birthdate, deathdate,
            gender, race, ethnicity, city, state, zip,
            healthcare_expenses, healthcare_coverage, income
        )
        SELECT
            ROW_NUMBER() OVER ()
                + COALESCE((SELECT MAX(patient_key) FROM dim_patient), 0),
            rp."ID",
            {_to_date('"BIRTHDATE"')},
            {_to_date('"DEATHDATE"')},
            rp."GENDER", rp."RACE", rp."ETHNICITY",
            rp."CITY", rp."STATE", rp."ZIP",
            TRY_CAST(rp."HEALTHCARE_EXPENSES" AS DECIMAL(12,2)),
            TRY_CAST(rp."HEALTHCARE_COVERAGE" AS DECIMAL(12,2)),
            TRY_CAST(rp."INCOME" AS INTEGER)
        FROM raw_patients rp
        WHERE NOT EXISTS (
            SELECT 1 FROM dim_patient dp WHERE dp.patient_id = rp."ID"
        )
    """)


def _populate_dim_provider(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("""
        INSERT INTO dim_provider (provider_key, provider_id, name, speciality, city, state)
        SELECT
            ROW_NUMBER() OVER ()
                + COALESCE((SELECT MAX(provider_key) FROM dim_provider), 0),
            rp."Id", rp."NAME", rp."SPECIALITY", rp."CITY", rp."STATE"
        FROM raw_providers rp
        WHERE NOT EXISTS (
            SELECT 1 FROM dim_provider dp WHERE dp.provider_id = rp."Id"
        )
    """)


def _populate_dim_condition_code(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("""
        INSERT INTO dim_condition_code (code_key, snomed_code, description)
        SELECT
            ROW_NUMBER() OVER ()
                + COALESCE((SELECT MAX(code_key) FROM dim_condition_code), 0),
            rc."CODE",
            rc."DESCRIPTION"
        FROM (
            SELECT DISTINCT "CODE", "DESCRIPTION" FROM raw_conditions
            WHERE NULLIF("CODE", '') IS NOT NULL
        ) rc
        WHERE NOT EXISTS (
            SELECT 1 FROM dim_condition_code d WHERE d.snomed_code = rc."CODE"
        )
    """)


def _populate_fact_encounter(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(f"""
        INSERT INTO fact_encounter (
            encounter_key, patient_key, provider_key,
            start_date_key, stop_date_key,
            encounter_id, encounter_class, description,
            base_cost, total_claim_cost, payer_coverage,
            reason_code, reason_description
        )
        SELECT
            ROW_NUMBER() OVER ()
                + COALESCE((SELECT MAX(encounter_key) FROM fact_encounter), 0),
            dp.patient_key,
            prov.provider_key,
            {_date_key(_to_date('re."START"'))},
            {_date_key(_to_date('re."STOP"'))},
            re."Id",
            re."ENCOUNTERCLASS",
            re."DESCRIPTION",
            TRY_CAST(re."BASE_ENCOUNTER_COST" AS DECIMAL(10,2)),
            TRY_CAST(re."TOTAL_CLAIM_COST"    AS DECIMAL(10,2)),
            TRY_CAST(re."PAYER_COVERAGE"      AS DECIMAL(10,2)),
            NULLIF(re."REASONCODE", ''),
            NULLIF(re."REASONDESCRIPTION", '')
        FROM raw_encounters re
        LEFT JOIN dim_patient  dp   ON dp.patient_id   = re."PATIENT"
        LEFT JOIN dim_provider prov ON prov.provider_id = re."PROVIDER"
        WHERE NOT EXISTS (
            SELECT 1 FROM fact_encounter fe WHERE fe.encounter_id = re."Id"
        )
    """)


def _populate_fact_condition(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(f"""
        INSERT INTO fact_condition (
            condition_key, patient_key, encounter_key,
            start_date_key, stop_date_key,
            snomed_code, description
        )
        SELECT
            ROW_NUMBER() OVER ()
                + COALESCE((SELECT MAX(condition_key) FROM fact_condition), 0),
            dp.patient_key,
            fe.encounter_key,
            {_date_key(_to_date('rc."START"'))},
            CASE WHEN NULLIF(rc."STOP", '') IS NOT NULL
                 THEN {_date_key(_to_date('rc."STOP"'))}
                 ELSE NULL END,
            rc."CODE",
            rc."DESCRIPTION"
        FROM raw_conditions rc
        LEFT JOIN dim_patient  dp ON dp.patient_id   = rc."PATIENT"
        LEFT JOIN fact_encounter fe ON fe.encounter_id = rc."ENCOUNTER"
        WHERE NOT EXISTS (
            SELECT 1 FROM fact_condition fc
            WHERE fc.patient_key = dp.patient_key
              AND fc.snomed_code  = rc."CODE"
              AND fc.start_date_key = {_date_key(_to_date('rc."START"'))}
        )
    """)


def _populate_fact_medication(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(f"""
        INSERT INTO fact_medication (
            medication_key, patient_key, encounter_key,
            start_date_key, stop_date_key,
            rxnorm_code, description,
            base_cost, total_cost, dispenses, payer_coverage
        )
        SELECT
            ROW_NUMBER() OVER ()
                + COALESCE((SELECT MAX(medication_key) FROM fact_medication), 0),
            dp.patient_key,
            fe.encounter_key,
            {_date_key(_to_date('rm."START"'))},
            CASE WHEN NULLIF(rm."STOP", '') IS NOT NULL
                 THEN {_date_key(_to_date('rm."STOP"'))}
                 ELSE NULL END,
            NULLIF(rm."CODE", ''),
            rm."DESCRIPTION",
            TRY_CAST(rm."BASE_COST"      AS DECIMAL(10,2)),
            TRY_CAST(rm."TOTALCOST"      AS DECIMAL(10,2)),
            TRY_CAST(rm."DISPENSES"      AS INTEGER),
            TRY_CAST(rm."PAYER_COVERAGE" AS DECIMAL(10,2))
        FROM raw_medications rm
        LEFT JOIN dim_patient  dp ON dp.patient_id   = rm."PATIENT"
        LEFT JOIN fact_encounter fe ON fe.encounter_id = rm."ENCOUNTER"
        WHERE NOT EXISTS (
            SELECT 1 FROM fact_medication fm
            WHERE fm.patient_key = dp.patient_key
              AND fm.rxnorm_code  = NULLIF(rm."CODE", '')
              AND fm.start_date_key = {_date_key(_to_date('rm."START"'))}
        )
    """)


def build_star_schema(conn: duckdb.DuckDBPyConnection, settings: Settings) -> None:
    """Transform Synthea raw tables into a clean star schema. Idempotent."""
    logger.info("building star schema")
    _run_ddl(conn)
    _populate_dim_date(conn)
    _populate_dim_patient(conn)
    _populate_dim_provider(conn)
    _populate_dim_condition_code(conn)
    _populate_fact_encounter(conn)
    _populate_fact_condition(conn)
    _populate_fact_medication(conn)
    logger.info("star schema build complete")
