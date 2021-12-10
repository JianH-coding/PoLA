from rainfallinterpolation import interpolateRainfallFromPoints, interpolateRainfallFromField
import rasterio
import time
import os
import rasterio.shutil
import pandas as pd
import numpy as np
from numba import jit
from osgeo import ogr
from osgeo import gdal
from zonalstatistics import calculateZonalSum
from progressbar import progressBar


def hazardAnalysis(inputSetting, outputFilePath):
    """Predict hazard scenarios given the input"""
    starttime = time.time()
    landslidePrediction(inputSetting, outputFilePath)
    endtime = time.time()
    print(f'Total time: {endtime - starttime} s')


def landslidePrediction(inputSetting, outputFilePath):
    # Predict landslide probability (density) based on normalized max rolling 24-h rainfall
    # Ko, F.W. and Lo, F.L., 2016. Rainfall-based landslide susceptibility analysis for natural terrain in Hong Kong-A direct stock-taking approach. Engineering Geology, 215, pp.95-107.
    # Read the slope data
    print('Assessing the hazard...')
    with rasterio.open(inputSetting['slopeFile']) as src:
        nodataValue = src.nodatavals[0]
        slope = src.read(1)
        rasterMeta = src.meta
        rasterCellArea = -rasterMeta['transform'].determinant
        rasterMask = np.where(slope == nodataValue, True, False)  # filter = True when the cell is nodata

    # Calculate the normalized maximum rolling 24-h rainfall
    rainfallFilePath = inputSetting['rainfall24h']
    if rainfallFilePath.split('.')[-1].lower() == 'csv':
        interpolateRainfallFromPoints(inputSetting['slopeFile'], rainfallFilePath, inputSetting['resultPath'])
    else:
        interpolateRainfallFromField(inputSetting['slopeFile'], rainfallFilePath, inputSetting['resultPath'])

    with rasterio.open(outputFilePath['Rainfall']) as src:
        maxRolling24hRainfall = src.read(1)

    with rasterio.open(inputSetting['meanAnnualRainfallFile']) as src:
        meanAnnualRainfall = src.read(1)

    normalizedMaxRolling24hRainfall = np.divide(maxRolling24hRainfall, meanAnnualRainfall)
    maxRolling24hRainfall = None
    meanAnnualRainfall = None
    normalizedMaxRolling24hRainfall[rasterMask] = nodataValue
    rasterMeta.update({'dtype': 'float64'})
    with rasterio.open(outputFilePath['NormalizedRainfallFine'], 'w', **rasterMeta, compress="LZW") as src:
        src.write(normalizedMaxRolling24hRainfall, 1)
    normalizedMaxRolling24hRainfall[rasterMask] = 0  # set nodata cells as 0 to avoid overflow in subsequent calculation

    # Calculate the landslide frequency for each cell
    # Read the rainfall landslide model, log10(density) = k*rainfall + b
    landslidePredict = pd.read_csv(inputSetting['landslidePredictionModel'], sep=',', skiprows=1)
    areaRatio = rasterCellArea/(1000*1000)  # convert the landslide density (no./km^2) to the landslide number per cell (no./cellArea)
    landslideFrequency = np.zeros_like(slope, dtype='float64')
    for slopeClass in progressBar(list(range(len(landslidePredict.index))), prefix='Progress:', suffix='Complete', decimals=2, length=50):
        slope_lb = landslidePredict.loc[slopeClass, 'Slope_lb']
        slope_ub = landslidePredict.loc[slopeClass, 'Slope_ub']
        k = landslidePredict.loc[slopeClass, 'k']
        b = landslidePredict.loc[slopeClass, 'b']
        rainfall_lb = landslidePredict.loc[slopeClass, 'Rainfall_lb']
        rainfall_ub = landslidePredict.loc[slopeClass, 'Rainfall_ub']
        maxLandslideFrequency = areaRatio*10**(k*rainfall_ub + b)  # maximum landslide probability is a statistical maxima of landslide density
        landslideFrequency = calculateFrequency(slope, slope_lb, slope_ub, normalizedMaxRolling24hRainfall, rainfall_lb, rainfall_ub, rasterMask, areaRatio, k, b, maxLandslideFrequency, landslideFrequency)

    normalizedMaxRolling24hRainfall = None
    slope = None

    # Read the natural terrain data
    with rasterio.open(inputSetting['naturalTerrainFile']) as src:
        naturalTerrain = src.read(1)

    # Read the geology data
    with rasterio.open(inputSetting['geologyFile']) as src:
        geology = src.read(1)

    landslideFrequency[np.where(naturalTerrain == 0)] = 0  # filter out the landslide frequency in urban areas
    landslideFrequency = np.where((geology == 1) | (geology == 2), 1.5 * landslideFrequency, landslideFrequency)  # adjust the landslide frequency to 1.5 times for volcanic and sedimentary areas
    landslideFrequency = np.where(geology == 3, 0.5 * landslideFrequency, landslideFrequency)  # adjust the landslide frequency to 0.5 times for intrusive areas
    landslideFrequency[np.where(geology >= 6)] = 0  # adjust the landslide frequency to 0 for reclaimed and reservoir areas
    landslideFrequency[rasterMask] = nodataValue  # filter out the landslide probability at nodata cells

    geology = None
    naturalTerrain = None
    rasterMask = None

    # Write the landslide frequency raster file
    with rasterio.open(outputFilePath['LandslideFrequencyFine'], 'w', **rasterMeta, compress="LZW") as src:
        src.write(landslideFrequency, 1)
    landslideFrequency = None

    DEMRaster = gdal.Open(inputSetting['DEMFile'])
    spatialReference = DEMRaster.GetSpatialRef()
    geoTransform = DEMRaster.GetGeoTransform()
    minX = geoTransform[0]
    maxY = geoTransform[3]
    maxX = minX + geoTransform[1] * DEMRaster.RasterXSize
    minY = maxY + geoTransform[5] * DEMRaster.RasterYSize
    pixelWidth = geoTransform[1]
    pixelHeight = geoTransform[5]

    # Convert the landslide frequency from 5 m-by-5 m grid to 20 m-by-20 m grid
    gdal.Warp(outputFilePath['LandslideFrequency'], outputFilePath['LandslideFrequencyFine'], srcNodata=nodataValue, dstNodata=nodataValue, outputBounds=(minX, minY, maxX, maxY), dstSRS=spatialReference, xRes=pixelWidth, yRes=-pixelHeight, resampleAlg="sum", format='GTiff', creationOptions=["COMPRESS=LZW", "PREDICTOR=3"])

    os.environ['SHAPE_ENCODING'] = "utf-8"
    landslideSum = calculateZonalSum(inputSetting['zoningFile'], outputFilePath['LandslideFrequency'], 'Sequence')
    shapefileDriver = ogr.GetDriverByName('ESRI Shapefile')
    landslideZoningSumShapefile = shapefileDriver.CreateDataSource(outputFilePath['LandslideZoning'])
    landslideZoningShapefile = shapefileDriver.Open(inputSetting['zoningFile'])
    landslideZoningLayer = landslideZoningShapefile.GetLayer(0)
    landslideZoningSumShapefile.CopyLayer(landslideZoningLayer, 'LandslideZoning')

    landslideZoningLayer = None
    landslideZoningShapefile = None

    # Count the number of landslides in each summary zone
    landslideZoningSumLayer = landslideZoningSumShapefile.GetLayer(0)
    landslideZoningSumLayerDefinition = landslideZoningSumLayer.GetLayerDefn()
    zoningSumField = ogr.FieldDefn('Landslide', ogr.OFTReal)
    landslideZoningSumLayer.CreateField(zoningSumField)
    sequenceFieldIndex = landslideZoningSumLayerDefinition.GetFieldIndex('Sequence')
    for zone in landslideZoningSumLayer:
        sequence = zone.GetFieldAsInteger(sequenceFieldIndex)
        zone.SetField('Landslide', landslideSum[sequence])
        landslideZoningSumLayer.SetFeature(zone)

    landslideZoningSumLayer = None
    landslideZoningSumShapefile = None

    # Convert the landslide frequency to the landslide probability (the probability of more than 1 landslide occurs)
    with rasterio.open(outputFilePath['LandslideFrequency']) as src:
        nodataValue = src.nodatavals[0]
        landslideFrequency = src.read(1)
        rasterMeta = src.meta
        rasterMask = np.where(landslideFrequency == nodataValue, True, False)  # filter = True when the cell is nodata
        landslideFrequency[rasterMask] = 0
        landslideProbability = 1 - np.exp(-landslideFrequency)  # calculate the landslide probability based on landslide frequency assuming a Poisson distribution
        landslideProbability[rasterMask] = nodataValue
    landslideFrequency = None

    # Write the landslide probability raster file
    with rasterio.open(outputFilePath['LandslideProbability'], 'w', **rasterMeta, compress="LZW") as src:
        src.write(landslideProbability, 1)
    landslideProbability = None

    # Convert the normalized rainfall from 5 m-by-5 m grid to 20 m-by-20 m grid
    gdal.Warp(outputFilePath['NormalizedRainfall'], outputFilePath['NormalizedRainfallFine'], srcNodata=nodataValue, dstNodata=nodataValue, outputBounds=(minX, minY, maxX, maxY), dstSRS=spatialReference, xRes=pixelWidth, yRes=-pixelHeight, resampleAlg="average", format='GTiff', creationOptions=["COMPRESS=LZW", "PREDICTOR=3"])

    with rasterio.open(outputFilePath['NormalizedRainfall']) as src:
        normalizedRainfall = src.read(1)

    # Read the rainfall-landslide volume model
    landslideVolumeModel = pd.read_csv(inputSetting['landslideVolumeModel'], sep=',', skiprows=1)
    numberOfVolumeClasses = len(landslideVolumeModel.columns)-2

    # Calculate the probability of each volume class
    landslideVolumeProbability= np.zeros((numberOfVolumeClasses, rasterMask.shape[0], rasterMask.shape[1]))

    for rainfallClass in range(len(landslideVolumeModel.index)):
        rainfall_lb = landslideVolumeModel.loc[rainfallClass, 'Rainfall_lb']
        rainfall_ub = landslideVolumeModel.loc[rainfallClass, 'Rainfall_ub']
        volumeProbabilityArray = landslideVolumeModel.iloc[rainfallClass, 2:2+numberOfVolumeClasses].to_numpy().reshape((numberOfVolumeClasses, 1, 1))
        landslideVolumeProbability = calculateVolumeProbability(rainfall_lb, rainfall_ub, normalizedRainfall, rasterMask, volumeProbabilityArray, landslideVolumeProbability)
    landslideVolumeProbability[:, rasterMask] = nodataValue

    # Write the landslide probability raster file
    rasterMeta.update(count=numberOfVolumeClasses)
    with rasterio.open(outputFilePath['LandslideVolumeProbability'], 'w', **rasterMeta, compress="LZW") as src:
        src.write(landslideVolumeProbability)

    normalizedRainfall = None
    landslideProbabilityVolume = None

    print('Natural terrain landslide probabilities have been calculated successfully.')


@jit(nopython=True, fastmath=True)
def calculateFrequency(slope, slope_lb, slope_ub, normalizedMaxRolling24hRainfall, rainfall_lb, rainfall_ub, rasterMask, areaRatio, k, b, maxLandslideFrequency, landslideFrequency):
    landslideFrequency = np.where(
        (slope > slope_lb) & (slope <= slope_ub) & (normalizedMaxRolling24hRainfall > rainfall_lb) & (
                    normalizedMaxRolling24hRainfall <= rainfall_ub) & (~rasterMask),
        np.minimum(areaRatio * 10 ** (k * normalizedMaxRolling24hRainfall + b),
                   maxLandslideFrequency),
        landslideFrequency)

    return landslideFrequency

@jit(nopython=True, fastmath=True)
def calculateVolumeProbability(rainfall_lb, rainfall_ub, normalizedRainfall, rasterMask, volumeProbability, landslideVolumeProbability):
    filter = (normalizedRainfall >= rainfall_lb) & (normalizedRainfall < rainfall_ub) & (~rasterMask)
    filterMatrix = np.full_like(landslideVolumeProbability, False, dtype=np.bool_)
    volumeProbabilityMatrix = volumeProbability*np.ones_like(landslideVolumeProbability)
    for i in range(landslideVolumeProbability.shape[0]):
        filterMatrix[i] = filter
    landslideVolumeProbability = np.where(filterMatrix, volumeProbabilityMatrix, landslideVolumeProbability)
    return landslideVolumeProbability
