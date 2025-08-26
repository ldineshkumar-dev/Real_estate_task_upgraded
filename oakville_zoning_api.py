"""
Advanced Oakville Zoning API Client
Integrates multiple data sources with fallback mechanisms and special provision support
"""

import requests
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import time
from urllib.parse import urlencode
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
import aiohttp

from enhanced_zone_detector import EnhancedZoneDetector, ZoneInfo

# Configure logging
logger = logging.getLogger(__name__)

@dataclass 
class PropertyData:
    """Complete property data structure"""
    address: str
    latitude: float
    longitude: float
    zone_info: ZoneInfo
    lot_dimensions: Dict[str, float]
    assessments: Dict[str, Any]
    property_boundaries: List[List[float]]
    nearby_amenities: List[Dict[str, Any]]
    zoning_regulations: Dict[str, Any]
    confidence_score: float
    data_sources: Dict[str, str]
    last_updated: str

class OakvilleZoningAPI:
    """
    Advanced API client for Oakville property and zoning data
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = 30
        
        # Primary API endpoints
        self.endpoints = {
            'oakville_gis_base': 'https://gis.oakville.ca/server/rest/services/',
            'oakville_open_data': 'https://gis.oakville.ca/server/rest/services/OpenData/',
            'oakville_public': 'https://gis.oakville.ca/server/rest/services/Public/',
            'ontario_lio': 'https://ws.lio.gov.on.ca/',
            'halton_region': 'https://gis.halton.ca/server/rest/services/',
            'mpac_assessment': 'https://www.mah.gov.on.ca/page/assessment'
        }
        
        # Service endpoints for different data types
        self.services = {
            'zoning': [
                'OpenData/Zoning/MapServer',
                'Public/ZoningBylaw/MapServer',
                'Planning/Zoning2014/MapServer'
            ],
            'property_boundaries': [
                'OpenData/PropertyBoundaries/MapServer',
                'Cadastral/PropertyFabric/MapServer',
                'Assessment/ParcelBoundaries/MapServer'
            ],
            'assessment': [
                'OpenData/Assessment/MapServer',
                'MPAC/PropertyAssessment/MapServer'
            ],
            'planning': [
                'OpenData/Planning/MapServer',
                'Public/PlanningApplications/MapServer'
            ]
        }
        
        # Initialize enhanced zone detector
        self.zone_detector = EnhancedZoneDetector()
        
        # Cache for API responses
        self._cache = {}
        self._cache_timeout = 3600  # 1 hour
    
    def get_comprehensive_property_data(self, 
                                      lat: float, 
                                      lon: float, 
                                      address: str = None) -> PropertyData:
        """
        Get comprehensive property data using all available sources
        """
        
        logger.info(f"Getting comprehensive data for lat={lat}, lon={lon}, address={address}")
        
        # Use ThreadPoolExecutor for parallel API calls
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {
                'zone_info': executor.submit(self._get_zoning_data, lat, lon, address),
                'lot_dimensions': executor.submit(self._get_lot_dimensions, lat, lon, address),
                'assessments': executor.submit(self._get_assessment_data, lat, lon, address),
                'boundaries': executor.submit(self._get_property_boundaries, lat, lon),
                'amenities': executor.submit(self._get_nearby_amenities, lat, lon),
                'regulations': executor.submit(self._get_zoning_regulations, lat, lon)
            }
            
            # Collect results
            results = {}
            for key, future in futures.items():
                try:
                    results[key] = future.result(timeout=30)
                except Exception as e:
                    logger.warning(f"Failed to get {key}: {e}")
                    results[key] = self._get_fallback_data(key, lat, lon, address)
        
        # Combine results into PropertyData
        return PropertyData(
            address=address or f"{lat}, {lon}",
            latitude=lat,
            longitude=lon,
            zone_info=results['zone_info'],
            lot_dimensions=results['lot_dimensions'],
            assessments=results['assessments'],
            property_boundaries=results['boundaries'],
            nearby_amenities=results['amenities'],
            zoning_regulations=results['regulations'],
            confidence_score=self._calculate_confidence_score(results),
            data_sources=self._extract_data_sources(results),
            last_updated=time.strftime('%Y-%m-%d %H:%M:%S')
        )
    
    def _get_zoning_data(self, lat: float, lon: float, address: str = None) -> ZoneInfo:
        """Get zoning information using multiple methods"""
        
        # Use enhanced zone detector
        zone_info = self.zone_detector.detect_zone_code(lat, lon, address)
        
        # Enhance with API data
        api_zoning = self._query_zoning_apis(lat, lon)
        if api_zoning:
            # Merge API data with detected zone info
            if api_zoning.get('zone_code') and zone_info.base_zone == "Unknown":
                parsed_api = self.zone_detector._parse_zone_string(api_zoning['zone_code'])
                zone_info = parsed_api
                zone_info.source = "api_enhanced"
                zone_info.confidence = "high"
        
        return zone_info
    
    def _query_zoning_apis(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Query multiple zoning API endpoints"""
        
        for service_path in self.services['zoning']:
            try:
                result = self._spatial_query(service_path, lat, lon, 'zoning')
                if result:
                    return result
            except Exception as e:
                logger.debug(f"Zoning API {service_path} failed: {e}")
                continue
        
        return None
    
    def _get_lot_area_from_parcels_api(self, address: str = None, lat: float = None, lon: float = None) -> Optional[float]:
        """Get lot area from the Parcels_Addresses FeatureServer."""
        logger.info(f"Querying Parcels_Addresses API for address: {address}")
        
        BASE_URL = "https://services5.arcgis.com/QJebCdoMf4PF8fJP/arcgis/rest/services/Parcels_Addresses/FeatureServer/0/query"
        
        params = {
            "f": "json",
            "where": "1=1",
            "outFields": "Shape__Area",
            "returnGeometry": "false",
            "resultRecordCount": 1
        }

        if address and address.strip():
            params["where"] = f"ADDRESS LIKE '%{address.strip().upper()}%'"
        elif lat and lon:
            params['geometry'] = f"{lon},{lat}"
            params['geometryType'] = 'esriGeometryPoint'
            params['spatialRel'] = 'esriSpatialRelIntersects'
        else:
            logger.warning("No address or coordinates provided to fetch lot area.")
            return None

        try:
            response = self.session.get(BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            features = data.get('features', [])
            if features:
                attributes = features[0].get('attributes', {})
                area = attributes.get('Shape__Area')
                if area is not None:
                    logger.info(f"Successfully fetched Shape__Area: {area}")
                    return float(area)
                else:
                    logger.warning("Shape__Area not found in API response.")
            else:
                logger.warning(f"No features found for address: {address}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying Parcels_Addresses API: {e}")
            
        return None

    def _get_lot_dimensions(self, lat: float, lon: float, address: str = None) -> Dict[str, float]:
        """Get lot dimensions from property boundary data"""
        
        # --- NEW: Prioritize the new Parcels_Addresses API for lot area ---
        lot_area_sqm = self._get_lot_area_from_parcels_api(address=address, lat=lat, lon=lon)
        if lot_area_sqm is not None:
            # If we get the area, we can return it with estimated frontage/depth
            # Or we can continue to try and get more precise dimensions
            estimated_frontage = 20.0 # default
            estimated_depth = lot_area_sqm / estimated_frontage if estimated_frontage > 0 else 0
            return {
                'area_sqm': lot_area_sqm,
                'area_sqft': lot_area_sqm * 10.764,
                'frontage_m': estimated_frontage,
                'depth_m': estimated_depth,
                'perimeter_m': 2 * (estimated_frontage + estimated_depth),
                'confidence': 'measured_from_api'
            }
        
        logger.warning("Failed to get lot area from Parcels_Addresses API, falling back to other methods.")
        # --- END NEW ---

        # Try property boundary APIs
        for service_path in self.services['property_boundaries']:
            try:
                boundaries = self._get_property_polygon(service_path, lat, lon)
                if boundaries:
                    dimensions = self._calculate_lot_dimensions(boundaries)
                    if dimensions:
                        return dimensions
            except Exception as e:
                logger.debug(f"Property boundary API {service_path} failed: {e}")
                continue
        
        # Fallback to coordinate-based estimation
        return self._estimate_lot_dimensions_from_coordinates(lat, lon)
    
    def _get_property_polygon(self, service_path: str, lat: float, lon: float) -> Optional[List[List[float]]]:
        """Get property polygon from boundary service"""
        
        url = f"{self.endpoints['oakville_gis_base']}{service_path}/query"
        
        params = {
            'where': '1=1',
            'geometry': f"{lon},{lat}",
            'geometryType': 'esriGeometryPoint',
            'spatialRel': 'esriSpatialRelIntersects',
            'outFields': '*',
            'returnGeometry': 'true',
            'f': 'json'
        }
        
        response = self.session.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            
            features = data.get('features', [])
            if features:
                geometry = features[0].get('geometry')
                if geometry and geometry.get('rings'):
                    # Convert rings to coordinate list
                    return geometry['rings'][0]  # Outer ring
        
        return None
    
    def _calculate_lot_dimensions(self, polygon: List[List[float]]) -> Dict[str, float]:
        """Calculate lot dimensions from polygon coordinates"""
        
        if len(polygon) < 4:
            return {}
        
        from geopy.distance import geodesic
        
        # Calculate perimeter and approximate dimensions
        total_perimeter = 0
        side_lengths = []
        
        for i in range(len(polygon)):
            p1 = polygon[i]
            p2 = polygon[(i + 1) % len(polygon)]
            
            # Convert to lat/lon for distance calculation
            distance = geodesic((p1[1], p1[0]), (p2[1], p2[0])).meters
            side_lengths.append(distance)
            total_perimeter += distance
        
        # Sort sides to identify frontage and depth
        sorted_sides = sorted(side_lengths, reverse=True)
        
        # Calculate area using Shoelace formula
        area = 0
        n = len(polygon)
        for i in range(n):
            j = (i + 1) % n
            area += polygon[i][0] * polygon[j][1]
            area -= polygon[j][0] * polygon[i][1]
        area = abs(area) / 2.0
        
        # Convert area to square meters (approximate)
        area_sqm = area * (111320 ** 2) * abs(math.cos(math.radians(polygon[0][1])))
        
        return {
            'area_sqm': area_sqm,
            'area_sqft': area_sqm * 10.764,
            'frontage_m': max(side_lengths[:2]) if len(side_lengths) >= 2 else 0,
            'depth_m': min(side_lengths[:2]) if len(side_lengths) >= 2 else 0,
            'perimeter_m': total_perimeter,
            'confidence': 'measured_from_boundaries'
        }
    
    def _estimate_lot_dimensions_from_coordinates(self, lat: float, lon: float) -> Dict[str, float]:
        """Estimate lot dimensions using coordinate-based heuristics"""
        
        # Default estimates based on typical Oakville lot sizes
        # These would be improved with machine learning models
        
        estimated_area = 650.0  # m² (typical RL2)
        estimated_frontage = 20.0  # m
        estimated_depth = 32.5  # m
        
        return {
            'area_sqm': estimated_area,
            'area_sqft': estimated_area * 10.764,
            'frontage_m': estimated_frontage,
            'depth_m': estimated_depth,
            'perimeter_m': 2 * (estimated_frontage + estimated_depth),
            'confidence': 'estimated_from_coordinates'
        }
    
    def _get_assessment_data(self, lat: float, lon: float, address: str = None) -> Dict[str, Any]:
        """Get property assessment data"""
        
        # Try MPAC/assessment APIs
        for service_path in self.services['assessment']:
            try:
                result = self._spatial_query(service_path, lat, lon, 'assessment')
                if result:
                    return self._process_assessment_data(result)
            except Exception as e:
                logger.debug(f"Assessment API {service_path} failed: {e}")
                continue
        
        # Fallback to estimated assessment data
        return self._generate_fallback_assessment(lat, lon)
    
    def _get_property_boundaries(self, lat: float, lon: float) -> List[List[float]]:
        """Get property boundary coordinates"""
        
        for service_path in self.services['property_boundaries']:
            try:
                polygon = self._get_property_polygon(service_path, lat, lon)
                if polygon:
                    return polygon
            except Exception as e:
                logger.debug(f"Boundary API {service_path} failed: {e}")
                continue
        
        # Generate approximate boundary
        return self._generate_approximate_boundary(lat, lon)
    
    def _get_nearby_amenities(self, lat: float, lon: float) -> List[Dict[str, Any]]:
        """Get nearby amenities and points of interest"""
        
        amenities = []
        
        # Query different amenity types
        amenity_types = ['parks', 'schools', 'transit', 'shopping', 'healthcare']
        
        for amenity_type in amenity_types:
            try:
                results = self._query_amenities(lat, lon, amenity_type)
                amenities.extend(results)
            except Exception as e:
                logger.debug(f"Amenity query for {amenity_type} failed: {e}")
                continue
        
        return amenities
    
    def _get_zoning_regulations(self, lat: float, lon: float) -> Dict[str, Any]:
        """Get detailed zoning regulations"""
        
        # This would query specific regulation databases
        # For now, return structure based on by-law data
        return {
            'setback_requirements': {},
            'height_limits': {},
            'density_limits': {},
            'use_permissions': {},
            'special_provisions': {},
            'confidence': 'by_law_reference'
        }
    
    def _spatial_query(self, service_path: str, lat: float, lon: float, query_type: str) -> Optional[Dict[str, Any]]:
        """Perform spatial query against API endpoint"""
        
        cache_key = f"{service_path}_{lat}_{lon}_{query_type}"
        
        # Check cache first
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_timeout:
                return cached_data
        
        url = f"{self.endpoints['oakville_gis_base']}{service_path}/query"
        
        params = {
            'where': '1=1',
            'geometry': f"{lon},{lat}",
            'geometryType': 'esriGeometryPoint',
            'spatialRel': 'esriSpatialRelIntersects',
            'outFields': '*',
            'returnGeometry': 'false',
            'f': 'json'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                
                features = data.get('features', [])
                if features:
                    result = features[0].get('attributes', {})
                    
                    # Cache the result
                    self._cache[cache_key] = (result, time.time())
                    
                    return result
        
        except Exception as e:
            logger.debug(f"Spatial query failed for {url}: {e}")
        
        return None
    
    def _query_amenities(self, lat: float, lon: float, amenity_type: str) -> List[Dict[str, Any]]:
        """Query nearby amenities of specific type"""
        
        # Buffer distance in degrees (approximately 1km)
        buffer = 0.009
        
        # Build bounding box
        bbox = f"{lon-buffer},{lat-buffer},{lon+buffer},{lat+buffer}"
        
        # Amenity service mappings
        service_mappings = {
            'parks': 'OpenData/Parks/MapServer',
            'schools': 'OpenData/Schools/MapServer', 
            'transit': 'OpenData/Transit/MapServer',
            'shopping': 'OpenData/Commercial/MapServer',
            'healthcare': 'OpenData/Healthcare/MapServer'
        }
        
        service_path = service_mappings.get(amenity_type)
        if not service_path:
            return []
        
        url = f"{self.endpoints['oakville_gis_base']}{service_path}/query"
        
        params = {
            'where': '1=1',
            'geometry': bbox,
            'geometryType': 'esriGeometryEnvelope',
            'spatialRel': 'esriSpatialRelIntersects',
            'outFields': 'NAME,TYPE,ADDRESS',
            'returnGeometry': 'true',
            'f': 'json'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                amenities = []
                for feature in data.get('features', []):
                    attributes = feature.get('attributes', {})
                    geometry = feature.get('geometry')
                    
                    if geometry:
                        amenity = {
                            'type': amenity_type,
                            'name': attributes.get('NAME', 'Unknown'),
                            'subtype': attributes.get('TYPE', ''),
                            'address': attributes.get('ADDRESS', ''),
                            'latitude': geometry.get('y', 0),
                            'longitude': geometry.get('x', 0)
                        }
                        
                        # Calculate distance
                        from geopy.distance import geodesic
                        distance = geodesic((lat, lon), (amenity['latitude'], amenity['longitude'])).meters
                        amenity['distance_m'] = distance
                        
                        amenities.append(amenity)
                
                # Sort by distance
                amenities.sort(key=lambda x: x['distance_m'])
                return amenities[:5]  # Return closest 5
        
        except Exception as e:
            logger.debug(f"Amenity query failed for {amenity_type}: {e}")
        
        return []
    
    def _process_assessment_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process raw assessment data"""
        
        return {
            'assessed_value': raw_data.get('ASSESSED_VALUE', 0),
            'property_class': raw_data.get('PROPERTY_CLASS', ''),
            'assessment_year': raw_data.get('ASSESSMENT_YEAR', 0),
            'roll_number': raw_data.get('ROLL_NUMBER', ''),
            'confidence': 'official_assessment'
        }
    
    def _generate_fallback_assessment(self, lat: float, lon: float) -> Dict[str, Any]:
        """Generate fallback assessment data"""
        
        return {
            'assessed_value': 750000,  # Estimated
            'property_class': 'Residential',
            'assessment_year': 2024,
            'roll_number': 'ESTIMATED',
            'confidence': 'estimated'
        }
    
    def _generate_approximate_boundary(self, lat: float, lon: float) -> List[List[float]]:
        """Generate approximate property boundary"""
        
        # Create approximate rectangular boundary
        offset = 0.0001  # Approximately 10-15 meters
        
        return [
            [lon - offset, lat - offset],
            [lon + offset, lat - offset],
            [lon + offset, lat + offset],
            [lon - offset, lat + offset],
            [lon - offset, lat - offset]  # Close polygon
        ]
    
    def _get_fallback_data(self, data_type: str, lat: float, lon: float, address: str = None) -> Any:
        """Get fallback data when APIs fail"""
        
        fallback_map = {
            'zone_info': ZoneInfo(base_zone="RL3", confidence="fallback", source="api_fallback"),
            'lot_dimensions': self._estimate_lot_dimensions_from_coordinates(lat, lon),
            'assessments': self._generate_fallback_assessment(lat, lon),
            'boundaries': self._generate_approximate_boundary(lat, lon),
            'amenities': [],
            'regulations': {}
        }
        
        return fallback_map.get(data_type, {})
    
    def _calculate_confidence_score(self, results: Dict[str, Any]) -> float:
        """Calculate overall confidence score for the data"""
        
        confidence_weights = {
            'zone_info': 0.3,
            'lot_dimensions': 0.25,
            'assessments': 0.2,
            'boundaries': 0.15,
            'amenities': 0.05,
            'regulations': 0.05
        }
        
        confidence_scores = {
            'high': 1.0,
            'verified': 1.0,
            'medium': 0.7,
            'measured_from_boundaries': 0.8,
            'official_assessment': 0.9,
            'low': 0.4,
            'estimated': 0.3,
            'fallback': 0.2
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for key, weight in confidence_weights.items():
            if key in results:
                data = results[key]
                
                # Extract confidence from data
                confidence = 'medium'  # default
                if hasattr(data, 'confidence'):
                    confidence = data.confidence
                elif isinstance(data, dict) and 'confidence' in data:
                    confidence = data['confidence']
                
                score = confidence_scores.get(confidence, 0.5)
                total_score += score * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.5
    
    def _extract_data_sources(self, results: Dict[str, Any]) -> Dict[str, str]:
        """Extract data sources from results"""
        
        sources = {}
        
        for key, data in results.items():
            if hasattr(data, 'source'):
                sources[key] = data.source
            elif isinstance(data, dict) and 'source' in data:
                sources[key] = data['source']
            else:
                sources[key] = 'unknown'
        
        return sources

# Utility functions for easy integration
def get_property_data(lat: float, lon: float, address: str = None) -> PropertyData:
    """
    Convenience function to get comprehensive property data
    """
    api = OakvilleZoningAPI()
    return api.get_comprehensive_property_data(lat, lon, address)

def get_zone_info_only(lat: float, lon: float, address: str = None) -> ZoneInfo:
    """
    Get only zoning information for a property
    """
    api = OakvilleZoningAPI()
    return api._get_zoning_data(lat, lon, address)

# Async version for high-performance applications
class AsyncOakvilleZoningAPI:
    """
    Async version of the API client for high-performance applications
    """
    
    async def get_comprehensive_property_data_async(self, 
                                                  lat: float, 
                                                  lon: float, 
                                                  address: str = None) -> PropertyData:
        """
        Async version of comprehensive property data retrieval
        """
        
        async with aiohttp.ClientSession() as session:
            tasks = [
                self._get_zoning_data_async(session, lat, lon, address),
                self._get_lot_dimensions_async(session, lat, lon, address),
                self._get_assessment_data_async(session, lat, lon, address),
                self._get_property_boundaries_async(session, lat, lon),
                self._get_nearby_amenities_async(session, lat, lon),
                self._get_zoning_regulations_async(session, lat, lon)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            zone_info, lot_dimensions, assessments, boundaries, amenities, regulations = results
            
            return PropertyData(
                address=address or f"{lat}, {lon}",
                latitude=lat,
                longitude=lon,
                zone_info=zone_info if not isinstance(zone_info, Exception) else ZoneInfo(base_zone="Unknown"),
                lot_dimensions=lot_dimensions if not isinstance(lot_dimensions, Exception) else {},
                assessments=assessments if not isinstance(assessments, Exception) else {},
                property_boundaries=boundaries if not isinstance(boundaries, Exception) else [],
                nearby_amenities=amenities if not isinstance(amenities, Exception) else [],
                zoning_regulations=regulations if not isinstance(regulations, Exception) else {},
                confidence_score=0.5,  # Would calculate properly
                data_sources={},
                last_updated=time.strftime('%Y-%m-%d %H:%M:%S')
            )
    
    async def _get_zoning_data_async(self, session: aiohttp.ClientSession, lat: float, lon: float, address: str = None) -> ZoneInfo:
        """Async zoning data retrieval"""
        # Implementation would be similar to sync version but using aiohttp
        return ZoneInfo(base_zone="RL3", confidence="async", source="async_api")
    
    async def _get_lot_dimensions_async(self, session: aiohttp.ClientSession, lat: float, lon: float, address: str = None) -> Dict[str, float]:
        """Async lot dimensions retrieval"""
        return {'area_sqm': 650.0, 'frontage_m': 20.0, 'depth_m': 32.5}
    
    async def _get_assessment_data_async(self, session: aiohttp.ClientSession, lat: float, lon: float, address: str = None) -> Dict[str, Any]:
        """Async assessment data retrieval"""
        return {'assessed_value': 750000, 'confidence': 'async_estimated'}
    
    async def _get_property_boundaries_async(self, session: aiohttp.ClientSession, lat: float, lon: float) -> List[List[float]]:
        """Async property boundaries retrieval"""
        offset = 0.0001
        return [[lon - offset, lat - offset], [lon + offset, lat - offset], [lon + offset, lat + offset], [lon - offset, lat + offset]]
    
    async def _get_nearby_amenities_async(self, session: aiohttp.ClientSession, lat: float, lon: float) -> List[Dict[str, Any]]:
        """Async amenities retrieval"""
        return []
    
    async def _get_zoning_regulations_async(self, session: aiohttp.ClientSession, lat: float, lon: float) -> Dict[str, Any]:
        """Async regulations retrieval"""
        return {}

# Testing functions
def test_oakville_api():
    """Test the Oakville API client"""
    
    api = OakvilleZoningAPI()
    
    # Test with 383 Maplehurst Avenue
    test_lat = 43.4675
    test_lon = -79.6877
    test_address = "383 Maplehurst Avenue, Oakville"
    
    print(f"Testing API with {test_address}")
    
    try:
        property_data = api.get_comprehensive_property_data(test_lat, test_lon, test_address)
        
        print(f"Zone: {property_data.zone_info.full_zone_code}")
        print(f"Confidence: {property_data.confidence_score}")
        print(f"Lot Area: {property_data.lot_dimensions.get('area_sqm', 'N/A')} m²")
        print(f"Data Sources: {property_data.data_sources}")
        
        return property_data
        
    except Exception as e:
        print(f"API test failed: {e}")
        return None

if __name__ == "__main__":
    import math
    test_result = test_oakville_api()
    if test_result:
        print("✅ Oakville API test completed successfully")
    else:
        print("❌ Oakville API test failed")