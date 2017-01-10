'''
Segment a multi spectral GeoTiff image and output as a shapefile

Author: Matthew Parker
'''
import argparse
import warnings
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.colors import ListedColormap
from skimage import exposure
from skimage.segmentation import felzenszwalb
import rasterio
from rasterio.features import shapes as polygonize, sieve
import fiona

def read_gtiff_as_array(fn, band_subset=False, rescale=False):
    '''
    Reads all, or the specified bands of, a GTiff file and
    merges them into a multi-band numpy array
    '''
    with rasterio.open(fn) as gtiff:
        geo_transform, crs = gtiff.transform, gtiff.crs
        to_read = band_subset if band_subset else gtiff.indexes
        print('Bands to be processed: {}'.format(to_read))
        all_bands = []
        for b in to_read:
            if rescale:
                band = exposure.rescale_intensity(gtiff.read(b))
            else:
                band = gtiff.read(b)
            all_bands.append(band)
    if len(to_read) == 1:
        all_bands = all_bands[0]
    else:
        all_bands = np.dstack(all_bands)
    return all_bands, geo_transform, crs


def felzenszwalb_multi_band(img, scale, sigma, min_size):
    '''
    Produces segments from a multiband numpy array using the
    skimage.segmentation.felzenszwalb function. Any areas
    which are masked in the original image will also be masked
    in the segmentation.
    
    NB Development version of scikit-image is much better as this
    uses euclidean distances of all bands to compute segments,
    whereas current stable release (0.12.3) calculates segments
    from each band separately, then overlays them. This results in
    lots of small segments at the edges of the larger segments.
    '''
    with warnings.catch_warnings():
        # felzenszwalb throws warning as we are using images with
        # more than three channels
        warnings.simplefilter("ignore")
        segments = felzenszwalb(img, scale=scale, sigma=sigma, min_size=min_size)
    # rasterio sieve/shapes require int32 dtype
    segments = segments.astype('int32')

    #remove any clusters created in masked areas
    mask = (img != 0).any(2)
    segments[mask==False] = 0
    return segments, mask


def sieve_small_segments(segments, min_size, mask=None):
    '''
    Sieve small clusters from a numpy array of segments using
    the rasterio.features.sieve function.
    '''
    kwargs = dict(size=min_size, connectivity=4)
    if mask is not None:
        kwargs['mask'] = mask
    sieved = sieve(segments, **kwargs)
    return sieved


def write_segments_as_shapefile(basename, segments, geo_transform, source_crs, mask=None):
    '''
    Convert a numpy array of segments to polygons using
    rasterio.features.shapes and write the resultant records
    to a Shapefile.
    '''
    fn = basename + '.shp'
    with fiona.open(fn, 'w', driver='ESRI Shapefile', crs=source_crs,
                    schema = {'geometry': 'Polygon', 'properties': {}}) as shpfile:
        kwargs = dict(transform=geo_transform)
        if mask is not None:
            kwargs['mask'] = mask
        for shape, val, in polygonize(segments, **kwargs):
            record = dict(geometry=shape, id=val, properties={})
            shpfile.write(record)


def write_segments_as_raster(basename, segments, geo_transform, source_crs):
    '''
    Write the segments as a GTiff using rasterio.
    '''
    fn = basename + '.tif'
    with rasterio.open(fn, 'w', driver='GTiff',
                       height=segments.shape[0],
                       width=segments.shape[1],
                       count=1, dtype=segments.dtype,
                       crs=source_crs,
                       transform=geo_transform) as rfile:
        rfile.write(segments, 1)


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('-i', '--image', type=str, required=True)
    a.add_argument('-o', '--output-basename', type=str, required=True)
    a.add_argument('--band-subset', type=str, required=False, default='')
    a.add_argument('--scale', type=int, default=200, required=False)
    a.add_argument('--sigma', type=float, default=0.25, required=False)
    a.add_argument('--min-size', type=int, default=15, required=False)
    a.add_argument('--sieve', type=int, default=0, required=False)
    a.add_argument('--plot', action='store_true', default=False)
    args = a.parse_args()

    # option of only using specific bands for segmentation
    if args.band_subset:
        band_subset = [int(x) for x in args.band_subset.split(',')]
    else:
        band_subset = []

    img, geo_transform, crs = read_gtiff_as_array(args.image,
                                                  band_subset,
                                                  rescale=True)

    # perform felzenszwalb segmentation
    segments, mask = felzenszwalb_multi_band(img,
                                             scale=args.scale,
                                             sigma=args.sigma,
                                             min_size=args.min_size)

    # merge segments considered too small into larger segments. 
    if args.sieve:
        segments = sieve_small_segments(segments,
                                        min_size=args.sieve,
                                        mask=mask)

    # write segments as both GTiff and Shapefile.
    write_segments_as_raster(args.output_basename,
                             segments,
                             geo_transform,
                             crs)

    write_segments_as_shapefile(args.output_basename,
                                segments,
                                geo_transform,
                                crs,
                                mask)

    # plot the segments with random colours for quick visualisation
    if args.plot:
        cmap = ListedColormap(np.random.rand(segments.max(), 3))
        fig, ax = plt.subplots()
        ax.imshow(segments, interpolation='none', cmap=cmap)
        ax.set_axis_off()
        plt.show()