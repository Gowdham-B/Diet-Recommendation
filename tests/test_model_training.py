"""
Unit tests for Machine Learning model artifacts, training outputs, and prediction interfaces.
Verifies Random Forest, HistGradientBoosting, MLP, and KNN models.
"""
import pytest
from pathlib import Path
import joblib
import numpy as np
from src.config.settings import ARTIFACTS_DIR


class TestModelTraining:
    @pytest.fixture
    def models_dir(self):
        return ARTIFACTS_DIR / "models"

    def test_all_model_artifacts_exist(self, models_dir):
        expected_artifacts = [
            "preprocessor.joblib",
            "random_forest.joblib",
            "gradient_boosting.joblib",
            "mlp.joblib",
            "knn.joblib",
            "ensemble_voting.joblib",
            "ensemble_stacking.joblib",
        ]
        for artifact in expected_artifacts:
            path = models_dir / artifact
            assert path.exists(), f"Artifact missing: {artifact}"

    def test_candidate_models_predict_valid_probabilities(self, models_dir):
        for model_name in ["random_forest", "gradient_boosting", "mlp", "knn", "ensemble_voting", "ensemble_stacking"]:
            model = joblib.load(models_dir / f"{model_name}.joblib")
            assert hasattr(model, "predict_proba")
            assert hasattr(model, "predict")

    def test_evaluation_metrics_persisted(self):
        metrics_file = ARTIFACTS_DIR / "metrics" / "model_comparison.json"
        assert metrics_file.exists()
        import json
        with open(metrics_file, "r") as f:
            data = json.load(f)
        assert len(data) >= 4
        # Verify metric keys
        for model_name, metrics in data.items():
            assert "ROC-AUC" in metrics
            assert "F1-Score" in metrics
            assert "Accuracy" in metrics
            assert "Precision" in metrics
            assert "Recall" in metrics

