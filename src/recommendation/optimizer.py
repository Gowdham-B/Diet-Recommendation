"""
Constraint-based meal plan optimizer using SciPy HiGHS Mixed-Integer Linear Programming (MILP)
and intelligent fallback heuristics.
Optimizes food selection and portion sizes to hit target calories and macros while strictly honoring constraints.
"""
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from src.nutrition.nutrient_calculator import calculate_food_nutrition, aggregate_meal_nutrition
from src.recommendation.eligibility import filter_eligible_foods
from src.recommendation.ranking import rank_foods_for_meal, get_balanced_meal_candidates


class MealPlanOptimizer:
    """
    Optimizes a 4-meal daily nutrition plan (breakfast, lunch, dinner, snack)
    to match target calories, protein, carbs, and fat within bounded servings.
    """

    def __init__(self, all_foods: List[Dict[str, Any]]):
        self.all_foods = all_foods

    def generate_plan(
        self,
        target_calories: float,
        target_macros: Dict[str, float],
        dietary_pattern: str = "Omnivore (No restrictions)",
        allergens: Optional[List[str]] = None,
        disliked_food_ids: Optional[List[str]] = None,
        meal_targets: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> Dict[str, Any]:
        """
        Generates daily meal plan satisfying nutritional targets and exclusions.
        """
        allergens = allergens or []
        disliked_food_ids = disliked_food_ids or []

        # 1. Filter eligible candidates
        eligible_pool = filter_eligible_foods(
            all_foods=self.all_foods,
            dietary_pattern=dietary_pattern,
            allergens=allergens,
            disliked_food_ids=disliked_food_ids,
        )

        if not eligible_pool:
            return {
                "success": False,
                "error": "No foods in database match your dietary restrictions and allergen exclusions.",
                "meals": {},
                "diagnostics": {"feasible": False, "eligible_count": 0},
            }

        # 2. Divide into meal candidate pools
        slots = ["breakfast", "lunch", "dinner", "snack"]
        slot_candidates = {}
        for slot in slots:
            candidates = [
                f for f in eligible_pool
                if slot in [m.lower() for m in f.get("suitable_meals_list", [])]
            ]
            if len(candidates) < 3:
                candidates = eligible_pool
            slot_candidates[slot] = candidates

        # 3. Solve via SciPy HiGHS MILP
        try:
            plan, diag = self._solve_scipy_milp(
                slot_candidates=slot_candidates,
                target_calories=target_calories,
                target_macros=target_macros,
            )
            if diag.get("feasible", False):
                return {
                    "success": True,
                    "method": "Mixed Integer Linear Programming (SciPy HiGHS MILP)",
                    "meals": plan,
                    "diagnostics": diag,
                }
        except Exception as e:
            pass

        # 4. Fallback to smart heuristic search if MILP is infeasible or too constrained
        plan, diag = self._solve_heuristic(
            slot_candidates=slot_candidates,
            target_calories=target_calories,
            target_macros=target_macros,
        )
        return {
            "success": True,
            "method": "Rule-Based Heuristic Matcher (Graceful Fallback)",
            "meals": plan,
            "diagnostics": diag,
        }

    def _solve_scipy_milp(
        self,
        slot_candidates: Dict[str, List[Dict[str, Any]]],
        target_calories: float,
        target_macros: Dict[str, float],
    ) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
        """
        Formulates and solves the meal planning MILP using scipy.optimize.milp (HiGHS).
        """
        slots = ["breakfast", "lunch", "dinner", "snack"]
        slot_bounds = {
            "breakfast": (2, 3),
            "lunch": (2, 4),
            "dinner": (2, 4),
            "snack": (1, 2),
        }

        # Build indexed candidate list
        candidate_items = []  # list of (slot, food_dict)
        for slot in slots:
            cands = slot_candidates.get(slot, self.all_foods)
            balanced = get_balanced_meal_candidates(cands, target_macros, max_items=10)
            for f in balanced:
                candidate_items.append((slot, f))

        N = len(candidate_items)
        if N == 0:
            return {}, {"feasible": False, "reason": "No candidate items"}

        # Variable structure:
        # 0 .. N-1: y_i (binary selection)
        # N .. 2N-1: s_i (continuous servings)
        # 2N: dev_cal_pos, 2N+1: dev_cal_neg
        # 2N+2: dev_prot_pos, 2N+3: dev_prot_neg
        num_vars = 2 * N + 4
        c = np.zeros(num_vars)
        # Objective weights
        c[2 * N] = 1.0       # dev_cal_pos
        c[2 * N + 1] = 1.0   # dev_cal_neg
        c[2 * N + 2] = 4.0   # dev_prot_pos
        c[2 * N + 3] = 4.0   # dev_prot_neg
        
        # Slight bonus for selecting high-ranked foods
        for i, (slot, f) in enumerate(candidate_items):
            c[i] = -0.05 * f.get("ranking_score", 1.0)

        integrality = np.zeros(num_vars)
        integrality[:N] = 1  # y_i are binary integers

        # Variable bounds
        lb = np.zeros(num_vars)
        ub = np.full(num_vars, np.inf)
        ub[:N] = 1.0       # y_i <= 1
        ub[N:2*N] = 2.5    # s_i <= 2.5 servings max

        bounds = Bounds(lb, ub)

        # Constraint rows
        row_list = []
        lhs_list = []
        rhs_list = []

        # 1. Linking constraints: 0.5 * y_i <= s_i <= 2.5 * y_i
        for i in range(N):
            # s_i - 0.5 * y_i >= 0
            row1 = np.zeros(num_vars)
            row1[i] = -0.5
            row1[N + i] = 1.0
            row_list.append(row1)
            lhs_list.append(0.0)
            rhs_list.append(np.inf)

            # s_i - 2.5 * y_i <= 0
            row2 = np.zeros(num_vars)
            row2[i] = -2.5
            row2[N + i] = 1.0
            row_list.append(row2)
            lhs_list.append(-np.inf)
            rhs_list.append(0.0)

        # 2. Slot count constraints
        for slot in slots:
            min_c, max_c = slot_bounds[slot]
            row = np.zeros(num_vars)
            for i, (s_name, _) in enumerate(candidate_items):
                if s_name == slot:
                    row[i] = 1.0
            row_list.append(row)
            lhs_list.append(min_c)
            rhs_list.append(max_c)

        # 3. Global Variety: each distinct food item used at most once across the whole day
        distinct_fids = set(f["food_id"] for _, f in candidate_items)
        for fid in distinct_fids:
            row = np.zeros(num_vars)
            for i, (_, f) in enumerate(candidate_items):
                if f["food_id"] == fid:
                    row[i] = 1.0
            row_list.append(row)
            lhs_list.append(0.0)
            rhs_list.append(1.0)

        # 4. Calorie target & deviation: sum(s_i * cal_i) - dev_cal_pos + dev_cal_neg = target_cal
        cal_row = np.zeros(num_vars)
        for i, (_, f) in enumerate(candidate_items):
            cal_row[N + i] = f.get("calories_per_serving", 0.0)
        cal_row[2 * N] = -1.0
        cal_row[2 * N + 1] = 1.0
        row_list.append(cal_row)
        lhs_list.append(target_calories)
        rhs_list.append(target_calories)

        # 5. Protein target & deviation: sum(s_i * prot_i) - dev_prot_pos + dev_prot_neg = target_prot
        t_prot = target_macros.get("protein_g", 100.0)
        prot_row = np.zeros(num_vars)
        for i, (_, f) in enumerate(candidate_items):
            prot_row[N + i] = f.get("protein_per_serving", 0.0)
        prot_row[2 * N + 2] = -1.0
        prot_row[2 * N + 3] = 1.0
        row_list.append(prot_row)
        lhs_list.append(t_prot)
        rhs_list.append(t_prot)

        # 6. Overall Calorie Range (within ±15% target)
        cal_range_row = np.zeros(num_vars)
        for i, (_, f) in enumerate(candidate_items):
            cal_range_row[N + i] = f.get("calories_per_serving", 0.0)
        row_list.append(cal_range_row)
        lhs_list.append(target_calories * 0.85)
        rhs_list.append(target_calories * 1.15)

        A = np.array(row_list)
        constraints = LinearConstraint(A, lhs_list, rhs_list)

        res = milp(c=c, constraints=constraints, integrality=integrality, bounds=bounds)

        if not res.success:
            return {}, {"feasible": False, "status": res.status, "message": res.message}

        # Parse solution into meals
        meals = {"breakfast": [], "lunch": [], "dinner": [], "snack": []}
        x_sol = res.x
        for i, (slot, f_data) in enumerate(candidate_items):
            y_val = x_sol[i]
            s_val = x_sol[N + i]
            if y_val > 0.5 and s_val >= 0.3:
                servings = round(float(s_val), 2)
                scaled = calculate_food_nutrition(f_data, servings=servings)
                meals[slot].append(scaled)

        return meals, {"feasible": True, "solver_status": "Optimal (HiGHS)"}

    def _solve_heuristic(
        self,
        slot_candidates: Dict[str, List[Dict[str, Any]]],
        target_calories: float,
        target_macros: Dict[str, float],
    ) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
        """
        Robust heuristic fallback: selects best ranked items per slot and balances portions.
        """
        meals = {"breakfast": [], "lunch": [], "dinner": [], "snack": []}
        used_fids = set()

        slot_shares = {
            "breakfast": (0.25, 2),
            "lunch": (0.35, 3),
            "dinner": (0.30, 3),
            "snack": (0.10, 1),
        }

        for slot, (share, target_count) in slot_shares.items():
            slot_cal_target = target_calories * share
            candidates = slot_candidates.get(slot, self.all_foods)
            balanced = get_balanced_meal_candidates(candidates, target_macros, max_items=12)

            chosen = []
            for f in balanced:
                fid = f["food_id"]
                if fid in used_fids:
                    continue
                chosen.append(f)
                used_fids.add(fid)
                if len(chosen) >= target_count:
                    break

            if not chosen:
                chosen = balanced[:target_count]

            # Adjust servings to match slot target calories
            current_slot_cal = sum(f.get("calories_per_serving", 100.0) for f in chosen)
            scaling_factor = slot_cal_target / (current_slot_cal + 1e-5)
            scaling_factor = max(0.6, min(2.2, scaling_factor))

            for f in chosen:
                scaled = calculate_food_nutrition(f, servings=round(scaling_factor, 2))
                meals[slot].append(scaled)

        return meals, {"feasible": True, "note": "Heuristic knapsack solver applied"}
