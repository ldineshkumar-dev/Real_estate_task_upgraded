"""
Knowledge Base for Oakville Real Estate Analyzer
Comprehensive zoning regulations and real estate data management
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class OakvilleKnowledgeBase:
    """Comprehensive knowledge base for Oakville zoning and real estate information"""
    
    def __init__(self, data_directory: str = "data"):
        self.data_dir = Path(data_directory)
        self.zoning_file = self.data_dir / "comprehensive_zoning_regulations.json"
        self.knowledge_file = self.data_dir / "oakville_knowledge_base.json"
        
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)
        
        self._comprehensive_data = None
        self._faq_data = None
        
    def load_comprehensive_data(self) -> Dict:
        """Load comprehensive zoning data"""
        if self._comprehensive_data is not None:
            return self._comprehensive_data
            
        try:
            if self.zoning_file.exists():
                with open(self.zoning_file, 'r', encoding='utf-8') as f:
                    self._comprehensive_data = json.load(f)
                logger.info(f"Loaded comprehensive zoning data from {self.zoning_file}")
            else:
                logger.warning(f"Comprehensive zoning file not found: {self.zoning_file}")
                self._comprehensive_data = self._get_fallback_zoning_data()
                
        except Exception as e:
            logger.error(f"Error loading comprehensive data: {e}")
            self._comprehensive_data = self._get_fallback_zoning_data()
        
        return self._comprehensive_data
    
    def load_faq_data(self) -> List[Dict]:
        """Load FAQ and common questions data"""
        if self._faq_data is not None:
            return self._faq_data
            
        try:
            if self.knowledge_file.exists():
                with open(self.knowledge_file, 'r', encoding='utf-8') as f:
                    knowledge_data = json.load(f)
                    self._faq_data = knowledge_data.get('faq', [])
            else:
                self._faq_data = self._get_default_faq_data()
                self._save_knowledge_base()
                
        except Exception as e:
            logger.error(f"Error loading FAQ data: {e}")
            self._faq_data = self._get_default_faq_data()
        
        return self._faq_data
    
    def _get_fallback_zoning_data(self) -> Dict:
        """Get fallback zoning data if main file is not available"""
        return {
            "residential_zones": {
                "RL2": {
                    "name": "Residential Low 2",
                    "category": "Residential Low",
                    "min_lot_area": 836.0,
                    "min_lot_frontage": 22.5,
                    "setbacks": {
                        "front_yard": 9.0,
                        "rear_yard": 7.5,
                        "interior_side": 2.4,
                        "flankage_yard": 3.5
                    },
                    "max_height": 12.0,
                    "max_lot_coverage": 0.30,
                    "permitted_uses": ["detached_dwelling", "home_occupation"]
                }
            },
            "suffix_zone_regulations": {
                "-0": {
                    "name": "The -0 Suffix Zone",
                    "description": "Enhanced restrictions for established neighborhoods"
                }
            }
        }
    
    def _get_default_faq_data(self) -> List[Dict]:
        """Get default FAQ data"""
        return [
            {
                "question": "What is RL2 zoning?",
                "answer": "RL2 (Residential Low 2) is a single-family residential zone that requires a minimum lot area of 836.0 m² and minimum frontage of 22.5 meters. It permits detached dwellings, home occupations, and various accessory uses. Maximum building height is 12.0 meters with 30% maximum lot coverage.",
                "category": "zoning_basics",
                "zone_codes": ["RL2"]
            },
            {
                "question": "What are the setback requirements for RL2?",
                "answer": "RL2 zone requires: Front yard: 9.0m minimum, Rear yard: 7.5m minimum, Interior side yard: 2.4m minimum (can be reduced to 1.2m with attached garage), Flankage yard: 3.5m minimum. Corner lots have special rear yard reduction provisions.",
                "category": "setbacks",
                "zone_codes": ["RL2"]
            },
            {
                "question": "What does SP:1 mean?",
                "answer": "SP:1 refers to Special Provision 1, which provides site-specific zoning regulations that override the general by-law requirements. Each special provision is unique to the property and must be reviewed individually. Special provisions are typically created through zoning by-law amendments or minor variances.",
                "category": "special_provisions",
                "zone_codes": ["SP1"]
            },
            {
                "question": "What's the minimum lot size for RL2?",
                "answer": "The minimum lot area for RL2 zoning is 836.0 square meters (approximately 9,000 square feet) with a minimum lot frontage of 22.5 meters (73.8 feet). For corner lots, special provisions may apply.",
                "category": "lot_requirements",
                "zone_codes": ["RL2"]
            },
            {
                "question": "Can I build a duplex in RL2?",
                "answer": "No, duplex dwellings are not permitted in RL2 zones. RL2 permits only detached dwellings as the primary residential use. Duplex dwellings are permitted in RL10 zones and some higher-density residential zones. You would need a zoning amendment to build a duplex in an RL2 zone.",
                "category": "permitted_uses",
                "zone_codes": ["RL2", "RL10"]
            },
            {
                "question": "What's the FAR for RL2-0?",
                "answer": "RL2-0 (RL2 with -0 suffix) has specific Floor Area Ratio (FAR) limits based on lot size. For lots 836.0-928.99 m², the maximum FAR is 39%. For lots 650.0-742.99 m², it's 41%. The FAR calculation includes special rules for attic space and garage areas above 6.0m height.",
                "category": "far_calculations",
                "zone_codes": ["RL2-0"]
            },
            {
                "question": "What are corner lot requirements?",
                "answer": "Corner lots have special provisions including: flankage yard setbacks (typically 3.0-3.5m), potential rear yard reductions when interior side yard is 3.0m, special consideration for driveways and parking, and daylight triangle setback requirements (0.7m minimum).",
                "category": "corner_lots",
                "zone_codes": ["all"]
            },
            {
                "question": "How do I measure my property?",
                "answer": "Use the Interactive Measurement tool in the app to click points on the map and measure frontage and depth. For accurate legal measurements, consult a licensed surveyor. Property dimensions from tax rolls or MLS listings may not be survey-accurate. The app provides multiple measurement tools including ArcGIS-style mapping.",
                "category": "measurement",
                "zone_codes": ["all"]
            },
            {
                "question": "How do I request a zoning change?",
                "answer": "Contact Town of Oakville Planning Services at 905-845-6601. Zoning changes require either a minor variance (for small deviations) or zoning by-law amendment (for major changes). Applications require fees, plans, and public consultation. Processing time is typically 3-6 months.",
                "category": "processes",
                "zone_codes": ["all"]
            },
            {
                "question": "What's the maximum building height in RH zones?",
                "answer": "RH (Residential High) zones have a maximum height equal to what was legally existing on the effective date of the by-law. Each RH property may have different height limits based on its existing development. Check specific property records for exact height permissions.",
                "category": "height_limits",
                "zone_codes": ["RH"]
            },
            {
                "question": "What is the -0 suffix zone?",
                "answer": "The -0 suffix zone applies enhanced restrictions to established neighborhoods. Key features: maximum 2 storeys, 9.0m height limit, no floor area above second storey, specific FAR limits by lot size, enhanced lot coverage restrictions, and balcony/deck prohibitions above first floor.",
                "category": "suffix_zones",
                "zone_codes": ["RL1-0", "RL2-0", "RL3-0", "RL4-0", "RL5-0", "RL6-0", "RL7-0", "RL8-0", "RL9-0", "RL10-0", "RL11-0"]
            },
            {
                "question": "What are accessory building requirements?",
                "answer": "Accessory buildings (garages, sheds) require: maximum 4.0m height (reduced to 2.5m within 3.5m of flankage lot line), minimum 0.6m setback from lot lines in rear/flankage yards, maximum lot coverage of greater of 5% or 42 m², and 2.0m separation from main dwelling.",
                "category": "accessory_buildings",
                "zone_codes": ["all"]
            },
            {
                "question": "How is property value calculated?",
                "answer": "The app estimates property value using: comparable sales analysis, lot value per m², building value based on size/age/condition, location premiums for amenities, market condition adjustments, and zoning development potential. Values are estimates only - consult a certified appraiser for official valuations.",
                "category": "valuation",
                "zone_codes": ["all"]
            },
            {
                "question": "What factors affect development potential?",
                "answer": "Development potential depends on: current zone permissions, lot dimensions vs. minimum requirements, available density (units per hectare), Floor Area Ratio limits, height and setback constraints, heritage or environmental restrictions, and municipal servicing capacity.",
                "category": "development",
                "zone_codes": ["all"]
            },
            {
                "question": "What's the difference between RL zones?",
                "answer": "RL zones vary by density: RL1 (largest lots, 1,393.5 m²), RL2 (836.0 m²), RL3 (557.5 m²), RL4 (511.0 m²), RL5 (464.5 m²), RL6 (250.0 m²). Higher numbers = smaller lots, more intensive development. RL7-11 have special provisions for different dwelling types.",
                "category": "zoning_comparison",
                "zone_codes": ["RL1", "RL2", "RL3", "RL4", "RL5", "RL6", "RL7", "RL8", "RL9", "RL10", "RL11"]
            }
        ]
    
    def _save_knowledge_base(self):
        """Save knowledge base data to file"""
        try:
            knowledge_data = {
                "metadata": {
                    "version": "1.0",
                    "source": "Town of Oakville Zoning By-law 2014-014",
                    "consolidated_date": "July 10, 2024",
                    "created_by": "AI Oakville Real Estate Analyzer"
                },
                "faq": self._faq_data or self._get_default_faq_data()
            }
            
            with open(self.knowledge_file, 'w', encoding='utf-8') as f:
                json.dump(knowledge_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Knowledge base saved to {self.knowledge_file}")
            
        except Exception as e:
            logger.error(f"Error saving knowledge base: {e}")
    
    def add_faq_item(self, question: str, answer: str, category: str = "general", zone_codes: List[str] = None):
        """Add new FAQ item"""
        if self._faq_data is None:
            self.load_faq_data()
            
        new_item = {
            "question": question,
            "answer": answer,
            "category": category,
            "zone_codes": zone_codes or ["all"]
        }
        
        self._faq_data.append(new_item)
        self._save_knowledge_base()
        
        logger.info(f"Added new FAQ item: {question[:50]}...")
    
    def search_faq(self, query: str, category: str = None) -> List[Dict]:
        """Search FAQ items"""
        if self._faq_data is None:
            self.load_faq_data()
            
        query_lower = query.lower()
        results = []
        
        for item in self._faq_data:
            score = 0
            
            # Check question match
            if query_lower in item['question'].lower():
                score += 2
            
            # Check answer match
            if query_lower in item['answer'].lower():
                score += 1
            
            # Check zone codes
            for zone in item.get('zone_codes', []):
                if query_lower in zone.lower():
                    score += 1
            
            # Filter by category if specified
            if category and item.get('category') != category:
                score = 0
            
            if score > 0:
                results.append({
                    **item,
                    'relevance_score': score
                })
        
        # Sort by relevance
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        return results
    
    def get_zone_info(self, zone_code: str) -> Optional[Dict]:
        """Get comprehensive information for a specific zone"""
        data = self.load_comprehensive_data()
        
        zone_code = zone_code.upper()
        
        # Check residential zones
        if zone_code in data.get('residential_zones', {}):
            return data['residential_zones'][zone_code]
        
        # Check for zone without suffix
        base_zone = zone_code.split('-')[0]
        if base_zone in data.get('residential_zones', {}):
            zone_info = data['residential_zones'][base_zone].copy()
            
            # Add suffix information if applicable
            if '-' in zone_code:
                suffix = zone_code[zone_code.find('-'):]
                if suffix in data.get('suffix_zone_regulations', {}):
                    zone_info['suffix_regulations'] = data['suffix_zone_regulations'][suffix]
            
            return zone_info
        
        return None
    
    def get_all_zones(self) -> List[str]:
        """Get list of all available zone codes"""
        data = self.load_comprehensive_data()
        zones = list(data.get('residential_zones', {}).keys())
        
        # Add suffix variants
        extended_zones = []
        suffix_zones = data.get('suffix_zone_regulations', {}).keys()
        
        for zone in zones:
            extended_zones.append(zone)
            for suffix in suffix_zones:
                if suffix.startswith('-'):
                    extended_zones.append(f"{zone}{suffix}")
        
        return sorted(extended_zones)
    
    def get_categories(self) -> List[str]:
        """Get all FAQ categories"""
        if self._faq_data is None:
            self.load_faq_data()
            
        categories = set()
        for item in self._faq_data:
            categories.add(item.get('category', 'general'))
            
        return sorted(list(categories))
    
    def get_statistics(self) -> Dict:
        """Get knowledge base statistics"""
        data = self.load_comprehensive_data()
        faq_data = self.load_faq_data()
        
        return {
            'total_zones': len(data.get('residential_zones', {})),
            'suffix_zones': len(data.get('suffix_zone_regulations', {})),
            'faq_items': len(faq_data),
            'categories': len(self.get_categories()),
            'data_files': {
                'comprehensive_exists': self.zoning_file.exists(),
                'knowledge_exists': self.knowledge_file.exists()
            }
        }
    
    def validate_data(self) -> Dict:
        """Validate knowledge base data integrity"""
        issues = []
        warnings = []
        
        try:
            data = self.load_comprehensive_data()
            faq_data = self.load_faq_data()
            
            # Check residential zones
            residential_zones = data.get('residential_zones', {})
            if not residential_zones:
                issues.append("No residential zones found")
            
            for zone_code, zone_data in residential_zones.items():
                # Check required fields
                required_fields = ['name', 'min_lot_area', 'min_lot_frontage']
                for field in required_fields:
                    if field not in zone_data:
                        issues.append(f"Zone {zone_code} missing required field: {field}")
                
                # Check setbacks
                setbacks = zone_data.get('setbacks', {})
                if not setbacks:
                    warnings.append(f"Zone {zone_code} has no setback information")
            
            # Check FAQ data
            if not faq_data:
                warnings.append("No FAQ data available")
            
            for i, item in enumerate(faq_data):
                if 'question' not in item or 'answer' not in item:
                    issues.append(f"FAQ item {i} missing question or answer")
            
        except Exception as e:
            issues.append(f"Validation error: {e}")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'total_issues': len(issues),
            'total_warnings': len(warnings)
        }

def create_knowledge_base(data_directory: str = "data") -> OakvilleKnowledgeBase:
    """Factory function to create knowledge base"""
    return OakvilleKnowledgeBase(data_directory=data_directory)