-- Business question: How have encounter volumes and costs changed year-over-year,
--                    broken down by encounter class?
-- SQL technique:     LAG window for year-over-year delta; PARTITION BY encounter_class
--                    so each class has its own prior-year reference row
-- Scaling note:      At V2, pre-aggregate into utilization_summary; the base
--                    aggregation over 500M rows is the expensive part, not the window.

WITH yearly AS (
    SELECT
        EXTRACT(YEAR FROM dd.full_date)::INTEGER AS encounter_year,
        fe.encounter_class,
        COUNT(*)                                 AS encounter_count,
        ROUND(SUM(fe.total_claim_cost), 2)       AS total_cost
    FROM fact_encounter fe
    JOIN dim_date dd ON dd.date_key = fe.start_date_key
    GROUP BY EXTRACT(YEAR FROM dd.full_date), fe.encounter_class
)
SELECT
    encounter_year,
    encounter_class,
    encounter_count,
    total_cost,
    encounter_count - LAG(encounter_count) OVER w   AS count_delta,
    ROUND(
        100.0 * (encounter_count - LAG(encounter_count) OVER w)
        / NULLIF(LAG(encounter_count) OVER w, 0),
    2)                                               AS count_growth_pct,
    total_cost - LAG(total_cost) OVER w              AS cost_delta,
    ROUND(
        100.0 * (total_cost - LAG(total_cost) OVER w)
        / NULLIF(LAG(total_cost) OVER w, 0),
    2)                                               AS cost_growth_pct
FROM yearly
WINDOW w AS (PARTITION BY encounter_class ORDER BY encounter_year)
ORDER BY encounter_year, encounter_class
