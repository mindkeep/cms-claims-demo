-- Business question: How does per-beneficiary total cost distribute across the population? Who are the high-cost outliers?
-- SQL technique:     Window functions: PERCENTILE_CONT, NTILE, RANK; aggregation across claim types
-- Scaling note:      At V2, aggregate by shard then merge percentiles using t-digest or approx_quantile

WITH bene_total_cost AS (
    SELECT
        desynpuf_id,
        claim_year,
        SUM(pmt_amt) AS total_cost
    FROM fact_claim_line
    GROUP BY desynpuf_id, claim_year
),
ranked AS (
    SELECT
        desynpuf_id,
        claim_year,
        total_cost,
        NTILE(4) OVER (PARTITION BY claim_year ORDER BY total_cost) AS cost_quartile,
        RANK()   OVER (PARTITION BY claim_year ORDER BY total_cost DESC) AS cost_rank
    FROM bene_total_cost
)
SELECT
    claim_year,
    COUNT(*)                                             AS beneficiary_count,
    ROUND(AVG(total_cost), 2)                            AS avg_cost,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY total_cost), 2) AS p50_cost,
    ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY total_cost), 2) AS p90_cost,
    ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY total_cost), 2) AS p99_cost,
    ROUND(MAX(total_cost), 2)                            AS max_cost,
    COUNT(*) FILTER (WHERE cost_quartile = 4)            AS top_quartile_count
FROM ranked
GROUP BY claim_year
ORDER BY claim_year
