"""
Payment Blueprint for VectorCraft
Handles PayPal integration and transaction processing
"""

from flask import Blueprint

payment_bp = Blueprint('payment', __name__, url_prefix='/payment')

from . import routes, paypal