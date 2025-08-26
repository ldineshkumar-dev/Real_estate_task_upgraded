"""
Precise Manual Point Selection System for Real Estate Property Measurement
User clicks exactly 2 points for frontage and 2 points for depth
Calculates lot area using frontage × depth (rectangular approximation)
"""

import streamlit as st
import folium
from folium import plugins
import json
from typing import List, Tuple, Dict, Optional
import math
from streamlit_folium import st_folium
import pandas as pd
from datetime import datetime

class PrecisePointSelector:
    """
    Precise 2-point selection system for property measurement
    Step-by-step process: 2 points for frontage, then 2 points for depth
    """
    
    def __init__(self):
        self.reset_session()
    
    def reset_session(self):
        """Reset measurement session to initial state"""
        if 'precise_measurement' not in st.session_state:
            st.session_state.precise_measurement = {
                'step': 'frontage',  # 'frontage', 'depth', 'complete'
                'frontage_points': [],
                'depth_points': [],
                'frontage_distance': 0,
                'depth_distance': 0,
                'lot_area': 0,
                'measurements_complete': False
            }
    
    def calculate_haversine_distance(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """
        Calculate accurate distance between two GPS coordinates using Haversine formula
        Returns distance in meters
        """
        lat1, lon1 = point1
        lat2, lon2 = point2
        
        # Earth's radius in meters
        R = 6371000
        
        # Convert degrees to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        # Haversine formula
        a = (math.sin(delta_lat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return distance
    
    def convert_units(self, meters: float) -> Dict[str, float]:
        """Convert meters to various units"""
        return {
            'meters': meters,
            'feet': meters * 3.28084,
            'yards': meters * 1.09361
        }
    
    def create_measurement_map(self, center_lat: float, center_lon: float) -> folium.Map:
        """Create interactive map for precise point selection"""
        
        # Create high-resolution map centered on property
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=19,  # High zoom for precision
            control_scale=True,
            prefer_canvas=True,
            tiles=None  # Start without base tiles
        )
        
        # Add high-resolution tile layers
        folium.TileLayer(
            'OpenStreetMap',
            name='OpenStreetMap',
            overlay=False,
            control=True
        ).add_to(m)
        
        folium.TileLayer(
            'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri World Imagery',
            name='Satellite View',
            overlay=False,
            control=True
        ).add_to(m)
        
        folium.TileLayer(
            'CartoDB positron',
            name='Light Map',
            overlay=False,
            control=True
        ).add_to(m)
        
        # Add layer control
        folium.LayerControl(position='topright').add_to(m)
        
        # Add property center marker
        folium.Marker(
            [center_lat, center_lon],
            popup="Property Center",
            tooltip="Property Location",
            icon=folium.Icon(color='blue', icon='home', prefix='fa')
        ).add_to(m)
        
        # Add existing frontage points if any
        session = st.session_state.precise_measurement
        if session['frontage_points']:
            for i, point in enumerate(session['frontage_points']):
                folium.Marker(
                    point,
                    popup=f"Frontage Point {i+1}",
                    tooltip=f"Frontage {i+1}",
                    icon=folium.Icon(color='green', icon='circle', prefix='fa')
                ).add_to(m)
            
            # Draw frontage line if both points exist
            if len(session['frontage_points']) == 2:
                folium.PolyLine(
                    locations=session['frontage_points'],
                    color='green',
                    weight=4,
                    opacity=0.8,
                    popup=f"Frontage: {session['frontage_distance']:.1f}m"
                ).add_to(m)
        
        # Add existing depth points if any
        if session['depth_points']:
            for i, point in enumerate(session['depth_points']):
                folium.Marker(
                    point,
                    popup=f"Depth Point {i+1}",
                    tooltip=f"Depth {i+1}",
                    icon=folium.Icon(color='red', icon='circle', prefix='fa')
                ).add_to(m)
            
            # Draw depth line if both points exist
            if len(session['depth_points']) == 2:
                folium.PolyLine(
                    locations=session['depth_points'],
                    color='red',
                    weight=4,
                    opacity=0.8,
                    popup=f"Depth: {session['depth_distance']:.1f}m"
                ).add_to(m)
        
        # Add click event handling via custom JavaScript
        click_js = f"""
        function onClick(e) {{
            var lat = e.latlng.lat;
            var lng = e.latlng.lng;
            
            // Send coordinates back to Streamlit
            window.parent.postMessage({{
                'type': 'map_click',
                'lat': lat,
                'lng': lng
            }}, '*');
        }}
        
        // Add click event listener to map
        {m.get_name()}.on('click', onClick);
        """
        
        # Add crosshair cursor for precision
        cursor_css = """
        <style>
        .leaflet-container {
            cursor: crosshair !important;
        }
        </style>
        """
        m.get_root().html.add_child(folium.Element(cursor_css))
        
        # Add measurement instructions overlay
        instructions = self.get_current_instructions()
        folium.plugins.FloatImage(
            f"data:image/svg+xml;base64,{self.create_instruction_svg(instructions)}",
            bottom=10,
            left=10,
            width="300px",
            height="80px"
        ).add_to(m)
        
        return m
    
    def create_instruction_svg(self, text: str) -> str:
        """Create SVG with current instructions"""
        import base64
        svg = f'''
        <svg width="300" height="80" xmlns="http://www.w3.org/2000/svg">
            <rect width="100%" height="100%" fill="white" fill-opacity="0.9" stroke="black" rx="5"/>
            <text x="10" y="20" font-family="Arial, sans-serif" font-size="12" font-weight="bold" fill="black">
                {text}
            </text>
            <text x="10" y="40" font-family="Arial, sans-serif" font-size="10" fill="black">
                Click precisely on property boundaries
            </text>
            <text x="10" y="55" font-family="Arial, sans-serif" font-size="10" fill="gray">
                Use satellite view for best accuracy
            </text>
        </svg>
        '''
        return base64.b64encode(svg.encode('utf-8')).decode('utf-8')
    
    def get_current_instructions(self) -> str:
        """Get current step instructions"""
        session = st.session_state.precise_measurement
        
        if session['step'] == 'frontage':
            if len(session['frontage_points']) == 0:
                return "Step 1: Click FIRST frontage point"
            elif len(session['frontage_points']) == 1:
                return "Step 1: Click SECOND frontage point"
        elif session['step'] == 'depth':
            if len(session['depth_points']) == 0:
                return "Step 2: Click FIRST depth point"
            elif len(session['depth_points']) == 1:
                return "Step 2: Click SECOND depth point"
        elif session['step'] == 'complete':
            return "Measurement Complete!"
        
        return "Click to place points"
    
    def process_point_click(self, lat: float, lon: float):
        """Process a point click based on current step"""
        session = st.session_state.precise_measurement
        point = (lat, lon)
        
        if session['step'] == 'frontage':
            if len(session['frontage_points']) < 2:
                session['frontage_points'].append(point)
                
                if len(session['frontage_points']) == 2:
                    # Calculate frontage distance
                    session['frontage_distance'] = self.calculate_haversine_distance(
                        session['frontage_points'][0],
                        session['frontage_points'][1]
                    )
                    # Move to depth step
                    session['step'] = 'depth'
                    
        elif session['step'] == 'depth':
            if len(session['depth_points']) < 2:
                session['depth_points'].append(point)
                
                if len(session['depth_points']) == 2:
                    # Calculate depth distance
                    session['depth_distance'] = self.calculate_haversine_distance(
                        session['depth_points'][0],
                        session['depth_points'][1]
                    )
                    # Calculate lot area (rectangular approximation)
                    session['lot_area'] = session['frontage_distance'] * session['depth_distance']
                    session['step'] = 'complete'
                    session['measurements_complete'] = True
    
    def display_measurement_interface(self, center_lat: float, center_lon: float, address: str = ""):
        """Main interface for precise point selection"""
        
        st.header("🎯 Precise 2-Point Property Measurement")
        
        # Progress indicator
        session = st.session_state.precise_measurement
        progress_value = 0
        if session['step'] == 'frontage':
            progress_value = len(session['frontage_points']) * 25
        elif session['step'] == 'depth':
            progress_value = 50 + len(session['depth_points']) * 25
        elif session['step'] == 'complete':
            progress_value = 100
        
        st.progress(progress_value / 100)
        
        # Current step indicator
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            frontage_status = "✅" if len(session['frontage_points']) == 2 else "🔄" if session['step'] == 'frontage' else "⏸️"
            st.write(f"{frontage_status} **Frontage** ({len(session['frontage_points'])}/2 points)")
        with col2:
            depth_status = "✅" if len(session['depth_points']) == 2 else "🔄" if session['step'] == 'depth' else "⏸️"
            st.write(f"{depth_status} **Depth** ({len(session['depth_points'])}/2 points)")
        with col3:
            complete_status = "✅" if session['measurements_complete'] else "⏸️"
            st.write(f"{complete_status} **Complete**")
        
        st.divider()
        
        # Instructions
        with st.expander("📋 Step-by-Step Instructions", expanded=True):
            st.markdown("""
            ### How to Use the Precise Point Selector:
            
            **Step 1: Frontage Measurement**
            1. Click the **first corner** of your property frontage (street side)
            2. Click the **second corner** of your property frontage
            3. System automatically calculates frontage distance
            
            **Step 2: Depth Measurement**  
            1. Click the **first point** at the front property line
            2. Click the **second point** at the rear property line (same side)
            3. System automatically calculates depth distance
            
            **Tips for Accuracy:**
            - Switch to **Satellite View** for better property visibility
            - Zoom in as much as possible before clicking
            - Click precisely on property boundary corners
            - Use property lines, fences, or building edges as guides
            """)
        
        # Property info
        if address:
            st.info(f"📍 **Property:** {address}")
        
        # Main measurement interface
        col_map, col_controls = st.columns([3, 1])
        
        with col_map:
            st.subheader("🗺️ Interactive Property Map")
            
            # Create and display map
            measurement_map = self.create_measurement_map(center_lat, center_lon)
            
            # Display map with click detection
            map_data = st_folium(
                measurement_map,
                key="precise_selector_map",
                width=700,
                height=600,
                returned_objects=["last_object_clicked"]
            )
            
            # Process map clicks
            if map_data and 'last_object_clicked' in map_data and map_data['last_object_clicked']:
                clicked_data = map_data['last_object_clicked']
                if 'lat' in clicked_data and 'lng' in clicked_data:
                    self.process_point_click(clicked_data['lat'], clicked_data['lng'])
                    st.rerun()
        
        with col_controls:
            st.subheader("📊 Measurements")
            
            # Current instruction
            current_instruction = self.get_current_instructions()
            if session['step'] == 'complete':
                st.success(current_instruction)
            else:
                st.info(current_instruction)
            
            st.divider()
            
            # Display measurements
            if session['frontage_distance'] > 0:
                frontage_units = self.convert_units(session['frontage_distance'])
                st.metric(
                    "🟢 Frontage",
                    f"{frontage_units['feet']:.1f} ft",
                    f"{frontage_units['meters']:.1f} m"
                )
            else:
                st.metric("🟢 Frontage", "Not measured")
            
            if session['depth_distance'] > 0:
                depth_units = self.convert_units(session['depth_distance'])
                st.metric(
                    "🔴 Depth", 
                    f"{depth_units['feet']:.1f} ft",
                    f"{depth_units['meters']:.1f} m"
                )
            else:
                st.metric("🔴 Depth", "Not measured")
            
            if session['lot_area'] > 0:
                area_sqm = session['lot_area']
                area_sqft = area_sqm * 10.764
                st.metric(
                    "📐 Lot Area",
                    f"{area_sqft:,.0f} sq ft",
                    f"{area_sqm:,.1f} sq m"
                )
            else:
                st.metric("📐 Lot Area", "Not calculated")
            
            st.divider()
            
            # Control buttons
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("🔄 Reset", type="secondary", use_container_width=True):
                    self.reset_session()
                    st.rerun()
            
            with col_btn2:
                if session['measurements_complete']:
                    if st.button("💾 Save", type="primary", use_container_width=True):
                        self.save_measurements()
                        st.success("Saved!")
                else:
                    st.button("💾 Save", disabled=True, use_container_width=True)
            
            # Measurement validation
            if session['measurements_complete']:
                st.success("✅ Measurements complete!")
                
                # Validation checks
                frontage_ft = session['frontage_distance'] * 3.28084
                depth_ft = session['depth_distance'] * 3.28084
                
                if frontage_ft < 10:
                    st.warning("⚠️ Frontage seems very small. Please verify.")
                if depth_ft < 15:
                    st.warning("⚠️ Depth seems very small. Please verify.")
                if frontage_ft > 200:
                    st.warning("⚠️ Frontage seems very large. Please verify.")
                if depth_ft > 500:
                    st.warning("⚠️ Depth seems very large. Please verify.")
        
        # Return measurement results for integration
        if session['measurements_complete']:
            return {
                'frontage_m': session['frontage_distance'],
                'depth_m': session['depth_distance'],
                'frontage_ft': session['frontage_distance'] * 3.28084,
                'depth_ft': session['depth_distance'] * 3.28084,
                'area_sqm': session['lot_area'],
                'area_sqft': session['lot_area'] * 10.764,
                'method': 'precise_2_point_selection',
                'confidence': 'user_measured_high_precision'
            }
        
        return None
    
    def save_measurements(self):
        """Save measurements to session state for integration with main app"""
        session = st.session_state.precise_measurement
        
        if not session['measurements_complete']:
            return
        
        # Save to measurement history
        if 'precise_measurement_history' not in st.session_state:
            st.session_state.precise_measurement_history = []
        
        measurement_record = {
            'timestamp': datetime.now().isoformat(),
            'frontage_m': session['frontage_distance'],
            'depth_m': session['depth_distance'],
            'frontage_ft': session['frontage_distance'] * 3.28084,
            'depth_ft': session['depth_distance'] * 3.28084,
            'area_sqm': session['lot_area'],
            'area_sqft': session['lot_area'] * 10.764,
            'frontage_points': session['frontage_points'],
            'depth_points': session['depth_points'],
            'method': 'precise_2_point_selection'
        }
        
        st.session_state.precise_measurement_history.append(measurement_record)
        
        # Update main app session state for integration
        st.session_state.manual_lot_calculation = {
            'lot_area': session['lot_area'],
            'frontage': session['frontage_distance'],
            'depth': session['depth_distance'],
            'method': 'precise_2_point_manual_selection',
            'confidence': 'user_measured_high_precision'
        }
    
    def display_measurement_history(self):
        """Display history of saved measurements"""
        if 'precise_measurement_history' in st.session_state and st.session_state.precise_measurement_history:
            with st.expander("📊 Measurement History"):
                df = pd.DataFrame(st.session_state.precise_measurement_history)
                df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
                
                # Format display columns
                display_df = df[[
                    'timestamp', 'frontage_ft', 'depth_ft', 'area_sqft'
                ]].copy()
                
                display_df.columns = ['Time', 'Frontage (ft)', 'Depth (ft)', 'Area (sq ft)']
                display_df['Frontage (ft)'] = display_df['Frontage (ft)'].round(1)
                display_df['Depth (ft)'] = display_df['Depth (ft)'].round(1)
                display_df['Area (sq ft)'] = display_df['Area (sq ft)'].round(0).astype(int)
                
                st.dataframe(display_df, use_container_width=True)
                
                if st.button("🗑️ Clear History"):
                    st.session_state.precise_measurement_history = []
                    st.rerun()


# Integration functions
def render_precise_point_selector(lat: float = 43.467517, lon: float = -79.686937, address: str = ""):
    """
    Render the precise point selector interface
    Returns measurement results when complete
    """
    selector = PrecisePointSelector()
    return selector.display_measurement_interface(lat, lon, address)


def get_current_precise_measurements() -> Optional[Dict]:
    """Get current measurements from the precise selector"""
    if 'precise_measurement' in st.session_state:
        session = st.session_state.precise_measurement
        if session['measurements_complete']:
            return {
                'frontage_m': session['frontage_distance'],
                'depth_m': session['depth_distance'],
                'frontage_ft': session['frontage_distance'] * 3.28084,
                'depth_ft': session['depth_distance'] * 3.28084,
                'area_sqm': session['lot_area'],
                'area_sqft': session['lot_area'] * 10.764,
                'method': 'precise_2_point_selection',
                'confidence': 'user_measured_high_precision'
            }
    return None


def clear_precise_measurements():
    """Clear all precise measurements from session"""
    if 'precise_measurement' in st.session_state:
        del st.session_state.precise_measurement
    if 'precise_measurement_history' in st.session_state:
        del st.session_state.precise_measurement_history


if __name__ == "__main__":
    # Test the precise point selector
    st.set_page_config(
        page_title="Precise Point Selector", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Test coordinates (383 Maplehurst Avenue, Oakville)
    test_lat = 43.467517
    test_lon = -79.686937
    test_address = "383 Maplehurst Avenue, Oakville, ON"
    
    measurements = render_precise_point_selector(test_lat, test_lon, test_address)
    
    if measurements:
        st.success("✅ Measurements complete and ready for property analysis!")
        with st.expander("View Measurement Details"):
            st.json(measurements)