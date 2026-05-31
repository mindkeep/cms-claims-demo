import duckdb

from cms_platform.common.config import Settings


def build_star_schema(conn: duckdb.DuckDBPyConnection, settings: Settings) -> None:
    """Transform raw CMS tables into a clean star schema.

    Builds: dim_beneficiary (SCD-style), dim_provider, dim_diagnosis (ICD-9),
    dim_date, fact_inpatient, fact_outpatient, fact_carrier, fact_pde,
    and a unified fact_claim_line view across all claim types.
    # V2 note: facts will be partitioned by claim_year + beneficiary_id_hash
    # to keep joins shard-local at scale.
    Implemented in WP2.
    """
    raise NotImplementedError("WP2")
