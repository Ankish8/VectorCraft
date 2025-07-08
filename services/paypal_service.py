#!/usr/bin/env python3
"""
PayPal Service for VectorCraft
Handles PayPal REST API integration for one-time payments
"""

import os
import requests
import base64
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

class PayPalService:
    """PayPal REST API service for processing payments"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client_id = os.getenv('PAYPAL_CLIENT_ID', '')
        self.client_secret = os.getenv('PAYPAL_CLIENT_SECRET', '')
        self.environment = os.getenv('PAYPAL_ENVIRONMENT', 'sandbox')
        
        # Set API base URL based on environment
        if self.environment == 'sandbox':
            self.base_url = 'https://api.sandbox.paypal.com'
        else:
            self.base_url = 'https://api.paypal.com'
        
        self.access_token = None
        self.token_expires_at = None
        
        if not self.client_id or not self.client_secret:
            self.logger.warning("PayPal credentials not configured. Payment processing will be simulated.")
            self.enabled = False
        else:
            self.enabled = True
            self.logger.info(f"PayPal service configured: {self.environment} environment")
    
    def _get_access_token(self):
        """Get OAuth access token from PayPal"""
        if not self.enabled:
            return None
        
        # Check if we have a valid token
        if self.access_token and self.token_expires_at:
            if datetime.now().timestamp() < self.token_expires_at:
                return self.access_token
        
        # Get new token
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = 'grant_type=client_credentials'
        
        try:
            response = requests.post(
                f"{self.base_url}/v1/oauth2/token",
                headers=headers,
                data=data,
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                # Set expiration to 90% of actual expiration for safety
                expires_in = int(token_data.get('expires_in', 3600)) * 0.9
                self.token_expires_at = datetime.now().timestamp() + expires_in
                self.logger.debug(f"PayPal access token obtained")
                return self.access_token
            else:
                self.logger.error(f"Failed to get PayPal access token: {response.status_code}")
                self.logger.error(f"Response: {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting PayPal access token: {str(e)}")
            return None
    
    def create_order(self, amount=49.00, currency='USD', customer_email=None):
        """Create a PayPal order for VectorCraft purchase"""
        if not self.enabled:
            return self._simulate_order_creation(amount, currency)
        
        access_token = self._get_access_token()
        if not access_token:
            return None
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'PayPal-Request-Id': f'vectorcraft-{int(datetime.now().timestamp())}'
        }
        
        order_data = {
            'intent': 'CAPTURE',
            'purchase_units': [{
                'reference_id': f'vectorcraft-{int(datetime.now().timestamp())}',
                'amount': {
                    'currency_code': currency,
                    'value': f'{amount:.2f}'
                },
                'description': 'VectorCraft Professional - Lifetime Access',
                'soft_descriptor': 'VECTORCRAFT'
            }],
            'payment_source': {
                'paypal': {
                    'experience_context': {
                        'payment_method_preference': 'IMMEDIATE_PAYMENT_REQUIRED',
                        'brand_name': 'VectorCraft',
                        'locale': 'en-US',
                        'landing_page': 'LOGIN',
                        'shipping_preference': 'NO_SHIPPING',
                        'user_action': 'PAY_NOW',
                        'return_url': f"{os.getenv('DOMAIN_URL', 'http://localhost:8080')}/payment/success",
                        'cancel_url': f"{os.getenv('DOMAIN_URL', 'http://localhost:8080')}/payment/cancel"
                    }
                }
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/v2/checkout/orders",
                headers=headers,
                json=order_data,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                order = response.json()
                self.logger.info(f"PayPal order created: {order['id']}")
                self.logger.debug(f"PayPal order links: {order.get('links', [])}")
                approval_url = self._get_approval_url(order)
                self.logger.info(f"Approval URL: {approval_url}")
                return {
                    'success': True,
                    'order_id': order['id'],
                    'approval_url': approval_url,
                    'amount': amount,
                    'currency': currency
                }
            else:
                self.logger.error(f"Failed to create PayPal order: {response.status_code}")
                self.logger.error(f"Response: {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating PayPal order: {str(e)}")
            return None
    
    def capture_order(self, order_id):
        """Capture payment for a PayPal order"""
        if not self.enabled:
            return self._simulate_order_capture(order_id)
        
        access_token = self._get_access_token()
        if not access_token:
            return None
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/v2/checkout/orders/{order_id}/capture",
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                capture_data = response.json()
                self.logger.info(f"PayPal payment captured: {order_id}")
                
                # Extract payment details
                payment_info = self._extract_payment_info(capture_data)
                return {
                    'success': True,
                    'order_id': order_id,
                    'payment_id': payment_info['payment_id'],
                    'amount': payment_info['amount'],
                    'currency': payment_info['currency'],
                    'payer_email': payment_info['payer_email'],
                    'transaction_id': payment_info['transaction_id'],
                    'status': 'COMPLETED'
                }
            else:
                self.logger.error(f"Failed to capture PayPal payment: {response.status_code}")
                self.logger.error(f"Response: {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error capturing PayPal payment: {str(e)}")
            return None
    
    def get_order_details(self, order_id):
        """Get details of a PayPal order"""
        if not self.enabled:
            return self._simulate_order_details(order_id)
        
        access_token = self._get_access_token()
        if not access_token:
            return None
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/v2/checkout/orders/{order_id}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Failed to get PayPal order details: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting PayPal order details: {str(e)}")
            return None
    
    def _get_approval_url(self, order):
        """Extract approval URL from PayPal order response"""
        if 'links' in order:
            for link in order['links']:
                if link['rel'] in ['approve', 'payer-action']:
                    return link['href']
        return None
    
    def _extract_payment_info(self, capture_data):
        """Extract payment information from capture response"""
        payment_info = {
            'payment_id': capture_data.get('id', ''),
            'amount': 0.0,
            'currency': 'USD',
            'payer_email': '',
            'transaction_id': ''
        }
        
        # Extract purchase unit info
        if 'purchase_units' in capture_data and len(capture_data['purchase_units']) > 0:
            unit = capture_data['purchase_units'][0]
            
            # Get amount
            if 'payments' in unit and 'captures' in unit['payments']:
                captures = unit['payments']['captures']
                if len(captures) > 0:
                    capture = captures[0]
                    payment_info['transaction_id'] = capture.get('id', '')
                    if 'amount' in capture:
                        payment_info['amount'] = float(capture['amount'].get('value', 0))
                        payment_info['currency'] = capture['amount'].get('currency_code', 'USD')
        
        # Extract payer email
        if 'payer' in capture_data and 'email_address' in capture_data['payer']:
            payment_info['payer_email'] = capture_data['payer']['email_address']
        
        return payment_info
    
    def _simulate_order_creation(self, amount, currency):
        """Simulate order creation when PayPal is not configured"""
        self.logger.info(f"SIMULATED: PayPal order creation for ${amount:.2f} {currency}")
        return {
            'success': True,
            'order_id': f'SIMULATED_{int(datetime.now().timestamp())}',
            'approval_url': '/payment/simulate',
            'amount': amount,
            'currency': currency
        }
    
    def _simulate_order_capture(self, order_id):
        """Simulate order capture when PayPal is not configured"""
        self.logger.info(f"SIMULATED: PayPal payment capture for order {order_id}")
        return {
            'success': True,
            'order_id': order_id,
            'payment_id': f'SIM_{order_id}',
            'amount': 49.00,
            'currency': 'USD',
            'payer_email': 'test@example.com',
            'transaction_id': f'TXN_{order_id}',
            'status': 'COMPLETED'
        }
    
    def _simulate_order_details(self, order_id):
        """Simulate order details when PayPal is not configured"""
        return {
            'id': order_id,
            'status': 'APPROVED',
            'intent': 'CAPTURE'
        }

# Global PayPal service instance
paypal_service = PayPalService()