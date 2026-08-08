"""
SportShare RandomForest model — training, persistence, and inference.

NOT called per HTTP request. Model is trained once, serialized, and loaded for inference.
"""

import json
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestRegressor

from ml.sportshare.features import FEATURE_NAMES


@dataclass
class SportShareModelArtifact:
    """Serializable model artifact with full provenance."""

    model: Any  # RandomForestRegressor
    feature_names: list[str] = field(default_factory=lambda: list(FEATURE_NAMES))
    random_state: int = 42
    n_estimators: int = 100
    max_depth: int | None = None
    min_samples_leaf: int = 5
    model_version: str = "SPORTSHARE-RF-2026-08"
    training_dataset_version: str = ""
    feature_schema_version: str = "SPORTSHARE-FEATURES-2026-08"
    training_samples: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


def create_model(random_state: int = 42) -> RandomForestRegressor:
    """Create a fresh RandomForestRegressor with fixed random_state."""
    return RandomForestRegressor(
        n_estimators=100,
        max_depth=None,
        min_samples_leaf=5,
        random_state=random_state,
        n_jobs=-1,
    )


def train_model(
    X: np.ndarray,
    y: np.ndarray,
    random_state: int = 42,
) -> RandomForestRegressor:
    """Train a RandomForestRegressor on (X, y)."""
    model = create_model(random_state=random_state)
    model.fit(X, y)
    return model


def save_artifact(artifact: SportShareModelArtifact, directory: str | Path) -> str:
    """Save model artifact to disk. Returns the artifact path."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    # Save model
    model_path = directory / "model.joblib"
    with open(model_path, "wb") as f:
        pickle.dump(artifact.model, f)

    # Save metadata (without model object)
    meta = {
        "feature_names": artifact.feature_names,
        "random_state": artifact.random_state,
        "n_estimators": artifact.n_estimators,
        "max_depth": artifact.max_depth,
        "min_samples_leaf": artifact.min_samples_leaf,
        "model_version": artifact.model_version,
        "training_dataset_version": artifact.training_dataset_version,
        "feature_schema_version": artifact.feature_schema_version,
        "training_samples": artifact.training_samples,
        "metadata": artifact.metadata,
    }
    meta_path = directory / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    return str(directory)


def load_artifact(directory: str | Path) -> SportShareModelArtifact:
    """Load model artifact from disk."""
    directory = Path(directory)
    model_path = directory / "model.joblib"
    meta_path = directory / "metadata.json"

    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")
    if not meta_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {meta_path}")

    with open(model_path, "rb") as f:
        model = pickle.load(f)

    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    return SportShareModelArtifact(
        model=model,
        feature_names=meta.get("feature_names", FEATURE_NAMES),
        random_state=meta.get("random_state", 42),
        n_estimators=meta.get("n_estimators", 100),
        max_depth=meta.get("max_depth"),
        min_samples_leaf=meta.get("min_samples_leaf", 5),
        model_version=meta.get("model_version", ""),
        training_dataset_version=meta.get("training_dataset_version", ""),
        feature_schema_version=meta.get("feature_schema_version", ""),
        training_samples=meta.get("training_samples", 0),
        metadata=meta.get("metadata", {}),
    )


def predict(
    artifact: SportShareModelArtifact,
    X: np.ndarray,
) -> np.ndarray:
    """Run inference using a loaded model artifact. Returns float array [0,1]."""
    raw = artifact.model.predict(X)
    return np.clip(raw, 0.0, 1.0)


def predict_single(
    artifact: SportShareModelArtifact,
    features: list[float],
) -> float:
    """Predict SportShare for a single feature vector."""
    X = np.array([features])
    return float(predict(artifact, X)[0])
