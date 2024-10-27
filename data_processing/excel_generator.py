from pathlib import Path
from typing import Dict, List, Union, Any
from datetime import datetime, timedelta
import os
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.worksheet.worksheet import Worksheet
from pydantic import BaseModel, Field, ConfigDict, field_validator, validator, computed_field, model_validator
from what_if_table import update_what_if_table, WhatIfTableGenerator

from logger_config import LogConfig, log_exceptions
from utils.path_resolver import PathResolver
from models.models import Property

# Initialize logging
log_config = LogConfig()
logger = log_config.get_logger("excel_generator")


class SpreadsheetTemplate(BaseModel):
    """Model for spreadsheet template configuration"""
    template_name: str = Field(..., description="Path to template file")
    output_path: Path = Field(..., description="Path where output file will be saved")
    sheet_name: str = Field(default="Sheet1", description="Name of the worksheet to use")

    @property
    def template_path(self) -> Path:
        """Resolve the template path dynamically"""
        try:
            return PathResolver.resolve_template_path(self.template_name)
        except FileNotFoundError as e:
            logger.error(f"Failed to resolve template path: {e}")
            raise

    model_config = ConfigDict(validate_assignment=True)


class WorkOrderMetrics(BaseModel):
    """Model for work order metrics with calculations"""
    # Work order tracking fields
    open_work_orders: int = Field(ge=0)
    new_work_orders: int = Field(ge=0)
    completed_work_orders: int = Field(ge=0)
    cancelled_work_orders: int = Field(ge=0)
    pending_work_orders: int = Field(ge=0)
    percentage_completed: float = Field(ge=0, le=100)

    # Rate calculations
    days_per_month: int = Field(ge=0, le=31, default=21)
    daily_rate: float = Field(ge=0)
    monthly_rate: float = Field(ge=0)
    break_even_target: float = Field(ge=0)
    current_output: float = Field(ge=0)

    @model_validator(mode='after')
    def calculate_rates(self) -> 'WorkOrderMetrics':
        """Calculate all rates based on completed work orders"""
        # Calculate daily rate from completed work orders
        self.daily_rate = round(self.completed_work_orders / self.days_per_month, 1)

        # Calculate monthly rate from daily rate
        self.monthly_rate = round(self.daily_rate * self.days_per_month, 1)

        # Set current output same as daily rate for consistency
        self.current_output = self.daily_rate

        # Calculate break-even target
        target_rate = max(self.new_work_orders, self.completed_work_orders) / self.days_per_month
        self.break_even_target = round(target_rate * 1.1, 1)  # Adding 10% buffer

        return self

    @field_validator('percentage_completed', 'daily_rate', 'monthly_rate', 'break_even_target', 'current_output')
    def round_values(cls, v: float) -> float:
        return round(v, 1)

    def get_metrics_for_table(self) -> dict:
        """Get metrics formatted for what-if table calculations"""
        return {
            'daily_rate': self.daily_rate,
            'monthly_rate': self.monthly_rate,
            'break_even_target': self.break_even_target,
            'current_output': self.current_output,
            'days_per_month': self.days_per_month
        }

    def get_all_metrics(self) -> dict:
        """Get all metrics including work orders and calculations"""
        return {
            **self.get_metrics_for_table(),
            'open_work_orders': self.open_work_orders,
            'new_work_orders': self.new_work_orders,
            'completed_work_orders': self.completed_work_orders,
            'cancelled_work_orders': self.cancelled_work_orders,
            'pending_work_orders': self.pending_work_orders,
            'percentage_completed': self.percentage_completed
        }


class ExcelGeneratorService:
    """Service for handling Excel generation with improved error handling and logging"""

    def __init__(self, template: SpreadsheetTemplate):
        """Initialize the Excel generator service"""
        logger.info(f"Initializing ExcelGeneratorService with template: {template.template_path}")
        self.template = template
        self.workbook = None
        self.sheet = None
        self._font = Font(name='Aptos Narrow Bold')

    @log_exceptions(logger)
    def initialize_workbook(self) -> None:
        """Initialize workbook from template with comprehensive error handling"""
        logger.info(f"Loading template from: {self.template.template_path}")
        try:
            self.workbook = openpyxl.load_workbook(self.template.template_path)
            if self.template.sheet_name == "Sheet1":
                self.sheet = self.workbook.active
            else:
                if self.template.sheet_name not in self.workbook.sheetnames:
                    raise ValueError(f"Sheet '{self.template.sheet_name}' not found in workbook")
                self.sheet = self.workbook[self.template.sheet_name]

            logger.info(f"Successfully loaded workbook with {len(self.workbook.sheetnames)} sheets")
        except Exception as e:
            logger.error(f"Failed to initialize workbook", exc_info=True)
            raise ValueError(f"Failed to initialize workbook: {str(e)}") from e

    @log_exceptions(logger)
    def update_cell(self, cell_ref: str, value: Any, wrap_text: bool = False) -> None:
        """Update a cell with proper formatting and error handling"""
        if not self.sheet:
            logger.error("Attempted to update cell without initialized workbook")
            raise ValueError("Workbook not initialized")

        try:
            logger.debug(f"Updating cell {cell_ref} with value: {value}")
            cell = self.sheet[cell_ref]
            cell.value = value
            cell.font = self._font
            if wrap_text:
                cell.alignment = Alignment(wrap_text=True)
        except KeyError as e:
            logger.error(f"Invalid cell reference: {cell_ref}")
            raise KeyError(f"Invalid cell reference: {cell_ref}") from e
        except Exception as e:
            logger.error(f"Failed to update cell {cell_ref}", exc_info=True)
            raise

    @log_exceptions(logger)
    def format_date_range(self, end_date: datetime) -> str:
        """Format date range for the report"""
        try:
            start_date = end_date - timedelta(days=30)
            return f"{start_date.strftime('%m/%d/%y')} - {end_date.strftime('%m/%d/%y')}"
        except Exception as e:
            logger.error("Failed to format date range", exc_info=True)
            raise ValueError(f"Failed to format date range: {str(e)}") from e

    @log_exceptions(logger)
    def _parse_date(self, date_value: Union[str, datetime]) -> datetime:
        """Parse date from various formats with detailed error logging"""
        logger.debug(f"Parsing date value: {date_value} of type {type(date_value)}")

        if isinstance(date_value, datetime):
            return date_value

        try:
            # Try parsing standard API format
            return datetime.strptime(date_value, '%a, %d %b %Y %H:%M:%S GMT')
        except ValueError:
            logger.debug("Failed to parse GMT format, trying ISO format")
            try:
                # Try ISO format
                return datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            except ValueError:
                logger.error(f"Unsupported date format: {date_value}")
                return datetime.now()

    @log_exceptions(logger)
    def update_metrics(self, metrics: WorkOrderMetrics) -> None:
        """Update the what-if table with work order metrics"""
        if not self.sheet:
            raise ValueError("Workbook not initialized")

        try:
            logger.info("Updating work order metrics and what-if table")

            # Update initial metrics cells
            self.update_cell('B6', 21)  # Days per month
            self.update_cell('M9', metrics.current_output)  # Current output

            # Update what-if table with necessary data
            update_what_if_table(
                sheet=self.sheet,
                data={
                    'NewWorkOrders_Current': metrics.new_work_orders,
                    'CancelledWorkOrder_Current': metrics.cancelled_work_orders,
                    'CompletedWorkOrder_Current': metrics.completed_work_orders,
                    'PendingWorkOrders': metrics.pending_work_orders,
                },
                open_actual=metrics.new_work_orders - metrics.cancelled_work_orders
            )

            logger.info("Successfully updated metrics and what-if table")
        except Exception as e:
            logger.error("Failed to update metrics", exc_info=True)
            raise

    @log_exceptions(logger)
    def update_property_data(self, property_data: Dict[str, Any]) -> None:
        """Update cells with property data and handle all calculations"""
        logger.info(f"Updating property data for: {property_data.get('PropertyName', 'Unknown')}")
        try:
            # Calculate opened actual
            opened_actual = property_data['NewWorkOrders_Current'] - property_data['CancelledWorkOrder_Current']
            logger.debug(f"Calculated opened_actual: {opened_actual}")

            # Parse and validate dates
            end_date = self._parse_date(property_data['LatestPostDate'])
            date_range = self.format_date_range(end_date)

            # Update cells with validated data
            updates = {
                'B22': property_data['TotalUnitCount'],
                'M9': opened_actual,
                'N9': property_data['CompletedWorkOrder_Current'],
                'O9': property_data['PendingWorkOrders'],
                'L8': property_data['PropertyName'],
                'D4': date_range,
                'M8': date_range,
                'A1': f"Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }

            logger.debug(f"Updating cells with values: {updates}")
            for cell_ref, value in updates.items():
                self.update_cell(cell_ref, value, wrap_text=cell_ref in ['D4', 'M8'])

            # Update what-if table after cell updates
            update_what_if_table(
                sheet=self.sheet,
                data=property_data,
                open_actual=opened_actual
            )

            logger.info("Successfully updated all property data")
        except Exception as e:
            logger.error("Failed to update property data", exc_info=True)
            raise

    @log_exceptions(logger)
    def save(self) -> None:
        """Save workbook with proper error handling and logging"""
        if not self.workbook:
            logger.error("Attempted to save without initialized workbook")
            raise ValueError("No workbook to save")

        try:
            logger.info(f"Saving workbook to: {self.template.output_path}")
            os.makedirs(os.path.dirname(self.template.output_path), exist_ok=True)
            self.workbook.save(self.template.output_path)
            logger.info("Workbook saved successfully")
        except PermissionError:
            logger.error("Permission denied while saving workbook", exc_info=True)
            raise
        except Exception as e:
            logger.error("Failed to save workbook", exc_info=True)
            raise


def generate_multi_property_report(
        template_name: str,
        properties: List[Property],
        api_url: str
) -> str:
    """
    Generate Excel reports for multiple properties.

    Args:
        template_name: Name of the template file
        properties: List of Property objects
        api_url: API URL for data retrieval

    Returns:
        str: Path to the output directory containing generated reports
    """
    logger.info(f"Starting multi-property report generation for {len(properties)} properties")

    try:
        # Create timestamp-based output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_output_dir = f'output/multi_property_report_{timestamp}'
        os.makedirs(base_output_dir, exist_ok=True)
        logger.info(f"Created output directory: {base_output_dir}")

        # Generate report for each property
        generated_files = []
        for property_data in properties:
            try:
                # Create safe filename from property name
                safe_name = "".join(c for c in property_data.property_name if c.isalnum() or c in (' ', '-', '_'))
                safe_name = safe_name.replace(' ', '_')[:31]  # limit length and replace spaces
                property_output_path = os.path.join(base_output_dir, f"{safe_name}.xlsx")

                logger.info(f"Generating report for property: {property_data.property_name}")

                # Convert Property model to dict format
                property_dict = {
                    'PropertyKey': property_data.property_key,
                    'PropertyName': property_data.property_name,
                    'TotalUnitCount': property_data.total_unit_count,
                    'LatestPostDate': property_data.latest_post_date,
                    'OpenWorkOrder_Current': property_data.metrics.open_work_orders if property_data.metrics else 0,
                    'NewWorkOrders_Current': property_data.metrics.new_work_orders if property_data.metrics else 0,
                    'CompletedWorkOrder_Current': property_data.metrics.completed_work_orders if property_data.metrics else 0,
                    'CancelledWorkOrder_Current': property_data.metrics.cancelled_work_orders if property_data.metrics else 0,
                    'PendingWorkOrders': property_data.metrics.pending_work_orders if property_data.metrics else 0,
                }

                # Generate individual report
                generate_report(
                    template_name=template_name,
                    output_path=property_output_path,
                    property_data=property_dict
                )

                generated_files.append(property_output_path)
                logger.info(f"Successfully generated report for {property_data.property_name}")

            except Exception as e:
                logger.error(f"Failed to generate report for {property_data.property_name}: {str(e)}", exc_info=True)
                # Continue with next property instead of failing completely
                continue

        # Verify generated files
        successful_count = len(generated_files)
        logger.info(
            f"Completed report generation. Successfully generated {successful_count} out of {len(properties)} reports")

        if successful_count == 0:
            raise Exception("Failed to generate any reports successfully")

        return base_output_dir

    except Exception as e:
        logger.error(f"Failed to generate multi-property report: {str(e)}", exc_info=True)
        raise


def generate_report(template_name: str, output_path: str, property_data: Dict[str, Any]) -> None:
    """Main function to generate Excel report with comprehensive logging"""
    logger.info(f"Starting report generation for property: {property_data.get('PropertyName', 'Unknown')}")

    try:
        # Initialize template with template_name instead of template_path
        template = SpreadsheetTemplate(
            template_name=template_name,  # Use template_name here
            output_path=Path(output_path)
        )

        # Create service and generate report
        service = ExcelGeneratorService(template)
        service.initialize_workbook()
        service.update_property_data(property_data)
        service.save()

        logger.info("Report generated successfully")
    except Exception as e:
        logger.error("Failed to generate report", exc_info=True)
        raise


if __name__ == "__main__":
    # Example usage with error handling
    template_path = 'break_even_template.xlsx'
    output_path = "output/filled_work_order_report.xlsx"

    # Sample property data
    property_data = {
        "PropertyKey": 1,
        "PropertyName": "Test Property",
        "TotalUnitCount": 100,
        "LatestPostDate": "Wed, 23 Oct 2024 00:00:00 GMT",
        "NewWorkOrders_Current": 10,
        "CompletedWorkOrder_Current": 8,
        "CancelledWorkOrder_Current": 1,
        "PendingWorkOrders": 1
    }

    try:
        generate_report(template_path, output_path, property_data)
        logger.info("Example report generated successfully!")
    except Exception as e:
        logger.error("Failed to generate example report", exc_info=True)
