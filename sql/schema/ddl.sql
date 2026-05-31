-- Business question: defines the dimensional model for all analytical queries
-- SQL technique:     surrogate PKs, SCD-lite beneficiary, date-key calendar dim
-- Scaling note:      claim_year + bene_key hash are V2 shard keys for shard-local joins

CREATE TABLE IF NOT EXISTS dim_date (
    date_key    INTEGER  PRIMARY KEY,
    full_date   DATE     NOT NULL,
    year        SMALLINT NOT NULL,
    month       SMALLINT NOT NULL,
    day         SMALLINT NOT NULL,
    quarter     SMALLINT NOT NULL,
    day_of_week SMALLINT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_beneficiary (
    bene_key             INTEGER  PRIMARY KEY,
    desynpuf_id          VARCHAR  NOT NULL,
    claim_year           SMALLINT NOT NULL,
    birth_dt             DATE,
    death_dt             DATE,
    sex_cd               SMALLINT,
    race_cd              SMALLINT,
    esrd_ind             BOOLEAN,
    state_code           SMALLINT,
    county_cd            SMALLINT,
    hi_coverage_months   SMALLINT,
    smi_coverage_months  SMALLINT,
    hmo_coverage_months  SMALLINT,
    plan_coverage_months SMALLINT,
    sp_alzheimer         BOOLEAN,
    sp_chf               BOOLEAN,
    sp_chrnkidn          BOOLEAN,
    sp_cncr              BOOLEAN,
    sp_copd              BOOLEAN,
    sp_depressn          BOOLEAN,
    sp_diabetes          BOOLEAN,
    sp_ischmcht          BOOLEAN,
    sp_osteoprs          BOOLEAN,
    sp_ra_oa             BOOLEAN,
    sp_strketia          BOOLEAN,
    medreimb_ip          DECIMAL(12,2),
    medreimb_op          DECIMAL(12,2),
    medreimb_car         DECIMAL(12,2)
);

CREATE TABLE IF NOT EXISTS dim_provider (
    provider_key INTEGER PRIMARY KEY,
    provider_id  VARCHAR NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dim_diagnosis (
    dx_key    INTEGER PRIMARY KEY,
    icd9_code VARCHAR NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS fact_inpatient (
    claim_key           INTEGER      PRIMARY KEY,
    desynpuf_id         VARCHAR      NOT NULL,
    bene_key            INTEGER,
    provider_key        INTEGER,
    admit_date_key      INTEGER,
    discharge_date_key  INTEGER,
    claim_year          SMALLINT,
    clm_id              VARCHAR,
    drg_cd              VARCHAR,
    clm_pmt_amt         DECIMAL(12,2),
    bene_ip_ddctbl_amt  DECIMAL(12,2),
    utilization_day_cnt SMALLINT,
    primary_dx          VARCHAR
);

CREATE TABLE IF NOT EXISTS fact_outpatient (
    claim_key           INTEGER      PRIMARY KEY,
    desynpuf_id         VARCHAR      NOT NULL,
    bene_key            INTEGER,
    provider_key        INTEGER,
    service_date_key    INTEGER,
    claim_year          SMALLINT,
    clm_id              VARCHAR,
    clm_pmt_amt         DECIMAL(12,2),
    bene_ptb_ddctbl_amt DECIMAL(12,2),
    primary_dx          VARCHAR
);

CREATE TABLE IF NOT EXISTS fact_carrier (
    claim_key        INTEGER      PRIMARY KEY,
    desynpuf_id      VARCHAR      NOT NULL,
    bene_key         INTEGER,
    service_date_key INTEGER,
    claim_year       SMALLINT,
    clm_id           VARCHAR,
    total_pmt_amt    DECIMAL(12,2),
    primary_dx       VARCHAR
);

CREATE TABLE IF NOT EXISTS fact_pde (
    pde_key          INTEGER      PRIMARY KEY,
    desynpuf_id      VARCHAR      NOT NULL,
    bene_key         INTEGER,
    service_date_key INTEGER,
    claim_year       SMALLINT,
    pde_id           VARCHAR,
    prod_srvc_id     VARCHAR,
    qty_dispensed    DECIMAL(10,2),
    days_supply      SMALLINT,
    patient_pay_amt  DECIMAL(12,2),
    total_rx_cost    DECIMAL(12,2)
);

CREATE OR REPLACE VIEW fact_claim_line AS
    SELECT 'inpatient'  AS claim_type, desynpuf_id, claim_year, clm_id        AS claim_id,
           clm_pmt_amt  AS pmt_amt, admit_date_key AS date_key
    FROM   fact_inpatient
    UNION ALL
    SELECT 'outpatient', desynpuf_id, claim_year, clm_id, clm_pmt_amt, service_date_key
    FROM   fact_outpatient
    UNION ALL
    SELECT 'carrier',    desynpuf_id, claim_year, clm_id, total_pmt_amt, service_date_key
    FROM   fact_carrier
    UNION ALL
    SELECT 'pde',        desynpuf_id, claim_year, pde_id, total_rx_cost, service_date_key
    FROM   fact_pde;
