# Shared Organization Billing & Resources (Phase 24)

**Status:** Implemented (seat-based org billing + org-scoped resource ACL).

## Billing model

1. **One subscription per organization** — `organizations` document holds `plan_id`, `seat_count`, `billing_cycle`, `subscription_status`, Razorpay IDs, and billing period.
2. **Seats** — Each active `organization_members` row consumes a seat. Invites do not reserve seats in v1; accept is blocked when `members.count >= seat_count` (HTTP 402).
3. **Who pays** — Owner or admin (`can_manage_billing`). Checkout via `POST /api/organizations/billing/checkout` + `verify-payment`.
4. **Member plans** — `get_effective_subscription(username)` returns org plan when user is in an org; personal `subscriptions` doc is frozen (`migrated_to_org` after owner migration).
5. **Cloud pass-through** — BYOC usage remains per-member; Team summary rollups unchanged.

## Resource ownership

| Collection | Fields | ACL |
|------------|--------|-----|
| `vm_assignments` | `org_id`, `created_by` | Admin: all org; member: own |
| `provision_deployments` | `org_id`, `created_by` | Same |
| `files` | `org_id`, `created_by` | Same |

Module: `backend/app/organizations/resource_acl.py` — `list_filter_for_user`, `can_access_resource`, `org_tags_for_create`.

Quotas: `backend/app/organizations/limits.py` — org VM/storage limits from org `plan_id`.

## Key APIs

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/organizations/billing` | Plan, seats, period, `can_manage_billing` |
| POST | `/api/organizations/billing/checkout` | Razorpay order (admin) |
| POST | `/api/organizations/billing/verify-payment` | Activate org sub |
| PATCH | `/api/organizations/billing/seats` | Increase seats |
| POST | `/api/organizations/billing/cancel` | Cancel at period end |
| POST | `/api/organizations/billing/migrate-personal` | Owner moves personal sub to org |
| GET | `/api/organizations/resources/summary` | Org VM/storage totals |
| PATCH | `/api/organizations/resources/reassign` | Admin reassign `created_by` |

Resolver gate: `subscription_service.get_effective_subscription()` — used by `/payments/my-subscription`, VM/storage/provision limits, org summary plan rollups.

## Migration

1. **Lazy org billing defaults** — `ensure_org_billing_defaults()` on first billing read (`plan_id=free`, `seat_count=max(1, member_count)`).
2. **Backfill** — `backend/scripts/backfill_org_resources.py` tags existing resources with `org_id` + `created_by` for members.

## Frontend

- **Team:** Seats card, org resources card, migrate-personal CTA
- **Billing:** Organization billing panel (admin checkout + seat stepper; member read-only)
- **VM / Storage / Provision:** Org + creator labels; admin toggle “Show all team resources”

## Out of scope (v1)

- Razorpay Subscription API auto-seat proration
- Merging BYOC into org Razorpay invoice
- Pending invites reserving seats

## Related code

- Billing service: `backend/app/organizations/billing.py`
- Routes: `backend/app/organizations/routes_billing.py`
- Shared checkout: `backend/app/payments/checkout.py`
- Tests: `backend/tests/integration/test_org_billing_resources.py`
- Manual QA: `docs/testing/manual_testing.md` rows 6.12a–f
