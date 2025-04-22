import os
import csv
import json
import click
from datetime import datetime
from collections import defaultdict

variable_mapper = {
    "Gridded_1_linear": "r4i1p1f1 Linear Regression",
    "Gridded_1_ridge": "r4i1p1f1 Ridge Regression",
    "Gridded_1_rf": "r4i1p1f1 Random Forest",
    "Gridded_1_svr": "r4i1p1f1 Support Vector Regression",
    "Gridded_2_linear": "r10i1p1f1 Linear Regression",
    "Gridded_2_ridge": "r10i1p1f1 Ridge Regression",
    "Gridded_2_rf": "r10i1p1f1 Random Forest",
    "Gridded_2_svr": "r10i1p1f1 Support Vector Regression",
    "Gridded_3_linear": "r11i1p1f1 Linear Regression",
    "Gridded_3_ridge": "r11i1p1f1 Ridge Regression",
    "Gridded_3_rf": "r11i1p1f1 Random Forest",
    "Gridded_3_svr": "r11i1p1f1 Support Vector Regression",
}

def detect_type(values):
    is_number = True
    numbers = []

    for v in values:
        try:
            num = float(v)
            numbers.append(num)
        except (ValueError, TypeError):
            is_number = False

    if is_number:
        return {
            "type": "number",
            "value_count": len(numbers),
            "min": min(numbers),
            "max": max(numbers)
        }
    else:
        return {
            "type": "string",
            "value_count": len(values),
            "searchable": True,
            "unique": len(set(values))
        }

@click.command()
@click.argument('main_folder', type=click.Path(exists=True))
@click.argument('output_file', type=click.File('w'))
def process_folder(main_folder, output_file):
    result = defaultdict(list)

    for folder_name in os.listdir(main_folder):
        subfolder_path = os.path.join(main_folder, folder_name)
        if not os.path.isdir(subfolder_path):
            continue

        for filename in os.listdir(subfolder_path):
            if not filename.lower().endswith('.csv'):
                continue

            file_path = os.path.join(subfolder_path, filename)
            with open(file_path, newline='', encoding='latin1') as csvfile:
                reader = csv.DictReader(csvfile)
                original_headers = reader.fieldnames
                if 'site_no' not in original_headers or 'datetime' not in original_headers:
                    click.echo(f"Skipping {file_path}: Missing 'site_no' or 'datetime'")
                    continue

                # Map headers if present in variable_mapper
                mapped_headers = [variable_mapper.get(h, h) for h in original_headers]
                header_map = dict(zip(original_headers, mapped_headers))

                data_by_site = defaultdict(list)
                column_values = defaultdict(list)
                rows = []
                min_date, max_date = None, None

                for row in reader:
                    site_no = str(row['site_no']).zfill(8)
                    dt_str = row['datetime']
                    try:
                        dt_obj = datetime.strptime(dt_str, "%Y-%m-%d")
                        unix_time = int(dt_obj.timestamp())
                    except ValueError:
                        click.echo(f"Skipping row with invalid datetime: {dt_str}")
                        continue

                    # Add unix_time
                    row['unix_time'] = unix_time

                    # Update date tracking
                    if not min_date or dt_obj < min_date:
                        min_date = dt_obj
                    if not max_date or dt_obj > max_date:
                        max_date = dt_obj

                    processed_row = {}
                    for key, value in row.items():
                        mapped_key = header_map.get(key, key)
                        try:
                            if key != 'site_no':
                                float_val = float(value)
                                if value.strip() == "" or value.strip().lower() == "nan":
                                    raise ValueError
                                value = float_val
                        except (ValueError, TypeError, AttributeError):
                            pass
                        processed_row[mapped_key] = value
                        column_values[mapped_key].append(value)

                    full_headers = [header_map.get(h, h) for h in original_headers] + ['unix_time']
                    row_values = [processed_row.get(h, "") for h in full_headers]
                    rows.append(row_values)
                    data_by_site[site_no].append(processed_row)

                # Summarize columns
                summary = {}
                for col, values in column_values.items():
                    summary[col] = detect_type(values)

                for site_no in data_by_site:
                    name = f"{site_no}_{folder_name}"
                    entry = {
                        "name": name,
                        "description": f"Site {site_no} from folder {folder_name}. "
                                       f"Date range: {min_date.date()} to {max_date.date()}. "
                                       f"Total records: {len(data_by_site[site_no])}.",
                        "type": folder_name,
                        "header": full_headers,
                        "summary": summary,
                        "rows": rows
                    }
                    result[site_no].append(entry)

    json.dump(result, output_file, indent=2)
    click.echo(f"JSON output written to {output_file.name}")

if __name__ == '__main__':
    process_folder()
