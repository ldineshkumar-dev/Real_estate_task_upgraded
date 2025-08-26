"""
Interactive Measurement System for Oakville Properties
Provides property boundary data and interactive measurement tools
Based on Oakville's ArcGIS REST APIs and interactive map methodology
"""

import requests
import json
import math
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import numpy as np
from pyproj import Transformer

logger = logging.getLogger(__name__)

@dataclass
class PropertyBoundary:
    """Property boundary data structure"""
    coordinates: List[Tuple[float, float]]  # List of (x, y) coordinate pairs
    area_sqm: float
    perimeter_m: float
    centroid: Tuple[float, float]
    spatial_reference: int
    geometry_type: str

@dataclass
class MeasurementPoint:
    """Measurement point with coordinates and metadata"""
    x: float
    y: float
    lat: float
    lon: float
    point_type: str  # 'frontage', 'depth', 'custom'
    description: str

@dataclass
class PropertyMeasurement:
    """Property measurement result"""
    distance_m: float
    distance_ft: float
    point1: MeasurementPoint
    point2: MeasurementPoint
    measurement_type: str  # 'frontage', 'depth', 'diagonal'
    azimuth_degrees: float  # Direction of measurement

class InteractiveMeasurementClient:
    """
    Client for interactive property measurements using Oakville GIS APIs
    Replicates functionality of Oakville's interactive map ruler tool
    """
    
    def __init__(self):
        self.base_url = "https://maps.oakville.ca/oakgis/rest/services/SBS"
        
        # API endpoints for property boundary data (CORRECTED)
        self.endpoints = {
            'property_boundaries': '/Zoning_By_law_2014_014/FeatureServer/10/query',  # Property boundaries (CORRECT ENDPOINT)
            'parcel_fabric': '/Parcel_Address/FeatureServer/0/query',  # Parcel fabric data
            'assessment_parcels': '/Assessment_Parcels/FeatureServer/0/query'  # Assessment parcel polygons
        }
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'OakvilleMeasurementTool/1.0',
            'Accept': 'application/json, application/pbf'
        })
        
        # Coordinate transformers (CORRECTED TO USE WEB MERCATOR)
        # Web Mercator (102100/3857) to WGS84 (4326)
        self.web_mercator_to_wgs84 = Transformer.from_crs("EPSG:102100", "EPSG:4326", always_xy=True)
        # WGS84 to Web Mercator (102100) - CORRECT for Oakville API
        self.wgs84_to_web_mercator = Transformer.from_crs("EPSG:4326", "EPSG:102100", always_xy=True)
        # UTM Zone 17N (26917) to WGS84 (4326) - Keep for distance calculations  
        self.utm17n_to_wgs84 = Transformer.from_crs("EPSG:26917", "EPSG:4326", always_xy=True)
        # WGS84 to UTM Zone 17N for accurate distance calculations
        self.wgs84_to_utm17n = Transformer.from_crs("EPSG:4326", "EPSG:26917", always_xy=True)
        
        self.timeout = 30
        self.max_retries = 3
        
    def get_property_boundary(self, lat: float, lon: float, address: str = None) -> Optional[PropertyBoundary]:
        """
        Get property boundary data for interactive measurement
        
        Args:
            lat: Property latitude (WGS84)
            lon: Property longitude (WGS84)
            address: Optional property address
            
        Returns:
            PropertyBoundary object with coordinate data for measurement
        """
        try:
            # Method 1: Try using property boundaries endpoint (FeatureServer/4)
            boundary = self._get_boundary_from_zoning_service(lat, lon)
            if boundary:
                return boundary
                
            # Method 2: Try using parcel fabric data
            boundary = self._get_boundary_from_parcel_fabric(lat, lon, address)
            if boundary:
                return boundary
                
            # Method 3: Fallback to assessment parcels
            boundary = self._get_boundary_from_assessment_parcels(lat, lon, address)
            return boundary
            
        except Exception as e:
            logger.error(f"Error getting property boundary: {e}")
            return None
    
    def _get_boundary_from_zoning_service(self, lat: float, lon: float) -> Optional[PropertyBoundary]:
        """Get boundary from zoning service (FeatureServer/10) - CORRECTED IMPLEMENTATION"""
        try:
            # Convert WGS84 to Web Mercator for the query (CORRECTED)
            x_mercator, y_mercator = self.wgs84_to_web_mercator.transform(lon, lat)
            
            # Create envelope around the point (buffer of ~50 meters)
            buffer = 50  # meters in Web Mercator
            envelope = {
                "xmin": x_mercator - buffer,
                "ymin": y_mercator - buffer,
                "xmax": x_mercator + buffer,
                "ymax": y_mercator + buffer
            }
            
            # Query parameters for property boundary (CORRECTED)
            params = {
                'f': 'json',  # Request JSON for easier parsing
                'geometry': json.dumps(envelope),  # Use envelope geometry
                'geometryType': 'esriGeometryEnvelope',  # CORRECTED
                'inSR': '102100',  # Web Mercator (CORRECTED)
                'outSR': '102100',  # Return in Web Mercator (CORRECTED)
                'spatialRel': 'esriSpatialRelIntersects',
                'where': '1=1',
                'outFields': '*',  # Get all fields
                'returnGeometry': 'true',
                'resultRecordCount': 10  # Get up to 10 features
            }
            
            url = self.base_url + self.endpoints['property_boundaries']
            logger.info(f"Querying property boundaries at {lat}, {lon} (Web Mercator: {x_mercator}, {y_mercator})")
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"API response keys: {list(data.keys())}")
                
                if data.get('features') and len(data['features']) > 0:
                    features = data['features']
                    logger.info(f"Found {len(features)} features")
                    
                    # Return the first (largest/most relevant) feature
                    feature = features[0]
                    
                    # Log feature info for debugging
                    attrs = feature.get('attributes', {})
                    zone_desc = attrs.get('ZONE_DESC', 'Unknown')
                    logger.info(f"Selected feature: ZONE_DESC={zone_desc}, OBJECTID={attrs.get('OBJECTID', 'Unknown')}")
                    
                    return self._parse_boundary_geometry(feature, spatial_ref=102100)
                else:
                    logger.warning(f"No features found for coordinates {lat}, {lon}. Response: {data}")
            else:
                logger.error(f"API request failed with status {response.status_code}: {response.text[:200]}")
                    
        except Exception as e:
            logger.error(f"Zoning service boundary lookup failed: {e}")
            
        return None
    
    def _get_boundary_from_parcel_fabric(self, lat: float, lon: float, address: str = None) -> Optional[PropertyBoundary]:
        """Get boundary from parcel fabric data"""
        try:
            # If address provided, use it for lookup
            if address:
                clean_address = address.upper().strip()
                where_clause = f"ADDRESS LIKE '%{clean_address}%'"
            else:
                # Use spatial query with coordinates
                x_utm, y_utm = self.wgs84_to_utm17n.transform(lon, lat)
                where_clause = '1=1'
            
            params = {
                'f': 'json',
                'where': where_clause,
                'outFields': '*',
                'returnGeometry': 'true',
                'spatialRel': 'esriSpatialRelIntersects',
                'outSR': '26917'  # UTM Zone 17N
            }
            
            # Add geometry if no address provided
            if not address:
                x_utm, y_utm = self.wgs84_to_utm17n.transform(lon, lat)
                params['geometry'] = f'{x_utm},{y_utm}'
                params['geometryType'] = 'esriGeometryPoint'
                params['inSR'] = '26917'
            
            url = self.base_url + self.endpoints['parcel_fabric']
            response = self.session.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('features') and len(data['features']) > 0:
                    feature = data['features'][0]
                    return self._parse_boundary_geometry(feature)
                    
        except Exception as e:
            logger.warning(f"Parcel fabric boundary lookup failed: {e}")
            
        return None
    
    def _get_boundary_from_assessment_parcels(self, lat: float, lon: float, address: str = None) -> Optional[PropertyBoundary]:
        """Get boundary from assessment parcels as fallback"""
        try:
            x_utm, y_utm = self.wgs84_to_utm17n.transform(lon, lat)
            
            params = {
                'f': 'json',
                'geometry': f'{x_utm},{y_utm}',
                'geometryType': 'esriGeometryPoint',
                'inSR': '26917',
                'spatialRel': 'esriSpatialRelIntersects',
                'where': '1=1',
                'outFields': '*',
                'returnGeometry': 'true',
                'outSR': '26917'
            }
            
            url = self.base_url + self.endpoints['assessment_parcels']
            response = self.session.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('features') and len(data['features']) > 0:
                    feature = data['features'][0]
                    return self._parse_boundary_geometry(feature)
                    
        except Exception as e:
            logger.warning(f"Assessment parcels boundary lookup failed: {e}")
            
        return None
    
    def _parse_boundary_geometry(self, feature: Dict, spatial_ref: int = 102100) -> Optional[PropertyBoundary]:
        """Parse geometry from ArcGIS feature into PropertyBoundary (CORRECTED)"""
        try:
            geometry = feature.get('geometry', {})
            attributes = feature.get('attributes', {})
            
            # Handle different geometry types
            if 'rings' in geometry:
                # Polygon geometry
                coordinates = []
                rings = geometry['rings']
                if rings and len(rings) > 0:
                    # Get exterior ring (first ring)
                    exterior_ring = rings[0]
                    coordinates = [(point[0], point[1]) for point in exterior_ring]
                    
            elif 'paths' in geometry:
                # Polyline geometry (shouldn't happen for parcels but handle it)
                paths = geometry['paths']
                if paths and len(paths) > 0:
                    coordinates = [(point[0], point[1]) for point in paths[0]]
            else:
                logger.warning("Unsupported geometry type")
                return None
            
            if not coordinates:
                return None
            
            # Convert coordinates to UTM for accurate area/perimeter calculations
            utm_coordinates = []
            for x_merc, y_merc in coordinates:
                # Convert Web Mercator to WGS84, then to UTM
                lon, lat = self.web_mercator_to_wgs84.transform(x_merc, y_merc)
                x_utm, y_utm = self.wgs84_to_utm17n.transform(lon, lat)
                utm_coordinates.append((x_utm, y_utm))
            
            # Calculate area and perimeter using UTM coordinates for accuracy
            area_sqm = self._calculate_polygon_area(utm_coordinates)
            perimeter_m = self._calculate_polygon_perimeter(utm_coordinates)
            centroid_utm = self._calculate_centroid(utm_coordinates)
            
            # Store coordinates in Web Mercator as received from API
            return PropertyBoundary(
                coordinates=coordinates,  # Keep in Web Mercator
                area_sqm=area_sqm,
                perimeter_m=perimeter_m,
                centroid=centroid_utm,  # Store centroid in UTM for calculations
                spatial_reference=spatial_ref,  # Web Mercator (102100)
                geometry_type="polygon"
            )
            
        except Exception as e:
            logger.error(f"Error parsing boundary geometry: {e}")
            return None
    
    def calculate_distance(self, point1: Tuple[float, float], point2: Tuple[float, float], 
                          coordinate_system: str = 'wgs84') -> float:
        """
        Calculate distance between two points
        
        Args:
            point1: First point (lat, lon) or (x, y)
            point2: Second point (lat, lon) or (x, y)  
            coordinate_system: 'wgs84' for lat/lon, 'utm' for UTM coordinates
            
        Returns:
            Distance in meters
        """
        if coordinate_system == 'wgs84':
            # Convert to UTM for accurate distance calculation
            x1, y1 = self.wgs84_to_utm17n.transform(point1[1], point1[0])  # lon, lat -> x, y
            x2, y2 = self.wgs84_to_utm17n.transform(point2[1], point2[0])
        else:
            # Already in UTM
            x1, y1 = point1
            x2, y2 = point2
        
        # Euclidean distance in UTM coordinates (meters)
        distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        return distance
    
    def calculate_azimuth(self, point1: Tuple[float, float], point2: Tuple[float, float],
                         coordinate_system: str = 'wgs84') -> float:
        """
        Calculate azimuth (bearing) between two points
        
        Returns:
            Azimuth in degrees (0-360, where 0 is North)
        """
        if coordinate_system == 'wgs84':
            x1, y1 = self.wgs84_to_utm17n.transform(point1[1], point1[0])
            x2, y2 = self.wgs84_to_utm17n.transform(point2[1], point2[0])
        else:
            x1, y1 = point1
            x2, y2 = point2
        
        # Calculate azimuth
        dx = x2 - x1
        dy = y2 - y1
        
        azimuth = math.degrees(math.atan2(dx, dy))
        if azimuth < 0:
            azimuth += 360
            
        return azimuth
    
    def create_measurement(self, point1_lat: float, point1_lon: float,
                          point2_lat: float, point2_lon: float,
                          measurement_type: str = 'custom',
                          point1_desc: str = 'Point 1',
                          point2_desc: str = 'Point 2') -> PropertyMeasurement:
        """
        Create a measurement between two points
        
        Args:
            point1_lat, point1_lon: First point coordinates
            point2_lat, point2_lon: Second point coordinates  
            measurement_type: Type of measurement ('frontage', 'depth', 'diagonal', 'custom')
            point1_desc, point2_desc: Descriptions for the points
            
        Returns:
            PropertyMeasurement object with distance and metadata
        """
        # Convert to UTM for accurate measurements
        x1, y1 = self.wgs84_to_utm17n.transform(point1_lon, point1_lat)
        x2, y2 = self.wgs84_to_utm17n.transform(point2_lon, point2_lat)
        
        # Create measurement points
        point1 = MeasurementPoint(
            x=x1, y=y1, lat=point1_lat, lon=point1_lon,
            point_type=measurement_type, description=point1_desc
        )
        
        point2 = MeasurementPoint(
            x=x2, y=y2, lat=point2_lat, lon=point2_lon,
            point_type=measurement_type, description=point2_desc
        )
        
        # Calculate distance and azimuth
        distance_m = self.calculate_distance((point1_lat, point1_lon), (point2_lat, point2_lon))
        distance_ft = distance_m * 3.28084  # Convert to feet
        azimuth = self.calculate_azimuth((point1_lat, point1_lon), (point2_lat, point2_lon))
        
        return PropertyMeasurement(
            distance_m=distance_m,
            distance_ft=distance_ft,
            point1=point1,
            point2=point2,
            measurement_type=measurement_type,
            azimuth_degrees=azimuth
        )
    
    def suggest_measurement_points(self, boundary: PropertyBoundary) -> Dict[str, List[Tuple[float, float]]]:
        """
        Suggest optimal points for frontage and depth measurements
        
        Args:
            boundary: PropertyBoundary object
            
        Returns:
            Dictionary with suggested measurement points for frontage and depth
        """
        if not boundary or len(boundary.coordinates) < 4:
            return {}
        
        # Convert Web Mercator coordinates to lat/lon for return
        coordinates_latlon = []
        for x, y in boundary.coordinates:
            lon, lat = self.web_mercator_to_wgs84.transform(x, y)
            coordinates_latlon.append((lat, lon))
        
        # Find the longest edge (likely street frontage)
        max_distance = 0
        frontage_points = None
        
        for i in range(len(boundary.coordinates) - 1):
            p1 = boundary.coordinates[i]
            p2 = boundary.coordinates[i + 1]
            # Convert Web Mercator to WGS84 for distance calculation
            lon1, lat1 = self.web_mercator_to_wgs84.transform(p1[0], p1[1])
            lon2, lat2 = self.web_mercator_to_wgs84.transform(p2[0], p2[1])
            distance = self.calculate_distance((lat1, lon1), (lat2, lon2), 'wgs84')
            
            if distance > max_distance:
                max_distance = distance
                # Convert Web Mercator to lat/lon
                lon1, lat1 = self.web_mercator_to_wgs84.transform(p1[0], p1[1])
                lon2, lat2 = self.web_mercator_to_wgs84.transform(p2[0], p2[1])
                frontage_points = [(lat1, lon1), (lat2, lon2)]
        
        # Find perpendicular points for depth measurement
        # This is a simplified approach - in practice you'd want more sophisticated analysis
        depth_points = None
        if frontage_points and len(boundary.coordinates) >= 4:
            # Find points roughly perpendicular to frontage
            # Use the centroid and find the furthest point from frontage line
            centroid_utm = boundary.centroid
            centroid_lon, centroid_lat = self.utm17n_to_wgs84.transform(centroid_utm[0], centroid_utm[1])
            
            # For simplicity, use centroid and a point opposite to frontage midpoint
            frontage_midpoint_lat = (frontage_points[0][0] + frontage_points[1][0]) / 2
            frontage_midpoint_lon = (frontage_points[0][1] + frontage_points[1][1]) / 2
            
            depth_points = [(frontage_midpoint_lat, frontage_midpoint_lon), (centroid_lat, centroid_lon)]
        
        suggestions = {}
        if frontage_points:
            suggestions['frontage'] = frontage_points
        if depth_points:
            suggestions['depth'] = depth_points
            
        return suggestions
    
    def _calculate_polygon_area(self, coordinates: List[Tuple[float, float]]) -> float:
        """Calculate polygon area using shoelace formula"""
        if len(coordinates) < 3:
            return 0.0
        
        area = 0.0
        n = len(coordinates)
        
        for i in range(n):
            j = (i + 1) % n
            area += coordinates[i][0] * coordinates[j][1]
            area -= coordinates[j][0] * coordinates[i][1]
        
        return abs(area) / 2.0
    
    def _calculate_polygon_perimeter(self, coordinates: List[Tuple[float, float]]) -> float:
        """Calculate polygon perimeter"""
        if len(coordinates) < 2:
            return 0.0
        
        perimeter = 0.0
        for i in range(len(coordinates) - 1):
            distance = self.calculate_distance(coordinates[i], coordinates[i + 1], 'utm')
            perimeter += distance
        
        # Close the polygon if needed
        if coordinates[0] != coordinates[-1]:
            distance = self.calculate_distance(coordinates[-1], coordinates[0], 'utm')
            perimeter += distance
        
        return perimeter
    
    def _calculate_centroid(self, coordinates: List[Tuple[float, float]]) -> Tuple[float, float]:
        """Calculate polygon centroid"""
        if not coordinates:
            return (0.0, 0.0)
        
        x_sum = sum(coord[0] for coord in coordinates)
        y_sum = sum(coord[1] for coord in coordinates)
        
        return (x_sum / len(coordinates), y_sum / len(coordinates))

# Singleton instance
_measurement_client = None

def get_measurement_client() -> InteractiveMeasurementClient:
    """Get singleton measurement client instance"""
    global _measurement_client
    if _measurement_client is None:
        _measurement_client = InteractiveMeasurementClient()
    return _measurement_client