# Compliance & Regulated Data Posture

> **Status:** Placeholder. WP6 fills in the full posture. The core audit
> infrastructure (`common/audit.py`) is already wired; this document describes
> the policy it enforces.

## Why these controls exist

The CMS DE-SynPUF dataset is fully synthetic and safe to handle publicly.
These controls are modeled anyway — the engineering demonstration is the point.
A production Medicare claims platform handles real PHI; this project shows that
the engineering team has internalized what that means.

## Controls (WP6 expands each section)

### Beneficiary IDs as PHI
All `beneficiary_id` values are treated as PHI throughout the codebase.

### Audit Logging
Every beneficiary-level read calls `common.audit.log_access()`, which emits a
structured JSON audit record containing: beneficiary_id, action, accessor,
timestamp, and request context. See `src/cms_platform/common/audit.py`.

### Field-Level Masking
A config-driven masking helper (WP6) redacts or hashes sensitive fields before
they leave the API boundary.

### Minimum Necessary Access
API endpoints return only the fields required for the stated purpose. No bulk
beneficiary exports without explicit scope.

### Data Retention
Raw CSVs and the DuckDB file are gitignored and never committed. At V2, a
retention policy (default: 7 years, matching CMS requirements for Medicare data)
is enforced via automated deletion of raw records.

### De-identification Note
The dataset is already synthetic and de-identified. In a production context,
de-identification would follow the Safe Harbor or Expert Determination methods
under HIPAA before any data leaves the regulated boundary.
