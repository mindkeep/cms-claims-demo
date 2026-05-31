-- Business question: Unified star schema for Synthea synthetic patient data
-- SQL technique:     Dimensional modelling — surrogate keys, date dimension, NOT EXISTS guards
-- Scaling note:      At V2, partition fact_encounter by (year, patient_key % N);
--                    replace DuckDB with Postgres and add a columnar extension for analytics.

-- ── Calendar dimension ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_date (
    date_key    INTEGER PRIMARY KEY,   -- YYYYMMDD integer
    full_date   DATE    NOT NULL,
    year        SMALLINT NOT NULL,
    month       SMALLINT NOT NULL,
    day         SMALLINT NOT NULL,
    quarter     SMALLINT NOT NULL,
    day_of_week SMALLINT NOT NULL      -- 0=Sunday … 6=Saturday
);

-- ── Patient dimension ────────────────────────────────────────────────────────
-- One row per Synthea patient. Patient IDs are UUIDs; treat as PHI.
CREATE TABLE IF NOT EXISTS dim_patient (
    patient_key          BIGINT  PRIMARY KEY,
    patient_id           VARCHAR NOT NULL UNIQUE,   -- Synthea UUID — PHI
    birthdate            DATE,
    deathdate            DATE,
    gender               VARCHAR,
    race                 VARCHAR,
    ethnicity            VARCHAR,
    city                 VARCHAR,
    state                VARCHAR,
    zip                  VARCHAR,
    healthcare_expenses  DECIMAL(12,2),
    healthcare_coverage  DECIMAL(12,2),
    income               INTEGER
);

-- ── Provider dimension ───────────────────────────────────────────────────────
-- Healthcare providers (individual clinicians) from providers.csv.
CREATE TABLE IF NOT EXISTS dim_provider (
    provider_key  BIGINT  PRIMARY KEY,
    provider_id   VARCHAR NOT NULL UNIQUE,   -- Synthea UUID
    name          VARCHAR,
    speciality    VARCHAR,
    city          VARCHAR,
    state         VARCHAR
);

-- ── Condition code dimension (SNOMED-CT dictionary) ──────────────────────────
-- One row per distinct SNOMED-CT code seen in the data.
-- SNOMED-CT is the international clinical terminology standard; it replaces
-- ICD-9 for clinical use. ICD-10 is still used for billing — see ARCHITECTURE.md.
CREATE TABLE IF NOT EXISTS dim_condition_code (
    code_key     BIGINT  PRIMARY KEY,
    snomed_code  VARCHAR NOT NULL UNIQUE,
    description  VARCHAR
);

-- ── Encounter fact ───────────────────────────────────────────────────────────
-- One row per clinical encounter (visit, admission, etc.).
-- encounter_class values from Synthea: inpatient, ambulatory, emergency,
--   urgentcare, wellness, outpatient.
CREATE TABLE IF NOT EXISTS fact_encounter (
    encounter_key     BIGINT  PRIMARY KEY,
    patient_key       BIGINT  REFERENCES dim_patient(patient_key),
    provider_key      BIGINT  REFERENCES dim_provider(provider_key),
    start_date_key    INTEGER REFERENCES dim_date(date_key),
    stop_date_key     INTEGER REFERENCES dim_date(date_key),
    encounter_id      VARCHAR NOT NULL UNIQUE,
    encounter_class   VARCHAR,
    description       VARCHAR,
    base_cost         DECIMAL(10,2),
    total_claim_cost  DECIMAL(10,2),
    payer_coverage    DECIMAL(10,2),
    reason_code       VARCHAR,
    reason_description VARCHAR
);

-- ── Condition fact ───────────────────────────────────────────────────────────
-- One row per condition episode (start → stop or still active if stop IS NULL).
CREATE TABLE IF NOT EXISTS fact_condition (
    condition_key   BIGINT  PRIMARY KEY,
    patient_key     BIGINT  REFERENCES dim_patient(patient_key),
    encounter_key   BIGINT  REFERENCES fact_encounter(encounter_key),
    start_date_key  INTEGER REFERENCES dim_date(date_key),
    stop_date_key   INTEGER,           -- NULL = still active
    snomed_code     VARCHAR,
    description     VARCHAR
);

-- ── Medication fact ──────────────────────────────────────────────────────────
-- One row per medication dispense event. RxNorm codes identify drugs.
-- TODO(future-coding): add a dim_drug table keyed on rxnorm_code for richer lookups.
CREATE TABLE IF NOT EXISTS fact_medication (
    medication_key  BIGINT  PRIMARY KEY,
    patient_key     BIGINT  REFERENCES dim_patient(patient_key),
    encounter_key   BIGINT  REFERENCES fact_encounter(encounter_key),
    start_date_key  INTEGER REFERENCES dim_date(date_key),
    stop_date_key   INTEGER,           -- NULL = ongoing
    rxnorm_code     VARCHAR,
    description     VARCHAR,
    base_cost       DECIMAL(10,2),
    total_cost      DECIMAL(10,2),
    dispenses       INTEGER,
    payer_coverage  DECIMAL(10,2)
);
