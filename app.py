from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta
from models.models import *
from functools import wraps
from typing import Dict, List, Optional, Union
from pydantic import ValidationError
from property_search import PropertySearch
from logger_config import LogConfig, log_exceptions

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5173"],  # Vite's default port
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type"]
    }
})

# Setup logging
log_config = LogConfig()
logger = log_config.get_logger('api')

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
            logger.error(f"Error occurred: {str(e)}", exc_info=True)
            return jsonify({
                "status": "error",
                "message": "An internal error occurred. Please try again later."
            }), 500

    return wrapper


def update_cache():
    from data_retrieval import sql_queries
    global cache
    logger.info("Updating cache with new data.")
    cache['data'] = sql_queries.fetch_make_ready_data().to_dict(orient='records')
    cache['last_updated'] = datetime.now()
    logger.info("Cache updated successfully.")


@app.route('/api/data', methods=['GET'])
@catch_exceptions
@log_exceptions(logger)
def get_make_ready_data():
    logger.info("GET /api/data endpoint accessed.")
    if cache['data'] is None or (isinstance(cache['last_updated'], datetime) and
                                 datetime.now() - cache['last_updated'] > timedelta(hours=12)):
        logger.info("Cache is empty or outdated. Updating cache.")
        update_cache()

    logger.info("Returning data from cache.")
    return jsonify({
        "status": "success",
        "data": cache['data'],
        "total_records": len(cache['data']) if cache['data'] is not None else 0,
        "last_updated": cache['last_updated'].isoformat() if isinstance(cache['last_updated'], datetime) else None
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    logger.info("GET /api/health endpoint accessed.")
    return jsonify({"status": "healthy"}), 200


@app.route('/api/properties/search', methods=['GET'])
@catch_exceptions
@log_exceptions(logger)
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
@log_exceptions(logger)
def generate_report():
    """Generate Excel report for selected properties."""
    try:
        # Validate request data
        request_data = request.get_json()
        if not request_data:
            logger.error("No request data provided")
            return jsonify({
                "success": False,
                "message": "No request data provided"
            }), 400

        try:
            report_request = ReportGenerationRequest(**request_data)
        except ValidationError as e:
            logger.error(f"Invalid request format: {str(e)}")
            return jsonify({
                "success": False,
                "message": f"Invalid request format: {str(e)}"
            }), 400

        # Ensure cache is up to date
        if cache['data'] is None or (
                isinstance(cache['last_updated'], datetime) and
                datetime.now() - cache['last_updated'] > timedelta(hours=12)
        ):
            update_cache()

        # Use PropertySearch class
        searcher = PropertySearch(cache['data'])
        properties = searcher.search_properties(property_keys=report_request.properties)

        if not properties:
            logger.warning(f"No properties found for keys: {report_request.properties}")
            return jsonify({
                "success": False,
                "message": "No properties found matching the request"
            }), 404

        # Generate reports
        from data_processing import generate_multi_property_report
        output_dir = generate_multi_property_report(
            template_name="break_even_template.xlsx",
            properties=properties,
            api_url='http://127.0.0.1:5000/api/data'
        )

        # Verify output directory exists
        output_path = Path(output_dir)
        if not output_path.exists():
            logger.error(f"Output directory not created: {output_dir}")
            return jsonify({
                "success": False,
                "message": "Failed to create output directory"
            }), 500

        # Get list of generated files
        files = [f.name for f in output_path.glob('*.xlsx')]

        # Create response using corrected model
        response = ReportGenerationResponse(
            success=True,
            message="Reports generated successfully",
            output=ReportOutput(
                directory=output_dir,
                propertyCount=len(properties),
                files=files
            )
        )

        return jsonify(response.model_dump())

    except Exception as e:
        logger.error(f"Error generating report: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Error generating report: {str(e)}"
        }), 500


@app.route('/api/refresh', methods=['POST'])
@catch_exceptions
@log_exceptions(logger)
def refresh_data():
    logger.info("POST /api/refresh endpoint accessed. Refreshing data.")
    update_cache()
    logger.info("Data refreshed successfully.")
    return jsonify({"status": "success", "message": "Data refreshed successfully"})


if __name__ == '__main__':
    logger.info("Starting application and updating initial cache.")
    app.run(debug=True)
