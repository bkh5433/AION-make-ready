from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator, PrivateAttr
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
from logger_config import LogConfig
from typing import Union

logger = LogConfig().get_logger('models')



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
    actual_open_work_orders: int = Field(ge=0)
    new_work_orders: int = Field(ge=0, default=0)
    completed_work_orders: int = Field(ge=0)
    cancelled_work_orders: int = Field(ge=0)
    pending_work_orders: int = Field(ge=0)
    percentage_completed: float = Field(ge=0, le=100)
    average_days_to_complete: float = Field(ge=0, default=0.0)

    # Period dates
    period_start_date: Optional[datetime] = None
    period_end_date: Optional[datetime] = None

    # Configuration
    days_per_month: int = Field(ge=0, le=31, default=21)

    # Calculated metrics
    _daily_rate: float = PrivateAttr(default=0.0)
    _monthly_rate: float = PrivateAttr(default=0.0)
    _break_even_target: float = PrivateAttr(default=0.0)
    _current_output: float = PrivateAttr(default=0.0)

    model_config = ConfigDict(
        validate_assignment=True,
        extra='allow',
        arbitrary_types_allowed=True
    )

    @field_validator('days_per_month')
    def validate_days(cls, v: int) -> int:
        if v <= 0:
            return 21  # Default if invalid
        return v

    def __init__(self, **data):
        # Ensure all required fields have at least default values
        if 'open_work_orders' not in data:
            data['open_work_orders'] = 0
        if 'actual_open_work_orders' not in data:
            data['actual_open_work_orders'] = data.get('ActualOpenWorkOrders_Current', 0)
        if 'completed_work_orders' not in data:
            data['completed_work_orders'] = data.get('CompletedWorkOrder_Current', 0)
        if 'cancelled_work_orders' not in data:
            data['cancelled_work_orders'] = data.get('CancelledWorkOrder_Current', 0)
        if 'pending_work_orders' not in data:
            data['pending_work_orders'] = data.get('PendingWorkOrders', 0)
        if 'percentage_completed' not in data:
            data['percentage_completed'] = data.get('PercentageCompletedThisPeriod', 0.0)
        if 'average_days_to_complete' not in data:
            data['average_days_to_complete'] = data.get('AverageDaysToComplete', 0.0)

        super().__init__(**data)
        self._calculate_metrics()

    def _calculate_metrics(self) -> None:
        """Calculate all derived metrics"""
        try:
            if self.days_per_month > 0:
                self._daily_rate = round(self.completed_work_orders / self.days_per_month, 1)
                self._monthly_rate = round(self._daily_rate * self.days_per_month, 1)
                self._current_output = self._daily_rate

                # Calculate break-even target with 10% buffer
                target_rate = max(self.actual_open_work_orders, self.completed_work_orders) / self.days_per_month
                self._break_even_target = round(target_rate * 1.1, 1)
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            self._daily_rate = 0.0
            self._monthly_rate = 0.0
            self._current_output = 0.0
            self._break_even_target = 0.0

    @property
    def daily_rate(self) -> float:
        return self._daily_rate

    @property
    def monthly_rate(self) -> float:
        return self._monthly_rate

    @property
    def break_even_target(self) -> float:
        return self._break_even_target

    @property
    def current_output(self) -> float:
        return self._current_output

    def get_metrics_for_table(self) -> dict:
        """Get metrics formatted for what-if table calculations"""
        return {
            'daily_rate': self.daily_rate,
            'monthly_rate': self.monthly_rate,
            'break_even_target': self.break_even_target,
            'current_output': self.current_output,
            'days_per_month': self.days_per_month,
            'period_start': self.period_start_date,  # Include dates in output
            'period_end': self.period_end_date
        }

    @field_validator('period_start_date', 'period_end_date', mode='before')
    @classmethod
    def parse_dates(cls, v: Optional[Union[str, datetime]]) -> Optional[datetime]:
        if not v:
            return None
        if isinstance(v, datetime):
            return v
        try:
            # Try parsing common formats
            for fmt in [
                '%a, %d %b %Y %H:%M:%S GMT',  # Tue, 12 Nov 2024 00:00:00 GMT
                '%Y-%m-%dT%H:%M:%S',  # ISO format
                '%Y-%m-%d'  # Simple date
            ]:
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    continue
            raise ValueError(f"Could not parse date: {v}")
        except Exception as e:
            logger.error(f"Date parsing error in WorkOrderMetrics: {str(e)}")
            return None

    @model_validator(mode='after')
    def validate_dates(self) -> 'WorkOrderMetrics':
        """Validate period dates if present"""
        if self.period_start_date and self.period_end_date:
            if self.period_end_date < self.period_start_date:
                raise ValueError("End date must be after start date")
        return self

    def model_dump(self, **kwargs) -> Dict:
        """Override model_dump to include calculated metrics"""
        base_dict = super().model_dump(**kwargs)
        base_dict.update({
            'daily_rate': self.daily_rate,
            'monthly_rate': self.monthly_rate,
            'break_even_target': self.break_even_target,
            'current_output': self.current_output
        })
        return base_dict


class Property(BaseModel):
    """Model for property data"""
    property_key: int = Field(gt=0)
    property_name: str
    total_unit_count: int = Field(gt=0)
    latest_post_date: Optional[datetime] = None
    status: PropertyStatus = PropertyStatus.ACTIVE
    metrics: Optional[WorkOrderMetrics] = None
    period_start_date: Optional[datetime] = None
    period_end_date: Optional[datetime] = None

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

    @field_validator('period_start_date', 'period_end_date', mode='before')
    @classmethod
    def parse_dates(cls, v: Optional[Union[str, datetime]]) -> Optional[datetime]:
        if not v:
            return None
        if isinstance(v, datetime):
            return v
        try:
            # Try parsing common formats
            for fmt in [
                '%a, %d %b %Y %H:%M:%S GMT',  # Tue, 12 Nov 2024 00:00:00 GMT
                '%Y-%m-%dT%H:%M:%S',  # ISO format
                '%Y-%m-%d'  # Simple date
            ]:
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    continue
            raise ValueError(f"Could not parse date: {v}")
        except Exception as e:
            raise ValueError(f"Date parsing error: {str(e)}")

    @model_validator(mode='after')
    def validate_dates(self) -> 'Property':
        """Ensure period dates are valid and propagate to metrics"""
        if self.period_start_date and self.period_end_date:
            if self.period_end_date < self.period_start_date:
                raise ValueError("End date must be after start date")

            # Propagate dates to metrics if they exist
            if self.metrics:
                self.metrics.period_start_date = self.period_start_date
                self.metrics.period_end_date = self.period_end_date

        return self

    def get_summary(self) -> Dict:
        """Get property summary including key metrics"""
        summary = {
            'property_key': self.property_key,
            'property_name': self.property_name,
            'total_units': self.total_unit_count,
            'status': self.status,
            'last_updated': self.latest_post_date
        }

        if self.metrics:
            summary.update({
                'metrics': self.metrics.get_performance_metrics(),
                'period': {
                    'start': self.period_start_date,
                    'end': self.period_end_date
                }
            })

        return summary


class PropertySearchResult(BaseModel):
    """Model for property search results"""
    count: int
    data: List[Property]
    last_updated: datetime
    period_info: Optional[Dict[str, datetime]] = None

    model_config = ConfigDict(frozen=True)

    @model_validator(mode='after')
    def validate_dates(self) -> 'PropertySearchResult':
        """Ensure all properties have consistent period dates"""
        if self.data and not self.period_info:
            first_property = self.data[0]
            if first_property.period_start_date and first_property.period_end_date:
                self.period_info = {
                    'start_date': first_property.period_start_date,
                    'end_date': first_property.period_end_date
                }
        return self


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


class WorkOrderAnalytics(BaseModel):
    """Enhanced work order analytics calculations"""
    # Core rates
    daily_rate: float = Field(ge=0)
    monthly_rate: float = Field(ge=0)
    break_even_target: float = Field(ge=0)
    current_output: float = Field(ge=0)

    # Additional metrics from SQL
    average_days_to_complete: float = Field(ge=0, default=0.0)
    completion_percentage: float = Field(ge=0, le=100, default=0.0)

    # Configuration
    days_per_month: int = Field(ge=0, le=31, default=21)
    buffer_percentage: float = Field(ge=0, le=100, default=10.0)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator('daily_rate', 'monthly_rate', 'break_even_target',
                     'current_output', 'average_days_to_complete', 'completion_percentage')
    @classmethod
    def round_rate(cls, v: float) -> float:
        return round(v, 1)

    def calculate_monthly_metrics(self) -> Dict[str, float]:
        """Calculate comprehensive monthly metrics"""
        metrics = {
            'projected_monthly': round(self.daily_rate * self.days_per_month, 1),
            'break_even_gap': round(self.break_even_target - self.daily_rate, 1),
            'performance_ratio': round((self.daily_rate / self.break_even_target * 100), 1)
            if self.break_even_target > 0 else 0,
            'efficiency_score': self._calculate_efficiency_score(),
            'average_completion_time': self.average_days_to_complete,
            'completion_rate': self.completion_percentage
        }

        # Add trend indicators
        metrics.update(self._calculate_trend_indicators())

        return metrics

    def _calculate_efficiency_score(self) -> float:
        """Calculate overall efficiency score (0-100)"""
        if self.break_even_target == 0:
            return 0.0

        # Weighted components
        completion_weight = 0.4
        speed_weight = 0.3
        output_weight = 0.3

        # Calculate component scores
        completion_score = min(self.completion_percentage, 100)

        speed_score = 100
        if self.average_days_to_complete > 0:
            speed_score = max(0, 100 - (int(self.average_days_to_complete) - 1) * 20)

        output_ratio = (self.daily_rate / self.break_even_target) * 100
        output_score = min(output_ratio, 100)

        # Calculate weighted average
        total_score = (completion_score * completion_weight +
                       speed_score * speed_weight +
                       output_score * output_weight)

        return round(total_score, 1)

    def _calculate_trend_indicators(self) -> Dict[str, float]:
        """Calculate trend indicators for key metrics"""
        trends = {}

        # Output trend
        if self.current_output > self.break_even_target:
            trends['output_trend'] = 1.0  # above_target
        elif self.current_output >= self.break_even_target * 0.9:
            trends['output_trend'] = 0.5  # near_target
        else:
            trends['output_trend'] = 0.0  # below_target

        # Completion trend
        if self.completion_percentage >= 90:
            trends['completion_trend'] = 1.0  # excellent
        elif self.completion_percentage >= 75:
            trends['completion_trend'] = 0.75  # good
        elif self.completion_percentage >= 50:
            trends['completion_trend'] = 0.5  # fair
        else:
            trends['completion_trend'] = 0.0  # needs_improvement

        return trends

    def get_recommendations(self) -> List[str]:
        """Generate recommendations based on analytics"""
        recommendations = []

        # Check output rate
        if self.daily_rate < self.break_even_target:
            gap = self.break_even_target - self.daily_rate
            recommendations.append(
                f"Increase daily output by {round(gap, 1)} to meet break-even target"
            )

        # Check completion time
        if self.average_days_to_complete > 3:
            recommendations.append(
                "Review workflow to reduce average completion time"
            )

        # Check completion rate
        if self.completion_percentage < 75:
            recommendations.append(
                "Focus on improving completion rate, currently below target"
            )

        return recommendations

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics and status indicators"""
        return {
            'metrics': self.calculate_monthly_metrics(),
            'recommendations': self.get_recommendations(),
            'status': {
                'on_target': self.current_output >= self.break_even_target,
                'efficiency_score': self._calculate_efficiency_score(),
                'needs_attention': (
                        self.completion_percentage < 75 or
                        self.current_output < self.break_even_target * 0.9
                )
            }
        }
