import argparse
import sys
import fiona
from shapely.geometry import shape

if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('-s','--input-shapefile', required=True, type=str)
    a.add_argument('-o', '--output-tsv', required=False, default='stdout', type=str)
    a.add_argument('--sep', required=False, default='\t', type=str)
    args = a.parse_args()
    
    if args.output_tsv == 'stdout':
        o = sys.stdout
    else:
        o = open(args.output_tsv, 'w')
    
    with fiona.open(args.input_shapefile) as f:
        for record in f:
            r_id = record['id']
            r_shape = shape(record['geometry'])
            o.write(args.sep.join([str(r_id),
                                   '{:.1f}'.format(r_shape.area),
                                   '{:.1f}\n'.format(r_shape.length)]))
            