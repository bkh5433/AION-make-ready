import asyncio
import aiohttp
import time
from datetime import datetime, timedelta
import statistics
import argparse
from typing import List, Dict, Optional
import logging
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import matplotlib.pyplot as plt
import json
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestScenario(Enum):
    CACHE_REFRESH = "cache_refresh"
    DATA_FETCH = "data_fetch"
    SEARCH = "search"
    REPORT_GENERATION = "report_generation"
    SSO_AUTH = "sso_auth"
    IMPORT_WINDOW = "import_window"


@dataclass
class ReportConfig:
    """Configuration for report generation tests"""
    property_keys: List[str]
    max_properties_per_request: int = 2
    min_delay_between_requests: float = 2.0  # seconds
    timeout: float = 60.0  # seconds for longer-running report generation


@dataclass
class TestConfig:
    scenario: TestScenario
    endpoint: str
    method: str = "GET"
    payload: Optional[Dict] = None
    expected_status: int = 200
    validate_response: bool = True
    check_staleness: bool = False
    report_config: Optional[ReportConfig] = None
    timeout: float = 30.0  # default timeout

class RequestQueue:
    def __init__(self, max_concurrent=20):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.queue = asyncio.Queue()
        self.active_requests = 0
        self.total_processed = 0
        self.processing = False
        self.error_count = 0
        self.success_count = 0
        self.response_times = []

    async def add_request(self, request_func):
        """Add a request to the queue"""
        await self.queue.put(request_func)
        if not self.processing:
            self.processing = True
            asyncio.create_task(self._process_queue())

    async def _process_queue(self):
        """Process requests from the queue with enhanced error handling"""
        try:
            while not self.queue.empty():
                async with self.semaphore:
                    self.active_requests += 1
                    request_func = await self.queue.get()
                    start_time = time.time()
                    try:
                        result = await request_func()
                        self.success_count += 1
                        self.total_processed += 1
                    except Exception as e:
                        self.error_count += 1
                        logger.error(f"Request error: {str(e)}")
                    finally:
                        self.active_requests -= 1
                        self.queue.task_done()
                        self.response_times.append(time.time() - start_time)
        finally:
            self.processing = False

    @property
    def stats(self):
        return {
            'queue_size': self.queue.qsize(),
            'active_requests': self.active_requests,
            'total_processed': self.total_processed,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'avg_response_time': statistics.mean(self.response_times) if self.response_times else 0,
            'p95_response_time': statistics.quantiles(self.response_times, n=20)[18] if len(
                self.response_times) >= 20 else None
        }


class SpikeConfig:
    """Configuration for spike testing"""

    def __init__(self,
                 initial_users: int = 10,
                 peak_users: int = 100,
                 ramp_up_time: float = 5.0,  # seconds
                 hold_time: float = 30.0,  # seconds
                 ramp_down_time: float = 5.0  # seconds
                 ):
        self.initial_users = initial_users
        self.peak_users = peak_users
        self.ramp_up_time = ramp_up_time
        self.hold_time = hold_time
        self.ramp_down_time = ramp_down_time

class APILoadTester:
    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url
        self.results: List[Dict] = []
        self.session = None
        self.request_queue = RequestQueue(max_concurrent=20)
        self.semaphore = asyncio.Semaphore(20)

        # Sample property keys for testing - you should replace these with actual property keys
        self.test_property_keys = [
            "80", "131", "113", "62",
            "125", "81", "82", "64"
        ]

        self.scenarios = {
            TestScenario.CACHE_REFRESH: TestConfig(
                scenario=TestScenario.CACHE_REFRESH,
                endpoint="/api/refresh",
                method="POST",
                check_staleness=True
            ),
            TestScenario.DATA_FETCH: TestConfig(
                scenario=TestScenario.DATA_FETCH,
                endpoint="/api/data"
            ),
            TestScenario.SEARCH: TestConfig(
                scenario=TestScenario.SEARCH,
                endpoint="/api/properties/search"
            ),
            TestScenario.REPORT_GENERATION: TestConfig(
                scenario=TestScenario.REPORT_GENERATION,
                endpoint="/api/reports/generate",
                method="POST",
                report_config=ReportConfig(
                    property_keys=self.test_property_keys,
                    max_properties_per_request=2,
                    min_delay_between_requests=2.0,
                    timeout=60.0
                ),
                timeout=60.0
            ),
            TestScenario.SSO_AUTH: TestConfig(
                scenario=TestScenario.SSO_AUTH,
                endpoint="/api/auth/microsoft/login"
            ),
            TestScenario.IMPORT_WINDOW: TestConfig(
                scenario=TestScenario.IMPORT_WINDOW,
                endpoint="/api/import-window/status"
            )
        }

        # Add spike testing configuration
        self.spike_metrics = {
            'concurrent_users': [],
            'response_times': [],
            'error_rates': [],
            'timestamps': []
        }

    async def initialize_session(self):
        """Initialize aiohttp session with retry capability"""
        if not self.session:
            # Default timeout for most requests
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)

    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def get_session_with_timeout(self, timeout: float) -> aiohttp.ClientSession:
        """Get a session with specific timeout"""
        return aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout))

    async def validate_response(self, response: aiohttp.ClientResponse, config: TestConfig) -> bool:
        """Validate response based on test configuration"""
        if not config.validate_response:
            return True

        try:
            data = await response.json()

            # Basic validation
            if response.status != config.expected_status:
                return False

            # Scenario-specific validation
            if config.scenario == TestScenario.CACHE_REFRESH:
                return data.get('status') == 'success'
            elif config.scenario == TestScenario.DATA_FETCH:
                return isinstance(data.get('data'), list)
            elif config.scenario == TestScenario.SEARCH:
                return 'data' in data and isinstance(data['data'], list)
            elif config.scenario == TestScenario.IMPORT_WINDOW:
                return 'in_import_window' in data

            return True
        except Exception as e:
            logger.error(f"Response validation error: {str(e)}")
            return False

    async def make_request(self, config: TestConfig) -> Dict:
        """Make a single request with enhanced error handling and validation"""
        if not self.session:
            await self.initialize_session()

        start_time = time.time()
        result = {
            'timestamp': datetime.now(),
            'endpoint': config.endpoint,
            'scenario': config.scenario.value,
            'queued_at': start_time,
            'status_code': None
        }

        try:
            async with self.semaphore:
                # Use specific session for report generation
                if config.scenario == TestScenario.REPORT_GENERATION:
                    session = await self.get_session_with_timeout(config.timeout)
                else:
                    session = self.session

                try:
                    method = getattr(session, config.method.lower())

                    # Prepare payload for report generation
                    payload = None
                    if config.scenario == TestScenario.REPORT_GENERATION:
                        report_config = config.report_config
                        if not report_config:
                            raise ValueError("Report configuration missing")

                        # Get a subset of property keys for this request
                        start_idx = result.get('request_number', 0) % len(report_config.property_keys)
                        end_idx = min(start_idx + report_config.max_properties_per_request,
                                      len(report_config.property_keys))
                        property_keys = report_config.property_keys[start_idx:end_idx]

                        payload = {"properties": property_keys}
                    else:
                        payload = config.payload

                    async with method(
                            f"{self.base_url}{config.endpoint}",
                            headers=getattr(self, 'headers', {}),
                            json=payload if config.method in ['POST', 'PUT'] else None
                    ) as response:
                        try:
                            data = await response.json()
                        except aiohttp.ContentTypeError:
                            # Handle text response
                            text_data = await response.text()
                            data = {'text_response': text_data}

                        is_valid = await self.validate_response(response, config)

                        result.update({
                            'status_code': response.status,
                            'success': is_valid,
                            'duration': time.time() - start_time,
                            'queue_time': time.time() - result['queued_at'],
                            'data_staleness': data.get('is_stale') if config.check_staleness else None,
                            'payload': payload
                        })

                        # Add specific metrics for report generation
                        if config.scenario == TestScenario.REPORT_GENERATION:
                            result.update({
                                'property_count': len(property_keys),
                                'generation_time': data.get('generation_time'),
                                'report_status': data.get('status')
                            })

                finally:
                    if session != self.session:
                        await session.close()

        except Exception as e:
            result.update({
                'success': False,
                'error': str(e),
                'duration': time.time() - start_time,
                'status_code': 500
            })
            logger.error(f"Request error: {e}")

        self.results.append(result)
        return result

    async def run_scenario(self, scenario: TestScenario, num_requests: int, delay: float = 0):
        """Run a specific test scenario with enhanced report generation handling"""
        config = self.scenarios[scenario]
        logger.info(f"Running scenario: {scenario.value} with {num_requests} requests")
        
        tasks = []
        for i in range(num_requests):
            if scenario == TestScenario.REPORT_GENERATION:
                # Add delay between report generation requests
                if i > 0:
                    delay = max(delay, config.report_config.min_delay_between_requests)
            
            if delay:
                await asyncio.sleep(delay)

            # Create a request with request number
            request_config = config
            if scenario == TestScenario.REPORT_GENERATION:
                request_config = TestConfig(**config.__dict__)
                request_config.request_number = i

            # Await the request directly
            tasks.append(await self.make_request(request_config))

        return tasks

    async def run_mixed_scenarios(self, scenario_weights: Dict[TestScenario, float], total_requests: int,
                                  delay: float = 0):
        """Run multiple scenarios with specified weights"""
        tasks = []
        for scenario, weight in scenario_weights.items():
            num_requests = int(total_requests * weight)
            if num_requests > 0:
                tasks.extend([self.make_request(self.scenarios[scenario]) for _ in range(num_requests)])

        random.shuffle(tasks)
        for task in tasks:
            if delay:
                await asyncio.sleep(delay)
            await self.request_queue.add_request(lambda t=task: t)

        await self.request_queue.queue.join()

    def analyze_results(self) -> Dict:
        """Analyze test results with enhanced metrics"""
        if not self.results:
            return {}

        # Group results by scenario
        scenario_results = {}
        for result in self.results:
            scenario = result['scenario']
            if scenario not in scenario_results:
                scenario_results[scenario] = []
            scenario_results[scenario].append(result)

        analysis = {
            'overall': self._analyze_scenario_group(self.results),
            'scenarios': {
                scenario: self._analyze_scenario_group(results)
                for scenario, results in scenario_results.items()
            }
        }

        # Add cache-specific metrics
        cache_results = [r for r in self.results if 'cache_stats' in r]
        if cache_results:
            analysis['cache_metrics'] = self._analyze_cache_metrics(cache_results)

        return analysis

    def _analyze_scenario_group(self, results: List[Dict]) -> Dict:
        """Analyze metrics for a group of results with enhanced report generation metrics"""
        base_metrics = super()._analyze_scenario_group(results)

        # Add report generation specific metrics
        report_results = [r for r in results if r.get('scenario') == TestScenario.REPORT_GENERATION.value]
        if report_results:
            base_metrics.update({
                'report_metrics': {
                    'avg_generation_time': statistics.mean([
                        r.get('generation_time', 0) for r in report_results
                        if r.get('generation_time')
                    ]),
                    'avg_property_count': statistics.mean([
                        r.get('property_count', 0) for r in report_results
                    ]),
                    'status_breakdown': self._count_report_statuses(report_results)
                }
            })

        return base_metrics

    def _count_report_statuses(self, report_results: List[Dict]) -> Dict:
        """Count different report generation statuses"""
        status_counts = {}
        for result in report_results:
            status = result.get('report_status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        return status_counts

    def _analyze_cache_metrics(self, cache_results: List[Dict]) -> Dict:
        """Analyze cache-specific metrics"""
        return {
            'staleness_rate': len([r for r in cache_results if r.get('data_staleness')]) / len(cache_results) * 100,
            'avg_refresh_age': statistics.mean([
                r['cache_stats']['refresh_age'] for r in cache_results
                if 'cache_stats' in r and 'refresh_age' in r['cache_stats']
            ]) if any('cache_stats' in r and 'refresh_age' in r['cache_stats'] for r in cache_results) else None,
            'import_window_detections': len([
                r for r in cache_results
                if r.get('import_window_active')
            ])
        }

    def _analyze_errors(self, failed_requests: List[Dict]) -> Dict:
        """Analyze error patterns with enhanced categorization"""
        error_counts = {}
        for req in failed_requests:
            error_type = req.get('error', 'Unknown error')
            if isinstance(error_type, str):
                if 'timeout' in error_type.lower():
                    error_type = 'Timeout'
                elif 'connection' in error_type.lower():
                    error_type = 'Connection Error'
                elif 'validation' in error_type.lower():
                    error_type = 'Validation Error'
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        return error_counts

    def plot_results(self, filename: str = 'load_test_results.png'):
        """Generate comprehensive visualization of test results with async operation insights"""
        if not self.results:
            return

        df = pd.DataFrame(self.results)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        # Add scenario-based analysis
        df['scenario'] = df['scenario'].fillna('unknown')
        
        # Create figure with subplots
        fig = plt.figure(figsize=(15, 12))
        gs = plt.GridSpec(3, 2, figure=fig)

        # 1. Response Time Over Time by Scenario
        ax1 = fig.add_subplot(gs[0, :])
        for scenario in df['scenario'].unique():
            scenario_df = df[df['scenario'] == scenario]
            ax1.scatter(scenario_df['elapsed_seconds'], scenario_df['duration'],
                        alpha=0.3, label=scenario)
        ax1.set_title('Response Time by Scenario')
        ax1.set_xlabel('Elapsed Time (seconds)')
        ax1.set_ylabel('Response Time (seconds)')
        ax1.grid(True)
        ax1.legend()

        # 2. Response Time Distribution by Scenario
        ax2 = fig.add_subplot(gs[1, 0])
        df.boxplot(column='duration', by='scenario', ax=ax2)
        ax2.set_title('Response Time Distribution by Scenario')
        ax2.set_xlabel('Scenario')
        ax2.set_ylabel('Response Time (seconds)')
        plt.xticks(rotation=45)

        # 3. Success Rate by Scenario
        ax3 = fig.add_subplot(gs[1, 1])
        success_rates = df.groupby('scenario')['success'].mean() * 100
        success_rates.plot(kind='bar', ax=ax3)
        ax3.set_title('Success Rate by Scenario')
        ax3.set_xlabel('Scenario')
        ax3.set_ylabel('Success Rate (%)')
        plt.xticks(rotation=45)

        # 4. Cache Performance (if available)
        ax4 = fig.add_subplot(gs[2, 0])
        if 'data_staleness' in df.columns:
            staleness_rates = df.groupby('elapsed_seconds')['data_staleness'].mean().rolling(window=10).mean()
            ax4.plot(staleness_rates.index, staleness_rates.values, label='Cache Staleness')
            ax4.set_title('Cache Performance Over Time')
            ax4.set_xlabel('Elapsed Time (seconds)')
            ax4.set_ylabel('Staleness Rate')
            ax4.grid(True)

        # 5. Summary Statistics
        ax5 = fig.add_subplot(gs[2, 1])
        ax5.axis('off')

        stats_text = [
            f"Total Requests: {len(df)}",
            f"Overall Success Rate: {(df['success'].mean() * 100):.1f}%",
            f"Mean Response Time: {df['duration'].mean():.3f}s",
            f"95th Percentile: {df['duration'].quantile(0.95):.3f}s",
            f"Total Test Duration: {df['elapsed_seconds'].max():.1f}s",
            f"Avg Throughput: {len(df) / df['elapsed_seconds'].max():.1f} req/s"
        ]

        # Add cache-specific stats if available
        if 'data_staleness' in df.columns:
            cache_stats = [
                f"Cache Staleness Rate: {(df['data_staleness'].mean() * 100):.1f}%",
                f"Import Window Detections: {df['import_window_active'].sum() if 'import_window_active' in df.columns else 0}"
            ]
            stats_text.extend(cache_stats)

        ax5.text(0.05, 0.95, '\n'.join(stats_text),
                 transform=ax5.transAxes,
                 fontsize=10,
                 verticalalignment='top',
                 fontfamily='monospace')
        ax5.set_title('Test Summary Statistics')

        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()

        # Generate additional performance insights
        self._generate_performance_report(df, filename.replace('.png', '_report.txt'))

    def _generate_performance_report(self, df: pd.DataFrame, filename: str):
        """Generate a detailed performance report"""

        # Calculate time-based segments
        total_duration = df['elapsed_seconds'].max()
        segment_size = total_duration / 4  # Split into quarters

        segments = []
        for i in range(4):
            start = i * segment_size
            end = (i + 1) * segment_size
            segment_df = df[(df['elapsed_seconds'] >= start) & (df['elapsed_seconds'] < end)]

            if not segment_df.empty:
                segments.append({
                    'segment': f"Q{i + 1}",
                    'avg_response': segment_df['duration'].mean(),
                    'success_rate': segment_df['success'].mean() * 100,
                    'requests': len(segment_df),
                    'throughput': len(segment_df) / segment_size
                })

        # Generate report
        with open(filename, 'w') as f:
            f.write("=== Load Test Performance Report ===\n\n")

            # Overall Statistics
            f.write("Overall Performance:\n")
            f.write(f"Total Requests: {len(df)}\n")
            f.write(f"Total Duration: {total_duration:.1f} seconds\n")
            f.write(f"Average Throughput: {len(df) / total_duration:.1f} requests/second\n")
            f.write(f"Success Rate: {df['success'].mean() * 100:.1f}%\n\n")

            # Response Time Statistics
            f.write("Response Time Statistics:\n")
            f.write(f"Mean: {df['duration'].mean():.3f}s\n")
            f.write(f"Median: {df['duration'].median():.3f}s\n")
            f.write(f"95th Percentile: {df['duration'].quantile(0.95):.3f}s\n")
            f.write(f"99th Percentile: {df['duration'].quantile(0.99):.3f}s\n")
            f.write(f"Standard Deviation: {df['duration'].std():.3f}s\n\n")

            # Performance by Time Segment
            f.write("Performance by Time Segment:\n")
            for segment in segments:
                f.write(f"\n{segment['segment']}:\n")
                f.write(f"  Requests: {segment['requests']}\n")
                f.write(f"  Avg Response Time: {segment['avg_response']:.3f}s\n")
                f.write(f"  Success Rate: {segment['success_rate']:.1f}%\n")
                f.write(f"  Throughput: {segment['throughput']:.1f} req/s\n")

            # Status Code Analysis
            f.write("\nStatus Code Distribution:\n")
            status_counts = df['status_code'].value_counts()
            for status, count in status_counts.items():
                f.write(f"{status}: {count} ({count / len(df) * 100:.1f}%)\n")

            # Performance Thresholds Analysis
            slow_threshold = df['duration'].quantile(0.95)
            f.write(f"\nSlow Requests (>{slow_threshold:.3f}s):\n")
            slow_requests = df[df['duration'] > slow_threshold]
            if not slow_requests.empty:
                for _, req in slow_requests.iterrows():
                    f.write(f"  {req['timestamp'].strftime('%H:%M:%S')}: {req['duration']:.3f}s\n")

            # Recommendations
            f.write("\nRecommendations:\n")
            if df['duration'].std() > df['duration'].mean() * 0.5:
                f.write(
                    "- High response time variability detected. Consider investigating caching or database optimization.\n")
            if df['success'].mean() < 0.95:
                f.write("- Success rate below 95%. Review error patterns and error handling.\n")
            if df['duration'].quantile(0.95) > 1.0:
                f.write("- 95th percentile response time exceeds 1 second. Consider performance optimization.\n")

    async def run_spike_test(self, scenario: TestScenario, spike_config: SpikeConfig):
        """Run a spike test to determine server capacity"""
        logger.info(f"Starting spike test for scenario: {scenario.value}")
        logger.info(f"Peak users: {spike_config.peak_users}, Ramp up time: {spike_config.ramp_up_time}s")

        start_time = time.time()
        results = []

        # Calculate user increments for ramp up
        user_increment = (spike_config.peak_users - spike_config.initial_users) / spike_config.ramp_up_time
        current_users = spike_config.initial_users

        # Ramp up phase
        logger.info("Starting ramp up phase...")
        while current_users < spike_config.peak_users:
            concurrent_tasks = []
            for _ in range(int(current_users)):
                concurrent_tasks.append(self.make_request(self.scenarios[scenario]))

            batch_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            results.extend([r for r in batch_results if not isinstance(r, Exception)])

            # Record metrics
            self._record_spike_metrics(current_users, batch_results)

            current_users += user_increment
            await asyncio.sleep(1)  # 1-second intervals

        # Hold at peak
        logger.info("Holding at peak load...")
        hold_start = time.time()
        while time.time() - hold_start < spike_config.hold_time:
            concurrent_tasks = []
            for _ in range(spike_config.peak_users):
                concurrent_tasks.append(self.make_request(self.scenarios[scenario]))

            batch_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            results.extend([r for r in batch_results if not isinstance(r, Exception)])

            # Record metrics
            self._record_spike_metrics(spike_config.peak_users, batch_results)

            await asyncio.sleep(1)

        # Ramp down phase
        logger.info("Starting ramp down phase...")
        while current_users > spike_config.initial_users:
            concurrent_tasks = []
            for _ in range(int(current_users)):
                concurrent_tasks.append(self.make_request(self.scenarios[scenario]))

            batch_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            results.extend([r for r in batch_results if not isinstance(r, Exception)])

            # Record metrics
            self._record_spike_metrics(current_users, batch_results)

            current_users -= user_increment
            await asyncio.sleep(1)

        return self._analyze_spike_results(results, spike_config)

    def _record_spike_metrics(self, current_users: int, batch_results: List[Dict]):
        """Record metrics during spike test"""
        timestamp = time.time()
        successful_requests = [r for r in batch_results if not isinstance(r, Exception) and r.get('success', False)]
        error_rate = 1 - (len(successful_requests) / len(batch_results)) if batch_results else 1

        response_times = [r.get('duration', 0) for r in batch_results if not isinstance(r, Exception)]
        avg_response_time = statistics.mean(response_times) if response_times else 0

        self.spike_metrics['concurrent_users'].append(current_users)
        self.spike_metrics['response_times'].append(avg_response_time)
        self.spike_metrics['error_rates'].append(error_rate)
        self.spike_metrics['timestamps'].append(timestamp)

    def _analyze_spike_results(self, results: List[Dict], spike_config: SpikeConfig) -> Dict:
        """Analyze results from spike test"""
        if not results:
            return {}

        # Calculate key metrics
        peak_rps = max([
            len([r for r in results
                 if abs(r['timestamp'].timestamp() - t) < 1])
            for t in self.spike_metrics['timestamps']
        ])

        saturation_point = None
        for users, error_rate in zip(self.spike_metrics['concurrent_users'], self.spike_metrics['error_rates']):
            if error_rate > 0.1:  # Consider 10% error rate as saturation
                saturation_point = users
                break

        response_times = [r['duration'] for r in results]

        analysis = {
            'peak_rps': peak_rps,
            'saturation_point': saturation_point,
            'peak_concurrent_users': spike_config.peak_users,
            'response_time_stats': {
                'min': min(response_times),
                'max': max(response_times),
                'avg': statistics.mean(response_times),
                'p95': statistics.quantiles(response_times, n=20)[18],
                'p99': statistics.quantiles(response_times, n=100)[98]
            },
            'error_rate_stats': {
                'min': min(self.spike_metrics['error_rates']),
                'max': max(self.spike_metrics['error_rates']),
                'avg': statistics.mean(self.spike_metrics['error_rates'])
            }
        }

        # Generate spike test visualization
        self._plot_spike_results(f"spike_test_{int(time.time())}.png")

        return analysis

    def _plot_spike_results(self, filename: str):
        """Generate visualization for spike test results"""
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 12))

        # Normalize timestamps to seconds from start
        start_time = min(self.spike_metrics['timestamps'])
        elapsed_times = [t - start_time for t in self.spike_metrics['timestamps']]

        # Plot concurrent users
        ax1.plot(elapsed_times, self.spike_metrics['concurrent_users'])
        ax1.set_title('Concurrent Users Over Time')
        ax1.set_xlabel('Time (seconds)')
        ax1.set_ylabel('Users')
        ax1.grid(True)

        # Plot response times
        ax2.plot(elapsed_times, self.spike_metrics['response_times'])
        ax2.set_title('Average Response Time Over Time')
        ax2.set_xlabel('Time (seconds)')
        ax2.set_ylabel('Response Time (seconds)')
        ax2.grid(True)

        # Plot error rates
        ax3.plot(elapsed_times, self.spike_metrics['error_rates'])
        ax3.set_title('Error Rate Over Time')
        ax3.set_xlabel('Time (seconds)')
        ax3.set_ylabel('Error Rate')
        ax3.grid(True)

        plt.tight_layout()
        plt.savefig(filename)
        plt.close()


async def run_load_test(
        scenarios: List[TestScenario],
        num_requests: int,
        concurrent_users: int,
        delay: float = 0,
        token: str = None,
        scenario_weights: Optional[Dict[TestScenario, float]] = None,
        spike_test: bool = False,
        spike_config: Optional[SpikeConfig] = None
):
    """Run a complete load test with multiple scenarios and optional spike testing"""
    tester = APILoadTester()
    tester.headers = {'Authorization': f'Bearer {token}'} if token else {}

    try:
        if spike_test and spike_config:
            results = []
            for scenario in scenarios:
                scenario_results = await tester.run_spike_test(scenario, spike_config)
                results.append({
                    'scenario': scenario.value,
                    'spike_results': scenario_results
                })
            return results
        else:
            # ... existing normal test logic ...
            pass
    finally:
        if tester.session:
            await tester.close_session()

def main():
    parser = argparse.ArgumentParser(description='Enhanced API Load Testing Tool')
    parser.add_argument('--scenarios', nargs='+', default=['search'],
                        choices=[s.value for s in TestScenario],
                        help='Scenarios to test')
    parser.add_argument('--requests', type=int, default=100,
                        help='Total number of requests to make')
    parser.add_argument('--users', type=int, default=10,
                        help='Number of concurrent users')
    parser.add_argument('--delay', type=float, default=0.1,
                        help='Delay between requests (seconds)')
    parser.add_argument('--token', type=str, required=True,
                        help='Authentication token')
    parser.add_argument('--weighted', action='store_true',
                        help='Use weighted scenario distribution')
    parser.add_argument('--property-keys', nargs='+',
                        help='Property keys to use for report generation testing')
    parser.add_argument('--max-properties-per-report', type=int, default=2,
                        help='Maximum number of properties per report generation request')
    parser.add_argument('--spike-test', action='store_true',
                        help='Run spike test instead of normal load test')
    parser.add_argument('--peak-users', type=int, default=100,
                        help='Peak number of concurrent users for spike test')
    parser.add_argument('--ramp-up-time', type=float, default=5.0,
                        help='Time in seconds to ramp up to peak users')
    parser.add_argument('--hold-time', type=float, default=30.0,
                        help='Time in seconds to hold at peak users')
    parser.add_argument('--ramp-down-time', type=float, default=5.0,
                        help='Time in seconds to ramp down from peak users')

    args = parser.parse_args()

    # Convert scenario strings to enum values
    scenarios = [TestScenario(s) for s in args.scenarios]

    # Update property keys if provided
    if args.property_keys and TestScenario.REPORT_GENERATION in scenarios:
        for scenario in scenarios:
            if scenario == TestScenario.REPORT_GENERATION:
                scenario.report_config.property_keys = args.property_keys
                scenario.report_config.max_properties_per_request = args.max_properties_per_report

    # Create scenario weights if specified
    scenario_weights = None
    if args.weighted:
        total_scenarios = len(scenarios)
        scenario_weights = {scenario: 1.0 / total_scenarios for scenario in scenarios}

    # Create spike config if spike test is requested
    spike_config = None
    if args.spike_test:
        spike_config = SpikeConfig(
            initial_users=args.users,
            peak_users=args.peak_users,
            ramp_up_time=args.ramp_up_time,
            hold_time=args.hold_time,
            ramp_down_time=args.ramp_down_time
        )

    asyncio.run(run_load_test(
        scenarios=scenarios,
        num_requests=args.requests,
        concurrent_users=args.users,
        delay=args.delay,
        token=args.token,
        scenario_weights=args.weighted and {s: 1.0 / len(scenarios) for s in scenarios},
        spike_test=args.spike_test,
        spike_config=spike_config
    ))

if __name__ == '__main__':
    main()
