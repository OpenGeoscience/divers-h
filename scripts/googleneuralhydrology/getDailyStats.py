import click
import json
import pathlib
import pandas as pd
from dataretrieval import nwis
import numpy as np
import time
import calendar
import datetime

def get_unix_time(row, year_index, month_index, day_index):
    if year_index is not None:
        year = int(row[year_index])
    else:
        year = 1970
    if month_index is not None:
        month = int(row[month_index])
    else:
        month = 1
    if day_index is not None:
        day = int(row[day_index])
    else:
        day = 1
    if month < 1 or month > 12:
        month = 1
    if day < 1 or day > 31:
        day = 1

    return calendar.timegm(time.strptime(f"{year}-{month}-{day}", "%Y-%m-%d"))
# Define the function for fetching and formatting data
@click.command()
@click.option('-p', '--param-codes', default=['00060'], multiple=True, required=True, help="List of parameter codes to query.")
@click.option('--input', required=True, type=click.Path(exists=True), help="JSON file containing an array of site numbers.")
@click.option('--start-date', default='1989-10-01', help="Start date for the data query.")
@click.option('--end-date', default='1999-09-30', help="End date for the data query.")
@click.option('--output', default='dailyStats.json', help="Output JSON file where the results will be saved.")
@click.option('--usgs-parameters', default='../nwis/USGSParameters.tsv', type=click.Path(exists=True), help="Path to the USGSParameters.tsv file.")
def fetch_data(param_codes, input, start_date, end_date, output, usgs_parameters):
    """Fetch data from NWIS and save it in a JSON format with descriptions for each table."""
    # Load the USGS parameters file
    usgs_df = pd.read_csv(usgs_parameters, sep='\t', comment='#')
    # Create a dictionary mapping parameter codes to their descriptions
    param_desc = dict(zip(usgs_df['parm_cd'], usgs_df['parm_nm']))

    # Load geojson file
    with open(input, 'r') as f:
        site_loaded = json.load(f)  # Expecting a JSON array of site numbers

    site_numbers = [str(item) for item in site_loaded]
    # Split the site numbers into chunks of 10 (because NWIS allows a max of 10 sites per request)
    def split_list(l):
        n = 10
        for i in range(0, len(l), n):
            yield l[i:i + n]
    
    site_lists = list(split_list(site_numbers))

    # Prepare the result container
    result = {}

    # Fetch data for each site and each report type (monthly, daily, annual)
    report_types = ['daily']  # Assuming you want monthly, daily, and annual reports
    
    for report_type in report_types:
        for i, site_list in enumerate(site_lists):
            try:
                response = nwis.get_dv(
                    sites=site_list,
                    start=start_date,
                    end=end_date,
                    parameterCd=",".join(param_codes),
                )
                df, meta = response
            except Exception as e:
                print(f"Error fetching {report_type} data for sites {site_list}: {e}")
                continue
            df, meta = response

            # Replace NaN values with empty strings
            print(df.index)
            df.index = pd.MultiIndex.from_tuples([(site, pd.to_datetime(dt)) for site, dt in df.index], 
                                                names=['site_number', 'datetime'])

            # Extract the datetime level from the MultiIndex
            datetime_index = df.index.get_level_values("datetime")

            # Add new columns
            df["date_str"] = datetime_index.strftime("%Y-%m-%d")  # Convert to 'YYYY-MM-DD' string
            df["year_nu"] = datetime_index.year  # Extract year
            df["month_nu"] = datetime_index.month  # Extract month
            df["day_nu"] = datetime_index.day  # Extract day
            df["unix_time"] = datetime_index.astype(int) // 10**9  # Convert to Unix timestamp
            df["site_no"] = df.index.get_level_values("site_number")



            # Add the data to the result dictionary with site_number as the key
            for site_number in site_list:
                site_data = df[df['site_no'] == site_number]
                if not site_data.empty:
                    # Remove the 'ts_id' column if it exists
                    site_data = site_data.drop(columns=['site_no', 'loc_web_ds'], errors='ignore')
                    
                    # Create a description of the parameters
                    param_headers = []
                    header = site_data.columns.tolist()
                    for item in header:
                        print(item)
                        if item.endswith('_Mean_cd'):
                            site_data = site_data.drop(columns=[item], errors='ignore')
                            header.remove(item)
                        if item.endswith('_Mean'):
                            param_headers.append(item)
                    unique_param_codes = [item.replace('_Mean', '') for item in param_headers]
                    param_names = [param_desc.get(code, 'Unknown parameter') for code in unique_param_codes]
                    description = f"This is a table of the mean {report_type} values for the following parameters: {', '.join([f'{code} - {name}' for code, name in zip(unique_param_codes, param_names)])}"


                    # Prepare table object
                    rows = site_data.values.tolist()

                    table_object = {
                        "name": f"{site_number}_{report_type}",
                        "description": description,
                        "type": f'USGS_gauge_{report_type}_{"_".join(param_codes)}',
                        "header": header,
                        "summary": generate_summary(site_data, param_desc, site_data.columns.tolist()),
                        "rows": rows,
                    }
                    if site_number not in result:
                        result[site_number] = []
                    
                    result[site_number].append(table_object)
            
            print(f"Fetched {report_type} data for {len(site_list)} sites.")

    # Save the result to the output file as JSON
    with open(output, 'w') as f:
        json.dump(result, f, indent=4)

    print(f"Results saved to {output}.")

limit = 100
def generate_summary(df, param_desc, rows):
    """Generate a summary object for the table with column type and stats, focusing on unique parameter_cd."""
    summary = {}
    for header in rows:
        if header.endswith('_Mean'):
            if header not in summary.keys():
                summary[header] = {'type':'parameter_cd'}
            parameter_cd = header.replace('_Mean', '')
            param_data = df[df[header] == header]
            value_col = df[header]
            summary[header][parameter_cd] = {
                "parameter_cd": parameter_cd,
                "parameter_name": param_desc.get(parameter_cd, 'Unknown parameter'),
                "min": float(value_col.min()),
                "max": float(value_col.max()),
                "mean": float(value_col.mean())
            }
        # Iterate over each unique parameter_cd
        elif header == 'parameter_cd':
            if header not in summary.keys():
                summary[header] = {'type':'parameter_cd'}
            for parameter_cd in df['parameter_cd'].unique():
                param_data = df[df['parameter_cd'] == parameter_cd]
                
                # Assuming the 'value' column contains the actual data values
                value_col = param_data['mean_va']

                # Calculate the min, max, and mean for each parameter_cd
                summary[header][parameter_cd] = {
                    "parameter_cd": parameter_cd,
                    "parameter_name": param_desc.get(parameter_cd, 'Unknown parameter'),
                    "min": float(value_col.min()),
                    "max": float(value_col.max()),
                    "mean": float(value_col.mean())
                }
        else:  # Calculate type/min/max and other fields

            if header not in summary.keys():
                summary[header] = {'type': None, 'values': set(), 'value_count': 0}
                parameter_cd = param_desc.get(header, None)
                if parameter_cd:
                    summary[header]["description"] = parameter_cd[0] if isinstance(parameter_cd, tuple) else parameter_cd
            for value in df[header].unique():
                if isinstance(value, bool):
                    summary[header]['type'] = 'bool'
                    summary[header]['value_count'] += 1
                elif isinstance(value, (int, float, np.float64, np.int32, np.int64)):
                    summary[header]['type'] = 'number'
                    summary[header]['value_count'] += 1
                    if 'min' not in summary[header] or value < summary[header]['min']:
                        if np.isnan(float(value)) or value is None and summary[header].get('min', None) is None:
                            summary[header]['min'] = float('inf')
                        else:
                            summary[header]['min'] = float(value)
                    if 'max' not in summary[header] or value > summary[header]['max']:
                        if np.isnan(float(value)) or value is None and summary[header].get('max', None) is None:
                            summary[header]['max'] = float('-inf')
                        else:
                            summary[header]['max'] = float(value)
                elif isinstance(value, str):
                    if 'values' not in summary[header]:
                        summary[header]['values'] = set()
                    summary[header]['value_count'] += 1
                    summary[header]['type'] = 'string'
                    summary[header]['values'].add(value)
    for header in summary.keys():
        if summary[header]['type'] is None:
            summary[header]['type'] = 'unknown'
            del summary[header]['values']
            continue
        if summary[header]['type'] == 'number':
            if summary[header]['value_count'] == 1:
                summary[header]['values'] = summary[header].get('min', summary[header].get('max'))
                del summary[header]['min']
                del summary[header]['max']
            elif summary[header]['min'] == summary[header]['max']:
                val = summary[header]['min']
                del summary[header]['values']
                del summary[header]['min']
                del summary[header]['max']
                summary[header]['static'] = True
                summary[header]['value'] = val
            else:
                if np.isnan(summary[header]['min']):
                    summary[header]['min'] = None
                if np.isnan(summary[header]['max']):
                    summary[header]['max'] = None
                del summary[header]['values']
        elif (
            summary[header]['type'] == 'string'
            and 'values' in summary[header]
            and not summary[header].get('searchable')
        ):
            summary[header]['values'] = sorted(summary[header]['values'])
            if len(summary[header]['values']) >= limit:
                summary[header]['searchable'] = True
                summary[header]['unique'] = len(summary[header]['values'])
                del summary[header]['values']
        elif summary[header]['type'] == 'bool':
            del summary[header]['values']
    check_json_validity(summary)
    return summary

def check_json_validity(obj, path="root"):
    valid_types = (str, int, float, bool, type(None), list, dict)
    
    if isinstance(obj, (np.float64, np.float128, np.int64, np.int32)):
        print(f"Invalid type at {path}: {type(obj).__name__} (Value: {obj})")
        return False
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            check_json_validity(value, path=f"{path}.{key}")
    
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            check_json_validity(item, path=f"{path}[{idx}]")
    
    elif not isinstance(obj, valid_types):
        print(f"Invalid type at {path}: {type(obj).__name__} (Value: {obj})")
        return False
    

if __name__ == '__main__':
    fetch_data()

