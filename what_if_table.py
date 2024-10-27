from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import re
from logger_config import LogConfig

log_config = LogConfig()
logger = log_config.get_logger('what_if_table')


# logging.basicConfig(filename='logs/what_if.log', level=logging.DEBUG)


def generate_what_if_table(initial_daily_rate, days_per_month, break_even_target):
    daily_rates = [round(initial_daily_rate + (i * 0.1), 1) for i in
                   range(52)]  # 52 daily values with increments of 0.1
    monthly_rates = [round(daily * days_per_month) for daily in daily_rates]

    # Find the closest match for the break-even target
    break_even_index = next((i for i, daily in enumerate(daily_rates) if daily >= break_even_target), -1)

    # If no exact match, set to -1 (which might be causing your current issue)
    if break_even_index == -1:
        logger.warning(f"No match found for break-even target {break_even_target}.")

    table_data = []
    for i, (daily, monthly) in enumerate(zip(daily_rates, monthly_rates)):
        row = {
            'day': i + 1,  # Row counting starts from 1
            'daily_rate': daily,
            'monthly_rate': monthly,
            'is_break_even': i == break_even_index
        }
        table_data.append(row)

    # Add 1 to break-even index to convert to a 1-based row index
    return table_data, break_even_index + 1


def update_what_if_table(sheet, break_even_value, current_output_value):
    start_row = 11  # Starting at row 11
    daily_col = 'F'
    monthly_col = 'G'
    label_col = 'H'

    # Track the closest match for current output
    closest_output_row = None
    closest_output_diff = float('inf')  # Start with a large difference to find the closest match

    # Insert the current output into F11 and G11, rounded to nearest 0.1
    sheet[f'{daily_col}{start_row}'] = round(current_output_value, 1)  # Current output rounded
    sheet[f'{monthly_col}{start_row}'] = round(current_output_value * 21.7, 1)  # Monthly work orders, rounded

    # Track the break-even row
    break_even_row = None

    # Start from row 12 for the rest of the rows
    current_row = start_row + 1
    for i in range(1, 53):  # Assuming a range of 52 possible work order scenarios
        daily_value = i
        monthly_value = daily_value * 22  # Keep precise, no rounding for non-special rows

        # Insert values into the corresponding columns
        sheet[f'{daily_col}{current_row}'] = daily_value  # Keep exact daily value
        sheet[f'{monthly_col}{current_row}'] = monthly_value  # Keep exact monthly value

        # Track the closest value to the current output
        output_diff = abs(current_output_value - daily_value)
        if output_diff < closest_output_diff:
            closest_output_diff = output_diff
            closest_output_row = current_row

        # Check if this is the break-even row, and round it to nearest 0.1
        if break_even_row is None and daily_value >= round(break_even_value, 1):
            break_even_row = current_row
            # Insert break-even row with rounding to nearest 0.1
            sheet[f'{daily_col}{current_row}'] = round(break_even_value, 1)
            sheet[f'{monthly_col}{current_row}'] = round(break_even_value * 21.7, 1)
            highlight_row(sheet, current_row, "<-------- Break even", "0000FF", font_color="FFFFFF", bold=True)

        current_row += 1

    # Highlight the closest row to the current output (already rounded)
    if closest_output_row:
        # Insert current output rounded
        sheet[f'{daily_col}{closest_output_row}'] = round(current_output_value, 1)
        sheet[f'{monthly_col}{closest_output_row}'] = round(current_output_value * 21.7, 1)
        highlight_row(sheet, closest_output_row, "<-------- Current output (AVG)", "FFA500", font_color="000000", bold=True)

    return sheet




def calculate_metrics(data, sheet, open_actual):
    # Populate necessary cells
    # sheet['B17'] = data['TotalWorkOrders']
    sheet['B6'] = 21
    sheet['M9'] = open_actual

    # Read and evaluate the break-even formula
    break_even_formula = sheet['B24'].value
    logger.info(f"Evaluating break-even formula: {break_even_formula}")
    if isinstance(break_even_formula, str) and break_even_formula.startswith('='):
        break_even_value = evaluate_simple_formula(break_even_formula, sheet)
    else:
        break_even_value = float(break_even_formula) if break_even_formula is not None else 0
    logger.info(f"Break-even value: {break_even_value}")

    # Read and evaluate the current output formula
    current_output_formula = sheet['B4'].value
    logger.info(f"Evaluating current output formula: {current_output_formula}")
    if isinstance(current_output_formula, str) and current_output_formula.startswith('='):
        current_output_value = evaluate_simple_formula(current_output_formula, sheet)
    else:
        current_output_value = float(current_output_formula) if current_output_formula is not None else 0
    logger.info(f"Current output value: {current_output_value}")

    # Calculate initial daily rate
    initial_daily_rate = current_output_value
    days_per_month = 21

    logger.info(
        f"Generating what-if table with initial daily rate: {initial_daily_rate}, days per month: {days_per_month}, break-even value: {break_even_value}")
    what_if_table, break_even_row = generate_what_if_table(initial_daily_rate, days_per_month, break_even_value)

    logger.info(f"Generated what-if table with break-even row: {break_even_row}")

    return {
        'what_if_table': what_if_table,
        'break_even_row': break_even_row,
        'current_output_value': current_output_value,
        'break_even_value': break_even_value
    }


# Highlight a row with specified formatting
def highlight_row(sheet, row, label, color, font_color='000000', bold=False):
    fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
    font = Font(color=font_color, bold=bold)  # Define font style with color and bold options

    for col in ['F', 'G']:  # Columns F and G contain the daily and monthly work orders
        cell = sheet[f'{col}{row}']
        cell.fill = fill
        cell.font = font
        # Preserve existing borders if any, otherwise set new borders
        if not cell.border:
            cell.border = Border(top=Side(style='thin'), bottom=Side(style='thin'))

    # Label column H with the provided label
    label_cell = sheet[f'H{row}']
    label_cell.value = label
    label_cell.fill = fill
    label_cell.font = font
    label_cell.alignment = Alignment(horizontal='left')


# Evaluate a simple formula in a cell, handling recursion for references to other cells
def evaluate_simple_formula(formula, sheet):
    # Remove the leading '=' if present
    formula = formula.lstrip('=')

    # Handle Excel AVERAGE function
    if 'AVERAGE' in formula:
        formula = re.sub(r'AVERAGE\(([^)]+)\)', r'(\1) / len([\1])', formula)  # Convert AVERAGE() to Python equivalent

    # Use regex to find cell references in the formula
    cell_refs = re.findall(r'[A-Z]+[0-9]+', formula)

    # Replace cell references with their evaluated values
    for cell_ref in cell_refs:
        cell_value = sheet[cell_ref].value
        if isinstance(cell_value, str) and cell_value.startswith('='):
            # Recursively evaluate if the cell contains another formula
            cell_value = evaluate_simple_formula(cell_value, sheet)
        if cell_value is None:
            return 0  # Handle missing or empty cells appropriately
        formula = formula.replace(cell_ref, str(cell_value))

    # Evaluate the resulting expression
    try:
        return eval(formula)
    except Exception as e:
        print(f"Error evaluating formula {formula}: {e}")
        return 0  # Handle any evaluation errors