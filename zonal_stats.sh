#!/bin/bash
#$ -l rmem=15G
#$ -l mem=15G
#$ -j y
#$ -N zonal_stats
set -eo pipefail

module load apps/python/conda
source activate living_maps

SHAPEFILE=$1
RASTER=$2
echo "processing $RASTER"
BANDS=`rio info $RASTER --count`
echo "contains $BANDS bands"

for B in `seq 1 "${BANDS}"`; do
  TSV="${RASTER%.*}_${B}_zonal_stats.tsv"
  echo "processing band $B"
  fio cat $SHAPEFILE | rio zonalstats \
    -r $RASTER --band $B \
    --nodata=0 \
    --stats "min max mean std" | \
  jq -r '.features[] | [.id, .properties._max, .properties._min, .properties._mean, .properties._std] | @tsv' > $TSV
done
