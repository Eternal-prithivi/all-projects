"""Tests for Phase 8 feedback evaluation and retraining readiness."""

from datetime import datetime, timedelta

from bson import ObjectId

from app.ml.feedback import (
    calculate_retraining_readiness,
    classify_feedback_score,
    evaluate_feedback,
    normalize_storage_tier,
)
from app.ml.models import OutcomeQuality


class FakeCursor(list):
    def sort(self, key, direction):
        reverse = direction < 0
        return FakeCursor(sorted(self, key=lambda doc: doc.get(key) or datetime.min, reverse=reverse))

    def limit(self, count):
        return FakeCursor(self[:count])


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = docs or []

    def find(self, query=None):
        return FakeCursor([doc for doc in self.docs if self._matches(doc, query or {})])

    def find_one(self, query=None):
        matches = self.find(query or {})
        return matches[0] if matches else None

    def count_documents(self, query):
        return len(self.find(query))

    def update_one(self, query, update):
        doc = self.find_one(query)
        if not doc:
            return
        for key, value in update.get("$set", {}).items():
            doc[key] = value

    def insert_one(self, doc):
        doc["_id"] = doc.get("_id") or ObjectId()
        self.docs.append(doc)
        return type("InsertResult", (), {"inserted_id": doc["_id"]})()

    def _matches(self, doc, query):
        for key, expected in query.items():
            value = doc.get(key)
            if isinstance(expected, dict):
                if "$gte" in expected and not (value >= expected["$gte"]):
                    return False
                if "$lte" in expected and not (value <= expected["$lte"]):
                    return False
                if "$lt" in expected and not (value < expected["$lt"]):
                    return False
            elif value != expected:
                return False
        return True


class FakeDB(dict):
    def __getitem__(self, name):
        if name not in self:
            self[name] = FakeCollection()
        return dict.__getitem__(self, name)


def test_normalize_storage_tier_and_quality():
    assert normalize_storage_tier("S3 Standard") == "hot"
    assert normalize_storage_tier("STANDARD_IA") == "warm"
    assert normalize_storage_tier("GLACIER") == "cold"
    assert classify_feedback_score(0.95) == OutcomeQuality.GOOD
    assert classify_feedback_score(0.65) == OutcomeQuality.ACCEPTABLE
    assert classify_feedback_score(0.25) == OutcomeQuality.BAD


def test_evaluate_storage_feedback_and_training_readiness():
    now = datetime.utcnow()
    prediction_id = ObjectId()
    db = FakeDB(
        {
            "ml_predictions": FakeCollection(
                [
                    {
                        "_id": prediction_id,
                        "username": "tanjiro",
                        "filename": "archive.zip",
                        "final_tier": "cold",
                        "evaluation_status": "pending",
                        "created_at": now - timedelta(days=8),
                        "feedback_score": None,
                    }
                ]
            ),
            "files": FakeCollection(
                [
                    {
                        "_id": ObjectId(),
                        "owner_username": "tanjiro",
                        "filename": "archive.zip",
                        "storage_class": "GLACIER",
                        "access_frequency_score": 0,
                    }
                ]
            ),
            "ml_workload_descriptions": FakeCollection([]),
            "ml_retraining_runs": FakeCollection([]),
        }
    )

    summary = evaluate_feedback(db, now=now)
    prediction = db["ml_predictions"].find_one({"_id": prediction_id})
    readiness = calculate_retraining_readiness(db, minimum_samples=1)

    assert summary["evaluated_predictions"] == 1
    assert prediction["evaluation_status"] == "evaluated"
    assert prediction["outcome_quality"] == "good"
    assert prediction["feedback_score"] >= 0.8
    assert readiness["ready_for_retraining"] is True
    assert readiness["storage_samples"] == 1


def test_young_predictions_remain_pending_and_old_predictions_skip():
    now = datetime.utcnow()
    young_id = ObjectId()
    old_id = ObjectId()
    db = FakeDB(
        {
            "ml_predictions": FakeCollection(
                [
                    {
                        "_id": young_id,
                        "username": "tanjiro",
                        "filename": "new.zip",
                        "final_tier": "cold",
                        "evaluation_status": "pending",
                        "created_at": now - timedelta(days=2),
                    },
                    {
                        "_id": old_id,
                        "username": "tanjiro",
                        "filename": "old.zip",
                        "final_tier": "cold",
                        "evaluation_status": "pending",
                        "created_at": now - timedelta(days=45),
                    },
                ]
            ),
            "files": FakeCollection([]),
            "ml_workload_descriptions": FakeCollection([]),
        }
    )

    summary = evaluate_feedback(db, now=now)
    young = db["ml_predictions"].find_one({"_id": young_id})
    old = db["ml_predictions"].find_one({"_id": old_id})

    assert summary["evaluated_predictions"] == 0
    assert young["evaluation_status"] == "pending"
    assert old["evaluation_status"] == "skipped"
    assert old["evaluation_details"]["reason"] == "evaluation_window_expired"
