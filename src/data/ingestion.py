"""
Ingestion pipeline for importing, checking, and validating food nutrition data files.
"""
from pathlib import Path
from typing import Dict, Any, Tuple
import pandas as pd
from src.data.validation import FoodItemSchema


def ingest_food_records_from_csv(csv_path: Path) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Ingests and validates raw CSV records against the FoodItemSchema.
    Returns (valid_df, diagnostic_summary).
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"File not found: {csv_path}")

    df = pd.read_csv(csv_path)
    total_records = len(df)
    valid_records = []
    error_log = []

    for idx, row in df.iterrows():
        try:
            item_dict = row.to_dict()
            if isinstance(item_dict.get("allergens"), str):
                item_dict["allergens"] = [
                    a.strip() for a in item_dict["allergens"].split(",") if a.strip().lower() != "none"
                ]
            elif pd.isna(item_dict.get("allergens")):
                item_dict["allergens"] = []
                
            if isinstance(item_dict.get("suitable_meals"), str):
                item_dict["suitable_meals"] = [
                    m.strip() for m in item_dict["suitable_meals"].split(",")
                ]

            validated = FoodItemSchema(**item_dict)
            valid_records.append(validated.model_dump())
        except Exception as e:
            error_log.append({"row_index": idx, "food_name": row.get("name", "Unknown"), "error": str(e)})

    valid_df = pd.DataFrame(valid_records)
    summary = {
        "total_attempted": total_records,
        "successfully_validated": len(valid_records),
        "validation_errors_count": len(error_log),
        "errors": error_log[:10],
    }
    return valid_df, summary
