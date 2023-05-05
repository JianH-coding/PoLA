import geopandas as gpd
import rasterio.shutil
import rasterio.plot
from osgeo import gdal
from osgeo import ogr
from datetime import datetime
from textwrap import fill, shorten
import matplotlib.colorbar as colorbar
import matplotlib.pyplot as plt

from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Rectangle
import matplotlib.gridspec as gridspec
import contextily as ctx
import numpy as np
import pandas as pd


def reportGeneration(inputSetting, outputFilePath):
    '''Generate a one-page report'''
    print('Generating the report...')
    mm = 0.0393701  # convert mm to inch
    leftrightmargin = 5 * mm
    topbottommargin = 5 * mm
    width = 170 * mm
    height_rows = np.array([12, 7, 7, 23, 7, 12, 7, 57, 7, 57, 4]) * mm
    height = height_rows.sum() + 2 * topbottommargin
    horizontalMargin = leftrightmargin / width
    verticalMargin = topbottommargin / height

    fig = plt.figure(figsize=(width, height), dpi=600, constrained_layout=False)

    # Set height ratio
    height_ratios = height_rows / (height - 2 * topbottommargin)

    # The report is separated into gridspecs of 11 rows
    gs = gridspec.GridSpec(11, 1, figure=fig, height_ratios=height_ratios, wspace=0.0, hspace=0.0,
                           left=horizontalMargin, right=1 - horizontalMargin, top=1 - verticalMargin,
                           bottom=verticalMargin)

    # The 1st row contains the logo, the report title and the risk level
    gs0 = gridspec.GridSpecFromSubplotSpec(1, 2, subplot_spec=gs[0], width_ratios=[0.75, 0.25], hspace=0, wspace=0)
    ax00 = fig.add_subplot(gs0[0, 0])
    plotReportTitle(ax00)
    ax01 = fig.add_subplot(gs0[0, 1])  # this plot is the risk level

    # The 2nd row contains the report time and the report number
    gs1 = gridspec.GridSpecFromSubplotSpec(1, 2, subplot_spec=gs[1], width_ratios=[0.7, 0.3])
    ax10 = fig.add_subplot(gs1[0, 0])
    plotReportTime(inputSetting, ax10)
    ax11 = fig.add_subplot(gs1[0, 1])
    plotReportNumber(inputSetting, ax11)

    # The 3rd row contains the summary title, the rainstorm coverage title and the landslide distribution title
    gs2 = gridspec.GridSpecFromSubplotSpec(1, 4, subplot_spec=gs[2], width_ratios=[0.5, 0.29, 0.29, 0.0001])
    ax20 = fig.add_subplot(gs2[0, 0])
    plotSubTitle(ax20, 'Summary')
    ax21 = fig.add_subplot(gs2[0, 1])
    plotSubTitle(ax21, '24-h Rainfall      ', ha='center')
    ax21.text(0.8, 0.15, '(mm)', ha='center', va='bottom', fontsize=8)
    ax22 = fig.add_subplot(gs2[0, 2])
    plotSubTitle(ax22, 'Landslide        ', ha='center')
    ax22.text(0.8, 0.13, r'(no./km$^2$)', ha='center', va='bottom', fontsize=8)


    # The 4th row contains the summary, the rainstorm coverage and the landslide distribution
    gs3 = gridspec.GridSpecFromSubplotSpec(1, 4, subplot_spec=gs[3], width_ratios=[0.5, 0.29, 0.29, 0.0001])
    ax30 = fig.add_subplot(gs3[0, 0])  # this plot is the summary

    ax31 = fig.add_subplot(gs3[0, 1])
    maximumRainfall = plotRainfallDistribution(inputSetting, outputFilePath, ax31)
    ax32 = fig.add_subplot(gs3[0, 2])
    plotLandslideDistribution(inputSetting, outputFilePath, ax32)

    # The 5th row contains the landslide title
    gs4 = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=gs[4])
    ax40 = fig.add_subplot(gs4[0, 0])
    plotSubTitle(ax40, 'Estimated Landslides')

    # The 6th row contains the landslide table
    gs5 = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=gs[5])
    ax50 = fig.add_subplot(gs5[0, 0])
    totalLandslide = plotHazardSummaryTable(outputFilePath, ax50)

    # The 7th row contains the affected building title
    gs6 = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=gs[6])
    ax60 = fig.add_subplot(gs6[0, 0])
    plotSubTitle(ax60, 'Estimated Affected Buildings')

    # The 8th row contains the affected building map, the affected building probability bar chart and the table
    gs7 = gridspec.GridSpecFromSubplotSpec(2, 2, subplot_spec=gs[7], width_ratios=[0.65, 0.35], height_ratios=[0.3, 0.7],
                                           hspace=0.4, wspace=0.25)
    ax70 = fig.add_subplot(gs7[:, 0])
    plotAffectedBuildingsMap(inputSetting, outputFilePath, ax70)
    ax71 = fig.add_subplot(gs7[0, 1])
    plotAffectedBuildingsProbability(inputSetting, outputFilePath, ax71)
    ax72 = fig.add_subplot(gs7[1, 1])
    totalAffectedBuildings, propertyRiskLevel = plotAffectedBuildingsSummaryTable(inputSetting, outputFilePath, ax72)

    # The 9th row contains the affected building title
    gs8 = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=gs[8])
    ax80 = fig.add_subplot(gs8[0, 0])
    plotSubTitle(ax80, 'Estimated Fatalities')

    # The 10th row contains the fatality map, the fatality probability bar chart and the table
    gs9 = gridspec.GridSpecFromSubplotSpec(2, 2, subplot_spec=gs[9], width_ratios=[0.65, 0.35], height_ratios=[0.3, 0.7],
                                           hspace=0.4, wspace=0.25)
    ax90 = fig.add_subplot(gs9[:, 0])
    plotFatalityMap(inputSetting, outputFilePath, ax90)
    ax91 = fig.add_subplot(gs9[0, 1])
    plotFatalitiesProbability(inputSetting, outputFilePath, ax91)
    ax92 = fig.add_subplot(gs9[1, 1])
    totalFatalities, humanRiskLevel = plotFatalitiesSummaryTable(inputSetting, outputFilePath, ax92)

    # The 11th row contains the footnote
    gs10 = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=gs[10])
    ax100 = fig.add_subplot(gs10[0, 0])
    plotFootnote(ax100)

    # Add summary text and risk level
    plotRiskLevel(inputSetting, propertyRiskLevel, humanRiskLevel, ax01)
    plotSummary(inputSetting, maximumRainfall, totalLandslide, totalAffectedBuildings, totalFatalities,
                propertyRiskLevel, humanRiskLevel, ax30)

    plt.rcParams['font.sans-serif'] = "Arial"
    plt.rcParams['font.family'] = "sans-serif"

    fig.savefig(outputFilePath['ReportPNG'], pad_inches=0)
    # fig.savefig(outputFilePath['ReportSVG'], pad_inches=0)
    fig.savefig(outputFilePath['ReportPDF'], pad_inches=0)
    print('Finished.')

    if not inputSetting['saveLargeFile']:
        gdal.GetDriverByName('GTiff').Delete(outputFilePath['Rainfall'])
        gdal.GetDriverByName('GTiff').Delete(outputFilePath['NormalizedRainfallFine'])
        gdal.GetDriverByName('GTiff').Delete(outputFilePath['NormalizedRainfall'])
        gdal.GetDriverByName('GTiff').Delete(outputFilePath['LandslideFrequencyFine'])
        gdal.GetDriverByName('GTiff').Delete(outputFilePath['LandslideFrequency'])
        gdal.GetDriverByName('GTiff').Delete(outputFilePath['LandslideProbability'])
        gdal.GetDriverByName('GTiff').Delete(outputFilePath['LandslideVolumeProbability'])
        gdal.GetDriverByName('GTiff').Delete(outputFilePath['AffectedProbability'])
        gdal.GetDriverByName('GTiff').Delete(outputFilePath['FatalityRate'])
        ogr.GetDriverByName('ESRI Shapefile').DeleteDataSource(outputFilePath['LandslideZoning'])
        ogr.GetDriverByName('ESRI Shapefile').DeleteDataSource(outputFilePath['Building'])
        ogr.GetDriverByName('ESRI Shapefile').DeleteDataSource(outputFilePath['Summary'])


def plotAffectedBuildingsMap(inputSetting, outputFilePath, ax):
    summary = gpd.read_file(outputFilePath['Summary'])
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="4%", pad=0.1)

    # make a color map of fixed colors
    cmap = ListedColormap(['green', 'gold', 'orange', 'red', 'darkred'])
    bounds = [0, 0.2, 1, 4, 10, 100]
    ticks = [str(x) for x in bounds]
    norm = BoundaryNorm(bounds, cmap.N)

    minx, miny, maxx, maxy = summary.total_bounds
    ax.set_xlim(minx-3000, maxx+3000)
    ax.set_ylim(miny, maxy)

    if inputSetting['addBasemap']:
        ax = summary.plot(column='ABExp', ax=ax, cax=cax, cmap=cmap, norm=norm, edgecolor='gray', linewidth=0.5)
        if inputSetting['basemapStyle'] == 'TonerLite':
            ctx.add_basemap(ax, crs=summary.crs, source=ctx.providers.Stamen.TonerLite, attribution='')
        elif inputSetting['basemapStyle'] == 'Terrain':
            ctx.add_basemap(ax, crs=summary.crs, source=ctx.providers.Stamen.Terrain, attribution='') 
        else:
            ctx.add_basemap(ax, crs=summary.crs, source=inputSetting['basemapStyle'], attribution='')
    else:
        ax = summary.plot(column='ABExp', ax=ax, cax=cax, cmap=cmap, norm=norm, edgecolor='gray', linewidth=0.5)
    cb = colorbar.ColorbarBase(cax, cmap=cmap, norm=norm, boundaries=bounds, ticks=bounds, spacing='uniform', orientation='vertical')
    cb.set_ticklabels(ticks)
    cb.ax.tick_params(labelsize=8)
    cb.set_label('Expected No. of Affected Buildings', fontsize=9, labelpad=0.5)

    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)


def plotFatalityMap(inputSetting, outputFilePath, ax):
    summary = gpd.read_file(outputFilePath['Summary'])
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="4%", pad=0.1)

    # make a color map of fixed colors
    cmap = ListedColormap(['green', 'gold', 'orange', 'red', 'darkred'])
    bounds = [0, 0.1, 0.2, 1, 2, 50]
    ticks = [str(x) for x in bounds]
    norm = BoundaryNorm(bounds, cmap.N)

    minx, miny, maxx, maxy = summary.total_bounds
    ax.set_xlim(minx-3000, maxx+3000)
    ax.set_ylim(miny, maxy)

    if inputSetting['addBasemap']:
        ax = summary.plot(column='FExp', ax=ax, cax=cax, cmap=cmap, norm=norm, edgecolor='gray', linewidth=0.5)
        if inputSetting['basemapStyle'] == 'TonerLite':
            ctx.add_basemap(ax, crs=summary.crs, source=ctx.providers.Stamen.TonerLite, attribution='')
        elif inputSetting['basemapStyle'] == 'Terrain':
            ctx.add_basemap(ax, crs=summary.crs, source=ctx.providers.Stamen.Terrain, attribution='')
        else:
            ctx.add_basemap(ax, crs=summary.crs, source=inputSetting['basemapStyle'], attribution='')
    else:
        ax = summary.plot(column='FExp', ax=ax, cax=cax, cmap=cmap, norm=norm, edgecolor='gray', linewidth=0.5)

    cb = colorbar.ColorbarBase(cax, cmap=cmap, norm=norm, boundaries=bounds, ticks=bounds, spacing='uniform', orientation='vertical')
    cb.set_ticklabels(ticks)
    cb.ax.tick_params(labelsize=8)
    cb.set_label('Expected No. of Fatalities', fontsize=9, labelpad=5.5)

    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)


def plotRainfallDistribution(inputSetting, outputFilePath, ax):

    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.05)

    # make a color map of fixed colors
    cmap = ListedColormap(plt.get_cmap('Blues')([0, 0.2, 0.4, 0.6, 0.8, 1]))
    bounds = [0, 100, 200, 300, 400, 500, 1000]
    ticks = [str(x) for x in bounds]
    norm = BoundaryNorm(bounds, cmap.N)

    rainfall = rasterio.open(outputFilePath['Rainfall'])
    rasterio.plot.show(rainfall, ax=ax, cmap=cmap, norm=norm)
    territory = gpd.read_file(inputSetting['territoryBoundaryFile'])
    territory.boundary.plot(ax=ax, edgecolor='black', linewidth=0.2)
    cb = colorbar.ColorbarBase(cax, cmap=cmap, norm=norm, boundaries=bounds, ticks=bounds, spacing='uniform',
                               orientation='vertical')
    cb.set_ticklabels(ticks)
    cb.ax.tick_params(labelsize=8)
    ax.tick_params(left=False, labelleft=False, labelbottom=False, bottom=False)
    ax.axis('scaled')
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)

    minx, miny, maxx, maxy = territory.total_bounds
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)

    maximumRainfall = rainfall.read(1).max()

    return maximumRainfall

def plotAffectedBuildingsProbability(inputSetting, outputFilePath, ax):
    summaryDataframe = pd.read_csv(outputFilePath['AffectedBuildingSummary'])

    histIntervals = inputSetting['buildingBin']
    count = np.zeros(len(histIntervals) - 1)
    for ninterval in range(len(histIntervals) - 1):
        count[ninterval] = summaryDataframe.iat[0, 8 + ninterval]

    colorList = inputSetting['buildingThemeColor']

    x = np.arange(len(histIntervals) - 1)
    width = 1
    countBars = ax.bar(x + width / 2, count, width, color=colorList, edgecolor='k')
    ax.set_xticks(x)
    xlabel = [f'{x:n}' for x in histIntervals[:-1]]
    ax.set_xticklabels(xlabel, fontsize=8)
    ax.set_xlabel('No. of affected buildings', fontsize=9, labelpad=0.5)
    ax.set_xlim(0, len(histIntervals) - 1)
    ax.get_yaxis().set_visible(False)
    for spine in ["left", "top", "right"]:
        ax.spines[spine].set_visible(False)

    for bar in countBars:
        height = bar.get_height()
        ax.annotate(f'{height:.0%}', fontsize=8, xy=(bar.get_x() + bar.get_width() / 2, height), xytext=(0, 3),
                    textcoords='offset points', ha='center', va='bottom')


def plotFatalitiesProbability(inputSetting, outputFilePath, ax):
    summaryDataframe = pd.read_csv(outputFilePath['FatalitySummary'])

    histIntervals = inputSetting['fatalityBin']
    count = np.zeros(len(histIntervals) - 1)
    for ninterval in range(len(histIntervals) - 1):
        count[ninterval] = summaryDataframe.iat[0, 8 + ninterval]
    colorList = inputSetting['fatalityThemeColor']

    x = np.arange(len(histIntervals) - 1)
    width = 1
    countBars = ax.bar(x + width / 2, count, width, color=colorList, edgecolor='k')
    ax.set_xticks(x)
    xlabel = [f'{x:n}' for x in histIntervals[:-1]]
    ax.set_xticklabels(xlabel, fontsize=8)
    ax.set_xlabel('No. of fatalities', fontsize=9, labelpad=0.5)
    ax.set_xlim(0, len(histIntervals) - 1)
    ax.get_yaxis().set_visible(False)
    for spine in ["left", "top", "right"]:
        ax.spines[spine].set_visible(False)

    for bar in countBars:
        height = bar.get_height()
        ax.annotate(f'{height:.0%}', fontsize=8, xy=(bar.get_x() + bar.get_width() / 2, height), xytext=(0, 3),
                    textcoords='offset points', ha='center', va='bottom')



def plotAffectedBuildingsSummaryTable(inputSetting, outputFilePath, ax):
    summaryDataframe = pd.read_csv(outputFilePath['AffectedBuildingSummary'])
    sortedDataframe = summaryDataframe.sort_values(by=['Expectation'], ascending=False)
    totalAffectedBuildings = sortedDataframe.iloc[0][[3]][0]
    histIntervals = inputSetting['buildingBin']
    propertyRiskLevel = 0
    for level in range(len(histIntervals)-1):
        if (totalAffectedBuildings>=histIntervals[level])&(totalAffectedBuildings<histIntervals[level+1]):
            propertyRiskLevel = level
    colorList = inputSetting['buildingThemeColor']
    ax.add_patch(Rectangle(xy=(0.45, 0.7143), width=0.2, height=0.14286, facecolor=colorList[propertyRiskLevel], zorder=-1))
    colName = ['Region', 'Mean', '95%CI']
    ncol = len(colName)
    nrow = 6
    tableContent = []

    for row in range(nrow):
        rowContent = sortedDataframe.iloc[row][[1, 3, 6, 7]]
        name = shorten(rowContent[0], width=20, placeholder="...")
        stats = []
        for i in range(3):
            number = rowContent[i + 1]
            if number >= 100:
                stats.append(f'{number:.0f}')
            else:
                stats.append(f'{number:.1f}')
        l = [name, stats[0], f'{stats[1]}-{stats[2]}']
        tableContent.append(l)

    summaryTable = ax.table(cellText=tableContent, colLabels=colName, cellLoc='left', colLoc='left', bbox=(0, 0, 1, 1), colWidths=[0.45,0.2,0.35])
    summaryTable.auto_set_font_size(False)
    summaryTable.set_fontsize(8)

    applyThreePartTable(summaryTable, ncol)
    setTableTextProperties(summaryTable, row=[x for x in range(nrow + 1)], col=[1], ha='center')
    setTableTextProperties(summaryTable, row=[x for x in range(nrow + 1)], col=[2], ha='right')
    ax.axis('off')

    return totalAffectedBuildings, propertyRiskLevel


def plotFatalitiesSummaryTable(inputSetting, outputFilePath, ax):
    summaryDataframe = pd.read_csv(outputFilePath['FatalitySummary'])
    sortedDataframe = summaryDataframe.sort_values(by=['Expectation'], ascending=False)
    totalFatalities = sortedDataframe.iloc[0][[3]][0]
    histIntervals = inputSetting['fatalityBin']
    humanRiskLevel = 0
    for level in range(len(histIntervals)-1):
        if (totalFatalities>=histIntervals[level])&(totalFatalities<histIntervals[level+1]):
            humanRiskLevel = level
    colorList = inputSetting['fatalityThemeColor']
    ax.add_patch(Rectangle(xy=(0.45, 0.7143), width=0.2, height=0.14286, facecolor=colorList[humanRiskLevel], zorder=-1))
    colName = ['Region', 'Mean', '95%CI']
    ncol = len(colName)
    nrow = 6
    tableContent = []
    for row in range(nrow):
        rowContent = sortedDataframe.iloc[row][[1, 3, 6, 7]]
        name = shorten(rowContent[0], width=20, placeholder="...")
        stats = []
        for i in range(3):
            number = rowContent[i + 1]
            if number >= 100:
                stats.append(f'{number:.0f}')
            else:
                stats.append(f'{number:.1f}')
        l = [name, stats[0], f'{stats[1]}-{stats[2]}']
        tableContent.append(l)
    summaryTable = ax.table(cellText=tableContent, colLabels=colName, cellLoc='left', colLoc='left', bbox=(0, 0, 1, 1), colWidths=[0.45,0.2,0.35])
    summaryTable.auto_set_font_size(False)
    summaryTable.set_fontsize(8)

    setTableTextProperties(summaryTable, row=[x for x in range(nrow+1)], col=[1], ha='center')
    setTableTextProperties(summaryTable, row=[x for x in range(nrow + 1)], col=[2], ha='right')

    applyThreePartTable(summaryTable, ncol)
    ax.axis('off')

    return totalFatalities, humanRiskLevel


def plotHazardSummaryTable(outputFilePath, ax):
    hazardZoningSumShapefile = ogr.Open(outputFilePath['LandslideZoning'])
    hazardZoningSumLayer = hazardZoningSumShapefile.GetLayer(0)
    zoningCount = hazardZoningSumLayer.GetFeatureCount()
    hazardZoningSumDefinition = hazardZoningSumLayer.GetLayerDefn()
    zoningNameFieldIndex = hazardZoningSumDefinition.GetFieldIndex('Region')
    sequenceFieldIndex = hazardZoningSumDefinition.GetFieldIndex('Sequence')
    landslideCountFieldIndex = hazardZoningSumDefinition.GetFieldIndex('Landslide')
    hazardSummaryDataframe = pd.DataFrame(columns=['Sequence', 'ZoningName', 'LandslideCount'])
    for nzone in range(zoningCount):
        zone = hazardZoningSumLayer.GetFeature(nzone)
        zoneSequence = zone.GetFieldAsInteger(sequenceFieldIndex)
        zoneName = zone.GetFieldAsString(zoningNameFieldIndex)
        zoneLandslideCount = zone.GetFieldAsInteger(landslideCountFieldIndex)
        hazardSummaryDataframe = hazardSummaryDataframe.append(
            {'Sequence': zoneSequence, 'ZoningName': zoneName, 'LandslideCount': zoneLandslideCount}, ignore_index=True)

    sortedHazardSummaryDataframe = hazardSummaryDataframe.sort_values(by=['Sequence'])
    region = ['Region', 'Entire HK']
    totalLandslide = int(hazardSummaryDataframe['LandslideCount'].sum())
    estimatedLandslide = ['Estimated No.', f"{totalLandslide}"]

    for nzone in range(zoningCount):
        region.append(sortedHazardSummaryDataframe.iloc[nzone][1])
        estimatedLandslide.append(f"{sortedHazardSummaryDataframe.iloc[nzone][2]:.0f}")

    summaryTable = ax.table(cellText=[region, estimatedLandslide], cellLoc='center', bbox=(0, 0, 1, 1))
    summaryTable.auto_set_font_size(False)
    summaryTable.set_fontsize(9)
    applyThreePartTable(summaryTable, len(region))

    ax.axis('off')

    return totalLandslide


def plotLandslideDistribution(inputSetting, outputFilePath, ax):
    # Calculate the number of landslides per km^2
    gdal.Warp(outputFilePath['LandslideNumber'], outputFilePath['LandslideFrequency'], xRes=1000, yRes=1000, resampleAlg="sum",
                                   format='GTiff')
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.05)

    # make a color map of fixed colors
    cmap = ListedColormap(['white', 'green', 'gold', 'orange', 'red', 'darkred'])
    bounds = [0, 0.5, 5, 10, 20, 50, 500]
    ticks = [str(x) for x in bounds]
    norm = BoundaryNorm(bounds, cmap.N)

    landslideNumber = rasterio.open(outputFilePath['LandslideNumber'])
    rasterio.plot.show(landslideNumber, ax=ax, cmap=cmap, norm=norm)
    territory = gpd.read_file(inputSetting['territoryBoundaryFile'])
    territory.boundary.plot(ax=ax, edgecolor='black', linewidth=0.2)
    cb = colorbar.ColorbarBase(cax, cmap=cmap, norm=norm, boundaries=bounds, ticks=bounds, spacing='uniform',
                               orientation='vertical')
    cb.set_ticklabels(ticks)
    cb.ax.tick_params(labelsize=8)
    ax.tick_params(left=False, labelleft=False, labelbottom=False, bottom=False)
    ax.axis('scaled')
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)

    minx, miny, maxx, maxy = territory.total_bounds
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)


def plotReportTitle(ax, fontsize=13):
    title = 'Prompt Landslide Risk Assessment'
    ax.text(0.02, 0.5, title, ha='left', va='bottom', weight="bold", fontsize=fontsize)
    version = 'Alpha version'
    ax.text(0.02, 0.45, version, ha='left', va='top', fontsize=9)
    ax.add_patch(Rectangle(xy=(0, 0.2), width=0.01, height=0.7, facecolor='k', edgecolor='k'))
    ax.axis('off')


def plotReportTime(inputSetting, ax, fontsize=8):
    now = datetime.now()
    nowString = now.strftime("%a %Y-%m-%d %H:%M:%S")
    reportTime = f"Report generation time: {nowString}\nRainstorm event date: {inputSetting['rainstormDate']}"
    ax.text(0, 0.7, reportTime, ha='left', va='top', fontsize=fontsize)
    ax.axis('off')


def plotReportNumber(inputSetting, ax, fontsize=8):
    reportNumber = f"Report No.: {inputSetting['reportNumber']}"
    ax.text(1, 0.7, reportNumber, ha='right', va='top', fontsize=fontsize)
    ax.axis('off')


def plotRiskLevel(inputSetting, propertyRiskLevel, humanRiskLevel, ax, fontsize=10):
    buildingThemeColor = inputSetting['buildingThemeColor']
    buildingRiskName = inputSetting['buildingWarningNames']
    fatalityThemeColor = inputSetting['fatalityThemeColor']
    fatalityRiskName = inputSetting['fatalityWarningNames']
    ax.text(0.5, 1, 'Risk Level:', ha='center', va='top', weight='bold', fontsize=fontsize)
    propertyLabelX = 0.25
    humanLabelX = 0.75
    labelY = 0.7
    symbolY = 0.05
    symbolHeight = 0.4
    symbolWidth = 0.4
    ax.text(propertyLabelX, labelY, 'Property', ha='center', va='top', fontsize=9)
    ax.add_patch(Rectangle(xy=(propertyLabelX - symbolWidth / 2, symbolY), width=symbolWidth, height=symbolHeight,
                           facecolor=buildingThemeColor[propertyRiskLevel], edgecolor='k'))
    ax.annotate(buildingRiskName[propertyRiskLevel], (propertyLabelX, symbolY + symbolHeight / 2), color='w',
                weight='bold', fontsize=9, ha='center', va='center')

    ax.text(humanLabelX, labelY, 'Human', ha='center', va='top', fontsize=9)
    ax.add_patch(Rectangle(xy=(humanLabelX - symbolWidth / 2, symbolY), width=symbolWidth, height=symbolHeight,
                           facecolor=fatalityThemeColor[humanRiskLevel], edgecolor='k'))
    ax.annotate(fatalityRiskName[humanRiskLevel], (humanLabelX, symbolY + symbolHeight / 2), color='w',
                weight='bold', fontsize=9, ha='center', va='center')
    ax.axis('off')


def plotSubTitle(ax, text, ha='left', fontsize=10):
    if ha == 'left':
        ax.text(0, 0.1, text, ha='left', va='bottom', weight="bold", fontsize=fontsize)
    else:
        ax.text(0.5, 0.1, text, ha='center', va='bottom', weight="bold", fontsize=fontsize)
    ax.axis('off')


def plotSummary(inputSetting, maximumRainfall, totalLandslide, totalAffectedBuildings, totalFatalities,
                propertyRiskLevel, humanRiskLevel, ax, fontsize=9):
    overallRiskLevel = max(propertyRiskLevel, humanRiskLevel)
    riskLevel = inputSetting['buildingWarningNames'][overallRiskLevel]
    if totalAffectedBuildings >= 100:
        totalAffectedBuildingsText = f'{totalAffectedBuildings:.0f}'
    else:
        totalAffectedBuildingsText = f'{totalAffectedBuildings:.1f}'
    if totalFatalities >= 100:
        totalFatalitiesText = f'{totalFatalities:.0f}'
    else:
        totalFatalitiesText = f'{totalFatalities:.1f}'
    summaryText = f'A rainstorm with maximum rolling 24-h rainfall of about {maximumRainfall:.0f} mm hit Hong Kong on {inputSetting["rainstormDate"]}.      About {totalLandslide:.0f} landslides are likely to occur. The expected numbers of buildings affected by landslides and fatalities are {totalAffectedBuildingsText} and {totalFatalitiesText}, respectively. The overall risk level is {riskLevel}.'
    wrappedText = fill(summaryText, width=50, break_long_words=False)
    ax.text(0, 1, wrappedText, ha='left', va='top', wrap=True, fontsize=fontsize)
    ax.axis('off')


def plotFootnote(ax, fontsize=8):
    footnoteText = 'Note: The risk thresholds in this report are just for illustrative purposes.'
    wrappedText = fill(footnoteText, width=135)
    footnote = ax.text(0, 0.5, wrappedText, ha='left', va='center', style='italic', fontsize=fontsize)
    ax.axis('off')


def applyThreePartTable(the_table, ncol):
    nrow = len(the_table.get_celld()) // ncol
    for row in range(nrow):
        for col in range(ncol):
            cell = the_table[row, col]
            if row == 0:  # the header row
                if col == 0:  # the most left column
                    cell.visible_edges = 'LBT'
                elif col == ncol - 1:  # the most right column
                    cell.visible_edges = 'RBT'
                else:  # other columns
                    cell.visible_edges = 'BT'
            elif row == nrow - 1:  # the last row
                if col == 0:  # the most left column
                    cell.visible_edges = 'LB'
                elif col == ncol - 1:  # the most right column
                    cell.visible_edges = 'RB'
                else:  # other columns
                    cell.visible_edges = 'B'
            else:  # other rows
                if col == 0:  # the most left column
                    cell.visible_edges = 'L'
                elif col == ncol - 1:  # the most right column
                    cell.visible_edges = 'R'
                else:  # other columns
                    cell.visible_edges = ''


def setLabelFontBold(the_table, row=0, col=-1):
    for loc, cell in the_table.get_celld().items():
        if (loc[0] == row) and (loc[1] == col):
            cell.set_text_props(weight='bold')


def setTableTextProperties(the_table, row=None, col=None, **kwargs):
    if col is None:
        col = [-1]
    if row is None:
        row = [-1]
    for loc, cell in the_table.get_celld().items():
        if (loc[0] in row) and (loc[1] in col):
            cell.set_text_props(**kwargs)
