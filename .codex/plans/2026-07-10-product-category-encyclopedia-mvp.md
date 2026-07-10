# Product Category Encyclopedia MVP Technical Design

## Design Summary

Build an internal web application for a structured product-category encyclopedia using FastAPI, MySQL 8.0, and Vue 3 with TypeScript. The web application is the only system of record. Feishu is a one-way publishing, notification, reading, commenting, and sharing surface.

The MVP uses structured filtering and MySQL full-text search. It does not deploy a vector database and does not use Obsidian as runtime storage. AI generation is limited to producing a validated draft from explicitly selected source records. The default development provider is deterministic and local; a model provider can be connected later without changing the domain workflow.

## Existing Context

- The Git repository is empty and has no existing stack or conventions.
- Confirmed backend stack: Python, FastAPI, MySQL 8.0.
- Confirmed frontend stack: Vue 3, TypeScript, Vite, Element Plus.
- Confirmed deployment baseline: Docker Compose.
- Confirmed category scope: Heat Therapy with Far Infrared Heat Therapy and Shoulder/Neck Heat Therapy child categories.
- Confirmed content workflow: data preparation, draft generation, human editing, review, publication, and later refresh.
- Confirmed collaboration boundary: the web app owns all editable content; Feishu receives published snapshots only.
- Existing Amazon data contains duplicate human-readable and category-code folders. Imports must be idempotent by marketplace, ASIN, and scraped timestamp.
- No Feishu application credentials or production LLM credentials are required for the local MVP.

## Proposed Changes

| Area | Change | Files/modules |
| --- | --- | --- |
| Repository | Create a backend/frontend monorepo with Docker Compose | `backend/`, `frontend/`, `docker-compose.yml` |
| Backend | FastAPI application with explicit API, service, repository, and integration layers | `backend/app/` |
| Database | MySQL schema and Alembic migrations | `backend/alembic/`, `backend/app/models/` |
| Import | Import Amazon Listing JSON directories with validation, deduplication, and job reporting | `backend/app/services/import_service.py` |
| Encyclopedia | Category hierarchy, content sections, evidence, versions, and workflow states | `backend/app/services/encyclopedia_service.py` |
| Drafts | Deterministic local draft provider behind a typed provider interface | `backend/app/services/draft_service.py` |
| Publishing | Feishu publisher interface, local preview publisher, and future real adapter boundary | `backend/app/integrations/feishu.py` |
| Frontend | Operational UI for category browsing, imports, editing, evidence, review, and publish preview | `frontend/src/` |
| Tests | Service and API tests using an isolated test database contract | `backend/tests/` |
| Docs | Setup, environment variables, commands, and architecture notes | `README.md`, `.env.example` |

## Architecture

```text
Vue 3 SPA
   |
   | JSON/HTTP
   v
FastAPI
   |-- category and encyclopedia services
   |-- import and evidence services
   |-- controlled draft provider
   |-- review and publication workflow
   |-- Feishu publisher port
   v
MySQL 8.0 (system of record)

External side effects:
FastAPI --explicit publish action--> Feishu publisher

Future optional path:
FastAPI --SearchProvider port--> Qdrant or another vector service
```

The application starts as one backend service and one frontend service. It does not add a queue, cache, vector database, object store, or separate AI service until measured requirements justify them.

## Contracts And Data

### Core entities

| Entity | Purpose | Important fields |
| --- | --- | --- |
| `categories` | Stable hierarchy and business boundaries | `id`, `code`, `name`, `parent_id`, `aliases`, `included_items`, `excluded_items`, `status` |
| `listing_snapshots` | Immutable marketplace snapshots | `marketplace`, `asin`, `category_id`, `scraped_at`, listing content fields, `raw_payload`, `content_hash` |
| `source_materials` | Documents, links, files, manual notes, or imported platform data | `type`, `title`, `url`, `published_at`, `collected_at`, `category_id`, `status` |
| `encyclopedia_sections` | Current editable section content | `category_id`, `section_key`, `content`, `generation_mode`, `locked_by_human`, `review_status` |
| `evidence_links` | Traceability from statements or sections to sources | `section_id`, `source_type`, `source_id`, `locator`, `support_type` |
| `encyclopedia_versions` | Immutable submitted or published snapshots | `category_id`, `version`, `status`, `content_snapshot`, `created_by`, `reviewed_by`, timestamps |
| `import_jobs` | Batch import audit and error summary | `status`, counts, `source_path`, `mapping`, `errors`, timestamps |
| `publication_records` | Feishu publication attempts and result | `category_id`, `version_id`, `provider`, `external_doc_id`, `status`, `error_code`, timestamps |
| `audit_events` | Bounded audit trail | `actor`, `action`, `entity_type`, `entity_id`, safe metadata, timestamp |

No embedding columns are created in the MVP. Future compatibility is provided through a `SearchProvider` interface and optional `source_chunks` migration only when semantic retrieval is approved.

### Idempotency and transactions

- Listing uniqueness: `(marketplace, asin, scraped_at)`.
- Category uniqueness: stable `code`.
- Publication idempotency: `(provider, version_id)`; retry updates the same publication record.
- Importing one file is transactional. A malformed file fails without a partial listing row.
- A batch continues after individual file failures and records each safe error summary.
- Submitting for review creates an immutable version snapshot in the same transaction as the status change.
- Publishing is two phase: commit publication intent, call the provider with a timeout, then persist success or failure.

### Initial category seed

```text
HEAT_THERAPY
|-- FAR_INFRARED
`-- SHOULDER_NECK_HEAT_THERAPY
```

Directory aliases map to stable codes. Directory names never become primary identifiers.

### API surface

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/dashboard` | Counts, recent updates, pending reviews |
| `GET` | `/api/v1/categories` | Category tree and search |
| `GET` | `/api/v1/categories/{code}` | Category metadata and current sections |
| `PATCH` | `/api/v1/categories/{code}` | Edit boundary metadata |
| `GET` | `/api/v1/categories/{code}/listings` | Paginated listing snapshots and filters |
| `POST` | `/api/v1/imports/amazon` | Start a validated directory import |
| `GET` | `/api/v1/imports/{id}` | Import status and safe errors |
| `POST` | `/api/v1/source-materials` | Add a manual source, document, or link |
| `POST` | `/api/v1/categories/{code}/drafts` | Generate uncommitted structured draft suggestions |
| `PUT` | `/api/v1/categories/{code}/sections/{section_key}` | Save one edited section |
| `POST` | `/api/v1/categories/{code}/submit-review` | Create immutable review version |
| `POST` | `/api/v1/versions/{id}/review` | Approve or reject a version |
| `POST` | `/api/v1/versions/{id}/publish` | Explicit one-way publication |
| `GET` | `/api/v1/versions/{id}/publication-preview` | Review the generated Feishu snapshot locally |

All write requests require an actor and role in development mode. The production authentication port will later resolve these from Feishu SSO; arbitrary client-provided roles must not be accepted in production.

## Product Workflow And Side Effects

1. An administrator creates or selects a stable category.
2. Data staff import Amazon JSON directories. The import validates schema, maps directory aliases, and reports inserted, duplicate, and failed files.
3. A researcher adds internal or external source materials manually.
4. A user selects eligible sources and requests draft suggestions.
5. The draft provider returns a typed section map plus evidence references and missing-data notices.
6. The user chooses which suggestions to apply. Generated output never silently overwrites a human-locked section.
7. Submitting creates an immutable version for review.
8. A reviewer approves or rejects with a reason.
9. An explicit publish action renders the approved version and calls the configured Feishu publisher.
10. Publication failures do not roll back approved content. They remain retryable and auditable.

## AI Boundary

### MVP provider

The default provider is deterministic and local. It computes descriptive summaries from selected Listing fields and review-topic aggregates. It labels missing modules instead of inventing content. This enables a complete demo without credentials or hidden network calls.

### Future model provider

A future provider must:

- receive trusted instructions separately from untrusted source text;
- accept only server-selected source IDs, not arbitrary paths or URLs;
- return a validated structured schema keyed by allowed section names;
- include evidence references for every generated section;
- enforce request timeout and bounded retry;
- store provider name, model identifier, prompt version, and safe usage metadata;
- never directly write to the database or invoke Feishu publishing;
- never log full private source contents by default.

## Search Decision

MVP search uses:

- exact filters for category, marketplace, ASIN, brand, rating, price, and BSR;
- MySQL `FULLTEXT` indexes for English text;
- MySQL ngram full-text indexes where the runtime supports the approved CJK configuration;
- explicit fallbacks for short search strings and small datasets.

A vector database is added only after a semantic-search requirement and retrieval evaluation dataset are approved. MySQL remains the source of truth if Qdrant or another vector service is introduced.

## Security And Failure Handling

- Secrets are environment variables and are never committed.
- The import API accepts configured import roots only; it rejects arbitrary filesystem traversal.
- `.session`, cookies, browser-state files, hidden files, and non-Listing JSON are excluded.
- Raw upstream errors are not returned to users.
- Logs include request IDs, entity IDs, and safe counts, not credentials or complete private payloads.
- Development role headers are disabled when authentication mode is not `development`.
- Human approval is required before publication.
- Feishu calls use explicit timeouts, bounded retries, and idempotency keys.
- Medical claims remain marked as requiring human/compliance confirmation.

## Frontend Experience

- The first screen is the working application, not a marketing page.
- A restrained operational layout preserves business habits: category tree, document outline, searchable content, source panel, and visible workflow state.
- Main views: encyclopedia, data import, source materials, review queue, and publication history.
- Reading and editing are distinct modes.
- Draft suggestions show source counts, missing evidence, and apply controls.
- Empty, loading, import-progress, partial-failure, and publication-failure states are designed explicitly.
- Desktop is primary, with a usable responsive reading and review experience on mobile.

## Test Plan

### Backend

- Category hierarchy and alias mapping.
- Successful Listing import, duplicate import, malformed JSON, missing ASIN, and excluded session file.
- Transactional review version creation and invalid state transitions.
- Draft schema validation and protection of human-locked sections.
- Publication success, provider timeout, retry, and idempotency.
- Search and pagination with empty and populated data.
- Development role enforcement and production-header rejection.

### Frontend

- Category navigation and search.
- Listing import result display.
- Reading/editing mode transitions.
- Draft preview and selective apply.
- Review approval/rejection.
- Publication preview and failure feedback.
- Responsive layout at desktop and mobile widths.

### End-to-end MVP acceptance

1. Import the provided heat-therapy directories and show deduplicated results.
2. Generate a traceable local draft for both heat-therapy child categories.
3. Edit one section and prove regeneration cannot overwrite it silently.
4. Submit, approve, and create a local Feishu publication preview.
5. Find the published category through the category tree and keyword search.

## Implementation Steps

1. Scaffold backend, frontend, environment examples, Docker Compose, and documentation.
2. Implement MySQL models, Alembic migration, category seed, and repositories.
3. Implement Listing import, validation, directory alias mapping, and job reporting.
4. Implement encyclopedia sections, evidence, versions, and workflow transitions.
5. Implement deterministic draft provider and validated apply flow.
6. Implement local publisher and Feishu adapter interface.
7. Build the Vue operational interface.
8. Add focused backend and frontend tests.
9. Run Docker, import the heat-therapy sample, and verify desktop/mobile behavior.
10. Record remaining requirements for Feishu SSO, live publishing credentials, and production LLM provider.

## Deferred Decisions

- Production LLM provider and model.
- Feishu application credentials, folder ownership, and production SSO setup.
- Whether published Feishu documents are updated in place or versioned as separate documents.
- Object storage for uploaded binary files.
- Semantic retrieval provider and evaluation threshold.
- Production hosting topology, backups, monitoring, and disaster recovery.
