## Setup Guide

This guide explains how to configure secrets and service account keys for the backend.

Required environment variables (place in `backend/.env`):

- `MONGO_CONNECTION_STRING` — MongoDB connection string.
- `MONGO_DB_NAME` — Database name.
- `GCP_SERVICE_ACCOUNT_JSON_PATH` — Absolute path to your GCP service account JSON file, or a path relative to the repository `backend` folder.

Notes and best practices:

- Use the canonical name `GCP_SERVICE_ACCOUNT_JSON_PATH` in the `.env` file. Some older code may have used `GCP_SA_KEY_PATH`; the codebase supports that as a fallback but prefer the canonical name.
- Never commit service account JSON files or other secrets to the repository. Add them to `.gitignore`.

Example `backend/.env` snippet:

```
MONGO_CONNECTION_STRING="mongodb://localhost:27017"
MONGO_DB_NAME="CloudResourceOptimizationDB"
GCP_SERVICE_ACCOUNT_JSON_PATH="/Users/you/keys/zenith-gcp-key.json"
```

If you prefer to use a relative path (not recommended for production), set the value relative to the repo `backend` directory, for example:

```
GCP_SERVICE_ACCOUNT_JSON_PATH="secrets/zenith-gcp-key.json"
```

The application exposes a `/health` endpoint that reports whether MongoDB is connected and whether the GCP credentials file is present.

Security checklist:
- Add `backend/*.json` or any secret directory to `.gitignore`.
- Use environment-specific secret storage for production (e.g., AWS Secrets Manager, GCP Secret Manager, Vault).
