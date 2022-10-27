import geopandas as gpd
import rasterio
from rasterio import features
import numpy as np


def landslideConversion(inputSetting, outputFilePath):
    # If the location and the volume of landslides are prescibed by polygons
    with rasterio.open(inputSetting['flowDirectionFile']) as src:
        shape = src.read(1).shape
        transform = src.transform
        rasterMeta = src.meta
    nodata = -1
    rasterMeta.update(dtype=rasterio.float64, nodata=nodata)
    # Convert the probability into a raster file
    landslide = gpd.read_file(inputSetting['prescribedLandslideFile'])
    rasterizedProbability = features.rasterize([(l, p) for l,p in zip(landslide['geometry'],landslide['Prob'] )],
                                                         out_shape=shape,
                                                         transform=transform,
                                                         fill=0,
                                                         dtype=rasterio.float64)
    with rasterio.open(outputFilePath['LandslideProbability'], 'w', **rasterMeta, compress="LZW") as src:
        src.write(rasterizedProbability, indexes=1)

    # Convert the volume into a raster file
    rasterizedVolume = features.rasterize([(l, v) for l,v in zip(landslide['geometry'],landslide['Volume'] )],
                                                         out_shape=shape,
                                                         transform=transform,
                                                         fill=0,
                                                         dtype=rasterio.float64)

    volumeClass = np.array([0, 20, 50, 500, 2000, 10000, 50000])
    volumeProbability = np.ones((len(volumeClass)-1,shape[0],shape[1]))*0
    for volumeID in range(len(volumeClass)-1):
        volumeProbability[volumeID,:,:] = np.where((rasterizedVolume>volumeClass[volumeID])&(rasterizedVolume<=volumeClass[volumeID+1])&(rasterizedVolume!=0), 1, 0)

    rasterMeta.update(count=len(volumeClass)-1)
    with rasterio.open(outputFilePath['LandslideVolumeProbability'], 'w', **rasterMeta, compress="LZW") as src:
        src.write(volumeProbability)
