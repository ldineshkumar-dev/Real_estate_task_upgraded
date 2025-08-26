"""
ArcGIS-Style Interactive Property Measurement Map
Replicates the functionality of ArcGIS experience with advanced point selection and measurement
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import math
from typing import Dict, List, Tuple, Optional, Any
import logging
from geopy.distance import geodesic
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)

class ArcGISStyleMap:
    """
    Advanced interactive map component that replicates ArcGIS Experience functionality
    """
    
    def __init__(self, lat: float = 43.467517, lon: float = -79.687666):
        """Initialize the interactive map"""
        self.center_lat = lat
        self.center_lon = lon
        self.zoom_level = 18
        self.measurement_points = []
        self.measurement_lines = []
        self.property_boundaries = []
        
        # Map styles and layers
        self.available_layers = {
            'OpenStreetMap': 'OpenStreetMap',
            'Satellite': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            'Hybrid': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            'Terrain': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}',
            'Streets': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}'
        }
        
    def create_interactive_map(self, 
                             property_address: str = None,
                             measurement_mode: str = "point_to_point",
                             show_property_boundaries: bool = True,
                             show_zoning_overlay: bool = True) -> folium.Map:
        """
        Create an interactive map with advanced measurement capabilities
        
        Args:
            property_address: Address to center the map on
            measurement_mode: Type of measurement (point_to_point, polygon, line)
            show_property_boundaries: Whether to show property boundaries
            show_zoning_overlay: Whether to show zoning overlays
        """
        
        # Initialize session state for measurements
        if 'arcgis_measurements' not in st.session_state:
            st.session_state.arcgis_measurements = {
                'points': [],
                'lines': [],
                'polygons': [],
                'current_measurement': None
            }
        
        # Create base map with high zoom for precise measurements
        m = folium.Map(
            location=[self.center_lat, self.center_lon],
            zoom_start=self.zoom_level,
            tiles=None,  # We'll add custom tiles
            prefer_canvas=True,
            max_zoom=22,
            min_zoom=10
        )
        
        # Add multiple tile layers for different views
        self._add_tile_layers(m)
        
        # Add property boundary layer if available
        if show_property_boundaries:
            self._add_property_boundaries(m)
        
        # Add zoning overlay if requested
        if show_zoning_overlay:
            self._add_zoning_overlay(m)
        
        # Add measurement tools
        self._add_measurement_tools(m, measurement_mode)
        
        # Add drawing plugins for advanced interaction
        self._add_drawing_plugins(m)
        
        # Add scale bar and coordinate display
        self._add_map_controls(m)
        
        return m
    
    def _add_tile_layers(self, m: folium.Map):
        """Add multiple tile layers with layer control"""
        
        # Base layers
        folium.TileLayer(
            'OpenStreetMap',
            name='Street Map',
            attr='OpenStreetMap'
        ).add_to(m)
        
        folium.TileLayer(
            'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            name='Satellite',
            attr='Esri'
        ).add_to(m)
        
        folium.TileLayer(
            'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
            name='Streets (Detailed)',
            attr='Esri'
        ).add_to(m)
        
        folium.TileLayer(
            'https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}',
            name='Terrain',
            attr='Esri'
        ).add_to(m)
        
        # Hybrid layer (satellite with labels)
        folium.TileLayer(
            'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            name='Hybrid Base',
            attr='Esri'
        ).add_to(m)
        
        folium.TileLayer(
            'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
            name='Hybrid Labels',
            attr='Esri',
            overlay=True
        ).add_to(m)
    
    def _add_property_boundaries(self, m: folium.Map):
        """Add property boundary overlays from Oakville GIS"""
        # This would integrate with Oakville's property boundary API
        # For now, we'll add a placeholder
        
        property_boundary_url = (
            "https://gis.oakville.ca/server/rest/services/OpenData/"
            "PropertyBoundaries/MapServer/tile/{z}/{y}/{x}"
        )
        
        try:
            folium.TileLayer(
                property_boundary_url,
                name='Property Boundaries',
                attr='Town of Oakville',
                overlay=True,
                opacity=0.7
            ).add_to(m)
        except Exception as e:
            logger.warning(f"Could not load property boundaries: {e}")
    
    def _add_zoning_overlay(self, m: folium.Map):
        """Add zoning overlay from Oakville GIS"""
        # Oakville zoning overlay
        zoning_url = (
            "https://gis.oakville.ca/server/rest/services/OpenData/"
            "Zoning/MapServer/tile/{z}/{y}/{x}"
        )
        
        try:
            folium.TileLayer(
                zoning_url,
                name='Zoning Classifications',
                attr='Town of Oakville',
                overlay=True,
                opacity=0.5
            ).add_to(m)
        except Exception as e:
            logger.warning(f"Could not load zoning overlay: {e}")
    
    def _add_measurement_tools(self, m: folium.Map, mode: str):
        """Add interactive measurement tools"""
        
        # Add JavaScript for click handling
        click_handler = """
        <script>
        var measurementPoints = [];
        var measurementLines = [];
        var currentMeasurement = null;
        
        function handleMapClick(e) {
            var lat = e.latlng.lat;
            var lng = e.latlng.lng;
            
            // Add point marker
            var marker = L.marker([lat, lng], {
                draggable: true,
                icon: L.divIcon({
                    className: 'measurement-point',
                    html: '<div style="background: red; width: 10px; height: 10px; border-radius: 50%; border: 2px solid white;"></div>',
                    iconSize: [14, 14],
                    iconAnchor: [7, 7]
                })
            }).addTo(window.map);
            
            measurementPoints.push({
                marker: marker,
                lat: lat,
                lng: lng
            });
            
            // Update measurements
            updateMeasurements();
        }
        
        function updateMeasurements() {
            // Clear existing lines
            measurementLines.forEach(function(line) {
                window.map.removeLayer(line);
            });
            measurementLines = [];
            
            // Draw lines between points
            for (var i = 0; i < measurementPoints.length - 1; i++) {
                var p1 = measurementPoints[i];
                var p2 = measurementPoints[i + 1];
                
                var line = L.polyline([[p1.lat, p1.lng], [p2.lat, p2.lng]], {
                    color: '#ff0000',
                    weight: 3,
                    opacity: 0.8
                }).addTo(window.map);
                
                measurementLines.push(line);
                
                // Calculate distance
                var distance = calculateDistance(p1.lat, p1.lng, p2.lat, p2.lng);
                
                // Add distance label
                var midLat = (p1.lat + p2.lat) / 2;
                var midLng = (p1.lng + p2.lng) / 2;
                
                var label = L.marker([midLat, midLng], {
                    icon: L.divIcon({
                        className: 'distance-label',
                        html: '<div style="background: white; padding: 2px 6px; border-radius: 4px; font-size: 12px; font-weight: bold; border: 1px solid #ccc;">' + distance.toFixed(2) + 'm</div>',
                        iconSize: [60, 20],
                        iconAnchor: [30, 10]
                    })
                }).addTo(window.map);
                
                measurementLines.push(label);
            }
        }
        
        function calculateDistance(lat1, lng1, lat2, lng2) {
            var R = 6371000; // Earth's radius in meters
            var dLat = (lat2 - lat1) * Math.PI / 180;
            var dLng = (lng2 - lng1) * Math.PI / 180;
            var a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                    Math.sin(dLng/2) * Math.sin(dLng/2);
            var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
            return R * c;
        }
        
        function clearMeasurements() {
            measurementPoints.forEach(function(point) {
                window.map.removeLayer(point.marker);
            });
            measurementLines.forEach(function(line) {
                window.map.removeLayer(line);
            });
            measurementPoints = [];
            measurementLines = [];
        }
        
        // Attach click handler to map
        if (window.map) {
            window.map.on('click', handleMapClick);
        }
        </script>
        """
        
        m.get_root().html.add_child(folium.Element(click_handler))
    
    def _add_drawing_plugins(self, m: folium.Map):
        """Add drawing plugins for advanced measurement"""
        from folium.plugins import Draw, MeasureControl
        
        # Add drawing tools
        draw = Draw(
            export=True,
            position='topright',
            draw_options={
                'polyline': {
                    'allowIntersection': False,
                    'drawError': {
                        'color': '#e1e100',
                        'message': "Intersection not allowed!"
                    },
                    'shapeOptions': {
                        'color': '#ff0000',
                        'weight': 4
                    }
                },
                'polygon': {
                    'allowIntersection': False,
                    'drawError': {
                        'color': '#e1e100',
                        'message': "Intersection not allowed!"
                    },
                    'shapeOptions': {
                        'color': '#0000ff',
                        'fillColor': '#0000ff',
                        'fillOpacity': 0.2
                    }
                },
                'circle': False,
                'rectangle': {
                    'shapeOptions': {
                        'color': '#00ff00',
                        'fillColor': '#00ff00',
                        'fillOpacity': 0.2
                    }
                },
                'marker': True,
                'circlemarker': False
            }
        )
        draw.add_to(m)
        
        # Add measurement control
        measure_control = MeasureControl(
            position='topright',
            primary_length_unit='meters',
            secondary_length_unit='feet',
            primary_area_unit='sqmeters',
            secondary_area_unit='sqfeet'
        )
        measure_control.add_to(m)
    
    def _add_map_controls(self, m: folium.Map):
        """Add scale bar and coordinate display"""
        from folium.plugins import MousePosition
        
        # Add mouse position (coordinates)
        MousePosition().add_to(m)
        
        # Add layer control
        folium.LayerControl(position='topright', collapsed=False).add_to(m)
        
        # Add custom CSS for better styling
        custom_css = """
        <style>
        .measurement-point {
            z-index: 1000;
        }
        .distance-label {
            z-index: 999;
        }
        .leaflet-control-layers {
            background: rgba(255, 255, 255, 0.9);
        }
        .leaflet-control-mouseposition {
            background: rgba(255, 255, 255, 0.9);
            padding: 5px 10px;
            font-family: monospace;
            font-size: 12px;
            border-radius: 4px;
        }
        </style>
        """
        
        m.get_root().html.add_child(folium.Element(custom_css))

def render_arcgis_style_interface(lat: float, lon: float, address: str = None) -> Dict[str, Any]:
    """
    Render the ArcGIS-style interactive measurement interface
    
    Args:
        lat: Property latitude
        lon: Property longitude 
        address: Property address
    
    Returns:
        Dict containing measurement results and user interactions
    """
    
    st.markdown("### 🗺️ ArcGIS-Style Interactive Property Measurement")
    st.info("🎯 **Professional-Grade Measurement Tool**: Click points on the map to create precise measurements. Includes satellite imagery, property boundaries, and real-time distance calculations.")
    
    # Initialize the map component
    arcgis_map = ArcGISStyleMap(lat, lon)
    
    # Measurement options
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        measurement_mode = st.selectbox(
            "Measurement Mode",
            ["point_to_point", "polygon", "line", "area"],
            help="Select the type of measurement to perform"
        )
    
    with col2:
        show_boundaries = st.checkbox(
            "Property Boundaries",
            value=True,
            help="Show property boundary overlay"
        )
    
    with col3:
        show_zoning = st.checkbox(
            "Zoning Overlay", 
            value=True,
            help="Show zoning classification overlay"
        )
    
    with col4:
        map_layer = st.selectbox(
            "Base Layer",
            ["Satellite", "Street Map", "Hybrid", "Terrain"],
            help="Select map base layer"
        )
    
    # Create the interactive map
    interactive_map = arcgis_map.create_interactive_map(
        property_address=address,
        measurement_mode=measurement_mode,
        show_property_boundaries=show_boundaries,
        show_zoning_overlay=show_zoning
    )
    
    # Display the map with enhanced interaction
    st.markdown("#### 🎯 Interactive Measurement Map")
    st.markdown("**Instructions:**")
    st.markdown("1. **Click** on the map to place measurement points")
    st.markdown("2. **Drag** points to adjust measurements") 
    st.markdown("3. Use **drawing tools** (top-right) for advanced shapes")
    st.markdown("4. **Right-click** to access context menu")
    
    # Render the map
    map_data = st_folium(
        interactive_map,
        width=800,
        height=600,
        returned_objects=["last_object_clicked", "all_drawings", "last_clicked"],
        key="arcgis_map"
    )
    
    # Process map interactions
    results = process_map_interactions(map_data)
    
    # Control panel
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🗑️ Clear All Measurements", type="secondary"):
            if 'arcgis_measurements' in st.session_state:
                st.session_state.arcgis_measurements = {
                    'points': [],
                    'lines': [], 
                    'polygons': [],
                    'current_measurement': None
                }
            st.rerun()
    
    with col2:
        if st.button("📏 Calculate Area", type="primary"):
            if results.get('points') and len(results['points']) >= 3:
                area_result = calculate_polygon_area(results['points'])
                st.success(f"Area: {area_result['area_sqm']:.2f} m² ({area_result['area_sqft']:.2f} sq ft)")
            else:
                st.warning("Need at least 3 points to calculate area")
    
    with col3:
        export_format = st.selectbox("Export Format", ["JSON", "CSV", "KML"])
        if st.button(f"📤 Export {export_format}"):
            export_data = export_measurements(results, export_format)
            st.download_button(
                f"Download {export_format}",
                data=export_data,
                file_name=f"measurements.{export_format.lower()}",
                mime=f"application/{export_format.lower()}"
            )
    
    # Display current measurements
    if results.get('measurements'):
        st.markdown("#### 📊 Current Measurements")
        display_measurement_results(results)
    
    return results

def process_map_interactions(map_data: Dict) -> Dict[str, Any]:
    """Process map interactions and extract measurement data"""
    
    results = {
        'points': [],
        'lines': [],
        'polygons': [],
        'measurements': {}
    }
    
    # Process clicked points
    if map_data.get('last_clicked'):
        clicked = map_data['last_clicked']
        if clicked:
            point = {
                'lat': clicked['lat'],
                'lng': clicked['lng'],
                'timestamp': clicked.get('timestamp')
            }
            results['points'].append(point)
    
    # Process drawings
    if map_data.get('all_drawings'):
        drawings = map_data['all_drawings']
        
        for drawing in drawings:
            geometry = drawing.get('geometry', {})
            coordinates = geometry.get('coordinates', [])
            
            if geometry.get('type') == 'LineString':
                results['lines'].append({
                    'coordinates': coordinates,
                    'distance_m': calculate_line_distance(coordinates)
                })
            
            elif geometry.get('type') == 'Polygon':
                results['polygons'].append({
                    'coordinates': coordinates,
                    'area_sqm': calculate_polygon_area_from_coords(coordinates)
                })
    
    # Calculate measurements from points
    if len(results['points']) >= 2:
        total_distance = 0
        measurements = []
        
        for i in range(len(results['points']) - 1):
            p1 = results['points'][i]
            p2 = results['points'][i + 1]
            
            distance = geodesic(
                (p1['lat'], p1['lng']),
                (p2['lat'], p2['lng'])
            ).meters
            
            total_distance += distance
            measurements.append({
                'segment': i + 1,
                'distance_m': distance,
                'distance_ft': distance * 3.28084
            })
        
        results['measurements'] = {
            'total_distance_m': total_distance,
            'total_distance_ft': total_distance * 3.28084,
            'segments': measurements,
            'num_points': len(results['points'])
        }
    
    return results

def calculate_line_distance(coordinates: List[List[float]]) -> float:
    """Calculate total distance of a line string"""
    total_distance = 0
    
    for i in range(len(coordinates) - 1):
        p1 = coordinates[i]
        p2 = coordinates[i + 1]
        
        distance = geodesic((p1[1], p1[0]), (p2[1], p2[0])).meters
        total_distance += distance
    
    return total_distance

def calculate_polygon_area(points: List[Dict]) -> Dict[str, float]:
    """Calculate area of a polygon from point list"""
    if len(points) < 3:
        return {'area_sqm': 0, 'area_sqft': 0}
    
    # Convert to coordinate pairs
    coords = [(p['lat'], p['lng']) for p in points]
    coords.append(coords[0])  # Close the polygon
    
    return calculate_polygon_area_from_coords([coords])

def calculate_polygon_area_from_coords(coordinates: List[List[List[float]]]) -> float:
    """Calculate polygon area from coordinate array using Shoelace formula"""
    if not coordinates or len(coordinates[0]) < 3:
        return 0
    
    coords = coordinates[0]  # Get the outer ring
    
    # Shoelace formula for area calculation
    area = 0
    n = len(coords) - 1  # Last point should be same as first
    
    for i in range(n):
        j = (i + 1) % n
        area += coords[i][1] * coords[j][0]  # lng * lat
        area -= coords[j][1] * coords[i][0]  # lng * lat
    
    area = abs(area) / 2.0
    
    # Convert to square meters (approximate)
    # This is a rough approximation - for precise calculations, use proper geodesic methods
    area_sqm = area * (111320 ** 2)  # degrees to meters conversion
    
    return area_sqm

def display_measurement_results(results: Dict[str, Any]):
    """Display measurement results in organized format"""
    
    measurements = results.get('measurements', {})
    
    if measurements:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Total Distance",
                f"{measurements['total_distance_m']:.2f} m",
                f"{measurements['total_distance_ft']:.2f} ft"
            )
        
        with col2:
            st.metric("Measurement Points", measurements['num_points'])
        
        with col3:
            if len(results.get('polygons', [])) > 0:
                total_area = sum(p['area_sqm'] for p in results['polygons'])
                st.metric(
                    "Total Area", 
                    f"{total_area:.2f} m²",
                    f"{total_area * 10.764:.2f} sq ft"
                )
        
        # Detailed segment breakdown
        if measurements.get('segments'):
            st.markdown("##### 📏 Measurement Segments")
            
            for segment in measurements['segments']:
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.write(f"**Segment {segment['segment']}:**")
                with col2:
                    st.write(f"{segment['distance_m']:.2f} m ({segment['distance_ft']:.2f} ft)")

def export_measurements(results: Dict[str, Any], format: str) -> str:
    """Export measurement data in specified format"""
    
    if format == "JSON":
        return json.dumps(results, indent=2)
    
    elif format == "CSV":
        csv_data = "Type,Latitude,Longitude,Distance_M,Distance_Ft\n"
        
        for i, point in enumerate(results.get('points', [])):
            csv_data += f"Point,{point['lat']},{point['lng']},,\n"
        
        for i, segment in enumerate(results.get('measurements', {}).get('segments', [])):
            csv_data += f"Segment_{segment['segment']},,,{segment['distance_m']},{segment['distance_ft']}\n"
        
        return csv_data
    
    elif format == "KML":
        kml_data = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Property Measurements</name>
    <Placemark>
      <name>Measurement Points</name>
      <LineString>
        <coordinates>'''
        
        for point in results.get('points', []):
            kml_data += f"\n          {point['lng']},{point['lat']},0"
        
        kml_data += '''
        </coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>'''
        
        return kml_data
    
    return ""

# Example usage and testing functions
def test_arcgis_map():
    """Test function for the ArcGIS-style map"""
    # Test coordinates for Oakville
    test_lat = 43.467517
    test_lon = -79.687666
    
    results = render_arcgis_style_interface(
        lat=test_lat,
        lon=test_lon,
        address="383 Maplehurst Avenue, Oakville"
    )
    
    return results

if __name__ == "__main__":
    # Run test if executed directly
    test_results = test_arcgis_map()
    print("ArcGIS-style map test completed")
    print(f"Results: {test_results}")