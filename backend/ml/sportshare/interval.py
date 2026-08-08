"""
SportShare prediction intervals based on model residual distribution.

Uses q_0.90 of absolute residuals from calibration/validation samples.
Replaces the old heuristic confidence-interval implementation.
"""

import numpy as np


def build_prediction_interval(
    prediction: float,
    residual_q90: float,
) -> tuple[float, float]:
    """
    Build prediction interval: [prediction - q90, prediction + q90], clipped to [0, 1].

    Args:
        prediction: point estimate (model_share)
        residual_q90: 90th percentile of absolute residuals from calibration

    Returns:
        (lower_bound, upper_bound) both in [0, 1]
    """
    lower = max(0.0, prediction - residual_q90)
    upper = min(1.0, prediction + residual_q90)
    return (round(lower, 4), round(upper, 4))


def compute_calibration_interval(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    q: float = 0.90,
) -> float:
    """
    Compute calibration q_90 from validation residuals.

    This is the authoritative interval width parameter.
    Must be computed from real data, never hardcoded.

    Args:
        y_true: ground truth values
        y_pred: model predictions
        q: quantile (default 0.90)

    Returns:
        q-th quantile of absolute residuals
    """
    residuals = np.abs(y_true - y_pred)
    return float(np.quantile(residuals, q))
