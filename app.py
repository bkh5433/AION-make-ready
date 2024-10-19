from flask import Flask, jsonify, request
from data_retrieval import sql_queries
import pandas as pd
from datetime import datetime, timedelta
import logging
from functools import wraps
import os
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


@app.route('/api/refresh', methods=['POST'])
@catch_exceptions
def refresh_data():
    logging.info("POST /api/refresh endpoint accessed. Refreshing data.")
    update_cache()
    logging.info("Data refreshed successfully.")
    return jsonify({"status": "success", "message": "Data refreshed successfully"})


@app.route('/test')
def test():
    logging.info("GET /test endpoint accessed.")
    return "Test successful"


if __name__ == '__main__':
    logging.info("Starting application and updating initial cache.")
    app.run(debug=True)