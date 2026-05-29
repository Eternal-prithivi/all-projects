# Credential rotation runbook

Rotate credentials if they may have been exposed (committed to Git, shared in chat, or lost device).

## JWT `SECRET_KEY`

1. Generate a new random string (64+ chars).
2. Update `SECRET_KEY` in Render/Vercel env and local `.env`.
3. Redeploy backend — **all users must sign in again**.

## MongoDB

1. Create new DB user/password in Atlas (or rotate root password).
2. Update `MONGO_CONNECTION_STRING`.
3. Redeploy; verify `/health` shows `mongo_connected: true`.

## AWS access keys (platform or BYOC)

1. IAM → create new access key → update env or BYOC in UI.
2. Disable/delete old key after confirming uploads and Cost Explorer work.

## GCP service account JSON

1. IAM → Service account → Keys → **Add key** (JSON).
2. Replace file path or BYOC JSON paste; delete old key in console.
3. Old JSON cannot be re-downloaded.

## Google OAuth (SSO)

1. Google Cloud Console → APIs & Credentials → OAuth client.
2. Rotate client secret; update `GOOGLE_OAUTH_CLIENT_SECRET` and redeploy.

## Razorpay

1. Razorpay dashboard → regenerate API secret if compromised.
2. Update `RAZORPAY_KEY_SECRET` and webhook secret; redeploy.

## Twilio

1. Console → rotate Auth Token.
2. Update `TWILIO_AUTH_TOKEN`.

## After rotation

- [ ] `git log` — ensure `.env` was never committed (if yes: rotate everything + consider `git filter-repo`)
- [ ] Test login, upload, BYOC test connection, admin dashboard
- [ ] Note rotation date in your internal ops log
