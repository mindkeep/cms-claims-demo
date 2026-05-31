-- Business question: Which diabetic patients have gone >= 12 months without
--                    any encounter (a proxy for a care gap)?
-- SQL technique:     LEFT JOIN anti-join; CURRENT_DATE date arithmetic
-- Scaling note:      At V2, run this as a scheduled job and write results to
--                    a care_gaps table so the API can serve them without a
--                    full-scan query at request time.
--
-- SNOMED-CT: 44054006 = Type 2 diabetes mellitus; 73211009 = Diabetes mellitus

WITH diabetic_patients AS (
    SELECT DISTINCT patient_key
    FROM fact_condition
    WHERE snomed_code IN ('44054006', '73211009')
      AND stop_date_key IS NULL          -- condition still active
),
last_encounter AS (
    SELECT
        fe.patient_key,
        MAX(dd.full_date) AS last_encounter_date
    FROM fact_encounter fe
    JOIN dim_date dd ON dd.date_key = fe.start_date_key
    GROUP BY fe.patient_key
)
SELECT
    COUNT(*)                                                        AS diabetic_patients,
    COUNT(*) FILTER (
        WHERE le.last_encounter_date IS NULL
           OR CURRENT_DATE - le.last_encounter_date > 365
    )                                                               AS patients_with_care_gap,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE le.last_encounter_date IS NULL
               OR CURRENT_DATE - le.last_encounter_date > 365
        ) / NULLIF(COUNT(*), 0),
    2)                                                              AS care_gap_rate_pct
FROM diabetic_patients dp
LEFT JOIN last_encounter le ON le.patient_key = dp.patient_key
