from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field


class ReportMetrics(BaseModel):
    """Model for tracking report generation metrics"""
    user_id: str = Field(..., description="ID of the user who generated the report")
    user_email: str = Field(..., description="Email of the user who generated the report")
    report_id: str = Field(..., description="Unique identifier for the report")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),
                                description="When the report was generated (UTC)")
    property_count: int = Field(..., description="Number of properties in the report")
    property_keys: List[str] = Field(..., description="List of property keys included in the report")
    success: bool = Field(default=False, description="Whether the report generation was successful")
    error: Optional[str] = Field(None, description="Error message if generation failed")
    generation_time: Optional[float] = Field(None, description="Time taken to generate report in seconds")
