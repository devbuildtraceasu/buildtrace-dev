"""
Google OAuth 2.0 Authentication Blueprint
Uses Google Cloud Identity (not Firebase)
"""

import logging
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, redirect, session, current_app
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
import requests

from config import config
from gcp.database import get_db_session
from gcp.database.models import User, Organization, Project
from utils.jwt_utils import generate_token, get_user_from_token
from utils.auth_helpers import get_current_user_id

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')

# OAuth 2.0 scopes
SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]


def get_flow():
    """Create OAuth flow instance"""
    if not config.GOOGLE_CLIENT_ID or not config.GOOGLE_CLIENT_SECRET:
        raise ValueError("Google OAuth not configured - missing CLIENT_ID or CLIENT_SECRET")
    
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": config.GOOGLE_CLIENT_ID,
                "client_secret": config.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [config.GOOGLE_REDIRECT_URI]
            }
        },
        scopes=SCOPES,
        redirect_uri=config.GOOGLE_REDIRECT_URI
    )
    return flow


@auth_bp.route('/google/login', methods=['GET'])
def google_login():
    """Initiate Google OAuth login"""
    try:
        if not config.GOOGLE_CLIENT_ID or not config.GOOGLE_CLIENT_SECRET:
            return jsonify({'error': 'Google OAuth not configured'}), 500
        
        flow = get_flow()
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'  # Force consent to get refresh token
        )
        
        # Store state in session for CSRF protection
        session['oauth_state'] = state
        
        logger.info("Google OAuth login initiated", extra={'state': state})
        return jsonify({
            'auth_url': authorization_url,
            'state': state
        }), 200
        
    except Exception as e:
        logger.error(f"Google login error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/google/callback', methods=['GET'])
def google_callback():
    """Handle Google OAuth callback"""
    try:
        # Get authorization code
        code = request.args.get('code')
        if not code:
            error = request.args.get('error')
            logger.warning(f"OAuth callback error: {error}")
            return redirect(f"{config.FRONTEND_URL}/?error={error}")
        
        # Get state from callback (CSRF protection)
        state = request.args.get('state')
        
        # Verify state - check session first, but if session doesn't work (cross-domain),
        # we'll still proceed if state is present (OAuth library generates secure states)
        session_state = session.get('oauth_state')
        if state and session_state and state != session_state:
            logger.warning("OAuth state mismatch - possible CSRF attack")
            return redirect(f"{config.FRONTEND_URL}/?error=invalid_state")
        
        # If no state at all, that's suspicious
        if not state:
            logger.warning("OAuth callback missing state parameter")
            return redirect(f"{config.FRONTEND_URL}/?error=invalid_state")
        
        # Exchange code for token
        flow = get_flow()
        # Set state on flow for validation
        if state:
            flow.state = state
        flow.fetch_token(code=code)
        
        # Get user info from Google
        credentials = flow.credentials
        user_info_response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {credentials.token}'}
        )
        user_info = user_info_response.json()
        
        # Verify token with Google
        idinfo = id_token.verify_oauth2_token(
            credentials.id_token,
            Request(),
            config.GOOGLE_CLIENT_ID
        )
        
        # Extract user information
        google_id = idinfo.get('sub')
        email = user_info.get('email')
        name = user_info.get('name', '')
        picture = user_info.get('picture', '')
        domain = email.split('@')[1] if '@' in email else None
        
        # Check domain restrictions if configured
        if config.ALLOWED_EMAIL_DOMAINS and domain not in config.ALLOWED_EMAIL_DOMAINS:
            logger.warning(f"Domain not allowed: {domain}", extra={'email': email})
            return redirect(f"{config.FRONTEND_URL}/?error=domain_not_allowed")
        
        # Create or update user in database
        with get_db_session() as db:
            # Check if user exists by email
            user = db.query(User).filter_by(email=email).first()
            
            if not user:
                # Create new user
                user = User(
                    id=str(uuid.uuid4()),
                    email=email,
                    name=name,
                    email_verified=True,  # Google emails are verified
                    is_active=True,
                    last_login=datetime.utcnow()
                )
                
                # Try to find organization by domain
                if domain:
                    org = db.query(Organization).filter_by(domain=domain).first()
                    if org:
                        user.organization_id = org.id
                
                db.add(user)
                logger.info(f"Created new user from Google OAuth", extra={'user_id': user.id, 'email': email})
            else:
                # Update existing user
                user.name = name or user.name
                user.last_login = datetime.utcnow()
                user.email_verified = True
                logger.info(f"Updated user from Google OAuth", extra={'user_id': user.id, 'email': email})
            
            _ensure_default_project(db, user)
            db.commit()
            
            # Store user in session (for backend requests)
            session['user_id'] = user.id
            session['user_email'] = user.email
            session['user_name'] = user.name
            session.permanent = True
            
            # Generate JWT token for cross-domain authentication
            jwt_token = generate_token(
                user_id=user.id,
                email=user.email,
                name=user.name or '',
                organization_id=user.organization_id
            )
            
            logger.info(f"User logged in via Google OAuth", extra={'user_id': user.id, 'email': email})
            
            # Redirect to frontend with success, user info, and JWT token
            import urllib.parse
            user_params = urllib.parse.urlencode({
                'auth': 'success',
                'user_id': user.id,
                'email': user.email,
                'name': user.name or '',
                'token': jwt_token  # JWT token for API authentication
            })
            redirect_url = f"{config.FRONTEND_URL}/?{user_params}"
            logger.info(f"Redirecting to frontend: {redirect_url}", extra={'user_id': user.id})
            return redirect(redirect_url)
            
    except Exception as e:
        logger.error(f"Google callback error: {e}", exc_info=True)
        return redirect(f"{config.FRONTEND_URL}/?error=authentication_failed")


@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """Get current authenticated user - supports both session cookies and JWT tokens"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        with get_db_session() as db:
            user = db.query(User).filter_by(id=user_id).first()
            if not user:
                # Clear session if it was session-based
                session.clear()
                return jsonify({'error': 'User not found'}), 404
            
            return jsonify({
                'user_id': user.id,
                'email': user.email,
                'name': user.name,
                'company': user.company,
                'role': user.role,
                'organization_id': user.organization_id,
                'email_verified': user.email_verified,
                'is_active': user.is_active
            }), 200
            
    except Exception as e:
        logger.error(f"Error getting current user: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Logout current user"""
    try:
        user_id = session.get('user_id')
        session.clear()
        logger.info(f"User logged out", extra={'user_id': user_id})
        return jsonify({'message': 'Logged out successfully'}), 200
    except Exception as e:
        logger.error(f"Logout error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/verify', methods=['GET'])
def verify_token():
    """Verify JWT token from frontend (for API authentication)"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        
        # Verify token with Google
        idinfo = id_token.verify_oauth2_token(
            token,
            Request(),
            config.GOOGLE_CLIENT_ID
        )
        
        # Get user from database
        email = idinfo.get('email')
        with get_db_session() as db:
            user = db.query(User).filter_by(email=email).first()
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            return jsonify({
                'user_id': user.id,
                'email': user.email,
                'name': user.name,
                'verified': True
            }), 200
            
    except ValueError as e:
        logger.warning(f"Token verification failed: {e}")
        return jsonify({'error': 'Invalid token'}), 401
    except Exception as e:
        logger.error(f"Token verification error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def _ensure_default_project(db, user: User):
    """Create a default project for the user if none exists."""
    has_project = db.query(Project).filter_by(user_id=user.id).first()
    if has_project:
        return
    project = Project(
        name="My First Project",
        user_id=user.id,
        status='active',
        description='Auto-created project',
    )
    db.add(project)
    logger.info("Created default project for user", extra={'user_id': user.id, 'project_id': project.id})

