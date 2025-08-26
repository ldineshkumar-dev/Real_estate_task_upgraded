"""
AI Chatbot for Oakville Real Estate Analyzer
GROQ LLM with RAG (Retrieval-Augmented Generation) Integration
"""

import os
import time
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

import streamlit as st
from groq import Groq

from rag_system import RAGSystem
from knowledge_base import OakvilleKnowledgeBase

logger = logging.getLogger(__name__)

@dataclass
class ChatMessage:
    """Represents a chat message"""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime
    context_used: List[str] = None
    sources: List[str] = None

@dataclass
class ChatResponse:
    """Represents a chatbot response with metadata"""
    content: str
    sources: List[str]
    context_chunks: List[str]
    confidence: float
    processing_time: float
    tokens_used: int

class OakvilleAIChatbot:
    """AI-powered chatbot for Oakville real estate analysis using GROQ LLM with RAG"""
    
    def __init__(self, groq_api_key: str):
        """Initialize the AI chatbot with GROQ and RAG systems"""
        if not groq_api_key:
            raise ValueError("GROQ API key is required")
            
        self.groq_client = Groq(api_key=groq_api_key)
        self.rag_system = RAGSystem()
        self.knowledge_base = OakvilleKnowledgeBase()
        
        # Load knowledge base into RAG system
        self._initialize_knowledge_base()
        
        # Chat configuration
        self.model = "mixtral-8x7b-32768"  # Primary model
        self.fallback_model = "llama2-70b-4096"  # Fallback if primary fails
        
        self.max_tokens = 1024
        self.temperature = 0.1  # Low temperature for factual responses
        self.top_p = 0.9
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum seconds between requests
        
        # Conversation history
        self.conversation_history: List[ChatMessage] = []
        self.max_history_length = 20
        
        # Context window management
        self.max_context_length = 16000  # Characters
        
        logger.info("OakvilleAIChatbot initialized successfully")
    
    def _initialize_knowledge_base(self):
        """Initialize the knowledge base with Oakville zoning data"""
        try:
            # Load comprehensive zoning data
            zoning_data = self.knowledge_base.load_comprehensive_data()
            
            # Add to RAG system
            documents = []
            
            # Process zoning regulations
            for zone_code, zone_data in zoning_data.get('residential_zones', {}).items():
                doc_text = self._format_zone_document(zone_code, zone_data)
                documents.append({
                    'id': f"zone_{zone_code}",
                    'content': doc_text,
                    'metadata': {
                        'type': 'zoning_regulation',
                        'zone_code': zone_code,
                        'category': zone_data.get('category', 'residential')
                    }
                })
            
            # Process special provisions
            suffix_zones = zoning_data.get('suffix_zone_regulations', {})
            for suffix, suffix_data in suffix_zones.items():
                doc_text = self._format_suffix_document(suffix, suffix_data)
                documents.append({
                    'id': f"suffix_{suffix}",
                    'content': doc_text,
                    'metadata': {
                        'type': 'suffix_zone',
                        'suffix': suffix,
                        'category': 'special_regulation'
                    }
                })
            
            # Process general regulations
            general_regs = [
                'accessory_buildings_structures',
                'reduced_front_yard',
                'day_care_regulations',
                'parking_structures'
            ]
            
            for reg_type in general_regs:
                if reg_type in zoning_data:
                    doc_text = self._format_general_regulation(reg_type, zoning_data[reg_type])
                    documents.append({
                        'id': f"regulation_{reg_type}",
                        'content': doc_text,
                        'metadata': {
                            'type': 'general_regulation',
                            'regulation_type': reg_type,
                            'category': 'general'
                        }
                    })
            
            # Add FAQ and common questions
            faq_data = self.knowledge_base.load_faq_data()
            for i, qa_pair in enumerate(faq_data):
                doc_text = f"Question: {qa_pair['question']}\nAnswer: {qa_pair['answer']}"
                documents.append({
                    'id': f"faq_{i}",
                    'content': doc_text,
                    'metadata': {
                        'type': 'faq',
                        'category': qa_pair.get('category', 'general'),
                        'question': qa_pair['question']
                    }
                })
            
            # Add all documents to RAG system
            self.rag_system.add_documents(documents)
            
            logger.info(f"Knowledge base initialized with {len(documents)} documents")
            
        except Exception as e:
            logger.error(f"Failed to initialize knowledge base: {e}")
            raise
    
    def _format_zone_document(self, zone_code: str, zone_data: Dict) -> str:
        """Format zone data into searchable document text"""
        doc_parts = [
            f"Zone Code: {zone_code}",
            f"Zone Name: {zone_data.get('name', 'Unknown')}",
            f"Category: {zone_data.get('category', 'Residential')}",
            f"Table Reference: {zone_data.get('table_reference', 'Unknown')}",
            ""
        ]
        
        # Add dimensional requirements
        if 'min_lot_area' in zone_data:
            doc_parts.append(f"Minimum lot area: {zone_data['min_lot_area']} square meters")
        if 'min_lot_frontage' in zone_data:
            doc_parts.append(f"Minimum lot frontage: {zone_data['min_lot_frontage']} meters")
        
        # Add setbacks
        setbacks = zone_data.get('setbacks', {})
        if setbacks:
            doc_parts.append("\nSetback requirements:")
            for setback_type, value in setbacks.items():
                if isinstance(value, (int, float)):
                    doc_parts.append(f"- {setback_type.replace('_', ' ').title()}: {value} meters")
        
        # Add height and storey limits
        if 'max_height' in zone_data:
            doc_parts.append(f"Maximum building height: {zone_data['max_height']} meters")
        if 'max_storeys' in zone_data:
            doc_parts.append(f"Maximum storeys: {zone_data['max_storeys']}")
        
        # Add lot coverage
        if 'max_lot_coverage' in zone_data:
            coverage = zone_data['max_lot_coverage']
            if isinstance(coverage, float):
                doc_parts.append(f"Maximum lot coverage: {coverage:.0%}")
            else:
                doc_parts.append(f"Maximum lot coverage: {coverage}")
        
        # Add permitted uses
        permitted_uses = zone_data.get('permitted_uses', [])
        if permitted_uses:
            doc_parts.append("\nPermitted uses:")
            for use in permitted_uses:
                formatted_use = use.replace('_', ' ').title()
                doc_parts.append(f"- {formatted_use}")
        
        # Add use restrictions
        restrictions = zone_data.get('use_restrictions', {})
        if restrictions:
            doc_parts.append("\nUse restrictions:")
            for restriction_type, value in restrictions.items():
                doc_parts.append(f"- {restriction_type.replace('_', ' ').title()}: {value}")
        
        # Add special provisions
        if 'corner_lot_adjustments' in zone_data:
            doc_parts.append("\nCorner lot special provisions apply")
        
        if 'garage_adjustments' in zone_data:
            doc_parts.append("\nGarage setback adjustments available")
        
        return "\n".join(doc_parts)
    
    def _format_suffix_document(self, suffix: str, suffix_data: Dict) -> str:
        """Format suffix zone data into searchable document text"""
        doc_parts = [
            f"Suffix Zone: {suffix}",
            f"Name: {suffix_data.get('name', 'Unknown')}",
            f"Description: {suffix_data.get('description', '')}",
            ""
        ]
        
        # Add specific regulations for suffix zones
        if suffix == "-0":
            doc_parts.extend([
                "The -0 Suffix Zone provides enhanced restrictions:",
                "- Maximum 2 storeys permitted",
                "- Maximum 9.0 meters height",
                "- Floor area prohibited above second storey",
                "- Balconies and decks prohibited above first storey",
                "- Specific FAR limits based on lot size",
                "- Enhanced lot coverage restrictions"
            ])
            
            # Add FAR table
            far_table = suffix_data.get('residential_floor_area_ratio', {}).get('far_table', {})
            if far_table:
                doc_parts.append("\nFloor Area Ratio limits:")
                for lot_range, far_value in far_table.items():
                    doc_parts.append(f"- {lot_range}: {far_value:.0%} FAR")
        
        return "\n".join(doc_parts)
    
    def _format_general_regulation(self, reg_type: str, reg_data: Dict) -> str:
        """Format general regulation data into searchable document text"""
        doc_parts = [
            f"Regulation Type: {reg_type.replace('_', ' ').title()}",
            f"Reference Section: {reg_data.get('reference_section', 'Unknown')}",
            ""
        ]
        
        # Add specific content based on regulation type
        if reg_type == "accessory_buildings_structures":
            doc_parts.extend([
                "Accessory buildings and structures regulations:",
                f"- Maximum height: {reg_data.get('regulations', {}).get('max_height', 4.0)} meters",
                f"- Minimum setback from lot lines: {reg_data.get('regulations', {}).get('minimum_yard_flankage_rear', {}).get('distance', 0.6)} meters",
                f"- Maximum lot coverage: {reg_data.get('regulations', {}).get('max_lot_coverage', 'greater of 5% or 42 sq.m')}",
                "- Must be on same lot as primary use",
                "- No human habitation or occupation for gain permitted"
            ])
        
        elif reg_type == "day_care_regulations":
            doc_parts.extend([
                "Day care facility regulations:",
                "- Must be on lot where front or flankage line abuts arterial or major collector road",
                f"- Minimum interior side yard: {reg_data.get('min_interior_side_yard', 4.2)} meters",
                f"- Maximum driveway width: {reg_data.get('driveway_max_width', 6.0)} meters",
                "- Special playground equipment setback requirements apply"
            ])
        
        return "\n".join(doc_parts)
    
    def _rate_limit_check(self):
        """Check and enforce rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _truncate_context(self, context_chunks: List[str], max_length: int) -> List[str]:
        """Truncate context to fit within max length"""
        current_length = 0
        truncated_chunks = []
        
        for chunk in context_chunks:
            if current_length + len(chunk) <= max_length:
                truncated_chunks.append(chunk)
                current_length += len(chunk)
            else:
                # Try to fit partial chunk
                remaining_space = max_length - current_length
                if remaining_space > 100:  # Only if we have meaningful space
                    truncated_chunks.append(chunk[:remaining_space] + "...")
                break
        
        return truncated_chunks
    
    def _build_system_prompt(self, context_chunks: List[str], user_query: str, property_context: Dict = None) -> str:
        """Build comprehensive system prompt with context"""
        
        # Truncate context if needed
        context_chunks = self._truncate_context(context_chunks, self.max_context_length)
        
        system_prompt = """You are an expert AI assistant specializing in Oakville, Ontario real estate and zoning regulations. You have comprehensive knowledge of the Town of Oakville Zoning By-law 2014-014 and can provide detailed, accurate information about:

- Zoning classifications (RL1-RL11, RUC, RM1-RM4, RH)
- Setback requirements and dimensional regulations
- Permitted uses and restrictions
- Special provisions and suffix zones (-0 designations)
- Development potential and FAR calculations
- Property valuation factors
- Municipal processes and requirements

IMPORTANT GUIDELINES:
1. Always base your answers on the provided context from the official zoning by-law
2. If asked about specific measurements or requirements, provide exact values from the by-law
3. When discussing zones, always mention both the base zone and any suffix/special provisions
4. For complex calculations, show your work step-by-step
5. If information is not available in the context, clearly state this limitation
6. Always recommend consulting with Town planning staff for official interpretations
7. Use clear, professional language suitable for property owners, developers, and real estate professionals

CONTEXT FROM ZONING BY-LAW:
"""
        
        # Add context chunks
        for i, chunk in enumerate(context_chunks, 1):
            system_prompt += f"\n--- Context {i} ---\n{chunk}\n"
        
        # Add property-specific context if available
        if property_context:
            system_prompt += f"\nCURRENT PROPERTY CONTEXT:\n"
            system_prompt += f"Address: {property_context.get('address', 'Not specified')}\n"
            system_prompt += f"Zone: {property_context.get('zone_code', 'Not specified')}\n"
            system_prompt += f"Lot Area: {property_context.get('lot_area', 'Not specified')} m²\n"
            system_prompt += f"Lot Frontage: {property_context.get('lot_frontage', 'Not specified')} m\n"
            
            if property_context.get('special_provision'):
                system_prompt += f"Special Provision: {property_context['special_provision']}\n"
        
        system_prompt += f"\nUSER QUESTION: {user_query}\n\nProvide a comprehensive, accurate answer based on the context provided. Include relevant section references and be specific about requirements."
        
        return system_prompt
    
    def answer_question(self, question: str, property_context: Dict = None) -> ChatResponse:
        """Answer a question using RAG-enhanced GROQ LLM"""
        start_time = time.time()
        
        try:
            # Rate limiting
            self._rate_limit_check()
            
            # Retrieve relevant context using RAG
            logger.info(f"Retrieving context for question: {question[:100]}...")
            context_results = self.rag_system.retrieve(question, top_k=5)
            
            context_chunks = [result['content'] for result in context_results]
            sources = [f"{result['metadata'].get('type', 'unknown')}:{result['metadata'].get('zone_code', result['id'])}" 
                      for result in context_results]
            
            # Build system prompt
            system_prompt = self._build_system_prompt(context_chunks, question, property_context)
            
            # Prepare messages for GROQ
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ]
            
            # Add recent conversation history for context
            history_context = self._get_conversation_context()
            if history_context:
                messages.insert(1, {"role": "assistant", "content": f"Previous conversation context: {history_context}"})
            
            logger.info(f"Sending request to GROQ model: {self.model}")
            
            # Make request to GROQ
            try:
                response = self.groq_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    stream=False
                )
            except Exception as e:
                logger.warning(f"Primary model {self.model} failed: {e}")
                logger.info(f"Trying fallback model: {self.fallback_model}")
                
                response = self.groq_client.chat.completions.create(
                    model=self.fallback_model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    stream=False
                )
            
            # Extract response
            answer_content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 0
            
            processing_time = time.time() - start_time
            
            # Calculate confidence based on context relevance
            confidence = self._calculate_confidence(context_results, question)
            
            # Store in conversation history
            user_message = ChatMessage(
                role="user",
                content=question,
                timestamp=datetime.now()
            )
            assistant_message = ChatMessage(
                role="assistant", 
                content=answer_content,
                timestamp=datetime.now(),
                context_used=context_chunks[:3],  # Store top 3 contexts
                sources=sources
            )
            
            self._add_to_history([user_message, assistant_message])
            
            logger.info(f"Successfully answered question in {processing_time:.2f}s using {tokens_used} tokens")
            
            return ChatResponse(
                content=answer_content,
                sources=sources,
                context_chunks=context_chunks,
                confidence=confidence,
                processing_time=processing_time,
                tokens_used=tokens_used
            )
            
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            
            # Provide fallback response
            fallback_content = f"I apologize, but I encountered an error processing your question about Oakville zoning: {str(e)}\n\nFor accurate information, please consult the Town of Oakville Zoning By-law 2014-014 directly or contact Planning Services at 905-845-6601."
            
            return ChatResponse(
                content=fallback_content,
                sources=[],
                context_chunks=[],
                confidence=0.0,
                processing_time=time.time() - start_time,
                tokens_used=0
            )
    
    def _calculate_confidence(self, context_results: List[Dict], question: str) -> float:
        """Calculate confidence score based on context relevance"""
        if not context_results:
            return 0.0
        
        # Average the similarity scores
        scores = [result.get('score', 0.5) for result in context_results]
        avg_score = sum(scores) / len(scores)
        
        # Boost confidence if we have exact matches for zone codes
        question_lower = question.lower()
        zone_patterns = ['rl1', 'rl2', 'rl3', 'rl4', 'rl5', 'rl6', 'rl7', 'rl8', 'rl9', 'rl10', 'rl11', 'ruc', 'rm1', 'rm2', 'rm3', 'rm4', 'rh']
        
        for pattern in zone_patterns:
            if pattern in question_lower:
                # Check if we have specific context for this zone
                for result in context_results:
                    if pattern.upper() in result.get('metadata', {}).get('zone_code', ''):
                        avg_score *= 1.2  # 20% confidence boost
                        break
        
        return min(avg_score, 1.0)  # Cap at 1.0
    
    def _get_conversation_context(self, max_messages: int = 4) -> str:
        """Get recent conversation context"""
        if len(self.conversation_history) < 2:
            return ""
        
        recent_messages = self.conversation_history[-max_messages:]
        context_parts = []
        
        for msg in recent_messages:
            if msg.role in ["user", "assistant"]:
                content_preview = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                context_parts.append(f"{msg.role}: {content_preview}")
        
        return "\n".join(context_parts)
    
    def _add_to_history(self, messages: List[ChatMessage]):
        """Add messages to conversation history with length management"""
        self.conversation_history.extend(messages)
        
        # Trim history if too long
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[-self.max_history_length:]
    
    def clear_conversation_history(self):
        """Clear the conversation history"""
        self.conversation_history.clear()
        logger.info("Conversation history cleared")
    
    def get_conversation_history(self) -> List[ChatMessage]:
        """Get the current conversation history"""
        return self.conversation_history.copy()
    
    def export_conversation(self, format: str = "json") -> str:
        """Export conversation history in specified format"""
        if format.lower() == "json":
            return json.dumps([
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "sources": msg.sources if msg.sources else []
                }
                for msg in self.conversation_history
            ], indent=2)
        elif format.lower() == "text":
            lines = []
            for msg in self.conversation_history:
                lines.append(f"[{msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {msg.role.upper()}: {msg.content}")
                if msg.sources:
                    lines.append(f"   Sources: {', '.join(msg.sources)}")
                lines.append("")
            return "\n".join(lines)
        else:
            raise ValueError("Format must be 'json' or 'text'")
    
    def get_chat_statistics(self) -> Dict:
        """Get chat session statistics"""
        total_messages = len(self.conversation_history)
        user_messages = len([msg for msg in self.conversation_history if msg.role == "user"])
        assistant_messages = len([msg for msg in self.conversation_history if msg.role == "assistant"])
        
        return {
            "total_messages": total_messages,
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "session_duration": (datetime.now() - self.conversation_history[0].timestamp).total_seconds() / 60 if self.conversation_history else 0,
            "knowledge_base_size": self.rag_system.get_document_count(),
            "last_activity": self.conversation_history[-1].timestamp.isoformat() if self.conversation_history else None
        }


def get_ai_chatbot(api_key: str = None) -> OakvilleAIChatbot:
    """Factory function to create and cache AI chatbot instance"""
    if api_key is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            # Use environment variable for API key
            api_key = os.getenv("GROQ_API_KEY", "your-groq-api-key-here")
    
    if "ai_chatbot" not in st.session_state:
        st.session_state.ai_chatbot = OakvilleAIChatbot(api_key)
    
    return st.session_state.ai_chatbot