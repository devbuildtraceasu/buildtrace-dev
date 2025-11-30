"""
OAuth Configuration for BuildTrace
"""

import os
from flask_dance.contrib.google import make_google_blueprint

def create_oauth_blueprint(app):
    """Create and configure OAuth blueprint"""

    # Google OAuth configuration
    google_bp = make_google_blueprint(
        client_id=os.getenv('GOOGLE_OAUTH_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_OAUTH_CLIENT_SECRET'),
        scope=[
            "openid",
            "email",
            "profile"
        ],
        redirect_to="oauth_callback"
    )

    return google_bp

# OAuth configuration for different environments
OAUTH_CONFIG = {
    'google': {
        'authorize_url': 'https://accounts.google.com/o/oauth2/v2/auth',
        'token_url': 'https://oauth2.googleapis.com/token',
        'userinfo_url': 'https://openidconnect.googleapis.com/v1/userinfo',
        'scopes': ['openid', 'email', 'profile']
    }
}

def get_oauth_redirect_uri(app, provider='google'):
    """Get the OAuth redirect URI for the given provider"""
    if app.config.get('ENVIRONMENT') == 'production':
        base_url = "https://buildtrace-overlay-feature-largesize-123644909590.us-central1.run.app"
    else:
        base_url = "http://localhost:5001"

    return f"{base_url}/auth/{provider}/callback"