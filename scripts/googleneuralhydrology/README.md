# Google Neural Hydrology Processing

## extractHruIds.py

This when given a geojson with properties.hru_id will extract all of the HRUIds from the geojson and make sure they are 8 digit codes and place them into a single list.
This was used to create a small sample that could be used to run testing data on

## runExperiment.py 

`python runExperiment.py hru_ids.json`

Requires the `run_demo.sh` script as well as properly downloading the docker and relevant data for running Google Neural Hydrology.
This file will go through the hru_ids.json and will run the experiments on each one and then extract the resulting .nc file and name it to the hru_id for further processing

# subSampleHruIds.py

`python subSampleHruIds.py camelsData.geojson hru_ids.json`

Takes the base camerlsData.geojson with all hru_ids and updates the hru_ids to be an 8 digit code with leading zeros.  I've also updated this to gather the USGS gauge data and add it as a point as well as transfer some information betwene the two Features in the geojson such as Name and other information.
Outputs a new geojson file 'matching_hru_ids.geojson' as well as HRU_AREA_MAP.json.  The second file is used for converting USGS daily calculations from cuft/s to mm/d values.

# nctoJson.py

`python nsToJson.py ./folder`

Takes all *.nc files from the runExperiment.py results and converts them into row data that can be used by DIVERS-H.  It als creates a nc_stat_mapping tool so that the stats can be added to the output geojson from subSampleHruIds.py.  Results by default in a ncToJSONOutput.json as well as a nc_stat_mapping.json file

# addStatsToGeoJSON.py

Takes the output from nctoJson.py (nc_stat_mapping.json) and adds this information to the output from subSampleHruIds.py so that way sample data can be 