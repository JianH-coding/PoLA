"""
This module is revised based on
https://pcjericks.github.io/py-gdalogr-cookbook/raster_layers.html#calculate-zonal-statistics
https://gis.stackexchange.com/questions/262240/python-creating-layers-and-rasterizing-polygons-in-gdal
"""

from osgeo import gdal
from osgeo import ogr
from osgeo import osr
import numpy


def calculateZonalStatistics(input_zone_polygon, input_value_raster, field_name):

    # Open data
    raster = gdal.Open(input_value_raster)
    shapefile = ogr.Open(input_zone_polygon)
    layer = shapefile.GetLayer()
    layerDefinition = layer.GetLayerDefn()
    fieldIndex = layerDefinition.GetFieldIndex(field_name)
    if fieldIndex == -1:
        print(f'Cannot find the field named {field_name}')
        return
    fieldValue = []
    for feature in layer:
        fieldValue.append(feature.GetFieldAsInteger(fieldIndex))
    fieldValue = numpy.unique(numpy.array(fieldValue))
    fieldValue = numpy.sort(fieldValue)

    layerExtent = layer.GetExtent()
    xminLayer = layerExtent[0]
    xmaxLayer = layerExtent[1]
    yminLayer = layerExtent[2]
    ymaxLayer = layerExtent[3]

    statDict = {}

    # Get raster georeference info
    transform = raster.GetGeoTransform()
    xminRaster = transform[0]
    ymaxRaster = transform[3]
    pixelWidth = transform[1]
    pixelHeight = transform[5]
    ncolRaster = raster.RasterXSize
    nrowRaster = raster.RasterYSize
    xmaxRaster = xminRaster + ncolRaster*pixelWidth
    yminRaster = ymaxRaster + nrowRaster*pixelHeight

    # If the extents of the shapefile and the raster are not intersected, return dict with zeros
    condition1 = (xmaxRaster < xminLayer) or (yminRaster > ymaxLayer)
    condition2 = (xmaxLayer < xminRaster) or (yminLayer > ymaxRaster)

    if condition1 or condition2:  # if the extents does not intersect
        for field in fieldValue:
            statDict[field] = (0, 0, 0, 0)
        return statDict

    # Create memory target raster
    ncolLayer = int((xmaxLayer-xminLayer)/pixelWidth)
    nrowLayer = int((ymaxLayer-yminLayer)/(-pixelHeight))
    yminLayer = ymaxLayer + nrowLayer*pixelHeight
    xmaxLayer = xminLayer + ncolLayer*pixelWidth
    target_ds = gdal.GetDriverByName('MEM').Create('', ncolLayer, nrowLayer, 1, gdal.GDT_Int16)
    target_ds.SetGeoTransform((
        xminLayer, pixelWidth, 0,
        ymaxLayer, 0, pixelHeight,
    ))

    # Create for target raster the same projection as for the value raster
    raster_srs = osr.SpatialReference()
    raster_srs.ImportFromWkt(raster.GetProjectionRef())
    target_ds.SetProjection(raster_srs.ExportToWkt())

    # Fill the target raster with nodata value
    tempTile = target_ds.GetRasterBand(1)
    tempTile.Fill(-9999)
    tempTile.SetNoDataValue(-9999)

    # Rasterize zone polygon to raster
    gdal.RasterizeLayer(target_ds, [1], layer, options=[f"ATTRIBUTE={field_name}"])

    # Warp the raster to the same extent of the shapefile layer
    rasterWarped = gdal.Warp('', raster, dstNodata=-9999, outputBounds=(xminLayer, yminLayer, xmaxLayer, ymaxLayer), format='vrt')
    banddataraster = rasterWarped.GetRasterBand(1)
    nodataValue = banddataraster.GetNoDataValue()
    dataraster = banddataraster.ReadAsArray(0, 0, ncolLayer, nrowLayer).astype(numpy.float)
    dataraster[dataraster == nodataValue] = 0  # Set nodata cell to zero to avoid involving nodata in the input raster

    bandmask = target_ds.GetRasterBand(1)
    datamask = bandmask.ReadAsArray(0, 0, ncolLayer, nrowLayer).astype(numpy.int16)

    for field in fieldValue:
        # Create a mask zone of raster with respect to the fid
        mask = numpy.logical_not(datamask==field)
        zoneraster = numpy.ma.masked_array(dataraster, mask)
        # Calculate statistics of zonal raster
        statDict[field] = (numpy.sum(zoneraster), numpy.mean(zoneraster), numpy.std(zoneraster), numpy.var(zoneraster))
    return statDict


def calculateZonalSum(input_zone_polygon, input_value_raster, field_name):

    # Open data
    raster = gdal.Open(input_value_raster)
    shapefile = ogr.Open(input_zone_polygon)
    layer = shapefile.GetLayer()
    layerDefinition = layer.GetLayerDefn()
    fieldIndex = layerDefinition.GetFieldIndex(field_name)
    if fieldIndex == -1:
        print(f'Cannot find the field named {field_name}')
        return
    fieldValue = []
    for feature in layer:
        fieldValue.append(feature.GetFieldAsInteger(fieldIndex))
    fieldValue = numpy.unique(numpy.array(fieldValue))
    fieldValue = numpy.sort(fieldValue)

    layerExtent = layer.GetExtent()
    xminLayer = layerExtent[0]
    xmaxLayer = layerExtent[1]
    yminLayer = layerExtent[2]
    ymaxLayer = layerExtent[3]

    statDict = {}

    # Get raster georeference info
    transform = raster.GetGeoTransform()
    xminRaster = transform[0]
    ymaxRaster = transform[3]
    pixelWidth = transform[1]
    pixelHeight = transform[5]
    ncolRaster = raster.RasterXSize
    nrowRaster = raster.RasterYSize
    xmaxRaster = xminRaster + ncolRaster*pixelWidth
    yminRaster = ymaxRaster + nrowRaster*pixelHeight

    # If the extents of the shapefile and the raster are not intersected, return dict with zeros
    condition1 = (xmaxRaster < xminLayer) or (yminRaster > ymaxLayer)
    condition2 = (xmaxLayer < xminRaster) or (yminLayer > ymaxRaster)

    if condition1 or condition2:  # if the extents does not intersect
        for field in fieldValue:
            statDict[field] = 0
        return statDict

    # Create memory target raster
    ncolLayer = int((xmaxLayer-xminLayer)/pixelWidth)
    nrowLayer = int((ymaxLayer-yminLayer)/(-pixelHeight))
    yminLayer = ymaxLayer + nrowLayer*pixelHeight
    xmaxLayer = xminLayer + ncolLayer*pixelWidth
    target_ds = gdal.GetDriverByName('MEM').Create('', ncolLayer, nrowLayer, 1, gdal.GDT_Int16)
    target_ds.SetGeoTransform((
        xminLayer, pixelWidth, 0,
        ymaxLayer, 0, pixelHeight,
    ))

    # Create for target raster the same projection as for the value raster
    raster_srs = osr.SpatialReference()
    raster_srs.ImportFromWkt(raster.GetProjectionRef())
    target_ds.SetProjection(raster_srs.ExportToWkt())

    # Fill the target raster with nodata value
    tempTile = target_ds.GetRasterBand(1)
    tempTile.Fill(-9999)
    tempTile.SetNoDataValue(-9999)

    # Rasterize zone polygon to raster
    gdal.RasterizeLayer(target_ds, [1], layer, options=[f"ATTRIBUTE={field_name}"])

    # Warp the raster to the same extent of the shapefile layer
    rasterWarped = gdal.Warp('', raster, dstNodata=-9999, outputBounds=(xminLayer, yminLayer, xmaxLayer, ymaxLayer), format='vrt')
    banddataraster = rasterWarped.GetRasterBand(1)
    nodataValue = banddataraster.GetNoDataValue()
    dataraster = banddataraster.ReadAsArray(0, 0, ncolLayer, nrowLayer).astype(numpy.float)
    dataraster[dataraster == nodataValue] = 0  # Set nodata cell to zero to avoid involving nodata in the input raster

    bandmask = target_ds.GetRasterBand(1)
    datamask = bandmask.ReadAsArray(0, 0, ncolLayer, nrowLayer).astype(numpy.int16)

    for field in fieldValue:
        # Create a mask zone of raster with respect to the fid
        mask = numpy.logical_not(datamask==field)
        zoneraster = numpy.ma.masked_array(dataraster, mask)
        # Calculate statistics of zonal raster
        statDict[field] = numpy.sum(zoneraster)
    return statDict
