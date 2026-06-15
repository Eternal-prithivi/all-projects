# ADR 001 — Caching Strategy

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Date** | June 2026 |
| **Deciders** | Platform team |
| **Tags** | performance, cost, caching, frontend, backend |

---

## Context

Zenith queries multiple cloud provider APIs (AWS Cost Explorer, GCP Monitoring, Azure Cost
Management) on behalf of each user. These APIs are:

- **Metered** — AWS Cost Explorer charges $0.01 per 1 000 queries; GCP Monitoring charges
  per metric time-series request.
- **Slow** — P95 latency of 2–4 s for billing aggregations.
- **Not real-time** — Billing data is typically 24–48 h delayed by the provider anyway.

Without caching, a modest deployment (100 concurrent users, 10 VMs, 8-hour day) would
generate ~48 000 GCP Monitoring API calls and ~480 Cost Explorer calls per day, costing
roughly $20–40/day. This is disproportionate for a student/portfolio deployment.

Additionally, the frontend re-fetches the same data on every page navigation in a SPA
context, adding perceived latency.

---

## Decision

Implement a **multi-layer, user-keyed, process-local cache** with explicit TTLs and
invalidation hooks. No dedicated cache service (Redis) is added in this phase.

### Layer 1 — Backend in-process dict caches

Each cache slot is keyed `{username}:{other query params}` to prevent cross-user data
leakage. TTLs are tuned to the staleness tolerance of each data type:

| Data | TTL | Rationale |
|------|-----|-----------|
| VM metrics | 120 s | 2-minute staleness acceptable for dashboards |
| Cluster health | 60 s | Refreshes every 30 s in UI; one real call per minute sufficient |
| VM recommendations | 180 s | Expensive to compute; users do not expect sub-minute updates |
| Cost queries | 3 600 s | Cloud billing is 24–48 h stale at the source anyway |
| Billing costs | 3 600 s | Same as above |
| Dashboard cost aggregation | 3 600 s | Force-refresh endpoint available |
| Budget alerts | 900 s | Budget state changes infrequently |
| Org summary | 300 s | Invalidated on member/billing changes |

### Layer 2 — MongoDB-backed caches

Used for data that must survive process restarts or be shared across queries:

| Data | TTL |
|------|-----|
| AWS bucket discovery | 600 s |
| Cloud provider pricing | 7 days |

### Layer 3 — Frontend sessionStorage (anti-flicker)

Page-level data (VM list, billing history, file list) is cached in `sessionStorage` for
the lifetime of the browser tab. This eliminates re-fetch flicker on back-navigation.
No TTL is enforced at this layer (tab close acts as implicit eviction).

### Layer 4 — `@lru_cache` singletons

Static configuration (platform regions, ML models, Terraform probe) is cached for the
process lifetime. Explicit invalidation functions are provided for deploy-time reloads.

---

## Consequences

### Positive

- **~90% reduction** in cloud API calls and cost in standard usage.
- **Sub-100 ms** page loads on re-navigation within the same tab.
- **Zero additional infrastructure** — no Redis required for Phase 1.
- **Predictable staleness** — every cache has a documented TTL and users can force-refresh.

### Negative / trade-offs

- **Process-local**: Multi-instance deployments (Render with ≥2 dynos) do not share caches.
  Invalidation on instance A does not propagate to instance B. Acceptable for current
  single-dyno Render deployment.
- **No stale-while-revalidate**: Users see old data until TTL expires rather than getting
  fresh data in the background. Mitigated by explicit refresh buttons throughout the UI.
- **Tab-scoped frontend caches**: Changes made in another tab are not reflected until the
  user navigates back and the data is re-fetched from the API.

---

## Alternatives considered

### A. React Query / TanStack Query (frontend)

**Pros:** Automatic stale-while-revalidate, deduplication, mutation-driven invalidation,
DevTools.  
**Cons:** Significant refactor of all `useEffect`-based data fetching (40+ pages); adds
25 kB gzipped to bundle.  
**Decision:** Deferred to Phase 25. The current `api.js` + `sessionStorage` approach is
sufficient and already in production.

### B. Redis application cache (backend)

**Pros:** Shared across all Render instances; TTL managed by Redis; pub/sub for cache
invalidation.  
**Cons:** Adds a managed Redis service ($7–15/month); operational complexity.  
**Decision:** Deferred to Phase 25. Current Render deployment is single-instance, so
process-local caches are equivalent.

### C. HTTP Cache-Control headers

**Pros:** Browser handles caching transparently; CDN can cache public responses.  
**Cons:** Most Zenith API responses are user-specific and must not be cached at CDN/proxy
level without `Vary: Authorization`. Implementation is non-trivial and can cause
cache poisoning.  
**Decision:** Not implemented. All API responses are private (authenticated) and are
not suitable for shared HTTP caching.

### D. Service Worker / offline cache

**Pros:** Enables offline support; can cache API responses across sessions.  
**Cons:** Complex to implement correctly; risk of serving stale data; no clear user need
identified yet.  
**Decision:** Not in scope.

---

## Security notes

1. **Per-user cache keys are mandatory.** A shared cache slot for multi-tenant data is a
   data-leak vulnerability. The `billing_cache` shared-slot bug (fixed June 2026) is an
   example of what happens when this principle is violated.
2. **Cache-clear endpoints must require authentication.** An unauthenticated
   `DELETE /api/cost/cache/clear` endpoint could be used for a denial-of-service attack
   (forcing expensive cache-miss refreshes). Fixed June 2026.
3. **Never cache credentials in memory without a TTL.** `byoc/credential_resolver.py`
   explicitly warns against this.

---

## Review schedule

This decision should be revisited when:
- Monthly active users exceed 500 (process-local caches become insufficient)
- Render deployment moves to ≥2 dynos
- Phase 25 (Redis app cache) is scoped
