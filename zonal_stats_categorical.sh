#!/bin/bash
#$ -l rmem=1G
#$ -l mem=1G
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
  qsub -cwd -j y -N "zonalstats_${B}" <<DELIM
#!/bin/bash
#$ -l mem=10G
#$ -l rmem=10G
#$ -m bea
#$ -M mparker2@sheffield.ac.uk
set -eo pipefail
module load apps/python/conda
source activate living_maps
fio cat $SHAPEFILE | rio zonalstats \
  -r $RASTER --band $B \
  --nodata=0 \
  --stats "majority" | \
jq -r '.features[] | [.id, .properties._majority] | @tsv' > $TSV
DELIM
done
