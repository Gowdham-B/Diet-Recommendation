"""
Unit tests for FoodRepository: querying, strict filtering, allergen exclusions, and dietary lifestyles.
"""
import pytest
from src.data.food_repository import FoodRepository


@pytest.fixture
def repo():
    return FoodRepository()


class TestFoodRepository:
    def test_repo_load_non_empty(self, repo):
        foods = repo.get_all()
        assert len(foods) >= 35

    def test_get_by_id(self, repo):
        apple = repo.get_by_id("apple")
        assert apple is not None
        assert "Apple" in apple["name"]

        unknown = repo.get_by_id("non_existent_food_xyz")
        assert unknown is None

    def test_search_by_name(self, repo):
        results = repo.search_by_name("chicken")
        assert len(results) >= 1
        assert any("chicken" in r["name"].lower() for r in results)

    def test_strict_allergen_exclusion(self, repo):
        # Exclude dairy
        non_dairy = repo.filter_foods(exclude_allergens=["Dairy"])
        for food in non_dairy:
            allergens = [a.lower() for a in food["allergens_list"]]
            assert "dairy" not in allergens

        # Exclude nuts
        nut_free = repo.filter_foods(exclude_allergens=["Nuts / Peanuts"])
        for food in nut_free:
            allergens = [a.lower() for a in food["allergens_list"]]
            assert "nuts / peanuts" not in allergens

    def test_strict_vegan_filtering(self, repo):
        vegans = repo.filter_foods(dietary_pattern="Vegan")
        assert len(vegans) > 0
        for food in vegans:
            assert food["is_vegan"] is True
            # No animal meats or dairy
            assert food["category"] not in ["meat"]

    def test_strict_vegetarian_filtering(self, repo):
        veggies = repo.filter_foods(dietary_pattern="Vegetarian")
        assert len(veggies) > 0
        for food in veggies:
            assert food["is_vegetarian"] is True
            assert food["category"] != "meat"

    def test_disliked_food_exclusion(self, repo):
        filtered = repo.filter_foods(exclude_food_ids=["apple", "banana"])
        fids = [f["food_id"] for f in filtered]
        assert "apple" not in fids
        assert "banana" not in fids
