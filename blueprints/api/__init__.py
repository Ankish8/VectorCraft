"""
API Blueprint for VectorCraft
Handles all API endpoints for vectorization and file processing
"""

from flask import Blueprint

api_bp = Blueprint('api', __name__, url_prefix='/api')

from . import vectorize, uploads, health