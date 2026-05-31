-- Business question: What percentage of inpatient encounters result in a
--                    readmission within 30 days?
-- SQL technique:     LAG window function over inpatient encounters ordered by
--                    admit date per patient; date arithmetic on full_date
-- Scaling note:      At V2, partition fact_encounter by patient_key % N;
--                    the LAG window becomes shard-local for most patients.

WITH inpatient AS (
    SELECT
        fe.patient_key,
        dd_start.full_date                            AS admit_date,
        dd_stop.full_date                             AS discharge_date,
        EXTRACT(YEAR FROM dd_start.full_date)::INTEGER AS encounter_year
    FROM fact_encounter fe
    JOIN dim_date dd_start ON dd_start.date_key = fe.start_date_key
    JOIN dim_date dd_stop  ON dd_stop.date_key  = fe.stop_date_key
    WHERE fe.encounter_class = 'inpatient'
),
with_prior AS (
    SELECT
        patient_key,
        admit_date,
        discharge_date,
        encounter_year,
        LAG(discharge_date) OVER (
            PARTITION BY patient_key ORDER BY admit_date
        ) AS prior_discharge
    FROM inpatient
)
SELECT
    encounter_year,
    COUNT(*)                                                AS total_admissions,
    COUNT(*) FILTER (
        WHERE prior_discharge IS NOT NULL
          AND admit_date - prior_discharge <= 30
    )                                                       AS readmissions,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE prior_discharge IS NOT NULL
              AND admit_date - prior_discharge <= 30
        ) / NULLIF(COUNT(*), 0),
    2)                                                      AS readmission_rate_pct
FROM with_prior
GROUP BY encounter_year
ORDER BY encounter_year
