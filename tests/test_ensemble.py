"""
Unit tests for ensemble methods and aggregation algorithms.
Verifies weighted soft voting, weight normalization, and probability alignment.
"""
import pytest
import numpy as np
import joblib
from src.config.settings import ARTIFACTS_DIR
from src.models.ensemble import weighted_soft_voting_aggregation


class TestEnsemble:
    def test_weighted_soft_voting_aggregation_math(self):
        # 3 models, 2 samples, 2 classes
        p1 = np.array([[0.8, 0.2], [0.1, 0.9]])
        p2 = np.array([[0.6, 0.4], [0.3, 0.7]])
        p3 = np.array([[0.9, 0.1], [0.2, 0.8]])

        weights = [2.0, 1.0, 1.0]  # Sum = 4.0 -> norm weights: 0.5, 0.25, 0.25
        aggregated = weighted_soft_voting_aggregation([p1, p2, p3], weights)

        # Expected sample 0 class 0: 0.8*0.5 + 0.6*0.25 + 0.9*0.25 = 0.4 + 0.15 + 0.225 = 0.775
        assert np.isclose(aggregated[0, 0], 0.775)
        # Expected sample 0 class 1: 0.2*0.5 + 0.4*0.25 + 0.1*0.25 = 0.1 + 0.1 + 0.025 = 0.225
        assert np.isclose(aggregated[0, 1], 0.225)
        # Probabilities sum to 1.0
        assert np.allclose(aggregated.sum(axis=1), np.array([1.0, 1.0]))

    def test_ensemble_voting_artifact_is_callable(self):
        voting_path = ARTIFACTS_DIR / "models" / "ensemble_voting.joblib"
        assert voting_path.exists()
        voting_model = joblib.load(voting_path)
        assert hasattr(voting_model, "predict_proba")
        assert hasattr(voting_model, "predict")

    def test_ensemble_stacking_artifact_is_callable(self):
        stacking_path = ARTIFACTS_DIR / "models" / "ensemble_stacking.joblib"
        assert stacking_path.exists()
        stacking_model = joblib.load(stacking_path)
        assert hasattr(stacking_model, "predict_proba")
        assert hasattr(stacking_model, "predict")
