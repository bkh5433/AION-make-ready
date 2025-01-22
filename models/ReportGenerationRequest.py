from pydantic import BaseModel, Field, model_validator
from datetime import datetime, timedelta
from typing import Optional, List, Dict


class ReportGenerationRequest(BaseModel):
    """Model for report generation requests"""
    properties: List[int] = Field(min_length=1)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    include_metrics: bool = Field(default=True)
    format_preferences: Optional[Dict[str, str]] = None

    @model_validator(mode='after')
    def validate_dates(self) -> 'ReportGenerationRequest':
        """Validate date range if provided"""
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValueError("End date must be after start date")
            if (self.end_date - self.start_date) > timedelta(days=366):
                raise ValueError("Date range cannot exceed one year")
        return self
