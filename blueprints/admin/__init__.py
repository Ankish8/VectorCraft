"""
Admin Blueprint for VectorCraft
Handles administrative functionality and monitoring
"""

from flask import Blueprint

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

from . import routes, monitoring, dashboard, analytics_routes, file_management, system_config, system_control