"""
Database initialization and seeding script.
Creates all tables and seeds the USDA-verified food composition dataset.
"""
from pathlib import Path
import pandas as pd
from src.config.settings import REFERENCE_DATA_DIR
from src.database.connection import init_db, get_db_context
from src.database.models import Food, User
import hashlib
import os


def hash_password(password: str) -> str:
    """Secure PBKDF2-HMAC-SHA256 password hashing with unique salt."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"{salt.hex()}:{key.hex()}"


def seed_database():
    """Initializes schema and populates verified foods."""
    print("Initializing database schema...")
    init_db()

    csv_path = REFERENCE_DATA_DIR / "verified_food_composition.csv"
    if not csv_path.exists():
        from src.data.build_reference_data import build_and_validate_reference_dataset
        build_and_validate_reference_dataset()

    df = pd.read_csv(csv_path)

    with get_db_context() as session:
        # Check existing foods
        existing_count = session.query(Food).count()
        if existing_count == 0:
            print(f"Seeding {len(df)} USDA-verified foods into database...")
            for _, row in df.iterrows():
                food = Food(
                    food_id=str(row["food_id"]),
                    name=str(row["name"]),
                    category=str(row["category"]),
                    serving_size_g=float(row["serving_size_g"]),
                    serving_unit=str(row["serving_unit"]),
                    calories_per_100g=float(row.get("calories_per_100g", 0.0)),
                    protein_per_100g=float(row.get("protein_per_100g", 0.0)),
                    carbs_per_100g=float(row.get("carbs_per_100g", 0.0)),
                    fat_per_100g=float(row.get("fat_per_100g", 0.0)),
                    fiber_per_100g=float(row.get("fiber_per_100g", 0.0)),
                    sodium_mg_per_100g=float(row.get("sodium_mg_per_100g", 0.0)),
                    calories_per_serving=float(row["calories_per_serving"]),
                    protein_per_serving=float(row["protein_per_serving"]),
                    carbs_per_serving=float(row["carbs_per_serving"]),
                    fat_per_serving=float(row["fat_per_serving"]),
                    fiber_per_serving=float(row.get("fiber_per_serving", 0.0)),
                    sugars_per_serving=float(row.get("sugars_per_serving", 0.0)),
                    sodium_mg_per_serving=float(row.get("sodium_mg_per_serving", 0.0)),
                    cholesterol_mg_per_serving=float(row.get("cholesterol_mg_per_serving", 0.0)),
                    allergens=str(row.get("allergens", "")),
                    is_vegan=bool(row.get("is_vegan", False)),
                    is_vegetarian=bool(row.get("is_vegetarian", False)),
                    is_pescatarian=bool(row.get("is_pescatarian", False)),
                    is_gluten_free=bool(row.get("is_gluten_free", True)),
                    is_dairy_free=bool(row.get("is_dairy_free", True)),
                    is_keto_friendly=bool(row.get("is_keto_friendly", False)),
                    suitable_meals=str(row.get("suitable_meals", "lunch,dinner")),
                    estimated_cost_usd=float(row.get("estimated_cost_usd", 1.0)),
                    data_source=str(row.get("data_source", "USDA FoodData Central")),
                    data_quality_status=str(row.get("data_quality_status", "Verified")),
                )
                session.add(food)
            print("Food database successfully seeded.")
        else:
            print(f"Database already contains {existing_count} foods.")

        # Seed local demo user if not present
        demo_user = session.query(User).filter(User.username == "demo_user").first()
        if not demo_user:
            demo_user = User(
                username="demo_user",
                email="demo@nutriplan.ai",
                password_hash=hash_password("password123"),
                auth_provider="local",
            )
            session.add(demo_user)
            print("Seeded demo user: username='demo_user', password='password123'")

    print("Database initialization complete.")


if __name__ == "__main__":
    seed_database()
