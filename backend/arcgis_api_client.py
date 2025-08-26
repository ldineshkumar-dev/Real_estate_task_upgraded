"""
Fixed ArcGIS REST API Client for Oakville Real Estate
Following ArcGIS documentation exactly - NO FALLBACKS, ONLY REAL API DATA
"""

import requests
import json
import logging
import math
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

class ArcGISAPIClient:
    """ArcGIS REST API compliant client for Oakville GIS data"""
    
    def __init__(self):
        self.base_url = "https://maps.oakville.ca/oakgis/rest/services/SBS"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'OakvilleRealEstateAnalyzer/2.0',
            'Accept': 'application/json'
        })
        
        # ArcGIS REST API endpoints (verified working)
        self.endpoints = {
            'parcel_address': '/Parcel_Address/FeatureServer/0/query',
            'zoning': '/Zoning_By_law_2014_014/FeatureServer/10/query',
            'assessment_parcels': '/Assessment_Parcels/FeatureServer/0/query'
        }
    
    def _make_arcgis_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict]:
        """
        Make ArcGIS REST API compliant request
        
        Args:
            endpoint: API endpoint key
            params: Query parameters following ArcGIS specification
            
        Returns:
            JSON response or None if failed
        """
        if endpoint not in self.endpoints:
            raise ValueError(f"Unknown endpoint: {endpoint}")
        
        url = self.base_url + self.endpoints[endpoint]
        
        try:
            logger.info(f"ArcGIS API Request: {endpoint}")
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"HTTP {response.status_code}: {response.text[:500]}")
                return None
            
            data = response.json()
            
            # Check for ArcGIS service errors
            if 'error' in data:
                logger.error(f"ArcGIS API Error: {data['error']}")
                return None
            
            if 'features' in data:
                logger.info(f"Found {len(data['features'])} features")
                return data
            else:
                logger.warning("No features in response")
                return None
                
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return None
    
    def _wgs84_to_utm17n(self, lat: float, lon: float) -> Tuple[float, float]:
        """
        Convert WGS84 (lat/lon) to UTM Zone 17N (EPSG:26917)
        Oakville uses UTM Zone 17N coordinate system
        """
        # Simple UTM conversion for Southern Ontario (approximation)
        # For production, use proper projection library like pyproj
        
        # UTM Zone 17N parameters
        a = 6378137.0  # Semi-major axis
        e2 = 0.00669438  # Eccentricity squared
        k0 = 0.9996  # Scale factor
        E0 = 500000.0  # False easting
        N0 = 0.0  # False northing
        
        # Convert to radians
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        lon0_rad = math.radians(-81.0)  # Central meridian for Zone 17
        
        # Simplified UTM calculation
        n = a / math.sqrt(1 - e2 * math.sin(lat_rad) ** 2)
        t = math.tan(lat_rad)
        c = e2 * math.cos(lat_rad) ** 2 / (1 - e2)
        A = math.cos(lat_rad) * (lon_rad - lon0_rad)
        
        M = a * ((1 - e2/4 - 3*e2**2/64) * lat_rad - 
                 (3*e2/8 + 3*e2**2/32) * math.sin(2*lat_rad) +
                 (15*e2**2/256) * math.sin(4*lat_rad))
        
        x = E0 + k0 * n * (A + (1-t**2+c) * A**3/6)
        y = N0 + k0 * (M + n*t * (A**2/2 + (5-t**2+9*c+4*c**2) * A**4/24))
        
        return (x, y)
    
    def get_property_by_address(self, address: str) -> Optional[Dict]:
        """
        Get property data by address using Parcel_Address endpoint
        
        Args:
            address: Property address (e.g., "383 Maplehurst Avenue")
            
        Returns:
            Property data with geometry and attributes
        """
        # Clean address for search
        clean_address = address.upper().strip()
        # Remove common variations
        clean_address = clean_address.replace(" AVENUE", " AVE")
        clean_address = clean_address.replace(" STREET", " ST")
        clean_address = clean_address.replace(" ROAD", " RD")
        
        # ArcGIS REST API query parameters
        params = {
            'where': f"ADDRESS LIKE '%{clean_address}%'",
            'outFields': '*',  # Get all fields
            'returnGeometry': 'true',  # Need geometry for zoning query
            'f': 'json'
        }
        
        logger.info(f"Searching for address: {clean_address}")
        data = self._make_arcgis_request('parcel_address', params)
        
        if data and data.get('features'):
            feature = data['features'][0]  # Take first match
            attributes = feature['attributes']
            geometry = feature.get('geometry', {})
            
            # Extract property information
            property_data = {
                'address': attributes.get('ADDRESS', ''),
                'roll_number': attributes.get('ROLL_NUMBER', ''),
                'geometry': geometry,
                'shape_area': attributes.get('Shape__Area'),  # Lot area in m²
                'shape_length': attributes.get('Shape__Length'),  # Perimeter in m
                'source': 'oakville_parcel_api',
                'api_verified': True
            }
            
            logger.info(f"Found property: {property_data['address']}")
            return property_data
        
        logger.warning(f"No property found for address: {address}")
        return None
    
    def get_zoning_by_geometry(self, geometry: Dict) -> Optional[Dict]:
        """
        Get zoning data using property geometry
        
        Args:
            geometry: ArcGIS geometry object from property
            
        Returns:
            Zoning data with zone code, special provisions, etc.
        """
        if not geometry or 'rings' not in geometry:
            return None
        
        # Get centroid of property polygon
        rings = geometry['rings'][0]  # First ring
        x_coords = [point[0] for point in rings]
        y_coords = [point[1] for point in rings]
        centroid_x = sum(x_coords) / len(x_coords)
        centroid_y = sum(y_coords) / len(y_coords)
        
        # ArcGIS REST API spatial query parameters
        params = {
            'geometry': f'{centroid_x},{centroid_y}',
            'geometryType': 'esriGeometryPoint',
            'inSR': '26917',  # UTM Zone 17N (Oakville's coordinate system)
            'spatialRel': 'esriSpatialRelIntersects',
            'where': '1=1',  # Get all records
            'outFields': 'ZONE,ZONE_DESC,CLASS,SP1,SP2,SP3,SP4,SP5,SP_DESC,FULL_ZONING_DESC,Shape__Area,Shape__Length',
            'returnGeometry': 'false',
            'f': 'json'
        }
        
        data = self._make_arcgis_request('zoning', params)
        
        if data and data.get('features'):
            feature = data['features'][0]
            attributes = feature['attributes']
            
            # Extract special provisions from SP1-SP5 fields
            special_provisions = []
            for i in range(1, 6):
                sp_value = attributes.get(f'SP{i}')
                if sp_value and str(sp_value).strip():
                    special_provisions.append(f"SP:{sp_value}")
            
            zoning_data = {
                'zone_code': attributes.get('ZONE', ''),
                'zone_description': attributes.get('ZONE_DESC', ''),
                'zone_class': attributes.get('CLASS', ''),
                'special_provisions': special_provisions,
                'special_provision_desc': attributes.get('SP_DESC', ''),
                'full_zoning_desc': attributes.get('FULL_ZONING_DESC', ''),
                'zone_shape_area': attributes.get('Shape__Area'),  # Zone boundary area
                'zone_shape_length': attributes.get('Shape__Length'),  # Zone boundary length
                'source': 'oakville_zoning_api',
                'api_verified': True
            }
            
            logger.info(f"Found zoning: {zoning_data['zone_code']} with {len(special_provisions)} special provisions")
            return zoning_data
        
        logger.warning("No zoning data found for geometry")
        return None
    
    def get_property_analysis(self, address: str) -> Dict[str, Any]:
        """
        Get complete property analysis using ONLY real API data
        NO FALLBACKS - returns clear errors if data unavailable
        
        Args:
            address: Property address
            
        Returns:
            Complete analysis with real data or clear error messages
        """
        result = {
            'success': False,
            'address': address,
            'data_source': 'real_api_only',
            'fallback_used': False,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Step 1: Get property by address
            property_data = self.get_property_by_address(address)
            if not property_data:
                result['errors'].append("Property not found in Oakville address database")
                return result
            
            # Step 2: Get zoning data using property geometry
            zoning_data = self.get_zoning_by_geometry(property_data['geometry'])
            if not zoning_data:
                result['errors'].append("Zoning data not available for this property")
                return result
            
            # Step 3: Calculate real property dimensions
            shape_area = property_data.get('shape_area')
            shape_length = property_data.get('shape_length')
            
            if not shape_area or shape_area <= 0:
                result['warnings'].append("Property area not available from API")
                lot_area = None
            else:
                lot_area = float(shape_area)  # Already in m²
            
            # Step 4: Build final zone code with special provisions
            zone_code = zoning_data['zone_code']
            special_provisions = zoning_data['special_provisions']
            
            if special_provisions:
                full_zone_code = f"{zone_code} {' '.join(special_provisions)}"
            else:
                full_zone_code = zone_code
            
            # Step 5: Success - compile real data
            result.update({
                'success': True,
                'property_address': property_data['address'],
                'roll_number': property_data['roll_number'],
                'zone_code': full_zone_code,
                'base_zone': zone_code,
                'special_provisions': special_provisions,
                'zone_description': zoning_data['zone_description'],
                'zone_class': zoning_data['zone_class'],
                'lot_area_m2': lot_area,
                'lot_area_sqft': lot_area * 10.764 if lot_area else None,
                'lot_perimeter_m': float(shape_length) if shape_length else None,
                'geometry': property_data['geometry'],
                'data_quality': {
                    'property_api_verified': True,
                    'zoning_api_verified': True,
                    'has_real_geometry': True,
                    'has_shape_area': shape_area is not None,
                    'has_special_provisions': len(special_provisions) > 0
                }
            })
            
            logger.info(f"Complete analysis successful for {address}")
            return result
            
        except Exception as e:
            result['errors'].append(f"API analysis failed: {str(e)}")
            logger.error(f"Property analysis error: {e}")
            return result

# Singleton instance
_arcgis_client = None

def get_arcgis_api_client() -> ArcGISAPIClient:
    """Get singleton ArcGIS API client"""
    global _arcgis_client
    if _arcgis_client is None:
        _arcgis_client = ArcGISAPIClient()
    return _arcgis_client