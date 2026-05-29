"""Storage optimizer / ensemble smoke tests without MongoDB."""

from app.storage.optimizer import get_initial_placement_recommendation


def test_storage_placement_recommendation_shape():
    result = get_initial_placement_recommendation(
        user_priority="balanced",
        user_intent="active",
        filename="data.csv",
        file_size_mb=10.0,
    )
    assert "recommendation" in result or "determined_tier" in result
