# API Conventions — Outur AI

## Base URL

```
http://localhost:8000          # Development
https://api.outur.ai/v1        # Production (planned)
```

All versioned endpoints are under `/api/v1/`.

---

## Response Format

All JSON responses follow this envelope:

### Success (2xx)

```json
{
  "data": { ... },
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 150
  }
}
```

### Error (4xx / 5xx)

```json
{
  "error": "not_found",
  "detail": "Company with id 'abc-123' not found."
}
```

---

## Error Codes

| HTTP  | `error`                   | Cause                                     |
|-------|---------------------------|-------------------------------------------|
| 400   | `bad_request`             | Malformed request body or params          |
| 401   | `unauthorized`            | Missing or invalid authentication token   |
| 403   | `forbidden`               | Authenticated but insufficient permission |
| 404   | `not_found`               | Resource does not exist                   |
| 409   | `conflict`                | Resource state conflict (e.g. duplicate)  |
| 422   | `validation_error`        | Business rule validation failure          |
| 429   | `rate_limit_exceeded`     | Too many requests                         |
| 500   | `internal_error`          | Unexpected server error                   |
| 502   | `external_service_error`  | Third-party API failure                   |

---

## Pagination

### Offset Pagination (default)

Query params: `?page=1&page_size=20`

```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "pages": 8,
  "has_next": true,
  "has_prev": false
}
```

### Cursor Pagination (large/streaming datasets)

Query params: `?cursor=<opaque_token>&limit=20`

```json
{
  "items": [...],
  "next_cursor": "eyJ...",
  "has_next": true
}
```

Pass `next_cursor` as the `cursor` param in your next request.
When `next_cursor` is `null`, you have reached the end.

---

## Health Endpoints

### GET /health — Liveness

Always returns 200 if the process is alive.

```json
{
  "status": "ok",
  "app": "Outur AI",
  "version": "0.1.0",
  "environment": "production",
  "timestamp": "2025-01-01T12:00:00Z"
}
```

### GET /ready — Readiness

Returns 200 when all dependencies are reachable, 503 otherwise.

```json
{
  "status": "ok",
  "components": {
    "database": { "status": "ok", "latency_ms": 2.3 }
  }
}
```

---

## Request Tracing

Every response includes an `X-Request-ID` header (UUID v4).
Include this in support tickets for log correlation.

```
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

---

## Authentication (Planned — Phase 4)

JWT Bearer tokens via the `Authorization` header:

```
Authorization: Bearer <token>
```

Token format: HS256 signed JWT with:
- `sub` — user ID (UUID)
- `exp` — expiry timestamp
- `iat` — issued-at timestamp

---

## Versioning

The API is versioned via URL path (`/api/v1/`).
Breaking changes will increment the version (`/api/v2/`).
Non-breaking additions (new fields, new endpoints) do not increment the version.
