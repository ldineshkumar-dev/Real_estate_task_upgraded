"""
Streamlit UI Components for Oakville Real Estate AI Chatbot
Interactive chat interface with conversation history and context display
"""

import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Any

import streamlit as st
import pandas as pd
import plotly.express as px

from ai_chatbot import get_ai_chatbot, ChatMessage, ChatResponse

def render_chatbot_interface(property_context: Dict = None):
    """Render the main chatbot interface"""
    st.header("🤖 AI Assistant - Oakville Real Estate Expert")
    
    # Initialize chatbot
    try:
        chatbot = get_ai_chatbot()
        
        # Display chatbot status
        stats = chatbot.get_chat_statistics()
        
        with st.expander("🔍 AI Assistant Information", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Knowledge Base", f"{stats['knowledge_base_size']} documents")
                st.metric("Model", "GROQ Mixtral-8x7b")
                
            with col2:
                st.metric("Session Messages", stats['total_messages'])
                if stats['last_activity']:
                    last_activity = datetime.fromisoformat(stats['last_activity'])
                    st.metric("Last Activity", last_activity.strftime("%H:%M:%S"))
                
            with col3:
                st.metric("Session Duration", f"{stats['session_duration']:.1f} min")
                confidence_color = "🟢" if stats['knowledge_base_size'] > 50 else "🟡" if stats['knowledge_base_size'] > 20 else "🔴"
                st.metric("Status", f"{confidence_color} Ready")
        
        # Property context display
        if property_context:
            render_property_context(property_context)
        
        # Chat interface
        render_chat_messages(chatbot)
        render_chat_input(chatbot, property_context)
        
        # Chat controls
        render_chat_controls(chatbot)
        
    except Exception as e:
        st.error(f"❌ Failed to initialize AI Assistant: {str(e)}")
        st.info("💡 Please check that the GROQ API key is configured correctly.")
        
        with st.expander("🔧 Troubleshooting"):
            st.markdown("""
            **Common Issues:**
            1. **API Key**: Ensure GROQ API key is valid and has sufficient quota
            2. **Dependencies**: Install required packages: `pip install groq sentence-transformers chromadb`
            3. **Internet**: Check internet connection for API access
            4. **Rate Limits**: Wait a few seconds between requests if hitting rate limits
            
            **Fallback Options:**
            - Use the FAQ section below for common questions
            - Consult the Zoning Analysis tab for detailed regulations
            - Contact Town of Oakville Planning Services: 905-845-6601
            """)

def render_property_context(property_context: Dict):
    """Render current property context information"""
    with st.container():
        st.markdown("### 🏠 Current Property Context")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            address = property_context.get('address', 'Not specified')
            st.info(f"**Address:** {address}")
            
        with col2:
            zone = property_context.get('zone_code', 'Unknown')
            suffix = property_context.get('suffix', '')
            special = property_context.get('special_provision', '')
            
            zone_display = zone
            if suffix:
                zone_display += suffix
            if special:
                zone_display += f" ({special})"
                
            st.info(f"**Zone:** {zone_display}")
        
        with col3:
            lot_area = property_context.get('lot_area', 0)
            if lot_area:
                st.info(f"**Lot Area:** {lot_area:.0f} m²")
            else:
                st.info("**Lot Area:** Not specified")
        
        with col4:
            frontage = property_context.get('lot_frontage', 0)
            if frontage:
                st.info(f"**Frontage:** {frontage:.1f} m")
            else:
                st.info("**Frontage:** Not specified")
        
        if special:
            st.warning(f"⚠️ **Special Provision Active:** {special} - This may override standard zoning regulations")

def render_chat_messages(chatbot):
    """Render chat message history"""
    messages = chatbot.get_conversation_history()
    
    if not messages:
        st.markdown("### 💬 Start a Conversation")
        st.markdown("Ask me anything about Oakville zoning, property regulations, or real estate analysis!")
        
        # Suggested questions
        st.markdown("**💡 Try asking:**")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("- What is RL2 zoning?")
            st.markdown("- What are the setback requirements for my zone?")
            st.markdown("- Can I build a duplex in RL2?")
            
        with col2:
            st.markdown("- What does SP:1 mean?")
            st.markdown("- How do I calculate lot coverage?")
            st.markdown("- What's the maximum building height in RH zones?")
        
        return
    
    st.markdown("### 💬 Conversation")
    
    # Create chat container
    chat_container = st.container()
    
    with chat_container:
        for message in messages:
            if message.role == "user":
                render_user_message(message)
            elif message.role == "assistant":
                render_assistant_message(message)

def render_user_message(message: ChatMessage):
    """Render a user message"""
    with st.chat_message("user"):
        st.write(message.content)
        st.caption(f"🕐 {message.timestamp.strftime('%H:%M:%S')}")

def render_assistant_message(message: ChatMessage):
    """Render an assistant message with sources and context"""
    with st.chat_message("assistant"):
        st.markdown(message.content)
        
        # Show sources and context if available
        col1, col2 = st.columns([3, 1])
        
        with col2:
            st.caption(f"🕐 {message.timestamp.strftime('%H:%M:%S')}")
            
            if message.sources:
                with st.expander("📚 Sources", expanded=False):
                    for source in message.sources[:5]:  # Limit to 5 sources
                        st.caption(f"• {source}")
            
            if message.context_used:
                with st.expander("🔍 Context Used", expanded=False):
                    for i, context in enumerate(message.context_used[:3], 1):
                        with st.container():
                            st.caption(f"**Context {i}:**")
                            st.caption(context[:150] + "..." if len(context) > 150 else context)
                            st.divider()

def render_chat_input(chatbot, property_context: Dict = None):
    """Render chat input interface"""
    st.markdown("### ✍️ Ask Your Question")
    
    # Quick question buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("What are my zone's setback requirements?", key="quick1"):
            if property_context and property_context.get('zone_code'):
                question = f"What are the setback requirements for {property_context['zone_code']} zoning?"
                process_chat_message(chatbot, question, property_context)
            else:
                st.warning("Please specify a property first to get zone-specific information.")
                
    with col2:
        if st.button("What can I build in my zone?", key="quick2"):
            if property_context and property_context.get('zone_code'):
                question = f"What are the permitted uses and building types for {property_context['zone_code']} zoning?"
                process_chat_message(chatbot, question, property_context)
            else:
                st.warning("Please specify a property first to get zone-specific information.")
    
    with col3:
        if st.button("How do I measure my lot?", key="quick3"):
            question = "How do I accurately measure my property lot area, frontage and depth?"
            process_chat_message(chatbot, question, property_context)
    
    # Text input
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_area(
            "Your question:",
            placeholder="Ask about zoning regulations, setbacks, permitted uses, lot requirements, or any real estate topic...",
            height=100,
            key="user_input"
        )
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            submitted = st.form_submit_button("💬 Send Message", type="primary", use_container_width=True)
        
        with col2:
            include_context = st.checkbox("Use property context", value=True, 
                                        help="Include current property information in the query")
        
        with col3:
            expert_mode = st.checkbox("Expert mode", value=False,
                                    help="Include technical details and by-law references")
    
    if submitted and user_input.strip():
        # Add expert mode context to question
        if expert_mode:
            user_input += " Please include specific by-law section references and technical details."
        
        context_to_use = property_context if include_context else None
        process_chat_message(chatbot, user_input, context_to_use)

def process_chat_message(chatbot, question: str, property_context: Dict = None):
    """Process a chat message and display response"""
    try:
        # Show thinking indicator
        with st.spinner("🤔 AI is thinking..."):
            start_time = time.time()
            
            # Get response from chatbot
            response: ChatResponse = chatbot.answer_question(question, property_context)
            
            processing_time = time.time() - start_time
        
        # Display response metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Response Time", f"{processing_time:.1f}s")
        with col2:
            st.metric("Confidence", f"{response.confidence:.0%}")
        with col3:
            st.metric("Sources Used", len(response.sources))
        with col4:
            st.metric("Tokens", response.tokens_used)
        
        # Show confidence indicator
        if response.confidence >= 0.8:
            st.success("🎯 High confidence response")
        elif response.confidence >= 0.6:
            st.info("📊 Medium confidence response")
        else:
            st.warning("⚠️ Low confidence - consider consulting Planning Services")
        
        st.rerun()  # Refresh to show new messages
        
    except Exception as e:
        st.error(f"❌ Error processing message: {str(e)}")

def render_chat_controls(chatbot):
    """Render chat control buttons"""
    st.markdown("### 🛠️ Chat Controls")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🗑️ Clear Chat", help="Clear conversation history"):
            chatbot.clear_conversation_history()
            st.success("Chat history cleared!")
            st.rerun()
    
    with col2:
        if st.button("📊 Chat Stats", help="Show conversation statistics"):
            show_chat_statistics(chatbot)
    
    with col3:
        format_option = st.selectbox("Export Format", ["JSON", "Text"], key="export_format")
        if st.button("📥 Export Chat", help="Export conversation history"):
            export_conversation(chatbot, format_option.lower())
    
    with col4:
        if st.button("❓ Show FAQ", help="Display frequently asked questions"):
            show_faq_section()

def show_chat_statistics(chatbot):
    """Display detailed chat statistics"""
    stats = chatbot.get_chat_statistics()
    
    st.markdown("#### 📊 Chat Session Statistics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Messages", stats['total_messages'])
        st.metric("User Messages", stats['user_messages'])
        st.metric("Assistant Messages", stats['assistant_messages'])
    
    with col2:
        st.metric("Session Duration", f"{stats['session_duration']:.1f} minutes")
        st.metric("Knowledge Base Size", f"{stats['knowledge_base_size']} documents")
        if stats['last_activity']:
            last_time = datetime.fromisoformat(stats['last_activity'])
            st.metric("Last Activity", last_time.strftime("%H:%M:%S"))
    
    # Message timeline
    messages = chatbot.get_conversation_history()
    if messages:
        st.markdown("#### 📈 Message Timeline")
        
        message_data = []
        for msg in messages:
            message_data.append({
                'Time': msg.timestamp,
                'Role': msg.role.title(),
                'Length': len(msg.content)
            })
        
        df = pd.DataFrame(message_data)
        
        fig = px.scatter(df, x='Time', y='Length', color='Role',
                        title='Message Length Over Time',
                        labels={'Length': 'Characters', 'Time': 'Timestamp'})
        
        st.plotly_chart(fig, use_container_width=True)

def export_conversation(chatbot, format: str):
    """Export conversation in specified format"""
    try:
        exported_data = chatbot.export_conversation(format)
        
        if format == "json":
            st.download_button(
                label="📥 Download JSON",
                data=exported_data,
                file_name=f"oakville_chat_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json"
            )
        else:
            st.download_button(
                label="📥 Download Text",
                data=exported_data,
                file_name=f"oakville_chat_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain"
            )
        
        st.success("📥 Conversation exported successfully!")
        
    except Exception as e:
        st.error(f"❌ Export failed: {str(e)}")

def show_faq_section():
    """Display FAQ section with common questions"""
    st.markdown("### ❓ Frequently Asked Questions")
    
    # Load FAQ data
    try:
        chatbot = get_ai_chatbot()
        faq_data = chatbot.knowledge_base.load_faq_data()
        
        # Categorize questions
        categories = {}
        for item in faq_data:
            category = item.get('category', 'general')
            if category not in categories:
                categories[category] = []
            categories[category].append(item)
        
        # Display by category
        for category, questions in categories.items():
            with st.expander(f"📂 {category.replace('_', ' ').title()}", expanded=False):
                for i, qa in enumerate(questions):
                    st.markdown(f"**Q{i+1}: {qa['question']}**")
                    st.markdown(qa['answer'])
                    
                    if qa.get('zone_codes'):
                        zones = [z for z in qa['zone_codes'] if z != 'all']
                        if zones:
                            st.caption(f"🏷️ Relevant zones: {', '.join(zones)}")
                    
                    if qa.get('related_sections'):
                        st.caption(f"📖 By-law sections: {', '.join(qa['related_sections'])}")
                    
                    st.divider()
        
    except Exception as e:
        st.error(f"❌ Could not load FAQ data: {str(e)}")

def render_compact_chat():
    """Render a compact version of the chat interface for sidebar or small spaces"""
    st.markdown("#### 🤖 Quick AI Assistant")
    
    try:
        chatbot = get_ai_chatbot()
        
        # Compact input
        user_question = st.text_input(
            "Quick question:",
            placeholder="Ask about zoning...",
            key="compact_chat"
        )
        
        if st.button("💬 Ask", type="primary", key="compact_ask"):
            if user_question.strip():
                with st.spinner("Thinking..."):
                    response = chatbot.answer_question(user_question)
                    st.success(f"**Answer:** {response.content[:200]}...")
                    if len(response.content) > 200:
                        with st.expander("📄 Full Answer"):
                            st.write(response.content)
        
        # Show last few messages
        messages = chatbot.get_conversation_history()
        if messages:
            with st.expander(f"💬 Recent ({len(messages)} messages)", expanded=False):
                for msg in messages[-3:]:  # Show last 3 messages
                    if msg.role == "user":
                        st.caption(f"**You:** {msg.content[:100]}...")
                    else:
                        st.caption(f"**AI:** {msg.content[:100]}...")
        
    except Exception as e:
        st.error("AI Assistant unavailable")

def render_context_aware_suggestions(property_context: Dict):
    """Render context-aware question suggestions"""
    if not property_context:
        return
    
    zone_code = property_context.get('zone_code', '')
    special_provision = property_context.get('special_provision', '')
    
    st.markdown("#### 💡 Suggested Questions for Your Property")
    
    suggestions = [
        f"What are the specific requirements for {zone_code} zoning?",
        f"What is the maximum building size I can build in {zone_code}?",
        f"What are the setback requirements for {zone_code}?",
        "How do I calculate my lot coverage?",
        "What accessory buildings can I build?"
    ]
    
    if special_provision:
        suggestions.insert(1, f"What does {special_provision} mean for my property?")
    
    if zone_code.endswith('-0'):
        suggestions.append("What are the special restrictions for -0 suffix zones?")
    
    for suggestion in suggestions[:5]:  # Limit to 5 suggestions
        if st.button(suggestion, key=f"suggest_{suggestion[:20]}"):
            chatbot = get_ai_chatbot()
            process_chat_message(chatbot, suggestion, property_context)