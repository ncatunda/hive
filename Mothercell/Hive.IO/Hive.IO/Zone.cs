﻿using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

using rg = Rhino.Geometry;
using Hive.IO.BuildingComponents;


namespace Hive.IO
{

    /// <summary>
    /// Thermal Zone.
    /// Geometry must be (1) Brep, (2) closed, (3) convex, and (4) not contain any curves, i.e. lines only.
    /// </summary>
    public class Zone
    {
        #region Main Properties
        /// <summary>
        /// The actual zone geometry, as rhino Brep
        /// </summary>
        public rg.Brep ZoneGeometry { get; private set; }
        /// <summary>
        /// Unique index, used to identify the zone when it is part of a Building object
        /// </summary>
        public int Index { get; private set; }
        /// <summary>
        /// Tolerance for geometric operations. Get from RhinoDoc.ModelAbsoluteTolerance?
        /// </summary>
        public double Tolerance { get; private set; }
        /// <summary>
        /// fix the horizon to one year, hourly
        /// </summary>
        private const int _horizon = 8760;
        #endregion

        #region Loads And Schedules
        /// <summary>
        /// Zone name, e.g. 'Kitchen01'
        /// </summary>
        public string Name { get; private set; }
        /// <summary>
        /// Internal loads.
        /// Values indicate full / maximal value.
        /// Unit in W/sqm
        /// </summary>
        public struct StructInternalLoads
        {
            public double Occupants;
            public double Devices;
            public double Lighting;
        }
        /// <summary>
        /// Internal loads structure. Values in W/m2
        /// </summary>
        public StructInternalLoads InternalLoads;

        /// <summary>
        /// Time-resolved schedules, values are [0, 1].
        /// Value of 1 indicates full load as defined in this.InternalLoads
        /// </summary>
        public struct StructSchedules
        {
            public double[] Occupants;
            public double[] Devices;
            public double[] Lighting;
        }
        /// <summary>
        /// Schedules that define annual hourly internal loads schedules
        /// </summary>
        public StructSchedules Schedule;
        #endregion

        #region Building Components
        /// <summary>
        /// Wall components of this zone. Cannot be empty.
        /// </summary>
        public Wall[] Walls { get; private set; }
        /// <summary>
        /// Ceiling components of this zone. Cannot be empty.
        /// </summary>
        public Ceiling[] Ceilings { get; private set; }
        /// <summary>
        /// Floor components of this zone. Cannot be empty. A void would also be a floor, but with material property 'air' or something
        /// </summary>
        public Floor[] Floors { get; private set; }
        /// <summary>
        /// Apertures of this zone, e.g. windows, skylights, doors, ventilation openings, etc.. Can be empty.
        /// </summary>
        public Opening[] Openings { get; private set; }
        /// <summary>
        /// Roof components of this zone. Can be empty.
        /// </summary>
        public Roof[] Roofs { get; private set; }

        /// <summary>
        /// Shading devices
        /// </summary>
        public Shading[] ShadingDevices { get; private set; }

        #endregion

        #region Boolean properties
        /// <summary>
        /// For simplicity of thermal calculations, avoid curves etc., only accept linear floorplans and geometries
        /// </summary>
        public bool IsLinear { get; private set; }
        /// <summary>
        /// For simplicity of thermal calculations, only accept convex zones
        /// </summary>
        public bool IsConvex { get; private set; }
        /// <summary>
        /// Zone geometry must be a closed Brep, since it defines a thermal space
        /// </summary>
        public bool IsClosed { get; private set; }
        /// <summary>
        /// Main bool, if this is false, then no thermal simulations can be done
        /// </summary>
        public bool IsValid { get; private set; }
        #endregion
        

        #region Constructor
        /// <summary>
        /// Create an instance of a Zone object
        /// </summary>
        /// <param name="zone_geometry">Brep geometry. Must be closed, linear and convex.</param>
        /// <param name="index">Unique identifier</param>
        /// <param name="name">Zone name, e.g. kitchen 1</param>
        public Zone(rg.Brep zone_geometry, int index, double tolerance, string name, rg.Surface[] opening_srfs =  null, rg.Surface[] shading_srfs = null)
        {
            this.ZoneGeometry = zone_geometry;
            this.Index = index;
            this.Tolerance = tolerance;

            this.IsLinear = CheckLinearity(this.ZoneGeometry);
            if (this.IsLinear)
            {
                this.IsClosed = CheckClosedness(this.ZoneGeometry);
                if (this.IsClosed)
                    this.IsConvex = CheckConvexity(this.ZoneGeometry, this.Tolerance);
                else
                    this.IsConvex = false;
            }
            else
            {
                // these might still be true, but let's set to false to save unnecessary computation
                this.IsConvex = false;
                this.IsClosed = false;
            }
            this.IsValid = CheckValidity(this.IsClosed, this.IsConvex, this.IsLinear);


            if (this.IsValid)
            {
                Tuple< Wall[], Ceiling[], Roof[], Floor[], Opening[], Shading[]> tuple = IdentifyComponents(zone_geometry, opening_srfs, shading_srfs);
                this.Walls = tuple.Item1;
                this.Ceilings = tuple.Item2;
                this.Roofs = tuple.Item3;
                this.Floors = tuple.Item4;
                this.Openings = tuple.Item5;
                this.ShadingDevices = tuple.Item6;
            }
            else 
            { 
                return; 
            }


            // define standard building physical properties upon inizialization. 
            // Can be changed later via Windows Form
            this.Name = name;
            this.InternalLoads.Occupants = 16.0;
            this.InternalLoads.Lighting = 4.0;
            this.InternalLoads.Devices = 3.0;
            this.Schedule.Occupants = new double[_horizon];
            this.Schedule.Lighting = new double[_horizon];
            this.Schedule.Devices = new double[_horizon];
            // windows form with interface to change schedules for workdays and weekends / holidays?
            for(int i=0; i<_horizon; i++)
            {
                this.Schedule.Occupants[i] = 1.0;
                this.Schedule.Lighting[i] = 1.0;
                this.Schedule.Devices[i] = 1.0;
            }




        }
        #endregion


        #region internalMethods
        /// <summary>
        /// Check the linearity of the brep zone geometry. No curves allowed for simplicity.
        /// </summary>
        /// <param name="brep"></param>
        /// <returns>True if all is linear</returns>
        private bool CheckLinearity(rg.Brep brep)
        {
            bool isLinear = true;
            foreach (rg.BrepEdge edge in brep.Edges)
            {
                if (edge.IsLinear() == false)
                {
                    isLinear = false;
                    break;
                }
            }
            return isLinear;
        }

        /// <summary>
        /// Check the convexity of the zone. Hive only allows convex spaces, for simplicity.
        /// </summary>
        /// <param name="brep">geometry that is checked for convexity</param>
        /// <param name="tolerance">model tolerance, for intersection checks</param>
        /// <returns>True, if convex</returns>
        private bool CheckConvexity(rg.Brep brep, double tolerance)
        {
            int vertexCount = brep.Vertices.Count;

            for (int i = 0; i < vertexCount; i++)
            {
                rg.BrepVertex vert1 = brep.Vertices[i];
                for (int u = 0; u < vertexCount; u++)
                {
                    if (i == u) continue;

                    rg.BrepVertex vert2 = brep.Vertices[u];
                    rg.LineCurve line = new rg.LineCurve(vert1.Location, vert2.Location);
                    rg.Curve[] overlap_curves;
                    rg.Point3d[] inter_points;
                    if (rg.Intersect.Intersection.CurveBrep(line, brep, tolerance, out overlap_curves, out inter_points))
                    {
                        if (overlap_curves.Length > 0 || inter_points.Length > 0)
                        {
                            if (inter_points.Length > 2)
                                return false;
                            else if(inter_points.Length == 2)
                            {
                                //check if middle point is within the brep or not. if not, its convex
                                rg.Point3d middlepoint = (inter_points[0] + inter_points[1]) / 2.0;
                                if (!brep.IsPointInside(middlepoint, tolerance, false))
                                {
                                    return false;
                                }
                            } //do i need a case with inter_points == 1?
                        }
                    }                   
                }
            }
            return true;
        }

        /// <summary>
        /// Check the closedness of the brep. No open breps allowed, since a the brep is used to define a thermal space.
        /// </summary>
        /// <param name="brep"></param>
        /// <returns>True, if it is closed</returns>
        private bool CheckClosedness(rg.Brep brep)
        {
            return brep.IsSolid;
        }

        /// <summary>
        /// Check if all three conditions (Closedness, Convexity, Linearity) are fulffilled.
        /// </summary>
        /// <returns>True, if zone geometry is valid</returns>
        private bool CheckValidity(bool closed, bool convex, bool linear)
        {
            if (convex && closed && linear)
                return true;
            else
                return false;
        }


        /// <summary>
        /// Identifies and initializes building components from input geometries
        /// </summary>
        /// <param name="zone_geometry"></param>
        /// <param name="openings_geometry"></param>
        /// <param name="shading_geometry"></param>
        /// <returns></returns>
        private Tuple<Wall [], Ceiling [], Roof [], Floor [], Opening[], Shading[]> 
            IdentifyComponents(rg.Brep zone_geometry, rg.Surface[] openings_geometry, rg.Surface[] shading_geometry)
        {
            Opening [] openings = new Opening[openings_geometry.Length];
            Shading [] shadings = new Shading[shading_geometry.Length];
            if (openings_geometry.Length > 0)
            {

            }

            if (shading_geometry.Length > 0)
            {

            }

            int wall_count = 0;
            int ceiling_count = 0;
            int roof_count = 0;
            int floor_count = 0;

            Rhino.Geometry.Collections.BrepSurfaceList srfs = zone_geometry.Surfaces;
            foreach (rg.Surface srf in srfs)
            {
                // Floor: flat surface with  normal pointing downwards

                // Roof: surface angle < 45? 
                // Ceiling: Same, but there must be an adjacent zone surface, such that this surface is internal. Hive 0.2

                // Wall: surface angle >= 45?


            }


            Wall [] walls = new Wall[wall_count];
            Ceiling [] ceilings = new Ceiling[ceiling_count];
            Roof [] roofs = new Roof[roof_count];
            Floor [] floors = new Floor[floor_count];

            return new Tuple<Wall[], Ceiling[], Roof[], Floor[], Opening[], Shading[]>(walls, ceilings, roofs, floors, openings, shadings);
        }
        #endregion
    }

}
