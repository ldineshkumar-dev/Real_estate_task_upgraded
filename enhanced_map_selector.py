"""
Enhanced Map Selector with Manual Point Selection
Provides advanced property boundary selection and measurement
"""

import streamlit as st
import folium
from folium import plugins
import json
from typing import List, Tuple, Dict, Optional, Any
import math
from streamlit_folium import st_folium
import pandas as pd
import numpy as np
from datetime import datetime
import requests
from dataclasses import dataclass
import plotly.graph_objects as go


@dataclass
class PropertyPoint:
    """Represents a point on the property boundary"""
    lat: float
    lon: float
    point_type: str  # 'frontage_start', 'frontage_end', 'depth_start', 'depth_end', 'corner'
    label: Optional[str] = None
    
    def to_tuple(self) -> Tuple[float, float]:
        return (self.lat, self.lon)


class EnhancedPropertySelector:
    """Advanced property selection with manual point picking"""
    
    POINT_COLORS = {
        'frontage': '#FF0000',  # Red for frontage
        'depth': '#0000FF',     # Blue for depth
        'corner': '#00FF00',    # Green for corners
        'selected': '#FFD700'    # Gold for selected points
    }
    
    def __init__(self):
        self.initialize_session_state()
        
    def initialize_session_state(self):
        """Initialize session state variables"""
        if 'property_points' not in st.session_state:
            st.session_state.property_points = []
        if 'measurement_mode' not in st.session_state:
            st.session_state.measurement_mode = 'frontage'
        if 'property_polygon' not in st.session_state:
            st.session_state.property_polygon = []
        if 'saved_properties' not in st.session_state:
            st.session_state.saved_properties = []
    
    def haversine_distance(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """Calculate distance between two GPS points in meters"""
        lat1, lon1 = point1
        lat2, lon2 = point2
        
        R = 6371000  # Earth's radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def calculate_bearing(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """Calculate bearing between two points"""
        lat1, lon1 = math.radians(point1[0]), math.radians(point1[1])
        lat2, lon2 = math.radians(point2[0]), math.radians(point2[1])
        
        dlon = lon2 - lon1
        
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        
        bearing = math.atan2(y, x)
        bearing = math.degrees(bearing)
        bearing = (bearing + 360) % 360
        
        return bearing
    
    def calculate_polygon_area(self, points: List[Tuple[float, float]]) -> float:
        """Calculate area of polygon using Shoelace formula (in square meters)"""
        if len(points) < 3:
            return 0
        
        # Convert lat/lon to local projection (simple approximation)
        # Using the centroid as reference
        center_lat = sum(p[0] for p in points) / len(points)
        center_lon = sum(p[1] for p in points) / len(points)
        
        # Convert to local coordinates (meters)
        local_points = []
        for lat, lon in points:
            x = self.haversine_distance((center_lat, center_lon), (center_lat, lon))
            if lon < center_lon:
                x = -x
            y = self.haversine_distance((center_lat, center_lon), (lat, center_lon))
            if lat < center_lat:
                y = -y
            local_points.append((x, y))
        
        # Shoelace formula
        area = 0
        n = len(local_points)
        for i in range(n):
            j = (i + 1) % n
            area += local_points[i][0] * local_points[j][1]
            area -= local_points[j][0] * local_points[i][1]
        
        return abs(area) / 2
    
    def create_enhanced_map(self, center_lat: float = 43.467517, center_lon: float = -79.686937) -> folium.Map:
        """Create an enhanced interactive map with multiple selection modes"""
        
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=18,
            control_scale=True,
            prefer_canvas=True,
            max_zoom=20
        )
        
        # Add multiple tile layers
        folium.TileLayer('OpenStreetMap', name='Street Map').add_to(m)
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            attr='Google Satellite',
            name='Satellite',
            overlay=False,
            control=True
        ).add_to(m)
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
            attr='Google Hybrid',
            name='Hybrid',
            overlay=False,
            control=True
        ).add_to(m)
        
        # Add existing points from session state
        if st.session_state.property_points:
            for i, point in enumerate(st.session_state.property_points):
                color = self.POINT_COLORS.get(point.point_type.split('_')[0], '#000000')
                folium.CircleMarker(
                    location=[point.lat, point.lon],
                    radius=8,
                    popup=f"{point.label or point.point_type}<br>Point {i+1}",
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.7
                ).add_to(m)
            
            # Draw lines between consecutive points
            if len(st.session_state.property_points) >= 2:
                # Group points by type
                frontage_points = [p for p in st.session_state.property_points if 'frontage' in p.point_type]
                depth_points = [p for p in st.session_state.property_points if 'depth' in p.point_type]
                
                # Draw frontage line
                if len(frontage_points) >= 2:
                    folium.PolyLine(
                        locations=[p.to_tuple() for p in frontage_points],
                        color='red',
                        weight=3,
                        opacity=0.8,
                        popup='Frontage Line'
                    ).add_to(m)
                
                # Draw depth line
                if len(depth_points) >= 2:
                    folium.PolyLine(
                        locations=[p.to_tuple() for p in depth_points],
                        color='blue',
                        weight=3,
                        opacity=0.8,
                        popup='Depth Line'
                    ).add_to(m)
        
        # Add property polygon if exists
        if st.session_state.property_polygon:
            folium.Polygon(
                locations=st.session_state.property_polygon,
                color='green',
                weight=2,
                fill=True,
                fillColor='green',
                fillOpacity=0.2,
                popup='Property Boundary'
            ).add_to(m)
        
        # Add drawing tools
        draw = plugins.Draw(
            export=True,
            position='topleft',
            draw_options={
                'polyline': True,
                'polygon': True,
                'circle': False,
                'rectangle': True,
                'marker': True,
                'circlemarker': False
            },
            edit_options={
                'edit': True,
                'remove': True
            }
        )
        draw.add_to(m)
        
        # Add measure control
        plugins.MeasureControl(
            position='topright',
            primary_length_unit='meters',
            secondary_length_unit='feet',
            primary_area_unit='sqmeters',
            secondary_area_unit='sqfeet'
        ).add_to(m)
        
        # Add minimap
        minimap = plugins.MiniMap(toggle_display=True)
        m.add_child(minimap)
        
        # Add fullscreen
        plugins.Fullscreen(position='topleft').add_to(m)
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        # Add mouse position
        plugins.MousePosition().add_to(m)
        
        return m
    
    def display_selector_interface(self):
        """Display the complete property selector interface"""
        
        st.title("🗺️ Advanced Property Boundary Selector")
        
        # Top controls
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            property_address = st.text_input(
                "Property Address",
                placeholder="123 Main St, Oakville, ON",
                help="Enter address to center map"
            )
        
        with col2:
            measurement_mode = st.selectbox(
                "Selection Mode",
                ["Frontage Points", "Depth Points", "Property Corners", "Full Boundary"],
                index=0
            )
        
        with col3:
            st.write("")  # Spacer
            clear_btn = st.button("🗑️ Clear All", use_container_width=True)
            if clear_btn:
                st.session_state.property_points = []
                st.session_state.property_polygon = []
                st.rerun()
        
        with col4:
            st.write("")  # Spacer
            undo_btn = st.button("↩️ Undo Last", use_container_width=True)
            if undo_btn and st.session_state.property_points:
                st.session_state.property_points.pop()
                st.rerun()
        
        # Instructions panel
        with st.expander("📖 Instructions & Tips", expanded=False):
            st.markdown("""
            ### How to Select Property Boundaries:
            
            **Method 1: Point Selection**
            1. Select "Frontage Points" mode
            2. Click on the map to mark the front property line endpoints
            3. Switch to "Depth Points" mode
            4. Click to mark the property depth (front to back)
            
            **Method 2: Draw Lines**
            1. Use the polyline tool (line icon) to draw frontage
            2. Draw another line for depth
            3. The system will calculate dimensions automatically
            
            **Method 3: Full Boundary**
            1. Select "Full Boundary" mode
            2. Use the polygon tool to draw the complete property outline
            3. System calculates area and estimates frontage/depth
            
            **Tips:**
            - Switch to Satellite view for better property visibility
            - Zoom in (18-20) for precise placement
            - Use the measure tool for quick distance checks
            - Click points clockwise for proper area calculation
            """)
        
        # Main map area
        col_map, col_info = st.columns([3, 1])
        
        with col_map:
            # Create and display map
            m = self.create_enhanced_map()
            
            # Capture map interactions
            map_data = st_folium(
                m,
                key="property_selector_map",
                width=800,
                height=600,
                returned_objects=["all_drawings", "last_object_clicked"]
            )
            
            # Process map clicks and drawings
            if map_data:
                # Handle point clicks
                if map_data.get('last_object_clicked'):
                    coords = map_data['last_object_clicked'].get('lat'), map_data['last_object_clicked'].get('lng')
                    if coords[0] and coords[1]:
                        self.add_point_from_click(coords, measurement_mode)
                
                # Handle drawn features
                if map_data.get('all_drawings'):
                    self.process_drawings(map_data['all_drawings'])
        
        with col_info:
            st.subheader("📊 Measurements")
            
            # Calculate and display measurements
            measurements = self.calculate_measurements()
            
            # Frontage
            st.metric(
                "Frontage",
                f"{measurements['frontage_ft']:.1f} ft",
                f"({measurements['frontage_m']:.1f} m)"
            )
            
            # Depth
            st.metric(
                "Depth", 
                f"{measurements['depth_ft']:.1f} ft",
                f"({measurements['depth_m']:.1f} m)"
            )
            
            # Area
            if measurements['area_sqft'] > 0:
                st.metric(
                    "Area",
                    f"{measurements['area_sqft']:,.0f} sq ft",
                    f"({measurements['area_sqm']:.0f} sq m)"
                )
            
            # Lot dimensions
            if measurements['frontage_ft'] > 0 and measurements['depth_ft'] > 0:
                st.info(f"Lot: {measurements['frontage_ft']:.0f}' × {measurements['depth_ft']:.0f}'")
            
            st.divider()
            
            # Point list
            if st.session_state.property_points:
                st.subheader("📍 Selected Points")
                for i, point in enumerate(st.session_state.property_points):
                    st.text(f"{i+1}. {point.point_type}")
                    st.caption(f"   {point.lat:.6f}, {point.lon:.6f}")
            
            # Save button
            if measurements['frontage_ft'] > 0 or measurements['depth_ft'] > 0:
                if st.button("💾 Save Property", use_container_width=True):
                    self.save_property_data(property_address, measurements)
                    st.success("Property saved!")
        
        # Display saved properties
        if st.session_state.saved_properties:
            st.divider()
            st.subheader("📁 Saved Properties")
            
            df = pd.DataFrame(st.session_state.saved_properties)
            st.dataframe(
                df[['address', 'frontage_ft', 'depth_ft', 'area_sqft', 'timestamp']],
                use_container_width=True
            )
    
    def add_point_from_click(self, coords: Tuple[float, float], mode: str):
        """Add a point from map click based on current mode"""
        lat, lon = coords
        
        # Determine point type based on mode
        if mode == "Frontage Points":
            existing_frontage = len([p for p in st.session_state.property_points if 'frontage' in p.point_type])
            point_type = f"frontage_{existing_frontage + 1}"
        elif mode == "Depth Points":
            existing_depth = len([p for p in st.session_state.property_points if 'depth' in p.point_type])
            point_type = f"depth_{existing_depth + 1}"
        else:
            point_type = "corner"
        
        # Create and add point
        new_point = PropertyPoint(lat, lon, point_type, mode)
        st.session_state.property_points.append(new_point)
    
    def process_drawings(self, drawings: List[Dict]):
        """Process drawn features from the map"""
        for feature in drawings:
            geometry = feature.get('geometry', {})
            
            if geometry.get('type') == 'LineString':
                coords = geometry.get('coordinates', [])
                if len(coords) >= 2:
                    # Determine if this is frontage or depth based on existing points
                    has_frontage = any('frontage' in p.point_type for p in st.session_state.property_points)
                    
                    for i, coord in enumerate(coords):
                        point_type = 'depth' if has_frontage else 'frontage'
                        point = PropertyPoint(coord[1], coord[0], f"{point_type}_{i+1}")
                        
                        # Avoid duplicates
                        if not any(abs(p.lat - point.lat) < 0.00001 and abs(p.lon - point.lon) < 0.00001 
                                  for p in st.session_state.property_points):
                            st.session_state.property_points.append(point)
            
            elif geometry.get('type') == 'Polygon':
                coords = geometry.get('coordinates', [[]])[0]
                if coords:
                    st.session_state.property_polygon = [(c[1], c[0]) for c in coords]
    
    def calculate_measurements(self) -> Dict:
        """Calculate all property measurements from selected points"""
        result = {
            'frontage_m': 0,
            'frontage_ft': 0,
            'depth_m': 0,
            'depth_ft': 0,
            'area_sqm': 0,
            'area_sqft': 0
        }
        
        # Calculate frontage
        frontage_points = [p for p in st.session_state.property_points if 'frontage' in p.point_type]
        if len(frontage_points) >= 2:
            total_distance = 0
            for i in range(len(frontage_points) - 1):
                segment = self.haversine_distance(
                    frontage_points[i].to_tuple(),
                    frontage_points[i + 1].to_tuple()
                )
                total_distance += segment
            result['frontage_m'] = total_distance
            result['frontage_ft'] = total_distance * 3.28084
        
        # Calculate depth
        depth_points = [p for p in st.session_state.property_points if 'depth' in p.point_type]
        if len(depth_points) >= 2:
            total_distance = 0
            for i in range(len(depth_points) - 1):
                segment = self.haversine_distance(
                    depth_points[i].to_tuple(),
                    depth_points[i + 1].to_tuple()
                )
                total_distance += segment
            result['depth_m'] = total_distance
            result['depth_ft'] = total_distance * 3.28084
        
        # Calculate area from polygon
        if st.session_state.property_polygon:
            area_m2 = self.calculate_polygon_area(st.session_state.property_polygon)
            result['area_sqm'] = area_m2
            result['area_sqft'] = area_m2 * 10.7639
        elif result['frontage_m'] > 0 and result['depth_m'] > 0:
            # Estimate rectangular area
            result['area_sqm'] = result['frontage_m'] * result['depth_m']
            result['area_sqft'] = result['frontage_ft'] * result['depth_ft']
        
        return result
    
    def save_property_data(self, address: str, measurements: Dict):
        """Save property data to session state"""
        property_data = {
            'address': address or 'Unknown Address',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'frontage_ft': round(measurements['frontage_ft'], 1),
            'depth_ft': round(measurements['depth_ft'], 1),
            'area_sqft': round(measurements['area_sqft'], 0),
            'points': [p.__dict__ for p in st.session_state.property_points],
            'polygon': st.session_state.property_polygon
        }
        
        st.session_state.saved_properties.append(property_data)
    
    def get_latest_measurements(self) -> Optional[Dict]:
        """Get the most recent measurements for integration"""
        measurements = self.calculate_measurements()
        if measurements['frontage_ft'] > 0 or measurements['depth_ft'] > 0:
            return {
                'frontage': measurements['frontage_ft'],
                'depth': measurements['depth_ft'],
                'area': measurements['area_sqft'],
                'frontage_m': measurements['frontage_m'],
                'depth_m': measurements['depth_m'],
                'area_sqm': measurements['area_sqm'],
                'points': st.session_state.property_points,
                'polygon': st.session_state.property_polygon
            }
        return None


# Integration function
def render_enhanced_property_selector():
    """Render the enhanced property selector and return measurements"""
    selector = EnhancedPropertySelector()
    selector.display_selector_interface()
    return selector.get_latest_measurements()


if __name__ == "__main__":
    st.set_page_config(page_title="Property Boundary Selector", layout="wide")
    render_enhanced_property_selector()