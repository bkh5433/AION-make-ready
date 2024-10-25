from datetime import datetime, timedelta
import pytest
from pydantic import ValidationError
from models.models import (
    WorkOrderMetrics,
    Property,
    PropertyStatus,
    ReportGenerationRequest,
    WorkOrderAnalytics
)


class TestWorkOrderMetrics:
    def test_valid_metrics(self):
        metrics = WorkOrderMetrics(
            open_work_orders=10,
            new_work_orders=5,
            completed_work_orders=3,
            cancelled_work_orders=1,
            pending_work_orders=11,
            percentage_completed=75.67
        )
        assert metrics.percentage_completed == 75.7
        assert metrics.open_work_orders == 10

    def test_negative_values(self):
        with pytest.raises(ValidationError):
            WorkOrderMetrics(
                open_work_orders=-1,
                new_work_orders=5,
                completed_work_orders=3,
                cancelled_work_orders=1,
                pending_work_orders=11,
                percentage_completed=75.67
            )

    def test_percentage_bounds(self):
        with pytest.raises(ValidationError):
            WorkOrderMetrics(
                open_work_orders=10,
                new_work_orders=5,
                completed_work_orders=3,
                cancelled_work_orders=1,
                pending_work_orders=11,
                percentage_completed=101
            )


class TestProperty:
    @pytest.fixture
    def valid_metrics(self):
        return WorkOrderMetrics(
            open_work_orders=10,
            new_work_orders=5,
            completed_work_orders=3,
            cancelled_work_orders=1,
            pending_work_orders=11,
            percentage_completed=75.7
        )

    def test_valid_property(self, valid_metrics):
        property = Property(
            property_key=1,
            property_name="Test Property",
            total_unit_count=100,
            latest_post_date=datetime.now(),
            status=PropertyStatus.ACTIVE,
            metrics=valid_metrics
        )
        assert property.property_key == 1
        assert property.property_name == "Test Property"
        assert property.status == PropertyStatus.ACTIVE

    def test_property_name_validation(self):
        with pytest.raises(ValueError):
            Property(
                property_key=1,
                property_name="",
                total_unit_count=100,
                latest_post_date=datetime.now()
            )

        with pytest.raises(ValueError):
            Property(
                property_key=1,
                property_name="Historical Test Property",
                total_unit_count=100,
                latest_post_date=datetime.now()
            )


class TestWorkOrderAnalytics:
    def test_valid_analytics(self):
        analytics = WorkOrderAnalytics(
            daily_rate=10.567,
            monthly_rate=200.789,
            break_even_target=15.123,
            current_output=12.89
        )
        assert analytics.daily_rate == 10.6
        assert analytics.monthly_rate == 200.8
        assert analytics.break_even_target == 15.1
        assert analytics.current_output == 12.9

    def test_monthly_metrics_calculation(self):
        analytics = WorkOrderAnalytics(
            daily_rate=10.0,
            monthly_rate=200.0,
            break_even_target=15.0,
            current_output=12.0,
            days_per_month=21
        )
        metrics = analytics.calculate_monthly_metrics()
        assert metrics['projected_monthly'] == 210.0
        assert metrics['break_even_gap'] == 5.0
        assert metrics['performance_ratio'] == 66.7

    def test_zero_break_even_target(self):
        analytics = WorkOrderAnalytics(
            daily_rate=10.0,
            monthly_rate=200.0,
            break_even_target=0.0,
            current_output=12.0
        )
        metrics = analytics.calculate_monthly_metrics()
        assert metrics['performance_ratio'] == 0

    def test_days_per_month_bounds(self):
        with pytest.raises(ValidationError):
            WorkOrderAnalytics(
                daily_rate=10.0,
                monthly_rate=200.0,
                break_even_target=15.0,
                current_output=12.0,
                days_per_month=-1
            )

        with pytest.raises(ValidationError):
            WorkOrderAnalytics(
                daily_rate=10.0,
                monthly_rate=200.0,
                break_even_target=15.0,
                current_output=12.0,
                days_per_month=32
            )


class TestReportGenerationRequest:
    def test_valid_request_with_minimal_data(self):
        """Test creating request with just properties list"""
        request = ReportGenerationRequest(properties=[1, 2, 3])
        assert len(request.properties) == 3
        assert request.start_date is None
        assert request.end_date is None

    def test_valid_request_with_full_data(self):
        """Test creating request with all optional fields"""
        start_date = datetime.now()
        end_date = start_date + timedelta(days=7)
        request = ReportGenerationRequest(
            properties=[1, 2, 3],
            start_date=start_date,
            end_date=end_date
        )
        assert len(request.properties) == 3
        assert request.start_date == start_date
        assert request.end_date == end_date

    def test_empty_properties_list(self):
        """Test validation of empty properties list"""
        with pytest.raises(ValidationError) as exc_info:
            ReportGenerationRequest(properties=[])
        assert "min_items" in str(exc_info.value)

    def test_too_many_properties(self):
        """Test validation of properties list exceeding maximum size"""
        with pytest.raises(ValidationError) as exc_info:
            ReportGenerationRequest(properties=list(range(51)))
        assert "Maximum of 50 properties can be processed at once" in str(exc_info.value)

    def test_properties_with_invalid_values(self):
        """Test validation of property values"""
        with pytest.raises(ValidationError):
            ReportGenerationRequest(properties=[-1, 0, 1])  # Negative and zero values

    def test_invalid_date_range(self):
        """Test creating request with end_date before start_date"""
        start_date = datetime.now()
        end_date = start_date - timedelta(days=7)  # end_date is before start_date

        # Currently this passes as we don't validate date range
        # If we want to add this validation, we should update the model
        request = ReportGenerationRequest(
            properties=[1],
            start_date=start_date,
            end_date=end_date
        )

        # Add a TODO comment suggesting improvement
        # TODO: Consider adding date range validation to ensure end_date is after start_date

    def test_request_immutability(self):
        """Test that properties can't be modified after creation"""
        request = ReportGenerationRequest(properties=[1, 2, 3])

        with pytest.raises(ValidationError):
            request.properties = []  # Should not be able to set to empty list

        with pytest.raises(ValidationError):
            request.properties = list(range(51))  # Should not be able to exceed max

    def test_request_serialization(self):
        """Test request serialization to dict/json"""
        start_date = datetime.now()
        end_date = start_date + timedelta(days=7)
        request = ReportGenerationRequest(
            properties=[1, 2, 3],
            start_date=start_date,
            end_date=end_date
        )

        request_dict = request.model_dump()
        assert isinstance(request_dict, dict)
        assert 'properties' in request_dict
        assert 'start_date' in request_dict
        assert 'end_date' in request_dict

        # Test JSON serialization
        request_json = request.model_dump_json()
        assert isinstance(request_json, str)

    def test_request_property_types(self):
        """Test that properties must be integers"""
        with pytest.raises(ValidationError):
            ReportGenerationRequest(properties=["1", "2", "3"])  # Strings instead of ints

        with pytest.raises(ValidationError):
            ReportGenerationRequest(properties=[1.1, 2.2, 3.3])  # Floats instead of ints
