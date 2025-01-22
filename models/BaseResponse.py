from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


class BaseResponse(BaseModel):
    """Base response model for all API endpoints"""
    success: bool
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(frozen=True)
