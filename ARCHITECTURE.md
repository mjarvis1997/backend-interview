# Architecture Overview

> This document covers the architecture of the Feathr distributed event processing platform. Sections not applicable to a backend-only service (Frontend, External Integrations) are noted as excluded.

---

## 1. Project Structure

```
feathr-backend/
├── compose.yaml                  # Docker Compose for all services
├── ARCHITECTURE.md               # This document
├── README.md                     # High-level overview, setup instructions, and AI workflow section
└── server/
    ├── Dockerfile
    ├── pyproject.toml
    └── app/
        ├── main.py               # FastAPI app entry point, lifespan, router registration
        ├── models/
        │   └── event.py          # Beanie document model + MongoDB index definitions
        ├── routers/
        │   └── events/
        │       ├── crud.py       # GET /events, POST /events, DELETE /events
        │       ├── stats.py      # GET /events/stats, GET /events/stats/realtime
        │       └── search.py     # GET /events/search
        ├── dependencies/
        │   ├── database.py       # MongoDB/Beanie initialization (shared by API + workers)
        │   ├── redis.py          # Redis connection pools + cache key generation
        │   ├── rq.py             # RQ queue setup and worker job functions
        │   └── elasticsearch.py  # ES client, index mapping, initialization
        └── helpers/
            └── date.py           # ISO 8601 parsing utility
        └── sample-requests       # Sample payloads/queries for easy testing
        └── tests
            ├── unit/             # Unit tests for individual functions and components
            └── integration/      # Integration tests covering end-to-end request lifecycles

```

---

## 2. High-Level System Diagram

```
                          ┌─────────────────────────────────┐
                          │            Client               │
                          └────────────────┬────────────────┘
                                           │ HTTP
                          ┌────────────────▼────────────────┐
                          │          FastAPI (API)           │
                          │   crud / stats / search routers  │
                          └───┬────────────┬────────────────┘
                              │            │
               enqueue job    │       read / aggregate / search
                              │            │
             ┌────────────────▼──┐         │
             │   Redis (DB 0)    │         │
             │   RQ job queue    │         │
             └────────┬──────────┘         │
                      │ consume            │
             ┌────────▼──────────┐         │
             │   RQ Workers x10  │         │
             │   ingest_event()  │         │
             └────┬──────────────┘         │
                  │ write   │ index        │
           ┌──────▼──┐  ┌───▼───────────┐  │
           │ MongoDB │  │ Elasticsearch │◄─┤ search
           └─────────┘  └───────────────┘  │
                                            │
             ┌──────────────────────┐       │
             │   Redis (DB 1)       │◄──────┘ stats/realtime (cache)
             │   Stats result cache │
             └──────────────────────┘
```

**Ingestion:** `POST /events` → enqueue → worker → MongoDB + Elasticsearch

**Querying:** `GET /events`, `GET /events/stats` → MongoDB directly

**Search:** `GET /events/search` → Elasticsearch

**Cached stats:** `GET /events/stats/realtime` → Redis → MongoDB (on miss)

---

## 3. Core Components

### 3.1. Event API

**Description:** FastAPI application that validates incoming events, enqueues them for async processing, and serves query, aggregation, and search endpoints.

**Technologies:** Python, FastAPI, Beanie ODM, Pydantic

**Deployment:** Docker container (`api` service), port 8000

### 3.2. Ingestion Workers

**Description:** RQ worker processes that consume jobs from the Redis queue, write events to MongoDB, and index them in Elasticsearch. Scaled via Docker Compose replicas. Retries failed jobs with exponential backoff. There is a simple DLQ that comes implicitly with the RQ implementation.

**Technologies:** Python, RQ, AsyncElasticsearch, Beanie

**Deployment:** Docker container (`workers` service), 10 replicas by default

---

## 4. Data Stores

### 4.1. MongoDB

**Type:** Document database

**Purpose:** Primary source of truth for all event data. Handles structured filtering, sorting, and time-bucketed aggregation via aggregation pipelines.

**Key Collections:** `events`

**Indexes:**
- `(type ASC, timestamp DESC)` — stats aggregation and type filtering
- `(user_id ASC, timestamp DESC)` — user-scoped queries
- `(source_url ASC, timestamp DESC)` — URL-scoped queries

**Indexing Rationale:** 
Focus on indexing the fields that are most commonly used for filtering and aggregation in the endpoints. I also thought about what a frontend user would want to filter or group by when looking at event data.
I suspect most use cases would involve filtering by a specific time range, so I created compound indexes that include the timestamp along with other commonly filtered fields. In terms of directionality, I set the timestamp to be descending in the indexes since most queries will likely be looking for recent events.

While it is tempting to index all fields for optimal reads, this is a slippery slope. Each index adds overhead to writes and in this context the MongoDB's main purpose is to quickly ingest events - the more complicated filtering and searching should be offloaded to Elasticsearch.

### 4.2. Elasticsearch

**Type:** Search index

**Purpose:** Full-text search over flexible event metadata fields. Not a source of truth — can be rebuilt from MongoDB if needed.

**Key Index:** `events`

**Field mapping:**

| Field | Type | Rationale |
|---|---|---|
| `type`, `user_id`, `source_url` | `keyword` | Identifiers — exact match only, tokenizing is meaningless |
| `timestamp` | `date` | Range queries and sorting |
| `metadata` | `object` (dynamic) | Flexible payload — ES infers sub-field types, all sub-fields full-text indexed |

### 4.3. Redis

**Type:** In-memory store

**Purpose (DB 0):** RQ job queue — holds serialized event payloads pending worker consumption. Provides at-least-once delivery.

**Purpose (DB 1):** Result cache for `/events/stats/realtime`. Fixed cache key with configurable TTL (`REALTIME_STATS_CACHE_TTL_MINUTES`, default 60 min). Time-based expiration only; no event-driven invalidation.

---

## 5. External Integrations / APIs

> *Excluded — this service has no third-party API dependencies.*

---

## 6. Deployment & Infrastructure

**Cloud Provider:** Local / Docker (no cloud provider in current implementation)

**Key Services:**
- `api` — FastAPI server (profile: `prod`)
- `workers` — RQ workers, 10 replicas
- `mongo` — MongoDB 8.x
- `redis` — Redis 8.x Alpine, 256MB max memory, LRU eviction
- `elasticsearch` — Elasticsearch 9.3.1, single-node, 2GB memory limit
- `mongo-express` — MongoDB UI at `:8081`
- `rq-dashboard` — RQ job monitor at `:9181`

**CI/CD Pipeline:** Not implemented — in a production environment, I would set up automated testing and deployment via GitHub Actions or similar.

**Monitoring & Logging:** RQ Dashboard for queue visibility; no structured logging or metrics in current implementation. In production: structured JSON logs, Prometheus + Grafana for queue depth and latency.

---

## 7. Security Considerations

> *Current implementation is a proof of concept — the following gaps are acknowledged.*

**Authentication:** None.

**Authorization:** None.

**Secrets Management:** Credentials are hardcoded in `compose.yaml` environment variables. In production these would be stored in a secrets manager (AWS Secrets Manager, Vault) and injected at runtime.

**Encryption:** Elasticsearch security (`xpack.security`) is disabled for local development. MongoDB has no TLS. Neither would be acceptable in production.

---

## 8. Development & Testing Environment

**Local Setup:** See `server/README.md` — run infrastructure via Docker Compose, run the FastAPI server directly with `poetry run uvicorn`.

**Testing Frameworks:** pytest (unit + integration), `server/tests/simple_load_test.py` for load testing

**Code Quality Tools:** pylint, autopep8 (configured in `pyproject.toml`)

---

## 9. Future Considerations

- **Event deduplication** — no deduplication logic currently. A worker crash after MongoDB write but before ES index leaves stores out of sync. A content hash key on `(user_id, timestamp, type)` would prevent duplicates on retry.
- **Cache invalidation** — current TTL-based invalidation is blunt.
- **Optimize docker images** — currently the same image is used for API and workers, which includes unnecessary dependencies for each.
- **Support multiple environments** — local, staging, production configs with appropriate secrets management and access controls.
- **MongoDB connection-per-worker** — each worker opens its own connection, pooling would be more efficient.
- **Bulk Elasticsearch indexing** — current implementation indexes one document per job.
- **Observability** — structured production logging and performance monitoring.

---

## 10. Project Identification

**Project Name:** Feathr — Distributed Event Processing Platform

**Repository:** Private (take-home submission)

**Author:** Michael Jarvis

**Date of Last Update:** 2026-02-28

---

## 11. Glossary

| Term | Definition |
|---|---|
| **RQ** | Redis Queue — Python library for background job processing backed by Redis |
| **Beanie** | Async Python ODM for MongoDB built on Motor and Pydantic |
| **TTL** | Time To Live — duration before a cached entry expires |
| **DLQ** | Dead Letter Queue — a queue for messages that have exhausted retries |
| **ODM** | Object Document Mapper — analogous to ORM but for document databases |
| **Aggregation pipeline** | MongoDB's framework for multi-stage data transformation and analytics queries |

