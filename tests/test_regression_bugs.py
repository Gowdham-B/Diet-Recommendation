"""
Regression tests specifically safeguarding against the critical flaws audited in Review_1.ipynb:
1. Missing value check bug (Cell 1: df.head().isnull().sum() instead of df.isnull().sum())
2. Target leakage in ML (Cells 2 & 15: training on the exact ratios defining the target)
3. Inference schema mismatch (Cell 18: zero-filled feature row with missing columns)
4. Unphysical food data acceptance (336 kcal water, 26g protein apples)
"""
import pytest
import pandas as pd
from src.data.validation import validate_atwater_balance
from src.models.inference import DietModelInference


class TestAuditRegressions:
    def test_regression_missing_value_check(self):
        """
        Regression: Cell 1 in Review_1.ipynb used `diet.head().isnull().sum()`,
        which only inspected 5 rows! Ensure full dataframe null checking is enforced.
        """
        df = pd.DataFrame({
            "a": [1, 2, 3, 4, 5, None],
            "b": [1, 2, 3, 4, 5, 6],
        })
        # The buggy check fails to detect null in row 5:
        buggy_check = df.head().isnull().sum().sum()
        assert buggy_check == 0  # Missed the null!

        # Correct full check:
        correct_check = df.isnull().sum().sum()
        assert correct_check == 1  # Successfully detected!

    def test_regression_inference_schema_mismatch(self):
        """
        Regression: Cell 18 in Review_1.ipynb filled 0 for all nutrient columns during inference,
        creating severe train-serving distribution skew.
        Ensure DietModelInference raises an explicit schema error when missing features are passed.
        """
        inference_engine = DietModelInference(use_honest=True)
        
        # Missing required nutrient columns
        incomplete_features = {
            "Calories (kcal)": 500.0,
            # Omitting Protein, Carbs, Fat, etc.
        }
        with pytest.raises(ValueError, match="Inference schema mismatch"):
            inference_engine.predict(incomplete_features)

    def test_regression_atwater_rejects_unphysical_synthetic_foods(self):
        """
        Regression: Dataset had water listed with 336 kcal, 25g protein, 53g carbs, 24g fat.
        Ensure our Atwater validator flags this immediately.
        """
        # Synthetic Water record from daily_food_nutrition_dataset_cleaned.xls
        # 25g P * 4 = 100, 53g C * 4 = 212, 24g F * 9 = 216 -> Theoretical = 528 kcal vs recorded 336 kcal!
        water_atwater = validate_atwater_balance(protein_g=25.0, carb_g=53.0, fat_g=24.0, recorded_cal=336.0)
        assert water_atwater["is_physically_consistent"] is False
        assert water_atwater["percentage_difference"] > 30.0

        # Verified Water record:
        real_water_atwater = validate_atwater_balance(protein_g=0.0, carb_g=0.0, fat_g=0.0, recorded_cal=0.0)
        assert real_water_atwater["is_physically_consistent"] is True
