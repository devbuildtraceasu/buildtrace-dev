#!/usr/bin/env python3
"""
Chatbot API Endpoints

Provides chatbot functionality with session and drawing context support.
Synced with buildtrace-overlay- chatbot for consistent behavior.
"""

import logging
import uuid
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session as DBSession

from config import config
from gcp.database import get_db_session
from gcp.database.models import ChatConversation, ChatMessage, Session, AnalysisResult, Comparison
from services.chatbot_service import ConstructionChatBot, ChatMessage as ChatMsg, get_chatbot
from services.session_service import SessionService
from utils.auth_helpers import get_current_user_id, require_auth

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__, url_prefix='/api/v1/chat')


@chat_bp.route('/jobs/<job_id>', methods=['POST'])
@require_auth
def send_chat_message_job(job_id: str):
    """
    Send a chat message with job context (new system - uses job_id)
    
    Request body:
        - message: User message text
    
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
            from gcp.database.models import Job, ChatConversation, ChatMessage
            
            # Verify job exists
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return jsonify({'error': 'Job not found'}), 404
            
            # Get or create a session for this job (ChatConversation requires a session)
            from gcp.database.models import Session
            session = db.query(Session).filter(Session.id == job_id).first()
            
            if not session:
                # Create a session for this job
                session = Session(
                    id=job_id,
                    user_id=user_id or job.created_by,
                    project_id=job.project_id,
                    session_type='comparison',
                    status='active'
                )
                db.add(session)
                db.flush()
            
            # Get or create conversation for this session
            conversation = db.query(ChatConversation).filter(
                ChatConversation.session_id == session.id
            ).first()
            
            if not conversation:
                conversation = ChatConversation(
                    id=str(uuid.uuid4()),
                    session_id=session.id
                )
                db.add(conversation)
                db.flush()
            
            # Get conversation history
            previous_messages = db.query(ChatMessage).filter(
                ChatMessage.conversation_id == conversation.id
            ).order_by(ChatMessage.timestamp.asc()).all()
            
            # Convert to ChatMessage objects for the chatbot
            conversation_history = [
                ChatMsg(
                    role=msg.role,
                    content=msg.content,
                    timestamp=msg.timestamp,
                    session_id=job_id
                )
                for msg in previous_messages
            ]
            
            # Get chatbot instance and send message (use job_id as session_id for context)
            chatbot = get_chatbot()
            response = chatbot.chat(
                user_message=user_message,
                session_id=job_id,  # Use job_id for context retrieval
                conversation_history=conversation_history
            )
            
            # Save user message
            user_msg = ChatMessage(
                id=str(uuid.uuid4()),
                conversation_id=conversation.id,
                role='user',
                content=user_message,
                message_metadata={
                    'job_id': job_id
                }
            )
            db.add(user_msg)
            
            # Save assistant response
            assistant_msg = ChatMessage(
                id=str(uuid.uuid4()),
                conversation_id=conversation.id,
                role='assistant',
                content=response.content,
                message_metadata={
                    'job_id': job_id,
                    'context_used': True
                }
            )
            db.add(assistant_msg)
            db.commit()
            
            return jsonify({
                'response': response.content,
                'conversation_id': conversation.id,
                'context_used': True,
                'model': chatbot.model
            }), 200
    
    except ImportError as e:
        logger.error(f"Chatbot service not available: {e}")
        return jsonify({'error': 'Chatbot service not available. Please check OpenAI API key configuration.'}), 503
    except Exception as e:
        logger.error(f"Error sending chat message: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/sessions/<session_id>', methods=['POST'])
@require_auth
def send_chat_message(session_id: str):
    """
    Send a chat message with session context (legacy endpoint)
    
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
            
            # Convert to ChatMessage objects for the chatbot
            conversation_history = [
                ChatMsg(
                    role=msg.role,
                    content=msg.content,
                    timestamp=msg.timestamp,
                    session_id=session_id
                )
                for msg in previous_messages
            ]
            
            # Get chatbot instance and send message
            chatbot = get_chatbot()
            response = chatbot.chat(
                user_message=user_message,
                session_id=session_id,
                conversation_history=conversation_history
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
                content=response.content,
                message_metadata={
                    'session_id': session_id,
                    'context_used': True  # Chatbot always uses context if available
                }
            )
            db.add(assistant_msg)
            db.commit()
            
            return jsonify({
                'response': response.content,
                'conversation_id': conversation.id,
                'context_used': True,
                'model': chatbot.model
            }), 200
    
    except ImportError as e:
        logger.error(f"Chatbot service not available: {e}")
        return jsonify({'error': 'Chatbot service not available. Please check OpenAI API key configuration.'}), 503
    except Exception as e:
        logger.error(f"Error sending chat message: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/jobs/<job_id>/suggested', methods=['GET'])
def get_suggested_questions_job(job_id: str):
    """
    Get suggested questions based on job context (new system)
    
    Returns:
        - questions: List of suggested questions
    """
    try:
        # Get chatbot instance and get suggestions
        chatbot = get_chatbot()
        suggestions = chatbot.get_suggested_questions(job_id)
        
        return jsonify({
            'job_id': job_id,
            'suggestions': suggestions
        }), 200
    
    except (ImportError, ValueError):
        # Fallback suggestions if chatbot not available
        return jsonify({
            'job_id': job_id,
            'suggestions': [
                "What changes were detected in these drawings?",
                "What are the cost implications of these changes?",
                "How long should these changes take to implement?",
                "What permits might be required?",
                "Are there any safety considerations?"
            ]
        }), 200
    except Exception as e:
        logger.error(f"Error getting suggested questions: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/sessions/<session_id>/suggested', methods=['GET'])
def get_suggested_questions(session_id: str):
    """
    Get suggested questions based on session context (legacy)
    
    Returns:
        - questions: List of suggested questions
    """
    try:
        # Get chatbot instance and get suggestions
        chatbot = get_chatbot()
        suggestions = chatbot.get_suggested_questions(session_id)
        
        return jsonify({
            'session_id': session_id,
            'suggestions': suggestions
        }), 200
    
    except (ImportError, ValueError):
        # Fallback suggestions if chatbot not available
        return jsonify({
            'session_id': session_id,
            'suggestions': [
                "What changes were detected in these drawings?",
                "What are the cost implications of these changes?",
                "How long should these changes take to implement?",
                "What permits might be required?",
                "Are there any safety considerations?"
            ]
        }), 200
    except Exception as e:
        logger.error(f"Error getting suggested questions: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/jobs/<job_id>/restart', methods=['POST'])
@require_auth
def restart_chat_job(job_id: str):
    """
    Restart chat conversation for a job (clear history)
    
    Returns:
        - success: Whether restart was successful
        - conversation_id: New conversation ID
    """
    try:
        user_id = get_current_user_id()
        
        with get_db_session() as db:
            from gcp.database.models import Job, ChatConversation, ChatMessage, Session
            
            # Verify job exists
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return jsonify({'error': 'Job not found'}), 404
            
            # Get or create session
            session = db.query(Session).filter(Session.id == job_id).first()
            if not session:
                session = Session(
                    id=job_id,
                    user_id=user_id or job.created_by,
                    project_id=job.project_id,
                    session_type='comparison',
                    status='active'
                )
                db.add(session)
                db.flush()
            
            # Delete existing conversation and messages
            existing_conversation = db.query(ChatConversation).filter(
                ChatConversation.session_id == session.id
            ).first()
            
            if existing_conversation:
                # Delete all messages
                db.query(ChatMessage).filter(
                    ChatMessage.conversation_id == existing_conversation.id
                ).delete()
                # Delete conversation
                db.delete(existing_conversation)
            
            # Create new conversation
            new_conversation = ChatConversation(
                id=str(uuid.uuid4()),
                session_id=session.id
            )
            db.add(new_conversation)
            db.commit()
            
            return jsonify({
                'success': True,
                'conversation_id': new_conversation.id,
                'message': 'Chat restarted successfully'
            }), 200
    
    except Exception as e:
        logger.error(f"Error restarting chat: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/jobs/<job_id>/history', methods=['GET'])
@require_auth
def get_chat_history_job(job_id: str):
    """
    Get chat history for a job (new system)
    
    Returns:
        - messages: List of chat messages
        - conversation_id: Conversation ID
    """
    try:
        with get_db_session() as db:
            from gcp.database.models import Job, ChatConversation, ChatMessage
            
            # Verify job exists
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return jsonify({'error': 'Job not found'}), 404
            
            # Get session for this job
            from gcp.database.models import Session
            session = db.query(Session).filter(Session.id == job_id).first()
            
            if not session:
                return jsonify({
                    'job_id': job_id,
                    'conversation_id': None,
                    'messages': []
                }), 200
            
            # Get conversation for this session
            conversation = db.query(ChatConversation).filter(
                ChatConversation.session_id == session.id
            ).first()
            
            if not conversation:
                return jsonify({
                    'job_id': job_id,
                    'conversation_id': None,
                    'messages': []
                }), 200
            
            messages = db.query(ChatMessage).filter(
                ChatMessage.conversation_id == conversation.id
            ).order_by(ChatMessage.timestamp.asc()).all()
            
            return jsonify({
                'job_id': job_id,
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


@chat_bp.route('/sessions/<session_id>/history', methods=['GET'])
@require_auth
def get_chat_history(session_id: str):
    """
    Get chat history for a session (legacy)
    
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
        # Get chatbot instance to check context retrieval
        chatbot = get_chatbot()
        context = chatbot.get_session_context(session_id)
        context_formatted = chatbot.format_context_for_prompt(context)
        
        return jsonify({
            'session_id': session_id,
            'context_summary': {
                'overlays_created': context['overlays_created'],
                'analyses_completed': context['analyses_completed'],
                'drawings': context['drawings'],
                'total_changes': sum(len(c.get('changes_found', [])) for c in context['changes'])
            },
            'changes': [
                {
                    'drawing_name': c['drawing_name'],
                    'critical_change': c['critical_change'][:100] if c['critical_change'] else None,
                    'changes_count': len(c.get('changes_found', [])),
                    'has_recommendations': len(c.get('recommendations', [])) > 0
                }
                for c in context['changes'][:10]
            ],
            'formatted_context_preview': context_formatted[:1000] + '...' if len(context_formatted) > 1000 else context_formatted
        }), 200
    
    except ImportError:
        return jsonify({
            'session_id': session_id,
            'error': 'Chatbot service not available',
            'context_summary': None
        }), 503
    except Exception as e:
        logger.error(f"Error getting debug context: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# Web search endpoint removed - GPT has built-in web search capabilities
# No need for external DuckDuckGo search
