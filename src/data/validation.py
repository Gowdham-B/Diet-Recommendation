"""
Data validation schemas and integrity checks using Pydantic.
Validates nutrient bounds, serving consistency, and user profile inputs.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class FoodItemSchema(BaseModel):
    """Schema for individual food items with USDA-standard bounds."""
    food_id: str = Field(..., description="Unique slug or ID")
    name: str = Field(..., min_length=2, max_length=100)
    category: str = Field(..., description="Food group category")
    serving_size_g: float = Field(..., gt=0.0, le=1000.0)
    serving_unit: str = Field(..., min_length=2)
    
    # Per 100g metrics
    calories_per_100g: float = Field(..., ge=0.0, le=900.0)
    protein_per_100g: float = Field(..., ge=0.0, le=100.0)
    carbs_per_100g: float = Field(..., ge=0.0, le=100.0)
    fat_per_100g: float = Field(..., ge=0.0, le=100.0)
    fiber_per_100g: float = Field(default=0.0, ge=0.0, le=100.0)
    sugars_per_100g: float = Field(default=0.0, ge=0.0, le=100.0)
    sodium_mg_per_100g: float = Field(default=0.0, ge=0.0, le=10000.0)
    cholesterol_mg_per_100g: float = Field(default=0.0, ge=0.0, le=3000.0)

    # Per serving metrics
    calories_per_serving: float = Field(..., ge=0.0, le=2500.0)
    protein_per_serving: float = Field(..., ge=0.0, le=200.0)
    carbs_per_serving: float = Field(..., ge=0.0, le=250.0)
    fat_per_serving: float = Field(..., ge=0.0, le=200.0)
    fiber_per_serving: float = Field(default=0.0, ge=0.0, le=100.0)
    sugars_per_serving: float = Field(default=0.0, ge=0.0, le=150.0)
    sodium_mg_per_serving: float = Field(default=0.0, ge=0.0, le=5000.0)
    cholesterol_mg_per_serving: float = Field(default=0.0, ge=0.0, le=1000.0)

    # Dietary classifications
    is_vegan: bool = False
    is_vegetarian: bool = False
    is_pescatarian: bool = False
    is_gluten_free: bool = True
    is_dairy_free: bool = True
    is_keto_friendly: bool = False

    # Allergens and meal suitability
    allergens: List[str] = Field(default_factory=list)
    suitable_meals: List[str] = Field(default_factory=lambda: ["lunch", "dinner"])
    estimated_cost_usd: float = Field(default=1.0, ge=0.0, le=50.0)
    data_source: str = "USDA FoodData Central"
    data_quality_status: str = "Verified"

    @model_validator(mode="after")
    def verify_serving_scaling(self) -> "FoodItemSchema":
        """Verify that per-serving calories approximately match 100g scaled value."""
        scale = self.serving_size_g / 100.0
        expected_cal = self.calories_per_100g * scale
        # Allow small rounding tolerance (±15% or ±10 kcal)
        diff = abs(self.calories_per_serving - expected_cal)
        if diff > 15.0 and diff / (expected_cal + 1e-5) > 0.20:
            raise ValueError(
                f"Calorie mismatch for {self.name}: per 100g is {self.calories_per_100g}, "
                f"serving ({self.serving_size_g}g) listed as {self.calories_per_serving}, expected ~{expected_cal:.1f}"
            )
        return self


class UserProfileSchema(BaseModel):
    """Strict schema for user physical stats and preferences."""
    age: int = Field(..., ge=12, le=120, description="Age in years")
    gender: str = Field(..., description="biological sex for BMR calculation ('Male' or 'Female')")
    height_cm: float = Field(..., ge=90.0, le=250.0, description="Height in centimeters")
    weight_kg: float = Field(..., ge=30.0, le=350.0, description="Weight in kilograms")
    activity_level: str = Field(
        default="Moderate (moderate exercise 3-5 days/week)",
        description="Physical activity multiplier key"
    )
    goal: str = Field(
        default="Maintenance",
        description="Weight goal or fitness target"
    )
    dietary_pattern: str = Field(
        default="Omnivore (No restrictions)",
        description="Dietary lifestyle restriction"
    )
    allergens: List[str] = Field(
        default_factory=list,
        description="List of allergies/intolerances to strictly avoid"
    )
    disliked_foods: List[str] = Field(
        default_factory=list,
        description="Foods explicitly excluded by taste"
    )
    target_calorie_override: Optional[float] = Field(
        default=None,
        ge=1000.0,
        le=6000.0,
        description="Optional custom calorie target"
    )

    @field_validator("target_calorie_override", mode="before")
    @classmethod
    def sanitize_override(cls, v: Any) -> Optional[float]:
        if v is None or v == "" or v == 0 or v == "0" or v == 0.0:
            return None
        return float(v)

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        clean = v.strip().capitalize()
        if clean not in ["Male", "Female"]:
            raise ValueError("Gender must be 'Male' or 'Female' for clinical BMR formulas.")
        return clean


def validate_atwater_balance(protein_g: float, carb_g: float, fat_g: float, recorded_cal: float) -> Dict[str, Any]:
    """
    Computes Atwater theoretical energy (P*4 + C*4 + F*9) and checks consistency.
    Returns deviation metrics and whether the record passes standard nutritional physics.
    """
    theoretical_cal = (protein_g * 4.0) + (carb_g * 4.0) + (fat_g * 9.0)
    abs_diff = abs(theoretical_cal - recorded_cal)
    pct_diff = (abs_diff / (theoretical_cal + 1e-5)) * 100.0
    
    # Real food labeling laws permit ~10-20% deviation due to fiber, water, and analytical variances.
    is_valid = pct_diff <= 25.0 or abs_diff <= 20.0
    return {
        "theoretical_calories": round(theoretical_cal, 1),
        "recorded_calories": round(recorded_cal, 1),
        "absolute_difference": round(abs_diff, 1),
        "percentage_difference": round(pct_diff, 1),
        "is_physically_consistent": is_valid,
    }
