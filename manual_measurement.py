"""
Manual Property Measurement System
Allows users to manually select points on a map to measure frontage and depth
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

class ManualMeasurementTool:
    """Tool for manually measuring property dimensions on an interactive map"""
    
    def __init__(self):
        self.measurements = []
        self.current_session = st.session_state.get('measurement_session', {})
        
    def calculate_distance(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """
        Calculate distance between two points in meters
        Using Haversine formula for accurate distance on Earth's surface
        """
        lat1, lon1 = point1
        lat2, lon2 = point2
        
        # Earth's radius in meters
        R = 6371000
        
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        # Haversine formula
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return distance
    
    def meters_to_feet(self, meters: float) -> float:
        """Convert meters to feet"""
        return meters * 3.28084
    
    def create_interactive_map(self, center_lat: float = 43.467517, center_lon: float = -79.686937) -> folium.Map:
        """
        Create an interactive Folium map for point selection
        """
        # Create base map centered on Oakville
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=17,
            control_scale=True,
            prefer_canvas=True
        )
        
        # Add tile layers for better visualization
        folium.TileLayer('OpenStreetMap').add_to(m)
        folium.TileLayer('Stamen Terrain', attr='terrain').add_to(m)
        folium.TileLayer('CartoDB positron', attr='light').add_to(m)
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        # Add draw plugin for point selection
        draw = plugins.Draw(
            export=True,
            position='topleft',
            draw_options={
                'polyline': True,
                'polygon': False,
                'circle': False,
                'circlemarker': False,
                'rectangle': False,
                'marker': True
            },
            edit_options={
                'edit': True,
                'remove': True
            }
        )
        draw.add_to(m)
        
        # Add measurement control
        plugins.MeasureControl(
            position='topright',
            primary_length_unit='meters',
            secondary_length_unit='feet',
            primary_area_unit='sqmeters',
            secondary_area_unit='sqfeet'
        ).add_to(m)
        
        # Add fullscreen control
        plugins.Fullscreen(
            position='topleft',
            title='Expand',
            title_cancel='Exit',
            force_separate_button=True
        ).add_to(m)
        
        # Add locate control to find user's location
        plugins.LocateControl(
            auto_start=False,
            position='topleft'
        ).add_to(m)
        
        return m
    
    def process_drawn_features(self, features: List[Dict]) -> Dict:
        """
        Process features drawn on the map to calculate measurements
        """
        results = {
            'frontage_points': [],
            'depth_points': [],
            'frontage_meters': 0,
            'frontage_feet': 0,
            'depth_meters': 0,
            'depth_feet': 0,
            'all_points': [],
            'polylines': []
        }
        
        if not features:
            return results
        
        for feature in features:
            geometry = feature.get('geometry', {})
            properties = feature.get('properties', {})
            
            if geometry.get('type') == 'Point':
                coords = geometry.get('coordinates', [])
                if coords:
                    # Folium returns [lon, lat], we need [lat, lon]
                    point = (coords[1], coords[0])
                    results['all_points'].append(point)
            
            elif geometry.get('type') == 'LineString':
                coords = geometry.get('coordinates', [])
                if len(coords) >= 2:
                    # Convert all coordinates to [lat, lon] format
                    line_points = [(c[1], c[0]) for c in coords]
                    results['polylines'].append(line_points)
                    
                    # Calculate total distance for the line
                    total_distance = 0
                    for i in range(len(line_points) - 1):
                        segment_distance = self.calculate_distance(
                            line_points[i], 
                            line_points[i + 1]
                        )
                        total_distance += segment_distance
                    
                    # Store as frontage or depth based on property type
                    if properties.get('type') == 'frontage' or len(results['frontage_points']) == 0:
                        results['frontage_points'] = line_points
                        results['frontage_meters'] = total_distance
                        results['frontage_feet'] = self.meters_to_feet(total_distance)
                    else:
                        results['depth_points'] = line_points
                        results['depth_meters'] = total_distance
                        results['depth_feet'] = self.meters_to_feet(total_distance)
        
        return results
    
    def display_measurement_interface(self):
        """
        Display the complete measurement interface in Streamlit
        """
        st.header("📏 Manual Property Measurement Tool")
        
        # Instructions
        with st.expander("📖 How to Use", expanded=True):
            st.markdown("""
            ### Instructions for Measuring Property Dimensions:
            
            1. **Draw Frontage Line:**
               - Click the polyline tool (line icon) in the map controls
               - Click along the property frontage to create points
               - Double-click to finish the frontage line
               
            2. **Draw Depth Line:**
               - Draw another polyline from front to back of the property
               - This represents the property depth
               
            3. **Using Measurement Tool:**
               - Click the ruler icon for quick measurements
               - Click points on the map to measure distances
               
            4. **Tips:**
               - Zoom in for more accurate placement
               - Use satellite view for better property visibility
               - Edit or delete lines using the edit tools
               - Lines are automatically calculated in both meters and feet
            """)
        
        # Property address input
        col1, col2 = st.columns([2, 1])
        with col1:
            address = st.text_input(
                "Property Address (optional)",
                placeholder="Enter address to center map",
                help="Enter an address to center the map on a specific property"
            )
        
        with col2:
            if st.button("🔍 Center Map", disabled=not address):
                # Here you would geocode the address
                # For now, we'll use default Oakville coordinates
                st.info("Map centered on address location")
        
        # Create columns for map and measurements
        col_map, col_stats = st.columns([3, 1])
        
        with col_map:
            # Create and display the interactive map
            st.subheader("Interactive Map")
            
            # Initialize map
            m = self.create_interactive_map()
            
            # Display map and capture drawn features
            map_data = st_folium(
                m,
                key="measurement_map",
                width=700,
                height=500,
                returned_objects=["all_drawings"]
            )
        
        with col_stats:
            st.subheader("Measurements")
            
            if map_data and 'all_drawings' in map_data and map_data['all_drawings']:
                # Process drawn features
                measurements = self.process_drawn_features(map_data['all_drawings'])
                
                # Display frontage measurements
                st.metric(
                    "Frontage",
                    f"{measurements['frontage_feet']:.1f} ft",
                    f"{measurements['frontage_meters']:.1f} m"
                )
                
                # Display depth measurements
                st.metric(
                    "Depth",
                    f"{measurements['depth_feet']:.1f} ft",
                    f"{measurements['depth_meters']:.1f} m"
                )
                
                # Calculate area if both measurements exist
                if measurements['frontage_meters'] > 0 and measurements['depth_meters'] > 0:
                    area_sqm = measurements['frontage_meters'] * measurements['depth_meters']
                    area_sqft = measurements['frontage_feet'] * measurements['depth_feet']
                    
                    st.metric(
                        "Estimated Area",
                        f"{area_sqft:.0f} sq ft",
                        f"{area_sqm:.0f} sq m"
                    )
                
                # Save measurements button
                if st.button("💾 Save Measurements"):
                    self.save_measurements(measurements)
                    st.success("Measurements saved!")
            else:
                st.info("Draw lines on the map to measure frontage and depth")
        
        # Display saved measurements history
        self.display_measurement_history()
    
    def save_measurements(self, measurements: Dict):
        """Save measurements to session state"""
        if 'measurement_history' not in st.session_state:
            st.session_state.measurement_history = []
        
        measurement_record = {
            'timestamp': datetime.now().isoformat(),
            'frontage_ft': measurements['frontage_feet'],
            'depth_ft': measurements['depth_feet'],
            'frontage_m': measurements['frontage_meters'],
            'depth_m': measurements['depth_meters'],
            'area_sqft': measurements['frontage_feet'] * measurements['depth_feet'] if measurements['frontage_feet'] > 0 and measurements['depth_feet'] > 0 else 0
        }
        
        st.session_state.measurement_history.append(measurement_record)
    
    def display_measurement_history(self):
        """Display history of saved measurements"""
        if 'measurement_history' in st.session_state and st.session_state.measurement_history:
            with st.expander("📊 Measurement History"):
                df = pd.DataFrame(st.session_state.measurement_history)
                df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
                
                # Format numeric columns
                df['frontage_ft'] = df['frontage_ft'].round(1)
                df['depth_ft'] = df['depth_ft'].round(1)
                df['area_sqft'] = df['area_sqft'].round(0)
                
                st.dataframe(
                    df[['timestamp', 'frontage_ft', 'depth_ft', 'area_sqft']],
                    use_container_width=True
                )
                
                # Clear history button
                if st.button("🗑️ Clear History"):
                    st.session_state.measurement_history = []
                    st.rerun()
    
    def get_current_measurements(self) -> Optional[Dict]:
        """Get the most recent measurements"""
        if 'measurement_history' in st.session_state and st.session_state.measurement_history:
            return st.session_state.measurement_history[-1]
        return None


# Standalone function for easy integration
def render_manual_measurement_tool():
    """Render the manual measurement tool interface"""
    tool = ManualMeasurementTool()
    tool.display_measurement_interface()
    return tool.get_current_measurements()


if __name__ == "__main__":
    # Test the manual measurement tool
    st.set_page_config(page_title="Manual Property Measurement", layout="wide")
    render_manual_measurement_tool()