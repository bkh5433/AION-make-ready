from pydantic import BaseModel, ConfigDict, model_validator
from datetime import datetime
from typing import Optional, List, Dict
from models.Property import Property


class PropertySearchResult(BaseModel):
    """Model for property search results"""
    count: int
    data: List[Property]
    last_updated: Optional[datetime] = None
    period_info: Optional[Dict] = None
    data_issues: Optional[List[Dict]] = None

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
