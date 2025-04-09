import click
import json
import pathlib
import pandas as pd
from dataretrieval import nwis
import numpy as np
import time
import calendar
import datetime
import os

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

@click.command()
@click.option('-p', '--param-codes', default=['00060'], multiple=True, required=True, help="List of parameter codes to query.")
@click.option('--input', required=True, type=click.Path(exists=True), help="JSON file containing an array of site numbers.")
@click.option('--start-date', default='1989-10-01', help="Start date for the data query.")
@click.option('--end-date', default='1999-09-30', help="End date for the data query.")
@click.option('--output', default='./dailyStats.json', help="Output JSON file where the results will be saved.")
@click.option('--usgs-parameters', default='../nwis/USGSParameters.tsv', type=click.Path(exists=True), help="Path to the USGSParameters.tsv file.")
@click.option('--area-mapping', default='./HRU_AREA_MAP.json', type=click.Path(exists=True), help="Path to the HRU area mapping file.")
def fetch_data(param_codes, input, start_date, end_date, output, usgs_parameters, area_mapping):
    """Fetch data from NWIS and save it in a JSON format with descriptions for each table."""
    
    # Load the USGS parameters file
    usgs_df = pd.read_csv(usgs_parameters, sep='\t', comment='#')
    param_desc = dict(zip(usgs_df['parm_cd'], usgs_df['parm_nm']))

    with open(input, 'r') as f:
        site_loaded = json.load(f)  # Expecting a JSON array of site numbers

    with open(area_mapping, 'r') as f:
        area_map = json.load(f)  # Expecting a JSON array of site numbers

    site_numbers = [str(item) for item in site_loaded]

    if os.path.exists(output):
        with open(output, 'r') as f:
            processed_sites = json.load(f)  # Expecting a JSON array of site numbers

        loaded_sites = processed_sites.keys()
        site_numbers = [site for site in site_numbers if site not in loaded_sites]
    
    # Split the site numbers into chunks of 10 (because NWIS allows a max of 10 sites per request)
    def split_list(l):
        n = 10
        for i in range(0, len(l), n):
            yield l[i:i + n]
    
    site_lists = list(split_list(site_numbers))

    # Open output file in append mode
    with open(output, 'a') as f:
        # Fetch data for each site and each report type (daily)
        report_types = ['daily']
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

                # Prepare data for writing
                site_data = process_site_data(df, meta, area_map, site_list, param_codes, param_desc)

                # Append processed data to file incrementally
                with open(output, 'a') as f:
                    for entry in site_data:
                        json_str = json.dumps(entry, default=lambda x: None if isinstance(x, float) and np.isnan(x) else x, separators=(',', ':'))
                        f.write(f"{json_str}\n")  # Write each object on a single line, each key on a new line

                print(f"Fetched {report_type} data for {len(site_list)} sites.")
                
    print(f"Results saved to {output}.")

def process_site_data(df, meta, area_map, site_list, param_codes, param_desc):
    """Process the data for a single site list."""
    valid_index_tuples = []
    for site, dt in df.index:
        try:
            valid_dt = pd.to_datetime(dt, errors='raise')  # Raise an error for invalid dates
            valid_index_tuples.append((site, valid_dt))
        except Exception as e:
            print(f"Skipping site {site} due to invalid date: {dt} ({e})")

    if valid_index_tuples:
        df.index = pd.MultiIndex.from_tuples(valid_index_tuples, names=['site_number', 'datetime'])
    else:
        print("No valid sites found due to date errors. Skipping further processing.")
        return []

    # Add additional columns and process data
    datetime_index = df.index.get_level_values("datetime")
    df["date_str"] = datetime_index.strftime("%Y-%m-%d")
    df["year_nu"] = datetime_index.year
    df["month_nu"] = datetime_index.month
    df["day_nu"] = datetime_index.day
    df["unix_time"] = datetime_index.astype(int) // 10**9
    df["site_no"] = df.index.get_level_values("site_number")

    # Prepare and append the data for each site
    site_data = []
    endsWith = ['date_str', 'year_nu', 'month_nu', 'day_nu', 'unix_time', '00060_Mean']
    for site_number in site_list:
        site_data_frame = df[df['site_no'] == site_number]
        area = area_map.get(str(site_number))

        if not site_data_frame.empty:
            site_data_frame = site_data_frame.drop(columns=['site_no', 'loc_web_ds'], errors='ignore')
            param_headers = [col for col in site_data_frame.columns if col.endswith('_Mean')]
            columns = site_data_frame.columns.tolist()
            for col in columns:
                if col not in endsWith:
                    site_data_frame = site_data_frame.drop(columns=[col])
            param_names = [param_desc.get(code.replace('_Mean', ''), 'Unknown parameter') for code in param_headers]

            site_data_frame = site_data_frame.where(pd.notna(site_data_frame), 0)

            # Prepare table object for the site
            table_object = {
                "name": f"{site_number}_daily",
                "description": "This is a table of mean daily values for USGS gauges converted to mm/d for the whole watershed",
                "type": f'USGS_gauge_daily_{"_".join(param_codes)}',
                "header": site_data_frame.columns.tolist(),
                "summary": generate_summary(site_data_frame, param_desc, site_data_frame.columns.tolist()),
                "rows": site_data_frame.values.tolist(),
            }
            site_data.append(table_object)
    
    return site_data

def generate_summary(df, param_desc, rows):
    """Generate a summary object for the table."""
    summary = {}
    for header in rows:
        if header.endswith('00060_Mean'):
            summary[header] = {'type': 'parameter_cd', 'parameter_name': 'USGS cuft/s converted to mm/d for CAMELS data'}
        elif header.endswith('_Mean'):
            summary[header] = {'type': 'parameter_cd', 'parameter_name': param_desc.get(header.replace('_Mean', ''), 'Unknown parameter')}
    return summary

if __name__ == '__main__':
    fetch_data()
