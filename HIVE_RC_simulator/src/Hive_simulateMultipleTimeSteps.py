# This component can be used to simulate indoor temperature, heating, cooling and lighting demand for a series of hourly time steps.
#
# Hive: A energy simulation plugin developed by the A/S chair at ETH Zurich
# This component is adapted from examples\annualSimulation.py in the RC_BuildingSimulator Github repository
# https://github.com/architecture-building-systems/RC_BuildingSimulator
# Extensive documentation about the model is available on the project wiki.
#
# Author: Justin Zarb <zarbj@student.ethz.ch>
#
# This file is part of Hive
#
# Licensing/Copyright and liability comments go here.
# <Copyright 2018, Architecture and Building Systems - ETH Zurich>
# <Licence: MIT>

"""
Use this component to simulate indoor temperature, heating, cooling and lighting for a series of hourly time steps. You may add a custom zone or leave the Zone arg blank for the default zone.
-
Provided by Hive 0.0.1
    
    Args:
        Zone: Input a customized Zone from the Zone component.
        outdoor_air_temperature: List of hourly outdoor air temperatures
        previous_mass_temperature: The temperature of the mass node during the hour prior to the first time step. This temperature represents the average temperature of the building envelope itself.
        internal_gains: List of hourly internal heat gains [Watts].
        solar_irradiation: List of solar irradiation gains [Watts].
        illuminance: Illuminance after transmitting through the window [Lumens]
        occupancy: Occupancy for the timestep [people/hour/square_meter]
    Returns:
        readMe!: Currently shows the list lengths of all the inputs for quick debugging.
        indoor_air_temperature: Profile of the indoor air temperature.
        lighting_demand: Profile of the lighting energy demand.
        heating_demand: Profile of the heating energy demand required to maintain the heating setpoint temperature defined in the Zone.
        cooling_demand: Profile of the cooling energy demand required to maintain the cooling setpoint temperature defined in the Zone.
        energy_demand: Sum of heating, cooling and lighting demand profiles for the given timestep.
        solar_gains: Estimated solar gains, calculated by multiplying the irradiation by a transmission factor.
        ill: hourly illuminance levels
"""

ghenv.Component.Name = "Hive_simulateMultipleTimeSteps"
ghenv.Component.NickName = 'simulateMultipleTimeSteps'
ghenv.Component.Message = 'VER 0.0.1\nAPR_24_2018'
ghenv.Component.IconDisplayMode = ghenv.Component.IconDisplayMode.application
ghenv.Component.Category = "Hive"
ghenv.Component.SubCategory = "2 | Simulation"
# ComponentExposure=2

import Grasshopper.Kernel as gh
import scriptcontext as sc

def main(Zone, outdoor_air_temperature, previous_mass_temperature, internal_gains, solar_gains, occupancy, illuminance):
    if not sc.sticky.has_key('RCModel'): return "Add the modular RC component to the canvas!"
    HivePreparateion = sc.sticky['HivePreparation']()
    #Initialise zone object
    if Zone is None:
        Zone = sc.sticky["RCModel"]()
        warning = """No zone definition has been detected. The default zone will be
        applied."""
        w = gh.GH_RuntimeMessageLevel.Warning
        ghenv.Component.AddRuntimeMessage(w, warning)
    else:
        Zone = Zone
    
    """
    Spectral luminous efficacy (108)- can be calculated from the weather file 
    https://en.wikipedia.org/wiki/Luminous_efficacy
    ill = [s * 108 for s in solar_gains]
    """
    
    #Initialise result lists
    indoor_air_temperature = []
    operative_temperature = []
    mass_temperature = []
    energy_demand = []
    heating_demand = []
    cooling_demand = []
    lighting_demand = []
    
    #Start simulation
    for b in range(outdoor_air_temperature.BranchCount):
        hour, ta = outdoor_air_temperature.Branch(b)
        oc = 0 if occupancy is False else occupancy[b]
        ig = 0 if internal_gains is False else internal_gains[b]
        sg = 0 if solar_gains is False else solar_gains[b]
        il = 0 if illuminance is False else illuminance[b]
        
        try:
            Zone.solve_building_energy(ig, sg, ta, previous_mass_temperature)    
            Zone.solve_building_lighting(il, oc)
        except:
            print 'building energy could not be solved for the following inputs'
            print 'outdoor air temperature: ', ta
            print 'previous mass temperature: ', previous_mass_temperature
            print 'internal gains: ', ig
            print 'solar gains: ', sg
            print 'illuminance: ',il
            print 'occupancy: ',oc
            Zone.solve_building_energy(ig, sg, ta, previous_mass_temperature) 
            break
        
        #Set T_m as t_m_prev for next timestep
        t_m_prev = Zone.t_m
        
        #Record Results
        indoor_air_temperature.append([Zone.t_air])
        operative_temperature.append([Zone.t_operative])
        mass_temperature.append([Zone.t_m])  # Printing Room Temperature of the medium
        lighting_demand.append([Zone.lighting_demand])  # Print Lighting Demand
        energy_demand.append([Zone.energy_demand])  # Print heating/cooling loads
        heating_demand.append([Zone.heating_demand])
        cooling_demand.append([Zone.cooling_demand])
        
    return HivePreparation.list_to_tree(indoor_air_temperature), \
    HivePreparation.list_to_tree(operative_temperature), \
    HivePreparation.list_to_tree(mass_temperature), \
    HivePreparation.list_to_tree(lighting_demand), \
    HivePreparation.list_to_tree(energy_demand), \
    HivePreparation.list_to_tree(heating_demand), \
    HivePreparation.list_to_tree(cooling_demand)

def check_input_tree(input_tree,input_tree_name):
    if input_tree.BranchCount>0:
        total_per_hour = []
        for b in range(0,input_tree.BranchCount):
            total_per_hour.append(sum(input_tree.Branch(b)))
        return total_per_hour
    else:
        HivePreparation.raise_warning('No data for %s'%input_tree_name)
        return False

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
HivePreparation = sc.sticky['HivePreparation']()

# Initialise previous mass temperature if it hasn't been specified
previous_mass_temperature = initial_mass_temperature if initial_mass_temperature is not None else 20.0

# Check input for outdoor air temperature
if outdoor_air_temperature.BranchCount==0:
    HivePreparation.raise_warning('No data for outdoor_air_temperature')

# Check input and add all data streams
sg_list = check_input_tree(solar_gains,'solar_gains')
ill_list = check_input_tree(illuminance,'illuminance')
ig_list = check_input_tree(internal_gains,'internal_gains')
occ_list = check_input_tree(occupancy,'occupancy')

#if sg_list and ill_list and ig_list and occ_list:
indoor_air_temperature, operative_temperature, mass_temperature, lighting_demand, energy_demand, heating_demand, cooling_demand = main(Zone, outdoor_air_temperature, previous_mass_temperature, ig_list, sg_list, occ_list, ill_list)