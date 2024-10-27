from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum


class PropertyStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PENDING = "PENDING"


class BaseResponse(BaseModel):
    """Base response model for all API endpoints"""
    success: bool
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(frozen=True)


class WorkOrderMetrics(BaseModel):
    """Model for work order metrics data"""
    open_work_orders: int = Field(ge=0)
    new_work_orders: int = Field(ge=0)
    completed_work_orders: int = Field(ge=0)
    cancelled_work_orders: int = Field(ge=0)
    pending_work_orders: int = Field(ge=0)
    percentage_completed: float = Field(ge=0, le=100)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator('percentage_completed')
    @classmethod
    def round_percentage(cls, v: float) -> float:
        return round(v, 1)


class Property(BaseModel):
    """Model for property data"""
    property_key: int = Field(gt=0)
    property_name: str
    total_unit_count: int = Field(gt=0)
    latest_post_date: datetime
    status: PropertyStatus = PropertyStatus.ACTIVE
    metrics: Optional[WorkOrderMetrics] = None

    model_config = ConfigDict(validate_assignment=True)

    @field_validator('property_name')
    @classmethod
    def validate_property_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Property name cannot be empty")
        if v.startswith("Historical"):
            raise ValueError("Property name cannot start with 'Historical'")
        return v


class PropertySearchResult(BaseModel):
    """Model for property search results"""
    count: int
    data: List[Property]
    last_updated: datetime

    model_config = ConfigDict(frozen=True)


class ReportGenerationRequest(BaseModel):
    """Model for report generation requests"""
    properties: List[int] = Field(min_length=1)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ReportOutput(BaseModel):
    """Model for report generation output details"""
    directory: str  # Changed from int to str
    propertyCount: int
    files: Optional[List[str]] = None


class ReportGenerationResponse(BaseModel):
    """Model for report generation responses"""
    success: bool
    message: str
    output: ReportOutput
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WorkOrderAnalytics(BaseModel):
    """Model for work order analytics calculations"""
    daily_rate: float = Field(ge=0)
    monthly_rate: float = Field(ge=0)
    break_even_target: float = Field(ge=0)
    current_output: float = Field(ge=0)
    days_per_month: int = Field(ge=0, le=31, default=21)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator('daily_rate', 'monthly_rate', 'break_even_target', 'current_output')
    @classmethod
    def round_rate(cls, v: float) -> float:
        return round(v, 1)

    def calculate_monthly_metrics(self) -> Dict[str, float]:
        """Calculate monthly metrics based on daily rates"""
        return {
            'projected_monthly': round(self.daily_rate * self.days_per_month, 1),
            'break_even_gap': round(self.break_even_target - self.daily_rate, 1),
            'performance_ratio': round((self.daily_rate / self.break_even_target * 100), 1)
            if self.break_even_target > 0 else 0
        }
