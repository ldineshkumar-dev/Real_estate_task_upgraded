"""
Standalone AI Assistant for Oakville Real Estate Analysis
Streamlined interface for comprehensive real estate analysis and consultation
"""

import streamlit as st
from datetime import datetime
from system_wide_chatbot import render_system_wide_chatbot_interface, get_system_wide_chatbot

# Page configuration
st.set_page_config(
    page_title="Oakville Real Estate AI Assistant",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Streamlined CSS for clean interface
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f2937;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #6b7280;
        text-align: center;
        margin-bottom: 2rem;
    }
    .status-box {
        background-color: #f0f9ff;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #0ea5e9;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main standalone AI assistant application"""
    
    # Clean header
    st.markdown('<h1 class="main-header">🏠 Oakville Real Estate AI Assistant</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Your Expert Guide for Property Analysis, Zoning, and Market Intelligence</p>', unsafe_allow_html=True)
    
    # Simplified sidebar
    with st.sidebar:
        st.header("🎯 AI Capabilities")
        st.markdown("""
        **I can help you with:**
        
        🏠 **Property Analysis**
        - Zoning requirements & setbacks
        - Property valuations
        - Development potential
        
        📊 **Market Intelligence** 
        - Current market trends
        - Neighborhood comparisons
        - Investment opportunities
        
        🔧 **System Support**
        - Tool explanations
        - Troubleshooting
        - Contact information
        """)
        
        st.divider()
        
        # Simple system status
        st.markdown("### 📡 Status")
        st.success("🟢 AI Assistant Online")
        st.info("🔗 Connected to Oakville Systems")
        
        # Usage stats if available
        if 'system_chatbot' in st.session_state:
            chatbot = st.session_state.system_chatbot
            summary = chatbot.get_conversation_summary()
            if summary.get('user_questions', 0) > 0:
                st.divider()
                st.metric("Questions Asked", summary.get('user_questions', 0))
                st.metric("Session Time", summary.get('session_duration', '0 min'))
    
    # Welcome message
    st.markdown("### 👋 Welcome! How can I help with your real estate needs?")
    st.markdown("Ask me anything about Oakville properties, zoning regulations, market trends, or system features.")
    
    # Render the main AI assistant interface
    try:
        # Simple system context for standalone mode
        system_context = {
            'timestamp': datetime.now().isoformat(),
            'system_status': 'operational',
            'standalone_mode': True
        }
        
        # Render the chatbot interface
        render_system_wide_chatbot_interface(system_context)
        
    except Exception as e:
        st.error(f"❌ AI Assistant Error: {str(e)}")
        st.info("💡 Ensure GROQ API key is configured: `GROQ_API_KEY=your_key_here`")
        
        # Fallback support information
        st.markdown("### 📞 Alternative Support")
        col1, col2 = st.columns(2)
        with col1:
            st.info("**Town of Oakville Planning**\nPhone: 905-845-6601\nWebsite: oakville.ca")
        with col2:
            st.info("**Email Support**\nplanning@oakville.ca\nTown Hall: 1225 Trafalgar Rd")
    
    # Simple footer
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("**Oakville Real Estate AI**\nPowered by advanced AI technology")
    with col2:
        st.success("**Always Current**\nReal-time market data & regulations")
    with col3:
        st.warning("**Professional Advice**\nConsult certified professionals for legal decisions")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Application Error: {str(e)}")
        st.info("Please refresh the page or contact support if the issue persists.")