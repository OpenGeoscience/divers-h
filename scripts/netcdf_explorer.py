import click
import xarray as xr
from PIL import Image
import numpy as np
import os
import json
import matplotlib.pyplot as plt
from matplotlib import cm

@click.group()
def cli():
    """A CLI tool for processing netCDF files."""
    pass

@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("output_json", type=click.Path())
def describe(file_path, output_json):
    """
    Analyze the structure of a netCDF file and output a JSON description.

    FILE_PATH: Path to the input netCDF file.
    OUTPUT_JSON: Path to save the output JSON file.
    """
    try:
        ds = xr.open_dataset(file_path)

        description = {
            "dimensions": {dim: int(len(ds[dim])) for dim in ds.dims},  # Ensure values are standard Python integers
            "variables": {},
            "attributes": {key: str(value) for key, value in ds.attrs.items()},  # Convert attributes to strings if needed
        }

        for var_name, variable in ds.variables.items():
            var_info = {
                "dimensions": list(variable.dims),
                "dtype": str(variable.dtype),
                "attributes": {key: str(value) for key, value in variable.attrs.items()},
            }

            # Calculate min and max values if the variable has numeric data
            try:
                var_min = float(variable.min().values) if variable.size > 0 else None
                var_max = float(variable.max().values) if variable.size > 0 else None
                var_info["min"] = var_min
                var_info["max"] = var_max
            except Exception:
                var_info["min"] = 0
                var_info["max"] = variable.size

            description["variables"][var_name] = var_info

        # Write the description to a JSON file
        with open(output_json, "w") as f:
            json.dump(description, f, indent=4)

        click.echo(f"Description written to {output_json}")
    except Exception as e:
        click.echo(f"Error processing file: {e}")

@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("output_folder", type=click.Path())
@click.option("--variable", required=True, help="Variable to visualize.")
@click.option("--slice-dim", required=True, help="Dimension to slide over.")
@click.option("--step", type=int, default=1, help="Step size for sliding.")
@click.option("--start", type=int, default=0, help="Start index for sliding.")
@click.option("--end", type=int, help="End index for sliding. Defaults to the last index.")
@click.option("--cmap", default="viridis", help="Matplotlib colormap to use (default: viridis).")
@click.option("--additional-dims", type=str, default="", help="Comma-separated list of indices for additional dimensions.")
def generate_images(file_path, output_folder, variable, slice_dim, step, start, end, cmap, additional_dims):
    """
    Generate PNG images for a moving slice along a specified dimension.

    FILE_PATH: Path to the input netCDF file.
    OUTPUT_FOLDER: Folder to save the images.
    """
    try:
        # Open the NetCDF file
        ds = xr.open_dataset(file_path)

        # Check if the specified variable and dimension exist
        if variable not in ds:
            raise ValueError(f"Variable '{variable}' not found in the dataset.")
        if slice_dim not in ds.dims:
            raise ValueError(f"Dimension '{slice_dim}' not found in the dataset.")

        # Extract the data for the specified variable
        data_var = ds.get(variable)
        variables = data_var.dims
        print(variables)
        dim_size = ds.dims.get(slice_dim)
        end = dim_size if end is None else end

        base_variables = ('latitude', 'longitude', slice_dim)
        user_dims = additional_dims.split(",") if additional_dims else []

        extra_variables = []
        for internal_variable in variables:
            if internal_variable not in base_variables:
                index = 0
                extra_variables.append({'variable': internal_variable, 'index': 3})

        print(f'Extra Variables: {extra_variables}')
        additional_dims = additional_dims.split(",") if additional_dims else []
        additional_indices = [int(i) for i in additional_dims] if additional_dims else [0] * (data_var.ndim - 1)

        # If the variable has more than 3 dimensions, we slice over the additional dimensions using the provided or default indices

        # Create output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)

        # Get the colormap from matplotlib
        try:
            colormap = cm.get_cmap(cmap)
        except ValueError:
            raise ValueError(f"Invalid colormap '{cmap}'. Please use a valid matplotlib colormap.")

        # Iterate through the dimension to create slices and save images
        for i in range(start, end, step):
            # Extract a slice along the specified dimension
            indexers = { slice_dim: i }
            for item in extra_variables:
                indexers[item['variable']] = item['index'] 
            slice_data = data_var.isel(indexers).values

            # Normalize data to 0-1 for colormap application
            slice_min = np.nanmin(slice_data)
            slice_max = np.nanmax(slice_data)
            normalized_data = (slice_data - slice_min) / (slice_max - slice_min)

            # Apply the colormap
            colored_data = colormap(normalized_data)  # Returns RGBA values
            colored_data = (colored_data[:, :, :3] * 255).astype(np.uint8)  # Drop alpha, scale to 0-255

            # Convert to an RGB image using PIL
            image = Image.fromarray(colored_data, mode="RGB")

            # Save the image
            output_path = os.path.join(output_folder, f"{variable}_{slice_dim}_{i}.png")
            image.save(output_path)
            click.echo(f"Image saved: {output_path}")

        click.echo("Image generation completed.")

    except Exception as e:
        click.echo(f"Error processing file: {e}")

if __name__ == "__main__":
    cli()
