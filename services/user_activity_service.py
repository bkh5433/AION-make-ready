from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from models.UserActivityMetrics import UserActivity, UserActivityMetrics
from auth_middleware import db
from logger_config import LogConfig

# Initialize logging
log_config = LogConfig()
logger = log_config.get_logger("user_activity")


class UserActivityService:
    """Service for tracking user activity and calculating DAU/MAU metrics"""

    def __init__(self):
        self.activity_ref = db.collection('user_activity')
        self.metrics_ref = db.collection('user_activity_metrics')

    def record_activity(self, user_data: Dict[str, Any], activity_type: str) -> None:
        """Record a user activity"""
        try:
            now = datetime.now(timezone.utc)
            today = now.strftime('%Y-%m-%d')

            activity = UserActivity(
                user_id=user_data['user_id'],
                user_email=user_data['email'],
                last_active=now,
                activity_type=activity_type
            )

            # Store activity
            activity_doc = self.activity_ref.document(f"{user_data['user_id']}_{today}")
            activity_doc.set(activity.model_dump(), merge=True)

            # Update metrics
            self._update_metrics(today)

            logger.info(f"Recorded activity for user {user_data['email']}: {activity_type}")

        except Exception as e:
            logger.error(f"Error recording user activity: {str(e)}")
            raise

    def _update_metrics(self, date: str) -> None:
        """Update DAU/MAU metrics for a given date"""
        try:
            # Convert date string to datetime
            current_date = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            month_start = current_date.replace(day=1)

            # Query for daily active users
            daily_users = (
                self.activity_ref
                .where('last_active', '>=', current_date)
                .where('last_active', '<', current_date + timedelta(days=1))
                .stream()
            )
            daily_count = len(set(doc.get('user_id') for doc in daily_users))

            # Query for monthly active users
            monthly_users = (
                self.activity_ref
                .where('last_active', '>=', month_start)
                .where('last_active', '<', current_date + timedelta(days=1))
                .stream()
            )
            monthly_count = len(set(doc.get('user_id') for doc in monthly_users))

            # Update metrics
            metrics = UserActivityMetrics(
                date=date,
                daily_active_users=daily_count,
                monthly_active_users=monthly_count
            )

            self.metrics_ref.document(date).set(metrics.model_dump())
            logger.info(f"Updated metrics for {date}: DAU={daily_count}, MAU={monthly_count}")

        except Exception as e:
            logger.error(f"Error updating metrics: {str(e)}")
            raise

    def get_metrics(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get activity metrics for the last N days"""
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)

            query = (
                self.metrics_ref
                .where('last_updated', '>=', start_date)
                .order_by('last_updated', direction='DESCENDING')
                .limit(days)
            )

            docs = query.stream()
            return [doc.to_dict() for doc in docs]

        except Exception as e:
            logger.error(f"Error getting metrics: {str(e)}")
            raise

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get metrics for current day and month"""
        try:
            now = datetime.now(timezone.utc)
            today = now.strftime('%Y-%m-%d')

            metrics_doc = self.metrics_ref.document(today).get()

            if not metrics_doc.exists:
                self._update_metrics(today)
                metrics_doc = self.metrics_ref.document(today).get()

            return metrics_doc.to_dict()

        except Exception as e:
            logger.error(f"Error getting current metrics: {str(e)}")
            raise
