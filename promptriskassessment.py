"""
Prompt Risk Assessment of Rain-Induced Shallow Landslides
Date: Dec. 9, 2021
Written by Jian HE
"""

import argparse
import geopandas as gpd
from readinputfiles import definition
from generatedatabase import *
from hazardanalysis import hazardAnalysis
from consequenceanalysis import consequenceAnalysis
from individualriskanalysis import individualRiskAnalysis
from totalriskanalysis import totalRiskCalculation
from reportgeneration import reportGeneration


def promptAssessment(inputFilePath):

    # --------------------------------Step 1: Read input files-----------------------------------
    inputSetting, outputFilePath = definition(inputFilePath)
    if not inputSetting:
        return

    # If the assessment is executed for the first time, it will take some time to generate potential landslide trail and building location files.
    generatePotentialTrailDatabase(inputSetting)
    generateBuildingLocationDatabase(inputSetting)

    # --------------------------------Step 2: Hazard assessment----------------------------------
    hazardAnalysis(inputSetting, outputFilePath)

    # --------------------------------Step 3: Consequence assessment-----------------------------
    consequenceAnalysis(inputSetting, outputFilePath)

    # --------------------------------Step 4: Individual risk assessment-------------------------
    individualRiskAnalysis(inputSetting, outputFilePath)

    # --------------------------------Step 5: Total risk assessment------------------------------
    totalRiskCalculation(inputSetting, outputFilePath)

    # --------------------------------Step 6: Generate figures and reports-----------------------
    reportGeneration(inputSetting, outputFilePath)


# Run the risk assessment
if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='PoLA', description='Prompt Landslide Risk Assessment.')
    parser.add_argument('--input', '-i', default='Input/Risk assessment input.txt', metavar='FILE',
                        help='Specify the input file')
    inputFilePath = parser.parse_args().input
    promptAssessment(inputFilePath)
