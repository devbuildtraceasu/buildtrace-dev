"""
Authentication helper functions for extracting user_id from JWT tokens or sessions
"""
from flask import request, session
from typing import Optional
from utils.jwt_utils import get_user_from_token
import logging

logger = logging.getLogger(__name__)


def get_current_user_id() -> Optional[str]:
    """
    Get current user ID from either JWT token (Authorization header) or session cookie.
    Returns None if not authenticated.
    
    This function supports both authentication methods:
    1. JWT token in Authorization header (for cross-domain Cloud Run)
    2. Session cookie (for same-domain requests)
    """
    user_id = None
    
    # Try JWT token first (for cross-domain authentication)
    auth_header = request.headers.get('Authorization')
    token = None
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header[7:]
    elif request.args.get('token'):
        token = request.args.get('token')
    
    if token:
        jwt_user = get_user_from_token(token)
        if jwt_user:
            user_id = jwt_user.get('user_id')
            logger.debug("Authenticated via JWT token", extra={'user_id': user_id})
    
    # Fallback to session cookie (for same-domain requests)
    if not user_id:
        user_id = session.get('user_id')
        if user_id:
            logger.debug("Authenticated via session cookie", extra={'user_id': user_id})
    
    return user_id


def require_auth():
    """
    Decorator or helper to require authentication.
    Returns (user_id, error_response) tuple.
    If authenticated: (user_id, None)
    If not authenticated: (None, (json_response, status_code))
    """
    user_id = get_current_user_id()
    if not user_id:
        from flask import jsonify
        return None, (jsonify({'error': 'Not authenticated'}), 401)
    return user_id, None

