"""
Geocoding Service
Converts addresses to coordinates and validates Oakville locations
"""

import logging
import re
import time
from typing import Dict, Optional, List, Tuple
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from config import Config
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from utils.cache_manager import CacheManager

logger = logging.getLogger(__name__)


class GeocodingService:
    """Service for geocoding addresses and coordinate validation"""
    
    def __init__(self):
        self.geocoder = Nominatim(user_agent="OakvilleRealEstateAnalyzer/1.0")
        # Use advanced cache manager (simplified)
        self.cache_manager = CacheManager(
            memory_size=500,     # Smaller cache for geocoding
            enable_redis=False,  # Disable Redis
            enable_file=True     # Enable file persistence
        )
        
        # Oakville boundaries (more precise)
        self.oakville_bounds = {
            'lat_min': 43.380,   # Southern boundary near Lake Ontario
            'lat_max': 43.520,   # Northern boundary
            'lon_min': -79.780,  # Western boundary
            'lon_max': -79.640   # Eastern boundary
        }
        
        # Common Oakville postal code prefixes
        self.oakville_postal_prefixes = ['L6H', 'L6J', 'L6K', 'L6L', 'L6M']
    
    def geocode_address(self, address: str, validate_oakville: bool = True) -> Optional[Dict]:
        """
        Geocode an address to latitude/longitude coordinates
        
        Args:
            address: Street address to geocode
            validate_oakville: Whether to validate the address is in Oakville
            
        Returns:
            Dictionary with geocoding results or None if failed
        """
        # Clean and normalize address
        clean_address = self._clean_address(address)
        
        # Create cache key
        cache_key = self.cache_manager._generate_key('geocoding', clean_address)
        
        # Check cache first
        cached_result = self.cache_manager.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Using cached geocoding result for {clean_address}")
            return cached_result
        
        # Add Oakville context if not present
        if 'oakville' not in clean_address.lower():
            clean_address = f"{clean_address}, Oakville, ON, Canada"
        
        try:
            logger.info(f"Geocoding address: {clean_address}")
            
            # Geocode with timeout
            location = self.geocoder.geocode(
                clean_address,
                timeout=10,
                exactly_one=True,
                country_codes=['CA']
            )
            
            if not location:
                logger.warning(f"No geocoding results for: {address}")
                return None
            
            # Extract coordinates
            lat, lon = location.latitude, location.longitude
            
            # Smart Oakville validation
            in_boundaries = self.is_in_oakville(lat, lon)
            in_oakville_by_address = any(keyword in location.address.lower() 
                                       for keyword in ['oakville', 'l6h', 'l6j', 'l6k', 'l6l', 'l6m'])
            
            # More lenient validation - if address contains Oakville or postal code, accept it
            if validate_oakville and not in_boundaries and not in_oakville_by_address:
                logger.warning(f"Address {address} may be outside Oakville")
                result = {
                    'latitude': lat,
                    'longitude': lon,
                    'formatted_address': location.address,
                    'confidence': 'medium',
                    'in_oakville': False,
                    'warning': 'Address may be outside Oakville boundaries'
                }
            else:
                result = {
                    'latitude': lat,
                    'longitude': lon,
                    'formatted_address': location.address,
                    'confidence': 'high' if in_boundaries or in_oakville_by_address else 'medium',
                    'in_oakville': True
                }
            
            # Add to cache with long TTL (geocoding rarely changes)
            self.cache_manager.set(cache_key, result, cache_type='geocoding')
            
            logger.info(f"Successfully geocoded: {address} -> {lat:.6f}, {lon:.6f}")
            return result
            
        except GeocoderTimedOut:
            logger.error(f"Geocoding timeout for address: {address}")
            return None
            
        except GeocoderServiceError as e:
            logger.error(f"Geocoding service error for {address}: {e}")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error geocoding {address}: {e}")
            return None
    
    def reverse_geocode(self, lat: float, lon: float) -> Optional[Dict]:
        """
        Reverse geocode coordinates to an address
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Dictionary with address information or None if failed
        """
        try:
            logger.info(f"Reverse geocoding: {lat:.6f}, {lon:.6f}")
            
            location = self.geocoder.reverse(
                (lat, lon),
                timeout=10,
                exactly_one=True
            )
            
            if not location:
                logger.warning(f"No reverse geocoding results for: {lat}, {lon}")
                return None
            
            address_components = location.raw.get('address', {})
            
            result = {
                'formatted_address': location.address,
                'street_number': address_components.get('house_number', ''),
                'street_name': address_components.get('road', ''),
                'city': address_components.get('city', address_components.get('town', '')),
                'province': address_components.get('state', ''),
                'postal_code': address_components.get('postcode', ''),
                'country': address_components.get('country', ''),
                'latitude': lat,
                'longitude': lon,
                'in_oakville': self.is_in_oakville(lat, lon)
            }
            
            logger.info(f"Successfully reverse geocoded: {lat}, {lon}")
            return result
            
        except Exception as e:
            logger.error(f"Error reverse geocoding {lat}, {lon}: {e}")
            return None
    
    def _clean_address(self, address: str) -> str:
        """Clean and normalize address string"""
        # Remove extra whitespace
        clean = re.sub(r'\s+', ' ', address.strip())
        
        # Standardize common abbreviations
        clean = re.sub(r'\bSt\.?\b', 'Street', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\bAve\.?\b', 'Avenue', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\bRd\.?\b', 'Road', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\bBlvd\.?\b', 'Boulevard', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\bDr\.?\b', 'Drive', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\bCt\.?\b', 'Court', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\bCres\.?\b', 'Crescent', clean, flags=re.IGNORECASE)
        
        return clean
    
    def is_in_oakville(self, lat: float, lon: float) -> bool:
        """
        Check if coordinates are within Oakville boundaries
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            True if coordinates are in Oakville
        """
        return (self.oakville_bounds['lat_min'] <= lat <= self.oakville_bounds['lat_max'] and
                self.oakville_bounds['lon_min'] <= lon <= self.oakville_bounds['lon_max'])
    
    def validate_postal_code(self, postal_code: str) -> bool:
        """
        Validate if postal code is likely in Oakville
        
        Args:
            postal_code: Canadian postal code
            
        Returns:
            True if postal code appears to be in Oakville
        """
        if not postal_code:
            return False
        
        # Clean postal code
        clean_postal = postal_code.replace(' ', '').upper()
        
        # Check if it matches Oakville prefixes
        for prefix in self.oakville_postal_prefixes:
            if clean_postal.startswith(prefix):
                return True
        
        return False
    
    def get_address_suggestions(self, partial_address: str, limit: int = 5) -> List[Dict]:
        """
        Get address suggestions for partial address input
        
        Args:
            partial_address: Partial address string
            limit: Maximum number of suggestions
            
        Returns:
            List of address suggestions
        """
        try:
            # Add Oakville context
            search_query = f"{partial_address}, Oakville, ON, Canada"
            
            # Use geocoder for suggestions (limited functionality with Nominatim)
            locations = self.geocoder.geocode(
                search_query,
                exactly_one=False,
                limit=limit,
                timeout=5
            )
            
            if not locations:
                return []
            
            suggestions = []
            for location in locations:
                if self.is_in_oakville(location.latitude, location.longitude):
                    suggestions.append({
                        'address': location.address,
                        'latitude': location.latitude,
                        'longitude': location.longitude,
                        'confidence': 'medium'
                    })
            
            return suggestions[:limit]
            
        except Exception as e:
            logger.error(f"Error getting address suggestions: {e}")
            return []
    
    def batch_geocode(self, addresses: List[str], delay: float = 1.0) -> Dict[str, Optional[Dict]]:
        """
        Geocode multiple addresses with rate limiting
        
        Args:
            addresses: List of addresses to geocode
            delay: Delay between requests in seconds
            
        Returns:
            Dictionary mapping addresses to geocoding results
        """
        results = {}
        
        for i, address in enumerate(addresses):
            logger.info(f"Batch geocoding {i+1}/{len(addresses)}: {address}")
            
            result = self.geocode_address(address)
            results[address] = result
            
            # Rate limiting
            if i < len(addresses) - 1:  # Don't delay after last request
                time.sleep(delay)
        
        return results
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two coordinates using Haversine formula
        
        Args:
            lat1, lon1: First coordinate pair
            lat2, lon2: Second coordinate pair
            
        Returns:
            Distance in kilometers
        """
        from math import radians, cos, sin, asin, sqrt
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        # Earth's radius in kilometers
        r = 6371
        
        return c * r
    
    def find_nearby_addresses(self, center_lat: float, center_lon: float, 
                             addresses: List[str], radius_km: float = 1.0) -> List[Dict]:
        """
        Find addresses within a specified radius of a center point
        
        Args:
            center_lat, center_lon: Center coordinates
            addresses: List of addresses to check
            radius_km: Search radius in kilometers
            
        Returns:
            List of addresses within radius with distances
        """
        nearby = []
        
        for address in addresses:
            geocoded = self.geocode_address(address)
            if geocoded:
                distance = self.calculate_distance(
                    center_lat, center_lon,
                    geocoded['latitude'], geocoded['longitude']
                )
                
                if distance <= radius_km:
                    nearby.append({
                        'address': address,
                        'latitude': geocoded['latitude'],
                        'longitude': geocoded['longitude'],
                        'distance_km': round(distance, 2)
                    })
        
        # Sort by distance
        nearby.sort(key=lambda x: x['distance_km'])
        
        return nearby
    
    def get_neighborhood_info(self, lat: float, lon: float) -> Dict:
        """
        Get neighborhood information for coordinates
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Dictionary with neighborhood information
        """
        reverse_result = self.reverse_geocode(lat, lon)
        
        if not reverse_result:
            return {}
        
        # Extract neighborhood information from address components
        address_parts = reverse_result['formatted_address'].split(', ')
        
        return {
            'neighborhood': self._extract_neighborhood(address_parts),
            'city': reverse_result.get('city', ''),
            'postal_code': reverse_result.get('postal_code', ''),
            'coordinates': (lat, lon),
            'in_oakville': reverse_result.get('in_oakville', False)
        }
    
    def _extract_neighborhood(self, address_parts: List[str]) -> str:
        """Extract neighborhood from address parts"""
        # Simple heuristic to identify neighborhood
        # In practice, this would use more sophisticated mapping
        oakville_neighborhoods = [
            'Glen Abbey', 'Clearview', 'Iroquois Ridge', 'West Oak Trails',
            'Joshua Creek', 'Uptown Core', 'Old Oakville', 'Bronte',
            'College Park', 'Eastlake', 'Heritage Way', 'Palermo'
        ]
        
        for part in address_parts:
            for neighborhood in oakville_neighborhoods:
                if neighborhood.lower() in part.lower():
                    return neighborhood
        
        return 'Unknown'


# Singleton instance
_geocoding_service = None

def get_geocoding_service() -> GeocodingService:
    """Get singleton geocoding service instance"""
    global _geocoding_service
    if _geocoding_service is None:
        _geocoding_service = GeocodingService()
    return _geocoding_service


# Convenience functions
def geocode_address(address: str) -> Optional[Dict]:
    """Convenience function to geocode an address"""
    service = get_geocoding_service()
    return service.geocode_address(address)


def reverse_geocode(lat: float, lon: float) -> Optional[Dict]:
    """Convenience function to reverse geocode coordinates"""
    service = get_geocoding_service()
    return service.reverse_geocode(lat, lon)


def is_in_oakville(lat: float, lon: float) -> bool:
    """Convenience function to check if coordinates are in Oakville"""
    service = get_geocoding_service()
    return service.is_in_oakville(lat, lon)