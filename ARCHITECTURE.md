# Architecture — CMS Claims Analytics Platform

> **Status:** Living document. Written before V0 code to establish design intent.
> Updated as each work package completes.
>
> **How to read this:** The V2 design below drove every V0 abstraction choice.
> Read this first, then read the V0 code — the V2 seam annotations in the code
> will make sense.

---

## Design Philosophy

V0 is not a prototype to be thrown away. It is a deliberately simple foundation
whose boundaries were chosen to make V1→V2 evolution non-destructive:

- **DuckDB** was selected for V0 because it requires zero infrastructure and is
  fully analytical-SQL-compatible. The `get_connection()` factory in `common/db.py`
  is the single swap point for Postgres/columnar warehouse at V2.
- **Synthea CSV download** in `ingest/download.py` is the V0 data source —
  five CSV files (patients, encounters, conditions, medications, providers)
  loaded into raw DuckDB tables with all-VARCHAR columns. The swap to streaming
  is a replacement of one module, not a rewrite of the analytical layer.
- **Star schema** is designed for partition pruning by `claim_year` and
  `beneficiary_id_hash` — the same partition keys used at V2.

---

## V0 → V1 → V2 Migration Path

### Storage

| Tier | Store | Reason |
|------|-------|--------|
| V0 | DuckDB (embedded) | Zero-infra, full analytical SQL, laptop-tractable |
| V1 | DuckDB + read API | FastAPI layer over the same DuckDB file |
| V2 | Postgres + columnar warehouse (e.g., Redshift, BigQuery, or Postgres + columnar extension) | Concurrent writes, replication, multi-tenancy |

**Migration path (V0→V2):** Replace `common/db.py::get_connection()` with a
Postgres connection pool (psycopg3 / asyncpg). All SQL in `sql/` is
standard ANSI SQL with window functions — no DuckDB-specific syntax. The
star schema DDL translates directly; partition keys (`claim_year`,
`beneficiary_id_hash`) become Postgres partition columns.

### Ingestion

| Tier | Mechanism | Reason |
|------|-----------|--------|
| V0 | Synthea CSV download + raw table load | Reproducible, testable, no infra |
| V1 | Batch + scheduled refresh | Adds daily/weekly pipeline trigger |
| V2 | Kafka streaming topics per claim type | Near-real-time ingestion, replay, backpressure |

**Migration path (V0→V2):** The Synthea CSV downloader in `ingest/download.py`
is replaced by a Blue Button 2.0 FHIR R4 consumer. The raw table contract
(`raw_patients`, `raw_encounters`, etc.) stays identical — different producer,
same schema. One topic per FHIR resource type (Patient, Encounter, Condition,
MedicationRequest, Practitioner). Consumer groups allow parallel ingestion.
Schema registry enforces the same explicit-typing discipline as V0.

### API / Serving

| Tier | Serving | Notes |
|------|---------|-------|
| V0 | None — CLI only | `make ingest`, notebook |
| V1 | FastAPI (single-node, Docker) | Read-only; DuckDB connection per request |
| V2 | FastAPI behind load balancer, read replicas | Connection pooling, horizontal scale |

---

## Partitioning Strategy

**Primary partition key:** `claim_year` (2008, 2009, 2010; extensible to current year)
**Secondary (hash) partition key:** `beneficiary_id_hash % N` (N = shard count)

Rationale: the dominant query patterns are (a) longitudinal — all claims for a
beneficiary across years, and (b) cohort — all beneficiaries in a year matching
a chronic-condition flag. Hash-partitioning by beneficiary keeps (a) shard-local.
Range-partitioning by year keeps (b) partition-prunable. The star schema's fact
tables carry both keys as partition columns.

Shard count N: start at 8 for a 20-subsample deployment (~2.3M beneficiaries ÷
8 ≈ 290K per shard). Scale to 32 when the analytical layer saturates a single
node.

---

## Kafka Streaming Design (V2)

**Topics:** one per CMS claim type — `cms.inpatient`, `cms.outpatient`,
`cms.carrier`, `cms.pde`, `cms.beneficiary`.

**Producers:** claim processors publish JSON events keyed by `beneficiary_id`
(ensures ordering per beneficiary within a partition).

**Consumers:** one consumer group per downstream: `analytics-loader` (writes to
fact tables), `risk-scorer` (triggers incremental re-scoring), `audit-logger`
(PHI access stream).

**Schema registry:** Avro schemas enforcing the same typed columns as the V0
data dictionary. No schema drift — any producer publishing an unknown field
is rejected.

**FHIR compatibility:** Topic schemas use FHIR R4 resource types (`Patient`,
`Encounter`, `Condition`) as the event envelope, so the V2 Kafka pipeline is
compatible with real Blue Button 2.0 data without field re-mapping.

**Replay / backfill:** The V0 batch CSV load becomes the Kafka producer for
historical data. Same schema, different producer implementation.

---

## High Availability & Resiliency (V2)

- **Database:** Postgres streaming replication (1 primary, 2 read replicas).
  Analytical queries routed to replicas; writes to primary only.
- **API:** Stateless FastAPI pods behind a load balancer. Horizontal scale via
  replica count. No session state — all state in the database.
- **Kafka:** 3-broker cluster, replication factor 3, min ISR 2. Topic retention
  72 hours for replay.
- **Failure modes:** DuckDB (V0) is single-node; a crash loses in-flight writes
  but the raw CSVs are the source of truth — re-running `make ingest` is the
  recovery path. At V2, WAL-based Postgres replication + Kafka log retention
  cover both the database and the ingestion pipeline.

---

## Security & Compliance

See [`COMPLIANCE.md`](COMPLIANCE.md) for the full PHI posture.

Key architectural controls:

- **Audit logging:** every beneficiary-level read emits a structured JSON log
  entry via `common/audit.py`. At V2, the audit stream is a dedicated Kafka
  topic consumed by a SIEM.
- **Field-level masking:** configurable redaction of PII fields at the API layer.
  Downstream consumers receive masked data unless they hold an explicit
  `PHI_READ` claim in their JWT.
- **Network:** at V2, the database and Kafka cluster are VPC-internal. The API
  is the only public-facing surface. TLS everywhere.
- **Data at rest:** disk encryption on all storage nodes. The V0 DuckDB file is
  stored in `data/processed/` which is gitignored and never committed.

---

## Cost & Complexity Tradeoffs

| Decision | V0 choice | V2 choice | What you'd defer |
|----------|-----------|-----------|-----------------|
| Storage | DuckDB | Postgres + columnar | Columnar until query latency demands it |
| Ingestion | Batch CSV | Kafka streaming | Kafka until latency SLA < 1 hour |
| API scale | Single Docker container | LB + replicas | Replicas until P99 latency degrades |
| Sharding | N/A | Hash by beneficiary | Sharding until single-node saturates |
| Schema evolution | Manual migration | Schema registry + migration tool | Registry until >2 producers exist |

The principle: defer complexity until the pain is real and measurable. V0 runs
on a laptop. V2 runs on a cluster. The migration path between them is explicit
and non-destructive.

---

## Observability Stack (V2)

Three-signal observability: metrics, logs, traces.

**Metrics (Prometheus + Grafana):**
- FastAPI: `prometheus-fastapi-instrumentator` — request count, latency P50/P95/P99, error rate per route
- DuckDB (V0): custom metrics on query duration, row counts per transform step
- Kafka (V2): consumer lag per topic partition, producer send rate, topic backlog bytes
- Key SLOs: API P99 < 500 ms, ingest throughput > 10K claims/sec at V2 full load, consumer lag < 30 s

**Logs (structured JSON → centralized):**
- All application logs emit structured JSON via Python's stdlib logging with a JSON formatter
- PHI audit log (`common/audit.py`) is the highest-priority log stream — routed separately from app logs
- V2: PHI audit log is a dedicated Kafka topic (`cms.audit`) consumed by a SIEM (Splunk / OpenSearch)
- Log levels: DEBUG in dev, INFO in staging, WARNING in prod. Never log raw PHI values — `patient_id` appears in logs only in its masked form

**Traces (OpenTelemetry):**
- V1+: instrument FastAPI with `opentelemetry-instrumentation-fastapi`
- Trace context propagated through DuckDB query span + audit log emission
- Sampling: 100% for error paths, 1% for healthy paths in production
- Backend: Jaeger (self-hosted) or Honeycomb (SaaS)

**What V0 provides today:**
- `logging` at each pipeline step (download, load, transform)
- Structured audit records in `common/audit.py`
- Row count logging after each DuckDB insert — visibility into silent data loss risk from `ignore_errors=true`

---

## Multi-Tenancy Design (V2)

**Problem:** V0 is single-tenant (one DuckDB file, one schema). V2 must support multiple payers or research organizations with isolated data.

**Approach: schema-per-tenant isolation**

Each tenant gets a dedicated Postgres schema: `CREATE SCHEMA tenant_{id}`. All tables live under the tenant schema (`tenant_abc.fact_inpatient`, etc.). The API extracts tenant ID from the JWT `org_id` claim; a FastAPI dependency sets `SET search_path = tenant_{id}` at connection time.

Kafka topics extend the single-tenant naming convention from the [Kafka Streaming Design](#kafka-streaming-design-v2) section (`cms.inpatient`, etc.) by prepending a tenant segment: `cms.{tenant_id}.inpatient`. Single-tenant V2 deployments use the short form; multi-tenant deployments use the prefixed form. The consumer group convention follows: `analytics-loader-{tenant_id}`. Topic ACLs enforce that a tenant's service account can only produce/consume its own topic prefix.

**Why schema-per-tenant over row-level security (RLS):**

RLS adds predicate overhead on every query; at V2 analytical query volumes this degrades P99 latency. Schema isolation allows tenant-specific vacuuming, index strategies, and backup scheduling. It also simplifies the audit trail — no risk of a misconfigured RLS policy leaking cross-tenant data. Tradeoff: schema proliferation at >1,000 tenants. Mitigation: pool small tenants into a shared schema + RLS tier; reserve dedicated schemas for enterprise accounts.

**Tenant onboarding steps:**
1. `CREATE SCHEMA tenant_{id}` + run DDL migrations under the new schema
2. Provision Kafka topics with topic-level ACLs scoped to the tenant's service account
3. Issue a JWT signing key with `org_id` claim bound to the tenant
4. Bootstrap historical data via the V0 batch ingest pipeline (same code, different schema target)

---

## Schema Evolution (V2)

**Problem:** Synthea releases new data dictionary versions. SNOMED-CT code set updates. New CSV fields. The raw schema must evolve without breaking downstream consumers.

**Strategy: schema registry + migration-as-code**

Kafka messages use Avro schemas registered with a Confluent Schema Registry. Producers register new schema versions; consumers specify compatibility level (`BACKWARD` or `FULL`). SQL DDL migrations are managed by `alembic`; migration files live in `sql/migrations/` and are applied by CI in staging before prod.

**Backward compatibility rule:** new nullable columns only — no column renames or type changes. Breaking changes require a three-step migration: (1) add the new column, (2) dual-write old and new, (3) remove the old column across three separate releases.

**V0 → V2 star schema migration:**
1. Export DuckDB star schema to Parquet, partitioned by `claim_year`
2. Load into Postgres via `COPY FROM` or `pg_parquet`
3. Verify row counts; diff the 5 analytical query results between DuckDB and Postgres
4. Swap `common/db.py::get_connection()` to return a Postgres connection pool

**V0 data dictionary version management:**

The `_PATIENT_COLS`, `_ENCOUNTER_COLS`, etc. column lists in `ingest/load.py` are the schema version pins. When Synthea releases a new CSV layout, add a new versioned column list (do not modify existing lists in-place). The loader selects the list based on a version argument. This ensures historical re-runs use the original schema.

---

## Operational Runbooks

**Runbook 1: DuckDB corrupt or missing (V0)**

Source of truth is the raw CSVs in `data/raw/`. Recovery:
1. Delete `data/processed/cms.duckdb`
2. Run `make ingest` — download step skips existing zips, load step re-creates DuckDB
3. RTO: ~20 min for a small Synthea sample; ~6 hours for a full 2.3M-patient Synthea run on a standard laptop

**Runbook 2: Kafka consumer lag spike (V2)**

1. Check lag: `kafka-consumer-groups.sh --describe --group analytics-loader`
2. If lag > 10 min: scale consumer pods — `kubectl scale deployment analytics-loader --replicas=N`
3. If lag is caused by a bad message (deserialization failure): identify via dead-letter topic `cms.{topic}.dlq`, fix the schema, replay from saved offset
4. Never reset consumer offsets without recording the reset in the PHI audit log

**Runbook 3: PHI data subject request (V0 + V2)**

1. Receive request with `beneficiary_id` and requestor identity
2. Query `common/audit.py` logs for all access records for that beneficiary
3. Export masked record (`phi_read=False`) unless requestor holds `PHI_READ` JWT claim
4. Log the disclosure event via `log_access(action="disclosure", ...)`
5. Retain the disclosure log for 7 years per HIPAA §164.530(j)

**Runbook 4: Failed CI pipeline**

1. `quality` job fails → fix ruff/mypy errors locally before re-pushing; never suppress with `# noqa` unless the lint rule is genuinely inapplicable
2. `test` job fails → run `.venv/bin/pytest tests/ -v` locally; CI test matrix is the contract
3. `docker` job fails → run `docker build .` locally; check for missing deps in `pyproject.toml`

---

## Implementation-Level Design Decisions

Decisions made deliberately at the code level — not V0/V2 infrastructure
choices, but specific implementation trade-offs within V0 itself. These are
"this is the right call for the demo" decisions, not oversights.

| Decision | What we did | Why | What changes at V2 |
|----------|-------------|-----|--------------------|
| **Per-request DB connection** | `deps.py` opens and closes a DuckDB connection per HTTP request | DuckDB is embedded; a connection is cheap and the V0 API is single-node, single-writer. A connection pool would add complexity with no throughput benefit at demo scale. | Replace with `asyncpg` connection pool when moving to Postgres. The swap point is `common/db.py::get_connection()`. |
| **`phi_read` query param** | `?phi_read=true` bypasses field masking | No JWT infrastructure in V0; a query param is sufficient to demonstrate the bypass surface and the masking logic. Acknowledged insecure — see `TODO(future-auth)` in `patient.py`. | Replace with a JWT `PHI_READ` scope claim validated in a FastAPI dependency. |
| **`ignore_errors=true` in CSV load** | DuckDB `read_csv` silently skips malformed rows | Synthea CSVs are clean in practice. Failing the entire ingest on a single bad row is the wrong failure mode for a batch loader; silent loss is visible via row-count logging. | Add a dead-letter table (`raw_rejected`) to capture and count rejected rows explicitly. |
| **LogisticRegression over LightGBM** | Sklearn `LogisticRegression` in `scoring/risk_model.py` | Logistic regression is deterministic, interpretable, and correct at 1,000-patient scale. LightGBM would not improve signal on synthetic data at this volume — adding it now optimises the wrong thing. | Swap to LightGBM when data volume and feature engineering justify the complexity. The `RiskModel` dataclass and `train_risk_model` / `predict_risk` interface are the swap points. |
| **Rank-based labels, no train/test split** | Top-25% by cost → label=1; entire dataset is both train and test | With ~1,000 synthetic patients a held-out test set would be too small to be statistically meaningful, and the goal is demonstrating the pipeline, not maximising AUC. See the synthetic-data caveat in `risk_model.py`. | Add stratified train/test split and cross-validation when real data with meaningful volume is available. |
| **`ROW_NUMBER()` for surrogate keys** | `transforms.py` assigns `MAX(key) + ROW_NUMBER()` for all dim/fact inserts | DuckDB is single-writer at V0 — there are no concurrent inserts, so sequence generation via `ROW_NUMBER()` is safe and avoids a sequence object. | Replace with a proper sequence (`CREATE SEQUENCE`) or identity column when moving to Postgres with concurrent writers. |

---

## V2 Cost Model

Concrete sizing for a 20-subsample deployment (~2.3M beneficiaries, ~500M claim records).

**Storage:**

| Layer | Size estimate | Monthly cost (AWS us-east-1, 2025 pricing) |
|-------|--------------|---------------------------------------------|
| Raw CSVs (S3 Standard) | ~80 GB (20 samples × ~4 GB) | ~$1.84 |
| DuckDB file (EBS gp3) | ~15 GB processed | ~$1.20 |
| Postgres (RDS db.r6g.xlarge, Multi-AZ) | ~50 GB | ~$700 |
| Kafka (MSK 3-broker m5.large) | 72 h log retention | ~$460 |

**Compute:**

| Service | Sizing | Monthly cost |
|---------|--------|-------------|
| FastAPI (ECS Fargate, 2 vCPU / 4 GB × 2 replicas) | 730 hrs | ~$160 |
| Analytics loader (ECS 2 vCPU × 2 consumers) | 730 hrs | ~$160 |
| Risk scorer (ECS 4 vCPU / 8 GB × 1 pod) | on-demand bursts | ~$70 |

**Total V2 estimate:** ~$1,550/month on-demand (AWS us-east-1, 2025 list pricing). Reserved instances (1-year, no upfront) reduce compute ~30%, bringing the steady-state estimate to ~$1,100/month.

**V0 cost:** $0 — runs on a developer laptop.

**Migration trigger:** move to V2 when (a) cohort query latency exceeds 5 seconds for common workloads, or (b) a second concurrent writer is required. At V0 with subsample 1, DuckDB query time is under 1 second. The decision rule is data-driven, not speculative.
