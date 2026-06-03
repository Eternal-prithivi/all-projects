"""Unit tests for closed-loop workflow orchestrator and federated statistics."""

from app.ml.federated_aggregate import latest_federated_round, run_federated_statistics_round
from app.ml.workflow_orchestrator import run_storage_closed_loop_workflow


def test_closed_loop_workflow_has_five_steps(test_database):
    result = run_storage_closed_loop_workflow(
        db=test_database,
        username="workflow_user",
        filename="archive_logs.tar.gz",
        file_size_mb=120.0,
        user_priority="cost",
        user_intent="archival",
    )
    assert result["workflow"] == "storage_closed_loop_v1"
    assert result["closed_loop"] is True
    assert len(result["steps"]) == 5
    step_names = [s["name"] for s in result["steps"]]
    assert step_names[0] == "task_arrival_preprocessing"
    assert step_names[-1] == "model_learning_update"
    assert "determined_tier" in result["recommendation"]


def test_closed_loop_workflow_without_db():
    result = run_storage_closed_loop_workflow(
        db=None,
        username="anon",
        filename="doc.pdf",
        file_size_mb=1.0,
        user_priority="balanced",
        user_intent="frequent",
    )
    assert len(result["steps"]) == 5
    step3 = result["steps"][2]["outputs"]
    assert step3.get("rl_policy", {}).get("applied") is False


def test_federated_statistics_round_aggregates_buckets(test_database):
    test_database["ml_predictions"].insert_many(
        [
            {
                "evaluation_status": "evaluated",
                "feedback_score": 0.8,
                "final_tier": "cold",
                "input_features": {
                    "priority_cost": 1.0,
                    "intent_archival": 1.0,
                    "file_size_mb": 200.0,
                },
            },
            {
                "evaluation_status": "evaluated",
                "feedback_score": 0.6,
                "final_tier": "cold",
                "input_features": {
                    "priority_cost": 1.0,
                    "intent_archival": 1.0,
                    "file_size_mb": 150.0,
                },
            },
        ]
    )
    summary = run_federated_statistics_round(test_database, limit=100)
    assert summary["method"] == "federated_statistics_v1"
    assert summary["participant_samples"] >= 2
    latest = latest_federated_round(test_database)
    assert latest["available"] is True
