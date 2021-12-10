import ujson
import rasterio
import pandas as pd
import numpy as np
from numba import jit
import time
from progressbar import progressBar


def consequenceAnalysis(inputSetting, outputFilePath):
    starttime = time.time()
    landslideConsequenceAnalysis(inputSetting, outputFilePath)
    endtime = time.time()
    print(f'Total time: {endtime-starttime} s')


def landslideConsequenceAnalysis(inputSetting, outputFilePath):
    print('Assessing the consequence...')

    # Read the landslide potential trail list file
    landslidePotentialTrailList = pd.read_csv(inputSetting['landslidePotentialTrailListFile'], sep=',', skiprows=1)
    landslidePotentialTrailList = landslidePotentialTrailList.sort_values(by=['StartRow'])

    humanVulnerabilityModel = pd.read_csv(inputSetting['humanVulnerabilityModel'], sep=',', skiprows=1)
    humanVulnerabilityModel = humanVulnerabilityModel.sort_values(by=['TravelAngle_lb'])
    humanVulnerabilityArray = humanVulnerabilityModel.to_numpy()

    # Read the raster of the landslide probability
    with rasterio.open(outputFilePath['LandslideProbability']) as src:
        nodataValue = src.nodatavals[0]
        rasterMeta = src.meta
        ncol = src.meta['width']
        nrow = src.meta['height']
        landslideProbability = src.read(1)
        rasterMask = np.where(landslideProbability == nodataValue, True, False)  # filter = True when the cell is nodata
        landslideProbability[rasterMask] = 0

    # Read the raster of the landslide volume probability
    with rasterio.open(outputFilePath['LandslideVolumeProbability']) as src:
        landslideVolumeProbability = src.read()
        nodataValue = src.nodatavals[0]
        volumeRasterMask = np.where(landslideVolumeProbability == nodataValue, True, False)  # filter = True when the cell is nodata
        landslideVolumeProbability[volumeRasterMask] = 0

    fatalityRate = np.ones_like(landslideProbability)
    affectedProbability = np.ones_like(landslideProbability)

    currentFileIndex = landslidePotentialTrailList[(landslidePotentialTrailList['StartRow'] <= 0) & (landslidePotentialTrailList['EndRow'] >= 0)].index[0]

    databaseLoaded = False
    for row in progressBar(list(range(nrow)), prefix='Progress:', suffix='Complete', decimals=2, length=50):
        while not ((row >= landslidePotentialTrailList.loc[currentFileIndex, 'StartRow']) & (row <= landslidePotentialTrailList.loc[currentFileIndex, 'EndRow'])):
            currentFileIndex += 1
            databaseLoaded = False

        if not databaseLoaded:
            with open(landslidePotentialTrailList.loc[currentFileIndex, 'FileName'], 'r') as f:
                landslidePotentialTrail = ujson.load(f)
            databaseLoaded = True

        for col in range(ncol):
            landslideProbabilityCell = landslideProbability[row, col]
            landslideVolumeProbabilityCell = landslideVolumeProbability[:, row, col]
            if landslideProbabilityCell > 0.000001:  # For computational efficiency, landslides with occurrence probabilities smaller than 10e-6 will be ignored
                try:
                    cellTrail = landslidePotentialTrail[f'{row}'][f'{col}']
                except KeyError:
                    continue
                trailRow = np.array(cellTrail[0])
                trailCol = np.array(cellTrail[1])
                trailTravelAngle = np.array(cellTrail[2])
                trailProbability = np.array(cellTrail[3])
                affectedProbabilityCell, fatalityRateCell = assessAffectedProbabilityAndFatalityRate(trailTravelAngle,
                                                                                                     trailProbability,
                                                                                                     humanVulnerabilityArray,
                                                                                                     landslideProbabilityCell,
                                                                                                     landslideVolumeProbabilityCell,
                                                                                                     affectedProbability[(trailRow,trailCol)],
                                                                                                     fatalityRate[(trailRow, trailCol)])
                affectedProbability[(trailRow, trailCol)] = affectedProbabilityCell
                fatalityRate[(trailRow, trailCol)] = fatalityRateCell

    affectedProbability = 1-affectedProbability
    fatalityRate = 1-fatalityRate

    affectedProbability = np.where(rasterMask, nodataValue, affectedProbability)
    fatalityRate = np.where(rasterMask, nodataValue, fatalityRate)

    with rasterio.open(outputFilePath['AffectedProbability'], 'w', **rasterMeta, compress="LZW") as src:
        src.write(affectedProbability, 1)

    with rasterio.open(outputFilePath['FatalityRate'], 'w', **rasterMeta, compress="LZW") as src:
        src.write(fatalityRate, 1)

@jit(nopython=True, fastmath=True)
def assessAffectedProbabilityAndFatalityRate(trailTravelAngle, trailProbability, humanVulnerabilityArray, landslideProbabilityCell, landslideVolumeProbabilityCell, affectedProbabilityCell, fatalityRateCell):
    humanVulnerability = np.empty((len(trailTravelAngle), len(landslideVolumeProbabilityCell)))

    for ncell in range(len(trailTravelAngle)):
        humanVulnerability[ncell, :] = humanVulnerabilityArray[(humanVulnerabilityArray[:, 0] <= trailTravelAngle[ncell]) & (humanVulnerabilityArray[:, 1] > trailTravelAngle[ncell]), 2:]
    affectedProbabilityCell *= (1 - np.sum(landslideProbabilityCell * trailProbability.T * landslideVolumeProbabilityCell, axis=1))
    fatalityRateCell *= (1 - np.sum(landslideProbabilityCell * trailProbability.T * humanVulnerability * landslideVolumeProbabilityCell, axis=1))
    return affectedProbabilityCell, fatalityRateCell
