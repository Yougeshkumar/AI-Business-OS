# AI Business Operating System — API Specification

**Document type:** Production API contract (OpenAPI 3.1 standard)
**Companion to:** `ai-bos-architecture.md`, `ai-bos-roadmap.md`, `ai-bos-database-design.md`
**Version:** 1.0

---

## Table of Contents

1. API Overview
2. Standards & Conventions
3. Authentication & Security
4. Common Schemas
5. Error Standards
6. Module Endpoints (25 modules)
7. AI API Endpoints
8. File API Endpoints
9. Search API Endpoints
10. WebSocket Contracts
11. Webhook Contracts
12. Versioning & Deprecation Strategy

---

# 1. API Overview

## Base URL

```
Production:  https://api.aibos.io/v1
Staging:     https://api.staging.aibos.io/v1
Sandbox:     https://api.sandbox.aibos.io/v1
```

## Transport

All traffic over HTTPS (TLS 1.3). HTTP requests are rejected (not redirected). WebSocket connections use `wss://`.

## Content Types

- Request: `application/json` (default), `multipart/form-data` (file uploads), `text/event-stream` (SSE responses).
- Response: `application/json` (default), `text/event-stream` (AI streaming), `application/octet-stream` (file downloads), `application/pdf` (rendered documents).

## API Style

RESTful resource-oriented design. URLs use plural nouns. Actions that don't map cleanly to CRUD use sub-resource verbs (`/invoices/{id}/send`, `/deals/{id}/move`).

Internal service-to-service calls use gRPC (not documented here). The GraphQL endpoint (`/graphql`) is reserved for the admin console and is out of scope for this document.

---

# 2. Standards & Conventions

## 2.1 Naming

- URLs: `kebab-case` for multi-word resources (`/pipeline-stages`, `/leave-requests`).
- Query parameters: `snake_case` (`sort_by`, `created_after`).
- JSON fields: `snake_case` in request and response bodies.
- Headers: `Title-Case` for standard HTTP headers; `X-` prefix for custom headers (`X-Tenant-Id`, `X-Trace-Id`).

## 2.2 HTTP Methods

| Method | Semantics | Idempotent | Safe |
|---|---|---|---|
| GET | Read resource(s) | Yes | Yes |
| POST | Create resource or trigger action | No (unless Idempotency-Key) | No |
| PUT | Full replace | Yes | No |
| PATCH | Partial update (merge-patch) | Yes | No |
| DELETE | Remove resource (soft delete) | Yes | No |

## 2.3 URL Structure

```
/{version}/{module}/{resource}
/{version}/{module}/{resource}/{id}
/{version}/{module}/{resource}/{id}/{sub-resource}
/{version}/{module}/{resource}/{id}/{action-verb}
```

Examples:
```
GET    /v1/crm/deals
GET    /v1/crm/deals/{id}
POST   /v1/crm/deals/{id}/move
GET    /v1/crm/deals/{id}/activities
POST   /v1/finance/invoices/{id}/send
```

## 2.4 Response Envelope

Every JSON response uses a consistent envelope.

**Success (single resource):**
```json
{
  "data": { "..." },
  "meta": {
    "request_id": "req_abc123",
    "trace_id": "tr_xyz789",
    "timestamp": "2026-07-09T12:00:00Z"
  }
}
```

**Success (collection):**
```json
{
  "data": [ "..." ],
  "meta": {
    "request_id": "req_abc123",
    "trace_id": "tr_xyz789",
    "timestamp": "2026-07-09T12:00:00Z"
  },
  "pagination": {
    "cursor": "eyJpZCI6IjEyMyJ9",
    "has_more": true,
    "total_count": 1482
  }
}
```

**Error:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": "2 field(s) invalid",
    "field_errors": [
      { "field": "email", "code": "INVALID_FORMAT", "message": "Must be a valid email address" },
      { "field": "amount", "code": "OUT_OF_RANGE", "message": "Must be greater than 0" }
    ],
    "trace_id": "tr_xyz789",
    "timestamp": "2026-07-09T12:00:00Z",
    "doc_url": "https://docs.aibos.io/errors/VALIDATION_ERROR"
  }
}
```

## 2.5 Pagination

**Cursor-based** (default for all list endpoints). Keyset pagination on `(id)` or `(sort_col, id)`.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `limit` | integer | 25 | Items per page (max 100) |
| `cursor` | string | null | Opaque cursor from previous response |
| `direction` | string | `after` | `after` (forward) or `before` (backward) |

Response includes `pagination.cursor`, `pagination.has_more`, and optionally `pagination.total_count` (only when `include_count=true`).

## 2.6 Filtering

Filters are query parameters on list endpoints. Convention: `{field}` for equality, `{field}_{operator}` for comparison.

| Operator suffix | Meaning | Example |
|---|---|---|
| _(none)_ | equals | `status=active` |
| `_not` | not equals | `status_not=archived` |
| `_in` | in set (comma-separated) | `status_in=active,past_due` |
| `_gt` / `_gte` | greater than / >= | `amount_gt=1000` |
| `_lt` / `_lte` | less than / <= | `created_at_lte=2026-06-01` |
| `_contains` | substring (case-insensitive) | `name_contains=acme` |
| `_starts_with` | prefix | `email_starts_with=john` |
| `_is_null` | null check | `assignee_id_is_null=true` |

Multiple filters are AND-joined.

## 2.7 Sorting

| Parameter | Type | Default | Description |
|---|---|---|---|
| `sort_by` | string | `created_at` | Field to sort by |
| `sort_order` | string | `desc` | `asc` or `desc` |

Multi-sort: `sort_by=priority,-created_at` (prefix `-` for descending). Maximum 3 sort fields.

## 2.8 Sparse Fieldsets

`fields=id,name,status,created_at` — returns only the listed fields (plus `id` always).

## 2.9 Idempotency

All `POST` endpoints that create resources accept an `Idempotency-Key` header (client-generated, max 128 chars, 24h TTL). Replay within TTL returns original response with `X-Idempotent-Replayed: true`. Key collision with different body → `409 Conflict`.

## 2.10 Optimistic Concurrency

Mutable resources return `ETag` (from `version` column). `PATCH`/`DELETE` require `If-Match`. Stale writes → `412 Precondition Failed`.

## 2.11 Bulk & Batch

```
POST /v1/{module}/{resource}/bulk
```
Array of operations (max 100). Response includes per-item status. `X-Batch-Transaction: true` for all-or-nothing.

## 2.12 Async / Long-Running Operations

Operations exceeding 30s return `202 Accepted` with a `Job` resource. Poll `GET /v1/jobs/{job_id}` or subscribe via WebSocket.

## 2.13 Rate Limiting

| Tier | Requests/min | Burst | AI Requests/min |
|---|---|---|---|
| Free | 60 | 10 | 10 |
| Pro | 300 | 50 | 60 |
| Business | 1000 | 200 | 200 |
| Enterprise | 5000 | 1000 | 1000 |

Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `X-RateLimit-Policy`. Exceeded → `429 Too Many Requests` with `Retry-After`.

## 2.14 Standard Request Headers

| Header | Required | Description |
|---|---|---|
| `Authorization` | Yes (except public) | `Bearer <jwt>` or `Api-Key <key>` |
| `Content-Type` | Yes (body requests) | `application/json` |
| `Accept` | No | `application/json` (default) |
| `Idempotency-Key` | Conditional | Required on POST create/action |
| `If-Match` | Conditional | ETag for PATCH/DELETE |
| `X-Tenant-Id` | No | Override for multi-org users |
| `X-Request-Id` | No | Client-supplied, echoed in response |

## 2.15 Standard Response Headers

`X-Request-Id`, `X-Trace-Id`, `ETag`, `X-RateLimit-*`, `X-Idempotent-Replayed`, `Cache-Control`, `Content-Type`.

---

# 3. Authentication & Security

## 3.1 JWT Bearer Token (primary)

```
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
```

Claims: `sub`, `tenant_id`, `roles[]`, `scopes[]`, `session_id`, `token_use=access`, `iss`, `aud`, `iat`, `exp`. RS256 with rotating JWKS. TTL: 10 min.

## 3.2 API Key (developers/integrations)

```
Authorization: Api-Key aibos_live_sk_a1b2c3d4...
```

Prefix encodes environment. Hashed at rest (SHA-256), scoped by permissions and IP allow-list.

## 3.3 OAuth 2.0 (third-party)

Authorization Code + PKCE. Scopes mirror permission catalog (`crm.deals.read`, `finance.invoices.write`). Wildcard: `crm.*`, `*.read`.

## 3.4 Authorization Model

Every endpoint declares `permission: {resource}.{action}`. Gateway evaluates: token valid → tenant match → permission check → scope check → ABAC conditions. Denied → `403 Forbidden`.

## 3.5 Tenant Isolation

JWT `tenant_id` stamped into DB session via RLS GUC. API keys scoped to single tenant. Cross-tenant impossible.

---

# 4. Common Schemas

```yaml
UUID:
  type: string
  format: uuid

Timestamp:
  type: string
  format: date-time
  description: "ISO 8601, always UTC"

DateOnly:
  type: string
  format: date

Money:
  type: object
  required: [amount, currency]
  properties:
    amount: { type: string, pattern: "^-?\\d+\\.\\d{2,4}$" }
    currency: { type: string, minLength: 3, maxLength: 3 }

Address:
  type: object
  properties:
    line1: { type: string }
    line2: { type: string }
    city: { type: string }
    state: { type: string }
    postal_code: { type: string }
    country: { type: string, minLength: 2, maxLength: 2 }

PaginationParams:
  type: object
  properties:
    limit: { type: integer, minimum: 1, maximum: 100, default: 25 }
    cursor: { type: string, nullable: true }
    direction: { type: string, enum: [after, before], default: after }

PaginationResponse:
  type: object
  properties:
    cursor: { type: string, nullable: true }
    has_more: { type: boolean }
    total_count: { type: integer, nullable: true }

ResponseMeta:
  type: object
  properties:
    request_id: { type: string }
    trace_id: { type: string }
    timestamp: { $ref: Timestamp }

AuditFields:
  type: object
  properties:
    created_at: { $ref: Timestamp }
    updated_at: { $ref: Timestamp }
    created_by: { $ref: UUID, nullable: true }
    updated_by: { $ref: UUID, nullable: true }
    version: { type: integer }

FileRef:
  type: object
  properties:
    id: { $ref: UUID }
    filename: { type: string }
    mime_type: { type: string }
    size_bytes: { type: integer }
    url: { type: string, format: uri }

UserSummary:
  type: object
  properties:
    id: { $ref: UUID }
    email: { type: string, format: email }
    full_name: { type: string, nullable: true }
    avatar_url: { type: string, nullable: true }

TenantSummary:
  type: object
  properties:
    id: { $ref: UUID }
    name: { type: string }
    slug: { type: string }
    plan: { type: string }
    status: { type: string, enum: [trial, active, past_due, suspended] }

Job:
  type: object
  properties:
    job_id: { type: string }
    status: { type: string, enum: [pending, processing, succeeded, failed, cancelled] }
    progress: { type: integer, minimum: 0, maximum: 100 }
    result: { type: object, nullable: true }
    result_url: { type: string, nullable: true }
    error: { $ref: ErrorResponse, nullable: true }
    created_at: { $ref: Timestamp }
    completed_at: { $ref: Timestamp, nullable: true }
```

---

# 5. Error Standards

## 5.1 Error Response Schema

```yaml
ErrorResponse:
  type: object
  required: [code, message, trace_id, timestamp]
  properties:
    code: { type: string }
    message: { type: string }
    details: { type: string, nullable: true }
    field_errors:
      type: array
      nullable: true
      items: { $ref: FieldError }
    trace_id: { type: string }
    timestamp: { $ref: Timestamp }
    doc_url: { type: string, format: uri, nullable: true }

FieldError:
  type: object
  required: [field, code, message]
  properties:
    field: { type: string, description: "JSON path" }
    code: { type: string }
    message: { type: string }
```

## 5.2 Error Code Catalog

| HTTP | Code | When |
|---|---|---|
| 400 | `BAD_REQUEST` | Malformed JSON, missing content-type |
| 400 | `VALIDATION_ERROR` | Field validation failed (with `field_errors`) |
| 401 | `UNAUTHENTICATED` | Missing or invalid token |
| 401 | `TOKEN_EXPIRED` | JWT expired |
| 401 | `MFA_REQUIRED` | Step-up MFA needed |
| 403 | `FORBIDDEN` | Lacking permission |
| 403 | `TENANT_SUSPENDED` | Tenant suspended |
| 403 | `BUDGET_EXCEEDED` | AI budget cap reached |
| 404 | `NOT_FOUND` | Resource not found |
| 409 | `CONFLICT` | Duplicate or idempotency mismatch |
| 409 | `STATE_CONFLICT` | Invalid state transition |
| 412 | `PRECONDITION_FAILED` | ETag mismatch |
| 413 | `PAYLOAD_TOO_LARGE` | Body exceeds limit |
| 422 | `BUSINESS_RULE_VIOLATION` | Domain rule prevented operation |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Server error |
| 502 | `UPSTREAM_ERROR` | Dependency failure |
| 503 | `SERVICE_UNAVAILABLE` | Temporarily unavailable |

Global error responses (401, 403, 429, 500, 503) apply to every endpoint and are not repeated in per-endpoint documentation below.

---

# 6. Module Endpoints

> **Documentation convention for this section.** Each endpoint is specified with: method, URL, summary, description, auth, permission, headers, parameters, request body, response body (status + schema), validation rules, error responses (module-specific), rate limit tier. Global errors (401/403/429/500/503) and standard headers (§2.14–2.15) apply to all and are not repeated.

---

## 6.1 Authentication

### POST /v1/auth/register
- **Summary:** Register a new user (self-serve tenant creation)
- **Auth:** None (public)
- **Permission:** None
- **Idempotency:** Required
- **Request Body:**
```yaml
type: object
required: [email, password, full_name, tenant_name]
properties:
  email: { type: string, format: email, maxLength: 254 }
  password: { type: string, minLength: 12, maxLength: 128 }
  full_name: { type: string, minLength: 1, maxLength: 200 }
  tenant_name: { type: string, minLength: 2, maxLength: 100 }
  tenant_slug: { type: string, pattern: "^[a-z0-9-]{3,50}$" }
  locale: { type: string, default: "en" }
  timezone: { type: string, default: "UTC" }
```
- **Validation:** Password must include upper, lower, digit, symbol. Email must be unique. Slug must be unique. Breached-password check (HIBP k-anonymity).
- **Response:** `201 Created`
```yaml
data:
  user: { $ref: UserSummary }
  tenant: { $ref: TenantSummary }
  access_token: { type: string }
  refresh_token: { type: string }
  expires_in: { type: integer, description: "seconds" }
```
- **Errors:** `409 CONFLICT` (email/slug taken), `400 VALIDATION_ERROR`
- **Rate Limit:** 5/min per IP

### POST /v1/auth/login
- **Summary:** Authenticate user with credentials
- **Auth:** None (public)
- **Request Body:**
```yaml
required: [email, password]
properties:
  email: { type: string, format: email }
  password: { type: string }
  device_info: { type: object, properties: { name: string, type: string } }
```
- **Response:** `200 OK`
```yaml
data:
  access_token: { type: string }
  refresh_token: { type: string }
  expires_in: { type: integer }
  user: { $ref: UserSummary }
  tenant: { $ref: TenantSummary }
  mfa_required: { type: boolean }
  mfa_challenge_token: { type: string, nullable: true }
```
- **Errors:** `401 UNAUTHENTICATED` (bad credentials), `403 TENANT_SUSPENDED`, `423 ACCOUNT_LOCKED` (after 5 failures)
- **Rate Limit:** 10/min per IP-email pair

### POST /v1/auth/callback
- **Summary:** OIDC/SSO callback
- **Auth:** None (redirect from IdP)
- **Query Params:** `code`, `state`
- **Response:** `200 OK` — same as login response
- **Errors:** `400 BAD_REQUEST` (invalid code/state)

### POST /v1/auth/refresh
- **Summary:** Refresh access token
- **Auth:** None (uses refresh token in body)
- **Request Body:**
```yaml
required: [refresh_token]
properties:
  refresh_token: { type: string }
```
- **Response:** `200 OK` — new access_token + rotated refresh_token
- **Errors:** `401 TOKEN_EXPIRED`, `401 UNAUTHENTICATED` (reuse detected → entire session revoked)

### POST /v1/auth/logout
- **Summary:** Revoke current session
- **Auth:** Bearer JWT
- **Response:** `204 No Content`

### POST /v1/auth/mfa/enroll
- **Summary:** Begin TOTP MFA enrollment
- **Auth:** Bearer JWT
- **Permission:** `self`
- **Response:** `200 OK` — `{ data: { secret, otpauth_uri, qr_code_url } }`

### POST /v1/auth/mfa/verify
- **Summary:** Verify TOTP code (enrollment confirmation or login challenge)
- **Auth:** Bearer JWT or MFA challenge token
- **Request Body:** `{ code: "123456" }`
- **Response:** `200 OK` — `{ data: { verified: true } }` (on login: returns full token set)
- **Errors:** `401 UNAUTHENTICATED` (bad code)

### DELETE /v1/auth/mfa
- **Summary:** Disable MFA
- **Auth:** Bearer JWT + step-up MFA
- **Permission:** `self`
- **Response:** `204 No Content`

### POST /v1/auth/password/reset-request
- **Summary:** Request password reset email
- **Auth:** None (public)
- **Request Body:** `{ email: "..." }`
- **Response:** `202 Accepted` (always, to prevent email enumeration)
- **Rate Limit:** 3/min per email

### POST /v1/auth/password/reset-confirm
- **Summary:** Set new password with reset token
- **Auth:** None (token in body)
- **Request Body:** `{ token: "...", new_password: "..." }`
- **Response:** `200 OK`
- **Errors:** `401 UNAUTHENTICATED` (bad/expired token), `400 VALIDATION_ERROR`

### GET /v1/auth/sessions
- **Summary:** List active sessions for current user
- **Auth:** Bearer JWT
- **Response:** `200 OK` — array of `{ id, device, ip, last_seen_at, current: boolean }`

### DELETE /v1/auth/sessions/{session_id}
- **Summary:** Revoke a specific session
- **Auth:** Bearer JWT
- **Permission:** `self` (own sessions only)
- **Response:** `204 No Content`

### GET /v1/auth/me
- **Summary:** Get current user profile with tenant and permissions
- **Auth:** Bearer JWT
- **Response:** `200 OK`
```yaml
data:
  user: { full User object }
  tenant: { $ref: TenantSummary }
  permissions: { type: array, items: string }
  feature_flags: { type: object }
```

---

## 6.2 Users

### GET /v1/users
- **Summary:** List users in current tenant
- **Permission:** `users.read`
- **Query Params:** `status`, `role_id`, `department_id`, `search` (name/email), `sort_by`, `sort_order`, `limit`, `cursor`, `fields`
- **Response:** `200 OK` — paginated array of User objects

### POST /v1/users
- **Summary:** Create user (admin invite)
- **Permission:** `users.write`
- **Idempotency:** Required
- **Request Body:**
```yaml
required: [email, role_id]
properties:
  email: { type: string, format: email }
  full_name: { type: string }
  role_id: { $ref: UUID }
  department_id: { $ref: UUID, nullable: true }
  locale: { type: string }
  timezone: { type: string }
```
- **Response:** `201 Created` — User object (invitation sent automatically)
- **Errors:** `409 CONFLICT` (email exists)

### GET /v1/users/{id}
- **Summary:** Get user by ID
- **Permission:** `users.read`
- **Path Params:** `id` (UUID)
- **Response:** `200 OK` — full User object with roles, department, team memberships

### PATCH /v1/users/{id}
- **Summary:** Update user
- **Permission:** `users.write`
- **Headers:** `If-Match` required
- **Request Body:** Partial User fields (full_name, status, locale, timezone)
- **Response:** `200 OK` — updated User
- **Errors:** `412 PRECONDITION_FAILED`

### DELETE /v1/users/{id}
- **Summary:** Deactivate user (soft delete)
- **Permission:** `users.delete`
- **Headers:** `If-Match` required
- **Response:** `204 No Content`
- **Errors:** `422 BUSINESS_RULE_VIOLATION` (cannot delete tenant owner)

### GET /v1/users/{id}/roles
- **Summary:** List roles assigned to a user
- **Permission:** `users.read`
- **Response:** `200 OK` — array of role grants with scope

### POST /v1/users/{id}/roles
- **Summary:** Assign role to user
- **Permission:** `roles.assign`
- **Request Body:** `{ role_id, scope_type, scope_id, expires_at }`
- **Response:** `201 Created`

### DELETE /v1/users/{id}/roles/{role_id}
- **Summary:** Remove role from user
- **Permission:** `roles.assign`
- **Response:** `204 No Content`

### GET /v1/me/preferences
- **Summary:** Get current user preferences
- **Permission:** `self`
- **Response:** `200 OK` — preferences object

### PUT /v1/me/preferences
- **Summary:** Update current user preferences
- **Permission:** `self`
- **Request Body:** `{ theme, locale, timezone, layout_density, default_module }`
- **Response:** `200 OK`

---

## 6.3 Organizations

### GET /v1/organizations
- **Permission:** `organizations.read`
- **Query Params:** `parent_id`, `search`, pagination
- **Response:** `200 OK` — paginated array

### POST /v1/organizations
- **Permission:** `organizations.write`
- **Request Body:** `{ name, parent_id (nullable) }`
- **Response:** `201 Created`

### GET /v1/organizations/{id}
- **Permission:** `organizations.read`
- **Response:** `200 OK` — org with children summary

### PATCH /v1/organizations/{id}
- **Permission:** `organizations.write`
- **Headers:** `If-Match`
- **Response:** `200 OK`

### DELETE /v1/organizations/{id}
- **Permission:** `organizations.delete`
- **Response:** `204 No Content`
- **Errors:** `422 BUSINESS_RULE_VIOLATION` (has departments with employees)

### GET /v1/organizations/{id}/tree
- **Summary:** Get full org hierarchy tree
- **Permission:** `organizations.read`
- **Response:** `200 OK` — nested tree structure

---

## 6.4 Departments

### GET /v1/departments
- **Permission:** `departments.read`
- **Query Params:** `organization_id`, `search`, pagination
- **Response:** `200 OK`

### POST /v1/departments
- **Permission:** `departments.write`
- **Request Body:** `{ name, organization_id }`
- **Response:** `201 Created`

### GET /v1/departments/{id}
- **Permission:** `departments.read`
- **Response:** `200 OK`

### PATCH /v1/departments/{id}
- **Permission:** `departments.write`
- **Response:** `200 OK`

### DELETE /v1/departments/{id}
- **Permission:** `departments.delete`
- **Response:** `204 No Content`

---

## 6.5 Teams

### GET /v1/teams
- **Permission:** `teams.read`
- **Query Params:** `department_id`, `search`, pagination
- **Response:** `200 OK`

### POST /v1/teams
- **Permission:** `teams.write`
- **Request Body:** `{ name, department_id }`
- **Response:** `201 Created`

### GET /v1/teams/{id}
- **Permission:** `teams.read`
- **Response:** `200 OK` — team with members

### PATCH /v1/teams/{id}
- **Permission:** `teams.write`
- **Response:** `200 OK`

### DELETE /v1/teams/{id}
- **Permission:** `teams.delete`
- **Response:** `204 No Content`

### POST /v1/teams/{id}/members
- **Summary:** Add member to team
- **Permission:** `teams.write`
- **Request Body:** `{ user_id, role }`
- **Response:** `201 Created`

### DELETE /v1/teams/{id}/members/{user_id}
- **Permission:** `teams.write`
- **Response:** `204 No Content`

---

## 6.6 Roles & Permissions (Workspaces / RBAC)

### GET /v1/roles
- **Permission:** `roles.read`
- **Query Params:** `is_system`, pagination
- **Response:** `200 OK` — roles with permission count

### POST /v1/roles
- **Summary:** Create custom role
- **Permission:** `roles.write`
- **Request Body:** `{ name, description, permission_ids[] }`
- **Response:** `201 Created`

### GET /v1/roles/{id}
- **Permission:** `roles.read`
- **Response:** `200 OK` — role with full permission list

### PATCH /v1/roles/{id}
- **Permission:** `roles.write`
- **Response:** `200 OK`
- **Errors:** `422 BUSINESS_RULE_VIOLATION` (cannot edit system roles)

### DELETE /v1/roles/{id}
- **Permission:** `roles.delete`
- **Response:** `204 No Content`
- **Errors:** `422 BUSINESS_RULE_VIOLATION` (role has users assigned)

### PUT /v1/roles/{id}/permissions
- **Summary:** Replace permissions on a role
- **Permission:** `roles.write`
- **Request Body:** `{ permission_ids: [UUID] }`
- **Response:** `200 OK`

### GET /v1/permissions
- **Summary:** List all available permissions
- **Permission:** `roles.read`
- **Response:** `200 OK` — full permission catalog (resource + action)

---

## 6.7 CRM

### Companies

**GET /v1/crm/companies** — List. Permission: `crm.companies.read`. Filters: `name_contains`, `industry`, `owner_id`, `created_at_gte/lte`. Sorting: `name`, `created_at`, `annual_revenue`.

**POST /v1/crm/companies** — Create. Permission: `crm.companies.write`. Request: `{ name*, domain, industry, size_bracket, annual_revenue: Money, owner_id, address: Address }`. Response: `201`. Errors: `409 CONFLICT` (duplicate domain).

**GET /v1/crm/companies/{id}** — Detail. Permission: `crm.companies.read`. Response includes contact count, deal summary.

**PATCH /v1/crm/companies/{id}** — Update. Permission: `crm.companies.write`. `If-Match` required.

**DELETE /v1/crm/companies/{id}** — Soft delete. Permission: `crm.companies.delete`. `If-Match` required. Errors: `422` if company has open invoices (RESTRICT from finance schema).

### Contacts

**GET /v1/crm/contacts** — Filters: `company_id`, `email_contains`, `owner_id`, `source`, `created_at_gte/lte`.

**POST /v1/crm/contacts** — Request: `{ first_name, last_name, email, phone, title, company_id, owner_id, source }`. Validation: email format. Duplicate detection returns `X-Duplicate-Candidates` header with IDs if fuzzy match found (not blocking).

**GET /v1/crm/contacts/{id}** — Includes company, deals, activities.

**PATCH /v1/crm/contacts/{id}** — `If-Match` required.

**DELETE /v1/crm/contacts/{id}** — `If-Match` required.

**POST /v1/crm/contacts/bulk** — Bulk create/update/delete (max 100).

### Leads

**GET /v1/crm/leads** — Filters: `status`, `owner_id`, `score_gte`, `source`, `created_at_gte/lte`.

**POST /v1/crm/leads** — Request: `{ contact_id, company_id, source, owner_id }`.

**GET /v1/crm/leads/{id}** — Includes enrichment data, score history.

**PATCH /v1/crm/leads/{id}** — `If-Match`.

**DELETE /v1/crm/leads/{id}** — `If-Match`.

**POST /v1/crm/leads/{id}/convert** — Convert to deal. Permission: `crm.leads.convert`. Request: `{ pipeline_id, stage_id, deal_title, amount: Money }`. Response: `200` with new deal object. Errors: `409 STATE_CONFLICT` (already converted).

**POST /v1/crm/leads/{id}/qualify** — Update status + score. Request: `{ status, score }`.

### Pipelines & Stages

**GET /v1/crm/pipelines** — List pipelines with stage summary.
**POST /v1/crm/pipelines** — `{ name, stages: [{ name, position, probability, is_won, is_lost }] }`.
**GET /v1/crm/pipelines/{id}** — Pipeline with full stage list.
**PATCH /v1/crm/pipelines/{id}** — `If-Match`.
**DELETE /v1/crm/pipelines/{id}** — Errors: `422` if pipeline has deals.

**GET /v1/crm/pipelines/{id}/stages** — List stages ordered by position.
**POST /v1/crm/pipelines/{id}/stages** — Add stage.
**PATCH /v1/crm/pipeline-stages/{id}** — Update stage.
**DELETE /v1/crm/pipeline-stages/{id}** — Errors: `422` if stage has deals.

### Deals

**GET /v1/crm/deals** — Filters: `pipeline_id`, `stage_id`, `owner_id`, `result`, `amount_gte/lte`, `expected_close_date_gte/lte`. Sorting: `amount`, `expected_close_date`, `created_at`.

**POST /v1/crm/deals** — Permission: `crm.deals.write`.
```yaml
required: [title, pipeline_id, stage_id]
properties:
  title: { type: string, maxLength: 300 }
  pipeline_id: { $ref: UUID }
  stage_id: { $ref: UUID }
  company_id: { $ref: UUID, nullable: true }
  primary_contact_id: { $ref: UUID, nullable: true }
  owner_id: { $ref: UUID }
  amount: { $ref: Money, nullable: true }
  expected_close_date: { $ref: DateOnly, nullable: true }
```
Response: `201 Created`.

**GET /v1/crm/deals/{id}** — Includes stage history, activities, associated contacts.

**PATCH /v1/crm/deals/{id}** — `If-Match` required.

**DELETE /v1/crm/deals/{id}** — `If-Match`.

**POST /v1/crm/deals/{id}/move** — Move to new stage. Permission: `crm.deals.write`. Request: `{ stage_id }`. Response: `200 OK`. Creates stage history entry. Errors: `409 STATE_CONFLICT` (deal already won/lost).

**POST /v1/crm/deals/{id}/win** — Mark as won. Request: `{ closed_amount: Money }`. Response: `200 OK`.

**POST /v1/crm/deals/{id}/lose** — Mark as lost. Request: `{ reason }`. Response: `200 OK`.

**GET /v1/crm/deals/{id}/stage-history** — List stage transitions.

### Activities

**GET /v1/crm/activities** — Filters: `subject_type` (lead/deal/contact/company), `subject_id`, `type` (note/call/email/meeting/task), `owner_id`, `due_at_gte/lte`.

**POST /v1/crm/activities** — Request: `{ type*, subject_type*, subject_id*, title, body, due_at, owner_id }`. Response: `201`.

**PATCH /v1/crm/activities/{id}** — `If-Match`.

**DELETE /v1/crm/activities/{id}** — `If-Match`.

**POST /v1/crm/activities/{id}/complete** — Mark activity completed.

---

## 6.8 Finance

### Chart of Accounts

**GET /v1/finance/accounts** — Permission: `finance.accounts.read`. Filters: `type` (asset/liability/equity/revenue/expense), `is_active`, `parent_id`.
**POST /v1/finance/accounts** — `{ code*, name*, type*, parent_id }`. Errors: `409 CONFLICT` (duplicate code).
**PATCH /v1/finance/accounts/{id}** — `If-Match`.
**DELETE /v1/finance/accounts/{id}** — Errors: `422` (has journal entries or children).

### Invoices

**GET /v1/finance/invoices** — Filters: `status`, `customer_id`, `due_date_gte/lte`, `amount_gte/lte`, `created_at_gte/lte`. Sorting: `number`, `due_date`, `total`, `created_at`.

**POST /v1/finance/invoices** — Permission: `finance.invoices.write`. Idempotency required.
```yaml
required: [customer_id, currency, items]
properties:
  customer_id: { $ref: UUID }
  currency: { type: string }
  issue_date: { $ref: DateOnly }
  due_date: { $ref: DateOnly }
  notes: { type: string }
  items:
    type: array
    minItems: 1
    maxItems: 500
    items:
      type: object
      required: [description, quantity, unit_price]
      properties:
        description: { type: string, maxLength: 1000 }
        quantity: { type: string, pattern: "^\\d+\\.?\\d*$" }
        unit_price: { type: string, pattern: "^\\d+\\.\\d{2,4}$" }
        tax_rule_id: { $ref: UUID, nullable: true }
```
Response: `201 Created` — Invoice with computed subtotal, tax_total, total, auto-assigned `number`.
Validation: quantity > 0, unit_price >= 0, at least 1 item. Number is gapless and auto-generated.

**GET /v1/finance/invoices/{id}** — Full invoice with items, payments allocated, PDF URL.

**PATCH /v1/finance/invoices/{id}** — Only when status=draft. `If-Match`. Errors: `409 STATE_CONFLICT` (not in draft).

**DELETE /v1/finance/invoices/{id}** — Only when status=draft. `If-Match`.

**POST /v1/finance/invoices/{id}/send** — Permission: `finance.invoices.send`. Transitions draft→sent. Triggers email delivery. Response: `200 OK`.

**POST /v1/finance/invoices/{id}/void** — Permission: `finance.invoices.void`. Transitions to void. Errors: `409 STATE_CONFLICT` (can't void a paid invoice). Creates offsetting journal entries.

**POST /v1/finance/invoices/{id}/mark-paid** — Manual payment recording. Request: `{ amount: Money, method, reference }`. Creates payment + allocation. Response: `200 OK`.

**GET /v1/finance/invoices/{id}/pdf** — Returns `application/pdf`. Cache: `Cache-Control: private, max-age=3600`. Generates on first call, caches thereafter.

### Quotes

**GET /v1/finance/quotes** — Same filter/sort pattern as invoices.
**POST /v1/finance/quotes** — Same shape as invoice creation.
**GET /v1/finance/quotes/{id}**
**PATCH /v1/finance/quotes/{id}** — Only when status=draft.
**DELETE /v1/finance/quotes/{id}**
**POST /v1/finance/quotes/{id}/send** — Transitions draft→sent.
**POST /v1/finance/quotes/{id}/convert-to-invoice** — Creates invoice from quote. Response: `201 Created` — new Invoice.

### Payments

**GET /v1/finance/payments** — Filters: `status`, `customer_id`, `method`, `received_at_gte/lte`.
**POST /v1/finance/payments** — `{ customer_id*, amount: Money*, method*, external_ref }`.
**GET /v1/finance/payments/{id}** — With allocations.
**POST /v1/finance/payments/{id}/allocate** — `{ invoice_id, amount }`. Errors: `422` (over-allocation).
**POST /v1/finance/payments/{id}/refund** — `{ amount }`.

### Expenses

**GET /v1/finance/expenses** — Filters: `category_id`, `submitted_by`, `spent_at_gte/lte`.
**POST /v1/finance/expenses** — `{ category_id, amount: Money, spent_at, vendor, receipt_file_id }`.
**PATCH /v1/finance/expenses/{id}**
**DELETE /v1/finance/expenses/{id}**

### Tax Rules

**GET /v1/finance/tax-rules** — Filters: `region_id`, `is_active`.
**POST /v1/finance/tax-rules** — `{ region_id, name, rate, category }`.
**PATCH /v1/finance/tax-rules/{id}**

### Journal Entries (read-only, system-generated)

**GET /v1/finance/journal-entries** — Permission: `finance.journal.read`. Filters: `account_id`, `batch_id`, `entered_at_gte/lte`. Sorting: `entered_at`.

---

## 6.9 Projects

**GET /v1/projects** — Filters: `status`, `owner_id`, `start_date_gte/lte`. Sorting: `name`, `start_date`, `created_at`.

**POST /v1/projects** — Permission: `projects.write`.
```yaml
required: [name, key]
properties:
  name: { type: string, maxLength: 200 }
  key: { type: string, pattern: "^[A-Z]{2,6}$" }
  description: { type: string }
  owner_id: { $ref: UUID }
  start_date: { $ref: DateOnly }
  end_date: { $ref: DateOnly }
  budget_amount: { $ref: Money, nullable: true }
```
Errors: `409 CONFLICT` (duplicate key).

**GET /v1/projects/{id}** — Full project with stats (task counts by status, time logged).

**PATCH /v1/projects/{id}** — `If-Match`.

**DELETE /v1/projects/{id}** — Soft-deletes project and cascades to tasks.

**GET /v1/projects/{id}/gantt** — Returns tasks with dependencies formatted for Gantt rendering.

---

## 6.10 Tasks

**GET /v1/projects/{project_id}/tasks** — Filters: `status`, `priority`, `assignee_id`, `milestone_id`, `parent_task_id`, `due_date_gte/lte`. Sorting: `position`, `priority`, `due_date`, `created_at`.

**POST /v1/projects/{project_id}/tasks** — Permission: `tasks.write`.
```yaml
required: [title]
properties:
  title: { type: string, maxLength: 500 }
  description: { type: string }
  status: { type: string, enum: [todo, in_progress, blocked, in_review, done], default: todo }
  priority: { type: string, enum: [low, medium, high, urgent], default: medium }
  parent_task_id: { $ref: UUID, nullable: true }
  milestone_id: { $ref: UUID, nullable: true }
  assignee_ids: { type: array, items: UUID }
  start_date: { $ref: DateOnly }
  due_date: { $ref: DateOnly }
  estimate_hours: { type: number }
  position: { type: integer }
```

**GET /v1/tasks/{id}** — Full task with subtasks, assignees, watchers, comments, time entries.

**PATCH /v1/tasks/{id}** — `If-Match`.

**DELETE /v1/tasks/{id}** — `If-Match`. Cascades to subtasks.

**POST /v1/tasks/{id}/move** — Change status/position (kanban). Request: `{ status, position }`.

**POST /v1/tasks/{id}/assign** — `{ user_ids: [UUID] }`.

**POST /v1/tasks/{id}/complete** — Transitions to done.

**POST /v1/tasks/{id}/log-time** — Permission: `time_entries.write`. Request: `{ started_at, ended_at, duration_minutes, note }`. Validation: no overlapping entries for same user.

**GET /v1/tasks/{id}/comments** — List comments.
**POST /v1/tasks/{id}/comments** — `{ body }`.
**PATCH /v1/task-comments/{id}** — Edit own comment.
**DELETE /v1/task-comments/{id}** — Delete own comment.

### Milestones

**GET /v1/projects/{project_id}/milestones**
**POST /v1/projects/{project_id}/milestones** — `{ name, due_date, status }`.
**PATCH /v1/milestones/{id}**
**DELETE /v1/milestones/{id}**

### Task Dependencies

**POST /v1/tasks/{id}/dependencies** — `{ predecessor_id, type }`. Validation: cycle detection. Errors: `422 BUSINESS_RULE_VIOLATION` (would create cycle).
**DELETE /v1/task-dependencies/{id}**

### Timesheets

**GET /v1/timesheets** — Permission: `time_entries.read`. Query: `user_id`, `from` (date), `to` (date). Returns grouped time entries.

---

## 6.11 HR

### Employees

**GET /v1/hr/employees** — Filters: `status`, `department_id`, `manager_id`, `job_title_id`. Sorting: `full_name`, `hired_at`.
**POST /v1/hr/employees** — `{ employee_code*, first_name*, last_name*, work_email, job_title_id, manager_id, department_id, user_id, hired_at }`. Errors: `409 CONFLICT` (duplicate code).
**GET /v1/hr/employees/{id}** — Includes hierarchy, leave balances.
**PATCH /v1/hr/employees/{id}** — `If-Match`.
**DELETE /v1/hr/employees/{id}** — `If-Match`. Errors: `422` (has open payroll items).

**GET /v1/hr/employees/{id}/hierarchy** — Returns reporting tree.

### Attendance

**POST /v1/hr/attendance/clock-in** — Permission: `attendance.write`. Request: `{ employee_id, geo: { lat, lng }, source }`. Validation: not already clocked in.
**POST /v1/hr/attendance/clock-out** — `{ employee_id, geo }`. Validation: must be clocked in.
**GET /v1/hr/attendance** — Filters: `employee_id`, `date_gte/lte`. Permission: `attendance.read`.
**GET /v1/hr/attendance/daily-summary** — Aggregated view. Filters: `employee_id`, `date`.

### Leave

**GET /v1/hr/leave-types** — List leave types.
**POST /v1/hr/leave-types** — `{ name, accrual_config, is_paid }`.

**GET /v1/hr/leave-requests** — Filters: `employee_id`, `status`, `leave_type_id`, `start_date_gte/lte`.
**POST /v1/hr/leave-requests** — `{ employee_id, leave_type_id*, start_date*, end_date*, reason }`. Validation: end >= start, no overlap with approved/requested leaves, sufficient balance.
**POST /v1/hr/leave-requests/{id}/approve** — Permission: `leave.approve`. Response: `200 OK`. Updates balance atomically.
**POST /v1/hr/leave-requests/{id}/deny** — Permission: `leave.approve`. Request: `{ reason }`.
**POST /v1/hr/leave-requests/{id}/cancel** — Only by requester, only if status=requested.

**GET /v1/hr/leave-balances** — Filters: `employee_id`, `leave_type_id`.

### Payroll

**GET /v1/hr/payroll-runs** — Filters: `status`, `period_month`.
**POST /v1/hr/payroll-runs** — `{ period_month }`. Errors: `409 CONFLICT` (period already exists).
**GET /v1/hr/payroll-runs/{id}** — With items.
**POST /v1/hr/payroll-runs/{id}/close** — Permission: `payroll.close`. Transitions draft→closed. Creates journal entries. Idempotent.
**POST /v1/hr/payroll-runs/{id}/reverse** — Permission: `payroll.reverse`. Only within 48h. Creates offsetting entries.

**GET /v1/hr/payroll-runs/{id}/items** — List payroll items.
**POST /v1/hr/payroll-runs/{id}/items** — `{ employee_id, component, amount: Money }`.
**PATCH /v1/hr/payroll-items/{id}** — Only when run status=draft.
**DELETE /v1/hr/payroll-items/{id}** — Only when run status=draft.

### Reviews

**GET /v1/hr/review-cycles**
**POST /v1/hr/review-cycles** — `{ name, start_date, end_date }`.
**POST /v1/hr/review-cycles/{id}/forms** — `{ schema_json }`.
**POST /v1/hr/reviews** — `{ form_id, employee_id, reviewer_id }`.
**PATCH /v1/hr/reviews/{id}** — `{ answers_json }`.
**POST /v1/hr/reviews/{id}/submit** — Transitions draft→submitted.

---

## 6.12 Inventory

### Products & SKUs

**GET /v1/inventory/products** — Filters: `category`, `is_active`, `name_contains`.
**POST /v1/inventory/products** — `{ name*, description, category }`.
**PATCH /v1/inventory/products/{id}**
**DELETE /v1/inventory/products/{id}**

**GET /v1/inventory/products/{id}/skus** — List variants.
**POST /v1/inventory/products/{id}/skus** — `{ sku_code*, barcode, attributes: {}, unit_cost: Money, reorder_point, allow_negative }`. Errors: `409 CONFLICT` (duplicate code).
**PATCH /v1/inventory/skus/{id}**

### Warehouses

**GET /v1/inventory/warehouses**
**POST /v1/inventory/warehouses** — `{ name*, code*, address }`.
**PATCH /v1/inventory/warehouses/{id}**

### Suppliers

**GET /v1/inventory/suppliers**
**POST /v1/inventory/suppliers** — `{ name*, contact_info }`.
**PATCH /v1/inventory/suppliers/{id}**

### Stock

**GET /v1/inventory/stock** — Query: `sku_id`, `warehouse_id`. Returns current on-hand, reserved quantities.
**POST /v1/inventory/movements/adjust** — `{ sku_id*, warehouse_id*, quantity*, unit_cost, reason }`. Validation: quantity != 0, no negative stock unless `allow_negative`.
**POST /v1/inventory/movements/transfer** — `{ sku_id*, from_warehouse_id*, to_warehouse_id*, quantity* }`. Validation: sufficient stock in source.
**POST /v1/inventory/movements/receive** — `{ sku_id*, warehouse_id*, quantity*, unit_cost, po_id }`.
**POST /v1/inventory/movements/ship** — `{ sku_id*, warehouse_id*, quantity*, reference_type, reference_id }`.

**GET /v1/inventory/stock-movements** — Filters: `sku_id`, `warehouse_id`, `kind`, `moved_at_gte/lte`. Append-only, no PATCH/DELETE.

### Purchase Orders

**GET /v1/inventory/purchase-orders** — Filters: `status`, `supplier_id`, `expected_at_gte/lte`.
**POST /v1/inventory/purchase-orders** — `{ supplier_id*, warehouse_id*, currency, expected_at, items: [{ sku_id, quantity, unit_cost }] }`.
**GET /v1/inventory/purchase-orders/{id}** — With items, receipts.
**PATCH /v1/inventory/purchase-orders/{id}** — Only when draft.
**POST /v1/inventory/purchase-orders/{id}/send** — Transitions draft→sent.
**POST /v1/inventory/purchase-orders/{id}/receive** — Records receipt, creates stock movements. Request: `{ items: [{ po_item_id, received_quantity }] }`.
**POST /v1/inventory/purchase-orders/{id}/close**

---

## 6.13 Support Desk

### Tickets

**GET /v1/support/tickets** — Permission: `support.tickets.read`. Filters: `status`, `priority`, `assignee_id`, `requester_contact_id`, `created_at_gte/lte`. Sorting: `priority`, `created_at`, `resolution_due_at`.

**POST /v1/support/tickets** — Permission: `support.tickets.write`.
```yaml
required: [subject]
properties:
  subject: { type: string, maxLength: 500 }
  body: { type: string }
  priority: { type: string, enum: [low, normal, high, urgent], default: normal }
  requester_contact_id: { $ref: UUID, nullable: true }
  assignee_id: { $ref: UUID, nullable: true }
  sla_policy_id: { $ref: UUID, nullable: true }
  tags: { type: array, items: string }
```
Auto-assigns SLA deadlines if `sla_policy_id` provided.

**GET /v1/support/tickets/{id}** — Full ticket with messages, SLA state.

**PATCH /v1/support/tickets/{id}** — `If-Match`.

**POST /v1/support/tickets/{id}/reply** — Permission: `support.tickets.reply`. Request: `{ body*, kind (public_reply | internal_note), attachments: [file_id] }`.

**POST /v1/support/tickets/{id}/assign** — `{ assignee_id }`.

**POST /v1/support/tickets/{id}/close** — Transitions to closed. Errors: `409 STATE_CONFLICT` (already closed).

**POST /v1/support/tickets/{id}/reopen** — Transitions closed→open.

**GET /v1/support/tickets/{id}/messages** — Paginated thread.

**GET /v1/support/tickets/{id}/sla** — Current SLA state and timestamps.

### SLA Policies

**GET /v1/support/sla-policies**
**POST /v1/support/sla-policies** — `{ name, first_response_minutes, resolution_minutes, business_hours }`.
**PATCH /v1/support/sla-policies/{id}**

### Canned Responses

**GET /v1/support/canned-responses**
**POST /v1/support/canned-responses** — `{ title, body }`.
**PATCH /v1/support/canned-responses/{id}**
**DELETE /v1/support/canned-responses/{id}**

### Knowledge Base

**GET /v1/support/kb/articles** — Filters: `is_public`, `search`.
**POST /v1/support/kb/articles** — `{ title*, slug*, body*, is_public }`. Errors: `409 CONFLICT` (duplicate slug).
**GET /v1/support/kb/articles/{id}** — Includes version history.
**PATCH /v1/support/kb/articles/{id}** — Creates new version.
**DELETE /v1/support/kb/articles/{id}**

**GET /v1/support/kb/articles/{id}/versions** — Version history.

### Customer Portal

**POST /v1/portal/magic-link** — Public. Request: `{ email }`. Response: `202 Accepted`.
**POST /v1/portal/verify** — `{ token }`. Returns portal session token.
**GET /v1/portal/tickets** — Auth: portal session. Lists requester's tickets only.
**POST /v1/portal/tickets** — Create ticket from portal.
**POST /v1/portal/tickets/{id}/reply** — Public reply only.

---

## 6.14 Documents (see also §8 File APIs)

**GET /v1/documents** — Permission: `documents.read`. Filters: `module`, `status`, `created_at_gte/lte`.

**POST /v1/documents** — Registers a document for RAG indexing. Request: `{ file_id*, title, source, auto_index: boolean }`. Response: `201`.

**GET /v1/documents/{id}** — With chunk count, index status.

**DELETE /v1/documents/{id}** — Removes from RAG index.

**POST /v1/documents/{id}/reindex** — Re-run chunking and embedding. Response: `202 Accepted` (async job).

---

## 6.15–6.17 AI APIs — see §7 below

---

## 6.18 Workflow Automation

### Workflows

**GET /v1/workflows** — Permission: `workflows.read`. Filters: `status`, `name_contains`.

**POST /v1/workflows** — Permission: `workflows.write`.
```yaml
required: [name]
properties:
  name: { type: string }
  description: { type: string }
  definition:
    type: object
    description: "DAG of triggers, conditions, actions"
    properties:
      triggers: { type: array }
      steps: { type: array }
```
Response: `201` — creates workflow + initial version.

**GET /v1/workflows/{id}** — With current version, trigger config, run stats.

**PATCH /v1/workflows/{id}** — `If-Match`.

**DELETE /v1/workflows/{id}** — `If-Match`. Soft delete.

**POST /v1/workflows/{id}/publish** — Publish a new version. Request: `{ definition }`. Creates new version and sets as current.

**POST /v1/workflows/{id}/pause** — Pauses all triggers.

**POST /v1/workflows/{id}/resume** — Resumes triggers.

**POST /v1/workflows/{id}/trigger** — Manual trigger. Request: `{ payload }`. Response: `201` — new workflow run.

**POST /v1/workflows/dry-run** — Validate and simulate. Request: `{ definition, mock_payload }`. Response: `200` — validation results + simulated step outputs.

### Workflow Versions

**GET /v1/workflows/{id}/versions** — List versions.
**GET /v1/workflow-versions/{version_id}** — Full definition.

### Workflow Runs

**GET /v1/workflow-runs** — Filters: `workflow_id`, `status`, `trigger_kind`, `started_at_gte/lte`.
**GET /v1/workflow-runs/{id}** — With step runs.
**POST /v1/workflow-runs/{id}/retry** — Retry failed run from last failed step.
**POST /v1/workflow-runs/{id}/cancel** — Cancel running workflow.

**GET /v1/workflow-runs/{id}/steps** — List step run details.

---

## 6.19 Notifications

**GET /v1/notifications** — Permission: `self`. Filters: `unread_only` (boolean), `kind`, `created_at_gte/lte`.

**PATCH /v1/notifications/{id}/read** — Mark as read. Response: `200`.

**POST /v1/notifications/mark-all-read** — Mark all as read. Response: `200` — `{ data: { count: 42 } }`.

**GET /v1/me/notification-preferences** — Returns per-channel, per-kind preferences.

**PUT /v1/me/notification-preferences** — Replace preferences.
```yaml
type: array
items:
  type: object
  properties:
    kind: { type: string }
    channels:
      type: object
      properties:
        in_app: { type: boolean }
        email: { type: boolean }
        push: { type: boolean }
        sms: { type: boolean }
```

---

## 6.20 Analytics — see §9.5 for report/dashboard APIs

**GET /v1/analytics/reports** — List saved reports.
**POST /v1/analytics/reports** — `{ name, definition: { metrics, dimensions, filters, time_range } }`.
**GET /v1/analytics/reports/{id}**
**PATCH /v1/analytics/reports/{id}**
**DELETE /v1/analytics/reports/{id}**
**POST /v1/analytics/reports/{id}/run** — Execute report. Response: `200` with data, or `202 Accepted` if > 30s.
**POST /v1/analytics/reports/{id}/schedule** — `{ cron, recipients, format (csv|pdf|xlsx) }`.
**POST /v1/analytics/reports/{id}/share** — Generate shareable link. Response: `{ token, url, expires_at }`.
**GET /v1/analytics/reports/shared/{token}** — Public (token-authed) report view.
**POST /v1/analytics/reports/{id}/export** — `{ format }`. Response: `202 Accepted` with job.

**GET /v1/analytics/dashboards** — List dashboards.
**POST /v1/analytics/dashboards** — `{ name, layout }`.
**GET /v1/analytics/dashboards/{id}** — With widgets.
**PATCH /v1/analytics/dashboards/{id}**
**DELETE /v1/analytics/dashboards/{id}**

**POST /v1/analytics/dashboards/{id}/widgets** — `{ report_id, position, config }`.
**PATCH /v1/analytics/dashboard-widgets/{id}**
**DELETE /v1/analytics/dashboard-widgets/{id}**

---

## 6.21 Billing

**GET /v1/billing/current** — Get current subscription, usage, plan details.

**POST /v1/billing/subscribe** — `{ plan_id }`. Creates Stripe subscription. Response: `200` with client_secret for payment confirmation.

**POST /v1/billing/portal-session** — Redirects to Stripe Customer Portal. Response: `200` with `{ url }`.

**GET /v1/billing/invoices** — List billing invoices (from Stripe).

**GET /v1/billing/usage** — Current period metered usage (AI tokens, storage, seats).

**POST /v1/billing/webhooks/stripe** — Stripe webhook receiver. Auth: Stripe signature verification. Not tenant-scoped.

---

## 6.22 Admin (internal ops)

All admin endpoints require `staff` role and are on a separate auth issuer with IP allowlist + WebAuthn MFA.

**GET /v1/admin/tenants** — List all tenants. Filters: `status`, `plan`, `region`, `search`.
**GET /v1/admin/tenants/{id}** — Full tenant detail with usage, billing, feature flags.
**PATCH /v1/admin/tenants/{id}** — Update tenant (plan, status, settings).
**POST /v1/admin/tenants/{id}/suspend** — `{ reason }`.
**POST /v1/admin/tenants/{id}/reactivate**

**POST /v1/admin/impersonation/request** — `{ target_tenant_id, target_user_id, reason }`. Response: `201` with grant_id.
**POST /v1/admin/impersonation/{grant_id}/approve** — Requires different approver. Response: `200`.
**POST /v1/admin/impersonation/{grant_id}/start** — Opens 30-min impersonation session.
**POST /v1/admin/impersonation/{grant_id}/end** — End early.

**PUT /v1/admin/flags/{feature_key}** — `{ tenant_id (null=global), enabled, config }`.

**POST /v1/admin/billing/credits** — `{ tenant_id, amount, reason }`.

**GET /v1/admin/audit** — Admin audit log (separate from tenant audit).

---

## 6.23 Audit Logs

**GET /v1/audit-log** — Permission: `audit_log.read`.
- **Filters:** `resource_type`, `resource_id`, `actor_id`, `action`, `from` (timestamp), `to` (timestamp).
- **Sorting:** `at` (desc default).
- **Pagination:** Cursor-based.
- **Response:** Array of audit entries:
```yaml
type: object
properties:
  id: { $ref: UUID }
  action: { type: string }
  resource_type: { type: string }
  resource_id: { $ref: UUID }
  actor:
    type: object
    properties:
      type: { type: string, enum: [user, system, api_key, integration] }
      id: { $ref: UUID, nullable: true }
      name: { type: string, nullable: true }
  before: { type: object, nullable: true }
  after: { type: object, nullable: true }
  ip: { type: string, nullable: true }
  trace_id: { type: string }
  at: { $ref: Timestamp }
```
- **Rate Limit:** Standard. Read-only, no write endpoints (append-only from system).

**GET /v1/audit-log/export** — `{ from, to, format (csv|json) }`. Response: `202 Accepted` with job.

---

## 6.24 File Upload — see §8 below

---

## 6.25 Search — see §9 below

---

# 7. AI API Endpoints

All AI endpoints are routed through the AI Orchestrator gateway. Business modules never call providers directly.

---

## 7.1 AI Copilot — Conversations

### POST /v1/ai/conversations
- **Summary:** Start a new Copilot conversation
- **Permission:** `ai.copilot.use`
- **Idempotency:** Required
- **Request Body:**
```yaml
type: object
properties:
  module: { type: string, enum: [crm, finance, projects, hr, inventory, support, general], description: "Context scope" }
  title: { type: string, nullable: true }
  model: { type: string, nullable: true, description: "Model preference; null = auto-route" }
```
- **Response:** `201 Created`
```yaml
data:
  id: { $ref: UUID }
  module: { type: string }
  title: { type: string }
  model: { type: string, description: "Resolved model" }
  created_at: { $ref: Timestamp }
```

### GET /v1/ai/conversations
- **Summary:** List conversations (history)
- **Permission:** `ai.copilot.use`
- **Filters:** `module`, `created_at_gte/lte`, `search` (title search)
- **Sorting:** `updated_at` (desc default)
- **Response:** Paginated array of conversation summaries (id, title, module, message_count, last_message_at)

### GET /v1/ai/conversations/{id}
- **Summary:** Get conversation with messages
- **Permission:** `ai.copilot.use` (own conversations only)
- **Query Params:** `include_tool_calls=true` to expand tool call details
- **Response:**
```yaml
data:
  id: { $ref: UUID }
  module: string
  title: string
  messages:
    type: array
    items:
      type: object
      properties:
        id: { $ref: UUID }
        role: { type: string, enum: [user, assistant, system, tool] }
        content: { type: string }
        model: { type: string, nullable: true }
        tool_calls: { type: array, nullable: true, items: { $ref: ToolCall } }
        tokens_in: { type: integer }
        tokens_out: { type: integer }
        created_at: { $ref: Timestamp }
  created_at: { $ref: Timestamp }
```

### DELETE /v1/ai/conversations/{id}
- **Summary:** Delete conversation
- **Permission:** `ai.copilot.use` (own only)
- **Response:** `204 No Content`

---

## 7.2 AI Chat — Streaming

### POST /v1/ai/conversations/{id}/messages
- **Summary:** Send a message and receive AI response (streaming or blocking)
- **Permission:** `ai.copilot.use`
- **Request Headers:** `Accept: text/event-stream` for streaming; `Accept: application/json` for blocking
- **Request Body:**
```yaml
type: object
required: [content]
properties:
  content: { type: string, maxLength: 32000 }
  attachments: { type: array, items: { $ref: UUID }, description: "File IDs for vision/document context" }
  model: { type: string, nullable: true, description: "Override model for this message" }
  tools_enabled: { type: boolean, default: true, description: "Allow tool calling" }
  rag_enabled: { type: boolean, default: true, description: "Include RAG retrieval" }
  temperature: { type: number, minimum: 0, maximum: 2, nullable: true }
  max_tokens: { type: integer, minimum: 1, maximum: 16384, nullable: true }
```
- **Validation:** Content not empty, attachment IDs must exist and be accessible.
- **Streaming Response (SSE):** `Content-Type: text/event-stream`
```
event: message_start
data: {"message_id":"msg_abc","model":"claude-sonnet-4-6"}

event: content_delta
data: {"delta":"Here are the "}

event: content_delta
data: {"delta":"top 5 deals..."}

event: tool_call_start
data: {"tool_call_id":"tc_1","tool":"crm.search_deals","input":{"status":"open","sort":"amount","limit":5}}

event: tool_call_result
data: {"tool_call_id":"tc_1","output":{"deals":[...]}}

event: content_delta
data: {"delta":"Based on the data..."}

event: message_complete
data: {"message_id":"msg_abc","tokens_in":342,"tokens_out":587,"cost_usd":"0.0048","finish_reason":"stop"}

event: done
data: [DONE]
```
- **Blocking Response:** `200 OK` — full message object with content, tool_calls, token counts.
- **Errors:** `403 BUDGET_EXCEEDED`, `502 UPSTREAM_ERROR` (provider down), `422` (content too long), `409 STATE_CONFLICT` (conversation deleted)
- **Rate Limit:** AI tier (see §2.13)

### POST /v1/ai/chat/completions
- **Summary:** Stateless chat completion (no conversation persistence)
- **Permission:** `ai.chat.use`
- **Request Body:**
```yaml
required: [messages]
properties:
  messages:
    type: array
    items:
      type: object
      required: [role, content]
      properties:
        role: { type: string, enum: [system, user, assistant] }
        content: { type: string }
  model: { type: string, nullable: true }
  temperature: { type: number }
  max_tokens: { type: integer }
  tools: { type: array, nullable: true, description: "Tool schemas for function calling" }
  stream: { type: boolean, default: false }
```
- **Response:** Same SSE or JSON format as above.

---

## 7.3 Context Memory

### GET /v1/ai/conversations/{id}/context
- **Summary:** Get the assembled context for a conversation (system prompt, retrieved chunks, tool schemas)
- **Permission:** `ai.copilot.use` (own only)
- **Response:**
```yaml
data:
  system_prompt: { type: string }
  retrieved_chunks:
    type: array
    items:
      type: object
      properties:
        chunk_id: { $ref: UUID }
        document_title: string
        text: string
        relevance_score: number
  available_tools: { type: array, items: string }
  token_budget: { type: object, properties: { total: integer, used: integer, remaining: integer } }
```

---

## 7.4 Prompt Library

### GET /v1/ai/prompts
- **Permission:** `ai.prompts.read`
- **Filters:** `key`, `status`, `owner_id`
- **Response:** Paginated prompt list

### POST /v1/ai/prompts
- **Permission:** `ai.prompts.write`
- **Request:** `{ key*, description, template*, variables: [{ name, type, required }], output_schema }`.
- **Response:** `201` — creates prompt + version 1.

### GET /v1/ai/prompts/{id}
- **Response:** Prompt with current published version.

### PATCH /v1/ai/prompts/{id}
- **Permission:** `ai.prompts.write`

### DELETE /v1/ai/prompts/{id}

### GET /v1/ai/prompts/{id}/versions
- **Response:** Version history.

### POST /v1/ai/prompts/{id}/versions
- **Summary:** Create new version
- **Request:** `{ template, variables, output_schema }`.
- **Response:** `201` — new version in draft status.

### PUT /v1/ai/prompts/{id}/versions/{version}/publish
- **Summary:** Publish a version (gates on eval score if eval set exists)
- **Errors:** `422 BUSINESS_RULE_VIOLATION` (eval score below baseline)

### POST /v1/ai/prompts/{id}/rollback
- **Summary:** Rollback to previous published version.

### POST /v1/ai/prompts/{id}/eval
- **Summary:** Run evaluation against a golden set
- **Request:** `{ version_id, eval_set_id }`. Response: `202 Accepted` with job.

---

## 7.5 Model Management

### GET /v1/ai/models
- **Summary:** List available AI models
- **Permission:** `ai.models.read`
- **Response:**
```yaml
data:
  type: array
  items:
    type: object
    properties:
      model_key: string
      provider: string
      capabilities: { type: array, items: string }
      context_window: integer
      price_in_per_1k: string
      price_out_per_1k: string
      is_active: boolean
```

### GET /v1/ai/models/{model_key}
- **Response:** Model detail with current health metrics.

---

## 7.6 Embeddings

### POST /v1/ai/embeddings
- **Summary:** Generate embeddings for text
- **Permission:** `ai.embeddings.use`
- **Request Body:**
```yaml
required: [input]
properties:
  input:
    oneOf:
      - { type: string }
      - { type: array, items: string, maxItems: 100 }
  model: { type: string, default: "text-embedding-3-small" }
```
- **Response:** `200 OK`
```yaml
data:
  embeddings:
    type: array
    items:
      type: object
      properties:
        index: integer
        embedding: { type: array, items: number }
  model: string
  usage: { tokens: integer, cost_usd: string }
```

---

## 7.7 Vector Search (RAG)

### POST /v1/ai/rag/search
- **Summary:** Semantic search over tenant documents
- **Permission:** `ai.rag.search`
- **Request Body:**
```yaml
required: [query]
properties:
  query: { type: string, maxLength: 2000 }
  top_k: { type: integer, minimum: 1, maximum: 50, default: 10 }
  filters:
    type: object
    properties:
      document_ids: { type: array, items: UUID }
      source: { type: string }
      indexed_after: { $ref: Timestamp }
  rerank: { type: boolean, default: true }
  include_text: { type: boolean, default: true }
```
- **Response:** `200 OK`
```yaml
data:
  results:
    type: array
    items:
      type: object
      properties:
        chunk_id: { $ref: UUID }
        document_id: { $ref: UUID }
        document_title: string
        text: { type: string, nullable: true }
        score: number
        rerank_score: { type: number, nullable: true }
  query_embedding_model: string
  latency_ms: integer
```

### POST /v1/ai/rag/index/{file_id}
- **Summary:** Index a file for RAG
- **Permission:** `ai.rag.manage`
- **Response:** `202 Accepted` — async job (chunking → embedding → storage)

### POST /v1/ai/rag/reindex/{document_id}
- **Summary:** Re-index existing document
- **Permission:** `ai.rag.manage`
- **Response:** `202 Accepted`

### GET /v1/ai/rag/documents
- **Summary:** List indexed documents
- **Filters:** `status`, `source`, `indexed_at_gte/lte`
- **Response:** Paginated document list with chunk counts and index status

---

## 7.8 Tool Calling

### GET /v1/ai/tools
- **Summary:** List available tools for the current user (RBAC-filtered)
- **Permission:** `ai.copilot.use`
- **Response:**
```yaml
data:
  type: array
  items:
    type: object
    properties:
      key: { type: string, example: "crm.search_deals" }
      description: string
      module: string
      required_permission: string
      parameters_schema: { type: object, description: "JSON Schema for tool input" }
```

### POST /v1/ai/tools/{tool_key}/execute
- **Summary:** Directly execute a tool (for debugging/testing)
- **Permission:** Same as the underlying module permission
- **Request Body:** `{ input: { ... } }` (must match tool's parameter schema)
- **Response:** `200 OK` — `{ data: { output: { ... }, latency_ms: integer } }`

---

## 7.9 AI Agents

### POST /v1/ai/agents/run
- **Summary:** Start an autonomous agent run (multi-step reasoning + tool use)
- **Permission:** `ai.agents.run`
- **Request Body:**
```yaml
required: [goal]
properties:
  goal: { type: string, maxLength: 5000, description: "Natural language objective" }
  model: { type: string, nullable: true }
  max_steps: { type: integer, minimum: 1, maximum: 50, default: 10 }
  allowed_tools: { type: array, items: string, nullable: true, description: "Tool whitelist; null = all allowed" }
  require_approval: { type: boolean, default: false, description: "Pause before executing side-effect tools" }
  context:
    type: object
    properties:
      module: string
      resource_ids: { type: array, items: UUID }
```
- **Response:** `202 Accepted` — returns job + WebSocket channel for live streaming
```yaml
data:
  agent_run_id: { $ref: UUID }
  status: "running"
  ws_channel: "agent:{agent_run_id}"
  poll_url: "/v1/ai/agents/runs/{agent_run_id}"
```

### GET /v1/ai/agents/runs/{id}
- **Summary:** Get agent run status and step log
- **Response:**
```yaml
data:
  id: { $ref: UUID }
  goal: string
  status: { type: string, enum: [running, awaiting_approval, completed, failed, cancelled] }
  steps:
    type: array
    items:
      type: object
      properties:
        step: integer
        reasoning: string
        tool_call: { $ref: ToolCall, nullable: true }
        result_summary: string
        status: string
  final_answer: { type: string, nullable: true }
  tokens_used: integer
  cost_usd: string
  started_at: { $ref: Timestamp }
  completed_at: { $ref: Timestamp, nullable: true }
```

### POST /v1/ai/agents/runs/{id}/approve
- **Summary:** Approve a pending tool execution (when require_approval=true)
- **Request:** `{ step, approved: boolean }`
- **Response:** `200 OK`

### POST /v1/ai/agents/runs/{id}/cancel
- **Summary:** Cancel a running agent
- **Response:** `200 OK`

---

## 7.10 Conversation History

### GET /v1/ai/conversations/{id}/messages
- **Summary:** Paginated message history for a conversation
- **Filters:** `role`, `created_at_gte/lte`
- **Response:** Paginated array of messages with tool calls

### GET /v1/ai/messages/{id}/tool-calls
- **Summary:** List tool calls for a specific message
- **Response:** Array of ToolCall objects with input/output/status/latency

---

## 7.11 Token Usage & Cost Tracking

### GET /v1/ai/usage
- **Summary:** Get AI usage for current tenant
- **Permission:** `ai.usage.read`
- **Query Params:** `period` (day|week|month), `from`, `to`, `group_by` (feature|model|user)
- **Response:**
```yaml
data:
  period: { from: Timestamp, to: Timestamp }
  totals: { tokens_in: integer, tokens_out: integer, cost_usd: string, requests: integer }
  breakdown:
    type: array
    items:
      type: object
      properties:
        key: string
        tokens_in: integer
        tokens_out: integer
        cost_usd: string
        requests: integer
```

### GET /v1/ai/budgets
- **Summary:** Get current AI budget status
- **Permission:** `ai.budgets.read`
- **Response:**
```yaml
data:
  month: string
  soft_cap_usd: string
  hard_cap_usd: string
  used_usd: string
  remaining_usd: string
  projected_end_of_month_usd: string
  is_at_risk: boolean
```

### PUT /v1/ai/budgets
- **Summary:** Update AI budget caps
- **Permission:** `ai.budgets.write`
- **Request:** `{ soft_cap_usd, hard_cap_usd }`
- **Response:** `200 OK`

---

## 7.12 AI Feedback

### POST /v1/ai/messages/{id}/feedback
- **Summary:** Submit feedback on an AI response
- **Permission:** `ai.copilot.use`
- **Request Body:** `{ verdict: "up"|"down", reason: string (nullable) }`
- **Response:** `201 Created`

---

## 7.13 AI Guardrails (Admin)

### GET /v1/ai/guardrails
- **Permission:** `ai.guardrails.read`
- **Response:** List of active guardrail rules

### PUT /v1/ai/guardrails/{id}
- **Permission:** `ai.guardrails.write`
- **Request:** `{ kind, config, is_active }`
- **Response:** `200 OK`

---

## Common AI Schemas

```yaml
ToolCall:
  type: object
  properties:
    id: { $ref: UUID }
    tool_key: { type: string, example: "crm.search_deals" }
    input: { type: object }
    output: { type: object, nullable: true }
    status: { type: string, enum: [pending, succeeded, failed, denied] }
    denied_reason: { type: string, nullable: true }
    latency_ms: { type: integer }

AIMessage:
  type: object
  properties:
    id: { $ref: UUID }
    role: { type: string, enum: [user, assistant, system, tool] }
    content: { type: string }
    model: { type: string, nullable: true }
    tool_calls: { type: array, items: { $ref: ToolCall }, nullable: true }
    tokens_in: { type: integer }
    tokens_out: { type: integer }
    created_at: { $ref: Timestamp }

SSEEvent:
  description: "Server-Sent Event for AI streaming"
  oneOf:
    - { event: message_start, data: { message_id, model } }
    - { event: content_delta, data: { delta: string } }
    - { event: tool_call_start, data: { tool_call_id, tool, input } }
    - { event: tool_call_result, data: { tool_call_id, output } }
    - { event: message_complete, data: { message_id, tokens_in, tokens_out, cost_usd, finish_reason } }
    - { event: error, data: { code, message } }
    - { event: done, data: "[DONE]" }
```

---

# 8. File API Endpoints

## 8.1 Upload (presigned)

### POST /v1/files/presign-upload
- **Summary:** Get a presigned URL for direct-to-S3 upload
- **Permission:** `files.upload`
- **Request Body:**
```yaml
required: [filename, content_type, size_bytes]
properties:
  filename: { type: string, maxLength: 255 }
  content_type: { type: string }
  size_bytes: { type: integer, maximum: 524288000, description: "Max 500MB" }
  module: { type: string, description: "Owning module (crm, finance, etc.)" }
  purpose: { type: string, enum: [attachment, avatar, document, export, import] }
```
- **Validation:** Content-type allowlist (no executables), size within plan limit.
- **Response:** `200 OK`
```yaml
data:
  file_id: { $ref: UUID }
  upload_url: { type: string, format: uri, description: "PUT this URL with the file body" }
  upload_headers: { type: object, description: "Headers to include in the PUT" }
  expires_at: { $ref: Timestamp, description: "URL valid for 10 min" }
```

### POST /v1/files/{id}/confirm
- **Summary:** Confirm upload completed; triggers virus scan
- **Permission:** `files.upload`
- **Response:** `200 OK` — file status transitions to `scanning`
```yaml
data:
  id: { $ref: UUID }
  status: "scanning"
  filename: string
  mime_type: string
  size_bytes: integer
```

### POST /v1/files/upload
- **Summary:** Direct upload (small files < 10MB, multipart form)
- **Permission:** `files.upload`
- **Content-Type:** `multipart/form-data`
- **Form fields:** `file` (binary), `module` (string), `purpose` (string)
- **Response:** `201 Created` — file object (scan queued)

## 8.2 Multipart Upload (large files)

### POST /v1/files/multipart/initiate
- **Summary:** Begin a multipart upload for files > 100MB
- **Request:** `{ filename, content_type, size_bytes, part_size }`.
- **Response:** `200 OK` — `{ upload_id, part_count, part_urls: [{ part_number, url }] }`

### POST /v1/files/multipart/{upload_id}/complete
- **Summary:** Complete multipart upload after all parts uploaded
- **Request:** `{ parts: [{ part_number, etag }] }`
- **Response:** `200 OK` — file object

### DELETE /v1/files/multipart/{upload_id}
- **Summary:** Abort multipart upload
- **Response:** `204 No Content`

## 8.3 Download

### GET /v1/files/{id}
- **Summary:** Get file metadata
- **Permission:** `files.read` (module-scoped: a CRM file requires `crm.*.read`)
- **Response:** `200 OK` — file metadata with presigned download URL (5-min TTL)

### GET /v1/files/{id}/download
- **Summary:** Get presigned download URL
- **Permission:** `files.read`
- **Response:** `200 OK` — `{ url, expires_at }`
- **Alternative:** `Accept: application/octet-stream` → `302 Found` redirect to presigned URL

## 8.4 Preview

### GET /v1/files/{id}/preview
- **Summary:** Get a preview rendition (thumbnail for images, first page for PDFs)
- **Permission:** `files.read`
- **Query Params:** `width` (pixels), `height` (pixels), `format` (png|webp)
- **Response:** `200 OK` — `{ url, width, height, format }`

## 8.5 Delete

### DELETE /v1/files/{id}
- **Summary:** Delete a file (soft delete; object retained per retention policy)
- **Permission:** `files.delete`
- **Headers:** `If-Match`
- **Response:** `204 No Content`

## 8.6 Version History

### GET /v1/files/{id}/versions
- **Summary:** List file versions (when a file is re-uploaded)
- **Permission:** `files.read`
- **Response:** Array of `{ version, size_bytes, created_at, created_by, url }`

## 8.7 Permissions

### GET /v1/files/{id}/permissions
- **Summary:** List who can access this file
- **Permission:** `files.manage`
- **Response:** Array of `{ subject_type (user|role|team), subject_id, access (read|write|manage) }`

### PUT /v1/files/{id}/permissions
- **Summary:** Set file access permissions
- **Permission:** `files.manage`
- **Request:** `{ grants: [{ subject_type, subject_id, access }] }`
- **Response:** `200 OK`

---

# 9. Search API Endpoints

## 9.1 Global Search

### GET /v1/search
- **Summary:** Search across all modules (permission-filtered)
- **Permission:** per-module read permissions applied to results
- **Query Params:**
```yaml
q: { type: string, minLength: 2, maxLength: 500, description: "Search query" }
types: { type: string, description: "Comma-separated: contacts,deals,invoices,tasks,tickets,documents,kb_articles" }
limit: { type: integer, default: 20, maximum: 50 }
cursor: { type: string }
```
- **Response:** `200 OK`
```yaml
data:
  results:
    type: array
    items:
      type: object
      properties:
        type: { type: string, description: "Entity type" }
        id: { $ref: UUID }
        title: { type: string }
        subtitle: { type: string, nullable: true }
        snippet: { type: string, nullable: true, description: "Highlighted match" }
        url: { type: string, description: "Deep link path" }
        module: { type: string }
        score: { type: number }
        updated_at: { $ref: Timestamp }
  facets:
    type: object
    properties:
      types: { type: array, items: { type: object, properties: { key: string, count: integer } } }
```

## 9.2 Semantic Search

### POST /v1/search/semantic
- **Summary:** AI-powered semantic search using embeddings
- **Permission:** `search.semantic`
- **Request Body:**
```yaml
required: [query]
properties:
  query: { type: string }
  types: { type: array, items: string }
  limit: { type: integer, default: 10 }
  similarity_threshold: { type: number, minimum: 0, maximum: 1, default: 0.7 }
```
- **Response:** Same shape as global search with `similarity_score` per result.

## 9.3 Autocomplete

### GET /v1/search/autocomplete
- **Summary:** Fast prefix-based suggestions for search-as-you-type
- **Query Params:** `q` (min 1 char), `types`, `limit` (default 5, max 10)
- **Response:**
```yaml
data:
  suggestions:
    type: array
    items:
      type: object
      properties:
        text: string
        type: string
        id: { $ref: UUID }
        url: string
```
- **Rate Limit:** 120/min (higher for typing speed)
- **Cache:** `Cache-Control: private, max-age=5`

## 9.4 Faceted Search

### POST /v1/search/faceted
- **Summary:** Search with facet computation
- **Request Body:**
```yaml
required: [query]
properties:
  query: string
  types: { type: array, items: string }
  filters: { type: object, description: "Pre-applied facet filters" }
  facets: { type: array, items: string, description: "Facets to compute: type, module, status, owner, date_range" }
  limit: integer
```
- **Response:** Results + facet counts for drill-down UI.

## 9.5 Saved Searches

### GET /v1/search/saved
- **Summary:** List user's saved searches
- **Response:** Array of `{ id, name, query, filters, created_at }`

### POST /v1/search/saved
- **Request:** `{ name, query, types, filters }`
- **Response:** `201 Created`

### DELETE /v1/search/saved/{id}
- **Response:** `204 No Content`

---

# 10. WebSocket Contracts

## 10.1 Connection

```
wss://rt.aibos.io/v1/ws?token=<short-lived-ws-token>
```

**Authentication:** Client first calls `POST /v1/auth/ws-token` (Bearer JWT) to get a single-use, 60-second WebSocket token. This avoids passing the JWT in a query parameter.

**Heartbeat:** Client sends `ping` every 30s; server responds with `pong`. No heartbeat for 90s → server disconnects.

**Reconnection:** Client uses exponential backoff (1s, 2s, 4s, 8s, max 30s) with jitter.

## 10.2 Message Envelope

All WebSocket messages follow this envelope:

```json
{
  "type": "event_type",
  "channel": "channel_name",
  "data": { },
  "id": "msg_unique_id",
  "timestamp": "2026-07-09T12:00:00Z"
}
```

## 10.3 Channels & Subscriptions

Client subscribes to channels after connecting:

```json
{ "type": "subscribe", "channels": ["notifications", "tasks:project_abc", "ai:conv_xyz"] }
```

Server confirms:
```json
{ "type": "subscribed", "channels": ["notifications", "tasks:project_abc", "ai:conv_xyz"] }
```

Unsubscribe:
```json
{ "type": "unsubscribe", "channels": ["tasks:project_abc"] }
```

## 10.4 Channel Types

### notifications
- **Direction:** Server → Client
- **Events:**
  - `notification.new` — `{ id, kind, title, body, data, created_at }`
  - `notification.read` — `{ id }` (synced across devices)
  - `badge.update` — `{ unread_count: integer }`

### ai:{conversation_id}
- **Direction:** Server → Client
- **Events:**
  - `ai.message_start` — `{ message_id, model }`
  - `ai.content_delta` — `{ delta: string }`
  - `ai.tool_call_start` — `{ tool_call_id, tool, input }`
  - `ai.tool_call_result` — `{ tool_call_id, output }`
  - `ai.message_complete` — `{ message_id, tokens_in, tokens_out, cost_usd, finish_reason }`
  - `ai.error` — `{ code, message }`

### agent:{agent_run_id}
- **Direction:** Server → Client
- **Events:**
  - `agent.step_start` — `{ step, reasoning }`
  - `agent.tool_call` — `{ step, tool, input }`
  - `agent.tool_result` — `{ step, output_summary }`
  - `agent.approval_required` — `{ step, tool, input, description }`
  - `agent.complete` — `{ final_answer, steps_taken, cost_usd }`
  - `agent.failed` — `{ error }`

### tasks:{project_id}
- **Direction:** Server → Client
- **Events:**
  - `task.created` — `{ task summary }`
  - `task.updated` — `{ id, changes: { field: { old, new } } }`
  - `task.moved` — `{ id, from_status, to_status, position }`
  - `task.completed` — `{ id, completed_by }`
  - `task.commented` — `{ task_id, comment summary }`

### workflow:{workflow_id}
- **Direction:** Server → Client
- **Events:**
  - `workflow.run_started` — `{ run_id, trigger }`
  - `workflow.step_completed` — `{ run_id, step_key, status }`
  - `workflow.run_completed` — `{ run_id, status, duration_ms }`
  - `workflow.run_failed` — `{ run_id, step_key, error }`

### chat:{room_id}
- **Direction:** Bidirectional
- **Client → Server:**
  - `chat.message` — `{ room_id, body, attachments }`
  - `chat.typing` — `{ room_id }`
- **Server → Client:**
  - `chat.message` — `{ id, author, body, attachments, created_at }`
  - `chat.typing` — `{ room_id, user_id, user_name }`

### presence:{scope}
- **Direction:** Server → Client (after subscribing)
- **Events:**
  - `presence.join` — `{ user_id, user_name }`
  - `presence.leave` — `{ user_id }`
  - `presence.list` — `{ users: [{ user_id, user_name, status, last_seen_at }] }` (on subscribe)

## 10.5 Error Handling

```json
{
  "type": "error",
  "data": {
    "code": "SUBSCRIPTION_DENIED",
    "message": "Insufficient permissions for channel tasks:project_abc",
    "channel": "tasks:project_abc"
  }
}
```

## 10.6 Backpressure

If a client falls behind, the server buffers up to 1000 messages per connection. Beyond that, older messages are dropped and a `buffer_overflow` event is sent, indicating the client should re-fetch state via REST.

---

# 11. Webhook Contracts

## 11.1 Registration

### POST /v1/webhooks/subscriptions
- **Permission:** `webhooks.write`
- **Request Body:**
```yaml
required: [url, events]
properties:
  url: { type: string, format: uri }
  events: { type: array, items: string, description: "Event types to subscribe to" }
  secret: { type: string, description: "HMAC secret; if omitted, server generates one" }
  active: { type: boolean, default: true }
```
- **Response:** `201 Created` — subscription with `id`, `secret` (shown once)

### GET /v1/webhooks/subscriptions
### PATCH /v1/webhooks/subscriptions/{id}
### DELETE /v1/webhooks/subscriptions/{id}
### GET /v1/webhooks/deliveries — Delivery log with status
### POST /v1/webhooks/deliveries/{id}/replay — Re-deliver a specific event

## 11.2 Delivery Format

```http
POST {subscriber_url}
Content-Type: application/json
X-Webhook-Id: wh_abc123
X-Webhook-Timestamp: 1720526400
X-Webhook-Signature: sha256=a1b2c3...
X-Webhook-Event: invoice.paid
```

```json
{
  "id": "evt_abc123",
  "type": "invoice.paid",
  "api_version": "2026-07-01",
  "created_at": "2026-07-09T12:00:00Z",
  "tenant_id": "tnt_xyz789",
  "data": {
    "object": {
      "id": "inv_abc",
      "number": "INV-2026-0042",
      "total": { "amount": "1250.00", "currency": "USD" },
      "status": "paid",
      "paid_at": "2026-07-09T12:00:00Z"
    },
    "previous_attributes": {
      "status": "sent"
    }
  }
}
```

**Signature verification:** `HMAC-SHA256(webhook_secret, X-Webhook-Timestamp + "." + raw_body)`. Compare to `X-Webhook-Signature`.

## 11.3 Retry Policy

| Attempt | Delay |
|---|---|
| 1 | Immediate |
| 2 | 5 min |
| 3 | 30 min |
| 4 | 2 hours |
| 5 | 8 hours |
| 6 | 24 hours |

After 6 failures: event marked dead; endpoint disabled after 3 consecutive dead events; owner notified.

Expected response: `2xx` within 30 seconds. Non-2xx or timeout → retry.

## 11.4 Event Catalog

| Event | Trigger | Payload (data.object) |
|---|---|---|
| `user.created` | User registered or invited | User object |
| `user.updated` | User profile changed | User + previous_attributes |
| `organization.created` | New organization | Organization object |
| `task.created` | Task created | Task object |
| `task.updated` | Task status/assignment changed | Task + previous_attributes |
| `task.completed` | Task marked done | Task object |
| `deal.created` | Deal created | Deal object |
| `deal.moved` | Deal changed stage | Deal + previous_attributes (stage) |
| `deal.won` | Deal marked won | Deal object |
| `deal.lost` | Deal marked lost | Deal object |
| `invoice.created` | Invoice created | Invoice object |
| `invoice.sent` | Invoice sent to customer | Invoice object |
| `invoice.paid` | Invoice fully paid | Invoice + payment summary |
| `invoice.overdue` | Invoice past due date | Invoice object |
| `payment.received` | Payment recorded | Payment object |
| `ticket.created` | Support ticket opened | Ticket object |
| `ticket.resolved` | Ticket resolved | Ticket object |
| `ticket.sla_breached` | SLA target missed | Ticket + SLA detail |
| `employee.created` | Employee record created | Employee object |
| `leave.approved` | Leave request approved | Leave request object |
| `stock.low` | Stock below reorder point | SKU + warehouse + quantity |
| `workflow.run.completed` | Workflow execution finished | Run summary |
| `workflow.run.failed` | Workflow execution failed | Run + error detail |
| `ai.agent.completed` | Agent run finished | Agent run summary |
| `document.indexed` | Document RAG indexing complete | Document object |
| `notification.delivered` | Notification sent to user | Notification object |
| `export.ready` | Async export file ready | Job + download URL |

---

# 12. Versioning & Deprecation Strategy

## 12.1 Versioning

**Method:** URL path versioning (`/v1/`, `/v2/`).

**Rules:**
- Additive, non-breaking changes (new optional fields, new endpoints) are added to the current version without incrementing.
- Breaking changes (field removal, type changes, behavioral changes) require a new major version.
- A maximum of 2 major versions are supported concurrently.
- Version `v1` is the initial and current version.

**Non-breaking changes (no version bump):**
- Adding a new optional field to a response
- Adding a new optional query parameter
- Adding a new endpoint
- Adding a new webhook event type
- Adding a new enum value to a response-only field
- Widening a constraint (e.g. increasing max limit)

**Breaking changes (require version bump):**
- Removing or renaming a field
- Changing a field's type
- Making a previously optional field required
- Changing URL structure
- Changing error code semantics
- Changing default behavior

## 12.2 Deprecation

1. **Announce:** deprecated endpoint/field marked with `Sunset` header and `deprecated: true` in OpenAPI.
2. **Migration period:** 12 months from announcement.
3. **Warnings:** responses include `X-Deprecation-Warning` header with migration guide URL.
4. **Metrics:** usage of deprecated endpoints is tracked; tenants still using them are notified.
5. **Removal:** after migration period, endpoint returns `410 Gone` with a doc link.

```
Sunset: Sat, 09 Jul 2027 00:00:00 GMT
X-Deprecation-Warning: This endpoint is deprecated. Migrate to /v2/crm/deals. See https://docs.aibos.io/migration/v2-deals
```

## 12.3 API Changelog

An append-only changelog is published at `/v1/changelog` and at `https://docs.aibos.io/changelog`. Entries include date, category (added/changed/deprecated/removed), affected endpoints, and migration notes.

## 12.4 Date-Based Sub-Versioning (Stripe-style, future)

For webhook payloads and response shape evolution within a major version, a date-based API version header (`X-API-Version: 2026-07-01`) pins the response schema to a specific date. This allows non-breaking response evolution without forcing all consumers to update simultaneously. This will be introduced post-v1 GA.

---

# Appendix A: Endpoint Count Summary

| Module | Endpoints |
|---|---|
| Authentication | 13 |
| Users | 11 |
| Organizations | 6 |
| Departments | 5 |
| Teams | 7 |
| Roles & Permissions | 7 |
| CRM (Companies, Contacts, Leads, Pipelines, Deals, Activities) | 32 |
| Finance (Accounts, Invoices, Quotes, Payments, Expenses, Tax, Journal) | 28 |
| Projects | 5 |
| Tasks (Tasks, Milestones, Dependencies, Timesheets) | 18 |
| HR (Employees, Attendance, Leave, Payroll, Reviews) | 26 |
| Inventory (Products, SKUs, Warehouses, Stock, POs) | 20 |
| Support (Tickets, SLA, Canned, KB, Portal) | 22 |
| Documents | 4 |
| AI Copilot & Chat | 12 |
| AI Prompts | 9 |
| AI Models | 2 |
| AI Embeddings | 1 |
| AI RAG / Vector Search | 4 |
| AI Tools | 2 |
| AI Agents | 4 |
| AI Usage & Budgets | 4 |
| AI Feedback & Guardrails | 3 |
| Workflow Automation | 14 |
| Notifications | 4 |
| Analytics | 12 |
| Billing | 5 |
| Admin | 10 |
| Audit Logs | 2 |
| Files | 12 |
| Search | 5 |
| Webhooks | 5 |
| Jobs (async) | 1 |
| **Total** | **~340** |

---

# Appendix B: Quick Reference — Permission Catalog

| Resource | Actions |
|---|---|
| `users` | read, write, delete |
| `roles` | read, write, delete, assign |
| `organizations` | read, write, delete |
| `departments` | read, write, delete |
| `teams` | read, write, delete |
| `crm.companies` | read, write, delete, export |
| `crm.contacts` | read, write, delete, export |
| `crm.leads` | read, write, delete, convert |
| `crm.deals` | read, write, delete, export |
| `crm.pipelines` | read, write, delete |
| `crm.activities` | read, write, delete |
| `finance.accounts` | read, write, delete |
| `finance.invoices` | read, write, delete, send, void |
| `finance.quotes` | read, write, delete, send |
| `finance.payments` | read, write, refund |
| `finance.expenses` | read, write, delete |
| `finance.journal` | read |
| `projects` | read, write, delete |
| `tasks` | read, write, delete |
| `time_entries` | read, write, delete |
| `hr.employees` | read, write, delete |
| `hr.attendance` | read, write |
| `hr.leave` | read, write, approve |
| `hr.payroll` | read, write, close, reverse |
| `hr.reviews` | read, write |
| `inventory.products` | read, write, delete |
| `inventory.stock` | read, write |
| `inventory.pos` | read, write, receive |
| `support.tickets` | read, write, reply, delete |
| `support.kb` | read, write, delete |
| `documents` | read, write, delete |
| `files` | upload, read, delete, manage |
| `workflows` | read, write, delete, trigger |
| `ai.copilot` | use |
| `ai.chat` | use |
| `ai.agents` | run |
| `ai.prompts` | read, write |
| `ai.rag` | search, manage |
| `ai.embeddings` | use |
| `ai.models` | read |
| `ai.usage` | read |
| `ai.budgets` | read, write |
| `ai.guardrails` | read, write |
| `search` | use, semantic |
| `webhooks` | read, write |
| `audit_log` | read, export |
| `analytics` | read, write, share |
| `billing` | read, write |
| `admin.*` | (staff only, all actions) |

---

API specification complete. Awaiting signal for the next stage.
