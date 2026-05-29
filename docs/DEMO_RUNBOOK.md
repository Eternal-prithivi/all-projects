# Zenith Demo Runbook (Viva / Handoff)

**Duration:** ~15 minutes  
**Prerequisites:** Backend on `:8000`, frontend on `:5173`, MongoDB connected, optional AWS BYOC for storage/security.

## 1. Login and session integrity (2 min)

1. Open `/login`, sign in.
2. Go to **Settings → Security** (or Profile security section).
3. Show **This device** card: location, IP, **Device ID** (fingerprint short hash).

## 2. Secure vault — auto SSE (4 min)

1. Open **Security**; complete 2FA if enabled.
2. Upload a `.txt` file containing `api_key=test123` (no “always ask” checkbox).
3. Expect toast: auto-protected with **SSE-S3**; badge **SSE-S3** in file table.
4. Optional: enable **Always ask before encrypting** and re-upload to show encryption choice modal (SSE vs browser).

## 3. Storage ML placement (3 min)

1. **Storage** → upload a sample file → **Analyze & Upload**.
2. Show recommendation modal (CSP, tier, expert votes).

## 4. VM NLP cluster (3 min)

1. **VM Cluster** → request VM with workload description e.g. “Python ML training on GPU”.
2. Show analyze-workload / cluster assignment.

## 5. Cost intelligence (2 min)

1. **Cost Analysis** → cost hub links (Simulator, Optimization, Billing).
2. Show forecast or anomaly banner if data exists.

## 6. Provision (optional, 1 min)

1. **Provision** → Terraform wizard (template select, policy check).

## Screenshots checklist

- [ ] Dashboard Mission Control
- [ ] Security file table with SSE / CSE badges
- [ ] Security settings sessions
- [ ] Storage recommendation modal
- [ ] Cost hub sub-nav

## Quality gate before demo

```bash
cd backend && .venv/bin/python -m pytest -q
cd frontend && npm run lint && npm run build
```
