from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Dict, Any


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
