from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator, PrivateAttr
from datetime import datetime
from typing import Optional, Dict
from typing import Union
from models.PropertyStatus import PropertyStatus
from models.WorkOrderMetrics import WorkOrderMetrics


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
