"""
Database repositories providing transactional CRUD operations with strict user scoping.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timezone
from sqlalchemy.orm import Session, joinedload
from src.database.models import (
    User,
    UserProfile,
    DietaryPreference,
    Food,
    MealPlan,
    MealPlanItem,
    MealLog,
    ProgressRecord,
    RecommendationFeedback,
)


class UserRepository:
    @staticmethod
    def create_user(session: Session, username: str, email: str, password_hash: str, auth_provider: str = "local") -> User:
        user = User(
            username=username.strip().lower(),
            email=email.strip().lower(),
            password_hash=password_hash,
            auth_provider=auth_provider,
        )
        session.add(user)
        session.flush()
        return user

    @staticmethod
    def get_by_id(session: Session, user_id: int) -> Optional[User]:
        return session.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_username(session: Session, username: str) -> Optional[User]:
        return session.query(User).filter(User.username == username.strip().lower()).first()

    @staticmethod
    def get_by_email(session: Session, email: str) -> Optional[User]:
        return session.query(User).filter(User.email == email.strip().lower()).first()


class ProfileRepository:
    @staticmethod
    def get_profile(session: Session, user_id: int) -> Optional[UserProfile]:
        return session.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    @staticmethod
    def upsert_profile(session: Session, user_id: int, profile_data: Dict[str, Any]) -> UserProfile:
        profile = session.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            profile = UserProfile(user_id=user_id, **profile_data)
            session.add(profile)
        else:
            for key, val in profile_data.items():
                if hasattr(profile, key):
                    setattr(profile, key, val)
        session.flush()
        return profile

    @staticmethod
    def get_preferences(session: Session, user_id: int) -> Optional[DietaryPreference]:
        return session.query(DietaryPreference).filter(DietaryPreference.user_id == user_id).first()

    @staticmethod
    def upsert_preferences(session: Session, user_id: int, pref_data: Dict[str, Any]) -> DietaryPreference:
        pref = session.query(DietaryPreference).filter(DietaryPreference.user_id == user_id).first()
        if not pref:
            pref = DietaryPreference(user_id=user_id, **pref_data)
            session.add(pref)
        else:
            for key, val in pref_data.items():
                if hasattr(pref, key):
                    setattr(pref, key, val)
        session.flush()
        return pref


class FoodDatabaseRepository:
    @staticmethod
    def get_all(session: Session) -> List[Food]:
        return session.query(Food).order_by(Food.name).all()

    @staticmethod
    def get_by_id(session: Session, food_id: str) -> Optional[Food]:
        return session.query(Food).filter(Food.food_id == food_id).first()

    @staticmethod
    def count(session: Session) -> int:
        return session.query(Food).count()


class MealPlanRepository:
    @staticmethod
    def save_plan(
        session: Session,
        user_id: int,
        target_calories: float,
        target_protein: float,
        target_carbs: float,
        target_fat: float,
        total_calories: float,
        total_protein: float,
        total_carbs: float,
        total_fat: float,
        meals_dict: Dict[str, List[Dict[str, Any]]],
        model_version: str = "Ensemble v1.0",
        ensemble_config: str = "Soft Voting (RF + HistGB + MLP + KNN)",
    ) -> MealPlan:
        # Mark previous active plans as historical
        session.query(MealPlan).filter(MealPlan.user_id == user_id, MealPlan.status == "active").update(
            {"status": "historical"}
        )

        plan = MealPlan(
            user_id=user_id,
            target_calories=target_calories,
            target_protein_g=target_protein,
            target_carbs_g=target_carbs,
            target_fat_g=target_fat,
            total_calories=total_calories,
            total_protein_g=total_protein,
            total_carbs_g=total_carbs,
            total_fat_g=total_fat,
            model_version=model_version,
            ensemble_config=ensemble_config,
            status="active",
        )
        session.add(plan)
        session.flush()

        # Add items
        for slot, items in meals_dict.items():
            for rank, item in enumerate(items, 1):
                m_item = MealPlanItem(
                    meal_plan_id=plan.id,
                    food_id=item.get("food_id", "custom"),
                    food_name=item.get("name", "Unknown Food"),
                    meal_slot=slot,
                    servings=float(item.get("servings", 1.0)),
                    total_weight_g=float(item.get("total_weight_g", 100.0)),
                    serving_unit=item.get("serving_unit", "1 serving"),
                    calories=float(item.get("calories", 0.0)),
                    protein_g=float(item.get("protein_g", 0.0)),
                    carbs_g=float(item.get("carbs_g", 0.0)),
                    fat_g=float(item.get("fat_g", 0.0)),
                    fiber_g=float(item.get("fiber_g", 0.0)),
                    sodium_mg=float(item.get("sodium_mg", 0.0)),
                    estimated_cost_usd=float(item.get("estimated_cost_usd", 0.0)),
                    predicted_suitability_score=float(item.get("predicted_suitability_score", 0.0)),
                    rank=rank,
                    rationale=item.get("rationale", ""),
                )
                session.add(m_item)

        session.flush()
        return plan

    @staticmethod
    def get_active_plan(session: Session, user_id: int) -> Optional[MealPlan]:
        return (
            session.query(MealPlan)
            .options(joinedload(MealPlan.items))
            .filter(MealPlan.user_id == user_id, MealPlan.status == "active")
            .order_by(MealPlan.created_at.desc())
            .first()
        )

    @staticmethod
    def get_plan_history(session: Session, user_id: int, limit: int = 10) -> List[MealPlan]:
        return (
            session.query(MealPlan)
            .options(joinedload(MealPlan.items))
            .filter(MealPlan.user_id == user_id)
            .order_by(MealPlan.created_at.desc())
            .limit(limit)
            .all()
        )



class MealLogRepository:
    @staticmethod
    def log_meal(session: Session, user_id: int, food_data: Dict[str, Any], meal_slot: str, servings: float = 1.0) -> MealLog:
        log = MealLog(
            user_id=user_id,
            food_id=food_data.get("food_id"),
            food_name=food_data.get("name", "Food Item"),
            meal_slot=meal_slot,
            servings=servings,
            calories=food_data.get("calories", food_data.get("calories_per_serving", 0.0)) * servings,
            protein_g=food_data.get("protein_g", food_data.get("protein_per_serving", 0.0)) * servings,
            carbs_g=food_data.get("carbs_g", food_data.get("carbs_per_serving", 0.0)) * servings,
            fat_g=food_data.get("fat_g", food_data.get("fat_per_serving", 0.0)) * servings,
        )
        session.add(log)
        session.flush()
        return log

    @staticmethod
    def get_logs_by_date(session: Session, user_id: int, target_date: date) -> List[MealLog]:
        logs = (
            session.query(MealLog)
            .filter(MealLog.user_id == user_id)
            .order_by(MealLog.logged_at.desc())
            .all()
        )
        # Filter matching calendar day
        return [l for l in logs if l.logged_at.date() == target_date]

    @staticmethod
    def get_recent_logs(session: Session, user_id: int, limit: int = 20) -> List[MealLog]:
        return (
            session.query(MealLog)
            .filter(MealLog.user_id == user_id)
            .order_by(MealLog.logged_at.desc())
            .limit(limit)
            .all()
        )


class ProgressRepository:
    @staticmethod
    def add_weight_record(session: Session, user_id: int, weight_kg: float, notes: str = "") -> ProgressRecord:
        record = ProgressRecord(user_id=user_id, weight_kg=weight_kg, notes=notes)
        session.add(record)
        session.flush()
        return record

    @staticmethod
    def get_weight_history(session: Session, user_id: int) -> List[ProgressRecord]:
        return (
            session.query(ProgressRecord)
            .filter(ProgressRecord.user_id == user_id)
            .order_by(ProgressRecord.date.asc())
            .all()
        )


class FeedbackRepository:
    @staticmethod
    def add_feedback(
        session: Session,
        user_id: int,
        food_id: str,
        food_name: str,
        feedback_type: str,
        comment: str = "",
        recommendation_id: Optional[int] = None,
    ) -> RecommendationFeedback:
        fb = RecommendationFeedback(
            user_id=user_id,
            food_id=food_id,
            food_name=food_name,
            feedback_type=feedback_type,
            comment=comment,
            recommendation_id=recommendation_id,
        )
        session.add(fb)
        session.flush()
        return fb

    @staticmethod
    def get_user_feedback(session: Session, user_id: int) -> List[RecommendationFeedback]:
        return (
            session.query(RecommendationFeedback)
            .filter(RecommendationFeedback.user_id == user_id)
            .order_by(RecommendationFeedback.created_at.desc())
            .all()
        )
