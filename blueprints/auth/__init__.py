"""
Authentication Blueprint for VectorCraft
Handles user authentication, session management, and security
"""

from flask import Blueprint

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

from . import routes