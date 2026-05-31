-- Business question: What % of inpatient stays result in a readmission within 30 days?
-- SQL technique:     Self-join on beneficiary ID with date range predicate using LAG window function
-- Scaling note:      At V2, partition fact_inpatient by (bene_key % N, claim_year) — self-join becomes shard-local

WITH ordered_admits AS (
    SELECT
        fi.desynpuf_id,
        fi.claim_year,
        fi.clm_id,
        dd_admit.full_date    AS admit_date,
        dd_disch.full_date    AS discharge_date,
        fi.clm_pmt_amt,
        LAG(dd_disch.full_date) OVER (PARTITION BY fi.desynpuf_id ORDER BY dd_admit.full_date) AS prev_discharge
    FROM fact_inpatient fi
    JOIN dim_date dd_admit ON dd_admit.date_key = fi.admit_date_key
    LEFT JOIN dim_date dd_disch ON dd_disch.date_key = fi.discharge_date_key
),
flagged AS (
    SELECT *,
        CASE WHEN prev_discharge IS NOT NULL
              AND admit_date <= prev_discharge + INTERVAL '30 days'
             THEN 1 ELSE 0 END AS is_readmission
    FROM ordered_admits
)
SELECT
    claim_year,
    COUNT(*)                                          AS total_admissions,
    SUM(is_readmission)                               AS readmissions,
    ROUND(100.0 * SUM(is_readmission) / COUNT(*), 2) AS readmission_rate_pct
FROM flagged
GROUP BY claim_year
ORDER BY claim_year
