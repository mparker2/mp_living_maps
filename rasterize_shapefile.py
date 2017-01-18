import argparse
import numpy as np
import rasterio
from rasterio.features import rasterize
import fiona


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('-s', '--shapefile', type=str, required=True)
    a.add_argument('-t', '--template-raster', type=str, required=True)
    a.add_argument('-o', '--output-raster', type=str, required=True)
    a.add_argument('--burn-val', type=int, required=False, default=255)
    a.add_argument('--no-data-val', type=int, default=0, required=False)
    args = a.parse_args()
    
    with rasterio.open(args.template_raster) as template:
        metadata = template.meta.copy()
        out_shape = template.shape
    metadata.update(dtype=rasterio.uint8, count=1, compress='lzw')
    with fiona.open(args.shapefile) as shp:
        img = rasterize(
            ((g['geometry'], args.burn_val) for g in shp),
            out_shape=out_shape,
            fill=args.no_data_val,
            all_touched=True,
            dtype=rasterio.uint8,
            transform=metadata['transform']
        )
    with rasterio.open(args.output_raster, 'w', **metadata) as gtiff:
        gtiff.write(img, indexes=1)