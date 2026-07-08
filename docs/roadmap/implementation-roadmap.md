# AI Business Operating System — Implementation Roadmap

**Document type:** Engineering delivery plan
**Companion to:** `ai-bos-architecture.md`
**Version:** 1.0

---

## Roadmap Philosophy

The plan below decomposes the platform into **9 phases and 30 sprints**. Sprints are two calendar weeks each. The dependency chain is designed so that:

- **Every sprint can be built by a single team in isolation** once its dependencies land.
- **Multiple sprints in the same phase can run in parallel** by different squads, and the roadmap flags which pairs are safe to overlap.
- **Business modules are cookie-cutter** by sprint 8 — they reuse core primitives (auth, tenancy, RBAC, audit, events, storage, notifications, search) and follow the same folder/domain template. This is why 6 modules ship across sprints 9–14 rather than one big monolith sprint.
- **The AI layer lands after the business modules** because Copilot needs real domain data and tools to be useful. Ordering AI-first would produce a plausible-but-empty demo.

Sprint scope is sized around a **6-engineer squad** (2 backend, 2 frontend, 1 platform/SRE, 1 QA) plus embedded design and product. Larger orgs can parallelize; smaller teams stretch a sprint into 3 weeks without changing scope.

### Phase summary

| Phase | Sprints | Weeks | Theme | Parallelizable |
|---|---|---|---|---|
| 0. Foundation | 0–2 | 6 | Repo, infra, observability | Sequential |
| 1. Platform Core | 3–6 | 8 | Auth, tenancy, RBAC, audit, events, storage | 5 and 6 in parallel |
| 2. Web Shell + Admin | 7–8 | 4 | Design system, admin console | 7 and 8 in parallel |
| 3. Business Module MVPs | 9–14 | 12 | CRM, Finance, Projects, HR, Inventory, Support | Up to 3 in parallel |
| 4. AI Layer | 15–19 | 10 | Orchestrator, prompts, RAG, Copilot, streaming | 16 and 17 in parallel |
| 5. Automation | 20–22 | 6 | Workflow engine, builder UI, integrations | 21 and 22 in parallel |
| 6. Analytics | 23–24 | 4 | CDC → ClickHouse, report builder | Sequential |
| 7. Mobile + Public API | 25–26 | 4 | Mobile app, developer platform | 25 and 26 in parallel |
| 8. Hardening + Launch | 27–29 | 6 | Security, performance, GA | Sequential |

**Total: 60 weeks (14 months) end-to-end, ~10 months with maximum parallelization.**

### Sprint template (used below)

Every sprint documents: **Objective · Deliverables · Dependencies · Files to create · Backend modules · Frontend modules · Database tables · APIs · Validation checklist · Exit criteria**.

---

# PHASE 0 — Foundation

Goal: land the ground truth (repo, environments, observability) that every subsequent sprint depends on.

## Sprint 0 — Monorepo & Tooling

**Objective:** Establish the monorepo, coding standards, and CI/CD skeleton so that all downstream sprints have a consistent surface to build on.

**Deliverables**
- Turborepo + pnpm workspace for TS packages; uv (or Poetry) per Python service.
- Pre-commit hooks: ruff, black, mypy, eslint, prettier, biome check, commitlint.
- Base Docker images (`python-runtime`, `node-runtime`, `nginx-static`) with vulnerability scanning.
- GitHub Actions skeleton: lint, unit, build, container publish, SBOM (Syft), secret scan (Gitleaks), Trivy image scan.
- Branch protection: 2 reviewers, required checks, linear history, signed commits.
- ADR template and initial ADRs.
- README with 15-minute onboarding path.

**Dependencies:** None.

**Files to create**
- `/pnpm-workspace.yaml`, `/turbo.json`, `/package.json`
- `/services/api/pyproject.toml`, `/services/ai-orchestrator/pyproject.toml`, `/services/workflow-engine/pyproject.toml`, `/services/workers/pyproject.toml`, `/services/realtime/pyproject.toml`, `/services/analytics/pyproject.toml`
- `/.pre-commit-config.yaml`
- `/.github/workflows/ci.yml`, `/release.yml`, `/security.yml`
- `/docs/CONTRIBUTING.md`, `/docs/SECURITY.md`, `/docs/adr/0000-template.md`, `/0001-modular-monolith.md`, `/0002-python-fastapi.md`, `/0003-pgvector-first.md`
- `/docker/base/{python,node,nginx}/Dockerfile`

**Backend modules:** none yet.
**Frontend modules:** empty scaffolds for `apps/web`, `apps/admin`, `packages/design-system`.
**Database tables:** none.
**APIs:** none.

**Validation checklist**
- CI green on empty PR under 8 minutes.
- Pre-commit and CI produce identical results.
- SBOM generated for every image.
- Secret scan blocks a test PR with a fake key.
- New engineer follows README to `pnpm dev` + `make dev-api` in ≤ 15 minutes.

**Exit criteria:** All future sprints start from a working `main` build with a green CI pipeline and a documented local dev loop.

---

## Sprint 1 — Cloud & Data Provisioning

**Objective:** Provision baseline infrastructure for `dev` and `staging` using Terraform, with GitOps delivery via Argo CD.

**Deliverables**
- Terraform modules for VPC, EKS/GKE, RDS PostgreSQL 16, ElastiCache Redis 7, S3 buckets, KMS keys, IAM roles (IRSA), Route 53/Cloud DNS.
- Two environments up: `dev`, `staging`. Separate cloud accounts.
- Argo CD installed with app-of-apps pattern.
- External Secrets Operator + Vault (or AWS Secrets Manager) integration.
- cert-manager, ingress-nginx, metrics-server.
- Base Helm chart `platform-base` (namespaces, quotas, network policies, PodSecurity).
- Bastion / SSO access documented.

**Dependencies:** Sprint 0.

**Files to create**
- `/infra/terraform/modules/{network,eks,rds,elasticache,s3,kms,iam,dns}/`
- `/infra/terraform/envs/dev/main.tf`, `/staging/main.tf`
- `/infra/helm/charts/platform-base/`
- `/infra/k8s/argo-cd/{root-app.yaml,apps/}`
- `/ops/runbooks/env-bootstrap.md`, `/ops/runbooks/db-restore.md`
- `/docs/adr/0004-managed-postgres.md`

**Backend modules:** none.
**Frontend modules:** none.
**Database tables:** empty databases `ai_bos_dev`, `ai_bos_staging` created.
**APIs:** none.

**Validation checklist**
- `terraform plan` clean twice in a row.
- Argo CD sync green for `platform-base`.
- TLS cert issued to `*.dev.aibos.internal`.
- Test pod can reach RDS and Redis using IRSA (no static creds).
- Point-in-time restore tested from a snapshot to a scratch instance.

**Exit criteria:** A trivial "hello-world" service can be deployed to both environments via a PR to `main`, in under 20 minutes, without a human touching a cloud console.

---

## Sprint 2 — Observability Foundation

**Objective:** Deploy logs, metrics, traces, and error tracking before any real code lands, so every subsequent service ships instrumented.

**Deliverables**
- OpenTelemetry Collector (agent + gateway).
- Prometheus + Grafana (via kube-prometheus-stack).
- Loki + Promtail.
- Tempo + tail-based sampling policy.
- Sentry (self-hosted or SaaS) with source-map upload in CI.
- PagerDuty integration for alerts.
- Shared instrumentation libraries: `@aibos/observability` (TS) and `aibos.observability` (Python) exposing tracer, meter, logger, request middleware.
- Base dashboards: cluster health, HTTP service RED, worker queue depth, DB health.
- Base alerts: node pressure, DB CPU / replication lag, cert expiry.
- Synthetics scaffold (k6 in Argo Workflows) for future canary probes.

**Dependencies:** Sprint 1.

**Files to create**
- `/infra/helm/charts/observability/` (umbrella chart)
- `/ops/dashboards/{cluster,http-service,worker,postgres,redis}.json`
- `/ops/alerts/{platform,slo}.yaml`
- `/packages/observability/src/{tracer,logger,metrics,http-middleware,celery-instr}.ts` (+ Python mirror)
- `/docs/adr/0005-otel-first.md`
- `/docs/observability/instrumentation-standard.md`

**Backend modules:** shared observability lib (skeleton, no domain code).
**Frontend modules:** web + admin instrumented for Sentry.
**Database tables:** none.
**APIs:** none.

**Validation checklist**
- A dummy service emits logs to Loki, metrics to Prometheus, and traces to Tempo, correlated by `trace_id`.
- Synthetic alert paged to PagerDuty and resolved.
- Sentry captures a thrown exception from web with correct release + tenant tag placeholder.
- Log redaction middleware strips `password`, `token`, `secret`, `authorization`, `card_number`.

**Exit criteria:** No service is allowed to merge going forward unless it uses the shared instrumentation lib and ships a dashboard entry — enforced by CI linter.

---

# PHASE 1 — Platform Core

Goal: build the shared kernel that every business module and AI feature depends on.

## Sprint 3 — Auth Service

**Objective:** Deliver OIDC-based authentication with JWT tokens, MFA, session management, and audit-ready login events.

**Deliverables**
- Keycloak (or Auth0) tenant configured with per-realm settings.
- API auth middleware: JWKS-backed JWT validation, kid rotation, clock skew handling.
- OIDC Authorization Code + PKCE flow end-to-end.
- MFA: TOTP enrollment/verify; WebAuthn stub.
- Password policy, breached-password check (HIBP k-anonymity).
- Session store in Redis with sliding TTL; device fingerprinting; concurrent session limits.
- Refresh token rotation with reuse detection.
- Login pages, MFA challenge, session management UI.

**Dependencies:** Sprint 1, 2.

**Files to create**
- `/services/api/src/core/auth/{middleware.py, routes.py, services.py, models.py, schemas.py, mfa.py, tokens.py, password.py}`
- `/services/api/src/core/auth/jwks.py`
- `/services/api/migrations/versions/0001_auth.py`
- `/apps/web/app/(auth)/{login,register,mfa,forgot-password,reset-password}/page.tsx`
- `/apps/web/lib/{auth-client.ts, session.ts}`
- `/docs/adr/0006-oidc-pkce.md`

**Backend modules:** `core/auth`.
**Frontend modules:** web auth pages, auth store, HTTP client with auth interceptor and silent refresh.

**Database tables**
- `users(id, email, hashed_password, mfa_secret, mfa_enrolled_at, status, locale, timezone, created_at, updated_at)`
- `sessions(id, user_id, device, user_agent, ip, last_seen_at, expires_at, revoked_at)`
- `refresh_tokens(id, session_id, token_hash, rotated_from_id, expires_at, revoked_at, reuse_detected_at)`
- `login_attempts(id, email, ip, succeeded, reason, created_at)`
- `password_resets(id, user_id, token_hash, expires_at, used_at)`
- `webauthn_credentials(id, user_id, credential_id, public_key, sign_count, created_at)`

**APIs**
- `POST /v1/auth/login`
- `POST /v1/auth/callback`
- `POST /v1/auth/refresh`
- `POST /v1/auth/logout`
- `POST /v1/auth/mfa/enroll`, `POST /v1/auth/mfa/verify`, `DELETE /v1/auth/mfa`
- `POST /v1/auth/password/reset-request`, `POST /v1/auth/password/reset-confirm`
- `GET /v1/auth/sessions`, `DELETE /v1/auth/sessions/{id}`
- `GET /v1/auth/me`

**Validation checklist**
- JWT verification unit tests: expired, wrong `aud`, wrong `iss`, `kid` rotation, malformed.
- Brute-force lockout after 5 failures per IP-user pair.
- Refresh token reuse revokes the session tree.
- MFA required for `admin` and `owner` roles.
- Audit events emitted: `auth.login_succeeded`, `auth.login_failed`, `auth.mfa_verified`, `auth.session_revoked`.
- OWASP ASVS Level 2 relevant checks pass.

**Exit criteria:** A user completes registration (via invite), login, MFA enroll/challenge, and logout on web. Session revocation propagates within 30 seconds across pods.

---

## Sprint 4 — Tenancy, RBAC, Policy Engine

**Objective:** Enforce tenant boundaries and role-based access on every request. Any future endpoint added without a permission check must fail CI.

**Deliverables**
- Tenant lifecycle: `trial → active → past_due → suspended → offboarded`.
- Tenant context middleware: resolves `tenant_id` from JWT + subdomain; sets Postgres GUC `app.tenant_id`; injects into logs/traces.
- Row-level security bootstrapped on every tenant-scoped table (policy templates).
- Roles & permissions catalog with 5 default roles: `owner, admin, manager, member, guest`.
- Per-tenant custom roles with UI.
- Policy engine (OPA sidecar or Casbin embedded) for ABAC conditions.
- `require(permission, scope)` FastAPI dependency; CI lint rule that every router must call it.
- Organization hierarchy: `organizations → departments → teams`.
- Invitation flow (invite → accept → assign role).

**Dependencies:** Sprint 3.

**Files to create**
- `/services/api/src/core/tenancy/{middleware.py, routes.py, services.py, models.py, schemas.py}`
- `/services/api/src/core/rbac/{catalog.py, decorators.py, policy_engine.py, models.py, routes.py}`
- `/services/api/src/core/db/{rls.py, session.py}`
- `/services/api/migrations/versions/0002_tenancy_rbac.py`
- `/services/api/scripts/lint_rbac_coverage.py`
- `/apps/web/app/(platform)/settings/{tenants,roles,users,invitations,organizations}/page.tsx`
- `/docs/adr/0007-postgres-rls.md`, `/0008-rbac-abac.md`

**Backend modules:** `core/tenancy`, `core/rbac`.
**Frontend modules:** tenant switcher in shell, roles admin, users admin, invitations.

**Database tables**
- `tenants(id, name, slug, plan, region, status, primary_domain, created_at)`
- `tenant_features(tenant_id, feature_key, enabled, config_json)`
- `plans(id, name, limits_json)`
- `roles(id, tenant_id, name, description, is_system)`
- `permissions(id, resource, action, description)`
- `role_permissions(role_id, permission_id)`
- `user_roles(user_id, role_id, scope_type, scope_id, granted_by, granted_at, expires_at)`
- `organizations(id, tenant_id, name, parent_id)`
- `departments(id, organization_id, name)`
- `teams(id, department_id, name)`
- `team_members(team_id, user_id, role)`
- `invitations(id, tenant_id, email, role_id, token_hash, invited_by, expires_at, accepted_at)`

**APIs**
- `POST /v1/tenants`, `GET /v1/tenants/current`, `PATCH /v1/tenants/current`
- `GET/POST/PATCH/DELETE /v1/roles`
- `GET /v1/permissions`
- `POST /v1/roles/{id}/permissions`
- `POST /v1/users/{id}/roles`, `DELETE /v1/users/{id}/roles/{role_id}`
- `GET/POST /v1/organizations`, `/departments`, `/teams`
- `POST /v1/invitations`, `POST /v1/invitations/{token}/accept`

**Validation checklist**
- Cross-tenant query test: user of tenant A cannot read tenant B rows even if middleware is bypassed (RLS enforced).
- Full permission matrix tested for 5 default roles.
- CI fails a fabricated router lacking `require(...)`.
- Policy engine returns explicit `allow/deny` with rule reason logged.
- Custom role creation UI covered by E2E.

**Exit criteria:** Two tenants share one database with 100% isolation; a new tenant can be provisioned in under 60 seconds; every prior endpoint is retrofitted with `require(...)`.

---

## Sprint 5 — Audit, Event Bus, Notifications Core

**Objective:** Provide append-only auditing, transactional event publishing via the outbox pattern, and a notification pipeline with in-app + email channels.

**Deliverables**
- Audit middleware capturing every mutation with actor, before/after, `trace_id`, IP, UA.
- Daily hash-chain over audit log for tamper evidence.
- In-process event bus + RabbitMQ publisher.
- Transactional outbox table + relay worker (Debezium-lite pattern).
- Envelope schema (canonical) + AsyncAPI catalog.
- Celery scaffolding: broker, result backend, base task, retry policy, DLQ per queue.
- Notification template registry + dispatcher.
- Channels: in-app (WebSocket + persistence), email (SMTP for dev, SES/SendGrid for prod).
- SMS/WhatsApp/Push channels stubbed with adapters.
- Notification preferences per user.

**Dependencies:** Sprint 3, 4.

**Files to create**
- `/services/api/src/core/audit/{middleware.py, writer.py, hash_chain.py, models.py, routes.py}`
- `/services/api/src/core/events/{bus.py, outbox.py, envelope.py, publisher.py, subscribers.py}`
- `/services/api/src/core/events/relay_worker.py`
- `/services/api/src/core/notifications/{registry.py, dispatcher.py, prefs.py, models.py, routes.py}`
- `/services/api/src/core/notifications/channels/{inapp.py, email.py, sms.py, whatsapp.py, push.py}`
- `/services/workers/{celery_app.py, config.py, queues/__init__.py, tasks/notifications.py}`
- `/services/api/migrations/versions/0003_audit_events_notifications.py`
- `/packages/contracts/events/*.asyncapi.yaml`
- `/apps/web/app/(platform)/notifications/page.tsx`
- `/apps/web/components/notifications/{bell.tsx, drawer.tsx}`

**Backend modules:** `core/audit`, `core/events`, `core/notifications`, `services/workers`.
**Frontend modules:** notifications bell + drawer in shell, audit log viewer under admin/security.

**Database tables**
- `audit_log(id, tenant_id, actor_type, actor_id, action, resource_type, resource_id, before_json, after_json, ip, user_agent, trace_id, at)` — partitioned monthly
- `audit_hashchain_daily(day, tenant_id, prev_hash, current_hash)`
- `outbox(id, tenant_id, event_type, event_version, payload_json, occurred_at, published_at, publish_attempts, last_error)`
- `notifications(id, tenant_id, user_id, kind, title, body, data_json, read_at, created_at)`
- `notification_prefs(user_id, channel, kind, enabled)`
- `notification_templates(key, channel, subject_template, body_template, locale, active)`

**APIs**
- `GET /v1/audit-log?resource_type=&from=&to=`
- `GET /v1/notifications?unread_only=`
- `PATCH /v1/notifications/{id}/read`
- `POST /v1/notifications/mark-all-read`
- `GET/PUT /v1/me/notification-preferences`

**Validation checklist**
- Outbox test: crash between DB commit and broker publish; relay recovers on restart.
- Idempotent consumer test: same `event_id` delivered twice results in one side effect.
- Hash chain verifier detects a single-row tamper.
- Notification dispatcher fan-out ≤ 500 ms P95 for 10k recipients.
- Audit stream separate from app logs; retention configured (7 years).

**Exit criteria:** Every write endpoint produces audit entries and events; DLQ is monitored; notifications land in-app in real time and via email through a sandbox provider.

---

## Sprint 6 — Storage, Search, Cache, Feature Flags

**Objective:** Provide tenant-safe abstractions for object storage, full-text search, caching, and feature flags. Business modules must be able to adopt these with a handful of lines.

**Deliverables**
- S3 client with presigned upload/download, tenant-prefixed keys, size/content-type enforcement.
- Upload pipeline: `presign → client PUT → confirm → virus scan → indexed`.
- OpenSearch cluster + shared indexer + query API with permission filter injection.
- Redis cache-aside helpers with typed decorators + event-driven invalidation hooks.
- Feature flag client: OpenFeature SDK + Unleash provider + Redis fallback cache.
- Antivirus (ClamAV) worker.

**Dependencies:** Sprint 5.

**Files to create**
- `/services/api/src/core/storage/{s3_client.py, presign.py, models.py, routes.py, scan_hooks.py}`
- `/services/api/src/core/search/{indexer.py, query.py, models.py, routes.py, mappings/}`
- `/services/api/src/core/cache/{client.py, decorators.py, invalidation.py}`
- `/services/api/src/core/flags/{client.py, decorators.py}`
- `/services/workers/tasks/{scan_file.py, index_document.py}`
- `/services/api/migrations/versions/0004_files_search.py`
- `/infra/helm/charts/opensearch/`, `/infra/helm/charts/clamav/`
- `/apps/web/components/file-uploader/`, `/apps/web/components/global-search/`

**Backend modules:** `core/storage`, `core/search`, `core/cache`, `core/flags`.
**Frontend modules:** reusable file uploader with progress, global search bar + results page.

**Database tables**
- `files(id, tenant_id, owner_id, module, s3_key, mime, size_bytes, checksum, status, scan_result, created_at)`
- `file_scans(file_id, scanner, result, details_json, scanned_at)`
- `search_index_state(entity_type, tenant_id, last_indexed_at, backfill_status)`

**APIs**
- `POST /v1/files/presign-upload`
- `POST /v1/files/{id}/confirm`
- `GET /v1/files/{id}`
- `GET /v1/files/{id}/presign-download`
- `DELETE /v1/files/{id}`
- `GET /v1/search?q=&types=&limit=`

**Validation checklist**
- Presigned URL rejects wrong content-type and oversize payloads.
- EICAR test file quarantines and blocks download.
- Cross-tenant key access denied at S3 IAM.
- Search results filtered by RBAC on every hit before returning.
- Feature flag evaluated against local cache when Unleash is down (fail-static).

**Exit criteria:** Any module can upload a file with 3 lines of code; global search returns permission-filtered results across placeholder entities; feature-flagged routes documented.

---

# PHASE 2 — Web Shell + Admin

## Sprint 7 — Web Shell & Design System

**Objective:** Ship a production-quality web shell and reusable design system so that all business modules render inside a consistent UX and can be built by any frontend engineer.

**Deliverables**
- Next.js 14 App Router shell with auth-aware layouts.
- Design system package (Tailwind + shadcn/ui derived) with tokens: color, spacing, radii, typography, motion.
- Components: Button, Input, Textarea, Select, Combobox, Dialog, Drawer, Sheet, Table (with server-side pagination/sort/filter contract), Form (react-hook-form + zod), Toast, Tabs, Command palette, EmptyState, DataGrid.
- Navigation: sidebar, tenant switcher, module switcher, breadcrumbs.
- Command palette (⌘K) for global navigation + search + AI actions.
- Theme switcher (light/dark/system), locale switcher, timezone-aware date rendering.
- i18n scaffolding (next-intl).
- API client wrapper: fetcher with auth, retry, idempotency-key, error shape normalization.

**Dependencies:** Sprint 3, 4, 6.

**Files to create**
- `/apps/web/app/(platform)/layout.tsx`, `/apps/web/app/(platform)/page.tsx`
- `/apps/web/components/{nav/sidebar.tsx, nav/tenant-switcher.tsx, nav/user-menu.tsx, shell/*, command/*}`
- `/apps/web/lib/{api-client.ts, query-client.ts, i18n.ts, dates.ts}`
- `/packages/design-system/src/{button,input,select,combobox,dialog,drawer,sheet,table,data-grid,form,toast,tabs,command,empty-state,badge,card,skeleton}.tsx`
- `/packages/design-system/{tokens.ts, tailwind.preset.ts, index.ts}`
- `/apps/web/messages/{en,es,fr,de,hi}.json`

**Backend modules:** none.
**Frontend modules:** shell, navigation, design system, i18n, API client.

**Database tables**
- `user_preferences(user_id, theme, locale, timezone, layout_density, default_module)`

**APIs**
- `GET/PUT /v1/me/preferences`

**Validation checklist**
- Lighthouse ≥ 90 for performance, accessibility, best-practices, SEO on shell pages.
- Full keyboard navigation across every interactive element.
- Command palette opens < 100 ms after ⌘K on cold cache.
- RTL layout verified.
- Design system Storybook published.
- Component visual regression tests (Chromatic or Playwright).

**Exit criteria:** A signed-in user lands in the shell, switches tenants, opens command palette, and sees consistent empty-state placeholders for future modules. Design system is publishable and consumed by both `apps/web` and `apps/admin`.

---

## Sprint 8 — Admin Console

**Objective:** Provide an internal ops surface for tenant lifecycle, impersonation, billing overrides, and feature flag operations.

**Deliverables**
- Separate `apps/admin` Next.js app on a distinct domain.
- Auth via a distinct issuer + IP allow-list + mandatory WebAuthn MFA.
- Tenant list, detail, suspend/reactivate, region migration workflow.
- Impersonation with 2-person approval and 30-minute time box.
- Billing overrides (credits, plan changes, refunds).
- Feature flag admin surface (per-tenant overrides).
- Admin audit stream separate from tenant audit.

**Dependencies:** Sprint 4, 5, 7.

**Files to create**
- `/apps/admin/app/{tenants,users,impersonation,flags,billing,audit}/`
- `/apps/admin/lib/{api-client.ts, auth.ts}`
- `/services/api/src/core/admin/{routes.py, services.py, models.py, guards.py}`
- `/services/api/migrations/versions/0005_admin.py`

**Backend modules:** `core/admin` (gated by `staff` role).
**Frontend modules:** entire `apps/admin`.

**Database tables**
- `impersonation_grants(id, requester_id, target_tenant_id, target_user_id, reason, approver_id, approved_at, expires_at, revoked_at)`
- `impersonation_sessions(id, grant_id, session_id, started_at, ended_at)`
- `admin_overrides(id, tenant_id, kind, payload_json, actor_id, reason, created_at)`
- `admin_audit_log(id, actor_id, action, resource_type, resource_id, before_json, after_json, at)`

**APIs**
- `GET/POST /v1/admin/tenants`, `PATCH /v1/admin/tenants/{id}`
- `POST /v1/admin/tenants/{id}/suspend`, `.../reactivate`
- `POST /v1/admin/impersonation/request`, `POST /v1/admin/impersonation/{id}/approve`
- `POST /v1/admin/impersonation/{id}/start`, `POST /v1/admin/impersonation/{id}/end`
- `PUT /v1/admin/flags/{key}`
- `POST /v1/admin/billing/credits`
- `GET /v1/admin/audit`

**Validation checklist**
- Impersonation requires two distinct approvers.
- Impersonated tenant receives in-app + email notification.
- All admin actions land in `admin_audit_log`.
- Admin session cannot be extended without re-authentication.
- Compromise drill: rotate admin issuer keys and confirm invalidation.

**Exit criteria:** Ops team can onboard, suspend, refund, and impersonate tenants without engineering involvement.

---

# PHASE 3 — Business Module MVPs

Each of sprints 9–14 follows the **same template**: bounded context, CRUD + module-specific workflows, RBAC + RLS + audit + events wired in, plus a native web UI. Up to three module squads can run in parallel because they share no writes.

## Sprint 9 — CRM MVP

**Objective:** Ship lead → contact → deal → won lifecycle with pipelines, kanban, and activity timeline.

**Deliverables**
- CRUD for companies, contacts, leads, deals.
- Pipelines with configurable stages; drag-drop kanban board.
- Activity timeline (notes, calls, emails, meetings).
- Email → CRM ingestion stub (BCC-to-lead@).
- Duplicate detection on contact create.

**Dependencies:** Sprint 4, 5, 6, 7.

**Files to create**
- `/services/api/src/modules/crm/{api,application,domain,infrastructure}/`
- `/services/api/src/modules/crm/domain/{entities,services,events}.py`
- `/apps/web/app/(platform)/crm/{leads,contacts,companies,deals,pipelines,activities}/`
- `/apps/web/components/crm/{kanban.tsx, deal-card.tsx, activity-timeline.tsx}`
- `/services/api/migrations/versions/0006_crm.py`

**Backend modules:** `modules/crm`.
**Frontend modules:** all CRM pages, kanban board component (reusable), timeline component.

**Database tables**
- `companies`, `contacts`, `leads`, `deals`
- `pipelines`, `pipeline_stages`, `deal_stage_history`
- `activities` (typed: note/call/email/meeting/task)
- `crm_tags`, `crm_entity_tags`

**APIs**
- CRUD `/v1/crm/companies|contacts|leads|deals`
- `POST /v1/crm/leads/{id}/convert`
- `POST /v1/crm/deals/{id}/move`, `/win`, `/lose`
- CRUD `/v1/crm/pipelines`, `/stages`
- `GET/POST /v1/crm/activities?resource_type=&resource_id=`

**Validation checklist**
- RBAC per entity (`crm.deals.read`, `.write`, `.delete`, `.export`).
- Kanban move produces one atomic event with old/new stage.
- Duplicate contact detection ≥ 95% precision on test set.
- Events emitted: `lead.created`, `lead.qualified`, `deal.moved`, `deal.won`, `deal.lost`.
- Audit populated for every mutation.

**Exit criteria:** Full lead → deal → won lifecycle usable; global search finds CRM entities; ready for AI Copilot to reason over CRM data in Phase 4.

---

## Sprint 10 — Finance MVP

**Objective:** Ship invoices, quotes, payments, expenses, chart of accounts, and tax rules with PDF rendering.

**Deliverables**
- CRUD for above entities.
- Quote → Invoice conversion.
- Multi-currency with Decimal arithmetic.
- Tax rule engine (per region + product category).
- PDF invoice generator (WeasyPrint or Chromium-headless template).
- Manual payment recording; Stripe payment intent stub.
- Invoice email delivery.
- Per-tenant invoice numbering with no gaps.

**Dependencies:** Sprints 4–7.

**Files to create**
- `/services/api/src/modules/finance/{api,application,domain,infrastructure}/`
- `/services/api/src/modules/finance/domain/{money.py, tax_engine.py, journal.py}`
- `/services/api/src/modules/finance/infrastructure/pdf_renderer.py`
- `/apps/web/app/(platform)/finance/{invoices,quotes,payments,expenses,accounts,taxes}/`
- `/services/workers/tasks/{generate_invoice_pdf.py, send_invoice_email.py}`
- `/services/api/migrations/versions/0007_finance.py`

**Backend modules:** `modules/finance`.
**Frontend modules:** finance pages, PDF viewer, line-item editor.

**Database tables**
- `accounts` (chart), `invoices`, `invoice_items`, `quotes`, `quote_items`
- `payments`, `payment_allocations`
- `expenses`, `expense_categories`
- `tax_rules`, `tax_regions`
- `journal_entries` (double-entry)
- `invoice_sequences(tenant_id, year, next_number)`

**APIs**
- CRUD `/v1/finance/{invoices,quotes,payments,expenses,accounts,tax-rules}`
- `POST /v1/finance/quotes/{id}/convert-to-invoice`
- `POST /v1/finance/invoices/{id}/send`
- `POST /v1/finance/invoices/{id}/void`
- `POST /v1/finance/invoices/{id}/mark-paid`
- `GET /v1/finance/invoices/{id}/pdf`

**Validation checklist**
- Money arithmetic uses Decimal; rounding rule tested.
- Journal entries always balance (sum(dr) = sum(cr)).
- Multi-currency conversion preserves original amount + FX rate.
- Invoice numbering strictly monotonic per tenant.
- PDF matches design across Linux/macOS/Windows viewers.
- Events: `invoice.created|sent|paid|voided|overdue`.

**Exit criteria:** Create → send → pay lifecycle green; multi-currency invoice paid in a different currency reconciles cleanly.

---

## Sprint 11 — Projects MVP

**Objective:** Ship projects, tasks, subtasks, milestones, time tracking, kanban, and gantt.

**Deliverables**
- CRUD for projects/tasks/subtasks/milestones.
- Kanban and Gantt views.
- Task dependencies with cycle detection.
- Assignees, watchers, comments.
- Time entries + weekly timesheet.

**Dependencies:** Sprints 4–7.

**Files to create**
- `/services/api/src/modules/projects/…`
- `/services/api/src/modules/projects/domain/{scheduler.py, dependency_graph.py}`
- `/apps/web/app/(platform)/projects/{list,board,gantt,timesheet,task-detail}/`
- `/apps/web/components/projects/{gantt.tsx, timesheet-grid.tsx}`
- `/services/api/migrations/versions/0008_projects.py`

**Backend modules:** `modules/projects`.
**Frontend modules:** project pages, gantt, timesheet grid.

**Database tables**
- `projects`, `tasks`, `subtasks`, `milestones`
- `task_dependencies`, `task_assignees`, `task_watchers`
- `task_comments`
- `time_entries` (partitioned by month)

**APIs**
- CRUD `/v1/projects/*`, `/tasks/*`, `/milestones/*`
- `POST /v1/projects/tasks/{id}/move`, `/assign`, `/log-time`, `/complete`
- `GET /v1/projects/{id}/gantt`
- `GET /v1/timesheets?user_id=&from=&to=`

**Validation checklist**
- Cycle detection blocks dependency loops.
- Gantt recomputation deterministic for the same input.
- Time-entry overlap prevented per user.
- Events: `task.created|assigned|completed|moved`.

**Exit criteria:** A team can plan and track a project end-to-end with kanban and gantt; timesheet exports to CSV.

---

## Sprint 12 — HR MVP

**Objective:** Ship employees, attendance, leave, payroll ledger, and performance reviews.

**Deliverables**
- Employee directory with hierarchy.
- Clock-in/out with geofence option.
- Leave workflow: request → approve/deny; balance tracking.
- Payroll items + monthly close (ledger only; no bank rails).
- Performance review cycles with configurable forms.

**Dependencies:** Sprints 4–7.

**Files to create**
- `/services/api/src/modules/hr/…`
- `/services/api/src/modules/hr/domain/{leave_policy.py, payroll_calc.py}`
- `/apps/web/app/(platform)/hr/{employees,attendance,leave,payroll,reviews}/`
- `/services/api/migrations/versions/0009_hr.py`

**Backend modules:** `modules/hr`.
**Frontend modules:** HR pages, review form builder.

**Database tables**
- `employees`, `employee_hierarchy`, `job_titles`
- `attendance_events`, `attendance_daily_summary`
- `leave_types`, `leave_requests`, `leave_balances`
- `payroll_items`, `payroll_runs`, `payroll_ledger`
- `review_cycles`, `review_forms`, `review_responses`

**APIs**
- CRUD `/v1/hr/employees`, `/leave-requests`, `/attendance`, `/reviews`
- `POST /v1/hr/leave-requests/{id}/approve|deny`
- `POST /v1/hr/attendance/clock-in|clock-out`
- `POST /v1/hr/payroll-runs`, `.../close`
- `POST /v1/hr/reviews/{id}/submit`

**Validation checklist**
- Leave balance updates atomic with request approval.
- Overlapping leave requests detected and blocked.
- Payroll close idempotent + reversible within 48h.
- Events: `leave.requested|approved|denied`, `payroll.run.closed`.

**Exit criteria:** Employee → manager leave workflow works; monthly payroll close produces a signed ledger PDF.

---

## Sprint 13 — Inventory MVP

**Objective:** Ship products, SKUs, warehouses, stock movements, and purchase orders.

**Deliverables**
- Product catalog with variants (SKUs).
- Multi-warehouse stock ledger.
- Adjust / transfer / receive / ship operations.
- Purchase orders with supplier + line items.
- Low-stock alerts.

**Dependencies:** Sprints 4–7.

**Files to create**
- `/services/api/src/modules/inventory/…`
- `/services/api/src/modules/inventory/domain/{stock_ledger.py, reservation.py}`
- `/apps/web/app/(platform)/inventory/{products,warehouses,movements,pos,suppliers}/`
- `/services/api/migrations/versions/0010_inventory.py`

**Backend modules:** `modules/inventory`.
**Frontend modules:** inventory pages, barcode-friendly input.

**Database tables**
- `products`, `skus`, `warehouses`, `suppliers`
- `stock_movements` (partitioned monthly), `stock_snapshots_daily`
- `purchase_orders`, `po_items`, `po_receipts`

**APIs**
- CRUD `/v1/inventory/products`, `/skus`, `/warehouses`, `/suppliers`, `/pos`
- `POST /v1/inventory/movements/adjust|transfer|receive|ship`
- `POST /v1/inventory/pos/{id}/receive`
- `GET /v1/inventory/stock?sku_id=&warehouse_id=`

**Validation checklist**
- Concurrent movements per (SKU, warehouse) serialized.
- Stock cannot go negative unless `allow_negative` flag set.
- PO totals reconcile with line items and taxes.
- Events: `stock.moved`, `stock.low`, `po.created|received|closed`.

**Exit criteria:** Full receive → stock → ship cycle green; multi-warehouse transfer preserves integrity under concurrent load.

---

## Sprint 14 — Support MVP

**Objective:** Ship ticketing, SLAs, knowledge base, and a customer portal.

**Deliverables**
- Ticket lifecycle: new → open → pending → resolved → closed.
- Internal notes vs. public replies.
- SLA policies with breach events.
- Canned responses.
- Knowledge base articles with public/private visibility.
- Customer portal via magic link (no full account required).

**Dependencies:** Sprints 4–7, 9 (contacts as customers).

**Files to create**
- `/services/api/src/modules/support/…`
- `/services/api/src/modules/support/domain/{sla_engine.py, routing.py}`
- `/apps/web/app/(platform)/support/{tickets,kb,canned}/`
- `/apps/portal/app/` (customer portal — separate Next.js app)
- `/services/api/migrations/versions/0011_support.py`

**Backend modules:** `modules/support`, `core/portal_auth`.
**Frontend modules:** agent UI, KB editor, `apps/portal`.

**Database tables**
- `tickets`, `ticket_messages`, `ticket_watchers`, `ticket_tags`
- `sla_policies`, `sla_events`
- `canned_responses`
- `kb_articles`, `kb_article_versions`
- `portal_sessions`, `portal_magic_links`

**APIs**
- CRUD `/v1/support/tickets`, `/kb/articles`, `/canned-responses`
- `POST /v1/support/tickets/{id}/reply` (internal or public)
- `POST /v1/support/tickets/{id}/assign`, `.../close`, `.../reopen`
- `POST /v1/portal/magic-link`, `POST /v1/portal/verify`
- `GET /v1/portal/tickets` (portal-authenticated)

**Validation checklist**
- SLA breach events fire within 1 minute of due time.
- Email replies threaded to correct ticket via message-id.
- Magic-link tokens single-use, 15-minute expiry.
- Portal RLS restricts to that customer's tickets only.

**Exit criteria:** Customer files a ticket via portal, agent replies, SLA tracked; KB fully searchable and public articles indexable.

---

# PHASE 4 — AI Layer

## Sprint 15 — AI Orchestrator Foundation

**Objective:** Stand up the provider-agnostic AI gateway with routing, cost accounting, budgets, and health checks. No business module ever calls a provider SDK directly.

**Deliverables**
- Separate `ai-orchestrator` service.
- Provider adapters: OpenAI, Anthropic, Google (Vertex), self-hosted vLLM.
- Common `ChatRequest` / `ChatChunk` / `EmbedRequest` schema.
- Router: choose by capability, plan, cost budget, latency, health.
- Cost/token accounting persisted per request.
- Per-tenant monthly budgets with soft/hard caps.
- Provider health checks + circuit breakers.
- SDK for business services: `ai_client.chat(...)`, `.embed(...)`.

**Dependencies:** Sprints 1–6.

**Files to create**
- `/services/ai-orchestrator/src/{main.py, api/, providers/{openai,anthropic,google,vllm}.py, router/, accounting/, health/, budgets/}`
- `/services/api/src/core/ai_client/` (client SDK)
- `/services/ai-orchestrator/migrations/versions/0001_ai_core.py`
- `/docs/adr/0009-ai-gateway.md`

**Backend modules:** `services/ai-orchestrator`, `core/ai_client`.
**Frontend modules:** none.

**Database tables** (in shared Postgres, own schema `ai`)
- `ai_requests` (partitioned monthly) `(id, tenant_id, user_id, feature, provider, model, tokens_in, tokens_out, cost_usd, latency_ms, status, created_at)`
- `ai_costs_daily(day, tenant_id, feature, provider, tokens_in, tokens_out, cost_usd)`
- `ai_budgets(tenant_id, month, soft_cap_usd, hard_cap_usd, used_usd)`
- `ai_provider_health(provider, model, success_rate, p95_latency_ms, updated_at)`
- `ai_models(model_key, provider, capabilities_json, price_in_per_1k, price_out_per_1k, active)`

**APIs** (internal, mTLS-only)
- `POST /internal/ai/chat` (streaming)
- `POST /internal/ai/embed`
- `GET /internal/ai/budgets/{tenant_id}`
- `GET /internal/ai/health`

**Validation checklist**
- Adapters conform to shared schema (contract test per provider).
- Cost per request within 5% of provider bill on a reconciliation sample.
- Budget breach returns 429 with `Retry-After` and structured reason.
- Provider outage triggers failover in < 5 seconds; health check flips within 30 seconds.
- No PII passes to a provider unless tenant opts in (redaction verified on 20 fixtures).

**Exit criteria:** Business services get streaming AI via `ai_client.chat(...)` regardless of provider; nightly cost roll-up is accurate per tenant/feature.

---

## Sprint 16 — Prompt Registry & Guardrails

**Objective:** Manage prompts as versioned artifacts with input/output guardrails and evaluation gates.

**Deliverables**
- Prompt registry: prompt + versions + tenant overrides.
- Prompt evaluation harness with golden sets and metrics.
- Input filters: prompt-injection detector, PII scrubber.
- Output validators: JSON schema, moderation, refusal detection.
- Admin UI for prompt CRUD, publish, roll back.

**Dependencies:** Sprint 15.

**Files to create**
- `/services/ai-orchestrator/src/prompts/{registry.py, versions.py, overrides.py, evals.py}`
- `/services/ai-orchestrator/src/guardrails/{injection.py, pii.py, moderation.py, schema.py}`
- `/apps/admin/app/ai/{prompts,evals,guardrails}/`
- `/services/ai-orchestrator/migrations/versions/0002_prompts.py`

**Backend modules:** `ai-orchestrator/prompts`, `ai-orchestrator/guardrails`.
**Frontend modules:** prompt admin, eval dashboard.

**Database tables**
- `prompts(id, key, description, owner, created_at)`
- `prompt_versions(id, prompt_id, version, template, variables_json, output_schema_json, status, created_by, published_at)`
- `prompt_tenant_overrides(tenant_id, prompt_id, version_id, active)`
- `prompt_eval_sets(id, prompt_id, name, items_json)`
- `prompt_eval_runs(id, prompt_id, version_id, set_id, metrics_json, created_at)`
- `guardrail_rules(id, kind, config_json, active)`
- `pii_redactions(id, request_id, entity_type, hash, at)`

**APIs**
- CRUD `/v1/ai/prompts`, `/prompts/{id}/versions`
- `POST /v1/ai/prompts/{id}/eval` (run against set)
- `PUT /v1/ai/prompts/{id}/versions/{v}/publish`
- `POST /v1/ai/prompts/{id}/rollback`

**Validation checklist**
- Prompt-injection test set: ≥ 95% detection on curated attacks.
- PII scrub redacts 20 sample docs correctly on emails/PANs/phones.
- JSON schema validator rejects malformed outputs and triggers repair loop.
- Rollout gated by eval score ≥ published baseline.

**Exit criteria:** Modules reference prompts by `(key, version)`; admin can roll back a version in one click; every prompt has an eval set.

---

## Sprint 17 — RAG Pipeline

**Objective:** Enable retrieval-augmented generation over tenant documents with an ingest → chunk → embed → retrieve → rerank pipeline.

**Deliverables**
- Chunker (semantic + length-aware).
- Batch embedder with backpressure.
- Storage: pgvector primary; Qdrant path behind a flag.
- Hybrid retriever: vector + BM25 (OpenSearch).
- Cross-encoder reranker.
- Retrieval quality dashboard (recall@k, MRR).
- Re-indexing on document update.

**Dependencies:** Sprints 6, 15.

**Files to create**
- `/services/ai-orchestrator/src/rag/{chunker.py, embedder.py, retriever.py, reranker.py, quality.py}`
- `/services/workers/tasks/embed_document.py`
- `/services/ai-orchestrator/migrations/versions/0003_rag.py`
- `/apps/web/app/(platform)/knowledge/`
- `/apps/web/components/knowledge/{document-list.tsx, reindex-controls.tsx}`

**Backend modules:** `ai-orchestrator/rag`.
**Frontend modules:** knowledge base view, per-doc re-index controls.

**Database tables**
- `documents(id, tenant_id, file_id, title, source, status, indexed_at)`
- `document_chunks(id, document_id, ordinal, text, tokens, hash)`
- `chunk_embeddings(chunk_id, embedding vector, model, created_at)` — HNSW index per tenant
- `retrieval_events(id, tenant_id, query_hash, top_ids_json, latency_ms, at)`
- `rag_evals(id, set_id, run_at, recall_at_k, mrr, ndcg)`

**APIs**
- `POST /v1/ai/rag/index/{file_id}`
- `POST /v1/ai/rag/reindex/{document_id}`
- `POST /v1/ai/rag/search` (internal)
- `GET /v1/ai/rag/documents`

**Validation checklist**
- Recall@10 ≥ threshold on golden set.
- Embedder retries on transient failures with backoff.
- Reindex fully within 15 min per 10k pages.
- Vector query enforces tenant filter at index level.

**Exit criteria:** Copilot can ground answers on tenant documents; retrieval quality dashboard tracked over time.

---

## Sprint 18 — Copilot & Tool Bridge

**Objective:** Deliver a chat-based assistant with conversation state, module-aware tool calling, and RBAC-checked execution.

**Deliverables**
- Copilot conversation store + resumable state.
- System-prompt composer combining tenant profile, module context, retrieved chunks, tool schemas.
- Tool registry exposing module use cases as callable tools (e.g. `crm.search_deals`, `finance.get_invoice`, `projects.list_overdue_tasks`).
- Tool bridge enforces RBAC identical to REST equivalents.
- Feedback capture (👍/👎 + reason).
- Copilot side panel + full-page chat.

**Dependencies:** Sprints 15–17, and any business module the copilot should reason over (9–14).

**Files to create**
- `/services/ai-orchestrator/src/copilot/{orchestrator.py, tools_registry.py, context_builder.py, feedback.py}`
- `/services/api/src/core/tool_bridge/{registry.py, dispatcher.py, guards.py}`
- `/apps/web/app/(platform)/copilot/`
- `/apps/web/components/copilot/{panel.tsx, message.tsx, tool-call-trace.tsx}`
- `/services/ai-orchestrator/migrations/versions/0004_copilot.py`

**Backend modules:** `ai-orchestrator/copilot`, `core/tool_bridge`.
**Frontend modules:** copilot side panel + full page, tool call visualizer.

**Database tables**
- `ai_conversations(id, tenant_id, user_id, module, title, created_at, updated_at)`
- `ai_messages(id, conversation_id, role, content, tokens_in, tokens_out, model, created_at)`
- `ai_tool_calls(id, message_id, tool_key, input_json, output_json, status, latency_ms, denied_reason)`
- `ai_feedback(id, message_id, user_id, verdict, reason, at)`

**APIs**
- `POST /v1/ai/conversations`
- `GET /v1/ai/conversations`, `GET /v1/ai/conversations/{id}`
- `POST /v1/ai/conversations/{id}/messages` (streaming)
- `POST /v1/ai/messages/{id}/feedback`

**Validation checklist**
- Tool calls denied when RBAC would deny the direct REST call.
- Hallucination rate below threshold on grounded eval set.
- Conversation resumable after client disconnect + reconnect.
- Every tool call logged with input/output for debug (redacted view for tenant, full for admin).

**Exit criteria:** User asks "list top 5 open deals over $50k this quarter" and Copilot returns grounded answer with tool trace; admin can audit any conversation.

---

## Sprint 19 — Realtime Gateway & AI Streaming

**Objective:** Ship a dedicated realtime layer with WebSocket/SSE for AI streams, notifications, and presence, backed by Redis Streams for reliability.

**Deliverables**
- Separate `realtime` service, autoscaled independently.
- Authenticated WebSocket + SSE endpoints.
- Redis Streams as the durable backing for AI token streams.
- Presence with per-tenant channels.
- Backpressure and per-connection buffer limits.
- Frontend hooks: `useStream`, `usePresence`, `useNotifications`.

**Dependencies:** Sprints 5, 15, 18.

**Files to create**
- `/services/realtime/src/{main.py, api/, ws/, sse/, streams/, presence/, auth/}`
- `/apps/web/lib/realtime-client.ts`
- `/apps/web/hooks/{use-stream.ts, use-presence.ts, use-notifications.ts}`

**Backend modules:** `services/realtime`.
**Frontend modules:** realtime client + hooks.

**Database tables:** none (state in Redis).

**APIs**
- `WS /v1/rt` (auth via short-lived token)
- `SSE /v1/rt/streams/{stream_id}`
- `GET /v1/rt/presence/{channel}`

**Validation checklist**
- 10k concurrent connections per pod under baseline load.
- Token stream resumes cleanly after disconnect using stream cursor.
- Slow consumer disconnected without harming other connections.
- Presence accurate within 5 seconds under churn.

**Exit criteria:** Copilot streams smoothly at ~30 tok/s under 20% simulated packet loss; realtime notifications visible < 1s from event emit.

---

# PHASE 5 — Automation

## Sprint 20 — Workflow Engine Core

**Objective:** Ship a durable workflow runtime with triggers (schedule, event, webhook, manual), conditions, actions, and AI steps.

**Deliverables**
- `workflow-engine` service (Temporal or custom DAG runtime).
- Trigger types: schedule (cron), event (broker), webhook (inbound), manual.
- Action library: send email, HTTP request, module use case, AI step, wait, branch, parallel.
- Retries, error branches, timeouts.
- Per-tenant concurrency limits.

**Dependencies:** Sprints 5, 15.

**Files to create**
- `/services/workflow-engine/src/{main.py, runtime/, triggers/, actions/, scheduler/, api/}`
- `/services/workflow-engine/src/actions/{email.py, http.py, module.py, ai.py, wait.py, branch.py}`
- `/services/api/migrations/versions/0015_workflow.py`
- `/docs/adr/0010-durable-workflow.md`

**Backend modules:** `services/workflow-engine`.
**Frontend modules:** workflow run history viewer, minimal debug UI.

**Database tables**
- `workflows(id, tenant_id, name, description, active, current_version_id)`
- `workflow_versions(id, workflow_id, version, definition_json, published_at, published_by)`
- `workflow_runs(id, workflow_id, version_id, trigger_kind, trigger_payload_json, status, started_at, finished_at)` — partitioned monthly
- `workflow_step_runs(id, run_id, step_key, status, input_json, output_json, error_json, attempts, started_at, finished_at)`
- `workflow_schedules(id, workflow_id, cron, timezone, active)`
- `workflow_triggers(id, workflow_id, kind, config_json)`

**APIs**
- CRUD `/v1/workflows`
- `POST /v1/workflows/{id}/versions`, `.../publish`
- `POST /v1/workflows/{id}/trigger`
- `GET /v1/workflow-runs?workflow_id=&status=`
- `GET /v1/workflow-runs/{id}`
- `POST /v1/workflow-runs/{id}/retry`, `.../cancel`

**Validation checklist**
- Durable across worker restart (kill mid-step, resume completes).
- Retries with exponential backoff and jitter.
- Idempotent step execution using step keys.
- Per-tenant concurrency limits honored.
- Audit for every run start/finish/failure.

**Exit criteria:** "When invoice paid → notify Slack + update CRM deal + wait 2h → send follow-up" workflow runs reliably under fault injection.

---

## Sprint 21 — Workflow Builder UI

**Objective:** Give tenants a visual canvas to design and test workflows without engineering.

**Deliverables**
- React Flow-based canvas with node palette.
- Trigger and action config drawers with typed forms.
- Graph validation (unreachable steps, missing connections, cyclic branches).
- Test-run mode with a mock trigger payload.
- Version history and diff view.

**Dependencies:** Sprint 20.

**Files to create**
- `/apps/web/app/(platform)/automation/workflows/`
- `/apps/web/components/workflow-canvas/{canvas.tsx, node-palette.tsx, node-config.tsx, edge.tsx, validator.ts}`

**Backend modules:** extends `workflow-engine` with dry-run endpoint.
**Frontend modules:** workflow canvas suite.

**Database tables:** none new.

**APIs**
- `POST /v1/workflows/dry-run`
- `GET /v1/workflows/{id}/versions` (diff)

**Validation checklist**
- Undo/redo (≥ 50 steps).
- Canvas performant with 100 nodes.
- Graph validation catches at least: unreachable nodes, missing required config, invalid connection types.
- Keyboard-drivable canvas (WCAG 2.1 AA).

**Exit criteria:** A non-technical tenant admin builds a 5-step workflow in under 10 minutes without help.

---

## Sprint 22 — Integrations Hub

**Objective:** Ship the connector SDK plus first six connectors: Gmail, Slack, Stripe, QuickBooks, WhatsApp Business, Google Drive.

**Deliverables**
- OAuth broker (managed installs per tenant).
- Connector SDK: auth, config, actions, triggers, webhook receiver contract.
- 6 connectors implemented against the SDK.
- Credential storage with per-tenant KMS-encrypted secrets.
- Webhook receiver with signature verification per provider.

**Dependencies:** Sprints 5, 6, 20.

**Files to create**
- `/services/api/src/integrations/sdk/{connector.py, oauth_broker.py, credentials.py, webhook.py}`
- `/services/api/src/integrations/connectors/{gmail,slack,stripe,quickbooks,whatsapp,gdrive}/`
- `/apps/web/app/(platform)/integrations/{catalog,connected,configure}/`
- `/services/api/migrations/versions/0016_integrations.py`

**Backend modules:** `integrations/sdk`, per-connector modules.
**Frontend modules:** integrations gallery, per-connector config screens, connection status.

**Database tables**
- `integrations(id, tenant_id, connector_key, status, created_at)`
- `integration_credentials(integration_id, key, ciphertext, kms_key_id, updated_at)`
- `webhook_endpoints(id, tenant_id, provider, secret_hash, active)`
- `webhook_deliveries(id, endpoint_id, provider_event_id, payload_hash, verified, processed_at, status)`
- `oauth_state(state, tenant_id, connector_key, expires_at)`

**APIs**
- `GET /v1/integrations/catalog`
- `POST /v1/integrations/{key}/connect`
- `GET /v1/integrations/{key}/callback`
- `GET /v1/integrations` (connected list)
- `DELETE /v1/integrations/{id}`
- `POST /v1/webhooks/{provider}/{tenant_slug}` (inbound)

**Validation checklist**
- OAuth flow works for each connector, including token refresh.
- Credentials never leave the KMS-decrypt boundary.
- Webhook signatures verified per provider.
- Contract tests per connector against provider sandbox.
- Rate-limit handling per provider documented.

**Exit criteria:** Tenant connects Slack → workflow sends message; Stripe webhook triggers a finance workflow; connection failures alert only the tenant admin, not the platform.

---

# PHASE 6 — Analytics

## Sprint 23 — Analytics Pipeline (CDC → ClickHouse)

**Objective:** Stand up the analytics data plane: CDC from Postgres → Kafka/Redpanda → ClickHouse, plus a semantic layer.

**Deliverables**
- Debezium connectors per publication.
- Kafka/Redpanda cluster.
- ClickHouse cluster with materialized views for the main facts.
- Analytics ingest service that shapes events into facts/dims.
- Semantic layer: metrics + dimensions catalog, permission model.
- Reconciliation job Postgres ↔ ClickHouse.

**Dependencies:** Sprint 1, plus business modules (any subset for MVP).

**Files to create**
- `/infra/helm/charts/analytics/` (Redpanda, ClickHouse, Debezium)
- `/services/analytics/src/{ingest,semantic,query,api}/`
- `/services/analytics/src/semantic/{metrics.py, dimensions.py, catalog.py}`
- `/services/analytics/clickhouse/migrations/*.sql`
- `/docs/adr/0011-cdc-to-clickhouse.md`

**Backend modules:** `services/analytics`.
**Frontend modules:** none.

**Database tables**
- Postgres side: `analytics_publications`, `analytics_reconciliation`
- ClickHouse side: `fact_events`, `fact_invoices`, `fact_payments`, `fact_deals`, `fact_tasks`, `fact_tickets`, `fact_stock_movements`; `dim_tenant`, `dim_user`, `dim_time`, `dim_product`, `dim_customer`; materialized views per metric

**APIs** (internal)
- `POST /internal/analytics/query`
- `GET /internal/analytics/catalog`

**Validation checklist**
- Postgres → ClickHouse lag < 60 s P95.
- Schema evolution safe (Avro schema registry).
- Row counts reconcile daily; discrepancies alert.
- Tenant filter enforced at query API.

**Exit criteria:** Any module can request metrics via a single query API with sub-second latency for standard aggregates.

---

## Sprint 24 — Report Builder & Dashboards

**Objective:** Let tenants build reports and dashboards without SQL, with scheduled delivery.

**Deliverables**
- Report builder UI: metrics + dimensions + filters.
- Visualizations: bar, line, area, pie, table, KPI, funnel, cohort.
- Dashboard canvas with grid layout.
- Scheduled email delivery, PDF/CSV export.
- Public sharing with signed URLs (opt-in).

**Dependencies:** Sprint 23.

**Files to create**
- `/apps/web/app/(platform)/analytics/{reports,dashboards,widgets}/`
- `/apps/web/components/analytics/{builder.tsx, charts/, dashboard-grid.tsx}`
- `/services/api/src/modules/analytics_reports/…`
- `/services/workers/tasks/deliver_scheduled_report.py`
- `/services/api/migrations/versions/0017_reports.py`

**Backend modules:** `modules/analytics_reports`.
**Frontend modules:** report builder, dashboard canvas, chart library.

**Database tables**
- `reports(id, tenant_id, name, definition_json, owner_id, created_at)`
- `dashboards(id, tenant_id, name, layout_json, owner_id)`
- `dashboard_widgets(id, dashboard_id, report_id, position_json, config_json)`
- `report_schedules(id, report_id, cron, recipients_json, format, active)`
- `report_shares(id, report_id, token_hash, expires_at, revoked_at)`

**APIs**
- CRUD `/v1/reports`, `/dashboards`
- `POST /v1/reports/{id}/run`
- `POST /v1/reports/{id}/schedule`
- `POST /v1/reports/{id}/share`
- `GET /v1/reports/share/{token}`

**Validation checklist**
- Query respects RBAC on facts and dimensions.
- Scheduled reports delivered within 5 min of scheduled time.
- Export files < 25 MB or paginated.
- Shared link revocable and rate-limited.

**Exit criteria:** Tenant admin builds "revenue by month per rep" without engineering help.

---

# PHASE 7 — Mobile + Public API

## Sprint 25 — Mobile Client

**Objective:** Deliver a React Native + Expo app at parity with the web on the highest-value flows: Copilot, CRM, Support, Notifications.

**Deliverables**
- Expo-managed RN app.
- Auth flow with biometric MFA.
- Module screens: Copilot, CRM (leads/deals), Support (tickets), Notifications.
- Push notifications via APNs + FCM.
- Offline queue for support replies and CRM notes.

**Dependencies:** Sprints 3, 5, 9, 14, 18, 19.

**Files to create**
- `/apps/mobile/app/*`
- `/apps/mobile/lib/{api,auth,realtime,offline-queue}.ts`
- `/apps/mobile/components/{copilot,crm,support,notifications}/`

**Backend modules:** none new (mobile uses the same public API).
**Frontend modules:** mobile app.

**Database tables**
- `push_tokens(id, user_id, platform, token, device_id, updated_at)`

**APIs**
- `POST /v1/me/push-tokens`, `DELETE /v1/me/push-tokens/{id}`

**Validation checklist**
- Cold start < 3 s on midrange Android.
- Push notifications received < 5 s from send.
- Offline queue survives kill + relaunch.
- Biometric MFA fallback to TOTP.

**Exit criteria:** TestFlight + Play internal beta green; four flagship flows fully usable on mobile.

---

## Sprint 26 — Public API, Webhooks, SDKs

**Objective:** Externalize the API for tenant developers with API keys, webhook subscriptions, developer portal, and language SDKs.

**Deliverables**
- API keys with scopes, IP allow-list, rotation.
- Developer portal with docs, API console, request logs.
- Webhook subscriptions: HMAC signatures, exponential retries up to 24h, replay endpoint.
- Generated SDKs (TypeScript, Python) published from OpenAPI.
- Sandbox tenant environment with synthetic data.

**Dependencies:** Sprints 3, 5, 15, plus any business modules to be exposed.

**Files to create**
- `/apps/portal-dev/app/` (developer portal — separate Next.js app)
- `/packages/sdk-ts/`, `/packages/sdk-py/`
- `/services/api/src/core/api_keys/{routes.py, services.py, models.py, guards.py}`
- `/services/api/src/core/dev_webhooks/{routes.py, dispatcher.py, models.py}`
- `/services/workers/tasks/dispatch_dev_webhook.py`
- `/services/api/migrations/versions/0018_api_keys_webhooks.py`

**Backend modules:** `core/api_keys`, `core/dev_webhooks`.
**Frontend modules:** developer portal.

**Database tables**
- `api_keys(id, tenant_id, name, key_hash, prefix, scopes_json, ip_allow_list_json, last_used_at, expires_at, revoked_at)`
- `api_key_usage(day, api_key_id, requests, errors)`
- `dev_webhook_endpoints(id, tenant_id, url, secret_hash, events_json, active)`
- `dev_webhook_deliveries(id, endpoint_id, event_id, status, attempts, response_status, next_attempt_at)`
- `dev_webhook_events(id, tenant_id, event_type, payload_json, created_at)`

**APIs**
- CRUD `/v1/api-keys`
- CRUD `/v1/webhooks/subscriptions`
- `GET /v1/webhooks/deliveries`
- `POST /v1/webhooks/deliveries/{id}/replay`

**Validation checklist**
- API key auth latency < 5 ms P95 with Redis cache.
- HMAC verified end-to-end using SDK samples.
- Exponential backoff up to 24 h; DLQ after final failure.
- SDK generation reproducible in CI on OpenAPI change.

**Exit criteria:** An external developer registers an app, obtains an API key, subscribes to webhooks, and receives verified events end-to-end using the published SDK.

---

# PHASE 8 — Hardening + Launch

## Sprint 27 — Security Hardening & Compliance

**Objective:** Achieve production-grade security posture and pass an external penetration test in preparation for SOC 2 Type II and ISO 27001 audits.

**Deliverables**
- Updated threat model.
- DAST run in staging; remediation of findings.
- External pen test + full remediation.
- Secret rotation automated (weekly for app secrets, annually for KMS keys).
- Per-tenant KMS keys enforced for sensitive columns and object storage.
- DPIA, DPA, sub-processor list finalized.
- Incident response game day executed with post-mortem.

**Dependencies:** Everything above.

**Files to create**
- `/docs/security/{threat-model.md, pen-test.md, dpia.md, dpa.md, subprocessors.md}`
- `/ops/runbooks/{incident-response.md, key-rotation.md, breach-notification.md}`
- `/infra/terraform/modules/kms-per-tenant/`
- `/.github/workflows/security.yml` (weekly)

**Backend modules:** enhancements across `core/auth`, `core/tenancy`, `core/storage`, `core/api_keys`.
**Frontend modules:** user security page (session mgmt, audit access, data export/deletion).

**Database tables**
- `data_subject_requests(id, tenant_id, subject_ref, kind, status, created_at, completed_at)` (GDPR / DPDP)

**APIs**
- `POST /v1/me/data-export`
- `POST /v1/me/data-erasure`
- `GET /v1/tenants/current/security-events`

**Validation checklist**
- Pen test finds no High/Critical open.
- SAST + DAST + dependency scan clean at release gate.
- Rotation drill: rotate all secrets within one business day.
- Data subject request completed within regulatory SLA on test cases.

**Exit criteria:** External auditor signs off on control design; observation window for SOC 2 Type II can begin.

---

## Sprint 28 — Performance, Load, Chaos

**Objective:** Prove the platform meets the NFR targets stated in the architecture and validate incident readiness.

**Deliverables**
- k6 load-test suite covering top-N critical paths per module.
- Chaos experiments: kill pods, kill DB primary, throttle broker, partition network, degrade provider.
- Capacity plan document and cost model per 1k active users.
- Autoscaler tuning (HPA + KEDA).
- Runbook proofs from game day.

**Dependencies:** Everything above.

**Files to create**
- `/ops/load-tests/{k6/*.js, scenarios/*.md}`
- `/ops/chaos/{experiments/*.yaml, reports/}`
- `/docs/capacity-plan.md`
- `/ops/gameday-plans/{q1,q2}.md`

**Backend modules:** none new; scaling configs updated.
**Frontend modules:** none.
**Database tables:** none.
**APIs:** none.

**Validation checklist**
- Sustained 5k RPS with error rate < 0.1%.
- AI first-token P95 < 1.5 s under load.
- DB failover < 30 s automatically.
- Broker outage does not drop events (outbox catches up cleanly).
- Every runbook rehearsed and updated.

**Exit criteria:** All NFR targets in the architecture document validated with load and chaos artifacts.

---

## Sprint 29 — GA Launch

**Objective:** Cross the go-live line with billing, documentation, status page, and DR drill.

**Deliverables**
- Production readiness review passed.
- Documentation site (Docusaurus).
- Onboarding wizard polished (guided setup for CRM/Finance/Support).
- Billing live via Stripe (subscription + metered AI).
- Public status page with real health signals.
- Final DR drill: RTO ≤ 30 min, RPO ≤ 5 min validated.

**Dependencies:** Everything above.

**Files to create**
- `/apps/docs/` (docs site)
- `/apps/status/` (status page)
- `/services/api/src/modules/billing/{routes.py, services.py, stripe_client.py, models.py}`
- `/services/api/migrations/versions/0019_billing.py`
- `/ops/gameday-plans/dr-drill.md`
- `/docs/launch/prr-checklist.md`

**Backend modules:** `modules/billing`.
**Frontend modules:** onboarding wizard polish, docs site, status page.

**Database tables**
- `subscriptions(id, tenant_id, plan_id, status, current_period_start, current_period_end, stripe_subscription_id)`
- `billing_events(id, tenant_id, kind, payload_json, created_at)`
- `metered_usage(day, tenant_id, meter, quantity)`

**APIs**
- `POST /v1/billing/subscribe`
- `POST /v1/billing/portal-session`
- `POST /v1/billing/webhook` (Stripe)
- `GET /v1/billing/current`

**Validation checklist**
- DR drill: recover core stack within RTO in a secondary region.
- Test tenant flows through subscribe → invoice → paid → cancel.
- Docs cover every public API and connector.
- Status page reflects real synthetic and probe health.
- All P0/P1 bugs from the prior three sprints closed.

**Exit criteria:** First paid tenant onboarded successfully; 7-day incident-free soak; product marketing greenlit; launch executed.

---

# Cross-Cutting Appendices

## Parallelization Guide

The following pairs/trios can safely overlap once their dependencies are met:

- Sprint 5 (Audit/Events/Notifications) and Sprint 6 (Storage/Search/Cache) — different subsystems, no writes overlap.
- Sprint 7 (Web Shell) and Sprint 8 (Admin Console) — different apps, shared design system.
- Sprints 9, 10, 11 (CRM, Finance, Projects) — different modules, different DB namespaces. Same for sprints 12, 13, 14.
- Sprint 16 (Prompts/Guardrails) and Sprint 17 (RAG) — different subtrees under `ai-orchestrator`.
- Sprint 21 (Workflow Builder UI) and Sprint 22 (Integrations Hub) — mostly independent once Sprint 20 lands.
- Sprint 25 (Mobile) and Sprint 26 (Public API) — different clients, non-overlapping backend touches.

## Dependency Matrix (highest-value edges)

- Everything depends on Sprints 0–2.
- Every business module (9–14) depends on Sprints 3, 4, 5, 6, 7.
- Copilot (18) depends on 15, 16, 17, and any business module it should reason over.
- Workflow builder (21) depends on 20.
- Analytics reports (24) depends on 23.
- Mobile (25) depends on 3, 5, 9, 14, 18, 19.
- Public API (26) depends on 3, 5, 15, and modules to be exposed.
- Hardening (27) depends on all functional sprints.

## Risk Register (highlights)

| Risk | Sprint(s) most affected | Mitigation |
|---|---|---|
| Postgres RLS misconfiguration leaks tenants | 4, 5, 6, all modules | Fail-closed policies, cross-tenant test in CI, RLS-required lint |
| AI provider outage | 15, 18, 19 | Provider-agnostic gateway + fallback chain + budget-aware routing |
| Prompt regression on model upgrade | 16, 18 | Golden evals + blocked publish on regression |
| CDC lag on high-volume tenants | 23, 24 | Per-tenant publication + partitioned facts + backpressure |
| Cost overrun on AI | 15, 18, 19 | Per-tenant budgets, semantic cache, batching, self-hosted fallback |
| Long-running workflow drift | 20 | Durable runtime + step idempotency + reconciliation job |
| Mobile push token drift | 25 | Server-side re-registration on app open, dead-token pruning |

## Definition of Done (applied to every sprint)

1. All acceptance criteria in "Exit criteria" met and demoed.
2. Unit tests ≥ 80% on new code; integration tests for all new APIs.
3. E2E tests updated for user-visible changes.
4. Every new endpoint uses `require(...)`; RLS present on all new tenant-scoped tables.
5. Audit + events emitted for every mutation.
6. Dashboards + alerts committed for every new service.
7. Runbook written or updated where applicable.
8. Docs updated (docs site + AsyncAPI/OpenAPI).
9. Feature flag defined and defaulted off until rollout.
10. Post-sprint retro filed with action items assigned.

---

Roadmap complete. Awaiting your signal for the next stage (ADR pack, module deep-dives, or sprint 0 kickoff plan).