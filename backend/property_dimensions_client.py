"""
Property Dimensions Client
Automatically fetches lot area, frontage, and depth from Oakville APIs and other data sources
"""

import requests
import json
import math
import logging
from typing import Dict, List, Optional, Any, Tuple
from functools import lru_cache
from config import Config
from urllib.parse import urlencode
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))
from utils.cache_manager import CacheManager, cached

# Import existing API client for working zoning queries
from backend.api_client import get_api_client

logger = logging.getLogger(__name__)

class PropertyDimensionsClient:
    """Enhanced client for fetching real property dimensions from Oakville's official APIs"""
    
    def __init__(self):
        self.base_url = Config.OAKVILLE_API_BASE
        self.endpoints = Config.API_ENDPOINTS
        self.timeout = Config.REQUEST_TIMEOUT
        self.max_retries = Config.MAX_RETRIES
        self.retry_delay = Config.RETRY_DELAY
        
        # Official Oakville API endpoints for real data
        self.official_endpoints = {
            'zoning_query': 'https://maps.oakville.ca/oakgis/rest/services/SBS/Zoning_By_law_2014_014/FeatureServer/10/query',
            'address_search': 'https://maps.oakville.ca/oakgis/rest/services/SBS/Zoning_By_law_2014_014/FeatureServer/10/query',
            'parcels_query': f"{Config.OAKVILLE_API_BASE}{Config.API_ENDPOINTS['parcels']}"
        }
        
        # Initialize session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'OakvilleRealEstateAnalyzer/1.0',
            'Accept': 'application/json,application/pbf'
        })
        
        # Real Oakville zoning requirements for accurate lot size estimation
        self.oakville_zoning_specs = {
            # Residential Low Density (Estate & Large Lots)
            'RL1': {
                'min_lot_area': 1500.0,    # 1,500 m² minimum per By-law 2014-014
                'typical_lot_area': 2000.0, # Typical estate lot size
                'min_frontage': 35.0,       # 35m minimum frontage
                'typical_depth_ratio': 3.0,
                'description': 'Estate Residential'
            },
            'RL2': {
                'min_lot_area': 1000.0,    # 1,000 m² minimum
                'typical_lot_area': 1200.0,
                'min_frontage': 30.0,       # 30m minimum frontage
                'typical_depth_ratio': 2.8,
                'description': 'Large Lot Residential'
            },
            'RL3': {
                'min_lot_area': 650.0,     # 650 m² minimum
                'typical_lot_area': 750.0,  # Typical suburban lot
                'min_frontage': 18.0,       # 18m minimum frontage
                'typical_depth_ratio': 2.5,
                'description': 'Standard Residential'
            },
            'RL4': {
                'min_lot_area': 500.0,     # 500 m² minimum
                'typical_lot_area': 600.0,
                'min_frontage': 15.0,       # 15m minimum frontage
                'typical_depth_ratio': 2.3,
                'description': 'Compact Residential'
            },
            'RL5': {
                'min_lot_area': 350.0,     # 350 m² minimum
                'typical_lot_area': 425.0,
                'min_frontage': 12.0,       # 12m minimum frontage
                'typical_depth_ratio': 2.2,
                'description': 'Small Lot Residential'
            },
            'RL6': {
                'min_lot_area': 280.0,     # 280 m² minimum
                'typical_lot_area': 350.0,
                'min_frontage': 10.0,       # 10m minimum frontage
                'typical_depth_ratio': 2.1,
                'description': 'Townhouse/Row Housing'
            },
            'RL7': {
                'min_lot_area': 230.0,     # 230 m² minimum
                'typical_lot_area': 300.0,
                'min_frontage': 8.5,        # 8.5m minimum frontage
                'typical_depth_ratio': 2.0,
                'description': 'High Density Residential'
            },
            
            # Residential Medium Density
            'RM1': {
                'min_lot_area': 650.0,     # 650 m² minimum
                'typical_lot_area': 800.0,
                'min_frontage': 18.0,       # 18m minimum frontage
                'typical_depth_ratio': 2.2,
                'description': 'Medium Density 1'
            },
            'RM2': {
                'min_lot_area': 500.0,     # 500 m² minimum
                'typical_lot_area': 650.0,
                'min_frontage': 15.0,       # 15m minimum frontage
                'typical_depth_ratio': 2.0,
                'description': 'Medium Density 2'
            },
            'RM3': {
                'min_lot_area': 400.0,     # 400 m² minimum
                'typical_lot_area': 500.0,
                'min_frontage': 12.0,       # 12m minimum frontage
                'typical_depth_ratio': 1.8,
                'description': 'Medium Density 3'
            },
            'RM4': {
                'min_lot_area': 280.0,     # 280 m² minimum
                'typical_lot_area': 400.0,
                'min_frontage': 10.0,       # 10m minimum frontage
                'typical_depth_ratio': 1.6,
                'description': 'Medium Density 4'
            },
            
            # Mixed Use and Special Zones
            'MU': {
                'min_lot_area': 200.0,     # 200 m² minimum
                'typical_lot_area': 400.0,
                'min_frontage': 8.0,        # 8m minimum frontage
                'typical_depth_ratio': 1.8,
                'description': 'Mixed Use'
            },
            'MU4': {
                'min_lot_area': 200.0,     # 200 m² minimum  
                'typical_lot_area': 500.0,  # Urban core mixed use
                'min_frontage': 8.0,        # 8m minimum frontage
                'typical_depth_ratio': 2.0,
                'description': 'Mixed Use Urban Core'
            },
            
            # Residential High Density
            'RH': {
                'min_lot_area': 1000.0,    # 1,000 m² minimum for apartments
                'typical_lot_area': 1500.0,
                'min_frontage': 30.0,       # 30m minimum frontage
                'typical_depth_ratio': 2.5,
                'description': 'High Density Residential'
            },
            
            # Default for unknown zones
            'default': {
                'min_lot_area': 500.0,
                'typical_lot_area': 650.0,
                'min_frontage': 15.0,
                'typical_depth_ratio': 2.5,
                'description': 'Standard Default'
            }
        }
    
    def get_property_dimensions(self, lat: float, lon: float, address: str = None, 
                              zone_code: str = None, manual_measurements: Dict = None) -> Dict[str, Any]:
        """
        Get property information from APIs but use ONLY manual measurements for lot area
        
        Args:
            lat: Latitude
            lon: Longitude  
            address: Property address for context
            zone_code: Zoning code (optional, will get exact from API)
            manual_measurements: Dictionary with 'frontage' and 'depth' measurements (required)
            
        Returns:
            Dictionary with manually calculated lot_area, zone_code, special provisions from APIs
        """
        logger.info(f"Getting property info for: {lat}, {lon} with manual measurements: {manual_measurements}")
        
        result = {
            'lot_area': None,
            'lot_frontage': None,
            'lot_depth': None,
            'zone_code': None,
            'zone_class': None,
            'special_provisions': None,
            'data_sources': {},
            'confidence': {},
            'warnings': [],
            'success': False,
            'raw_api_data': {},
            'manual_calculation': True
        }
        
        # CRITICAL: Calculate lot area ONLY from manual measurements
        if manual_measurements and manual_measurements.get('frontage') and manual_measurements.get('depth'):
            frontage = float(manual_measurements['frontage'])
            depth = float(manual_measurements['depth'])
            
            # Calculate lot area: Frontage × Depth
            result['lot_area'] = frontage * depth
            result['lot_frontage'] = frontage
            result['lot_depth'] = depth
            
            result['data_sources']['lot_area'] = 'manual_measurement_frontage_x_depth'
            result['data_sources']['lot_frontage'] = 'manual_measurement_user_input'
            result['data_sources']['lot_depth'] = 'manual_measurement_user_input'
            result['confidence']['lot_area'] = 'user_measured'
            result['confidence']['lot_frontage'] = 'user_measured'
            result['confidence']['lot_depth'] = 'user_measured'
            
            logger.info(f"MANUAL CALCULATION: Lot Area = {frontage:.2f}m × {depth:.2f}m = {result['lot_area']:.2f} m²")
            result['success'] = True
        else:
            result['warnings'].append("MANUAL MEASUREMENTS REQUIRED: Must provide frontage and depth measurements. Lot area will NOT be calculated from API Shape__Area.")
            logger.warning("No manual measurements provided - lot area calculation requires user input")
        
        try:
            # Get zoning and special provisions from API (but NOT lot area)
            from backend.api_client import get_api_client
            api_client = get_api_client()
            
            zoning_data = api_client.get_zoning_info(lat, lon, address)
            
            if zoning_data and zoning_data.get('source') == 'api':
                # Store raw API response for debugging (but ignore Shape__Area for lot calculation)
                result['raw_api_data'] = zoning_data
                
                # NOTE: We deliberately DO NOT use zoning_data.get('area') for lot area
                # Lot area comes ONLY from manual measurements above
                
                # Extract EXACT zone code (including -0 suffix and SP)
                if zoning_data.get('zone_code'):
                    result['zone_code'] = zoning_data['zone_code']
                    result['data_sources']['zone_code'] = 'oakville_zoning_api'
                    result['confidence']['zone_code'] = 'exact'
                    logger.info(f"Zone code from API: {result['zone_code']}")
                
                # Extract EXACT zone class
                if zoning_data.get('zone_class'):
                    result['zone_class'] = zoning_data['zone_class']
                    result['data_sources']['zone_class'] = 'oakville_zoning_api'
                
                # Extract EXACT special provisions
                special_provisions = []
                if zoning_data.get('special_provision'):
                    special_provisions.append(zoning_data['special_provision'])
                if zoning_data.get('special_provisions_list'):
                    special_provisions.extend(zoning_data['special_provisions_list'])
                
                if special_provisions:
                    result['special_provisions'] = '; '.join(special_provisions)
                    result['data_sources']['special_provisions'] = 'oakville_zoning_api'
                    logger.info(f"Special provisions from API: {result['special_provisions']}")
                
            else:
                logger.warning(f"No zoning API data available for coordinates: {lat}, {lon}")
                result['warnings'].append("No zoning data available from Oakville APIs - property may be outside Oakville or coordinates invalid")
            
        except Exception as e:
            logger.error(f"Error fetching zoning data: {e}")
            result['warnings'].append(f"API error: {str(e)}")
        
        return result
    
    def _calculate_dimensions_from_exact_data(self, lot_area: float, zone_code: str, 
                                            address: str = None) -> Dict[str, float]:
        """
        Calculate frontage and depth from exact lot area using real zoning requirements
        
        Args:
            lot_area: Exact lot area from Shape__Area API field
            zone_code: Exact zone code from API (with -0 suffix if present)
            address: Property address for location context
            
        Returns:
            Dictionary with calculated frontage and depth
        """
        # Extract base zone (handle -0 suffix and SP provisions)
        base_zone = zone_code.split()[0].split('-')[0].upper() if zone_code else 'RL3'
        
        # Get real Oakville zoning specifications  
        zone_spec = self.oakville_zoning_specs.get(base_zone, self.oakville_zoning_specs['default'])
        
        # Start with minimum frontage from zoning requirements
        min_frontage = zone_spec['min_frontage']
        depth_ratio = zone_spec['typical_depth_ratio']
        
        # Calculate based on geometric relationship: area = frontage × depth
        # Method: Use minimum frontage as base, calculate depth from area
        calculated_frontage = min_frontage
        calculated_depth = lot_area / calculated_frontage
        
        # Apply location adjustments if address provided
        if address:
            address_lower = address.lower()
            
            if any(keyword in address_lower for keyword in ['lakeshore', 'lake', 'water']):
                # Waterfront properties tend to be wider
                calculated_frontage *= 1.2
                calculated_depth = lot_area / calculated_frontage
            elif any(keyword in address_lower for keyword in ['kerr', 'trafalgar', 'downtown']):
                # Urban areas may be narrower but deeper
                calculated_frontage *= 0.95
                calculated_depth = lot_area / calculated_frontage
        
        # Apply bounds based on reasonable property dimensions
        calculated_frontage = max(min_frontage * 0.8, min(60.0, calculated_frontage))
        calculated_depth = lot_area / calculated_frontage  # Ensure area accuracy
        
        logger.debug(f"Calculated from exact area {lot_area:.0f}m² with zone {zone_code}: "
                    f"frontage={calculated_frontage:.1f}m, depth={calculated_depth:.1f}m")
        
        return {
            'frontage': round(calculated_frontage, 1),
            'depth': round(calculated_depth, 1)
        }
    
    @cached(cache_type='api_response', ttl=3600, key_prefix='parcel_data')
    def _get_parcel_data(self, lat: float, lon: float) -> Optional[Dict]:
        """Get parcel data for reference only - NOT used for lot area calculation"""
        try:
            # Get zoning and parcel info for reference, but lot area comes from manual measurements
            from backend.api_client import get_api_client
            api_client = get_api_client()
            
            # Get zoning info for reference
            zoning_info = api_client.get_zoning_info(lat, lon)
            
            if zoning_info:
                logger.info(f"Found parcel reference data - Zone: {zoning_info.get('zone_code', 'Unknown')}")
                
                # NOTE: We deliberately do NOT return lot_area here
                # Lot area must come from manual measurements only
                return {
                    'zone_code': zoning_info.get('zone_code'),
                    'zone_class': zoning_info.get('zone_class'),
                    'special_provision': zoning_info.get('special_provision'),
                    'parcel_id': zoning_info.get('object_id'),
                    'confidence': 'reference_only',  # Reference data, not for calculations
                    'data_source': 'oakville_zoning_api',
                    'api_shape_area': zoning_info.get('area'),  # Store for reference, not calculation
                    'note': 'API area data available but not used - manual measurements required'
                }
            
            # Try Assessment Parcels API for reference
            parcel_data = self._try_assessment_parcels_api(lat, lon)
            if parcel_data:
                return parcel_data
            
            logger.warning(f"No parcel reference data found for coordinates: {lat}, {lon}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching parcel reference data: {e}")
            return None
            
    def _try_assessment_parcels_api(self, lat: float, lon: float) -> Optional[Dict]:
        """Try to get data from Assessment Parcels API as fallback"""
        try:
            # Build Assessment Parcels API query
            params = {
                'where': '1=1',
                'geometry': f'{lon},{lat}',
                'geometryType': 'esriGeometryPoint',
                'inSR': '4326',
                'spatialRel': 'esriSpatialRelIntersects',
                'outFields': 'AREA,AREA_ACRES,PARCEL_ID,ROLL_NUMBER,ADDRESS,OWNER_NAME,Shape__Area',
                'returnGeometry': 'false',
                'f': 'json'
            }
            
            url = f"{self.base_url}/Assessment_Parcels/FeatureServer/0/query"
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if 'features' in data and len(data['features']) > 0:
                feature = data['features'][0]
                attributes = feature.get('attributes', {})
                
                # Try multiple area fields
                lot_area = None
                area_source = None
                
                # Priority 1: Shape__Area (most accurate)
                if attributes.get('Shape__Area') and float(attributes['Shape__Area']) > 0:
                    lot_area = float(attributes['Shape__Area'])
                    area_source = 'shape_area_parcel_api'
                # Priority 2: AREA field
                elif attributes.get('AREA') and float(attributes['AREA']) > 0:
                    lot_area = float(attributes['AREA'])
                    area_source = 'area_field_api'
                # Priority 3: AREA_ACRES converted
                elif attributes.get('AREA_ACRES') and float(attributes['AREA_ACRES']) > 0:
                    lot_area = float(attributes['AREA_ACRES']) * 4046.86  # Convert to m²
                    area_source = 'acres_converted_api'
                
                if lot_area and lot_area > 0:
                    logger.info(f"Found assessment parcel - Area: {lot_area:.2f} m² via {area_source}")
                    
                    return {
                        'lot_area': lot_area,
                        'area_source': area_source,
                        'parcel_id': attributes.get('PARCEL_ID'),
                        'roll_number': attributes.get('ROLL_NUMBER'),
                        'address': attributes.get('ADDRESS'),
                        'owner': attributes.get('OWNER_NAME'),
                        'confidence': 'high' if area_source == 'shape_area_parcel_api' else 'medium',
                        'data_source': 'oakville_assessment_api'
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Assessment Parcels API error: {e}")
            return None
    
    def _get_area_from_zoning(self, lat: float, lon: float) -> Optional[Dict]:
        """
        Get lot area from zoning Shape__Area field when parcel API is not available
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Dictionary with lot area from zoning data
        """
        try:
            zoning_data = self._get_enhanced_zoning_data(lat, lon)
            if zoning_data and zoning_data.get('shape_area'):
                shape_area = zoning_data['shape_area']
                
                # Zoning Shape__Area usually represents the entire zoning polygon, not individual lots
                # Use it only if it seems reasonable for a single property
                if 50 <= shape_area <= 5000:  # Between 50 and 5,000 m² might be individual lots
                    logger.info(f"Using zoning Shape__Area as lot area (seems to be individual lot): {shape_area:.2f} m²")
                    return {
                        'lot_area': shape_area,
                        'area_source': 'zoning_shape_area_individual',
                        'frontage_api': None,
                        'depth_api': None,
                        'calculated_dimensions': None,
                        'parcel_id': None,
                        'roll_number': None,
                        'address': None,
                        'owner': None,
                        'geometry': None
                    }
                else:
                    logger.info(f"Zoning Shape__Area represents zoning polygon ({shape_area:.0f} m²), estimating typical lot size")
                    # Estimate typical lot size based on zone type
                    estimated_area = self._estimate_typical_lot_area(zoning_data['zone_code'])
                    if estimated_area:
                        return {
                            'lot_area': estimated_area,
                            'area_source': 'zone_based_estimation',
                            'frontage_api': None,
                            'depth_api': None,
                            'calculated_dimensions': None,
                            'parcel_id': None,
                            'roll_number': None,
                            'address': None,
                            'owner': None,
                            'geometry': None
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting area from zoning: {e}")
            return None
    
    def _estimate_typical_lot_area(self, zone_code: str) -> Optional[float]:
        """
        Estimate typical lot area based on Oakville zoning requirements and market reality
        
        Args:
            zone_code: The zoning code (e.g., RL3, RM2, MU4)
            
        Returns:
            Estimated typical lot area in square meters
        """
        # Based on Oakville zoning by-law minimum requirements and typical development patterns
        typical_areas = {
            # Residential Low zones - estate to urban
            'RL1': 2000.0,    # Large estate lots
            'RL2': 1200.0,    # Estate lots
            'RL3': 750.0,     # Suburban lots
            'RL4': 600.0,     # Suburban to urban transition
            'RL5': 500.0,     # Urban residential
            'RL6': 400.0,     # Compact urban
            'RL7': 350.0,     # Dense urban
            'RL8': 300.0,     # High-density residential
            'RL9': 280.0,     # Very compact
            'RL10': 500.0,    # Duplex-capable lots
            'RL11': 400.0,    # Mixed housing forms
            
            # Residential Medium zones
            'RM1': 800.0,     # Low-medium density
            'RM2': 1200.0,    # Medium density apartments
            'RM3': 1500.0,    # Medium-high density
            'RM4': 2000.0,    # High density residential
            
            # Mixed Use and other zones
            'MU1': 600.0,     # Neighborhood mixed use
            'MU2': 800.0,     # Community mixed use
            'MU3': 1000.0,    # Regional mixed use
            'MU4': 500.0,     # Urban core mixed use
            'RUC': 400.0,     # Residential uptown core
            
            # Non-residential (estimate for context)
            'O1': 1000.0,     # Private open space
            'O2': 1500.0,     # Public open space
            'I': 2000.0,      # Institutional
            'U': 800.0,       # Utilities
            'N': 500.0,       # Natural area (if developed)
        }
        
        if not zone_code:
            return 600.0  # Default suburban lot
        
        # Clean the zone code (remove suffix like -0, special provisions)
        base_zone = zone_code.split('-')[0].split()[0].strip()
        
        estimated = typical_areas.get(base_zone)
        if estimated:
            logger.info(f"Estimated typical lot area for {zone_code}: {estimated:.0f} m²")
            return estimated
        
        # Default fallback based on zone type prefix
        if base_zone.startswith('RL'):
            return 600.0  # Average residential low
        elif base_zone.startswith('RM'):
            return 1000.0  # Average residential medium
        elif base_zone.startswith('MU'):
            return 700.0   # Average mixed use
        else:
            return 600.0   # General default
    
    def _calculate_frontage_depth(self, lot_area: float, zone_code: str = None, 
                                address: str = None) -> Dict[str, float]:
        """
        Calculate frontage and depth based on real Oakville zoning requirements
        
        Args:
            lot_area: Lot area in square meters
            zone_code: Zoning classification for context
            address: Address for location context
            
        Returns:
            Dictionary with calculated frontage and depth
        """
        # Extract base zone (remove suffix and SP)
        base_zone = zone_code.split()[0].split('-')[0].upper() if zone_code else 'RL3'
        
        # Get real Oakville zoning specifications
        zone_spec = self.oakville_zoning_specs.get(base_zone, self.oakville_zoning_specs['default'])
        
        # Use minimum frontage as starting point for calculation
        min_frontage = zone_spec['min_frontage']
        depth_ratio = zone_spec['typical_depth_ratio']
        
        # Start with zoning-appropriate frontage
        calculated_frontage = min_frontage
        
        # Apply location-based adjustments
        if address:
            address_lower = address.lower()
            
            # Adjust for typical Oakville neighborhood patterns
            if any(area in address_lower for area in ['lakeshore', 'riverside', 'waterfront']):
                # Waterfront properties tend to be wider
                calculated_frontage *= 1.3
                depth_ratio *= 0.8
            elif any(area in address_lower for area in ['downtown', 'kerr', 'rebecca']):
                # Downtown areas tend to be narrower
                calculated_frontage *= 0.9  
                depth_ratio *= 1.2
            elif any(area in address_lower for area in ['glen abbey', 'eastlake', 'westlake']):
                # Suburban developments tend to be more rectangular
                calculated_frontage *= 1.1
                depth_ratio *= 0.95
        
        # Calculate depth from area and frontage
        # Use geometric approach: area = frontage × depth, so depth = area / frontage
        # But also consider typical depth ratios for the zone
        
        # Method 1: Direct calculation from area
        basic_depth = lot_area / calculated_frontage
        
        # Method 2: Zone-typical depth based on frontage
        zone_typical_depth = calculated_frontage * depth_ratio
        
        # Use a weighted average favoring area accuracy but respecting zone patterns
        calculated_depth = (basic_depth * 0.7) + (zone_typical_depth * 0.3)
        
        # Apply reasonable bounds based on Oakville zoning standards
        calculated_frontage = max(zone_spec['min_frontage'] * 0.8, min(60.0, calculated_frontage))
        calculated_depth = max(15.0, min(200.0, calculated_depth))  
        
        # Final area check - adjust if needed to maintain area accuracy
        calculated_area = calculated_frontage * calculated_depth
        area_diff_percent = abs(calculated_area - lot_area) / lot_area * 100
        
        if area_diff_percent > 10:  # If more than 10% different, prioritize area accuracy
            calculated_depth = lot_area / calculated_frontage  # Recalculate depth to maintain area
        
        logger.debug(f"Zone: {base_zone} (min frontage: {min_frontage}m, depth ratio: {depth_ratio:.1f})")
        logger.debug(f"Calculated: frontage={calculated_frontage:.1f}m, depth={calculated_depth:.1f}m")
        logger.debug(f"Area check: {calculated_frontage * calculated_depth:.0f}m² vs target {lot_area:.0f}m²")
        
        return {
            'frontage': round(calculated_frontage, 1),
            'depth': round(calculated_depth, 1)
        }
    
    def _calculate_dimensions_from_geometry(self, geometry: Dict) -> Optional[Dict]:
        """
        Calculate real frontage and depth from property geometry boundaries
        
        Args:
            geometry: Geometry object from API response
            
        Returns:
            Dictionary with calculated frontage and depth from real boundaries
        """
        try:
            if not geometry or 'rings' not in geometry:
                return None
            
            rings = geometry['rings']
            if not rings or not rings[0]:
                return None
            
            # Get the exterior ring (first ring)
            exterior_ring = rings[0]
            if len(exterior_ring) < 4:  # Need at least 4 points for a polygon
                return None
            
            # Calculate distances between consecutive points to find frontage and depth
            # This is a simplified approach - assumes rectangular lot
            distances = []
            for i in range(len(exterior_ring) - 1):
                x1, y1 = exterior_ring[i][0], exterior_ring[i][1]
                x2, y2 = exterior_ring[i + 1][0], exterior_ring[i + 1][1]
                
                # Calculate distance using Haversine formula for lat/lon coordinates
                # Convert to approximate meters (simplified)
                dx = (x2 - x1) * 111320 * math.cos(math.radians(y1))  # meters per degree longitude
                dy = (y2 - y1) * 110540  # meters per degree latitude
                distance = math.sqrt(dx * dx + dy * dy)
                distances.append(distance)
            
            if len(distances) >= 2:
                # For rectangular lots, frontage and depth are typically the two different side lengths
                # Sort distances to get the two main dimensions
                sorted_distances = sorted(distances)
                
                # Group similar distances (sides of rectangle should be similar)
                groups = []
                for dist in sorted_distances:
                    placed = False
                    for group in groups:
                        if abs(group[0] - dist) < 2.0:  # Within 2 meters tolerance
                            group.append(dist)
                            placed = True
                            break
                    if not placed:
                        groups.append([dist])
                
                # Take the average of the two main dimension groups
                if len(groups) >= 2:
                    dim1 = sum(groups[0]) / len(groups[0])
                    dim2 = sum(groups[-1]) / len(groups[-1])
                    
                    # Assign shorter dimension as frontage, longer as depth (typical)
                    frontage = min(dim1, dim2)
                    depth = max(dim1, dim2)
                    
                    logger.info(f"Calculated from geometry - Frontage: {frontage:.1f}m, Depth: {depth:.1f}m")
                    
                    return {
                        'frontage': round(frontage, 1),
                        'depth': round(depth, 1),
                        'calculated_area': round(frontage * depth, 1),
                        'method': 'geometry_analysis'
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating dimensions from geometry: {e}")
            return None
    
    @cached(cache_type='api_response', ttl=3600, key_prefix='zoning_enhanced')
    def _get_enhanced_zoning_data(self, lat: float, lon: float) -> Optional[Dict]:
        """
        Get enhanced zoning data using the existing working API client
        This includes zone codes, SP details, and suffix zones like '-0'
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Enhanced zoning data with all details
        """
        try:
            # Use the working API client
            api_client = get_api_client()
            zoning_info = api_client.get_zoning_info(lat, lon)
            
            if zoning_info and zoning_info.get('zone_code'):
                # Parse the zone code for suffix zones
                raw_zone = zoning_info['zone_code']
                base_zone = zoning_info.get('base_zone', raw_zone)
                suffix = zoning_info.get('suffix')
                
                # Get special provisions
                special_provisions = zoning_info.get('special_provisions_list', [])
                
                logger.info(f"Enhanced zoning data - Zone: {raw_zone}, Base: {base_zone}, Suffix: {suffix}, SP: {len(special_provisions)}")
                
                return {
                    'zone_code': raw_zone,
                    'base_zone': base_zone,
                    'suffix': suffix,
                    'zone_description': zoning_info.get('zone_description', ''),
                    'zone_class': zoning_info.get('zone_class', ''),
                    'special_provisions': special_provisions,
                    'shape_area': zoning_info.get('area'),
                    'object_id': zoning_info.get('object_id'),
                    'confidence': zoning_info.get('confidence', 'medium'),
                    'source': 'existing_api_client'
                }
            
            logger.warning(f"No enhanced zoning data found for coordinates: {lat}, {lon}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching enhanced zoning data: {e}")
            return None
    
    def get_dimensions_with_fallbacks(self, lat: float, lon: float, address: str = None,
                                    zone_code: str = None, manual_measurements: Dict = None) -> Dict[str, Any]:
        """
        Get property dimensions using ONLY manual measurements for lot area
        
        Args:
            lat, lon: Coordinates
            address: Property address
            zone_code: Zoning classification
            manual_measurements: Dict with manual frontage and depth measurements (REQUIRED)
            
        Returns:
            Property data with manually calculated lot area and API zoning data
        """
        # Get data using manual measurements only
        api_result = self.get_property_dimensions(lat, lon, address, zone_code, manual_measurements)
        
        # CRITICAL: Lot area must come from manual measurements - no fallbacks allowed
        if not manual_measurements or not manual_measurements.get('frontage') or not manual_measurements.get('depth'):
            api_result['warnings'].append(
                "MANUAL MEASUREMENTS REQUIRED: This system requires user to manually measure frontage and depth from the interactive map. "
                "Lot area is calculated as: Frontage × Depth. No API Shape__Area will be used."
            )
            api_result['success'] = False
            logger.error("Manual measurements are required - no automatic fallbacks for lot area")
        
        # Final data quality assessment based on manual measurement approach
        manual_sources = [k for k, v in api_result.get('data_sources', {}).items() if 'manual' in v]
        api_sources = [k for k, v in api_result.get('data_sources', {}).items() if 'api' in v]
        
        api_result['data_summary'] = {
            'manual_measurement_sources': len(manual_sources),
            'api_reference_sources': len(api_sources),
            'calculation_method': 'manual_measurement_only',
            'overall_confidence': 'high' if manual_measurements and len(manual_sources) >= 2 else 'low',
            'recommendation': (
                'High confidence - lot area calculated from user measurements (Frontage × Depth)' 
                if manual_measurements and len(manual_sources) >= 2 else 
                'Manual measurements required - please use the interactive map to measure frontage and depth'
            )
        }
        
        return api_result
    
    def _get_zone_based_lot_area(self, zone_code: str = None, address: str = None) -> Optional[Dict]:
        """
        Get lot area based on real Oakville zoning requirements
        
        Args:
            zone_code: Zoning classification (e.g., 'RL3', 'RL4-0', 'MU4')
            address: Property address for location context
            
        Returns:
            Dictionary with zone-based lot area and details
        """
        if not zone_code:
            return None
            
        # Extract base zone (remove suffix like '-0' and special provisions)
        base_zone = zone_code.split()[0].split('-')[0].upper()
        
        # Get zoning specifications
        zone_spec = self.oakville_zoning_specs.get(base_zone, self.oakville_zoning_specs['default'])
        
        # Use typical lot area (not minimum) for realistic estimation
        lot_area = zone_spec['typical_lot_area']
        
        # Apply location-based adjustments
        if address:
            address_lower = address.lower()
            
            # Waterfront properties tend to be larger
            if any(keyword in address_lower for keyword in ['lakeshore', 'lake', 'water', 'shore', 'beach']):
                lot_area *= 1.3  # 30% larger for waterfront
                location_note = " (waterfront premium applied)"
            # Estate areas tend to be larger
            elif any(keyword in address_lower for keyword in ['glen abbey', 'westlake', 'eastlake', 'bronte']):
                lot_area *= 1.15  # 15% larger for estate areas
                location_note = " (estate area premium)"
            # Urban core tends to be more compact
            elif any(keyword in address_lower for keyword in ['kerr', 'trafalgar', 'downtown', 'rebecca']):
                lot_area *= 0.9   # 10% smaller for urban areas
                location_note = " (urban core adjustment)"
            else:
                location_note = ""
        else:
            location_note = ""
        
        # Handle suffix zones (like RL4-0) which typically have reduced requirements
        if '-0' in zone_code:
            lot_area *= 0.85  # 15% reduction for suffix zones
            suffix_note = " with -0 suffix reduction"
        else:
            suffix_note = ""
        
        return {
            'lot_area': round(lot_area, 1),
            'zone_description': f"{zone_spec['description']}{suffix_note}{location_note}",
            'base_zone': base_zone,
            'min_area': zone_spec['min_lot_area'],
            'typical_area': zone_spec['typical_lot_area'],
            'min_frontage': zone_spec['min_frontage'],
            'source': 'oakville_zoning_bylaw_2014_014'
        }