"""
Coordinate Geometry Utilities for Property Measurements
Advanced algorithms for property boundary analysis and measurement calculations
"""

import math
import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from pyproj import Transformer
import logging

logger = logging.getLogger(__name__)

@dataclass
class GeometryPoint:
    """Point with coordinate information"""
    x: float
    y: float
    lat: Optional[float] = None
    lon: Optional[float] = None
    label: Optional[str] = None

@dataclass
class PropertyDimensions:
    """Comprehensive property dimension analysis"""
    lot_area_sqm: float
    lot_area_sqft: float
    frontage_m: float
    frontage_ft: float
    depth_m: float
    depth_ft: float
    perimeter_m: float
    perimeter_ft: float
    aspect_ratio: float  # width/depth ratio
    rectangularity: float  # how close to rectangle (0-1)
    frontage_points: Tuple[GeometryPoint, GeometryPoint]
    depth_points: Tuple[GeometryPoint, GeometryPoint]
    corner_points: List[GeometryPoint]
    is_corner_lot: bool

class CoordinateGeometry:
    """Advanced coordinate geometry calculations for property analysis"""
    
    def __init__(self):
        # Coordinate system transformers
        self.wgs84_to_utm17n = Transformer.from_crs("EPSG:4326", "EPSG:26917", always_xy=True)
        self.utm17n_to_wgs84 = Transformer.from_crs("EPSG:26917", "EPSG:4326", always_xy=True)
        
    def analyze_property_geometry(self, coordinates: List[Tuple[float, float]], 
                                coordinate_system: str = 'utm') -> PropertyDimensions:
        """
        Comprehensive analysis of property geometry
        
        Args:
            coordinates: List of (x,y) or (lon,lat) coordinates defining property boundary
            coordinate_system: 'utm' for UTM coordinates, 'wgs84' for lat/lon
            
        Returns:
            PropertyDimensions with complete geometric analysis
        """
        if coordinate_system == 'wgs84':
            # Convert to UTM for accurate calculations
            utm_coords = []
            for lon, lat in coordinates:
                x, y = self.wgs84_to_utm17n.transform(lon, lat)
                utm_coords.append((x, y))
            coordinates = utm_coords
        
        # Basic measurements
        area_sqm = self.calculate_polygon_area(coordinates)
        area_sqft = area_sqm * 10.764
        perimeter_m = self.calculate_polygon_perimeter(coordinates)
        perimeter_ft = perimeter_m * 3.28084
        
        # Find frontage and depth
        frontage_data = self.find_frontage(coordinates)
        depth_data = self.find_depth(coordinates, frontage_data['line'])
        
        # Convert points back to lat/lon if needed
        frontage_points = self._create_geometry_points(
            frontage_data['points'], coordinate_system
        )
        depth_points = self._create_geometry_points(
            depth_data['points'], coordinate_system
        )
        
        # Identify corner points
        corner_points = self.identify_corners(coordinates, coordinate_system)
        
        # Calculate derived metrics
        aspect_ratio = frontage_data['length'] / depth_data['length'] if depth_data['length'] > 0 else 1.0
        rectangularity = self.calculate_rectangularity(coordinates)
        is_corner_lot = self.detect_corner_lot(coordinates)
        
        return PropertyDimensions(
            lot_area_sqm=area_sqm,
            lot_area_sqft=area_sqft,
            frontage_m=frontage_data['length'],
            frontage_ft=frontage_data['length'] * 3.28084,
            depth_m=depth_data['length'],
            depth_ft=depth_data['length'] * 3.28084,
            perimeter_m=perimeter_m,
            perimeter_ft=perimeter_ft,
            aspect_ratio=aspect_ratio,
            rectangularity=rectangularity,
            frontage_points=frontage_points,
            depth_points=depth_points,
            corner_points=corner_points,
            is_corner_lot=is_corner_lot
        )
    
    def find_frontage(self, coordinates: List[Tuple[float, float]]) -> Dict:
        """
        Find property frontage (typically the longest edge facing the street)
        
        Uses multiple heuristics:
        1. Longest edge
        2. Edge most parallel to coordinate axes
        3. Edge with specific orientation patterns
        """
        if len(coordinates) < 3:
            return {'points': coordinates[:2] if len(coordinates) >= 2 else [],
                   'length': 0, 'line': None}
        
        max_length = 0
        best_edge = None
        best_points = None
        
        # Analyze each edge
        for i in range(len(coordinates)):
            p1 = coordinates[i]
            p2 = coordinates[(i + 1) % len(coordinates)]
            
            # Calculate edge length
            length = self.euclidean_distance(p1, p2)
            
            # Calculate orientation (prefer edges parallel to coordinate axes)
            dx = abs(p2[0] - p1[0])
            dy = abs(p2[1] - p1[1])
            orientation_score = max(dx, dy) / (dx + dy + 1e-10)  # Prefer axis-aligned edges
            
            # Combined score (length weighted by orientation preference)
            score = length * (1 + 0.2 * orientation_score)
            
            if score > max_length:
                max_length = score
                best_edge = (p1, p2)
                best_points = [p1, p2]
        
        if not best_edge:
            return {'points': [], 'length': 0, 'line': None}
        
        actual_length = self.euclidean_distance(best_edge[0], best_edge[1])
        
        return {
            'points': best_points,
            'length': actual_length,
            'line': best_edge
        }
    
    def find_depth(self, coordinates: List[Tuple[float, float]], 
                   frontage_line: Optional[Tuple[Tuple[float, float], Tuple[float, float]]]) -> Dict:
        """
        Find property depth (perpendicular measurement to frontage)
        """
        if not frontage_line or len(coordinates) < 4:
            # Fallback: find second longest edge
            edges_by_length = []
            for i in range(len(coordinates)):
                p1 = coordinates[i]
                p2 = coordinates[(i + 1) % len(coordinates)]
                length = self.euclidean_distance(p1, p2)
                edges_by_length.append((length, (p1, p2)))
            
            edges_by_length.sort(reverse=True)
            if len(edges_by_length) >= 2:
                second_longest = edges_by_length[1]
                return {
                    'points': [second_longest[1][0], second_longest[1][1]],
                    'length': second_longest[0],
                    'line': second_longest[1]
                }
        
        # Find edge most perpendicular to frontage
        frontage_vector = (
            frontage_line[1][0] - frontage_line[0][0],
            frontage_line[1][1] - frontage_line[0][1]
        )
        frontage_angle = math.atan2(frontage_vector[1], frontage_vector[0])
        
        best_perpendicular = None
        max_length = 0
        best_points = None
        
        for i in range(len(coordinates)):
            p1 = coordinates[i]
            p2 = coordinates[(i + 1) % len(coordinates)]
            
            # Skip if this is the frontage line
            if (p1, p2) == frontage_line or (p2, p1) == frontage_line:
                continue
            
            edge_vector = (p2[0] - p1[0], p2[1] - p1[1])
            edge_angle = math.atan2(edge_vector[1], edge_vector[0])
            
            # Calculate angle difference from perpendicular
            perp_angle = frontage_angle + math.pi / 2
            angle_diff = abs(self.normalize_angle(edge_angle - perp_angle))
            
            # Prefer edges closer to perpendicular
            length = self.euclidean_distance(p1, p2)
            perp_score = length * (1 - angle_diff / (math.pi / 2))
            
            if perp_score > max_length:
                max_length = perp_score
                best_perpendicular = (p1, p2)
                best_points = [p1, p2]
        
        if not best_perpendicular:
            # Fallback: centroid to furthest point from frontage
            centroid = self.calculate_centroid(coordinates)
            furthest_point = self.find_furthest_point_from_line(coordinates, frontage_line)
            
            if furthest_point:
                length = self.euclidean_distance(centroid, furthest_point)
                return {
                    'points': [centroid, furthest_point],
                    'length': length,
                    'line': (centroid, furthest_point)
                }
        
        actual_length = self.euclidean_distance(best_perpendicular[0], best_perpendicular[1])
        
        return {
            'points': best_points or [],
            'length': actual_length,
            'line': best_perpendicular
        }
    
    def identify_corners(self, coordinates: List[Tuple[float, float]], 
                        coordinate_system: str = 'utm') -> List[GeometryPoint]:
        """
        Identify significant corner points in the property boundary
        """
        if len(coordinates) < 4:
            return [self._create_geometry_point(coord, coordinate_system) for coord in coordinates]
        
        corners = []
        
        for i in range(len(coordinates)):
            prev_point = coordinates[i - 1]
            current_point = coordinates[i]
            next_point = coordinates[(i + 1) % len(coordinates)]
            
            # Calculate interior angle
            angle = self.calculate_interior_angle(prev_point, current_point, next_point)
            
            # Identify significant corners (not close to 180 degrees)
            if abs(angle - math.pi) > math.pi / 6:  # More than 30 degrees from straight line
                corner = self._create_geometry_point(current_point, coordinate_system, f"Corner {len(corners) + 1}")
                corners.append(corner)
        
        return corners
    
    def detect_corner_lot(self, coordinates: List[Tuple[float, float]]) -> bool:
        """
        Detect if property is a corner lot based on geometry analysis
        Heuristics: irregular shape, multiple street-facing edges
        """
        if len(coordinates) < 4:
            return False
        
        # Count edges that could be street-facing (longer edges)
        edge_lengths = []
        for i in range(len(coordinates)):
            p1 = coordinates[i]
            p2 = coordinates[(i + 1) % len(coordinates)]
            length = self.euclidean_distance(p1, p2)
            edge_lengths.append(length)
        
        edge_lengths.sort(reverse=True)
        
        # If two longest edges are similar in length, might be corner lot
        if len(edge_lengths) >= 2:
            ratio = edge_lengths[1] / edge_lengths[0]
            if ratio > 0.6:  # Second longest is at least 60% of longest
                return True
        
        # Check for irregular angles suggesting corner lot
        acute_angles = 0
        for i in range(len(coordinates)):
            prev_point = coordinates[i - 1]
            current_point = coordinates[i]
            next_point = coordinates[(i + 1) % len(coordinates)]
            
            angle = self.calculate_interior_angle(prev_point, current_point, next_point)
            if angle < math.pi * 2 / 3:  # Less than 120 degrees
                acute_angles += 1
        
        return acute_angles >= 2
    
    def calculate_rectangularity(self, coordinates: List[Tuple[float, float]]) -> float:
        """
        Calculate how close the property shape is to a rectangle (0 to 1)
        """
        if len(coordinates) < 4:
            return 0.0
        
        # Calculate area
        actual_area = self.calculate_polygon_area(coordinates)
        
        # Find bounding rectangle
        min_x = min(coord[0] for coord in coordinates)
        max_x = max(coord[0] for coord in coordinates)
        min_y = min(coord[1] for coord in coordinates)
        max_y = max(coord[1] for coord in coordinates)
        
        bounding_area = (max_x - min_x) * (max_y - min_y)
        
        if bounding_area == 0:
            return 0.0
        
        # Rectangularity is ratio of actual area to bounding rectangle area
        rectangularity = actual_area / bounding_area
        
        # Also check angle regularity
        angles = []
        for i in range(len(coordinates)):
            prev_point = coordinates[i - 1]
            current_point = coordinates[i]
            next_point = coordinates[(i + 1) % len(coordinates)]
            
            angle = self.calculate_interior_angle(prev_point, current_point, next_point)
            angles.append(angle)
        
        # Check if angles are close to 90 degrees
        right_angle_score = 0
        for angle in angles:
            deviation = abs(angle - math.pi / 2)
            if deviation < math.pi / 6:  # Within 30 degrees of 90
                right_angle_score += 1
        
        angle_regularity = right_angle_score / len(angles)
        
        # Combine area ratio and angle regularity
        return (rectangularity + angle_regularity) / 2
    
    def calculate_polygon_area(self, coordinates: List[Tuple[float, float]]) -> float:
        """Calculate polygon area using shoelace formula"""
        if len(coordinates) < 3:
            return 0.0
        
        area = 0.0
        n = len(coordinates)
        
        for i in range(n):
            j = (i + 1) % n
            area += coordinates[i][0] * coordinates[j][1]
            area -= coordinates[j][0] * coordinates[i][1]
        
        return abs(area) / 2.0
    
    def calculate_polygon_perimeter(self, coordinates: List[Tuple[float, float]]) -> float:
        """Calculate polygon perimeter"""
        if len(coordinates) < 2:
            return 0.0
        
        perimeter = 0.0
        for i in range(len(coordinates)):
            current = coordinates[i]
            next_point = coordinates[(i + 1) % len(coordinates)]
            perimeter += self.euclidean_distance(current, next_point)
        
        return perimeter
    
    def calculate_centroid(self, coordinates: List[Tuple[float, float]]) -> Tuple[float, float]:
        """Calculate polygon centroid"""
        if not coordinates:
            return (0.0, 0.0)
        
        x_sum = sum(coord[0] for coord in coordinates)
        y_sum = sum(coord[1] for coord in coordinates)
        
        return (x_sum / len(coordinates), y_sum / len(coordinates))
    
    def euclidean_distance(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance between two points"""
        return math.sqrt((point2[0] - point1[0])**2 + (point2[1] - point1[1])**2)
    
    def calculate_interior_angle(self, p1: Tuple[float, float], p2: Tuple[float, float], 
                               p3: Tuple[float, float]) -> float:
        """Calculate interior angle at p2 formed by p1-p2-p3"""
        # Vectors from p2 to p1 and p2 to p3
        v1 = (p1[0] - p2[0], p1[1] - p2[1])
        v2 = (p3[0] - p2[0], p3[1] - p2[1])
        
        # Calculate angle using dot product
        dot_product = v1[0] * v2[0] + v1[1] * v2[1]
        mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
        mag2 = math.sqrt(v2[0]**2 + v2[1]**2)
        
        if mag1 == 0 or mag2 == 0:
            return 0
        
        cos_angle = dot_product / (mag1 * mag2)
        cos_angle = max(-1, min(1, cos_angle))  # Clamp to valid range
        
        return math.acos(cos_angle)
    
    def normalize_angle(self, angle: float) -> float:
        """Normalize angle to [-π, π] range"""
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle
    
    def find_furthest_point_from_line(self, coordinates: List[Tuple[float, float]], 
                                    line: Tuple[Tuple[float, float], Tuple[float, float]]) -> Optional[Tuple[float, float]]:
        """Find the point in coordinates that is furthest from the given line"""
        if not line or not coordinates:
            return None
        
        p1, p2 = line
        max_distance = 0
        furthest_point = None
        
        for point in coordinates:
            # Skip if point is on the line
            if point == p1 or point == p2:
                continue
            
            distance = self.point_to_line_distance(point, p1, p2)
            if distance > max_distance:
                max_distance = distance
                furthest_point = point
        
        return furthest_point
    
    def point_to_line_distance(self, point: Tuple[float, float], 
                             line_p1: Tuple[float, float], 
                             line_p2: Tuple[float, float]) -> float:
        """Calculate distance from point to line defined by two points"""
        px, py = point
        x1, y1 = line_p1
        x2, y2 = line_p2
        
        # Line equation: Ax + By + C = 0
        A = y2 - y1
        B = x1 - x2  
        C = x2 * y1 - x1 * y2
        
        # Distance formula
        distance = abs(A * px + B * py + C) / math.sqrt(A**2 + B**2)
        return distance
    
    def _create_geometry_points(self, points: List[Tuple[float, float]], 
                              coordinate_system: str) -> Tuple[GeometryPoint, GeometryPoint]:
        """Create GeometryPoint objects from coordinate pairs"""
        if len(points) < 2:
            return None
        
        p1 = self._create_geometry_point(points[0], coordinate_system, "Point 1")
        p2 = self._create_geometry_point(points[1], coordinate_system, "Point 2")
        
        return (p1, p2)
    
    def _create_geometry_point(self, coord: Tuple[float, float], 
                             coordinate_system: str, label: str = None) -> GeometryPoint:
        """Create a GeometryPoint from coordinates"""
        if coordinate_system == 'utm':
            x, y = coord
            lon, lat = self.utm17n_to_wgs84.transform(x, y)
        else:
            lat, lon = coord
            x, y = self.wgs84_to_utm17n.transform(lon, lat)
        
        return GeometryPoint(x=x, y=y, lat=lat, lon=lon, label=label)

# Utility functions
def meters_to_feet(meters: float) -> float:
    """Convert meters to feet"""
    return meters * 3.28084

def feet_to_meters(feet: float) -> float:
    """Convert feet to meters"""
    return feet / 3.28084

def square_meters_to_square_feet(sq_meters: float) -> float:
    """Convert square meters to square feet"""
    return sq_meters * 10.764

def square_feet_to_square_meters(sq_feet: float) -> float:
    """Convert square feet to square meters"""
    return sq_feet / 10.764