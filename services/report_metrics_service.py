from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from models.ReportMetrics import ReportMetrics
from auth_middleware import db
from logger_config import LogConfig
from config import Config
import uuid

# Initialize logging
log_config = LogConfig()
logger = log_config.get_logger("report_metrics")


class ReportMetricsService:
    """Service for tracking report generation metrics in Firestore"""

    def __init__(self):
        self.metrics_ref = db.collection('report_metrics')

    def create_report_id(self) -> str:
        """Generate a new report ID"""
        return str(uuid.uuid4())

    def record_metrics(self, user_data: Dict[str, Any], property_keys: List[str],
                       report_id: str, success: bool, error: Optional[str] = None,
                       start_time: Optional[datetime] = None) -> None:
        """
        Record report generation metrics after completion
        Only writes to Firestore once when the report is done and not in development
        """
        try:
            # Skip recording metrics in development environment
            if Config.ENV.lower() == 'development':
                logger.debug("Skipping metrics recording in development environment")
                return

            # Calculate generation time if start_time provided
            generation_time = None
            if start_time:
                # Ensure start_time is UTC
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=timezone.utc)
                generation_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            metrics = ReportMetrics(
                user_id=user_data['user_id'],
                user_email=user_data['email'],
                report_id=report_id,
                property_count=len(property_keys),
                property_keys=property_keys,
                success=success,
                error=error,
                generation_time=generation_time
            )

            # Store in Firestore
            self.metrics_ref.document(report_id).set(metrics.model_dump())
            logger.info(f"Recorded metrics for report {report_id} (success={success})")

        except Exception as e:
            logger.error(f"Error recording report metrics: {str(e)}")
            raise

    def get_user_metrics(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get report metrics for a specific user"""
        try:
            query = (self.metrics_ref
                     .where('user_id', '==', user_id)
                     .order_by('timestamp', direction='DESCENDING')
                     .limit(limit))

            docs = query.stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"Error getting user metrics: {str(e)}")
            raise

    def get_all_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all report metrics (admin only)"""
        try:
            query = (self.metrics_ref
                     .order_by('timestamp', direction='DESCENDING')
                     .limit(limit))

            docs = query.stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"Error getting all metrics: {str(e)}")
            raise
