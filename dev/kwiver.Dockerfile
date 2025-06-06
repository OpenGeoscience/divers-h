# Start from the KWIVER base image
FROM kitware/kwiver:latest

# Install system packages needed for Python and the app
RUN apt-get update && apt-get install --yes --no-install-recommends \
    build-essential wget curl libssl-dev zlib1g-dev libbz2-dev \
    libreadline-dev libsqlite3-dev libncurses5-dev libncursesw5-dev \
    xz-utils tk-dev git libffi-dev liblzma-dev libpq-dev \
    libvips-dev gcc libc6-dev gdal-bin libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python 3.10 manually if not available
RUN wget https://www.python.org/ftp/python/3.10.13/Python-3.10.13.tgz && \
    tar -xf Python-3.10.13.tgz && \
    cd Python-3.10.13 && \
    ./configure --enable-optimizations && \
    make -j"$(nproc)" && \
    make altinstall && \
    cd .. && rm -rf Python-3.10.13*

RUN python3.10 --version

# Install Python packages
RUN python3.10 -m ensurepip && \
    python3.10 -m pip install --upgrade pip

# Install large-image
RUN python3.10 -m pip install large-image[gdal,pil] large-image-converter --find-links https://girder.github.io/large_image_wheels

# Copy your application code
COPY ./setup.py /opt/uvdat-server/setup.py
COPY ./manage.py /opt/uvdat-server/manage.py
COPY ./uvdat /opt/uvdat-server/uvdat

# Install uvdat in editable mode with dev dependencies
RUN python3.10 -m pip install --editable /opt/uvdat-server[dev]

# Copy ffmpeg from static builder
RUN wget -O ffmpeg.tar.xz https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
RUN mkdir /tmp/ffextracted
RUN tar -xvf ffmpeg.tar.xz -C /tmp/ffextracted --strip-components 1

# Copy ffmpeg into final image
RUN cp /tmp/ffextracted/ffmpeg /usr/local/bin/
RUN cp  /tmp/ffextracted/ffprobe /usr/local/bin/

# Setup environment


# Set working directory
WORKDIR /opt/uvdat-server

