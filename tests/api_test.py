import requests
import json
from typing import Dict, List
import logging
from datetime import datetime
from pathlib import Path
from logger_config import LogConfig

# Initialize logging
log_config = LogConfig()
logger = log_config.get_logger("test_api")


class APITester:
    """Enhanced API testing class with better error handling and logging"""

    def __init__(self, base_url: str = "http://127.0.0.1:5000"):
        self.base_url = base_url
        logger.info(f"Initialized APITester with base URL: {base_url}")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with proper error handling"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        logger.debug(f"Making {method} request to: {url}")

        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()  # Raise exception for bad status codes
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            raise

    def search_properties(self, search_term: str = None) -> Dict:
        """Test the property search endpoint"""
        endpoint = "api/properties/search"
        params = {'q': search_term} if search_term else {}

        logger.info(f"Searching properties with term: {search_term}")
        try:
            response = self._make_request('GET', endpoint, params=params)
            data = response.json()
            logger.info(f"Found {data['count']} properties")

            # Log the first few properties found
            if data['data']:
                for prop in data['data'][:3]:
                    logger.info(f"Property: {prop['property_name']} (Key: {prop['property_key']})")

            return data
        except Exception as e:
            logger.error(f"Property search failed: {str(e)}", exc_info=True)
            raise

    def generate_reports(self, property_keys: List[int]) -> Dict:
        """Test the report generation endpoint with enhanced error handling"""
        endpoint = "api/reports/generate"
        payload = {
            "properties": property_keys,
            # Add any additional parameters needed for report generation
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"Generating reports for properties: {property_keys}")
        try:
            response = self._make_request('POST', endpoint, json=payload)
            data = response.json()

            if data.get('success', False):
                output_dir = data.get('output', {}).get('directory')
                logger.info(f"Reports generated successfully in {output_dir}")

                # Verify the output files exist
                if output_dir:
                    output_path = Path(output_dir)
                    if output_path.exists():
                        files = list(output_path.glob('*.xlsx'))
                        logger.info(f"Found {len(files)} report files")
                    else:
                        logger.warning(f"Output directory not found: {output_dir}")
            else:
                logger.error(f"Report generation failed: {json.dumps(data)}")

            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Report generation request failed: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error in report generation: {str(e)}", exc_info=True)
            raise


def run_tests():
    """Run the API test suite with comprehensive logging"""
    tester = APITester()

    try:
        # Test 1: Get all properties
        logger.info("\n=== Test 1: Get all properties ===")
        all_properties = tester.search_properties()

        if not all_properties.get('data'):
            logger.warning("No properties found in the system")
            return

        # Test 2: Search with specific term
        logger.info("\n=== Test 2: Search for specific properties ===")
        search_results = tester.search_properties("Park")

        for prop in search_results.get('data', []):
            logger.info(f"Found: {prop['property_name']} (Key: {prop['property_key']})")

        # Test 3: Generate reports for first two properties
        logger.info("\n=== Test 3: Generate reports ===")
        if all_properties['data']:
            property_keys = [prop['property_key'] for prop in all_properties['data'][:2]]
            logger.info(f"Generating reports for property keys: {property_keys}")
            report_result = tester.generate_reports(property_keys)

            if report_result.get('success', False):
                logger.info(f"Reports generated in: {report_result.get('output', {}).get('directory')}")
            else:
                logger.error(f"Report generation returned unexpected response: {report_result}")

        # Test 4: Search and generate report for specific property
        logger.info("\n=== Test 4: Search for a specific property and generate a report ===")
        specific_search = tester.search_properties("land")

        if specific_search.get('data'):
            specific_property = specific_search['data'][0]
            property_key = specific_property['property_key']
            logger.info(f"Generating report for property key: {property_key}")
            specific_report = tester.generate_reports([property_key])

            if specific_report.get('success', False):
                logger.info(f"Report generated in: {specific_report.get('output', {}).get('directory')}")
            else:
                logger.error(f"Report generation returned unexpected response: {specific_report}")
        else:
            logger.warning("No matching properties found")

    except Exception as e:
        logger.error(f"Test suite failed: {str(e)}", exc_info=True, stack_info=True)


if __name__ == "__main__":
    run_tests()
