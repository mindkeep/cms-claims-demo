# Entity-Relationship Diagram — CMS Claims Star Schema

Star schema centered on Medicare claim events. Fact tables reference dimension
tables via surrogate integer keys. `dim_beneficiary` is SCD-lite: one row per
beneficiary per calendar year. `fact_claim_line` is a UNION ALL view across all
four fact tables for cross-cutting analytics.

```mermaid
erDiagram
    dim_date {
        integer  date_key    PK
        date     full_date
        smallint year
        smallint month
        smallint day
        smallint quarter
        smallint day_of_week
    }

    dim_beneficiary {
        integer  bene_key              PK
        varchar  desynpuf_id
        smallint claim_year
        date     birth_dt
        date     death_dt
        smallint sex_cd
        smallint race_cd
        boolean  esrd_ind
        smallint state_code
        smallint county_cd
        smallint hi_coverage_months
        smallint smi_coverage_months
        smallint hmo_coverage_months
        smallint plan_coverage_months
        boolean  sp_alzheimer
        boolean  sp_chf
        boolean  sp_chrnkidn
        boolean  sp_cncr
        boolean  sp_copd
        boolean  sp_depressn
        boolean  sp_diabetes
        boolean  sp_ischmcht
        boolean  sp_osteoprs
        boolean  sp_ra_oa
        boolean  sp_strketia
        decimal  medreimb_ip
        decimal  medreimb_op
        decimal  medreimb_car
    }

    dim_provider {
        integer provider_key PK
        varchar provider_id
    }

    dim_diagnosis {
        integer dx_key    PK
        varchar icd9_code
    }

    fact_inpatient {
        integer  claim_key           PK
        varchar  desynpuf_id
        integer  bene_key            FK
        integer  provider_key        FK
        integer  admit_date_key      FK
        integer  discharge_date_key  FK
        smallint claim_year
        varchar  clm_id
        varchar  drg_cd
        decimal  clm_pmt_amt
        decimal  bene_ip_ddctbl_amt
        smallint utilization_day_cnt
        varchar  primary_dx
    }

    fact_outpatient {
        integer  claim_key           PK
        varchar  desynpuf_id
        integer  bene_key            FK
        integer  provider_key        FK
        integer  service_date_key    FK
        smallint claim_year
        varchar  clm_id
        decimal  clm_pmt_amt
        decimal  bene_ptb_ddctbl_amt
        varchar  primary_dx
    }

    fact_carrier {
        integer  claim_key        PK
        varchar  desynpuf_id
        integer  bene_key         FK
        integer  service_date_key FK
        smallint claim_year
        varchar  clm_id
        decimal  total_pmt_amt
        varchar  primary_dx
    }

    fact_pde {
        integer  pde_key          PK
        varchar  desynpuf_id
        integer  bene_key         FK
        integer  service_date_key FK
        smallint claim_year
        varchar  pde_id
        varchar  prod_srvc_id
        decimal  qty_dispensed
        smallint days_supply
        decimal  patient_pay_amt
        decimal  total_rx_cost
    }

    dim_beneficiary ||--o{ fact_inpatient  : "bene_key"
    dim_beneficiary ||--o{ fact_outpatient : "bene_key"
    dim_beneficiary ||--o{ fact_carrier    : "bene_key"
    dim_beneficiary ||--o{ fact_pde        : "bene_key"
    dim_provider    ||--o{ fact_inpatient  : "provider_key"
    dim_provider    ||--o{ fact_outpatient : "provider_key"
    dim_date        ||--o{ fact_inpatient  : "admit_date_key"
    dim_date        ||--o{ fact_outpatient : "service_date_key"
    dim_date        ||--o{ fact_carrier    : "service_date_key"
    dim_date        ||--o{ fact_pde        : "service_date_key"
```
