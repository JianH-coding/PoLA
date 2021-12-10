# Interpolate rainfall point

import numpy as np
import pandas as pd
from scipy.interpolate import Rbf, RectBivariateSpline
from osgeo import gdal


def interpolateField(point, xmin, xmax, ymin, ymax, xstep, ystep, xcoarsestep=100, ycoarsestep=100, epsilon=2):
    """
    Interpolate 2-D point data using 2-step methods: radius-based function (multiquadrics) to a coarse grid and RectBivariateSpline function to the final fine grid
    :param point: float ndarray: numpy ndarray of a shape of (n,3), i.e., (X, Y, Z)
    :param xmin: float: the left boundary of the interpolated field
    :param xmax: float: the right boundary of the interpolated field
    :param ymin: float: the lower boundary of the interpolated field
    :param xmax: float: the upper boundary of the interpolated field
    :param xstep: float: x step size for the fine grid interpolation
    :param ystep: float: y step size for the fine grid interpolation
    :param xcoarsestep: float: x step size for the coarse grid interpolation
    :param ycoarsestep: float: y step size for the coarse grid interpolation
    :param epsilon: float, optional: the parameter of radius-based function
    :return: float ndarray: the interpolated numpy ndarray
    """

    x = point[:, 0]
    y = point[:, 1]
    z = point[:, 2]

    # Construct the coarse grid for RBF interpolation
    nxcoarse = int((xmax - xmin) / xcoarsestep) + 1
    nycoarse = int((ymax - ymin) / ycoarsestep) + 1
    xmaxcoarse = xmin + nxcoarse*xcoarsestep
    ymaxcoarse = ymin + nycoarse*ycoarsestep
    Xcoarse = np.linspace(xmin, xmaxcoarse, nxcoarse+1)
    Ycoarse = np.linspace(ymin, ymaxcoarse, nycoarse+1)

    XX, YY = np.meshgrid(Xcoarse, Ycoarse)

    # Use RBF to interpolate the data to a coarse grid
    rbf = Rbf(x, y, z, epsilon=epsilon)
    ZZ = rbf(XX, YY)

    # Use RectBivariateSpline to interpolate the coarse grid data to the final fine grid
    rbs = RectBivariateSpline(Ycoarse, Xcoarse, ZZ)
    nx = int(np.round((xmax-xmin)/xstep))
    ny = int(np.round((ymax-ymin)/ystep))
    X = np.linspace(xmin, xmax, nx+1)
    Y = np.linspace(ymin, ymax, ny+1)
    Z = rbs(Y, X)

    return Z[::-1, :]


def interpolateRainfallFromPoints(sampleRasterFile, rainfallFile, outputPath, format="GTiff", maskData=False, outputdtype='int'):
    """
    Interpolate rainfall field from point observations
    :param sampleRaster: str: file name of the sample raster. The interpolated rainfall will have the same extent, resolution, spatial reference and projection as the sample raster
    :param rainfallFile: str: a csv file contains the observed rainfall data. The first and the second columns are X and Y locations of observed points, respectively. From the third column on are the observed values. The location columns should be denoted as X and Y in the first row. The interpolated field from each column will be saved to a file with the same name as the corresponding column name.
    :param outputPath: str: the file path (no the file name) of the output rasters without the slash
    :param format: str: the format of the output raster, default="GTiff". Output format can be either "GTiff" or "AAIGrid".
    :param maskData: bool: default=False. If maskData=True, the sample raster will be used as a mask layer for the interpolated rain field
    :return: None
    """

    sampleRaster = gdal.Open(sampleRasterFile)
    transform = sampleRaster.GetGeoTransform()
    spatialReference = sampleRaster.GetSpatialRef()
    sampleBand = sampleRaster.GetRasterBand(1)

    nx = sampleRaster.RasterXSize
    ny = sampleRaster.RasterYSize
    xul = transform[0]
    yul = transform[3]
    pixelWidth = transform[1]
    pixelHeight = transform[5]

    xmin = xul + pixelWidth/2  # x coordinate of the centre of the left boundary cell
    xmax = xul + (nx - 0.5) * pixelWidth  # x coordinate of the centre of the right boundary cell
    ymin = yul - (ny - 0.5) * (-pixelHeight)  # y coordinate of the centre of the lower boundary cell
    ymax = yul - (-pixelHeight)/2  # y coordinate of the centre of the upper boundary cell

    sampleArray = sampleBand.ReadAsArray(0, 0, nx, ny).astype(np.float)
    sampleNodate = sampleBand.GetNoDataValue()

    # Read the rainfall .csv file
    rainfallTable = pd.read_csv(rainfallFile)
    x = rainfallTable['X'].to_numpy()
    y = rainfallTable['Y'].to_numpy()
    colNameList = list(rainfallTable.columns)
    colNameList = [item for item in colNameList if (item != 'X') and (item != 'Y')]  # remove X and Y

    for colName in colNameList:
        if (rainfallTable[colName].dtype != np.float64) and (rainfallTable[colName].dtype != np.int64):  # check the dtype of the column
            continue

        notnan = rainfallTable[colName].notna()

        if np.count_nonzero(notnan) < 2:
            continue

        # Create a raster in memory
        if outputdtype == 'float':
            target_ds = gdal.GetDriverByName('MEM').Create('', nx, ny, 1, gdal.GDT_Float32)
            nodata = -9999
        else:
            target_ds = gdal.GetDriverByName('MEM').Create('', nx, ny, 1, gdal.GDT_Int16)
            nodata = 32767
        target_ds.SetGeoTransform(transform)
        target_ds.SetSpatialRef(spatialReference)

        outputBandTemp = target_ds.GetRasterBand(1)
        outputBandTemp.SetNoDataValue(nodata)

        rainfallPoint = rainfallTable[notnan]

        point = np.array([rainfallPoint['X'].to_numpy(), rainfallPoint['Y'].to_numpy(), rainfallPoint[colName].to_numpy()]).transpose()
        interpolatedField = interpolateField(point, xmin, xmax, ymin, ymax, pixelWidth, -pixelHeight)
        interpolatedField = np.where(interpolatedField < 0, 0, interpolatedField)  # rainfall cannot be negative
        if maskData:
            interpolatedField = np.where(sampleArray == sampleNodate, nodata, interpolatedField)

        outputBandTemp.WriteArray(interpolatedField, 0, 0)
        outputBandTemp.ComputeStatistics(1)

        if len(colNameList) == 1:  # if there is only one column of observation
            outputFilename = 'Rainfall'
        else:
            outputFilename = colName

        if format == "AAIGrid":
            outputRaster = gdal.Translate(f'{outputPath}/{outputFilename}.asc', target_ds, format=format, noData=nodata)
        elif outputdtype == 'float':
            outputRaster = gdal.Translate(f'{outputPath}/{outputFilename}.tif', target_ds, format=format, noData=nodata, creationOptions=["COMPRESS=LZW", "PREDICTOR=3"])
        elif outputdtype == 'int':
            outputRaster = gdal.Translate(f'{outputPath}/{outputFilename}.tif', target_ds, format=format, noData=nodata, creationOptions=["COMPRESS=LZW", "PREDICTOR=2"])

        target_ds = None
        outputRaster = None


def interpolateRainfallFromField(sampleRasterFile, rainfallFile, outputPath, format="GTiff", maskData=False, outputdtype='int'):
    """
    Interpolate rainfall field from raster file of arbitary resolutions to the extent and resolution same as the smaple raster file.
    :param sampleRaster: str: file name of the sample raster. The interpolated rainfall will have the same extent, resolution, spatial reference and projection as the sample raster
    :param rainfallFile: str: a raster file contains the observed rainfall data.
    :param outputPath: str: the file path (no the file name) of the output rasters without the slash
    :param format: str: the format of the output raster, default="GTiff". Output format can be either "GTiff" or "AAIGrid".
    :param maskData: bool: default=False. If maskData=True, the sample raster will be used as a mask layer for the interpolated rain field
    :return: None
    """

    sampleRaster = gdal.Open(sampleRasterFile)
    transform = sampleRaster.GetGeoTransform()
    spatialReference = sampleRaster.GetSpatialRef()
    sampleBand = sampleRaster.GetRasterBand(1)
    nodataValue = sampleBand.GetNoDataValue()

    nx = sampleRaster.RasterXSize
    ny = sampleRaster.RasterYSize
    minX = transform[0]
    maxY = transform[3]
    pixelWidth = transform[1]
    pixelHeight = transform[5]
    maxX = minX + nx*pixelWidth
    minY = maxY + ny*pixelHeight

    rainfallRaster = gdal.Open(rainfallFile)
    rainfallBand = rainfallRaster.GetRasterBand(1)
    sourceNodata = rainfallBand.GetNoDataValue()
    rainfallBand = None
    rainfallRaster = None

    outputFilename = 'Rainfall'

    gdal.Warp(f'{outputPath}/{outputFilename}.tif', rainfallFile, srcNodata=sourceNodata,
              dstNodata=nodataValue, outputBounds=(minX, minY, maxX, maxY), dstSRS=spatialReference, xRes=pixelWidth,
              yRes=-pixelHeight, resampleAlg="average", format='GTiff', creationOptions=["COMPRESS=LZW", "PREDICTOR=3"])

