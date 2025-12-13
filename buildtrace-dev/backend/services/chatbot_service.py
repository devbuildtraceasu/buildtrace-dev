"""
ChatBot Service for BuildTrace AI

Provides an intelligent chatbot interface that can answer construction-related questions
using GPT-4, web search capabilities, and context from the user's changelist results.

Synced with buildtrace-overlay- for consistent behavior
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from config import config

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not available - chatbot will be limited")


@dataclass
class ChatMessage:
    """Represents a chat message"""
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: datetime
    session_id: Optional[str] = None


@dataclass
class WebSearchResult:
    """Represents a web search result"""
    title: str
    url: str
    snippet: str
    relevance_score: float = 0.0


class ConstructionChatBot:
    """
    Intelligent chatbot for construction-related queries with context awareness
    Synced with buildtrace-overlay-
    """

    def __init__(self, api_key: str = None):
        """
        Initialize the chatbot

        Args:
            api_key: OpenAI API key (if None, loads from environment or config)
        """
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI library not installed. Install with: pip install openai")
        
        # Get API key from parameter, environment, or config
        self.api_key = api_key or os.getenv('OPENAI_API_KEY') or getattr(config, 'OPENAI_API_KEY', None)
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
        
        self.client = OpenAI(api_key=self.api_key)
        # Use GPT-4o which has built-in web search capabilities
        self.model = os.getenv('OPENAI_MODEL') or getattr(config, 'OPENAI_MODEL', 'gpt-4o')

        # System prompt - synced with buildtrace-overlay-
        self.system_prompt = """You are BuildTrace AI Assistant, an expert construction project manager and technical advisor with deep knowledge in:

- Construction scheduling and project management
- Cost estimation and budget planning
- Building codes and regulations
- Material specifications and procurement
- Quality control and safety protocols
- Change order management
- Risk assessment and mitigation
- Architectural and engineering coordination

You have access to:
1. Built-in web search capabilities - you can automatically search the web for current information when needed
2. Drawing comparison results and changelist data from the user's current session
3. Construction industry best practices and standards

When answering questions:
- Provide specific, actionable advice
- Use your built-in web search to get current information (costs, codes, regulations, standards) when needed
- Reference current industry standards and costs when relevant
- Consider the drawing changes in the user's session for context
- Suggest realistic timelines and budget impacts
- Always prioritize safety and code compliance
- Be concise but thorough in your responses
- Maintain conversation context across multiple turns

If you need current information (costs, codes, standards), use your built-in web search automatically.
If you reference the user's drawing changes, be specific about which changes you're discussing.
This is a multi-turn conversation - remember previous messages and build upon them."""

    def search_web(self, query: str, num_results: int = 5) -> List[WebSearchResult]:
        """
        Perform web search using GPT's built-in web search capabilities.
        GPT models with web browsing enabled will automatically search when needed.

        Args:
            query: Search query
            num_results: Number of results to return (not used with GPT web search)

        Returns:
            List of web search results (empty - GPT handles search internally)
        """
        # GPT-4o and newer models have built-in web search capabilities
        # We don't need to perform external searches - GPT will do it automatically
        # when the user asks questions that require current information
        logger.info(f"Web search requested for: {query} (GPT will handle this automatically)")
        return []

    def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """
        Get changelist context from a session or job.
        Supports both session_id (legacy) and job_id (new system).

        Args:
            session_id: Session ID or Job ID

        Returns:
            Dictionary with session context
        """
        context = {
            'overlays_created': 0,
            'analyses_completed': 0,
            'changes': [],
            'drawings': []
        }

        try:
            # Try database mode first
            try:
                from gcp.database import get_db_session
                from gcp.database.models import Job, DiffResult, ChangeSummary
                from gcp.storage import StorageService

                storage = StorageService()

                with get_db_session() as db:
                    # Try to find job by ID first (new system)
                    job = db.query(Job).filter(Job.id == session_id).first()
                    
                    if not job:
                        # Fallback: try to find jobs by session_id (legacy)
                        jobs = db.query(Job).filter(Job.session_id == session_id).all()
                        logger.info(f"[Chatbot] Found {len(jobs)} jobs for session {session_id}")
                    else:
                        jobs = [job]
                        logger.info(f"[Chatbot] Found job {session_id}")

                    for job in jobs:
                        # Get diff results for this job
                        diff_results = db.query(DiffResult).filter(DiffResult.job_id == job.id).order_by(DiffResult.created_at.asc()).all()

                        for diff in diff_results:
                            # Get drawing name from metadata or use default
                            metadata = diff.diff_metadata or {}
                            drawing_name = metadata.get('drawing_name') or diff.drawing_name or f"Page {metadata.get('page_number', '?')}"
                            logger.info(f"[Chatbot] Processing drawing: {drawing_name}")

                            # Try to get summary for this diff
                            summary = db.query(ChangeSummary).filter(
                                ChangeSummary.diff_result_id == diff.id,
                                ChangeSummary.is_active == True
                            ).first()

                            if summary:
                                summary_json = summary.summary_json or {}
                                
                                # Extract structured changes if available
                                structured_changes = summary_json.get('changes', [])
                                changes_found = summary_json.get('changes_found', [])
                                
                                # If we have structured changes, use those; otherwise fall back to changes_found
                                if structured_changes:
                                    changes_found = [
                                        f"{c.get('title', 'Change')}: {c.get('description', '')[:200]}"
                                        for c in structured_changes
                                    ]
                                
                                change_info = {
                                    'drawing_name': drawing_name,
                                    'page_number': metadata.get('page_number'),
                                    'critical_change': summary_json.get('critical_change', {}).get('title', 'Changes detected') if isinstance(summary_json.get('critical_change'), dict) else summary_json.get('critical_change', 'Changes detected'),
                                    'changes_found': changes_found,
                                    'analysis_summary': summary.summary_text or summary_json.get('ai_summary', ''),
                                    'construction_impact': summary_json.get('construction_impact', ''),
                                    'recommendations': summary_json.get('recommendations', []),
                                    'change_count': summary_json.get('total_changes', diff.change_count or 0),
                                    'changes_detected': diff.changes_detected,
                                    'added_keynotes': summary_json.get('added_keynotes', []),
                                    'removed_keynotes': summary_json.get('removed_keynotes', []),
                                    'modified_keynotes': summary_json.get('modified_keynotes', []),
                                    'structured_changes': structured_changes
                                }

                                context['changes'].append(change_info)
                                context['drawings'].append(drawing_name)
                                context['analyses_completed'] += 1

                    context['overlays_created'] = len(context['changes'])
                    logger.info(f"[Chatbot] Context loaded - Changes: {len(context['changes'])}, Drawings: {context['drawings']}")
                    return context

            except Exception as e:
                logger.warning(f"Database context retrieval failed: {e}")

            # File-based fallback (local mode)
            session_folder = os.path.join('uploads', session_id)
            results_file = os.path.join(session_folder, 'results.json')
            
            if os.path.exists(results_file):
                with open(results_file, 'r') as f:
                    results = json.load(f)
                
                output_directories = results.get('output_directories', [])
                
                for output_dir in output_directories:
                    if not os.path.exists(output_dir) or 'overlay_results' not in output_dir:
                        continue
                    
                    for file_name in os.listdir(output_dir):
                        if file_name.startswith('change_analysis_') and file_name.endswith('.json'):
                            analysis_file = os.path.join(output_dir, file_name)
                        
                            try:
                                with open(analysis_file, 'r') as f:
                                    analysis_data = json.load(f)
                                
                                if not analysis_data.get('success', False):
                                    continue
                                
                                drawing_name = analysis_data.get('drawing_name', '')
                                if not drawing_name:
                                    drawing_name = file_name.replace('change_analysis_', '').replace('.json', '')
                                
                                # Process changes
                                changes_found = analysis_data.get('changes_found', [])
                                clean_changes = []
                                for change in changes_found:
                                    if isinstance(change, str) and len(change.strip()) > 10:
                                        clean_change = change.replace('**', '').replace('- *Impact*:', 'Impact:')
                                        clean_changes.append(clean_change)
                                
                                # Get recommendations
                                recommendations = analysis_data.get('recommendations', [])
                                if not recommendations:
                                    recommendations = [
                                        'Prioritize Structural Changes: Begin with critical structural alterations',
                                        'Coordinate with Utility Providers Early',
                                        'Cost Management: Monitor budget impacts on structural changes',
                                        'Stakeholder Communication: Keep informed about timeline changes'
                                    ]
                                
                                change_info = {
                                    'drawing_name': drawing_name,
                                    'critical_change': analysis_data.get('critical_change', ''),
                                    'changes_found': clean_changes,
                                    'analysis_summary': analysis_data.get('analysis_summary', ''),
                                    'construction_impact': '',
                                    'recommendations': recommendations
                                }
                                
                                context['changes'].append(change_info)
                                context['drawings'].append(drawing_name)
                                context['analyses_completed'] += 1
                                
                            except Exception as e:
                                logger.warning(f"Error processing analysis file {analysis_file}: {e}")
                                continue
                
                context['overlays_created'] = len(context['changes'])
            
            return context

        except Exception as e:
            logger.error(f"Error getting session context: {e}")
            return context

    def format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """
        Format session context for inclusion in the prompt

        Args:
            context: Session context dictionary

        Returns:
            Formatted context string
        """
        if not context['changes']:
            return "No drawing comparison results available in this session."

        context_text = f"Current Session Drawing Analysis:\n"
        context_text += f"- {context['overlays_created']} drawing overlays created\n"
        context_text += f"- {context['analyses_completed']} AI analyses completed\n"
        context_text += f"- Drawings analyzed: {', '.join(context['drawings'])}\n\n"

        context_text += "Detected Changes by Drawing:\n"
        for i, change in enumerate(context['changes'], 1):
            context_text += f"\n{i}. Drawing: {change['drawing_name']}"
            if change.get('page_number'):
                context_text += f" (Page {change['page_number']})"
            context_text += f"\n"
            
            # Include full summary
            if change['analysis_summary']:
                context_text += f"   AI Summary: {change['analysis_summary']}\n"
            
            # Include critical change
            if change.get('critical_change'):
                critical = change['critical_change']
                if isinstance(critical, dict):
                    context_text += f"   Critical Change: {critical.get('title', 'N/A')}\n"
                    if critical.get('reason'):
                        context_text += f"   Reason: {critical.get('reason')}\n"
                else:
                    context_text += f"   Critical Change: {critical}\n"
            
            # Include structured changes if available (preferred)
            if change.get('structured_changes'):
                context_text += f"   Detailed Changes ({len(change['structured_changes'])} total):\n"
                for chg in change['structured_changes'][:15]:  # Show up to 15 changes
                    title = chg.get('title', 'Change')
                    desc = chg.get('description', '')
                    change_type = chg.get('change_type', 'modified')
                    location = chg.get('location', '')
                    trade = chg.get('trade_affected', '')
                    context_text += f"   - [{change_type.upper()}] {title}"
                    if location:
                        context_text += f" (Location: {location})"
                    if trade:
                        context_text += f" (Trade: {trade})"
                    context_text += f"\n"
                    if desc:
                        context_text += f"     {desc[:150]}\n"
            elif change['changes_found']:
                context_text += f"   Specific Changes:\n"
                for change_detail in change['changes_found'][:15]:  # Show up to 15 changes
                    context_text += f"   - {change_detail}\n"
            
            # Include keynotes if available
            if change.get('added_keynotes'):
                context_text += f"   Added Keynotes ({len(change['added_keynotes'])}):\n"
                for kn in change['added_keynotes'][:5]:
                    context_text += f"   - Keynote {kn.get('number', '?')}: {kn.get('description', '')[:100]}\n"
            if change.get('removed_keynotes'):
                context_text += f"   Removed Keynotes ({len(change['removed_keynotes'])}):\n"
                for kn in change['removed_keynotes'][:5]:
                    context_text += f"   - Keynote {kn.get('number', '?')}: {kn.get('description', '')[:100]}\n"
            if change.get('modified_keynotes'):
                context_text += f"   Modified Keynotes ({len(change['modified_keynotes'])}):\n"
                for kn in change['modified_keynotes'][:5]:
                    context_text += f"   - Keynote {kn.get('number', '?')}: {kn.get('old_text', '')[:50]} → {kn.get('new_text', '')[:50]}\n"

            # Include construction impact if available
            if change.get('construction_impact'):
                context_text += f"   Construction Impact: {change['construction_impact']}\n"

            if change['recommendations']:
                context_text += f"   Recommendations:\n"
                for rec in change['recommendations'][:5]:  # Limit to 5 recommendations
                    context_text += f"   - {rec}\n"

        return context_text

    def chat(self, user_message: str, session_id: Optional[str] = None,
             conversation_history: List[ChatMessage] = None) -> ChatMessage:
        """
        Process a chat message and generate a response

        Args:
            user_message: User's message
            session_id: Optional session ID for context
            conversation_history: Previous messages in conversation

        Returns:
            ChatMessage with assistant's response
        """
        try:
            # Build conversation context
            messages = [{"role": "system", "content": self.system_prompt}]

            # Add session context if available - ALWAYS include on first message
            # This ensures the chatbot has full drawing comparison context even when restarting
            is_first_message = not conversation_history or len(conversation_history) == 0
            if session_id:
                context = self.get_session_context(session_id)
                context_text = self.format_context_for_prompt(context)
                if context_text and context_text.strip() != "No drawing comparison results available in this session.":
                    # Include full context on first message, or if explicitly requested
                    if is_first_message:
                        messages.append({
                            "role": "system",
                            "content": f"Drawing Comparison Context (Full Details):\n{context_text}\n\nYou have complete information about all detected changes, keynotes, and drawing modifications. Use this context to answer questions accurately."
                        })
                    else:
                        # On subsequent messages, include a brief summary
                        messages.append({
                            "role": "system",
                            "content": f"Session Context Summary:\n{context_text[:500]}..."
                        })

            # Add conversation history
            if conversation_history:
                recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
                for msg in recent_history:
                    if msg.role in ['user', 'assistant']:
                        messages.append({"role": msg.role, "content": msg.content})

            # GPT-4o has built-in web search - it will automatically search when needed
            # We don't need to manually trigger searches - GPT handles this intelligently
            # Just ensure the system prompt tells GPT it can use web search

            # Add user message
            messages.append({"role": "user", "content": user_message})

            # Generate response with GPT-4o (has built-in web search)
            # GPT will automatically use web search when it detects the need for current information
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=2000  # Use max_completion_tokens for newer models
                # temperature removed - using model default (1.0)
            )

            assistant_message = response.choices[0].message.content
            
            # Ensure we have a valid response
            if not assistant_message or not assistant_message.strip():
                logger.warning("Empty response from OpenAI API")
                assistant_message = "I apologize, but I didn't receive a valid response. Please try rephrasing your question or try again in a moment."

            return ChatMessage(
                role="assistant",
                content=assistant_message,
                timestamp=datetime.now(),
                session_id=session_id
            )

        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            error_message = f"I apologize, but I encountered an error processing your request: {str(e)}"
            return ChatMessage(
                role="assistant",
                content=error_message,
                timestamp=datetime.now(),
                session_id=session_id
            )

    def get_suggested_questions(self, session_id: Optional[str] = None) -> List[str]:
        """
        Generate suggested questions based on session context

        Args:
            session_id: Optional session ID

        Returns:
            List of suggested questions
        """
        base_questions = [
            "What are the typical costs for these types of changes?",
            "How long should this project take to complete?",
            "What permits might be required for these modifications?",
            "Are there any safety considerations I should be aware of?",
            "What's the best sequence for implementing these changes?"
        ]

        if session_id:
            context = self.get_session_context(session_id)
            if context['changes']:
                # Generate context-specific questions
                drawings = context['drawings']
                context_questions = [
                    f"What's the estimated cost impact of changes to {drawings[0] if drawings else 'these drawings'}?",
                    "How do these changes affect the project timeline?",
                    "What materials will be needed for these modifications?",
                    "Should these changes be done in phases or all at once?",
                ]
                return context_questions + base_questions[:3]

        return base_questions


# Singleton instance for use by blueprints
_chatbot_instance: Optional[ConstructionChatBot] = None


def get_chatbot() -> ConstructionChatBot:
    """Get or create chatbot instance"""
    global _chatbot_instance
    if _chatbot_instance is None:
        _chatbot_instance = ConstructionChatBot()
    return _chatbot_instance


def chat_with_context(
    message: str,
    session_id: Optional[str] = None,
    history: Optional[List[Dict]] = None
) -> Dict:
    """
    Convenience function for chatting with session context
    
    Args:
        message: User message
        session_id: Optional session ID for context
        history: Optional conversation history as list of dicts
        
    Returns:
        Dict with response content and metadata
    """
    chatbot = get_chatbot()
    
    # Convert history dicts to ChatMessage objects
    chat_history = None
    if history:
        chat_history = [
            ChatMessage(
                role=h.get('role', 'user'),
                content=h.get('content', ''),
                timestamp=datetime.fromisoformat(h['timestamp']) if h.get('timestamp') else datetime.now(),
                session_id=session_id
            )
            for h in history
        ]
    
    response = chatbot.chat(message, session_id, chat_history)
    
    return {
        'role': response.role,
        'content': response.content,
        'timestamp': response.timestamp.isoformat(),
        'session_id': response.session_id
    }


# Alias for backwards compatibility
ChatbotService = ConstructionChatBot

__all__ = ['ConstructionChatBot', 'ChatbotService', 'ChatMessage', 'WebSearchResult', 'get_chatbot', 'chat_with_context']
