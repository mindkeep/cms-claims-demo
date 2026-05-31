# Entity-Relationship Diagram

> **Status:** Placeholder. WP2 generates the Mermaid ERD.

## Star Schema Overview

The analytical schema is a star schema centered on claim events:
- **Fact tables:** fact_inpatient, fact_outpatient, fact_carrier, fact_pde
- **Unified view:** fact_claim_line (cross-cutting analytics)
- **Dimension tables:** dim_beneficiary, dim_provider, dim_diagnosis, dim_date

WP2 fills in the full Mermaid diagram here.
