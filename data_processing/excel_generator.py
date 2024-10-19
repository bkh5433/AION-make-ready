import openpyxl
import requests
from datetime import datetime, timedelta
from openpyxl.styles import Font, Alignment
from utils.evaluate_cell import evaluate_cell
from utils.evaluate_formula import evaluate_formula, get_cell_value
import os
import logging
import re

# Setup logging
logging.basicConfig(filename='excel_generator.log', level=logging.DEBUG)

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
            raise Exception(f"403 Forbidden: Unable to access the API. Please check your authentication and permissions.")
        else:
            logging.error(f"HTTP error occurred: {http_err}")
            raise Exception(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as err:
        logging.error(f"An error occurred while fetching data from API: {err}")
        raise Exception(f"Error fetching data from API: {err}")

def generate_spreadsheet_from_template(template_path, output_path, api_url):
    logging.info(f"Loading template from: {template_path}")
    # Load the template
    workbook = openpyxl.load_workbook(template_path)
    sheet = workbook.active

    # Define the Aptos Narrow Body font
    aptos_font = Font(name='Aptos Narrow Bold')

    try:
        # Fetch data from API
        data = fetch_data_from_api(api_url)

        # Use the 6th item in the data list (index 5)
        property_data = data[5]

        # Calculate opened actual (opened work orders - canceled work orders)
        opened_actual = property_data['NewWorkOrders_Current'] - property_data['CancelledWorkOrder_Current']

        # Calculate date range
        end_date = datetime.strptime(property_data['LatestPostDate'], '%a, %d %b %Y %H:%M:%S GMT')
        start_date = end_date - timedelta(days=30)  # Assuming a 30-day period
        date_range = f"{start_date.strftime('%m/%d/%y')} - {end_date.strftime('%m/%d/%y')}"

        # Update cells with API data
        cells_to_update = {
            'B22': property_data['TotalUnitCount'],
            'M9': opened_actual,
            'N9': property_data['CompletedWorkOrder_Current'],
            'O9': property_data['PendingWorkOrders'],
            'L8': property_data['PropertyName'],
            'D4': date_range,
            'M8': date_range,
            'A1': f"Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }

        for cell, value in cells_to_update.items():
            sheet[cell] = value
            sheet[cell].font = aptos_font

            # if cell in ['D4', 'M8']:  # Assuming these cells might need text wrapping
            #     sheet[cell].alignment = Alignment(wrap_text=True)

        # Force recalculation of the entire workbook
        # Manually evaluate B24 formula
        b24_value = evaluate_cell(sheet, 'B24', cells_to_update)
        logging.info(f"Evaluated B24 value: {b24_value}")

        # Update L12 with the new B24 value
        current_l12_text = sheet['L12'].value
        new_l12_text = re.sub(r'\d+(\.\d+)?', str(b24_value), current_l12_text)
        sheet['L12'] = new_l12_text
        sheet['L12'].font = aptos_font
        sheet['L12'].alignment = Alignment(wrap_text=True)

        logging.info(f"Updated L12 text: {new_l12_text}")

        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Save the filled spreadsheet
        logging.info(f"Saving filled spreadsheet to: {output_path}")
        workbook.save(output_path)
        logging.info("Spreadsheet saved successfully.")
    except Exception as e:
        logging.error(f"An error occurred while generating the spreadsheet: {str(e)}")
        raise

# Usage
template_path = '/Users/brandonhightower/PycharmProjects/AION-make-ready/break_even_template.xlsx'
output_path = 'output/filled_work_order_report.xlsx'
api_url = 'http://127.0.0.1:5000/api/data'  # Adjust this to actual API URL

try:
    generate_spreadsheet_from_template(template_path, output_path, api_url)
except Exception as e:
    logging.error(f"An error occurred: {str(e)}", exc_info=True)
    print(f"An error occurred: {str(e)}")