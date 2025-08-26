"""Data models for the Real Estate Analyzer"""

from .property import Property, PropertyDetails, Location
from .zoning import ZoningInfo, ZoningRegulations, DevelopmentPotential
from .valuation import ValuationResult, MarketComparable, DevelopmentProforma

__all__ = [
    'Property',
    'PropertyDetails', 
    'Location',
    'ZoningInfo',
    'ZoningRegulations',
    'DevelopmentPotential',
    'ValuationResult',
    'MarketComparable',
    'DevelopmentProforma'
]