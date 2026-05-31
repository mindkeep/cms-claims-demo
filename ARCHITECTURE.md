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
- **Chunked CSV ingestion** in `ingest/load.py` mirrors the consumer model of a
  Kafka topic — the swap to streaming is a replacement of one module, not a
  rewrite of the analytical layer.
- **Subsample-list config** (`Settings.subsamples`) exists because V2 shards by
  `beneficiary_id_hash % N`. The config boundary is the sharding boundary.
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
| V0 | Batch CSV download + chunked load | Reproducible, testable, no infra |
| V1 | Batch + scheduled refresh | Adds daily/weekly pipeline trigger |
| V2 | Kafka streaming topics per claim type | Near-real-time ingestion, replay, backpressure |

**Migration path (V0→V2):** The chunked reader in `ingest/load.py` is replaced
by a Kafka consumer. One topic per claim type (inpatient, outpatient, carrier,
PDE, beneficiary). Consumer groups allow parallel ingestion across subsamples.
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
- Log levels: DEBUG in dev, INFO in staging, WARNING in prod. Never log raw PHI values — `desynpuf_id` appears in logs only in its masked form

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

Each tenant gets a dedicated Postgres schema: `CREATE SCHEMA tenant_{id}`. All tables live under the tenant schema (`tenant_abc.fact_inpatient`, etc.). The API extracts tenant ID from the JWT `org_id` claim; a FastAPI dependency sets `SET search_path = tenant_{id}` at connection time. Kafka topics are namespaced: `cms.{tenant_id}.inpatient`.

**Why schema-per-tenant over row-level security (RLS):**

RLS adds predicate overhead on every query; at V2 analytical query volumes this degrades P99 latency. Schema isolation allows tenant-specific vacuuming, index strategies, and backup scheduling. It also simplifies the audit trail — no risk of a misconfigured RLS policy leaking cross-tenant data. Tradeoff: schema proliferation at >1,000 tenants. Mitigation: pool small tenants into a shared schema + RLS tier; reserve dedicated schemas for enterprise accounts.

**Tenant onboarding steps:**
1. `CREATE SCHEMA tenant_{id}` + run DDL migrations under the new schema
2. Provision Kafka topics with topic-level ACLs scoped to the tenant's service account
3. Issue a JWT signing key with `org_id` claim bound to the tenant
4. Bootstrap historical data via the V0 batch ingest pipeline (same code, different schema target)

---

## Schema Evolution (V2)

**Problem:** CMS releases new data dictionary versions. ICD-9 → ICD-10 transition. New claim fields. The raw schema must evolve without breaking downstream consumers.

**Strategy: schema registry + migration-as-code**

Kafka messages use Avro schemas registered with a Confluent Schema Registry. Producers register new schema versions; consumers specify compatibility level (`BACKWARD` or `FULL`). SQL DDL migrations are managed by `alembic`; migration files live in `sql/migrations/` and are applied by CI in staging before prod.

**Backward compatibility rule:** new nullable columns only — no column renames or type changes. Breaking changes require a three-step migration: (1) add the new column, (2) dual-write old and new, (3) remove the old column across three separate releases.

**V0 → V2 star schema migration:**
1. Export DuckDB star schema to Parquet, partitioned by `claim_year`
2. Load into Postgres via `COPY FROM` or `pg_parquet`
3. Verify row counts; diff the 5 analytical query results between DuckDB and Postgres
4. Swap `common/db.py::get_connection()` to return a Postgres connection pool

**V0 data dictionary version management:**

The `_BENE_COLS`, `_INPATIENT_COLS`, etc. column lists in `ingest/load.py` are the schema version pins. When CMS releases a new dictionary version, add a new versioned column list (do not modify existing lists in-place). The loader selects the list based on a version argument. This ensures historical re-runs use the original schema.

---

## Operational Runbooks

**Runbook 1: DuckDB corrupt or missing (V0)**

Source of truth is the raw CSVs in `data/raw/`. Recovery:
1. Delete `data/processed/cms.duckdb`
2. Run `make ingest` — download step skips existing zips, load step re-creates DuckDB
3. RTO: ~20 min for subsample 1; ~6 hours for all 20 subsamples on a standard laptop

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

## V2 Cost Model

Concrete sizing for a 20-subsample deployment (~2.3M beneficiaries, ~500M claim records).

**Storage:**

| Layer | Size estimate | Monthly cost (AWS us-east-1, 2025 pricing) |
|-------|--------------|---------------------------------------------|
| Raw CSVs (S3 Standard) | ~80 GB (20 samples × ~4 GB) | ~$1.84 |
| DuckDB file (EBS gp3) | ~15 GB processed | ~$1.20 |
| Postgres (RDS db.r6g.xlarge, Multi-AZ) | ~50 GB | ~$400 |
| Kafka (MSK 3-broker m5.large) | 72 h log retention | ~$600 |

**Compute:**

| Service | Sizing | Monthly cost |
|---------|--------|-------------|
| FastAPI (ECS Fargate, 2 vCPU / 4 GB × 2 replicas) | 730 hrs | ~$120 |
| Analytics loader (ECS 2 vCPU × 2 consumers) | 730 hrs | ~$120 |
| Risk scorer (ECS 4 vCPU / 8 GB × 1 pod) | on-demand bursts | ~$60 |

**Total V2 estimate:** ~$1,300/month for a full 20-subsample production deployment.

**V0 cost:** $0 — runs on a developer laptop.

**Migration trigger:** move to V2 when (a) cohort query latency exceeds 5 seconds for common workloads, or (b) a second concurrent writer is required. At V0 with subsample 1, DuckDB query time is under 1 second. The decision rule is data-driven, not speculative.
