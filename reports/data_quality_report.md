
# Data Quality & Nutritional Integrity Report

## 1. Executive Summary

An audit of the initial dataset (`daily_food_nutrition_dataset_cleaned.xls`) revealed that it was synthetically generated using independent uniform distributions per column. As a result, the dataset violates fundamental biological and thermodynamic principles of nutrition and cannot be used for genuine dietary recommendations.

In response, we created a verified food composition database sourced from **USDA FoodData Central (SR Legacy and Foundation)** covering all 35 original foods plus essential meal staples (42 total items). Every record includes per-100g and per-serving measurements, verified portion weights, allergen tags, and dietary compatibility flags.

---

## 2. Empirical Findings: Synthetic Dataset Flaws

### 2.1 Uniform Distribution & Identical Food Profiles
In the synthetic dataset, all 35 foods share nearly identical statistical distributions regardless of food type:
- Mean Calories: ~320 kcal (all foods)
- Mean Protein: ~25 g (all foods)
- Mean Carbohydrates: ~52 g (all foods)
- Mean Fat: ~25 g (all foods)

In reality:
- An **Apple** has 0.3g protein per 100g (synthetic listed: 25.9g — **86x error**).
- **Broccoli** has 34 kcal per 100g (synthetic listed: 326 kcal — **9.6x error**).
- **Chicken Breast** has 0g carbohydrates (synthetic listed: 50.4g — **infinite ratio error**).
- **Drinking Water** has 0 kcal (synthetic listed: 336 kcal, 25g protein, 53g carbs, 24g fat).

### 2.2 Uncorrelated Nutrients
Within real biological foods, nutrients covary tightly. For instance, in eggs or chicken, protein and calories have a Pearson correlation $r > 0.90$. In the synthetic dataset:
- Eggs Calorie-Protein correlation: **$r = -0.077$** (uncorrelated random noise).
- Coefficient of variation (CV) is consistently **~50%** across every nutrient for every food, characteristic of uniform pseudo-random number generators ($U[a, b]$).

### 2.3 Atwater Energy Violation
According to the Atwater system, total metabolic energy is governed by:
$$\text{Theoretical Calories} = 4 \times \text{Protein (g)} + 4 \times \text{Carbohydrates (g)} + 9 \times \text{Fat (g)}$$

Across the 10,000 synthetic records:
- **5,814 records (58.1%)** deviate from the Atwater calculation by more than 25%.
- Average caloric discrepancy was **152%**.

---

## 3. Verified Food Composition Database (USDA FoodData Central)

To provide legitimate, clinically sound recommendations, we constructed `data/reference/verified_food_composition.csv`:

### 3.1 Dataset Metadata
- **Provenance:** USDA FoodData Central SR Legacy & Foundation Datasets
- **Record Count:** 42 verified whole foods
- **Validation Pipeline:** Pydantic `FoodItemSchema` verifying physical bounds, Atwater consistency, and serving scaling.
- **Portion Metadata:** Standard serving units with verified gram weights (e.g., 1 medium apple = 182g, 2 large eggs = 100g, 1 breast portion = 120g).

### 3.2 Categorical & Allergen Coverage
| Food Category | Item Count | Example Foods |
|---|---|---|
| Fruits | 6 | Apple, Banana, Grapes, Orange, Strawberries, Blueberries |
| Vegetables | 7 | Broccoli, Spinach, Carrots, Tomato, Potato, Sweet Potato, Bell Pepper |
| Protein (Meat/Seafood/Plant) | 7 | Chicken Breast, Beef Sirloin, Pork Chop, Salmon, Eggs, Tofu, Lentils |
| Dairy | 5 | Whole Milk, Greek Yogurt, Cheddar Cheese, Paneer, Salted Butter |
| Grains & Starches | 6 | Rolled Oats, Whole Wheat Bread, White Rice, Brown Rice, Pasta, Quinoa |
| Snacks & Healthy Fats | 6 | Mixed Nuts, Peanut Butter, Dark Chocolate, Popcorn, Chips, Cookies |
| Beverages | 5 | Water, Coffee, Green Tea, Orange Juice, Milkshake |

### 3.3 Strict Safety & Exclusion Annotations
- **Allergens Tracked:** Dairy, Eggs, Gluten, Nuts / Peanuts, Fish / Shellfish, Soy.
- **Dietary Classifications:** Vegan, Vegetarian, Pescatarian, Keto-Friendly, Gluten-Free, Dairy-Free.
- **Meal Slot Suitability:** Breakfast, Lunch, Dinner, Snack.

---

## 4. Quality Assurance Summary

| Check | Synthetic Raw Data | USDA-Verified Reference Data |
|---|---|---|
| Atwater Physical Balance | ❌ 58.1% violations | ✅ 100% compliant |
| Serving Size Defined | ❌ None | ✅ All foods have verified portion grams |
| Allergen Safety Flags | ❌ None | ✅ Explicitly labeled for 6 major allergen classes |
| Biological Realism | ❌ Unphysical (336 kcal water) | ✅ Lab-measured clinical reference |
| Status | **Preserved for Documentation** | **Active in Recommendation Engine** |
