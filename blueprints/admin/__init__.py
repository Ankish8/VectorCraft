"""
Admin Blueprint for VectorCraft
Handles administrative functionality and monitoring
"""

from flask import Blueprint

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Import all admin modules
from . import (
    routes, 
    monitoring, 
    dashboard, 
    analytics_routes, 
    file_management,
    system_config,
    system_control,
    pricing,
    email_campaigns,
    marketing,
    permissions,
    performance,
    content,
    business_logic,
    security,
    api_management,
    email_routes
)