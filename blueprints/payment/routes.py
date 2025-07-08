"""
Payment processing routes for VectorCraft
"""

import logging
from flask import render_template, request, redirect, url_for
from flask_login import current_user

from . import payment_bp

logger = logging.getLogger(__name__)


@payment_bp.route('/buy')
def buy_now():
    """Buy now page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('buy.html')


@payment_bp.route('/success')
def success():
    """PayPal payment success redirect"""
    return render_template('payment_success.html')


@payment_bp.route('/cancel')
def cancel():
    """PayPal payment cancel redirect"""
    return render_template('payment_cancel.html')


@payment_bp.route('/status')
def status():
    """Payment status page"""
    return render_template('payment_status.html')