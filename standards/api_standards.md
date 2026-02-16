# API Standards

Canonical specifications for API design. References authoritative standards.

---

## REST Design

**Reference:** RFC 7231 (HTTP/1.1 Semantics); Fielding's dissertation on REST

### URL Structure
```
/api/v{version}/{resource}/{id}/{sub-resource}
```

### Resource Naming
| Rule | Good | Bad |
|------|------|-----|
| Nouns, not verbs | `/users` | `/getUsers` |
| Plural | `/markets` | `/market` |
| Lowercase | `/order-items` | `/OrderItems` |
| Hyphens | `/order-items` | `/order_items` |

### HTTP Methods
**Reference:** RFC 7231, RFC 5789 (PATCH)

| Method | Usage | Idempotent |
|--------|-------|------------|
| GET | Read | Yes |
| POST | Create | No |
| PUT | Replace | Yes |
| PATCH | Partial update | No |
| DELETE | Remove | Yes |

---

## Response Format

**Reference:** JSON:API (jsonapi.org); RFC 7807 (Problem Details)

### Success
```json
{
    "success": true,
    "data": { ... },
    "meta": { "page": 1, "total": 100 }
}
```

### Error
**Reference:** RFC 7807 — Problem Details for HTTP APIs

```json
{
    "success": false,
    "error": "Human readable message",
    "code": "ERROR_CODE",
    "details": { "field": ["error"] }
}
```

---

## HTTP Status Codes

**Reference:** RFC 7231; IANA HTTP Status Code Registry

| Code | When |
|------|------|
| 200 | GET, PUT, PATCH success |
| 201 | POST success (created) |
| 204 | DELETE success |
| 400 | Validation error |
| 401 | Not authenticated |
| 403 | Not authorized |
| 404 | Not found |
| 409 | Conflict |
| 422 | Semantically invalid |
| 429 | Rate limited |
| 500 | Server error |

---

## Pagination

**Reference:** RFC 5988 (Web Linking); JSON:API pagination

```
GET /api/v1/items?page=2&per_page=20
```

### Response Meta
```json
{
    "meta": {
        "page": 2,
        "per_page": 20,
        "total": 100,
        "total_pages": 5
    }
}
```

**Defaults:** page=1, per_page=20, max=100

---

## Authentication

**Reference:** RFC 6750 (Bearer Token); RFC 7519 (JWT)

```
Authorization: Bearer <jwt_token>
```

### JWT Payload
```json
{
    "sub": "user_id",
    "exp": 1234567890,
    "iat": 1234567800
}
```

---

## Rate Limiting

**Reference:** IETF draft-ietf-httpapi-ratelimit-headers

### Headers
```
RateLimit-Limit: 100
RateLimit-Remaining: 95
RateLimit-Reset: 1234567890
```

---

## Data Formats

**Reference:** RFC 3339 (Date/Time); ISO 8601

| Type | Format |
|------|--------|
| Dates | ISO 8601: `2024-01-15T10:30:00Z` |
| Timezone | UTC always |
| Decimals | String: `"123.45"` |
| Booleans | `true`/`false` |

---

## Versioning

**Reference:** Semantic Versioning (semver.org)

**Strategy:** URL path versioning
```
/api/v1/users
/api/v2/users
```

### Deprecation Headers
**Reference:** RFC 8594 (Sunset Header)

```
Deprecation: true
Sunset: Sat, 01 Jan 2025 00:00:00 GMT
```

---

## Verification Checklist

- [ ] URLs follow naming conventions
- [ ] Correct HTTP methods
- [ ] Response format matches standard
- [ ] Error codes return proper status
- [ ] Dates in ISO 8601
- [ ] Pagination follows standard
