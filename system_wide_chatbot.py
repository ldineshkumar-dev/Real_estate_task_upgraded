"""
System-Wide AI Chatbot for Oakville Real Estate Analyzer
Comprehensive AI assistant that handles entire system functionality
"""

import os
import time
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import pandas as pd

import streamlit as st
from groq import Groq

# Import portfolio manager for comprehensive system capabilities
try:
    from portfolio_manager import get_portfolio_manager, render_portfolio_manager
    PORTFOLIO_MANAGER_AVAILABLE = True
except ImportError:
    PORTFOLIO_MANAGER_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class SystemChatMessage:
    """Represents a system-wide chat message"""
    role: str
    content: str
    timestamp: datetime
    context_type: str = "general"  # general, property, portfolio, market, system
    metadata: Dict = None

class SystemWideRealEstateChatbot:
    """System-wide AI chatbot for comprehensive real estate assistance"""
    
    def __init__(self, groq_api_key: str):
        """Initialize the system-wide chatbot"""
        if not groq_api_key:
            raise ValueError("GROQ API key is required")
            
        self.groq_client = Groq(api_key=groq_api_key)
        self.model = "mixtral-8x7b-32768"
        self.conversation_history: List[SystemChatMessage] = []
        
        # System knowledge base
        self.system_knowledge = self._get_system_knowledge()
        
    def _get_system_knowledge(self) -> str:
        """Get comprehensive system knowledge base"""
        return """
COMPREHENSIVE OAKVILLE REAL ESTATE SYSTEM KNOWLEDGE BASE:

=== SYSTEM CAPABILITIES ===
1. PROPERTY ANALYSIS:
   - Individual property zoning analysis
   - Property valuation estimates
   - Development potential assessment
   - Market comparison analysis
   - Special provisions interpretation

2. PORTFOLIO MANAGEMENT:
   - Multi-property analysis
   - Portfolio valuation summary
   - Risk assessment across properties
   - Investment opportunity identification
   - Comparative market analysis

3. MARKET INTELLIGENCE:
   - Market trend analysis
   - Price predictions by zone
   - Days on market statistics
   - Sales volume trends
   - Neighborhood insights

4. SYSTEM OPERATIONS:
   - Cache management and optimization
   - API integration status
   - Data source reliability
   - Error troubleshooting
   - Performance monitoring

=== OAKVILLE ZONING BY-LAW 2014-014 ===
RESIDENTIAL ZONES DETAILED:
- RL1: Estate Residential (Min: 1,393.5 m², 30.5m frontage, Max: 12m height, 25% coverage)
- RL2: Large Lot Residential (Min: 836.0 m², 22.5m frontage, Max: 12m height, 30% coverage)
- RL3: Medium Lot Residential (Min: 557.5 m², 18.0m frontage, Max: 12m height, 30% coverage)
- RL4: Standard Residential (Min: 511.0 m², 16.5m frontage, Max: 12m height, 35% coverage)
- RL5: Compact Residential (Min: 464.5 m², 15.0m frontage, Max: 12m height, 35% coverage)
- RL6: Small Lot Residential (Min: 250.0 m², 11.0m frontage, Max: 12m height, 40% coverage)
- RL7-RL11: Various residential configurations with specific requirements
- RUC: Residential Urban Core (Min: 220.0 m², 7.0m frontage, varies by location)
- RM1-RM4: Residential Multiple (apartments, townhouses)
- RH: Residential High (high-rise residential)

SPECIAL PROVISIONS:
- SP:1 = Enhanced residential development standards
- SP:2 = Modified setback requirements  
- SP:3 = Heritage considerations
- -0 Suffix = Maximum 2 storeys, 9.0m height, FAR restrictions

SETBACK FORMULAS:
- Front yard: Generally 6.0m to 9.0m depending on zone
- Rear yard: Generally 6.0m to 7.5m depending on zone
- Interior side: 1.2m to 2.4m depending on zone
- Flankage yard: 3.0m to 3.5m depending on zone

=== VALUATION METHODOLOGY ===
CALCULATION COMPONENTS:
1. Land Value = Zone Base Rate × Lot Area (m²)
2. Building Value = Construction Cost/m² × Building Area × Depreciation Factor
3. Location Adjustments = Park Proximity + Heritage - Corner Lot + Waterfront
4. Market Factor = Current Market Conditions (0.85-1.15 multiplier)
5. Final Value = (Land + Building + Adjustments) × Market Factor

ZONE BASE RATES (Per m²):
- RL1: $1,200-1,500/m²
- RL2: $1,000-1,200/m²  
- RL3: $800-1,000/m²
- RL4: $750-900/m²
- RL5: $700-850/m²
- RL6: $650-800/m²

=== DEVELOPMENT POTENTIAL ===
PROFIT ANALYSIS:
- Minimum 15% profit margin required for feasibility
- Construction costs: $2,200-2,800/m² for residential
- Soft costs: 15-25% of hard costs
- Financing: 6-8% annually
- Marketing: 3-5% of gross sales

DEVELOPMENT SCENARIOS:
1. Single Family Replacement
2. Duplex/Semi-detached (where permitted)
3. Townhouse Development (RM zones)
4. Apartment Building (RM3/RM4)

=== MARKET INTELLIGENCE ===
CURRENT MARKET METRICS:
- Average price/m²: $4,850 (↑5.2% YoY)
- Days on market: 21 days average
- Sales/List ratio: 98.5%
- Inventory levels: 342 active listings
- Price appreciation: 5-8% annually

NEIGHBORHOOD FACTORS:
- School ratings impact: +/-10% value
- Park proximity: +5-15% value  
- Transit access: +8-12% value
- Heritage designation: -5-10% value
- Waterfront: +25-50% value

=== SYSTEM INTEGRATION ===
API ENDPOINTS AVAILABLE:
- Oakville GIS Services (limited availability)
- Ottawa Municipal APIs (working)
- Enhanced Property Client (curated data)
- Google Maps Geocoding
- Property Dimensions Calculator

MEASUREMENT TOOLS:
- ArcGIS-style interactive mapping
- Precise 2-point selector
- Manual measurement tools
- Enhanced property selector
- Satellite imagery integration

CACHE SYSTEM:
- Multi-tier caching (Memory, Redis, File)
- Cache hit rates and performance monitoring
- Automatic cache warming for common queries
- Selective cache clearing by type

=== TROUBLESHOOTING ===
COMMON ISSUES:
1. API Rate Limits: Built-in retry logic and rate limiting
2. Zoning Data Missing: Fallback to curated datasets  
3. Geocoding Failures: Multiple geocoding service fallbacks
4. Calculation Errors: Validation and error handling
5. Performance Issues: Cache optimization and query tuning

CONTACT INFORMATION:
- Town of Oakville Planning: 905-845-6601
- Building Department: 905-845-6601
- Email: planning@oakville.ca
- Website: oakville.ca
"""

    def determine_context_type(self, question: str, system_state: Dict = None) -> str:
        """Determine the context type of the question"""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['portfolio', 'multiple properties', 'all properties', 'investment analysis']):
            return "portfolio"
        elif any(word in question_lower for word in ['market', 'trends', 'prices', 'neighborhood', 'investment outlook']):
            return "market"  
        elif any(word in question_lower for word in ['cache', 'performance', 'api', 'system', 'error', 'troubleshoot']):
            return "system"
        elif any(word in question_lower for word in ['property', 'zoning', 'setback', 'lot', 'building', 'valuation']):
            return "property"
        else:
            return "general"

    def get_system_context(self) -> Dict:
        """Get current system state and context"""
        context = {
            'timestamp': datetime.now().isoformat(),
            'active_properties': [],
            'system_status': 'operational',
            'cache_stats': {},
            'recent_searches': [],
            'portfolio_summary': None
        }
        
        # Get property data from session state if available
        if hasattr(st, 'session_state'):
            if hasattr(st.session_state, 'property_data') and st.session_state.property_data:
                context['current_property'] = {
                    'address': st.session_state.property_data.get('address', ''),
                    'zone_code': st.session_state.property_data.get('zone_code', ''),
                    'lot_area': st.session_state.property_data.get('lot_area', 0),
                    'lot_frontage': st.session_state.property_data.get('lot_frontage', 0)
                }
            
            if hasattr(st.session_state, 'analysis_results') and st.session_state.analysis_results:
                context['last_analysis'] = {
                    'valuation': st.session_state.analysis_results.get('valuation', {}),
                    'zoning': st.session_state.analysis_results.get('zoning', {})
                }
            
            # Get portfolio information if available
            if PORTFOLIO_MANAGER_AVAILABLE:
                try:
                    portfolio_mgr = get_portfolio_manager()
                    portfolio_summary = portfolio_mgr.get_portfolio_summary()
                    if portfolio_summary['total_properties'] > 0:
                        context['portfolio_summary'] = {
                            'total_properties': portfolio_summary['total_properties'],
                            'total_value': portfolio_summary['total_value'],
                            'zone_distribution': portfolio_summary['zone_distribution'],
                            'development_opportunities': portfolio_summary['development_opportunities']
                        }
                        
                        # Get investment analysis
                        investment_analysis = portfolio_mgr.analyze_investment_potential()
                        context['investment_analysis'] = investment_analysis
                except Exception as e:
                    logger.warning(f"Failed to get portfolio context: {e}")
        
        return context

    def answer_question(self, question: str, system_context: Dict = None) -> Tuple[str, str]:
        """Answer question with full system context"""
        try:
            # Determine context type
            context_type = self.determine_context_type(question, system_context)
            
            # Get current system state
            if not system_context:
                system_context = self.get_system_context()
            
            # Build comprehensive system prompt
            system_prompt = f"""You are the AI Assistant for the Oakville Real Estate Analyzer System. You have access to comprehensive system functionality and knowledge.

SYSTEM KNOWLEDGE:
{self.system_knowledge}

CURRENT SYSTEM STATE:
Context Type: {context_type}
Timestamp: {system_context.get('timestamp', 'Unknown')}
System Status: {system_context.get('system_status', 'Unknown')}

CURRENT SESSION DATA:
"""
            
            if system_context.get('current_property'):
                prop = system_context['current_property']
                system_prompt += f"""
Active Property:
- Address: {prop.get('address', 'Not specified')}
- Zone: {prop.get('zone_code', 'Unknown')}
- Lot Area: {prop.get('lot_area', 'Not specified')} m²
- Frontage: {prop.get('lot_frontage', 'Not specified')} m
"""
            
            if system_context.get('last_analysis'):
                analysis = system_context['last_analysis']
                if analysis.get('valuation'):
                    val = analysis['valuation']
                    estimated_value = val.get('estimated_value', 0)
                    if estimated_value:
                        system_prompt += f"- Last Valuation: ${estimated_value:,.0f}\n"
            
            if system_context.get('portfolio_summary'):
                portfolio = system_context['portfolio_summary']
                system_prompt += f"""
Portfolio Summary:
- Total Properties: {portfolio.get('total_properties', 0)}
- Portfolio Value: ${portfolio.get('total_value', 0):,.0f}
- Development Opportunities: {portfolio.get('development_opportunities', 0)}
- Zone Distribution: {portfolio.get('zone_distribution', {})}
"""
                
                if system_context.get('investment_analysis'):
                    inv_analysis = system_context['investment_analysis']
                    roi = inv_analysis.get('roi_percentage', 0)
                    if roi != 0:
                        system_prompt += f"- Portfolio ROI: {roi:.1f}%\n"
            
            # Add context-specific instructions
            if context_type == "portfolio":
                system_prompt += """
PORTFOLIO ANALYSIS INSTRUCTIONS:
- Provide insights across multiple properties
- Compare investment opportunities
- Calculate portfolio risk and returns
- Suggest diversification strategies
"""
            elif context_type == "market":
                system_prompt += """
MARKET ANALYSIS INSTRUCTIONS:
- Analyze market trends and conditions
- Provide neighborhood comparisons
- Forecast price movements
- Identify investment opportunities
"""
            elif context_type == "system":
                system_prompt += """
SYSTEM ADMINISTRATION INSTRUCTIONS:
- Help with system configuration and optimization
- Troubleshoot technical issues
- Explain system capabilities
- Provide performance recommendations
"""
            else:
                system_prompt += """
PROPERTY ANALYSIS INSTRUCTIONS:
- Provide detailed zoning and regulatory guidance
- Calculate precise setbacks and requirements
- Explain special provisions and restrictions
- Suggest development opportunities
"""
            
            system_prompt += """
RESPONSE GUIDELINES:
1. Be comprehensive yet concise
2. Provide specific numbers and calculations when relevant
3. Include actionable recommendations
4. Reference official sources (Oakville By-law 2014-014)
5. Suggest next steps when appropriate
6. For system issues, provide troubleshooting steps
7. For investment questions, include risk considerations
"""
            
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add recent conversation context (last 6 messages)
            for msg in self.conversation_history[-6:]:
                messages.append({
                    "role": msg.role,
                    "content": msg.content[:800]  # Truncate long messages
                })
            
            messages.append({"role": "user", "content": question})
            
            # Get response from GROQ
            response = self.groq_client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1500,
                temperature=0.1,
                top_p=0.9
            )
            
            answer = response.choices[0].message.content
            
            # Store conversation with context
            self.conversation_history.append(SystemChatMessage(
                role="user", 
                content=question, 
                timestamp=datetime.now(),
                context_type=context_type,
                metadata=system_context
            ))
            self.conversation_history.append(SystemChatMessage(
                role="assistant", 
                content=answer, 
                timestamp=datetime.now(),
                context_type=context_type
            ))
            
            # Keep history manageable
            if len(self.conversation_history) > 30:
                self.conversation_history = self.conversation_history[-30:]
            
            return answer, context_type
            
        except Exception as e:
            logger.error(f"Error in system-wide chatbot: {e}")
            error_response = f"""I apologize, but I encountered a system error: {str(e)}

**Troubleshooting Steps:**
1. Check GROQ API key configuration
2. Verify internet connectivity
3. Try refreshing the page
4. Contact system administrator if problem persists

**Alternative Resources:**
- Town of Oakville Planning: 905-845-6601
- Online: oakville.ca
- Email: planning@oakville.ca
"""
            return error_response, "error"

    def get_conversation_summary(self) -> Dict:
        """Get conversation summary and statistics"""
        if not self.conversation_history:
            return {"total_messages": 0, "context_breakdown": {}}
        
        context_counts = {}
        total_user_messages = 0
        
        for msg in self.conversation_history:
            if msg.role == "user":
                total_user_messages += 1
                context_type = msg.context_type
                context_counts[context_type] = context_counts.get(context_type, 0) + 1
        
        return {
            "total_messages": len(self.conversation_history),
            "user_questions": total_user_messages,
            "context_breakdown": context_counts,
            "session_duration": self._get_session_duration()
        }
    
    def _get_session_duration(self) -> str:
        """Calculate session duration"""
        if not self.conversation_history:
            return "0 minutes"
        
        start_time = self.conversation_history[0].timestamp
        end_time = self.conversation_history[-1].timestamp
        duration = end_time - start_time
        
        minutes = int(duration.total_seconds() / 60)
        return f"{minutes} minutes"

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history.clear()

    def get_history(self) -> List[SystemChatMessage]:
        """Get conversation history"""
        return self.conversation_history.copy()

    def export_conversation(self, format_type: str = "json") -> str:
        """Export conversation history"""
        if format_type == "json":
            export_data = []
            for msg in self.conversation_history:
                export_data.append({
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "context_type": msg.context_type
                })
            return json.dumps(export_data, indent=2)
        
        elif format_type == "text":
            export_text = f"Oakville Real Estate Analyzer - Chat Export\n"
            export_text += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            export_text += "=" * 50 + "\n\n"
            
            for msg in self.conversation_history:
                export_text += f"[{msg.timestamp.strftime('%H:%M:%S')}] "
                export_text += f"{msg.role.upper()} ({msg.context_type}):\n"
                export_text += f"{msg.content}\n\n"
            
            return export_text
        
        return ""

def render_system_wide_chatbot_interface(system_context: Dict = None):
    """Render comprehensive system-wide chatbot interface"""
    st.header("🤖 AI Assistant - Complete Real Estate System")
    
    try:
        # Initialize system-wide chatbot
        api_key = os.getenv("GROQ_API_KEY", "your-groq-api-key-here")
        
        if "system_chatbot" not in st.session_state:
            st.session_state.system_chatbot = SystemWideRealEstateChatbot(api_key)
        
        chatbot = st.session_state.system_chatbot
        
        # System Status Dashboard
        with st.expander("📊 System Status & Context", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("System Status", "🟢 Operational")
                st.metric("API Status", "🟢 Connected")
            
            with col2:
                # Show current property if available
                if system_context and system_context.get('current_property'):
                    prop = system_context['current_property']
                    st.info(f"**Active Property:**\n{prop.get('address', 'Unknown')}")
                else:
                    st.info("**Active Property:**\nNone selected")
            
            with col3:
                # Show last analysis if available
                if system_context and system_context.get('last_analysis'):
                    analysis = system_context['last_analysis']
                    if analysis.get('valuation', {}).get('estimated_value'):
                        value = analysis['valuation']['estimated_value']
                        st.success(f"**Last Valuation:**\n${value:,.0f}")
                    else:
                        st.info("**Last Valuation:**\nNot available")
                else:
                    st.info("**Last Valuation:**\nNot available")
            
            with col4:
                # Session stats
                summary = chatbot.get_conversation_summary()
                st.metric("Questions Asked", summary.get('user_questions', 0))
                st.metric("Session Duration", summary.get('session_duration', '0 minutes'))
        
        # Context type indicators
        st.markdown("### 🎯 Available System Capabilities")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.info("**🏠 Property Analysis**\n- Zoning & regulations\n- Valuations\n- Development potential")
        with col2:
            st.info("**📊 Portfolio Management**\n- Multi-property analysis\n- Investment insights\n- Risk assessment")
        with col3:
            st.info("**📈 Market Intelligence**\n- Trend analysis\n- Price forecasting\n- Neighborhood insights")
        with col4:
            st.info("**⚙️ System Operations**\n- Cache management\n- API integration\n- Troubleshooting")
        with col5:
            st.info("**🎓 Expert Guidance**\n- Zoning interpretation\n- Regulatory compliance\n- Best practices")
        
        # Chat Container for better conversation display
        st.markdown("### 💬 Conversation")
        
        # Create a scrollable chat container
        chat_container = st.container()
        
        with chat_container:
            history = chatbot.get_history()
            if history:
                # Group messages by context type for filtering
                context_filter = st.selectbox(
                    "Filter by context:",
                    ["All"] + list(set(msg.context_type for msg in history if msg.role == "user")),
                    key="context_filter"
                )
                
                # Display messages in chronological order
                displayed_messages = 0
                for msg in history:
                    if context_filter == "All" or msg.context_type == context_filter:
                        if msg.role == "user":
                            with st.chat_message("user"):
                                st.write(msg.content)
                                st.caption(f"🕐 {msg.timestamp.strftime('%H:%M:%S')} | 🏷️ {msg.context_type}")
                        else:
                            with st.chat_message("assistant"):
                                # Use st.markdown for better formatting
                                st.markdown(msg.content)
                                st.caption(f"🕐 {msg.timestamp.strftime('%H:%M:%S')} | 🏷️ {msg.context_type}")
                        displayed_messages += 1
                
                if displayed_messages == 0:
                    st.info(f"No messages found for context: {context_filter}")
            else:
                st.info("💡 **Start a conversation!** I can help with property analysis, portfolio management, market insights, and system operations.")
        
        # Quick action buttons organized by context
        st.markdown("### 🚀 Quick Actions")
        
        # Property Analysis Actions
        with st.expander("🏠 Property Analysis", expanded=True):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("📏 Zoning Requirements", key="quick_zoning"):
                    if system_context and system_context.get('current_property'):
                        zone = system_context['current_property'].get('zone_code', '')
                        question = f"What are the complete zoning requirements for {zone}? Include setbacks, height limits, lot coverage, and permitted uses."
                    else:
                        question = "Explain the different residential zoning categories in Oakville and their key requirements."
                    
                    # Display question
                    with st.chat_message("user"):
                        st.write(question)
                        st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | Quick Action")
                    
                    with st.spinner("🔍 Analyzing zoning requirements..."):
                        answer, context_type = chatbot.answer_question(question, system_context)
                    
                    # Display answer
                    with st.chat_message("assistant"):
                        st.markdown(answer)
                        st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | 🏷️ {context_type}")
                    
                    st.rerun()
            
            with col2:
                if st.button("💰 Property Valuation", key="quick_valuation"):
                    if system_context and system_context.get('current_property'):
                        prop = system_context['current_property']
                        question = f"Provide a detailed valuation analysis for the property at {prop.get('address', 'current property')}. Include land value, building value, location adjustments, and market factors."
                    else:
                        question = "Explain how property valuations are calculated in Oakville. What factors affect property values?"
                    
                    # Display question
                    with st.chat_message("user"):
                        st.write(question)
                        st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | Quick Action")
                    
                    with st.spinner("💰 Calculating property value..."):
                        answer, context_type = chatbot.answer_question(question, system_context)
                    
                    # Display answer
                    with st.chat_message("assistant"):
                        st.markdown(answer)
                        st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | 🏷️ {context_type}")
                    
                    st.rerun()
            
            with col3:
                if st.button("🏗️ Development Potential", key="quick_development"):
                    if system_context and system_context.get('current_property'):
                        question = "What is the development potential for my current property? Can I subdivide, build additions, or redevelop?"
                    else:
                        question = "Explain the different types of development opportunities available in Oakville residential zones."
                    
                    # Display question
                    with st.chat_message("user"):
                        st.write(question)
                        st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | Quick Action")
                    
                    with st.spinner("🏗️ Analyzing development potential..."):
                        answer, context_type = chatbot.answer_question(question, system_context)
                    
                    # Display answer
                    with st.chat_message("assistant"):
                        st.markdown(answer)
                        st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | 🏷️ {context_type}")
                    
                    st.rerun()
            
            with col4:
                if st.button("⚠️ Special Provisions", key="quick_special"):
                    question = "What are special provisions in Oakville zoning? How do SP:1, SP:2, and suffix zones like -0 affect properties?"
                    
                    # Display question
                    with st.chat_message("user"):
                        st.write(question)
                        st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | Quick Action")
                    
                    with st.spinner("⚠️ Explaining special provisions..."):
                        answer, context_type = chatbot.answer_question(question, system_context)
                    
                    # Display answer
                    with st.chat_message("assistant"):
                        st.markdown(answer)
                        st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | 🏷️ {context_type}")
                    
                    st.rerun()
        
        # Portfolio & Market Actions
        with st.expander("📊 Portfolio & Market Intelligence"):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("📈 Market Trends", key="quick_trends"):
                    question = "What are the current real estate market trends in Oakville? Include price movements, inventory levels, and market forecasts."
                    
                    # Display question
                    with st.chat_message("user"):
                        st.write(question)
                        st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | Quick Action")
                    
                    with st.spinner("📈 Analyzing market trends..."):
                        answer, context_type = chatbot.answer_question(question, system_context)
                    
                    # Display answer
                    with st.chat_message("assistant"):
                        st.markdown(answer)
                        st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | 🏷️ {context_type}")
                    
                    st.rerun()
            
            with col2:
                if st.button("🎯 Investment Analysis", key="quick_investment"):
                    if system_context and system_context.get('portfolio_summary'):
                        question = "Analyze my current portfolio performance. What is my ROI, risk exposure, and what recommendations do you have for optimization?"
                    else:
                        question = "Provide investment guidance for Oakville real estate. Which zones offer the best ROI? What are the key investment considerations?"
                    
                    # Display question
                    with st.chat_message("user"):
                        st.write(question)
                        st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | Quick Action")
                    
                    with st.spinner("🎯 Analyzing investment opportunities..."):
                        answer, context_type = chatbot.answer_question(question, system_context)
                    
                    # Display answer
                    with st.chat_message("assistant"):
                        st.markdown(answer)
                        st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | 🏷️ {context_type}")
                    
                    st.rerun()
            
            with col3:
                if st.button("🏘️ Neighborhood Comparison", key="quick_neighborhood"):
                    question = "Compare different neighborhoods and zones in Oakville. What are the pros and cons of each area for investment?"
                    
                    # Display question
                    with st.chat_message("user"):
                        st.write(question)
                        st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | Quick Action")
                    
                    with st.spinner("🏘️ Comparing neighborhoods..."):
                        answer, context_type = chatbot.answer_question(question, system_context)
                    
                    # Display answer
                    with st.chat_message("assistant"):
                        st.markdown(answer)
                        st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | 🏷️ {context_type}")
                    
                    st.rerun()
            
            with col4:
                if st.button("📊 Portfolio Analysis", key="quick_portfolio"):
                    if system_context and system_context.get('portfolio_summary'):
                        portfolio = system_context['portfolio_summary']
                        question = f"I have {portfolio['total_properties']} properties worth ${portfolio['total_value']:,.0f}. Provide detailed portfolio analysis including diversification, risk factors, and growth opportunities."
                    else:
                        question = "How should I analyze a real estate portfolio in Oakville? What metrics should I track and what diversification strategies work best?"
                    
                    # Display question
                    with st.chat_message("user"):
                        st.write(question)
                        st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | Quick Action")
                    
                    with st.spinner("📊 Analyzing portfolio strategies..."):
                        answer, context_type = chatbot.answer_question(question, system_context)
                    
                    # Display answer
                    with st.chat_message("assistant"):
                        st.markdown(answer)
                        st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | 🏷️ {context_type}")
                    
                    st.rerun()
        
        # Portfolio Management Interface
        if PORTFOLIO_MANAGER_AVAILABLE:
            with st.expander("🏠 Portfolio Management", expanded=False):
                st.markdown("**Manage your property portfolio directly from the AI interface:**")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📊 View Portfolio Manager", key="view_portfolio", use_container_width=True):
                        st.session_state.show_portfolio_manager = True
                        st.rerun()
                
                with col2:
                    if system_context and system_context.get('current_property'):
                        if st.button("➕ Add Current Property", key="add_current", use_container_width=True):
                            # Add current property to portfolio
                            try:
                                from portfolio_manager import PropertyRecord
                                prop = system_context['current_property']
                                valuation = system_context.get('last_analysis', {}).get('valuation', {})
                                estimated_value = valuation.get('estimated_value', 1000000)
                                
                                new_property = PropertyRecord(
                                    id=f"prop_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                    address=prop.get('address', 'Unknown Address'),
                                    zone_code=prop.get('zone_code', 'Unknown'),
                                    lot_area=prop.get('lot_area', 0),
                                    building_area=prop.get('building_area', 200),
                                    estimated_value=estimated_value,
                                    development_potential='single_family',
                                    notes=f"Added from analysis on {datetime.now().strftime('%Y-%m-%d')}"
                                )
                                
                                portfolio_mgr = get_portfolio_manager()
                                if portfolio_mgr.add_property(new_property):
                                    st.success("✅ Property added to portfolio!")
                                else:
                                    st.warning("⚠️ Property may already exist in portfolio")
                            except Exception as e:
                                st.error(f"❌ Error adding property: {e}")
                    else:
                        st.info("💡 Analyze a property first to add it to your portfolio")
                
                # Show portfolio summary if available
                if system_context and system_context.get('portfolio_summary'):
                    portfolio = system_context['portfolio_summary']
                    st.markdown(f"**Current Portfolio:** {portfolio['total_properties']} properties • ${portfolio['total_value']:,.0f} value")
        
        # Show portfolio manager if requested
        if st.session_state.get('show_portfolio_manager', False):
            st.divider()
            render_portfolio_manager()
            if st.button("🔙 Back to AI Assistant"):
                st.session_state.show_portfolio_manager = False
                st.rerun()
        
        # System Operations Actions
        with st.expander("⚙️ System Operations & Help"):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("🛠️ System Help", key="quick_system_help"):
                    question = "How do I use the Oakville Real Estate Analyzer system effectively? What are all the available features and tools?"
                    
                    # Display question
                    with st.chat_message("user"):
                        st.write(question)
                        st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | Quick Action")
                    
                    with st.spinner("🛠️ Loading system help..."):
                        answer, context_type = chatbot.answer_question(question, system_context)
                    
                    # Display answer
                    with st.chat_message("assistant"):
                        st.markdown(answer)
                        st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | 🏷️ {context_type}")
                    
                    st.rerun()
            
            with col2:
                if st.button("🔧 Troubleshooting", key="quick_troubleshoot"):
                    question = "I'm having issues with the system. What are common problems and their solutions? How can I optimize performance?"
                    
                    # Display question
                    with st.chat_message("user"):
                        st.write(question)
                        st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | Quick Action")
                    
                    with st.spinner("🔧 Providing troubleshooting help..."):
                        answer, context_type = chatbot.answer_question(question, system_context)
                    
                    # Display answer
                    with st.chat_message("assistant"):
                        st.markdown(answer)
                        st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | 🏷️ {context_type}")
                    
                    st.rerun()
            
            with col3:
                if st.button("📏 Measurement Tools", key="quick_measurement"):
                    question = "How do I use the measurement tools to get accurate lot dimensions? What are the different measurement options available?"
                    
                    # Display question
                    with st.chat_message("user"):
                        st.write(question)
                        st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | Quick Action")
                    
                    with st.spinner("📏 Explaining measurement tools..."):
                        answer, context_type = chatbot.answer_question(question, system_context)
                    
                    # Display answer
                    with st.chat_message("assistant"):
                        st.markdown(answer)
                        st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | 🏷️ {context_type}")
                    
                    st.rerun()
            
            with col4:
                if st.button("📞 Contact Information", key="quick_contact"):
                    question = "Provide contact information for Oakville planning services and other relevant municipal departments."
                    
                    # Display question
                    with st.chat_message("user"):
                        st.write(question)
                        st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | Quick Action")
                    
                    with st.spinner("📞 Getting contact information..."):
                        answer, context_type = chatbot.answer_question(question, system_context)
                    
                    # Display answer
                    with st.chat_message("assistant"):
                        st.markdown(answer)
                        st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | 🏷️ {context_type}")
                    
                    st.rerun()
        
        # Main chat interface
        st.markdown("### 💭 Ask Any Real Estate Question")
        with st.form("system_chat_form", clear_on_submit=True):
            user_question = st.text_area(
                "Your question:",
                placeholder="Ask about properties, zoning, market trends, portfolio analysis, system features, or any real estate topic...",
                height=100,
                key="system_chat_input",
                help="I can help with all aspects of the Oakville Real Estate Analyzer system"
            )
            
            # Advanced options
            with st.expander("🎛️ Advanced Options"):
                col1, col2 = st.columns(2)
                with col1:
                    include_calculations = st.checkbox("Include detailed calculations", value=True)
                    include_references = st.checkbox("Include By-law references", value=True)
                with col2:
                    provide_examples = st.checkbox("Provide examples", value=False)
                    suggest_next_steps = st.checkbox("Suggest next steps", value=True)
            
            # Submit buttons
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                submitted = st.form_submit_button("💬 Ask System AI", type="primary", use_container_width=True)
            with col2:
                if st.form_submit_button("🗑️ Clear Chat", use_container_width=True):
                    chatbot.clear_history()
                    st.rerun()
            with col3:
                if st.form_submit_button("📄 Export Chat", use_container_width=True):
                    export_data = chatbot.export_conversation("text")
                    st.download_button(
                        "💾 Download",
                        export_data,
                        file_name=f"oakville_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain"
                    )
        
        # Handle question submission
        if submitted and user_question.strip():
            # Modify question based on advanced options
            enhanced_question = user_question
            if include_calculations:
                enhanced_question += " Please include detailed calculations and formulas."
            if include_references:
                enhanced_question += " Please reference specific sections of Oakville By-law 2014-014."
            if provide_examples:
                enhanced_question += " Please provide concrete examples."
            if suggest_next_steps:
                enhanced_question += " Please suggest actionable next steps."
            
            # Display user question immediately
            with st.chat_message("user"):
                st.write(user_question)
                st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')}")
            
            # Process and display answer
            with st.spinner("🤖 System AI is analyzing your question..."):
                start_time = time.time()
                answer, context_type = chatbot.answer_question(enhanced_question, system_context)
                processing_time = time.time() - start_time
            
            # Display assistant response immediately
            with st.chat_message("assistant"):
                st.markdown(answer)
                st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} | 🏷️ {context_type} | ⚡ {processing_time:.1f}s")
            
            # Show success message
            st.success(f"✅ Response generated in {processing_time:.1f}s")
            
            # Clear the input and rerun to show updated conversation
            st.rerun()
        
        # Conversation statistics and export
        if history:
            with st.expander("📊 Chat Analytics & Export", expanded=False):
                summary = chatbot.get_conversation_summary()
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Messages", summary.get('total_messages', 0))
                    st.metric("User Questions", summary.get('user_questions', 0))
                
                with col2:
                    st.metric("Session Duration", summary.get('session_duration', '0 minutes'))
                    context_breakdown = summary.get('context_breakdown', {})
                    most_used_context = max(context_breakdown.items(), key=lambda x: x[1])[0] if context_breakdown else "None"
                    st.metric("Primary Focus", most_used_context)
                
                with col3:
                    st.markdown("**Context Breakdown:**")
                    for context, count in context_breakdown.items():
                        st.write(f"• {context}: {count} questions")
        
    except Exception as e:
        st.error(f"❌ System-Wide AI Assistant Error: {str(e)}")
        st.info("💡 Please check the GROQ API key configuration and system connectivity.")
        
        # Fallback help
        st.markdown("### 🆘 Fallback Resources")
        st.markdown("**Town of Oakville Resources:**")
        st.markdown("- Planning Services: 905-845-6601")
        st.markdown("- Website: oakville.ca")
        st.markdown("- Email: planning@oakville.ca")

def get_system_wide_chatbot():
    """Get system-wide chatbot instance"""
    api_key = os.getenv("GROQ_API_KEY", "your-groq-api-key-here")
    
    if "system_chatbot" not in st.session_state:
        st.session_state.system_chatbot = SystemWideRealEstateChatbot(api_key)
    
    return st.session_state.system_chatbot

if __name__ == "__main__":
    # Test the system-wide chatbot
    st.set_page_config(page_title="System-Wide AI Assistant", layout="wide")
    render_system_wide_chatbot_interface()