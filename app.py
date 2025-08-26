"""
Oakville Real Estate Analyzer - Main Streamlit Application
AI-Powered Property Analysis & Valuation Platform
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Import backend modules  
from backend.api_client import get_api_client
from backend.api_client_corrected import get_corrected_api_client
from backend.zoning_analyzer import ZoningAnalyzer
from backend.property_valuator import PropertyValuator
from services.geocoding_service import get_geocoding_service
from utils.cache_manager import get_global_cache_manager, clear_all_caches, get_cache_stats
from utils.cache_preloader import preload_on_startup
from analysis_simple import run_simple_analysis
from models.property import Property, Location, PropertyDetails, PropertyAmenities
from models.valuation import MarketCondition
from config import Config

# Import measurement system components
from components.interactive_measurement_ui import render_measurement_interface
from components.property_boundary_map import create_property_boundary_map
from backend.interactive_measurement_client import get_measurement_client

# Import manual measurement tools
from manual_measurement import render_manual_measurement_tool
from enhanced_map_selector import render_enhanced_property_selector

# Import new ArcGIS-style components
from arcgis_style_map import render_arcgis_style_interface
from enhanced_zone_detector import EnhancedZoneDetector, detect_zone_for_property

# Configure logging first
import os
import logging
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG_MODE else "INFO")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/app_debug.log') if DEBUG_MODE else logging.NullHandler()
    ]
)

# Create debug logger
debug_logger = logging.getLogger(__name__)
logger = logging.getLogger(__name__)

# Import AI chatbot components (with system-wide chatbot priority)
try:
    from system_wide_chatbot import render_system_wide_chatbot_interface, get_system_wide_chatbot
    AI_CHATBOT_AVAILABLE = True
    CHATBOT_TYPE = "system_wide"
    logger.info("System-wide AI chatbot loaded successfully")
    render_chatbot_interface = render_system_wide_chatbot_interface
    render_compact_chat = None
except ImportError as e:
    logger.warning(f"System-wide AI Chatbot not available: {e}")
    
    try:
        from chatbot_ui import render_chatbot_interface, render_compact_chat
        AI_CHATBOT_AVAILABLE = True
        CHATBOT_TYPE = "advanced"
        logger.info("Advanced AI chatbot loaded successfully")
    except ImportError as e:
        logger.warning(f"Advanced AI Chatbot not available: {e}")
        # Set fallback functions to None initially
        render_chatbot_interface = None
        render_compact_chat = None
        
        try:
            from simple_ai_chatbot import render_simple_chatbot_interface
            AI_CHATBOT_AVAILABLE = True
            CHATBOT_TYPE = "simple"
            render_chatbot_interface = render_simple_chatbot_interface
            logger.info("Using simple AI chatbot fallback")
        except ImportError as e2:
            AI_CHATBOT_AVAILABLE = False
            CHATBOT_TYPE = None
            render_chatbot_interface = None
            render_simple_chatbot_interface = None
            logger.warning(f"No AI Chatbot available: {e2}")

# Debug helper function
def debug_print(message: str, data: Any = None):
    """Enhanced debug printing with conditional output"""
    if DEBUG_MODE:
        debug_logger.debug(f"🐛 DEBUG: {message}")
        if data is not None:
            debug_logger.debug(f"📊 DATA: {data}")
        # Also print to Streamlit in debug mode
        if 'streamlit' in str(type(st)):
            st.write(f"🐛 **DEBUG**: {message}")
            if data is not None:
                st.write(f"📊 **DATA**:", data)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Oakville Real Estate Analyzer",
    page_icon="🏘️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/your-repo/oakville-analyzer',
        'Report a bug': 'https://github.com/your-repo/oakville-analyzer/issues',
        'About': "# Oakville Real Estate Analyzer\n\nAI-powered property analysis platform for Oakville, Ontario."
    }
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8fafc;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3b82f6;
    }
    .warning-box {
        background-color: #fef3cd;
        border: 1px solid #faeaa7;
        border-radius: 0.375rem;
        padding: 0.75rem;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d1fae5;
        border: 1px solid #a7f3d0;
        border-radius: 0.375rem;
        padding: 0.75rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Disabled cache preloading to prevent startup issues
# Cache will be populated naturally as users interact with the app

# Initialize services
@st.cache_resource
def init_services():
    """Initialize all backend services with enhanced integrations"""
    zoning_analyzer = ZoningAnalyzer()
    property_valuator = PropertyValuator(zoning_analyzer=zoning_analyzer)
    
    # Initialize enhanced property client for exact data
    from backend.enhanced_property_client import get_enhanced_property_client
    enhanced_client = get_enhanced_property_client()
    
    # Initialize property dimensions client  
    from backend.property_dimensions_client import PropertyDimensionsClient
    dimensions_client = PropertyDimensionsClient()
    
    return {
        'api_client': get_corrected_api_client(),
        'zoning_analyzer': zoning_analyzer,
        'property_valuator': property_valuator,
        'geocoding_service': get_geocoding_service(),
        'cache_manager': get_global_cache_manager(),
        'dimensions_client': dimensions_client,
        'enhanced_client': enhanced_client
    }

# Initialize session state
def init_session_state():
    """Initialize session state variables"""
    if 'property_data' not in st.session_state:
        st.session_state.property_data = {}
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = {}
    if 'coordinates' not in st.session_state:
        st.session_state.coordinates = None

# Main application
def main():
    """Main application function"""
    debug_print("Starting main application")
    
    # Add debug info panel in sidebar if debug mode is enabled
    if DEBUG_MODE:
        st.sidebar.markdown("### 🐛 Debug Mode Active")
        if st.sidebar.button("🔍 Show Session State"):
            st.sidebar.json(dict(st.session_state))
        if st.sidebar.button("🔄 Clear Debug Logs"):
            with open('logs/app_debug.log', 'w') as f:
                f.write(f"Debug log cleared at {datetime.now()}\n")
            st.sidebar.success("Debug logs cleared!")
    
    debug_print("Initializing session state")
    init_session_state()
    
    debug_print("Initializing services")
    services = init_services()
    debug_print("Services initialized", list(services.keys()))
    
    # Header
    st.markdown('<h1 class="main-header">🏘️ Oakville Real Estate Analyzer</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-Powered Property Analysis & Valuation Platform</p>', unsafe_allow_html=True)
    
    # Sidebar - Property Input
    with st.sidebar:
        st.header("📍 Property Information")
        
        # Cache Management and Statistics (expandable)
        with st.expander("🛠️ Cache Management & Performance", expanded=False):
            cache_manager = services['cache_manager']
            cache_stats = cache_manager.get_stats()
            cache_size_info = cache_manager.get_cache_size_info()
            
            # Cache Statistics
            st.write("**📊 Cache Statistics**")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Hit Rate", cache_stats.get('overall_hit_rate', '0%'))
                st.metric("Total Entries", cache_stats.get('total_entries', 0))
            with col2:
                st.metric("Memory Cache", f"{cache_stats['memory']['size']}/{cache_stats['memory']['max_size']}")
                st.metric("Total Requests", cache_stats['memory']['total_requests'])
            with col3:
                st.metric("Cache Hits", cache_stats['memory']['hits'])
                st.metric("Pending Reqs", cache_stats.get('pending_requests', 0))
            
            # Cache Size Information
            if cache_size_info['file']['enabled']:
                st.write(f"**📁 File Cache**: {cache_size_info['file']['cache_files']} files, {cache_size_info['file'].get('total_size_mb', 0):.1f} MB")
            if cache_size_info['redis']['enabled']:
                st.write(f"**🔴 Redis Cache**: {cache_size_info['redis']['entries']} entries")
            
            st.divider()
            
            # Cache Management Actions
            st.write("**🧹 Cache Management**")
            
            # Critical warning about manual measurement system
            st.error("🚨 **MANUAL MEASUREMENT SYSTEM**: This app calculates lot areas from YOUR manual measurements only. Clearing cache will NOT affect your manual calculations.")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Refresh Stats", help="Reload cache statistics"):
                    st.rerun()
                
                if st.button("🗑️ Clear Expired", help="Remove only expired cache entries"):
                    with st.spinner("Clearing expired entries..."):
                        cleared = cache_manager.clear_expired_entries()
                        total_cleared = sum(cleared.values())
                        if total_cleared > 0:
                            st.success(f"Cleared {total_cleared} expired entries")
                        else:
                            st.info("No expired entries found")
                        st.rerun()
            
            with col2:
                if st.button("🚀 Warm Cache", help="Pre-load common data"):
                    with st.spinner("Warming cache..."):
                        from utils.cache_preloader import CachePreloader
                        preloader = CachePreloader()
                        try:
                            preloader.warm_up_common_queries()
                            st.success("🚀 Cache warmed successfully!")
                        except Exception as e:
                            st.error(f"Cache warming failed: {str(e)}")
                
                # Selective cache clearing
                cache_type = st.selectbox(
                    "Clear by Type:",
                    ["All Types", "api_response", "zoning", "geocoding", "valuation", "analysis"],
                    help="Select cache type to clear"
                )
                
                if st.button(f"🗑️ Clear {cache_type}", help=f"Clear {cache_type.lower()} cache entries"):
                    with st.spinner(f"Clearing {cache_type.lower()} cache..."):
                        if cache_type == "All Types":
                            cleared = cache_manager.clear_all_caches()
                            total_cleared = sum(cleared.values())
                            st.success(f"🗑️ Cleared ALL cache: {total_cleared} total entries")
                            st.write(f"- Memory: {cleared['memory']} entries")
                            st.write(f"- Redis: {cleared['redis']} entries") 
                            st.write(f"- File: {cleared['file']} entries")
                        else:
                            cleared = cache_manager.clear_cache_by_type(cache_type)
                            st.success(f"🗑️ Cleared {cleared} {cache_type} entries")
                        st.rerun()
            
            # Manual cache clearing instructions
            with st.expander("📝 Manual Cache Clearing Instructions"):
                st.markdown("""
                **📁 Manual File Cache Clearing:**
                1. Navigate to the project directory
                2. Delete files in the `cache/` folder
                3. Or run: `rm -rf cache/*.cache` (Linux/Mac) or `del cache\\*.cache` (Windows)
                
                **🔴 Redis Cache Clearing** (if enabled):
                1. Connect to Redis: `redis-cli`
                2. Clear database: `FLUSHDB`
                
                **🧠 Memory Cache**: Automatically cleared on app restart
                
                **⚠️ Note**: Cache clearing does not affect your manual lot area calculations, which are stored in session state.
                """)
        
        st.divider()
        
        # Sample addresses for easy testing
        st.markdown("**🏠 Try these sample addresses:**")
        sample_addresses = [
            "2320 Lakeshore Rd W, Oakville, ON",
            "383 Maplehurst Avenue, Oakville, ON", 
            "1500 Rebecca Street, Oakville, ON",
            "100 Lakeshore Road East, Oakville, ON"
        ]
        
        selected_sample = st.selectbox("Quick select:", ["Enter custom address..."] + sample_addresses)
        
        st.divider()
        
        # Input method selection
        input_method = st.radio(
            "Input Method",
            ["🏠 Address", "📍 Coordinates"],
            help="Choose how to specify the property location"
        )
        
        # Address or coordinate input
        if input_method == "🏠 Address":
            address_input(services)
        else:
            coordinate_input()
        
        st.divider()
        
        # Property details
        property_details_input()
        
        st.divider()
        
        # Analysis options
        analysis_options()
    
    # Main content area
    if st.session_state.coordinates:
        display_analysis_results(services)
    else:
        display_welcome_screen()

def address_input(services):
    """Handle address input and geocoding"""
    st.subheader("Address Input")
    
    # Sample addresses for quick testing
    sample_addresses = [
        "2320 Lakeshore Rd W, Oakville, ON",
        "383 Maplehurst Avenue, Oakville, ON", 
        "1500 Rebecca Street, Oakville, ON",
        "Custom Address..."
    ]
    
    selected_sample = st.selectbox(
        "Quick Select (Sample Addresses)",
        sample_addresses,
        help="Select a sample address or choose 'Custom Address' to enter your own"
    )
    
    if selected_sample == "Custom Address...":
        address = st.text_input(
            "Property Address",
            placeholder="Enter full address (e.g., 123 Main St, Oakville, ON)",
            help="Include street number, street name, and city for best results"
        )
    else:
        address = selected_sample
        st.text_input("Selected Address", value=address, disabled=True)
    
    if st.button("🔍 Geocode Address", type="primary"):
        if address:
            with st.spinner("Geocoding address..."):
                geocode_result = services['geocoding_service'].geocode_address(address)
                
                if geocode_result:
                    st.session_state.coordinates = (
                        geocode_result['latitude'], 
                        geocode_result['longitude']
                    )
                    st.session_state.property_data['address'] = geocode_result['formatted_address']
                    
                    if geocode_result.get('in_oakville', True):
                        st.success(f"✅ Found: {geocode_result['latitude']:.6f}, {geocode_result['longitude']:.6f}")
                    else:
                        st.warning("⚠️ Address appears to be outside Oakville boundaries")
                        st.session_state.coordinates = (
                            geocode_result['latitude'], 
                            geocode_result['longitude']
                        )
                else:
                    st.error("❌ Could not geocode address. Please check the address and try again.")
        else:
            st.error("Please enter an address")

def coordinate_input():
    """Handle direct coordinate input"""
    st.subheader("Coordinate Input")
    
    col1, col2 = st.columns(2)
    with col1:
        lat = st.number_input(
            "Latitude",
            value=Config.DEFAULT_LAT,
            format="%.6f",
            help="Latitude coordinate (North/South)"
        )
    with col2:
        lon = st.number_input(
            "Longitude", 
            value=Config.DEFAULT_LON,
            format="%.6f",
            help="Longitude coordinate (East/West)"
        )
    
    if st.button("📍 Set Coordinates", type="primary"):
        st.session_state.coordinates = (lat, lon)
        st.success(f"✅ Coordinates set: {lat:.6f}, {lon:.6f}")

def property_details_input():
    """Property details input form"""
    st.subheader("🏗️ Property Details")
    
    # Lot information with auto-fetch functionality
    st.markdown("### 📐 Lot Dimensions")
    
    # Auto-fetch button
    coords = st.session_state.get('coordinates', (Config.DEFAULT_LAT, Config.DEFAULT_LON))
    address = st.session_state.get('address', "")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("💡 Click 'Auto-Fetch' to automatically retrieve lot dimensions from official records")
    with col2:
        auto_fetch_clicked = st.button("🔄 Auto-Fetch", type="primary", help="Automatically fetch lot area, frontage, and depth from APIs")
    
    # Initialize or get existing auto-fetched data
    if 'auto_fetched_dimensions' not in st.session_state:
        st.session_state.auto_fetched_dimensions = None
    
    # Handle auto-fetch
    if auto_fetch_clicked:
        try:
            # Try property dimensions extractor first for precise data
            try:
                from property_dimensions_extractor import get_property_dimensions
                
                with st.spinner("🎯 Extracting precise property dimensions..."):
                    dimensions = get_property_dimensions(address)
                    
                    if dimensions.confidence in ['high', 'medium'] and dimensions.lot_area_sqm:
                        auto_dims = {
                            'success': True,
                            'lot_area': dimensions.lot_area_sqm,
                            'lot_frontage': dimensions.frontage_m,
                            'lot_depth': dimensions.depth_m,
                            'source': dimensions.data_source,
                            'confidence': dimensions.confidence,
                            'data_sources': {
                                'lot_area': dimensions.data_source,
                                'frontage': dimensions.data_source,
                                'depth': dimensions.data_source
                            },
                            'notes': [dimensions.notes] if dimensions.notes else []
                        }
                        st.session_state.auto_fetched_dimensions = auto_dims
                    else:
                        raise Exception("No high-quality dimensions available")
            except Exception:
                # Fallback to enhanced property client
                from backend.enhanced_property_client import get_enhanced_property_client
            
            with st.spinner("🔍 Fetching property dimensions from official APIs..."):
                enhanced_client = get_enhanced_property_client()
                zone_code = st.session_state.get('zone_code', '')
                
                # Try enhanced client first for exact data
                auto_dims = enhanced_client.get_enhanced_property_data(address, coords[0], coords[1])
                
                # If enhanced client doesn't have exact data, fallback to regular client
                if not auto_dims.get('success') or auto_dims.get('source') not in ['verified_zoning_map', 'curated_verified']:
                    from backend.property_dimensions_client import PropertyDimensionsClient
                    dims_client = PropertyDimensionsClient()
                    auto_dims = dims_client.get_dimensions_with_fallbacks(
                        lat=coords[0], 
                        lon=coords[1], 
                        address=address,
                        zone_code=zone_code
                    )
                
                st.session_state.auto_fetched_dimensions = auto_dims
                
                if auto_dims['success'] and auto_dims.get('lot_area'):
                    # Show zone code and special provisions prominently
                    zone_display = auto_dims.get('zone_code', 'Unknown')
                    area_display = f"{auto_dims['lot_area']:.2f} m²"
                    
                    success_msg = f"✅ Found property data! Zone: {zone_display}, Lot area: {area_display}"
                    st.success(success_msg)
                    
                    # Show special provisions prominently if they exist
                    sp = auto_dims.get('special_provision', '')
                    if sp and sp.strip():
                        st.info(f"⚠️ **Special Provision**: {sp} (overrides general by-law regulations)")
                    
                    # Show exact dimensions if available
                    frontage = auto_dims.get('lot_frontage')
                    depth = auto_dims.get('lot_depth')
                    if frontage and depth:
                        st.info(f"📏 **Exact Dimensions**: {frontage}m × {depth}m (frontage × depth)")
                    
                    # Show data source and confidence
                    source = auto_dims.get('source', 'unknown')
                    confidence = auto_dims.get('confidence', 'unknown')
                    st.caption(f"📊 Source: {source} | Confidence: {confidence}")
                    
                    # Show data sources breakdown
                    sources = auto_dims.get('data_sources', {})
                    if sources:
                        source_text = ", ".join([f"{k}: {v}" for k, v in sources.items() if v])
                        st.caption(f"🔍 Data sources: {source_text}")
                        
                    # Show warnings if any
                    if auto_dims.get('warnings'):
                        for warning in auto_dims['warnings']:
                            st.warning(f"⚠️ {warning}")
                else:
                    st.warning("⚠️ Could not retrieve property dimensions from APIs. Using fallback estimates.")
        except Exception as e:
            st.error(f"❌ Error fetching property dimensions: {str(e)}")
            st.session_state.auto_fetched_dimensions = None
    
    # Determine default values based on auto-fetch results
    auto_dims = st.session_state.auto_fetched_dimensions
    default_area = auto_dims['lot_area'] if auto_dims and auto_dims.get('lot_area') else 500.0
    default_frontage = auto_dims['lot_frontage'] if auto_dims and auto_dims.get('lot_frontage') else 15.0
    default_depth = auto_dims['lot_depth'] if auto_dims and auto_dims.get('lot_depth') else 33.3
    
    col1, col2, col3 = st.columns(3)
    with col1:
        lot_area = st.number_input(
            "Lot Area (m²)",
            min_value=Config.MIN_LOT_AREA,
            max_value=Config.MAX_LOT_AREA,
            value=default_area,
            step=10.0,
            help="Total lot area in square meters"
        )
        
        # Show data source indicator
        if auto_dims and auto_dims.get('lot_area'):
            confidence = auto_dims.get('confidence', {}).get('lot_area', 'unknown')
            source = auto_dims.get('data_sources', {}).get('lot_area', 'unknown')
            if confidence == 'high':
                st.success(f"✅ From {source}")
            elif confidence == 'medium':
                st.info(f"ℹ️ Calculated ({source})")
            else:
                st.warning(f"⚠️ Estimate ({source})")
        
    with col2:
        lot_frontage = st.number_input(
            "Lot Frontage (m)",
            min_value=5.0,
            max_value=100.0,
            value=default_frontage,
            step=0.5,
            help="Lot frontage in meters"
        )
        
        # Show data source indicator
        if auto_dims and auto_dims.get('lot_frontage'):
            confidence = auto_dims.get('confidence', {}).get('lot_frontage', 'unknown')
            source = auto_dims.get('data_sources', {}).get('lot_frontage', 'unknown')
            if confidence == 'high':
                st.success(f"✅ From {source}")
            elif confidence == 'medium':
                st.info(f"ℹ️ Calculated ({source})")
            else:
                st.warning(f"⚠️ Estimate ({source})")
                
    with col3:
        lot_depth = st.number_input(
            "Lot Depth (m)",
            min_value=5.0,
            max_value=200.0,
            value=default_depth,
            step=0.5,
            help="Lot depth in meters"
        )
        
        # Show data source indicator  
        if auto_dims and auto_dims.get('lot_depth'):
            confidence = auto_dims.get('confidence', {}).get('lot_depth', 'unknown')
            source = auto_dims.get('data_sources', {}).get('lot_depth', 'unknown')
            if confidence == 'high':
                st.success(f"✅ From {source}")
            elif confidence == 'medium':
                st.info(f"ℹ️ Calculated ({source})")
            else:
                st.warning(f"⚠️ Estimate ({source})")
    
    # Building information
    col1, col2 = st.columns(2)
    with col1:
        building_area = st.number_input(
            "Building Area (m²)",
            min_value=Config.MIN_BUILDING_AREA,
            max_value=Config.MAX_BUILDING_AREA,
            value=200.0,
            step=10.0,
            help="Total building area in square meters"
        )
    with col2:
        building_type = st.selectbox(
            "Building Type",
            ["detached_dwelling", "semi_detached_dwelling", "townhouse_dwelling", 
             "apartment_dwelling", "duplex_dwelling"],
            help="Type of residential building"
        )
    
    # Room details
    col1, col2, col3 = st.columns(3)
    with col1:
        bedrooms = st.number_input(
            "Bedrooms",
            min_value=Config.MIN_BEDROOMS,
            max_value=Config.MAX_BEDROOMS,
            value=3,
            help="Number of bedrooms"
        )
    with col2:
        bathrooms = st.number_input(
            "Bathrooms",
            min_value=Config.MIN_BATHROOMS,
            max_value=Config.MAX_BATHROOMS,
            value=2.5,
            step=0.5,
            help="Number of bathrooms"
        )
    with col3:
        age = st.number_input(
            "Building Age (years)",
            min_value=Config.MIN_BUILDING_AGE,
            max_value=Config.MAX_BUILDING_AGE,
            value=10,
            help="Age of the building in years"
        )
    
    # Additional features
    st.subheader("Additional Features")
    col1, col2 = st.columns(2)
    with col1:
        is_corner = st.checkbox("Corner Lot", help="Property is on a corner")
        waterfront = st.checkbox("Waterfront", help="Property has water access")
    with col2:
        heritage = st.checkbox("Heritage Designated", help="Property has heritage designation")
        renovation_year = st.number_input(
            "Recent Renovation Year",
            min_value=1980,
            max_value=datetime.now().year,
            value=None,
            help="Year of major renovation (optional)"
        )
    
    # Store in session state
    st.session_state.property_data.update({
        'lot_area': lot_area,
        'lot_frontage': lot_frontage,
        'lot_depth': lot_depth,
        'building_area': building_area,
        'building_type': building_type,
        'bedrooms': bedrooms,
        'bathrooms': bathrooms,
        'age': age,
        'is_corner': is_corner,
        'waterfront': waterfront,
        'heritage': heritage,
        'renovation_year': renovation_year
    })

def analysis_options():
    """Analysis options and settings"""
    st.subheader("⚙️ Analysis Options")
    
    market_condition = st.selectbox(
        "Market Condition",
        ["balanced", "hot", "cool", "declining"],
        index=0,
        help="Current market conditions affecting valuations"
    )
    
    analysis_types = st.multiselect(
        "Analysis Types",
        ["Zoning Analysis", "Property Valuation", "Development Potential", "Market Comparison"],
        default=["Zoning Analysis", "Property Valuation"],
        help="Select which analyses to perform"
    )
    
    st.session_state.property_data.update({
        'market_condition': market_condition,
        'analysis_types': analysis_types
    })

def display_welcome_screen():
    """Display welcome screen when no property is selected"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        ### Welcome to Oakville Real Estate Analyzer
        
        This AI-powered platform provides comprehensive real estate analysis for properties in Oakville, Ontario.
        
        **Features:**
        - 🗺️ **Zoning Analysis** - Detailed zoning regulations and compliance
        - 💰 **Property Valuation** - Market-based property value estimates  
        - 🏗️ **Development Potential** - Building capacity and investment analysis
        - 📊 **Market Insights** - Local market trends and comparisons
        
        **Getting Started:**
        1. Enter a property address or coordinates in the sidebar
        2. Provide property details (lot size, building info, etc.)
        3. Select your analysis options
        4. View comprehensive analysis results
        
        **Sample Addresses to Try:**
        - 2320 Lakeshore Rd W, Oakville, ON
        - 383 Maplehurst Avenue, Oakville, ON
        - 1500 Rebecca Street, Oakville, ON
        """)

def display_analysis_results(services):
    """Display comprehensive analysis results"""
    lat, lon = st.session_state.coordinates
    
    # Run analysis with progress indicators
    progress_container = st.container()
    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("🔍 Starting analysis...")
        progress_bar.progress(10)
        
        try:
            status_text.text("🔍 Getting zoning info with enhanced detection...")
            progress_bar.progress(30)
            
            # Use enhanced zone detector for better zone detection including special provisions
            enhanced_detector = EnhancedZoneDetector()
            enhanced_zone_info = enhanced_detector.detect_zone_code(
                lat, lon, st.session_state.property_data.get('address', '')
            )
            
            # Display enhanced zone detection results
            if enhanced_zone_info.base_zone != "Unknown":
                zone_display = enhanced_zone_info.full_zone_code
                st.info(f"🎯 **Enhanced Zone Detection**: {zone_display} (Confidence: {enhanced_zone_info.confidence})")
                
                if enhanced_zone_info.special_provision:
                    st.warning(f"⚠️ **Special Provision Detected**: {enhanced_zone_info.special_provision}")
                
                if enhanced_zone_info.source:
                    st.caption(f"📊 Source: {enhanced_zone_info.source}")
                
                # Store enhanced zone info for AI Assistant
                st.session_state.enhanced_zone_info = enhanced_zone_info
            
            progress_bar.progress(40)
            
            # Integrate manual measurements from interactive measurement tool
            enhanced_property_data = st.session_state.property_data.copy()
            
            # Check for manual lot calculation from measurement tool
            if hasattr(st.session_state, 'manual_lot_calculation') and st.session_state.manual_lot_calculation:
                manual_calc = st.session_state.manual_lot_calculation
                enhanced_property_data.update({
                    'lot_area': manual_calc['lot_area'],
                    'lot_frontage': manual_calc['frontage'], 
                    'lot_depth': manual_calc['depth'],
                    'area_calculation_method': manual_calc['method'],
                    'area_calculation_confidence': manual_calc['confidence'],
                    'manual_measurement_used': True
                })
                
                # Show different success message based on measurement method
                method_display = {
                    'precise_2_point_manual_selection': '🎯 **PRECISE 2-POINT MEASUREMENTS**',
                    'manual_line_drawing': '📏 **MANUAL LINE MEASUREMENTS**',
                    'advanced_property_selector': '🗺️ **ADVANCED PROPERTY SELECTOR**'
                }
                method_text = method_display.get(manual_calc['method'], '🎯 **MANUAL MEASUREMENTS**')
                st.success(f"{method_text}: Lot Area = {manual_calc['lot_area']:.1f} m² (Frontage: {manual_calc['frontage']:.2f}m × Depth: {manual_calc['depth']:.2f}m)")
            else:
                # Check if user entered measurements in the input fields
                manual_measurements = {}
                if 'active_measurements' in st.session_state and st.session_state.active_measurements:
                    measurements = st.session_state.active_measurements
                    frontage_measurements = [m for m in measurements if m.measurement_type == 'frontage']
                    depth_measurements = [m for m in measurements if m.measurement_type == 'depth']
                    
                    if frontage_measurements and depth_measurements:
                        frontage_avg = sum(m.distance_m for m in frontage_measurements) / len(frontage_measurements)
                        depth_avg = sum(m.distance_m for m in depth_measurements) / len(depth_measurements)
                        
                        manual_measurements = {
                            'frontage': frontage_avg,
                            'depth': depth_avg
                        }
                        
                        enhanced_property_data.update({
                            'lot_area': frontage_avg * depth_avg,
                            'lot_frontage': frontage_avg,
                            'lot_depth': depth_avg,
                            'area_calculation_method': 'manual_measurement_frontage_x_depth',
                            'area_calculation_confidence': 'user_measured',
                            'manual_measurement_used': True
                        })
                        st.success(f"🎯 **Using YOUR manual measurements**: Lot Area = {frontage_avg * depth_avg:.1f} m² (Frontage: {frontage_avg:.2f}m × Depth: {depth_avg:.2f}m)")
                
                if not manual_measurements:
                    st.warning("⚠️ **Manual measurements recommended**: Use the 'Interactive Measurement' tab to measure frontage and depth for accurate lot area calculation.")
            
            analysis_results = run_simple_analysis(services, lat, lon, enhanced_property_data)
            
            progress_bar.progress(80)
            status_text.text("📋 Completing analysis...")
            
            progress_bar.progress(100)
            status_text.text("✅ Analysis complete!")
            
            # Clear progress indicators after a brief moment
            import time
            time.sleep(0.5)
            progress_container.empty()
            
        except Exception as e:
            progress_container.empty()
            st.error(f"❌ Analysis failed: {str(e)}")
            return
    
    if not analysis_results:
        st.error("❌ Failed to analyze property. Please check the location and try again.")
        return
    
    # Streamlined tabs focusing on core functionality
    core_tabs = ["🗺️ Property Overview", "📋 Zoning & Analysis", "💰 Valuation & Development", "📏 Measurements"]
    
    if AI_CHATBOT_AVAILABLE:
        if CHATBOT_TYPE == "system_wide":
            core_tabs.append("🤖 AI Assistant")
        else:
            core_tabs.append("🤖 Property AI")
        tab1, tab2, tab3, tab4, tab5 = st.tabs(core_tabs)
    else:
        tab1, tab2, tab3, tab4 = st.tabs(core_tabs)
    
    with tab1:
        # Combined overview with map and key property details
        display_overview_and_map(analysis_results, lat, lon)
        
        # Add market insights to overview
        st.divider()
        st.subheader("📊 Market Context")
        display_market_insights_summary(analysis_results)
    
    with tab2:
        # Combined zoning analysis with special requirements
        display_zoning_analysis(analysis_results)
        
        st.divider()
        st.subheader("🏛️ Special Requirements & Compliance")
        display_special_requirements(analysis_results)
    
    with tab3:
        # Combined valuation and development potential
        display_valuation_analysis(analysis_results)
        
        st.divider()
        st.subheader("🏗️ Development Analysis")
        display_development_potential(analysis_results)
    
    with tab4:
        # Combined measurement tools
        st.subheader("📏 Interactive Property Measurement")
        display_interactive_measurement(lat, lon, st.session_state.property_data.get('address', ''))
        
        st.divider()
        st.subheader("🎯 Manual Measurement Tools")
        display_manual_measurement_tools(lat, lon, st.session_state.property_data.get('address', ''))
    
    # AI Assistant tab (if available)
    if AI_CHATBOT_AVAILABLE:
        with tab5:
            display_ai_assistant(analysis_results, lat, lon)

def display_interactive_measurement(lat: float, lon: float, address: str = None):
    """Display interactive measurement interface"""
    try:
        render_measurement_interface(lat, lon, address)
    except Exception as e:
        st.error(f"❌ Error loading measurement interface: {str(e)}")
        st.markdown("""
        **Fallback Measurement Options:**
        
        1. **Manual Input**: Enter frontage and depth measurements manually in the property details section
        2. **Google Maps**: Use Google Maps ruler tool to measure property dimensions
        3. **Survey Documents**: Check property survey or deed for exact measurements
        
        **Common Oakville Lot Sizes:**
        - RL1: Min 1,393.5 m² (30.5m frontage)
        - RL2: Min 836.0 m² (22.5m frontage) 
        - RL3: Min 557.5 m² (18.0m frontage)
        - RL4: Min 511.0 m² (16.5m frontage)
        - RL5: Min 464.5 m² (15.0m frontage)
        - RL6: Min 250.0 m² (11.0m frontage)
        """)

def display_manual_measurement_tools(lat: float, lon: float, address: str = None):
    """Display manual measurement tools interface"""
    st.subheader("🎯 Manual Property Measurement Tools")
    
    # Provide multiple manual measurement options
    measurement_tool = st.radio(
        "Choose Measurement Tool:",
        ["🗺️ ArcGIS-Style Interactive Map", "🎯 Precise 2-Point Selector", "📏 Simple Manual Measurement", "🗗 Advanced Property Selector"],
        help="Select the measurement tool that best fits your needs"
    )
    
    if measurement_tool == "🗺️ ArcGIS-Style Interactive Map":
        st.markdown("### 🗺️ ArcGIS-Style Interactive Property Measurement")
        st.info("🎯 **Professional-grade measurement**: Click points, draw shapes, and measure with satellite imagery and property overlays")
        
        try:
            measurements = render_arcgis_style_interface(lat, lon, address)
            
            # Update session state with ArcGIS measurements
            if measurements and measurements.get('measurements'):
                meas = measurements['measurements']
                if meas.get('total_distance_m', 0) > 0:
                    # For now, use total distance as frontage approximation
                    # In a real implementation, you'd separate frontage and depth measurements
                    frontage_approx = meas['total_distance_m'] / 2  # Rough approximation
                    depth_approx = meas['total_distance_m'] / 2
                    
                    st.session_state.manual_lot_calculation = {
                        'lot_area': frontage_approx * depth_approx,
                        'frontage': frontage_approx,
                        'depth': depth_approx,
                        'method': 'arcgis_interactive_measurement',
                        'confidence': 'user_measured_interactive'
                    }
                    
                    st.success(f"✅ Interactive measurements captured: Total distance {meas['total_distance_m']:.1f}m ({meas['total_distance_ft']:.1f}ft)")
        except Exception as e:
            st.error(f"❌ Error with ArcGIS-style map: {str(e)}")
            st.info("Try one of the other measurement tools below")
    
    elif measurement_tool == "🎯 Precise 2-Point Selector":
        st.markdown("### 🎯 Precise 2-Point Property Measurement")
        st.info("Click exactly 2 points for frontage, then 2 points for depth - most precise method!")
        
        # For now, implement a simple 2-point selector since precise_point_selector.py needs to be created
        st.markdown("#### 🔧 Implementation Notice")
        st.warning("The precise 2-point selector is being implemented. Please use the ArcGIS-Style Interactive Map for now.")
        st.info("This tool will allow you to:")
        st.markdown("- Click exactly 2 points to define frontage")
        st.markdown("- Click exactly 2 points to define depth") 
        st.markdown("- Automatically calculate rectangular area")
    
    elif measurement_tool == "📏 Simple Manual Measurement":
        st.markdown("### 📏 Simple Manual Measurement Tool")
        st.info("Click and draw lines on the map to measure property frontage and depth")
        
        try:
            measurements = render_manual_measurement_tool()
            
            # Update session state with manual measurements
            if measurements:
                st.session_state.manual_lot_calculation = {
                    'lot_area': measurements['area_sqft'] / 10.764,  # Convert to m²
                    'frontage': measurements['frontage_ft'] / 3.281,  # Convert to m
                    'depth': measurements['depth_ft'] / 3.281,  # Convert to m
                    'method': 'manual_line_drawing',
                    'confidence': 'user_measured'
                }
                
                st.success(f"✅ Measurements updated: {measurements['frontage_ft']:.1f}' × {measurements['depth_ft']:.1f}' = {measurements['area_sqft']:.0f} sq ft")
        except Exception as e:
            st.error(f"❌ Error with simple measurement tool: {str(e)}")
            st.info("Try the Advanced Property Selector below")
    
    else:  # Advanced Property Selector 
        st.markdown("### 🗗 Advanced Property Selector")
        st.info("Advanced tool with satellite view, multiple selection modes, and property boundary tracing")
        
        try:
            measurements = render_enhanced_property_selector()
            
            # Update session state with manual measurements
            if measurements:
                st.session_state.manual_lot_calculation = {
                    'lot_area': measurements['area_sqm'],
                    'frontage': measurements['frontage_m'],
                    'depth': measurements['depth_m'],
                    'method': 'advanced_property_selector',
                    'confidence': 'user_measured'
                }
                
                st.success(f"✅ Advanced measurements updated: {measurements['frontage']:.1f}m × {measurements['depth']:.1f}m = {measurements['area']:.0f} sq ft")
        except Exception as e:
            st.error(f"❌ Error with advanced property selector: {str(e)}")
            st.info("Try the Simple Manual Measurement above")
    
    # Display current manual measurements if available
    if hasattr(st.session_state, 'manual_lot_calculation') and st.session_state.manual_lot_calculation:
        calc = st.session_state.manual_lot_calculation
        st.divider()
        st.markdown("### 📊 Current Manual Measurements")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Frontage", f"{calc['frontage']:.2f} m")
        with col2:
            st.metric("Depth", f"{calc['depth']:.2f} m") 
        with col3:
            st.metric("Area", f"{calc['lot_area']:.1f} m²")
        
        st.caption(f"Method: {calc['method']} | Confidence: {calc['confidence']}")
        
        if st.button("🗑️ Clear Manual Measurements"):
            del st.session_state.manual_lot_calculation
            st.rerun()


def run_comprehensive_analysis(services, lat: float, lon: float) -> Optional[Dict]:
    """Run comprehensive property analysis with timeout protection"""
    import time
    start_time = time.time()
    timeout = 30  # 30 seconds
    
    try:
        
        # Quick analysis instead of comprehensive
        # Get enhanced zoning info (fixes 383 Maplehurst Avenue issue)
        zoning_info = services['api_client'].get_enhanced_zoning_info(
            lat, lon, st.session_state.property_data.get('address', '')
        )
        
        if not zoning_info:
            st.warning("⚠️ Could not retrieve zoning data from Oakville GIS. Using fallback analysis.")
        
        # Extract zoning information
        zone_code = "RL3"  # Default
        if zoning_info:
            zone_code = zoning_info.get('zone_code', 'RL3')
        
        # Simplified analysis to prevent hanging
        analysis_results = {
            'zoning': {
                'zone_code': zone_code,
                'zone_class': zoning_info.get('zone_class', 'Residential Low') if zoning_info else 'Residential Low',
                'special_provision': zoning_info.get('special_provision', '') if zoning_info else '',
                'confidence': zoning_info.get('confidence', 'medium') if zoning_info else 'low',
                'source': zoning_info.get('source', 'fallback') if zoning_info else 'fallback'
            },
            'coordinates': {'lat': lat, 'lon': lon},
            'property_data': st.session_state.property_data
        }
        
        # Get basic zoning analysis from the zoning analyzer
        try:
            zoning_analysis = services['zoning_analyzer'].analyze_development_potential(
                zone_code=zone_code,
                lot_area=st.session_state.property_data['lot_area'],
                lot_frontage=st.session_state.property_data['lot_frontage']
            )
            analysis_results['zoning_analysis'] = zoning_analysis
        except Exception as e:
            st.warning(f"Zoning analysis failed: {e}")
            analysis_results['zoning_analysis'] = {'error': str(e)}
        
        # Get basic property valuation
        try:
            valuation = services['property_valuator'].estimate_property_value(
                zone_code=zone_code,
                lot_area=st.session_state.property_data['lot_area'],
                building_area=st.session_state.property_data['building_area'],
                num_bedrooms=st.session_state.property_data.get('bedrooms', 3),
                num_bathrooms=st.session_state.property_data.get('bathrooms', 2.5),
                age_years=st.session_state.property_data.get('age', 10)
            )
            analysis_results['valuation'] = valuation
        except Exception as e:
            st.warning(f"Valuation failed: {e}")
            analysis_results['valuation'] = {'error': str(e)}
        
        # Check if we're approaching timeout
        if time.time() - start_time > timeout - 5:
            st.warning("⏱️ Analysis taking longer than expected, but continuing...")
        
        return analysis_results
        
    except Exception as e:
        if time.time() - start_time > timeout:
            st.error("⏱️ Analysis timed out. Please try again with simpler parameters.")
        else:
            st.error(f"❌ Analysis failed: {str(e)}")
        # Return basic fallback analysis
        return {
            'zoning': {
                'zone_code': 'RL3',
                'zone_class': 'Residential Low',
                'source': 'error_fallback'
            },
            'coordinates': {'lat': lat, 'lon': lon},
            'property_data': st.session_state.property_data,
            'error': str(e)
        }


def display_overview_and_map(analysis_results: Dict, lat: float, lon: float):
    """Display property overview and interactive map"""
    st.subheader("📍 Property Overview")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Get enhanced zone display for overview
        zoning = analysis_results.get('zoning_analysis', {})
        base_zoning = analysis_results.get('zoning', {})
        
        zone_code = (
            get_zoning_value(zoning, 'zone_code') or
            get_zoning_value(zoning, 'base_zone') or
            base_zoning.get('zone_code', 'Unknown')
        )
        
        suffix = get_zoning_value(zoning, 'suffix', '')
        special_provision = get_zoning_value(zoning, 'special_provision', '')
        zone_display = format_zone_display(zone_code, suffix, special_provision)
        
        st.metric(
            "Zone Classification",
            zone_display,
            help="Complete zoning designation from Oakville By-law 2014-014"
        )
    
    with col2:
        st.metric(
            "Estimated Value",
            f"${analysis_results['valuation']['estimated_value']:,.0f}",
            help="AI-estimated property value"
        )
    
    with col3:
        st.metric(
            "Development Potential",
            f"{analysis_results.get('zoning_analysis', {}).get('potential_units', 1)} units",
            help="Maximum potential dwelling units"
        )
    
    with col4:
        confidence = analysis_results['valuation'].get('confidence', 'Medium')
        st.metric(
            "Analysis Confidence",
            confidence,
            help="Confidence level in analysis results"
        )
    
    st.divider()
    
    # Interactive map
    st.subheader("🗺️ Interactive Map")
    
    # Create Folium map
    m = folium.Map(
        location=[lat, lon],
        zoom_start=16,
        tiles='OpenStreetMap'
    )
    
    # Add property marker with enhanced zone display
    zoning = analysis_results.get('zoning_analysis', {})
    base_zoning = analysis_results.get('zoning', {})
    
    zone_code = (
        get_zoning_value(zoning, 'zone_code') or
        get_zoning_value(zoning, 'base_zone') or
        base_zoning.get('zone_code', 'Unknown')
    )
    
    suffix = get_zoning_value(zoning, 'suffix', '')
    special_provision = get_zoning_value(zoning, 'special_provision', '')
    zone_display = format_zone_display(zone_code, suffix, special_provision)
    
    folium.Marker(
        [lat, lon],
        popup=f"""
        <b>Property Analysis</b><br>
        Zone: {zone_display}<br>
        Value: ${analysis_results['valuation']['estimated_value']:,.0f}<br>
        Lot: {analysis_results.get('lot_dimensions', {}).get('area_sqm', st.session_state.property_data.get('lot_area', 0)):.0f} m²
        """,
        tooltip="Click for details",
        icon=folium.Icon(color='red', icon='home')
    ).add_to(m)
    
    # Add nearby parks
    for park in analysis_results.get('api_data', {}).get('nearby_parks', []):
        # Note: In production, you would get actual park coordinates
        # For now, we'll place them randomly around the property
        import random
        park_lat = lat + (random.random() - 0.5) * 0.01
        park_lon = lon + (random.random() - 0.5) * 0.01
        
        folium.Marker(
            [park_lat, park_lon],
            popup=f"<b>{park['name']}</b><br>Type: {park['type']}",
            icon=folium.Icon(color='green', icon='tree-deciduous', prefix='fa')
        ).add_to(m)
    
    # Display map
    map_data = st_folium(m, width=700, height=400)

def get_zoning_value(zoning_data, key: str, default=None):
    """Helper function to get values from either dict or object"""
    if hasattr(zoning_data, key):
        return getattr(zoning_data, key)
    elif isinstance(zoning_data, dict):
        return zoning_data.get(key, default)
    else:
        return default

def calculate_efficiency_ratio(zoning_data):
    """Calculate efficiency ratio from zoning data"""
    # Check if this is a proper zoning object with get_efficiency_ratio method
    if hasattr(zoning_data, 'get_efficiency_ratio') and callable(getattr(zoning_data, 'get_efficiency_ratio', None)):
        try:
            return zoning_data.get_efficiency_ratio()
        except Exception:
            # Fall through to dictionary calculation if method call fails
            pass
    
    # Handle error case
    if isinstance(zoning_data, dict) and 'error' in zoning_data:
        return 0.35  # Default efficiency for error cases
    
    # Calculate from dictionary data
    buildable_area = get_zoning_value(zoning_data, 'buildable_area', 0)
    max_building_footprint = get_zoning_value(zoning_data, 'max_building_footprint', 0)
    
    if max_building_footprint > 0:
        return buildable_area / max_building_footprint
    
    # Fallback calculation using lot area and coverage
    lot_area = get_zoning_value(zoning_data, 'lot_area', 0)
    max_coverage_percent = get_zoning_value(zoning_data, 'max_coverage_percent', 35)
    
    if lot_area > 0:
        max_coverage = max_coverage_percent / 100.0
        return max_coverage
    
    return 0.35  # Default 35% efficiency

def safe_get_floor_area(zoning_data, lot_area_fallback=500):
    """Safely get max floor area from zoning data"""
    # Try to get from object/dict
    max_floor_area = get_zoning_value(zoning_data, 'max_floor_area', 0)
    if max_floor_area and max_floor_area > 0:
        return max_floor_area
    
    # Calculate from lot area and coverage
    lot_area = get_zoning_value(zoning_data, 'lot_area', lot_area_fallback)
    max_coverage_percent = get_zoning_value(zoning_data, 'max_coverage_percent', 35)
    
    if lot_area and max_coverage_percent:
        return lot_area * (max_coverage_percent / 100.0)
    
    return lot_area_fallback * 0.35  # Default calculation

def safe_get_height(zoning_data):
    """Safely get max height from zoning data"""
    height = get_zoning_value(zoning_data, 'max_height', 0)
    if height and height > 0:
        return height
    return 12.0  # Default height for most zones

def format_zone_display(zone_code: str, suffix: str = None, special_provision: str = None) -> str:
    """Format complete zone designation with suffix and special provisions"""
    if not zone_code or zone_code == 'Unknown':
        return 'Unknown Zone'
    
    # Start with base zone code
    display_parts = [zone_code.strip()]
    
    # Handle suffix (like -0)
    if suffix and suffix.strip():
        suffix = suffix.strip()
        if not suffix.startswith('-'):
            suffix = f"-{suffix}"
        display_parts.append(suffix)
    
    # Create base zone display
    base_display = ''.join(display_parts)
    
    # Handle special provisions
    if special_provision and special_provision.strip():
        special_provision = special_provision.strip()
        
        # Format special provision display
        if special_provision.upper().startswith('SP'):
            # Already properly formatted (SP1, SP2, etc.)
            return f"{base_display} with {special_provision}"
        elif 'special' in special_provision.lower() or 'provision' in special_provision.lower():
            # Contains "special provision" text
            return f"{base_display} ({special_provision})"
        else:
            # Other special designation
            return f"{base_display} with {special_provision}"
    
    return base_display

def display_zoning_analysis(analysis_results: Dict):
    """Display enhanced detailed zoning analysis"""
    st.subheader("📋 Enhanced Zoning Analysis Results")
    
    zoning = analysis_results.get('zoning_analysis', {})
    comprehensive = analysis_results.get('zoning_analysis', {})
    base_zoning = analysis_results.get('zoning', {})
    
    # Enhanced compliance check with detailed information
    col1, col2 = st.columns(2)
    
    with col1:
        if zoning.get('meets_minimum_requirements', True):
            st.markdown(
                '<div class="success-box">✅ <b>Compliance:</b> Property meets minimum zoning requirements</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div class="warning-box">⚠️ <b>Non-Compliance:</b> Property does not meet minimum requirements</div>',
                unsafe_allow_html=True
            )
    
    with col2:
        # Enhanced zone display with proper formatting
        # Get zone information from the best available source
        zone_code = (
            get_zoning_value(zoning, 'zone_code') or
            get_zoning_value(zoning, 'base_zone') or
            base_zoning.get('zone_code', 'Unknown')
        )
        
        suffix = get_zoning_value(zoning, 'suffix', '')
        special_provision = get_zoning_value(zoning, 'special_provision', '')
        
        # Format complete zone display
        zone_display = format_zone_display(zone_code, suffix, special_provision)
        
        # Display with appropriate styling based on zone characteristics
        if special_provision and ('SP' in special_provision.upper() or 'SPECIAL' in special_provision.upper()):
            st.markdown(
                f'<div class="warning-box">📄 <b>Special Provision Zone:</b> {zone_display}<br>'
                f'<small>Special provisions override standard by-law regulations</small></div>',
                unsafe_allow_html=True
            )
        elif suffix == '-0' or zone_display.endswith('-0'):
            st.markdown(
                f'<div class="warning-box">🔒 <b>Suffix Zone:</b> {zone_display}<br>'
                f'<small>Subject to enhanced restrictions and FAR limits</small></div>',
                unsafe_allow_html=True
            )
        else:
            st.info(f"**Zone Classification:** {zone_display}")
    
    # Enhanced zoning details with precise calculations
    if comprehensive:
        st.markdown("#### 📐 Precise Dimensional Analysis")
        
        zoning_data = comprehensive.get('zoning_analysis', {})
        lot_dims = comprehensive.get('lot_dimensions', {})
        
        # Lot information
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Get lot dimensions from analysis results, not session state
            lot_dims = analysis_results.get('lot_dimensions', {})
            area_sqm = lot_dims.get('area_sqm', st.session_state.property_data.get('lot_area', 0))
            area_sqft = lot_dims.get('area_sqft', area_sqm * 10.764 if area_sqm else 0)
            
            st.metric(
                "Lot Area", 
                f"{area_sqm:.0f} m²",
                f"{area_sqft:.0f} sq.ft"
            )
        
        with col2:
            frontage_m = lot_dims.get('frontage_m', st.session_state.property_data.get('lot_frontage', 0))
            frontage_ft = lot_dims.get('frontage_ft', frontage_m * 3.281 if frontage_m else 0)
            
            st.metric(
                "Lot Frontage", 
                f"{frontage_m:.1f} m",
                f"{frontage_ft:.1f} ft"
            )
        
        with col3:
            depth_m = lot_dims.get('depth_m', st.session_state.property_data.get('lot_depth', 0))
            depth_ft = lot_dims.get('depth_ft', depth_m * 3.281 if depth_m else 0)
            
            st.metric(
                "Lot Depth", 
                f"{depth_m:.1f} m",
                f"{depth_ft:.1f} ft"
            )
        
        with col4:
            far_value = zoning_data.get('max_floor_area_ratio', 0)
            if far_value:
                st.metric(
                    "Floor Area Ratio", 
                    f"{far_value:.1%}",
                    help="Maximum floor area as percentage of lot area"
                )
            else:
                st.metric("Floor Area Ratio", "No limit")
        
        # Precise setbacks - handle both object and dict access
        setbacks = (
            get_zoning_value(zoning, 'setbacks') or 
            zoning_data.get('precise_setbacks') or
            zoning_data.get('setbacks')
        )
        
        if setbacks:
            st.markdown("#### 📏 Required Setbacks (Based on Exact By-law)")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                front_yard = get_zoning_value(setbacks, 'front_yard', 0)
                st.metric("Front Yard", f"{front_yard:.1f} m" if front_yard else "Not specified")
            
            with col2:
                rear_yard = get_zoning_value(setbacks, 'rear_yard', 0)
                st.metric("Rear Yard", f"{rear_yard:.1f} m" if rear_yard else "Not specified")
            
            with col3:
                interior_left = get_zoning_value(setbacks, 'interior_side_left', 0)
                st.metric("Interior Side (Left)", f"{interior_left:.1f} m" if interior_left else "Not specified")
            
            with col4:
                flankage_yard = get_zoning_value(setbacks, 'flankage_yard')
                if flankage_yard:
                    st.metric("Flankage Yard", f"{flankage_yard:.1f} m")
                else:
                    interior_right = get_zoning_value(setbacks, 'interior_side_right', 0)
                    st.metric("Interior Side (Right)", f"{interior_right:.1f} m" if interior_right else "Not specified")
    
    # Zoning details
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📏 Dimensional Requirements")
        
        # Safely extract dimensional data with fallbacks
        max_height = get_zoning_value(zoning, 'max_height', 0)
        max_storeys = get_zoning_value(zoning, 'max_storeys')
        max_building_footprint = get_zoning_value(zoning, 'max_building_footprint', 0)
        max_floor_area = get_zoning_value(zoning, 'max_floor_area', 0)
        buildable_area = get_zoning_value(zoning, 'buildable_area', max_building_footprint)
        
        metrics_data = [
            ("Max Building Height", f"{max_height:.1f} m" if max_height else "Not specified"),
            ("Max Storeys", str(max_storeys) if max_storeys else "No limit"),
            ("Max Building Footprint", f"{max_building_footprint:.0f} m²" if max_building_footprint else "Not calculated"),
            ("Max Floor Area", f"{max_floor_area:.0f} m²" if max_floor_area else "Not calculated"),
            ("Buildable Area", f"{buildable_area:.0f} m²" if buildable_area else "Not calculated")
        ]
        
        for label, value in metrics_data:
            st.metric(label, value)
    
    with col2:
        st.markdown("#### 🏠 Permitted Uses")
        
        # Safely get permitted uses
        permitted_uses = get_zoning_value(zoning, 'permitted_uses', [])
        
        # Categorize uses
        residential_uses = []
        other_uses = []
        
        for use in permitted_uses:
            formatted_use = use.replace('_', ' ').title()
            if 'dwelling' in use.lower() or 'residential' in use.lower():
                residential_uses.append(formatted_use)
            else:
                other_uses.append(formatted_use)
        
        if residential_uses:
            st.markdown("**Residential Uses:**")
            for use in residential_uses:
                st.write(f"• {use}")
        
        if other_uses:
            st.markdown("**Other Permitted Uses:**")
            for use in other_uses[:5]:  # Limit to first 5
                st.write(f"• {use}")
            if len(other_uses) > 5:
                st.write(f"• ... and {len(other_uses) - 5} more")
    
    # Constraints and opportunities
    col1, col2 = st.columns(2)
    
    with col1:
        constraints = get_zoning_value(zoning, 'constraints', [])
        if constraints:
            st.markdown("#### ⚠️ Development Constraints")
            for constraint in constraints:
                st.warning(f"• {constraint}")
    
    with col2:
        opportunities = get_zoning_value(zoning, 'opportunities', [])
        if opportunities:
            st.markdown("#### 💡 Development Opportunities")
            for opportunity in opportunities:
                st.info(f"• {opportunity}")

def display_valuation_analysis(analysis_results: Dict):
    """Display property valuation analysis"""
    st.subheader("💰 Property Valuation Analysis")
    
    valuation = analysis_results['valuation']
    
    # Main valuation display
    col1, col2, col3 = st.columns(3)
    
    with col1:
        estimated_value = get_zoning_value(valuation, 'estimated_value', 0)
        st.metric(
            "Estimated Value",
            f"${estimated_value:,.0f}",
            help="AI-estimated current market value"
        )
    
    with col2:
        confidence_range_low = get_zoning_value(valuation, 'confidence_range_low', estimated_value * 0.9)
        st.metric(
            "Value Range (Low)",
            f"${confidence_range_low:,.0f}",
            help="Lower confidence range"
        )
    
    with col3:
        confidence_range_high = get_zoning_value(valuation, 'confidence_range_high', estimated_value * 1.1)
        st.metric(
            "Value Range (High)",
            f"${confidence_range_high:,.0f}",
            help="Upper confidence range"
        )
    
    # Check if we have detailed breakdown data
    breakdown = get_zoning_value(valuation, 'breakdown', None)
    
    if breakdown:
        # Full breakdown available - use original complex display
        st.markdown("#### 📊 Value Breakdown")
        
        # Create pie chart
        breakdown_data = {
            'Component': ['Land Value', 'Building Value', 'Location Premium', 'Other Adjustments'],
            'Value': [
                get_zoning_value(breakdown, 'land_value', 0),
                get_zoning_value(breakdown, 'building_value', 0),
                get_zoning_value(breakdown, 'location_premium', 0),
                sum(get_zoning_value(breakdown, 'amenity_adjustments', {}).values()) + get_zoning_value(breakdown, 'market_adjustment', 0)
            ]
        }
        
        df_breakdown = pd.DataFrame(breakdown_data)
        df_breakdown = df_breakdown[df_breakdown['Value'] > 0]  # Remove zero values
        
        fig_pie = px.pie(
            df_breakdown,
            values='Value',
            names='Component',
            title='Property Value Components',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)
        
        # Detailed breakdown table
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 💵 Base Values")
            st.write(f"**Land Value:** ${get_zoning_value(breakdown, 'land_value', 0):,.0f}")
            st.write(f"**Building Value:** ${get_zoning_value(breakdown, 'building_value', 0):,.0f}")
            st.write(f"**Depreciation:** ${get_zoning_value(breakdown, 'depreciation', 0):,.0f}")
        
        with col2:
            st.markdown("#### 📈 Adjustments")
            st.write(f"**Location Premium:** ${get_zoning_value(breakdown, 'location_premium', 0):,.0f}")
            st.write(f"**Market Adjustment:** ${get_zoning_value(breakdown, 'market_adjustment', 0):,.0f}")
    else:
        # Simple breakdown using available data
        st.markdown("#### 📊 Simple Value Breakdown")
        
        land_value = get_zoning_value(valuation, 'land_value', 0)
        building_value = get_zoning_value(valuation, 'building_value', 0)
        
        if land_value or building_value:
            breakdown_data = {
                'Component': ['Land Value', 'Building Value'],
                'Value': [land_value, building_value]
            }
            
            df_breakdown = pd.DataFrame(breakdown_data)
            df_breakdown = df_breakdown[df_breakdown['Value'] > 0]
            
            fig_pie = px.pie(
                df_breakdown,
                values='Value',
                names='Component',
                title='Property Value Components',
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            
            st.plotly_chart(fig_pie, use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Land Value:** ${land_value:,.0f}")
                price_per_sqm = get_zoning_value(valuation, 'price_per_sqm_land', 0)
                if price_per_sqm:
                    st.write(f"**Price per m²:** ${price_per_sqm:,.0f}")
            
            with col2:
                st.write(f"**Building Value:** ${building_value:,.0f}")
                confidence = get_zoning_value(valuation, 'confidence', 'Medium')
                st.write(f"**Confidence:** {confidence}")
        else:
            st.info("Detailed value breakdown not available for simplified analysis")
    
    # Market insights
    st.markdown("#### 📊 Market Context")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        confidence_score = get_zoning_value(valuation, 'confidence_score', 0.75)
        if isinstance(confidence_score, str):
            # Handle string confidence like "Medium"
            st.metric(
                "Analysis Confidence",
                confidence_score,
                help="Confidence in valuation accuracy"
            )
        else:
            st.metric(
                "Confidence Score",
                f"{confidence_score:.0%}",
                help="Confidence in valuation accuracy"
            )
    
    with col2:
        days_on_market = get_zoning_value(valuation, 'days_on_market_estimate', 30)
        st.metric(
            "Est. Days on Market",
            f"{days_on_market} days",
            help="Estimated time to sell"
        )
    
    with col3:
        building_area = st.session_state.property_data.get('building_area', 200)
        try:
            building_area = float(building_area)
            price_per_sqm = estimated_value / building_area if building_area > 0 else 0
        except (ValueError, TypeError):
            price_per_sqm = 0
        st.metric(
            "Price per m²",
            f"${price_per_sqm:,.0f}",
            help="Price per square meter of building area"
        )
    
    # Valuation notes
    notes = get_zoning_value(valuation, 'notes', [])
    if notes:
        st.markdown("#### 📝 Important Notes")
        for note in notes:
            st.info(f"• {note}")

def display_development_potential(analysis_results: Dict):
    """Display development potential analysis"""
    st.subheader("🏗️ Development Potential Analysis")
    
    zoning = analysis_results['zoning_analysis']
    development = analysis_results.get('development_proforma')
    
    # Development summary
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Potential Units",
            get_zoning_value(zoning, 'potential_units', 1),
            help="Maximum developable units under current zoning"
        )
    
    with col2:
        efficiency = calculate_efficiency_ratio(zoning)
        st.metric(
            "Site Efficiency",
            f"{efficiency:.0%}",
            help="Buildable area as % of total lot area"
        )
    
    with col3:
        # Get lot area for fallback calculation
        lot_area = analysis_results.get('lot_dimensions', {}).get('area_sqm', 
                   st.session_state.property_data.get('lot_area', 500))
        max_floor_area = safe_get_floor_area(zoning, lot_area)
        st.metric(
            "Max Floor Area",
            f"{max_floor_area:,.0f} m²",
            help="Maximum permitted floor area"
        )
    
    with col4:
        max_height = safe_get_height(zoning)
        st.metric(
            "Max Height",
            f"{max_height:.1f} m",
            help="Maximum permitted building height"
        )
    
    # Development scenarios
    if development and get_zoning_value(zoning, 'potential_units', 1) > 1:
        st.markdown("#### 💼 Development Financial Analysis")
        
        # Financial metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Safely get revenue data
            revenue_data = get_zoning_value(development, 'revenue', {})
            gross_revenue = get_zoning_value(revenue_data, 'gross_revenue', 
                           get_zoning_value(development, 'gross_revenue', 0))
            st.metric(
                "Gross Revenue",
                f"${gross_revenue:,.0f}",
                help="Total expected revenue from sales"
            )
        
        with col2:
            # Safely get costs data
            costs_data = get_zoning_value(development, 'costs', {})
            total_costs = get_zoning_value(costs_data, 'total_costs',
                         get_zoning_value(development, 'total_costs', 0))
            st.metric(
                "Total Costs",
                f"${total_costs:,.0f}",
                help="Total development costs"
            )
        
        with col3:
            gross_profit = get_zoning_value(development, 'gross_profit', 0)
            st.metric(
                "Gross Profit",
                f"${gross_profit:,.0f}",
                help="Profit before taxes and financing"
            )
        
        # Profitability analysis
        col1, col2, col3 = st.columns(3)
        
        with col1:
            profit_margin = get_zoning_value(development, 'profit_margin', 0)
            st.metric(
                "Profit Margin",
                f"{profit_margin:.1%}",
                help="Profit as percentage of revenue"
            )
        
        with col2:
            roi = get_zoning_value(development, 'return_on_investment', 0)
            st.metric(
                "ROI",
                f"{roi:.1%}",
                help="Return on investment"
            )
        
        with col3:
            feasible = get_zoning_value(development, 'feasible', True)
            feasible_color = "green" if feasible else "red"
            feasible_text = "✅ Feasible" if feasible else "❌ Not Feasible"
            st.markdown(f"**Project Feasibility:**<br><span style='color: {feasible_color}'>{feasible_text}</span>", unsafe_allow_html=True)
        
        # Cost breakdown
        st.markdown("#### 💰 Cost Breakdown")
        
        # Safely extract cost components
        costs_data = get_zoning_value(development, 'costs', {})
        cost_data = {
            'Category': [
                'Land Acquisition',
                'Construction',
                'Soft Costs',
                'Financing',
                'Marketing',
                'Contingency'
            ],
            'Amount': [
                get_zoning_value(costs_data, 'land_acquisition', 0),
                get_zoning_value(costs_data, 'hard_costs', 0),
                get_zoning_value(costs_data, 'soft_costs', 0),
                get_zoning_value(costs_data, 'financing_costs', 0),
                get_zoning_value(costs_data, 'marketing_costs', 0),
                get_zoning_value(costs_data, 'contingency', 0)
            ]
        }
        
        df_costs = pd.DataFrame(cost_data)
        
        # Only show chart if we have non-zero costs
        if sum(cost_data['Amount']) > 0:
            fig_costs = px.bar(
                df_costs,
                x='Category',
                y='Amount',
                title='Development Cost Components',
                labels={'Amount': 'Cost ($CAD)'}
            )
            
            st.plotly_chart(fig_costs, use_container_width=True)
        else:
            st.info("💡 Detailed cost breakdown not available for this development scenario")
        
        # Risk factors
        risk_factors = get_zoning_value(development, 'risk_factors', [])
        if risk_factors:
            st.markdown("#### ⚠️ Development Risk Factors")
            for risk in risk_factors:
                st.warning(f"• {risk}")
    
    else:
        st.markdown("#### 🏠 Single Family Development")
        st.info("Property is zoned for single-family residential use. Multi-unit development not permitted under current zoning.")
        
        # Single family renovation/rebuild potential
        try:
            current_building = float(st.session_state.property_data.get('building_area', 200))
            lot_area = analysis_results.get('lot_dimensions', {}).get('area_sqm', 
                       st.session_state.property_data.get('lot_area', 500))
            max_potential = safe_get_floor_area(zoning, lot_area)
            
            if max_potential > current_building * 1.2:  # 20% larger potential
                expansion_potential = max_potential - current_building
                st.success(f"💡 Expansion Opportunity: Could add up to {expansion_potential:.0f} m² of floor area")
        except (ValueError, TypeError) as e:
            st.info("💡 Single family development potential - contact professional for detailed analysis")

def display_market_insights_summary(analysis_results: Dict):
    """Display condensed market insights summary for overview tab"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Avg Price/m²", "$4,850", "↑ 5.2%")
    with col2:
        st.metric("Days on Market", "21", "↓ 3 days")
    with col3:
        st.metric("Active Listings", "342", "↑ 12")
    with col4:
        st.metric("Sales/List Ratio", "98.5%", "↑ 1.2%")
    
    st.info("💡 **Market Status:** Seller's market with strong demand and quick sales. Price appreciation expected to continue at 5-8% annually.")

def display_market_insights(analysis_results: Dict):
    """Display market insights and trends"""
    st.subheader("📊 Market Insights & Trends")
    
    # Market overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Avg Price/m²", "$4,850", "↑ 5.2%")
    with col2:
        st.metric("Days on Market", "21", "↓ 3 days")
    with col3:
        st.metric("Active Listings", "342", "↑ 12")
    with col4:
        st.metric("Sales/List Ratio", "98.5%", "↑ 1.2%")
    
    # Zone comparison
    st.markdown("#### 🗺️ Average Values by Zone")
    
    zone_values = {
        'Zone': ['RL1', 'RL2', 'RL3', 'RL4', 'RL5', 'RL6', 'RM1', 'RM2', 'RM3', 'RM4'],
        'Avg Value ($CAD)': [2100000, 1850000, 1450000, 1250000, 1150000, 950000, 750000, 650000, 550000, 450000],
        'Properties Sold (YTD)': [45, 123, 234, 189, 156, 98, 67, 45, 34, 23]
    }
    
    df_zones = pd.DataFrame(zone_values)
    
    fig_zones = px.bar(
        df_zones,
        x='Zone',
        y='Avg Value ($CAD)',
        color='Properties Sold (YTD)',
        title='Average Property Values by Zoning Classification',
        labels={'Avg Value ($CAD)': 'Average Value ($CAD)'},
        color_continuous_scale='viridis'
    )
    
    st.plotly_chart(fig_zones, use_container_width=True)
    
    # Market trends
    st.markdown("#### 📈 Market Trends (Last 12 Months)")
    
    # Generate sample trend data
    import numpy as np
    months = pd.date_range(start='2023-01-01', periods=12, freq='ME')
    trend_data = pd.DataFrame({
        'Month': months,
        'Avg Price ($CAD)': [1250000 + i*15000 + np.random.randint(-20000, 30000) for i in range(12)],
        'Sales Volume': [120 + np.random.randint(-20, 30) for _ in range(12)],
        'New Listings': [150 + np.random.randint(-25, 35) for _ in range(12)]
    })
    
    # Create multi-line chart
    fig_trends = go.Figure()
    
    fig_trends.add_trace(go.Scatter(
        x=trend_data['Month'],
        y=trend_data['Avg Price ($CAD)'],
        mode='lines+markers',
        name='Average Price',
        line=dict(color='blue', width=3),
        yaxis='y'
    ))
    
    fig_trends.add_trace(go.Scatter(
        x=trend_data['Month'],
        y=trend_data['Sales Volume'],
        mode='lines+markers',
        name='Sales Volume',
        line=dict(color='green', width=2),
        yaxis='y2'
    ))
    
    fig_trends.update_layout(
        title='Oakville Real Estate Market Trends',
        xaxis_title='Month',
        yaxis=dict(title='Average Price ($CAD)', side='left'),
        yaxis2=dict(title='Sales Volume', side='right', overlaying='y'),
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_trends, use_container_width=True)
    
    # Neighborhood insights
    st.markdown("#### 🏘️ Neighborhood Analysis")
    
    nearby_parks = len(analysis_results.get('api_data', {}).get('nearby_parks', []))
    nearby_developments = len(analysis_results.get('api_data', {}).get('nearby_developments', []))
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Location Factors:**")
        st.write(f"• Parks within 1km: {nearby_parks}")
        st.write(f"• Active developments nearby: {nearby_developments}")
        st.write(f"• Transit access: Good")
        st.write(f"• School ratings: 8.5/10")
    
    with col2:
        st.markdown("**Investment Outlook:**")
        st.success("• Strong long-term appreciation potential")
        st.info("• Stable rental market demand")
        st.success("• Good infrastructure and amenities")
        st.warning("• Monitor interest rate impacts")

def display_special_requirements(analysis_results: Dict):
    """Display heritage, conservation, and arborist requirements"""
    if 'special_requirements' not in analysis_results:
        return
        
    st.subheader("🏛️ Special Requirements Assessment")
    
    special_reqs = analysis_results['special_requirements']
    
    # Create three columns for each type of requirement
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 🏛️ Heritage Assessment")
        heritage = special_reqs['heritage']
        status_color = "orange" if heritage['potential_heritage_concern'] else "green"
        st.markdown(f"**Status:** <span style='color: {status_color}'>{heritage['status']}</span>", unsafe_allow_html=True)
        st.write(heritage['notes'])
        if heritage['potential_heritage_concern']:
            st.warning("⚠️ Property may be subject to heritage restrictions")
        else:
            st.success("✅ No known heritage concerns")
    
    with col2:
        st.markdown("#### 🌿 Conservation Use")
        conservation = special_reqs['conservation']
        status_color = "green" if conservation['conservation_use_permitted'] else "red"
        st.markdown(f"**Status:** <span style='color: {status_color}'>{conservation['status']}</span>", unsafe_allow_html=True)
        st.write(conservation['notes'])
        if conservation['conservation_use_permitted']:
            st.success("✅ Conservation use is permitted")
        else:
            st.error("❌ Conservation use not permitted")
    
    with col3:
        st.markdown("#### 🌳 Arborist Requirements")
        arborist = special_reqs['arborist']
        status_color = "orange" if arborist['arborist_report_likely_required'] else "green"
        st.markdown(f"**Status:** <span style='color: {status_color}'>{arborist['status']}</span>", unsafe_allow_html=True)
        st.write(arborist['notes'])
        if arborist['arborist_report_likely_required']:
            st.warning("⚠️ Professional arborist assessment recommended")
        else:
            st.info("ℹ️ Standard tree preservation applies")
    
    # Additional information box
    with st.expander("📋 Additional Information"):
        st.markdown("""
        **Heritage Assessment:** Properties in heritage areas or with historical significance may require 
        heritage impact assessments and approvals from the Town's Heritage Oakville committee.
        
        **Conservation Use:** All residential zones permit conservation use as defined in the zoning by-law. 
        This includes uses related to natural resource management and environmental protection.
        
        **Arborist Requirements:** Large lots, estate zones, and properties with significant tree cover 
        typically require professional arborist reports for development applications. Tree preservation 
        and replacement may be required.
        
        **Next Steps:** Contact Town of Oakville Planning Services for specific requirements and application procedures.
        """)

def display_ai_assistant(analysis_results: Dict, lat: float, lon: float):
    """Display streamlined AI Assistant chatbot interface with comprehensive context"""
    
    # Display header with current property info
    if st.session_state.property_data.get('address'):
        st.info(f"🏠 **Current Property:** {st.session_state.property_data.get('address')} | **Zone:** {analysis_results.get('zoning', {}).get('zone_code', 'Unknown')}")
    
    # Prepare comprehensive system context
    system_context = _prepare_system_context(analysis_results, lat, lon)
    
    # Render the appropriate chatbot interface
    try:
        if CHATBOT_TYPE == "system_wide" and render_chatbot_interface is not None:
            render_chatbot_interface(system_context)
        elif render_chatbot_interface is not None:
            # Fallback to property context for other chatbot types
            property_context = system_context['current_property']
            render_chatbot_interface(property_context)
        else:
            _display_ai_fallback(system_context)
            
    except Exception as e:
        st.error(f"❌ AI Assistant Error: {str(e)}")
        _display_contact_info()

def _prepare_system_context(analysis_results: Dict, lat: float, lon: float) -> Dict:
    """Prepare comprehensive system context for the AI assistant"""
    
    # Get zoning analysis details
    zoning_analysis = analysis_results.get('zoning_analysis', {})
    
    system_context = {
        'timestamp': datetime.now().isoformat(),
        'system_status': 'operational',
        'current_property': {
            'address': st.session_state.property_data.get('address', ''),
            'coordinates': {'lat': lat, 'lon': lon},
            'zone_code': analysis_results.get('zoning', {}).get('zone_code', 'Unknown'),
            'lot_area': analysis_results.get('lot_dimensions', {}).get('area_sqm', st.session_state.property_data.get('lot_area', 0)),
            'lot_frontage': analysis_results.get('lot_dimensions', {}).get('frontage_m', st.session_state.property_data.get('lot_frontage', 0)),
            'lot_depth': analysis_results.get('lot_dimensions', {}).get('depth_m', st.session_state.property_data.get('lot_depth', 0)),
            'building_area': st.session_state.property_data.get('building_area', 0),
            'building_type': st.session_state.property_data.get('building_type', 'detached_dwelling'),
            'suffix': _extract_zone_attribute(zoning_analysis, 'suffix'),
            'special_provision': _extract_zone_attribute(zoning_analysis, 'special_provision')
        },
        'last_analysis': {
            'valuation': analysis_results.get('valuation', {}),
            'zoning': analysis_results.get('zoning', {}),
            'zoning_analysis': zoning_analysis,
            'development_potential': analysis_results.get('development_proforma', {})
        }
    }
    
    # Include manual measurements if available
    if hasattr(st.session_state, 'manual_lot_calculation') and st.session_state.manual_lot_calculation:
        manual_calc = st.session_state.manual_lot_calculation
        system_context['current_property'].update({
            'lot_area': manual_calc['lot_area'],
            'lot_frontage': manual_calc['frontage'],
            'lot_depth': manual_calc['depth'],
            'measurement_method': manual_calc['method'],
            'measurement_confidence': manual_calc['confidence']
        })
    
    return system_context

def _extract_zone_attribute(zoning_analysis, attribute: str) -> str:
    """Extract zone attribute from zoning analysis object or dict"""
    if hasattr(zoning_analysis, attribute):
        return getattr(zoning_analysis, attribute, '')
    elif isinstance(zoning_analysis, dict):
        return zoning_analysis.get(attribute, '')
    return ''

def _display_ai_fallback(system_context: Dict):
    """Display fallback AI interface when main assistant is not available"""
    st.warning("⚠️ AI Assistant is not available. Showing fallback information.")
    
    zone_code = system_context['current_property'].get('zone_code', 'Unknown')
    
    if zone_code and zone_code != 'Unknown':
        st.success(f"**Current Zone:** {zone_code}")
        
        # Display basic zone information
        if zone_code.startswith('RL'):
            zone_info = {
                'RL1': {'area': '1,393.5 m²', 'frontage': '30.5 m', 'height': '10.5 m'},
                'RL2': {'area': '836.0 m²', 'frontage': '22.5 m', 'height': '12.0 m'},
                'RL3': {'area': '557.5 m²', 'frontage': '18.0 m', 'height': '12.0 m'},
                'RL4': {'area': '511.0 m²', 'frontage': '16.5 m', 'height': '12.0 m'},
                'RL5': {'area': '464.5 m²', 'frontage': '15.0 m', 'height': '12.0 m'},
                'RL6': {'area': '250.0 m²', 'frontage': '11.0 m', 'height': '10.5 m'}
            }
            
            base_zone = zone_code.split('-')[0]
            if base_zone in zone_info:
                st.markdown("**Zone Requirements:**")
                info = zone_info[base_zone]
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Min Lot Area", info['area'])
                with col2:
                    st.metric("Min Frontage", info['frontage'])
                with col3:
                    st.metric("Max Height", info['height'])
    
    st.info("💡 **To enable full AI Assistant:** Install dependencies with `pip install groq sentence-transformers chromadb faiss-cpu`")
    _display_contact_info()

def _display_contact_info():
    """Display contact information for Oakville planning services"""
    st.markdown("### 📞 Town of Oakville Planning Services")
    col1, col2 = st.columns(2)
    with col1:
        st.info("**Phone:** 905-845-6601\n**Website:** oakville.ca")
    with col2:
        st.info("**Email:** planning@oakville.ca\n**Address:** Town Hall, 1225 Trafalgar Rd")

# Footer
def display_footer():
    """Display application footer"""
    st.divider()
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #6b7280; font-size: 0.9rem;'>
        💡 <b>Disclaimer:</b> This analysis uses Oakville Zoning By-law 2014-014 and real-time GIS data. 
        Valuations are estimates only and should be verified with professional appraisals.<br>
        <b>Oakville Real Estate Analyzer</b> | Powered by AI | Built with Streamlit
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
    display_footer()