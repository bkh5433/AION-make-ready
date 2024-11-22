from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict


class ReportOutput(BaseModel):
    """Enhanced report output model"""
    directory: str
    propertyCount: int
    files: Optional[List[str]] = None
    generated_at: datetime = Field(default_factory=datetime.now)
    metrics_included: bool = False
    period_covered: Optional[Dict[str, datetime]] = None

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
