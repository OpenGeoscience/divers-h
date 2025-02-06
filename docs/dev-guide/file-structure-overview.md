# Repository File Structure

- **`/`** - The root directory contains all of the Docker Compose files to ease in initialization of the system through utilizing **`docker compose up`** and variants of this command for initialization and management of the application. There are additional files for installing the application in Python, a tox file for managing tests, and the **mkdocs** configuration files for generating documentation.
- **`/uvdat`** - Contains backend code using the Django Web Framework for specifying models, REST endpoints, and Processing Tasks. More details are under the /uvdat folder structure.
- **`/client`** - Contains the front-end application code using the Vue framework. More details are under the /client folder structure.
- **`/sample_data`** - Includes the **`test.json`** which is used to automatically load sample data using the **`ingest_data`** management command for testing purposes. This test data includes importing various formats for validation that the files are working properly. When the environment variable **`NZ_INGEST_ROOT`** is set, the **`ingest_data`** command will look in the folder specified by **`NZ_INGEST_ROOT`** instead of the **`sample_data`** folder.
- **`/dev`** - Contains Dockerfiles and scripts to set environment variables for running the application in development mode.
- **`/prod`** - Dockerfiles and the Nginx reverse proxy configuration for deployment of the application.
- **`/docker`** - Additional Dockerfiles for other services, e.g. the service for vector tile basemap generation.
- **`/scripts`** - Contains sample scripts for processing data utilizing Python or other scripts that aren’t used directly in the application.

## /uvdat Django App Folder Structure

The `/uvdat` folder contains the back-end configuration utilizing the Django Web Framework. Django communicates with PostgreSQL to specify table structures through `models/` and endpoints can be specified through `urls.py` and the `core/rest/` folder.  Django and Celery use the `core/tasks/` folder for processing data.   Django also allows the installation of Django Apps that provide additional models and endpoints to enhance functionality.

Below are descriptions of the main folders and files used to configure Django.

- **`settings.py`** - Provides Django configuration, including additional Django Apps that are installed and used within the application. These additional applications provide models and endpoints without including their code directly. Some core applications are installed through the Django Compose configuration ([django-composed-configuration](https://github.com/kitware-resonant/django-composed-configuration)). Additional applications are included to provide specific functionality for this web application.
  - **`django.contrib.gis`** - GeoDjango ([docs](https://docs.djangoproject.com/en/5.1/ref/contrib/gis/#module-django.contrib.gis)) provides models and tools for dealing with geospatial data in Django.
  - **`django_large_image`** - Django Large Image ([github](https://github.com/girder/django-large-image)) provides models and endpoints for converting and tile-serving raster data like COG GeoTIFFs and other image sources.
- **`urls.py`** - Specifies REST endpoints directly through **`urlpatterns`** as well as Django routers for new resources. The routers are generally found under the **`./core/rest`** folder.
- **`/core`** - Contains the models for specifying tables in the database, REST endpoint configuration, tasks, management commands, and configuration of the admin interface.
  - **`/models`** - Each file under this folder is a single or multiple Django models. These models correspond to tables in the PostgreSQL database. The models can also have class methods that perform actions or create computed data, making it easier to generate data.
  - **`/migrations`** - When the PostgreSQL tables are modified, a new migration is created using the command **`docker compose run --rm django ./manage.py makemigrations`**. These migrations are used to upgrade the PostgreSQL database based on new or updated models.
  - **`/rest`** - Includes REST endpoints utilizing Django Rest Framework (DRF) **`ViewSet`** models. Each class that inherits **`ViewSet`** from DRF creates a basic CRUD (Create, Read, Update, Delete) set of restful endpoints for the corresponding model. Some additional endpoints are added in the class or automatically generated endpoints may be overridden.
    - **`serializers.py`** - Provides a way to serialize model data (PostgreSQL rows) for a JSON response by the endpoint. The **`ViewSet`** models will utilize the specified **`ModelSerializer`** class to process data before exporting it for REST endpoints.
  - **`/tasks`** - Celery tasks that are used to process data and create derivative data that can’t be done in the time of a simple web request.
  - **`/management`** - Provides specialized management commands to **`docker compose run --rm django ./manage.py`** such as the **`ingest_data`** command. This command reads an input JSON file for specifications and then uses the **`core/tasks`** to process and import the data.
- **`/tests`** - Automated tests used by Continuous Integration that are run to ensure the system is running properly when code changes are made.

## /client Folder Structure

The Client utilizes the Vue Framework for creating a single page application (SPA).  The other core libraries used are maplibre for rendering map data and d3.js for providing color schemes and creating graphs/charts.

- **`src`** - Root folder for the web application.
- **`types.ts`** - TypeScript definition for all the data types that are used in the system. This is mostly used to ensure that the client knows about the serialized data returned from the Django endpoints.
- **`/api/UVDATApi.ts`** - All REST points that the client application uses to interface with Django. Not all endpoints that are provided by Django are used; this is a subset of all endpoints that the client application will use.
- **`/components`** - Vue Single File Components used in the application. These are functional blocks used to display different interfaces within the application. The names of the components and the folders should hopefully be informative of what the component is displaying.
  - **`/Map.vue`** - Creation of the MapLibre main map used in the interface.
  - **`/DataSelection`** - Components used for data viewing/editing. This includes uploading, deleting, and selecting scenarios and datasets.
  - **`/Indicators`** - Components that visualize indicators associated with scenarios.
- **`/map`** - Files that interface with MapLibre for rendering and coloring different map layers.
  - **`/mapLayers.ts`** - Manages the rendering of raster and vector map layers.
- **`MapStore.ts`** - Holds the global state for the application such as the list of enabled and visible map layers, the current mode (Pro or regular user), and the currently selected vector feature IDs.
