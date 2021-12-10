import os


def definition(inputFilePath):

    inputSetting = readInputFiles(inputFilePath)
    if not inputSetting:  # if inputSetting is empty, which means the input file does not exist, exit the program
        print('The input file was not found.')
        return None, None
    else:
        print('The input file has been loaded successfully.')
        outputFilePath = defineOutputFile(inputSetting)
        return inputSetting, outputFilePath


def readInputFiles(inputFilePath):
    """Read the input file and store the input settings in a dict"""
    inputSetting = dict()  # a dict recording all input settings
    if os.path.exists(inputFilePath):
        print('Reading the input file...')
        with open(inputFilePath, 'r') as f:
            line = f.readline()
            while line:  # if the line is not empty
                if 'rainfall24h' in line:
                    line = f.readline()
                    inputSetting['rainfall24h'] = line.strip()
                elif 'DEMFile' in line:
                    line = f.readline()
                    inputSetting['DEMFile'] = line.strip()
                elif 'slopeFile' in line:
                    line = f.readline()
                    inputSetting['slopeFile'] = line.strip()
                elif 'slopeForTrailFile' in line:
                    line = f.readline()
                    inputSetting['slopeForTrailFile'] = line.strip()
                elif 'flowDirectionFile' in line:
                    line = f.readline()
                    inputSetting['flowDirectionFile'] = line.strip()
                elif 'meanAnnualRainfallFile' in line:
                    line = f.readline()
                    inputSetting['meanAnnualRainfallFile'] = line.strip()
                elif 'geologyFile' in line:
                    line = f.readline()
                    inputSetting['geologyFile'] = line.strip()
                elif 'naturalTerrainFile' in line:
                    line = f.readline()
                    inputSetting['naturalTerrainFile'] = line.strip()
                elif 'naturalTerrainForTrailFile' in line:
                    line = f.readline()
                    inputSetting['naturalTerrainForTrailFile'] = line.strip()
                elif 'territoryBoundaryFile' in line:
                    line = f.readline()
                    inputSetting['territoryBoundaryFile'] = line.strip()
                elif 'zoningFile' in line:
                    line = f.readline()
                    inputSetting['zoningFile'] = line.strip()
                elif 'buildingFile' in line:
                    line = f.readline()
                    inputSetting['buildingFile'] = line.strip()
                elif 'buildingCSVFile' in line:
                    line = f.readline()
                    inputSetting['buildingCSVFile'] = line.strip()
                elif 'buildingLocationFile' in line:
                    line = f.readline()
                    inputSetting['buildingLocationFile'] = line.strip()

                elif 'landslidePredictionModel' in line:
                    line = f.readline()
                    inputSetting['landslidePredictionModel'] = line.strip()
                elif 'landslideVolumeModel' in line:
                    line = f.readline()
                    inputSetting['landslideVolumeModel'] = line.strip()
                elif 'landslideRunoutModel' in line:
                    line = f.readline()
                    inputSetting['landslideRunoutModel'] = line.strip()
                elif 'landslidePotentialTrailListFile' in line:
                    line = f.readline()
                    inputSetting['landslidePotentialTrailListFile'] = line.strip()

                elif 'humanVulnerabilityModel' in line:
                    line = f.readline()
                    inputSetting['humanVulnerabilityModel'] = line.strip()

                elif 'numberOfMonteCarloSamples' in line:
                    line = f.readline()
                    inputSetting['numberOfMonteCarloSamples'] = int(line.strip())
                elif 'buildingProtectionFactor' in line:
                    line = f.readline()
                    factor = line.strip()
                    inputSetting['buildingProtectionFactor'] = [float(x) for x in factor.split(',')]

                elif 'buildingBin' in line:
                    line = f.readline()
                    interval = line.strip()
                    inputSetting['buildingBin'] = [float(x) for x in interval.split(',')]
                elif 'fatalityBin' in line:
                    line = f.readline()
                    interval = line.strip()
                    inputSetting['fatalityBin'] = [float(x) for x in interval.split(',')]
                elif 'buildingThemeColor' in line:
                    line = f.readline()
                    themeColor = line.strip()
                    inputSetting['buildingThemeColor'] = [f'{x.strip()}' for x in themeColor.split(',')]
                elif 'buildingWarningNames' in line:
                    line = f.readline()
                    warningNames = line.strip()
                    inputSetting['buildingWarningNames'] = [f'{x.strip()}' for x in warningNames.split(',')]
                elif 'fatalityThemeColor' in line:
                    line = f.readline()
                    themeColor = line.strip()
                    inputSetting['fatalityThemeColor'] = [f'{x.strip()}' for x in themeColor.split(',')]
                elif 'fatalityWarningNames' in line:
                    line = f.readline()
                    warningNames = line.strip()
                    inputSetting['fatalityWarningNames'] = [f'{x.strip()}' for x in warningNames.split(',')]
                elif 'addBasemap' in line:
                    line = f.readline()
                    temp = line.strip()
                    inputSetting['addBasemap'] = True if temp in ['Y', 'y', 'YES', 'Yes', 'yes', 'T', 't', 'TRUE', 'True', 'true', '1'] else False
                elif 'basemapStyle' in line:
                    line = f.readline()
                    inputSetting['basemapStyle'] = line.strip()
                elif 'reportNumber' in line:
                    line = f.readline()
                    inputSetting['reportNumber'] = line.strip()
                elif 'reportType' in line:
                    line = f.readline()
                    inputSetting['reportType'] = line.strip()
                elif 'rainstormDate' in line:
                    line = f.readline()
                    inputSetting['rainstormDate'] = line.strip()
                elif 'resultPath' in line:
                    line = f.readline()
                    inputSetting['resultPath'] = line.strip()
                elif 'saveLargeFile' in line:
                    line = f.readline()
                    temp = line.strip()
                    inputSetting['saveLargeFile'] = True if temp in ['Y', 'y', 'YES', 'Yes', 'yes', 'T', 't', 'TRUE', 'True', 'true', '1'] else False
                line = f.readline()  # read the next line

    else:
        # if the file does not exist, raise an error
        print(f'The input file was not found at "{inputFilePath}"')
    return inputSetting


def defineOutputFile(inputSetting):
    outputPath = inputSetting['resultPath']
    if not os.path.exists(outputPath):
        os.makedirs(outputPath)
    outputFilePath = dict()
    outputFilePath['Rainfall'] = f'{outputPath}/Rainfall.tif'
    outputFilePath['NormalizedRainfallFine'] = f'{outputPath}/NormalizedRainfallFine.tif'
    outputFilePath['NormalizedRainfall'] = f'{outputPath}/NormalizedRainfall.tif'
    outputFilePath['LandslideFrequencyFine'] = f'{outputPath}/LandslideFrequencyFine.tif'
    outputFilePath['LandslideFrequency'] = f'{outputPath}/LandslideFrequency.tif'
    outputFilePath['LandslideNumber'] = f'{outputPath}/LandslideNumber.tif'
    outputFilePath['LandslideProbability'] = f'{outputPath}/LandslideProbability.tif'
    outputFilePath['LandslideVolumeProbability'] = f'{outputPath}/LandslideVolumeProbability.tif'
    outputFilePath['LandslideZoning'] = f'{outputPath}/LandslideZoning.shp'
    outputFilePath['AffectedProbability'] = f'{outputPath}/AffectedProbability.tif'
    outputFilePath['FatalityRate'] = f'{outputPath}/FatalityRate.tif'
    outputFilePath['Building'] = f'{outputPath}/Building.shp'
    outputFilePath['BuildingCSV'] = f'{outputPath}/Building.csv'
    outputFilePath['Road'] = f'{outputPath}/Road.shp'
    outputFilePath['Summary'] = f'{outputPath}/Summary.shp'
    outputFilePath['AffectedBuildingSummary'] = f'{outputPath}/AffectedBuildingSummary.csv'
    outputFilePath['FatalitySummary'] = f'{outputPath}/FatalitySummary.csv'
    outputFilePath['AffectedBuildingSample'] = f'{outputPath}/AffectedBuildingSample.txt'
    outputFilePath['FatalitySample'] = f'{outputPath}/FatalitySample.txt'
    outputFilePath['Report'] = f'{outputPath}/Report.pdf'
    outputFilePath['ReportPNG'] = f'{outputPath}/Report.png'
    return outputFilePath
