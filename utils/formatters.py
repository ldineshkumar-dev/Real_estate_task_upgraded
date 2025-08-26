"""
Data formatting utilities
"""

import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP


class CurrencyFormatter:
    """Currency formatting utilities"""
    
    @staticmethod
    def format_cad(amount: Union[int, float], include_symbol: bool = True, 
                  precision: int = 0) -> str:
        """
        Format amount as Canadian currency
        
        Args:
            amount: Monetary amount
            include_symbol: Whether to include $ symbol
            precision: Number of decimal places
            
        Returns:
            Formatted currency string
        """
        if amount is None:
            return "N/A"
        
        # Round to specified precision
        if precision == 0:
            formatted = f"{amount:,.0f}"
        else:
            formatted = f"{amount:,.{precision}f}"
        
        if include_symbol:
            return f"${formatted}"
        
        return formatted
    
    @staticmethod
    def format_price_range(low: float, high: float, include_symbol: bool = True) -> str:
        """Format price range"""
        low_formatted = CurrencyFormatter.format_cad(low, include_symbol)
        high_formatted = CurrencyFormatter.format_cad(high, include_symbol)
        
        return f"{low_formatted} - {high_formatted}"
    
    @staticmethod
    def format_price_per_unit(amount: float, unit: str = "m²", 
                             include_symbol: bool = True) -> str:
        """Format price per unit"""
        formatted = CurrencyFormatter.format_cad(amount, include_symbol)
        return f"{formatted}/{unit}"


class AreaFormatter:
    """Area formatting utilities"""
    
    @staticmethod
    def format_area(area: float, unit: str = "m²", precision: int = 0) -> str:
        """
        Format area with unit
        
        Args:
            area: Area value
            unit: Area unit (m², sq ft, etc.)
            precision: Number of decimal places
            
        Returns:
            Formatted area string
        """
        if area is None:
            return "N/A"
        
        if precision == 0:
            formatted = f"{area:,.0f}"
        else:
            formatted = f"{area:,.{precision}f}"
        
        return f"{formatted} {unit}"
    
    @staticmethod
    def convert_sqm_to_sqft(sqm: float) -> float:
        """Convert square meters to square feet"""
        return sqm * 10.764
    
    @staticmethod
    def convert_sqft_to_sqm(sqft: float) -> float:
        """Convert square feet to square meters"""
        return sqft * 0.092903
    
    @staticmethod
    def format_dual_area(sqm: float, show_both: bool = True) -> str:
        """Format area in both metric and imperial"""
        if sqm is None:
            return "N/A"
        
        sqft = AreaFormatter.convert_sqm_to_sqft(sqm)
        
        if show_both:
            return f"{sqm:,.0f} m² ({sqft:,.0f} sq ft)"
        else:
            return f"{sqm:,.0f} m²"


class PercentageFormatter:
    """Percentage formatting utilities"""
    
    @staticmethod
    def format_percentage(value: float, precision: int = 1, 
                         include_symbol: bool = True) -> str:
        """
        Format value as percentage
        
        Args:
            value: Decimal value (0.25 for 25%)
            precision: Number of decimal places
            include_symbol: Whether to include % symbol
            
        Returns:
            Formatted percentage string
        """
        if value is None:
            return "N/A"
        
        percentage = value * 100
        
        if precision == 0:
            formatted = f"{percentage:.0f}"
        else:
            formatted = f"{percentage:.{precision}f}"
        
        if include_symbol:
            return f"{formatted}%"
        
        return formatted
    
    @staticmethod
    def format_change(old_value: float, new_value: float, 
                     as_percentage: bool = True) -> str:
        """Format change between two values"""
        if old_value is None or new_value is None or old_value == 0:
            return "N/A"
        
        change = new_value - old_value
        
        if as_percentage:
            percentage_change = (change / old_value) * 100
            symbol = "↑" if percentage_change > 0 else "↓" if percentage_change < 0 else "→"
            return f"{symbol} {abs(percentage_change):.1f}%"
        else:
            symbol = "+" if change > 0 else ""
            return f"{symbol}{change:,.0f}"


class DateFormatter:
    """Date and time formatting utilities"""
    
    @staticmethod
    def format_date(date: datetime, format_type: str = "short") -> str:
        """
        Format date
        
        Args:
            date: Date to format
            format_type: Format type ('short', 'long', 'iso')
            
        Returns:
            Formatted date string
        """
        if date is None:
            return "N/A"
        
        if format_type == "short":
            return date.strftime("%Y-%m-%d")
        elif format_type == "long":
            return date.strftime("%B %d, %Y")
        elif format_type == "iso":
            return date.isoformat()
        else:
            return str(date)
    
    @staticmethod
    def format_duration(days: int) -> str:
        """Format duration in days to human readable format"""
        if days is None:
            return "N/A"
        
        if days < 30:
            return f"{days} days"
        elif days < 365:
            months = days // 30
            remaining_days = days % 30
            if remaining_days == 0:
                return f"{months} months"
            else:
                return f"{months} months, {remaining_days} days"
        else:
            years = days // 365
            remaining_days = days % 365
            if remaining_days == 0:
                return f"{years} years"
            else:
                months = remaining_days // 30
                return f"{years} years, {months} months"
    
    @staticmethod
    def format_time_ago(date: datetime) -> str:
        """Format time elapsed since date"""
        if date is None:
            return "N/A"
        
        now = datetime.now()
        delta = now - date
        
        if delta.days == 0:
            hours = delta.seconds // 3600
            if hours == 0:
                minutes = delta.seconds // 60
                return f"{minutes} minutes ago"
            else:
                return f"{hours} hours ago"
        elif delta.days == 1:
            return "Yesterday"
        elif delta.days < 7:
            return f"{delta.days} days ago"
        elif delta.days < 30:
            weeks = delta.days // 7
            return f"{weeks} weeks ago"
        elif delta.days < 365:
            months = delta.days // 30
            return f"{months} months ago"
        else:
            years = delta.days // 365
            return f"{years} years ago"


class AddressFormatter:
    """Address formatting utilities"""
    
    @staticmethod
    def format_address(address_components: Dict[str, str]) -> str:
        """Format address from components"""
        parts = []
        
        # Street address
        street_number = address_components.get('street_number', '')
        street_name = address_components.get('street_name', '')
        if street_number and street_name:
            parts.append(f"{street_number} {street_name}")
        
        # City
        city = address_components.get('city', '')
        if city:
            parts.append(city)
        
        # Province
        province = address_components.get('province', '')
        if province:
            parts.append(province)
        
        # Postal code
        postal_code = address_components.get('postal_code', '')
        if postal_code:
            parts.append(postal_code)
        
        return ', '.join(parts)
    
    @staticmethod
    def format_postal_code(postal_code: str) -> str:
        """Format Canadian postal code"""
        if not postal_code:
            return ""
        
        # Remove spaces and convert to uppercase
        clean = postal_code.replace(' ', '').upper()
        
        # Add space in middle if needed
        if len(clean) == 6:
            return f"{clean[:3]} {clean[3:]}"
        
        return clean
    
    @staticmethod
    def abbreviate_street_type(street_name: str) -> str:
        """Abbreviate common street types"""
        abbreviations = {
            'STREET': 'ST',
            'AVENUE': 'AVE',
            'ROAD': 'RD',
            'BOULEVARD': 'BLVD',
            'DRIVE': 'DR',
            'COURT': 'CT',
            'CRESCENT': 'CRES',
            'PLACE': 'PL',
            'LANE': 'LN',
            'CIRCLE': 'CIR'
        }
        
        upper_name = street_name.upper()
        for full, abbrev in abbreviations.items():
            upper_name = upper_name.replace(full, abbrev)
        
        return upper_name.title()


class ZoningFormatter:
    """Zoning information formatting utilities"""
    
    @staticmethod
    def format_zone_code(zone_code: str) -> str:
        """Format zoning code for display"""
        if not zone_code:
            return "Unknown"
        
        # Clean and format zone code
        clean = zone_code.strip().upper()
        
        # Add spacing for special provisions
        if ' SP:' in clean:
            parts = clean.split(' SP:')
            return f"{parts[0]} (SP:{parts[1]})"
        
        return clean
    
    @staticmethod
    def format_zone_description(zone_code: str) -> str:
        """Get human-readable zone description"""
        zone_descriptions = {
            'RL1': 'Residential Low Density 1 (Estate Lots)',
            'RL2': 'Residential Low Density 2 (Large Lots)',
            'RL3': 'Residential Low Density 3 (Medium Lots)',
            'RL4': 'Residential Low Density 4 (Medium Lots)',
            'RL5': 'Residential Low Density 5 (Medium Lots)',
            'RL6': 'Residential Low Density 6 (Small Lots)',
            'RL7': 'Residential Low Density 7 (Mixed)',
            'RL8': 'Residential Low Density 8 (Higher Density)',
            'RL9': 'Residential Low Density 9 (Higher Density)',
            'RL10': 'Residential Low Density 10 (Duplex)',
            'RL11': 'Residential Low Density 11 (Linked)',
            'RUC': 'Residential Uptown Core',
            'RM1': 'Residential Medium Density 1 (Townhouse)',
            'RM2': 'Residential Medium Density 2 (Back-to-Back)',
            'RM3': 'Residential Medium Density 3 (Stacked)',
            'RM4': 'Residential Medium Density 4 (Apartment)',
            'RH': 'Residential High Density'
        }
        
        base_zone = zone_code.split('-')[0].split(' ')[0]
        return zone_descriptions.get(base_zone, f"Zone {zone_code}")
    
    @staticmethod
    def format_permitted_uses(uses: List[str]) -> List[str]:
        """Format permitted uses for display"""
        formatted_uses = []
        
        for use in uses:
            # Convert underscores to spaces and title case
            formatted = use.replace('_', ' ').title()
            
            # Special formatting for common terms
            formatted = formatted.replace('Dwelling', 'Dwelling Unit')
            formatted = formatted.replace('Day Care', 'Daycare')
            formatted = formatted.replace('Home Occupation', 'Home Business')
            
            formatted_uses.append(formatted)
        
        return formatted_uses


class ReportFormatter:
    """Report generation formatting utilities"""
    
    @staticmethod
    def format_property_summary(property_data: Dict[str, Any]) -> Dict[str, str]:
        """Format property data for summary display"""
        summary = {}
        
        # Address
        if 'address' in property_data:
            summary['Address'] = property_data['address']
        
        # Coordinates
        if 'latitude' in property_data and 'longitude' in property_data:
            lat = property_data['latitude']
            lon = property_data['longitude']
            summary['Coordinates'] = f"{lat:.6f}, {lon:.6f}"
        
        # Lot area
        if 'lot_area' in property_data:
            summary['Lot Area'] = AreaFormatter.format_dual_area(
                property_data['lot_area']
            )
        
        # Building area
        if 'building_area' in property_data:
            summary['Building Area'] = AreaFormatter.format_dual_area(
                property_data['building_area']
            )
        
        # Bedrooms and bathrooms
        if 'bedrooms' in property_data:
            summary['Bedrooms'] = str(property_data['bedrooms'])
        
        if 'bathrooms' in property_data:
            summary['Bathrooms'] = str(property_data['bathrooms'])
        
        # Building age
        if 'age' in property_data:
            summary['Building Age'] = f"{property_data['age']} years"
        
        return summary
    
    @staticmethod
    def format_valuation_summary(valuation_data: Dict[str, Any]) -> Dict[str, str]:
        """Format valuation data for summary display"""
        summary = {}
        
        if 'estimated_value' in valuation_data:
            summary['Estimated Value'] = CurrencyFormatter.format_cad(
                valuation_data['estimated_value']
            )
        
        if 'confidence_range_low' in valuation_data and 'confidence_range_high' in valuation_data:
            summary['Value Range'] = CurrencyFormatter.format_price_range(
                valuation_data['confidence_range_low'],
                valuation_data['confidence_range_high']
            )
        
        if 'confidence_score' in valuation_data:
            summary['Confidence'] = PercentageFormatter.format_percentage(
                valuation_data['confidence_score']
            )
        
        if 'days_on_market_estimate' in valuation_data:
            summary['Est. Days on Market'] = f"{valuation_data['days_on_market_estimate']} days"
        
        return summary
    
    @staticmethod
    def format_development_summary(development_data: Dict[str, Any]) -> Dict[str, str]:
        """Format development analysis for summary display"""
        summary = {}
        
        if 'potential_units' in development_data:
            summary['Potential Units'] = str(development_data['potential_units'])
        
        if 'max_floor_area' in development_data:
            summary['Max Floor Area'] = AreaFormatter.format_area(
                development_data['max_floor_area']
            )
        
        if 'max_height' in development_data:
            summary['Max Height'] = f"{development_data['max_height']:.1f} m"
        
        if 'gross_profit' in development_data:
            summary['Development Profit'] = CurrencyFormatter.format_cad(
                development_data['gross_profit']
            )
        
        if 'profit_margin' in development_data:
            summary['Profit Margin'] = PercentageFormatter.format_percentage(
                development_data['profit_margin']
            )
        
        return summary


class NumberFormatter:
    """General number formatting utilities"""
    
    @staticmethod
    def format_large_number(number: Union[int, float], precision: int = 1) -> str:
        """Format large numbers with K, M, B suffixes"""
        if number is None:
            return "N/A"
        
        abs_number = abs(number)
        
        if abs_number >= 1_000_000_000:
            formatted = f"{number / 1_000_000_000:.{precision}f}B"
        elif abs_number >= 1_000_000:
            formatted = f"{number / 1_000_000:.{precision}f}M"
        elif abs_number >= 1_000:
            formatted = f"{number / 1_000:.{precision}f}K"
        else:
            formatted = f"{number:.{precision}f}"
        
        return formatted
    
    @staticmethod
    def format_decimal(number: Union[int, float], precision: int = 2) -> str:
        """Format decimal number with specified precision"""
        if number is None:
            return "N/A"
        
        if precision == 0:
            return f"{number:.0f}"
        else:
            return f"{number:.{precision}f}"
    
    @staticmethod
    def round_to_nearest(number: float, nearest: float = 1000) -> float:
        """Round number to nearest specified value"""
        if number is None:
            return None
        
        return round(number / nearest) * nearest