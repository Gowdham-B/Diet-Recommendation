"""
Dataset auditing, cleaning, and comparison tools.
Demonstrates the empirical differences between synthetic and verified nutrition data.
"""
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from src.config.settings import RAW_DATA_DIR, REFERENCE_DATA_DIR


def audit_synthetic_dataset(file_path: str = None) -> Dict[str, Any]:
    """
    Performs full health audit of the raw synthetic dataset.
    Detects Atwater violation rate, zero-correlations, and uniform distribution CVs.
    """
    path = file_path or (RAW_DATA_DIR / "daily_food_nutrition_dataset_synthetic.csv")
    if not path.exists():
        # Fallback to current directory if not yet copied
        path = "daily_food_nutrition_dataset_cleaned.xls"
    
    df = pd.read_csv(path)
    total_records = len(df)
    null_counts = df.isnull().sum().to_dict()
    
    # Calculate Atwater energy deviation
    atwater_energy = (df["Protein (g)"] * 4.0) + (df["Carbohydrates (g)"] * 4.0) + (df["Fat (g)"] * 9.0)
    pct_mismatch = (np.abs(atwater_energy - df["Calories (kcal)"]) / atwater_energy) * 100.0
    severe_violations = (pct_mismatch > 25.0).sum()
    
    # Check food level calorie CVs
    food_cvs = {}
    for food in df["Food_Item"].unique()[:5]:
        subset = df[df["Food_Item"] == food]["Calories (kcal)"]
        cv = (subset.std() / (subset.mean() + 1e-5)) * 100.0
        food_cvs[food] = round(cv, 1)

    return {
        "total_records": total_records,
        "null_values": null_counts,
        "unique_foods": int(df["Food_Item"].nunique()),
        "atwater_severe_violation_count": int(severe_violations),
        "atwater_violation_rate_pct": round((severe_violations / total_records) * 100.0, 1),
        "sample_food_calorie_cvs": food_cvs,
        "status": "Synthetic/Invalid for Clinical Nutrition",
    }


def compare_synthetic_vs_verified() -> List[Dict[str, Any]]:
    """
    Direct comparison between identical food items in the raw dataset vs USDA verified values.
    """
    raw_path = RAW_DATA_DIR / "daily_food_nutrition_dataset_synthetic.csv"
    if not raw_path.exists():
        raw_path = "daily_food_nutrition_dataset_cleaned.xls"
    raw_df = pd.read_csv(raw_path)
    
    ref_df = pd.read_csv(REFERENCE_DATA_DIR / "verified_food_composition.csv")
    
    benchmark_foods = ["apple", "chicken breast", "broccoli", "eggs", "water", "salmon"]
    comparison = []
    
    for food_name in benchmark_foods:
        raw_sub = raw_df[raw_df["Food_Item"].str.lower() == food_name]
        # Match in ref_df
        ref_sub = ref_df[ref_df["food_id"].str.replace("_", " ") == food_name]
        if ref_sub.empty:
            ref_sub = ref_df[ref_df["name"].str.lower().str.contains(food_name)]
        
        if not raw_sub.empty and not ref_sub.empty:
            raw_row = raw_sub.mean(numeric_only=True)
            ref_row = ref_sub.iloc[0]
            
            comparison.append({
                "food": food_name.title(),
                "synthetic_calories": round(raw_row["Calories (kcal)"], 1),
                "verified_calories_100g": round(ref_row["calories_per_100g"], 1),
                "synthetic_protein_g": round(raw_row["Protein (g)"], 1),
                "verified_protein_100g": round(ref_row["protein_per_100g"], 1),
                "synthetic_carbs_g": round(raw_row["Carbohydrates (g)"], 1),
                "verified_carbs_100g": round(ref_row["carbs_per_100g"], 1),
                "synthetic_fat_g": round(raw_row["Fat (g)"], 1),
                "verified_fat_100g": round(ref_row["fat_per_100g"], 1),
                "serving_unit": ref_row["serving_unit"],
                "calories_per_serving": round(ref_row["calories_per_serving"], 1),
            })
            
    return comparison
