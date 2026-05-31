-- Business question: Which diabetic beneficiaries had no carrier claim in a year (potential care gap)?
-- SQL technique:     LEFT JOIN anti-join pattern (NOT EXISTS alternative)
-- Scaling note:      At V2, filter dim_beneficiary by shard then LEFT JOIN within shard — no cross-shard join needed

SELECT
    db.claim_year,
    COUNT(DISTINCT db.desynpuf_id)              AS diabetic_beneficiaries,
    COUNT(DISTINCT db.desynpuf_id)
        FILTER (WHERE fc.desynpuf_id IS NULL)   AS with_care_gap,
    ROUND(
        100.0 * COUNT(DISTINCT db.desynpuf_id) FILTER (WHERE fc.desynpuf_id IS NULL)
        / NULLIF(COUNT(DISTINCT db.desynpuf_id), 0),
        2
    )                                           AS care_gap_rate_pct
FROM dim_beneficiary db
LEFT JOIN (
    SELECT DISTINCT desynpuf_id, claim_year FROM fact_carrier
) fc ON fc.desynpuf_id = db.desynpuf_id
      AND fc.claim_year  = db.claim_year
WHERE db.sp_diabetes = TRUE
GROUP BY db.claim_year
ORDER BY db.claim_year
