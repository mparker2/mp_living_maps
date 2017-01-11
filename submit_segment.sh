#!/bin/bash
#$ -l rmem=40G
#$ -l mem=40G
#$ -j y
#$ -N segment
set -eo pipefail

module load apps/python/conda
source activate living_maps

python /home/mbp14mtp/mp_living_maps/felzenszwalb_segment.py \
  --image $1 --output-basename $2 \
  --scale=$3 --sigma=$4 \
  --min-size=$5 --sieve=$6
