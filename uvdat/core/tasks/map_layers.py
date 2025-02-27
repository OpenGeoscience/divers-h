from collections import defaultdict
from functools import partial
import json
import logging
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

from django.contrib.gis.geos import GEOSGeometry, LineString, MultiLineString
from django.core.files.base import ContentFile
import fiona
import geopandas
import pandas
import rasterio
from rasterio.enums import ColorInterp  # Import ColorInterp from rasterio
import shapefile
from shapely.geometry import Point
from shapely.wkt import loads as wkt_loads

from uvdat.core.models import (
    RasterMapLayer,
    VectorFeatureRowData,
    VectorFeatureTableData,
    VectorMapLayer,
)
from uvdat.core.models.map_layers import VectorFeature

logger = logging.getLogger(__name__)

SHAPEFILE_EXTS = ['.shp', '.shx', '.dbf', '.prj']


def calculate_styling(geojson_data, style_options):
    if style_options:
        return style_options

    geometry_types = set()
    has_render_height = False
    for _index, feature in enumerate(geojson_data.iterfeatures()):
        geometry_type = feature.get('geometry', {}).get('type', False)
        render_height = feature.get('properties', {}).get('render_height', False)
        if render_height is not False:
            has_render_height = True
        if geometry_type:
            geometry_types.add(geometry_type)

    updated_style_options = {
        'layers': {
            'circle': {'color': '#888888', 'enabled': False, 'size': 3},
            'line': {'color': '#000000', 'enabled': False, 'size': 1},
            'fill': {'color': '#888888', 'enabled': False},
            'text': {'color': '#888888', 'enabled': False},
            'fill-extrusion': {'color': '#888888', 'enabled': False},
        }
    }
    if any(item in ['Point', 'MultiPoint'] for item in geometry_types):
        updated_style_options['layers']['circle'] = {'enabled': True, 'color': '#888888'}
    if any(
        item in ['LineString', 'MultiLineString', 'Polygon', 'MultiPolygon']
        for item in geometry_types
    ):
        updated_style_options['layers']['line'] = {'enabled': True, 'color': '#000000', 'size': 1}
    if any(item in ['Polygon', 'MultiPolygon'] for item in geometry_types):
        updated_style_options['layers']['fill'] = {'enabled': True, 'color': '#888888'}
    if has_render_height:
        updated_style_options['layers']['fill-extrusion'] = {'enabled': True, 'color': '#CCCCCC'}
    # make the largest geometry type single selectable with the selectColor being cyan
    enabled = [
        layer for layer, options in updated_style_options['layers'].items() if options['enabled']
    ]

    for layer in ['fill-extrusion', 'fill', 'line']:
        if layer in enabled:
            updated_style_options['layers'][layer]['selectColor'] = '#00FFFF'
            updated_style_options['layers'][layer]['selectable'] = 'singleSelect'
            break
    if 'circle' in enabled:
        updated_style_options['layers']['circle']['selectColor'] = '#00FFFF'
        updated_style_options['layers']['circle']['selectable'] = 'singleSelect'

    return updated_style_options


def is_list_of_str(lst) -> bool:
    """Is a given variable a list of strings."""
    if not isinstance(lst, list):
        return False
    return all(isinstance(v, str) for v in lst)


def filter_dict(row: dict, include: list[str] | str | None, exclude: list[str] | None) -> dict:
    """Filter a dictionary according to the include/exclude spec.

    If `include` is "*", then include all keys (except for those in `exclude`).
    """
    if include is None:
        return {}
    exclude = exclude or []

    def test_membership(key: str) -> bool:
        return key not in exclude and (include == '*' or key in include)

    return {key: value for key, value in row.items() if test_membership(key)}


def wkt_geom_from_dict(wkt_col: str, metadata_cols: list[str] | str | None, row: dict):
    """Parse a WKT column and metadata columns.

    Returns: (Geometry, metadata_dict)
    """
    return wkt_loads(row[wkt_col]), filter_dict(row, metadata_cols, [wkt_col])


def point_geom_from_dict(
    lon_col: str, lat_col: str, metadata_cols: list[str] | str | None, row: dict
):
    """Parse lon/lat columns and metadata columns.

    Returns: (Point Geometry, metadata_dict)
    """
    return Point(float(row[lon_col]), float(row[lat_col])), filter_dict(
        row, metadata_cols, [lon_col, lat_col]
    )


def get_csv_row_parser(spec):
    """Return a function that will parse a dict-like object given a spec.

    Parser spec:
    {
      "columns": {
        // must have one of either: "geometry_wkt", "point_lat" & "point_lon"

        // the column name containing the well-known-text string
        "geometry_wkt": string|empty

        // for point geometries only. The latitude column name
        "point_lat": string|empty
        // for point geometries only. The longitude column name
        "point_lon": string|empty

        // list of property column names. "*" means "all columns".
        "properties": string[]|"*"|empty
      }
    }

    """
    if 'columns' not in spec:
        raise ValueError('CSV metadata must specify "columns" for ingestion')
    columns = spec['columns']

    has_geometry_wkt = 'geometry_wkt' in columns
    has_point_lat = 'point_lat' in columns
    has_point_lon = 'point_lon' in columns

    # must have one of either: "geometry_wkt", ("point_lat", "point_lon")
    if (
        not (has_geometry_wkt or has_point_lat or has_point_lon)
        or has_geometry_wkt
        and has_point_lat
        and has_point_lon
    ):
        raise ValueError(
            'CSV metadata must specify one of: ("geometry_wkt") or ("point_lat", "point_lon")'
        )

    properties = columns.get('properties')
    if not (properties is None or properties == '*' or is_list_of_str(properties)):
        raise ValueError('"properties" must be a string, a list of strings')

    if has_geometry_wkt:
        geometry_wkt = columns['geometry_wkt']
        if not isinstance(geometry_wkt, str):
            raise ValueError('"geometry_wkt" must be a string')

        return partial(
            wkt_geom_from_dict,
            geometry_wkt,
            properties,
        )

    elif has_point_lat and has_point_lon:
        point_lat = columns['point_lat']
        point_lon = columns['point_lon']
        if not isinstance(point_lat, str):
            raise ValueError('"point_lat" must be a string')
        if not isinstance(point_lon, str):
            raise ValueError('"point_lon" must be a string')

        return partial(point_geom_from_dict, point_lon, point_lat, properties)


def create_raster_map_layer(file_item, style_options):
    """Save a RasterMapLayer from a FileItem's contents."""
    with tempfile.TemporaryDirectory() as temp_dir:
        raw_data_path = Path(temp_dir, 'raw_data.tiff')
        with open(raw_data_path, 'wb') as raw_data:
            with file_item.file.open('rb') as raw_data_archive:
                raw_data.write(raw_data_archive.read())

        # Pass the file path and map layer to the next function
        new_map_layer = create_raster_map_layer_from_file(file_item, raw_data_path, style_options)
        return new_map_layer


def create_raster_map_layer_from_file(file_item, file_path, style_options, name='', index=None):
    """Create a RasterMapLayer from a file's contents."""
    import large_image_converter

    if not style_options:
        style_options = {}
    with rasterio.open(file_path) as src:
        bands = []
        for i in range(1, src.count + 1):
            stats = src.statistics(i, approx=True)
            band_min = stats.min
            band_max = stats.max
            minmax = style_options.get('minmax', None)
            # Check if the band's min/max values are not in the range of 0-255
            if int(band_min) != 0 or int(band_max) != 255 or (minmax):
                color_interp = src.colorinterp[i - 1]

                # Initialize the palette color based on color interpretation
                palette = None
                if color_interp == ColorInterp.red:
                    palette = '#FF0000'
                elif color_interp == ColorInterp.green:
                    palette = '#00FF00'
                elif color_interp == ColorInterp.blue:
                    palette = '#0000FF'
                min_value = 'min'
                max_value = 'max'
                if minmax:
                    min_value = minmax.get('min', 'min')
                    max_value = minmax.get('max', 'max')

                # if we set a custom nodata we need to adjust min/max
                if style_options.get('nodata', None) is not None:
                    min_value = float(band_min)
                    max_value = float(band_max)
                band_dict = {
                    'band': i,
                    'enabled': True,
                    'min': min_value,
                    'max': max_value,
                    'clamp': False,
                }

                # Add the palette if a color is determined
                if palette:
                    band_dict['palette'] = palette

                bands.append(band_dict)
            else:
                band_dict = {
                    'band': i,
                    'enabled': False,
                    'min': 'min',
                    'max': 'max',
                    'clamp': False,
                }
                bands.append(band_dict)
        # If there are any bands with out-of-range values, update the default_style
        if bands:
            if 'largeImageStyle' not in style_options:
                style_options['largeImageStyle'] = {}
            if style_options['largeImageStyle'].get('bands', None) is None:
                style_options['largeImageStyle']['bands'] = bands

    # Update the default style with new styling
    layer_index = file_item.index
    if name == '':  # On empty name use the file_item name
        name = file_item.name
    if index is not None:
        layer_index = index
    new_map_layer = RasterMapLayer.objects.create(
        dataset=file_item.dataset,
        name=name,
        metadata={},
        default_style=style_options,
        index=layer_index,
    )

    # Convert the file to cloud-optimized geotiff and save it
    with tempfile.TemporaryDirectory() as temp_dir:
        cog_raster_path = Path(temp_dir, 'cog_raster.tiff')
        # _concurrent=None should use all logical CPUS
        # https://github.com/girder/large_image/blob/master/utilities/converter/large_image_converter/__init__.py#L925
        large_image_converter.convert(str(file_path), str(cog_raster_path), _concurrency=None)
        with open(cog_raster_path, 'rb') as cog_raster_file:
            new_map_layer.cloud_optimized_geotiff.save(
                cog_raster_path, ContentFile(cog_raster_file.read())
            )

    return new_map_layer


def create_vector_map_layer(file_item, style_options, name='', index=None, metadata=None):
    """Save a VectorMapLayer from a FileItem's contents."""
    geojson_array = []
    if file_item.file_type == 'zip':
        geojson_array = convert_zip_to_geojson(file_item)
    elif file_item.file_type == 'csv':
        geojson_array.append({'geojson': convert_csv_to_geojson(file_item), 'name': name})
    elif file_item.file_type == 'geojson' or file_item.file_type == 'json':
        logger.info(f'Processing geojson file: {file_item.name} with type: {file_item.file_type}')
        source_data = json.load(file_item.file.open())
        source_projection = source_data.get('crs', {}).get('properties', {}).get('name')
        geojson_data = geopandas.GeoDataFrame.from_features(source_data.get('features'))
        if source_projection:
            geojson_data = geojson_data.set_crs(source_projection)
            geojson_data = geojson_data.to_crs(4326)
        geojson_array.append({'geojson': geojson_data, 'name': name})
    new_map_layers = []
    for data in geojson_array:
        geojson = data['geojson']
        layer_name = name
        # Use the layer names only if there is more than one layer created from the files
        if len(geojson_array) > 1:
            layer_name = data['name']
        new_map_layer = create_vector_map_from_json(
            file_item, geojson, style_options, layer_name, index, metadata
        )
        new_map_layers.append(new_map_layer)

    return new_map_layers


def create_vector_map_from_json(
    file_item, geojson_data, style_options, name='', index=None, metadata=None
):
    updated_style_options = calculate_styling(geojson_data, style_options)
    layer_index = file_item.index
    if index is not None:
        layer_index = index
    new_map_layer = VectorMapLayer.objects.create(
        dataset=file_item.dataset,
        name=name,
        metadata=metadata,
        default_style=updated_style_options,
        index=layer_index,
    )
    print('\t', f'VectorMapLayer {new_map_layer.id} created with name: {name}')
    new_map_layer.write_geojson_data(geojson_data.to_json())
    new_map_layer.save()
    print('\t', 'Done Writing GeoJSON file to Map Layer')

    return new_map_layer


def convert_zip_to_geojson(file_item):
    geodata_list = []
    with tempfile.TemporaryDirectory() as temp_dir:
        archive_path = Path(temp_dir, 'archive.zip')
        logger.warning(f'Opening {file_item.file.name}')

        # Write the file content to a temp directory
        with open(archive_path, 'wb') as archive_file:
            content = file_item.file.open('rb').read()
            archive_file.write(content)

        # Check the written file size and file type
        if not archive_path.exists() or archive_path.stat().st_size == 0:
            logger.error(f'File {file_item.file.name} is empty or does not exist.')
            return []

        # Ensure it's a valid ZIP file
        if not file_item.file.name.endswith('.zip'):
            logger.error(f'File {file_item.file.name} is not a zip file.')
            return []

        with zipfile.ZipFile(archive_path) as zip_archive:
            filenames = zip_archive.namelist()

            for filename in filenames:
                if filename.endswith(('.geojson', '.json')):
                    if filename.startswith('__MACOSX/') or Path(filename).name.startswith('._'):
                        logger.info(f'Skipping macOS metadata file: {filename}')
                        continue

                    logger.info(f'Processing GeoJSON file: {filename}')

                    with zip_archive.open(filename) as geojson_file:
                        raw_content = geojson_file.read()

                        # Try decoding with UTF-8 first
                        for encoding in ('utf-8', 'iso-8859-1', 'windows-1252'):
                            try:
                                content = raw_content.decode(encoding).strip()
                                break  # Stop at the first successful decode
                            except UnicodeDecodeError:
                                logger.warning(
                                    f'Failed to decode {filename} with {encoding}, trying next.'
                                )
                        else:
                            logger.error(
                                f'Could not decode {filename} with any common encoding, skipping.'
                            )
                            continue  # Skip the file if all decoding attempts fail

                        if not content:
                            logger.error(f'File {filename} is empty!')
                            continue  # Skip empty files

                        try:
                            source_data = json.loads(content)
                        except json.JSONDecodeError as e:
                            logger.error(f'Error decoding JSON in {filename}: {e}')
                            continue  # Skip invalid JSON files

                        source_projection = (
                            source_data.get('crs', {}).get('properties', {}).get('name')
                        )
                        geojson_data = geopandas.GeoDataFrame.from_features(
                            source_data.get('features')
                        )
                        if source_projection:
                            geojson_data = geojson_data.set_crs(
                                source_projection, allow_override=True
                            )
                            geojson_data = geojson_data.to_crs(4326)
                        geodata_list.append({'geojson': geojson_data, 'name': Path(filename).stem})

            # Group shapefile components by basename
            shapefile_groups = defaultdict(list)
            for filename in filenames:
                base_name = Path(filename).stem
                for ext in SHAPEFILE_EXTS:
                    if ext in filename:
                        shapefile_groups[base_name].append(filename)

            for base_name, files in shapefile_groups.items():
                try:
                    shp_file = next((f for f in files if f.endswith('.shp')), None)
                    dbf_file = next((f for f in files if f.endswith('.dbf')), None)
                    prj_file = next((f for f in files if f.endswith('.prj')), None)

                    if not shp_file:
                        logger.warning(f'Shapefile {base_name}.shp not found, skipping.')
                        continue
                    if not dbf_file:
                        logger.warning(f'DBF file {base_name}.dbf is missing, skipping.')
                        continue
                    # Create file-like options that can be read
                    shp_data = zip_archive.open(shp_file)
                    dbf_data = zip_archive.open(dbf_file)
                    if prj_file:
                        prj_data = zip_archive.open(prj_file)
                    sf = shapefile.Reader(shp=shp_data, dbf=dbf_data)
                    features = sf.__geo_interface__['features']

                    # Extract geometry and properties
                    geometries = [
                        feature['geometry'] for feature in features if feature['geometry']
                    ]

                    if not geometries:
                        logger.warning(
                            f'Shapefile {base_name}.shp has no valid geometries, skipping.'
                        )
                        continue

                    # Create GeoDataFrame
                    features = sf.__geo_interface__['features']
                    geodata = geopandas.GeoDataFrame.from_features(features)
                    if prj_data:
                        source_projection = prj_data.read().decode('utf-8')
                        geodata = geodata.set_crs(source_projection, allow_override=True)

                    # Convert to WGS84
                    geodata = geodata.to_crs(4326)
                    shp_data.close()
                    dbf_data.close()
                    if prj_data:
                        prj_data.close
                    geodata_list.append({'geojson': geodata, 'name': base_name})

                except Exception as e:
                    logger.error(f'Error processing shapefile group {base_name}: {e}')

    return geodata_list


def convert_csv_to_geojson(file_item):
    if not file_item.metadata:
        raise ValueError('CSV file does not have metadata to describe its contents')

    file_metadata = file_item.metadata
    parse_row = get_csv_row_parser(file_metadata)

    frame_dict = defaultdict(list)

    with tempfile.TemporaryDirectory() as temp_dir:
        csv_path = Path(temp_dir, 'csv.csv')
        with open(csv_path, 'wb') as csv_file:
            content = file_item.file.open().read()
            csv_file.write(content)

        df = pandas.read_csv(csv_path)

        for _, row in df.iterrows():
            geom, properties = parse_row(row)
            frame_dict['geometry'].append(geom)
            for propkey, propval in properties.items():
                # Rename "geometry" property to avoid conflict with GeoDataFrame's "geometry" column
                if propkey == 'geometry':
                    propkey = 'geometry_property'
                frame_dict[propkey].append(propval)

    return geopandas.GeoDataFrame(frame_dict, crs='EPSG:4326')


def save_vector_features(vector_map_layer: VectorMapLayer):
    features = vector_map_layer.read_geojson_data()['features']
    vector_features = []
    for feature in features:
        geometry = GEOSGeometry(json.dumps(feature['geometry']))

        # Check if the feature is a MultiLineString
        if geometry.geom_type == 'MultiLineString':
            # Check if the geometry is 3D (has Z-coordinates)
            if geometry.hasz:
                # Convert to 2D by flattening Z-coordinates
                new_lines = []
                for line in geometry:
                    if isinstance(line, LineString) and line.hasz:
                        new_lines.append(LineString([(x, y) for x, y, z in line.coords]))
                    else:
                        new_lines.append(line)  # Preserve 2D LineStrings

                # Replace the geometry with the new 2D MultiLineString
                geometry = MultiLineString(new_lines)
        vector_features.append(
            VectorFeature(
                map_layer=vector_map_layer,
                geometry=geometry,
                properties=feature['properties'],
            )
        )

    created = VectorFeature.objects.bulk_create(vector_features)

    return created


def process_geopackage(file_item, style_options):
    raster_map_layers = []
    vector_map_layers = []
    with tempfile.TemporaryDirectory() as temp_dir:
        gpkg_file = Path(temp_dir, 'raw.gpkg')
        with open(gpkg_file, 'wb') as raw_data:
            with file_item.file.open('rb') as raw_data_archive:
                raw_data.write(raw_data_archive.read())
        # Create a temporary directory to store the exported files
        index = 0
        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                with fiona.Env():  # Context manager to handle GDAL and Fiona environment properly
                    layers = fiona.listlayers(gpkg_file)
                    logger.warning(f'Vector layers found: {layers}')
                    for layer in layers:
                        # Open each layer
                        with fiona.open(gpkg_file, layer=layer) as layer_src:
                            output_geojson = os.path.join(tmp_dir, f'{layer}.geojson')

                            # Write layer to GeoJSON
                            with fiona.open(
                                output_geojson,
                                'w',
                                driver='GeoJSON',
                                crs=layer_src.crs,
                                schema=layer_src.schema,
                            ) as dst:
                                for feature in layer_src:
                                    dst.write(feature)

                            with open(output_geojson, 'r') as geojson_file:
                                data = geojson_file.read()
                                source_data = json.loads(data)
                                source_projection = (
                                    source_data.get('crs', {}).get('properties', {}).get('name')
                                )
                                geojson_data = geopandas.GeoDataFrame.from_features(
                                    source_data.get('features')
                                )
                                if source_projection:
                                    geojson_data = geojson_data.set_crs(source_projection)
                                    geojson_data = geojson_data.to_crs(4326)
                                new_vector_layer = create_vector_map_from_json(
                                    file_item, geojson_data, style_options, layer, index
                                )
                                save_vector_features(new_vector_layer)
                                vector_map_layers.append(new_vector_layer)
                                index += 1
            except fiona.errors.DriverError as e:
                logger.warning('GeoPackage file may not contain vector layers')
                logger.warning(
                    'Logging information, if geopackage file does not contain vector layers this is not an error'
                )
                logger.warning(f'File Being Processed: {gpkg_file} - Returned Value: {e}')

            # List the raster layers using gdalinfo
            # sometimes gdalino will fail if the geopackage only contains vectors
            try:
                gdal_info_output = subprocess.check_output(['gdalinfo', gpkg_file]).decode()

                for line in gdal_info_output.splitlines():
                    if 'SUBDATASET_' in line and '_NAME=' in line:
                        raster_layer = line.split('=')[-1]  # Get the full name of the raster layer
                        base_layer_name = raster_layer.split(':')[-1]
                        output_tiff = os.path.join(tmp_dir, f'{base_layer_name}.tif')

                        # Convert raster layer to TIFF using gdal_translate
                        subprocess.run(
                            ['gdal_translate', '-of', 'GTiff', raster_layer, output_tiff]
                        )

                        # Save the TIFF content to the RasterMapLayer's cloud_optimized_geotiff
                        raster_map_layer = create_raster_map_layer_from_file(
                            file_item, output_tiff, style_options, base_layer_name, index
                        )
                        raster_map_layers.append(raster_map_layer)
                        index += 1
            except subprocess.CalledProcessError as e:
                logger.warning('GeoPackage file may not contain raster layers')
                logger.warning(
                    'Logging information, if geopackage file does not contain raster layers this is not an error'
                )
                logger.warning(f'File Being Processed: {gpkg_file} - Returned Value: {e}')
    return raster_map_layers, vector_map_layers


# Some function that will connect VectorFeatures to JSON data


def process_tabular_vector_feature_data(map_layer_id, json_data, matcher):
    # Take the matcher from the properties in VectorFeatures
    vector_features = VectorFeature.objects.filter(map_layer_id=map_layer_id)

    for feature in vector_features:
        # Ensure properties contain the matcher key
        matcher_value = str(feature.properties.get(matcher))

        # Ensure the matcher value exists in json_data
        if matcher_value not in json_data:
            logger.info(
                f'Could not find a match for the property {matcher} in vectorFeature properties'
            )
            logger.info(feature.properties)
            continue

        table_list = json_data.get(matcher_value)  # Retrieve the corresponding JSON object
        if table_list is None:
            logger.info(
                f'Could not find a matching table with value {matcher_value} for the property {matcher}'
            )
        # Create a new VectorFeatureTableData object
        for table in table_list:
            table_data = VectorFeatureTableData.objects.create(
                vector_feature=feature,
                map_layer=feature.map_layer,
                name=table.get('name', 'Unnamed Table'),
                type=table.get('type', 'Unknown'),
                description=table.get('description', ''),
                columns=table.get('header', []),  # Use 'header' for columns
                summary=table.get('summary', {}),
            )

            # Process rows and create VectorFeatureRowData objects
            rows = table.get('rows', [])
            VectorFeatureRowData.objects.bulk_create(
                [
                    VectorFeatureRowData(
                        vector_feature_table=table_data, row_data=row  # Store the row JSON data
                    )
                    for row in rows
                ]
            )
