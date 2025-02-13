import click
import pathlib
import pandas as pd
import geopandas as gpd
from dataretrieval import nwis
from shapely.geometry import shape
from shapely.validation import make_valid, explain_validity


# Parameter codes at https://help.waterdata.usgs.gov/codes-and-parameters/parameters
# Example: water temperature in Celsius
query_site_types = 'ES,LK,ST,ST-TS,FA-TEP,FA-HP'
start_dt = '2000-01-01'
end_dt = '2024-12-31'

@click.command()
@click.option(
    '--param-codes', '-p',
    multiple=True,
    required=True,
    help="Parameter codes to query (e.g., 00010 for water temperature). Multiple codes can be provided.",
)
@click.option(
    '--usgs-parameters', '-u',
    type=click.Path(exists=True),
    default='USGSParameters.tsv',
    help="Path to the USGSParameters.tsv file.",
)
@click.option(
    '--site-types', '-s',
    type=click.Path(exists=True),
    default='SiteTypes.tsv',
    help="Path to the SiteTypes.tsv file.",
)
def fetch_tva_sites(param_codes, usgs_parameters, site_types):
    """Fetch TVA sites with specified parameter data available from NWIS."""

    # Load USGS parameters file
    try:
        usgs_df = pd.read_csv(usgs_parameters, sep='\t', comment='#')
        print("Loaded USGS parameters file successfully.")
        # print("Parameter Names:")
        # print(usgs_df['parm_nm'].to_string(index=False))
    except Exception as e:
        print(f"Error loading USGS parameters file: {e}")
        return

    # Load Site Types file
    try:
        site_types_df = pd.read_csv(site_types, sep='\t')
        site_type_map = site_types_df.set_index('Name')['Long name'].to_dict()
        print("Loaded Site Types file successfully.")
    except Exception as e:
        print(f"Error loading Site Types file: {e}")
        return

    # Define TVA bounding box parts (to avoid NWIS error for large areas)
    bounds_parts = [
        (-90.5, 32.0, -81.5, 34.0),
        (-90.5, 34.0, -81.5, 36.0),
        (-90.5, 36.0, -81.5, 38.0),
    ]

    df_parts = []
    for i, bounds in enumerate(bounds_parts):
        bbox = ','.join(map(str, bounds))
        print(f"Querying bounding box: {bbox}")
        print(f"ParamCodes: {param_codes}")
        site_response = nwis.what_sites(
            bBox=bbox,
            parameterCd=",".join(param_codes),
            siteType=query_site_types,
            siteStatus='active',
            startDt=start_dt,
            endDt=end_dt,
        )
        df, meta = site_response

        if df.empty:
            print(f"Part {i} -- no sites found")
            continue

        print(f"Part {i} -- found {len(df)} sites")
        df_parts.append(df)

    # Combine all parts into one DataFrame
    if not df_parts:
        print("No sites found")
        return

    df_sites = pd.concat(df_parts, ignore_index=True)

    # Convert to GeoDataFrame
    gdf_sites = gpd.GeoDataFrame(
        df_sites,
        geometry=gpd.points_from_xy(df_sites.dec_long_va, df_sites.dec_lat_va),
        crs='EPSG:4326',
    )

    # Save to CSV
    filename = 'tva_sites.csv'
    gdf_sites.to_csv(filename, index=False)
    print(f"Saved all TVA sites to {filename}")

    # Load TVA multipolygon from geojson and filter sites within its geometry

    tva_path = 'tva.geojson'
    try:
        tva_mpoly = gpd.read_file(tva_path)

        # Validate geometries
        def validate_geometry(geom):
            if not geom.is_valid:
                print(f"Invalid geometry: {explain_validity(geom)}")
                return make_valid(geom)
            return geom

        tva_mpoly["geometry"] = tva_mpoly["geometry"].apply(validate_geometry)
    except Exception as e:
        print(f"Error reading or processing the GeoJSON file: {e}")
        return

    tva_polys = list(tva_mpoly.explode().geometry)

    for i, poly in enumerate(tva_polys):
        gdf_sites[f'within_poly_{i}'] = gdf_sites.geometry.within(poly)
        print(gdf_sites[f'within_poly_{i}'].value_counts())


    # Filter sites within the TVA polygon
    tva_sites = gdf_sites[gdf_sites['within_poly_0']]
    tva_sites = tva_sites.drop(columns=[f'within_poly_{i}' for i in range(len(tva_polys))])

    # Add site_type_name property
    tva_sites['site_type_name'] = tva_sites['site_tp_cd'].map(site_type_map)

    # Save filtered sites to CSV
    filename = 'filtered_tva_sites.csv'
    tva_sites.to_csv(filename, index=False)
    print(f"Saved filtered TVA sites to {filename}")

    # Save GeoJSON with specific fields
    tva_sites_geojson = tva_sites.rename(columns={
        'site_no': 'site_number',
        'station_nm': 'name',
        'site_tp_cd': 'site_type_code',
        'huc_cd': 'huc_code'
    })
    tva_sites_geojson = tva_sites_geojson[[
        'site_number', 'name', 'site_type_code', 'huc_code', 'site_type_name', 'geometry'
    ]]

    geojson_filename = 'filtered_tva_sites.geojson'
    tva_sites_geojson.to_file(geojson_filename, driver='GeoJSON')
    print(f"Saved filtered TVA sites GeoJSON to {geojson_filename}")

if __name__ == '__main__':
    fetch_tva_sites()

