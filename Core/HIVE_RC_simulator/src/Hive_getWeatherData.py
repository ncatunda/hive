#
# Hive: An educational plugin developed by the A/S chair at ETH Zurich
# 
# This file is part of Hive.
# 
# TODO: Check terms of GNU modification.
#
# This component is a mashup of functions from Ladybug for importing and reading 
# EPW files. 
# 

"""
Extract temperature, location and irradiation data from a weather file. 
-
Provided by Hive 0.0.1

    Args:
        epw_file: connect a path to a weather file
        browse_for_epw: Set to True to browse for a weather file in your system.
        start_HOY: Default=1. Optional HOY for the start of the analysis period
        end_HOY: Default=8760. Optional HOY for the end of the analysis period
    Returns:
        ReadMe!: ...
        location: a list of longitude, latitude, utc offset and year
        temperature: a tree in the form: {hoy,temperature}
        irradiation: a tree in the form: {hoy, direct normal irradiation, diffuse horizontal irradiation, direct normal illuminance, diffuse horizontal illuminance)
"""

ghenv.Component.Name = "Hive_getWeatherData"
ghenv.Component.NickName = 'getWeatherData'
ghenv.Component.Message = 'VER 0.0.1\nMAY_29_2018'
ghenv.Component.Category = "Hive"
ghenv.Component.SubCategory = "1. Environment"
# ComponentExposure=1

import rhinoscriptsyntax as rs
import scriptcontext as sc
import Grasshopper.Kernel as ghKernel
from Grasshopper.Kernel.Data import GH_Path
from Grasshopper import DataTree
from System import Object

class GhPythonDictionary(object):
    def __init__(self, pythonDict=None):
        if pythonDict:
            self.d = pythonDict
        else:
            self.d = {}
    def ToString(self):
        return 'GhPythonDictionary object'

def separate_data(inputList):
    # Based on Ladybug_Separate data, but uses lists instead of DataTree objects
    num = []
    str = []
    lastOne = None
    
    strPath = 0
    numPath = 0
    
    p = []
    numbers = []
    strings = []
    
    for count, item in enumerate(inputList):
        try:
            item = float(item)
            if count == 0: numfirst = True
            if lastOne == None: lastOne = "float"
            if lastOne!= "float":
                lastOne = "float"
                numPath += 1
            if numfirst == False:
                p.append(numPath-1)
                numbers.append(item)
            else:
                p.append(numPath)
                numbers.append(item)
        except:
            if count == 0: numfirst = False
            if lastOne == None: lastOne = "str"
            if lastOne!= "str":
                lastOne = "str"
                strPath += 1
            if numfirst == True:
                p.append(strPath-1)
                strings.append(item)
            else:
                p.append(strPath)
                strings.append(item)
    
    return numbers

def open_epw(open):
    #Based on Ladybug_Open EPW Weather File
    if open == True:
        filter = "EPW file (*.epw)|*.epw|All Files (*.*)|*.*||"
        epwFile = rs.OpenFileName("Open .epw Weather File", filter)
        print 'Done!'
        return epwFile
    else:
        print 'Please set open to True'

def list_to_tree(nestedlist):
    layerTree = DataTree[object]()
    for i, item_list in enumerate(nestedlist):
        path = GH_Path(i)
        layerTree.AddRange(item_list,path)
    return layerTree

def main(epw_file,start_HOY,end_HOY):
    if not sc.sticky.has_key('HivePreparation'): return "Add the modular RC component to the canvas!"
    #TODO: Set up compatibility checks like in Ladybug.
    
    sc.sticky['simulation_period'] = '[%i,%i]'%(start_HOY,end_HOY)
    
    HivePreparation = sc.sticky["HivePreparation"]()
    start,end = HivePreparation.set_simulation_period(start_HOY,end_HOY)
    temperature = []
    irradiation = []
    
    if (epw_file is not None):
        locationData = HivePreparation.epwLocation(epw_file)
        weatherData = HivePreparation.epwDataReader(epw_file, locationData[0])

        location = [locationData[1], locationData[2], locationData[3]]
        dryBulbTemperature, dewPointTemperature, relativeHumidity, windSpeed, windDirection, directNormalRadiation, diffuseHorizontalRadiation, globalHorizontalRadiation, directNormalIlluminance, diffuseHorizontalIlluminance, globalHorizontalIlluminance, totalSkyCover, horizontalInfraredRadiation, barometricPressure, modelYear = weatherData
        location.append(modelYear[7])

        dryBulbTemperature = separate_data(dryBulbTemperature)
        directRadiation = separate_data(directNormalRadiation)
        diffuseRadiation = separate_data(diffuseHorizontalRadiation)
        directIlluminance = separate_data(directNormalIlluminance)
        diffuseIlluminance = separate_data(diffuseHorizontalIlluminance)
        
        for i in range(start-1,end):
            temperature.append([i,dryBulbTemperature[i]])
            irradiation.append([i, directRadiation[i], diffuseRadiation[i], directIlluminance[i], diffuseIlluminance[i]])
    
    return location, list_to_tree(temperature), list_to_tree(irradiation)

def raise_warning(warning_str):
    warning = warning_str
    w = ghKernel.GH_RuntimeMessageLevel.Warning
    ghenv.Component.AddRuntimeMessage(w, warning)

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

if epw_file is None:
    if browse_for_epw:
        epw_file = open_epw(browse_for_epw)
else:
    if start_HOY is None or end_HOY is None:
        raise_warning('start_HOY or end_HOY are disconnected. Default values of 0 or 8760, respectively, will be assumed')
    
    start_HOY = 1 if not start_HOY else start_HOY
    end_HOY = 8760 if not end_HOY else end_HOY
    location, temperature, irradiation = main(epw_file,start_HOY,end_HOY)
