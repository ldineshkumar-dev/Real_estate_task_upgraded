"""Valuation and financial analysis models"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class ValuationMethod(str, Enum):
    """Valuation methodology"""
    COMPARABLE_SALES = "comparable_sales"
    COST_APPROACH = "cost_approach"
    INCOME_APPROACH = "income_approach"
    AUTOMATED = "automated"
    HYBRID = "hybrid"


class MarketCondition(str, Enum):
    """Market condition"""
    HOT = "hot"
    BALANCED = "balanced"
    COOL = "cool"
    DECLINING = "declining"


class MarketComparable(BaseModel):
    """Comparable property for valuation"""
    address: str
    sale_price: float = Field(..., gt=0)
    sale_date: datetime
    lot_area: float = Field(..., gt=0)
    building_area: float = Field(..., gt=0)
    bedrooms: int = Field(..., ge=0)
    bathrooms: float = Field(..., ge=0)
    distance_km: float = Field(..., ge=0)
    similarity_score: float = Field(..., ge=0, le=1)
    price_per_sqm: float = Field(..., gt=0)
    
    @validator('similarity_score')
    def validate_similarity(cls, v):
        if v < 0 or v > 1:
            raise ValueError('Similarity score must be between 0 and 1')
        return v


class ValuationBreakdown(BaseModel):
    """Detailed valuation breakdown"""
    land_value: float = Field(..., ge=0)
    building_value: float = Field(..., ge=0)
    depreciation: float = Field(..., le=0)
    location_premium: float = Field(default=0)
    amenity_adjustments: Dict[str, float] = {}
    market_adjustment: float = Field(default=0)
    total_adjustments: float = Field(default=0)
    
    def get_base_value(self) -> float:
        """Get base value before adjustments"""
        return self.land_value + self.building_value + self.depreciation
    
    def get_final_value(self) -> float:
        """Get final value after all adjustments"""
        return self.get_base_value() + self.total_adjustments


class ValuationResult(BaseModel):
    """Property valuation result"""
    property_id: Optional[str] = None
    valuation_date: datetime = Field(default_factory=datetime.now)
    valuation_method: ValuationMethod
    estimated_value: float = Field(..., gt=0)
    confidence_score: float = Field(..., ge=0, le=1)
    confidence_range_low: float = Field(..., gt=0)
    confidence_range_high: float = Field(..., gt=0)
    breakdown: ValuationBreakdown
    comparables_used: List[MarketComparable] = []
    market_condition: MarketCondition = MarketCondition.BALANCED
    days_on_market_estimate: int = Field(21, ge=0)
    notes: List[str] = []
    
    @validator('confidence_range_low')
    def validate_range_low(cls, v, values):
        if 'estimated_value' in values and v > values['estimated_value']:
            raise ValueError('Low range cannot be higher than estimated value')
        return v
    
    @validator('confidence_range_high')
    def validate_range_high(cls, v, values):
        if 'estimated_value' in values and v < values['estimated_value']:
            raise ValueError('High range cannot be lower than estimated value')
        return v
    
    def get_price_per_sqft(self, building_area: float) -> float:
        """Calculate price per square foot"""
        sqft = building_area * 10.764  # Convert m² to sq ft
        return self.estimated_value / sqft if sqft > 0 else 0
    
    def get_confidence_spread(self) -> float:
        """Get confidence spread as percentage"""
        spread = self.confidence_range_high - self.confidence_range_low
        return (spread / self.estimated_value) * 100


class DevelopmentCosts(BaseModel):
    """Development cost breakdown"""
    land_acquisition: float = Field(..., ge=0)
    hard_costs: float = Field(..., ge=0, description="Construction costs")
    soft_costs: float = Field(..., ge=0, description="Permits, consultants, etc.")
    financing_costs: float = Field(..., ge=0)
    marketing_costs: float = Field(..., ge=0)
    contingency: float = Field(..., ge=0)
    total_costs: float = Field(..., ge=0)
    
    def get_cost_per_unit(self, units: int) -> float:
        """Get cost per unit"""
        return self.total_costs / units if units > 0 else 0


class DevelopmentRevenue(BaseModel):
    """Development revenue projection"""
    unit_count: int = Field(..., gt=0)
    avg_unit_price: float = Field(..., gt=0)
    gross_revenue: float = Field(..., gt=0)
    absorption_months: int = Field(12, gt=0)
    price_escalation: float = Field(0.03, ge=0, le=0.2)
    
    def get_monthly_absorption(self) -> float:
        """Get monthly absorption rate"""
        return self.unit_count / self.absorption_months if self.absorption_months > 0 else 0


class DevelopmentProforma(BaseModel):
    """Development pro forma analysis"""
    project_name: Optional[str] = None
    zone_code: str
    total_units: int = Field(..., gt=0)
    unit_mix: Dict[str, int] = {}  # e.g., {"1-bed": 10, "2-bed": 20}
    costs: DevelopmentCosts
    revenue: DevelopmentRevenue
    gross_profit: float = Field(..., description="Revenue minus costs")
    profit_margin: float = Field(..., description="Profit as percentage of revenue")
    return_on_investment: float = Field(..., description="ROI percentage")
    internal_rate_return: Optional[float] = None
    payback_period_months: int = Field(..., gt=0)
    feasible: bool = Field(..., description="Whether project meets minimum requirements")
    risk_factors: List[str] = []
    
    @validator('profit_margin')
    def validate_margin(cls, v):
        if v < -1 or v > 1:
            raise ValueError('Profit margin must be between -100% and 100%')
        return v
    
    def get_return_metrics(self) -> Dict[str, Any]:
        """Get key return metrics"""
        return {
            'gross_profit': self.gross_profit,
            'profit_margin_pct': self.profit_margin * 100,
            'roi_pct': self.return_on_investment * 100,
            'irr_pct': self.internal_rate_return * 100 if self.internal_rate_return else None,
            'payback_months': self.payback_period_months,
            'feasible': self.feasible
        }