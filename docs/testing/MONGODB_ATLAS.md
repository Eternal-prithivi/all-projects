# MongoDB Atlas migration guide (Phase 20.15)

Move from local MongoDB to Atlas for shared dev/staging/production.

## 1. Create Atlas cluster

1. Create a free or dedicated M10+ cluster in [MongoDB Atlas](https://www.mongodb.com/atlas).
2. Enable **network access** (IP allowlist or `0.0.0.0/0` only for dev — tighten for prod).
3. Create a database user with read/write on your database.

## 2. Connection string

Set in backend environment (never commit secrets):

```bash
MONGO_CONNECTION_STRING=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
```

The app currently uses database name `CloudResourceOptimizationDB` in `mongo_client.py` unless overridden by test wiring.

For **tests**, always use:

```bash
MONGO_DB_NAME=zenith_test
```

## 3. Migrate data (optional)

From local dump:

```bash
mongodump --uri="mongodb://localhost:27017/CloudResourceOptimizationDB" --out=./dump
mongorestore --uri="$MONGO_CONNECTION_STRING" --db=CloudResourceOptimizationDB ./dump/CloudResourceOptimizationDB
```

Verify user counts and indexes after restore.

## 4. Enable backups

In Atlas: **Backup** → enable continuous cloud backup for production clusters.

## 5. CI and local dev

- **CI:** GitHub Actions uses ephemeral MongoDB 7 service — no Atlas required for PR checks.
- **Local integration tests:** `mongodb://localhost:27017` + `zenith_test` (see [TESTING.md](./TESTING.md)).

## 6. Rollback

Keep local Mongo dump before cutover. Update `MONGO_CONNECTION_STRING` back to local if needed.
