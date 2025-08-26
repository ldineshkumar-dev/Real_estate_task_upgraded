"""
Correct API Integration for Oakville Real Estate Analyzer
Properly implements zoning and lot area retrieval from APIs
"""

import requests
from shapely.geometry import shape
from typing import Dict, List, Optional, Tuple
import json

# API URLs
PARCELS_URL = "https://services5.arcgis.com/QJebCdoMf4PF8fJP/arcgis/rest/services/Parcels_Addresses/FeatureServer/0/query"
ZONING_URL = "https://maps.oakville.ca/oakgis/rest/services/SBS/Zoning_By_law_2014_014/FeatureServer/10/query"

# ========================================
# PARCEL API FUNCTIONS
# ========================================

def fetch_parcels_by_address(address_query: str, max_records: int = 50) -> List[Dict]:
    """
    Query Parcels_Addresses FeatureServer for address-like match.
    Returns list of features (GeoJSON-like ArcGIS JSON).
    """
    params = {
        "f": "json",
        "where": f"ADDRESS LIKE '%{address_query}%'",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": 4326,  # Request in WGS84 to avoid coordinate conversion
        "resultRecordCount": max_records,
        "orderByFields": "OBJECTID ASC",
    }
    
    try:
        r = requests.get(PARCELS_URL, params=params, timeout=30)
        r.raise_for_status()
        return r.json().get("features", [])
    except Exception as e:
        print(f"Error fetching parcels: {e}")
        return []

def get_single_parcel_exact(address_str: str) -> Optional[Dict]:
    """
    Attempt exact ADDRESS match (may or may not work depending on dataset formatting).
    Fixed syntax error from original code.
    """
    params = {
        "f": "json",
        "where": f"ADDRESS = '{address_str}'",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": 4326,  # Request in WGS84
    }
    
    try:
        r = requests.get(PARCELS_URL, params=params, timeout=20)
        r.raise_for_status()
        features = r.json().get("features", [])
        return features[0] if features else None
    except Exception as e:
        print(f"Error fetching single parcel: {e}")
        return None

def get_parcel_comprehensive(address: str) -> Optional[Dict]:
    """
    Comprehensive parcel lookup with multiple strategies.
    Returns parcel data with lot area, geometry, and centroid.
    """
    # Strategy 1: Try exact match first
    parcel = get_single_parcel_exact(address.upper())
    if parcel:
        return process_parcel_data(parcel, "exact_match")
    
    # Strategy 2: Try LIKE query with original address
    parcels = fetch_parcels_by_address(address)
    if parcels:
        return process_parcel_data(parcels[0], "like_match")
    
    # Strategy 3: Try with address variations
    variations = [
        address.replace('Avenue', 'AVE').replace('avenue', 'AVE'),
        address.replace('Ave', 'AVE').replace('ave', 'AVE'),
        address.replace('Street', 'ST').replace('street', 'ST'),
        address.replace('Road', 'RD').replace('road', 'RD'),
    ]
    
    for variation in variations:
        parcels = fetch_parcels_by_address(variation)
        if parcels:
            return process_parcel_data(parcels[0], f"variation_match_{variation}")
    
    return None

def process_parcel_data(parcel_feature: Dict, match_type: str) -> Dict:
    """
    Process parcel feature data to extract key information.
    Returns standardized parcel data with centroid calculation.
    """
    attrs = parcel_feature["attributes"]
    geometry = parcel_feature["geometry"]
    
    # Calculate centroid from geometry
    centroid_lat, centroid_lon = calculate_centroid(geometry)
    
    return {
        "address": attrs.get("ADDRESS", "Unknown"),
        "lot_area_sqm": attrs.get("Shape__Area", 0),  # Lot area in square meters
        "lot_area_acres": attrs.get("PRCL_AREA", 0),  # Sometimes in acres
        "roll_number": attrs.get("ROLL_NUMBER"),
        "legal_description": attrs.get("LEGAL_DESC"),
        "ward": attrs.get("WARD"),
        "centroid_lat": centroid_lat,
        "centroid_lon": centroid_lon,
        "geometry": geometry,
        "match_type": match_type,
        "raw_attributes": attrs
    }

def calculate_centroid(geometry: Dict) -> Tuple[float, float]:
    """
    Calculate centroid of ArcGIS geometry.
    Handles both UTM and WGS84 coordinate systems.
    Returns (latitude, longitude) in WGS84.
    """
    try:
        if "rings" in geometry:  # Polygon
            # Get the first ring (exterior)
            coords = geometry["rings"][0]
            
            # Check if coordinates are in UTM (large numbers) or WGS84 (small numbers)
            sample_x, sample_y = coords[0]
            
            if abs(sample_x) > 180 or abs(sample_y) > 90:
                # UTM coordinates - convert to lat/lon
                # Calculate centroid in UTM first
                x_coords = [point[0] for point in coords]
                y_coords = [point[1] for point in coords]
                centroid_x = sum(x_coords) / len(x_coords)
                centroid_y = sum(y_coords) / len(y_coords)
                
                # Convert UTM to lat/lon using pyproj if available
                try:
                    from pyproj import Transformer
                    transformer = Transformer.from_crs("EPSG:26917", "EPSG:4326", always_xy=True)
                    lon, lat = transformer.transform(centroid_x, centroid_y)
                    return lat, lon
                except ImportError:
                    # Fallback: Request geometry in WGS84 from API instead
                    print("Warning: pyproj not available for coordinate conversion")
                    return None, None
            else:
                # Already in WGS84 (lat/lon)
                geojson_geom = {"type": "Polygon", "coordinates": [coords]}
                geom = shape(geojson_geom)
                centroid = geom.centroid
                return centroid.y, centroid.x  # (lat, lon)
                
        elif "x" in geometry and "y" in geometry:  # Point
            x, y = geometry["x"], geometry["y"]
            if abs(x) > 180 or abs(y) > 90:
                # UTM coordinates
                try:
                    from pyproj import Transformer
                    transformer = Transformer.from_crs("EPSG:26917", "EPSG:4326", always_xy=True)
                    lon, lat = transformer.transform(x, y)
                    return lat, lon
                except ImportError:
                    print("Warning: pyproj not available for coordinate conversion")
                    return None, None
            else:
                return y, x  # (lat, lon)
        else:
            raise ValueError("Unsupported geometry type")
            
    except Exception as e:
        print(f"Error calculating centroid: {e}")
        return None, None

# ========================================
# ZONING API FUNCTIONS
# ========================================

def query_zoning_by_point(lat: float, lon: float) -> List[Dict]:
    """
    Query zoning layer by a point (lat, lon) using esri point intersects.
    Returns list of feature dicts.
    Fixed syntax from original code.
    """
    params = {
        "f": "json",
        "geometryType": "esriGeometryPoint",
        "geometry": f"{lon},{lat}",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "returnGeometry": "false",
    }
    
    try:
        r = requests.get(ZONING_URL, params=params, timeout=30)
        r.raise_for_status()
        return r.json().get("features", [])
    except Exception as e:
        print(f"Error querying zoning: {e}")
        return []

def get_zoning_comprehensive(lat: float, lon: float) -> Optional[Dict]:
    """
    Comprehensive zoning lookup with full field mapping.
    Returns structured zoning information.
    """
    zoning_features = query_zoning_by_point(lat, lon)
    
    if not zoning_features:
        return {
            "status": "not_found",
            "zone": "Unknown",
            "message": f"No zoning found for coordinates {lat}, {lon}"
        }
    
    # Process the first zoning feature
    attrs = zoning_features[0]["attributes"]
    
    # Extract base zone code
    zone_code = attrs.get("ZONE", "").strip()
    
    # Extract special provisions from SP1-SP10 fields
    special_provisions = []
    for i in range(1, 11):
        sp_value = attrs.get(f"SP{i}")
        if sp_value and str(sp_value).strip() and str(sp_value).strip().upper() != "NULL":
            special_provisions.append(str(sp_value).strip())
    
    # Build full zone code with special provisions
    full_zone_code = zone_code
    if special_provisions:
        sp_numbers = [sp for sp in special_provisions if sp.isdigit()]
        if sp_numbers:
            full_zone_code += f" SP:{','.join(sp_numbers)}"
    
    return {
        "status": "found",
        "zone": zone_code,
        "full_zone_code": full_zone_code,
        "zone_class": attrs.get("CLASS", "").strip(),
        "zone_description": attrs.get("ZONE_DESC", "").strip(),
        "full_zoning_description": attrs.get("FULL_ZONING_DESC", "").strip(),
        "special_provisions": special_provisions,
        "building_heights": attrs.get("BLDG_HEIGHTS"),
        "temp_use": attrs.get("TEMP"),
        "hold_provisions": attrs.get("HOLD"),
        "growth_area": attrs.get("GROWTH_AREA"),
        "zoning_area_sqm": attrs.get("Shape__Area"),
        "coordinates": (lat, lon),
        "raw_attributes": attrs
    }

# ========================================
# COMPREHENSIVE WORKFLOW
# ========================================

def analyze_property_complete(address: str) -> Dict:
    """
    Complete property analysis workflow:
    1. Find parcel by address
    2. Get lot area from parcel
    3. Calculate centroid from geometry
    4. Get zoning from centroid coordinates
    5. Return comprehensive data
    """
    print(f"Starting property analysis for: {address}")
    
    # Step 1: Get parcel data
    print("1. Fetching parcel data...")
    parcel_data = get_parcel_comprehensive(address)
    
    if not parcel_data:
        return {
            "status": "error",
            "message": f"No parcel found for address: {address}",
            "address": address
        }
    
    print(f"   Found parcel: {parcel_data['address']}")
    print(f"   Lot area: {parcel_data['lot_area_sqm']:.0f} sq meters")
    print(f"   Centroid: {parcel_data['centroid_lat']:.6f}, {parcel_data['centroid_lon']:.6f}")
    
    # Step 2: Get zoning data using centroid
    if parcel_data['centroid_lat'] and parcel_data['centroid_lon']:
        print("2. Fetching zoning data...")
        zoning_data = get_zoning_comprehensive(
            parcel_data['centroid_lat'], 
            parcel_data['centroid_lon']
        )
        
        if zoning_data['status'] == 'found':
            print(f"   Zone: {zoning_data['full_zone_code']}")
            print(f"   Class: {zoning_data['zone_class']}")
        else:
            print(f"   Zoning: {zoning_data['message']}")
    else:
        zoning_data = {
            "status": "error",
            "message": "Could not calculate centroid for zoning lookup"
        }
    
    # Step 3: Combine results
    result = {
        "status": "success",
        "input_address": address,
        "parcel": parcel_data,
        "zoning": zoning_data,
        "summary": {
            "address": parcel_data['address'],
            "lot_area_sqm": parcel_data['lot_area_sqm'],
            "lot_area_sqft": parcel_data['lot_area_sqm'] * 10.764 if parcel_data['lot_area_sqm'] else 0,
            "zone": zoning_data.get('full_zone_code', 'Unknown'),
            "zone_class": zoning_data.get('zone_class', 'Unknown'),
            "coordinates": (parcel_data['centroid_lat'], parcel_data['centroid_lon'])
        }
    }
    
    return result

# ========================================
# TESTING FUNCTIONS
# ========================================

def test_api_integration():
    """Test the complete API integration with known addresses."""
    test_addresses = [
        "383 MAPLEHURST AVE",
        "383 Maplehurst Avenue",
        "123 KERR ST"
    ]
    
    print("=" * 60)
    print("TESTING OAKVILLE API INTEGRATION")
    print("=" * 60)
    
    for address in test_addresses:
        print(f"\n{'='*20} Testing: {address} {'='*20}")
        
        try:
            result = analyze_property_complete(address)
            
            if result['status'] == 'success':
                summary = result['summary']
                print(f"\n✓ SUCCESS:")
                print(f"  Address: {summary['address']}")
                print(f"  Lot Area: {summary['lot_area_sqm']:.0f} sq meters ({summary['lot_area_sqft']:.0f} sq ft)")
                print(f"  Zoning: {summary['zone']} - {summary['zone_class']}")
                print(f"  Coordinates: {summary['coordinates'][0]:.6f}, {summary['coordinates'][1]:.6f}")
                
                if result['zoning'].get('special_provisions'):
                    print(f"  Special Provisions: {', '.join(result['zoning']['special_provisions'])}")
                    
            else:
                print(f"✗ FAILED: {result['message']}")
                
        except Exception as e:
            print(f"✗ ERROR: {e}")
    
    print(f"\n{'='*60}")
    print("API Integration Test Complete")
    print(f"{'='*60}")

if __name__ == "__main__":
    # Run the test
    test_api_integration()
    
    # Example of individual function usage:
    print("\n" + "="*40)
    print("INDIVIDUAL FUNCTION EXAMPLES")
    print("="*40)
    
    # Example 1: Just get parcel data
    parcel = get_parcel_comprehensive("383 MAPLEHURST AVE")
    if parcel:
        print(f"Parcel lot area: {parcel['lot_area_sqm']} sq meters")
    
    # Example 2: Just get zoning data
    if parcel and parcel['centroid_lat']:
        zoning = get_zoning_comprehensive(parcel['centroid_lat'], parcel['centroid_lon'])
        print(f"Zoning: {zoning.get('full_zone_code', 'Not found')}")