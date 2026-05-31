# WP8: Narrative Notebook + README Completion

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `notebooks/story.ipynb` (end-to-end platform walkthrough) and enrich the README JD mapping table with specific code evidence.

**Architecture:** A self-contained Jupyter notebook using in-memory DuckDB fixtures — no actual CMS data download required to run the demo. Narrative flows: intro → ingest model → star schema → analytics → risk scoring → care gaps → scaling story.

**Tech Stack:** Python 3.14, DuckDB, Polars, scikit-learn, ipynb JSON format

---

## File Structure

- Create: `notebooks/story.ipynb` — Jupyter notebook (ipynb JSON)
- Modify: `README.md` — expand JD mapping table

---

### Task 1: Create the narrative notebook

The notebook uses in-memory DuckDB fixtures so it runs without any downloaded data. It is pure Python in `.ipynb` JSON format; no `jupyter` in project deps — write runnable cells only (no magic commands, no `%` syntax).

**Notebook structure (cells in order):**

**Cell 1 — markdown:** Title + intro
```
# CMS Claims Analytics Platform — End-to-End Walkthrough

Portfolio demo built on [CMS DE-SynPUF](https://www.cms.gov/) synthetic Medicare claims.
Demonstrates a **V0 → V2 architecture maturity story**:

| Tier | What it is |
|------|------------|
| V0 | Batch analytics core: CSV → DuckDB star schema + SQL library |
| V1 | Served platform: FastAPI + risk scoring + Ollama explainer |
| V2 | Scale & resiliency: Postgres, Kafka streaming, HA |

This notebook walks through every layer: data ingest, star schema transforms,
five analytical queries, risk stratification, care-gap explanation, and the
distributed-systems design that V0 was deliberately built to evolve into.
```

**Cell 2 — code:** Setup
```python
import sys, pathlib
sys.path.insert(0, str(pathlib.Path("..") / "src"))

import duckdb
import polars as pl

conn = duckdb.connect()
print("DuckDB", duckdb.__version__, "| Polars", pl.__version__)
```

**Cell 3 — markdown:** "1. Data Acquisition" section header + explanation of how ingest works (chunked CSV, explicit schema, idempotency). Include the file template table.

**Cell 4 — code:** Show the file templates and validation:
```python
from cms_platform.ingest.download import file_names_for_sample
files = file_names_for_sample(1)
for f in files:
    print(f)
```

**Cell 5 — markdown:** "2. Star Schema" + explanation of dim/fact design choices.

**Cell 6 — code:** Build the star schema on fixture data, show table row counts:
```python
from cms_platform.ingest.load import _ensure_raw_tables
from cms_platform.schema.transforms import build_star_schema
from cms_platform.common.config import Settings

# Seed in-memory DuckDB with fixture rows
_ensure_raw_tables(conn)

# Insert one beneficiary fixture
conn.execute("""
INSERT INTO raw_beneficiary VALUES (
  'BENE001', '20080101', '', '1', '1', '0',
  '25', '0', '12', '12', '0', '12',
  '0','1','0','0','1','0','1','0','0','0','0',
  '1500.00','300.00','800.00', '2008'
)
""")

# Insert one inpatient claim
conn.execute("""
INSERT INTO raw_inpatient
SELECT 'BENE001','CLM001','20080301','20080305','0011B','12345','','','','','','','','','',
       '20080301','1500.00','200.00','4','41401','','','','','','','','','','','',
       '','','','','','','',''
""")

# Insert one carrier claim
conn.execute("""
INSERT INTO raw_carrier
SELECT 'BENE001','CAR001','20080601','20080601',
       '','100.00','','','','','','','','','','','',
       '','','','','','','','','','','','','',
       '','','','','','','','','41401',
       '','','','','','','','','','','',
       '','',''
""")

# Insert one outpatient claim
conn.execute("""
INSERT INTO raw_outpatient
SELECT 'BENE001','OUT001','20080401','20080401','0011B','12345','','',
       '','','','','','','','','','','',
       '500.00','50.00','','','','','','','','','','','',
       '','','','','','','','41401',
       '','','','','','','',''
""")

# Insert one PDE
conn.execute("""
INSERT INTO raw_pde
SELECT 'BENE001','PDE001','20080201','NDC12345','30','90','25.00','80.00','','',''
""")

settings = Settings(_env_file=None)
build_star_schema(conn, settings)

for tbl in ['dim_date','dim_beneficiary','dim_provider','dim_diagnosis',
            'fact_inpatient','fact_outpatient','fact_carrier','fact_pde']:
    n = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
    print(f"{tbl:25s}  {n:>6} rows")
```

> NOTE: The fixture SQL above must match the actual column count of the raw tables as defined in `src/cms_platform/ingest/load.py`. Count columns carefully from `_BENE_COLS`, `_INPATIENT_COLS`, etc. Use positional INSERT with exactly the right number of placeholder values. If the column count doesn't match, use a CREATE TABLE AS SELECT approach seeding only named columns. The simplest approach: use `conn.execute("INSERT INTO raw_beneficiary SELECT ...")` with explicit column names.

Actually, use this simpler approach for fixtures — INSERT with explicit column names:

```python
conn.execute("""
    INSERT INTO raw_beneficiary (
        DESYNPUF_ID, BENE_BIRTH_DT, BENE_DEATH_DT,
        BENE_SEX_IDENT_CD, BENE_RACE_CD, BENE_ESRD_IND,
        SP_STATE_CODE, BENE_COUNTY_CD,
        BENE_HI_CVRAGE_TOT_MONS, BENE_SMI_CVRAGE_TOT_MONS,
        BENE_HMO_CVRAGE_TOT_MONS, PLAN_CVRG_MOS_NUM,
        SP_ALZHDMTA, SP_CHF, SP_CHRNKIDN, SP_CNCR, SP_COPD,
        SP_DEPRESSN, SP_DIABETES, SP_ISCHMCHT, SP_OSTEOPRS,
        SP_RA_OA, SP_STRKETIA,
        MEDREIMB_IP, MEDREIMB_OP, MEDREIMB_CAR, _claim_year
    ) VALUES (
        'BENE001', '19400101', '',
        '1', '1', '0',
        '25', '001',
        '12', '12', '0', '12',
        '0','1','0','0','1','0','1','0','0','0','0',
        '1500.00','300.00','800.00','2008'
    )
""")
```

Do the same explicit-column INSERT for all other raw tables. Look up exact column names from `src/cms_platform/ingest/load.py` (`_BENE_COLS`, `_INPATIENT_COLS`, etc.).

**Cell 7 — markdown:** "3. Analytical Queries" + explain the 5 queries.

**Cell 8 — code:** Run each query and show the result:
```python
from cms_platform.analytics.queries import (
    readmission_30day, cohort_segmentation,
    cost_benchmarking, care_gap_detection, utilization_trends
)

print("=== 30-day readmission rate ===")
print(readmission_30day(conn))

print("\n=== Cohort segmentation ===")
print(cohort_segmentation(conn))

print("\n=== Cost benchmarking ===")
print(cost_benchmarking(conn))

print("\n=== Care gap detection ===")
print(care_gap_detection(conn))

print("\n=== Utilization trends ===")
print(utilization_trends(conn))
```

**Cell 9 — markdown:** "4. Risk Stratification" + explain the model, include the honest-metrics caveat.

**Cell 10 — code:** Train and predict:
```python
from cms_platform.scoring.risk_model import train_risk_model, predict_risk, RISK_FEATURES

# Pull features from dim_beneficiary
features_df = conn.execute(f"""
    SELECT {', '.join(RISK_FEATURES)} FROM dim_beneficiary
""").fetchall()
# Build polars DataFrame
import polars as pl
cols_desc = conn.execute(f"SELECT {', '.join(RISK_FEATURES)} FROM dim_beneficiary LIMIT 0").description
col_names = [d[0] for d in cols_desc]

# Need more rows for training — add synthetic rows
for i in range(20):
    conn.execute(f"""
        INSERT INTO raw_beneficiary (
            DESYNPUF_ID, BENE_BIRTH_DT, SP_DIABETES, SP_CHF,
            SP_ALZHDMTA, SP_CHRNKIDN, SP_CNCR, SP_COPD,
            SP_DEPRESSN, SP_ISCHMCHT, SP_OSTEOPRS, SP_RA_OA, SP_STRKETIA,
            MEDREIMB_IP, MEDREIMB_OP, MEDREIMB_CAR, _claim_year,
            BENE_SEX_IDENT_CD, BENE_RACE_CD, BENE_ESRD_IND,
            SP_STATE_CODE, BENE_COUNTY_CD,
            BENE_HI_CVRAGE_TOT_MONS, BENE_SMI_CVRAGE_TOT_MONS,
            BENE_HMO_CVRAGE_TOT_MONS, PLAN_CVRG_MOS_NUM
        ) VALUES (
            'BENE{i:03d}', '19400101', '{"1" if i % 3 == 0 else "0"}',
            '{"1" if i % 4 == 0 else "0"}', '0', '0', '0', '0',
            '0', '0', '0', '0', '0',
            '{i * 100}', '{i * 50}', '{i * 80}', '2008',
            '1', '1', '0', '25', '001', '12', '12', '0', '12'
        )
    """)
conn.execute("DELETE FROM dim_beneficiary")
from cms_platform.schema.transforms import _populate_dim_beneficiary
_populate_dim_beneficiary(conn)

features_df = conn.execute(f"SELECT {', '.join(RISK_FEATURES)} FROM dim_beneficiary").pl()
```

> NOTE: `conn.execute(...).pl()` may not be available in all DuckDB versions. Use `_to_polars()` helper from `cms_platform.analytics.queries` module if needed, or use `fetchall()` + `description`.

Actually, use a simpler approach — create the features DataFrame directly:

```python
import polars as pl
from cms_platform.scoring.risk_model import train_risk_model, predict_risk, RISK_FEATURES

# Generate synthetic training data (realistic feature distribution)
import random
random.seed(42)
n = 50

data = {}
bool_cols = [c for c in RISK_FEATURES if c.startswith("sp_")]
money_cols = [c for c in RISK_FEATURES if c.startswith("medreimb_")]

for col in bool_cols:
    data[col] = [random.random() > 0.7 for _ in range(n)]
for col in money_cols:
    data[col] = [round(random.uniform(0, 5000), 2) for _ in range(n)]

features = pl.DataFrame(data)
# Risk label: high cost OR multiple conditions
target = pl.Series("label", [
    1 if (sum(row[c] for c in bool_cols) >= 3 or max(row[c] for c in money_cols) > 3000)
    else 0
    for row in features.to_dicts()
])

model = train_risk_model(features, target, Settings(_env_file=None))
scores = predict_risk(model, features)
print(f"Risk scores (first 10): {scores[:10].to_list()}")
print(f"Score range: [{scores.min():.3f}, {scores.max():.3f}]")
print(f"High-risk (>0.5): {(scores > 0.5).sum()} / {len(scores)}")
print()
print("Note: synthetic data caps real predictive signal.")
print("These figures demonstrate the pipeline, not clinical validity.")
```

**Cell 11 — markdown:** "5. Care-Gap Explanation" + explain Ollama integration, stub fallback.

**Cell 12 — code:** Show the explainer (uses stub since Ollama not running):
```python
from cms_platform.scoring.explainer import explain_care_gaps
from cms_platform.common.config import Settings

settings = Settings(_env_file=None)
gaps = ["No carrier claim in past 12 months", "Diabetes diagnosis with no HbA1c claim"]
explanation = explain_care_gaps("BENE001", gaps, settings)
print(explanation)
```

**Cell 13 — markdown:** "6. How This Scales — V0 → V2" — the architecture story. Include a table of the 5 swap points:

```
| What changes | V0 | V2 |
|---|---|---|
| Storage | DuckDB file | Postgres + columnar warehouse |
| Ingestion | Batch CSV download | Kafka streaming topics |
| API serving | Single Docker container | LB + read replicas |
| Partitioning | None | Hash by beneficiary_id % N |
| Audit log | Python logger → stdout | Dedicated Kafka topic → SIEM |
```

Also quote the relevant V2 seam annotations from the code (show 3 examples).

**Cell 14 — markdown:** Closing — repo structure, links.

---

**Files:**
- Create: `notebooks/story.ipynb`

- [ ] **Step 1: Read the column definitions**

Read `src/cms_platform/ingest/load.py` — find `_BENE_COLS`, `_INPATIENT_COLS`, `_OUTPATIENT_COLS`, `_CARRIER_COLS`, `_PDE_COLS`. These are the exact column names for the fixture inserts.

- [ ] **Step 2: Read the analytics query functions**

Read `src/cms_platform/analytics/queries.py` and all 5 SQL files under `sql/analytics/`. Understand what columns each returns so you can write realistic fixture data.

- [ ] **Step 3: Read the scoring module**

Read `src/cms_platform/scoring/risk_model.py` and `src/cms_platform/scoring/explainer.py`. Confirm `RISK_FEATURES` list, `train_risk_model` signature, `explain_care_gaps` signature.

- [ ] **Step 4: Write the notebook JSON**

Create `notebooks/story.ipynb` as valid Jupyter notebook JSON (nbformat 4.5). Structure:
```json
{
  "nbformat": 4,
  "nbformat_minor": 5,
  "metadata": {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.14"}
  },
  "cells": [...]
}
```

Each cell has format:
- Markdown: `{"cell_type": "markdown", "id": "...", "metadata": {}, "source": ["line1\n", "line2"]}`
- Code: `{"cell_type": "code", "id": "...", "metadata": {}, "execution_count": null, "outputs": [], "source": ["line1\n", "line2"]}`

IDs: unique 8-char hex strings.

Use the outline from Task 1 above. All code cells must be valid Python that runs against an in-memory DuckDB (no actual CMS data required). Use `Settings(_env_file=None)` to avoid needing a `.env` file.

Key requirements:
- The fixture inserts must use explicit column names (not positional)
- Use `random.seed(42)` for reproducibility
- Include the honest-metrics caveat in both the markdown and the code cell output text
- The care-gap explainer cell should use the stub (no Ollama needed) — just call `explain_care_gaps()`
- Show `file_names_for_sample(1)` output to demonstrate the 8-file template
- All 5 analytics queries must be called and printed

- [ ] **Step 5: Verify the notebook is valid JSON**

Run: `python -c "import json; json.load(open('notebooks/story.ipynb')); print('valid JSON')"`

- [ ] **Step 6: Verify the code cells run**

Extract all code cells and run them as a script to verify they execute without errors:
```bash
python -c "
import json, sys
nb = json.load(open('notebooks/story.ipynb'))
code = '\n'.join(
    ''.join(c['source'])
    for c in nb['cells'] if c['cell_type'] == 'code'
)
print(code[:200])
# Write to temp script and run
open('/tmp/nb_check.py','w').write(code)
"
.venv/bin/python /tmp/nb_check.py
```

- [ ] **Step 7: Commit**

```bash
git add notebooks/story.ipynb
git commit -m "feat(notebook): add end-to-end narrative walkthrough (story.ipynb)"
```

---

### Task 2: Expand README JD mapping table

The current JD mapping table in README.md has 8 rows but lacks specific code pointers. Expand each row to include the exact module path, function/class name, and a one-line "why it counts."

**Files:**
- Modify: `README.md`

Replace the current JD Requirement Mapping table with an expanded version:

```markdown
## JD Requirement Mapping

| Requirement | Where demonstrated | Key evidence |
|-------------|-------------------|-------------|
| Large multi-table SQL, window functions, CTEs | `sql/analytics/*.sql` + `src/cms_platform/analytics/queries.py` | 5 query types: 30-day readmissions (LAG + date range), cohort FILTER aggregation, cost PERCENTILE_CONT + NTILE, care-gap anti-join, YoY utilization LAG |
| AI-driven features → scalable products | `src/cms_platform/scoring/risk_model.py` + `scoring/explainer.py` | sklearn Pipeline risk stratification; Ollama/OpenAI-compat care-gap narrative; honest-metrics caveat in all outputs |
| Sensitive / regulated data handling | `COMPLIANCE.md`, `src/cms_platform/common/audit.py`, `common/mask.py` | `log_access()` before every PHI read; `mask_record()` with SHA-256 prefix; `phi_read=True` bypass pattern |
| Distributed systems thinking | `ARCHITECTURE.md`, V2 seam annotations in `ingest/load.py` + `schema/transforms.py` | Kafka topic design, shard partitioning (beneficiary_id_hash % N), HA failover, schema registry design |
| V0 / V1 / V2 architecture maturity | Entire repo structure + `ARCHITECTURE.md` | Each tier is a runnable state; seam annotations mark the exact swap points |
| Platform / API ecosystem | `src/cms_platform/api/` — FastAPI serving layer | 4 routes; PHI masking at boundary; per-request DuckDB connection via FastAPI dependency; Pydantic v2 models |
| CI/CD pipelines | `.github/workflows/ci.yml` | 3-job pipeline: quality (ruff + mypy) → test (pytest, 76 tests) → Docker build |
| Staff-level engineering judgment | Design decisions in `ARCHITECTURE.md`, `COMPLIANCE.md`, `CLAUDE.md`, `docs/` | YAGNI deferral table; seam annotation discipline; "honest metrics" rule |
| Data modeling at scale | `sql/schema/ddl.sql`, `src/cms_platform/schema/transforms.py` | Star schema: 4 dims + 4 facts + unified view; idempotent surrogate keys via ROW_NUMBER + NOT EXISTS |
| Observability / audit trails | `src/cms_platform/common/audit.py` | Structured JSON audit log on every PHI access; V2 seam to Kafka SIEM topic |
```

- [ ] **Step 1: Read the current README.md**

Read the full `README.md`.

- [ ] **Step 2: Replace the JD mapping section**

Find the `## JD Requirement Mapping` section and replace it with the expanded table above. Verify the table renders correctly as markdown (no broken pipes, aligned columns not required since GitHub renders any pipe table).

- [ ] **Step 3: Run lint and tests**

```bash
.venv/bin/ruff check src/ tests/
.venv/bin/mypy src/
.venv/bin/pytest tests/ -q
```

Expected: no ruff/mypy errors (README is not checked), all tests pass.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(readme): expand JD mapping table with specific code evidence"
```
