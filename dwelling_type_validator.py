"""
Dwelling Type Validation Module
Based on Oakville Zoning By-law 2014-014 Part 6 - Tables 6.2.1 and 6.2.2

This module validates whether specific dwelling types are permitted in each zone.
"""

from typing import List, Dict, Optional, Tuple
import json

def load_dwelling_type_rules():
    """Load zone-specific dwelling type permissions from the official by-law"""
    return {
        # Residential Low Zones (RL1-RL6) - Table 6.2.1
        'RL1': ['detached_dwelling'],
        'RL2': ['detached_dwelling'],
        'RL3': ['detached_dwelling'],
        'RL4': ['detached_dwelling'],
        'RL5': ['detached_dwelling'],
        'RL6': ['detached_dwelling'],
        
        # Residential Low Zones (RL7-RL9) - Table 6.2.1
        'RL7': ['detached_dwelling', 'semi_detached_dwelling'],
        'RL8': ['detached_dwelling', 'semi_detached_dwelling'],
        'RL9': ['detached_dwelling', 'semi_detached_dwelling'],
        
        # Residential Low Zone RL10 - Table 6.2.1
        'RL10': ['detached_dwelling', 'duplex_dwelling'],
        
        # Residential Low Zone RL11 - Table 6.2.1
        'RL11': ['detached_dwelling', 'linked_dwelling'],
        
        # Residential Uptown Core (RUC) - Table 6.2.1
        'RUC': ['detached_dwelling', 'semi_detached_dwelling', 'townhouse_dwelling'],
        
        # Residential Medium Zones - Table 6.2.2
        'RM1': ['townhouse_dwelling'],
        'RM2': ['back_to_back_townhouse_dwelling'],
        'RM3': ['apartment_dwelling', 'stacked_townhouse_dwelling'],
        'RM4': ['apartment_dwelling'],
        
        # Residential High Zone - Table 6.2.2
        'RH': ['apartment_dwelling']
    }

def validate_dwelling_type_for_zone(zone_code: str, dwelling_type: str) -> Tuple[bool, str]:
    """
    Validate if a dwelling type is permitted in the specified zone
    
    Args:
        zone_code: Zone code (e.g., 'RL1', 'RL10', 'RUC', 'RM3')
        dwelling_type: Type of dwelling to validate
    
    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    # Parse zone code to get base zone
    base_zone = zone_code.split('-')[0].split(' ')[0]
    
    dwelling_rules = load_dwelling_type_rules()
    
    if base_zone not in dwelling_rules:
        return False, f"Zone '{base_zone}' is not recognized in the zoning by-law"
    
    permitted_types = dwelling_rules[base_zone]
    
    if dwelling_type in permitted_types:
        return True, f"'{dwelling_type}' is permitted in zone '{base_zone}'"
    else:
        return False, f"'{dwelling_type}' is NOT permitted in zone '{base_zone}'. Permitted types: {', '.join(permitted_types)}"

def get_permitted_dwelling_types(zone_code: str) -> List[str]:
    """
    Get list of all dwelling types permitted in the specified zone
    
    Args:
        zone_code: Zone code (e.g., 'RL1', 'RL10', 'RUC')
    
    Returns:
        List of permitted dwelling types
    """
    base_zone = zone_code.split('-')[0].split(' ')[0]
    dwelling_rules = load_dwelling_type_rules()
    
    return dwelling_rules.get(base_zone, [])

def get_zones_for_dwelling_type(dwelling_type: str) -> List[str]:
    """
    Get list of all zones where the specified dwelling type is permitted
    
    Args:
        dwelling_type: Type of dwelling (e.g., 'duplex_dwelling', 'townhouse_dwelling')
    
    Returns:
        List of zones that permit this dwelling type
    """
    dwelling_rules = load_dwelling_type_rules()
    permitted_zones = []
    
    for zone, types in dwelling_rules.items():
        if dwelling_type in types:
            permitted_zones.append(zone)
    
    return permitted_zones

def validate_development_proposal(zone_code: str, proposed_dwellings: List[str]) -> Dict[str, any]:
    """
    Comprehensive validation of a development proposal against zone regulations
    
    Args:
        zone_code: Zone code
        proposed_dwellings: List of proposed dwelling types
    
    Returns:
        Dictionary with validation results and details
    """
    base_zone = zone_code.split('-')[0].split(' ')[0]
    permitted_types = get_permitted_dwelling_types(zone_code)
    
    results = {
        'zone_code': zone_code,
        'base_zone': base_zone,
        'permitted_dwelling_types': permitted_types,
        'proposed_dwellings': proposed_dwellings,
        'is_compliant': True,
        'violations': [],
        'warnings': [],
        'compliant_dwellings': [],
        'non_compliant_dwellings': []
    }
    
    for dwelling in proposed_dwellings:
        is_valid, message = validate_dwelling_type_for_zone(zone_code, dwelling)
        
        if is_valid:
            results['compliant_dwellings'].append(dwelling)
        else:
            results['non_compliant_dwellings'].append(dwelling)
            results['violations'].append(message)
            results['is_compliant'] = False
    
    # Add specific warnings for common violations
    if 'duplex_dwelling' in proposed_dwellings and base_zone != 'RL10':
        results['warnings'].append("Duplex dwellings are ONLY permitted in RL10 zones")
    
    if 'linked_dwelling' in proposed_dwellings and base_zone != 'RL11':
        results['warnings'].append("Linked dwellings are ONLY permitted in RL11 zones")
    
    if 'townhouse_dwelling' in proposed_dwellings and base_zone not in ['RUC', 'RM1']:
        results['warnings'].append("Townhouse dwellings are ONLY permitted in RUC and RM1 zones")
    
    return results

# Zone-specific development constraints
ZONE_SPECIFIC_CONSTRAINTS = {
    'RL10': {
        'duplex_dwelling': {
            'min_lot_area': 743.0,  # m²
            'min_lot_frontage': 21.0,  # m
            'max_lot_coverage': 0.25,
            'note': 'Duplex dwellings have different requirements than detached dwellings in RL10'
        },
        'detached_dwelling': {
            'min_lot_area': 464.5,  # m²
            'min_lot_frontage': 15.0,  # m
            'max_lot_coverage': 0.35
        }
    },
    'RL11': {
        'linked_dwelling': {
            'min_lot_area': 650.0,  # m²
            'min_lot_frontage': 18.0,  # m
            'max_lot_coverage': 0.35,
            'note': 'Linked dwellings are a special type only allowed in RL11'
        }
    },
    'RUC': {
        'detached_dwelling': {'min_lot_area': 220.0, 'min_lot_frontage': 7.0},
        'semi_detached_dwelling': {'min_lot_area': 350.0, 'min_lot_frontage': 11.0},
        'townhouse_dwelling': {'min_lot_area_per_unit': 150.0, 'min_lot_frontage': 14.5}
    }
}

def get_dwelling_specific_requirements(zone_code: str, dwelling_type: str) -> Optional[Dict]:
    """
    Get specific requirements for a dwelling type in a zone
    
    Args:
        zone_code: Zone code
        dwelling_type: Dwelling type
    
    Returns:
        Dictionary with specific requirements or None if not found
    """
    base_zone = zone_code.split('-')[0].split(' ')[0]
    
    if base_zone in ZONE_SPECIFIC_CONSTRAINTS:
        return ZONE_SPECIFIC_CONSTRAINTS[base_zone].get(dwelling_type)
    
    return None

def generate_compliance_report(zone_code: str, proposed_dwellings: List[str]) -> str:
    """
    Generate a detailed compliance report for a development proposal
    
    Args:
        zone_code: Zone code
        proposed_dwellings: List of proposed dwelling types
    
    Returns:
        Formatted compliance report as string
    """
    validation = validate_development_proposal(zone_code, proposed_dwellings)
    
    report = f"""
=== DWELLING TYPE COMPLIANCE REPORT ===
Zone: {validation['zone_code']}
Base Zone: {validation['base_zone']}

PERMITTED DWELLING TYPES IN THIS ZONE:
{chr(10).join('• ' + dt for dt in validation['permitted_dwelling_types'])}

PROPOSED DWELLINGS:
{chr(10).join('• ' + dt for dt in validation['proposed_dwellings'])}

COMPLIANCE STATUS: {'✅ COMPLIANT' if validation['is_compliant'] else '❌ NON-COMPLIANT'}

"""
    
    if validation['compliant_dwellings']:
        report += f"COMPLIANT DWELLINGS:\n"
        report += '\n'.join('✅ ' + dt for dt in validation['compliant_dwellings'])
        report += '\n\n'
    
    if validation['non_compliant_dwellings']:
        report += f"NON-COMPLIANT DWELLINGS:\n"
        report += '\n'.join('❌ ' + dt for dt in validation['non_compliant_dwellings'])
        report += '\n\n'
    
    if validation['violations']:
        report += f"VIOLATIONS:\n"
        report += '\n'.join('• ' + v for v in validation['violations'])
        report += '\n\n'
    
    if validation['warnings']:
        report += f"WARNINGS:\n"
        report += '\n'.join('⚠️ ' + w for w in validation['warnings'])
        report += '\n'
    
    report += "\nSource: Oakville Zoning By-law 2014-014, Part 6, Tables 6.2.1 and 6.2.2"
    
    return report

# Example usage for testing
if __name__ == "__main__":
    # Test cases
    test_cases = [
        ("RL10", ["detached_dwelling", "duplex_dwelling"]),  # Should be compliant
        ("RL10", ["townhouse_dwelling"]),  # Should be non-compliant
        ("RL11", ["linked_dwelling"]),  # Should be compliant
        ("RUC", ["detached_dwelling", "townhouse_dwelling"]),  # Should be compliant
        ("RM3", ["apartment_dwelling", "duplex_dwelling"])  # Mixed compliance
    ]
    
    for zone, dwellings in test_cases:
        print(generate_compliance_report(zone, dwellings))
        print("=" * 60)