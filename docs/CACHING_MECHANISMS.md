# Caching Mechanisms in Cloud Resource Optimization Platform

This document provides a comprehensive overview of all caching mechanisms implemented to reduce API costs and improve performance, along with instructions for disabling caching to get real-time data.

---

## 📊 Summary Table

| Component | Cache Type | TTL | Purpose | API Cost Saved | File Location |
|-----------|-----------|-----|---------|----------------|---------------|
| **AWS Cost Explorer** | In-Memory | 1 hour | Reduce Cost Explorer API calls ($0.01/call) | ~$0.01 per hour | `backend/app/cost/routes_cost.py` |
| **Budget Status** | In-Memory | 15 minutes | Reduce Cost Explorer API calls for budgets | ~$0.01 per 15min | `backend/app/budgets/routes_budgets.py` |
| **Dashboard Costs** | In-Memory | 1 hour | Cache monthly AWS costs for dashboard | ~$0.01 per hour | `backend/app/dashboard/routes_dashboard.py` |
| **Billing Costs** | In-Memory | 1 hour | Cache billing cost breakdown | ~$0.01 per hour | `backend/app/billing/routes_billing.py` |
| **VM Metrics** | In-Memory | 10 minutes | Reduce GCP Monitoring API calls | Free tier optimization | `backend/app/vm/routes_vm.py` |
| **Cluster Health** | In-Memory | 5 minutes | Cache GCP cluster health checks | Free tier optimization | `backend/app/vm/routes_vm.py` |
| **Migration Recommendations** | In-Memory | 10 minutes | Cache expensive ML recommendations | CPU/memory optimization | `backend/app/vm/routes_vm.py` |

---

## 🔍 Detailed Cache Implementations

### 1. AWS Cost Explorer API Cache

**Location:** `backend/app/cost/routes_cost.py`

**Cache Details:**
- **TTL:** 1 hour (3600 seconds)
- **Storage:** In-memory dictionary (`cost_cache`)
- **Max Entries:** 50 entries (LRU eviction)
- **Cache Key Format:** `aws_{start_date}_{end_date}_{granularity}`
- **API Cost:** $0.01 per Cost Explorer API call

**What it caches:**
- AWS Cost and Usage data from Cost Explorer API
- Grouped by date range and granularity (DAILY/MONTHLY)

**Code Reference:**
```python
# Cache for cost queries (1 hour TTL)
cost_cache = {}
CACHE_TTL = 3600  # 1 hour in seconds
MAX_CACHE_ENTRIES = 50
```

**Endpoints Affected:**
- `GET /api/cost/aws` - Returns cached data if available

**Cost Savings:**
- **Before:** Every request = $0.01 API call
- **After:** 1 request per hour = $0.01 per hour
- **Savings:** ~99% reduction (if requests within 1 hour window)

---

### 2. Budget Status Cache

**Location:** `backend/app/budgets/routes_budgets.py`

**Cache Details:**
- **TTL:** 15 minutes (900 seconds)
- **Storage:** In-memory dictionary (`budget_cost_cache`)
- **Cache Key Format:** `{provider}_{start_date}_{end_date}`
- **API Cost:** $0.01 per Cost Explorer API call per budget (if not cached)

**What it caches:**
- Cost data per budget (by provider and date range)
- Batches requests: Same date range = 1 API call for all budgets

**Code Reference:**
```python
# Cache for budget cost data (15 minutes TTL to reduce API calls)
budget_cost_cache = {}
BUDGET_CACHE_TTL = 900  # 15 minutes in seconds
```

**Endpoints Affected:**
- `GET /api/budgets/status` - Returns cached budget spend data

**Cost Savings:**
- **Before:** N budgets × $0.01 = $0.01 × N per page load
- **After:** 1 API call per unique date range per 15 min
- **Savings:** ~90-95% reduction (depending on budget count)

**Optimization Features:**
- Request-level batching: Multiple budgets with same date range = 1 API call
- Cross-budget caching: If Budget A and Budget B use same date range, only fetch once

---

### 3. Dashboard Cost Cache

**Location:** `backend/app/dashboard/routes_dashboard.py`

**Cache Details:**
- **TTL:** 1 hour (3600 seconds)
- **Storage:** In-memory dictionary (`aws_cost_cache`)
- **API Cost:** $0.01 per Cost Explorer API call

**What it caches:**
- Monthly AWS cost total for dashboard overview
- Updated only when `/dashboard/refresh-costs` is called

**Code Reference:**
```python
# Cache for AWS cost data (1 hour TTL)
aws_cost_cache = {
    "data": None,
    "timestamp": 0,
    "ttl": 3600  # 1 hour in seconds
}
```

**Endpoints Affected:**
- `GET /api/dashboard/stats` - Uses cached monthly costs
- `POST /api/dashboard/refresh-costs` - Updates cache (makes API call)

**Cost Savings:**
- **Before:** Every dashboard load = $0.01 API call
- **After:** $0.01 only when manually refreshing
- **Savings:** 100% reduction (if not manually refreshing)

---

### 4. Billing Cost Cache

**Location:** `backend/app/billing/routes_billing.py`

**Cache Details:**
- **TTL:** 1 hour (3600 seconds)
- **Storage:** In-memory dictionary (`billing_cache`)
- **Cache Key:** Date range (`{start_date}_{end_date}`)
- **API Cost:** $0.01 per Cost Explorer API call

**What it caches:**
- Multi-provider cost breakdown (AWS, GCP, Azure)
- Used by billing/invoice generation

**Code Reference:**
```python
# Cache for billing cost data (1 hour TTL)
billing_cache = {
    "data": None,
    "timestamp": 0,
    "ttl": 3600  # 1 hour
}
```

**Endpoints Affected:**
- `fetch_real_cloud_costs()` - Used by billing routes

**Cost Savings:**
- **Before:** Every billing request = $0.01 API call
- **After:** $0.01 per hour per date range
- **Savings:** ~99% reduction (if requests within 1 hour window)

---

### 5. VM Metrics Cache

**Location:** `backend/app/vm/routes_vm.py`

**Cache Details:**
- **TTL:** 10 minutes (600 seconds)
- **Storage:** In-memory dictionary (`metrics_cache`)
- **Cache Key Format:** `metrics_{vm_name}_{real|sim}`
- **API Cost:** GCP Monitoring API calls (free tier limits)

**What it caches:**
- VM performance metrics (CPU, memory, disk, network)
- GCP Monitoring API responses
- **Note:** Always fetches fresh user count from MongoDB (no cache)

**Code Reference:**
```python
# Cache for metrics to reduce GCP API calls
metrics_cache = {}
METRICS_CACHE_TTL = 600  # 10 minutes (600 seconds)
```

**Endpoints Affected:**
- `GET /api/vm/metrics/{vm_name}` - Returns cached metrics if available

**Cost Savings:**
- Reduces GCP Monitoring API quota usage
- Prevents hitting free tier limits (3 requests/second)

---

### 6. Cluster Health Cache

**Location:** `backend/app/vm/routes_vm.py`

**Cache Details:**
- **TTL:** 5 minutes (300 seconds)
- **Storage:** In-memory dictionary (`cluster_health_cache`)
- **Cache Key Format:** `cluster_health_{cluster_type}`
- **API Cost:** GCP Compute API calls

**What it caches:**
- Cluster health status (VM availability, load)
- GCP Compute API responses

**Code Reference:**
```python
# Cache for cluster health (5 minutes TTL)
cluster_health_cache = {}
CLUSTER_HEALTH_CACHE_TTL = 300  # 5 minutes
```

**Endpoints Affected:**
- `GET /api/vm/admin/cluster-metrics/{cluster_type}` - Returns cached health data

**Cache Invalidation:**
- Automatically cleared after VM operations (request/release/migrate)
- Manual invalidation: `invalidate_cluster_health_cache()`

**Cost Savings:**
- Reduces GCP Compute API calls
- Faster response times

---

### 7. Migration Recommendations Cache

**Location:** `backend/app/vm/routes_vm.py`

**Cache Details:**
- **TTL:** 10 minutes (600 seconds)
- **Storage:** In-memory dictionary (`recommendations_cache`)
- **Cache Key Format:** `recommendations_{cluster_type}_{min_score}`
- **API Cost:** CPU/memory intensive (not API cost, but compute cost)

**What it caches:**
- ML-powered migration recommendations
- Expensive calculations (analyzes all VMs, metrics, loads)

**Code Reference:**
```python
# Cache for recommendations (10 minutes TTL)
recommendations_cache = {}
RECOMMENDATIONS_CACHE_TTL = 600  # 10 minutes
```

**Endpoints Affected:**
- `GET /api/vm/admin/recommendations` - Returns cached recommendations

**Cost Savings:**
- Reduces CPU/memory usage
- Faster response times for expensive calculations

---

## 🔄 How to Disable Caching for Real-Time Data

If you need real-time data instead of cached data, here are the methods to disable caching:

### Method 1: Set TTL to 0 (Quick Fix)

This forces cache to always expire, requiring fresh fetches.

#### For Cost Explorer API Cache:
```python
# File: backend/app/cost/routes_cost.py
CACHE_TTL = 0  # Change from 3600 to 0
```

#### For Budget Status Cache:
```python
# File: backend/app/budgets/routes_budgets.py
BUDGET_CACHE_TTL = 0  # Change from 900 to 0
```

#### For Dashboard Cost Cache:
```python
# File: backend/app/dashboard/routes_dashboard.py
aws_cost_cache = {
    "data": None,
    "timestamp": 0,
    "ttl": 0  # Change from 3600 to 0
}
```

#### For Billing Cost Cache:
```python
# File: backend/app/billing/routes_billing.py
billing_cache = {
    "data": None,
    "timestamp": 0,
    "ttl": 0  # Change from 3600 to 0
}
```

#### For VM Metrics Cache:
```python
# File: backend/app/vm/routes_vm.py
METRICS_CACHE_TTL = 0  # Change from 600 to 0
```

#### For Cluster Health Cache:
```python
# File: backend/app/vm/routes_vm.py
CLUSTER_HEALTH_CACHE_TTL = 0  # Change from 300 to 0
```

#### For Recommendations Cache:
```python
# File: backend/app/vm/routes_vm.py
RECOMMENDATIONS_CACHE_TTL = 0  # Change from 600 to 0
```

---

### Method 2: Add Query Parameter (Recommended)

Add a `use_cache` or `force_refresh` parameter to endpoints for selective real-time fetching.

#### Example Implementation for Cost Endpoint:
```python
# File: backend/app/cost/routes_cost.py

@router.get("/aws", summary="Get AWS Cost and Usage Data")
async def get_aws_costs(
    start_date: str = Query(...),
    end_date: str = Query(...),
    granularity: str = Query("DAILY"),
    group_by_dimension: Optional[List[str]] = Query(None),
    group_by_tag: Optional[List[str]] = Query(None),
    force_refresh: bool = Query(False, description="Force fresh data, bypass cache")  # NEW
) -> Dict[str, Any]:
    try:
        cache_key = f"aws_{start_date}_{end_date}_{granularity}"
        current_time = time.time()
        
        # Check cache first (unless force_refresh is True)
        if not force_refresh and cache_key in cost_cache:
            cached_data, cached_time = cost_cache[cache_key]
            if (current_time - cached_time) < CACHE_TTL:
                logger.info(f"Using cached AWS cost data for {cache_key}")
                return {"provider": "aws", "data": cached_data, "cached": True}
        
        # Fetch fresh data
        logger.info(f"Fetching fresh AWS cost data for {cache_key} (force_refresh={force_refresh})")
        # ... rest of the code
```

#### Usage:
```bash
# Use cache (default)
GET /api/cost/aws?start_date=2025-01-01&end_date=2025-01-31

# Force real-time fetch
GET /api/cost/aws?start_date=2025-01-01&end_date=2025-01-31&force_refresh=true
```

---

### Method 3: Clear Cache Manually

Use existing cache clear endpoints (if available):

#### For Cost Cache:
```bash
# Clear cost cache
DELETE /api/cost/cache/clear

# Check cache stats
GET /api/cost/cache/stats
```

#### For Other Caches:
Clear cache in code or restart the server (clears all in-memory caches).

---

### Method 4: Bypass Cache in Code

Modify functions to accept a `use_cache` parameter:

#### For Budget Status:
```python
# File: backend/app/budgets/routes_budgets.py

@router.get("/status", response_model=List[BudgetStatus])
async def get_budget_status(
    use_cache: bool = Query(True, description="Use cached data if available")
):
    # ... existing code ...
    
    # Check cache first (unless use_cache is False)
    if use_cache and cache_key in budget_cost_cache:
        cached_spend, cached_timestamp = budget_cost_cache[cache_key]
        if (current_time - cached_timestamp) < BUDGET_CACHE_TTL:
            current_spend = cached_spend
        else:
            del budget_cost_cache[cache_key]
    
    # Fetch fresh data if not cached or use_cache is False
    if not use_cache or cache_key not in budget_cost_cache or current_spend == 0.0:
        # ... fetch fresh data ...
```

---

## ⚠️ Cost Implications of Disabling Cache

### AWS Cost Explorer API
- **Current Cost (with cache):** ~$0.01-0.10 per day
- **Cost (no cache):** ~$1.00-10.00 per day (depending on usage)
- **Increase:** 10-100x more expensive

**Example Scenario:**
- 100 requests per day with cache: ~10 API calls = $0.10/day
- 100 requests per day without cache: 100 API calls = $1.00/day

### Recommendation
- **Keep cache enabled** for production to minimize costs
- **Use `force_refresh=true`** parameter when real-time data is needed
- **Consider reducing TTL** instead of disabling entirely (e.g., 15 min instead of 1 hour)

---

## 🛠️ Implementation Examples

### Example 1: Add Force Refresh to Cost Endpoint

```python
# File: backend/app/cost/routes_cost.py

@router.get("/aws", summary="Get AWS Cost and Usage Data")
async def get_aws_costs(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    granularity: str = Query("DAILY", regex="^(DAILY|MONTHLY)$"),
    group_by_dimension: Optional[List[str]] = Query(None),
    group_by_tag: Optional[List[str]] = Query(None),
    force_refresh: bool = Query(False, description="Bypass cache and fetch fresh data")
) -> Dict[str, Any]:
    """
    Retrieves AWS Cost and Usage data from Cost Explorer.
    
    Args:
        force_refresh: If True, bypasses cache and makes fresh API call ($0.01)
    """
    try:
        cache_key = f"aws_{start_date}_{end_date}_{granularity}"
        current_time = time.time()
        
        # Skip cache if force_refresh is True
        if not force_refresh and cache_key in cost_cache:
            cached_data, cached_time = cost_cache[cache_key]
            if (current_time - cached_time) < CACHE_TTL:
                logger.info(f"Using cached AWS cost data for {cache_key}")
                return {"provider": "aws", "data": cached_data, "cached": True}
        
        # Fetch fresh data
        if force_refresh:
            logger.info(f"Force refresh requested - fetching fresh AWS cost data for {cache_key} (Cost Explorer API call)")
        else:
            logger.info(f"Cache miss - fetching fresh AWS cost data for {cache_key} (Cost Explorer API call)")
        
        # ... rest of fetch logic ...
```

### Example 2: Add Force Refresh to Budget Status

```python
# File: backend/app/budgets/routes_budgets.py

@router.get("/status", response_model=List[BudgetStatus])
async def get_budget_status(
    force_refresh: bool = Query(False, description="Bypass cache and fetch fresh cost data")
):
    """
    Get status of all budgets with current spending.
    
    Args:
        force_refresh: If True, bypasses cache and makes fresh API calls ($0.01 per unique date range)
    """
    # ... existing code ...
    
    # Skip cache check if force_refresh is True
    if not force_refresh and cache_key in budget_cost_cache:
        cached_spend, cached_timestamp = budget_cost_cache[cache_key]
        if (current_time - cached_timestamp) < BUDGET_CACHE_TTL:
            logger.debug(f"Using cached cost data for budget '{budget.name}'")
            current_spend = cached_spend
        else:
            del budget_cost_cache[cache_key]
    
    # Fetch fresh if force_refresh or cache miss
    if force_refresh or cache_key not in budget_cost_cache or current_spend == 0.0:
        if force_refresh:
            logger.info(f"Force refresh requested - fetching cost data for budget '{budget.name}'")
        # ... fetch logic ...
```

### Example 3: Add Real-Time Flag to Dashboard

```python
# File: backend/app/dashboard/routes_dashboard.py

@router.get("/stats")
async def get_dashboard_stats(
    user: dict = Depends(get_current_user),
    real_time_costs: bool = Query(False, description="Fetch real-time costs (bypasses cache, costs $0.01)")
):
    """
    Returns real statistics for the main dashboard overview.
    
    Args:
        real_time_costs: If True, fetches fresh AWS costs ($0.01 API call)
    """
    # ... existing code ...
    
    # Check if real-time costs requested
    if real_time_costs:
        from app.cost.manager import get_aws_cost_and_usage
        from datetime import timedelta
        
        end_date = datetime.utcnow().strftime("%Y-%m-%d")
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        logger.info(f"Real-time costs requested - fetching fresh AWS cost data (Cost Explorer API call)")
        aws_data = get_aws_cost_and_usage(start_date, end_date, "DAILY")
        monthly_costs = sum(
            float(item.get("Total", {}).get("UnblendedCost", {}).get("Amount", 0))
            for item in aws_data.get("ResultsByTime", [])
        )
        
        # Update cache with fresh data
        aws_cost_cache["data"] = monthly_costs
        aws_cost_cache["timestamp"] = time.time()
    else:
        # Use cached monthly costs
        monthly_costs = aws_cost_cache.get("data", 0.0)
    
    # ... rest of code ...
```

---

## 📋 Cache Management Endpoints

### Check Cache Status

```bash
# Get cost cache statistics
GET /api/cost/cache/stats

# Response:
{
  "total_entries": 5,
  "active_entries": 3,
  "expired_entries": 2,
  "max_capacity": 50,
  "utilization": "10.0%",
  "cache_ttl_minutes": 60
}
```

### Clear Cache

```bash
# Clear cost cache
DELETE /api/cost/cache/clear

# Response:
{
  "success": true,
  "entries_cleared": 5,
  "message": "Cost cache cleared successfully. Next requests will fetch fresh data."
}
```

---

## 🔍 Monitoring Cache Effectiveness

### Log Messages to Watch For

**Cache Hits (No API Call):**
```
Using cached AWS cost data for aws_2025-01-01_2025-01-31_DAILY
Using cached cost data for budget 'Monthly Budget'
```

**Cache Misses (API Call Made):**
```
Fetching fresh AWS cost data for aws_2025-01-01_2025-01-31_DAILY (Cost Explorer API call)
Fetching cost data for budget 'Monthly Budget' (cache key: aws_2025-01-01_2025-01-31) - Cost Explorer API call
```

**Force Refresh:**
```
Force refresh requested - fetching fresh AWS cost data...
```

---

## ✅ Best Practices

### For Production:
1. ✅ **Keep caching enabled** - Significantly reduces API costs
2. ✅ **Use appropriate TTLs** - Balance freshness vs. cost
3. ✅ **Add `force_refresh` parameter** - Allow selective real-time fetching
4. ✅ **Monitor cache hit rates** - Use `/api/cost/cache/stats` endpoint
5. ✅ **Clear cache after data updates** - Use `DELETE /api/cost/cache/clear`

### For Development/Testing:
1. ✅ **Use shorter TTLs** (e.g., 5 minutes) - Faster feedback
2. ✅ **Add `force_refresh` flag** - Easy testing without code changes
3. ✅ **Monitor API calls** - Check logs for cache hit/miss patterns

### For Real-Time Requirements:
1. ✅ **Don't disable cache entirely** - Too expensive
2. ✅ **Add query parameter** - `force_refresh=true` for specific requests
3. ✅ **Reduce TTL** - Instead of disabling, reduce to 5-15 minutes
4. ✅ **Use webhooks/events** - For true real-time updates (more complex)

---

## 🚨 Important Notes

1. **In-Memory Cache Limitation:** All caches are in-memory and will be lost on server restart
2. **No Shared Cache:** Each server instance has its own cache (if running multiple instances)
3. **Cache Size Limits:** Cost cache limited to 50 entries (LRU eviction)
4. **TTL Override:** Setting TTL to 0 effectively disables cache (but code still runs)

---

**Last Updated:** November 1, 2025  
**Status:** ✅ All caches documented and configurable

