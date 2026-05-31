-- Business question: How many beneficiaries fall into each chronic-condition cohort, and what are their comorbidity burdens?
-- SQL technique:     CASE/FILTER aggregation, comorbidity count via column sum
-- Scaling note:      At V2, pre-aggregate by shard then UNION — cohort counts are additive

WITH bene_comorbidity AS (
    SELECT
        desynpuf_id,
        claim_year,
        (sp_alzheimer::INT + sp_chf::INT + sp_chrnkidn::INT + sp_cncr::INT +
         sp_copd::INT + sp_depressn::INT + sp_diabetes::INT + sp_ischmcht::INT +
         sp_osteoprs::INT + sp_ra_oa::INT + sp_strketia::INT) AS comorbidity_count,
        sp_diabetes,
        sp_chf,
        sp_copd,
        sp_cncr
    FROM dim_beneficiary
)
SELECT
    claim_year,
    COUNT(*)                                    AS total_beneficiaries,
    COUNT(*) FILTER (WHERE sp_diabetes)         AS diabetes_cohort,
    COUNT(*) FILTER (WHERE sp_chf)              AS chf_cohort,
    COUNT(*) FILTER (WHERE sp_copd)             AS copd_cohort,
    COUNT(*) FILTER (WHERE sp_cncr)             AS cancer_cohort,
    ROUND(AVG(comorbidity_count), 2)            AS avg_comorbidities,
    MAX(comorbidity_count)                      AS max_comorbidities
FROM bene_comorbidity
GROUP BY claim_year
ORDER BY claim_year
