# ML Training and Datasets

Last updated: 2026-05-24

## Current Truth

Zenith did not originally include a real production dataset. The earlier storage ensemble was functioning, but its Random Forest and XGBoost-style experts were trained in memory from a synthetic grid inside `backend/app/ml/storage_ensemble.py`. The NLP workload classifier was also functioning, but it was not originally trained from a project dataset; it used TextBlob, spaCy, custom technology dictionaries, negation checks, and confidence scoring.

This has now been made explicit and repeatable.

## Generated Datasets

Run this from `backend/`:

```bash
.venv/bin/python scripts/train_sample_ml_models.py
```

It generates:

| File | Purpose | Rows |
|---|---:|---:|
| `app/ml/datasets/storage_tier_training.csv` | Storage tier training data for hot/warm/cold prediction | 13,824 |
| `app/ml/datasets/workload_classification_training.csv` | Workload text samples for general/storage/memory/performance/AI-ML routing | 600 |

The datasets are synthetic and report-aligned. They are useful for demos, repeatable validation, and local training. They are not a substitute for real production cloud telemetry.

## Trained Artifacts

The same script trains and writes:

| Artifact | Used by | Notes |
|---|---|---|
| `app/ml/artifacts/storage_ensemble.joblib` | `storage_ensemble.py` | Random Forest + XGBoost/fallback expert models |
| `app/ml/artifacts/workload_classifier.joblib` | `nlp_workload.py` | Heavier TF-IDF soft-voting ensemble: Logistic Regression + Naive Bayes + Random Forest |

If artifacts are missing, storage inference falls back to in-memory synthetic training, and workload NLP falls back to TextBlob/spaCy/dictionary scoring.

## Feedback-Driven Self-Retraining

The production feedback loop uses:

| Collection | Learns from | Target |
|---|---|---|
| `ml_predictions` | storage tier predictions evaluated against later file tier/access behavior | hot/warm/cold storage tier |
| `ml_workload_descriptions` | workload text, recommended cluster, final selected cluster, user override signal | general/storage/memory/performance/AI-ML cluster |

Automation:

| Path | Purpose |
|---|---|
| `app/ml/feedback.py` | evaluates feedback after the 7-30 day report window and filters samples with `feedback_score >= 0.5` |
| `app/ml/retraining.py` | trains candidate artifacts from eligible feedback plus synthetic seed data |
| `app/ml/tasks_feedback.py` | Celery tasks for daily feedback evaluation and weekly guarded retraining |
| `POST /api/ml/feedback/retrain` | manual guarded retraining trigger |

Deployment is conservative. Candidate artifacts are written under `app/ml/artifacts/candidates/` first. They replace active artifacts only if the candidate feedback accuracy beats the current feedback baseline by either:

- `+1%` absolute gain, or
- `+2%` relative gain.

If the guard fails, the candidate is kept for inspection but the active model is unchanged.

## Last Local Training Result

```text
storage_tier_training.csv: 13,824 rows
workload_classification_training.csv: 600 rows
storage random_forest test accuracy: 0.9996
storage xgboost/fallback test accuracy: 0.9993
workload classifier test accuracy: 1.0
workload classifier implementation: TF-IDF + soft-voting Logistic Regression/Naive Bayes/Random Forest
```

The high scores are expected because the sample datasets are synthetic and generated from report-aligned labeling rules. Real feedback from `ml_predictions` and `ml_workload_descriptions` should replace or augment this data when enough production samples exist.
