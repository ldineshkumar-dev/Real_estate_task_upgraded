"""
Simple, reliable analysis functions that won't hang
Enhanced with automatic property dimension fetching
"""

# Property dimensions will be imported dynamically when needed

def check_heritage_conservation_arborist(lat: float, lon: float, property_data: dict, zone_code: str) -> dict:
    """Check heritage, conservation, and arborist requirements"""
    
    # Conservation use is permitted in all residential zones according to the zoning by-law
    conservation_permitted = zone_code.startswith('RL') or zone_code.startswith('RM') or zone_code == 'RH' or zone_code == 'RUC'
    
    # Basic heritage check - properties near Old Oakville might have heritage concerns
    address = property_data.get('address', '').lower()
    heritage_concern = any(keyword in address for keyword in [
        'lakeshore', 'ontario', 'navy', 'trafalgar', 'kerr', 'randall', 'robinson'
    ]) or (lat > 43.44 and lat < 43.47 and lon > -79.71 and lon < -79.68)
    
    # Arborist requirements - larger lots or specific zones may require tree preservation
    try:
        lot_area = float(property_data.get('lot_area', 0))
    except (ValueError, TypeError):
        lot_area = 0
    arborist_required = (
        lot_area > 1000 or  # Large lots typically have mature trees
        zone_code in ['RL1', 'RL2'] or  # Larger estate zones
        'ravine' in address or 'creek' in address or 'valley' in address  # Natural features
    )
    
    return {
        'conservation': {
            'conservation_use_permitted': conservation_permitted,
            'status': 'Permitted' if conservation_permitted else 'Not Permitted',
            'notes': 'Conservation use is permitted in all residential zones per zoning by-law'
        },
        'heritage': {
            'potential_heritage_concern': heritage_concern,
            'status': 'Heritage Assessment Recommended' if heritage_concern else 'No Known Heritage Concerns',
            'notes': 'Properties in Old Oakville core area may have heritage designations'
        },
        'arborist': {
            'arborist_report_likely_required': arborist_required,
            'status': 'Arborist Report Required' if arborist_required else 'Standard Tree Preservation',
            'notes': 'Large lots and estate zones typically require professional tree assessment'
        }
    }

def enhance_property_data_with_api(lat: float, lon: float, property_data: dict) -> dict:
    """
    Enhance property data - RESPECTS manual measurements, only adds zoning data from APIs
    
    Args:
        lat: Latitude
        lon: Longitude  
        property_data: User-provided property data (may include manual measurements)
        
    Returns:
        Enhanced property data with zoning info from APIs but preserving manual measurements
    """
    enhanced_data = property_data.copy()
    
    # Check if manual measurements are already provided
    has_manual_measurements = property_data.get('manual_measurement_used', False)
    
    if has_manual_measurements:
        print(f"✅ Using manual measurements: Area={property_data.get('lot_area', 'N/A'):.1f}m², Method={property_data.get('area_calculation_method', 'unknown')}")
        # Don't call API for lot dimensions - use manual measurements as-is
        enhanced_data['lot_area_source'] = 'manual_measurement'
        enhanced_data['lot_frontage_source'] = 'manual_measurement'
        enhanced_data['lot_depth_source'] = 'manual_measurement'
        return enhanced_data
    
    # Only enhance with API if no manual measurements provided
    try:
        # Import the new PropertyDimensionsClient
        from backend.property_dimensions_client import PropertyDimensionsClient
        
        # Get dimensions client
        dimensions_client = PropertyDimensionsClient()
        
        # Check if we have manual measurements to pass
        manual_measurements = None
        if property_data.get('lot_frontage') and property_data.get('lot_depth'):
            manual_measurements = {
                'frontage': property_data['lot_frontage'],
                'depth': property_data['lot_depth']
            }
        
        # Get property info with manual measurements if available
        api_result = dimensions_client.get_property_dimensions(
            lat, lon,
            address=property_data.get('address', ''),
            zone_code=property_data.get('zone_code', ''),
            manual_measurements=manual_measurements
        )
        
        # Only use zoning information from API - lot area comes from manual measurements
        if api_result:
            # Add zoning information
            if api_result.get('zone_code'):
                enhanced_data['zone_code'] = api_result['zone_code']
                enhanced_data['zone_code_source'] = 'api'
                
            if api_result.get('zone_class'):
                enhanced_data['zone_class'] = api_result['zone_class']
                
            if api_result.get('special_provisions'):
                enhanced_data['special_provisions'] = api_result['special_provisions']
                
            # Store API response for reference (but don't use lot area from it)
            enhanced_data['api_response_reference'] = api_result
            enhanced_data['api_shape_area_reference'] = api_result.get('raw_api_data', {}).get('area')
            
            # If manual measurements were provided and used
            if manual_measurements and api_result.get('success'):
                enhanced_data['lot_area'] = api_result['lot_area']  # This comes from manual calc
                enhanced_data['lot_frontage'] = api_result['lot_frontage']
                enhanced_data['lot_depth'] = api_result['lot_depth']
                enhanced_data['lot_area_source'] = 'manual_measurement'
                enhanced_data['area_calculation_method'] = 'manual_measurement_frontage_x_depth'
                print(f"✅ Using manual measurements from inputs: {enhanced_data['lot_area']:.1f} m²")
        
        return enhanced_data
        
    except Exception as e:
        print(f"Warning: Could not enhance property data with API: {e}")
        return enhanced_data

def run_simple_analysis(services, lat: float, lon: float, property_data: dict) -> dict:
    """Run fast, reliable property analysis without hanging"""
    import time
    start_time = time.time()
    
    try:
        # Step 0: Enhance property data with API-fetched dimensions
        enhanced_property_data = enhance_property_data_with_api(lat, lon, property_data)
        # Step 1: Get zoning info with timeout
        zoning_info = None
        try:
            if hasattr(services, 'api_client'):
                zoning_info = services.api_client.get_zoning_info(
                    lat, lon, enhanced_property_data.get('address', '')
                )
            else:
                zoning_info = services['api_client'].get_zoning_info(
                    lat, lon, enhanced_property_data.get('address', '')
                )
        except Exception as e:
            print(f"Zoning API failed: {e}")
        
        # Step 2: Determine zone with smart fallback
        if zoning_info and zoning_info.get('zone_code'):
            zone_code = zoning_info['zone_code']
            source = zoning_info.get('source', 'api')
        else:
            # Smart fallback based on address patterns
            address = enhanced_property_data.get('address', '').lower()
            if 'lakeshore' in address:
                zone_code = 'RL2'
            elif 'glen abbey' in address or 'rebecca' in address:
                zone_code = 'RL3'  
            elif 'maplehurst' in address:
                zone_code = 'RL2'
            else:
                zone_code = 'RL3'  # Most common
            source = 'address_pattern'
        
        # Step 3: Basic zoning rules (hardcoded for reliability)
        zone_rules = {
            'RL1': {'max_height': 10.5, 'max_coverage': 0.30, 'min_area': 1393.5, 'description': 'Large Estate Lots'},
            'RL2': {'max_height': 12.0, 'max_coverage': 0.30, 'min_area': 836.0, 'description': 'Large Residential'},
            'RL3': {'max_height': 12.0, 'max_coverage': 0.35, 'min_area': 557.5, 'description': 'Medium Residential'},
            'RL4': {'max_height': 12.0, 'max_coverage': 0.35, 'min_area': 511.0, 'description': 'Medium Residential'},
            'RL5': {'max_height': 12.0, 'max_coverage': 0.35, 'min_area': 464.5, 'description': 'Medium Residential'},
            'RL6': {'max_height': 10.5, 'max_coverage': 0.75, 'min_area': 250.0, 'description': 'Small Lot Residential'}
        }
        
        rules = zone_rules.get(zone_code, zone_rules['RL3'])
        
        # Safely extract numeric values with fallbacks (now using enhanced data)
        try:
            lot_area = float(enhanced_property_data.get('lot_area', 500))
        except (ValueError, TypeError):
            lot_area = 500.0
            
        try:
            lot_frontage = float(enhanced_property_data.get('lot_frontage', 15.0))
        except (ValueError, TypeError):
            lot_frontage = 15.0
            
        try:
            lot_depth = float(enhanced_property_data.get('lot_depth', lot_area / lot_frontage if lot_frontage > 0 else 33.3))
        except (ValueError, TypeError):
            lot_depth = lot_area / lot_frontage if lot_frontage > 0 else 33.3
        
        # Step 4: Calculate development potential
        max_footprint = lot_area * rules['max_coverage']
        complies = lot_area >= rules['min_area']
        
        # Step 5: Simple valuation
        base_values = {'RL1': 5500, 'RL2': 5000, 'RL3': 4800, 'RL4': 4600, 'RL5': 4500, 'RL6': 4200}
        land_value_per_sqm = base_values.get(zone_code, 4500)
        
        land_value = lot_area * land_value_per_sqm
        
        try:
            building_area = float(enhanced_property_data.get('building_area', 200))
        except (ValueError, TypeError):
            building_area = 200.0
            
        building_value = building_area * 2500  # $2500/sqm construction cost
        total_value = (land_value + building_value) * 1.05  # 5% market premium
        
        # Step 6: Heritage, conservation, and arborist checks
        special_requirements = check_heritage_conservation_arborist(lat, lon, enhanced_property_data, zone_code)
        
        # Return results
        return {
            'success': True,
            'processing_time': time.time() - start_time,
            'zoning': {
                'zone_code': zone_code,
                'zone_class': 'Residential Low',
                'description': rules['description'],
                'source': source,
                'special_provision': zoning_info.get('special_provision', '') if zoning_info else ''
            },
            'lot_dimensions': {
                'area_sqm': round(lot_area, 1),
                'area_sqft': round(lot_area * 10.764, 0),  # Convert m² to sq.ft
                'frontage_m': round(lot_frontage, 1),
                'frontage_ft': round(lot_frontage * 3.281, 1),  # Convert m to ft
                'depth_m': round(lot_depth, 1),
                'depth_ft': round(lot_depth * 3.281, 1),  # Convert m to ft
            },
            'zoning_analysis': {
                'max_height': rules['max_height'],
                'max_coverage_percent': rules['max_coverage'] * 100,
                'max_building_footprint': round(max_footprint, 1),
                'complies_min_area': complies,
                'development_potential': 'Excellent' if complies and lot_area > rules['min_area'] * 1.5 else 'Good' if complies else 'Limited',
                'potential_units': 1,  # Single family residential zones allow 1 unit
                'lot_area': round(lot_area, 1),  # Include lot area in zoning analysis
                'lot_frontage': round(lot_frontage, 1),  # Include lot frontage
                'lot_depth': round(lot_depth, 1)  # Include lot depth
            },
            'valuation': {
                'estimated_value': round(total_value, -3),  # Round to nearest thousand
                'land_value': round(land_value),
                'building_value': round(building_value),
                'price_per_sqm_land': round(land_value_per_sqm),
                'confidence': 'Medium - Simplified calculation'
            },
            'special_requirements': special_requirements,
            'coordinates': {'lat': lat, 'lon': lon},
            'property_data': enhanced_property_data,
            'original_property_data': property_data,
            'data_enhancement': {
                'api_enhanced': 'api_dimensions_data' in enhanced_property_data,
                'lot_area_source': enhanced_property_data.get('lot_area_source', 'manual'),
                'frontage_source': enhanced_property_data.get('lot_frontage_source', 'manual'),
                'depth_source': enhanced_property_data.get('lot_depth_source', 'manual')
            }
        }
        
    except Exception as e:
        # Provide fallback values for error case with safe type conversion
        # Try to use enhanced data even in error case
        try:
            enhanced_property_data = enhance_property_data_with_api(lat, lon, property_data)
        except Exception:
            enhanced_property_data = property_data.copy()
            
        try:
            fallback_lot_area = float(enhanced_property_data.get('lot_area', 500))
        except (ValueError, TypeError):
            fallback_lot_area = 500.0
            
        try:
            fallback_lot_frontage = float(enhanced_property_data.get('lot_frontage', 15.0))
        except (ValueError, TypeError):
            fallback_lot_frontage = 15.0
            
        try:
            fallback_lot_depth = float(enhanced_property_data.get('lot_depth', fallback_lot_area / fallback_lot_frontage if fallback_lot_frontage > 0 else 33.3))
        except (ValueError, TypeError):
            fallback_lot_depth = fallback_lot_area / fallback_lot_frontage if fallback_lot_frontage > 0 else 33.3
        
        return {
            'success': False,
            'error': str(e),
            'zoning': {'zone_code': 'RL3', 'zone_class': 'Residential Low', 'source': 'error_fallback'},
            'lot_dimensions': {
                'area_sqm': round(fallback_lot_area, 1),
                'area_sqft': round(fallback_lot_area * 10.764, 0),
                'frontage_m': round(fallback_lot_frontage, 1),
                'frontage_ft': round(fallback_lot_frontage * 3.281, 1),
                'depth_m': round(fallback_lot_depth, 1),
                'depth_ft': round(fallback_lot_depth * 3.281, 1),
            },
            'zoning_analysis': {
                'max_height': 12.0,
                'max_building_footprint': round(fallback_lot_area * 0.35, 1),
                'complies_min_area': True,
                'development_potential': 'Good',
                'potential_units': 1,  # Single family residential fallback
                'lot_area': round(fallback_lot_area, 1),
                'lot_frontage': round(fallback_lot_frontage, 1),
                'lot_depth': round(fallback_lot_depth, 1)
            },
            'valuation': {
                'estimated_value': 2250000,  # Fallback estimate
                'confidence': 'Low - Error fallback'
            },
            'coordinates': {'lat': lat, 'lon': lon},
            'property_data': enhanced_property_data,
            'original_property_data': property_data,
            'data_enhancement': {
                'api_enhanced': 'api_dimensions_data' in enhanced_property_data,
                'error_fallback': True
            }
        }