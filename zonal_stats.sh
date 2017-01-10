#!/bin/bash
#$ -l rmem=5G
#$ -l mem=5G
#$ -j y
#$ -N zonal_stats
set -eo pipefail

module load apps/python/conda
source activate living_maps

SHAPEFILE=$1
RASTER=$2
echo "processing $RASTER"
BANDS=`rio info $RASTER | jq -r '.["descriptions"] | join(",")'`
echo "contains bands: $BANDS"
IFS=',' read -r -a BANDSARR <<< "$BANDS"

for B in `seq 1 "${#BANDSARR[@]}"`; do
  BANDNAME="${BANDSARR[$B-1]}"
  TSV="${RASTER%.*}_${BANDNAME}_zonal_stats.tsv"
  echo "processing band $BANDNAME"
  fio cat $SHAPEFILE | rio zonalstats \
    -r $RASTER --band $B \
    --stats "min max mean std" | \
  jq -r '.features[] | .properties | [.FID, ._max, ._min, ._mean, ._std] | @tsv' > $TSV
done
