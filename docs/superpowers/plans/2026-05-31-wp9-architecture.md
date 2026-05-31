# WP9: ARCHITECTURE.md Completion

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand `ARCHITECTURE.md` with the missing V2 distributed-systems design sections that demonstrate staff-level thinking: observability, multi-tenancy, schema evolution, operational runbooks, and a quantified cost model.

**Architecture:** Pure documentation expansion. No code changes. All sections must be concrete and specific — not generic "we would add monitoring" filler. Every design decision must name the technology, explain why, and include the tradeoff.

**Tech Stack:** Markdown only

---

## File Structure

- Modify: `ARCHITECTURE.md`

---

### Task 1: Add missing V2 architecture sections

Read the current `ARCHITECTURE.md` first. It already has:
- Design Philosophy
- V0→V1→V2 Migration Path (Storage, Ingestion, API/Serving)
- Partitioning Strategy
- Kafka Streaming Design (V2)
- High Availability & Resiliency (V2)
- Security & Compliance
- Cost & Complexity Tradeoffs

**Add the following sections after "Cost & Complexity Tradeoffs":**

---

#### Section: Observability Stack (V2)

Three-signal observability: metrics, logs, traces.

**Metrics (Prometheus + Grafana):**
- FastAPI: `prometheus-fastapi-instrumentator` — request count, latency P50/P95/P99, error rate per route
- DuckDB (V0): custom metrics on query duration, row counts per transform step
- Kafka (V2): consumer lag per topic partition, producer send rate, topic backlog bytes
- Key SLOs: API P99 < 500ms, ingest throughput > 10K claims/sec at V2 full load, consumer lag < 30s

**Logs (structured JSON → centralized):**
- All application logs use Python `structlog` (or stdlib JSON formatter) emitting structured JSON
- PHI audit log (`common/audit.py`) is the highest-priority log stream — routed separately from app logs
- V2: PHI audit log is a dedicated Kafka topic (`cms.audit`) consumed by a SIEM (Splunk / OpenSearch)
- Log levels: DEBUG in dev, INFO in staging, WARNING in prod. Never log raw PHI values — `desynpuf_id` in logs is the masked form only

**Traces (OpenTelemetry):**
- V1+: instrument FastAPI with `opentelemetry-instrumentation-fastapi`
- Trace context propagated through DuckDB query span + audit log emission
- Sampling: 100% for error paths, 1% for healthy paths in production
- Backend: Jaeger (self-hosted) or Honeycomb (SaaS)

**What V0 provides today:**
- `logging` at each pipeline step (download, load, transform)
- Structured audit records in `common/audit.py`
- Row count logging after each DuckDB insert (visibility into `ignore_errors=true` behavior)

---

#### Section: Multi-Tenancy Design (V2)

**Problem:** The V0 system is single-tenant (one DuckDB file, one schema). V2 must support multiple payers or research organizations, each with isolated data.

**Approach: Schema-per-tenant isolation**

- Each tenant gets a dedicated Postgres schema: `CREATE SCHEMA tenant_{id}`
- All tables live under the tenant schema: `tenant_abc.fact_inpatient`, `tenant_abc.dim_beneficiary`
- API layer: tenant ID extracted from JWT `org_id` claim; FastAPI dependency sets `SET search_path = tenant_{id}` at connection time
- Kafka: topic-per-tenant naming: `cms.{tenant_id}.inpatient`; consumer group: `analytics-loader-{tenant_id}`

**Why schema-per-tenant over row-level security (RLS):**
- RLS adds predicate overhead on every query; at V2 analytical query volumes this degrades
- Schema isolation allows tenant-specific vacuuming, index strategies, and backup scheduling
- Simpler audit trail — no risk of a misconfigured RLS policy leaking cross-tenant data
- Tradeoff: schema proliferation at >1000 tenants. Mitigate by pooling small tenants into "shared schema + RLS" tier, reserving dedicated schemas for enterprise accounts

**Onboarding a new tenant:**
1. `CREATE SCHEMA tenant_{id}` + run DDL migrations
2. Provision Kafka topics with topic-level ACLs
3. Issue JWT signing key scoped to `org_id`
4. Bootstrap with historical CSV load (the V0 batch ingest becomes the historical onboarding tool)

---

#### Section: Schema Evolution (V2)

**Problem:** CMS releases new data dictionary versions. New ICD-10 coding. New claim fields. The raw schema must evolve without breaking downstream consumers.

**Strategy: Schema Registry + Migration-as-Code**

- **Avro schema registry** (Confluent Schema Registry or AWS Glue): every Kafka message schema is versioned. Producers register new schemas; consumers specify their compatibility level (`BACKWARD`, `FORWARD`, or `FULL`).
- **SQL migrations:** `alembic` (Postgres) manages DDL migrations. Each migration is reversible. Migration files live in `sql/migrations/` and are applied by the CI pipeline in staging before prod.
- **Backward compatibility rule:** new nullable columns only; no column renames or type changes without a migration pair (add new → backfill → remove old in 3 steps across 3 releases).

**V0 → V2 migration of the star schema:**
1. Dump DuckDB star schema to Parquet (partitioned by `claim_year`)
2. `COPY FROM PARQUET` into Postgres via `pg_parquet` or `COPY` + Python loader
3. Verify row counts match; run the 5 analytical queries against both systems; diff results
4. Switch `common/db.py::get_connection()` to return a Postgres connection

**CMS data dictionary version handling (V0):**
- `_BENE_COLS`, `_INPATIENT_COLS`, etc. in `ingest/load.py` are the schema version pins
- When CMS releases a new dictionary version, create a new column list and a version-aware loader
- Never change existing column lists in-place — tag them with a version comment

---

#### Section: Operational Runbooks

**Runbook 1: DuckDB corrupt/missing (V0)**
1. Source of truth is the raw CSVs in `data/raw/`
2. Delete `data/processed/cms.duckdb`
3. Run `make ingest` — download step is idempotent (skips existing zips), load step re-creates DuckDB
4. RTO: ~20 min for subsample 1; ~6 hours for all 20 subsamples

**Runbook 2: Kafka consumer lag spike (V2)**
1. Check consumer group lag: `kafka-consumer-groups.sh --describe --group analytics-loader`
2. If lag > 10 min: scale consumer pods (`kubectl scale deployment analytics-loader --replicas=N`)
3. If lag is caused by a bad message: identify via dead-letter topic `cms.{topic}.dlq`, fix the schema, replay from offset
4. Never reset consumer offsets without recording the reset in the audit log

**Runbook 3: PHI data request (V0 + V2)**
1. Receive request with `beneficiary_id` and accessor identity
2. Query `common/audit.py` logs for all access records for that beneficiary
3. Export masked record (`phi_read=False`) unless requestor holds PHI_READ claim in JWT
4. Log the disclosure event via `log_access(action="disclosure", ...)`

**Runbook 4: Failed CI pipeline**
1. `quality` job fails → fix ruff/mypy errors before proceeding; never bypass with `# noqa` unless the rule is genuinely inapplicable
2. `test` job fails → run `make test` locally, fix failing tests; the CI test matrix is the contract
3. `docker` job fails → run `docker build .` locally; check for missing deps in `pyproject.toml`

---

#### Section: V2 Cost Model

Concrete sizing for a 20-subsample deployment (~2.3M beneficiaries, ~500M claim records).

**Storage:**
| Layer | Size estimate | Cost (AWS us-east-1, 2025 pricing) |
|-------|--------------|-------------------------------------|
| Raw CSVs (S3) | ~80 GB (20 subsamples × ~4 GB) | ~$1.84/month |
| DuckDB file (EBS gp3) | ~15 GB processed | ~$1.20/month |
| Postgres (RDS db.r6g.xlarge, Multi-AZ) | ~50 GB | ~$400/month |
| Kafka (MSK 3-broker m5.large) | log retention 72h | ~$600/month |

**Compute:**
| Service | Sizing | Cost |
|---------|--------|------|
| FastAPI (ECS Fargate, 2 vCPU / 4 GB × 2 replicas) | 730 hrs/month | ~$120/month |
| Analytics loader (ECS 2 vCPU × 2 consumers) | 730 hrs | ~$120/month |
| Risk scorer (ECS 4 vCPU / 8 GB × 1 pod) | on-demand | ~$60/month |

**Total V2 estimated:** ~$1,300/month for full 20-subsample production deployment.

**V0 cost:** $0 — runs on a laptop.

**Decision rule:** the V0 → V2 migration is justified when query latency exceeds 5 seconds for common cohort queries OR when a second concurrent writer is needed. At V0 with 1 subsample, DuckDB query time is <1s. The migration trigger is real, not speculative.

---

**Files:**
- Modify: `ARCHITECTURE.md`

- [ ] **Step 1: Read the current ARCHITECTURE.md**

Read the full current content of `ARCHITECTURE.md`.

- [ ] **Step 2: Identify insertion point**

Find the "## Cost & Complexity Tradeoffs" section (it's the last section). The new content goes after it.

- [ ] **Step 3: Append the 5 new sections**

Append to `ARCHITECTURE.md` after the Cost & Complexity Tradeoffs table:

```markdown
---

## Observability Stack (V2)

[content from Task 1 section above]

---

## Multi-Tenancy Design (V2)

[content from Task 1 section above]

---

## Schema Evolution (V2)

[content from Task 1 section above]

---

## Operational Runbooks

[content from Task 1 section above]

---

## V2 Cost Model

[content from Task 1 section above]
```

Write the content verbatim from the specification above (not paraphrased). The sections must be concrete and specific — replace any "[content from...]" with the actual content.

- [ ] **Step 4: Run lint and tests**

```bash
.venv/bin/ruff check src/ tests/
.venv/bin/mypy src/
.venv/bin/pytest tests/ -q
```

Expected: no errors, all tests pass. (ARCHITECTURE.md is not linted by ruff.)

- [ ] **Step 5: Commit**

```bash
git add ARCHITECTURE.md
git commit -m "docs(architecture): add observability, multi-tenancy, schema evolution, runbooks, cost model"
```
