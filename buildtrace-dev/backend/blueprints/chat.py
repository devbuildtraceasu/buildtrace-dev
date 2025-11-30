#!/usr/bin/env python3
"""
Chatbot API Endpoints

Provides chatbot functionality with session and drawing context support.
"""

import logging
import uuid
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session as DBSession

from config import config
from gcp.database import get_db_session
from gcp.database.models import ChatConversation, ChatMessage, Session, AnalysisResult, Comparison
from services.chatbot_service import ChatbotService
from services.context_retriever import ContextRetriever
from services.session_service import SessionService
from utils.auth_helpers import get_current_user_id, require_auth

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__, url_prefix='/api/v1/chat')

# Initialize services
chatbot_service = ChatbotService()
context_retriever = ContextRetriever()


@chat_bp.route('/sessions/<session_id>', methods=['POST'])
@require_auth
def send_chat_message(session_id: str):
    """
    Send a chat message with session context
    
    Request body:
        - message: User message text
        - conversation_id: Optional conversation ID (for continuing existing conversation)
    
    Returns:
        - response: Assistant response
        - conversation_id: Conversation ID
        - context_used: Whether drawing context was used
    """
    try:
        user_id = get_current_user_id()
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400
        
        user_message = data.get('message', '').strip()
        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        with get_db_session() as db:
            # Verify session exists
            session_service = SessionService(db)
            session = session_service.get_session(session_id)
            
            if not session:
                return jsonify({'error': 'Session not found'}), 404
            
            # Get or create conversation
            conversation = session_service.get_or_create_chat_conversation(session_id)
            
            # Get conversation history
            previous_messages = db.query(ChatMessage).filter(
                ChatMessage.conversation_id == conversation.id
            ).order_by(ChatMessage.timestamp.asc()).all()
            
            conversation_history = [
                {
                    'role': msg.role,
                    'content': msg.content
                }
                for msg in previous_messages
            ]
            
            # Get session context (drawing changes, analyses)
            session_context = _get_session_context(session_id, db)
            
            # Send message to chatbot
            response_data = chatbot_service.send_message(
                user_message=user_message,
                drawing_version_id=None,  # Session-based, not drawing-version-based
                drawing_version_ids=None,
                conversation_history=conversation_history,
                session_context=session_context  # Pass session context
            )
            
            # Save user message
            user_msg = ChatMessage(
                id=str(uuid.uuid4()),
                conversation_id=conversation.id,
                role='user',
                content=user_message,
                message_metadata={
                    'session_id': session_id
                }
            )
            db.add(user_msg)
            
            # Save assistant response
            assistant_msg = ChatMessage(
                id=str(uuid.uuid4()),
                conversation_id=conversation.id,
                role='assistant',
                content=response_data.get('response', ''),
                message_metadata={
                    'session_id': session_id,
                    'context_used': response_data.get('context_used', False),
                    'tokens_used': response_data.get('tokens_used'),
                    'model': response_data.get('model')
                }
            )
            db.add(assistant_msg)
            db.commit()
            
            return jsonify({
                'response': response_data.get('response', ''),
                'conversation_id': conversation.id,
                'context_used': response_data.get('context_used', False),
                'tokens_used': response_data.get('tokens_used'),
                'model': response_data.get('model')
            }), 200
    
    except Exception as e:
        logger.error(f"Error sending chat message: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/sessions/<session_id>/suggested', methods=['GET'])
def get_suggested_questions(session_id: str):
    """
    Get suggested questions based on session context
    
    Returns:
        - questions: List of suggested questions
    """
    try:
        with get_db_session() as db:
            session_service = SessionService(db)
            session = session_service.get_session(session_id)
            
            if not session:
                return jsonify({'error': 'Session not found'}), 404
            
            # Get session context to generate relevant suggestions
            analyses = session_service.get_session_analyses(session_id)
            
            # Generate suggested questions based on context
            suggestions = []
            
            if analyses:
                suggestions.extend([
                    "What are the most critical changes in these drawings?",
                    "What are the cost implications of these changes?",
                    "How long should these changes take to implement?",
                    "What permits might be required for these changes?"
                ])
            else:
                suggestions.extend([
                    "What changes were detected in these drawings?",
                    "What should I know about these drawing comparisons?",
                    "Are there any critical issues I should be aware of?"
                ])
            
            return jsonify({
                'session_id': session_id,
                'suggestions': suggestions
            }), 200
    
    except Exception as e:
        logger.error(f"Error getting suggested questions: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/sessions/<session_id>/history', methods=['GET'])
@require_auth
def get_chat_history(session_id: str):
    """
    Get chat history for a session
    
    Returns:
        - messages: List of chat messages
        - conversation_id: Conversation ID
    """
    try:
        with get_db_session() as db:
            session_service = SessionService(db)
            session = session_service.get_session(session_id)
            
            if not session:
                return jsonify({'error': 'Session not found'}), 404
            
            conversation = session_service.get_or_create_chat_conversation(session_id)
            
            messages = db.query(ChatMessage).filter(
                ChatMessage.conversation_id == conversation.id
            ).order_by(ChatMessage.timestamp.asc()).all()
            
            return jsonify({
                'session_id': session_id,
                'conversation_id': conversation.id,
                'messages': [
                    {
                        'id': msg.id,
                        'role': msg.role,
                        'content': msg.content,
                        'timestamp': msg.timestamp.isoformat() if msg.timestamp else None
                    }
                    for msg in messages
                ]
            }), 200
    
    except Exception as e:
        logger.error(f"Error getting chat history: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/sessions/<session_id>/debug-context', methods=['GET'])
@require_auth
def debug_chat_context(session_id: str):
    """
    Debug endpoint to see what context is available for the chatbot
    
    Returns:
        - context: Available context information
    """
    try:
        with get_db_session() as db:
            session_service = SessionService(db)
            session = session_service.get_session(session_id)
            
            if not session:
                return jsonify({'error': 'Session not found'}), 404
            
            # Get all context data
            comparisons = session_service.get_session_comparisons(session_id)
            analyses = session_service.get_session_analyses(session_id)
            
            context_summary = {
                'session_id': session_id,
                'session_status': session.status,
                'comparisons_count': len(comparisons),
                'analyses_count': len(analyses),
                'drawing_names': list(set([c.drawing_name for c in comparisons if c.drawing_name])),
                'has_critical_changes': any(a.critical_change for a in analyses),
                'total_changes': sum(
                    len(a.changes_found) if isinstance(a.changes_found, list) else (1 if a.changes_found else 0)
                    for a in analyses
                )
            }
            
            return jsonify({
                'context_summary': context_summary,
                'comparisons': [
                    {
                        'drawing_name': c.drawing_name,
                        'changes_detected': c.changes_detected,
                        'alignment_score': c.alignment_score
                    }
                    for c in comparisons[:10]  # Limit to first 10
                ],
                'analyses': [
                    {
                        'drawing_name': a.drawing_name,
                        'has_critical_change': a.critical_change is not None,
                        'changes_count': len(a.changes_found) if isinstance(a.changes_found, list) else (1 if a.changes_found else 0)
                    }
                    for a in analyses[:10]  # Limit to first 10
                ]
            }), 200
    
    except Exception as e:
        logger.error(f"Error getting debug context: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def _get_session_context(session_id: str, db: DBSession) -> str:
    """
    Get formatted context string from session data
    
    Args:
        session_id: Session ID
        db: Database session
    
    Returns:
        Formatted context string for chatbot
    """
    try:
        session_service = SessionService(db)
        analyses = session_service.get_session_analyses(session_id)
        comparisons = session_service.get_session_comparisons(session_id)
        
        context_parts = []
        
        if comparisons:
            context_parts.append(f"Found {len(comparisons)} drawing comparisons:")
            for comp in comparisons[:5]:  # Limit to first 5
                context_parts.append(f"  - {comp.drawing_name}: {'Changes detected' if comp.changes_detected else 'No changes'}")
        
        if analyses:
            context_parts.append(f"\nAnalysis results:")
            for analysis in analyses[:5]:  # Limit to first 5
                if analysis.critical_change:
                    context_parts.append(f"  - {analysis.drawing_name}: CRITICAL - {analysis.critical_change[:100]}")
                elif analysis.changes_found:
                    changes = analysis.changes_found if isinstance(analysis.changes_found, list) else [analysis.changes_found]
                    context_parts.append(f"  - {analysis.drawing_name}: {len(changes)} changes detected")
        
        return "\n".join(context_parts) if context_parts else "No context available for this session."
    
    except Exception as e:
        logger.error(f"Error getting session context: {e}", exc_info=True)
        return "Error retrieving session context."

