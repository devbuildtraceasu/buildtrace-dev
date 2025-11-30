"""
Simple Chatbot Service (Option 1)
Gemini wrapper with context injection from OCR results
"""

import logging
import os
from typing import Dict, List, Optional
from config import config
from services.context_retriever import ContextRetriever

logger = logging.getLogger(__name__)

# Try to import Gemini
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-generativeai not available - install with: pip install google-generativeai")


class ChatbotService:
    """Simple chatbot with context from OCR results using Gemini"""
    
    def __init__(self):
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai library not installed. Install with: pip install google-generativeai")
        
        # Initialize Gemini client
        api_key = os.getenv('GEMINI_API_KEY') or getattr(config, 'GEMINI_API_KEY', None)
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")
        
        genai.configure(api_key=api_key)
        # Use best available model - gemini-2.5-pro for quality, or gemini-2.5-flash for speed
        model_name = os.getenv('GEMINI_MODEL') or getattr(config, 'GEMINI_MODEL', 'models/gemini-2.5-pro')
        # Ensure 'models/' prefix is present
        if not model_name.startswith('models/'):
            model_name = f'models/{model_name}'
        self.model_name = model_name
        
        # Context retriever
        self.context_retriever = ContextRetriever()
        
        # System instruction for Gemini (better than system prompt)
        self.system_instruction = """You are BuildTrace AI Assistant, an expert construction project manager and technical advisor specializing in architectural drawings.

Your role:
- Analyze and interpret architectural drawings with precision
- Extract and explain keynotes, annotations, dimensions, and specifications
- Compare different drawing versions to identify changes
- Provide actionable insights for construction teams

Guidelines:
- Always reference specific details from the provided drawing context
- Cite page numbers, keynotes, and section names when available
- Be concise but thorough - provide complete answers
- If information is unclear or missing, state that explicitly
- For comparisons, highlight specific differences with examples"""
        
        # Initialize model with system instruction
        self.model = genai.GenerativeModel(
            self.model_name,
            system_instruction=self.system_instruction
        )
    
    def send_message(
        self,
        user_message: str,
        drawing_version_id: Optional[str] = None,
        drawing_version_ids: Optional[List[str]] = None,
        conversation_history: Optional[List[Dict]] = None,
        session_context: Optional[str] = None
    ) -> Dict:
        """
        Send a message to the chatbot
        
        Args:
            user_message: User's question
            drawing_version_id: Single drawing version ID for context
            drawing_version_ids: Multiple drawing version IDs for comparison context
            conversation_history: Previous messages in format [{"role": "user", "content": "..."}, ...]
            session_context: Optional session context string (for session-based queries)
        
        Returns:
            Dict with 'response', 'context_used', 'tokens_used'
        """
        # Get context if drawing(s) specified, or use session context
        context_text = ""
        
        # Use session context if provided (takes precedence for session-based queries)
        if session_context:
            context_text = session_context
        elif drawing_version_ids and len(drawing_version_ids) > 1:
            # Multiple drawings - for comparison
            try:
                contexts = self.context_retriever.get_multiple_drawings_context(drawing_version_ids)
                if contexts.get('count', 0) > 0:
                    context_text = self.context_retriever.format_multiple_context_for_prompt(contexts)
            except Exception as e:
                logger.error(f"Error retrieving multiple contexts: {e}")
        elif drawing_version_id:
            # Single drawing
            try:
                context = self.context_retriever.get_drawing_context(drawing_version_id)
                if 'error' not in context:
                    context_text = self.context_retriever.format_context_for_prompt(context)
                else:
                    logger.warning(f"Failed to get context: {context.get('error')}")
            except Exception as e:
                logger.error(f"Error retrieving context: {e}")
        
        # Use Gemini's chat API for proper multi-turn conversations
        # Build chat history
        chat_history = []
        
        # Add conversation history to chat
        if conversation_history:
            for msg in conversation_history[-20:]:  # Last 20 messages for better context
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    chat_history.append({"role": "user", "parts": [content]})
                elif role == "assistant":
                    chat_history.append({"role": "model", "parts": [content]})
        
        # Build user message with context
        user_parts = []
        
        # Add context to user message if available
        if context_text:
            if drawing_version_ids and len(drawing_version_ids) > 1:
                user_parts.append(f"""DRAWING CONTEXT (Multiple Drawings for Comparison):

{context_text}

Use this context to answer the following question. Compare the drawings and highlight specific differences.""")
            else:
                user_parts.append(f"""DRAWING CONTEXT:

{context_text}

Use this context to answer the following question. Reference specific details from the context.""")
        
        # Add current user question
        user_parts.append(f"\n\nQuestion: {user_message}")
        
        user_message_with_context = "\n".join(user_parts)
        
        # Call Gemini with chat API
        try:
            generation_config = {
                'max_output_tokens': 4000,  # Increased for detailed responses
                'temperature': 0.4,  # Lower temperature for more focused responses
            }
            
            if chat_history:
                # Multi-turn: use chat
                chat = self.model.start_chat(history=chat_history)
                response = chat.send_message(
                    user_message_with_context,
                    generation_config=generation_config
                )
            else:
                # First turn: use generate_content
                response = self.model.generate_content(
                    user_message_with_context,
                    generation_config=generation_config
                )
            
            assistant_message = response.text
            
            # Get token usage if available
            tokens_used = None
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                tokens_used = response.usage_metadata.total_token_count
            
            return {
                'response': assistant_message,
                'context_used': bool(context_text),
                'tokens_used': tokens_used,
                'model': self.model_name
            }
        
        except Exception as e:
            logger.error(f"Error calling Gemini: {e}")
            return {
                'response': f"I apologize, but I encountered an error: {str(e)}",
                'context_used': False,
                'error': str(e)
            }

