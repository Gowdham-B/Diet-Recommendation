"""
SQLAlchemy database models for NutriPlan AI.
Normalized schema supporting multi-user persistence, meal logs, plans, and feedback.
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.orm import relationship
from src.database.connection import Base


def utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    auth_provider = Column(String(50), default="local", nullable=False)
    provider_sub = Column(String(120), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    preferences = relationship("DietaryPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    meal_plans = relationship("MealPlan", back_populates="user", cascade="all, delete-orphan")
    meal_logs = relationship("MealLog", back_populates="user", cascade="all, delete-orphan")
    progress_records = relationship("ProgressRecord", back_populates="user", cascade="all, delete-orphan")
    feedbacks = relationship("RecommendationFeedback", back_populates="user", cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    age = Column(Integer, nullable=False)
    gender = Column(String(20), nullable=False)
    height_cm = Column(Float, nullable=False)
    weight_kg = Column(Float, nullable=False)
    activity_level = Column(String(100), nullable=False)
    goal = Column(String(100), nullable=False)
    target_calorie_override = Column(Float, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="profile")


class DietaryPreference(Base):
    __tablename__ = "dietary_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    dietary_pattern = Column(String(100), default="Omnivore (No restrictions)", nullable=False)
    allergens = Column(Text, default="", nullable=False)  # Comma-separated or JSON list
    excluded_foods = Column(Text, default="", nullable=False)
    preferred_foods = Column(Text, default="", nullable=False)
    meals_per_day = Column(Integer, default=4, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="preferences")


class Food(Base):
    __tablename__ = "foods"

    id = Column(Integer, primary_key=True, autoincrement=True)
    food_id = Column(String(80), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    serving_size_g = Column(Float, nullable=False)
    serving_unit = Column(String(80), nullable=False)

    calories_per_100g = Column(Float, default=0.0, nullable=False)
    protein_per_100g = Column(Float, default=0.0, nullable=False)
    carbs_per_100g = Column(Float, default=0.0, nullable=False)
    fat_per_100g = Column(Float, default=0.0, nullable=False)
    fiber_per_100g = Column(Float, default=0.0, nullable=False)
    sodium_mg_per_100g = Column(Float, default=0.0, nullable=False)

    calories_per_serving = Column(Float, nullable=False)
    protein_per_serving = Column(Float, nullable=False)
    carbs_per_serving = Column(Float, nullable=False)
    fat_per_serving = Column(Float, nullable=False)
    fiber_per_serving = Column(Float, default=0.0, nullable=False)
    sugars_per_serving = Column(Float, default=0.0, nullable=False)
    sodium_mg_per_serving = Column(Float, default=0.0, nullable=False)
    cholesterol_mg_per_serving = Column(Float, default=0.0, nullable=False)

    allergens = Column(String(200), default="", nullable=False)
    is_vegan = Column(Boolean, default=False, nullable=False)
    is_vegetarian = Column(Boolean, default=False, nullable=False)
    is_pescatarian = Column(Boolean, default=False, nullable=False)
    is_gluten_free = Column(Boolean, default=True, nullable=False)
    is_dairy_free = Column(Boolean, default=True, nullable=False)
    is_keto_friendly = Column(Boolean, default=False, nullable=False)

    suitable_meals = Column(String(100), default="lunch,dinner", nullable=False)
    estimated_cost_usd = Column(Float, default=1.0, nullable=False)
    data_source = Column(String(100), default="USDA FoodData Central", nullable=False)
    data_quality_status = Column(String(50), default="Verified", nullable=False)


class MealPlan(Base):
    __tablename__ = "meal_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_name = Column(String(120), default="Personalized Daily Plan", nullable=False)
    target_calories = Column(Float, nullable=False)
    target_protein_g = Column(Float, nullable=False)
    target_carbs_g = Column(Float, nullable=False)
    target_fat_g = Column(Float, nullable=False)
    total_calories = Column(Float, nullable=False)
    total_protein_g = Column(Float, nullable=False)
    total_carbs_g = Column(Float, nullable=False)
    total_fat_g = Column(Float, nullable=False)
    model_version = Column(String(80), default="Ensemble v1.0", nullable=False)
    ensemble_config = Column(String(120), default="Soft Voting (RF + HistGB + MLP + KNN)", nullable=False)
    status = Column(String(50), default="active", nullable=False)  # active, historical
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    user = relationship("User", back_populates="meal_plans")
    items = relationship("MealPlanItem", back_populates="meal_plan", cascade="all, delete-orphan")


class MealPlanItem(Base):
    __tablename__ = "meal_plan_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meal_plan_id = Column(Integer, ForeignKey("meal_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    food_id = Column(String(80), nullable=False)
    food_name = Column(String(120), nullable=False)
    meal_slot = Column(String(30), nullable=False)  # breakfast, lunch, dinner, snack
    servings = Column(Float, default=1.0, nullable=False)
    total_weight_g = Column(Float, default=100.0, nullable=False)
    serving_unit = Column(String(80), default="1 serving", nullable=False)
    calories = Column(Float, nullable=False)
    protein_g = Column(Float, nullable=False)
    carbs_g = Column(Float, nullable=False)
    fat_g = Column(Float, nullable=False)
    fiber_g = Column(Float, default=0.0, nullable=False)
    sodium_mg = Column(Float, default=0.0, nullable=False)
    estimated_cost_usd = Column(Float, default=0.0, nullable=False)
    predicted_suitability_score = Column(Float, default=0.0, nullable=False)
    rank = Column(Integer, default=1, nullable=False)
    rationale = Column(Text, default="", nullable=False)

    meal_plan = relationship("MealPlan", back_populates="items")


class MealLog(Base):
    __tablename__ = "meal_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    food_id = Column(String(80), nullable=True)
    food_name = Column(String(120), nullable=False)
    meal_slot = Column(String(30), nullable=False)
    servings = Column(Float, default=1.0, nullable=False)
    calories = Column(Float, nullable=False)
    protein_g = Column(Float, nullable=False)
    carbs_g = Column(Float, nullable=False)
    fat_g = Column(Float, nullable=False)
    logged_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    user = relationship("User", back_populates="meal_logs")


class ProgressRecord(Base):
    __tablename__ = "progress_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(DateTime, default=utc_now, nullable=False, index=True)
    weight_kg = Column(Float, nullable=False)
    notes = Column(Text, default="", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    user = relationship("User", back_populates="progress_records")


class RecommendationFeedback(Base):
    __tablename__ = "recommendation_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    food_id = Column(String(80), nullable=False, index=True)
    food_name = Column(String(120), nullable=False)
    recommendation_id = Column(Integer, nullable=True)
    feedback_type = Column(String(30), nullable=False)  # liked, disliked, selected, skipped, substituted
    comment = Column(Text, default="", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    user = relationship("User", back_populates="feedbacks")
