"""
Body Mass Index (BMI) calculations, WHO classifications, and healthy weight ranges.
"""
from typing import Dict, Any, Tuple


def compute_bmi(weight_kg: float, height_cm: float) -> float:
    """
    Computes BMI using the standard formula: weight (kg) / (height (m))^2.
    """
    if height_cm <= 0:
        raise ValueError("Height must be greater than zero.")
    if weight_kg <= 0:
        raise ValueError("Weight must be greater than zero.")
    
    height_m = height_cm / 100.0
    bmi = weight_kg / (height_m ** 2)
    return round(bmi, 2)


def get_healthy_weight_range(height_cm: float) -> Tuple[float, float]:
    """
    Returns the healthy weight range (kg) corresponding to BMI 18.5 - 24.9.
    """
    height_m = height_cm / 100.0
    min_weight = 18.5 * (height_m ** 2)
    max_weight = 24.9 * (height_m ** 2)
    return round(min_weight, 1), round(max_weight, 1)


def classify_bmi(bmi: float, height_cm: float) -> Dict[str, Any]:
    """
    Returns WHO category, health risk status, and healthy target weight range.
    """
    min_w, max_w = get_healthy_weight_range(height_cm)
    
    if bmi < 18.5:
        category = "Underweight"
        risk = "Risk of nutritional deficiency and osteoporosis"
        badge_color = "#3b82f6"  # Blue
    elif 18.5 <= bmi < 25.0:
        category = "Normal Weight"
        risk = "Low risk (optimal range)"
        badge_color = "#10b981"  # Emerald Green
    elif 25.0 <= bmi < 30.0:
        category = "Overweight"
        risk = "Increased risk of cardiovascular issues"
        badge_color = "#f59e0b"  # Amber
    elif 30.0 <= bmi < 35.0:
        category = "Obesity Class I"
        risk = "High risk of lifestyle diseases"
        badge_color = "#ef4444"  # Red
    elif 35.0 <= bmi < 40.0:
        category = "Obesity Class II"
        risk = "Very high clinical risk"
        badge_color = "#dc2626"
    else:
        category = "Obesity Class III"
        risk = "Extremely high clinical risk"
        badge_color = "#991b1b"

    return {
        "bmi": bmi,
        "category": category,
        "risk_assessment": risk,
        "healthy_weight_min_kg": min_w,
        "healthy_weight_max_kg": max_w,
        "healthy_weight_range_kg": (min_w, max_w),
        "badge_color": badge_color,
    }

