"""
🏡 Oakville Zoning Analyzer - Streamlined Version
AI-Powered Property Analysis & Valuation Platform with Real API Integration
"""

import streamlit as st
import requests
from shapely.geometry import shape
import json
from typing import Dict, List, Optional, Any
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
import math
import io
try:
    from pyproj import Transformer
    PYPROJ_AVAILABLE = True
except ImportError:
    PYPROJ_AVAILABLE = False
    st.warning("⚠️ PyProj not available. Coordinate transformation features will be limited.")

try:
    from pdf_generator import PropertyReportGenerator
    PDF_GENERATOR_AVAILABLE = True
except ImportError:
    PDF_GENERATOR_AVAILABLE = False
    st.warning("⚠️ PDF Generator not available. PDF download feature will be limited.")

# ------------------------
# CONFIG & CONSTANTS
# ------------------------
PARCELS_URL = "https://services5.arcgis.com/QJebCdoMf4PF8fJP/arcgis/rest/services/Parcels_Addresses/FeatureServer/0/query"
ZONING_URL = "https://maps.oakville.ca/oakgis/rest/services/SBS/Zoning_By_law_2014_014/FeatureServer/10/query"
HERITAGE_URL = "https://maps.oakville.ca/oakgis/rest/services/SBS/Heritage_Properties/FeatureServer/0/query"

# Load comprehensive zoning rules
@st.cache_data
def load_zoning_rules():
    """Load comprehensive zoning regulations from JSON files"""
    try:
        with open('data/comprehensive_zoning_regulations.json', 'r') as f:
            zoning_data = json.load(f)
        with open('data/special_provisions.json', 'r') as f:
            special_provisions = json.load(f)
        with open('data/zoning_lookup_tables.json', 'r') as f:
            lookup_tables = json.load(f)
        return zoning_data, special_provisions, lookup_tables
    except FileNotFoundError as e:
        st.error(f"Could not load zoning data files: {e}")
        return {}, {}, {}

# Load zoning data
ZONING_DATA, SPECIAL_PROVISIONS, LOOKUP_TABLES = load_zoning_rules()

# Load parcel data for faster lookup
@st.cache_data
def load_parcel_data():
    """Load parcel area data from CSV for faster lookup"""
    try:
        df = pd.read_csv('oakville_parcels_area.csv')
        # Create a dictionary for quick lookup
        parcel_dict = {}
        for _, row in df.iterrows():
            address = str(row['ADDRESS']).strip().upper()
            if address != 'NO ADDRESS ASSIGNED':
                parcel_dict[address] = float(row['Shape__Area'])
        return parcel_dict
    except FileNotFoundError:
        st.warning("Parcel data file not found. Using API lookup only.")
        return {}

PARCEL_DATA = load_parcel_data()

# Base property values per square meter by zone (CAD)
BASE_LAND_VALUES = {
    'RL1': 650, 'RL1-0': 700, 'RL2': 580, 'RL2-0': 620, 'RL3': 520, 'RL3-0': 550,
    'RL4': 500, 'RL4-0': 530, 'RL5': 480, 'RL5-0': 510, 'RL6': 450, 'RL6-0': 480,
    'RL7': 470, 'RL7-0': 500, 'RL8': 420, 'RL8-0': 450, 'RL9': 400, 'RL9-0': 430,
    'RL10': 490, 'RL10-0': 520, 'RL11': 460, 'RL11-0': 490, 
    'RUC': 380, 'RM1': 350, 'RM2': 330, 'RM3': 320, 'RM4': 300, 'RH': 280
}

# Building values per square meter (CAD)
BUILDING_VALUES = {
    'detached_dwelling': 2800, 'semi_detached_dwelling': 2600, 'townhouse_dwelling': 2400,
    'back_to_back_townhouse': 2200, 'stacked_townhouse': 2300, 'apartment_dwelling': 2000,
    'luxury_finish': 3800, 'standard_finish': 2800, 'basic_finish': 2000
}

# Location adjustment factors
LOCATION_PREMIUMS = {
    'waterfront': 0.30, 'park_adjacent': 0.10, 'school_nearby': 0.08,
    'transit_accessible': 0.12, 'shopping_nearby': 0.05, 'quiet_street': 0.07,
    'corner_lot': -0.05, 'busy_road': -0.10, 'heritage_designated': -0.10,
    'suffix_0_zone': -0.05, 'special_provision': 0.00, 'aru_potential': 0.08,
    'duplex_potential': 0.15, 'multi_unit_potential': 0.20
}

# ------------------------
# GEOCODING & COORDINATE TRANSFORMATION
# ------------------------
def geocode_address(address):
    """Geocode address to WGS84 coordinates"""
    url = "https://utility.arcgis.com/usrsvcs/servers/283eee7a387a43bc97553a68a6054861/rest/services/World/GeocodeServer/findAddressCandidates"
    params = {
        "SingleLine": address,
        "maxSuggestions": 1,
        "outFields": "*",
        "f": "json",
        "outSR": '{"wkid":4326}'
    }
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        if data.get("candidates"):
            location = data["candidates"][0]["location"]
            return {"lat": location["y"], "lon": location["x"]}
        return None
    except requests.RequestException as e:
        st.error(f"Geocoding failed: {e}")
        return None

def transform_coordinates(lon, lat):
    """Transform WGS84 coordinates to UTM Zone 17N for accurate measurements"""
    if not PYPROJ_AVAILABLE:
        # Simple approximation for Oakville area if pyproj not available
        x = (lon + 79.7071) * 111320 * math.cos(math.radians(lat))
        y = (lat - 43.4685) * 110540
        return {"x": x, "y": y}
    
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:26917", always_xy=True)
    x, y = transformer.transform(lon, lat)
    return {"x": x, "y": y}

def calculate_frontage_depth(geometry):
    """Calculate lot frontage and depth from parcel geometry - DISABLED to avoid assumptions"""
    # Returning None values to prevent incorrect automatic calculations
    # User must manually input frontage and depth for accurate analysis
    return {
        "frontage": None, 
        "depth": None,
        "frontage_meters": None,
        "depth_meters": None
    }

# ------------------------
# HERITAGE PROPERTIES INTEGRATION
# ------------------------

@st.cache_data(ttl=3600)  # Cache for 1 hour
def query_heritage_properties_by_coordinates(lat: float, lon: float, buffer_meters: int = 100) -> Dict[str, Any]:
    """
    Query heritage properties near given coordinates using spatial intersection
    
    Args:
        lat: Latitude (WGS84)
        lon: Longitude (WGS84)
        buffer_meters: Search buffer in meters (default 100m)
        
    Returns:
        Dict containing heritage properties data and metadata
    """
    try:
        # Create point geometry for spatial query
        point_geometry = {
            "x": lon,
            "y": lat,
            "spatialReference": {"wkid": 4326}  # WGS84
        }
        
        params = {
            'geometry': json.dumps(point_geometry),
            'geometryType': 'esriGeometryPoint',
            'spatialRel': 'esriSpatialRelIntersects',
            'distance': buffer_meters,
            'units': 'esriSRUnit_Meter',
            'outFields': '*',
            'f': 'json',
            'returnGeometry': 'true'
        }
        
        response = requests.get(HERITAGE_URL, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        features = data.get('features', [])
        
        return {
            'success': True,
            'count': len(features),
            'features': features,
            'query_coords': {'lat': lat, 'lon': lon, 'buffer': buffer_meters}
        }
        
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': f"Heritage API request failed: {str(e)}",
            'count': 0,
            'features': []
        }
    except json.JSONDecodeError as e:
        return {
            'success': False,
            'error': f"Heritage API JSON decode error: {str(e)}",
            'count': 0,
            'features': []
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Heritage API unexpected error: {str(e)}",
            'count': 0,
            'features': []
        }

def parse_heritage_property_info(heritage_feature: Dict) -> Dict[str, Any]:
    """
    Parse heritage property feature into structured information
    
    Args:
        heritage_feature: Raw feature from heritage API
        
    Returns:
        Dict with parsed heritage property information
    """
    attributes = heritage_feature.get('attributes', {})
    
    return {
        'address': attributes.get('ADDRESS', '').strip(),
        'street_name': attributes.get('SNAME', '').strip(),
        'status': attributes.get('STATUS', '').strip(),
        'bylaw': attributes.get('BYLAW', '').strip(),
        'year_built': attributes.get('YR_BUILT'),
        'designation_year': attributes.get('DESIGNATION_YEAR'),
        'history': attributes.get('HISTORY', '').strip(),
        'description': attributes.get('DESCRIPTION', '').strip(),
        'architecture': attributes.get('ARCHITECTURE', '').strip(),
        'heritage_value': attributes.get('HERITAGE_VALUE', '').strip(),
        'condition': attributes.get('CONDITION', '').strip(),
        'recommendations': attributes.get('RECOMMENDATIONS', '').strip(),
        'geometry': heritage_feature.get('geometry')
    }

def get_heritage_requirements(parcel: Dict, buffer_meters: int = 100) -> Dict[str, Any]:
    """
    Get heritage requirements for a property based on its location
    
    Args:
        parcel: Property parcel data with coordinates
        buffer_meters: Search radius for nearby heritage properties
        
    Returns:
        Dict with heritage requirements and nearby heritage properties
    """
    # Extract coordinates from parcel
    lat = parcel.get('lat')
    lon = parcel.get('lon')
    
    if not lat or not lon:
        # Try to get coordinates from geometry if available
        if parcel.get('geometry'):
            try:
                lat, lon = get_centroid(parcel['geometry'])
            except:
                return {
                    'has_heritage_requirements': False,
                    'heritage_status': 'Unknown - No coordinates available',
                    'nearby_properties': [],
                    'error': 'Cannot determine location - no coordinates or geometry available'
                }
        else:
            return {
                'has_heritage_requirements': False,
                'heritage_status': 'Unknown - No coordinates available',
                'nearby_properties': [],
                'error': 'Cannot determine location - no coordinates or geometry available'
            }
    
    # Query heritage properties API
    heritage_result = query_heritage_properties_by_coordinates(lat, lon, buffer_meters)
    
    if not heritage_result['success']:
        return {
            'has_heritage_requirements': False,
            'heritage_status': 'Unknown - API Error',
            'nearby_properties': [],
            'error': heritage_result.get('error', 'Heritage API query failed'),
            'api_available': False
        }
    
    # Parse heritage properties
    heritage_properties = []
    direct_heritage_match = False
    
    for feature in heritage_result['features']:
        prop_info = parse_heritage_property_info(feature)
        heritage_properties.append(prop_info)
        
        # Check if this is the exact property (address match)
        parcel_address = parcel.get('address', '').upper().strip()
        heritage_address = prop_info['address'].upper().strip()
        
        if parcel_address and heritage_address:
            # Simple address matching - could be enhanced
            if (parcel_address in heritage_address or 
                heritage_address in parcel_address or
                prop_info['street_name'].upper().strip() in parcel_address):
                direct_heritage_match = True
    
    # Determine heritage status
    if direct_heritage_match:
        heritage_status = "Yes - Property is designated heritage"
    elif len(heritage_properties) > 0:
        heritage_status = f"Possibly - {len(heritage_properties)} heritage property(ies) within {buffer_meters}m"
    else:
        heritage_status = "No - No heritage properties found nearby"
    
    return {
        'has_heritage_requirements': direct_heritage_match,
        'heritage_status': heritage_status,
        'nearby_properties': heritage_properties,
        'search_radius': buffer_meters,
        'api_available': True,
        'query_coords': heritage_result['query_coords']
    }

def detect_conservation_requirements(parcel, zoning_info):
    """
    Enhanced detect if property has conservation requirements
    Now includes Heritage Properties API integration for accurate heritage detection
    """
    address = parcel.get('address', '').upper()
    
    # First, try to get accurate heritage information from Heritage Properties API
    try:
        heritage_info = get_heritage_requirements(parcel, buffer_meters=50)
        
        if heritage_info.get('api_available', False):
            # If we have a direct heritage match, return with details
            if heritage_info['has_heritage_requirements']:
                return "Yes - Heritage Property (API Verified)"
            
            # If there are nearby heritage properties, flag as possible
            elif len(heritage_info['nearby_properties']) > 0:
                return f"Possibly - {len(heritage_info['nearby_properties'])} heritage property(ies) within 50m"
        
        # If API is not available, fall back to legacy method
        else:
            st.warning("Heritage API unavailable - using fallback detection")
    
    except Exception as e:
        # Fallback gracefully if heritage API fails
        st.warning(f"Heritage API error (using fallback): {str(e)[:100]}")
    
    # Legacy fallback method - Check for heritage conservation districts or natural heritage features
    # Known heritage conservation districts in Oakville
    heritage_areas = [
        'OLD OAKVILLE', 'BRONTE', 'KERR VILLAGE', 'DOWNTOWN', 
        'HERITAGE DISTRICT', 'HISTORIC', 'CONSERVATION'
    ]
    
    for area in heritage_areas:
        if area in address:
            return "Yes - Heritage Area (Address-based)"
    
    # Check zoning info for conservation designation
    if zoning_info:
        zone_class = zoning_info.get('class', '').upper()
        if 'CONSERVATION' in zone_class or 'HERITAGE' in zone_class:
            return "Yes - Conservation Zoning"
    
    # Default to No for most residential properties
    return "No"

def detect_arborist_requirements(parcel, lot_area, development_potential):
    """Detect if arborist report is required"""
    # Arborist typically required for:
    # 1. Large lots (>1000 m²)
    # 2. Properties with significant tree coverage
    # 3. Development near mature trees
    
    if lot_area and lot_area > 1000:
        return "Yes"
    
    # Check for tree-related requirements in development potential
    if development_potential.get('tree_preservation_required'):
        return "Yes"
    
    # Check address for indicators of mature neighborhoods
    address = parcel.get('address', '').upper()
    mature_areas = [
        'FOREST', 'WOODS', 'GROVE', 'GLEN', 'CREEK', 'VALLEY',
        'HERITAGE', 'OLD', 'MATURE', 'ESTABLISHED'
    ]
    
    for indicator in mature_areas:
        if indicator in address:
            return "Yes"
    
    # Cannot determine without specific site conditions
    return "Unknown"

def check_heritage_property_status(lat, lon, address=None):
    """Check if a property is designated heritage or is within heritage area"""
    try:
        # Heritage Properties API
        url = "https://maps.oakville.ca/oakgis/rest/services/SBS/Heritage_Properties/FeatureServer/0/query"
        
        # First try spatial query around the property
        params = {
            'geometry': f'{lon},{lat}',
            'geometryType': 'esriGeometryPoint',
            'distance': 100,  # 100m radius
            'units': 'esriSRUnit_Meter',
            'inSR': '4326',
            'spatialRel': 'esriSpatialRelIntersects',
            'outFields': 'ADDRESS,HER_ID,BYLAW,DESIGNATION_YEAR,STATUS,HISTORY,DESCRIPTION',
            'f': 'json'
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'features' in data and data['features']:
            # Found heritage property at or near this location
            heritage_info = {
                'is_heritage': True,
                'designation_type': 'Direct',
                'properties': []
            }
            
            for feature in data['features']:
                attrs = feature.get('attributes', {})
                heritage_info['properties'].append({
                    'address': attrs.get('ADDRESS'),
                    'heritage_id': attrs.get('HER_ID'),
                    'bylaw': attrs.get('BYLAW'),
                    'year': attrs.get('DESIGNATION_YEAR'),
                    'status': attrs.get('STATUS'),
                    'history': attrs.get('HISTORY'),
                    'description': attrs.get('DESCRIPTION')
                })
            
            return heritage_info
        
        # Check if in heritage district (wider search)
        params['distance'] = 500  # 500m radius for district check
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'features' in data and len(data['features']) > 3:
            # Multiple heritage properties nearby suggest heritage district
            return {
                'is_heritage': False,
                'designation_type': 'Nearby',
                'nearby_heritage_count': len(data['features']),
                'note': 'Property is in area with multiple heritage properties'
            }
        
        return {
            'is_heritage': False,
            'designation_type': None,
            'note': 'No heritage designation found'
        }
        
    except Exception as e:
        return {
            'is_heritage': False,
            'designation_type': 'Unknown',
            'error': str(e)
        }

def check_development_applications(lat, lon, radius=500):
    """Check for active development applications in the area"""
    try:
        # Development Applications API - using correct layer ID 4
        url = "https://maps.oakville.ca/oakgis/rest/services/SBS/Development_Applications/FeatureServer/4/query"
        
        params = {
            'geometry': f'{lon},{lat}',
            'geometryType': 'esriGeometryPoint',
            'distance': radius,
            'units': 'esriSRUnit_Meter',
            'inSR': '4326',
            'spatialRel': 'esriSpatialRelIntersects',
            'outFields': '*',
            'f': 'json'
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        development_info = {
            'has_applications': False,
            'applications': [],
            'total_count': 0
        }
        
        if 'features' in data and data['features']:
            development_info['has_applications'] = True
            development_info['total_count'] = len(data['features'])
            
            for feature in data['features'][:5]:  # Limit to 5 most recent
                attrs = feature.get('attributes', {})
                
                # Get all available fields for debugging
                available_fields = list(attrs.keys()) if attrs else []
                
                # Use the correct field names from the Development Applications API
                app_number = attrs.get('ID_NUMBER', 'Unknown')
                
                # The API doesn't have a description field, so we'll indicate this
                description = 'Description not available in API'
                
                # Use DEV_ENG_STATUS for status
                status = attrs.get('DEV_ENG_STATUS', 'Unknown')
                if not status or status.strip() == '':
                    status = 'Status not available'
                
                # Use TYPE field for application type
                app_type = attrs.get('TYPE', 'Unknown')
                
                # Convert date from timestamp if available
                date_created = attrs.get('CREATED_DATE')
                if date_created:
                    try:
                        # Convert from epoch milliseconds to readable date
                        import datetime
                        date_received = datetime.datetime.fromtimestamp(date_created / 1000).strftime('%Y-%m-%d')
                    except:
                        date_received = 'Date conversion failed'
                else:
                    date_received = None
                
                # The API doesn't have address field
                address = None
                
                development_info['applications'].append({
                    'application_number': app_number,
                    'description': description,
                    'status': status,
                    'type': app_type,
                    'date_received': date_received,
                    'address': address,
                    'folder_rsn': attrs.get('FOLDER_RSN'),
                    'parent_rsn': attrs.get('PARENT_RSN'),
                    'north_oak': attrs.get('NORTH_OAK'),
                    'available_fields': available_fields  # For debugging
                })
        
        return development_info
        
    except Exception as e:
        return {
            'has_applications': False,
            'applications': [],
            'error': str(e)
        }

def check_conservation_authority(lat, lon):
    """Check which conservation authority has jurisdiction over the property"""
    try:
        # Conservation Halton Watersheds Service
        url = "https://gis.conservationhalton.net/chmaps/rest/services/ms-oper/Watersheds/MapServer/identify"
        
        # Convert WGS84 to UTM Zone 17N (Conservation Halton's coordinate system)
        from pyproj import Transformer
        transformer = Transformer.from_crs("EPSG:4326", "EPSG:26917", always_xy=True)
        x_utm, y_utm = transformer.transform(lon, lat)
        
        params = {
            'geometry': f'{x_utm},{y_utm}',
            'geometryType': 'esriGeometryPoint',
            'layers': 'all',
            'tolerance': 5,
            'mapExtent': f'{x_utm-1000},{y_utm-1000},{x_utm+1000},{y_utm+1000}',
            'imageDisplay': '400,400,96',
            'returnGeometry': 'false',
            'f': 'json'
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        conservation_info = {
            'conservation_authority': 'Unknown',
            'within_watershed': False,
            'watershed_details': {},
            'permits_required': 'Unknown',
            'contact_info': {},
            'regulated_features': []
        }
        
        # Check if within Conservation Halton watershed
        if 'results' in data and data['results']:
            for result in data['results']:
                layer_name = result.get('layerName', '')
                attributes = result.get('attributes', {})
                
                if 'watershed' in layer_name.lower() or 'conservation' in layer_name.lower():
                    conservation_info['within_watershed'] = True
                    conservation_info['conservation_authority'] = 'Halton Conservation Authority'
                    conservation_info['watershed_details'] = attributes
                    
                    # Set contact information for Halton Conservation
                    conservation_info['contact_info'] = {
                        'name': 'Halton Conservation Authority',
                        'website': 'https://conservationhalton.ca',
                        'email': 'web@hrca.on.ca',
                        'phone': '905.336.1158',
                        'address': '2596 Britannia Road West, Burlington, Ontario L7P 0G3'
                    }
                    
                    # Determine permit requirements (general rules for Oakville area)
                    conservation_info['permits_required'] = 'Likely Required'
                    conservation_info['regulated_features'] = [
                        'Development within 30m of watercourse',
                        'Alteration of watercourse',
                        'Development in flood hazard areas',
                        'Wetland interference',
                        'Development on unstable slopes'
                    ]
        
        # If not within Halton Conservation, check if it's near other conservation authorities
        if not conservation_info['within_watershed']:
            # For Oakville properties, still likely under Halton Conservation influence
            if 43.40 <= lat <= 43.55 and -79.80 <= lon <= -79.60:  # Oakville bounds
                conservation_info['conservation_authority'] = 'Halton Conservation Authority (Assumed)'
                conservation_info['permits_required'] = 'Possibly Required'
                conservation_info['contact_info'] = {
                    'name': 'Halton Conservation Authority',
                    'website': 'https://conservationhalton.ca',
                    'email': 'web@hrca.on.ca',
                    'phone': '905.336.1158'
                }
        
        return conservation_info
        
    except Exception as e:
        # Fallback for Oakville properties
        return {
            'conservation_authority': 'Halton Conservation Authority (Default)',
            'within_watershed': 'Unknown',
            'permits_required': 'Contact Required',
            'contact_info': {
                'name': 'Halton Conservation Authority',
                'website': 'https://conservationhalton.ca',
                'email': 'web@hrca.on.ca',
                'phone': '905.336.1158'
            },
            'error': str(e)
        }

# ------------------------
# API HELPERS
# ------------------------
def get_parcel(address):
    """Get parcel data from address - Always try API first, with CSV as backup
    Updated to use the corrected API integration"""
    
    # Use the corrected comprehensive function
    corrected_parcel = get_parcel_comprehensive_corrected(address)
    
    if corrected_parcel:
        # Convert to the format expected by the main app
        dimensions = {"frontage": None, "depth": None, "frontage_meters": None, "depth_meters": None}
        if corrected_parcel.get("geometry"):
            dimensions = calculate_frontage_depth(corrected_parcel["geometry"])
        
        return {
            "address": corrected_parcel["address"],
            "lot_area": corrected_parcel["lot_area_sqm"], 
            "geometry": corrected_parcel["geometry"],
            "roll_number": corrected_parcel["roll_number"],
            "legal_desc": corrected_parcel["legal_description"],
            "ward": corrected_parcel.get("ward"),
            "frontage": dimensions.get("frontage"),
            "depth": dimensions.get("depth"),
            "frontage_meters": dimensions.get("frontage_meters"),
            "depth_meters": dimensions.get("depth_meters"),
            "source": corrected_parcel["match_type"],
            "lat": corrected_parcel["centroid_lat"],
            "lon": corrected_parcel["centroid_lon"],
            "raw_attributes": corrected_parcel["raw_attributes"]
        }
    
    # Fallback to original implementation if corrected version fails
    address_variations = [
        address,  # Original
        address.upper(),  # All uppercase
        address.replace('Avenue', 'AVE').replace('avenue', 'AVE'),
        address.replace('Ave', 'AVE').replace('ave', 'AVE'),
        address.replace('Street', 'ST').replace('street', 'ST'),
        address.replace('Road', 'RD').replace('road', 'RD'),
        address.replace('Drive', 'DR').replace('drive', 'DR'),
        address.replace('Court', 'CRT').replace('court', 'CRT'),
        address.replace('Crescent', 'CRES').replace('crescent', 'CRES'),
    ]
    
    # Try exact match first
    for addr_variant in address_variations:
        params = {
            "f": "json",
            "where": f"ADDRESS = '{addr_variant}'",
            "outFields": "*",
            "returnGeometry": True,
        }
        try:
            r = requests.get(PARCELS_URL, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            features = data.get("features", [])
            if features:
                f = features[0]
                geometry = f.get("geometry")
                dimensions = calculate_frontage_depth(geometry) if geometry else {"frontage": None, "depth": None, "frontage_meters": None, "depth_meters": None}
                return {
                    "address": f["attributes"].get("ADDRESS"),
                    "lot_area": f["attributes"].get("Shape__Area"),
                    "geometry": geometry,
                    "roll_number": f["attributes"].get("ROLL_NUMBER"),
                    "legal_desc": f["attributes"].get("LEGAL_DESC"),
                    "frontage": dimensions.get("frontage"),
                    "depth": dimensions.get("depth"),
                    "frontage_meters": dimensions.get("frontage_meters"),
                    "depth_meters": dimensions.get("depth_meters"),
                    "source": "api_exact"
                }
        except Exception as e:
            continue
    
    # Try LIKE queries if exact match fails
    for addr_variant in address_variations:
        params = {
            "f": "json",
            "where": f"UPPER(ADDRESS) LIKE '%{addr_variant.upper()}%'",
            "outFields": "*",
            "returnGeometry": True,
        }
        try:
            r = requests.get(PARCELS_URL, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            features = data.get("features", [])
            if features:
                f = features[0]
                geometry = f.get("geometry")
                dimensions = calculate_frontage_depth(geometry) if geometry else {"frontage": None, "depth": None, "frontage_meters": None, "depth_meters": None}
                return {
                    "address": f["attributes"].get("ADDRESS"),
                    "lot_area": f["attributes"].get("Shape__Area"),
                    "geometry": geometry,
                    "roll_number": f["attributes"].get("ROLL_NUMBER"),
                    "legal_desc": f["attributes"].get("LEGAL_DESC"),
                    "frontage": dimensions.get("frontage"),
                    "depth": dimensions.get("depth"),
                    "frontage_meters": dimensions.get("frontage_meters"),
                    "depth_meters": dimensions.get("depth_meters"),
                    "source": "api_like"
                }
        except Exception as e:
            continue
    
    # Try partial match with street number and name
    address_parts = address.split()
    if len(address_parts) >= 2:
        street_number = address_parts[0]
        street_name = address_parts[1]
        
        params = {
            "f": "json",
            "where": f"ADDRESS LIKE '{street_number} {street_name}%'",
            "outFields": "*",
            "returnGeometry": True,
        }
        try:
            r = requests.get(PARCELS_URL, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            features = data.get("features", [])
            if features:
                f = features[0]
                actual_address = f["attributes"].get("ADDRESS")
                geometry = f.get("geometry")
                dimensions = calculate_frontage_depth(geometry) if geometry else {"frontage": None, "depth": None, "frontage_meters": None, "depth_meters": None}
                st.info(f"Found similar address: {actual_address}")
                return {
                    "address": actual_address,
                    "lot_area": f["attributes"].get("Shape__Area"),
                    "geometry": geometry,
                    "roll_number": f["attributes"].get("ROLL_NUMBER"),
                    "legal_desc": f["attributes"].get("LEGAL_DESC"),
                    "frontage": dimensions.get("frontage"),
                    "depth": dimensions.get("depth"),
                    "frontage_meters": dimensions.get("frontage_meters"),
                    "depth_meters": dimensions.get("depth_meters"),
                    "source": "api_partial_match"
                }
        except Exception as e:
            pass
    
    # If API fails, try CSV as backup
    address_key = address.strip().upper()
    if address_key in PARCEL_DATA:
        return {
            "address": address,
            "lot_area": PARCEL_DATA[address_key],
            "geometry": None,  # No geometry from CSV
            "roll_number": None,
            "legal_desc": None,
            "frontage": None,
            "depth": None,
            "frontage_meters": None,
            "depth_meters": None,
            "source": "local_csv"
        }
    
    # Try fuzzy matching in CSV
    if len(address_parts) >= 2:
        for csv_addr in PARCEL_DATA.keys():
            if street_number in csv_addr and any(part.upper() in csv_addr for part in address_parts[1:]):
                st.info(f"Found similar address in CSV: {csv_addr}")
                return {
                    "address": csv_addr,
                    "lot_area": PARCEL_DATA[csv_addr],
                    "geometry": None,
                    "roll_number": None,
                    "legal_desc": None,
                    "frontage": None,
                    "depth": None,
                    "frontage_meters": None,
                    "depth_meters": None,
                    "source": "local_csv_fuzzy"
                }
    
    return None

def get_parcel_comprehensive_corrected(address: str):
    """
    Comprehensive parcel lookup with multiple strategies and proper coordinate handling.
    Returns parcel data with lot area, geometry, and centroid in WGS84.
    """
    # Strategy 1: Try exact match first
    parcel = get_single_parcel_exact(address.upper())
    if parcel:
        return process_parcel_data_corrected(parcel, "exact_match")
    
    # Strategy 2: Try LIKE query with original address
    parcels = fetch_parcels_by_address_corrected(address)
    if parcels:
        return process_parcel_data_corrected(parcels[0], "like_match")
    
    # Strategy 3: Try with address variations
    variations = [
        address.replace('Avenue', 'AVE').replace('avenue', 'AVE'),
        address.replace('Ave', 'AVE').replace('ave', 'AVE'),
        address.replace('Street', 'ST').replace('street', 'ST'),
        address.replace('Road', 'RD').replace('road', 'RD'),
    ]
    
    for variation in variations:
        parcels = fetch_parcels_by_address_corrected(variation)
        if parcels:
            return process_parcel_data_corrected(parcels[0], f"variation_match")
    
    return None

def get_single_parcel_exact(address_str: str):
    """Get single parcel with exact address match in WGS84 coordinates"""
    params = {
        "f": "json",
        "where": f"ADDRESS = '{address_str}'",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": 4326,  # Request in WGS84
    }
    
    try:
        resp = requests.get(PARCELS_URL, params=params, timeout=20)
        resp.raise_for_status()
        features = resp.json().get("features", [])
        return features[0] if features else None
    except Exception as e:
        st.warning(f"Parcel exact match error: {str(e)}")
        return None

def fetch_parcels_by_address_corrected(address_query: str, max_records: int = 50):
    """Query parcels with LIKE match in WGS84 coordinates"""
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
        resp = requests.get(PARCELS_URL, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json().get("features", [])
    except Exception as e:
        st.warning(f"Parcels LIKE query error: {str(e)}")
        return []

def process_parcel_data_corrected(parcel_feature, match_type: str):
    """Process parcel feature data to extract key information with proper coordinate handling"""
    attrs = parcel_feature["attributes"]
    geometry = parcel_feature["geometry"]
    
    # Calculate centroid from geometry (should be in WGS84 now)
    centroid_lat, centroid_lon = calculate_centroid_corrected(geometry)
    
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

def calculate_centroid_corrected(geometry):
    """Calculate centroid from ArcGIS geometry, handling WGS84 coordinates properly"""
    try:
        if "rings" in geometry:  # Polygon
            # Get the first ring (exterior)
            coords = geometry["rings"][0]
            
            # Should be in WGS84 now, so just calculate centroid
            x_coords = [point[0] for point in coords]
            y_coords = [point[1] for point in coords]
            centroid_lon = sum(x_coords) / len(x_coords)
            centroid_lat = sum(y_coords) / len(y_coords)
            
            return centroid_lat, centroid_lon
                
        elif "x" in geometry and "y" in geometry:  # Point
            return geometry["y"], geometry["x"]  # (lat, lon)
        else:
            st.error("Unsupported geometry type")
            return None, None
            
    except Exception as e:
        st.error(f"Error calculating centroid: {e}")
        return None, None

def get_zoning_comprehensive_corrected(lat: float, lon: float):
    """
    Comprehensive zoning lookup with full field mapping.
    Returns structured zoning information using the corrected approach.
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
        resp = requests.get(ZONING_URL, params=params, timeout=30)
        resp.raise_for_status()
        zoning_features = resp.json().get("features", [])
    except Exception as e:
        st.error(f"Zoning API error: {str(e)}")
        return {
            "status": "error",
            "zone": "Unknown",
            "message": f"API error: {str(e)}"
        }
    
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

def get_zone(lat, lon, address=None):
    """
    Enhanced get_zone function using corrected comprehensive approach
    
    Args:
        lat: Latitude (decimal degrees, WGS84)
        lon: Longitude (decimal degrees, WGS84)  
        address: Optional property address for validation
        
    Returns:
        Dict with zone information or None if unable to determine
    """
    
    # Validate coordinates
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        st.error("Invalid coordinates provided")
        return None
        
    # Oakville coordinate bounds validation
    oakville_bounds = {
        'north': 43.55, 'south': 43.40,
        'east': -79.55, 'west': -79.85
    }
    
    within_oakville = (oakville_bounds['south'] <= lat <= oakville_bounds['north'] and 
                      oakville_bounds['west'] <= lon <= oakville_bounds['east'])
    
    if not within_oakville:
        st.info(f"Coordinates {lat}, {lon} may be outside Oakville municipal boundaries")
    
    # Use the corrected comprehensive zoning function
    st.info("Fetching zoning information...")
    zoning_data = get_zoning_comprehensive_corrected(lat, lon)
    
    if zoning_data['status'] != 'found':
        st.error(f"Zoning lookup failed: {zoning_data['message']}")
        return {
            "zone": "Unknown",
            "class": "Unknown", 
            "special_provision": None,
            "full_zone_code": "Unknown",
            "zone_description": "Unable to determine zoning for this property",
            "full_zoning_description": "No zoning data available",
            "confidence": "none",
            "source": "api_failure",
            "coordinates": (lat, lon),
            "within_oakville_bounds": within_oakville,
            "error": zoning_data['message']
        }
    
    # Convert to backward-compatible format
    result = {
        "zone": zoning_data['zone'],  # Base zone only for backward compatibility
        "class": zoning_data['zone_class'],
        "special_provision": zoning_data['special_provisions'][0] if zoning_data['special_provisions'] else None,
        "full_zone_code": zoning_data['full_zone_code'],
        "zone_description": zoning_data['zone_description'],
        "full_zoning_description": zoning_data['full_zoning_description'],
        "building_heights": zoning_data['building_heights'],
        "temp_use": zoning_data['temp_use'],
        "hold_provisions": zoning_data['hold_provisions'], 
        "growth_area": zoning_data['growth_area'],
        "area": zoning_data['zoning_area_sqm'],
        "confidence": "high",
        "source": "oakville_zoning_api_corrected",
        "coordinates": (lat, lon),
        "special_provisions_list": zoning_data['special_provisions'],
        "raw_attributes": zoning_data['raw_attributes'],
        "within_oakville_bounds": within_oakville
    }
    
    st.success(f"Successfully retrieved zoning: {zoning_data['full_zone_code']} ({zoning_data['zone_class']})")
    return result

def get_centroid(geometry):
    """Calculate centroid of geometry"""
    try:
        if "rings" in geometry:
            geojson_geom = {"type": "Polygon", "coordinates": geometry["rings"]}
        elif "x" in geometry and "y" in geometry:
            geojson_geom = {"type": "Point", "coordinates": [geometry["x"], geometry["y"]]}
        else:
            return None, None
        geom = shape(geojson_geom)
        c = geom.centroid
        return c.y, c.x
    except Exception as e:
        st.error(f"Error calculating centroid: {e}")
        return None, None

# ------------------------
# ZONING ANALYSIS
# ------------------------
def parse_zone_code(zone_code: str):
    """Parse zone code to extract base zone, suffix, and special provisions"""
    import re
    
    # Clean the zone code
    zone_code = zone_code.strip().upper() if zone_code else ""
    
    # Extract special provision (SP:X)
    special_provision = None
    sp_match = re.search(r'SP:(\d+)', zone_code)
    if sp_match:
        special_provision = f"SP:{sp_match.group(1)}"
        zone_code = re.sub(r'\s*SP:\d+', '', zone_code).strip()
    
    # Extract suffix (-0)
    suffix = None
    if zone_code.endswith('-0'):
        suffix = '-0'
        base_zone = zone_code[:-2]
    else:
        base_zone = zone_code
    
    return base_zone, suffix, special_provision

def get_zone_rules(zone_code):
    """Get comprehensive zoning rules for a zone code with all modifications"""
    if not zone_code:
        return None
    
    # Parse zone code
    base_zone, suffix, special_provision = parse_zone_code(zone_code)
    
    zone_rules = ZONING_DATA.get('residential_zones', {}).get(base_zone)
    if not zone_rules:
        return None
    
    # Start with base rules
    rules = zone_rules.copy()
    
    # Apply -0 suffix modifications
    if suffix == '-0':
        # Height restrictions for -0 zones
        if 'max_height_suffix_0' in zone_rules:
            rules['max_height'] = zone_rules['max_height_suffix_0']
        if 'max_storeys_suffix_0' in zone_rules:
            rules['max_storeys'] = zone_rules['max_storeys_suffix_0']
        # Floor area ratio for -0 zones
        if 'max_residential_floor_area_ratio_suffix_0' in zone_rules:
            rules['max_residential_floor_area_ratio'] = zone_rules['max_residential_floor_area_ratio_suffix_0']
        # Coverage for -0 zones
        if 'max_lot_coverage_suffix_0' in zone_rules:
            rules['max_lot_coverage'] = zone_rules['max_lot_coverage_suffix_0']
        
        rules['is_suffix_0'] = True
        rules['suffix'] = suffix
    
    # Add special provision info
    if special_provision:
        rules['special_provision'] = special_provision
        # Load special provision overrides if available
        sp_data = SPECIAL_PROVISIONS.get(special_provision, {})
        if sp_data.get('overrides'):
            rules.update(sp_data['overrides'])
    
    rules['original_zone_code'] = zone_code
    rules['base_zone'] = base_zone
    
    return rules

def calculate_precise_setbacks(zone_code: str, lot_frontage: float, lot_depth: float, 
                             is_corner: bool = False, is_plan_subdivision: bool = False) -> dict:
    """Calculate precise setbacks based on Oakville By-law 2014-014"""
    rules = get_zone_rules(zone_code)
    if not rules:
        return {}
    
    setbacks = rules.get('setbacks', {})
    calculated_setbacks = {}
    
    # Front yard setback
    front_yard = setbacks.get('front_yard')
    if rules.get('is_suffix_0') and 'front_yard_suffix_0' in setbacks:
        if setbacks['front_yard_suffix_0'] == "-1":
            # For -0 zones, calculate based on existing buildings (requires survey data)
            front_yard = "-1"  # Keep as string to indicate special calculation needed
        else:
            front_yard = setbacks['front_yard_suffix_0']
    
    calculated_setbacks['front_yard'] = front_yard
    
    # Side yard setbacks
    interior_side = setbacks.get('interior_side')
    if 'interior_side_min' in setbacks and 'interior_side_max' in setbacks:
        # For zones like RL3 with min/max requirements
        calculated_setbacks['interior_side_min'] = setbacks['interior_side_min']
        calculated_setbacks['interior_side_max'] = setbacks['interior_side_max']
    else:
        calculated_setbacks['interior_side'] = interior_side
    
    # Rear yard
    rear_yard = setbacks.get('rear_yard')
    
    # Corner lot adjustments
    if is_corner:
        corner_adjustments = rules.get('corner_lot_adjustments', {})
        if corner_adjustments.get('rear_yard_reduction'):
            if calculated_setbacks.get('interior_side', interior_side) >= 3.0:
                rear_yard = corner_adjustments['rear_yard_reduction'].get('reduced_to', rear_yard)
    
    calculated_setbacks['rear_yard'] = rear_yard
    
    # Flankage yard for corner lots
    if is_corner:
        calculated_setbacks['flankage_yard'] = setbacks.get('flankage_yard', 3.5)
    
    # Garage adjustments
    garage_adjustments = rules.get('garage_adjustments', {})
    if garage_adjustments.get('interior_side_reduction'):
        calculated_setbacks['garage_interior_side'] = garage_adjustments['interior_side_reduction']['reduced_to']
        calculated_setbacks['garage_applies_to'] = garage_adjustments['interior_side_reduction']['applies_to']
    
    return calculated_setbacks

def calculate_floor_area_ratio(zone_code: str, lot_area: float) -> float:
    """Calculate precise floor area ratio based on zone and lot characteristics"""
    rules = get_zone_rules(zone_code)
    if not rules:
        return None
    
    max_far = rules.get('max_residential_floor_area_ratio')
    
    # Handle table references for -0 zones
    if isinstance(max_far, str) and max_far == "table_6.4.1":
        return calculate_suffix_zero_far(lot_area)
    
    return max_far

def calculate_suffix_zero_far(lot_area: float) -> float:
    """Calculate FAR for -0 suffix zones based on Table 6.4.1"""
    # Table 6.4.1 from Oakville By-law 2014-014 - CORRECTED VALUES
    if lot_area < 557.5:
        return 0.43  # 43%
    elif lot_area <= 649.99:
        return 0.42  # 42%
    elif lot_area <= 742.99:
        return 0.41  # 41%
    elif lot_area <= 835.99:
        return 0.40  # 40%
    elif lot_area <= 928.99:
        return 0.39  # 39%
    elif lot_area <= 1021.99:
        return 0.38  # 38%
    elif lot_area <= 1114.99:
        return 0.37  # 37%
    elif lot_area <= 1207.99:
        return 0.35  # 35%
    elif lot_area <= 1300.99:
        return 0.32  # 32%
    else:
        return 0.29  # 29% for 1,301.00 m² or greater

def calculate_lot_coverage(zone_code: str, lot_area: float) -> float:
    """Calculate precise lot coverage based on zone and lot characteristics"""
    rules = get_zone_rules(zone_code)
    if not rules:
        return None
    
    max_coverage = rules.get('max_lot_coverage')
    
    # Handle table references for -0 zones  
    if isinstance(max_coverage, str) and max_coverage == "table_6.4.2":
        return calculate_suffix_zero_coverage(zone_code)
    
    return max_coverage

def calculate_suffix_zero_coverage(zone_code: str, building_height: float = None) -> float:
    """Calculate lot coverage for -0 suffix zones based on Table 6.4.2"""
    # Table 6.4.2 from Oakville By-law 2014-014 - CORRECTED VALUES
    base_zone, _, _ = parse_zone_code(zone_code)
    
    # Default height assumption if not provided
    if building_height is None:
        building_height = 9.0  # Most -0 zones have 9.0m max height
    
    if base_zone in ['RL1', 'RL2']:
        if building_height <= 7.0:
            # Use parent zone maximum (30% for RL1/RL2)
            return 0.30
        else:
            return 0.25  # 25% for buildings > 7.0m height
    elif base_zone in ['RL3', 'RL4', 'RL5', 'RL7', 'RL8', 'RL10']:
        return 0.35  # 35% for these zones
    else:
        return None  # No default for unknown zones

def calculate_buildable_area(lot_area: float, lot_frontage: float, lot_depth: float, 
                           setbacks: dict) -> dict:
    """Calculate the actual buildable area considering all setbacks"""
    # Only calculate if we have all required setback values
    interior_side = setbacks.get('interior_side')
    front_yard = setbacks.get('front_yard')
    rear_yard = setbacks.get('rear_yard')
    
    if not all([interior_side, front_yard, rear_yard]) or lot_frontage <= 0 or lot_depth <= 0:
        return {
            'usable_frontage': None,
            'usable_depth': None,
            'buildable_area': None,
            'efficiency_ratio': None
        }
    
    # Safe conversion function for setback values
    def safe_float(value, default=0):
        try:
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            return default
    
    # Convert setback values safely, handling strings like "-1"
    interior_side_val = safe_float(interior_side)
    front_yard_val = safe_float(front_yard)
    rear_yard_val = safe_float(rear_yard)
    
    # For -0 zones with "existing -1" setbacks, we can't calculate without survey data
    if isinstance(front_yard, str) and front_yard == "-1":
        return {
            'usable_frontage': None,
            'usable_depth': None,
            'buildable_area': None,
            'efficiency_ratio': None,
            'note': 'Requires survey data for existing building setback calculation'
        }
    
    # Calculate usable dimensions after setbacks
    usable_frontage = lot_frontage - interior_side_val * 2
    usable_depth = lot_depth - front_yard_val - rear_yard_val
    
    # Ensure positive values
    usable_frontage = max(usable_frontage, 0)
    usable_depth = max(usable_depth, 0)
    
    buildable_area = usable_frontage * usable_depth
    
    return {
        'usable_frontage': usable_frontage,
        'usable_depth': usable_depth,
        'buildable_area': buildable_area,
        'efficiency_ratio': buildable_area / lot_area if lot_area > 0 else 0
    }

def calculate_development_potential(zone_code, lot_area, lot_frontage, lot_depth, is_corner=False):
    """Calculate comprehensive development potential based on Oakville zoning rules"""
    rules = get_zone_rules(zone_code)
    if not rules:
        return {"error": f"No rules found for zone {zone_code}"}
    
    # Parse zone components
    base_zone, suffix, special_provision = parse_zone_code(zone_code)
    
    results = {
        "zone_name": rules.get('name'),
        "zone_code": zone_code,
        "base_zone": base_zone,
        "suffix": suffix,
        "special_provision": special_provision,
        "meets_minimum_requirements": True,
        "violations": [],
        "warnings": [],
        "analysis_confidence": "high"
    }
    
    # Check minimum lot area
    min_area = rules.get('min_lot_area')
    if min_area and lot_area < min_area:
        results["meets_minimum_requirements"] = False
        results["violations"].append(f"Lot area {lot_area:.1f} m² ({lot_area * 10.764:.0f} sq ft) is below minimum {min_area:.1f} m² ({min_area * 10.764:.0f} sq ft)")
    
    # Check minimum frontage - only if frontage is provided (> 0)
    min_frontage = rules.get('min_lot_frontage')
    if min_frontage and lot_frontage > 0 and lot_frontage < min_frontage:
        results["meets_minimum_requirements"] = False
        results["violations"].append(f"Lot frontage {lot_frontage:.1f} m is below minimum {min_frontage:.1f} m")
    elif lot_frontage == 0:
        results["warnings"].append("Lot frontage not available - cannot verify minimum frontage requirements")
    
    # Calculate precise setbacks
    setbacks = calculate_precise_setbacks(zone_code, lot_frontage, lot_depth, is_corner)
    results["setbacks"] = setbacks
    
    # Calculate buildable area
    buildable_area_calc = calculate_buildable_area(lot_area, lot_frontage, lot_depth, setbacks)
    results.update(buildable_area_calc)
    
    # Calculate maximum coverage
    max_coverage_pct = calculate_lot_coverage(zone_code, lot_area)
    max_coverage_area = lot_area * max_coverage_pct if max_coverage_pct else None
    results["max_coverage_percent"] = max_coverage_pct * 100 if max_coverage_pct else None
    results["max_coverage_area"] = max_coverage_area
    
    # Calculate floor area ratio
    max_far = calculate_floor_area_ratio(zone_code, lot_area)
    max_floor_area = lot_area * max_far if max_far else None
    results["max_floor_area_ratio"] = max_far
    results["max_floor_area"] = max_floor_area
    
    # Height and storey limits
    results["max_height"] = rules.get('max_height')
    results["max_storeys"] = rules.get('max_storeys')
    
    # Building depth limits
    max_dwelling_depth = rules.get('max_dwelling_depth')
    if max_dwelling_depth:
        # Safely convert setback values to float, defaulting to 0 if not numeric
        def safe_float(value, default=0):
            try:
                return float(value) if value is not None else default
            except (ValueError, TypeError):
                return default
        
        front_setback = safe_float(setbacks.get('front_yard', 0))
        rear_setback = safe_float(setbacks.get('rear_yard', 0))
        usable_depth = lot_depth - front_setback - rear_setback
        actual_max_depth = min(max_dwelling_depth, usable_depth) if usable_depth > 0 else max_dwelling_depth
        results["max_building_depth"] = actual_max_depth
    
    # Special depth provisions
    if rules.get('max_dwelling_depth_special_provision'):
        special = rules['max_dwelling_depth_special_provision']
        results["special_depth_provisions"] = special
    
    # Calculate potential units
    potential_units = calculate_potential_units(zone_code, lot_area, max_floor_area)
    results["potential_units"] = potential_units
    
    # Permitted uses
    results["permitted_uses"] = rules.get('permitted_uses', [])
    
    # Use restrictions
    results["use_restrictions"] = rules.get('use_restrictions', {})
    
    # Plan subdivision adjustments
    if rules.get('plan_subdivision_adjustments'):
        results["plan_subdivision_adjustments"] = rules['plan_subdivision_adjustments']
    
    # Calculate final buildable floor area analysis
    final_analysis = calculate_final_buildable_area(zone_code, lot_area, results)
    results["final_buildable_analysis"] = final_analysis
    
    return results

def calculate_final_buildable_area(zone_code: str, lot_area: float, development_data: dict) -> dict:
    """Calculate the final buildable floor area with comprehensive analysis"""
    
    analysis = {
        "calculation_method": "Standard",
        "lot_coverage_sqm": None,
        "lot_coverage_sqft": None,
        "max_floors": 2,  # Default to 2 storeys for most residential zones
        "gross_floor_area_sqm": None,
        "gross_floor_area_sqft": None,
        "setback_deduction_sqft": 750,  # Standard setback deduction
        "final_buildable_sqm": None,
        "final_buildable_sqft": None,
        "confidence_level": "High",
        "analysis_note": None
    }
    
    # Get zone rules
    rules = get_zone_rules(zone_code)
    if not rules:
        analysis["confidence_level"] = "Low"
        analysis["analysis_note"] = "Zone rules not available"
        return analysis
    
    # Get maximum coverage
    max_coverage_pct = development_data.get("max_coverage_percent")
    if max_coverage_pct:
        lot_coverage_sqm = lot_area * (max_coverage_pct / 100)
        analysis["lot_coverage_sqm"] = lot_coverage_sqm
        analysis["lot_coverage_sqft"] = lot_coverage_sqm * 10.764
        
        # Determine number of floors based on zone and height
        max_storeys = development_data.get("max_storeys") or rules.get('max_storeys') or 2
        if max_storeys:
            analysis["max_floors"] = min(max_storeys, 2)  # Typically 2 floors for residential
        
        # Calculate gross floor area (coverage × floors)
        gross_floor_area_sqft = analysis["lot_coverage_sqft"] * analysis["max_floors"]
        analysis["gross_floor_area_sqft"] = gross_floor_area_sqft
        analysis["gross_floor_area_sqm"] = gross_floor_area_sqft / 10.764
        
        # Apply setback deductions
        final_buildable_sqft = gross_floor_area_sqft - analysis["setback_deduction_sqft"]
        analysis["final_buildable_sqft"] = max(final_buildable_sqft, 0)
        analysis["final_buildable_sqm"] = analysis["final_buildable_sqft"] / 10.764
        
        # Add confidence note
        if development_data.get("suffix") == "-0":
            # Check if buildable area calculation was affected by "-1" setback
            if development_data.get('note') and 'survey data' in development_data.get('note', ''):
                analysis["analysis_note"] = "Based on -0 suffix zone regulations. Note: Front yard setback requires survey data for precise calculation."
                analysis["confidence_level"] = "Moderate"
            else:
                analysis["analysis_note"] = "Based on -0 suffix zone regulations with existing -1m front yard setback"
        else:
            analysis["analysis_note"] = f"Based on {zone_code} zoning regulations and {max_coverage_pct:.0f}% lot coverage"
            
    else:
        # Use FAR method if coverage not available
        max_floor_area = development_data.get("max_floor_area")
        if max_floor_area:
            analysis["calculation_method"] = "Floor Area Ratio"
            analysis["gross_floor_area_sqm"] = max_floor_area
            analysis["gross_floor_area_sqft"] = max_floor_area * 10.764
            
            # Apply standard deductions
            final_buildable_sqft = (max_floor_area * 10.764) - analysis["setback_deduction_sqft"]
            analysis["final_buildable_sqft"] = max(final_buildable_sqft, 0)
            analysis["final_buildable_sqm"] = analysis["final_buildable_sqft"] / 10.764
            
            analysis["analysis_note"] = f"Based on Floor Area Ratio calculation for {zone_code}"
        else:
            analysis["confidence_level"] = "Low"
            analysis["analysis_note"] = "Insufficient data for calculation"
    
    return analysis

def calculate_potential_units(zone_code: str, lot_area: float, max_floor_area: float) -> int:
    """Calculate potential number of dwelling units"""
    base_zone, suffix, special_provision = parse_zone_code(zone_code)
    
    # Cannot calculate units without floor area for most zones
    if not max_floor_area and base_zone not in ['RL1', 'RL2', 'RL3', 'RL4', 'RL5', 'RL6', 'RL7', 'RL8', 'RL9', 'RL10']:
        return 1  # Default to 1 unit
    
    # Unit calculation based on zone type
    if base_zone in ['RL1', 'RL2', 'RL3', 'RL4', 'RL5', 'RL6']:
        # Single family zones
        return 1
    elif base_zone in ['RL7', 'RL8', 'RL9']:
        # Mixed single/semi zones
        return 1 if lot_area < 600 else 2
    elif base_zone in ['RL10']:
        # Duplex potential
        return 2
    elif base_zone in ['RL11']:
        # Linked dwellings
        return min(int(max_floor_area / 120), 3) if max_floor_area else 1  # ~120m² (~1,292 sq ft) per unit
    elif base_zone == 'RUC':
        # Uptown core - higher density
        return min(int(max_floor_area / 80), 6) if max_floor_area else 1  # ~80m² (~861 sq ft) per unit
    elif base_zone.startswith('RM'):
        # Medium density residential
        if not max_floor_area:
            return 1
        units_per_100m2_floor = {'RM1': 1, 'RM2': 1.2, 'RM3': 1.5, 'RM4': 2}
        multiplier = units_per_100m2_floor.get(base_zone, 1)
        return int((max_floor_area / 100) * multiplier)
    elif base_zone == 'RH':
        # High density
        return int(max_floor_area / 60) if max_floor_area else 1  # ~60m² (~646 sq ft) per unit
    else:
        return 1

def get_coverage_from_table(zone_code, lot_area, lot_frontage):
    """Get lot coverage from lookup table for -0 zones"""
    # Use the comprehensive suffix zone coverage calculation
    return calculate_suffix_zero_coverage(lot_area)

def get_far_from_table(zone_code, lot_area, lot_frontage):
    """Get floor area ratio from lookup table for -0 zones"""
    # Use the comprehensive suffix zone FAR calculation
    return calculate_suffix_zero_far(lot_area)

# ------------------------
# ZONE RULES DISPLAY
# ------------------------
def get_comprehensive_zone_rules(zone_code: str) -> dict:
    """Get comprehensive zone rules from JSON file for display"""
    try:
        with open('data/comprehensive_zoning_regulations.json', 'r') as f:
            zoning_data = json.load(f)
    except FileNotFoundError:
        return {"error": "Zoning regulations file not found"}
    
    # Parse zone code to handle -0 suffix and special provisions
    base_zone = zone_code.replace(' SP:1', '').replace(' SP:2', '').replace('-0', '')
    is_suffix_zero = '-0' in zone_code
    special_provision = None
    if 'SP:1' in zone_code:
        special_provision = "SP:1"
    elif 'SP:2' in zone_code:
        special_provision = "SP:2"
    
    residential_zones = zoning_data.get('residential_zones', {})
    
    if base_zone not in residential_zones:
        return {"error": f"Zone {base_zone} not found in regulations"}
    
    zone_rules = residential_zones[base_zone].copy()
    
    # Add parsing information
    zone_rules['_parsed_info'] = {
        'original_zone_code': zone_code,
        'base_zone': base_zone,
        'has_suffix_zero': is_suffix_zero,
        'special_provision': special_provision
    }
    
    # Add metadata
    zone_rules['_metadata'] = zoning_data.get('_metadata', {})
    
    return zone_rules

def display_zone_rules_tab(zone_code: str):
    """Display comprehensive zone rules in a separate tab with proper alignment"""
    st.header("📋 Comprehensive Zone Rules & Regulations")
    
    zone_rules = get_comprehensive_zone_rules(zone_code)
    
    if 'error' in zone_rules:
        st.error(f"❌ {zone_rules['error']}")
        return
    
    parsed_info = zone_rules.get('_parsed_info', {})
    
    # Zone Information Header - Better aligned
    st.subheader("🏷️ Zone Information")
    info_col1, info_col2, info_col3 = st.columns([3, 3, 4])
    
    with info_col1:
        st.metric("Zone Code", parsed_info['original_zone_code'])
        st.caption(f"Base: {parsed_info['base_zone']}")
    
    with info_col2:
        st.metric("Zone Name", zone_rules.get('name', 'N/A'))
        st.caption(f"Category: {zone_rules.get('category', 'N/A')}")
    
    with info_col3:
        if zone_rules.get('_metadata', {}).get('source'):
            st.info(f"📖 **Source:**\n{zone_rules['_metadata']['source']}")
            if zone_rules.get('_metadata', {}).get('consolidated_date'):
                st.caption(f"Last Updated: {zone_rules['_metadata']['consolidated_date']}")
    
    # Special Indicators - Better formatting
    if parsed_info['has_suffix_zero'] or parsed_info['special_provision']:
        st.markdown("---")
        st.info("🔍 **Special Zone Modifications Apply:**")
        mod_col1, mod_col2 = st.columns(2)
        
        with mod_col1:
            if parsed_info['has_suffix_zero']:
                st.success("**-0 Suffix Zone**\nModified height, coverage, and FAR rules apply")
        
        with mod_col2:
            if parsed_info['special_provision']:
                st.warning(f"**{parsed_info['special_provision']}**\nSpecial provision regulations apply")
    
    st.markdown("---")
    
    # Lot Requirements - Better layout
    st.subheader("📐 Lot Requirements")
    req_col1, req_col2, req_col3 = st.columns([3, 3, 2])
    
    with req_col1:
        min_area = zone_rules.get('min_lot_area')
        if min_area:
            st.metric("Minimum Lot Area", f"{min_area} m²")
            st.caption(f"≈ {min_area * 10.764:.0f} sq ft")
        else:
            st.metric("Minimum Lot Area", "N/A")
    
    with req_col2:
        min_frontage = zone_rules.get('min_lot_frontage')
        if min_frontage:
            st.metric("Minimum Lot Frontage", f"{min_frontage} m")
            st.caption(f"≈ {min_frontage * 3.28084:.1f} ft")
        else:
            st.metric("Minimum Lot Frontage", "N/A")
    
    with req_col3:
        if min_area and min_frontage:
            est_depth = min_area / min_frontage
            st.metric("Est. Min Depth", f"{est_depth:.1f} m")
            st.caption("Based on min area ÷ frontage")
    
    st.markdown("---")
    
    # Setback Requirements - Improved alignment
    st.subheader("🏠 Setback Requirements")
    setbacks = zone_rules.get('setbacks', {})
    
    if setbacks:
        # Main setbacks row
        setback_col1, setback_col2, setback_col3, setback_col4 = st.columns(4)
        
        # Front Yard
        with setback_col1:
            front_val = setbacks.get('front_yard')
            front_suffix = setbacks.get('front_yard_suffix_0')
            if front_val:
                st.metric("🔸 Front Yard", f"{front_val} m")
                if parsed_info['has_suffix_zero'] and front_suffix:
                    if isinstance(front_suffix, str):
                        st.caption(f"**-0:** {front_suffix}")
                    else:
                        st.caption(f"**-0:** {front_suffix} m")
            else:
                st.metric("🔸 Front Yard", "N/A")
        
        # Rear Yard
        with setback_col2:
            rear_val = setbacks.get('rear_yard')
            rear_suffix = setbacks.get('rear_yard_suffix_0')
            if rear_val:
                st.metric("🔸 Rear Yard", f"{rear_val} m")
                if parsed_info['has_suffix_zero'] and rear_suffix:
                    if isinstance(rear_suffix, str):
                        st.caption(f"**-0:** {rear_suffix}")
                    else:
                        st.caption(f"**-0:** {rear_suffix} m")
            else:
                st.metric("🔸 Rear Yard", "N/A")
        
        # Interior Side
        with setback_col3:
            interior_val = setbacks.get('interior_side')
            interior_min = setbacks.get('interior_side_min')
            interior_max = setbacks.get('interior_side_max')
            
            if interior_val:
                st.metric("🔸 Interior Side", f"{interior_val} m")
            elif interior_min:
                st.metric("🔸 Interior Side", f"{interior_min} m min")
                if interior_max:
                    st.caption(f"Max: {interior_max} m")
            else:
                st.metric("🔸 Interior Side", "N/A")
        
        # Flankage Yard
        with setback_col4:
            flankage_val = setbacks.get('flankage_yard')
            if flankage_val:
                st.metric("🔸 Flankage Yard", f"{flankage_val} m")
                st.caption("Corner lots only")
            else:
                st.metric("🔸 Flankage Yard", "N/A")
                st.caption("Not applicable")
    else:
        st.info("No setback information available")
    
    st.markdown("---")
    
    # Building Envelope - Better layout
    st.subheader("🏗️ Building Envelope")
    envelope_col1, envelope_col2, envelope_col3, envelope_col4 = st.columns(4)
    
    with envelope_col1:
        height = zone_rules.get('max_height')
        height_suffix = zone_rules.get('max_height_suffix_0')
        if height:
            st.metric("🏢 Max Height", f"{height} m")
            st.caption(f"≈ {height * 3.28084:.1f} ft")
            if parsed_info['has_suffix_zero'] and height_suffix:
                st.info(f"**-0 Zone:** {height_suffix} m")
        else:
            st.metric("🏢 Max Height", "N/A")
    
    with envelope_col2:
        storeys = zone_rules.get('max_storeys')
        storeys_suffix = zone_rules.get('max_storeys_suffix_0')
        if storeys:
            st.metric("🏠 Max Storeys", storeys)
        elif storeys_suffix and parsed_info['has_suffix_zero']:
            st.metric("🏠 Max Storeys", f"{storeys_suffix}")
            st.caption("-0 Zone limit")
        else:
            st.metric("🏠 Max Storeys", "N/A")
    
    with envelope_col3:
        depth = zone_rules.get('max_dwelling_depth')
        if depth:
            st.metric("📐 Max Depth", f"{depth} m")
            st.caption(f"≈ {depth * 3.28084:.1f} ft")
        else:
            st.metric("📐 Max Depth", "N/A")
    
    with envelope_col4:
        coverage = zone_rules.get('max_lot_coverage')
        coverage_suffix = zone_rules.get('max_lot_coverage_suffix_0')
        if coverage:
            st.metric("📊 Lot Coverage", f"{coverage * 100:.0f}%")
            if parsed_info['has_suffix_zero'] and coverage_suffix:
                st.info(f"**-0:** {coverage_suffix}")
        else:
            st.metric("📊 Lot Coverage", "N/A")
    
    # Floor Area Ratio - Separate section for clarity
    if zone_rules.get('max_residential_floor_area_ratio') or zone_rules.get('max_residential_floor_area_ratio_suffix_0'):
        st.markdown("**Floor Area Ratio (FAR):**")
        far_col1, far_col2 = st.columns(2)
        
        with far_col1:
            far = zone_rules.get('max_residential_floor_area_ratio')
            if far:
                st.metric("Standard FAR", f"{far:.2f}")
        
        with far_col2:
            far_suffix = zone_rules.get('max_residential_floor_area_ratio_suffix_0')
            if far_suffix and parsed_info['has_suffix_zero']:
                st.metric("-0 Zone FAR", f"{far_suffix}")
                st.caption("Enhanced infill development")
    
    st.markdown("---")
    
    # Special Adjustments - Cleaner layout
    if any(key in zone_rules for key in ['corner_lot_adjustments', 'garage_adjustments', 'plan_subdivision_adjustments']):
        st.subheader("⚙️ Special Adjustments")
        
        adj_col1, adj_col2, adj_col3 = st.columns(3)
        
        # Corner Lot Adjustments
        if 'corner_lot_adjustments' in zone_rules:
            with adj_col1:
                with st.expander("🔄 Corner Lot Adjustments", expanded=True):
                    corner_adj = zone_rules['corner_lot_adjustments']
                    for key, value in corner_adj.items():
                        if isinstance(value, dict):
                            st.write(f"**{key.replace('_', ' ').title()}:**")
                            for sub_key, sub_value in value.items():
                                st.write(f"• {sub_key.replace('_', ' ').title()}: `{sub_value}`")
                        else:
                            st.write(f"**{key.replace('_', ' ').title()}:** `{value}`")
        
        # Garage Adjustments  
        if 'garage_adjustments' in zone_rules:
            with adj_col2:
                with st.expander("🚗 Garage Adjustments", expanded=True):
                    garage_adj = zone_rules['garage_adjustments']
                    for key, value in garage_adj.items():
                        if isinstance(value, dict):
                            st.write(f"**{key.replace('_', ' ').title()}:**")
                            for sub_key, sub_value in value.items():
                                st.write(f"• {sub_key.replace('_', ' ').title()}: `{sub_value}`")
                        else:
                            st.write(f"**{key.replace('_', ' ').title()}:** `{value}`")
        
        # Plan Subdivision Adjustments
        if 'plan_subdivision_adjustments' in zone_rules:
            with adj_col3:
                with st.expander("📋 Plan of Subdivision", expanded=True):
                    plan_adj = zone_rules['plan_subdivision_adjustments']
                    for key, value in plan_adj.items():
                        if isinstance(value, dict):
                            st.write(f"**{key.replace('_', ' ').title()}:**")
                            for sub_key, sub_value in value.items():
                                st.write(f"• {sub_key.replace('_', ' ').title()}: `{sub_value}`")
                        else:
                            st.write(f"**{key.replace('_', ' ').title()}:** `{value}`")
    
    # Special Provisions - Enhanced layout
    if zone_rules.get('max_dwelling_depth_special_provision'):
        st.markdown("---")
        st.subheader("⭐ Special Dwelling Depth Provisions")
        special = zone_rules['max_dwelling_depth_special_provision']
        for provision_type, details in special.items():
            with st.expander(f"🏠 {provision_type.replace('_', ' ').title()}", expanded=True):
                detail_cols = st.columns(len(details))
                for idx, (key, value) in enumerate(details.items()):
                    with detail_cols[idx]:
                        st.metric(key.replace('_', ' ').title(), f"{value}" + (" m" if "height" in key or "depth" in key or "yard" in key else ""))
    
    st.markdown("---")
    
    # Permitted Uses - Grid layout
    st.subheader("✅ Permitted Uses")
    permitted_uses = zone_rules.get('permitted_uses', [])
    if permitted_uses:
        # Calculate optimal columns (max 4, min 2)
        num_cols = min(4, max(2, len(permitted_uses) // 3))
        use_cols = st.columns(num_cols)
        
        for idx, use in enumerate(permitted_uses):
            with use_cols[idx % num_cols]:
                clean_use = use.replace('_', ' ').title()
                st.success(f"✓ {clean_use}")
    else:
        st.info("ℹ️ No specific permitted uses listed")
    
    # Use Restrictions - Clear formatting
    if 'use_restrictions' in zone_rules:
        st.markdown("---")
        st.subheader("⚠️ Use Restrictions")
        restrictions = zone_rules['use_restrictions']
        for restriction_type, restricted_uses in restrictions.items():
            clean_uses = [use.replace('_', ' ').title() for use in restricted_uses]
            st.error(f"🚫 **{restriction_type.replace('_', ' ').title()}:** {', '.join(clean_uses)}")
    
    # Footer with source information
    st.markdown("---")
    st.caption(f"📋 **Data Source:** {zone_rules.get('_metadata', {}).get('source', 'Oakville Zoning By-law 2014-014')} | **Last Updated:** {zone_rules.get('_metadata', {}).get('consolidated_date', 'N/A')}")

# ------------------------
# CONSERVATION, HERITAGE & ENVIRONMENTAL ANALYSIS
# ------------------------
def assess_heritage_conservation_requirements(zone_code: str, address: str, lat: float, lon: float, 
                                            lot_area: float, age_years: int = 10) -> dict:
    """Comprehensive heritage and conservation assessment for Oakville properties"""
    
    results = {
        "heritage_assessment": {},
        "conservation_requirements": {},
        "environmental_considerations": {},
        "required_studies": [],
        "approval_complexity": "standard"
    }
    
    # === HERITAGE ASSESSMENT ===
    # Check Heritage Conservation Districts (HCDs) in Oakville
    heritage_districts = {
        "Old Oakville": {
            "bounds": {"lat_min": 43.44, "lat_max": 43.47, "lon_min": -79.71, "lon_max": -79.68},
            "designation": "Heritage Conservation District",
            "requirements": ["Heritage Impact Assessment", "Heritage Permit", "Design Guidelines Compliance"]
        },
        "Bronte Village": {
            "bounds": {"lat_min": 43.39, "lat_max": 43.41, "lon_min": -79.71, "lon_max": -79.69},
            "designation": "Heritage Conservation District",
            "requirements": ["Heritage Impact Assessment", "Heritage Permit", "Village Character Guidelines"]
        }
    }
    
    # Heritage street keywords indicating potential heritage areas
    heritage_street_keywords = [
        'lakeshore', 'ontario', 'navy', 'trafalgar', 'kerr', 'randall', 'robinson', 
        'dunn', 'allan', 'rebecca', 'church', 'king', 'colborne', 'thomas'
    ]
    
    address_lower = address.lower()
    heritage_concern = False
    heritage_district = None
    
    # Check if in heritage conservation district
    for district_name, district_info in heritage_districts.items():
        bounds = district_info["bounds"]
        if (bounds["lat_min"] <= lat <= bounds["lat_max"] and 
            bounds["lon_min"] <= lon <= bounds["lon_max"]):
            heritage_district = district_name
            heritage_concern = True
            break
    
    # Check heritage street names
    if not heritage_concern:
        heritage_concern = any(keyword in address_lower for keyword in heritage_street_keywords)
    
    # Age-based heritage potential (properties over 40 years)
    if age_years > 40:
        heritage_concern = True
    
    results["heritage_assessment"] = {
        "heritage_concern_level": "high" if heritage_district else "medium" if heritage_concern else "low",
        "heritage_district": heritage_district,
        "potential_designation": heritage_concern,
        "age_consideration": age_years > 40,
        "required_assessments": []
    }
    
    if heritage_district:
        district_requirements = heritage_districts[heritage_district]["requirements"]
        results["heritage_assessment"]["required_assessments"].extend(district_requirements)
        results["required_studies"].extend(district_requirements)
        results["approval_complexity"] = "complex"
    elif heritage_concern:
        results["heritage_assessment"]["required_assessments"] = ["Heritage Screening Assessment"]
        results["required_studies"].append("Heritage Screening Assessment")
    
    # === CONSERVATION REQUIREMENTS ===
    # Conservation use is permitted in all residential zones per Oakville by-law
    conservation_permitted = zone_code.startswith(('RL', 'RM', 'RH')) or zone_code == 'RUC'
    
    results["conservation_requirements"] = {
        "conservation_use_permitted": conservation_permitted,
        "zone_allows_conservation": conservation_permitted,
        "conservation_overlay": False,  # Would need API check for actual overlays
        "natural_heritage_features": []
    }
    
    # Check for natural heritage indicators in address
    natural_keywords = ['creek', 'ravine', 'valley', 'brook', 'glen', 'woods', 'forest']
    natural_features = [keyword for keyword in natural_keywords if keyword in address_lower]
    
    if natural_features:
        results["conservation_requirements"]["natural_heritage_features"] = natural_features
        results["required_studies"].append("Environmental Impact Study")
        results["approval_complexity"] = "complex"
    
    # === ENVIRONMENTAL CONSIDERATIONS ===
    results["environmental_considerations"] = {
        "watercourse_proximity": False,
        "floodplain_risk": "low",
        "tree_preservation_required": False,
        "soil_contamination_risk": "low"
    }
    
    # Check for watercourse proximity (Sixteen Mile Creek, etc.)
    watercourse_keywords = ['sixteen mile', 'creek', 'river', 'stream']
    if any(keyword in address_lower for keyword in watercourse_keywords):
        results["environmental_considerations"]["watercourse_proximity"] = True
        results["required_studies"].append("Watercourse Assessment")
    
    return results

def assess_arborist_requirements(zone_code: str, address: str, lat: float, lon: float, 
                               lot_area: float, lot_frontage: float) -> dict:
    """Comprehensive arborist and tree preservation assessment"""
    
    results = {
        "arborist_report_required": False,
        "tree_preservation_bylaw_applies": True,
        "protected_tree_likelihood": "medium",
        "tree_removal_permits_required": [],
        "preservation_requirements": {},
        "estimated_tree_survey_cost": 0
    }
    
    # === ARBORIST REPORT REQUIREMENTS ===
    # Based on Oakville Tree Protection By-law
    
    arborist_triggers = []
    
    # Large lot requirement (typically >1000m²)
    if lot_area > 1000:
        arborist_triggers.append("Large lot size (>1000m² / >10,764 sq ft)")
    
    # Estate zones (RL1, RL2) typically have mature trees
    if zone_code in ['RL1', 'RL2']:
        arborist_triggers.append("Estate residential zone with mature tree potential")
    
    # Wide frontage lots often have significant trees
    if lot_frontage > 25:
        arborist_triggers.append("Wide frontage lot (>25m)")
    
    # Natural heritage area indicators
    address_lower = address.lower()
    tree_keywords = [
        'oak', 'maple', 'elm', 'pine', 'cedar', 'birch', 'willow',  # Tree species
        'woods', 'forest', 'grove', 'park', 'garden',               # Tree areas
        'ravine', 'creek', 'valley', 'glen'                         # Natural features
    ]
    
    natural_indicators = [keyword for keyword in tree_keywords if keyword in address_lower]
    if natural_indicators:
        arborist_triggers.append(f"Natural heritage indicators: {', '.join(natural_indicators)}")
    
    # Mature neighborhood indicators (established before 1980)
    mature_neighborhoods = [
        'glen abbey', 'clearview', 'eastlake', 'west oak trails', 'old oakville',
        'bronte', 'iroquois ridge', 'college park', 'uptown core'
    ]
    
    if any(neighborhood in address_lower for neighborhood in mature_neighborhoods):
        arborist_triggers.append("Mature established neighborhood")
    
    # === PROTECTED TREE ASSESSMENT ===
    protected_tree_criteria = {
        "diameter_threshold_cm": 15,  # Trees >15cm diameter typically protected
        "heritage_trees": zone_code in ['RL1', 'RL2'],
        "significant_woodland": lot_area > 2000,
        "watercourse_buffer": any(word in address_lower for word in ['creek', 'river', 'stream'])
    }
    
    # Calculate likelihood of protected trees
    likelihood_score = 0
    if lot_area > 1000: likelihood_score += 2
    if zone_code in ['RL1', 'RL2']: likelihood_score += 2
    if natural_indicators: likelihood_score += 2
    if lot_frontage > 25: likelihood_score += 1
    
    if likelihood_score >= 5:
        results["protected_tree_likelihood"] = "high"
    elif likelihood_score >= 3:
        results["protected_tree_likelihood"] = "medium"
    else:
        results["protected_tree_likelihood"] = "low"
    
    # === REQUIREMENTS DETERMINATION ===
    if arborist_triggers:
        results["arborist_report_required"] = True
        results["tree_removal_permits_required"] = ["Tree Removal Permit", "Site Plan Review"]
        
        # Estimate costs
        base_cost = 2500  # Base arborist report
        if lot_area > 2000: base_cost += 1000  # Large lot surcharge
        if results["protected_tree_likelihood"] == "high": base_cost += 1500  # Complex assessment
        
        results["estimated_tree_survey_cost"] = base_cost
    
    # === PRESERVATION REQUIREMENTS ===
    results["preservation_requirements"] = {
        "tree_protection_fencing": results["arborist_report_required"],
        "root_protection_zone": results["protected_tree_likelihood"] in ["high", "medium"],
        "replacement_planting_required": True,  # Generally required for removals
        "cash_in_lieu_option": lot_area < 500,  # Small lots may pay cash instead
        "monitoring_during_construction": results["protected_tree_likelihood"] == "high"
    }
    
    results["arborist_triggers"] = arborist_triggers
    
    return results

# ------------------------
# PROPERTY VALUATION
# ------------------------
def estimate_property_value(zone_code, lot_area, building_area, building_type="detached_dwelling", 
                          num_bedrooms=3, num_bathrooms=2.5, age_years=10, 
                          nearby_parks=0, waterfront=False, heritage_designated=False, 
                          is_corner=False, special_provision=None):
    """Comprehensive property valuation"""
    
    # Base land value
    base_land_value_per_sqm = BASE_LAND_VALUES.get(zone_code, BASE_LAND_VALUES.get(zone_code.replace('-0', ''), 400))
    base_land_value = base_land_value_per_sqm * lot_area
    
    # Building value with depreciation
    building_value_per_sqm = BUILDING_VALUES.get(building_type, 2800)
    depreciation_rate = 0.02  # 2% per year
    building_value = building_area * building_value_per_sqm * (1 - depreciation_rate * min(age_years, 40))
    
    # Feature adjustments
    bedroom_adjustment = max(0, (num_bedrooms - 3)) * 25000
    bathroom_adjustment = max(0, (num_bathrooms - 2.5)) * 15000
    
    # Location adjustments
    location_adjustments = 0
    if waterfront:
        location_adjustments += base_land_value * LOCATION_PREMIUMS['waterfront']
    if nearby_parks > 0:
        location_adjustments += base_land_value * LOCATION_PREMIUMS['park_adjacent'] * min(nearby_parks, 3)
    if heritage_designated:
        location_adjustments += base_land_value * LOCATION_PREMIUMS['heritage_designated']
    if is_corner:
        location_adjustments += base_land_value * LOCATION_PREMIUMS['corner_lot']
    if zone_code.endswith('-0'):
        location_adjustments += base_land_value * LOCATION_PREMIUMS['suffix_0_zone']
    if special_provision:
        location_adjustments += base_land_value * LOCATION_PREMIUMS['special_provision']
    
    # Total value calculation
    total_value = (
        base_land_value + building_value + bedroom_adjustment + 
        bathroom_adjustment + location_adjustments
    )
    
    # Market adjustment
    market_adjustment = 1.05  # 5% hot market
    final_value = total_value * market_adjustment
    
    return {
        "estimated_value": round(final_value, -3),
        "land_value": round(base_land_value),
        "building_value": round(building_value),
        "adjustments": {
            "bedrooms": bedroom_adjustment,
            "bathrooms": bathroom_adjustment,
            "location_total": round(location_adjustments)
        },
        "confidence_range": {
            "low": round(final_value * 0.85, -3),
            "high": round(final_value * 1.15, -3)
        },
        "price_per_sqm": round(final_value / lot_area) if lot_area > 0 else 0,
        "valuation_date": datetime.now().strftime('%Y-%m-%d %H:%M')
    }

def calculate_development_value(zone_code, lot_area, development_potential, current_value):
    """Calculate development feasibility and potential profit"""
    
    # Determine development type based on zone
    if zone_code.startswith('RM'):
        if 'townhouse' in zone_code or zone_code == 'RM1':
            unit_type = 'townhouse'
            avg_unit_value = 650000
            construction_cost_per_unit = 280000
        elif zone_code in ['RM2']:
            unit_type = 'back_to_back_townhouse'
            avg_unit_value = 550000
            construction_cost_per_unit = 250000
        else:
            unit_type = 'apartment'
            avg_unit_value = 450000
            construction_cost_per_unit = 220000
    else:
        # Single family zones
        unit_type = 'detached_dwelling'
        avg_unit_value = current_value
        return {"message": "Single family zone - limited redevelopment potential"}
    
    # Calculate potential units (simplified)
    max_floor_area = development_potential.get('max_floor_area', 0)
    if max_floor_area is None:
        max_floor_area = 0
    
    avg_unit_size = 120  # 120 sqm (~1,292 sq ft) average unit
    potential_units = int(max_floor_area / avg_unit_size) if max_floor_area and max_floor_area > 0 else 1
    
    if potential_units <= 1:
        return {"message": "No multi-unit development potential"}
    
    # Financial analysis
    gross_revenue = avg_unit_value * potential_units
    total_construction = construction_cost_per_unit * potential_units
    soft_costs = total_construction * 0.20  # 20% soft costs
    land_cost = current_value * 1.1  # 10% premium for development land
    
    total_costs = total_construction + soft_costs + land_cost
    potential_profit = gross_revenue - total_costs
    profit_margin = (potential_profit / gross_revenue * 100) if gross_revenue > 0 else 0
    
    return {
        "unit_type": unit_type,
        "potential_units": potential_units,
        "gross_revenue": round(gross_revenue),
        "total_costs": round(total_costs),
        "construction_costs": round(total_construction),
        "soft_costs": round(soft_costs),
        "land_cost": round(land_cost),
        "potential_profit": round(potential_profit),
        "profit_margin": round(profit_margin, 1),
        "feasible": profit_margin > 15,
        "roi_percentage": round((potential_profit / total_costs * 100), 1) if total_costs > 0 else 0
    }

# ------------------------
# PDF DATA PREPARATION
# ------------------------
def prepare_property_data_for_pdf(parcel, zone_code, full_zone_code, development_potential, setbacks, lot_area_m2, frontage, depth):
    """Prepare all property data for PDF generation"""
    
    # Get coordinates for additional API checks
    lat = parcel.get('lat')
    lon = parcel.get('lon')
    
    # Basic property information
    property_data = {
        'address': parcel.get('address', 'Unknown Address'),
        'designation': full_zone_code or zone_code or 'Unknown',
        'lot_area': round(lot_area_m2, 2) if lot_area_m2 else 0,
        'frontage': round(frontage, 2) if frontage else 0,
        'depth': round(depth, 2) if depth else 0,
    }
    
    # Get real-time conservation authority data
    if lat and lon:
        try:
            conservation_check = check_conservation_authority(lat, lon)
            ca_name = conservation_check.get('conservation_authority', 'Unknown')
            if 'Halton' in ca_name:
                permits_req = conservation_check.get('permits_required', 'Unknown')
                if permits_req == 'Likely Required':
                    property_data['conservation_authority'] = "Halton CA - Permits Required"
                elif permits_req == 'Possibly Required':
                    property_data['conservation_authority'] = "Halton CA - Contact Required"
                else:
                    property_data['conservation_authority'] = "Halton Conservation Authority"
            else:
                property_data['conservation_authority'] = ca_name
                
            # Get heritage status
            heritage_check = check_heritage_property_status(lat, lon)
            property_data['heritage_status'] = 'Yes' if heritage_check.get('is_heritage') else 'No'
            
            # Get development applications
            dev_check = check_development_applications(lat, lon)
            property_data['development_status'] = 'Yes' if dev_check.get('has_applications') else 'No'
            
        except:
            property_data['conservation_authority'] = 'Unable to verify - contact required'
            property_data['heritage_status'] = 'Unable to check'
            property_data['development_status'] = 'Unable to check'
    else:
        property_data['conservation_authority'] = 'Unknown - coordinates required'
        property_data['heritage_status'] = 'Unknown'  
        property_data['development_status'] = 'Unknown'
    
    # Set default values for other statuses
    property_data.update({
        'conservation_status': 'No',  # Environmental conservation overlay
        'arborist_status': 'Yes'  # Default assumption for tree preservation
    })
    
    # Extract development potential data
    if development_potential:
        # Max RFA data (direct from development_potential)
        property_data.update({
            'max_floor_area': development_potential.get('max_floor_area', 0),
            'max_far': development_potential.get('max_floor_area_ratio', 0)
        })
        
        # Building size limits
        property_data.update({
            'max_building_depth': development_potential.get('max_building_depth', 0),
            'garage_projection': development_potential.get('garage_projection_beyond_dwelling', 0)
        })
        
        # Coverage data (direct from development_potential)
        property_data.update({
            'max_coverage_area': development_potential.get('max_coverage_area', 0),
            'max_coverage_percent': development_potential.get('max_coverage_percent', 0)
        })
        
        # Height limits
        height_data = development_potential.get('height_limits', {})
        property_data.update({
            'building_height': height_data.get('building_height', 0),
            'flat_roof_height': height_data.get('flat_roof', 0),
            'eaves_height': 'N/A',
            'storeys': height_data.get('storeys', 2)
        })
        
        # Final buildable analysis
        final_analysis = development_potential.get('final_buildable_analysis', {})
        property_data.update({
            'final_buildable_sqft': final_analysis.get('final_buildable_sqft', 0),
            'final_buildable_sqm': final_analysis.get('final_buildable_sqm', 0),
            'confidence_level': final_analysis.get('confidence_level', 'Moderate')
        })
    
    # Setback data - structured for PDF generator
    if setbacks:
        front_yard = setbacks.get('front_yard', 'N/A')
        property_data['setbacks'] = {
            'front_yard': front_yard,
            'interior_side_min': setbacks.get('interior_side_min', setbacks.get('interior_side', 'N/A')),
            'interior_side_max': setbacks.get('interior_side_max', setbacks.get('interior_side', 'N/A')),
            'rear_yard': setbacks.get('rear_yard', 'N/A')
        }
        property_data['has_suffix_zero'] = full_zone_code and '-0' in full_zone_code
    else:
        property_data['setbacks'] = {
            'front_yard': 'N/A',
            'interior_side_min': 'N/A',
            'interior_side_max': 'N/A',
            'rear_yard': 'N/A'
        }
        property_data['has_suffix_zero'] = False
    
    # Add comprehensive zone details and special provisions
    if zone_code:
        try:
            # Get detailed zone rules
            zone_rules = get_comprehensive_zone_rules(full_zone_code or zone_code)
            if zone_rules and 'error' not in zone_rules:
                # Add zone information
                property_data['zone_name'] = zone_rules.get('name', 'N/A')
                property_data['zone_category'] = zone_rules.get('category', 'N/A')
                
                # Get parsed zone info for special provisions
                parsed_info = zone_rules.get('_parsed_info', {})
                if parsed_info.get('special_provision'):
                    property_data['special_provision'] = parsed_info['special_provision']
                    # Get special provision details
                    sp_data = SPECIAL_PROVISIONS.get(parsed_info['special_provision'], {})
                    property_data['special_provision_description'] = sp_data.get('description', 'Site-specific zoning requirements')
                else:
                    property_data['special_provision'] = None
                    property_data['special_provision_description'] = None
                
                # Add suffix-0 specific details if applicable
                if parsed_info.get('has_suffix_zero'):
                    property_data['has_suffix_zero'] = True
                    property_data['suffix_zero_details'] = {
                        'front_yard_setback': 'Existing building setback minus 1 metre',
                        'max_height': zone_rules.get('max_height_suffix_0', zone_rules.get('max_height', 'N/A')),
                        'max_storeys': zone_rules.get('max_storeys_suffix_0', zone_rules.get('max_storeys', 'N/A')),
                        'max_coverage': zone_rules.get('max_lot_coverage_suffix_0', zone_rules.get('max_lot_coverage', 'N/A')),
                        'max_far': zone_rules.get('max_residential_floor_area_ratio_suffix_0', zone_rules.get('max_residential_floor_area_ratio', 'N/A')),
                        'description': 'Zone modifications for infill development - reduced setbacks and enhanced permissions'
                    }
                else:
                    property_data['suffix_zero_details'] = None
                
                # Add permitted uses
                permitted_uses = zone_rules.get('permitted_uses', [])
                property_data['permitted_uses'] = [use.replace('_', ' ').title() for use in permitted_uses[:5]]  # Limit to first 5
                
                # Add use restrictions if any
                restrictions = zone_rules.get('use_restrictions', {})
                if restrictions:
                    restricted_list = []
                    for category, uses in restrictions.items():
                        restricted_list.extend(uses[:2])  # Limit items
                    property_data['use_restrictions'] = [use.replace('_', ' ').title() for use in restricted_list[:3]]
                else:
                    property_data['use_restrictions'] = []
                    
        except Exception as e:
            # Fallback if zone rules lookup fails
            property_data['zone_name'] = 'N/A'
            property_data['zone_category'] = 'N/A'
            property_data['special_provision'] = None
            property_data['special_provision_description'] = None
            property_data['permitted_uses'] = []
            property_data['use_restrictions'] = []
    
    return property_data

# ------------------------
# STREAMLIT APP
# ------------------------
def main():
    st.set_page_config(
        page_title="Oakville Zoning Analyzer",
        page_icon="🏡",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🏡 Oakville Zoning Analyzer")
    st.markdown("### AI-Powered Property Analysis & Valuation with Real API Integration")
    
    # Sidebar inputs
    with st.sidebar:
        st.header("🔍 Property Lookup")
        
        # Input method selection
        input_method = st.radio("Input Method", ["Address Search", "Manual Coordinates"], key="input_method")
        
        if input_method == "Address Search":
            address = st.text_input("Enter property address:", "383 MAPLEHURST AVE")
            use_geocoding = st.checkbox("🌍 Use Geocoding if not found", value=True)
            
            if st.button("🔎 Lookup Property", type="primary"):
                st.session_state['lookup_triggered'] = True
                st.session_state['address'] = address
                st.session_state['use_geocoding'] = use_geocoding
        else:
            st.info("💡 Enter coordinates directly if you know them")
            col1, col2 = st.columns(2)
            with col1:
                manual_lat = st.number_input("Latitude", value=43.4685, format="%.6f", key="direct_lat")
            with col2:
                manual_lon = st.number_input("Longitude", value=-79.7071, format="%.6f", key="direct_lon")
            
            if st.button("🗺️ Lookup by Coordinates", type="primary"):
                st.session_state['lookup_triggered'] = True
                st.session_state['manual_lat'] = manual_lat
                st.session_state['manual_lon'] = manual_lon
        
        # Debug mode toggle
        debug_mode = st.checkbox("🔧 Show Debug Information", value=False)
        
        st.divider()
        
        # Building details for valuation
        st.header("🏠 Building Details")
        building_area = st.number_input("Building Area (m² / sq ft)", min_value=50.0, value=200.0, step=10.0)
        st.caption(f"≈ {building_area * 10.764:.0f} sq ft")
        bedrooms = st.number_input("Bedrooms", min_value=1, value=3, step=1)
        bathrooms = st.number_input("Bathrooms", min_value=1.0, value=2.5, step=0.5)
        age = st.number_input("Building Age (years)", min_value=0, value=10, step=1)
        
        st.header("📖 How to Use")
        with st.expander("🔍 **Search Methods**", expanded=True):
            st.write("**Address Search:** Enter full address (e.g., '383 MAPLEHURST AVE')")
            st.write("**Coordinates:** Use if address not found in database")
            st.write("**🌍 Geocoding:** Automatically enabled for unlisted addresses")
        
        with st.expander("📊 **Understanding Results**"):
            st.write("**Zone Code:** Shows base zone + modifications (e.g., RL1-0)")
            st.write("**Suffix-0:** Enhanced infill development permissions")
            st.write("**Special Provisions:** Site-specific requirements (SP:1, SP:2)")
            st.write("**Setbacks:** Building placement requirements from property lines")
        
        with st.expander("🏗️ **Development Analysis**"):
            st.write("**Max Coverage:** Maximum building footprint allowed")
            st.write("**Floor Area Ratio:** Maximum floor area relative to lot size")
            st.write("**Final Buildable:** Estimated buildable area after all restrictions")
            st.write("**Confidence Level:** Reliability of calculations")
        
        with st.expander("📄 **PDF Reports**"):
            st.write("**Generate Report:** Creates comprehensive property analysis")
            st.write("**Includes:** All calculations, zone details, authority requirements")
            st.write("**Professional Format:** Suitable for planning applications")
    
    # Main content - Show system overview when no search is active
    if 'lookup_triggered' not in st.session_state or not st.session_state.get('lookup_triggered', False):
        # System Overview Section
        st.markdown("---")
        st.header("🏗️ Oakville Real Estate Analyzer - System Overview")
        
        # Introduction
        intro_col1, intro_col2 = st.columns([2, 1])
        with intro_col1:
            st.markdown("""
            ### 🎯 **What This System Does**
            
            The Oakville Real Estate Analyzer is an AI-powered platform that provides comprehensive property analysis 
            for Oakville, Ontario. It combines zoning regulations, real-time municipal data, and development calculations 
            to help property owners, developers, and real estate professionals make informed decisions.
            
            **Key Features:**
            - 🏘️ **Zoning Analysis** - Detailed zone code interpretation with special provisions
            - 📐 **Development Calculations** - Maximum buildable area, coverage, and setbacks
            - 🏛️ **Authority Integration** - Real-time checks for heritage, conservation, and development status
            - 📄 **Professional Reports** - Comprehensive PDF reports for planning applications
            """)
            
        with intro_col2:
            st.info("""
            **🚀 Quick Start**
            
            1️⃣ Enter property address
            
            2️⃣ Review zoning analysis
            
            3️⃣ Check development potential
            
            4️⃣ Download PDF report
            """)
        
        st.markdown("---")
        
        # Technical Implementation Details
        st.subheader("⚙️ How the System Works")
        
        tech_tabs = st.tabs(["🗂️ Data Sources", "🔄 Processing", "📊 Calculations", "🎯 Accuracy"])
        
        with tech_tabs[0]:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("""
                **Municipal APIs:**
                - Oakville Parcels & Addresses Database
                - Zoning By-law 2014-014 (Live Data)
                - Heritage Properties Registry
                - Development Applications Tracker
                - Conservation Authority Watersheds
                """)
            with col2:
                st.markdown("""
                **Zoning Regulations:**
                - Comprehensive zone rules (RL1-RL11, RM, RH)
                - Suffix-0 zone modifications
                - Special provisions (SP:1, SP:2, etc.)
                - Setback calculations with corner lot adjustments
                - Building envelope analysis
                """)
        
        with tech_tabs[1]:
            st.markdown("""
            **Data Processing Pipeline:**
            
            1. **Address Resolution** → Geocoding → Coordinate validation
            2. **Spatial Queries** → API calls to municipal databases
            3. **Zone Analysis** → Rule interpretation and modification application
            4. **Calculations** → Building envelope, coverage, and FAR computations
            5. **Authority Checks** → Real-time heritage, conservation, and development verification
            6. **Report Generation** → Professional PDF with all findings
            """)
        
        with tech_tabs[2]:
            calculation_col1, calculation_col2 = st.columns(2)
            with calculation_col1:
                st.markdown("""
                **Zoning Calculations:**
                - **Lot Coverage**: `lot_area × coverage_percentage`
                - **Floor Area Ratio**: `lot_area × FAR_coefficient`
                - **Maximum Height**: Zone-specific limits + suffix modifications
                - **Setbacks**: Front/rear/side yard requirements
                """)
            with calculation_col2:
                st.markdown("""
                **Development Analysis:**
                - **Buildable Area**: Coverage - setback deductions
                - **Gross Floor Area**: Coverage × storeys allowed
                - **Final Buildable**: GFA - circulation - mechanical
                - **Confidence Level**: Based on data completeness
                """)
        
        with tech_tabs[3]:
            accuracy_col1, accuracy_col2 = st.columns(2)
            with accuracy_col1:
                st.success("""
                **High Accuracy Elements:**
                - Zoning designations (Official By-law)
                - Parcel boundaries (Municipal database)
                - Heritage status (Live API)
                - Conservation authority jurisdiction
                """)
            with accuracy_col2:
                st.warning("""
                **Verification Recommended:**
                - Survey-dependent setbacks (existing buildings)
                - Site-specific conditions
                - Special provision interpretations
                - Development application requirements
                """)
        
        st.markdown("---")
        
        # Zone Types Overview
        st.subheader("🏘️ Supported Zone Types")
        
        zone_col1, zone_col2, zone_col3 = st.columns(3)
        with zone_col1:
            st.markdown("""
            **Residential Low Density**
            - RL1 to RL11 (various densities)
            - Suffix-0 modifications available
            - Special provisions (SP:1, SP:2)
            - Detached dwellings primary use
            """)
        with zone_col2:
            st.markdown("""
            **Medium/High Density**
            - RM1-RM4 (Medium density)
            - RH (High density residential)
            - Multiple dwelling types
            - Enhanced FAR calculations
            """)
        with zone_col3:
            st.markdown("""
            **Special Features**
            - Corner lot adjustments
            - Garage placement rules
            - Height bonus provisions
            - Infill development support
            """)
        
        st.markdown("---")
        
        # Sample Analysis
        st.subheader("📋 Sample Analysis Results")
        st.markdown("**Example: 383 MAPLEHURST AVE (RL1-0 Zone)**")
        
        sample_col1, sample_col2, sample_col3 = st.columns(3)
        with sample_col1:
            st.metric("Zone Designation", "RL1-0")
            st.caption("Low density with infill permissions")
        with sample_col2:
            st.metric("Max Coverage", "25%")
            st.caption("Enhanced from standard 20%")
        with sample_col3:
            st.metric("Front Setback", "Existing -1m")
            st.caption("Reduced for infill development")
        
        st.info("💡 **Ready to analyze your property?** Enter an address in the sidebar to get started!")
        
    elif 'lookup_triggered' in st.session_state and st.session_state['lookup_triggered']:
        # Determine input method based on what data is available in session state
        if 'address' in st.session_state:
            input_method = "address"
        elif 'manual_lat' in st.session_state and 'manual_lon' in st.session_state:
            input_method = "coordinates"
        else:
            input_method = "address"  # Default fallback
        
        if input_method == "address":
            # Address-based lookup
            address = st.session_state['address']
            use_geocoding = st.session_state.get('use_geocoding', True)
            
            # Show debug info
            if debug_mode:
                st.info(f"🔍 Searching for: {address}")
                st.info(f"📊 CSV Database has {len(PARCEL_DATA)} addresses loaded")
            
            with st.spinner("🔍 Fetching property data..."):
                parcel = get_parcel(address)
            
            # If not found and geocoding enabled, try geocoding
            if not parcel and use_geocoding:
                st.info("🌍 Address not found in parcel database, trying geocoding...")
                with st.spinner("🌍 Geocoding address..."):
                    coords = geocode_address(address)
                    if coords:
                        st.success(f"📍 Geocoded to: {coords['lat']:.6f}, {coords['lon']:.6f}")
                        # Create a basic parcel record with geocoded coordinates
                        parcel = {
                            "address": address,
                            "lot_area": None,
                            "geometry": None,
                            "roll_number": None,
                            "legal_desc": None,
                            "frontage": None,
                            "depth": None,
                            "frontage_meters": None,
                            "depth_meters": None,
                            "source": "geocoded",
                            "lat": coords['lat'],
                            "lon": coords['lon']
                        }
            
            if debug_mode and parcel:
                st.success(f"✅ Found via: {parcel.get('source', 'unknown')}")
                with st.expander("🔧 Raw Parcel Data"):
                    st.json(parcel)
            
            if not parcel:
                st.error("❌ No parcel found for this address. Please check the address and try again.")
                if debug_mode:
                    st.info("💡 Try one of these formats: '383 MAPLEHURST AVE', '383 Maplehurst Avenue', '383 Maplehurst'")
                return
                
        else:
            # Coordinate-based lookup
            lat = st.session_state['manual_lat']
            lon = st.session_state['manual_lon']
            
            if debug_mode:
                st.info(f"🗺️ Using coordinates: {lat:.6f}, {lon:.6f}")
            
            # Create a basic parcel record with coordinates
            parcel = {
                "address": f"Coordinates: {lat:.6f}, {lon:.6f}",
                "lot_area": None,
                "geometry": None,
                "roll_number": None,
                "legal_desc": None,
                "frontage": None,
                "depth": None,
                "frontage_meters": None,
                "depth_meters": None,
                "source": "manual_coordinates",
                "lat": lat,
                "lon": lon
            }
        
        # Get basic property data
        lot_area_m2 = parcel["lot_area"]
        lot_area_ft2 = lot_area_m2 * 10.764 if lot_area_m2 else None
        
        # Handle geometry for coordinate extraction
        if parcel.get("geometry"):
            lat, lon = get_centroid(parcel["geometry"])
            if debug_mode:
                st.info(f"🗺️ Coordinates: {lat:.6f}, {lon:.6f}")
            with st.spinner("🗺️ Fetching zoning information..."):
                zoning_info = get_zone(lat, lon) if lat and lon else None
                if debug_mode and zoning_info:
                    with st.expander("🔧 Raw Zoning Data"):
                        st.json(zoning_info)
        else:
            # For CSV data without geometry, we'll need coordinates from user or geocoding
            st.info("💡 Property found in local database. Please provide coordinates for zoning lookup.")
            col1, col2 = st.columns(2)
            with col1:
                lat = st.number_input("Latitude", value=43.4685, format="%.6f", key="manual_lat")
            with col2:
                lon = st.number_input("Longitude", value=-79.7071, format="%.6f", key="manual_lon")
            
            if st.button("🗺️ Get Zoning Info"):
                with st.spinner("🗺️ Fetching zoning information..."):
                    zoning_info = get_zone(lat, lon)
                    if debug_mode and zoning_info:
                        with st.expander("🔧 Raw Zoning Data"):
                            st.json(zoning_info)
            else:
                zoning_info = None
        
        zone_code = zoning_info.get('zone') if zoning_info else None
        special_provision = zoning_info.get('special_provision') if zoning_info else None
        full_zone_code = zoning_info.get('full_zone_code') if zoning_info else None
        
        # Display basic information
        source_icons = {
            "api_exact": "🌐 API (Exact)",
            "api_like": "🌐 API (Match)",
            "api_partial_match": "🌐 API (Partial)",
            "local_csv": "🗂️ Local Database",
            "local_csv_fuzzy": "🗂️ Local DB (Fuzzy)",
            "geocoded": "🌍 Geocoded",
            "manual_coordinates": "🗺️ Manual Coords"
        }
        data_source = source_icons.get(parcel.get("source"), "Unknown")
        st.success(f"✅ Property data retrieved successfully! ({data_source})")
        
        # Show lot area and calculated dimensions
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            display_address = parcel.get("address", "Unknown")
            st.metric("📍 Address", display_address if len(display_address) < 20 else display_address[:17] + "...")
        
        with col2:
            if lot_area_ft2:
                st.metric("📐 Lot Area", f"{lot_area_ft2:,.0f} sq.ft")
                st.caption(f"({lot_area_m2:.1f} m²)")
            else:
                st.metric("📐 Lot Area", "N/A")
        
        with col3:
            frontage = parcel.get("frontage")
            if frontage:
                st.metric("📏 Frontage", f"{frontage:.1f} ft")
                st.caption(f"({parcel.get('frontage_meters', 0):.1f} m)")
            else:
                st.metric("📏 Frontage", "Not calculated")
        
        with col4:
            depth = parcel.get("depth")
            if depth:
                st.metric("📐 Depth", f"{depth:.1f} ft")
                st.caption(f"({parcel.get('depth_meters', 0):.1f} m)")
            else:
                st.metric("📐 Depth", "Not calculated")
        
        # Additional info row
        col1, col2, col3 = st.columns(3)
        with col1:
            # Display full zone code with special provisions if available
            display_zone = full_zone_code or zone_code or "Unknown"
            st.metric("🏘️ Zone Code", display_zone)
        with col2:
            # Display coordinates instead of data source
            if lat and lon:
                st.metric("📍 Coordinates", f"{lat:.6f}, {lon:.6f}")
                st.caption(f"Lat: {lat:.6f}° | Lon: {lon:.6f}°")
            else:
                st.metric("📍 Coordinates", "Not available")
        with col3:
            if parcel.get("roll_number"):
                st.metric("📋 Roll Number", parcel["roll_number"])
            else:
                # Show zone classification as additional info instead of data source
                st.metric("🏘️ Zone Type", "Residential" if zone_code and zone_code.startswith(('RL', 'RM', 'RH')) else "Unknown")
        
        # Get lot dimensions - use calculated if available, otherwise manual input
        st.header("📏 Lot Dimensions")
        
        calculated_frontage = parcel.get("frontage_meters")
        calculated_depth = parcel.get("depth_meters")
        
        if calculated_frontage and calculated_depth:
            st.success("✅ Dimensions automatically calculated from parcel geometry!")
            col1, col2 = st.columns(2)
            with col1:
                frontage = st.number_input("Lot Frontage (m)", min_value=0.0, value=calculated_frontage, step=0.1, key="calc_frontage")
                st.caption(f"Auto-calculated: {calculated_frontage:.1f}m ({parcel.get('frontage', 0):.1f}ft)")
            with col2:
                depth = st.number_input("Lot Depth (m)", min_value=0.0, value=calculated_depth, step=0.1, key="calc_depth")
                st.caption(f"Auto-calculated: {calculated_depth:.1f}m ({parcel.get('depth', 0):.1f}ft)")
            st.info("💡 Values above are auto-calculated. You can adjust them if needed.")
        else:
            st.info("📐 Please provide lot dimensions for zoning analysis (geometry not available for automatic calculation).")
            col1, col2 = st.columns(2)
            with col1:
                frontage = st.number_input("Lot Frontage (m)", min_value=0.0, value=0.0, step=0.1, key="manual_frontage")
                st.caption("Enter 0 if unknown - will display as N/A")
            with col2:
                depth = st.number_input("Lot Depth (m)", min_value=0.0, value=0.0, step=0.1, key="manual_depth")
                st.caption("Enter 0 if unknown - will display as N/A")
        
        # Show available addresses for testing
        if st.checkbox("🔍 Show Sample Addresses from Database"):
            st.subheader("📋 Available Addresses in Local Database")
            sample_addresses = list(PARCEL_DATA.keys())[:20]  # Show first 20 addresses
            for i, addr in enumerate(sample_addresses):
                if i % 4 == 0:
                    cols = st.columns(4)
                with cols[i % 4]:
                    if st.button(f"📍 {addr}", key=f"addr_{i}"):
                        st.session_state['address'] = addr
                        st.rerun()
        
        if zone_code:
            # Zoning Analysis Tab
            tabs = st.tabs(["🗺️ Zoning Analysis", "💰 Property Valuation", "🏗️ Development Potential", "📊 Special Requirements", "📋 Zone Rules"])
            
            with tabs[0]:
                st.header("🗺️ Zoning Analysis & Compliance")
                
                # Get comprehensive zoning analysis (corner lot detection can be added later if needed)
                corner_lot = False  # Default value since we removed property features from sidebar
                development_potential = calculate_development_potential(zone_code, lot_area_m2, frontage, depth, corner_lot)
                
                if "error" in development_potential:
                    st.error(f"❌ {development_potential['error']}")
                else:
                    # Compliance status
                    if development_potential['meets_minimum_requirements']:
                        st.success("✅ Property meets all minimum zoning requirements")
                    else:
                        st.error("❌ Property has zoning compliance issues")
                        for violation in development_potential['violations']:
                            st.error(f"• {violation}")
                    
                    # Display warnings
                    for warning in development_potential.get('warnings', []):
                        st.warning(f"⚠️ {warning}")
                    
                    # COMPREHENSIVE ZONING ANALYSIS - Matching Municipal Report Format
                    st.markdown("---")
                    
                    # Parse zone information for special handling
                    base_zone, suffix, special_provision_parsed = parse_zone_code(zone_code)
                    parsed_info = {
                        'has_suffix_zero': suffix == '-0',
                        'base_zone': base_zone,
                        'suffix': suffix,
                        'special_provision': special_provision_parsed
                    }
                    
                    # Header with zone designation
                    zone_display = full_zone_code or zone_code or 'N/A'
                    st.markdown(f"### **Designation: {zone_display}**")
                    st.markdown("---")
                    
                    # Two column layout matching the image
                    left_col, right_col = st.columns([1, 1])
                    
                    with left_col:
                        # Site Dimensions Section
                        st.markdown("#### **Site Dimensions**")
                        
                        # Create metrics table format with both metric and imperial
                        dimensions_data = []
                        if lot_area_m2:
                            lot_area_sf = lot_area_m2 * 10.764
                            dimensions_data.append(["**Lot Area**", f"{lot_area_m2:.2f}", "m²"])
                            dimensions_data.append(["", f"{lot_area_sf:.2f}", "ft²"])
                        else:
                            dimensions_data.append(["**Lot Area**", "N/A", "m²"])
                            dimensions_data.append(["", "N/A", "ft²"])
                        
                        if frontage and frontage > 0:
                            frontage_ft = frontage * 3.28084
                            dimensions_data.append(["**Lot Frontage**", f"{frontage:.2f}", "m"])
                            dimensions_data.append(["", f"{frontage_ft:.2f}", "ft"])
                        else:
                            dimensions_data.append(["**Lot Frontage**", "N/A", "m"])
                            dimensions_data.append(["", "N/A", "ft"])
                            
                        if depth and depth > 0:
                            depth_ft = depth * 3.28084
                            dimensions_data.append(["**Lot Depth**", f"{depth:.2f}", "m"])
                            dimensions_data.append(["", f"{depth_ft:.2f}", "ft"])
                        else:
                            dimensions_data.append(["**Lot Depth**", "N/A", "m"])
                            dimensions_data.append(["", "N/A", "ft"])
                        
                        for label, value, unit in dimensions_data:
                            cols = st.columns([2, 1, 1])
                            with cols[0]:
                                st.write(label)
                            with cols[1]:
                                st.write(f"**{value}**")
                            with cols[2]:
                                st.write(unit)
                        
                        st.markdown("---")
                        
                        # Max RFA Section
                        st.markdown("#### **Max RFA**")
                        max_floor_area = development_potential.get('max_floor_area')
                        max_far = development_potential.get('max_floor_area_ratio')
                        
                        rfa_data = []
                        if max_floor_area:
                            rfa_data.append(["**Maximum Area**", f"{max_floor_area:.2f}", "m²"])
                            rfa_data.append(["", f"{max_floor_area * 10.764:.2f}", "ft²"])
                        else:
                            rfa_data.append(["**Maximum Area**", "N/A", "m²"])
                            rfa_data.append(["", "N/A", "ft²"])
                        
                        if max_far:
                            rfa_data.append(["**Ratio**", f"{max_far:.2f}", ""])
                        else:
                            rfa_data.append(["**Ratio**", "N/A", ""])
                        
                        for label, value, unit in rfa_data:
                            cols = st.columns([2, 1, 1])
                            with cols[0]:
                                st.write(label)
                            with cols[1]:
                                st.write(f"**{value}**")
                            with cols[2]:
                                st.write(unit)
                        
                        st.caption("*Maximum floor area above grade*")
                        
                        st.markdown("---")
                        
                        # Building Size Limits Section
                        st.markdown("#### **Building Size Limits**")
                        max_building_depth = development_potential.get('max_building_depth') or development_potential.get('max_dwelling_depth')
                        garage_projection = development_potential.get('garage_projection')
                        
                        building_data = []
                        if max_building_depth:
                            building_depth_ft = float(max_building_depth) * 3.28084
                            building_data.append(["**Max Building Depth**", f"{max_building_depth:.2f}", "m"])
                            building_data.append(["", f"{building_depth_ft:.2f}", "ft"])
                        else:
                            building_data.append(["**Max Building Depth**", "N/A", "m"])
                            building_data.append(["", "N/A", "ft"])
                        
                        if garage_projection:
                            garage_projection_ft = float(garage_projection) * 3.28084
                            building_data.append(["**Garage Projection**", f"{garage_projection:.2f}", "m"])
                            building_data.append(["", f"{garage_projection_ft:.2f}", "ft"])
                        else:
                            building_data.append(["**Garage Projection**", "N/A", "m"])
                            building_data.append(["", "N/A", "ft"])
                        
                        for label, value, unit in building_data:
                            cols = st.columns([2, 1, 1])
                            with cols[0]:
                                st.write(label)
                            with cols[1]:
                                st.write(f"**{value}**")
                            with cols[2]:
                                st.write(unit)
                    
                    with right_col:
                        # Site Info Section
                        st.markdown("#### **Site Info**")
                        
                        # Check conservation and arborist status
                        conservation_status = detect_conservation_requirements(parcel, zoning_info)
                        arborist_status = detect_arborist_requirements(parcel, lot_area_m2, development_potential)
                        
                        # Check heritage status if coordinates are available
                        heritage_status = "Unknown"
                        development_status = "Unknown"
                        conservation_authority_status = "Unknown"
                        
                        if lat and lon:
                            try:
                                heritage_check = check_heritage_property_status(lat, lon)
                                if heritage_check.get('is_heritage'):
                                    heritage_status = "Yes - Designated"
                                elif heritage_check.get('designation_type') == 'Nearby':
                                    heritage_status = "Nearby Heritage Area"
                                else:
                                    heritage_status = "No"
                                    
                                # Check development applications
                                dev_check = check_development_applications(lat, lon)
                                if dev_check.get('has_applications'):
                                    development_status = f"Yes ({dev_check['total_count']} applications)"
                                else:
                                    development_status = "No"
                                    
                                # Check conservation authority
                                ca_check = check_conservation_authority(lat, lon)
                                ca_name = ca_check.get('conservation_authority', 'Unknown')
                                if 'Halton' in ca_name:
                                    permits_req = ca_check.get('permits_required', 'Unknown')
                                    if permits_req == 'Likely Required':
                                        conservation_authority_status = "Halton CA - Permits Required"
                                    elif permits_req == 'Possibly Required':
                                        conservation_authority_status = "Halton CA - Contact Required"
                                    else:
                                        conservation_authority_status = "Halton Conservation Authority"
                                else:
                                    conservation_authority_status = ca_name
                                    
                            except:
                                heritage_status = "Unable to check"
                                development_status = "Unable to check"
                                conservation_authority_status = "Unable to check"
                        
                        info_data = []
                        info_data.append(["**Conservation**", conservation_status])
                        info_data.append(["**Arborist**", arborist_status])
                        info_data.append(["**Heritage**", heritage_status])
                        info_data.append(["**Development Apps**", development_status])
                        info_data.append(["**Conservation Authority**", conservation_authority_status])
                        
                        for label, value in info_data:
                            cols = st.columns([2, 1])
                            with cols[0]:
                                st.write(label)
                            with cols[1]:
                                st.write(f"**{value}**")
                        
                        st.markdown("---")
                        
                        # Max Coverage Section
                        st.markdown("#### **Max Coverage**")
                        coverage_area = development_potential.get('max_coverage_area')
                        coverage_percent = development_potential.get('max_coverage_percent')
                        
                        coverage_data = []
                        if coverage_area:
                            coverage_data.append(["**Maximum Area**", f"{coverage_area:.2f}", "m²"])
                            coverage_data.append(["", f"{coverage_area * 10.764:.2f}", "ft²"])
                        else:
                            coverage_data.append(["**Maximum Area**", "N/A", "m²"])
                            coverage_data.append(["", "N/A", "ft²"])
                        
                        if coverage_percent:
                            coverage_data.append(["**Coverage %**", f"{coverage_percent:.0f}%", ""])
                        else:
                            coverage_data.append(["**Coverage %**", "N/A", ""])
                        
                        for label, value, unit in coverage_data:
                            cols = st.columns([2, 1, 1])
                            with cols[0]:
                                st.write(label)
                            with cols[1]:
                                st.write(f"**{value}**")
                            with cols[2]:
                                st.write(unit)
                        
                        st.caption("*Maximum footprint of all structures*")
                        
                        st.markdown("---")
                        
                        # Minimum Setbacks Section
                        st.markdown("#### **Minimum Setbacks**")
                        setbacks = development_potential.get('setbacks', {})
                        
                        # Handle -0 suffix zone front yard calculations
                        front_yard_min = setbacks.get('front_yard')
                        interior_side = setbacks.get('interior_side')
                        rear_yard = setbacks.get('rear_yard')
                        
                        setback_data = []
                        
                        # Front yard setbacks
                        if parsed_info.get('has_suffix_zero'):
                            setback_data.append(["**Minimum Front**", "Existing -1", "m"])
                            setback_data.append(["", "Existing -3.3", "ft"])
                            setback_data.append(["**Maximum Front**", "Min. + 5.5", "m"])
                            setback_data.append(["", "Min. + 18.0", "ft"])
                        else:
                            if front_yard_min:
                                front_yard_ft = front_yard_min * 3.28084
                                front_max_ft = (front_yard_min + 5.5) * 3.28084
                                setback_data.append(["**Minimum Front**", f"{front_yard_min:.2f}", "m"])
                                setback_data.append(["", f"{front_yard_ft:.2f}", "ft"])
                                setback_data.append(["**Maximum Front**", f"{front_yard_min + 5.5:.2f}", "m"])
                                setback_data.append(["", f"{front_max_ft:.2f}", "ft"])
                            else:
                                setback_data.append(["**Minimum Front**", "N/A", "m"])
                                setback_data.append(["", "N/A", "ft"])
                                setback_data.append(["**Maximum Front**", "N/A", "m"])
                                setback_data.append(["", "N/A", "ft"])
                        
                        # Side yard setbacks
                        if interior_side:
                            interior_side_ft = interior_side * 3.28084
                            setback_data.append(["**Int Side L**", f"{interior_side:.2f}", "m"])
                            setback_data.append(["", f"{interior_side_ft:.2f}", "ft"])
                            setback_data.append(["**Int Side R**", f"{interior_side:.2f}", "m"])
                            setback_data.append(["", f"{interior_side_ft:.2f}", "ft"])
                        else:
                            setback_data.append(["**Int Side L**", "N/A", "m"])
                            setback_data.append(["", "N/A", "ft"])
                            setback_data.append(["**Int Side R**", "N/A", "m"])
                            setback_data.append(["", "N/A", "ft"])
                        
                        # Rear yard setbacks
                        if rear_yard:
                            rear_yard_ft = rear_yard * 3.28084
                            setback_data.append(["**Rear**", f"{rear_yard:.2f}", "m"])
                            setback_data.append(["", f"{rear_yard_ft:.2f}", "ft"])
                        else:
                            setback_data.append(["**Rear**", "N/A", "m"])
                            setback_data.append(["", "N/A", "ft"])
                        
                        for label, value, unit in setback_data:
                            cols = st.columns([2, 1, 1])
                            with cols[0]:
                                st.write(label)
                            with cols[1]:
                                st.write(f"**{value}**")
                            with cols[2]:
                                st.write(unit)
                    
                    # Bottom section spanning full width
                    st.markdown("---")
                    
                    # Maximum Height Section
                    st.markdown("#### **Maximum Height**")
                    max_height = development_potential.get('max_height', 0)
                    max_storeys = development_potential.get('max_storeys', 0)
                    
                    height_cols = st.columns(4)
                    
                    # Convert heights to feet
                    max_height_ft = max_height * 3.28084 if max_height else 0
                    
                    eave_height = development_potential.get('eave_height')
                    eave_height_ft = eave_height * 3.28084 if eave_height else None
                    
                    height_data = [
                        ("**Building Height**", f"{max_height:.2f} m" if max_height else "N/A", f"{max_height_ft:.2f} ft" if max_height else "N/A"),
                        ("**Flat Roof**", f"{max_height:.2f} m" if max_height else "N/A", f"{max_height_ft:.2f} ft" if max_height else "N/A"),
                        ("**Eaves**", f"{eave_height:.2f} m" if eave_height else "N/A", f"{eave_height_ft:.2f} ft" if eave_height else "N/A"),
                        ("**Storeys**", f"{max_storeys:.0f}" if max_storeys else "N/A", "")
                    ]
                    
                    for i, (label, metric_value, imperial_value) in enumerate(height_data):
                        with height_cols[i]:
                            st.write(label)
                            st.write(f"**{metric_value}**")
                            if imperial_value:
                                st.caption(imperial_value)
                    
                    st.markdown("---")
                    st.caption("*This information was collected by scaling online city mapping, this information should be confirmed with accurate survey.*")
                    
                    # Final Buildable Area Analysis
                    st.subheader("🏗️ Final Buildable Floor Area Analysis")
                    final_analysis = development_potential.get('final_buildable_analysis', {})
                    
                    if final_analysis.get('final_buildable_sqft'):
                        # Create analysis summary box
                        st.success(f"""
                        ### ✅ Final Analysis Result
                        
                        Based on our understanding and interpretation of the by-law, we are confident that you can build a house of approximately **{final_analysis['final_buildable_sqft']:,.0f} sq. ft.** ({final_analysis['final_buildable_sqm']:,.0f} sq. m.)
                        
                        **Confidence Level:** {final_analysis.get('confidence_level', 'Moderate')}
                        """)
                        
                        # Show calculation breakdown
                        with st.expander("📊 Detailed Calculation Breakdown"):
                            st.markdown("#### Calculation Method: " + final_analysis.get('calculation_method', 'Standard'))
                            
                            calc_cols = st.columns(2)
                            
                            with calc_cols[0]:
                                st.markdown("**Step 1: Lot Coverage**")
                                if final_analysis.get('lot_coverage_sqft'):
                                    coverage_pct = development_potential.get('max_coverage_percent', 30)
                                    st.write(f"• {coverage_pct:.0f}% × {lot_area_m2:,.2f} m²")
                                    st.write(f"• = {final_analysis['lot_coverage_sqm']:,.2f} m²")
                                    st.write(f"• = {final_analysis['lot_coverage_sqft']:,.2f} sq. ft.")
                                
                                st.markdown("**Step 2: Gross Floor Area**")
                                if final_analysis.get('gross_floor_area_sqft'):
                                    st.write(f"• Coverage: {final_analysis.get('lot_coverage_sqft', 0):,.2f} sq. ft.")
                                    st.write(f"• × {final_analysis.get('max_floors', 2)} floors")
                                    st.write(f"• = {final_analysis['gross_floor_area_sqft']:,.2f} sq. ft.")
                            
                            with calc_cols[1]:
                                st.markdown("**Step 3: Setback Deductions**")
                                st.write(f"• Gross: {final_analysis.get('gross_floor_area_sqft', 0):,.2f} sq. ft.")
                                st.write(f"• Minus: {final_analysis.get('setback_deduction_sqft', 750):,.0f} sq. ft. (setbacks)")
                                st.write(f"• **Final: {final_analysis['final_buildable_sqft']:,.0f} sq. ft.**")
                                
                                st.markdown("**Important Factors:**")
                                st.write("• Maximum Residential Floor Area Ratio")
                                st.write("• Maximum Lot Coverage")
                                st.write("• Dwelling Setbacks")
                                if development_potential.get('suffix') == "-0":
                                    st.write("• Front Yard: Existing -1m")
                                st.write(f"• Rear Yard: {setbacks.get('rear_yard', 'N/A')} m")
                            
                            if final_analysis.get('analysis_note'):
                                st.info(f"📝 {final_analysis['analysis_note']}")
                    else:
                        st.warning("⚠️ Unable to calculate final buildable area - insufficient data available")
                        if final_analysis.get('analysis_note'):
                            st.caption(final_analysis['analysis_note'])
                        
                        # Check if it's due to "-1" setback requirement
                        buildable_info = development_potential.get('note')
                        if buildable_info and 'survey data' in buildable_info:
                            st.info("📋 **Survey Required**: Property has 'existing -1m' front yard setback requirement. A survey is needed to determine the exact existing building setback for accurate calculations.")
                    
                    st.markdown("---")
                    
                    # Detailed setbacks section
                    st.subheader("📏 Precise Setback Requirements")
                    setbacks = development_potential.get('setbacks', {})
                    
                    setback_cols = st.columns(5)
                    with setback_cols[0]:
                        front_yard_val = setbacks.get('front_yard', 'N/A')
                        if front_yard_val == "-1":
                            st.metric("Front Yard", "Existing -1 m")
                        else:
                            st.metric("Front Yard", f"{front_yard_val} m")
                    with setback_cols[1]:
                        st.metric("Rear Yard", f"{setbacks.get('rear_yard', 'N/A')} m")
                    with setback_cols[2]:
                        if 'interior_side_min' in setbacks:
                            st.metric("Side Yard Min", f"{setbacks['interior_side_min']} m")
                            st.metric("Side Yard Max", f"{setbacks['interior_side_max']} m")
                        else:
                            st.metric("Interior Side", f"{setbacks.get('interior_side', 'N/A')} m")
                    with setback_cols[3]:
                        if setbacks.get('flankage_yard'):
                            st.metric("Flankage Yard", f"{setbacks['flankage_yard']} m")
                        else:
                            st.write("N/A - Not Corner")
                    with setback_cols[4]:
                        if setbacks.get('garage_interior_side'):
                            st.metric("Garage Side", f"{setbacks['garage_interior_side']} m")
                            st.caption(f"Applies to: {setbacks.get('garage_applies_to', 'N/A')}")
                    
                    # Special provisions display
                    if development_potential.get('special_depth_provisions'):
                        st.subheader("⭐ Special Depth Provisions")
                        special = development_potential['special_depth_provisions']
                        with st.expander("Single Storey Extension Rules"):
                            st.write(f"**Max Height:** {special['single_storey_extension']['max_height']} m")
                            st.write(f"**Additional Depth:** {special['single_storey_extension']['additional_depth']} m")
                            st.write(f"**Required Side Yards:** {special['single_storey_extension']['required_side_yards']} m")
                    
                    # Permitted uses
                    st.subheader("✅ Permitted Uses")
                    permitted_uses = development_potential.get('permitted_uses', [])
                    if permitted_uses:
                        use_cols = st.columns(min(len(permitted_uses), 4))
                        for idx, use in enumerate(permitted_uses):  # Show all uses
                            with use_cols[idx % 4]:
                                st.info(use.replace('_', ' ').title())
                    
                    # Special provisions
                    if special_provision:
                        st.subheader("⭐ Special Provisions")
                        st.warning(f"This property has special provision: {special_provision}")
                        st.info("Special provisions may modify standard zoning requirements. Consult planning services for specific details.")
                    
                    # PDF Download Section
                    st.markdown("---")
                    st.subheader("📄 Generate Property Report")
                    
                    if PDF_GENERATOR_AVAILABLE:
                        if st.button("📄 Generate PDF Report", type="secondary", use_container_width=True):
                            with st.spinner("Generating PDF report..."):
                                # Prepare property data for PDF
                                property_data = prepare_property_data_for_pdf(
                                    parcel, zone_code, full_zone_code, development_potential,
                                    setbacks, lot_area_m2, frontage, depth
                                )
                                
                                # Generate PDF
                                pdf_generator = PropertyReportGenerator()
                                pdf_buffer = io.BytesIO()
                                pdf_generator.generate_property_report(property_data, pdf_buffer)
                                pdf_buffer.seek(0)
                                
                                # Offer download
                                property_address = parcel.get("address", "Property").replace(" ", "_").replace(",", "")
                                filename = f"{property_address}_Property_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
                                
                                st.download_button(
                                    label="📥 Download Property Report PDF",
                                    data=pdf_buffer.getvalue(),
                                    file_name=filename,
                                    mime="application/pdf",
                                    type="primary",
                                    use_container_width=True
                                )
                                
                                st.success("✅ PDF report generated successfully!")
                    else:
                        st.warning("PDF generation not available. Please ensure all required dependencies are installed.")
            
            with tabs[1]:
                st.header("💰 Property Valuation & Market Analysis")
                
                # Calculate property valuation
                # Use default values for property features since they're no longer in sidebar
                valuation = estimate_property_value(
                    zone_code, lot_area_m2, building_area, "detached_dwelling",
                    bedrooms, bathrooms, age, 
                    nearby_parks=1, waterfront=False, heritage_designated=False, 
                    is_corner=False, special_provision=special_provision
                )
                
                # Main valuation metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(
                        "🏠 Estimated Value",
                        f"${valuation['estimated_value']:,}",
                        delta=f"${valuation['estimated_value'] - valuation['land_value'] - valuation['building_value']:,}"
                    )
                with col2:
                    price_per_sqm = valuation['price_per_sqm']
                    st.metric("📊 Price per m²", f"${price_per_sqm:,}")
                    st.caption(f"≈ ${price_per_sqm / 10.764:.0f} per sq ft")
                with col3:
                    confidence_range = valuation['confidence_range']
                    st.metric(
                        "📈 Confidence Range", 
                        f"${confidence_range['low']:,} - ${confidence_range['high']:,}"
                    )
                
                # Value breakdown
                st.subheader("💵 Value Breakdown")
                breakdown_data = {
                    'Component': ['Land Value', 'Building Value', 'Feature Adjustments'],
                    'Value': [
                        valuation['land_value'],
                        valuation['building_value'],
                        sum(valuation['adjustments'].values())
                    ]
                }
                
                fig = px.pie(
                    pd.DataFrame(breakdown_data),
                    values='Value',
                    names='Component',
                    title='Property Value Components'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Adjustment details
                with st.expander("🔍 View Detailed Adjustments"):
                    adj = valuation['adjustments']
                    if adj['bedrooms'] != 0:
                        st.write(f"**Extra Bedrooms:** ${adj['bedrooms']:,}")
                    if adj['bathrooms'] != 0:
                        st.write(f"**Extra Bathrooms:** ${adj['bathrooms']:,}")
                    if adj['location_total'] != 0:
                        st.write(f"**Location Factors:** ${adj['location_total']:,}")
            
            with tabs[2]:
                st.header("🏗️ Development Potential & Financial Analysis")
                
                # Development analysis
                dev_analysis = calculate_development_value(zone_code, lot_area_m2, development_potential, valuation['estimated_value'])
                
                if "message" in dev_analysis:
                    st.info(f"ℹ️ {dev_analysis['message']}")
                else:
                    # Development feasibility
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("🏠 Development Overview")
                        st.metric("Development Type", dev_analysis['unit_type'].replace('_', ' ').title())
                        st.metric("Potential Units", dev_analysis['potential_units'])
                        
                        if dev_analysis['feasible']:
                            st.success("✅ Development appears financially feasible")
                        else:
                            st.error("❌ Development may not meet minimum profit targets")
                        
                        st.metric("Profit Margin", f"{dev_analysis['profit_margin']:.1f}%")
                        st.metric("ROI", f"{dev_analysis['roi_percentage']:.1f}%")
                    
                    with col2:
                        st.subheader("💰 Financial Projections")
                        st.metric("Gross Revenue", f"${dev_analysis['gross_revenue']:,}")
                        st.metric("Total Costs", f"${dev_analysis['total_costs']:,}")
                        st.metric("Potential Profit", f"${dev_analysis['potential_profit']:,}")
                        
                        # Cost breakdown
                        cost_data = pd.DataFrame({
                            'Cost Type': ['Construction', 'Soft Costs', 'Land Cost'],
                            'Amount': [
                                dev_analysis['construction_costs'],
                                dev_analysis['soft_costs'],
                                dev_analysis['land_cost']
                            ]
                        })
                        
                        fig = px.bar(cost_data, x='Cost Type', y='Amount', title='Development Cost Breakdown')
                        st.plotly_chart(fig, use_container_width=True)
            
            with tabs[3]:
                st.header("📋 Special Requirements Assessment")
                
                # Get comprehensive conservation, heritage, and arborist assessments
                display_address = parcel.get("address", "Unknown")
                
                # Get coordinates safely
                if parcel.get("lat") and parcel.get("lon"):
                    lat, lon = parcel["lat"], parcel["lon"]
                elif parcel.get("geometry"):
                    coord_result = get_centroid(parcel["geometry"])
                    if coord_result and len(coord_result) == 2:
                        lat, lon = coord_result
                    else:
                        lat, lon = 43.4685, -79.7071  # Default Oakville coordinates
                else:
                    lat, lon = 43.4685, -79.7071  # Default Oakville coordinates
                
                try:
                    heritage_assessment = assess_heritage_conservation_requirements(
                        zone_code or "RL3", display_address, lat, lon, lot_area_m2 or 500, age
                    )
                    
                    arborist_assessment = assess_arborist_requirements(
                        zone_code or "RL3", display_address, lat, lon, lot_area_m2 or 500, frontage or 15
                    )
                except Exception as e:
                    st.error(f"Error in special requirements assessment: {e}")
                    # Provide fallback assessments
                    heritage_assessment = {
                        "heritage_assessment": {"heritage_concern_level": "low", "heritage_district": None, "required_assessments": []},
                        "conservation_requirements": {"natural_heritage_features": []},
                        "environmental_considerations": {"watercourse_proximity": False, "floodplain_risk": "low"},
                        "required_studies": [],
                        "approval_complexity": "standard"
                    }
                    arborist_assessment = {
                        "arborist_report_required": False,
                        "protected_tree_likelihood": "low",
                        "tree_removal_permits_required": [],
                        "preservation_requirements": {},
                        "estimated_tree_survey_cost": 0,
                        "arborist_triggers": []
                    }
                
                # === REAL-TIME API CHECKS ===
                st.subheader("🔍 Live API Checks")
                
                # Heritage Properties Check
                heritage_check = check_heritage_property_status(lat, lon)
                dev_check = check_development_applications(lat, lon)
                conservation_check = check_conservation_authority(lat, lon)
                
                api_cols = st.columns(3)
                
                with api_cols[0]:
                    st.markdown("**Heritage Property Status**")
                    if heritage_check.get('is_heritage'):
                        st.success("🏛️ **HERITAGE PROPERTY FOUND**")
                        for prop in heritage_check.get('properties', []):
                            with st.expander(f"Heritage Property: {prop.get('address', 'Unknown')}"):
                                st.write(f"**Heritage ID:** {prop.get('heritage_id', 'N/A')}")
                                st.write(f"**By-law:** {prop.get('bylaw', 'N/A')}")
                                st.write(f"**Designation Year:** {prop.get('year', 'N/A')}")
                                st.write(f"**Status:** {prop.get('status', 'N/A')}")
                                if prop.get('description'):
                                    st.write(f"**Description:** {prop['description']}")
                    elif heritage_check.get('designation_type') == 'Nearby':
                        st.warning(f"🏘️ **{heritage_check['nearby_heritage_count']} heritage properties nearby**")
                        st.caption("Property may be subject to heritage area guidelines")
                    else:
                        st.info("✅ No heritage designation found")
                
                with api_cols[1]:
                    st.markdown("**Development Applications**")
                    if dev_check.get('has_applications'):
                        st.warning(f"📋 **{dev_check['total_count']} applications found in area**")
                        for idx, app in enumerate(dev_check.get('applications', [])[:3]):
                            app_title = app.get('application_number', 'Unknown Application')
                            app_type = app.get('type', 'Unknown')
                            with st.expander(f"Development App: {app_title} ({app_type})"):
                                
                                # Show available information
                                status = app.get('status', 'N/A')
                                if status and status != 'Status not available':
                                    st.write(f"**Status:** {status}")
                                else:
                                    st.write(f"**Status:** Not specified")
                                
                                st.write(f"**Application Type:** {app.get('type', 'Unknown')}")
                                
                                if app.get('date_received'):
                                    st.write(f"**Date Created:** {app['date_received']}")
                                
                                # Additional technical information
                                if app.get('folder_rsn'):
                                    st.write(f"**Folder Reference:** {app['folder_rsn']}")
                                
                                north_oak = app.get('north_oak', 'Unknown')
                                if north_oak and north_oak != 'Unknown':
                                    st.write(f"**North Oakville:** {north_oak}")
                                
                                # Note about limited API data
                                st.caption("ℹ️ Limited details available from municipal API. Contact planning department for full application details.")
                                
                                # Debug information - show available fields (only in debug mode)
                                if st.checkbox("🔍 Show API Debug Info", key=f"debug_dev_app_{idx}"):
                                    available_fields = app.get('available_fields', [])
                                    if available_fields:
                                        st.write("**Available API Fields:**")
                                        for field in available_fields:
                                            st.write(f"• {field}")
                                    else:
                                        st.write("No fields available in API response")
                    else:
                        st.info("✅ No development applications in area")
                
                with api_cols[2]:
                    st.markdown("**Conservation Authority**")
                    ca_name = conservation_check.get('conservation_authority', 'Unknown')
                    permits_req = conservation_check.get('permits_required', 'Unknown')
                    
                    if 'Halton' in ca_name:
                        st.success(f"🌊 **{ca_name}**")
                        
                        if permits_req == 'Likely Required':
                            st.warning("⚠️ **Permits Likely Required**")
                        elif permits_req == 'Possibly Required':
                            st.info("ℹ️ **Permits Possibly Required**")
                        else:
                            st.info(f"**Status:** {permits_req}")
                            
                        contact_info = conservation_check.get('contact_info', {})
                        if contact_info:
                            with st.expander("📞 Contact Information"):
                                st.write(f"**Phone:** {contact_info.get('phone', 'N/A')}")
                                st.write(f"**Email:** {contact_info.get('email', 'N/A')}")
                                if contact_info.get('website'):
                                    st.write(f"**Website:** [Visit]({contact_info['website']})")
                                    
                        regulated_features = conservation_check.get('regulated_features', [])
                        if regulated_features:
                            with st.expander("🚫 Regulated Features"):
                                for feature in regulated_features:
                                    st.write(f"• {feature}")
                    else:
                        st.info(f"ℹ️ **{ca_name}**")
                        if conservation_check.get('error'):
                            st.caption("Unable to verify - contact required")
                
                st.markdown("---")
                
                # === HERITAGE CONSERVATION ASSESSMENT ===
                st.subheader("🏛️ Heritage Conservation Assessment")
                heritage_data = heritage_assessment["heritage_assessment"]
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    concern_level = heritage_data["heritage_concern_level"]
                    concern_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}[concern_level]
                    st.metric("Heritage Concern Level", f"{concern_color} {concern_level.title()}")
                
                with col2:
                    if heritage_data["heritage_district"]:
                        st.metric("Heritage District", heritage_data["heritage_district"])
                    else:
                        st.metric("Heritage District", "None")
                
                with col3:
                    complexity = heritage_assessment["approval_complexity"]
                    st.metric("Approval Complexity", complexity.title())
                
                if heritage_data["required_assessments"]:
                    st.warning("⚠️ Heritage assessments required:")
                    for assessment in heritage_data["required_assessments"]:
                        st.write(f"• {assessment}")
                
                # === DETAILED HERITAGE PROPERTIES INFORMATION (API-BASED) ===
                try:
                    detailed_heritage_info = get_heritage_requirements(parcel, buffer_meters=100)
                    
                    if detailed_heritage_info.get('api_available', False):
                        if detailed_heritage_info['nearby_properties']:
                            with st.expander(f"📜 Heritage Properties Nearby ({len(detailed_heritage_info['nearby_properties'])} found)", expanded=detailed_heritage_info['has_heritage_requirements']):
                                st.write(f"**Search radius:** {detailed_heritage_info['search_radius']}m around property")
                                
                                for i, prop in enumerate(detailed_heritage_info['nearby_properties']):
                                    st.markdown(f"**Heritage Property #{i+1}**")
                                    
                                    prop_col1, prop_col2 = st.columns(2)
                                    with prop_col1:
                                        if prop['address']:
                                            st.write(f"📍 **Address:** {prop['address']}")
                                        if prop['status']:
                                            status_color = "🟢" if "Listed" in prop['status'] else "🔵" if "Part IV" in prop['status'] else "⚪"
                                            st.write(f"🏛️ **Status:** {status_color} {prop['status']}")
                                        if prop['year_built']:
                                            st.write(f"📅 **Year Built:** {prop['year_built']}")
                                        if prop['bylaw']:
                                            st.write(f"📋 **Bylaw:** {prop['bylaw']}")
                                    
                                    with prop_col2:
                                        if prop['history']:
                                            history_preview = prop['history'][:200] + "..." if len(prop['history']) > 200 else prop['history']
                                            st.write(f"📖 **History:** {history_preview}")
                                        if prop['description']:
                                            desc_preview = prop['description'][:200] + "..." if len(prop['description']) > 200 else prop['description']
                                            st.write(f"📝 **Description:** {desc_preview}")
                                    
                                    if i < len(detailed_heritage_info['nearby_properties']) - 1:
                                        st.divider()
                        else:
                            st.success("✅ No heritage properties found within 100m of this location")
                    else:
                        st.info("ℹ️ Heritage Properties API not available - using fallback heritage detection")
                        
                except Exception as e:
                    st.warning(f"Could not load detailed heritage information: {str(e)[:100]}")
                
                # === ARBORIST & TREE PRESERVATION ===
                st.subheader("🌳 Arborist & Tree Preservation Assessment")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    tree_likelihood = arborist_assessment["protected_tree_likelihood"]
                    tree_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}[tree_likelihood]
                    st.metric("Protected Tree Likelihood", f"{tree_color} {tree_likelihood.title()}")
                
                with col2:
                    arborist_required = "✅ Required" if arborist_assessment["arborist_report_required"] else "❌ Not Required"
                    st.metric("Arborist Report", arborist_required)
                
                with col3:
                    cost = arborist_assessment["estimated_tree_survey_cost"]
                    st.metric("Estimated Survey Cost", f"${cost:,}" if cost > 0 else "N/A")
                
                with col4:
                    permits = len(arborist_assessment["tree_removal_permits_required"])
                    st.metric("Tree Permits Required", permits)
                
                if arborist_assessment["arborist_triggers"]:
                    st.info("🌳 Arborist assessment triggers:")
                    for trigger in arborist_assessment["arborist_triggers"]:
                        st.write(f"• {trigger}")
                
                # Tree preservation requirements
                if arborist_assessment["preservation_requirements"]:
                    with st.expander("🛡️ Tree Preservation Requirements", expanded=True):
                        preserv = arborist_assessment["preservation_requirements"]
                        if preserv["tree_protection_fencing"]:
                            st.write("• Tree protection fencing during construction")
                        if preserv["root_protection_zone"]:
                            st.write("• Root protection zone establishment")
                        if preserv["replacement_planting_required"]:
                            st.write("• Replacement planting for removed trees")
                        if preserv["cash_in_lieu_option"]:
                            st.write("• Cash-in-lieu option available for small lots")
                        if preserv["monitoring_during_construction"]:
                            st.write("• Professional monitoring during construction")
                
                # === ENVIRONMENTAL CONSIDERATIONS ===
                st.subheader("🌿 Environmental Considerations")
                env_considerations = heritage_assessment["environmental_considerations"]
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    watercourse = "Yes" if env_considerations["watercourse_proximity"] else "No"
                    st.metric("Watercourse Proximity", watercourse)
                
                with col2:
                    floodplain = env_considerations["floodplain_risk"].title()
                    st.metric("Floodplain Risk", floodplain)
                
                with col3:
                    conservation_features = heritage_assessment["conservation_requirements"]["natural_heritage_features"]
                    st.metric("Natural Heritage Features", len(conservation_features))
                
                if conservation_features:
                    st.info(f"🌿 Natural heritage features: {', '.join(conservation_features)}")
                
                # === REQUIRED STUDIES SUMMARY ===
                all_studies = set(heritage_assessment["required_studies"])
                if arborist_assessment["arborist_report_required"]:
                    all_studies.add("Arborist Report & Tree Preservation Plan")
                
                if all_studies:
                    st.subheader("📊 Required Professional Studies")
                    study_cost_estimates = {
                        "Heritage Impact Assessment": "$3,500 - $7,500",
                        "Heritage Screening Assessment": "$1,500 - $3,000", 
                        "Environmental Impact Study": "$5,000 - $12,000",
                        "Watercourse Assessment": "$2,500 - $5,000",
                        "Arborist Report & Tree Preservation Plan": f"${arborist_assessment['estimated_tree_survey_cost']:,}" if arborist_assessment['estimated_tree_survey_cost'] > 0 else "$2,500 - $5,000"
                    }
                    
                    for study in all_studies:
                        cost_estimate = study_cost_estimates.get(study, "Contact consultant")
                        st.write(f"• **{study}**: {cost_estimate}")
                
                # === ZONING SPECIFIC REQUIREMENTS ===
                st.subheader("📋 Zone-Specific Requirements")
                requirements = []
                
                # -0 Suffix zone requirements
                if zone_code.endswith('-0'):
                    requirements.append({
                        "category": "Suffix Zone Requirements (-0)",
                        "items": [
                            "Property subject to enhanced design standards",
                            "Maximum 2 storeys permitted",
                            "Reduced floor area ratio applies",
                            "Front yard setback may be averaged with existing buildings",
                            "Balconies prohibited from extending into required yards"
                        ]
                    })
                
                # Heritage requirements (enhanced) - use actual heritage status
                # Check if property has heritage designation
                heritage_designated = False
                if lat and lon:
                    try:
                        heritage_check = check_heritage_property_status(lat, lon)
                        heritage_designated = heritage_check.get('is_heritage', False)
                    except:
                        heritage_designated = False
                
                if heritage_designated:
                    requirements.append({
                        "category": "Heritage Property Requirements",
                        "items": [
                            "Heritage Impact Assessment required for alterations",
                            "Municipal heritage permit required",
                            "Design must preserve heritage character",
                            "Consultation with Heritage Oakville required"
                        ]
                    })
                
                # Special provision requirements
                if special_provision:
                    sp_info = SPECIAL_PROVISIONS.get(special_provision, {})
                    requirements.append({
                        "category": f"Special Provision Requirements ({special_provision})",
                        "items": [
                            sp_info.get('description', 'Site-specific zoning requirements'),
                            "Consult Part 19 Maps for specific provisions",
                            "Professional planning consultation recommended",
                            "Site-specific development standards may apply"
                        ]
                    })
                
                # Corner lot requirements
                if corner_lot:
                    requirements.append({
                        "category": "Corner Lot Requirements",
                        "items": [
                            "Flankage yard setback requirements apply",
                            "Two front yard setbacks required",
                            "Potential for rear yard reduction with conditions",
                            "Enhanced landscaping may be required"
                        ]
                    })
                
                # Development application requirements
                if development_potential.get('potential_units', 1) > 1:
                    requirements.append({
                        "category": "Development Application Requirements",
                        "items": [
                            "Site Plan Control application required",
                            "Traffic impact study may be required",
                            "Servicing study required",
                            "Public consultation process",
                            "Development charges applicable"
                        ]
                    })
                
                # Display requirements
                if requirements:
                    for req in requirements:
                        with st.expander(f"📋 {req['category']}", expanded=False):
                            for item in req['items']:
                                st.write(f"• {item}")
                
                # === PROFESSIONAL CONSULTATION ===
                st.subheader("👥 Recommended Professional Team")
                base_professionals = [
                    "Licensed Professional Planner for zoning compliance",
                    "Registered Architect for building design",
                    "Professional Engineer for structural/servicing"
                ]
                
                specialized_professionals = []
                if heritage_assessment["approval_complexity"] == "complex":
                    specialized_professionals.append("Heritage Consultant (CAHP certified preferred)")
                if arborist_assessment["arborist_report_required"]:
                    specialized_professionals.append("Certified Arborist (ISA certification required)")
                if heritage_assessment["environmental_considerations"]["watercourse_proximity"]:
                    specialized_professionals.append("Environmental Consultant")
                if development_potential.get('potential_units', 1) > 1:
                    specialized_professionals.append("Development Project Manager")
                
                st.write("**Core Team:**")
                for prof in base_professionals:
                    st.write(f"• {prof}")
                
                if specialized_professionals:
                    st.write("**Specialized Consultants:**")
                    for prof in specialized_professionals:
                        st.write(f"• {prof}")
                
                # === TIMELINE & COST ESTIMATE ===
                st.subheader("⏱️ Estimated Timeline & Costs")
                
                base_timeline = "3-6 months"
                base_cost = "$15,000 - $35,000"
                
                if heritage_assessment["approval_complexity"] == "complex":
                    base_timeline = "6-12 months"
                    base_cost = "$35,000 - $75,000"
                
                if arborist_assessment["arborist_report_required"]:
                    base_cost = base_cost.replace("$35,000", "$45,000").replace("$75,000", "$85,000")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Estimated Timeline", base_timeline)
                with col2:
                    st.metric("Estimated Professional Costs", base_cost)
                
                st.caption("*Estimates include all professional studies and municipal fees. Actual costs may vary based on property complexity and market conditions.")
            
            with tabs[4]:
                # Zone Rules Tab - Display comprehensive zoning regulations
                display_zone_rules_tab(full_zone_code or zone_code)
        
        else:
            if not zone_code:
                st.error("❌ Unable to determine zoning for this property.")
            else:
                st.warning("⚠️ Please enter both frontage and depth dimensions to proceed with analysis.")

if __name__ == "__main__":
    main()