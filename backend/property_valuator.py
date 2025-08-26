"""
Enhanced Property Valuator
Comprehensive property valuation engine integrating precise Oakville zoning analysis with market comparables
Includes accurate development potential calculations based on official by-law documentation
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from config import Config, ZoningConfig
from models.valuation import (
    ValuationResult, ValuationBreakdown, MarketComparable, 
    DevelopmentProforma, DevelopmentCosts, DevelopmentRevenue,
    ValuationMethod, MarketCondition
)
from models.zoning import DevelopmentPotential

logger = logging.getLogger(__name__)


class PropertyValuator:
    """Enhanced property valuation engine with precise zoning integration"""
    
    def __init__(self, zoning_analyzer=None):
        # Integrate with enhanced zoning analyzer
        self.zoning_analyzer = zoning_analyzer
        
        # Base land values per square meter by zone (CAD)
        self.base_land_values = {
            'RL1': 650,   # Large estate lots
            'RL2': 580,   # Large lots  
            'RL3': 520,   # Medium-large lots
            'RL4': 500,   # Medium lots
            'RL5': 480,   # Medium lots
            'RL6': 450,   # Small lots
            'RL7': 470,   # Mixed detached/semi
            'RL8': 420,   # Higher density low
            'RL9': 400,   # Higher density low
            'RL10': 490,  # Duplex potential
            'RL11': 460,  # Linked dwellings
            'RUC': 380,   # Uptown core
            'RM1': 350,   # Townhouse
            'RM2': 330,   # Back-to-back
            'RM3': 320,   # Stacked/apartment
            'RM4': 300,   # Higher density apartment
            'RH': 280     # High density
        }
        
        # Building values per square meter by type (CAD)
        self.building_values = {
            'detached_dwelling': 2800,
            'semi_detached_dwelling': 2600,
            'townhouse_dwelling': 2400,
            'back_to_back_townhouse': 2200,
            'stacked_townhouse': 2300,
            'apartment_dwelling': 2000,
            'luxury_finish': 3800,
            'standard_finish': 2800,
            'basic_finish': 2000
        }
        
        # Location adjustment factors
        self.location_factors = ZoningConfig.LOCATION_PREMIUMS
        
        # Market conditions
        self.market_adjustment = Config.DEFAULT_MARKET_ADJUSTMENT
        self.depreciation_rate = Config.DEFAULT_DEPRECIATION_RATE
        
    def estimate_property_value(self, 
                               zone_code: str,
                               lot_area: float,
                               building_area: float,
                               building_type: str = "detached_dwelling",
                               num_bedrooms: int = 3,
                               num_bathrooms: float = 2.5,
                               age_years: int = 10,
                               nearby_parks: int = 0,
                               nearby_schools: int = 0,
                               transit_distance: Optional[float] = None,
                               waterfront: bool = False,
                               heritage_designated: bool = False,
                               is_corner: bool = False,
                               renovation_year: Optional[int] = None,
                               market_condition: MarketCondition = MarketCondition.BALANCED) -> ValuationResult:
        """
        Comprehensive property valuation using multiple factors
        
        Args:
            zone_code: Zoning classification
            lot_area: Lot area in square meters
            building_area: Building area in square meters
            building_type: Type of building
            num_bedrooms: Number of bedrooms
            num_bathrooms: Number of bathrooms
            age_years: Building age in years
            nearby_parks: Number of parks within 1km
            nearby_schools: Number of schools within 1km
            transit_distance: Distance to transit in meters
            waterfront: Is waterfront property
            heritage_designated: Has heritage designation
            is_corner: Is corner lot
            renovation_year: Year of major renovation
            market_condition: Current market condition
            
        Returns:
            ValuationResult with detailed breakdown
        """
        
        # Parse zone for base calculations
        base_zone = self._parse_base_zone(zone_code)
        
        # Calculate base land value
        land_value_per_sqm = self.base_land_values.get(base_zone, 500)
        base_land_value = lot_area * land_value_per_sqm
        
        # Calculate building value with depreciation
        building_value = self._calculate_building_value(
            building_area, building_type, age_years, renovation_year
        )
        
        # Calculate feature adjustments
        feature_adjustments = self._calculate_feature_adjustments(
            base_land_value, num_bedrooms, num_bathrooms
        )
        
        # Calculate location adjustments
        location_adjustments = self._calculate_location_adjustments(
            base_land_value, nearby_parks, nearby_schools, transit_distance,
            waterfront, heritage_designated, is_corner
        )
        
        # Apply market condition adjustment
        market_adj_value = self._apply_market_adjustment(
            base_land_value + building_value, market_condition
        )
        
        # Calculate total adjustments
        total_adjustments = sum(feature_adjustments.values()) + sum(location_adjustments.values()) + market_adj_value
        
        # Calculate final value
        base_value = base_land_value + building_value
        estimated_value = base_value + total_adjustments
        
        # Calculate confidence range
        confidence_score = self._calculate_confidence_score(
            zone_code, nearby_parks, heritage_designated
        )
        confidence_range = self._calculate_confidence_range(estimated_value, confidence_score)
        
        # Create breakdown
        breakdown = ValuationBreakdown(
            land_value=base_land_value,
            building_value=building_value,
            depreciation=self._calculate_depreciation(building_area, building_type, age_years),
            location_premium=sum(location_adjustments.values()),
            amenity_adjustments=feature_adjustments,
            market_adjustment=market_adj_value,
            total_adjustments=total_adjustments
        )
        
        # Estimate days on market
        days_on_market = self._estimate_days_on_market(estimated_value, market_condition, zone_code)
        
        return ValuationResult(
            valuation_method=ValuationMethod.AUTOMATED,
            estimated_value=max(0, estimated_value),
            confidence_score=confidence_score,
            confidence_range_low=confidence_range[0],
            confidence_range_high=confidence_range[1],
            breakdown=breakdown,
            market_condition=market_condition,
            days_on_market_estimate=days_on_market,
            notes=self._generate_valuation_notes(zone_code, heritage_designated, waterfront)
        )
    
    def _parse_base_zone(self, zone_code: str) -> str:
        """Extract base zone from complex zone code"""
        # Remove special provisions and suffix zones
        clean_zone = zone_code.split(' ')[0].split('-')[0]
        return clean_zone
    
    def _calculate_building_value(self, building_area: float, building_type: str, 
                                 age_years: int, renovation_year: Optional[int]) -> float:
        """Calculate building value with depreciation"""
        base_value_per_sqm = self.building_values.get(building_type, 2800)
        base_building_value = building_area * base_value_per_sqm
        
        # Apply age depreciation
        effective_age = age_years
        if renovation_year:
            current_year = datetime.now().year
            years_since_reno = current_year - renovation_year
            # Use lesser of actual age or years since major renovation
            effective_age = min(age_years, years_since_reno)
        
        # Cap depreciation at 40 years
        depreciation_years = min(effective_age, Config.MAX_DEPRECIATION_YEARS)
        depreciation_factor = 1 - (depreciation_years * self.depreciation_rate)
        depreciation_factor = max(0.3, depreciation_factor)  # Don't depreciate below 30%
        
        return base_building_value * depreciation_factor
    
    def _calculate_depreciation(self, building_area: float, building_type: str, age_years: int) -> float:
        """Calculate depreciation amount (negative value)"""
        base_value_per_sqm = self.building_values.get(building_type, 2800)
        base_building_value = building_area * base_value_per_sqm
        
        depreciation_years = min(age_years, Config.MAX_DEPRECIATION_YEARS)
        depreciation_amount = base_building_value * depreciation_years * self.depreciation_rate
        
        return -min(depreciation_amount, base_building_value * 0.7)  # Max 70% depreciation
    
    def _calculate_feature_adjustments(self, base_land_value: float, 
                                     bedrooms: int, bathrooms: float) -> Dict[str, float]:
        """Calculate adjustments for property features"""
        adjustments = {}
        
        # Bedroom adjustments (premium for 4+ bedrooms, discount for fewer than 3)
        if bedrooms >= 4:
            adjustments['extra_bedrooms'] = (bedrooms - 3) * 15000
        elif bedrooms < 3:
            adjustments['fewer_bedrooms'] = (bedrooms - 3) * 10000
        else:
            adjustments['bedrooms'] = 0
        
        # Bathroom adjustments (premium for 3+ bathrooms)
        if bathrooms >= 3:
            adjustments['extra_bathrooms'] = (bathrooms - 2.5) * 8000
        elif bathrooms < 2:
            adjustments['fewer_bathrooms'] = (bathrooms - 2.5) * 6000
        else:
            adjustments['bathrooms'] = 0
        
        return adjustments
    
    def _calculate_location_adjustments(self, base_land_value: float,
                                      nearby_parks: int, nearby_schools: int,
                                      transit_distance: Optional[float],
                                      waterfront: bool, heritage_designated: bool,
                                      is_corner: bool) -> Dict[str, float]:
        """Calculate location-based adjustments"""
        adjustments = {}
        
        # Park proximity premium
        if nearby_parks > 0:
            park_premium = min(nearby_parks * 0.02, 0.10)  # Max 10% premium
            adjustments['parks'] = base_land_value * park_premium
        
        # School proximity premium
        if nearby_schools > 0:
            school_premium = min(nearby_schools * 0.015, 0.08)  # Max 8% premium
            adjustments['schools'] = base_land_value * school_premium
        
        # Transit accessibility
        if transit_distance is not None:
            if transit_distance <= 500:  # Within 500m
                adjustments['transit'] = base_land_value * 0.12
            elif transit_distance <= 1000:  # Within 1km
                adjustments['transit'] = base_land_value * 0.06
            else:
                adjustments['transit'] = 0
        
        # Special location factors
        if waterfront:
            adjustments['waterfront'] = base_land_value * self.location_factors['waterfront']
        
        if heritage_designated:
            adjustments['heritage'] = base_land_value * self.location_factors['heritage_designated']
        
        if is_corner:
            adjustments['corner_lot'] = base_land_value * self.location_factors['corner_lot']
        
        return adjustments
    
    def _apply_market_adjustment(self, base_value: float, market_condition: MarketCondition) -> float:
        """Apply market condition adjustment"""
        if market_condition == MarketCondition.HOT:
            return base_value * 0.08  # 8% premium
        elif market_condition == MarketCondition.COOL:
            return base_value * -0.05  # 5% discount
        elif market_condition == MarketCondition.DECLINING:
            return base_value * -0.12  # 12% discount
        else:  # Balanced
            return base_value * 0.02  # 2% moderate premium
    
    def _calculate_confidence_score(self, zone_code: str, nearby_parks: int, 
                                   heritage_designated: bool) -> float:
        """Calculate confidence score for valuation"""
        base_confidence = 0.75
        
        # Higher confidence for common residential zones
        if zone_code.startswith(('RL', 'RM')):
            base_confidence += 0.10
        
        # Lower confidence for unusual zones or heritage properties
        if heritage_designated:
            base_confidence -= 0.15
        
        # Higher confidence with more comparable data (proxied by nearby parks)
        if nearby_parks >= 2:
            base_confidence += 0.05
        
        return max(0.5, min(0.95, base_confidence))
    
    def _calculate_confidence_range(self, estimated_value: float, confidence_score: float) -> Tuple[float, float]:
        """Calculate confidence range around estimated value"""
        # Lower confidence = wider range
        range_factor = (1 - confidence_score) * 0.3  # Max 30% range for lowest confidence
        
        low_value = estimated_value * (1 - range_factor)
        high_value = estimated_value * (1 + range_factor)
        
        return (low_value, high_value)
    
    def _estimate_days_on_market(self, estimated_value: float, market_condition: MarketCondition, 
                                zone_code: str) -> int:
        """Estimate days on market based on value and market conditions"""
        base_days = 28  # Base estimate
        
        # Market condition adjustments
        if market_condition == MarketCondition.HOT:
            base_days = 14
        elif market_condition == MarketCondition.COOL:
            base_days = 42
        elif market_condition == MarketCondition.DECLINING:
            base_days = 65
        
        # Price range adjustments
        if estimated_value > 2000000:  # Luxury market
            base_days += 21
        elif estimated_value > 1500000:  # High-end
            base_days += 14
        elif estimated_value < 800000:  # Entry-level
            base_days -= 7
        
        # Zone desirability
        if zone_code in ['RL1', 'RL2']:  # Premium zones
            base_days -= 7
        elif zone_code.startswith('RM'):  # Medium density
            base_days += 7
        
        return max(7, base_days)  # Minimum 1 week
    
    def _generate_valuation_notes(self, zone_code: str, heritage_designated: bool, 
                                 waterfront: bool) -> List[str]:
        """Generate valuation notes and disclaimers"""
        notes = []
        
        if heritage_designated:
            notes.append("Heritage designation may restrict development and affect value")
        
        if waterfront:
            notes.append("Waterfront premium applied - verify actual water access")
        
        if '-0' in zone_code:
            notes.append("Subject to -0 suffix zone restrictions affecting development potential")
        
        notes.append("Valuation is estimate only - professional appraisal recommended")
        notes.append("Market conditions subject to change - values updated monthly")
        
        return notes
    
    def calculate_development_value(self, zone_code: str, lot_area: float,
                                   development_potential: DevelopmentPotential,
                                   current_property_value: float) -> DevelopmentProforma:
        """
        Calculate development value and feasibility analysis
        
        Args:
            zone_code: Zoning classification
            lot_area: Lot area in square meters
            development_potential: Development potential analysis
            current_property_value: Current property value
            
        Returns:
            DevelopmentProforma with complete financial analysis
        """
        
        if development_potential.potential_units <= 1:
            # Single family - limited redevelopment potential
            return self._create_single_family_proforma(
                zone_code, current_property_value, development_potential
            )
        
        # Multi-unit development analysis
        return self._create_multi_unit_proforma(
            zone_code, lot_area, development_potential, current_property_value
        )
    
    def _create_single_family_proforma(self, zone_code: str, current_value: float,
                                      development_potential: DevelopmentPotential) -> DevelopmentProforma:
        """Create proforma for single family redevelopment"""
        
        # Estimate new construction value
        max_floor_area = development_potential.max_floor_area
        construction_cost_per_sqm = ZoningConfig.CONSTRUCTION_COSTS.get('detached_dwelling', 2500)
        
        # Calculate costs
        land_cost = current_value
        hard_costs = max_floor_area * construction_cost_per_sqm
        soft_costs = hard_costs * ZoningConfig.SOFT_COST_PERCENTAGES['total']
        total_costs = land_cost + hard_costs + soft_costs
        
        # Calculate revenue (estimated sale price)
        base_zone = self._parse_base_zone(zone_code)
        estimated_price_per_sqm = self.building_values.get('detached_dwelling', 2800) * 1.4  # Include profit margin
        gross_revenue = max_floor_area * estimated_price_per_sqm
        
        # Calculate returns
        gross_profit = gross_revenue - total_costs
        profit_margin = gross_profit / gross_revenue if gross_revenue > 0 else 0
        roi = gross_profit / total_costs if total_costs > 0 else 0
        
        # Development timeline
        timeline_months = 12  # Typical single family
        
        return DevelopmentProforma(
            zone_code=zone_code,
            total_units=1,
            unit_mix={"detached_house": 1},
            costs=DevelopmentCosts(
                land_acquisition=land_cost,
                hard_costs=hard_costs,
                soft_costs=soft_costs,
                financing_costs=total_costs * 0.04,  # 4% financing
                marketing_costs=gross_revenue * 0.02,  # 2% marketing
                contingency=hard_costs * 0.05,  # 5% contingency
                total_costs=total_costs
            ),
            revenue=DevelopmentRevenue(
                unit_count=1,
                avg_unit_price=gross_revenue,
                gross_revenue=gross_revenue,
                absorption_months=3,  # Single house sells quickly
                price_escalation=0.03
            ),
            gross_profit=gross_profit,
            profit_margin=profit_margin,
            return_on_investment=roi,
            payback_period_months=timeline_months,
            feasible=profit_margin >= Config.MIN_PROFIT_MARGIN,
            risk_factors=self._identify_development_risks(zone_code, 1)
        )
    
    def _create_multi_unit_proforma(self, zone_code: str, lot_area: float,
                                   development_potential: DevelopmentPotential,
                                   current_value: float) -> DevelopmentProforma:
        """Create proforma for multi-unit development"""
        
        units = development_potential.potential_units
        total_floor_area = development_potential.max_floor_area
        
        # Determine unit type and pricing
        unit_type, avg_unit_price = self._determine_unit_characteristics(zone_code, total_floor_area / units)
        
        # Calculate construction costs
        construction_cost_per_sqm = ZoningConfig.CONSTRUCTION_COSTS.get(unit_type, 2000)
        
        # Calculate costs
        land_cost = current_value
        hard_costs = total_floor_area * construction_cost_per_sqm
        soft_costs = hard_costs * ZoningConfig.SOFT_COST_PERCENTAGES['total']
        financing_costs = (land_cost + hard_costs) * 0.06  # 6% financing for multi-unit
        marketing_costs = (units * avg_unit_price) * 0.03  # 3% marketing
        contingency = hard_costs * 0.08  # 8% contingency for multi-unit
        
        total_costs = land_cost + hard_costs + soft_costs + financing_costs + marketing_costs + contingency
        
        # Calculate revenue
        gross_revenue = units * avg_unit_price
        
        # Calculate returns
        gross_profit = gross_revenue - total_costs
        profit_margin = gross_profit / gross_revenue if gross_revenue > 0 else 0
        roi = gross_profit / total_costs if total_costs > 0 else 0
        
        # Development timeline (longer for multi-unit)
        timeline_months = 18 + (units // 10) * 6  # Base 18 months + 6 months per 10 units
        
        # Absorption analysis
        absorption_months = max(6, units // 2)  # Assume 2 units per month absorption
        
        return DevelopmentProforma(
            project_name=f"{zone_code} Multi-Unit Development",
            zone_code=zone_code,
            total_units=units,
            unit_mix={unit_type: units},
            costs=DevelopmentCosts(
                land_acquisition=land_cost,
                hard_costs=hard_costs,
                soft_costs=soft_costs,
                financing_costs=financing_costs,
                marketing_costs=marketing_costs,
                contingency=contingency,
                total_costs=total_costs
            ),
            revenue=DevelopmentRevenue(
                unit_count=units,
                avg_unit_price=avg_unit_price,
                gross_revenue=gross_revenue,
                absorption_months=absorption_months,
                price_escalation=0.03
            ),
            gross_profit=gross_profit,
            profit_margin=profit_margin,
            return_on_investment=roi,
            payback_period_months=timeline_months + absorption_months,
            feasible=profit_margin >= Config.MIN_PROFIT_MARGIN,
            risk_factors=self._identify_development_risks(zone_code, units)
        )
    
    def _determine_unit_characteristics(self, zone_code: str, avg_unit_size: float) -> Tuple[str, float]:
        """Determine unit type and average price based on zone and size"""
        base_zone = self._parse_base_zone(zone_code)
        
        # Unit type mapping
        if base_zone == 'RM1':
            unit_type = 'townhouse'
            base_price_per_sqm = 4200
        elif base_zone == 'RM2':
            unit_type = 'back_to_back_townhouse'
            base_price_per_sqm = 3800
        elif base_zone == 'RM3':
            unit_type = 'stacked_townhouse'
            base_price_per_sqm = 3600
        elif base_zone == 'RM4':
            unit_type = 'apartment'
            base_price_per_sqm = 3400
        elif base_zone == 'RUC':
            unit_type = 'townhouse'
            base_price_per_sqm = 4000
        else:
            unit_type = 'townhouse'
            base_price_per_sqm = 3800
        
        # Calculate average unit price
        avg_unit_price = avg_unit_size * base_price_per_sqm
        
        return unit_type, avg_unit_price
    
    def _identify_development_risks(self, zone_code: str, units: int) -> List[str]:
        """Identify development risk factors"""
        risks = []
        
        if '-0' in zone_code:
            risks.append("Suffix zone restrictions may limit development")
        
        if units > 10:
            risks.append("Large project requires experienced developer")
            risks.append("Market absorption risk for multiple units")
        
        if zone_code.startswith('RM'):
            risks.append("Medium density requires higher construction standards")
        
        risks.extend([
            "Construction cost escalation risk",
            "Municipal approval timeline risk",
            "Interest rate fluctuation risk",
            "Market condition changes during development"
        ])
        
        return risks
    
    def generate_comparable_analysis(self, target_property: Dict, 
                                   comparables: List[Dict]) -> List[MarketComparable]:
        """Generate comparable property analysis (placeholder for real MLS integration)"""
        # This would integrate with real MLS data in production
        # For now, generate sample comparables
        
        sample_comparables = []
        base_price = target_property.get('estimated_value', 1000000)
        
        for i in range(3):
            comparable = MarketComparable(
                address=f"Sample Comparable {i+1}",
                sale_price=base_price * (0.9 + i * 0.1),
                sale_date=datetime.now() - timedelta(days=30 * (i+1)),
                lot_area=target_property.get('lot_area', 500) * (0.8 + i * 0.2),
                building_area=target_property.get('building_area', 200) * (0.9 + i * 0.1),
                bedrooms=target_property.get('bedrooms', 3),
                bathrooms=target_property.get('bathrooms', 2.5),
                distance_km=0.5 + i * 0.3,
                similarity_score=0.85 - i * 0.05,
                price_per_sqm=base_price / target_property.get('building_area', 200)
            )
            sample_comparables.append(comparable)
        
        return sample_comparables
    
    def estimate_comprehensive_property_value(self, 
                                             address: str,
                                             zone_code: str,
                                             lot_area: float,
                                             lot_frontage: float,
                                             lot_depth: Optional[float] = None,
                                             building_area: float = 0,
                                             building_type: str = "detached_dwelling",
                                             is_corner: bool = False,
                                             has_garage: bool = False,
                                             existing_building_age: int = 10,
                                             development_scenario: str = "current_use") -> Dict[str, Any]:
        """
        Comprehensive property valuation using enhanced zoning analysis
        
        Args:
            address: Property address
            zone_code: Full zone code including special provisions (e.g., 'RL2 SP:1')
            lot_area: Lot area in square meters
            lot_frontage: Lot frontage in meters
            lot_depth: Lot depth in meters (calculated if not provided)
            building_area: Existing building area in square meters
            building_type: Type of existing building
            is_corner: Whether this is a corner lot
            has_garage: Whether property has an attached garage
            existing_building_age: Age of existing building
            development_scenario: 'current_use', 'redevelopment', or 'maximize_density'
            
        Returns:
            Comprehensive valuation analysis
        """
        
        if not self.zoning_analyzer:
            logger.warning("No zoning analyzer available - using basic valuation")
            return self._basic_valuation_fallback(zone_code, lot_area, building_area)
        
        # Calculate lot depth if not provided
        if lot_depth is None:
            lot_depth = lot_area / lot_frontage if lot_frontage > 0 else 30.0
        
        # Get comprehensive development potential analysis
        development_potential = self.zoning_analyzer.analyze_development_potential(
            zone_code=zone_code,
            lot_area=lot_area,
            lot_frontage=lot_frontage,
            lot_depth=lot_depth,
            is_corner=is_corner,
            building_height=7.0  # Assume 7m for initial analysis
        )
        
        # Get precise setbacks
        precise_setbacks = self.zoning_analyzer.calculate_precise_setbacks(
            zone_code=zone_code,
            lot_frontage=lot_frontage,
            lot_depth=lot_depth,
            is_corner=is_corner,
            has_garage=has_garage
        )
        
        # Calculate precise FAR
        precise_far = self.zoning_analyzer.calculate_precise_floor_area_ratio(
            zone_code=zone_code,
            lot_area=lot_area
        )
        
        # Base property valuation
        current_use_value = self.estimate_property_value(
            zone_code=zone_code,
            lot_area=lot_area,
            building_area=building_area,
            building_type=building_type,
            age_years=existing_building_age,
            is_corner=is_corner
        )
        
        # Development scenarios
        scenarios = {}
        
        # Current use value
        scenarios['current_use'] = {
            'estimated_value': current_use_value.estimated_value,
            'description': 'Property value with existing use',
            'floor_area': building_area,
            'details': current_use_value
        }
        
        # Redevelopment scenario (single family replacement)
        if development_potential.max_floor_area > building_area:
            redevelopment_value = self._calculate_redevelopment_value(
                zone_code, lot_area, development_potential, current_use_value.estimated_value
            )
            scenarios['redevelopment'] = {
                'estimated_value': redevelopment_value['gross_development_value'],
                'description': 'New single family home maximizing zoning',
                'floor_area': development_potential.max_floor_area,
                'details': redevelopment_value
            }
        
        # Maximum density scenario
        if development_potential.potential_units > 1:
            max_density_value = self._calculate_multi_unit_value(
                zone_code, lot_area, development_potential, current_use_value.estimated_value
            )
            scenarios['maximize_density'] = {
                'estimated_value': max_density_value['gross_development_value'],
                'description': f'Multi-unit development ({development_potential.potential_units} units)',
                'floor_area': development_potential.max_floor_area,
                'units': development_potential.potential_units,
                'details': max_density_value
            }
        
        # Calculate highest and best use
        highest_value = max(scenarios.values(), key=lambda x: x['estimated_value'])
        highest_use = next(k for k, v in scenarios.items() if v == highest_value)
        
        return {
            'address': address,
            'zone_code': zone_code,
            'lot_dimensions': {
                'area_sqm': lot_area,
                'area_sqft': lot_area * 10.764,
                'frontage_m': lot_frontage,
                'frontage_ft': lot_frontage * 3.281,
                'depth_m': lot_depth,
                'depth_ft': lot_depth * 3.281
            },
            'zoning_analysis': {
                'development_potential': development_potential,
                'precise_setbacks': precise_setbacks,
                'max_floor_area_ratio': precise_far,
                'max_floor_area_sqm': development_potential.max_floor_area,
                'max_floor_area_sqft': development_potential.max_floor_area * 10.764,
                'max_building_footprint_sqm': development_potential.max_building_footprint,
                'max_building_footprint_sqft': development_potential.max_building_footprint * 10.764,
                'buildable_area_sqm': development_potential.buildable_area,
                'buildable_area_sqft': development_potential.buildable_area * 10.764
            },
            'valuation_scenarios': scenarios,
            'highest_and_best_use': {
                'scenario': highest_use,
                'value': highest_value['estimated_value'],
                'description': highest_value['description']
            },
            'development_constraints': development_potential.constraints,
            'development_opportunities': development_potential.opportunities,
            'analysis_date': datetime.now().isoformat(),
            'confidence_factors': self._assess_analysis_confidence(zone_code, development_potential)
        }
    
    def _basic_valuation_fallback(self, zone_code: str, lot_area: float, building_area: float) -> Dict[str, Any]:
        """Fallback valuation when zoning analyzer is not available"""
        basic_value = self.estimate_property_value(
            zone_code=zone_code,
            lot_area=lot_area,
            building_area=building_area
        )
        
        return {
            'estimated_value': basic_value.estimated_value,
            'method': 'basic_valuation',
            'note': 'Enhanced zoning analysis not available'
        }
    
    def _calculate_redevelopment_value(self, zone_code: str, lot_area: float, 
                                     development_potential, current_value: float) -> Dict[str, float]:
        """Calculate redevelopment value for single family home"""
        max_floor_area = development_potential.max_floor_area
        
        # Construction costs
        construction_cost_per_sqm = ZoningConfig.CONSTRUCTION_COSTS.get('detached_dwelling', 2500)
        hard_costs = max_floor_area * construction_cost_per_sqm
        soft_costs = hard_costs * ZoningConfig.SOFT_COST_PERCENTAGES['total']
        
        # Land costs (acquisition + demolition)
        land_costs = current_value + 50000  # Assume $50k demolition
        
        total_development_cost = land_costs + hard_costs + soft_costs
        
        # Revenue calculation
        base_zone = self._parse_base_zone(zone_code)
        price_per_sqm = self.building_values.get('detached_dwelling', 2800) * 1.5  # Market premium
        
        # Apply zone premium
        zone_premiums = {'RL1': 1.2, 'RL2': 1.15, 'RL3': 1.1, 'RL4': 1.05, 'RL5': 1.05, 'RL6': 1.0}
        price_per_sqm *= zone_premiums.get(base_zone, 1.0)
        
        gross_revenue = max_floor_area * price_per_sqm
        gross_profit = gross_revenue - total_development_cost
        profit_margin = gross_profit / gross_revenue if gross_revenue > 0 else 0
        
        return {
            'gross_development_value': gross_revenue,
            'total_development_cost': total_development_cost,
            'gross_profit': gross_profit,
            'profit_margin': profit_margin,
            'land_costs': land_costs,
            'construction_costs': hard_costs + soft_costs,
            'feasible': profit_margin >= 0.15  # 15% minimum margin
        }
    
    def _calculate_multi_unit_value(self, zone_code: str, lot_area: float,
                                   development_potential, current_value: float) -> Dict[str, float]:
        """Calculate multi-unit development value"""
        units = development_potential.potential_units
        total_floor_area = development_potential.max_floor_area
        avg_unit_size = total_floor_area / units
        
        # Determine unit type and pricing
        unit_type, avg_unit_price = self._determine_unit_characteristics(zone_code, avg_unit_size)
        
        # Construction costs (higher for multi-unit)
        construction_cost_per_sqm = ZoningConfig.CONSTRUCTION_COSTS.get(unit_type, 2200)
        hard_costs = total_floor_area * construction_cost_per_sqm
        soft_costs = hard_costs * (ZoningConfig.SOFT_COST_PERCENTAGES['total'] + 0.1)  # 10% higher for multi-unit
        
        # Land and demolition costs
        land_costs = current_value + 75000  # Higher demolition for multi-unit
        
        total_development_cost = land_costs + hard_costs + soft_costs
        
        # Revenue calculation
        gross_revenue = units * avg_unit_price
        gross_profit = gross_revenue - total_development_cost
        profit_margin = gross_profit / gross_revenue if gross_revenue > 0 else 0
        
        return {
            'gross_development_value': gross_revenue,
            'total_development_cost': total_development_cost,
            'gross_profit': gross_profit,
            'profit_margin': profit_margin,
            'units': units,
            'avg_unit_price': avg_unit_price,
            'avg_unit_size_sqm': avg_unit_size,
            'avg_unit_size_sqft': avg_unit_size * 10.764,
            'feasible': profit_margin >= 0.20  # 20% minimum margin for multi-unit
        }
    
    def _assess_analysis_confidence(self, zone_code: str, development_potential) -> Dict[str, Any]:
        """Assess confidence in the analysis"""
        confidence_factors = {
            'zoning_certainty': 0.9 if not development_potential.constraints else 0.7,
            'market_data_quality': 0.8,  # Would be based on actual comparable data
            'regulatory_risk': 0.9 if '-0' not in zone_code else 0.7,
            'development_complexity': 0.9 if development_potential.potential_units == 1 else 0.6
        }
        
        overall_confidence = sum(confidence_factors.values()) / len(confidence_factors)
        
        return {
            'overall_confidence': overall_confidence,
            'factors': confidence_factors,
            'confidence_level': 'High' if overall_confidence >= 0.8 else 'Medium' if overall_confidence >= 0.6 else 'Low'
        }