"""
Oakville Parcels API - Extract Property Data from Official ArcGIS Services
Uses the Parcels_Addresses service to get actual lot area, frontage, and depth
"""

import requests
import json
import math
from typing import Dict, Optional, List, Tuple

class OakvilleParcelAPI:
    """API client for Oakville Parcels_Addresses service"""
    
    def __init__(self):
        self.base_url = "https://services5.arcgis.com/QJebCdoMf4PF8fJP/arcgis/rest/services/Parcels_Addresses/FeatureServer/0"
        
    def get_property_by_address(self, street_num: str, street_name: str, street_type: str = "Avenue") -> Optional[Dict]:
        """Get property data by address components"""
        
        query_url = f"{self.base_url}/query"
        
        # Build where clause for address search
        where_clause = f"STREET_NUM = '{street_num}' AND STREET_NAME LIKE '%{street_name}%'"
        if street_type:
            where_clause += f" AND STREET_TYPE LIKE '%{street_type}%'"
        
        params = {
            'where': where_clause,
            'outFields': '*',
            'returnGeometry': 'true',
            'f': 'json'
        }
        
        try:
            response = requests.get(query_url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                features = data.get('features', [])
                
                if features:
                    return self._process_property_feature(features[0])
                else:
                    print(f"No property found for {street_num} {street_name} {street_type}")
                    return None
            else:
                print(f"API request failed: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error querying property: {e}")
            return None
    
    def _process_property_feature(self, feature: Dict) -> Dict:
        """Process raw feature data into usable property information"""
        
        attributes = feature.get('attributes', {})
        geometry = feature.get('geometry', {})
        
        # Extract available attribute data
        property_data = {
            'success': True,
            'address_info': {
                'street_num': attributes.get('STREET_NUM', ''),
                'street_name': attributes.get('STREET_NAME', ''),
                'street_type': attributes.get('STREET_TYPE', ''),
                'civic_number': attributes.get('CIVIC_NUMBER', ''),
                'postal_code': attributes.get('POSTAL_CODE', ''),
                'full_address': attributes.get('ADDRESS', ''),
            },
            'parcel_info': {
                'parcel_id': attributes.get('PARCEL_ID', ''),
                'parcel_area': attributes.get('PRCL_AREA', None),  # This might be lot area
                'assessment_roll': attributes.get('ROLL_NUMBER', ''),
            },
            'raw_attributes': attributes,  # Keep all attributes for debugging
            'geometry_available': bool(geometry)
        }
        
        # Calculate dimensions from geometry if available
        if geometry and 'rings' in geometry:
            calculated_dims = self._calculate_dimensions_from_geometry(geometry['rings'])
            property_data['calculated_dimensions'] = calculated_dims
        
        return property_data
    
    def _calculate_dimensions_from_geometry(self, rings: List) -> Dict:
        """Calculate lot area, frontage, and depth from polygon geometry"""
        
        if not rings or not rings[0] or len(rings[0]) < 4:
            return {'error': 'Invalid geometry'}
        
        points = rings[0][:-1]  # Remove last duplicate point
        
        # Calculate area using shoelace formula
        area = self._calculate_polygon_area(points)
        
        # Calculate frontage and depth (simplified approach)
        frontage, depth = self._estimate_frontage_depth(points)
        
        return {
            'lot_area_sqm': abs(area),
            'lot_area_sqft': abs(area) * 10.764,
            'estimated_frontage_m': frontage,
            'estimated_frontage_ft': frontage * 3.281,
            'estimated_depth_m': depth,
            'estimated_depth_ft': depth * 3.281,
            'calculation_method': 'geometry_analysis'
        }
    
    def _calculate_polygon_area(self, points: List[Tuple]) -> float:
        """Calculate polygon area using shoelace formula"""
        
        if len(points) < 3:
            return 0.0
        
        area = 0.0
        n = len(points)
        
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]
        
        return abs(area) / 2.0
    
    def _estimate_frontage_depth(self, points: List[Tuple]) -> Tuple[float, float]:
        """Estimate frontage and depth from polygon points"""
        
        if len(points) < 4:
            return 0.0, 0.0
        
        # Calculate distances between consecutive points
        distances = []
        for i in range(len(points)):
            j = (i + 1) % len(points)
            dist = math.sqrt((points[j][0] - points[i][0])**2 + (points[j][1] - points[i][1])**2)
            distances.append(dist)
        
        # For a rectangular lot, frontage and depth are typically the two shortest sides
        # Sort distances and take the two most common lengths
        distances.sort()
        
        if len(distances) >= 4:
            # Assume rectangular: take 1st and 3rd distances (similar pairs)
            frontage = min(distances[0], distances[1])
            depth = max(distances[0], distances[1])
        else:
            frontage = distances[0] if distances else 0.0
            depth = distances[1] if len(distances) > 1 else 0.0
        
        return frontage, depth

def get_maplehurst_property_data():
    """Get data for 383 Maplehurst Avenue specifically"""
    
    api = OakvilleParcelAPI()
    
    print("Querying Oakville Parcels API for 383 Maplehurst Avenue...")
    
    # Try the address query
    property_data = api.get_property_by_address("383", "Maplehurst", "Avenue")
    
    if property_data and property_data.get('success'):
        print("SUCCESS: Property data retrieved!")
        
        # Display address info
        addr_info = property_data['address_info']
        print(f"\nAddress Information:")
        print(f"  Full Address: {addr_info['full_address']}")
        print(f"  Street: {addr_info['street_num']} {addr_info['street_name']} {addr_info['street_type']}")
        print(f"  Postal Code: {addr_info['postal_code']}")
        
        # Display parcel info
        parcel_info = property_data['parcel_info']
        print(f"\nParcel Information:")
        print(f"  Parcel ID: {parcel_info['parcel_id']}")
        if parcel_info['parcel_area']:
            print(f"  Parcel Area: {parcel_info['parcel_area']} (units unknown)")
        print(f"  Assessment Roll: {parcel_info['assessment_roll']}")
        
        # Display calculated dimensions if available
        if 'calculated_dimensions' in property_data:
            calc_dims = property_data['calculated_dimensions']
            if 'error' not in calc_dims:
                print(f"\nCalculated Dimensions:")
                print(f"  Lot Area: {calc_dims['lot_area_sqm']:.2f} sq.m ({calc_dims['lot_area_sqft']:.0f} sq.ft)")
                print(f"  Est. Frontage: {calc_dims['estimated_frontage_m']:.2f} m ({calc_dims['estimated_frontage_ft']:.1f} ft)")
                print(f"  Est. Depth: {calc_dims['estimated_depth_m']:.2f} m ({calc_dims['estimated_depth_ft']:.1f} ft)")
                print(f"  Method: {calc_dims['calculation_method']}")
        
        # Show some raw attributes for debugging
        print(f"\nAvailable Raw Attributes:")
        raw_attrs = property_data['raw_attributes']
        interesting_fields = ['PRCL_AREA', 'AREA_ACRES', 'LOT_AREA', 'FRONTAGE', 'DEPTH', 'ZONE', 'ZONING']
        
        found_fields = []
        for field in interesting_fields:
            if field in raw_attrs and raw_attrs[field]:
                found_fields.append(f"  {field}: {raw_attrs[field]}")
        
        if found_fields:
            for field_info in found_fields:
                print(field_info)
        else:
            print("  No standard dimension fields found")
            # Show first few fields for debugging
            print("  First 10 available fields:")
            for i, (key, value) in enumerate(raw_attrs.items()):
                if i < 10:
                    print(f"    {key}: {value}")
        
        return property_data
    else:
        print("FAILED: Could not retrieve property data")
        return None

def test_different_address_formats():
    """Test different ways to query the address"""
    
    api = OakvilleParcelAPI()
    
    print("\nTesting different address query formats...")
    
    # Try different variations
    test_cases = [
        ("383", "Maplehurst", "Avenue"),
        ("383", "Maplehurst", "Ave"),
        ("383", "MAPLEHURST", "AVENUE"),
        ("383", "Maplehurst", ""),  # No street type
    ]
    
    for street_num, street_name, street_type in test_cases:
        print(f"\nTrying: {street_num} {street_name} {street_type}")
        result = api.get_property_by_address(street_num, street_name, street_type)
        
        if result and result.get('success'):
            addr = result['address_info']['full_address']
            print(f"  SUCCESS: Found {addr}")
            return result  # Return first successful result
        else:
            print(f"  FAILED: No results")
    
    return None

if __name__ == "__main__":
    print("OAKVILLE PARCELS API TEST")
    print("="*50)
    
    # Test specific address
    property_data = get_maplehurst_property_data()
    
    # If that fails, try different formats
    if not property_data:
        property_data = test_different_address_formats()
    
    # If we found data, show detailed results
    if property_data:
        print("\n" + "="*30)
        print("DETAILED PROPERTY DATA:")
        print("="*30)
        
        # Get the successful result details
        api = OakvilleParcelAPI()
        detailed_result = api.get_property_by_address("383", "Maplehurst", "Ave")
        
        if detailed_result:
            addr_info = detailed_result['address_info']
            parcel_info = detailed_result['parcel_info']
            
            print(f"Address: {addr_info['full_address']}")
            print(f"Parcel ID: {parcel_info['parcel_id']}")
            
            if parcel_info['parcel_area']:
                print(f"Official Parcel Area: {parcel_info['parcel_area']}")
            
            if 'calculated_dimensions' in detailed_result:
                calc = detailed_result['calculated_dimensions']
                if 'error' not in calc:
                    print(f"Calculated Area: {calc['lot_area_sqm']:.2f} sq.m ({calc['lot_area_sqft']:.0f} sq.ft)")
                    print(f"Estimated Frontage: {calc['estimated_frontage_m']:.2f} m")
                    print(f"Estimated Depth: {calc['estimated_depth_m']:.2f} m")
            
            # Show interesting raw fields
            raw = detailed_result['raw_attributes']
            print(f"\nAll Available Fields ({len(raw)} total):")
            for key, value in raw.items():
                if value is not None and str(value).strip():
                    print(f"  {key}: {value}")
    
    print("\n" + "="*50)
    if property_data:
        print("RESULT: Successfully extracted property data from Oakville ArcGIS!")
        print("This service can provide real lot dimensions for analysis.")
    else:
        print("RESULT: Could not find the specific property.")
        print("The service exists and works, but may need different query parameters.")