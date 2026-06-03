# Zenith enterprise improvement backlog (agile)

**Posture:** Modular services (storage, VM, cost, security, provision) — no unified energy optimizer.

**Legend:** Done | In progress | Next | Deferred | Blocked (cloud keys)

| # | Improvement | Status | GCP/Azure keys? |
|---|---------------|--------|-----------------|
| 1 | VM adaptive agent (alerts + optional auto-migrate) | Done | Platform GCP `.env` for live VM ops |
| 2 | Storage sync GCP/Azure UI + API parity | Done | Yes for live sync |
| 3 | Per-user multi-cloud billing (BYOC cost SP / BigQuery) | Done | Yes when keys added |
| 4 | Celery worker + Beat on staging/production | Done | No (copy env to worker on Render) |
| 5 | Admin diagnostics dashboard (Celery, Mongo, build) | Done | No |
| 6 | Auto-scale VM pool (start stopped VM on overload) | Planned | Platform GCP |
| 7 | True federated model rounds | Deferred | No |
| 8 | K8s / live migration (literature) | Deferred | N/A |

Update this file when each sprint ships.
