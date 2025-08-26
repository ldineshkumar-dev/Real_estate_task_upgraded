"""
Portfolio Management Module for System-Wide AI Chatbot
Handles multi-property analysis, investment insights, and portfolio optimization
"""

import json
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import streamlit as st

@dataclass
class PropertyRecord:
    """Individual property record for portfolio management"""
    id: str
    address: str
    zone_code: str
    lot_area: float
    building_area: float
    estimated_value: float
    purchase_price: Optional[float] = None
    purchase_date: Optional[str] = None
    current_use: str = "residential"
    development_potential: str = "single_family"
    special_provisions: str = ""
    notes: str = ""

class PortfolioManager:
    """Portfolio management and analysis system"""
    
    def __init__(self):
        """Initialize portfolio manager"""
        self.properties: List[PropertyRecord] = []
        self._load_portfolio_from_session()
    
    def _load_portfolio_from_session(self):
        """Load portfolio from Streamlit session state"""
        if 'portfolio_properties' in st.session_state:
            try:
                portfolio_data = st.session_state.portfolio_properties
                for prop_data in portfolio_data:
                    self.properties.append(PropertyRecord(**prop_data))
            except Exception as e:
                st.warning(f"Error loading portfolio: {e}")
                self.properties = []
    
    def _save_portfolio_to_session(self):
        """Save portfolio to Streamlit session state"""
        portfolio_data = []
        for prop in self.properties:
            portfolio_data.append({
                'id': prop.id,
                'address': prop.address,
                'zone_code': prop.zone_code,
                'lot_area': prop.lot_area,
                'building_area': prop.building_area,
                'estimated_value': prop.estimated_value,
                'purchase_price': prop.purchase_price,
                'purchase_date': prop.purchase_date,
                'current_use': prop.current_use,
                'development_potential': prop.development_potential,
                'special_provisions': prop.special_provisions,
                'notes': prop.notes
            })
        st.session_state.portfolio_properties = portfolio_data
    
    def add_property(self, property_record: PropertyRecord) -> bool:
        """Add a property to the portfolio"""
        try:
            # Check for duplicates
            if any(prop.address.lower() == property_record.address.lower() for prop in self.properties):
                return False
            
            self.properties.append(property_record)
            self._save_portfolio_to_session()
            return True
        except Exception:
            return False
    
    def remove_property(self, property_id: str) -> bool:
        """Remove a property from the portfolio"""
        try:
            self.properties = [prop for prop in self.properties if prop.id != property_id]
            self._save_portfolio_to_session()
            return True
        except Exception:
            return False
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary"""
        if not self.properties:
            return {
                'total_properties': 0,
                'total_value': 0,
                'average_value': 0,
                'zone_distribution': {},
                'development_opportunities': 0,
                'special_provision_count': 0
            }
        
        total_value = sum(prop.estimated_value for prop in self.properties)
        zone_counts = {}
        development_counts = {}
        special_provision_count = 0
        
        for prop in self.properties:
            # Zone distribution
            zone_counts[prop.zone_code] = zone_counts.get(prop.zone_code, 0) + 1
            
            # Development potential
            development_counts[prop.development_potential] = development_counts.get(prop.development_potential, 0) + 1
            
            # Special provisions
            if prop.special_provisions and prop.special_provisions.strip():
                special_provision_count += 1
        
        return {
            'total_properties': len(self.properties),
            'total_value': total_value,
            'average_value': total_value / len(self.properties),
            'zone_distribution': zone_counts,
            'development_distribution': development_counts,
            'development_opportunities': len([p for p in self.properties if p.development_potential != 'single_family']),
            'special_provision_count': special_provision_count,
            'properties': self.properties
        }
    
    def analyze_investment_potential(self) -> Dict[str, Any]:
        """Analyze investment potential of the portfolio"""
        summary = self.get_portfolio_summary()
        
        if summary['total_properties'] == 0:
            return {'analysis': 'No properties in portfolio for analysis'}
        
        # Calculate ROI where purchase prices are available
        properties_with_purchase = [p for p in self.properties if p.purchase_price and p.purchase_price > 0]
        
        total_invested = sum(p.purchase_price for p in properties_with_purchase)
        current_value_invested = sum(p.estimated_value for p in properties_with_purchase)
        
        roi = 0
        if total_invested > 0:
            roi = ((current_value_invested - total_invested) / total_invested) * 100
        
        # Risk assessment
        risk_factors = []
        
        # Zone concentration risk
        zone_dist = summary['zone_distribution']
        max_zone_concentration = max(zone_dist.values()) / summary['total_properties'] if zone_dist else 0
        if max_zone_concentration > 0.6:
            risk_factors.append(f"High concentration in {max(zone_dist, key=zone_dist.get)} zone ({max_zone_concentration:.0%})")
        
        # Development opportunities
        dev_opportunities = summary['development_opportunities']
        if dev_opportunities > 0:
            risk_factors.append(f"{dev_opportunities} properties with development potential")
        
        # Special provisions
        if summary['special_provision_count'] > 0:
            risk_factors.append(f"{summary['special_provision_count']} properties with special provisions")
        
        return {
            'analysis': 'Portfolio investment analysis completed',
            'roi_percentage': roi,
            'total_invested': total_invested,
            'current_portfolio_value': summary['total_value'],
            'unrealized_gains': current_value_invested - total_invested if total_invested > 0 else 0,
            'risk_factors': risk_factors,
            'properties_analyzed': len(properties_with_purchase),
            'total_properties': summary['total_properties'],
            'recommendations': self._generate_recommendations(summary, roi, risk_factors)
        }
    
    def _generate_recommendations(self, summary: Dict, roi: float, risk_factors: List[str]) -> List[str]:
        """Generate investment recommendations"""
        recommendations = []
        
        # Portfolio size recommendations
        if summary['total_properties'] < 3:
            recommendations.append("Consider expanding portfolio to reduce single-property risk")
        
        # Zone diversification
        zone_dist = summary['zone_distribution']
        if len(zone_dist) < 3 and summary['total_properties'] > 3:
            recommendations.append("Consider diversifying across more zoning types")
        
        # Development opportunities
        if summary['development_opportunities'] == 0:
            recommendations.append("Look for properties with development potential to increase returns")
        elif summary['development_opportunities'] > summary['total_properties'] * 0.5:
            recommendations.append("High development exposure - consider balancing with stable income properties")
        
        # ROI-based recommendations
        if roi < 5:
            recommendations.append("Portfolio ROI below market average - consider property improvements or acquisitions")
        elif roi > 15:
            recommendations.append("Strong portfolio performance - consider taking profits or expanding")
        
        # Special provisions
        if summary['special_provision_count'] > 0:
            recommendations.append("Review special provision properties for compliance and opportunities")
        
        return recommendations
    
    def export_portfolio(self, format_type: str = "json") -> str:
        """Export portfolio data"""
        summary = self.get_portfolio_summary()
        analysis = self.analyze_investment_potential()
        
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'portfolio_summary': summary,
            'investment_analysis': analysis,
            'properties': [
                {
                    'id': prop.id,
                    'address': prop.address,
                    'zone_code': prop.zone_code,
                    'lot_area': prop.lot_area,
                    'building_area': prop.building_area,
                    'estimated_value': prop.estimated_value,
                    'purchase_price': prop.purchase_price,
                    'purchase_date': prop.purchase_date,
                    'current_use': prop.current_use,
                    'development_potential': prop.development_potential,
                    'special_provisions': prop.special_provisions,
                    'notes': prop.notes
                }
                for prop in self.properties
            ]
        }
        
        if format_type == "json":
            return json.dumps(export_data, indent=2)
        elif format_type == "csv":
            df = pd.DataFrame(export_data['properties'])
            return df.to_csv(index=False)
        else:
            return str(export_data)

def render_portfolio_manager():
    """Render portfolio manager interface"""
    st.header("📊 Portfolio Manager")
    
    # Initialize portfolio manager
    if 'portfolio_manager' not in st.session_state:
        st.session_state.portfolio_manager = PortfolioManager()
    
    portfolio_mgr = st.session_state.portfolio_manager
    
    # Portfolio overview
    summary = portfolio_mgr.get_portfolio_summary()
    
    if summary['total_properties'] > 0:
        st.markdown("### 📈 Portfolio Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Properties", summary['total_properties'])
        with col2:
            st.metric("Portfolio Value", f"${summary['total_value']:,.0f}")
        with col3:
            st.metric("Average Value", f"${summary['average_value']:,.0f}")
        with col4:
            st.metric("Development Opportunities", summary['development_opportunities'])
        
        # Zone distribution chart
        if summary['zone_distribution']:
            st.markdown("### 🗺️ Zone Distribution")
            zone_df = pd.DataFrame(list(summary['zone_distribution'].items()), columns=['Zone', 'Count'])
            st.bar_chart(zone_df.set_index('Zone'))
        
        # Investment analysis
        analysis = portfolio_mgr.analyze_investment_potential()
        
        if analysis.get('properties_analyzed', 0) > 0:
            st.markdown("### 💰 Investment Analysis")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                roi = analysis.get('roi_percentage', 0)
                st.metric("Portfolio ROI", f"{roi:.1f}%", f"{roi - 8:.1f}% vs market")
            with col2:
                st.metric("Total Invested", f"${analysis.get('total_invested', 0):,.0f}")
            with col3:
                st.metric("Unrealized Gains", f"${analysis.get('unrealized_gains', 0):,.0f}")
            
            # Risk factors
            risk_factors = analysis.get('risk_factors', [])
            if risk_factors:
                st.markdown("### ⚠️ Risk Factors")
                for risk in risk_factors:
                    st.warning(f"• {risk}")
            
            # Recommendations
            recommendations = analysis.get('recommendations', [])
            if recommendations:
                st.markdown("### 💡 Recommendations")
                for rec in recommendations:
                    st.info(f"• {rec}")
        
        # Property list
        st.markdown("### 🏠 Property Details")
        for prop in summary['properties']:
            with st.expander(f"{prop.address} - {prop.zone_code}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Lot Area:** {prop.lot_area:,.0f} m²")
                    st.write(f"**Building Area:** {prop.building_area:,.0f} m²")
                    st.write(f"**Estimated Value:** ${prop.estimated_value:,.0f}")
                with col2:
                    st.write(f"**Development Potential:** {prop.development_potential}")
                    if prop.special_provisions:
                        st.write(f"**Special Provisions:** {prop.special_provisions}")
                    if prop.notes:
                        st.write(f"**Notes:** {prop.notes}")
                
                if st.button(f"Remove {prop.address}", key=f"remove_{prop.id}"):
                    portfolio_mgr.remove_property(prop.id)
                    st.rerun()
        
        # Export options
        st.markdown("### 📄 Export Portfolio")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Export JSON"):
                export_data = portfolio_mgr.export_portfolio("json")
                st.download_button(
                    "💾 Download JSON",
                    export_data,
                    file_name=f"portfolio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        with col2:
            if st.button("📊 Export CSV"):
                export_data = portfolio_mgr.export_portfolio("csv")
                st.download_button(
                    "💾 Download CSV", 
                    export_data,
                    file_name=f"portfolio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
    else:
        st.info("No properties in portfolio. Add properties from the main analysis or use the form below.")
    
    # Add property form
    st.markdown("### ➕ Add Property to Portfolio")
    
    with st.form("add_property_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            address = st.text_input("Property Address", placeholder="123 Main St, Oakville, ON")
            zone_code = st.selectbox("Zone Code", ["RL1", "RL2", "RL3", "RL4", "RL5", "RL6", "RL7", "RL8", "RL9", "RL10", "RL11", "RUC", "RM1", "RM2", "RM3", "RM4", "RH"])
            lot_area = st.number_input("Lot Area (m²)", min_value=100.0, value=500.0)
            building_area = st.number_input("Building Area (m²)", min_value=50.0, value=200.0)
        
        with col2:
            estimated_value = st.number_input("Estimated Value ($)", min_value=100000, value=1000000)
            purchase_price = st.number_input("Purchase Price ($)", min_value=0, value=0, help="Optional - for ROI calculations")
            development_potential = st.selectbox("Development Potential", ["single_family", "duplex", "townhouse", "multi_family", "commercial_conversion"])
            special_provisions = st.text_input("Special Provisions", placeholder="SP:1, SP:2, etc.")
        
        notes = st.text_area("Notes", placeholder="Additional notes about this property...")
        
        if st.form_submit_button("Add Property", type="primary"):
            if address and zone_code:
                new_property = PropertyRecord(
                    id=f"prop_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    address=address,
                    zone_code=zone_code,
                    lot_area=lot_area,
                    building_area=building_area,
                    estimated_value=estimated_value,
                    purchase_price=purchase_price if purchase_price > 0 else None,
                    purchase_date=datetime.now().strftime('%Y-%m-%d') if purchase_price > 0 else None,
                    development_potential=development_potential,
                    special_provisions=special_provisions,
                    notes=notes
                )
                
                if portfolio_mgr.add_property(new_property):
                    st.success(f"✅ Added {address} to portfolio")
                    st.rerun()
                else:
                    st.error("❌ Failed to add property - may already exist in portfolio")
            else:
                st.error("Please provide at least an address and zone code")

def get_portfolio_manager():
    """Get portfolio manager instance"""
    if 'portfolio_manager' not in st.session_state:
        st.session_state.portfolio_manager = PortfolioManager()
    return st.session_state.portfolio_manager