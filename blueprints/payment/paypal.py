"""
PayPal integration endpoints for VectorCraft
"""

import os
import time
import secrets
import string
import random
import logging
from datetime import datetime

from flask import request, jsonify, session
from flask_login import current_user

from . import payment_bp
from blueprints.auth.utils import rate_limit_decorator
from database import db
from services.email_service import email_service
from services.paypal_service import paypal_service
from services.monitoring import system_logger

logger = logging.getLogger(__name__)


@payment_bp.route('/api/create-paypal-order', methods=['POST'])
@rate_limit_decorator(max_attempts=5, cooldown_minutes=5)
def create_paypal_order():
    """Create PayPal order for VectorCraft purchase"""
    transaction_id = None
    try:
        data = request.get_json()
        email = data.get('email')
        amount = data.get('amount', 49.00)
        
        if not email:
            system_logger.warning('payment', 'PayPal order creation failed: No email provided')
            return jsonify({'error': 'Email is required'}), 400
        
        # Generate transaction ID for tracking
        transaction_id = f"VC_{int(time.time())}_{secrets.token_hex(4)}"
        
        # Log transaction creation
        system_logger.info('payment', f'Creating PayPal order for {email}', 
                          user_email=email, transaction_id=transaction_id,
                          details={'amount': amount, 'email': email})
        
        # Create initial transaction record
        db.log_transaction(
            transaction_id=transaction_id,
            email=email,
            amount=amount,
            currency='USD',
            status='pending'
        )
        
        # Create PayPal order
        order_result = paypal_service.create_order(amount=amount, customer_email=email)
        
        if not order_result or not order_result.get('success'):
            # Update transaction with failure
            db.update_transaction(transaction_id, 
                                status='failed', 
                                error_message='Failed to create PayPal order')
            
            system_logger.error('payment', 'PayPal order creation failed', 
                              user_email=email, transaction_id=transaction_id,
                              details={'error': 'PayPal service error'})
            return jsonify({'error': 'Failed to create PayPal order'}), 500
        
        # Update transaction with PayPal order ID
        db.update_transaction(transaction_id, 
                            paypal_order_id=order_result['order_id'],
                            status='awaiting_payment')
        
        # Store order info in session for later processing
        session['pending_order'] = {
            'email': email,
            'amount': amount,
            'paypal_order_id': order_result['order_id'],
            'transaction_id': transaction_id,
            'created_at': time.time()
        }
        
        system_logger.info('payment', f'PayPal order created successfully: {order_result["order_id"]}',
                          user_email=email, transaction_id=transaction_id)
        
        return jsonify({
            'success': True,
            'order_id': order_result['order_id'],
            'approval_url': order_result['approval_url'],
            'architecture': 'modular_blueprint'
        })
        
    except Exception as e:
        error_msg = f"PayPal order creation error: {e}"
        logger.error(error_msg)
        
        if transaction_id:
            db.update_transaction(transaction_id, 
                                status='error', 
                                error_message=str(e))
            system_logger.error('payment', error_msg, transaction_id=transaction_id)
        else:
            system_logger.error('payment', error_msg)
            
        return jsonify({'error': str(e)}), 500


@payment_bp.route('/api/capture-paypal-order', methods=['POST'])
@rate_limit_decorator(max_attempts=10, cooldown_minutes=10)
def capture_paypal_order():
    """Capture PayPal payment and create user account"""
    transaction_id = None
    try:
        system_logger.info('payment', 'Processing PayPal payment capture')
        data = request.get_json()
        order_id = data.get('order_id')
        
        if not order_id:
            system_logger.warning('payment', 'PayPal capture failed: No order ID provided')
            return jsonify({'error': 'Order ID is required'}), 400
        
        # Get pending order from session
        pending_order = session.get('pending_order')
        transaction_id = pending_order.get('transaction_id') if pending_order else None
        
        if not pending_order or pending_order['paypal_order_id'] != order_id:
            system_logger.error('payment', 'Invalid order session for PayPal capture',
                              transaction_id=transaction_id,
                              details={'order_id': order_id})
            return jsonify({'error': 'Invalid order session'}), 400
        
        system_logger.info('payment', f'Capturing PayPal payment for order {order_id}',
                          transaction_id=transaction_id)
        
        # Capture PayPal payment
        capture_result = paypal_service.capture_order(order_id)
        
        if not capture_result or not capture_result.get('success'):
            # Update transaction with failure
            if transaction_id:
                db.update_transaction(transaction_id, 
                                    status='failed', 
                                    error_message='PayPal capture failed')
            
            system_logger.error('payment', 'PayPal capture failed',
                              transaction_id=transaction_id,
                              details={'order_id': order_id, 'capture_result': capture_result})
            return jsonify({'error': 'Failed to capture PayPal payment'}), 500
        
        # Use email from capture result if available, otherwise from session
        paypal_email = capture_result.get('payer_email') or pending_order['email']
        amount = capture_result.get('amount', pending_order['amount'])
        
        # Use actual PayPal payer email
        email = paypal_email
        
        # Generate username and password
        username = f"user_{random.randint(10000, 99999)}"
        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        
        system_logger.info('payment', f'Creating user account for {email}',
                          user_email=email, transaction_id=transaction_id,
                          details={'username': username, 'amount': amount})
        
        # Create user account
        user_id = _create_user_account(email, username, password, transaction_id)
        
        if not user_id:
            return jsonify({'error': 'Failed to create user account'}), 500
        
        # Update transaction with success
        if transaction_id:
            db.update_transaction(transaction_id,
                                status='completed',
                                username=username,
                                paypal_payment_id=capture_result.get('payment_id'),
                                user_created=True,
                                completed_at=True,
                                metadata={
                                    'paypal_transaction_id': capture_result.get('transaction_id'),
                                    'payer_email': email,
                                    'amount': amount,
                                    'currency': 'USD'
                                })
        
        # Send emails
        email_sent = _send_user_emails(email, username, password, {
            'amount': amount,
            'order_id': order_id,
            'payment_id': capture_result.get('payment_id'),
            'transaction_id': capture_result.get('transaction_id'),
            'username': username,
            'payer_email': email
        }, transaction_id)
        
        # Update transaction with email status
        if transaction_id:
            db.update_transaction(transaction_id, email_sent=email_sent)
        
        # Log successful payment completion
        system_logger.info('payment', f'Payment completed successfully - ${amount:.2f}',
                          user_email=email, transaction_id=transaction_id,
                          details={
                              'order_id': order_id,
                              'username': username,
                              'amount': amount,
                              'email_sent': email_sent,
                              'architecture': 'modular_blueprint'
                          })
        
        # Clear session
        session.pop('pending_order', None)
        
        return jsonify({
            'success': True,
            'message': 'Payment completed successfully',
            'username': username,
            'email_sent': email_sent,
            'order_id': order_id,
            'architecture': 'modular_blueprint'
        })
        
    except Exception as e:
        error_msg = f"PayPal capture error: {str(e)}"
        
        # Update transaction with error if we have transaction_id
        if transaction_id:
            db.update_transaction(transaction_id, 
                                status='error', 
                                error_message=str(e))
        
        # Log error for monitoring
        system_logger.error('payment', error_msg, 
                           transaction_id=transaction_id,
                           details={'order_id': order_id if 'order_id' in locals() else 'unknown'})
        
        logger.error(f"PayPal capture failed - Order: {order_id if 'order_id' in locals() else 'unknown'}, Error: {str(e)}")
        
        return jsonify({'error': str(e)}), 500


@payment_bp.route('/api/create-order', methods=['POST'])
def create_order_legacy():
    """Legacy order creation endpoint for testing/simulation"""
    try:
        data = request.get_json()
        email = data.get('email')
        username = data.get('username', '')
        amount = data.get('amount', 49.00)
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Generate username if not provided
        if not username:
            username = f"user_{random.randint(10000, 99999)}"
        
        # Generate secure password
        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        
        # Create user account
        user_id = db.create_user(username, email, password)
        if not user_id:
            return jsonify({'error': 'Failed to create user account'}), 500
        
        # Send emails
        order_details = {
            'amount': amount,
            'order_id': f"SIM_{int(time.time())}_{user_id}",
            'username': username
        }
        
        email_service.send_purchase_confirmation(email, order_details)
        email_sent = email_service.send_credentials_email(email, username, password, order_details)
        
        if not email_sent:
            logger.warning(f"Failed to send email to {email} - but user account created successfully")
        
        # Send admin notification
        email_service.send_admin_notification(
            "New Simulated Purchase",
            f"New customer: {email} (username: {username})\nAmount: ${amount:.2f}"
        )
        
        return jsonify({
            'success': True,
            'message': 'Order created successfully',
            'username': username,
            'email_sent': email_sent,
            'architecture': 'modular_blueprint'
        })
        
    except Exception as e:
        logger.error(f"Order creation error: {e}")
        return jsonify({'error': str(e)}), 500


def _create_user_account(email, username, password, transaction_id):
    """Create user account with error handling"""
    try:
        # Check if user already exists
        existing_user = db.get_user_by_email(email)
        if existing_user:
            # Update transaction with error
            if transaction_id:
                db.update_transaction(transaction_id, 
                                    status='failed', 
                                    error_message=f'User with email {email} already exists')
            
            system_logger.warning('payment', f'User account already exists: {email}',
                                 user_email=email, transaction_id=transaction_id)
            return None
        
        user_id = db.create_user(username, email, password)
        
        if not user_id:
            # Update transaction with error
            if transaction_id:
                db.update_transaction(transaction_id, 
                                    status='failed', 
                                    error_message='Failed to create user account')
            
            system_logger.error('payment', 'User creation returned None/False',
                              user_email=email, transaction_id=transaction_id)
            return None
        
        return user_id
        
    except Exception as e:
        # Update transaction with error
        if transaction_id:
            db.update_transaction(transaction_id, 
                                status='failed', 
                                error_message=f'User creation failed: {str(e)}')
        
        system_logger.error('payment', f'User creation exception: {str(e)}',
                          user_email=email, transaction_id=transaction_id)
        return None


def _send_user_emails(email, username, password, order_details, transaction_id):
    """Send purchase confirmation and credentials emails"""
    try:
        # Send purchase confirmation
        system_logger.info('email', f'Sending purchase confirmation to {email}',
                          user_email=email, transaction_id=transaction_id)
        confirm_result = email_service.send_purchase_confirmation(email, order_details)
        
        # Send credentials email
        system_logger.info('email', f'Sending credentials email to {email}',
                          user_email=email, transaction_id=transaction_id)
        email_sent = email_service.send_credentials_email(email, username, password, order_details)
        
        if not email_sent:
            system_logger.warning('email', f'Failed to send credentials email to {email}',
                                 user_email=email, transaction_id=transaction_id)
        else:
            system_logger.info('email', f'Credentials email sent successfully to {email}',
                             user_email=email, transaction_id=transaction_id)
        
        # Send admin notification
        email_service.send_admin_notification(
            "New PayPal Purchase",
            f"New customer: {email} (username: {username})\nAmount: ${order_details['amount']:.2f}\nPayPal Order: {order_details['order_id']}\nTransaction: {order_details.get('transaction_id', 'N/A')}"
        )
        
        return email_sent
        
    except Exception as e:
        system_logger.error('email', f'Email sending failed: {str(e)}',
                          user_email=email, transaction_id=transaction_id)
        return False