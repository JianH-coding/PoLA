import os
from osgeo import ogr
import numpy as np
import pandas as pd
import time
from progressbar import progressBar


def totalRiskCalculation(inputSetting, outputFilePath):
    """Assess probability distribution of fatality and affected buildings using Monte Carlo simulation"""
    starttime = time.time()
    calculateDistributionOfAffectedBuildingsAndFatality(inputSetting, outputFilePath)
    endtime = time.time()
    print(f'Total time: {endtime-starttime} s')


def calculateDistributionOfAffectedBuildingsAndFatality(inputSetting, outputFilePath):
    print('Analysing total risk using Monte Carlo simulation...')
    numberOfMonteCarloSamples = inputSetting['numberOfMonteCarloSamples']
    buildingProtectionFactor = inputSetting['buildingProtectionFactor']
    buildingInterval = np.array(inputSetting['buildingBin'])
    fatalityInterval = np.array(inputSetting['fatalityBin'])

    os.environ['SHAPE_ENCODING'] = "utf-8"
    shapefileDriver = ogr.GetDriverByName('ESRI Shapefile')

    zoningIDField = 'Region_ID'
    zoningNameField = 'Region'
    zoningShapefile = shapefileDriver.Open(inputSetting['zoningFile'])

    zoningLayer = zoningShapefile.GetLayer(0)
    zoningCount = zoningLayer.GetFeatureCount() + 1  # the zero zone is the entire territory
    zoningLayerDefinition = zoningLayer.GetLayerDefn()
    zoningID = np.zeros(zoningCount, np.int64)
    zoningNameList = ['Entire HK']
    zoningIDFieldIndex = zoningLayerDefinition.GetFieldIndex(zoningIDField)
    zoningNameFieldIndex = zoningLayerDefinition.GetFieldIndex(zoningNameField)

    for nzone in range(zoningCount-1):
        zone = zoningLayer.GetFeature(nzone)
        zoningID[nzone+1] = zone.GetFieldAsInteger(zoningIDFieldIndex)
        zoningNameList.append(zone.GetFieldAsString(zoningNameFieldIndex))

    building = pd.read_csv(outputFilePath['BuildingCSV'])
    affectedBuilding = building[building['AffProb']>0]
    buildingCount = affectedBuilding.shape[0]
    buildingAffectedProbability = affectedBuilding['AffProb'].to_numpy()
    buildingFatalityRate = affectedBuilding['FataRate'].to_numpy()
    buildingZoningID = affectedBuilding['Region_ID'].to_numpy().astype('int')
    buildingPopulation = affectedBuilding['Population'].to_numpy()
    buildingFactor = np.where(affectedBuilding['Height'].to_numpy()<=10, buildingProtectionFactor[0], buildingProtectionFactor[1])

    # Monte Carlo Simulation
    zoningAffectedBuildings, zoningFatality = monteCarloSimulation(numberOfMonteCarloSamples, zoningCount, buildingCount, buildingAffectedProbability, buildingFatalityRate, buildingFactor, buildingPopulation, zoningID, buildingZoningID)

    # Save the Monte Carlo samples for the entire Hong Kong
    with open(outputFilePath['AffectedBuildingSample'], 'w') as f:
        np.savetxt(f, zoningAffectedBuildings[0, :])
    with open(outputFilePath['FatalitySample'], 'w') as f:
        np.savetxt(f, zoningFatality[0, :])

    # Calculate statistics
    expectationAffectedBuildings = np.zeros(zoningCount)
    expectationFatality = np.zeros(zoningCount)
    standardDeviationAffectedBuildings = np.zeros(zoningCount)
    standardDeviationFatality = np.zeros(zoningCount)
    medianAffectedBuildings = np.zeros(zoningCount)
    medianFatality = np.zeros(zoningCount)
    lowerPercentileAffectedBuildings = np.zeros(zoningCount)
    lowerPercentileFatality = np.zeros(zoningCount)
    upperPercentileAffectedBuildings = np.zeros(zoningCount)
    upperPercentileFatality = np.zeros(zoningCount)
    histogramAffectedBuildings = np.zeros((zoningCount, len(buildingInterval)-1))
    histogramFatality = np.zeros((zoningCount, len(fatalityInterval) - 1))

    for nzone in zoningID:
        expectationAffectedBuildings[nzone] = np.mean(zoningAffectedBuildings[nzone, :])
        expectationFatality[nzone] = np.mean(zoningFatality[nzone, :])
        standardDeviationAffectedBuildings[nzone] = np.std(zoningAffectedBuildings[nzone, :])
        standardDeviationFatality[nzone] = np.std(zoningFatality[nzone, :])
        medianAffectedBuildings[nzone] = np.median(zoningAffectedBuildings[nzone, :])
        medianFatality[nzone] = np.median(zoningFatality[nzone, :])
        lowerPercentileAffectedBuildings[nzone] = np.percentile(zoningAffectedBuildings[nzone, :], 2.5)
        lowerPercentileFatality[nzone] = np.percentile(zoningFatality[nzone, :], 2.5)
        upperPercentileAffectedBuildings[nzone] = np.percentile(zoningAffectedBuildings[nzone, :], 97.5)
        upperPercentileFatality[nzone] = np.percentile(zoningFatality[nzone, :], 97.5)
        histogramAffectedBuildings[nzone, :] = np.histogram(zoningAffectedBuildings[nzone, :], bins=buildingInterval)[0]
        histogramFatality[nzone, :] = np.histogram(zoningFatality[nzone, :], bins=fatalityInterval)[0]
    histogramAffectedBuildings = histogramAffectedBuildings/numberOfMonteCarloSamples
    histogramFatality = histogramFatality/numberOfMonteCarloSamples

    zoningName = {zoningNameField: zoningNameList}
    summaryAffectedBuildings = pd.DataFrame(zoningName)
    summaryFatality = pd.DataFrame(zoningName)
    summaryAffectedBuildings['Zoning ID'] = zoningID
    summaryFatality['Zoning ID'] = zoningID
    summaryAffectedBuildings['Expectation'] = expectationAffectedBuildings
    summaryFatality['Expectation'] = expectationFatality
    summaryAffectedBuildings['Standard Deviation'] = standardDeviationAffectedBuildings
    summaryFatality['Standard Deviation'] = standardDeviationFatality
    summaryAffectedBuildings['Median'] = medianAffectedBuildings
    summaryFatality['Median'] = medianFatality
    summaryAffectedBuildings['2.5th Percentile'] = lowerPercentileAffectedBuildings
    summaryFatality['2.5th Percentile'] = lowerPercentileFatality
    summaryAffectedBuildings['97.5th Percentile'] = upperPercentileAffectedBuildings
    summaryFatality['97.5th Percentile'] = upperPercentileFatality
    summaryAffectedBuildings.set_index('Zoning ID')
    summaryFatality.set_index('Zoning ID')

    for ninterval in range(len(buildingInterval)-1):
        summaryAffectedBuildings[f'[{buildingInterval[ninterval]},{buildingInterval[ninterval+1]})'] = histogramAffectedBuildings[:, ninterval]
    for ninterval in range(len(fatalityInterval) - 1):
        summaryFatality[f'[{fatalityInterval[ninterval]},{fatalityInterval[ninterval + 1]})'] = histogramFatality[:, ninterval]

    summaryAffectedBuildings.to_csv(outputFilePath['AffectedBuildingSummary'])
    summaryFatality.to_csv(outputFilePath['FatalitySummary'])

    summaryShapefile = shapefileDriver.CreateDataSource(outputFilePath['Summary'])
    summaryShapefile.CopyLayer(zoningLayer, 'Summary')
    summaryLayer = summaryShapefile.GetLayer(0)
    expectationField = ogr.FieldDefn('ABExp', ogr.OFTReal)
    summaryLayer.CreateField(expectationField)
    standardDeviationField = ogr.FieldDefn('ABStd', ogr.OFTReal)
    summaryLayer.CreateField(standardDeviationField)
    medianField = ogr.FieldDefn('ABMed', ogr.OFTReal)
    summaryLayer.CreateField(medianField)
    fifthPercentileField = ogr.FieldDefn('AB2_5thP', ogr.OFTReal)
    summaryLayer.CreateField(fifthPercentileField)
    ninetyfifthPercentileField = ogr.FieldDefn('AB97_5thP', ogr.OFTReal)
    summaryLayer.CreateField(ninetyfifthPercentileField)
    for ninterval in range(len(buildingInterval)-1):
        histogramField = ogr.FieldDefn(f'AB{buildingInterval[ninterval]}', ogr.OFTReal)
        summaryLayer.CreateField(histogramField)

    expectationField = ogr.FieldDefn('FExp', ogr.OFTReal)
    summaryLayer.CreateField(expectationField)
    standardDeviationField = ogr.FieldDefn('FStd', ogr.OFTReal)
    summaryLayer.CreateField(standardDeviationField)
    medianField = ogr.FieldDefn('FMed', ogr.OFTReal)
    summaryLayer.CreateField(medianField)
    fifthPercentileField = ogr.FieldDefn('F2_5thP', ogr.OFTReal)
    summaryLayer.CreateField(fifthPercentileField)
    ninetyfifthPercentileField = ogr.FieldDefn('F97_5thP', ogr.OFTReal)
    summaryLayer.CreateField(ninetyfifthPercentileField)
    for ninterval in range(len(fatalityInterval) - 1):
        histogramField = ogr.FieldDefn(f'F{fatalityInterval[ninterval]}', ogr.OFTReal)
        summaryLayer.CreateField(histogramField)

    for zone in summaryLayer:
        nzoneID = zone.GetFieldAsInteger(zoningIDFieldIndex)
        zone.SetField('ABExp', summaryAffectedBuildings.at[nzoneID, 'Expectation'])
        zone.SetField('ABStd', summaryAffectedBuildings.at[nzoneID, 'Standard Deviation'])
        zone.SetField('ABMed', summaryAffectedBuildings.at[nzoneID, 'Median'])
        zone.SetField('AB2_5thP', summaryAffectedBuildings.at[nzoneID, '2.5th Percentile'])
        zone.SetField('AB97_5thP', summaryAffectedBuildings.at[nzoneID, '97.5th Percentile'])
        for ninterval in range(len(buildingInterval) - 1):
            zone.SetField(f'AB{buildingInterval[ninterval]}', summaryAffectedBuildings.at[nzoneID, f'[{buildingInterval[ninterval]},{buildingInterval[ninterval+1]})'])

        zone.SetField('FExp', summaryFatality.at[nzoneID, 'Expectation'])
        zone.SetField('FStd', summaryFatality.at[nzoneID, 'Standard Deviation'])
        zone.SetField('FMed', summaryFatality.at[nzoneID, 'Median'])
        zone.SetField('F2_5thP', summaryFatality.at[nzoneID, '2.5th Percentile'])
        zone.SetField('F97_5thP', summaryFatality.at[nzoneID, '97.5th Percentile'])
        for ninterval in range(len(fatalityInterval) - 1):
            zone.SetField(f'F{fatalityInterval[ninterval]}', summaryFatality.at[nzoneID, f'[{fatalityInterval[ninterval]},{fatalityInterval[ninterval + 1]})'])

        summaryLayer.SetFeature(zone)

    summaryLayer = None
    summaryShapefile = None


def monteCarloSimulation(numberOfMonteCarloSamples, zoningCount, buildingCount, buildingAffectedProbability, buildingFatalityRate, buildingFactor, buildingPopulation, zoningID, buildingZoningID):

    zoningAffectedBuildings = np.zeros((zoningCount, numberOfMonteCarloSamples))
    zoningFatality = np.zeros((zoningCount, numberOfMonteCarloSamples))
    for nsample in progressBar(list(range(numberOfMonteCarloSamples)), prefix='Progress:', suffix='Complete', decimals=2, length=50):
        randomNumbers = np.random.rand(buildingCount)
        affected = np.where(randomNumbers <= buildingAffectedProbability, 1, 0)
        death = np.where(randomNumbers <= buildingFatalityRate, buildingFactor*buildingPopulation, 0)
        zoningAffectedBuildings[:, nsample], zoningFatality[:, nsample] = sumRandomVariables(zoningCount, zoningID, buildingZoningID, affected, death)

    return zoningAffectedBuildings, zoningFatality


def sumRandomVariables(zoningCount, zoningID, buildingZoningID, affected, death):
    zoningAffectedBuildings = np.zeros(zoningCount)
    zoningFatality = np.zeros(zoningCount)
    affectedBuildingsSumByGroup = pd.Series(affected).groupby(buildingZoningID).sum()
    deathSumByGroup = pd.Series(death).groupby(buildingZoningID).sum()
    zoningAffectedBuildings[np.searchsorted(zoningID, affectedBuildingsSumByGroup.index)] = affectedBuildingsSumByGroup
    zoningFatality[np.searchsorted(zoningID, deathSumByGroup.index)] = deathSumByGroup
    zoningAffectedBuildings[zoningID == 0] = np.sum(zoningAffectedBuildings[zoningID != 0])
    zoningFatality[zoningID == 0] = np.sum(zoningFatality[zoningID != 0])
    return zoningAffectedBuildings, zoningFatality
