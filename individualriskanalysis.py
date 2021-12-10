from osgeo import ogr
import ujson
import rasterio
import numpy as np
import pandas as pd
import time
import os
from progressbar import progressBar


def individualRiskAnalysis(inputSetting, outputFilePath):
    starttime = time.time()
    identifyAffectedBuildingAndFatality(inputSetting, outputFilePath)
    endtime = time.time()
    print(f'Total time: {endtime-starttime} s')


def identifyAffectedBuildingAndFatality(inputSetting, outputFilePath):
    print('Analysing individual risk...')

    with rasterio.open(outputFilePath['AffectedProbability']) as src:
        nodataValue = src.nodatavals[0]
        affectedProbability = src.read(1)
        affectedProbability = np.where(affectedProbability == nodataValue, 0, affectedProbability)

    with rasterio.open(outputFilePath['FatalityRate']) as src:
        nodataValue = src.nodatavals[0]
        fatalityRate = src.read(1)
        fatalityRate = np.where(fatalityRate == nodataValue, 0, fatalityRate)

    with open(inputSetting['buildingLocationFile'], 'r') as f:
        buildingLocation = ujson.load(f)

    building = pd.read_csv(inputSetting['buildingCSVFile'])
    affProb = np.zeros(building.shape[0])
    fataRate = np.zeros(building.shape[0])

    for nbuilding in progressBar(building.index, prefix='Progress:', suffix='Complete', decimals=2, length=50):
        buildingID = str(building.loc[nbuilding, 'BuildingID'])
        buildingRows = np.array(buildingLocation[buildingID][0])
        buildingCols = np.array(buildingLocation[buildingID][1])
        buildingAffectedProbability = 1 - np.prod(1 - (affectedProbability[(buildingRows, buildingCols)]))
        affProb[nbuilding] = max(buildingAffectedProbability, 0)
        buildingFatalityRate = 1 - np.prod(1 - (fatalityRate[(buildingRows, buildingCols)]))
        fataRate[nbuilding] = max(buildingFatalityRate, 0)

    building['AffProb'] = affProb
    building['FataRate'] = fataRate

    building.to_csv(outputFilePath['BuildingCSV'])
