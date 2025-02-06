FROM ghcr.io/systemed/tilemaker:master

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends wget ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY ./generate-vector-tiles.sh /app/generate-vector-tiles.sh

ENTRYPOINT ["/bin/bash"]
CMD ["/app/generate-vector-tiles.sh"]
