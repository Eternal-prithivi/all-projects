"""Cost forecasting helpers for report-aligned decay-weighted LR."""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
from sklearn.linear_model import LinearRegression


def extract_daily_costs(cost_data: dict) -> List[float]:
    """Extract daily cost values from AWS-style or wrapped API responses."""
    payload = cost_data.get("data", cost_data)
    results = payload.get("ResultsByTime", [])
    costs = []
    for item in results:
        amount = float(item.get("Total", {}).get("UnblendedCost", {}).get("Amount", 0))
        costs.append(amount)
    return costs


def decay_weights(sample_count: int, decay: float = 0.94) -> np.ndarray:
    """Newest samples receive the largest weight, matching the report's DWLR model."""
    weights = np.array([decay ** (sample_count - index - 1) for index in range(sample_count)])
    return weights / np.mean(weights)


def mean_absolute_percentage_error(actual: np.ndarray, predicted: np.ndarray) -> float:
    non_zero = actual != 0
    if not np.any(non_zero):
        return 0.0
    return float(np.mean(np.abs((actual[non_zero] - predicted[non_zero]) / actual[non_zero])) * 100)


def forecast_costs(historical_costs: List[float], days_ahead: int = 30, decay: float = 0.94) -> Dict[str, Any]:
    """Use decay-weighted linear regression to forecast future costs."""
    if len(historical_costs) < 7:
        raise ValueError("Need at least 7 days of historical data for forecasting")

    x_train = np.array(range(len(historical_costs))).reshape(-1, 1)
    y_train = np.array(historical_costs)
    sample_weights = decay_weights(len(historical_costs), decay=decay)

    model = LinearRegression()
    model.fit(x_train, y_train, sample_weight=sample_weights)

    future_x = np.array(range(len(historical_costs), len(historical_costs) + days_ahead)).reshape(-1, 1)
    predictions = model.predict(future_x)
    fitted = model.predict(x_train)

    residuals = y_train - fitted
    weighted_residual_std = np.sqrt(np.average(residuals ** 2, weights=sample_weights))
    recent_average = (
        np.average(y_train[-7:], weights=sample_weights[-7:])
        if len(historical_costs) >= 7
        else np.mean(y_train)
    )
    clamped_predictions = [max(0, float(prediction)) for prediction in predictions]

    return {
        "forecasted_costs": clamped_predictions,
        "average_daily_cost": float(recent_average),
        "total_forecast": float(sum(clamped_predictions)),
        "confidence_interval": {
            "lower": float(max(0, sum(clamped_predictions) - 1.96 * weighted_residual_std * np.sqrt(days_ahead))),
            "upper": float(sum(clamped_predictions) + 1.96 * weighted_residual_std * np.sqrt(days_ahead)),
        },
        "trend": "increasing" if model.coef_[0] > 0 else "decreasing",
        "daily_change_rate": float(model.coef_[0]),
        "model_type": "decay_weighted_linear_regression",
        "decay_factor": decay,
        "weighted_mape": mean_absolute_percentage_error(y_train, fitted),
    }
