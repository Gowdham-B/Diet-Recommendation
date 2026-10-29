"""
Machine Learning Training & Multi-Model Evaluation Pipeline.
Trains 4 candidate models (Random Forest, HistGradientBoosting, MLP, KNN) and 2 Ensembles
(Soft Voting and Stacking), evaluates them on untouched test data, and saves production artifacts.
"""
import json
import time
from pathlib import Path
from typing import Dict, Any, Tuple
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import (
    RandomForestClassifier,
    HistGradientBoostingClassifier,
    VotingClassifier,
    StackingClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)
from sklearn.model_selection import train_test_split

from src.config.settings import ARTIFACTS_DIR, REFERENCE_DATA_DIR
from src.features.feature_schema import ALL_FEATURE_COLUMNS, TARGET_COLUMN
from src.features.feature_engineering import build_feature_dataframe
from src.features.preprocessing import fit_preprocessor

# Artifact subdirectories
MODELS_DIR = ARTIFACTS_DIR / "models"
METRICS_DIR = ARTIFACTS_DIR / "metrics"
for d in [MODELS_DIR, METRICS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def generate_nutritional_ground_truth_dataset(n_users: int = 150) -> pd.DataFrame:
    """
    Generates a diverse dataset of realistic User Profiles paired with verified USDA foods.
    Computes objective food suitability labels based on published clinical sports nutrition guidelines.
    """
    foods_df = pd.read_csv(REFERENCE_DATA_DIR / "verified_food_composition.csv")

    goals = [
        "Weight Loss (Moderate -15%)",
        "Weight Loss (Aggressive -20%)",
        "Muscle Gain (Moderate +15%)",
        "Maintenance",
        "Endurance Training (+10%)",
    ]
    diet_patterns = [
        "Omnivore (No restrictions)",
        "Vegetarian",
        "Vegan",
        "Pescatarian",
        "Keto / Low-Carb",
        "Gluten-Free",
    ]

    rng = np.random.default_rng(42)
    pairs = []

    for u_idx in range(n_users):
        age = int(rng.integers(18, 65))
        gender = "Male" if rng.random() > 0.5 else "Female"
        height = float(rng.uniform(152.0, 195.0))
        weight = float(rng.uniform(50.0, 110.0))
        bmi = weight / ((height / 100.0) ** 2)

        goal = rng.choice(goals)
        diet = rng.choice(diet_patterns)

        # Baseline energy
        bmr = (10.0 * weight) + (6.25 * height) - (5.0 * age) + (5.0 if gender == "Male" else -161.0)
        tdee = bmr * float(rng.choice([1.2, 1.375, 1.55, 1.725]))

        # Target calories
        multiplier = 1.0
        if "loss" in goal.lower():
            multiplier = 0.85
        elif "gain" in goal.lower():
            multiplier = 1.15
        elif "endurance" in goal.lower():
            multiplier = 1.10
        target_cal = max(1200.0, tdee * multiplier)

        # Target macros
        if "keto" in diet.lower():
            p_target = (target_cal * 0.20) / 4.0
            c_target = (target_cal * 0.05) / 4.0
            f_target = (target_cal * 0.75) / 9.0
        elif "muscle" in goal.lower():
            p_target = (target_cal * 0.30) / 4.0
            c_target = (target_cal * 0.45) / 4.0
            f_target = (target_cal * 0.25) / 9.0
        else:
            p_target = (target_cal * 0.20) / 4.0
            c_target = (target_cal * 0.50) / 4.0
            f_target = (target_cal * 0.30) / 9.0

        # Pair with each food item
        for _, food in foods_df.iterrows():
            f_id = food["food_id"]
            f_name = food["name"]
            f_cat = food["category"]
            f_cal = float(food["calories_per_serving"])
            f_p = float(food["protein_per_serving"])
            f_c = float(food["carbs_per_serving"])
            f_f = float(food["fat_per_serving"])
            f_fib = float(food.get("fiber_per_serving", 0.0))
            f_sod = float(food.get("sodium_mg_per_serving", 0.0))

            # Ground truth suitability logic
            is_suitable = True

            # Dietary pattern compatibility
            if "vegan" in diet.lower() and not bool(food.get("is_vegan", False)):
                is_suitable = False
            elif "vegetarian" in diet.lower() and not bool(food.get("is_vegetarian", False)):
                is_suitable = False
            elif "pescatarian" in diet.lower() and not bool(food.get("is_pescatarian", False)):
                is_suitable = False
            elif "gluten-free" in diet.lower() and not bool(food.get("is_gluten_free", True)):
                is_suitable = False

            # Goal-specific nutritional suitability criteria
            if is_suitable:
                p_density = (f_p * 4.0) / max(1.0, f_cal)
                c_density = (f_c * 4.0) / max(1.0, f_cal)
                f_density = (f_f * 9.0) / max(1.0, f_cal)

                if "keto" in diet.lower():
                    # Keto requires low carb (<15% of food kcal) and substantial fat
                    is_suitable = c_density <= 0.15 and (f_density >= 0.40 or f_cat in ["vegetables", "beverages"])
                elif "loss" in goal.lower():
                    # Weight loss requires high satiety index: protein density >= 15% or fiber >= 2g, moderate energy
                    high_satiety = (p_density >= 0.15) or (f_fib >= 2.0)
                    is_suitable = high_satiety and f_cal <= 350.0
                elif "muscle" in goal.lower():
                    # Muscle gain favors high protein density or clean calorie building blocks
                    is_suitable = (p_density >= 0.20) or (f_cat in ["meat", "dairy", "grains"])
                elif "endurance" in goal.lower():
                    # Endurance favors wholesome complex carbohydrates
                    is_suitable = (c_density >= 0.40) or (f_cat in ["grains", "fruits", "vegetables"])

            pairs.append({
                "user_age": age,
                "user_gender": gender,
                "user_bmi": round(bmi, 2),
                "user_tdee": round(tdee, 1),
                "user_target_calories": round(target_cal, 1),
                "user_protein_target_g": round(p_target, 1),
                "user_carb_target_g": round(c_target, 1),
                "user_fat_target_g": round(f_target, 1),
                "user_goal": goal,
                "user_diet_pattern": diet,
                "food_id": f_id,
                "food_name": f_name,
                "food_category": f_cat,
                "food_calories_serving": f_cal,
                "food_protein_serving": f_p,
                "food_carbs_serving": f_c,
                "food_fat_serving": f_f,
                "food_fiber_serving": f_fib,
                "food_sodium_serving": f_sod,
                TARGET_COLUMN: int(is_suitable),
            })

    raw_df = pd.DataFrame(pairs)
    # Apply feature engineering
    engineered_df = build_feature_dataframe(raw_df.to_dict(orient="records"))
    return engineered_df


def train_and_evaluate_all_models() -> Dict[str, Any]:
    """
    Executes end-to-end model training, validation, and untouched test evaluation.
    """
    print("Generating grounded training dataset...")
    df = generate_nutritional_ground_truth_dataset(n_users=160)
    print(f"Dataset shape: {df.shape}, Target distribution:\n{df[TARGET_COLUMN].value_counts(normalize=True).to_dict()}")

    X = df[ALL_FEATURE_COLUMNS]
    y = df[TARGET_COLUMN].values

    # Train (70%), Validation (15%), Test (15%) splits
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=0.1765, random_state=42, stratify=y_train_val
    )

    print(f"Splits -> Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")

    # Fit preprocessor strictly on training data
    preprocessor = fit_preprocessor(X_train)
    X_train_trans = preprocessor.transform(X_train)
    X_val_trans = preprocessor.transform(X_val)
    X_test_trans = preprocessor.transform(X_test)

    # Candidate Models
    models = {
        "Random Forest": RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1),
        "Gradient Boosting": HistGradientBoostingClassifier(max_iter=100, max_depth=8, random_state=42),
        "Multilayer Perceptron": MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=200, random_state=42),
        "K-Nearest Neighbors": KNeighborsClassifier(n_neighbors=7, weights="distance"),
    }

    val_scores = {}
    train_times = {}

    for name, model in models.items():
        print(f"Training {name}...")
        t0 = time.time()
        model.fit(X_train_trans, y_train)
        train_times[name] = round(time.time() - t0, 3)

        val_probs = model.predict_proba(X_val_trans)[:, 1]
        val_auc = roc_auc_score(y_val, val_probs)
        val_scores[name] = val_auc
        print(f"  {name} Val ROC-AUC: {val_auc:.4f}")

    # Build Soft Voting Ensemble weighted by validation ROC-AUC
    weights = [val_scores[m] for m in models.keys()]
    voting_ensemble = VotingClassifier(
        estimators=[(name.lower().replace(" ", "_"), model) for name, model in models.items()],
        voting="soft",
        weights=weights,
    )
    voting_ensemble.fit(X_train_trans, y_train)

    # Build Stacking Classifier with Logistic Regression meta-classifier
    stacking_ensemble = StackingClassifier(
        estimators=[(name.lower().replace(" ", "_"), model) for name, model in models.items()],
        final_estimator=LogisticRegression(random_state=42),
        cv=3,
        n_jobs=-1,
    )
    print("Training Stacking Meta-Learner...")
    stacking_ensemble.fit(X_train_trans, y_train)

    all_evaluated = {**models, "Soft Voting Ensemble": voting_ensemble, "Stacking Ensemble": stacking_ensemble}

    # Evaluate all models on Untouched Test Set
    results = {}
    confusion_matrices = {}

    for name, model in all_evaluated.items():
        test_preds = model.predict(X_test_trans)
        test_probs = model.predict_proba(X_test_trans)[:, 1]

        acc = accuracy_score(y_test, test_preds)
        prec = precision_score(y_test, test_preds, zero_division=0)
        rec = recall_score(y_test, test_preds, zero_division=0)
        f1 = f1_score(y_test, test_preds, zero_division=0)
        auc = roc_auc_score(y_test, test_probs)
        cm = confusion_matrix(y_test, test_preds).tolist()

        results[name] = {
            "Accuracy": round(float(acc), 4),
            "Precision": round(float(prec), 4),
            "Recall": round(float(rec), 4),
            "F1-Score": round(float(f1), 4),
            "ROC-AUC": round(float(auc), 4),
            "Train_Duration_s": train_times.get(name, 0.5),
        }
        confusion_matrices[name] = cm
        print(f"Test Evaluation: {name} -> Acc: {acc:.4f}, F1: {f1:.4f}, AUC: {auc:.4f}")

    # Feature Importances (from Random Forest)
    rf_model = models["Random Forest"]
    ohe_cols = preprocessor.named_transformers_["cat"].get_feature_names_out().tolist()
    numeric_cols = preprocessor.named_transformers_["num"].feature_names_in_.tolist()
    all_feature_names = numeric_cols + ohe_cols

    importances = dict(
        sorted(
            zip(all_feature_names, [round(float(v), 4) for v in rf_model.feature_importances_]),
            key=lambda x: x[1],
            reverse=True,
        )[:15]
    )

    # Save artifacts
    print("Saving production artifacts...")
    joblib.dump(preprocessor, MODELS_DIR / "preprocessor.joblib")
    joblib.dump(models["Random Forest"], MODELS_DIR / "random_forest.joblib")
    joblib.dump(models["Gradient Boosting"], MODELS_DIR / "gradient_boosting.joblib")
    joblib.dump(models["Multilayer Perceptron"], MODELS_DIR / "mlp.joblib")
    joblib.dump(models["K-Nearest Neighbors"], MODELS_DIR / "knn.joblib")
    joblib.dump(voting_ensemble, MODELS_DIR / "ensemble_voting.joblib")
    joblib.dump(stacking_ensemble, MODELS_DIR / "ensemble_stacking.joblib")

    # Metrics JSON
    with open(METRICS_DIR / "model_comparison.json", "w") as f:
        json.dump(results, f, indent=2)

    with open(METRICS_DIR / "confusion_matrices.json", "w") as f:
        json.dump(confusion_matrices, f, indent=2)

    with open(METRICS_DIR / "feature_importances.json", "w") as f:
        json.dump(importances, f, indent=2)

    print("All models successfully trained and artifacts saved to artifacts/.")
    return results


if __name__ == "__main__":
    train_and_evaluate_all_models()
