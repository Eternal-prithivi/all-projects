# Zenith services reference (plain English)

> **What this is:** A single list of every **external service** Zenith connects to — what it does, where you configure it, and what breaks if it stops working.
>
> **Last updated:** 2026-07-11  
> **Related:** `CLOUD_ACCOUNT_MIGRATION_GUIDE.md` (cloud accounts only) · `docs/setup/DEPLOYMENT_SECRETS.md` (env var checklist)

---

## At a glance

| Service | Category | Required? | One-line job in Zenith |
|---------|----------|-----------|------------------------|
| **Render** | Hosting | Yes (production API) | Runs the backend API, Celery worker, and provision worker |
| **Vercel** | Hosting | Yes (production site) | Hosts the React website at rajverse.me |
| **MongoDB Atlas** | Database | Yes | Stores users, files metadata, billing, tickets, BYOC creds |
| **CloudAMQP** | Message queue | Yes (background jobs) | Celery task queue — emails, alerts, tiering, drift checks |
| **AWS** | Cloud | Yes (platform mode) | S3 storage, EC2 VMs, Cost Explorer, Terraform |
| **Google Cloud (GCP)** | Cloud | Yes (platform mode) | GCS storage, Compute VMs, billing export, Terraform |
| **Microsoft Azure** | Cloud | Yes (platform mode) | Blob storage, VMs, Cost Management, Terraform |
| **Razorpay** | Payments | Yes (paid plans) | INR subscriptions and checkout |
| **Gmail SMTP** | Email | Yes (auth & support) | Verification, password reset, tickets, alerts |
| **Twilio** | SMS | Optional | Password reset OTP, security/budget SMS alerts |
| **Sentry** | Monitoring | Optional | Crash and error reports (frontend + backend) |
| **Cloudflare Turnstile** | Bot protection | Optional | CAPTCHA on login/register |
| **Google OAuth** | Sign-in | Optional | “Sign in with Google” button |
| **GitHub** | Code + releases | Yes (dev workflow) | Source code, CI, desktop installer downloads |
| **GitHub Actions** | CI/CD | Yes (team workflow) | Tests, deploy hooks, keep-alive pings, desktop builds |

---

## How to read each section

Every service below has:

- **What it is** — the company/product in everyday words  
- **What Zenith uses it for** — features in the app  
- **Where you configure it** — file or dashboard  
- **Required?** — can the app run without it?  
- **In plain English** — analogy or simple explanation  
- **If it breaks** — what users notice  

---

## 1. Hosting & deployment

### Render

| | |
|---|---|
| **What it is** | Cloud host that runs your backend Docker containers 24/7 (free tier sleeps after ~15 min idle). |
| **What Zenith uses it for** | **zenith-api** (FastAPI), **zenith-celery** (background worker + scheduler), **zenith-provision** (Terraform jobs). |
| **Where you configure it** | [render.com](https://render.com) dashboard · `render.yaml` in repo (service names, some env defaults). |
| **Required?** | **Yes** for production API at rajverse.me. |
| **In plain English** | Render is the **engine room** — the brain of Zenith lives here, not on your laptop. |
| **If it breaks** | Website loads but login, uploads, billing, and API calls fail. |

**Key env vars (set in Render dashboard):** `MONGO_*`, `SECRET_KEY`, all `AWS_*` / `GCP_*` / `AZURE_*`, `CELERY_BROKER_URL`, `RAZORPAY_*`, `GMAIL_*`, `TWILIO_*`, etc.

---

### Vercel

| | |
|---|---|
| **What it is** | Host for static sites and frontend frameworks (React/Vite). |
| **What Zenith uses it for** | Serves the React app — pages, dashboard UI, marketing site. Proxies `/api` to Render backend. |
| **Where you configure it** | [vercel.com](https://vercel.com) dashboard · `frontend/vercel.json` (API rewrite rules). |
| **Required?** | **Yes** for production frontend. |
| **In plain English** | Vercel is the **shop window** — what users see and click. It talks to Render for data. |
| **If it breaks** | rajverse.me doesn’t load or shows errors; backend may still be fine. |

**Key env vars:** `VITE_API_URL`, `VITE_SITE_URL`, optional `VITE_SENTRY_DSN`, `VITE_TURNSTILE_SITE_KEY`.

---

## 2. Database

### MongoDB Atlas

| | |
|---|---|
| **What it is** | Cloud database (NoSQL) — documents instead of spreadsheet tables. |
| **What Zenith uses it for** | **Everything persistent:** user accounts, sessions, file records, secure vault metadata, VMs, cost cache, support tickets, BYOC encrypted credentials, billing state, notifications. |
| **Where you configure it** | [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas) · `MONGO_CONNECTION_STRING` + `MONGO_DB_NAME` in `.env` / Render. |
| **Required?** | **Yes** — API won’t start without it. |
| **In plain English** | MongoDB is Zenith’s **filing cabinet** — every account and file reference is stored here. Actual file bytes live in AWS/GCP/Azure. |
| **If it breaks** | Nothing works — login, dashboard, uploads all fail. Health check shows `mongo_connected: false`. |

**Not the same as cloud storage** — deleting Mongo doesn’t delete S3/GCS files, and vice versa.

---

## 3. Background jobs & queues

### CloudAMQP (RabbitMQ)

| | |
|---|---|
| **What it is** | Managed message queue — like a to-do list workers pick tasks from. |
| **What Zenith uses it for** | **Celery broker** — schedules and delivers background jobs. |
| **Where you configure it** | [cloudamqp.com](https://www.cloudamqp.com) · `CELERY_BROKER_URL` (starts with `amqps://`). |
| **Required?** | **Yes** for Celery worker on Render. API can boot without it but background tasks won’t run. |
| **In plain English** | When Zenith needs to “do something later” (send a nightly alert, tier old files, check provision drift), it drops a note in this queue and the Celery worker picks it up. |
| **If it breaks** | App feels fine short-term, but **no scheduled emails/SMS**, no storage tiering jobs, no drift checks, no payment renewal tasks. |

### Celery (software — not a paid service)

| | |
|---|---|
| **What it is** | Python task runner — part of your codebase, not a separate subscription. |
| **What Zenith uses it for** | Runs jobs from the queue: security alerts, budget alerts, cost anomaly detection, storage optimization, provision drift, subscription tasks. |
| **Where you configure it** | `backend/app/celery_worker.py` · Render service **zenith-celery**. |
| **Required?** | **Yes** in production for full feature set. |
| **In plain English** | Celery is the **night shift worker** that handles tasks while users aren’t clicking buttons. |

---

## 4. Cloud providers (platform + BYOC)

These three are Zenith’s core product — multi-cloud storage, VMs, cost, and provision.

### Amazon Web Services (AWS)

| | |
|---|---|
| **What it is** | Amazon’s cloud — S3 storage, EC2 virtual machines, IAM, Cost Explorer. |
| **What Zenith uses it for** | File uploads (S3), secure vault, multi-region buckets, VM cluster (EC2), cost analysis, Terraform/Boto3 provision, BYOC IAM role trust. |
| **Where you configure it** | AWS Console · `AWS_*`, `S3_*`, `SECURE_S3_*` in `.env` / Render · BYOC in Settings UI. |
| **Required?** | **Yes** for platform tri-cloud (unless user is BYOC-only for AWS). |
| **In plain English** | AWS is one of three **warehouses** where Zenith stores files and runs VMs. |
| **If it breaks** | AWS uploads/sync fail; AWS cost/VM features unavailable for platform users. |

See `CLOUD_ACCOUNT_MIGRATION_GUIDE.md` for account swap steps.

---

### Google Cloud Platform (GCP)

| | |
|---|---|
| **What it is** | Google’s cloud — Cloud Storage, Compute Engine, BigQuery billing export. |
| **What Zenith uses it for** | GCS uploads, secure vault, VMs, cost (BigQuery export), Terraform provision. |
| **Where you configure it** | GCP Console · `GCP_*` + service account JSON file · BYOC in Settings. |
| **Required?** | **Yes** for platform tri-cloud. |
| **In plain English** | GCP is the second **warehouse** — same idea as AWS, different company. |
| **If it breaks** | GCP storage/VM/cost paths fail for platform users. |

**Separate from Google OAuth** — storage service account ≠ “Sign in with Google” OAuth client.

---

### Microsoft Azure

| | |
|---|---|
| **What it is** | Microsoft’s cloud — Blob Storage, VMs, Cost Management, Entra ID app registrations. |
| **What Zenith uses it for** | Blob uploads, secure vault, multi-region storage accounts, cost analysis, Terraform provision. |
| **Where you configure it** | Azure Portal · `AZURE_*` in `.env` / Render · catalog JSON for regional accounts · BYOC in Settings. |
| **Required?** | **Yes** for platform tri-cloud. |
| **In plain English** | Azure is the third **warehouse** — completes the “use any cloud” promise. |
| **If it breaks** | Azure storage/cost/VM features fail for platform users. |

---

### BYOC (Bring Your Own Cloud) — not a separate vendor

| | |
|---|---|
| **What it is** | A **feature**, not a service — Pro/Enterprise users paste **their own** AWS/GCP/Azure credentials in Settings. |
| **What Zenith uses it for** | User’s cloud bills go to them; Zenith orchestrates uploads/VMs/cost with their keys (encrypted in MongoDB). |
| **Where you configure it** | **Dashboard → Settings → Cloud connections** (per user). |
| **Required?** | **No** — optional upgrade path. |
| **In plain English** | BYOC means “plug in your own warehouse keys” instead of using Zenith’s shared platform keys. |
| **If it breaks** | Only that user’s cloud features fail until they reconnect in Settings. |

---

## 5. Payments

### Razorpay

| | |
|---|---|
| **What it is** | Indian payment gateway — cards, UPI, netbanking for subscriptions. |
| **What Zenith uses it for** | **Plan checkout** (Basic, Pro, Enterprise), payment verification, webhooks, org seat billing. Users pay in **INR (₹)**. |
| **Where you configure it** | [dashboard.razorpay.com](https://dashboard.razorpay.com) · `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` in `.env` / Render. |
| **Required?** | **Yes** if you sell paid plans. Free tier works without it. |
| **In plain English** | Razorpay is the **cash register** — when someone upgrades from Free to Pro, Razorpay handles the money. |
| **If it breaks** | Users can’t upgrade plans or complete checkout; free tier still works. |

**Code:** `backend/app/payments/` · Frontend billing pages redirect to Razorpay checkout.

**Test vs live:** Keys starting with `rzp_test_` are sandbox; `rzp_live_` for real money.

---

## 6. Email

### Gmail SMTP (Google App Password)

| | |
|---|---|
| **What it is** | Sending email through your Gmail account using an **app password** (not your normal Gmail password). |
| **What Zenith uses it for** | **Signup verification** · **Password reset links** · **Support ticket** replies & OTP · **Org invites** · **Budget alerts** · **Security alert emails** · **Contact form** notifications · **Signup notify** to admin. |
| **Where you configure it** | Google Account → Security → 2-Step Verification → App passwords · `GMAIL_SENDER_EMAIL`, `GMAIL_APP_PASSWORD`, `ADMIN_EMAIL`, `SIGNUP_NOTIFY_EMAIL` in Render. |
| **Required?** | **Yes** for email verification and password reset by email. |
| **In plain English** | Gmail is Zenith’s **post office** — it sends the “click here to verify” and “reset your password” messages. |
| **If it breaks** | New users can’t verify email; password reset by email fails; support email notifications stop. SMS reset may still work if Twilio is on. |

**Not Gmail API OAuth** — simple SMTP with app password via `smtplib`.

---

## 7. SMS

### Twilio

| | |
|---|---|
| **What it is** | Cloud SMS and voice API — sends text messages programmatically. |
| **What Zenith uses it for** | **Password reset OTP** (text code instead of email link) · **Security alerts** (unencrypted sensitive files) · **Budget alert SMS** (optional). |
| **Where you configure it** | [twilio.com/console](https://www.twilio.com/console) · `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` (or `TWILIO_MESSAGING_SERVICE_SID`) in `.env` / Render. |
| **Required?** | **Optional** — app works without it; email reset is the fallback. |
| **In plain English** | Twilio is the **text message sender** — when you choose “reset via SMS,” Twilio delivers the 6-digit code. |
| **If it breaks** | SMS reset and SMS alerts stop; email paths still work. UI shows a hint to use email instead. |

**India note:** Sending to `+91` numbers may need an Indian Twilio number or geo permissions enabled in Twilio Console.

---

## 8. Auth, trust & bot protection

### JWT / `SECRET_KEY` (your app — not a vendor)

| | |
|---|---|
| **What it is** | A long random string **you generate** — signs login tokens. |
| **What Zenith uses it for** | Keeps users logged in securely · **Encrypts BYOC credentials** in MongoDB (derived key). |
| **Where you configure it** | `SECRET_KEY` in `.env` / Render — generate with `openssl rand -hex 32`. |
| **Required?** | **Yes**. |
| **In plain English** | Like the **master key** to the building — proves a login session is genuine. |
| **If you change it** | Everyone must log in again; **all stored BYOC passwords become unreadable** until users reconnect. |

---

### Google OAuth (optional)

| | |
|---|---|
| **What it is** | “Sign in with Google” — Google handles identity, Zenith gets an email/profile. |
| **What Zenith uses it for** | Optional SSO on login/register pages. |
| **Where you configure it** | Google Cloud Console → OAuth client · `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` on Render. |
| **Required?** | **No** — your project currently uses email/password only. |
| **In plain English** | A **shortcut login button** — “use my Google account instead of a new password.” |
| **If it breaks** | Google button hidden or fails; email/password login still works. |

---

### Cloudflare Turnstile (optional)

| | |
|---|---|
| **What it is** | Privacy-friendly CAPTCHA — proves a human is signing up, not a bot. |
| **What Zenith uses it for** | Bot protection on **login** and **register** pages. |
| **Where you configure it** | [dash.cloudflare.com](https://dash.cloudflare.com) → Turnstile · `TURNSTILE_SECRET_KEY` (Render) + `VITE_TURNSTILE_SITE_KEY` (Vercel). |
| **Required?** | **No** — skipped when keys are empty. |
| **In plain English** | The **“I’m not a robot”** check at the door. |
| **If it breaks** | Signup/login may work without CAPTCHA (or block if strictly required). |

---

## 9. Observability & reliability

### Sentry

| | |
|---|---|
| **What it is** | Error tracking SaaS — captures crashes and stack traces. |
| **What Zenith uses it for** | Frontend React errors + backend Python exceptions in production. |
| **Where you configure it** | [sentry.io](https://sentry.io) · `SENTRY_DSN` (Render) · `VITE_SENTRY_DSN` (Vercel). |
| **Required?** | **Optional** — recommended for production debugging. |
| **In plain English** | A **black box flight recorder** — when something crashes, you get an alert with details. |
| **If it breaks** | App still runs; you just don’t get automatic crash reports. |

---

### GitHub Actions (keep-alive & uptime)

| | |
|---|---|
| **What it is** | Automation built into GitHub — runs scripts on schedule or on git push. |
| **What Zenith uses it for** | **CI tests** (pytest, lint, Playwright) · **Deploy hooks** to Render/Vercel · **Render keep-alive** (ping every 5 min so free tier doesn’t sleep) · **Desktop installer builds** · **Uptime checks** (optional) · **Secret scanning** (Gitleaks). |
| **Where you configure it** | `.github/workflows/*.yml` · GitHub repo → Settings → Secrets. |
| **Required?** | **Yes** for automated quality gates; keep-alive optional but helps Render free tier. |
| **In plain English** | A **robot assistant** that tests code, deploys updates, and pokes the server so it stays awake. |
| **If it breaks** | Manual deploys still work; CI won’t catch bugs; Render may sleep more often. |

---

## 10. Desktop app

### Electron + GitHub Releases

| | |
|---|---|
| **What it is** | Electron wraps the website in a desktop window; GitHub Releases hosts installer files (.dmg, .exe, AppImage). |
| **What Zenith uses it for** | **Desktop downloads** at `/download` — native app that loads rajverse.me. Auto-update stub via `electron-updater`. |
| **Where you configure it** | `desktop/` package · tag `desktop-v*.*.*` triggers `.github/workflows/desktop-release.yml` · `frontend/public/releases.json` for version metadata. |
| **Required?** | **No** — browser works fine without desktop app. |
| **In plain English** | A **desktop shortcut** to the same website, distributed like any normal app installer. |
| **If it breaks** | Users use the browser; `/download` may show “installers not ready.” |

**No cloud credentials in desktop** — it’s just a browser shell.

---

## 11. ML & NLP (bundled — no external API)

These run **inside your backend container** — no separate subscription or API key.

| Library | What Zenith uses it for | Paid service? |
|---------|-------------------------|---------------|
| **spaCy** (`en_core_web_sm`) | Provision wizard — understands plain-English workload descriptions | No — model bundled |
| **TextBlob** | Sentiment / text helpers in ML workflows | No |
| **scikit-learn / custom models** | Storage tier recommendations, cost patterns | No |

**In plain English:** The “smart suggestions” run on your server CPU — you don’t pay OpenAI or Google for them.

---

## 12. WebSockets (built-in — not a vendor)

| | |
|---|---|
| **What it is** | Live connection between browser and API — part of FastAPI, not a third-party service. |
| **What Zenith uses it for** | Real-time **notifications** (bell icon) · **Support ticket** instant refresh when admin replies. |
| **Where you configure it** | `backend/app/websockets/` — no API key. |
| **Required?** | **Built-in** — works as long as Render API is up. |
| **In plain English** | A **phone line** that stays open so the app can push “you have a new message” without refreshing the page. |

---

## 13. Services map — where each env var lives

| Variable group | Service | Config file |
|----------------|---------|-------------|
| `MONGO_*` | MongoDB Atlas | `backend/.env` · Render |
| `SECRET_KEY` | Your app (JWT + BYOC encryption) | `backend/.env` · Render |
| `AWS_*`, `S3_*`, `SECURE_S3_*` | AWS | `backend/.env` · Render |
| `GCP_*` + JSON file | GCP | `backend/.env` · Render secret file |
| `AZURE_*` | Azure | `backend/.env` · Render · catalog JSON |
| `CELERY_BROKER_URL` | CloudAMQP | `backend/.env` · Render |
| `RAZORPAY_*` | Razorpay | `backend/.env` · Render |
| `GMAIL_*`, `ADMIN_EMAIL`, `SIGNUP_NOTIFY_EMAIL` | Gmail SMTP | `backend/.env` · Render |
| `TWILIO_*` | Twilio | `backend/.env` · Render |
| `SENTRY_DSN` | Sentry | `backend/.env` · Render |
| `VITE_SENTRY_DSN` | Sentry | Vercel |
| `GOOGLE_OAUTH_*` | Google OAuth | Render |
| `TURNSTILE_SECRET_KEY` | Cloudflare | Render |
| `VITE_TURNSTILE_SITE_KEY` | Cloudflare | Vercel |
| `VITE_API_URL`, `VITE_SITE_URL` | Vercel routing | Vercel |
| `FRONTEND_URL`, `BACKEND_URL`, `PUBLIC_API_URL` | Render + CORS | Render |
| `PLATFORM_OWNER_USERNAMES` | Your deployment config | Render |

---

## 14. Your deployment today (auto-detected)

| Service | Status in this project |
|---------|------------------------|
| Render + Vercel | Production on rajverse.me |
| MongoDB Atlas | Configured |
| CloudAMQP | Configured (`CELERY_BROKER_URL`) |
| AWS / GCP / Azure | Platform keys configured; multi-region catalog on |
| Razorpay | Test keys configured (`rzp_test_*`) |
| Gmail SMTP | Configured |
| Twilio | Configured |
| Sentry | Configured (backend + frontend DSN) |
| Google OAuth | **Not configured** (empty) |
| Cloudflare Turnstile | **Optional** — set keys to enable |
| Desktop releases | **v0.1.4** on GitHub Releases |

---

## 15. What breaks when — quick troubleshooting

| Symptom | Likely service |
|---------|----------------|
| Can’t log in / “session expired” | MongoDB down or `SECRET_KEY` changed |
| Upload fails on Storage | AWS / GCP / Azure credentials or bucket names |
| Can’t upgrade plan | Razorpay keys or webhook |
| No verification email | Gmail app password wrong or blocked |
| SMS reset doesn’t arrive | Twilio config or India geo permissions |
| Dashboard empty after idle | Render free tier slept — keep-alive or wait for wake |
| No background alerts | Celery worker down or CloudAMQP URL wrong |
| BYOC test fails | User’s own cloud creds — not platform `.env` |
| Desktop download missing | GitHub Release tag not built yet |

---

## 16. Related guides

| Doc | Use when |
|-----|----------|
| `CLOUD_ACCOUNT_MIGRATION_GUIDE.md` | Swapping AWS/GCP/Azure accounts |
| `docs/setup/DEPLOYMENT_SECRETS.md` | Full env var list for Render/Vercel |
| `docs/setup/CREDENTIAL_ROTATION.md` | Rotating keys on same account |
| `docs/setup/CLOUD_CREDENTIAL_SETUP_GUIDE.md` | First-time cloud setup |
| `docs/cloud/CREDENTIAL_CONTRACT.md` | Platform vs BYOC technical contract |

---

## One-page cheat sheet

```
ZENITH SERVICES — WHO DOES WHAT
────────────────────────────────
Render          → runs API + workers (brain)
Vercel          → runs website (shop window)
MongoDB Atlas   → stores all app data (filing cabinet)
CloudAMQP       → task queue for background jobs
Celery          → runs scheduled/background tasks (night shift)

AWS / GCP / Azure → file storage, VMs, cost, provision (warehouses)
BYOC            → user's own cloud keys in Settings (optional)

Razorpay        → paid plan checkout (cash register)
Gmail SMTP      → emails: verify, reset, support, alerts (post office)
Twilio          → SMS: reset OTP, alerts (optional texts)

SECRET_KEY      → login tokens + BYOC encryption (master key)
Google OAuth    → optional "Sign in with Google"
Turnstile       → optional bot CAPTCHA

Sentry          → crash reports (optional flight recorder)
GitHub Actions  → CI, deploy, keep-alive, desktop builds

Electron + GitHub Releases → desktop installers (optional app wrapper)
spaCy/TextBlob  → built-in ML, no external API bill
```

---

*Guide version: 2026-07-11 · Maintained in `ai-docs/` for owner and agent continuity.*
