-- DDL for CMS Claims star schema
-- Business question: defines the dimensional model for all analytical queries
-- SQL technique:     SCD-style dim_beneficiary, hash-partitioned facts
-- Scaling note:      partition keys (claim_year, beneficiary_id_hash) chosen for V2 shard-local joins
--
-- WP2 fills in the full DDL. This file is the authoritative schema definition.
-- Run via: schema/transforms.py::build_star_schema()

-- Placeholder: WP2 adds CREATE TABLE statements here
