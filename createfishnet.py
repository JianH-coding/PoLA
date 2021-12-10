"""
Create a fishnet grid shapefile
Modified based on Rutger Kassies's code on Stack Overflow
https://stackoverflow.com/questions/59189072/creating-fishet-grid-using-python
"""

import os
import numpy as np
from osgeo import ogr


def createFishnet(projection, ulx, uly, nrow, ncol, gridWidth, gridHeight=None):
    """
    :param projection: spatial reference of the fishnet grid
    :param ulx: upper left corner x
    :param uly: upper left corner y
    :param ncol: total number of columns
    :param nrow: total number of rows
    :param gridWidth: resolution in x direction
    :param gridHeight: resolution in y direction (negative)
    :return: the fishnet layer in the memory
    """
    # create a in-memory shapefile driver
    shapefileDriver = ogr.GetDriverByName('ESRI Shapefile')
    if os.path.exists('/vsimem/fishnet.shp'):
        shapefileDriver.DeleteDataSource('/vsimem/fishnet.shp')

    # if gridHeight is None, the gridHeight is take as -gridWidth
    if gridHeight is None:
        gridHeight = -gridWidth

    # calculate the coordinates of the lower right corner
    lrx = ulx + ncol * gridWidth
    lry = uly + nrow * gridHeight

    # half of the resolution
    dx = gridWidth/2
    dy = gridHeight/2

    # center coordinates
    xx, yy = np.meshgrid(np.arange(ulx+dx, lrx+dx, gridWidth), np.arange(uly+dy, lry+dy, gridHeight))

    # initialize the output shapefile
    outputShapefile = shapefileDriver.CreateDataSource('/vsimem/fishnet.shp')
    outputLayer = outputShapefile.CreateLayer('grid', projection, geom_type=ogr.wkbPolygon)
    outputLayerDef = outputLayer.GetLayerDefn()

    # loop over each center coordinate and add the polygon to the output
    for x, y in zip(xx.ravel(), yy.ravel()):

        poly_wkt = f'POLYGON (({x-dx} {y-dy}, {x+dx} {y-dy}, {x+dx} {y+dy}, {x-dx} {y+dy}, {x-dx} {y-dy}))'
        ft = ogr.Feature(outputLayerDef)
        ft.SetGeometry(ogr.CreateGeometryFromWkt(poly_wkt))
        outputLayer.CreateFeature(ft)
        ft = None

    return outputShapefile
