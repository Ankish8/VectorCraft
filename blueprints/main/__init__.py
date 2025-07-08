"""
Main Blueprint for VectorCraft
Handles core application routes and user interface
"""

from flask import Blueprint

main_bp = Blueprint('main', __name__)

from . import routes