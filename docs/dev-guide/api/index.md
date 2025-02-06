# API Overview

This WebGIS application supports programmatic access to the data stored on the system via a REST API. This API is available at `https://url.com/api/v1`.

The full API reference can be viewed at [the API Swagger page](https://url.com/api/docs/swagger). While the Swagger page is representative of all available REST endpoints, it might not define the proper structures for endpoint parameters.

## Authentication

To authenticate against the REST API endpoints, you will need to submit all HTTP requests with the `Authorization: Bearer <token>` header.

!!! maintenance "Under Construction"
    We have not yet added support for long-lived API access keys.

