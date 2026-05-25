"""Pydantic contracts for ML prediction logs and workload classifications."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class PredictionType(str, Enum):
    STORAGE_TIER = "storage_tier"
    WORKLOAD_CLUSTER = "workload_cluster"


class ExpertName(str, Enum):
    RULE = "rule"
    RANDOM_FOREST = "random_forest"
    XGBOOST = "xgboost"


class EvaluationStatus(str, Enum):
    PENDING = "pending"
    EVALUATED = "evaluated"
    SKIPPED = "skipped"


class OutcomeQuality(str, Enum):
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    BAD = "bad"


class ExpertVote(BaseModel):
    expert: ExpertName
    predicted_tier: Optional[str] = None
    predicted_cluster: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    weight: float = Field(..., ge=0.0, le=1.0)


class MLPredictionCreate(BaseModel):
    """Input for logging a storage-tier ensemble prediction (Phases 7–8)."""

    username: str
    prediction_type: Literal["storage_tier"] = "storage_tier"
    filename: Optional[str] = None
    file_size_mb: Optional[float] = None
    user_priority: str = "balanced"
    user_intent: str = "active"
    input_features: Dict[str, Any] = Field(default_factory=dict)
    expert_votes: List[ExpertVote]
    final_tier: str
    final_csp: Optional[str] = None
    final_service: Optional[str] = None
    ensemble_confidence: float = Field(..., ge=0.0, le=1.0)
    rule_score: Optional[int] = None


class MLPredictionRecord(MLPredictionCreate):
    """Document shape stored in MongoDB `ml_predictions`."""

    evaluation_status: EvaluationStatus = EvaluationStatus.PENDING
    outcome_quality: Optional[OutcomeQuality] = None
    feedback_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    evaluated_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WorkloadClassificationCreate(BaseModel):
    """Input for logging NLP/keyword workload classification (Phases 6–8)."""

    username: str
    workload_description: str
    recommended_cluster: str
    final_cluster: str
    confidence: int = Field(..., ge=0, le=100)
    classifier_version: str = "keyword_v1"
    nlp_features: Dict[str, Any] = Field(default_factory=dict)
    analysis_details: Dict[str, Any] = Field(default_factory=dict)
    user_overrode_recommendation: bool = False


class WorkloadClassificationRecord(WorkloadClassificationCreate):
    """Document shape stored in MongoDB `ml_workload_descriptions`."""

    feedback_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    outcome_quality: Optional[OutcomeQuality] = None
    evaluation_status: EvaluationStatus = EvaluationStatus.PENDING
    evaluated_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FeedbackOutcomeCreate(BaseModel):
    """Future Phase 8: link prediction IDs to observed user behavior."""

    source_collection: Literal["ml_predictions", "ml_workload_descriptions"]
    source_id: str
    feedback_score: float = Field(..., ge=0.0, le=1.0)
    outcome_quality: OutcomeQuality
    notes: Optional[str] = None


class FeedbackEvaluationSummary(BaseModel):
    """Phase 8 evaluation run summary."""

    evaluated_predictions: int = 0
    skipped_predictions: int = 0
    pending_predictions: int = 0
    evaluated_workloads: int = 0
    skipped_workloads: int = 0
    pending_workloads: int = 0
    training_eligible_samples: int = 0


class RetrainingReadiness(BaseModel):
    """Guarded retraining/deployment status from report §4.5."""

    ready_for_retraining: bool
    eligible_samples: int
    storage_samples: int
    workload_samples: int
    current_feedback_accuracy: float
    minimum_feedback_score: float
    deployment_guard: Dict[str, Any] = Field(default_factory=dict)
