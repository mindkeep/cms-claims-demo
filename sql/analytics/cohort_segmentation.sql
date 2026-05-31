-- Business question: How many patients have each major chronic condition,
--                    broken down by the year of their first encounter?
-- SQL technique:     Conditional aggregation with FILTER; LEFT JOIN to derive
--                    per-patient condition flags from SNOMED-CT codes
-- Scaling note:      At V2, materialise patient_conditions as a pre-aggregated
--                    table refreshed on each ingest run.
--
-- SNOMED-CT codes used (see ARCHITECTURE.md for full reference):
--   44054006 / 73211009 = Diabetes  |  84114007 = Heart failure
--   13645005 / 195967001 = COPD/Asthma  |  59621000 = Hypertension

WITH patient_conditions AS (
    SELECT
        patient_key,
        COUNT(DISTINCT snomed_code)                                         AS condition_count,
        MAX(CASE WHEN snomed_code IN ('44054006','73211009') THEN 1 ELSE 0 END) AS has_diabetes,
        MAX(CASE WHEN snomed_code = '84114007'               THEN 1 ELSE 0 END) AS has_heart_failure,
        MAX(CASE WHEN snomed_code IN ('13645005','195967001') THEN 1 ELSE 0 END) AS has_copd_asthma,
        MAX(CASE WHEN snomed_code = '59621000'               THEN 1 ELSE 0 END) AS has_hypertension
    FROM fact_condition
    GROUP BY patient_key
),
patient_year AS (
    SELECT
        fe.patient_key,
        EXTRACT(YEAR FROM MIN(dd.full_date))::INTEGER AS first_encounter_year
    FROM fact_encounter fe
    JOIN dim_date dd ON dd.date_key = fe.start_date_key
    GROUP BY fe.patient_key
)
SELECT
    py.first_encounter_year                             AS encounter_year,
    COUNT(*)                                            AS total_patients,
    SUM(COALESCE(pc.has_diabetes,      0))              AS diabetes_cohort,
    SUM(COALESCE(pc.has_heart_failure, 0))              AS heart_failure_cohort,
    SUM(COALESCE(pc.has_copd_asthma,   0))              AS copd_asthma_cohort,
    SUM(COALESCE(pc.has_hypertension,  0))              AS hypertension_cohort,
    ROUND(AVG(COALESCE(pc.condition_count, 0)), 2)      AS avg_condition_count
FROM patient_year py
LEFT JOIN patient_conditions pc ON pc.patient_key = py.patient_key
GROUP BY py.first_encounter_year
ORDER BY py.first_encounter_year
