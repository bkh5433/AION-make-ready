import logging
import requests

logging.basicConfig(filename='api.log', level=logging.INFO)

def fetch_data_from_api(api_url):
    logging.info(f"Fetching data from API: {api_url}")
    try:
        response = requests.get(api_url)
        response.raise_for_status()  # This will raise an HTTPError for bad responses
        logging.info("Data fetched successfully from API.")
        return response.json()['data']
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 403:
            logging.error(f"403 Forbidden error when accessing the API. This might be due to authentication issues or lack of permissions.")
            logging.error(f"Response content: {response.text}")
            raise Exception(f"403 Forbidden: Unable to access the API. Please check your authentication and permissions.") from http_err
        else:
            logging.error(f"HTTP error occurred: {http_err}")
            raise Exception(f"HTTP error occurred: {http_err}") from http_err
    except requests.exceptions.RequestException as err:
        logging.error(f"An error occurred while fetching data from API: {err}")
        raise Exception(f"Error fetching data from API: {err}") from err