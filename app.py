from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import logging
from functools import wraps
from typing import Dict, List, Optional, Union

app = Flask(__name__)

# Setup logging
logging.basicConfig(filename='api.log', level=logging.INFO)

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

    Example: /api/properties/search?q=Park
    If no search term provided, returns all properties
    """
    from property_search import PropertySearch
    search_term = request.args.get('q', None)

    # Ensure cache is up to date
    if cache['data'] is None or (isinstance(cache['last_updated'], datetime) and
                                 datetime.now() - cache['last_updated'] > timedelta(hours=12)):
        update_cache()

    # Create searcher instance and perform search
    searcher = PropertySearch(cache['data'])
    results = searcher.search_properties(search_term=search_term)

    return jsonify({
        "status": "success",
        "count": len(results),
        "data": [{
            "property_key": result.property_key,
            "name": result.property_name,
            "lastUpdated": result.latest_post_date
        } for result in results]
    })


@app.route('/api/reports/generate', methods=['POST'])
@catch_exceptions
def generate_report():
    """
    Generate Excel report for selected properties.
    Expected JSON body:
    {
        "properties": [123, 456, 789]  # List of property keys
    }
    """
    from data_processing.excel_generator import generate_multi_property_report
    try:
        data = request.get_json()

        if not data or 'properties' not in data:
            return jsonify({
                "status": "error",
                "message": "Missing required field 'properties' in request body"
            }), 400

        if not isinstance(data['properties'], list) or not data['properties']:
            return jsonify({
                "status": "error",
                "message": "Properties must be a non-empty list of property keys"
            }), 400

        # Ensure cache is up to date
        if cache['data'] is None or (isinstance(cache['last_updated'], datetime) and
                                     datetime.now() - cache['last_updated'] > timedelta(hours=12)):
            update_cache()

        # Generate reports
        output_dir = generate_multi_property_report(
            template_path='break_even_template.xlsx',
            selected_properties=data['properties'],
            cache_data=cache['data'],
            api_url='http://127.0.0.1:5000/api/data'
        )

        return jsonify({
            "status": "success",
            "message": "Reports generated successfully",
            "output": {
                "directory": output_dir,
                "propertyCount": len(data['properties'])
            }
        })

    except Exception as e:
        logging.error(f"Error generating reports: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
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