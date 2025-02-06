# Scenarios

!!! note
    "Scenarios" and "contexts" are synonymous in this application. The API refers to "scenarios" as "contexts".

The scenarios can accessed and manipulated via the `/api/v1/contexts/` endpoint.

## Model structure

Scenario:

- `id` (integer): the unique ID that can be used to reference a scenario.
- `default_map_center` (string): the map center (WGS84 coordinates) associated with the scenario.
- `default_map_zoom` (integer): the map zoom level when centering the map at the `default_map_center`.
- `indicators` (JSON array): a list of indicators asssociated with the scenario.
- `datasets` (integer array): a list of dataset IDs associated with the scenario.
