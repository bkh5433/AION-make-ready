import logging

logging.basicConfig(filename='excel_generator.log', level=logging.INFO)


def evaluate_formula(sheet, cell, updated_values):
    formula = sheet[cell].value
    logging.debug(f"Evaluating formula in {cell}: {formula}")

    if isinstance(formula, str) and formula.startswith('='):
        formula = formula[1:]  # Remove the '=' at the beginning
        parts = formula.split('/')
        logging.debug(f"Formula parts: {parts}")

        if len(parts) == 2:
            try:
                numerator_cell = parts[0].strip()
                denominator_cell = parts[1].strip()
                numerator = get_cell_value(sheet, numerator_cell, updated_values)
                denominator = get_cell_value(sheet, denominator_cell, updated_values)

                logging.debug(f"Numerator ({numerator_cell}): {numerator}")
                logging.debug(f"Denominator ({denominator_cell}): {denominator}")

                if denominator == 0:
                    logging.error("Division by zero encountered")
                    return 0

                result = numerator / denominator
                logging.debug(f"Calculation result: {result}")
                return result
            except Exception as e:
                logging.error(f"Error in formula evaluation: {e}")
                return 0

    return get_cell_value(sheet, cell, updated_values)


def get_cell_value(sheet, cell_reference, updated_values):
    if cell_reference in updated_values:
        return updated_values[cell_reference]

    cell_value = sheet[cell_reference].value
    logging.debug(f"Getting value for cell {cell_reference}: {cell_value}")

    try:
        return float(cell_value) if cell_value is not None else 0
    except ValueError:
        logging.error(f"Could not convert {cell_value} to float in cell {cell_reference}")
        return 0