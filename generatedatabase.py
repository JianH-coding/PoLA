"""Generate landslide potential trail database and building location database"""

import rasterio
import numpy as np
import pandas as pd
import geopandas as gpd
from osgeo import ogr
from numba import jit
import time
import ujson
import os
from os.path import dirname
from progressbar import progressBar
from createfishnet import createFishnet


def generatePotentialTrailDatabase(inputSetting, maskFile=None):
    # Read the landslide potential trail list file
    landslidePotentialTrailList = pd.read_csv(inputSetting['landslidePotentialTrailListFile'], sep=',', skiprows=1)
    landslidePotentialTrailList = landslidePotentialTrailList.sort_values(by=['StartRow'])
    numberOfPotentialTrailFiles = len(landslidePotentialTrailList.index)

    if not os.path.exists(landslidePotentialTrailList.loc[0, 'FileName']):
        print('The landslide potential trail file was not found.')
        print('Start generating the potential trail database:')
        if not os.path.exists(dirname(landslidePotentialTrailList.loc[0, 'FileName'])):
            os.makedirs(dirname(landslidePotentialTrailList.loc[0, 'FileName']))

        with rasterio.open(inputSetting['DEMFile']) as src:
            DEM = src.read(1)
            ncol = src.meta['width']
            nrow = src.meta['height']
            cellSize = src.meta['transform'].a

        with rasterio.open(inputSetting['slopeForTrailFile']) as src:
            slope = src.read(1)

        with rasterio.open(inputSetting['flowDirectionFile']) as src:
            flowDirection = src.read(1)

        if maskFile: # cells with mask value = 0 will be ignored in the trail database to reduce file size
            with rasterio.open(maskFile) as src:
                mask = src.read(1)
        else:
            mask = np.ones_like(slope)

        landslidePredict = pd.read_csv(inputSetting['landslidePredictionModel'], sep=',', skiprows=1)
        slopeLowerBound = landslidePredict['Slope_lb'].min()
        landslideRunoutModel = pd.read_csv(inputSetting['landslideRunoutModel'], sep=',', skiprows=1)
        numberOfVolumeClasses = len(landslideRunoutModel.columns)-2
        trailProbabilityModel = landslideRunoutModel.iloc[:, 2:2+numberOfVolumeClasses].to_numpy()
        trailProbabilityModel = np.cumsum(trailProbabilityModel[::-1], axis=0)[::-1].T
        maximumRunoutDistance = landslideRunoutModel['RunoutDistance_ub'].max()
        # According to the statistics of landslide runout, most landslides ceased to move within 50 m after when the terrain is flatter than 15 degrees (GEO Report No.337 P19).
        maximumNumberOfCellBeyond15 = 50/cellSize
        potentialLandslide = np.where((mask > 0) & (slope > slopeLowerBound), 1, 0)
        del mask

        starttime = time.time()
        currentFileIndex = 0
        if not os.path.exists(os.path.split(landslidePotentialTrailList.loc[currentFileIndex, 'FileName'])[0]):
            os.makedirs(os.path.split(landslidePotentialTrailList.loc[currentFileIndex, 'FileName'])[0])
        f = None
        isFirstRow = False
        for row in progressBar(list(range(nrow)), prefix='Progress:', suffix='Complete', decimals=2, length=50):
            if row == landslidePotentialTrailList.loc[currentFileIndex, 'StartRow']:
                f = open(landslidePotentialTrailList.loc[currentFileIndex, 'FileName'], 'a')
                f.write('{')
                isFirstRow = True

            if f:
                colDict = ''
                for col in range(ncol):
                    trailRow, trailCol, trailTravelAngle, trailProbability = findTrail(row, col, nrow, ncol, cellSize,
                                                                                       potentialLandslide, DEM, slope,
                                                                                       flowDirection,
                                                                                       trailProbabilityModel,
                                                                                       maximumRunoutDistance,
                                                                                       maximumNumberOfCellBeyond15)
                    if trailRow.size > 0:
                        if colDict:
                            colDict = f'{colDict}, "{col}": [{trailRow.tolist()}, {trailCol.tolist()}, {np.around(trailTravelAngle, 1).tolist()}, {np.around(trailProbability, 3).tolist()}]'
                        else:
                            colDict = f'"{col}": [{trailRow.tolist()}, {trailCol.tolist()}, {np.around(trailTravelAngle, 1).tolist()}, {np.around(trailProbability, 3).tolist()}]'

                if colDict:
                    if isFirstRow:
                        f.write(f'"{row}": {{{colDict}}}')
                        isFirstRow = False
                    else:
                        f.write(f', "{row}": {{{colDict}}}')

                if (row == landslidePotentialTrailList.loc[currentFileIndex, 'EndRow']) or (row == nrow-1):
                    f.write('}')
                    f.close()
                    f = None
                    currentFileIndex += 1
            if currentFileIndex == len(landslidePotentialTrailList):
                break

        endtime = time.time()
        print(f'Total time: {endtime - starttime} s')


# @jit(nopython=True, fastmath=True)
def findTrail(row, col, nrow, ncol, cellSize, potentialLandslide, DEM, slope, flowDirection, trailProbabilityModel, maximumRunoutDistance, maximumNumberOfCellBeyond15):

    trailRow = np.empty(0, np.int64)
    trailCol = np.empty(0, np.int64)
    trailTravelAngle = np.empty(0, np.float64)
    trailProbability = np.empty((0,0), np.float64)

    if potentialLandslide[row, col] == 0:
        return trailRow, trailCol, trailTravelAngle, trailProbability

    trailRow = np.append(trailRow, row)  # the cell that the landslide occurs is the head of the trail with a probability of 1 and a angle of reach of the slope
    trailCol = np.append(trailCol, col)
    # trailTravelAngle = np.append(trailTravelAngle, slope[row, col])
    trailTravelAngle = np.append(trailTravelAngle, 89)

    runoutDistanceUnit = 0
    cellInTrailCount = 0
    cellBeyond15Count = 0
    rowOriginal = row
    colOriginal = col


    while True:
        nextRow, nextCol, dist = findDownstreamCell(flowDirection[row, col], row, col)
        if (nextRow < 0) or (nextCol < 0) or (nextRow >= nrow) or (nextCol >= ncol) or (DEM[nextRow, nextCol]>DEM[row, col]) or (potentialLandslide[nextRow, nextCol]==0):
            break

        runoutDistance = cellSize * (runoutDistanceUnit + 1)
        travelAngle = 180/np.pi*np.arctan((DEM[rowOriginal, colOriginal] - DEM[nextRow, nextCol]) / runoutDistance)

        if runoutDistance > maximumRunoutDistance:
            break

        if (cellBeyond15Count > 0) or (slope[nextRow, nextCol] < 15):
            cellBeyond15Count += 1
        if cellBeyond15Count >= maximumNumberOfCellBeyond15:
            break

        trailRow = np.append(trailRow, nextRow)
        trailCol = np.append(trailCol, nextCol)
        trailTravelAngle = np.append(trailTravelAngle, travelAngle)
        cellInTrailCount += 1
        runoutDistanceUnit += dist
        row = nextRow
        col = nextCol

    if trailRow.size > 0:
        # If the trail is not empty, calculate the probability based on runout distance
        trailProbability = trailProbabilityModel[:, :cellInTrailCount+1]

    return trailRow, trailCol, trailTravelAngle, trailProbability


@jit(nopython=True, fastmath=True)
def findDownstreamCell(flowDirection, row, col):
    """Find the downstream cell based on the D8 flow direction"""
    if flowDirection == 1:
        nextRow = row
        nextCol = col + 1
        dist = 1
    elif flowDirection == 2:
        nextRow = row + 1
        nextCol = col + 1
        dist = 1.414
    elif flowDirection == 4:
        nextRow = row + 1
        nextCol = col
        dist = 1
    elif flowDirection == 8:
        nextRow = row + 1
        nextCol = col - 1
        dist = 1.414
    elif flowDirection == 16:
        nextRow = row
        nextCol = col - 1
        dist = 1
    elif flowDirection == 32:
        nextRow = row - 1
        nextCol = col - 1
        dist = 1.414
    elif flowDirection == 64:
        nextRow = row - 1
        nextCol = col
        dist = 1
    elif flowDirection == 128:
        nextRow = row - 1
        nextCol = col + 1
        dist = 1.414
    else:
        nextRow = -1
        nextCol = -1
        dist = 0
    return nextRow, nextCol, dist


def generateBuildingLocationDatabase(inputSetting):
    if not os.path.exists(inputSetting['buildingLocationFile']):
        print('The building location file was not found.')
        print('Start generating the building location database:')

        buildingLocationDatabase = {}  # building location database is a dict {"BuildingID":[[rows],[cols]]}

        with rasterio.open(inputSetting['DEMFile']) as src:
            upperLeftXGlobalGrid = src.meta['transform'].xoff  # x coordinate of the upper left origin of the global grid
            upperLeftYGlobalGrid = src.meta['transform'].yoff  # y coordinate of the upper left origin of the global grid
            cellSize = src.meta['transform'].a

        shapefileDriver = ogr.GetDriverByName('ESRI Shapefile')
        buildingShapefile = shapefileDriver.Open(inputSetting['buildingFile'], 0)
        buildingLayer = buildingShapefile.GetLayer(0)
        buildingLayerDefinition = buildingLayer.GetLayerDefn()
        buildingIDFieldIndex = buildingLayerDefinition.GetFieldIndex('BuildingID')
        projection = buildingLayer.GetSpatialRef()
        buildingCount = buildingLayer.GetFeatureCount()

        for nbuilding in progressBar(list(range(buildingCount)), prefix='Progress:', suffix='Complete', decimals=2, length=50):
            building = buildingLayer.GetFeature(nbuilding)
            buildingGeometry = building.geometry()
            envelope = np.array(buildingGeometry.GetEnvelope())
            upperLeftXLocalGrid, upperLeftYLocalGrid, nrow, ncol, rowOffset, colOffset = calculateLocalGridParameters(envelope, upperLeftXGlobalGrid, upperLeftYGlobalGrid, cellSize)
            localGrid = createFishnet(projection, upperLeftXLocalGrid, upperLeftYLocalGrid, nrow, ncol, cellSize)
            localGridLayer = localGrid.GetLayer(0)
            localGridLayer.SetSpatialFilter(buildingGeometry)
            rows = []
            cols = []
            for localCell in localGridLayer:
                localCellID = localCell.GetFID()
                rows.append(int(localCellID / ncol) + rowOffset)
                cols.append(int(localCellID % ncol) + colOffset)
            buildingLocationDatabase[building.GetFieldAsString(buildingIDFieldIndex)] = (rows, cols)

        with open(inputSetting['buildingLocationFile'], 'w') as f:
            ujson.dump(buildingLocationDatabase, f)
        
        buildingLayer = None
        buildingShapefile = None

        buildingShapefile = gpd.read_file(inputSetting['buildingFile'])
        buildingShapefile.drop(columns=['geometry'], inplace=True)
        buildingShapefile.to_csv(inputSetting['buildingCSVFile'])


@jit(nopython=True, fastmath=True)
def calculateLocalGridParameters(envelope, upperLeftXGlobalGrid, upperLeftYGlobalGrid, cellSize):
    minX = envelope[0]
    maxX = envelope[1]
    minY = envelope[2]
    maxY = envelope[3]
    rowOffset = int((upperLeftYGlobalGrid - maxY) / cellSize)  # row number in the global grid = local row number + rowOffset
    colOffset = int((minX - upperLeftXGlobalGrid) / cellSize)  # col number in the global grid = local col number + colOffset
    upperLeftXLocalGrid = upperLeftXGlobalGrid + colOffset * cellSize  # upper left corner of the local grid
    upperLeftYLocalGrid = upperLeftYGlobalGrid - rowOffset * cellSize  # upper left corner of the local grid
    nrow = (upperLeftYLocalGrid - minY) // cellSize + 1  # number of rows in the local grid
    ncol = (maxX - upperLeftXLocalGrid) // cellSize + 1  # number of cols in the local grid
    return upperLeftXLocalGrid, upperLeftYLocalGrid, nrow, ncol, rowOffset, colOffset
