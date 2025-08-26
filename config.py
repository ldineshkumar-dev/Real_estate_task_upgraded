"""
Configuration module for Oakville Real Estate Analyzer
Manages all application settings and constants
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""
    
    # API Configuration - WORKING MUNICIPAL APIs
    # UPDATE: Found working Oakville API endpoint!
    OAKVILLE_API_BASE = "https://maps.oakville.ca/oakgis/rest/services/SBS"
    
    MUNICIPAL_API_BASES = {
        'oakville': "https://maps.oakville.ca/oakgis/rest/services/SBS",
        'ottawa': "https://maps.ottawa.ca/ArcGIS/rest/services",
        'toronto': "https://map.toronto.ca/ArcGIS/rest/services"
    }
    
    # Primary working API (Oakville - NOW CONFIRMED WORKING!)
    PRIMARY_API_BASE = MUNICIPAL_API_BASES['oakville']
    
    # Working API Endpoints (Verified)
    API_ENDPOINTS = {
        # Oakville APIs - NOW CONFIRMED WORKING!
        'zoning': '/Zoning_By_law_2014_014/FeatureServer/10/query',
        'parcels': '/Assessment_Parcels/FeatureServer/0/query',
        'parks': '/Parks_2022/FeatureServer/0/query',
        'heritage': '/Heritage_Properties/FeatureServer/0/query',
        'development': '/Development_Applications/FeatureServer/0/query',
        
        # Ottawa APIs - Alternative working endpoints
        'ottawa_zoning': '/Zoning/MapServer/4/query',
        'ottawa_property': '/Property_Information/MapServer/0/query'
    }
    
    # Test coordinates for different cities
    TEST_COORDINATES = {
        'ottawa': {'lat': 45.4215, 'lon': -75.6919},
        'toronto': {'lat': 43.6532, 'lon': -79.3832},
        'oakville': {'lat': 43.4685, 'lon': -79.7071}
    }
    
    # Cache Configuration
    CACHE_TTL = 3600  # 1 hour cache
    ENABLE_CACHE = True
    
    # Geocoding Configuration
    GEOCODING_API_KEY = os.getenv("GEOCODING_API_KEY", "")
    DEFAULT_CITY = "Oakville"
    DEFAULT_PROVINCE = "ON"
    DEFAULT_COUNTRY = "Canada"
    
    # Development Configuration
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Data paths
    BASE_DIR = Path(__file__).parent
    DATA_PATH = BASE_DIR / "data"
    CACHE_PATH = BASE_DIR / "cache"
    LOGS_PATH = BASE_DIR / "logs"
    
    # Ensure directories exist
    DATA_PATH.mkdir(exist_ok=True)
    CACHE_PATH.mkdir(exist_ok=True)
    LOGS_PATH.mkdir(exist_ok=True)
    
    # Data files
    ZONING_RULES_FILE = DATA_PATH / "zoning_regulations.json"
    COMPREHENSIVE_ZONING_FILE = DATA_PATH / "comprehensive_zoning_regulations.json"
    ZONING_LOOKUP_TABLES_FILE = DATA_PATH / "zoning_lookup_tables.json"
    SPECIAL_PROVISIONS_FILE = DATA_PATH / "special_provisions.json"
    ZONE_MAPPINGS_FILE = DATA_PATH / "zone_mappings.csv"
    
    # Valuation Configuration
    DEFAULT_DEPRECIATION_RATE = 0.02  # 2% per year
    MAX_DEPRECIATION_YEARS = 40
    DEFAULT_MARKET_ADJUSTMENT = 1.05  # 5% hot market
    MIN_PROFIT_MARGIN = 0.15  # 15% minimum for development
    
    # API Request Configuration
    REQUEST_TIMEOUT = 30  # seconds
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    
    # Validation Limits
    MIN_LOT_AREA = 100.0  # square meters
    MAX_LOT_AREA = 10000.0  # square meters
    MIN_BUILDING_AREA = 50.0  # square meters
    MAX_BUILDING_AREA = 5000.0  # square meters
    MIN_BEDROOMS = 0
    MAX_BEDROOMS = 10
    MIN_BATHROOMS = 0.0
    MAX_BATHROOMS = 10.0
    MIN_BUILDING_AGE = 0
    MAX_BUILDING_AGE = 200
    
    # Map Configuration
    DEFAULT_LAT = 43.4685
    DEFAULT_LON = -79.7071
    DEFAULT_ZOOM = 15
    
    # Report Configuration
    COMPANY_NAME = "Oakville Real Estate Analytics"
    REPORT_FOOTER = "This analysis is for informational purposes only. Professional appraisal recommended."
    
    @classmethod
    def get_api_url(cls, endpoint: str, city: str = 'oakville') -> str:
        """Get full API URL for an endpoint"""
        if city in cls.MUNICIPAL_API_BASES:
            base_url = cls.MUNICIPAL_API_BASES[city]
        else:
            base_url = cls.OAKVILLE_API_BASE  # Use Oakville as default
        return base_url + cls.API_ENDPOINTS.get(endpoint, "")
    
    @classmethod
    def get_config_dict(cls) -> Dict[str, Any]:
        """Get configuration as dictionary"""
        return {
            key: value for key, value in cls.__dict__.items()
            if not key.startswith('_') and not callable(value)
        }


class ZoningConfig:
    """Enhanced zoning configuration based on comprehensive PDF analysis"""
    
    # System version and capabilities
    ANALYZER_VERSION = "2.0.0"
    PDF_SOURCE_VERSION = "2024-07-10"  # Consolidated date
    SUPPORTS_COMPREHENSIVE_ANALYSIS = True
    
    # Suffix zone special provisions - Enhanced
    SUFFIX_ZONES = {
        '-0': {
            'description': 'Special provisions for established neighborhoods - replaces R0 framework',
            'max_height': 9.0,
            'max_storeys': 2,
            'uses_far_table': True,
            'balcony_prohibition': True,
            'front_yard_averaging': True,
            'main_wall_proportionality': 0.50
        }
    }
    
    # Zone categories for quick lookup
    ZONE_CATEGORIES = {
        'residential_low': ['RL1', 'RL2', 'RL3', 'RL4', 'RL5', 'RL6', 'RL7', 'RL8', 'RL9', 'RL10', 'RL11'],
        'residential_uptown_core': ['RUC'],
        'residential_medium': ['RM1', 'RM2', 'RM3', 'RM4'],
        'residential_high': ['RH']
    }
    
    # Construction cost estimates (per square meter)
    CONSTRUCTION_COSTS = {
        'detached_dwelling': 2500,
        'semi_detached': 2200,
        'townhouse': 2000,
        'back_to_back_townhouse': 1800,
        'stacked_townhouse': 1900,
        'apartment': 1700,
        'luxury_finish': 3500,
        'standard_finish': 2500,
        'basic_finish': 1800
    }
    
    # Development soft costs
    SOFT_COST_PERCENTAGES = {
        'permits_and_fees': 0.05,
        'consultants': 0.08,
        'financing': 0.04,
        'contingency': 0.05,
        'marketing': 0.03,
        'total': 0.25
    }
    
    # Market value factors - Enhanced
    LOCATION_PREMIUMS = {
        'waterfront': 0.30,
        'park_adjacent': 0.10,
        'school_nearby': 0.08,
        'transit_accessible': 0.12,
        'shopping_nearby': 0.05,
        'quiet_street': 0.07,
        'corner_lot': -0.05,  # May have rear yard reduction benefit
        'busy_road': -0.10,
        'heritage_designated': -0.10,
        'suffix_0_zone': -0.05,  # Height/development restrictions
        'special_provision': 0.00,  # Varies by specific SP
        'aru_potential': 0.08,  # Additional residential unit potential
        'duplex_potential': 0.15,  # RL10 duplex potential
        'multi_unit_potential': 0.20  # RUC/RM zones
    }
    
    # Professional consultation requirements
    CONSULTATION_REQUIRED = {
        'special_provisions': True,
        'suffix_zones': False,  # Well-defined rules
        'heritage_properties': True,
        'complex_zoning': True,
        'development_applications': True
    }
    
    # Performance optimization settings
    OPTIMIZATION = {
        'use_lookup_tables': True,
        'cache_calculations': True,
        'batch_processing': True,
        'parallel_analysis': False  # For future enhancement
    }


# Initialize configuration
config = Config()
zoning_config = ZoningConfig()

# Validation function
def validate_data_files():
    """Validate that all required data files exist"""
    required_files = [
        config.COMPREHENSIVE_ZONING_FILE,
        config.ZONING_LOOKUP_TABLES_FILE,
        config.SPECIAL_PROVISIONS_FILE
    ]
    
    missing_files = []
    for file_path in required_files:
        if not file_path.exists():
            missing_files.append(str(file_path))
    
    if missing_files:
        raise FileNotFoundError(f"Missing required data files: {missing_files}")
    
    return True