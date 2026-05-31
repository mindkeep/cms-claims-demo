-- Business question: How are encounter costs distributed, and which patients
--                    are in the high-cost top quartile?
-- SQL technique:     PERCENTILE_CONT for distribution stats; NTILE(4) window
--                    for quartile assignment; CTE to separate ranking from aggregation
-- Scaling note:      At V2, pre-aggregate into a cost_summary materialised view
--                    refreshed nightly; the percentile computation is expensive at scale.

WITH ranked AS (
    SELECT
        fe.patient_key,
        fe.total_claim_cost,
        EXTRACT(YEAR FROM dd.full_date)::INTEGER AS encounter_year,
        NTILE(4) OVER (
            PARTITION BY EXTRACT(YEAR FROM dd.full_date)
            ORDER BY fe.total_claim_cost
        ) AS cost_quartile
    FROM fact_encounter fe
    JOIN dim_date dd ON dd.date_key = fe.start_date_key
    WHERE fe.total_claim_cost IS NOT NULL
)
SELECT
    encounter_year,
    COUNT(DISTINCT patient_key)                                     AS patient_count,
    ROUND(AVG(total_claim_cost), 2)                                 AS avg_cost,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (
          ORDER BY total_claim_cost), 2)                            AS p50_cost,
    ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (
          ORDER BY total_claim_cost), 2)                            AS p90_cost,
    ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP (
          ORDER BY total_claim_cost), 2)                            AS p99_cost,
    ROUND(MAX(total_claim_cost), 2)                                 AS max_cost,
    COUNT(*) FILTER (WHERE cost_quartile = 4)                       AS top_quartile_count
FROM ranked
GROUP BY encounter_year
ORDER BY encounter_year
