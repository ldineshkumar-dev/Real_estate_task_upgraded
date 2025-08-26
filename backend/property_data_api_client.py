"""
Property Data API Client
Based on comprehensive ArcGIS research for individual property dimensions
Implements standard Ontario municipal property data patterns
"""

import requests
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlencode
import time

logger = logging.getLogger(__name__)

class PropertyDataAPIClient:
    """
    Multi-source property data client following Ontario municipal standards
    Based on research from ArcGIS documentation and municipal GIS patterns
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PropertyDataClient/1.0',
            'Accept': 'application/json'
        })
        
        # Standard field mappings based on Ontario municipal GIS patterns
        self.standard_fields = {
            'lot_area': ['SiteArea', 'LOT_AREA', 'AREA', 'Shape__Area', 'PARCEL_AREA'],
            'frontage': ['Frontage', 'FRONTAGE', 'LOT_FRONTAGE', 'FRONT'],
            'depth': ['Depth', 'DEPTH', 'LOT_DEPTH'],
            'address': ['ADDRESS', 'FULL_ADDRESS', 'CIVIC_ADDRESS'],
            'roll_number': ['ROLL_NUMBER', 'ARN', 'ASSESSMENT_ROLL'],
            'unit_measure': ['Unit_of_Measure', 'UNIT', 'UOM']
        }
        
        # Known working endpoints from research
        self.endpoints = {
            'oakville_zoning': 'https://maps.oakville.ca/oakgis/rest/services/SBS/Zoning_By_law_2014_014/FeatureServer/10/query',
            'oakville_assessment': 'https://maps.oakville.ca/oakgis/rest/services/SBS/Assessment_Parcels/FeatureServer/0/query',
            'ontario_example': 'https://ws.lioservices.lrc.gov.on.ca/arcgis2/rest/services/MOI/Property_Parcels_Public/MapServer/0/query'
        }
    
    def _make_request(self, url: str, params: Dict[str, Any]) -> Optional[Dict]:
        """Make standardized API request with error handling"""
        try:
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 403:
                logger.warning(f"Access forbidden (403) for {url}")
                return {'error': 'access_forbidden', 'code': 403}
            elif response.status_code != 200:
                logger.error(f"HTTP {response.status_code}: {response.text[:200]}")
                return None
            
            data = response.json()
            
            if 'error' in data:
                logger.error(f"API Error: {data['error']}")
                return data  # Return error for analysis
            
            return data
            
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None
    
    def _extract_property_dimensions(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract property dimensions using standard field mapping patterns
        Based on research of Ontario municipal GIS schemas
        """
        result = {
            'lot_area': None,
            'lot_area_units': None,
            'frontage': None,
            'frontage_units': None,
            'depth': None,
            'depth_units': None,
            'address': None,
            'roll_number': None,
            'data_source': 'property_api',
            'fields_found': []
        }
        
        # Extract lot area using multiple possible field names
        for field_name in self.standard_fields['lot_area']:
            if field_name in attributes and attributes[field_name] is not None:
                value = attributes[field_name]
                if isinstance(value, (int, float)) and value > 0:
                    result['lot_area'] = float(value)
                    result['fields_found'].append(f'lot_area:{field_name}')
                    break
        
        # Extract frontage
        for field_name in self.standard_fields['frontage']:
            if field_name in attributes and attributes[field_name] is not None:
                value = attributes[field_name]
                if isinstance(value, (int, float)) and value > 0:
                    result['frontage'] = float(value)
                    result['fields_found'].append(f'frontage:{field_name}')
                    break
        
        # Extract depth  
        for field_name in self.standard_fields['depth']:
            if field_name in attributes and attributes[field_name] is not None:
                value = attributes[field_name]
                if isinstance(value, (int, float)) and value > 0:
                    result['depth'] = float(value)
                    result['fields_found'].append(f'depth:{field_name}')
                    break
        
        # Extract address
        for field_name in self.standard_fields['address']:
            if field_name in attributes and attributes[field_name]:
                result['address'] = str(attributes[field_name])
                result['fields_found'].append(f'address:{field_name}')
                break
        
        # Extract roll number
        for field_name in self.standard_fields['roll_number']:
            if field_name in attributes and attributes[field_name]:
                result['roll_number'] = str(attributes[field_name])
                result['fields_found'].append(f'roll_number:{field_name}')
                break
        
        # Extract units of measurement
        for field_name in self.standard_fields['unit_measure']:
            if field_name in attributes and attributes[field_name]:
                unit = str(attributes[field_name]).upper()
                if 'M' in unit or 'METER' in unit:
                    result['lot_area_units'] = 'm²'
                    result['frontage_units'] = 'm'
                    result['depth_units'] = 'm'
                elif 'FT' in unit or 'FEET' in unit:
                    result['lot_area_units'] = 'sq ft'
                    result['frontage_units'] = 'ft'
                    result['depth_units'] = 'ft'
                break
        
        # Default to metric if not specified
        if not result['lot_area_units']:
            result['lot_area_units'] = 'm²'
            result['frontage_units'] = 'm'
            result['depth_units'] = 'm'
        
        return result
    
    def test_oakville_assessment_parcels(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Test Oakville Assessment Parcels endpoint for property-specific data
        Based on research findings about potential property dimension sources
        """
        result = {
            'success': False,
            'endpoint': 'oakville_assessment_parcels',
            'coordinates': (lat, lon),
            'data_source': 'assessment_api_test'
        }
        
        # Standard ArcGIS spatial query parameters
        params = {
            'where': '1=1',
            'outFields': '*',  # Get all fields to see what's available
            'geometry': f'{lon},{lat}',
            'geometryType': 'esriGeometryPoint',
            'inSR': '4326',
            'spatialRel': 'esriSpatialRelIntersects',
            'returnGeometry': 'true',  # Get geometry for area calculation
            'f': 'json'
        }
        
        url = self.endpoints['oakville_assessment']
        logger.info(f"Testing Oakville Assessment Parcels API: {lat}, {lon}")
        
        data = self._make_request(url, params)
        
        if not data:
            result['error'] = 'request_failed'
            return result
        
        if 'error' in data:
            result['error'] = data['error']
            result['error_details'] = data
            return result
        
        if not data.get('features'):
            result['error'] = 'no_features_found'
            return result
        
        # Process the first feature
        feature = data['features'][0]
        attributes = feature['attributes']
        geometry = feature.get('geometry', {})
        
        # Extract property dimensions using standard patterns
        dimensions = self._extract_property_dimensions(attributes)
        
        # Calculate area from geometry if not in attributes
        if not dimensions['lot_area'] and geometry.get('rings'):
            calculated_area = self._calculate_polygon_area(geometry['rings'])
            if calculated_area > 0:
                dimensions['lot_area'] = calculated_area
                dimensions['fields_found'].append('geometry_calculated_area')
        
        result.update({
            'success': True,
            'property_dimensions': dimensions,
            'raw_attributes': attributes,
            'geometry': geometry,
            'available_fields': list(attributes.keys()),
            'dimension_fields_found': dimensions['fields_found']
        })
        
        logger.info(f"Assessment parcels query successful. Found {len(dimensions['fields_found'])} dimension fields")
        return result
    
    def _calculate_polygon_area(self, rings: List[List[List[float]]]) -> float:
        """
        Calculate polygon area from coordinate rings (Shoelace formula)
        For when area isn't provided as attribute but geometry is available
        """
        if not rings or not rings[0]:
            return 0.0
        
        coords = rings[0]  # Use exterior ring
        if len(coords) < 3:
            return 0.0
        
        # Shoelace formula for polygon area
        area = 0.0
        n = len(coords)
        
        for i in range(n):
            j = (i + 1) % n
            area += coords[i][0] * coords[j][1]
            area -= coords[j][0] * coords[i][1]
        
        return abs(area) / 2.0
    
    def search_property_by_address(self, address: str) -> Dict[str, Any]:
        """
        Search for property by address across multiple potential endpoints
        Implements the multi-source strategy from research
        """
        result = {
            'success': False,
            'address': address,
            'search_attempts': [],
            'data_source': 'address_search'
        }
        
        # Clean address for search
        clean_address = address.upper().strip()
        search_terms = [
            clean_address,
            clean_address.replace(' AVENUE', ' AVE'),
            clean_address.replace(' STREET', ' ST'),
            clean_address.replace(' ROAD', ' RD')
        ]
        
        for endpoint_name, endpoint_url in self.endpoints.items():
            if 'oakville' not in endpoint_name:
                continue  # Skip non-Oakville endpoints for address search
            
            for search_term in search_terms:
                logger.info(f"Searching {endpoint_name} for: {search_term}")
                
                params = {
                    'where': f"UPPER(ADDRESS) LIKE '%{search_term}%' OR UPPER(FULL_ADDRESS) LIKE '%{search_term}%'",
                    'outFields': '*',
                    'returnGeometry': 'true',
                    'f': 'json'
                }
                
                attempt_result = {
                    'endpoint': endpoint_name,
                    'search_term': search_term,
                    'success': False
                }
                
                data = self._make_request(endpoint_url, params)
                
                if data and data.get('features'):
                    feature = data['features'][0]
                    attributes = feature['attributes']
                    geometry = feature.get('geometry', {})
                    
                    # Extract property dimensions
                    dimensions = self._extract_property_dimensions(attributes)
                    
                    attempt_result.update({
                        'success': True,
                        'property_dimensions': dimensions,
                        'raw_attributes': attributes,
                        'geometry': geometry
                    })
                    
                    result.update({
                        'success': True,
                        'found_endpoint': endpoint_name,
                        'property_data': attempt_result
                    })
                    
                    logger.info(f"Found property in {endpoint_name}: {dimensions['address']}")
                    return result
                
                result['search_attempts'].append(attempt_result)
        
        logger.warning(f"Property not found in any endpoint: {address}")
        return result
    
    def get_comprehensive_property_data(self, address: str, lat: float = None, lon: float = None) -> Dict[str, Any]:
        """
        Get comprehensive property data using all available methods
        Implements the complete multi-source strategy from research
        """
        result = {
            'success': False,
            'address': address,
            'coordinates': (lat, lon) if lat and lon else None,
            'data_sources_attempted': [],
            'property_dimensions': None,
            'zoning_data': None,
            'final_data_source': None
        }
        
        # Method 1: Address search across endpoints
        if address:
            logger.info("Attempting property lookup by address")
            address_result = self.search_property_by_address(address)
            result['data_sources_attempted'].append('address_search')
            
            if address_result['success']:
                result.update({
                    'success': True,
                    'property_dimensions': address_result['property_data']['property_dimensions'],
                    'final_data_source': f"address_search_{address_result['found_endpoint']}",
                    'raw_data': address_result
                })
                
                # Also get coordinates from the found data
                geometry = address_result['property_data'].get('geometry', {})
                if geometry.get('rings'):
                    # Calculate centroid for zoning lookup
                    rings = geometry['rings'][0]
                    x_coords = [point[0] for point in rings]
                    y_coords = [point[1] for point in rings]
                    lat = sum(y_coords) / len(y_coords)
                    lon = sum(x_coords) / len(x_coords)
                    result['coordinates'] = (lat, lon)
        
        # Method 2: Coordinate-based search if coordinates available
        if lat and lon and not result['success']:
            logger.info(f"Attempting property lookup by coordinates: {lat}, {lon}")
            coord_result = self.test_oakville_assessment_parcels(lat, lon)
            result['data_sources_attempted'].append('coordinate_assessment_search')
            
            if coord_result['success']:
                result.update({
                    'success': True,
                    'property_dimensions': coord_result['property_dimensions'],
                    'final_data_source': 'coordinate_assessment_search',
                    'raw_data': coord_result
                })
        
        # Method 3: Get zoning data (always attempt if coordinates available)
        if result.get('coordinates'):
            from backend.oakville_real_api_client import get_oakville_real_api_client
            
            zoning_client = get_oakville_real_api_client()
            zoning_result = zoning_client.get_zoning_data(result['coordinates'][0], result['coordinates'][1])
            
            if zoning_result['success']:
                result['zoning_data'] = zoning_result
                result['data_sources_attempted'].append('zoning_api')
        
        # Compile final summary
        if result['success']:
            dimensions = result['property_dimensions']
            logger.info(f"Property data found via {result['final_data_source']}")
            logger.info(f"Dimensions: Area={dimensions.get('lot_area')}, Frontage={dimensions.get('frontage')}, Depth={dimensions.get('depth')}")
        else:
            logger.warning(f"No property data found for {address} at {lat}, {lon}")
        
        return result

# Singleton instance
_property_api_client = None

def get_property_data_api_client() -> PropertyDataAPIClient:
    """Get singleton property data API client"""
    global _property_api_client
    if _property_api_client is None:
        _property_api_client = PropertyDataAPIClient()
    return _property_api_client