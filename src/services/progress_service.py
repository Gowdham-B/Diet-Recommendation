"""
Progress tracking and meal logging service supporting weight trends and feedback.
"""
from typing import Dict, Any, List, Optional
from datetime import date, datetime
from src.database.connection import get_db_context
from src.database.repositories import MealLogRepository, ProgressRepository, FeedbackRepository


class ProgressService:
    """Manages user weight logs, daily meal tracking, and recommendation feedback."""

    @staticmethod
    def log_food_eaten(user_id: int, food_data: Dict[str, Any], meal_slot: str, servings: float = 1.0) -> Dict[str, Any]:
        """Records an ingested food item to database meal logs."""
        with get_db_context() as session:
            log = MealLogRepository.log_meal(session, user_id, food_data, meal_slot, servings)
            return {
                "id": log.id,
                "food_name": log.food_name,
                "meal_slot": log.meal_slot,
                "calories": log.calories,
                "logged_at": log.logged_at,
            }

    @staticmethod
    def get_recent_meal_logs(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieves recent meal logs for an authenticated user."""
        with get_db_context() as session:
            logs = MealLogRepository.get_recent_logs(session, user_id, limit)
            return [
                {
                    "id": l.id,
                    "food_name": l.food_name,
                    "meal_slot": l.meal_slot,
                    "servings": l.servings,
                    "calories": round(l.calories, 1),
                    "protein_g": round(l.protein_g, 1),
                    "carbs_g": round(l.carbs_g, 1),
                    "fat_g": round(l.fat_g, 1),
                    "logged_at": l.logged_at.strftime("%Y-%m-%d %H:%M"),
                }
                for l in logs
            ]

    get_recent_logs = get_recent_meal_logs

    @staticmethod
    def record_weight(user_id: int, weight_kg: float, notes: str = "") -> Dict[str, Any]:
        """Saves a user's weight measurement to the database."""
        with get_db_context() as session:
            rec = ProgressRepository.add_weight_record(session, user_id, weight_kg, notes)
            return {"id": rec.id, "weight_kg": rec.weight_kg, "date": rec.date}

    @staticmethod
    def get_weight_history(user_id: int) -> List[Dict[str, Any]]:
        """Retrieves chronological weight tracking records."""
        with get_db_context() as session:
            records = ProgressRepository.get_weight_history(session, user_id)
            return [
                {
                    "date": r.date.strftime("%Y-%m-%d"),
                    "weight_kg": r.weight_kg,
                    "notes": r.notes,
                }
                for r in records
            ]

    @staticmethod
    def submit_recommendation_feedback(
        user_id: int,
        food_id: str,
        food_name: str,
        feedback_type: str,
        comment: str = "",
    ) -> None:
        """Stores user feedback (liked, disliked, replaced) for continuous personalization."""
        with get_db_context() as session:
            FeedbackRepository.add_feedback(
                session=session,
                user_id=user_id,
                food_id=food_id,
                food_name=food_name,
                feedback_type=feedback_type,
                comment=comment,
            )
