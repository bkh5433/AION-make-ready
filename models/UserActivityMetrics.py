from datetime import datetime, timezone
from pydantic import BaseModel, Field


class UserActivity(BaseModel):
    """Model for tracking individual user activity"""
    user_id: str = Field(..., description="ID of the user")
    user_email: str = Field(..., description="Email of the user")
    last_active: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),
                                  description="Last activity timestamp (UTC)")
    activity_type: str = Field(..., description="Type of activity (e.g., 'report_generation', 'login')")


class UserActivityMetrics(BaseModel):
    """Model for aggregated user activity metrics"""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    daily_active_users: int = Field(default=0, description="Number of unique users active on this date")
    monthly_active_users: int = Field(default=0, description="Number of unique users active in this month")
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),
                                   description="Last update timestamp (UTC)")
