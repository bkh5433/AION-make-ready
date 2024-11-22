from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List
from models.ReportOutput import ReportOutput


class ReportGenerationResponse(BaseModel):
    """Enhanced report generation response model"""
    success: bool
    message: str
    output: ReportOutput
    timestamp: datetime = Field(default_factory=datetime.now)
    warnings: Optional[List[str]] = None
    session_id: Optional[str] = None

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
