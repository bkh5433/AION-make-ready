from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict
from models.ReportOutput import ReportOutput


class ReportGenerationResponse(BaseModel):
    """Enhanced report generation response model"""
    success: bool
    message: str
    output: Optional[ReportOutput] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    warnings: Optional[List[str]] = None
    data_issues: Optional[List[Dict]] = None
    session_id: Optional[str] = None

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
