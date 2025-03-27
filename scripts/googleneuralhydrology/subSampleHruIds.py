import json
import click
import dataretrieval.nwis as nwis
import pandas as pd
import geopandas as gpd
import us

COUNTY_SHP_URL = "https://www2.census.gov/geo/tiger/TIGER2022/COUNTY/tl_2022_us_county.zip"
counties = gpd.read_file(COUNTY_SHP_URL)[["STATEFP", "COUNTYFP", "NAME"]]

site_types_df = pd.read_csv('../nwis/SiteTypes.tsv', sep='\t')
site_type_map = site_types_df.set_index('Name')['Long name'].to_dict()

def split_list(l, n=10):
    """Split a list into chunks of size n."""
    for i in range(0, len(l), n):
        yield l[i:i + n]

def get_county_name(state_cd, county_cd):
    """Convert state and county FIPS codes to a county name."""
    state_cd = str(state_cd).zfill(2)  # Ensure it's two-digit
    county_cd = str(county_cd).zfill(3)  # Ensure it's three-digit
    match = counties[(counties["STATEFP"] == state_cd) & (counties["COUNTYFP"] == county_cd)]
    
    return match.iloc[0]["NAME"] if not match.empty else None

def get_state_abbr(state_cd):
    state = us.states.lookup(str(state_cd))
    return state.abbr if state else None

def get_usgs_gauge_data(hru_ids):
    """Retrieve USGS gauge information for a list of HRU IDs in batches."""
    usgs_data = {}
    
    for site_batch in split_list(hru_ids, 10):  # Process in batches of 10
        try:
            response = nwis.get_info(sites=site_batch)
            sites, meta = response
            if sites is None or "site_no" not in sites:
                continue

            # Convert all values to JSON-serializable types
            sites = sites.map(lambda x: x.item() if isinstance(x, (pd.Int64Dtype, pd.Float64Dtype, pd.Timestamp)) else x)
            
            for _, row in sites.iterrows():
                site_id = row.get("site_no")
                elevation = row.get("alt_va")
                
                # Replace NaN elevation values with -1
                if pd.isna(elevation):
                    elevation = -1

                usgs_data[site_id] = {
                    "usgs_site_id": site_id,
                    "name": row.get("station_nm"),
                    "latitude": row.get("dec_lat_va"),
                    "longitude": row.get("dec_long_va"),
                    "site_type": site_type_map.get(row.get("site_tp_cd"), 'Unknown'),
                    "agency": row.get("agency_cd"),
                    "state": get_state_abbr(str(row.get("state_cd")).zfill(2)),
                    "county": get_county_name(str(row.get("state_cd")).zfill(2), str(row.get("county_cd")).zfill(3)),
                    "elevation": elevation,
                }
        except Exception as e:
            click.echo(f"Error retrieving USGS gauge data: {e}")
            continue
    
    return usgs_data

@click.command()
@click.argument('geojson_file', type=click.Path(exists=True))
@click.argument('id_list_file', type=click.Path(exists=True))
@click.option('--output', default='matching_hru_ids.geojson', help='Output GeoJSON filename')
@click.option('--area_output', default='HRU_AREA_MAP.json', help='Output JSON filename for HRU area mapping')
def filter_geojson(geojson_file, id_list_file, output, area_output):
    """Filter features from a GEOJSON file based on matching HRU IDs and add USGS gauge data."""
    
    # Load the list of HRU IDs
    with open(id_list_file, 'r') as f:
        try:
            hru_ids = {str(id).zfill(8) for id in json.load(f)}  # Ensure zero-padded strings
        except (ValueError, TypeError) as e:
            click.echo(f"Error reading ID list file: {e}")
            return

    # Load the GeoJSON file
    with open(geojson_file, 'r') as f:
        geojson_data = json.load(f)
    
    if 'features' not in geojson_data:
        click.echo("Invalid GeoJSON file: No 'features' key found.")
        return

    # Fetch USGS data for all HRU IDs in batches
    usgs_data = get_usgs_gauge_data(list(hru_ids))

    # Filter features and merge USGS data
    filtered_features = []
    hru_area_map = {}  # Dictionary to store HRU ID -> AREA mapping

    for feature in geojson_data['features']:
        if 'properties' in feature and 'hru_id' in feature['properties']:
            hru_id = str(feature['properties']['hru_id']).zfill(8)
            if hru_id in hru_ids:
                feature['properties']['hru_id'] = hru_id  # Ensure consistent formatting
                
                # Store AREA property in the HRU area map
                if 'AREA' in feature['properties']:
                    hru_area_map[hru_id] = feature['properties']['AREA']
                
                # Add a new point feature for USGS gauge data if available
                if hru_id in usgs_data:
                    gauge_info = usgs_data[hru_id]
                    point_feature = {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [gauge_info["longitude"], gauge_info["latitude"]]
                        },
                        "properties": gauge_info
                    }
                    feature['properties']['Name'] = gauge_info['name']
                    filtered_features.append(point_feature)
                filtered_features.append(feature)  # Keep original polygon

    # Create new GeoJSON structure
    filtered_geojson = {
        "type": "FeatureCollection",
        "features": filtered_features
    }

    # Write the output files
    with open(output, 'w') as f:
        json.dump(filtered_geojson, f, indent=2)
    
    with open(area_output, 'w') as f:
        json.dump(hru_area_map, f, indent=2)

    click.echo(f"Filtered GeoJSON saved to {output}")
    click.echo(f"HRU Area mapping saved to {area_output}")

if __name__ == '__main__':
    filter_geojson()
