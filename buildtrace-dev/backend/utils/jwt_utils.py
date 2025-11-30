"""
JWT Token Utilities for Authentication
Used for cross-domain authentication in Cloud Run
"""
import jwt
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from config import config

logger = logging.getLogger(__name__)

# JWT secret key (use from config or secret)
JWT_SECRET = config.SECRET_KEY
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24 * 7  # 7 days


def generate_token(user_id: str, email: str, name: str, organization_id: Optional[str] = None) -> str:
    """Generate JWT token for user"""
    try:
        payload = {
            'user_id': user_id,
            'email': email,
            'name': name,
            'organization_id': organization_id,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return token
    except Exception as e:
        logger.error(f"Error generating JWT token: {e}")
        raise


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error verifying JWT token: {e}")
        return None


def get_user_from_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """Extract user info from JWT token (from Authorization header or query param)"""
    if not token:
        return None
    
    # Remove 'Bearer ' prefix if present
    if token.startswith('Bearer '):
        token = token[7:]
    
    return verify_token(token)

