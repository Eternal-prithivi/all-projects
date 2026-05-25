"""Phase 9 report-parity benchmark checks.

Runs local, zero-cloud-cost validation for the claims tracked in the major
project report: storage ensemble accuracy, five-cluster NLP routing, and
decay-weighted cost forecasting responsiveness.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from sklearn.linear_model import LinearRegression

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.cost.forecasting import forecast_costs
from app.ml.storage_ensemble import (
    LABEL_TO_TIER,
    TIER_TO_LABEL,
    _build_training_data,
    _load_expert_models,
)
from app.vm.workload_analyzer import WorkloadAnalyzer


def benchmark_storage_accuracy(sample_size: int = 500) -> Dict[str, Any]:
    x_data, y_data = _build_training_data()
    model_status = _load_expert_models()
    if not model_status["available"]:
        return {
            "status": "skipped",
            "reason": model_status["error"],
        }

    rng = random.Random(42)
    indexes = rng.sample(range(len(x_data)), min(sample_size, len(x_data)))
    x_sample = x_data[indexes]
    y_sample = y_data[indexes]

    rf_predictions = model_status["random_forest"].predict(x_sample)
    xgb_predictions = model_status["xgboost"].predict(x_sample)
    ensemble_predictions: List[int] = []

    for row, rf_label, xgb_label in zip(x_sample, rf_predictions, xgb_predictions):
        rule_label = int(row[-1])
        scores = {tier: 0.0 for tier in TIER_TO_LABEL}
        scores[LABEL_TO_TIER[rule_label]] += 0.30
        scores[LABEL_TO_TIER[int(rf_label)]] += 0.35
        scores[LABEL_TO_TIER[int(xgb_label)]] += 0.35
        ensemble_predictions.append(TIER_TO_LABEL[max(scores, key=scores.get)])

    accuracy = float(np.mean(np.array(ensemble_predictions) == y_sample))
    return {
        "status": "passed" if accuracy >= 0.893 else "needs_attention",
        "metric": "storage_ensemble_accuracy",
        "target": 0.893,
        "value": round(accuracy, 4),
        "sample_size": len(indexes),
        "xgboost_backend": model_status["xgboost_backend"],
    }


def benchmark_workload_taxonomy() -> Dict[str, Any]:
    examples = {
        "general": "Deploy a normal Node.js API with Docker containers and moderate traffic.",
        "storage": "Run PostgreSQL with object storage backups and large data warehouse exports.",
        "memory": "Run Redis and Memcached with 64GB RAM for in-memory session caching.",
        "performance": "High CPU parallel processing job with many cores for scientific simulation.",
        "ai_ml": "Training a PyTorch deep learning model with GPU CUDA acceleration.",
    }

    rows = []
    passed = 0
    for expected, description in examples.items():
        cluster, confidence, details = WorkloadAnalyzer.analyze(description)
        report_cluster = details.get("report_cluster") or cluster.value
        ok = cluster.value == expected and report_cluster == expected
        rows.append({
            "expected": expected,
            "actual_cluster": cluster.value,
            "report_cluster": report_cluster,
            "confidence": confidence,
            "passed": ok,
        })
        passed += int(ok)

    return {
        "status": "passed" if passed == len(examples) else "needs_attention",
        "metric": "five_cluster_nlp_taxonomy",
        "passed": passed,
        "total": len(examples),
        "cases": rows,
    }


def benchmark_decay_weighted_forecast() -> Dict[str, Any]:
    historical_costs = [
        10, 10.2, 10.1, 10.4, 10.3, 10.5, 10.6,
        11, 11.5, 12, 13, 15, 18, 22,
    ]
    weighted = forecast_costs(historical_costs, days_ahead=7)

    x_train = np.array(range(len(historical_costs))).reshape(-1, 1)
    y_train = np.array(historical_costs)
    baseline = LinearRegression().fit(x_train, y_train)
    future_x = np.array(range(len(historical_costs), len(historical_costs) + 7)).reshape(-1, 1)
    baseline_total = float(sum(max(0, p) for p in baseline.predict(future_x)))

    return {
        "status": "passed" if weighted["total_forecast"] > baseline_total else "needs_attention",
        "metric": "decay_weighted_forecast_responsiveness",
        "weighted_total_7d": round(weighted["total_forecast"], 2),
        "unweighted_total_7d": round(baseline_total, 2),
        "model_type": weighted["model_type"],
        "weighted_mape": round(weighted["weighted_mape"], 2),
    }


def run_benchmarks() -> Dict[str, Any]:
    results = {
        "storage": benchmark_storage_accuracy(),
        "workload": benchmark_workload_taxonomy(),
        "cost": benchmark_decay_weighted_forecast(),
    }
    results["overall_status"] = (
        "passed"
        if all(result.get("status") == "passed" for result in results.values())
        else "needs_attention"
    )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 9 report-parity benchmarks")
    parser.add_argument("--json", action="store_true", help="Print compact JSON only")
    args = parser.parse_args()

    results = run_benchmarks()
    if args.json:
        print(json.dumps(results, sort_keys=True))
    else:
        print(json.dumps(results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
