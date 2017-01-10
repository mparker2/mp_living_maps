import argparse
from collections import defaultdict
import numpy as np
import scipy.stats
import pandas as pd
import fiona
from shapely.geometry import shape
import rtree

def build_rtree(shapefn):
    rtree_idx = rtree.index.Index()
    segs_dict = {}
    with fiona.open(shapefn, 'r') as shp_iterator:
        source_crs = source.crs
        source_schema = source.schema
        for record in shp_iterator:
            rtree_idx.insert(
                record['id'],
                shape(record['geometry']).bounds
            )
            segs_dict[record['id']] = record
    return rtree_idx, segs_dict, source_crs, source_schema

def get_segment_containing_points(segmentsfn, pointsfn, v_property):
    rtree_idx, segs, crs, schema = build_rtree(segmentsfn)
    mapping = defaultdict(list)
    with fiona.open(pointsfn, 'r') as point_iterator:
        for point_record in point_iterator:
            point = shape(point_record['geometry'])
            for i in rtree_idx.intersection(point.coords[0]):
                if point.within(shape(segs[i]['geometry'])):
                    mapping[seg.id].append((point_record['id'],
                                            point_record['properties'][v_property]))
    mapping = validate_mapping(mapping)
    return segs, dict(mapping), crs, schema

def validate_mapping(mapping):
    valid_mappings = []
    for seg_id, point_ids in mapping.items():
        if len(points_ids) > 1:
            props = all(x[1] == point_ids[0][1] for x in point_ids)
            if props:
                valid_mappings.append((seg_id, points_ids))
        else:
            valid_mappings.append((seg_id, points_ids))
    return dict(valid_mappings)

if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('-s', '--segments', type=str, required=True)
    a.add_argument('-p', '--points', type=str, required=True)
    a.add_argument('-o', '--output', type=str, required=True)
    a.add_argument('--property', type=str, required=True)
    args = a.parse_args()
    segs, mapping, crs, schema = get_segment_containing_points(args.s, args.p, args.property)
    schema['properties'][args.property] = 'str'
    with fiona.open(fn, 'w', driver='ESRI Shapefile', crs=crs, schema=schema) as shpfile:
        for seg_id, point_ids in mapping:
            seg = segs[seg_id]
            seg['properties'][args.property] = points_id[0][1]
            shpfile.write(seg)