import click
import xarray as xr
import rasterio
from rasterio.transform import from_origin
from rasterio.crs import CRS
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles
import numpy as np

def netcdf_to_cog(netcdf_path, output_tiff):
    # Open NetCDF file
    ds = xr.open_dataset(netcdf_path)
    
    # Ensure required fields exist
    if 'lat' not in ds or 'lon' not in ds:
        raise ValueError("NetCDF file must contain 'lat' and 'lon' variables")
    
    # Extract data (assuming a variable to convert is provided)
    var_name = [var for var in ds.data_vars if var not in ['lat', 'lon']][0]  # Choose first data variable
    data = ds[var_name].values
    
    # Get latitude and longitude
    lat = ds['lat'].values
    lon = ds['lon'].values
    
    # Ensure longitude is wrapped correctly (-180 to 180)
    if lon.min() < -180 or lon.max() > 180:
        raise ValueError("Longitude values must be within -180 to 180 degrees")
    
    # Ensure latitude is in descending order
    if lat[0] < lat[-1]:
        lat = lat[::-1]
        data = np.flipud(data)
    
    # Handle NaNs
    data = np.nan_to_num(data, nan=-9999)
    
    # Define transform (assuming regularly spaced grid)
    transform = from_origin(lon.min(), lat.max(), np.abs(lon[1] - lon[0]), np.abs(lat[1] - lat[0]))
    
    # Write to initial GeoTIFF in EPSG:4326
    temp_tiff = output_tiff.replace('.tif', '_temp.tif')
    with rasterio.open(
        temp_tiff, "w",
        driver="GTiff",
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype=str(data.dtype),
        crs=CRS.from_epsg(4326),
        transform=transform,
        nodata=-9999,
    ) as dst:
        dst.write(data, 1)
    
    # Reproject to EPSG:3857 using rasterio
    reprojected_tiff = output_tiff.replace('.tif', '_3857.tif')
    with rasterio.open(temp_tiff) as src:
        orig_res_x = (src.bounds.right - src.bounds.left) / src.width
        orig_res_y = (src.bounds.top - src.bounds.bottom) / src.height

        # Convert resolution to meters for EPSG:3857 (Web Mercator)
        meters_per_degree = 111320  # Approximate at the equator
        target_res_x = orig_res_x * meters_per_degree
        target_res_y = orig_res_y * meters_per_degree

        transform, width, height = calculate_default_transform(
            src.crs, "EPSG:3857", src.width, src.height, *src.bounds, resolution=(target_res_x, target_res_y)
        )
        kwargs = src.meta.copy()
        kwargs.update({"crs": "EPSG:3857", "transform": transform, "width": width, "height": height})
        
        with rasterio.open(reprojected_tiff, "w", **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs="EPSG:3857",
                    resampling=Resampling.bilinear
                )
    
    # Convert to COG
    cog_translate(reprojected_tiff, output_tiff, cog_profiles.get("raw"), overview_resampling="average")
    click.echo(f"COG saved to {output_tiff}")

@click.command()
@click.argument("netcdf_path", type=click.Path(exists=True))
@click.argument("output_tiff", type=click.Path())
def cli(netcdf_path, output_tiff):
    "Convert a NetCDF file to a COG GeoTIFF."
    netcdf_to_cog(netcdf_path, output_tiff)

if __name__ == "__main__":
    cli()
