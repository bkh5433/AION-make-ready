import asyncio
import aiohttp
import time
from datetime import datetime
import statistics
import argparse
from typing import List, Dict
import logging
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RequestQueue:
    def __init__(self, max_concurrent=20):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.queue = asyncio.Queue()
        self.active_requests = 0
        self.total_processed = 0
        self.processing = False

    async def add_request(self, request_func):
        """Add a request to the queue"""
        await self.queue.put(request_func)
        if not self.processing:
            self.processing = True
            asyncio.create_task(self._process_queue())

    async def _process_queue(self):
        """Process requests from the queue"""
        try:
            while not self.queue.empty():
                async with self.semaphore:
                    self.active_requests += 1
                    request_func = await self.queue.get()
                    try:
                        await request_func()
                        self.total_processed += 1
                    finally:
                        self.active_requests -= 1
                        self.queue.task_done()
        finally:
            self.processing = False

    @property
    def stats(self):
        return {
            'queue_size': self.queue.qsize(),
            'active_requests': self.active_requests,
            'total_processed': self.total_processed
        }

class APILoadTester:
    def __init__(self, base_url: str = "http://127.0.0.1:5000"):
        self.base_url = base_url
        self.results: List[Dict] = []
        self.session = None
        self.request_queue = RequestQueue(max_concurrent=20)
        self.semaphore = asyncio.Semaphore(20)

    async def initialize_session(self):
        """Initialize aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def make_request(self, endpoint: str) -> Dict:
        """Make a single request with queue management"""
        if not self.session:
            await self.initialize_session()

        start_time = time.time()
        result = {
            'timestamp': datetime.now(),
            'endpoint': endpoint,
            'queued_at': start_time,
            'status_code': None
        }

        try:
            async with self.semaphore:
                async with self.session.get(
                        f"{self.base_url}{endpoint}",
                        headers=getattr(self, 'headers', {})
                ) as response:
                    await response.json()
                    result.update({
                        'status_code': response.status,
                        'success': 200 <= response.status < 300,
                        'duration': time.time() - start_time,
                        'queue_time': time.time() - result['queued_at']
                    })
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

    async def run_concurrent_requests(self, endpoint: str, num_requests: int, delay: float = 0):
        """Run multiple requests concurrently"""
        tasks = []
        for _ in range(num_requests):
            if delay:
                await asyncio.sleep(delay)
            tasks.append(self.make_request(endpoint))

        return await asyncio.gather(*tasks)

    def analyze_results(self) -> Dict:
        """Analyze test results"""
        if not self.results:
            return {}

        durations = [r['duration'] for r in self.results]
        successful_requests = [r for r in self.results if r['success']]
        failed_requests = [r for r in self.results if not r['success']]

        analysis = {
            'total_requests': len(self.results),
            'successful_requests': len(successful_requests),
            'failed_requests': len(failed_requests),
            'success_rate': len(successful_requests) / len(self.results) * 100,
            'min_duration': min(durations),
            'max_duration': max(durations),
            'avg_duration': statistics.mean(durations),
            'median_duration': statistics.median(durations),
            'p95_duration': statistics.quantiles(durations, n=20)[18],  # 95th percentile
            'total_duration': max(r['timestamp'].timestamp() for r in self.results) -
                              min(r['timestamp'].timestamp() for r in self.results)
        }

        if failed_requests:
            analysis['error_breakdown'] = self._analyze_errors(failed_requests)

        return analysis

    def _analyze_errors(self, failed_requests: List[Dict]) -> Dict:
        """Analyze error patterns"""
        error_counts = {}
        for req in failed_requests:
            error_type = req.get('error', 'Unknown error')
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        return error_counts

    def plot_results(self, filename: str = 'load_test_results.png'):
        """Generate comprehensive visualization of test results"""
        if not self.results:
            return

        df = pd.DataFrame(self.results)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        # Ensure status_code exists and has a valid value
        df['status_code'] = df['status_code'].fillna(0).astype(int)

        # Calculate rolling averages and other metrics
        df['rolling_avg'] = df['duration'].rolling(window=10).mean()
        df['rolling_std'] = df['duration'].rolling(window=10).std()

        # Create time-based metrics
        df['elapsed_seconds'] = (df['timestamp'] - df['timestamp'].min()).dt.total_seconds()
        df['requests_per_second'] = 1 / df['duration']

        # Create figure with subplots
        fig = plt.figure(figsize=(15, 12))
        gs = plt.GridSpec(3, 2, figure=fig)

        # 1. Response Time Over Time with Rolling Average
        ax1 = fig.add_subplot(gs[0, :])
        ax1.plot(df['elapsed_seconds'], df['duration'], 'b.', alpha=0.3, label='Individual Requests')
        ax1.plot(df['elapsed_seconds'], df['rolling_avg'], 'r-', linewidth=2, label='Rolling Average')
        ax1.fill_between(df['elapsed_seconds'],
                         df['rolling_avg'] - df['rolling_std'],
                         df['rolling_avg'] + df['rolling_std'],
                         color='red', alpha=0.1, label='±1 Std Dev')
        ax1.set_title('Response Time Over Time')
        ax1.set_xlabel('Elapsed Time (seconds)')
        ax1.set_ylabel('Response Time (seconds)')
        ax1.grid(True)
        ax1.legend()

        # 2. Response Time Distribution
        ax2 = fig.add_subplot(gs[1, 0])
        df['duration'].hist(ax=ax2, bins=30, edgecolor='black')
        ax2.axvline(df['duration'].mean(), color='r', linestyle='--', label='Mean')
        ax2.axvline(df['duration'].median(), color='g', linestyle='--', label='Median')
        ax2.set_title('Response Time Distribution')
        ax2.set_xlabel('Response Time (seconds)')
        ax2.set_ylabel('Count')
        ax2.legend()

        # 3. Requests Per Second Over Time
        ax3 = fig.add_subplot(gs[1, 1])
        rolling_rps = df['requests_per_second'].rolling(window=10).mean()
        ax3.plot(df['elapsed_seconds'], rolling_rps, 'g-', label='Rolling Average')
        ax3.set_title('Throughput (Requests/Second)')
        ax3.set_xlabel('Elapsed Time (seconds)')
        ax3.set_ylabel('Requests per Second')
        ax3.grid(True)
        ax3.legend()

        # 4. Status Code Distribution
        ax4 = fig.add_subplot(gs[2, 0])
        status_counts = df['status_code'].value_counts()
        status_colors = ['green' if 200 <= code < 300 else 'red' for code in status_counts.index]
        status_counts.plot(kind='bar', ax=ax4, color=status_colors)
        ax4.set_title('Response Status Distribution')
        ax4.set_xlabel('Status Code')
        ax4.set_ylabel('Count')

        # 5. Summary Statistics
        ax5 = fig.add_subplot(gs[2, 1])
        ax5.axis('off')

        stats_text = [
            f"Total Requests: {len(df)}",
            f"Success Rate: {(df['success'].mean() * 100):.1f}%",
            f"Mean Response Time: {df['duration'].mean():.3f}s",
            f"Median Response Time: {df['duration'].median():.3f}s",
            f"95th Percentile: {df['duration'].quantile(0.95):.3f}s",
            f"Min Response Time: {df['duration'].min():.3f}s",
            f"Max Response Time: {df['duration'].max():.3f}s",
            f"Std Dev: {df['duration'].std():.3f}s",
            f"Total Test Duration: {df['elapsed_seconds'].max():.1f}s",
            f"Avg Throughput: {len(df) / df['elapsed_seconds'].max():.1f} req/s"
        ]

        ax5.text(0.05, 0.95, '\n'.join(stats_text),
                 transform=ax5.transAxes,
                 fontsize=10,
                 verticalalignment='top',
                 fontfamily='monospace')
        ax5.set_title('Test Summary Statistics')

        # Adjust layout and save
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


async def run_load_test(endpoint: str, num_requests: int, concurrent_users: int, delay: float = 0, token: str = None):
    """Run a complete load test"""
    tester = APILoadTester()
    tester.headers = {'Authorization': f'Bearer {token}'} if token else {}

    logger.info(f"Starting load test with {num_requests} total requests, "
                f"{concurrent_users} concurrent users")

    # Split requests into batches for concurrent users
    requests_per_user = num_requests // concurrent_users
    remaining_requests = num_requests % concurrent_users

    tasks = []
    for i in range(concurrent_users):
        user_requests = requests_per_user + (1 if i < remaining_requests else 0)
        tasks.append(tester.run_concurrent_requests(endpoint, user_requests, delay))

    start_time = time.time()

    try:
        # Run all user simulations concurrently
        await asyncio.gather(*tasks)

        # Analyze and report results
        results = tester.analyze_results()
        logger.info("\nTest Results:")
        logger.info(f"Total Requests: {results['total_requests']}")
        logger.info(f"Success Rate: {results['success_rate']:.2f}%")
        logger.info(f"Average Response Time: {results['avg_duration']:.3f}s")
        logger.info(f"95th Percentile Response Time: {results['p95_duration']:.3f}s")
        logger.info(f"Total Test Duration: {results['total_duration']:.2f}s")

        # Generate visualization
        tester.plot_results()

    finally:
        await tester.close_session()

    return results


def main():
    parser = argparse.ArgumentParser(description='API Load Testing Tool')
    parser.add_argument('--endpoint', default='/api/properties/search',
                        help='API endpoint to test')
    parser.add_argument('--requests', type=int, default=100,
                        help='Total number of requests to make')
    parser.add_argument('--users', type=int, default=10,
                        help='Number of concurrent users')
    parser.add_argument('--delay', type=float, default=1,
                        help='Delay between requests (seconds)')
    parser.add_argument('--token', type=str, required=True,
                        help='Authentication token')

    args = parser.parse_args()

    asyncio.run(run_load_test(
        args.endpoint,
        args.requests,
        args.users,
        args.delay,
        args.token
    ))


if __name__ == '__main__':
    main()
