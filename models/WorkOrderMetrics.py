from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator, PrivateAttr
from datetime import datetime
from typing import Optional, Dict, List
from logger_config import LogConfig
from typing import Union

logger_config = LogConfig()
logger = logger_config.get_logger('models')


class WorkOrderType(BaseModel):
    """Model for work order type breakdown"""
    category: str
    count: int = Field(ge=0)
    percentage: float = Field(ge=0, le=100)

    model_config = ConfigDict(
        validate_assignment=True,
        extra='allow'
    )


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

    # Work order type breakdown
    work_order_types: List[WorkOrderType] = Field(default_factory=list)

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
            'current_output': self.current_output,
            'work_order_types': [wo.model_dump() for wo in self.work_order_types]
        })
        return base_dict
