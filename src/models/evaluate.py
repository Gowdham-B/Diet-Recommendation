"""
Model evaluation artifact loader and visualization helpers for Model Insights page.
"""
import json
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
from src.config.settings import ARTIFACTS_DIR

METRICS_DIR = ARTIFACTS_DIR / "metrics"


def load_model_comparison_metrics() -> pd.DataFrame:
    """Loads comparative performance metrics across all models and ensembles."""
    metrics_file = METRICS_DIR / "model_comparison.json"
    if not metrics_file.exists():
        from src.models.train import train_and_evaluate_all_models
        train_and_evaluate_all_models()

    with open(metrics_file, "r") as f:
        data = json.load(f)

    df = pd.DataFrame(data).T
    df.index.name = "Model"
    return df


def load_confusion_matrices() -> Dict[str, List[List[int]]]:
    """Loads confusion matrices for all evaluated models."""
    cm_file = METRICS_DIR / "confusion_matrices.json"
    if not cm_file.exists():
        from src.models.train import train_and_evaluate_all_models
        train_and_evaluate_all_models()

    with open(cm_file, "r") as f:
        return json.load(f)


def load_feature_importances() -> pd.DataFrame:
    """Loads top feature importances from trained tree ensemble."""
    fi_file = METRICS_DIR / "feature_importances.json"
    if not fi_file.exists():
        from src.models.train import train_and_evaluate_all_models
        train_and_evaluate_all_models()

    with open(fi_file, "r") as f:
        data = json.load(f)

    df = pd.DataFrame(list(data.items()), columns=["Feature", "Importance"])
    return df.sort_values(by="Importance", ascending=False)
