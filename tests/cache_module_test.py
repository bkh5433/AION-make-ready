import pytest
import asyncio
import threading
import time
from datetime import datetime, timedelta
from cache_module import CacheConfig, ConcurrentSQLCache


# Mock data generator
def generate_mock_data(size=10):
    return [
        {
            'PropertyKey': i,
            'PropertyName': f'Property {i}',
            'TotalUnitCount': i * 10,
            'ActualOpenWorkOrders_Current': i
        } for i in range(size)
    ]


# Mock fetch function
async def mock_fetch_success():
    """Simulates successful data fetch"""
    await asyncio.sleep(0.1)  # Simulate database query
    return generate_mock_data()


async def mock_fetch_slow():
    """Simulates slow data fetch"""
    await asyncio.sleep(2)
    return generate_mock_data()


async def mock_fetch_error():
    """Simulates failed data fetch"""
    await asyncio.sleep(0.1)
    raise Exception("Simulated fetch error")


@pytest.fixture
def cache():
    """Create cache instance with test configuration"""
    config = CacheConfig(
        refresh_interval=1,  # 1 second for faster testing
        force_refresh_interval=2,  # 2 seconds
        refresh_timeout=1,  # 1 second timeout
        max_retry_attempts=2,
        retry_delay=1,  # 100ms delay for faster testing
        enable_monitoring=True,
        stale_if_error=True
    )
    return ConcurrentSQLCache(config)


@pytest.mark.asyncio
async def test_initial_cache_state(cache):
    """Test initial cache state"""
    data, is_stale = await cache.get_data()
    assert data is None
    assert is_stale is True

    stats = cache.get_stats()
    assert stats['status']['is_stale'] is True
    assert stats['data']['current_records'] == 0


@pytest.mark.asyncio
async def test_successful_refresh(cache):
    """Test successful cache refresh"""
    # Initial refresh
    await cache.refresh_data(mock_fetch_success)
    data, is_stale = await cache.get_data()

    assert data is not None
    assert len(data) == 10
    assert not is_stale

    stats = cache.get_stats()
    assert stats['performance']['refresh_count'] == 1
    assert stats['performance']['failed_refreshes'] == 0


@pytest.mark.asyncio
async def test_cache_staleness(cache):
    """Test cache staleness detection"""
    # Initial refresh
    await cache.refresh_data(mock_fetch_success)

    # Wait for cache to become stale
    await asyncio.sleep(1.1)

    data, is_stale = await cache.get_data()
    assert is_stale is True
    assert data is not None  # Should still return data even when stale


@pytest.mark.asyncio
async def test_concurrent_refresh(cache):
    """Test concurrent refresh handling"""

    async def concurrent_refresh():
        tasks = [
            cache.refresh_data(mock_fetch_slow) for _ in range(3)
        ]
        await asyncio.gather(*tasks)

    print("Starting concurrent refresh")
    await concurrent_refresh()
    print("Concurrent refresh completed")

    stats = cache.get_stats()
    print("Cache stats:", stats)
    assert stats['performance']['concurrent_refreshes_prevented'] > 0
    assert stats['performance']['refresh_count'] == 1


@pytest.mark.asyncio
async def test_refresh_with_errors(cache):
    """Test error handling during refresh"""
    # Try to refresh with error
    with pytest.raises(Exception):
        await cache.refresh_data(mock_fetch_error)

    stats = cache.get_stats()
    assert stats['performance']['failed_refreshes'] == 1


@pytest.mark.asyncio
async def test_stale_data_serving(cache):
    """Test serving stale data when refresh fails"""
    # Initial successful refresh
    await cache.refresh_data(mock_fetch_success)
    initial_data, _ = await cache.get_data()

    # Wait for cache to become stale
    await asyncio.sleep(1.1)

    # Try refresh with error
    try:
        await cache.refresh_data(mock_fetch_error)
    except:
        pass

    # Should get stale data
    stale_data, is_stale = await cache.get_data()
    assert is_stale is True
    assert stale_data == initial_data


@pytest.mark.asyncio
async def test_force_refresh(cache):
    """Test force refresh behavior"""
    # Initial refresh
    await cache.refresh_data(mock_fetch_success)

    # Wait for force refresh interval
    await asyncio.sleep(2.1)

    assert cache.needs_force_refresh is True

    # Should trigger new refresh
    data, is_stale = await cache.get_data()
    assert cache._refresh_state.is_refreshing is True


def test_real_data_fetch(cache):
    """Integration test with real data fetch"""
    import asyncio
    from app import fetch_make_ready_data

    async def test_fetch():
        await cache.refresh_data(fetch_make_ready_data)
        data, is_stale = await cache.get_data()
        return data, is_stale

    data, is_stale = asyncio.run(test_fetch())

    assert data is not None
    assert isinstance(data, list)
    assert len(data) > 0
    assert 'PropertyKey' in data[0]
    assert 'ActualOpenWorkOrders_Current' in data[0]


def test_concurrent_access():
    """Test concurrent access from multiple threads"""
    config = CacheConfig(
        refresh_interval=1,
        refresh_timeout=1,
        max_retry_attempts=2,
        retry_delay=1
    )
    cache = ConcurrentSQLCache(config)

    def worker():
        async def get_data():
            data, _ = await cache.get_data()
            return data

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            print("Worker started")
            if loop.run_until_complete(get_data()) is None:
                print("Cache miss, refreshing data")
                loop.run_until_complete(cache.refresh_data(mock_fetch_success))
            else:
                print("Cache hit")
        finally:
            loop.close()
            print("Worker finished")

    # Create multiple threads accessing cache
    threads = [threading.Thread(target=worker) for _ in range(5)]

    # Start all threads
    for t in threads:
        t.start()
        print(f"Thread {t.name} started")

    # Wait for all threads to complete
    for t in threads:
        t.join()
        print(f"Thread {t.name} joined")

    stats = cache.get_stats()
    print("Cache stats:", stats)
    assert stats['performance']['concurrent_refreshes_prevented'] > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
