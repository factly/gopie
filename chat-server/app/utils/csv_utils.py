import csv
import io


def convert_rows_to_csv(rows: list[dict]) -> str:
    """
    Convert a list of dictionaries into a CSV-formatted string with special handling for certain cell values.

    Each row in the output CSV includes a "row_num" column as the first field.
    Cell values are converted as follows: `None` becomes "NULL",
    empty strings become "EMPTY_STRING",
    strings containing only whitespace become "WHITESPACE_ONLY",
    and numeric zeros become "0".
    Returns an empty string if the input list is empty.

    Parameters:
        rows (list[dict]): List of dictionaries representing table rows.

    Returns:
        str: CSV-formatted string representing the input rows.
    """
    if not rows:
        return ""

    output = io.StringIO()
    writer = csv.writer(output)

    if rows:
        headers = ["row_num"] + list(rows[0].keys())
        writer.writerow(headers)

        for idx, row in enumerate(rows, 1):
            record = [str(idx)]

            for value in row.values():
                if value is None:
                    record.append("NULL")
                elif value == "":
                    record.append("EMPTY_STRING")
                elif isinstance(value, str) and value.strip() == "":
                    record.append("WHITESPACE_ONLY")
                elif isinstance(value, (int, float)) and value == 0:
                    record.append("0")
                else:
                    record.append(str(value))

            writer.writerow(record)

    return output.getvalue()
