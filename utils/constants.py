"""
Application constants and enumerations
"""

from enum import Enum
from typing import Dict, List, Any


class ZoneType(Enum):
    """Zoning type enumeration"""
    RESIDENTIAL_LOW = "residential_low"
    RESIDENTIAL_MEDIUM = "residential_medium"
    RESIDENTIAL_HIGH = "residential_high"
    RESIDENTIAL_UPTOWN_CORE = "residential_uptown_core"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    INSTITUTIONAL = "institutional"
    OPEN_SPACE = "open_space"


class DwellingType(Enum):
    """Dwelling type enumeration"""
    DETACHED = "detached_dwelling"
    SEMI_DETACHED = "semi_detached_dwelling"
    DUPLEX = "duplex_dwelling"
    TOWNHOUSE = "townhouse_dwelling"
    BACK_TO_BACK_TOWNHOUSE = "back_to_back_townhouse_dwelling"
    STACKED_TOWNHOUSE = "stacked_townhouse_dwelling"
    APARTMENT = "apartment_dwelling"
    LINKED = "linked_dwelling"


class MarketCondition(Enum):
    """Market condition enumeration"""
    HOT = "hot"
    BALANCED = "balanced"
    COOL = "cool"
    DECLINING = "declining"


class AnalysisType(Enum):
    """Analysis type enumeration"""
    ZONING = "zoning_analysis"
    VALUATION = "property_valuation"
    DEVELOPMENT = "development_potential"
    MARKET = "market_insights"
    COMPREHENSIVE = "comprehensive"


# Oakville specific zone codes and their descriptions
OAKVILLE_ZONES: Dict[str, Dict[str, Any]] = {
    'RL1': {
        'name': 'Residential Low 1',
        'description': 'Large estate residential lots',
        'category': ZoneType.RESIDENTIAL_LOW,
        'typical_lot_size': '1,393+ m²',
        'primary_use': DwellingType.DETACHED
    },
    'RL2': {
        'name': 'Residential Low 2',
        'description': 'Large residential lots',
        'category': ZoneType.RESIDENTIAL_LOW,
        'typical_lot_size': '836+ m²',
        'primary_use': DwellingType.DETACHED
    },
    'RL3': {
        'name': 'Residential Low 3',
        'description': 'Medium-large residential lots',
        'category': ZoneType.RESIDENTIAL_LOW,
        'typical_lot_size': '557+ m²',
        'primary_use': DwellingType.DETACHED
    },
    'RL4': {
        'name': 'Residential Low 4',
        'description': 'Medium residential lots',
        'category': ZoneType.RESIDENTIAL_LOW,
        'typical_lot_size': '511+ m²',
        'primary_use': DwellingType.DETACHED
    },
    'RL5': {
        'name': 'Residential Low 5',
        'description': 'Medium residential lots',
        'category': ZoneType.RESIDENTIAL_LOW,
        'typical_lot_size': '464+ m²',
        'primary_use': DwellingType.DETACHED
    },
    'RL6': {
        'name': 'Residential Low 6',
        'description': 'Small residential lots',
        'category': ZoneType.RESIDENTIAL_LOW,
        'typical_lot_size': '250+ m²',
        'primary_use': DwellingType.DETACHED
    },
    'RL7': {
        'name': 'Residential Low 7',
        'description': 'Mixed detached and semi-detached',
        'category': ZoneType.RESIDENTIAL_LOW,
        'typical_lot_size': '557+ m²',
        'primary_use': [DwellingType.DETACHED, DwellingType.SEMI_DETACHED]
    },
    'RL8': {
        'name': 'Residential Low 8',
        'description': 'Higher density low residential',
        'category': ZoneType.RESIDENTIAL_LOW,
        'typical_lot_size': '360+ m²',
        'primary_use': [DwellingType.DETACHED, DwellingType.SEMI_DETACHED]
    },
    'RL9': {
        'name': 'Residential Low 9',
        'description': 'Higher density low residential',
        'category': ZoneType.RESIDENTIAL_LOW,
        'typical_lot_size': '270+ m²',
        'primary_use': [DwellingType.DETACHED, DwellingType.SEMI_DETACHED]
    },
    'RL10': {
        'name': 'Residential Low 10',
        'description': 'Detached and duplex dwellings',
        'category': ZoneType.RESIDENTIAL_LOW,
        'typical_lot_size': '464+ m²',
        'primary_use': [DwellingType.DETACHED, DwellingType.DUPLEX]
    },
    'RL11': {
        'name': 'Residential Low 11',
        'description': 'Linked dwelling units',
        'category': ZoneType.RESIDENTIAL_LOW,
        'typical_lot_size': '650+ m²',
        'primary_use': DwellingType.LINKED
    },
    'RUC': {
        'name': 'Residential Uptown Core',
        'description': 'Mixed residential in uptown core',
        'category': ZoneType.RESIDENTIAL_UPTOWN_CORE,
        'typical_lot_size': '150+ m² per unit',
        'primary_use': [DwellingType.DETACHED, DwellingType.SEMI_DETACHED, DwellingType.TOWNHOUSE]
    },
    'RM1': {
        'name': 'Residential Medium 1',
        'description': 'Townhouse developments',
        'category': ZoneType.RESIDENTIAL_MEDIUM,
        'typical_lot_size': '135 m² per unit',
        'primary_use': DwellingType.TOWNHOUSE
    },
    'RM2': {
        'name': 'Residential Medium 2',
        'description': 'Back-to-back townhouses',
        'category': ZoneType.RESIDENTIAL_MEDIUM,
        'typical_lot_size': '135 m² per unit',
        'primary_use': DwellingType.BACK_TO_BACK_TOWNHOUSE
    },
    'RM3': {
        'name': 'Residential Medium 3',
        'description': 'Stacked townhouses and apartments',
        'category': ZoneType.RESIDENTIAL_MEDIUM,
        'typical_lot_size': '1,486+ m²',
        'primary_use': [DwellingType.STACKED_TOWNHOUSE, DwellingType.APARTMENT]
    },
    'RM4': {
        'name': 'Residential Medium 4',
        'description': 'Apartment buildings',
        'category': ZoneType.RESIDENTIAL_MEDIUM,
        'typical_lot_size': '1,486+ m²',
        'primary_use': DwellingType.APARTMENT
    },
    'RH': {
        'name': 'Residential High',
        'description': 'High density residential',
        'category': ZoneType.RESIDENTIAL_HIGH,
        'typical_lot_size': '1,858+ m²',
        'primary_use': DwellingType.APARTMENT
    }
}

# Construction costs per square meter (CAD)
CONSTRUCTION_COSTS: Dict[str, Dict[str, float]] = {
    'residential': {
        'basic': 1800,
        'standard': 2500,
        'luxury': 3500,
        'renovation': 1200
    },
    'by_type': {
        'detached_dwelling': 2800,
        'semi_detached_dwelling': 2600,
        'townhouse_dwelling': 2400,
        'back_to_back_townhouse_dwelling': 2200,
        'stacked_townhouse_dwelling': 2300,
        'apartment_dwelling': 2000
    },
    'site_work': {
        'excavation': 150,
        'foundation': 300,
        'utilities': 200,
        'landscaping': 100,
        'driveway': 80
    }
}

# Development soft costs as percentages
DEVELOPMENT_SOFT_COSTS: Dict[str, float] = {
    'permits_and_fees': 0.05,      # 5% of construction
    'professional_fees': 0.08,     # 8% of construction
    'financing_costs': 0.04,       # 4% of total project
    'marketing_sales': 0.03,       # 3% of revenue
    'contingency': 0.05,           # 5% of construction
    'legal_admin': 0.02,           # 2% of total project
    'total_typical': 0.25          # 25% of construction costs
}

# Market value adjustments
LOCATION_ADJUSTMENTS: Dict[str, float] = {
    'waterfront': 0.30,            # 30% premium
    'park_adjacent': 0.10,         # 10% premium
    'school_nearby': 0.08,         # 8% premium (good schools)
    'transit_accessible': 0.12,    # 12% premium
    'shopping_nearby': 0.05,       # 5% premium
    'quiet_street': 0.07,          # 7% premium
    'mature_trees': 0.05,          # 5% premium
    'corner_lot': -0.05,           # 5% discount
    'busy_road': -0.10,            # 10% discount
    'heritage_designated': -0.10,   # 10% discount (restrictions)
    'environmental_issues': -0.15,  # 15% discount
    'odd_shaped_lot': -0.08        # 8% discount
}

# Market condition multipliers
MARKET_CONDITION_ADJUSTMENTS: Dict[MarketCondition, Dict[str, Any]] = {
    MarketCondition.HOT: {
        'price_multiplier': 1.08,
        'days_on_market': 14,
        'description': 'Seller\'s market - high demand, low inventory'
    },
    MarketCondition.BALANCED: {
        'price_multiplier': 1.02,
        'days_on_market': 28,
        'description': 'Balanced market - normal supply and demand'
    },
    MarketCondition.COOL: {
        'price_multiplier': 0.95,
        'days_on_market': 42,
        'description': 'Buyer\'s market - lower demand, higher inventory'
    },
    MarketCondition.DECLINING: {
        'price_multiplier': 0.88,
        'days_on_market': 65,
        'description': 'Declining market - values falling, high inventory'
    }
}

# Validation constants
VALIDATION_LIMITS: Dict[str, Dict[str, Any]] = {
    'lot_area': {
        'min': 100,        # m²
        'max': 10000,      # m²
        'typical_min': 250,
        'typical_max': 2000
    },
    'building_area': {
        'min': 50,         # m²
        'max': 2000,       # m² (residential)
        'typical_min': 100,
        'typical_max': 800
    },
    'lot_frontage': {
        'min': 5,          # m
        'max': 100,        # m
        'typical_min': 10,
        'typical_max': 50
    },
    'building_height': {
        'min': 2.5,        # m
        'max': 20,         # m (residential)
        'typical_min': 3,
        'typical_max': 12
    },
    'bedrooms': {
        'min': 0,
        'max': 10,
        'typical_min': 1,
        'typical_max': 6
    },
    'bathrooms': {
        'min': 0,
        'max': 10,
        'typical_min': 1,
        'typical_max': 5
    },
    'building_age': {
        'min': 0,
        'max': 200,
        'typical_max': 100
    },
    'property_value': {
        'min': 100000,     # CAD
        'max': 20000000,   # CAD
        'typical_min': 400000,
        'typical_max': 3000000
    }
}

# Oakville neighborhoods
OAKVILLE_NEIGHBORHOODS: Dict[str, Dict[str, Any]] = {
    'Old Oakville': {
        'description': 'Historic downtown core',
        'price_premium': 0.15,
        'typical_zones': ['RL2', 'RL3', 'RUC'],
        'characteristics': ['heritage', 'walkable', 'lake_access']
    },
    'Glen Abbey': {
        'description': 'Planned golf course community',
        'price_premium': 0.08,
        'typical_zones': ['RL3', 'RL4', 'RL5'],
        'characteristics': ['golf_course', 'family_friendly', 'established']
    },
    'West Oak Trails': {
        'description': 'Newer suburban development',
        'price_premium': 0.05,
        'typical_zones': ['RL4', 'RL5', 'RM1'],
        'characteristics': ['new_construction', 'family_friendly', 'trails']
    },
    'Clearview': {
        'description': 'Established family neighborhood',
        'price_premium': 0.03,
        'typical_zones': ['RL4', 'RL5', 'RL6'],
        'characteristics': ['established', 'good_schools', 'family_friendly']
    },
    'Bronte': {
        'description': 'Waterfront village area',
        'price_premium': 0.20,
        'typical_zones': ['RL2', 'RL3', 'RM1'],
        'characteristics': ['waterfront', 'village_feel', 'recreation']
    },
    'Uptown Core': {
        'description': 'High-density urban core',
        'price_premium': 0.00,
        'typical_zones': ['RUC', 'RM3', 'RM4'],
        'characteristics': ['transit', 'urban', 'mixed_use']
    },
    'Iroquois Ridge': {
        'description': 'Higher-end residential area',
        'price_premium': 0.12,
        'typical_zones': ['RL1', 'RL2', 'RL3'],
        'characteristics': ['luxury', 'large_lots', 'established']
    }
}

# API endpoints and external services
API_ENDPOINTS: Dict[str, str] = {
    'oakville_gis_base': 'https://maps.oakville.ca/oakgis/rest/services/SBS',
    'zoning_service': '/Zoning_By_law_2014_014/FeatureServer/10/query',
    'parks_service': '/Parks_2022/FeatureServer/0/query',
    'parcels_service': '/Assessment_Parcels/FeatureServer/0/query',
    'heritage_service': '/Heritage_Properties/FeatureServer/0/query',
    'development_service': '/Development_Applications/FeatureServer/0/query',
    'geocoding_fallback': 'https://nominatim.openstreetmap.org'
}

# Analysis confidence factors
CONFIDENCE_FACTORS: Dict[str, Dict[str, float]] = {
    'data_quality': {
        'gis_data_available': 0.2,
        'recent_comparables': 0.3,
        'complete_property_info': 0.2,
        'market_data_current': 0.3
    },
    'property_factors': {
        'standard_property': 0.1,
        'heritage_property': -0.2,
        'unique_features': -0.1,
        'corner_lot': -0.05,
        'irregular_shape': -0.1
    },
    'market_factors': {
        'hot_market': -0.1,
        'balanced_market': 0.0,
        'cool_market': -0.05,
        'declining_market': -0.15
    }
}

# Error messages
ERROR_MESSAGES: Dict[str, str] = {
    'invalid_coordinates': 'Coordinates must be valid latitude/longitude values',
    'invalid_address': 'Please provide a valid street address',
    'geocoding_failed': 'Unable to find location. Please check the address.',
    'api_timeout': 'Service timeout. Please try again.',
    'api_error': 'Unable to retrieve data. Please try again later.',
    'invalid_zone': 'Invalid or unknown zoning code',
    'insufficient_data': 'Insufficient data for accurate analysis',
    'calculation_error': 'Error in calculation. Please verify inputs.',
    'validation_failed': 'Input validation failed. Please check your data.'
}

# Success messages
SUCCESS_MESSAGES: Dict[str, str] = {
    'geocoding_success': 'Address successfully located',
    'analysis_complete': 'Property analysis completed successfully',
    'validation_passed': 'All inputs validated successfully',
    'data_retrieved': 'Property data retrieved successfully'
}

# Unit conversion constants
UNIT_CONVERSIONS: Dict[str, float] = {
    'sqm_to_sqft': 10.764,
    'sqft_to_sqm': 0.092903,
    'sqm_to_acres': 0.000247105,
    'acres_to_sqm': 4046.86,
    'm_to_ft': 3.28084,
    'ft_to_m': 0.3048
}

# Default values
DEFAULT_VALUES: Dict[str, Any] = {
    'lot_area': 500.0,           # m²
    'building_area': 200.0,      # m²
    'lot_frontage': 15.0,        # m
    'bedrooms': 3,
    'bathrooms': 2.5,
    'building_age': 10,          # years
    'market_condition': MarketCondition.BALANCED,
    'analysis_types': [AnalysisType.ZONING, AnalysisType.VALUATION],
    'confidence_threshold': 0.7,
    'max_days_on_market': 120
}