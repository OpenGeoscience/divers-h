# Datasets

The datasets can accessed and manipulated via the `/api/v1/datasets/` endpoint.

## Model structure

Dataset:

- `id` (integer): the unique ID that can be used to reference a dataset.
- `name` (string): the name of this dataset.
- `description` (string): the description of this dataset.
- `contextCount` (integer): the number of scenarios/contexts that this dataset is part of.
- `modified` (string): the date-time of most recent modification of this dataset.
- `created` (string): the date-time of when this dataset was created.
- `category` (string): the category of this dataset.
- `processing` (boolean): whether this dataset is being processed.
- `metadata` (JSON object): associated metadata
