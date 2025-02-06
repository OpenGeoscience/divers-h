import json
import random
import math

def generate_random_point(center, radius):
    """
    Generate a random point within a specified radius of a center point.
    :param center: Tuple of (latitude, longitude).
    :param radius: Radius in miles.
    :return: Tuple of (latitude, longitude).
    """
    radius_in_degrees = radius / 69  # Convert miles to degrees (approx)
    angle = random.uniform(0, 2 * math.pi)
    distance = random.uniform(0, radius_in_degrees)
    delta_lat = distance * math.cos(angle)
    delta_lon = distance * math.sin(angle)
    lat = center[0] + delta_lat
    lon = center[1] + delta_lon
    return lat, lon

def interpolate_points(start, end, steps):
    """
    Interpolate between two points over a number of steps.
    :param start: Tuple of (latitude, longitude).
    :param end: Tuple of (latitude, longitude).
    :param steps: Number of steps.
    :return: List of interpolated points.
    """
    lat_step = (end[0] - start[0]) / steps
    lon_step = (end[1] - start[1]) / steps
    return [(start[0] + i * lat_step, start[1] + i * lon_step) for i in range(steps + 1)]

def create_geojson(total_steps=300, total_points=50, output_file="points.geojson"):
    """
    Create a GeoJSON file for points moving between cities.
    :param total_steps: Total number of steps for the movement.
    :param total_points: Total number of points.
    :param output_file: File name for the output GeoJSON.
    """
    # City coordinates (latitude, longitude)
    cities = {
        "Albany": (42.6526, -73.7562),
        "Amsterdam": (42.9375, -74.1907),
        "Syracuse": (43.0481, -76.1474),
        "Watertown": (43.9748, -75.9108),
        "Plattsburg": (44.6995, -73.4529),
        "Glens Falls": (43.3095, -73.6441),
    }

    # Convert city keys to a list for ordered traversal
    city_names = list(cities.keys())

    # Generate initial points around Albany
    points = [generate_random_point(cities["Albany"], 10) for _ in range(total_points)]

    features = []
    step_counter = 0

    for i in range(len(city_names)):
        start_city = city_names[i]
        end_city = city_names[(i + 1) % len(city_names)]
        
        # Calculate interpolated points for all steps between start and end city
        interpolated_steps = total_steps // len(cities)
        for point_idx in range(total_points):
            start_point = points[point_idx]
            end_point = generate_random_point(cities[end_city], 10)
            movement_path = interpolate_points(start_point, end_point, interpolated_steps)
            
            # Update points
            points[point_idx] = end_point
            
            for step in range(interpolated_steps):
                lat, lon = movement_path[step]
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    },
                    "properties": {
                        "step": step_counter + step,
                        "point_id": point_idx
                    }
                })
        
        step_counter += interpolated_steps

    geojson_data = {
        "type": "FeatureCollection",
        "features": features
    }

    with open(output_file, 'w') as file:
        json.dump(geojson_data, file, indent=2)

    print(f"GeoJSON file '{output_file}' created with {len(features)} features.")

# Default execution
if __name__ == "__main__":
    create_geojson()
