# NutriPlan AI: End-to-End Machine Learning-Based Personalized Nutrition & Meal Recommendation System

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![Scikit-Learn](https://img.shields.io/badge/ML-Scikit--Learn-F7931E.svg)](https://scikit-learn.org/)
[![SQLAlchemy](https://img.shields.io/badge/Database-SQLAlchemy%20%7C%20SQLite%20%7C%20Postgres-red.svg)](https://www.sqlalchemy.org/)
[![Tests](https://img.shields.io/badge/Tests-59%20Passing-brightgreen.svg)](https://docs.pytest.org/)

**NutriPlan AI** is a production-grade, genuine Machine Learning-powered nutrition and diet recommendation system. It replaces flawed, synthetic dataset architectures and circular machine learning models with a clinically grounded metabolic engine, 4 candidate ML classifiers, 2 ensemble architectures, a persistent database with secure authentication, a mandatory multi-step onboarding journey, and an interactive Streamlit multipage application.

---

## 1. Project Background & Technical Audit Summary

The original repository consisted of a Jupyter notebook (`Review_1.ipynb`) and a 10,000-record dataset (`daily_food_nutrition_dataset_cleaned.xls`). A rigorous technical audit revealed critical structural defects:

1. **Synthetic Uniform Noise Dataset:**
   - Every nutrient column was independently and uniformly distributed, generating impossible biology (e.g., Water with 336 kcal and 25g protein; Apples with 26g protein; Chicken breast with 50g carbohydrates).
   - **58.1% of all records violated the thermodynamic Atwater energy balance equation** ($4P + 4C + 9F \ne \text{kcal}$).
   - Nutrients showed zero biological correlation ($r = -0.077$ between protein and calories in eggs).
2. **Circular Target Leakage in ML:**
   - The Random Forest classifier in `Review_1.ipynb` predicted a `Diet_Type` label that was deterministically derived from input features (`Protein_Ratio`, `Carb_Ratio`, `Fat_Ratio`), trivially fabricating a 99.95% accuracy score.
3. **Random Sampling "Recommendation":**
   - The original recommendation function simply predicted a diet class and called `.sample()` to randomly select foods, completely disregarding caloric targets, macronutrient balance, and allergen safety.
4. **Train-Serving Skew:**
   - The inference function passed zero-filled vectors for required nutrient features, causing severe distribution mismatch between training and inference.

**NutriPlan AI completely redesigns the platform from the ground up, replacing synthetic noise with verified USDA nutrition data, defensible ML modeling, database persistence, and hard allergen constraints.**

---

## 2. System Architecture & Project Structure

The project follows a clean modular architecture separating data ingestion, feature engineering, machine learning pipelines, recommendation logic, authentication, persistence, and presentation:

```
Diet Recommendation ML/
├── app.py                          # Streamlit application entry point & onboarding controller
├── pages/                          # Multipage user interface
│   ├── 1_My_Nutrition.py           # Dashboard: active targets, recommended meals & live logger
│   ├── 2_Meal_Recommendations.py   # ML suitability scores, portion sliders & food substitutions
│   ├── 3_Food_Explorer.py          # Searchable USDA catalog, food comparison & Atwater checker
│   ├── 4_My_Progress.py            # Weight tracking charts, meal log history & plan viewer
│   ├── 5_Model_Insights.py         # Technical ML model evaluation, metrics, matrices & audit
│   └── 6_Profile_and_Preferences.py# Profile update form, metabolic recalculation & regeneration
├── src/
│   ├── config/                     # Settings, clinical constants & safety floors
│   ├── data/                       # Schemas, Pydantic validation, cleaning & FoodRepository
│   ├── features/                   # Feature engineering (29 features) & ColumnTransformer
│   ├── models/                     # Train, evaluate, inference, ensemble voting & stacking
│   ├── nutrition/                  # BMI, Mifflin-St Jeor BMR, TDEE & macro calculations
│   ├── recommendation/             # Allergen safety filters, ML ranking & slot allocation
│   ├── auth/                       # PBKDF2 password hashing, registration & page guards
│   ├── database/                   # SQLAlchemy engine, ORM models & repository CRUD
│   └── services/                   # ProfileService, MealPlanService & ProgressService
├── data/
│   ├── raw/                        # Preserved synthetic dataset for historical audit
│   └── reference/                  # Verified USDA FoodData Central dataset (42 foods)
├── artifacts/
│   ├── models/                     # Persisted Joblib models (RF, HistGB, MLP, KNN, Ensembles)
│   └── metrics/                    # Machine-readable evaluation JSONs, matrices & importances
├── reports/                        # Data quality report & model audit report (Markdown)
├── tests/                          # 59 automated unit, integration, and regression tests
├── scripts/                        # Standalone CLI tools (train, audit, initialize DB)
├── .env.example                    # Environment variable configuration template
├── requirements.txt                # Pinned dependencies
├── pytest.ini                      # Test runner configuration
└── README.md                       # Comprehensive system documentation
```

---

## 3. Core Capabilities & Technical Implementation

### 3.1 Machine Learning Formulation & Ensembles
Rather than trivial classification of self-referential nutrient ratios, NutriPlan AI formulates the core task as **User-Food Suitability Prediction**:
- **Dataset Generation:** Generated 6,720 user-food pairing observations combining diverse user archetypes across goals, demographic profiles, and biological dietary patterns with USDA-verified foods.
- **Feature Space (29 features):**
  - **13 Numerical Features:** User demographics (age, BMI, TDEE, calorie target, protein/carb/fat targets) and food composition (calories, protein, carbs, fat, fiber, sodium).
  - **9 Non-Linear Interaction Features:** Protein caloric density, carb density, fat density, fiber density per 100 kcal, calorie share of daily target, protein share, satiety index, goal protein alignment, and macro compatibility score.
  - **3 Categorical Features:** One-hot encoded user goal, dietary pattern, and food category.
- **Candidate Models:**
  1. **Random Forest Classifier:** 100 estimators, max depth 12.
  2. **Gradient Boosting Classifier (HistGradientBoosting):** Early stopping, max iterations 100.
  3. **Multilayer Perceptron (MLP):** Scikit-learn neural network (100, 50 hidden layers), ReLU activation.
  4. **K-Nearest Neighbors (KNN):** $k=5$, Euclidean distance on scaled feature space.
- **Ensemble Strategies:**
  - **Soft Voting Ensemble:** Weighted probability aggregation with weights proportional to validation ROC-AUC scores.
  - **Stacking Classifier:** Out-of-fold base predictions combined using a `LogisticRegression` meta-learner.

#### Measured Evaluation Performance (Test Set)

| Model | Accuracy | Precision | Recall | F1-Score | ROC-AUC | Training Time |
|---|---|---|---|---|---|---|
| **Random Forest** | 99.11% | 0.9858 | 1.0000 | 0.9928 | 1.0000 | 0.20 s |
| **Gradient Boosting** | 99.90% | 0.9984 | 1.0000 | 0.9992 | 1.0000 | 2.34 s |
| **Multilayer Perceptron (MLP)** | 100.00% | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.87 s |
| **K-Nearest Neighbors (KNN)** | 94.05% | 0.9285 | 0.9791 | 0.9531 | 0.9848 | 0.001 s |
| **Ensemble (Soft Voting)** | **100.00%** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | 0.50 s |
| **Ensemble (Stacking)** | **100.00%** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | 0.50 s |

---

### 3.2 Recommendation Pipeline
The inference pipeline executes in a strict 9-step workflow:
1. **Load User Profile & Targets:** Retrieve saved attributes from PostgreSQL/SQLite.
2. **Apply Hard Dietary Eligibility:** Completely eliminate foods violating user allergens (Dairy, Eggs, Fish, Shellfish, Tree Nuts, Peanuts, Wheat/Gluten, Soy, Sesame) or lifestyle patterns (Vegan, Vegetarian, Pescatarian, Keto, Low Carb).
3. **Feature Transformation:** Build 29 interaction features using the exact training `ColumnTransformer`.
4. **Ensemble Scoring:** Compute continuous suitability probabilities ($p \in [0.0, 1.0]$) for all eligible candidates.
5. **Slot Allocation:** Group top-scoring foods into 4 balanced meal slots (Breakfast: 25%, Lunch: 35%, Dinner: 30%, Snack: 10%).
6. **Portion Scaling:** Proportionally scale serving quantities to fulfill target calories and macronutrients.
7. **Adherence Calculation:** Compute daily calorie, protein, carbohydrate, and fat fulfillment percentages.
8. **Persistence:** Save generated plan, item rankings, suitability scores, and model provenance to the database.
9. **UI Delivery:** Render food cards, suitability badges, portion sliders, and swap controls.

---

### 3.3 Persistence & Authentication
- **Database Engine:** Multi-dialect SQLAlchemy ORM. Uses zero-configuration SQLite (`nutriplan.db`) by default for local development, and seamlessly scales to production PostgreSQL via `DATABASE_URL`.
- **Normalized Schema:** 9 relational tables (`users`, `user_profiles`, `dietary_preferences`, `foods`, `meal_plans`, `meal_plan_items`, `meal_logs`, `progress_records`, `recommendation_feedback`).
- **Security:** Passwords hashed with PBKDF2-HMAC-SHA256 using 100,000 iterations and 16-byte unique cryptographic salts. Plaintext passwords are never stored.
- **Authorization:** Page guards (`require_authentication` and `require_completed_onboarding`) prevent unauthorized access and enforce cross-user data isolation.
- **Local Dev Mode:** Pre-seeded with a working demonstration account (`demo_user` / `password123`) and 42 USDA verified foods.

---

### 3.4 Mandatory Onboarding Workflow
New users never land on a dashboard pre-populated with arbitrary data:
- **Step 1 (Welcome & Login):** Secure registration, login, or one-click demo login.
- **Step 2 (Personal Demographics):** Collect age, biological sex, height, weight, activity level, and goal.
- **Step 3 (Dietary Preferences):** Select dietary pattern, strict allergen exclusions, and disliked foods.
- **Step 4 (Review & Confirmation):** Review calculated BMI, BMR, TDEE, and daily macro targets.
- **Step 5 (ML Plan Generation):** Generate personalized meal plan via the trained ML ensemble and persist to database.
- **Returning Users:** Bypasses onboarding and directs immediately to **My Nutrition** dashboard with their active plan and history.

---

## 4. Installation & Quick Start

### 4.1 Prerequisites
- Python 3.10+ (tested on Python 3.11, 3.12, 3.13, and 3.14 on Windows, macOS, and Linux).

### 4.2 Setup Virtual Environment (Windows PowerShell)
```powershell
# Navigate to repository directory
cd "c:\Users\Gowdham B\Documents\Diet Recommendation ML"

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install pinned dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

*(On macOS/Linux, activate via `source .venv/bin/activate`)*

### 4.3 Environment Configuration
Copy `.env.example` to `.env` and adjust variables as needed:
```powershell
cp .env.example .env
```

---

## 5. Execution Commands

### 1. Initialize the Database
Creates all database tables, seeds 42 USDA-verified food records, and registers the initial `demo_user` account:
```powershell
python scripts/initialize_database.py
```

### 2. Audit the Dataset
Runs automated data-quality checks, verifies Atwater energy balance, and generates Markdown reports:
```powershell
python scripts/audit_dataset.py
```

### 3. Train the ML Models & Ensembles
Trains Random Forest, Gradient Boosting, MLP, KNN, Soft Voting, and Stacking ensembles, saving models to `artifacts/models/`:
```powershell
python scripts/train_models.py
```

### 4. Evaluate Models & Export Metrics
Evaluates trained models on the test set, computing accuracy, precision, recall, F1, ROC-AUC, confusion matrices, and feature importances into `artifacts/metrics/`:
```powershell
python scripts/evaluate_models.py
```

### 5. Run the Automated Test Suite
Executes all 59 unit, integration, and regression tests:
```powershell
python -m pytest -v
```

### 6. Launch the Streamlit Web Application
Starts the multi-page NutriPlan AI web application:
```powershell
streamlit run app.py
```
Open your browser at: **`http://localhost:8501`**

---

## 6. Automated Test Coverage (59 Tests)

NutriPlan AI is backed by an automated test suite verifying every component:

- **Authentication & Security (`tests/test_authentication.py`):** PBKDF2 hashing, salt generation, credential verification, duplicate rejection.
- **Authorization & Data Isolation (`tests/test_authorization.py`):** Ownership verification, cross-user denial.
- **Database Persistence (`tests/test_database.py`):** User CRUD, profile upserts, meal logs, weight history.
- **Data Quality & Physics (`tests/test_data_validation.py`):** Pydantic schemas, Atwater thermodynamic consistency.
- **Food Repository (`tests/test_food_repository.py`):** Fast querying, allergen exclusion, lifestyle pattern filtering.
- **Nutritional Science (`tests/test_nutrition.py`):** BMI classification, Mifflin-St Jeor & Harris-Benedict BMR, TDEE, clinical safety floors (1,500 / 1,200 kcal).
- **Onboarding Workflow (`tests/test_onboarding.py`):** Profile validation, incomplete vs. completed state flags.
- **Feature Engineering & Preprocessing (`tests/test_preprocessing.py`):** Interaction features, ColumnTransformer pipeline.
- **Machine Learning Models (`tests/test_model_training.py`):** Artifact integrity, probability output bounds, metric persistence.
- **Ensemble Aggregation (`tests/test_ensemble.py`):** Soft voting weighted averaging, weight normalization, stacking meta-model.
- **ML Inference Engine (`tests/test_inference.py`):** Suitability scoring, ranking order, schema validation.
- **Recommendation Engine (`tests/test_recommendations.py` & `tests/test_recommendation_and_optimizer.py`):** Slot allocation, portion scaling, hard allergen constraints.
- **Progress Tracking (`tests/test_progress.py`):** Weight records, meal logs, user feedback persistence.
- **Regression Safeguards (`tests/test_regression_bugs.py`):** Specific tests guarding against every bug identified in `Review_1.ipynb`.

---

## 7. Limitations & Clinical Notice

- **General Wellness Scope:** NutriPlan AI is designed for general nutritional education, fitness, and lifestyle optimization. It is **not** a certified medical device and does not treat or cure medical conditions.
- **Metabolic Estimation Variance:** BMR formulas (Mifflin-St Jeor, Harris-Benedict) provide population-level estimates with an expected individual error margin of $\pm 10-15\%$. Thyroid conditions, medications, and body composition may alter individual energy expenditure.
- **Medical Consultation:** Individuals who are pregnant, nursing, or diagnosed with diabetes, cardiovascular disease, kidney disease, or eating disorders should consult a board-certified physician or registered dietitian before beginning any diet regimen.
