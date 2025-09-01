"""
Configurable Authentication Manager
Supports both Auth0 and Cloudflare Access authentication methods
"""
import os
import logging
from functools import wraps
from flask import request, session, redirect, url_for, jsonify
from datetime import datetime

logger = logging.getLogger(__name__)

class AuthManager:
    """Manages authentication based on configured method"""
    
    def __init__(self):
        self.auth_method = os.getenv('AUTH_METHOD', 'auth0').lower()
        logger.info(f"Authentication method: {self.auth_method}")
    
    def get_current_user(self):
        """Get current authenticated user info"""
        if self.auth_method == 'cloudflare_access':
            return self._get_cloudflare_access_user()
        elif self.auth_method == 'auth0':
            return self._get_auth0_user()
        else:
            logger.error(f"Unknown auth method: {self.auth_method}")
            return None
    
    def is_authenticated(self):
        """Check if user is authenticated"""
        user = self.get_current_user()
        return user is not None
    
    def require_auth_decorator(self, f):
        """Decorator to require authentication"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not self.is_authenticated():
                return self._handle_unauthenticated()
            return f(*args, **kwargs)
        return decorated_function
    
    def get_login_url(self):
        """Get the appropriate login URL"""
        if self.auth_method == 'cloudflare_access':
            # For Cloudflare Access, login happens automatically
            return url_for('index')
        else:
            # Auth0 login
            return url_for('login')
    
    def get_logout_url(self):
        """Get the appropriate logout URL"""
        return url_for('logout')
    
    def _get_cloudflare_access_user(self):
        """Get user info from Cloudflare Access headers"""
        email = request.headers.get('CF-Access-Authenticated-User-Email')
        user_id = request.headers.get('CF-Access-Authenticated-User-Id')
        name = request.headers.get('CF-Access-Authenticated-User-Name', email)
        
        if email:
            return {
                'user_id': user_id or email,
                'email': email,
                'name': name or email.split('@')[0],
                'picture': None,
                'auth_method': 'cloudflare_access'
            }
        return None
    
    def _get_auth0_user(self):
        """Get user info from Auth0 session"""
        user_info = session.get('user_info')
        if user_info:
            user_info['auth_method'] = 'auth0'
            return user_info
        return None
    
    def _handle_unauthenticated(self):
        """Handle unauthenticated access"""
        if self.auth_method == 'cloudflare_access':
            # For Cloudflare Access, if headers are missing, it means Access is not configured
            return jsonify({
                'error': 'Cloudflare Access not configured',
                'message': 'This application requires Cloudflare Access to be enabled on the domain'
            }), 401
        else:
            # Auth0 - redirect to login
            return redirect(url_for('login'))

# Global auth manager instance
auth_manager = AuthManager()