#!/bin/bash

set -Eeu

WORKDIR=/work
DATADIR=/data
OSMFILE="$WORKDIR/us-latest.osm.pbf"
PMTILESFILE="$WORKDIR/us.pmtiles"
OSMFILE_URL='https://download.geofabrik.de/north-america/us-latest.osm.pbf'
OUTPUT_PMTILES="$DATADIR/us.pmtiles"

trap 'echo "Failed to generate the pmtiles. Either download failed or not enough disk space + RAM for generation."' ERR

mkdir -p $WORKDIR $DATADIR

if [ -f "$OUTPUT_PMTILES" ]; then
  echo "$OUTPUT_PMTILES exists, exiting"
  exit 0
fi

echo "Downloading $OSMFILE..."
wget --quiet --continue -O "$OSMFILE" "$OSMFILE_URL"

echo "Converting $OSMFILE to $PMTILESFILE..."
/bin/sh /usr/src/app/resources/docker-entrypoint.sh "$OSMFILE" --output "$PMTILESFILE" --store /work/tmp
mv "$PMTILESFILE" "$OUTPUT_PMTILES"

echo "All done"
