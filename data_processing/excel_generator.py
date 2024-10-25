import openpyxl
from datetime import datetime, timedelta
from openpyxl.styles import Font, Alignment
from what_if_table import update_what_if_table
from utils.evaluate_cell import evaluate_cell
from property_search import PropertySearch
from models.models import Property
from typing import List, Dict
import os
import logging
import re
import what_if_table
from datetime import datetime
import os


# Setup logging
logging.basicConfig(filename='excel_generator.log', level=logging.DEBUG)

def generate_spreadsheet_from_template(template_path, output_path, api_url, property_data=None):
    from utils.fetch_data import fetch_data_from_api
    logging.info(f"Loading template from: {template_path}")
    # Load the template
    workbook = openpyxl.load_workbook(template_path)
    sheet = workbook.active

    # Define the Aptos Narrow Body font
    aptos_font = Font(name='Aptos Narrow Bold')

    try:
        # Fetch data from API
        if property_data is None:
            data = fetch_data_from_api(api_url)
            # Extract property data
            property_data = data[32]

        # Calculate opened actual (opened work orders - canceled work orders)
        opened_actual = property_data['NewWorkOrders_Current'] - property_data['CancelledWorkOrder_Current']

        # Handle date parsing based on input format
        try:
            if isinstance(property_data['LatestPostDate'], str):
                # Try parsing the standard API format first
                try:
                    end_date = datetime.strptime(property_data['LatestPostDate'], '%a, %d %b %Y %H:%M:%S GMT')
                except ValueError:
                    # If that fails, try parsing ISO format
                    end_date = datetime.fromisoformat(property_data['LatestPostDate'].replace('Z', '+00:00'))
            elif isinstance(property_data['LatestPostDate'], datetime):
                end_date = property_data['LatestPostDate']
            else:
                raise ValueError(f"Unsupported date format: {type(property_data['LatestPostDate'])}")

            start_date = end_date - timedelta(days=30)
            date_range = f"{start_date.strftime('%m/%d/%y')} - {end_date.strftime('%m/%d/%y')}"

        except Exception as e:
            logging.error(f"Error parsing date: {str(e)}")
            # Fallback to current date if date parsing fails
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
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
            sheet[cell].font = aptos_font # Apply Aptos Narrow Bold font

            # if cell in ['D4', 'M8']:  # Assuming these cells might need text wrapping
            #     sheet[cell].alignment = Alignment(wrap_text=True)

        # Force recalculation of the entire workbook
        # Manually evaluate B24 formula
        b24_value = evaluate_cell(sheet, 'B24', cells_to_update)
        logging.info(f"Evaluated B24 value: {b24_value}")

        # Update L12 with the new B24 value
        current_l12_text = sheet['L12'].value
        new_l12_text = re.sub(r'\d+(\.\d+)?', str(round(b24_value, 1)), current_l12_text)
        sheet['L12'] = new_l12_text
        sheet['L12'].font = aptos_font
        sheet['L12'].alignment = Alignment(wrap_text=True)

        logging.info(f"Updated L12 text: {new_l12_text}")

        # Calculate metrics
        metrics = what_if_table.calculate_metrics(property_data, sheet, opened_actual)

        # Update what-if table
        update_what_if_table(sheet, break_even_value=metrics['break_even_value'],
                                    current_output_value=metrics['current_output_value'])





        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Save the filled spreadsheet
        logging.info(f"Saving filled spreadsheet to: {output_path}")
        workbook.save(output_path)
        logging.info("Spreadsheet saved successfully.")
    except Exception as e:
        logging.error(f"An error occurred while generating the spreadsheet: {str(e)}")
        raise


def generate_multi_property_report(
        template_path: str,
        properties: List[Property],
        api_url: str
) -> str:
    """
    Generate a multi-sheet Excel report for selected properties.
    Now accepts Property models directly instead of raw data.
    """
    try:
        # Create timestamp for unique folder name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_output_dir = f'output/multi_property_report_{timestamp}'
        os.makedirs(base_output_dir, exist_ok=True)

        # Generate report for each property
        generated_files = []
        for property in properties:
            # Create property-specific output path
            property_output_path = os.path.join(
                base_output_dir,
                f"{property.property_name.replace(' ', '_')[:31]}.xlsx"
            )

            # Convert Property model back to dict format expected by generate_spreadsheet_from_template
            property_data = {
                'PropertyKey': property.property_key,
                'PropertyName': property.property_name,
                'TotalUnitCount': property.total_unit_count,
                'LatestPostDate': property.latest_post_date,
                'OpenWorkOrder_Current': property.metrics.open_work_orders,
                'NewWorkOrders_Current': property.metrics.new_work_orders,
                'CompletedWorkOrder_Current': property.metrics.completed_work_orders,
                'CancelledWorkOrder_Current': property.metrics.cancelled_work_orders,
                'PendingWorkOrders': property.metrics.pending_work_orders,
                'PercentageCompletedThisPeriod': property.metrics.percentage_completed
            }

            # Generate spreadsheet
            generate_spreadsheet_from_template(
                template_path=template_path,
                output_path=property_output_path,
                api_url=api_url,
                property_data=property_data
            )

            generated_files.append(property_output_path)

        return base_output_dir
    except Exception as e:
        logging.error(f"Error generating multi-property report: {str(e)}", exc_info=True)
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