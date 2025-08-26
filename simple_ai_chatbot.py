"""
Simple AI Chatbot for Oakville Real Estate Analyzer
GROQ LLM integration without RAG - Basic knowledge embedded in prompts
"""

import os
import time
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

import streamlit as st
from groq import Groq

logger = logging.getLogger(__name__)

@dataclass
class SimpleChatMessage:
    """Represents a simple chat message"""
    role: str
    content: str
    timestamp: datetime

class SimpleOakvilleChatbot:
    """Simple AI chatbot using GROQ with embedded knowledge"""
    
    def __init__(self, groq_api_key: str):
        """Initialize the simple chatbot"""
        if not groq_api_key:
            raise ValueError("GROQ API key is required")
            
        self.groq_client = Groq(api_key=groq_api_key)
        self.model = "mixtral-8x7b-32768"
        self.conversation_history: List[SimpleChatMessage] = []
        
        # Embedded Oakville zoning knowledge
        self.knowledge_base = self._get_embedded_knowledge()
        
    def _get_embedded_knowledge(self) -> str:
        """Get embedded Oakville zoning knowledge"""
        return """
OAKVILLE ZONING BY-LAW 2014-014 REFERENCE GUIDE:

RESIDENTIAL ZONES:
- RL1: Min 1,393.5 m² area, 30.5m frontage, 12m height, 25% coverage
- RL2: Min 836.0 m² area, 22.5m frontage, 12m height, 30% coverage  
- RL3: Min 557.5 m² area, 18.0m frontage, 12m height, 30% coverage
- RL4: Min 511.0 m² area, 16.5m frontage, 12m height, 35% coverage
- RL5: Min 464.5 m² area, 15.0m frontage, 12m height, 35% coverage
- RL6: Min 250.0 m² area, 11.0m frontage, 12m height, 40% coverage
- RUC: Min 220.0 m² area, 7.0m frontage, varies by location
- RH: Residential High - existing building heights grandfathered

SETBACK REQUIREMENTS (RL2 Example):
- Front yard: 9.0m minimum
- Rear yard: 7.5m minimum
- Interior side: 2.4m minimum (1.2m with attached garage)
- Flankage yard: 3.5m minimum

SPECIAL PROVISIONS:
- SP:1 = Enhanced residential development standards
- SP:2 = Modified setback requirements
- -0 Suffix = Maximum 2 storeys, 9.0m height, FAR restrictions

SUFFIX ZONES (-0):
- Maximum 2 storeys permitted
- Maximum 9.0 meters height
- No floor area above second storey
- Specific FAR limits based on lot size
- Enhanced lot coverage restrictions

COMMON QUESTIONS:
Q: What is RL2 zoning?
A: Single-family residential requiring 836.0 m² minimum lot, 22.5m frontage, permits detached dwellings.

Q: Can I build a duplex in RL2?
A: No, RL2 only permits detached single-family dwellings. Duplexes require RL10 or higher zones.

Q: What does SP:1 mean?
A: Special Provision 1 provides site-specific regulations that override general by-law requirements.

CONTACT: Town of Oakville Planning Services: 905-845-6601
"""
    
    def answer_question(self, question: str, property_context: Dict = None) -> str:
        """Answer a question using GROQ with embedded knowledge"""
        try:
            # Build context-aware prompt
            system_prompt = f"""You are an expert assistant for Oakville, Ontario real estate and zoning regulations. 

KNOWLEDGE BASE:
{self.knowledge_base}

CURRENT PROPERTY CONTEXT:
"""
            if property_context:
                system_prompt += f"""
- Address: {property_context.get('address', 'Not specified')}
- Zone: {property_context.get('zone_code', 'Unknown')}
- Lot Area: {property_context.get('lot_area', 'Not specified')} m²
- Frontage: {property_context.get('lot_frontage', 'Not specified')} m
"""
                if property_context.get('special_provision'):
                    system_prompt += f"- Special Provision: {property_context['special_provision']}\n"
            
            system_prompt += """
INSTRUCTIONS:
1. Answer based on the Oakville Zoning By-law 2014-014 knowledge provided
2. Be specific about measurements, requirements, and restrictions
3. If asked about specific zones, provide detailed dimensional requirements
4. For calculations, show your work step-by-step
5. If unsure, recommend consulting Planning Services at 905-845-6601
6. Keep answers professional and helpful
"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ]
            
            # Add recent conversation context
            for msg in self.conversation_history[-4:]:  # Last 4 messages
                messages.append({
                    "role": msg.role,
                    "content": msg.content[:500]  # Truncate long messages
                })
            
            messages.append({"role": "user", "content": question})
            
            # Get response from GROQ
            response = self.groq_client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1000,
                temperature=0.1,
                top_p=0.9
            )
            
            answer = response.choices[0].message.content
            
            # Store conversation
            self.conversation_history.append(SimpleChatMessage(
                role="user", content=question, timestamp=datetime.now()
            ))
            self.conversation_history.append(SimpleChatMessage(
                role="assistant", content=answer, timestamp=datetime.now()
            ))
            
            # Keep history manageable
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]
            
            return answer
            
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return f"I apologize, but I encountered an error: {str(e)}\n\nFor accurate information, please contact Town of Oakville Planning Services at 905-845-6601."
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history.clear()
    
    def get_history(self) -> List[SimpleChatMessage]:
        """Get conversation history"""
        return self.conversation_history.copy()

def render_simple_chatbot_interface(property_context: Dict = None):
    """Render simple chatbot interface"""
    st.header("🤖 AI Assistant - Oakville Zoning Expert")
    
    try:
        # Initialize chatbot
        api_key = os.getenv("GROQ_API_KEY", "your-groq-api-key-here")
        
        if "simple_chatbot" not in st.session_state:
            st.session_state.simple_chatbot = SimpleOakvilleChatbot(api_key)
        
        chatbot = st.session_state.simple_chatbot
        
        # Display property context if available
        if property_context:
            with st.expander("🏠 Current Property Context", expanded=False):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.info(f"**Address:** {property_context.get('address', 'Not specified')}")
                with col2:
                    zone_display = property_context.get('zone_code', 'Unknown')
                    if property_context.get('special_provision'):
                        zone_display += f" ({property_context['special_provision']})"
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
        
        # Show conversation history
        history = chatbot.get_history()
        if history:
            st.markdown("### 💬 Conversation")
            for msg in history:
                if msg.role == "user":
                    with st.chat_message("user"):
                        st.write(msg.content)
                        st.caption(f"🕐 {msg.timestamp.strftime('%H:%M:%S')}")
                else:
                    with st.chat_message("assistant"):
                        st.markdown(msg.content)
                        st.caption(f"🕐 {msg.timestamp.strftime('%H:%M:%S')}")
        else:
            st.markdown("### 💬 Ask Your Zoning Questions")
            st.info("I can help with Oakville zoning regulations, setbacks, lot requirements, and property analysis!")
        
        # Quick question buttons
        st.markdown("### 💡 Quick Questions")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("What are the setbacks for my zone?", key="quick_setbacks"):
                if property_context and property_context.get('zone_code'):
                    question = f"What are the setback requirements for {property_context['zone_code']} zoning?"
                    with st.spinner("🤔 Thinking..."):
                        answer = chatbot.answer_question(question, property_context)
                    st.rerun()
        
        with col2:
            if st.button("What can I build in my zone?", key="quick_build"):
                if property_context and property_context.get('zone_code'):
                    question = f"What are the permitted uses for {property_context['zone_code']} zoning?"
                    with st.spinner("🤔 Thinking..."):
                        answer = chatbot.answer_question(question, property_context)
                    st.rerun()
        
        with col3:
            if st.button("Explain special provisions", key="quick_sp"):
                if property_context and property_context.get('special_provision'):
                    question = f"What does {property_context['special_provision']} mean for my property?"
                    with st.spinner("🤔 Thinking..."):
                        answer = chatbot.answer_question(question, property_context)
                    st.rerun()
        
        # Text input for questions
        with st.form("simple_chat_form", clear_on_submit=True):
            user_question = st.text_area(
                "Your question:",
                placeholder="Ask about zoning, setbacks, lot requirements, permitted uses, or any Oakville real estate topic...",
                height=80,
                key="simple_chat_input"
            )
            
            col1, col2 = st.columns([3, 1])
            with col1:
                submitted = st.form_submit_button("💬 Ask Question", type="primary", use_container_width=True)
            with col2:
                if st.form_submit_button("🗑️ Clear Chat", use_container_width=True):
                    chatbot.clear_history()
                    st.rerun()
        
        if submitted and user_question.strip():
            with st.spinner("🤔 AI is thinking..."):
                start_time = time.time()
                answer = chatbot.answer_question(user_question, property_context)
                processing_time = time.time() - start_time
            
            # Show processing time
            st.success(f"✅ Answered in {processing_time:.1f} seconds")
            st.rerun()
        
        # Show stats
        if history:
            with st.expander("📊 Chat Statistics", expanded=False):
                user_msgs = len([m for m in history if m.role == "user"])
                assistant_msgs = len([m for m in history if m.role == "assistant"])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Messages", len(history))
                with col2:
                    st.metric("Questions Asked", user_msgs)
                with col3:
                    st.metric("Responses Given", assistant_msgs)
        
    except Exception as e:
        st.error(f"❌ AI Assistant Error: {str(e)}")
        st.info("💡 Please ensure the GROQ API key is configured correctly.")

def get_simple_chatbot():
    """Get simple chatbot instance"""
    api_key = os.getenv("GROQ_API_KEY", "your-groq-api-key-here")
    
    if "simple_chatbot" not in st.session_state:
        st.session_state.simple_chatbot = SimpleOakvilleChatbot(api_key)
    
    return st.session_state.simple_chatbot

if __name__ == "__main__":
    # Test the simple chatbot
    st.set_page_config(page_title="Simple AI Assistant", layout="wide")
    render_simple_chatbot_interface()