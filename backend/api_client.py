"""
Oakville GIS API Client - REAL DATA ONLY VERSION
Provides integration with Oakville's REST APIs using fixed ArcGIS implementation
NO FALLBACK DATA - ALL FROM LIVE APIs
"""

# Import the corrected API client that works with real data only
from .api_client_corrected import CorrectedOakvilleAPIClient as FixedOakvilleAPIClient, APIError
from typing import Dict, List, Optional, Any

import logging

logger = logging.getLogger(__name__)

class OakvilleAPIClient:
    """
    Wrapper around FixedOakvilleAPIClient for backward compatibility
    ALL DATA FROM REAL APIs - NO FALLBACKS
    
    This class delegates all methods to the FixedOakvilleAPIClient which uses
    proper ArcGIS REST API calls with real data only.
    """
    
    def __init__(self):
        # Use the fixed implementation that works with real API data
        self._client = FixedOakvilleAPIClient()
        
        # Backward compatibility properties
        self.base_url = self._client.base_url
        self.endpoints = self._client.endpoints
        self.timeout = self._client.timeout
        self.max_retries = self._client.max_retries
        self.retry_delay = self._client.retry_delay
    
    def get_zoning_info(self, lat: float, lon: float, address: str = None) -> Optional[Dict]:
        """
        Get zoning information using coordinates
        
        Args:
            lat: Latitude (WGS84)
            lon: Longitude (WGS84)  
            address: Optional address (used for fallback in original, now ignored)
            
        Returns:
            Zoning information dictionary from real API data
        """
        # Convert WGS84 to UTM Zone 17N using pyproj for accuracy
        try:
            from pyproj import Transformer
            transformer = Transformer.from_crs("EPSG:4326", "EPSG:26917", always_xy=True)
            utm_x, utm_y = transformer.transform(lon, lat)
        except ImportError:
            logger.error("pyproj not available - cannot perform coordinate transformation")
            return None
        except Exception as e:
            logger.error(f"Coordinate transformation failed: {e}")
            return None
        
        # Use the fixed client with UTM coordinates
        result = self._client.get_zoning_by_coordinate(utm_x, utm_y, spatial_reference=26917)
        
        if result:
            # Convert back to original format for compatibility
            return {
                'zone_code': result.get('zone_code', ''),
                'base_zone': result.get('base_zone', ''),
                'suffix': result.get('suffix', ''),
                'zone_class': result.get('zone_class', ''),
                'zone_description': result.get('zone_description', ''),
                'special_provision': result.get('special_provisions_text', ''),
                'special_provisions_list': result.get('special_provisions', []),
                'area': result.get('zone_area_sqm', 0),
                'coordinates': (lat, lon),
                'source': 'api',
                'confidence': 'high'
            }
        
        return None
    
    def get_assessment_parcel(self, lat: float, lon: float) -> Optional[Dict]:
        """
        Get assessment parcel information by address lookup
        
        Args:
            lat: Latitude (not used in new implementation)
            lon: Longitude (not used in new implementation)
            
        Returns:
            None (this method is deprecated in favor of address-based lookup)
        """
        logger.warning("get_assessment_parcel is deprecated. Use get_property_by_address instead.")
        return None
    
    def get_property_by_address(self, address: str) -> Optional[Dict]:
        """
        Get property data by address
        
        Args:
            address: Property address
            
        Returns:
            Property data from real API
        """
        return self._client.get_property_by_address(address)
    
    def get_comprehensive_property_data(self, lat: float, lon: float, address: str = "") -> Dict[str, Any]:
        """
        Get comprehensive property data - delegates to address-based lookup
        
        Args:
            lat: Latitude (ignored in new implementation) 
            lon: Longitude (ignored in new implementation)
            address: Property address (required for real data lookup)
            
        Returns:
            Comprehensive property data from real APIs only
        """
        if not address:
            return {
                'error': 'Address required for property lookup',
                'data_available': False,
                'message': 'Address parameter is required for real data lookup'
            }
        
        return self._client.get_comprehensive_property_data(address)
    
    def validate_coordinates(self, lat: float, lon: float) -> bool:
        """
        Validate if coordinates are within Oakville boundaries
        """
        return self._client.validate_coordinates(lat, lon)
    
    def get_nearby_parks(self, lat: float, lon: float, radius: int = 1000) -> List[Dict]:
        """
        Get nearby parks (not implemented in fixed client yet)
        
        Returns empty list for now - could be implemented later if needed
        """
        logger.warning("get_nearby_parks not implemented in fixed client")
        return []
    
    def check_heritage_designation(self, address: str) -> List[Dict]:
        """
        Check heritage designation (not implemented in fixed client yet)
        
        Returns empty list for now - could be implemented later if needed
        """
        logger.warning("check_heritage_designation not implemented in fixed client")
        return []
    
    def get_development_applications(self, lat: float, lon: float, radius: int = 500) -> List[Dict]:
        """
        Get development applications (not implemented in fixed client yet)
        
        Returns empty list for now - could be implemented later if needed
        """
        logger.warning("get_development_applications not implemented in fixed client")
        return []

# Singleton instance for caching
_api_client = None

def get_api_client() -> OakvilleAPIClient:
    """Get singleton API client instance"""
    global _api_client
    if _api_client is None:
        _api_client = OakvilleAPIClient()
    return _api_client