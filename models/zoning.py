"""Zoning data models based on Oakville By-law 2014-014"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class ZoneType(str, Enum):
    """Zone type enumeration"""
    RL1 = "RL1"
    RL2 = "RL2"
    RL3 = "RL3"
    RL4 = "RL4"
    RL5 = "RL5"
    RL6 = "RL6"
    RL7 = "RL7"
    RL8 = "RL8"
    RL9 = "RL9"
    RL10 = "RL10"
    RL11 = "RL11"
    RUC = "RUC"
    RM1 = "RM1"
    RM2 = "RM2"
    RM3 = "RM3"
    RM4 = "RM4"
    RH = "RH"


class PermittedUse(str, Enum):
    """Permitted uses enumeration"""
    DETACHED_DWELLING = "detached_dwelling"
    SEMI_DETACHED = "semi_detached_dwelling"
    DUPLEX = "duplex_dwelling"
    TOWNHOUSE = "townhouse_dwelling"
    BACK_TO_BACK_TOWNHOUSE = "back_to_back_townhouse"
    STACKED_TOWNHOUSE = "stacked_townhouse"
    APARTMENT = "apartment_dwelling"
    LINKED = "linked_dwelling"
    ADDITIONAL_UNIT = "additional_residential_unit"
    HOME_OCCUPATION = "home_occupation"
    BED_BREAKFAST = "bed_and_breakfast"
    DAY_CARE = "day_care"
    CONSERVATION = "conservation_use"
    PARK = "park_public"


class Setbacks(BaseModel):
    """Property setback requirements"""
    front_yard: float = Field(..., ge=0, description="Minimum front yard in meters")
    rear_yard: float = Field(..., ge=0, description="Minimum rear yard in meters")
    interior_side_left: float = Field(..., ge=0, description="Minimum left side yard in meters")
    interior_side_right: float = Field(..., ge=0, description="Minimum right side yard in meters")
    flankage_yard: Optional[float] = Field(None, ge=0, description="Minimum flankage yard for corner lots")
    
    def get_total_side_setback(self) -> float:
        """Get total side setback"""
        return self.interior_side_left + self.interior_side_right


class ZoningRegulations(BaseModel):
    """Complete zoning regulations for a zone"""
    zone_code: str
    zone_name: str
    zone_category: str  # Residential Low, Medium, High, etc.
    min_lot_area: float = Field(..., gt=0, description="Minimum lot area in square meters")
    min_lot_frontage: float = Field(..., gt=0, description="Minimum lot frontage in meters")
    setbacks: Setbacks
    max_height: float = Field(..., gt=0, description="Maximum height in meters")
    max_storeys: Optional[int] = Field(None, gt=0, le=50)
    max_lot_coverage: Optional[float] = Field(None, gt=0, le=1, description="Maximum lot coverage ratio")
    max_floor_area_ratio: Optional[float] = Field(None, gt=0, description="Maximum floor area ratio")
    min_lot_area_per_unit: Optional[float] = Field(None, gt=0, description="For multi-unit developments")
    permitted_uses: List[str]
    special_provisions: List[str] = []
    suffix_zone: Optional[str] = None  # e.g., "-0"
    
    @validator('max_lot_coverage')
    def validate_lot_coverage(cls, v):
        if v is not None and (v <= 0 or v > 1):
            raise ValueError('Lot coverage must be between 0 and 1')
        return v
    
    def applies_to_lot(self, lot_area: float, lot_frontage: float) -> bool:
        """Check if regulations apply to a given lot"""
        return (lot_area >= self.min_lot_area and 
                lot_frontage >= self.min_lot_frontage)


class DevelopmentPotential(BaseModel):
    """Development potential analysis result"""
    zone_code: str
    zone_name: str
    meets_minimum_requirements: bool
    max_building_footprint: float = Field(..., ge=0, description="Maximum building footprint in square meters")
    max_floor_area: float = Field(..., ge=0, description="Maximum total floor area in square meters")
    max_height: float = Field(..., ge=0, description="Maximum height in meters")
    max_storeys: Optional[int]
    buildable_area: float = Field(..., ge=0, description="Buildable area after setbacks")
    potential_units: int = Field(1, ge=1, description="Number of potential dwelling units")
    permitted_uses: List[str]
    constraints: List[str] = []
    opportunities: List[str] = []
    
    def get_efficiency_ratio(self) -> float:
        """Calculate efficiency ratio (buildable/total)"""
        if self.max_building_footprint > 0:
            return self.buildable_area / self.max_building_footprint
        return 0


class ZoningInfo(BaseModel):
    """Complete zoning information for a property"""
    zone_code: str
    zone_class: Optional[str] = None
    special_provision: Optional[str] = None
    regulations: Optional[ZoningRegulations] = None
    development_potential: Optional[DevelopmentPotential] = None
    nearby_developments: List[Dict[str, Any]] = []
    heritage_status: Optional[str] = None
    environmental_constraints: List[str] = []
    
    def has_development_restrictions(self) -> bool:
        """Check if there are development restrictions"""
        return (bool(self.heritage_status) or 
                bool(self.environmental_constraints) or
                self.zone_code.endswith('-0'))
    
    def get_summary(self) -> Dict[str, Any]:
        """Get zoning summary"""
        return {
            'zone': self.zone_code,
            'class': self.zone_class,
            'special_provision': self.special_provision,
            'has_restrictions': self.has_development_restrictions(),
            'potential_units': self.development_potential.potential_units if self.development_potential else 1,
            'max_height': self.regulations.max_height if self.regulations else None
        }