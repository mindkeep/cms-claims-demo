# Data Dictionary — CMS DE-SynPUF Raw Layer

All columns in the raw layer are stored as **VARCHAR**. No type inference is
performed at ingest time. Downstream schema transforms (`schema/transforms.py`)
cast to typed columns in the star-schema layer.

> **Note:** synthetic data caps real predictive signal. These figures demonstrate
> the pipeline, not clinical validity.

## Source
CMS DE-SynPUF (Data Entrepreneurs' Synthetic Public Use Files), 2008–2010.
[Data Users Guide (PDF)](https://www.cms.gov/Research-Statistics-Data-and-Systems/Downloadable-Public-Use-Files/SynPUFs/Downloads/SynPUF_DUG.pdf)

---

## 1. `raw_beneficiary`

**Source files (3 per subsample):** `DE1_0_{year}_Beneficiary_Summary_File_Sample_{N}.csv`
Years: 2008, 2009, 2010.

| Column | Raw Type | Description |
|--------|----------|-------------|
| DESYNPUF_ID | VARCHAR | Beneficiary code (synthetic, treated as PHI) |
| BENE_BIRTH_DT | VARCHAR | Date of birth (YYYYMMDD) |
| BENE_DEATH_DT | VARCHAR | Date of death (YYYYMMDD); blank if alive |
| BENE_SEX_IDENT_CD | VARCHAR | Sex: 1=Male, 2=Female |
| BENE_RACE_CD | VARCHAR | Race: 1=White, 2=Black, 3=Other, 4=Asian, 5=Hispanic, 6=North American Native |
| BENE_ESRD_IND | VARCHAR | End-Stage Renal Disease indicator (Y/N) |
| SP_STATE_CODE | VARCHAR | State FIPS code of beneficiary residence |
| BENE_COUNTY_CD | VARCHAR | County code of beneficiary residence |
| BENE_HI_CVRAGE_TOT_MONS | VARCHAR | Total months of Part A (Hospital Insurance) coverage |
| BENE_SMI_CVRAGE_TOT_MONS | VARCHAR | Total months of Part B (Supplementary Medical Insurance) coverage |
| BENE_HMO_CVRAGE_TOT_MONS | VARCHAR | Total months of HMO coverage |
| PLAN_CVRG_MOS_NUM | VARCHAR | Total months of Part D plan coverage |
| SP_ALZHDMTA | VARCHAR | Chronic condition: Alzheimer's or related disorders (1=Yes, 2=No) |
| SP_CHF | VARCHAR | Chronic condition: Congestive Heart Failure |
| SP_CHRNKIDN | VARCHAR | Chronic condition: Chronic Kidney Disease |
| SP_CNCR | VARCHAR | Chronic condition: Cancer |
| SP_COPD | VARCHAR | Chronic condition: Chronic Obstructive Pulmonary Disease |
| SP_DEPRESSN | VARCHAR | Chronic condition: Depression |
| SP_DIABETES | VARCHAR | Chronic condition: Diabetes |
| SP_ISCHMCHT | VARCHAR | Chronic condition: Ischemic Heart Disease |
| SP_OSTEOPRS | VARCHAR | Chronic condition: Osteoporosis |
| SP_RA_OA | VARCHAR | Chronic condition: Rheumatoid Arthritis / Osteoarthritis |
| SP_STRKETIA | VARCHAR | Chronic condition: Stroke / Transient Ischemic Attack |
| MEDREIMB_IP | VARCHAR | Medicare reimbursement amount — inpatient (annual) |
| BENRES_IP | VARCHAR | Beneficiary responsibility amount — inpatient |
| PPPYMT_IP | VARCHAR | Primary payer reimbursement — inpatient |
| MEDREIMB_OP | VARCHAR | Medicare reimbursement amount — outpatient (annual) |
| BENRES_OP | VARCHAR | Beneficiary responsibility amount — outpatient |
| PPPYMT_OP | VARCHAR | Primary payer reimbursement — outpatient |
| MEDREIMB_CAR | VARCHAR | Medicare reimbursement amount — carrier (annual) |
| BENRES_CAR | VARCHAR | Beneficiary responsibility amount — carrier |
| PPPYMT_CAR | VARCHAR | Primary payer reimbursement — carrier |
| _claim_year | VARCHAR | Ingest metadata: year extracted from filename (2008/2009/2010) |
| _source_file | VARCHAR | Ingest metadata: absolute path of source CSV |

---

## 2. `raw_inpatient`

**Source file (1 per subsample):** `DE1_0_2008_to_2010_Inpatient_Claims_Sample_{N}.csv`

| Column | Raw Type | Description |
|--------|----------|-------------|
| DESYNPUF_ID | VARCHAR | Beneficiary code (treated as PHI) |
| CLM_ID | VARCHAR | Claim ID |
| SEGMENT | VARCHAR | Claim line segment number |
| CLM_FROM_DT | VARCHAR | Claim start date (YYYYMMDD) |
| CLM_THRU_DT | VARCHAR | Claim end date (YYYYMMDD) |
| PRVDR_NUM | VARCHAR | Provider institution number |
| AT_PHYSN_NPI | VARCHAR | Attending physician NPI |
| OP_PHYSN_NPI | VARCHAR | Operating physician NPI |
| OT_PHYSN_NPI | VARCHAR | Other physician NPI |
| CLM_PMT_AMT | VARCHAR | Amount paid by Medicare for the claim |
| NCH_PRMRY_PYR_CLM_PD_AMT | VARCHAR | Amount paid by primary payer |
| NCH_BENE_IP_DDCTBL_AMT | VARCHAR | Inpatient deductible amount |
| NCH_BENE_PTA_COINSRNC_LBLTY_AM | VARCHAR | Beneficiary Part A coinsurance liability |
| NCH_BENE_BLOOD_DDCTBL_LBLTY_AM | VARCHAR | Beneficiary blood deductible liability |
| CLM_UTLZTN_DAY_CNT | VARCHAR | Number of utilization days |
| NCH_BENE_DSCHRG_DT | VARCHAR | Beneficiary discharge date (YYYYMMDD) |
| CLM_DRG_CD | VARCHAR | Diagnosis Related Group code |
| ICD9_DGNS_CD_1 … ICD9_DGNS_CD_10 | VARCHAR | ICD-9 diagnosis codes (up to 10) |
| ICD9_PRCDR_CD_1 … ICD9_PRCDR_CD_6 | VARCHAR | ICD-9 procedure codes (up to 6) |
| HCPCS_CD_1 … HCPCS_CD_45 | VARCHAR | HCPCS / CPT procedure codes (up to 45) |
| _source_file | VARCHAR | Ingest metadata: absolute path of source CSV |

---

## 3. `raw_outpatient`

**Source file (1 per subsample):** `DE1_0_2008_to_2010_Outpatient_Claims_Sample_{N}.csv`

| Column | Raw Type | Description |
|--------|----------|-------------|
| DESYNPUF_ID | VARCHAR | Beneficiary code (treated as PHI) |
| CLM_ID | VARCHAR | Claim ID |
| SEGMENT | VARCHAR | Claim line segment number |
| CLM_FROM_DT | VARCHAR | Claim start date (YYYYMMDD) |
| CLM_THRU_DT | VARCHAR | Claim end date (YYYYMMDD) |
| PRVDR_NUM | VARCHAR | Provider institution number |
| AT_PHYSN_NPI | VARCHAR | Attending physician NPI |
| OP_PHYSN_NPI | VARCHAR | Operating physician NPI |
| OT_PHYSN_NPI | VARCHAR | Other physician NPI |
| NCH_BENE_BLOOD_DDCTBL_LBLTY_AM | VARCHAR | Beneficiary blood deductible liability |
| CLM_PMT_AMT | VARCHAR | Amount paid by Medicare for the claim |
| NCH_PRMRY_PYR_CLM_PD_AMT | VARCHAR | Amount paid by primary payer |
| NCH_BENE_PTB_DDCTBL_AMT | VARCHAR | Beneficiary Part B deductible amount |
| NCH_BENE_PTB_COINSRNC_AMT | VARCHAR | Beneficiary Part B coinsurance amount |
| ADMTNG_ICD9_DGNS_CD | VARCHAR | Admitting ICD-9 diagnosis code |
| ICD9_DGNS_CD_1 … ICD9_DGNS_CD_10 | VARCHAR | ICD-9 diagnosis codes (up to 10) |
| ICD9_PRCDR_CD_1 … ICD9_PRCDR_CD_6 | VARCHAR | ICD-9 procedure codes (up to 6) |
| HCPCS_CD_1 … HCPCS_CD_45 | VARCHAR | HCPCS / CPT procedure codes (up to 45) |
| _source_file | VARCHAR | Ingest metadata: absolute path of source CSV |

---

## 4. `raw_carrier`

**Source files (2 per subsample):** `DE1_0_2008_to_2010_Carrier_Claims_Sample_{N}A.csv` and `…{N}B.csv`

Carrier claims cover physician/supplier services billed under Part B.
Each claim has up to 13 line items; line-level columns are suffixed `_1` through `_13`.

| Column | Raw Type | Description |
|--------|----------|-------------|
| DESYNPUF_ID | VARCHAR | Beneficiary code (treated as PHI) |
| CLM_ID | VARCHAR | Claim ID |
| CLM_FROM_DT | VARCHAR | Claim start date (YYYYMMDD) |
| CLM_THRU_DT | VARCHAR | Claim end date (YYYYMMDD) |
| ICD9_DGNS_CD_1 … ICD9_DGNS_CD_2 | VARCHAR | ICD-9 diagnosis codes (up to 2) |
| HCPCS_CD_1 … HCPCS_CD_13 | VARCHAR | HCPCS / CPT codes per line item |
| LINE_NCH_PMT_AMT_1 … _13 | VARCHAR | Line-level Medicare payment amounts |
| LINE_BENE_PTB_DDCTBL_AMT_1 … _13 | VARCHAR | Line-level Part B deductible amounts |
| LINE_BENE_PRMRY_PYR_PD_AMT_1 … _13 | VARCHAR | Line-level primary payer amounts |
| LINE_COINSRNC_AMT_1 … _13 | VARCHAR | Line-level coinsurance amounts |
| LINE_ALOWD_CHRG_AMT_1 … _13 | VARCHAR | Line-level allowed charge amounts |
| LINE_PRCSG_IND_CD_1 … _13 | VARCHAR | Line processing indicator codes |
| LINE_PLACE_OF_SRVC_CD_1 … _13 | VARCHAR | Line place-of-service codes |
| _source_file | VARCHAR | Ingest metadata: absolute path of source CSV |

---

## 5. `raw_pde`

**Source file (1 per subsample):** `DE1_0_2008_to_2010_Prescription_Drug_Events_Sample_{N}.csv`

| Column | Raw Type | Description |
|--------|----------|-------------|
| DESYNPUF_ID | VARCHAR | Beneficiary code (treated as PHI) |
| PDE_ID | VARCHAR | Prescription Drug Event ID |
| SRVC_DT | VARCHAR | Service date (YYYYMMDD) |
| PROD_SRVC_ID | VARCHAR | Product/service ID (NDC code) |
| QTY_DSPNSD_NUM | VARCHAR | Quantity dispensed |
| DAYS_SUPLY_NUM | VARCHAR | Days supply |
| PTNT_PAY_AMT | VARCHAR | Patient pay amount |
| TOT_RX_CST_AMT | VARCHAR | Total drug cost |
| _source_file | VARCHAR | Ingest metadata: absolute path of source CSV |
