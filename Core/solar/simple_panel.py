"""
Calculating solar irradiance on an unobstructed surface.
Parameters:
    Tilt
    Azimuth

Using external libraries SolarModel.dll and GHSolar.gha
"""
import System
import Grasshopper as gh
path = gh.Folders.AppDataFolder
import clr
import os
clr.AddReferenceToFileAndPath(os.path.join(path, "Libraries", "SolarModel.dll"))
import SolarModel as sm


def main(tilt, azimuth, DHI, DNI, latitude, longitude, solarazi, solaralti):
    return simulate_simple_panel(tilt, azimuth, DHI, DNI, latitude, longitude, solarazi, solaralti)


def simulate_simple_panel(tilt, azimuth, _dhi, _dni, latitude, longitude, solarazi, solaralti):
    paropts = System.Threading.Tasks.ParallelOptions()
    paropts.MaxDegreeOfParallelism = 1

    year = 2013 # ASSUMPTION

    recursion = 2
    horizon = 8760

    if (not solaralti) or (not solarazi):
        sunvectors = sm.SunVector.Create8760SunVectors(longitude, latitude, year)   # Blanco-Muriel (2001)
    else:
        sunvectors = sm.SunVector.Create8760SunVectors(longitude, latitude, year, System.Array[float](solarazi), System.Array[float](solaralti))

    # dummy variables, won't be used in this simplified calculation
    coord = [sm.Sensorpoints.p3d()] * 1
    coord[0].X, coord[0].Y, coord[0].Z = 0, 0, 0
    normal = [sm.Sensorpoints.v3d()] * 1
    normal[0].X, normal[0].Y, normal[0].Z = 0, 1, 0

    albedo = [0.3] * horizon    # ASSUMPTION
    weather = sm.Context.cWeatherdata()
    sm.Context.cWeatherdata.DHI.SetValue(weather, System.Collections.Generic.List[float]())
    sm.Context.cWeatherdata.DNI.SetValue(weather, System.Collections.Generic.List[float]())
    sm.Context.cWeatherdata.Snow.SetValue(weather, System.Collections.Generic.List[float]())
    for i in range(0, horizon):
        weather.DHI.Add(_dhi[i])
        weather.DNI.Add(_dni[i])

    #  Calculation points
    p = sm.Sensorpoints(System.Array[float]([tilt]), System.Array[float]([azimuth]), System.Array[sm.Sensorpoints.p3d](coord), System.Array[sm.Sensorpoints.v3d](normal), recursion)
    p.SetSimpleSkyMT(System.Array[float]([tilt]), paropts)
    p.SetSimpleGroundReflectionMT(System.Array[float]([tilt]), System.Array[float](albedo), weather, System.Array[sm.SunVector](sunvectors), paropts)
    p.CalcIrradiationMT(weather, System.Array[sm.SunVector](sunvectors), paropts)

    total = [0.0] * horizon
    # beam = [0.0] * horizon
    # diff = [0.0] * horizon
    # diff_refl = [0.0] * horizon
    for i in range(0, horizon):
        total[i] = p.I[0][i]
        # beam[i] = p.Ibeam[0][i]
        # diff[i] = p.Idiff[0][i]
        # diff_refl[i] = p.Irefl_diff[0][i]
    return total


def visualize_as_mesh():
    return 0


if __name__ == '__main__':
    tilt = 45
    azimuth = 180
    DHI = [10] * 8760
    DNI = [10] * 8760
    latitude = 47
    longitude = 8.55
    solarazi = None
    solaralti = None

    main(tilt, azimuth, DHI, DNI, latitude, longitude, solarazi, solaralti)