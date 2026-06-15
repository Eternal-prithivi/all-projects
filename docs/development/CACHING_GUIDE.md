# Zenith Caching Strategy — Complete Reference

> **Last updated:** June 2026  
> **Scope:** frontend browser caches + backend in-memory caches + Mongo-backed caches

---

## Overview

Zenith uses a layered caching strategy to keep cloud API costs low and page loads fast.
There is no dedicated cache service (Redis is the Celery broker only; an application-level
Redis cache is on the Phase 25 roadmap). All caches today are either **browser sessionStorage /
localStorage** or **in-process Python dicts / `@lru_cache`**.

### Key principle

> Each cache slot is **keyed by the requesting user and query parameters**. Sharing a single
> slot across users would leak one user's cloud cost data to another — this was a bug in
> `billing_cache` (fixed June 2026, see below).

---

## Backend caches

### 1. VM metrics, cluster health, and recommendations (`routes_vm.py`)

| Cache | TTL | Invalidation |
|-------|-----|--------------|
| `metrics_cache` | 120 s | `invalidate_all_caches()` on any VM operation; skipped if `REAL_TIME_MODE=true` |
| `cluster_health_cache` | 60 s | Same |
| `recommendations_cache` | 180 s | Same |

These are in-process dicts. They are **not shared across Render instances** — each dyno keeps
its own copy. Invalidation on one instance does not propagate to others.

**Cost impact:** Without caching, 100 users checking 10 VMs over 8 hours = ~48 000 GCP
Monitoring API calls/day. With the 2-minute cache: ~4 000 calls (~90 % saving).

---

### 2. Cost query cache (`routes_cost.py`)

| Property | Value |
|----------|-------|
| Type | In-process dict keyed `{username}_{provider}_{start}_{end}_{granularity}` |
| TTL | 3 600 s (1 h) |
| Max entries | 50 (LRU eviction) |
| Invalidation | TTL expiry · `DELETE /api/cost/cache/clear` (auth required) |

The `/api/cost/cache/clear` endpoint requires authentication (fixed June 2026; was unauthenticated
before, allowing anyone to force expensive cache-miss refreshes).

---

### 3. Billing cost cache (`routes_billing.py`)

| Property | Value |
|----------|-------|
| Type | In-process dict `_billing_cache` keyed `{username}:{start_date}:{end_date}` |
| TTL | 3 600 s (1 h) per entry |
| Max entries | 200 (LRU eviction) |
| Invalidation | TTL expiry |

> **Bug fixed June 2026:** The old implementation used a single global `{data, timestamp}`
> slot. All users shared it — user B could receive user A's costs within the 1-hour window.
> The new implementation uses a per-(user, start, end) tuple as the cache key.

---

### 4. Dashboard cost aggregation (`cost_aggregation.py`)

| Property | Value |
|----------|-------|
| Key | Per-username |
| TTL | 3 600 s |
| Force refresh | `POST /api/dashboard/refresh-costs` (calls `refresh_user_costs(force=True)`) |

---

### 5. Budget cost cache (`routes_budgets.py`)

| Property | Value |
|----------|-------|
| TTL | 900 s (15 min) |
| Invalidation | TTL expiry only |

---

### 6. Organisation summary cache (`organizations/service.py`)

| Property | Value |
|----------|-------|
| Key | Per `org_id` |
| TTL | 300 s |
| Invalidation | `invalidate_org_cache(org_id)` — called on billing + member changes |

---

### 7. AWS bucket discovery cache (`byoc/aws_bucket_discovery.py`)

| Property | Value |
|----------|-------|
| Store | MongoDB `aws_bucket_cache` collection |
| TTL | 600 s (10 min) |
| Invalidation | `invalidate_bucket_cache(username)` on credential update; `POST /byoc/aws-buckets/refresh` |

---

### 8. Pricing cache (`pricing/routes_pricing.py`)

| Property | Value |
|----------|-------|
| Store | MongoDB `pricing_cache` collection |
| TTL | 7 days |
| Invalidation | Celery `update_pricing_cache` weekly task; `POST /pricing/refresh` |

> **Known issue:** Refresh inserts new documents rather than upserting — the collection
> grows over time. A cleanup task should be added to prune old entries.

---

### 9. GCP zone cache (`vm/gcp_zones.py`)

| Property | Value |
|----------|-------|
| Key | Per GCP project ID |
| TTL | **None** (process lifetime) |
| Invalidation | `invalidate_gcp_zone_cache()` manual call |

Action: this should be given a TTL (e.g., 1 h) to handle zone additions without a deploy.

---

### 10. `@lru_cache` — process-lifetime singletons

| Location | What | Invalidation |
|----------|------|--------------|
| `cloud/platform_storage_catalog.py` | Platform region catalog | `invalidate_platform_catalog_cache()` |
| `ml/inference.py` | ML model artefacts | `clear_model_artifact_cache()` |

---

## Frontend caches

### A. Auth tokens (localStorage + sessionStorage)

| Key | Store | TTL | Invalidation |
|-----|-------|-----|--------------|
| `authToken` | localStorage | None (JWT expiry is server-side) | Logout, 401 response, session expiry |
| `cachedUser` | sessionStorage | Session lifetime | Re-fetched on every login; cleared on logout / 401 / 403 |

`cachedUser` is written by `AuthContext` after every successful `/api/users/me` fetch.
It is read on startup to avoid a loading flash. The session lifetime ensures it is cleared
when the tab closes.

---

### B. Cloud availability (`CloudAvailabilityContext.jsx`)

| Key | Store | TTL | Invalidation |
|-----|-------|-----|--------------|
| `cache_cloud_availability` | sessionStorage | **5 minutes** | `invalidateCloudAvailabilityCache()` exported from context — call after BYOC connect / disconnect |

> **Fixed June 2026:** Previously had no TTL — a stale availability snapshot could persist
> for the entire session after a BYOC credential change.

---

### C. Page-level UI caches (sessionStorage)

These caches prevent page flicker on re-navigation within a session. They have **no TTL**;
they survive until the tab closes or the relevant action triggers a re-fetch.

| Page / Hook | Keys | Stale risk | Notes |
|-------------|------|-----------|-------|
| `VMClusterPage` | `cache_vm_assignments`, `cache_vm_clusters`, `cache_vm_recs` | Low — VM ops trigger re-fetch | May show outdated data if another browser tab triggers a VM action |
| `BillingPage` | `cache_billing_sub`, `cache_billing_history`, `cache_billing_costs` | Low — refreshed on page visit | No invalidation after payment events |
| `SecurityPage` | `cache_secureFiles`, `cache_2faStatus` | Low | Could lag after file upload/delete in another tab |
| `StoragePage` | `zenith.storage.*` bucket/region | Very low — user selections only | Intentional persistence |
| Cloud bucket hooks | `{prefix}.bucket`, `.region` | Very low | User selection persistence |

**Recommendation:** Add a `ts` field to these caches and evict entries older than 15 minutes
on page mount. This would make stale-data windows predictable.

---

### D. Onboarding / preferences (localStorage)

| Key | Content | Cleared by |
|-----|---------|-----------|
| `zenith_onboarding_complete_{username}` | Tour finished flag | "Restart Tour" button in Settings |
| `zenith_onboarding_dismissed_{username}` | Tour dismissed (skip) | Same |
| `zenith_gs_dismissed_{username}` | Getting Started checklist dismissed | Dismiss button on card |
| `zenith-preferences` | Currency, timezone, date format | Overwritten on settings save |
| `zenith-theme` | dark / light / auto | `ThemeContext.setTheme()` |

Keys are suffixed with `_{username}` (fixed June 2026) so each account gets its own state
on shared devices.

---

## What is NOT cached

| Layer | Reason |
|-------|--------|
| User actions (VM request, release, migrate) | Must execute immediately; cache invalidated on completion |
| Authentication (login, logout, token validation) | Security-critical — never cache |
| File operations (upload, download, delete) | Must reflect immediately |
| MongoDB document reads | MongoDB is fast and local; no additional caching needed |
| WebSocket fan-out | Planned for Phase 25 with Redis pub/sub |

---

## Configuration variables

| Variable | Default | Effect |
|----------|---------|--------|
| `DEMO_MODE=true` | `true` | Returns mock data — zero cloud API calls, zero cost |
| `REAL_TIME_MODE=false` | `false` | When `true`: disables all in-process backend caches — ~10× API cost increase |

### Cost scenario (100 users, 10 VMs, 8-hour day)

```
REAL_TIME_MODE=false (recommended):
  VM metrics:       ~4 000 calls/day   (vs 48 000 — 92 % saving)
  Cluster health:   ~96 calls/day      (vs 480    — 80 % saving)
  Estimated cost:   ~$2–5/day

REAL_TIME_MODE=true:
  VM metrics:        48 000 calls/day
  Cluster health:      480 calls/day
  Estimated cost:   ~$20–40/day
```

---

## Cache monitoring

```bash
# Cost cache stats (authenticated)
curl -H "Authorization: Bearer $TOKEN" https://<api>/api/cost/cache/stats

# Force cost cache clear (authenticated)
curl -X DELETE -H "Authorization: Bearer $TOKEN" https://<api>/api/cost/cache/clear

# Force budget cost refresh
curl -X POST -H "Authorization: Bearer $TOKEN" https://<api>/api/dashboard/refresh-costs

# Pricing refresh
curl -X POST -H "Authorization: Bearer $TOKEN" https://<api>/api/pricing/refresh
```

---

## Known gaps and future work

| Gap | Priority | Plan |
|-----|----------|------|
| GCP zone cache has no TTL | Medium | Add 1-hour TTL |
| Pricing Mongo cache grows (no cleanup) | Low | Add TTL index + pruning task |
| Page-level sessionStorage has no TTL | Low | Add `ts` field + 15-min eviction on mount |
| No shared backend cache across Render instances | Medium | Phase 25: Redis app cache for cost / billing data |
| `BYOC` connect/disconnect should call `invalidateCloudAvailabilityCache()` | Done ✓ | Exported helper available in `CloudAvailabilityContext` |

---

## Summary table

| Cache | Layer | TTL | User-keyed | Invalidation |
|-------|-------|-----|-----------|--------------|
| VM metrics | Backend in-memory | 120 s | ✓ | VM operations |
| Cluster health | Backend in-memory | 60 s | ✓ | VM operations |
| VM recommendations | Backend in-memory | 180 s | ✓ | VM operations |
| Cost query | Backend in-memory | 3 600 s | ✓ | Auth-protected endpoint |
| Billing costs | Backend in-memory | 3 600 s | ✓ | TTL only |
| Dashboard costs | Backend in-memory | 3 600 s | ✓ | Force refresh endpoint |
| Org summary | Backend in-memory | 300 s | ✓ | Member/billing changes |
| AWS buckets | MongoDB | 600 s | ✓ | Credential update |
| Pricing data | MongoDB | 7 days | ✗ | Celery weekly + manual |
| GCP zones | `@lru_cache` | None | ✓ | Manual call |
| Platform catalog | `@lru_cache` | None | ✗ | App startup |
| ML model | `@lru_cache` | None | ✗ | Clear call |
| `authToken` | localStorage | JWT expiry | ✓ | Logout / 401 |
| `cachedUser` | sessionStorage | Session | ✓ | Logout / 401 / 403 |
| Cloud availability | sessionStorage | 5 min | ✓ | BYOC changes |
| VM/Billing/Security UI | sessionStorage | Session | ✓ | Page re-fetch |
| Onboarding state | localStorage | Forever | ✓ | Restart Tour button |
