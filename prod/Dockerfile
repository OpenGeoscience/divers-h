FROM python:3.10-slim
# Install system libraries for Python packages:
RUN apt-get update && \
    apt-get install --no-install-recommends --yes \
    libpq-dev libvips-dev gcc libc6-dev gdal-bin git && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install large-image[gdal,pil] large-image-converter --find-links https://girder.github.io/large_image_wheels
COPY ./setup.py /opt/uvdat-server/setup.py
RUN pip install --editable /opt/uvdat-server[dev]
COPY ./manage.py /opt/uvdat-server/manage.py
COPY ./uvdat /opt/uvdat-server/uvdat

# These must be set in order to run manage.py commands.
ARG DJANGO_CONFIGURATION
ARG DJANGO_DATABASE_URL
ARG DJANGO_MINIO_STORAGE_ENDPOINT
ARG DJANGO_MINIO_STORAGE_ACCESS_KEY
ARG DJANGO_MINIO_STORAGE_SECRET_KEY
ARG DJANGO_STORAGE_BUCKET_NAME
ARG DJANGO_MINIO_STORAGE_MEDIA_URL
RUN /opt/uvdat-server/manage.py collectstatic --noinput

# Use a directory name which will never be an import name, as isort considers this as first-party.
WORKDIR /opt/uvdat-server
