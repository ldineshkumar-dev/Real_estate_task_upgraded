"""Property data models"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime


class Location(BaseModel):
    """Location model"""
    address: Optional[str] = None
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    city: str = "Oakville"
    province: str = "ON"
    postal_code: Optional[str] = None
    
    @validator('postal_code')
    def validate_postal_code(cls, v):
        if v and not v.replace(' ', '').replace('-', '').isalnum():
            raise ValueError('Invalid postal code format')
        return v


class PropertyDetails(BaseModel):
    """Property physical details"""
    lot_area: float = Field(..., gt=0, le=100000, description="Lot area in square meters")
    lot_frontage: Optional[float] = Field(None, gt=0, le=1000, description="Lot frontage in meters")
    lot_depth: Optional[float] = Field(None, gt=0, le=1000, description="Lot depth in meters")
    building_area: float = Field(..., gt=0, le=10000, description="Building area in square meters")
    bedrooms: int = Field(3, ge=0, le=20)
    bathrooms: float = Field(2.5, ge=0, le=10)
    parking_spaces: int = Field(2, ge=0, le=10)
    building_age: int = Field(10, ge=0, le=300)
    building_type: str = Field("detached_dwelling", description="Type of building")
    is_corner_lot: bool = False
    has_basement: bool = True
    basement_finished: bool = False
    renovation_year: Optional[int] = None
    
    @validator('bathrooms')
    def validate_bathrooms(cls, v):
        # Ensure bathrooms are in 0.5 increments
        if v % 0.5 != 0:
            raise ValueError('Bathrooms must be in 0.5 increments')
        return v
    
    @validator('renovation_year')
    def validate_renovation_year(cls, v, values):
        if v is not None:
            current_year = datetime.now().year
            building_age = values.get('building_age', 0)
            construction_year = current_year - building_age
            if v < construction_year or v > current_year:
                raise ValueError(f'Renovation year must be between {construction_year} and {current_year}')
        return v


class PropertyAmenities(BaseModel):
    """Property amenities and features"""
    nearby_parks: int = Field(0, ge=0, description="Number of parks within 1km")
    nearby_schools: int = Field(0, ge=0, description="Number of schools within 1km") 
    transit_distance: Optional[float] = Field(None, ge=0, description="Distance to nearest transit in meters")
    shopping_distance: Optional[float] = Field(None, ge=0, description="Distance to shopping in meters")
    waterfront: bool = False
    heritage_designated: bool = False
    tree_preservation: bool = False
    environmental_constraint: bool = False


class Property(BaseModel):
    """Complete property model"""
    id: Optional[str] = None
    location: Location
    details: PropertyDetails
    amenities: Optional[PropertyAmenities] = None
    zone_code: Optional[str] = None
    roll_number: Optional[str] = None
    legal_description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get property summary"""
        return {
            'address': self.location.address,
            'coordinates': (self.location.latitude, self.location.longitude),
            'lot_area': self.details.lot_area,
            'building_area': self.details.building_area,
            'bedrooms': self.details.bedrooms,
            'bathrooms': self.details.bathrooms,
            'zone': self.zone_code,
            'type': self.details.building_type
        }