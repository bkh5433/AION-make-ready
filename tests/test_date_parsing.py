import pytest
from datetime import datetime, date
from property_search import PropertySearch


def test_property_search_date_parsing():
    """Test different date formats in property search"""
    # Sample data with different date formats
    test_data = [
        {
            'PropertyKey': 1,
            'PropertyName': 'Test Property 1',
            'TotalUnitCount': 100,
            'LatestPostDate': 'Wed, 23 Oct 2024 00:00:00 GMT',
            'OpenWorkOrder_Current': 5,
            'NewWorkOrders_Current': 10,
            'CompletedWorkOrder_Current': 8,
            'CancelledWorkOrder_Current': 2,
            'PendingWorkOrders': 5,
            'PercentageCompletedThisPeriod': 75.5
        },
        {
            'PropertyKey': 2,
            'PropertyName': 'Test Property 2',
            'TotalUnitCount': 100,
            'LatestPostDate': datetime.now(),  # datetime object
            'OpenWorkOrder_Current': 5,
            'NewWorkOrders_Current': 10,
            'CompletedWorkOrder_Current': 8,
            'CancelledWorkOrder_Current': 2,
            'PendingWorkOrders': 5,
            'PercentageCompletedThisPeriod': 75.5
        },
        {
            'PropertyKey': 3,
            'PropertyName': 'Test Property 3',
            'TotalUnitCount': 100,
            'LatestPostDate': date.today(),  # date object
            'OpenWorkOrder_Current': 5,
            'NewWorkOrders_Current': 10,
            'CompletedWorkOrder_Current': 8,
            'CancelledWorkOrder_Current': 2,
            'PendingWorkOrders': 5,
            'PercentageCompletedThisPeriod': 75.5
        },
        {
            'PropertyKey': 4,
            'PropertyName': 'Test Property 4',
            'TotalUnitCount': 100,
            'LatestPostDate': '2024-10-23T00:00:00Z',  # ISO format
            'OpenWorkOrder_Current': 5,
            'NewWorkOrders_Current': 10,
            'CompletedWorkOrder_Current': 8,
            'CancelledWorkOrder_Current': 2,
            'PendingWorkOrders': 5,
            'PercentageCompletedThisPeriod': 75.5
        }
    ]

    searcher = PropertySearch(test_data)

    # Verify all properties were successfully converted
    assert len(searcher.properties) == 4

    # Verify each property has a datetime object for latest_post_date
    for property in searcher.properties:
        assert isinstance(property.latest_post_date, datetime)


def test_property_search_invalid_date():
    """Test handling of invalid date formats"""
    test_data = [{
        'PropertyKey': 1,
        'PropertyName': 'Test Property 1',
        'TotalUnitCount': 100,
        'LatestPostDate': 'Invalid Date Format',
        'OpenWorkOrder_Current': 5,
        'NewWorkOrders_Current': 10,
        'CompletedWorkOrder_Current': 8,
        'CancelledWorkOrder_Current': 2,
        'PendingWorkOrders': 5,
        'PercentageCompletedThisPeriod': 75.5
    }]

    searcher = PropertySearch(test_data)

    # Verify that the invalid property was skipped
    assert len(searcher.properties) == 0
