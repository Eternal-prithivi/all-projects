"""Tests for guarded feedback-driven model retraining."""

from bson import ObjectId

from app.ml.retraining import _meets_deployment_guard, retrain_models_from_feedback


class FakeCursor(list):
    def sort(self, key, direction):
        return self

    def limit(self, count):
        return FakeCursor(self[:count])


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = docs or []

    def find(self, query=None):
        return FakeCursor([doc for doc in self.docs if self._matches(doc, query or {})])

    def count_documents(self, query):
        return len(self.find(query))

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
            elif value != expected:
                return False
        return True


class FakeDB(dict):
    def __getitem__(self, name):
        if name not in self:
            self[name] = FakeCollection()
        return dict.__getitem__(self, name)


def test_deployment_guard_accepts_absolute_or_relative_gain():
    assert _meets_deployment_guard(0.82, 0.80)["passed"] is True
    assert _meets_deployment_guard(0.806, 0.80)["passed"] is False


def test_retraining_skips_until_enough_feedback_exists():
    db = FakeDB(
        {
            "ml_predictions": FakeCollection([]),
            "ml_workload_descriptions": FakeCollection([]),
            "ml_retraining_runs": FakeCollection([]),
        }
    )

    result = retrain_models_from_feedback(db, minimum_samples=3, deploy=False)

    assert result["status"] == "skipped"
    assert result["deployed"] is False
    assert result["candidate"] is None
    assert len(db["ml_retraining_runs"].docs) == 1
