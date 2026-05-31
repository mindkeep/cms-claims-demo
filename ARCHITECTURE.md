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
