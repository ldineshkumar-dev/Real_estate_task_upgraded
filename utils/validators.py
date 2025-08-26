"""
Input validation utilities
"""

import re
from typing import Tuple, Optional, List, Dict, Any
from config import Config


class ValidationError(Exception):
    """Custom validation error"""
    pass


class PropertyValidator:
    """Validator for property data inputs"""
    
    @staticmethod
    def validate_coordinates(lat: float, lon: float) -> Tuple[bool, Optional[str]]:
        """
        Validate latitude and longitude coordinates
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Basic coordinate validation
        if not (-90 <= lat <= 90):
            return False, f"Latitude must be between -90 and 90, got {lat}"
        
        if not (-180 <= lon <= 180):
            return False, f"Longitude must be between -180 and 180, got {lon}"
        
        # Oakville-specific validation (approximate bounds)
        oakville_bounds = {
            'lat_min': 43.40,
            'lat_max': 43.55,
            'lon_min': -79.80,
            'lon_max': -79.60
        }
        
        if not (oakville_bounds['lat_min'] <= lat <= oakville_bounds['lat_max']):
            return False, f"Latitude {lat} appears to be outside Oakville area"
        
        if not (oakville_bounds['lon_min'] <= lon <= oakville_bounds['lon_max']):
            return False, f"Longitude {lon} appears to be outside Oakville area"
        
        return True, None
    
    @staticmethod
    def validate_lot_area(area: float) -> Tuple[bool, Optional[str]]:
        """Validate lot area"""
        if not isinstance(area, (int, float)):
            return False, "Lot area must be a number"
        
        if area < Config.MIN_LOT_AREA:
            return False, f"Lot area must be at least {Config.MIN_LOT_AREA} m²"
        
        if area > Config.MAX_LOT_AREA:
            return False, f"Lot area cannot exceed {Config.MAX_LOT_AREA} m²"
        
        return True, None
    
    @staticmethod
    def validate_building_area(area: float, lot_area: float = None) -> Tuple[bool, Optional[str]]:
        """Validate building area"""
        if not isinstance(area, (int, float)):
            return False, "Building area must be a number"
        
        if area < Config.MIN_BUILDING_AREA:
            return False, f"Building area must be at least {Config.MIN_BUILDING_AREA} m²"
        
        if area > Config.MAX_BUILDING_AREA:
            return False, f"Building area cannot exceed {Config.MAX_BUILDING_AREA} m²"
        
        # Check against lot area if provided
        if lot_area and area > lot_area:
            return False, "Building area cannot exceed lot area"
        
        return True, None
    
    @staticmethod
    def validate_bedrooms(bedrooms: int) -> Tuple[bool, Optional[str]]:
        """Validate number of bedrooms"""
        if not isinstance(bedrooms, int):
            return False, "Number of bedrooms must be an integer"
        
        if bedrooms < Config.MIN_BEDROOMS:
            return False, f"Number of bedrooms must be at least {Config.MIN_BEDROOMS}"
        
        if bedrooms > Config.MAX_BEDROOMS:
            return False, f"Number of bedrooms cannot exceed {Config.MAX_BEDROOMS}"
        
        return True, None
    
    @staticmethod
    def validate_bathrooms(bathrooms: float) -> Tuple[bool, Optional[str]]:
        """Validate number of bathrooms"""
        if not isinstance(bathrooms, (int, float)):
            return False, "Number of bathrooms must be a number"
        
        if bathrooms < Config.MIN_BATHROOMS:
            return False, f"Number of bathrooms must be at least {Config.MIN_BATHROOMS}"
        
        if bathrooms > Config.MAX_BATHROOMS:
            return False, f"Number of bathrooms cannot exceed {Config.MAX_BATHROOMS}"
        
        # Check for valid increments (0.5)
        if bathrooms % 0.5 != 0:
            return False, "Bathrooms must be in 0.5 increments (e.g., 1.5, 2.0, 2.5)"
        
        return True, None
    
    @staticmethod
    def validate_building_age(age: int) -> Tuple[bool, Optional[str]]:
        """Validate building age"""
        if not isinstance(age, int):
            return False, "Building age must be an integer"
        
        if age < Config.MIN_BUILDING_AGE:
            return False, f"Building age cannot be negative"
        
        if age > Config.MAX_BUILDING_AGE:
            return False, f"Building age cannot exceed {Config.MAX_BUILDING_AGE} years"
        
        return True, None
    
    @staticmethod
    def validate_zone_code(zone_code: str) -> Tuple[bool, Optional[str]]:
        """Validate zoning code format"""
        if not isinstance(zone_code, str):
            return False, "Zone code must be a string"
        
        # Basic format validation for Oakville zones
        zone_pattern = r'^R[LMH][1-9][0-9]?(-[0-9])?(\s+SP:[0-9]+)?$|^RUC(-[0-9])?(\s+SP:[0-9]+)?$'
        
        if not re.match(zone_pattern, zone_code.strip().upper()):
            return False, f"Invalid zone code format: {zone_code}"
        
        return True, None
    
    @staticmethod
    def validate_address(address: str) -> Tuple[bool, Optional[str]]:
        """Validate address format"""
        if not isinstance(address, str):
            return False, "Address must be a string"
        
        address = address.strip()
        if len(address) < 5:
            return False, "Address is too short"
        
        if len(address) > 200:
            return False, "Address is too long (max 200 characters)"
        
        # Basic format check (number + street name)
        address_pattern = r'^\d+\s+[A-Za-z\s]+'
        if not re.match(address_pattern, address):
            return False, "Address should start with a street number followed by street name"
        
        return True, None
    
    @staticmethod
    def validate_postal_code(postal_code: str) -> Tuple[bool, Optional[str]]:
        """Validate Canadian postal code"""
        if not isinstance(postal_code, str):
            return False, "Postal code must be a string"
        
        # Canadian postal code pattern
        postal_pattern = r'^[A-Za-z]\d[A-Za-z]\s?\d[A-Za-z]\d$'
        
        if not re.match(postal_pattern, postal_code.strip()):
            return False, "Invalid Canadian postal code format (should be A1A 1A1)"
        
        return True, None


class FinancialValidator:
    """Validator for financial data"""
    
    @staticmethod
    def validate_price(price: float, min_price: float = 0, max_price: float = 50000000) -> Tuple[bool, Optional[str]]:
        """Validate price values"""
        if not isinstance(price, (int, float)):
            return False, "Price must be a number"
        
        if price < min_price:
            return False, f"Price cannot be less than ${min_price:,.0f}"
        
        if price > max_price:
            return False, f"Price cannot exceed ${max_price:,.0f}"
        
        return True, None
    
    @staticmethod
    def validate_percentage(percentage: float, min_pct: float = 0, max_pct: float = 100) -> Tuple[bool, Optional[str]]:
        """Validate percentage values"""
        if not isinstance(percentage, (int, float)):
            return False, "Percentage must be a number"
        
        if percentage < min_pct:
            return False, f"Percentage cannot be less than {min_pct}%"
        
        if percentage > max_pct:
            return False, f"Percentage cannot exceed {max_pct}%"
        
        return True, None
    
    @staticmethod
    def validate_ratio(ratio: float, min_ratio: float = 0, max_ratio: float = 10) -> Tuple[bool, Optional[str]]:
        """Validate ratio values"""
        if not isinstance(ratio, (int, float)):
            return False, "Ratio must be a number"
        
        if ratio < min_ratio:
            return False, f"Ratio cannot be less than {min_ratio}"
        
        if ratio > max_ratio:
            return False, f"Ratio cannot exceed {max_ratio}"
        
        return True, None


class DataValidator:
    """General data validation utilities"""
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[str]:
        """
        Validate that all required fields are present
        
        Args:
            data: Data dictionary to validate
            required_fields: List of required field names
            
        Returns:
            List of missing field names
        """
        missing_fields = []
        
        for field in required_fields:
            if field not in data or data[field] is None:
                missing_fields.append(field)
        
        return missing_fields
    
    @staticmethod
    def validate_data_types(data: Dict[str, Any], type_specs: Dict[str, type]) -> List[str]:
        """
        Validate data types for specified fields
        
        Args:
            data: Data dictionary to validate
            type_specs: Dictionary mapping field names to expected types
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        for field, expected_type in type_specs.items():
            if field in data and data[field] is not None:
                if not isinstance(data[field], expected_type):
                    errors.append(f"Field '{field}' must be of type {expected_type.__name__}")
        
        return errors
    
    @staticmethod
    def sanitize_string(text: str, max_length: int = 1000) -> str:
        """
        Sanitize string input
        
        Args:
            text: Input text
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
        """
        if not isinstance(text, str):
            return str(text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length].strip()
        
        # Remove potentially harmful characters (basic sanitization)
        text = re.sub(r'[<>{}]', '', text)
        
        return text
    
    @staticmethod
    def validate_date_range(start_date, end_date) -> Tuple[bool, Optional[str]]:
        """Validate date range"""
        from datetime import datetime
        
        if start_date and end_date:
            if isinstance(start_date, str):
                try:
                    start_date = datetime.fromisoformat(start_date)
                except ValueError:
                    return False, "Invalid start date format"
            
            if isinstance(end_date, str):
                try:
                    end_date = datetime.fromisoformat(end_date)
                except ValueError:
                    return False, "Invalid end date format"
            
            if start_date >= end_date:
                return False, "Start date must be before end date"
        
        return True, None


def validate_property_input(property_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Comprehensive validation for property input data
    
    Args:
        property_data: Dictionary containing property information
        
    Returns:
        Dictionary with validation results categorized by field
    """
    errors = {}
    warnings = {}
    
    validator = PropertyValidator()
    
    # Validate coordinates if present
    if 'latitude' in property_data and 'longitude' in property_data:
        is_valid, error = validator.validate_coordinates(
            property_data['latitude'], 
            property_data['longitude']
        )
        if not is_valid:
            errors.setdefault('coordinates', []).append(error)
    
    # Validate lot area
    if 'lot_area' in property_data:
        is_valid, error = validator.validate_lot_area(property_data['lot_area'])
        if not is_valid:
            errors.setdefault('lot_area', []).append(error)
    
    # Validate building area
    if 'building_area' in property_data:
        lot_area = property_data.get('lot_area')
        is_valid, error = validator.validate_building_area(
            property_data['building_area'], lot_area
        )
        if not is_valid:
            errors.setdefault('building_area', []).append(error)
    
    # Validate bedrooms
    if 'bedrooms' in property_data:
        is_valid, error = validator.validate_bedrooms(property_data['bedrooms'])
        if not is_valid:
            errors.setdefault('bedrooms', []).append(error)
    
    # Validate bathrooms
    if 'bathrooms' in property_data:
        is_valid, error = validator.validate_bathrooms(property_data['bathrooms'])
        if not is_valid:
            errors.setdefault('bathrooms', []).append(error)
    
    # Validate building age
    if 'age' in property_data:
        is_valid, error = validator.validate_building_age(property_data['age'])
        if not is_valid:
            errors.setdefault('age', []).append(error)
    
    # Validate address if present
    if 'address' in property_data:
        is_valid, error = validator.validate_address(property_data['address'])
        if not is_valid:
            errors.setdefault('address', []).append(error)
    
    # Check for logical consistency
    if ('lot_area' in property_data and 'building_area' in property_data and 
        property_data['building_area'] > property_data['lot_area'] * 2):
        warnings.setdefault('consistency', []).append(
            "Building area seems unusually large relative to lot area"
        )
    
    if ('bedrooms' in property_data and 'bathrooms' in property_data and
        property_data['bathrooms'] > property_data['bedrooms'] * 1.5):
        warnings.setdefault('consistency', []).append(
            "Number of bathrooms seems high relative to bedrooms"
        )
    
    return {
        'errors': errors,
        'warnings': warnings,
        'is_valid': len(errors) == 0
    }