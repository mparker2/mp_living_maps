'''
Uses rtree to take a group of segments and a group of points and
efficiently determine which segment each point lies within.

Segments which contain two points are checked to make sure the
point is the same on a specified properties field. Those that are
not are removed (cannot train a model if segments belong to two
possible different classes).

Output is a shapefile of segments which overlapped with a point,
with the specified property of that point added to the properties
field.

Author: Matthew Parker
'''
import argparse
from collections import defaultdict
from itertools import chain
import numpy as np
import scipy.stats
import pandas as pd
import fiona
from shapely.geometry import shape
import rtree

def build_rtree(shapefn):
    '''
    Build a rtree index and plain dictionary from a shapefile of segments
    '''
    rtree_idx = rtree.index.Index()
    segs_dict = {}
    with fiona.open(shapefn, 'r') as shp_iterator:
        source_crs = shp_iterator.crs
        source_schema = shp_iterator.schema
        for record in shp_iterator:
            rid = int(record['id'])
            rtree_idx.insert(
                rid,
                shape(record['geometry']).bounds
            )
            segs_dict[rid] = record
    return rtree_idx, segs_dict, source_crs, source_schema

def get_segment_containing_points(segmentsfn, pointsfn, v_property):
    '''
    produce a dictionary mapping the points from a shapefile onto the
    segments they lie within.
    '''
    rtree_idx, segs, seg_crs, seg_schema = build_rtree(segmentsfn)
    mapping = defaultdict(list)
    with fiona.open(pointsfn, 'r') as point_iterator:
        point_schema = point_iterator.schema
        for point_record in point_iterator:
            point = shape(point_record['geometry'])
            for i in rtree_idx.intersection(point.coords[0]):
                # point may only intersect the bounding box of seg
                # make sure it fully intersects
                if point.within(shape(segs[i]['geometry'])):
                    mapping[i].append((point_record['id'],
                                       point_record['properties']))
    # validate mapping to make sure two points with different props fall
    # within the same segment.
    mapping = validate_mapping(mapping, v_property)
    return segs, dict(mapping), seg_crs, seg_schema, point_schema

def validate_mapping(mapping, v):
    '''
    validate mapping to make sure two points with different properties fall
    within the same segment.
    '''
    valid_mappings = []
    for seg_id, point_ids in mapping.items():
        if len(point_ids) > 1:
            props = all(x[1][v] == point_ids[0][1][v] for x in point_ids)
            if props:
                valid_mappings.append((seg_id, point_ids))
        else:
            valid_mappings.append((seg_id, point_ids))
    return dict(valid_mappings)

if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('-s', '--segments', type=str, required=True)
    a.add_argument('-p', '--points', type=str, required=True)
    a.add_argument('-o', '--output', type=str, required=True)
    a.add_argument('--property', type=str, required=True)
    args = a.parse_args()
    segs, mapping, crs, seg_schema, point_schema = get_segment_containing_points(args.segments,
                                                                                 args.points,
                                                                                 args.property)
    # do not overwrite properties in seg_schema:
    for k in seg_schema['properties']:
        _ = point_schema.pop(k, None)
    seg_schema['properties'] = OrderedDict(chain(seg_schema.items(), point_schema.items()))
    
    with fiona.open(args.output, 'w', driver='ESRI Shapefile', crs=crs, schema=schema) as shpfile:
        for seg_id, point_ids in mapping.items():
            seg = segs[seg_id]
            for k in point_schema:
                seg['properties'][k] = point_ids[0][1][k]
            shpfile.write(seg)