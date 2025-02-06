# Data Ingestion

## Ingesting test data

To ingest the testing data, run the following command.

```
docker compose run --rm django ./manage.py ingest_data ./sample_data/test.json
```

## Ingesting production data

Data is ingested into the system by bind-mounting data directories from the host and
running the ingest script on the bind-mounted files. Specifically,
the data to be ingested must be described by a JSON file in the correct ingest format.

Note that the system should be running via the  `docker compose up` command above prior to running
ingest.

When running the ingest script, set the `NZ_INGEST_ROOT` to the path that will be bind-mounted
into the container, and run the following command:

```bash
NZ_INGEST_ROOT=/absolute/path/to/nz_armada_data docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm django ./manage.py ingest_data nz_data.json
```

Make sure before running that command that you substitute the correct host path to the `nz_armada_data`
repository in the `NZ_INGEST_ROOT` env var.

Appending the argument `--replace` to the above command will replace any existing Scenarios and Datasets from the nz_data.json file.

If you want to clear all data add `--clear` to the end of the command.  This will remove all Scenarios and Datasets from the current database and only load the new ingestion file.
The console will prompt you to type `yes` to confirm you want to clear all data.


## Incremental/Advanced Data Ingestion

When ingesting a JSON file the system will attempt to see if any Context/Dataset/Files match existing items in the database and will skip over them if they already exist.  You can override this behavior using the global commands mentioned above of `--replace` or `--clear`.  You can also add a key-value pair of `"action": "replace"` or `"action": "delete"` to any existing Context/Dataset/File to either replace the existing data or delete it.

Example:

```json
{
    "type": "Dataset",
    "name": "TimePoints",
    "description": "TimePoints Test file",
    "category": "test",
    "metadata": {},
    "action": "replace",
    "files": [
        {
            "path": "./data/timePoints.geojson",
            "name": "TimePoints Geojson",
            "url": "https://data.kitware.com/api/v1/item/67532ab09ccf870f61ceac9f/download",
            "type": "geojson",
            "metadata": {}
        }
    ]
}
```

The snippet above will replace any existing Dataset that exists with the name 'TimePoints'.

The nz_data.json is a file that contains a top-level list of objects.  In the example file those top-level objects are of `"type": "Context"`.  This isn't a requirement, besides loading of Context's that have Datasets, Datasets can be loaded directly by using `"type": "Dataset"` and then including the `"files": []` as a list of files to ingest.  These won't show up under Scenarios in the interface but will be added to the 'Dataset' tab where a user can individually look at these datasets.  If the user is logged in they can delete any unconnected (not inside a scenario) datasets that they no longer want to visualize.

At any time a separate .json file can be loaded into the system.  If there are no conflicting Context/Dataset names it will load any new Data.  I.E you may create a sample.json file that contains an array of  `"type": "Dataset"` objects in it.  Loading this in separate from the nz_data.json will just add the new fields.

