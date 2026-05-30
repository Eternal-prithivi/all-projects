"""
Shared pytest fixtures for Zenith backend tests.

Integration tests use MongoDB (local or CI service). Unit tests keep using mocks.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient
from pymongo.database import Database

# --- Environment before any app imports that load Settings / Mongo singleton ---
_TEST_ENV: dict[str, str] = {
    "MONGO_CONNECTION_STRING": os.environ.get(
        "MONGO_CONNECTION_STRING", "mongodb://localhost:27017"
    ),
    "MONGO_DB_NAME": os.environ.get("MONGO_DB_NAME", "zenith_test"),
    "SECRET_KEY": "pytest-secret-key-do-not-use-in-production",
    "ALGORITHM": "HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "60",
    "AWS_ACCESS_KEY_ID": "test-aws-key",
    "AWS_SECRET_ACCESS_KEY": "test-aws-secret",
    "S3_BUCKET_NAME": "test-bucket",
    "REGULAR_S3_BUCKET_NAME": "test-regular-bucket",
    "SECURE_S3_BUCKET_NAME": "test-secure-bucket",
    "REPLICA_S3_BUCKET_NAME": "test-replica-bucket",
    "REPLICA_S3_REGION": "us-east-1",
    "PRIMARY_S3_REGION": "us-east-1",
    "CELERY_BROKER_URL": "redis://localhost:6379/0",
    "GCP_BUCKET_NAME": "test-gcp-bucket",
    "GCP_PROJECT_ID": "test-gcp-project",
    "GCP_ZONE": "us-central1-a",
    "GCP_SERVICE_ACCOUNT_JSON_PATH": "",
    "AZURE_STORAGE_ACCOUNT_NAME": "testazure",
    "AZURE_STORAGE_ACCOUNT_KEY": "testazurekey",
    "AZURE_CONTAINER_NAME": "test-container",
    "AZURE_TENANT_ID": "test-tenant",
    "AZURE_CLIENT_ID": "test-client",
    "AZURE_CLIENT_SECRET": "test-secret",
    "FRONTEND_URL": "http://localhost:5173",
    "BACKEND_URL": "http://localhost:8000",
    "ENVIRONMENT": "test",
    "DEMO_MODE": "true",
    "RAZORPAY_KEY_ID": "rzp_test",
    "RAZORPAY_KEY_SECRET": "rzp_test_secret",
}


def pytest_configure(config: pytest.Config) -> None:
    for key, value in _TEST_ENV.items():
        os.environ.setdefault(key, value)


def _test_db_name() -> str:
    return os.environ.get("MONGO_DB_NAME", "zenith_test")


def _mongo_uri() -> str:
    return os.environ["MONGO_CONNECTION_STRING"]


def _wire_mongodb_client(db: Database, client: MongoClient) -> None:
    from app.database import mongo_client as mc

    mc.mongodb_client.client = client
    mc.mongodb_client.db = db


def _rebind_route_databases(db: Database) -> None:
    """
    Routes that assign `DB = get_database()` at import time keep stale Collection
    handles if the module was imported before the test DB was wired (e.g. BYOCTestResult import).
    """
    modules = [
        ("app.byoc.routes_byoc", ("DB", "subscriptions_collection", "byoc_collection")),
        ("app.byoc.credential_resolver", ("DB", "byoc_collection")),
        ("app.users.routes_settings", ("DB",)),
        ("app.users.routes_profile", ("DB",)),
        ("app.billing.routes_billing", ("DB",)),
        ("app.admin.routes_admin", ("DB",)),
    ]
    for module_path, attrs in modules:
        try:
            import importlib

            mod = importlib.import_module(module_path)
            if "DB" in attrs:
                mod.DB = db
            if "byoc_collection" in attrs:
                mod.byoc_collection = db["byoc_credentials"]
            if module_path.endswith("routes_byoc"):
                mod.subscriptions_collection = db["subscriptions"]
        except ImportError:
            continue


def _disable_rate_limits(fastapi_app) -> None:
    from app.utils.rate_limit import disable_rate_limits

    disable_rate_limits(fastapi_app)


@pytest.fixture(scope="session")
def mongo_client() -> Generator[MongoClient, None, None]:
    client = MongoClient(_mongo_uri(), serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
    except Exception as exc:
        pytest.skip(f"MongoDB not available at {_mongo_uri()}: {exc}")
    yield client
    client.close()


@pytest.fixture(scope="session")
def test_database(mongo_client: MongoClient) -> Database:
    db = mongo_client[_test_db_name()]
    _wire_mongodb_client(db, mongo_client)
    _rebind_route_databases(db)
    return db


@pytest.fixture(scope="session")
def app(test_database: Database):
    """FastAPI app with test MongoDB wired."""
    from app.main import app as fastapi_app

    _disable_rate_limits(fastapi_app)
    _rebind_route_databases(test_database)
    return fastapi_app


@pytest.fixture(autouse=True)
def _reset_rate_limits_between_tests(request: pytest.FixtureRequest, app) -> Generator[None, None, None]:
    """Re-clear slowapi counters so integration tests do not share one 5/min login bucket."""
    if "integration" not in request.keywords:
        yield
        return
    _disable_rate_limits(app)
    yield
    _disable_rate_limits(app)


@pytest.fixture
def client(app) -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_database(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Clear collections between integration tests (does not require Mongo for unit tests)."""
    if "integration" not in request.keywords:
        yield
        return
    test_database: Database = request.getfixturevalue("test_database")
    yield
    for name in test_database.list_collection_names():
        if name.startswith("system."):
            continue
        test_database[name].delete_many({})


@pytest.fixture
def db(test_database: Database) -> Database:
    return test_database


@pytest.fixture
def user_factory(db: Database):
    from app.auth.auth_utils import get_password_hash

    def _create(
        *,
        username: str | None = None,
        email: str | None = None,
        password: str = "TestPass123!",
        role: str = "user",
        email_verified: bool = True,
        two_fa_enabled: bool = False,
        two_fa_verified: bool = False,
    ) -> dict[str, Any]:
        uname = username or f"user_{uuid.uuid4().hex[:8]}"
        doc = {
            "username": uname,
            "email": email or f"{uname}@example.com",
            "hashed_password": get_password_hash(password),
            "role": role,
            "email_verified": email_verified,
            "two_fa_enabled": two_fa_enabled,
            "two_fa_verified": two_fa_verified,
        }
        db["users"].insert_one(doc)
        return {**doc, "password": password}

    return _create


@pytest.fixture
def auth_headers(client: TestClient, user_factory):
    def _login(
        user: dict[str, Any] | None = None,
        *,
        username: str | None = None,
        password: str | None = None,
        role: str = "user",
        email_verified: bool = True,
        two_fa_enabled: bool = False,
        two_fa_verified: bool = False,
    ):
        if user is None:
            user = user_factory(
                username=username,
                password=password or "TestPass123!",
                role=role,
                email_verified=email_verified,
                two_fa_enabled=two_fa_enabled,
                two_fa_verified=two_fa_verified,
            )
        response = client.post(
            "/api/auth/token",
            data={
                "username": user["username"],
                "password": password or user["password"],
            },
        )
        assert response.status_code == 200, response.text
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}, user

    return _login


@pytest.fixture
def pro_subscription(db: Database):
    """Grant Pro plan so BYOC routes are eligible."""

    def _grant(username: str, plan_id: str = "pro") -> None:
        db["subscriptions"].update_one(
            {"$or": [{"user_id": username}, {"username": username}]},
            {
                "$set": {
                    "user_id": username,
                    "username": username,
                    "plan_id": plan_id,
                    "status": "active",
                }
            },
            upsert=True,
        )

    return _grant
