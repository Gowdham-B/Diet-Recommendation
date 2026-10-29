"""
Food Repository module for querying, filtering, and retrieving validated food items.
"""
from pathlib import Path
from typing import List, Optional, Dict, Any
import pandas as pd
from src.config.settings import REFERENCE_DATA_DIR


class FoodRepository:
    """In-memory repository for fast querying of verified nutritional food records."""

    def __init__(self, csv_path: Optional[Path] = None):
        self.csv_path = csv_path or (REFERENCE_DATA_DIR / "verified_food_composition.csv")
        self._df: pd.DataFrame = pd.DataFrame()
        self.load()

    def load(self) -> None:
        """Loads and formats the food dataset."""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Verified food database not found at {self.csv_path}")
        
        df = pd.read_csv(self.csv_path)
        # Parse boolean columns
        bool_cols = ["is_vegan", "is_vegetarian", "is_pescatarian", "is_gluten_free", "is_dairy_free", "is_keto_friendly"]
        for col in bool_cols:
            if col in df.columns:
                df[col] = df[col].astype(bool)
        
        # Parse allergen lists
        df["allergens_list"] = df["allergens"].apply(
            lambda x: [] if pd.isna(x) or str(x).strip().lower() in ["none", ""] else [item.strip() for item in str(x).split(",")]
        )
        
        # Parse suitable meals list
        df["suitable_meals_list"] = df["suitable_meals"].apply(
            lambda x: [m.strip().lower() for m in str(x).split(",")] if pd.notna(x) else ["lunch", "dinner"]
        )

        self._df = df

    @property
    def dataframe(self) -> pd.DataFrame:
        """Access underlying DataFrame."""
        return self._df.copy()

    def get_all(self) -> List[Dict[str, Any]]:
        """Returns all food records as dictionaries."""
        return self._df.to_dict(orient="records")

    get_all_foods = get_all

    def get_by_id(self, food_id: str) -> Optional[Dict[str, Any]]:
        """Finds food record by unique ID."""
        matches = self._df[self._df["food_id"] == food_id]
        if matches.empty:
            return None
        return matches.iloc[0].to_dict()

    def search_by_name(self, query: str) -> List[Dict[str, Any]]:
        """Case-insensitive search by food name."""
        if not query:
            return self.get_all()
        q = query.strip().lower()
        matches = self._df[self._df["name"].str.lower().str.contains(q)]
        return matches.to_dict(orient="records")

    def filter_foods(
        self,
        category: Optional[str] = None,
        meal_slot: Optional[str] = None,
        dietary_pattern: Optional[str] = None,
        exclude_allergens: Optional[List[str]] = None,
        exclude_food_ids: Optional[List[str]] = None,
        max_calories_per_serving: Optional[float] = None,
        min_protein_per_serving: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Comprehensive multi-criteria filter.
        Ensures strict exclusion of allergens and dietary violations.
        """
        df = self._df.copy()

        # Category filter
        if category and category != "All":
            df = df[df["category"].str.lower() == category.lower()]

        # Meal slot filter (breakfast, lunch, dinner, snack)
        if meal_slot:
            slot = meal_slot.strip().lower()
            df = df[df["suitable_meals_list"].apply(lambda meals: slot in meals)]

        # Dietary lifestyle pattern filter
        if dietary_pattern:
            pat = dietary_pattern.lower()
            if "vegan" in pat:
                df = df[df["is_vegan"] == True]
            elif "vegetarian" in pat:
                df = df[df["is_vegetarian"] == True]
            elif "pescatarian" in pat:
                df = df[df["is_pescatarian"] == True]
            elif "keto" in pat or "low-carb" in pat:
                df = df[df["is_keto_friendly"] == True]
            elif "gluten-free" in pat:
                df = df[df["is_gluten_free"] == True]
            elif "dairy-free" in pat:
                df = df[df["is_dairy_free"] == True]

        # Strict Allergen Exclusion
        if exclude_allergens:
            allergens_to_avoid = {a.strip().lower() for a in exclude_allergens if a.strip()}
            if allergens_to_avoid:
                def is_safe(food_allergens: List[str]) -> bool:
                    food_set = {fa.lower() for fa in food_allergens}
                    # If intersection is non-empty, food is unsafe
                    return len(allergens_to_avoid.intersection(food_set)) == 0
                
                df = df[df["allergens_list"].apply(is_safe)]

        # Explicit Food Dislikes Exclusion
        if exclude_food_ids:
            dislikes = {f.strip().lower() for f in exclude_food_ids}
            df = df[~df["food_id"].str.lower().isin(dislikes)]

        # Nutritional criteria
        if max_calories_per_serving is not None:
            df = df[df["calories_per_serving"] <= max_calories_per_serving]
        if min_protein_per_serving is not None:
            df = df[df["protein_per_serving"] >= min_protein_per_serving]

        return df.to_dict(orient="records")

    def get_categories(self) -> List[str]:
        """Returns sorted list of distinct categories."""
        return sorted(self._df["category"].dropna().unique().tolist())
