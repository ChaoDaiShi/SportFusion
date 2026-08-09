"""
SportShare model evaluation — 5×5 repeated CV, metrics, and reporting.

Reports: MAE, RMSE, R², Spearman rank correlation.
All metrics computed from y_true vs y_pred, never hardcoded.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import make_scorer
from sklearn.model_selection import RepeatedKFold, cross_validate

from ml.sportshare.model import create_model


def _spearman_score(y_true, y_pred):
    """Spearman rank correlation for make_scorer."""
    from scipy.stats import spearmanr
    corr, _ = spearmanr(y_true, y_pred)
    return corr


@dataclass
class EvaluationResult:
    """Cross-validation evaluation results."""

    mae: float = 0.0
    rmse: float = 0.0
    r2: float = 0.0
    spearman: float = 0.0
    mae_std: float = 0.0
    rmse_std: float = 0.0
    r2_std: float = 0.0
    spearman_std: float = 0.0
    n_splits: int = 5
    n_repeats: int = 5
    n_samples: int = 0
    n_features: int = 0
    random_state: int = 42
    metadata: dict[str, Any] = field(default_factory=dict)


def evaluate_cv(
    X: np.ndarray,
    y: np.ndarray,
    n_splits: int = 5,
    n_repeats: int = 5,
    random_state: int = 42,
) -> EvaluationResult:
    """
    Run 5×5 repeated k-fold cross-validation.

    Returns EvaluationResult with MAE, RMSE, R², Spearman.
    """
    model = create_model(random_state=random_state)
    cv = RepeatedKFold(n_splits=n_splits, n_repeats=n_repeats, random_state=random_state)

    scoring = {
        "mae": "neg_mean_absolute_error",
        "rmse": "neg_root_mean_squared_error",
        "r2": "r2",
        "spearman": make_scorer(_spearman_score),
    }

    scores = cross_validate(model, X, y, cv=cv, scoring=scoring, n_jobs=-1)

    result = EvaluationResult(
        mae=round(float(-scores["test_mae"].mean()), 4),
        rmse=round(float(-scores["test_rmse"].mean()), 4),
        r2=round(float(scores["test_r2"].mean()), 4),
        spearman=round(float(scores["test_spearman"].mean()), 4),
        mae_std=round(float(scores["test_mae"].std()), 4),
        rmse_std=round(float(scores["test_rmse"].std()), 4),
        r2_std=round(float(scores["test_r2"].std()), 4),
        spearman_std=round(float(scores["test_spearman"].std()), 4),
        n_splits=n_splits,
        n_repeats=n_repeats,
        n_samples=len(y),
        n_features=X.shape[1],
        random_state=random_state,
    )
    return result


def compute_residual_quantile(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    q: float = 0.90,
) -> float:
    """Compute the q-th quantile of absolute residuals for prediction intervals."""
    residuals = np.abs(y_true - y_pred)
    return float(np.quantile(residuals, q))


def save_evaluation(result: EvaluationResult, path: str | Path) -> None:
    """Save evaluation result as JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "mae": result.mae,
        "rmse": result.rmse,
        "r2": result.r2,
        "spearman": result.spearman,
        "mae_std": result.mae_std,
        "rmse_std": result.rmse_std,
        "r2_std": result.r2_std,
        "spearman_std": result.spearman_std,
        "n_splits": result.n_splits,
        "n_repeats": result.n_repeats,
        "n_samples": result.n_samples,
        "n_features": result.n_features,
        "random_state": result.random_state,
        "metadata": result.metadata,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
