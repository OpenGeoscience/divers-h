# WebGIS Application Architecture

The **WebGIS** application is a **Docker container-based** web application that allows for visualization, processing, and management of **geospatial data**. This includes importing/uploading **vector data** from **GeoJSON / JSON / Shapefiles** and **raster data** from **TIFFs / GeoTIFFs / Geopackage** and other formats.

## Main Services/Frameworks

The Web Application uses a variety of **services/frameworks** and communication between them. Below is a brief description of the main services used:

- **Django** - A Python-based **Object Relational Mapping (ORM) Framework** that integrates with a database to allow for the configuration of tables through Python code. Django also provides a mechanism for creating **REST endpoints** and integrates with **Celery** for running long-running tasks.
- **PostgreSQL** - The backing database for Django.
- **Celery** - A **distributed system** to process task messages. It is used in the Web application to **queue and run long-running tasks**, such as processing user data from uploads or importing and processing data.
- **RabbitMQ** - Celery requires a **messaging broker** to facilitate communication between Django and Celery.
- **MinIO** - An **S3-compatible file-object storage solution**. MinIO is used in the application to store files such as **uploaded TIFF/Geopackage/Shapefiles**. It is also used to store **derivative files** produced from processing, such as **GeoJSON from vector data** or **GeoTIFFs from raster processing**.
- **Vue** - A **Front-End Framework** used to create a **Single Page Application (SPA)** to interact with the REST endpoints provided by Django. Vue is a **reactive framework** that enables highly dynamic and interactive user interfaces.

## Docker Containers

The application is initialized, and communication between the different services is organized through **Docker Compose YAML files**.

- **`docker-compose.yml`** - Initializes the **PostgreSQL** database container, the **MinIO** container for file storage, and the **RabbitMQ** container for handling long-running tasks.
- **`docker-compose.override.yml`** - Used in **development mode** (`docker compose up`). It launches the **Django** container and **Celery** in 'dev' mode for local development. It also launches a service to generate the **vector tile basemap** and a service to **host the documentation**.
- **`docker-compose.prod.yml`** - Used for **production deployment**. The **Django** and **Celery** containers are launched in **production mode**. The **vector tile basemap service** also runs in this mode. Additionally, a **web service** is included, which hosts an **Nginx reverse proxy**. This proxy:
  - Serves the **Vue front-end** on the **base URL**.
  - Serves **documentation** at `{baseURL}/docs`.
  - Routes API requests (`/api`) to the **Django service**.

## Docker Services

A **comprehensive listing** of the **Docker containers/services** used in the application:

- **Django** - The **Python web framework** that:
  - Communicates with **PostgreSQL** to modify and retrieve data.
  - Creates a **REST API**.
  - Queues tasks via **RabbitMQ**, which are processed by **Celery**.
  - Runs in **development mode** (`docker-compose.override.yml`) with live-reloading.
  - Runs in **production mode** (`docker-compose.prod.yml`).
- **Celery** - A **distributed system** that processes **messages from RabbitMQ**. These messages, sent by **Django**, are typically **long-running tasks** such as **data processing**.
  - Example: A user uploads a file → Django queues a task → Celery processes it → Celery updates the database or pushes derivative files to MinIO.
- **PostgreSQL** - The backing **relational database** for Django.
- **RabbitMQ** - A **message broker** that facilitates communication between **Celery** and **Django**.
- **MinIO** - An **S3-compatible object storage service** used for **uploaded files** and **derivative outputs** (e.g., images, GeoJSON, Cloud-Optimized GeoTIFFs).
- **gen-vector-basemap** - A service that:
  - Downloads and **creates a vector tile basemap** for the UI.
  - May take a few hours to generate tiles on first launch.
  - Writes out a file called `us.pmtiles` that is served to the front-end.
- **Docs** - A service that **hosts the application's documentation**.
- **Web** - A service (only in `docker-compose.prod.yml`) that runs **Nginx as a reverse proxy**.
  - Routes `/api` requests to **Django**.
  - Serves **static files** (front-end & documentation).

## Docker Files

Some services use **pre-built images from DockerHub**, while others are **built locally** using `Dockerfile` definitions.

- **`./dev/Dockerfile`** - Builds the **development** version of **Celery** and **Django**.
- **`./prod/Dockerfile`** - Builds the **production** version of **Celery** and **Django**.
- **`./prod/client.Dockerfile`** - Builds the service containing:
  - The **Nginx reverse proxy**.
  - The **Vue front-end** and **documentation**, placing static files in a location served by Nginx.
- **`./docker/tilemaker`** - Manages the **download and serving of vector tile basemaps**.

### Example Data Flow

Below is a simplified example of how data flows between services for the process of uploading a new file in the user interface.

1. A user creates a new dataset and uploads a new file in the client application when the server is in the deployed version.
2. The client application is served from the **web** service in docker-compose.prod.yml to provide the interface.
3. On upload an a series of API REST requests are made to `api/v1/s3-upload/upload-initialize/`, `api/v1/s3-upload/upload-complete` and `api/v1/s3-upload/finalize`.  These endpoint requests go through the **web** container and using the nginx reverse proxy are routed to the **django** service.
4. During this process the file is moved from **django** service to **minIO** for storage.
5. Once the file upload is complete the client then makes an additional request to `POST /api/v1/files/` that again is done through the reverse proxying in **web** to the **django** service.  This endpoint will update the row for the FileItem in **postgres** with a reference to the MinIO location of the file.
6. The **django** service then schedules a task to process the uploaded file.  This is done by creating a a new message in **rabbitMQ**.
7. The **celery** service using **rabbitMQ** begins the task by retrieving the information for the FileItem from the **postgres** service and grabbing the file from **minIO** so it can be processed.  At the end of processing new MapLayers are created and any new files are added to **MinIO**
