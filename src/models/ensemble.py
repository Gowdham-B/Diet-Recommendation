"""
Ensemble learning module supporting Soft Voting and Stacking strategies.
"""
from typing import List, Dict, Any
import numpy as np


def weighted_soft_voting_aggregation(model_predictions: List[np.ndarray], weights: List[float]) -> np.ndarray:
    """
    Computes normalized weighted average of predicted class probabilities across base models.
    """
    normalized_weights = np.array(weights) / sum(weights)
    weighted_probs = np.zeros_like(model_predictions[0])

    for pred, w in zip(model_predictions, normalized_weights):
        weighted_probs += pred * w

    return weighted_probs
