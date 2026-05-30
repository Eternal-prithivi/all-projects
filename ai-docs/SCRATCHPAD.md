# SCRATCHPAD.md

## 🔄 Current Resume State

**Status:** Phase **20.5** code landed — verify CI on `stage` push.

**Done in repo:** CI-gated deploy, required Playwright, coverage 40%, audits, CodeQL, gitleaks, terraform plan PR job, ESLint zero warnings, jspdf 4.x, Trivy Dockerfile scan.

**Manual (you):** **20.5.10** — GitHub → Settings → Branches → protect `stage` with checks: `backend`, `frontend`, `terraform-validate`, `playwright`, `security-audit`. Set secret `STAGE_API_URL` for post-deploy smoke.

**Next:** Confirm green CI, then start **Phase 21**.
