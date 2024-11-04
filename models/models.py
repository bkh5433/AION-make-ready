from pydantic import BaseModel, Field, ConfigDict, field_validator, validator, model_validator
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
    """Model for work order metrics with calculations"""
    # Work order tracking fields
    open_work_orders: int = Field(ge=0)
    new_work_orders: int = Field(ge=0)
    completed_work_orders: int = Field(ge=0)
    cancelled_work_orders: int = Field(ge=0)
    pending_work_orders: int = Field(ge=0)
    percentage_completed: float = Field(ge=0, le=100)

    # Rate calculations with defaults (will be recalculated)
    days_per_month: int = Field(ge=0, le=31, default=21)
    daily_rate: float = Field(ge=0, default=0.0)
    monthly_rate: float = Field(ge=0, default=0.0)
    break_even_target: float = Field(ge=0, default=0.0)
    current_output: float = Field(ge=0, default=0.0)

    @model_validator(mode='after')
    def calculate_rates(self) -> 'WorkOrderMetrics':
        """Calculate all rates based on completed work orders"""
        try:
            if self.days_per_month > 0:
                # Calculate daily rate from completed work orders
                self.daily_rate = round(self.completed_work_orders / self.days_per_month, 1)

                # Calculate monthly rate from daily rate
                self.monthly_rate = round(self.daily_rate * self.days_per_month, 1)

                # Set current output same as daily rate for consistency
                self.current_output = self.daily_rate

                # Calculate break-even target
                target_rate = max(self.new_work_orders, self.completed_work_orders) / self.days_per_month
                self.break_even_target = round(target_rate * 1.1, 1)  # Adding 10% buffer
        except Exception as e:
            # If any calculation fails, ensure we have valid defaults
            self.daily_rate = 0.0
            self.monthly_rate = 0.0
            self.current_output = 0.0
            self.break_even_target = 0.0

        return self

    @field_validator('percentage_completed', 'daily_rate', 'monthly_rate', 'break_even_target', 'current_output')
    def round_values(cls, v: float) -> float:
        return round(v, 1)

    def get_metrics_for_table(self) -> dict:
        """Get metrics formatted for what-if table calculations"""
        return {
            'daily_rate': self.daily_rate,
            'monthly_rate': self.monthly_rate,
            'break_even_target': self.break_even_target,
            'current_output': self.current_output,
            'days_per_month': self.days_per_month
        }

    def get_all_metrics(self) -> dict:
        """Get all metrics including work orders and calculations"""
        return {
            **self.get_metrics_for_table(),
            'open_work_orders': self.open_work_orders,
            'new_work_orders': self.new_work_orders,
            'completed_work_orders': self.completed_work_orders,
            'cancelled_work_orders': self.cancelled_work_orders,
            'pending_work_orders': self.pending_work_orders,
            'percentage_completed': self.percentage_completed
        }


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
