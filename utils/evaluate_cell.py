import logging

logging.basicConfig(filename='excel_generator.log', level=logging.DEBUG)

def evaluate_cell(sheet, cell_reference, updated_values, visited=None):
    if visited is None:
        visited = set()

    if cell_reference in visited:
        logging.error(f"Circular reference detected: {cell_reference}")
        return 0

    visited.add(cell_reference)

    if cell_reference in updated_values:
        return updated_values[cell_reference]

    cell_value = sheet[cell_reference].value
    logging.debug(f"Evaluating cell {cell_reference}: {cell_value}")

    if isinstance(cell_value, (int, float)):
        return cell_value
    elif isinstance(cell_value, str) and cell_value.startswith('='):
        formula = cell_value[1:]  # Remove the '=' at the beginning
        if formula.startswith('M'):  # Direct reference to another cell
            return evaluate_cell(sheet, formula, updated_values, visited)
        elif '/' in formula:  # Division operation
            parts = formula.split('/')
            if len(parts) == 2:
                numerator = evaluate_cell(sheet, parts[0].strip(), updated_values, visited)
                denominator = evaluate_cell(sheet, parts[1].strip(), updated_values, visited)
                if denominator == 0:
                    logging.error(f"Division by zero in {cell_reference}")
                    return 0
                return numerator / denominator

    logging.error(f"Unable to evaluate {cell_reference}: {cell_value}")
    return 0