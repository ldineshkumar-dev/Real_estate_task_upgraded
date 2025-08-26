"""
Corrected Oakville Zoning API Client
Fixes critical issues in zone code retrieval and provides comprehensive zoning analysis
"""

import requests
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import time
from functools import lru_cache

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class ZoningResult:
    """Complete zoning information structure"""
    zone_code: str
    zone_description: str
    full_zoning_description: str
    zoning_class: str
    special_provisions: List[str]
    building_heights: Optional[str]
    temp_use: Optional[str]
    hold_provisions: Optional[str]
    growth_area: Optional[str]
    confidence: str
    source: str
    raw_attributes: Dict[str, Any]
    coordinates: Tuple[float, float]
    api_response_time: float

class CorrectedOakvilleZoningAPI:
    """
    Corrected and enhanced Oakville zoning API client with proper error handling
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = 30
        
        # Primary and fallback API endpoints
        self.zoning_endpoints = [
            "https://maps.oakville.ca/oakgis/rest/services/SBS/Zoning_By_law_2014_014/FeatureServer/10/query",
            "https://maps.oakville.ca/oakgis/rest/services/SBS/Zoning_By_law_2014_014/FeatureServer/0/query",
            "https://maps.oakville.ca/oakgis/rest/services/Planning/MapServer/10/query"
        ]
        
        # Parcels API for coordinate validation
        self.parcels_api = "https://services5.arcgis.com/QJebCdoMf4PF8fJP/arcgis/rest/services/Parcels_Addresses/FeatureServer/0/query"
        
        # Cache for API responses (TTL: 1 hour)
        self._cache = {}
        self._cache_timeout = 3600
        
        # Load zoning regulations for validation
        try:
            with open('data/comprehensive_zoning_regulations.json', 'r') as f:
                self.zoning_regulations = json.load(f)
        except FileNotFoundError:
            logger.warning("Zoning regulations file not found - using basic validation")
            self.zoning_regulations = {}

    def get_zone(self, lat: float, lon: float, address: str = None) -> Optional[ZoningResult]:
        """
        Enhanced get_zone function with comprehensive error handling and field mapping
        
        Args:
            lat: Latitude (decimal degrees, WGS84)
            lon: Longitude (decimal degrees, WGS84)  
            address: Optional property address for validation
            
        Returns:
            ZoningResult object with complete zoning information or None if unable to determine
        """
        
        # Validate coordinates
        if not self._validate_coordinates(lat, lon):
            logger.error(f"Invalid coordinates: lat={lat}, lon={lon}")
            return None
            
        # Check if coordinates are within Oakville bounds
        if not self._is_within_oakville_bounds(lat, lon):
            logger.warning(f"Coordinates may be outside Oakville: lat={lat}, lon={lon}")
        
        # Check cache first
        cache_key = f"zone_{lat}_{lon}"
        if cache_key in self._cache:
            cached_result, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_timeout:
                logger.info(f"Returning cached zoning result for {lat}, {lon}")
                return cached_result
        
        start_time = time.time()
        
        # Try multiple API endpoints with fallback
        for endpoint_idx, endpoint in enumerate(self.zoning_endpoints):
            try:
                logger.info(f"Attempting zoning query with endpoint {endpoint_idx + 1}/{len(self.zoning_endpoints)}")
                
                result = self._query_zoning_endpoint(endpoint, lat, lon, address)
                
                if result:
                    result.api_response_time = time.time() - start_time
                    result.source = f"oakville_api_endpoint_{endpoint_idx + 1}"
                    
                    # Cache successful result
                    self._cache[cache_key] = (result, time.time())
                    
                    logger.info(f"Successfully retrieved zone: {result.zone_code}")
                    return result
                    
            except Exception as e:
                logger.warning(f"Endpoint {endpoint_idx + 1} failed: {str(e)}")
                continue
        
        # If all API endpoints fail, try address-based lookup
        if address:
            logger.info("Attempting address-based zone lookup as fallback")
            result = self._get_zone_from_address_lookup(address, lat, lon)
            if result:
                result.api_response_time = time.time() - start_time
                result.source = "address_fallback"
                return result
        
        # Final fallback: return basic result with unknown zone
        logger.error(f"Unable to determine zoning for coordinates {lat}, {lon}")
        return ZoningResult(
            zone_code="Unknown",
            zone_description="Unable to determine zoning for this property",
            full_zoning_description="No zoning data available",
            zoning_class="Unknown",
            special_provisions=[],
            building_heights=None,
            temp_use=None,
            hold_provisions=None,
            growth_area=None,
            confidence="none",
            source="api_failure",
            raw_attributes={},
            coordinates=(lat, lon),
            api_response_time=time.time() - start_time
        )

    def _query_zoning_endpoint(self, endpoint: str, lat: float, lon: float, address: str = None) -> Optional[ZoningResult]:
        """Query a specific zoning API endpoint"""
        
        params = {
            "f": "json",
            "geometry": f"{lon},{lat}",
            "geometryType": "esriGeometryPoint",
            "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "returnGeometry": False,
            "where": "1=1"
        }
        
        try:
            response = self.session.get(endpoint, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if 'error' in data:
                logger.warning(f"API returned error: {data['error']}")
                return None
            
            features = data.get("features", [])
            
            if not features:
                logger.debug(f"No zoning features found at {lat}, {lon}")
                return None
                
            # Process the first (most relevant) feature
            attrs = features[0]["attributes"]
            
            return self._parse_zoning_attributes(attrs, lat, lon)
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout querying zoning endpoint: {endpoint}")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed for endpoint {endpoint}: {str(e)}")
            return None
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON response from endpoint: {endpoint}")
            return None

    def _parse_zoning_attributes(self, attrs: Dict[str, Any], lat: float, lon: float) -> ZoningResult:
        """Parse zoning attributes from API response into structured result"""
        
        # Extract base zone code
        zone_code = attrs.get("ZONE", "").strip()
        
        # Extract special provisions
        special_provisions = []
        for i in range(1, 11):  # SP1 through SP10
            sp_value = attrs.get(f"SP{i}")
            if sp_value and str(sp_value).strip() and str(sp_value).strip().upper() != "NULL":
                special_provisions.append(str(sp_value).strip())
        
        # Build full zone code with special provisions
        full_zone_code = zone_code
        if special_provisions:
            sp_numbers = [sp for sp in special_provisions if sp.isdigit()]
            if sp_numbers:
                full_zone_code += f" SP:{','.join(sp_numbers)}"
        
        # Determine confidence level
        confidence = "high" if zone_code and zone_code != "Unknown" else "low"
        
        return ZoningResult(
            zone_code=full_zone_code,
            zone_description=attrs.get("ZONE_DESC", "").strip(),
            full_zoning_description=attrs.get("FULL_ZONING_DESC", full_zone_code).strip(),
            zoning_class=attrs.get("CLASS", "").strip(),
            special_provisions=special_provisions,
            building_heights=attrs.get("BLDG_HEIGHTS"),
            temp_use=attrs.get("TEMP"),
            hold_provisions=attrs.get("HOLD"),
            growth_area=attrs.get("GROWTH_AREA"),
            confidence=confidence,
            source="oakville_api",
            raw_attributes=attrs,
            coordinates=(lat, lon),
            api_response_time=0.0  # Will be set by caller
        )

    def _validate_coordinates(self, lat: float, lon: float) -> bool:
        """Validate coordinate ranges for realistic values"""
        
        # Oakville is approximately between:
        # Latitude: 43.40 to 43.55
        # Longitude: -79.85 to -79.55
        
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            return False
            
        # Extended bounds to allow for nearby areas
        if not (43.0 <= lat <= 44.0):
            return False
            
        if not (-80.0 <= lon <= -79.0):
            return False
            
        return True

    def _is_within_oakville_bounds(self, lat: float, lon: float) -> bool:
        """Check if coordinates are within Oakville municipal boundaries"""
        
        # Oakville approximate bounds
        oakville_bounds = {
            'north': 43.55,
            'south': 43.40,
            'east': -79.55,
            'west': -79.85
        }
        
        return (oakville_bounds['south'] <= lat <= oakville_bounds['north'] and 
                oakville_bounds['west'] <= lon <= oakville_bounds['east'])

    def _get_zone_from_address_lookup(self, address: str, lat: float, lon: float) -> Optional[ZoningResult]:
        """Fallback method using address-based lookup"""
        
        # This could integrate with the existing enhanced zone detector
        logger.info(f"Attempting address-based lookup for: {address}")
        
        # Try to use the existing enhanced zone detector as fallback
        try:
            from enhanced_zone_detector import EnhancedZoneDetector
            detector = EnhancedZoneDetector()
            zone_info = detector.detect_zone_code(lat, lon, address)
            
            if zone_info and zone_info.base_zone != "Unknown":
                return ZoningResult(
                    zone_code=zone_info.full_zone_code,
                    zone_description=zone_info.base_zone,
                    full_zoning_description=zone_info.full_zone_code,
                    zoning_class="Detected",
                    special_provisions=[str(zone_info.special_provision_number)] if zone_info.special_provision_number else [],
                    building_heights=None,
                    temp_use=None,
                    hold_provisions=None,
                    growth_area=None,
                    confidence=zone_info.confidence,
                    source="enhanced_detector",
                    raw_attributes={},
                    coordinates=(lat, lon),
                    api_response_time=0.0
                )
        except ImportError:
            logger.debug("Enhanced zone detector not available")
        except Exception as e:
            logger.warning(f"Enhanced zone detector failed: {str(e)}")
        
        return None

    def get_zone_regulations(self, zone_code: str) -> Optional[Dict[str, Any]]:
        """Get detailed regulations for a specific zone code"""
        
        # Parse the zone code to extract base zone
        base_zone = zone_code.split()[0].split('SP:')[0]  # Remove special provisions
        
        if base_zone in self.zoning_regulations.get('residential_zones', {}):
            return self.zoning_regulations['residential_zones'][base_zone]
        
        return None

    def validate_zone_code(self, zone_code: str) -> bool:
        """Validate if a zone code exists in Oakville's zoning bylaw"""
        
        base_zone = zone_code.split()[0].split('SP:')[0]
        
        # Check against known residential zones
        residential_zones = ['RL1', 'RL2', 'RL3', 'RL4', 'RL5', 'RM1', 'RM2', 'RM3', 'RH']
        commercial_zones = ['LC', 'GC', 'RC', 'CC', 'TC']
        institutional_zones = ['I', 'OS']
        industrial_zones = ['IL', 'IH']
        
        all_zones = residential_zones + commercial_zones + institutional_zones + industrial_zones
        
        return base_zone in all_zones

    def get_comprehensive_property_analysis(self, lat: float, lon: float, address: str = None) -> Dict[str, Any]:
        """Get comprehensive property analysis including zoning, regulations, and development potential"""
        
        zoning_result = self.get_zone(lat, lon, address)
        
        if not zoning_result or zoning_result.zone_code == "Unknown":
            return {
                'error': 'Unable to determine zoning for this property',
                'coordinates': (lat, lon),
                'address': address
            }
        
        # Get detailed regulations
        regulations = self.get_zone_regulations(zoning_result.zone_code)
        
        return {
            'zoning': asdict(zoning_result),
            'regulations': regulations,
            'development_potential': self._calculate_development_potential(zoning_result, regulations),
            'property_info': {
                'coordinates': (lat, lon),
                'address': address,
                'within_oakville_bounds': self._is_within_oakville_bounds(lat, lon)
            }
        }

    def _calculate_development_potential(self, zoning_result: ZoningResult, regulations: Optional[Dict]) -> Dict[str, Any]:
        """Calculate basic development potential metrics"""
        
        if not regulations:
            return {'status': 'No regulations available for calculation'}
        
        # Basic development metrics
        potential = {
            'max_floors': regulations.get('max_floors', 'Not specified'),
            'max_height_meters': regulations.get('max_height', 'Not specified'),
            'max_lot_coverage': regulations.get('max_lot_coverage', 'Not specified'),
            'min_lot_area': regulations.get('min_lot_area', 'Not specified'),
            'setback_requirements': {
                'front': regulations.get('front_setback', 'Not specified'),
                'rear': regulations.get('rear_setback', 'Not specified'),
                'side': regulations.get('side_setback', 'Not specified')
            },
            'special_restrictions': zoning_result.special_provisions
        }
        
        return potential


# Integration function for existing applications
def get_zone(lat: float, lon: float, address: str = None) -> Optional[Dict[str, Any]]:
    """
    Drop-in replacement for the existing get_zone function
    Returns dict format for backward compatibility
    """
    
    api = CorrectedOakvilleZoningAPI()
    result = api.get_zone(lat, lon, address)
    
    if not result:
        return None
    
    # Return in format expected by existing code
    return {
        "zone": result.zone_code.split()[0],  # Base zone code only
        "class": result.zoning_class,
        "special_provision": result.special_provisions[0] if result.special_provisions else None,
        "full_zone_code": result.zone_code,
        "zone_description": result.zone_description,
        "building_heights": result.building_heights,
        "confidence": result.confidence,
        "source": result.source,
        "area": result.raw_attributes.get("Shape__Area"),
        "coordinates": result.coordinates
    }


# Test function
def test_corrected_api():
    """Test the corrected API with known addresses"""
    
    api = CorrectedOakvilleZoningAPI()
    
    # Test cases
    test_cases = [
        {
            'name': '383 Maplehurst Ave',
            'lat': 43.467,
            'lon': -79.688,
            'address': '383 MAPLEHURST AVE'
        },
        {
            'name': 'Downtown Oakville',
            'lat': 43.4675,
            'lon': -79.6876,
            'address': None
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        print(f"Coordinates: {test_case['lat']}, {test_case['lon']}")
        
        result = api.get_zone(test_case['lat'], test_case['lon'], test_case['address'])
        
        if result:
            print(f"Zone Code: {result.zone_code}")
            print(f"Zone Class: {result.zoning_class}")
            print(f"Confidence: {result.confidence}")
            print(f"Source: {result.source}")
            print(f"Response Time: {result.api_response_time:.2f}s")
            if result.special_provisions:
                print(f"Special Provisions: {', '.join(result.special_provisions)}")
        else:
            print("No zoning information found")
    
    return True


if __name__ == "__main__":
    test_corrected_api()