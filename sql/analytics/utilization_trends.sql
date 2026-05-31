-- Business question: How did claim volume and cost evolve year-over-year 2008–2010?
-- SQL technique:     Window functions: LAG over year partitions for YoY delta and growth rate
-- Scaling note:      At V2, aggregate by shard first; YoY window runs on the merged aggregation only

WITH yearly AS (
    SELECT
        claim_year,
        claim_type,
        COUNT(*)        AS claim_count,
        ROUND(SUM(pmt_amt), 2) AS total_cost
    FROM fact_claim_line
    WHERE claim_year IS NOT NULL
    GROUP BY claim_year, claim_type
),
with_lag AS (
    SELECT
        claim_year,
        claim_type,
        claim_count,
        total_cost,
        LAG(claim_count) OVER (PARTITION BY claim_type ORDER BY claim_year) AS prev_count,
        LAG(total_cost)  OVER (PARTITION BY claim_type ORDER BY claim_year) AS prev_cost
    FROM yearly
)
SELECT
    claim_year,
    claim_type,
    claim_count,
    total_cost,
    claim_count - prev_count                                           AS count_delta,
    ROUND(100.0 * (claim_count - prev_count) / NULLIF(prev_count, 0), 2) AS count_growth_pct,
    ROUND(total_cost - prev_cost, 2)                                  AS cost_delta,
    ROUND(100.0 * (total_cost - prev_cost) / NULLIF(prev_cost, 0), 2) AS cost_growth_pct
FROM with_lag
ORDER BY claim_type, claim_year
