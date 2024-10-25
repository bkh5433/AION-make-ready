from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import logging
from models.models import *

from functools import wraps
from typing import Dict, List, Optional, Union
from pydantic import ValidationError
from property_search import PropertySearch

app = Flask(__name__)

# Setup logging
logging.basicConfig(filename='api.log', level=logging.DEBUG)

# In-memory cache with type hints
cache: Dict[str, Optional[Union[List[Dict], datetime]]] = {
    'data': None,
    'last_updated': None
}


def catch_exceptions(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error occurred: {str(e)}", exc_info=True)
            return jsonify({
                "status": "error",
                "message": "An internal error occurred. Please try again later."
            }), 500

    return wrapper


def update_cache():
    from data_retrieval import sql_queries
    global cache
    logging.info("Updating cache with new data.")
    cache['data'] = sql_queries.fetch_make_ready_data().to_dict(orient='records')
    cache['last_updated'] = datetime.now()
    logging.info("Cache updated successfully.")


@app.route('/api/data', methods=['GET'])
@catch_exceptions
def get_make_ready_data():
    logging.info("GET /api/data endpoint accessed.")
    if cache['data'] is None or (isinstance(cache['last_updated'], datetime) and
                                 datetime.now() - cache['last_updated'] > timedelta(hours=12)):
        logging.info("Cache is empty or outdated. Updating cache.")
        update_cache()

    logging.info("Returning data from cache.")
    return jsonify({
        "status": "success",
        "data": cache['data'],
        "total_records": len(cache['data']) if cache['data'] is not None else 0,
        "last_updated": cache['last_updated'].isoformat() if isinstance(cache['last_updated'], datetime) else None
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    logging.info("GET /api/health endpoint accessed.")
    return jsonify({"status": "healthy"}), 200


@app.route('/api/properties/search', methods=['GET'])
@catch_exceptions
def search_properties():
    """
    Search properties by name.
    Query parameter:
    - q: Search term for property name (optional)
    """
    search_term = request.args.get('q', None)

    # Ensure cache is up to date
    if cache['data'] is None or (
            isinstance(cache['last_updated'], datetime) and
            datetime.now() - cache['last_updated'] > timedelta(hours=12)
    ):
        update_cache()

    # Use PropertySearch class
    searcher = PropertySearch(cache['data'])
    result = searcher.get_search_result(
        search_term=search_term,
        last_updated=cache['last_updated']
    )

    return jsonify(result.model_dump())


@app.route('/api/reports/generate', methods=['POST'])
@catch_exceptions
def generate_report():
    """Generate Excel report for selected properties."""
    try:
        from data_processing import excel_generator as dp
        # Validate request using our model
        request_data = request.get_json()
        report_request = ReportGenerationRequest(**request_data)

        # Ensure cache is up to date
        if cache['data'] is None or (
                isinstance(cache['last_updated'], datetime) and
                datetime.now() - cache['last_updated'] > timedelta(hours=12)
        ):
            update_cache()

        # Use PropertySearch class
        searcher = PropertySearch(cache['data'])
        properties = searcher.search_properties(property_keys=report_request.properties)

        # Generate reports
        output_dir = dp.generate_multi_property_report(
            template_path='break_even_template.xlsx',
            properties=properties,  # Pass Property models instead of just IDs
            api_url='http://127.0.0.1:5000/api/data'
        )

        response = ReportGenerationResponse(
            success=True,
            message="Reports generated successfully",
            output={
                "directory": output_dir,
                "propertyCount": len(properties)
            },
            timestamp=datetime.now()
        )

        return jsonify(response.model_dump())

    except ValidationError as e:
        logging.error(f"Validation error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    except Exception as e:
        logging.error(f"Error generating report: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "An error occurred while generating the report"
        }), 500


@app.route('/api/refresh', methods=['POST'])
@catch_exceptions
def refresh_data():
    logging.info("POST /api/refresh endpoint accessed. Refreshing data.")
    update_cache()
    logging.info("Data refreshed successfully.")
    return jsonify({"status": "success", "message": "Data refreshed successfully"})



if __name__ == '__main__':
    logging.info("Starting application and updating initial cache.")
    app.run(debug=True)