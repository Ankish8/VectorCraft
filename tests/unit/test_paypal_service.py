#!/usr/bin/env python3
"""
Unit tests for PayPal service functionality
Tests payment creation, execution, and error handling
"""

import pytest
import json
import responses
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime, timedelta

from services.paypal_service import PayPalService, PayPalError


class TestPayPalServiceInitialization:
    """Test PayPal service initialization"""
    
    def test_init_sandbox_environment(self):
        """Test initialization with sandbox environment"""
        with patch.dict('os.environ', {
            'PAYPAL_CLIENT_ID': 'test_client_id',
            'PAYPAL_CLIENT_SECRET': 'test_client_secret',
            'PAYPAL_ENVIRONMENT': 'sandbox'
        }):
            paypal_service = PayPalService()
            
            assert paypal_service.client_id == 'test_client_id'
            assert paypal_service.client_secret == 'test_client_secret'
            assert paypal_service.environment == 'sandbox'
            assert 'sandbox' in paypal_service.base_url
    
    def test_init_live_environment(self):
        """Test initialization with live environment"""
        with patch.dict('os.environ', {
            'PAYPAL_CLIENT_ID': 'live_client_id',
            'PAYPAL_CLIENT_SECRET': 'live_client_secret',
            'PAYPAL_ENVIRONMENT': 'live'
        }):
            paypal_service = PayPalService()
            
            assert paypal_service.client_id == 'live_client_id'
            assert paypal_service.client_secret == 'live_client_secret'
            assert paypal_service.environment == 'live'
            assert 'sandbox' not in paypal_service.base_url
    
    def test_init_missing_credentials(self):
        """Test initialization with missing credentials"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="PayPal credentials not configured"):
                PayPalService()
    
    def test_init_invalid_environment(self):
        """Test initialization with invalid environment"""
        with patch.dict('os.environ', {
            'PAYPAL_CLIENT_ID': 'test_client_id',
            'PAYPAL_CLIENT_SECRET': 'test_client_secret',
            'PAYPAL_ENVIRONMENT': 'invalid'
        }):
            with pytest.raises(ValueError, match="Invalid PayPal environment"):
                PayPalService()


class TestPayPalAuthentication:
    """Test PayPal authentication functionality"""
    
    @responses.activate
    def test_get_access_token_success(self):
        """Test successful access token retrieval"""
        # Mock OAuth token response
        responses.add(
            responses.POST,
            'https://api-m.sandbox.paypal.com/v1/oauth2/token',
            json={
                'access_token': 'test_access_token',
                'token_type': 'Bearer',
                'expires_in': 3600
            },
            status=200
        )
        
        paypal_service = PayPalService()
        token = paypal_service.get_access_token()
        
        assert token == 'test_access_token'
        assert len(responses.calls) == 1
    
    @responses.activate
    def test_get_access_token_failure(self):
        """Test access token retrieval failure"""
        # Mock OAuth token error response
        responses.add(
            responses.POST,
            'https://api-m.sandbox.paypal.com/v1/oauth2/token',
            json={
                'error': 'invalid_client',
                'error_description': 'Client authentication failed'
            },
            status=401
        )
        
        paypal_service = PayPalService()
        
        with pytest.raises(PayPalError, match="Authentication failed"):
            paypal_service.get_access_token()
    
    @responses.activate
    def test_access_token_caching(self):
        """Test access token caching"""
        # Mock OAuth token response
        responses.add(
            responses.POST,
            'https://api-m.sandbox.paypal.com/v1/oauth2/token',
            json={
                'access_token': 'cached_token',
                'token_type': 'Bearer',
                'expires_in': 3600
            },
            status=200
        )
        
        paypal_service = PayPalService()
        
        # First call should make HTTP request
        token1 = paypal_service.get_access_token()
        assert token1 == 'cached_token'
        assert len(responses.calls) == 1
        
        # Second call should use cached token
        token2 = paypal_service.get_access_token()
        assert token2 == 'cached_token'
        assert len(responses.calls) == 1  # No additional HTTP calls
    
    @responses.activate
    def test_access_token_refresh(self):
        """Test access token refresh when expired"""
        # Mock initial token response
        responses.add(
            responses.POST,
            'https://api-m.sandbox.paypal.com/v1/oauth2/token',
            json={
                'access_token': 'initial_token',
                'token_type': 'Bearer',
                'expires_in': 1  # Expires in 1 second
            },
            status=200
        )
        
        # Mock refresh token response
        responses.add(
            responses.POST,
            'https://api-m.sandbox.paypal.com/v1/oauth2/token',
            json={
                'access_token': 'refreshed_token',
                'token_type': 'Bearer',
                'expires_in': 3600
            },
            status=200
        )
        
        paypal_service = PayPalService()
        
        # First call
        token1 = paypal_service.get_access_token()
        assert token1 == 'initial_token'
        
        # Mock time passing to expire token
        with patch('time.time') as mock_time:
            mock_time.return_value = paypal_service.token_expires_at + 1
            
            # Second call should refresh token
            token2 = paypal_service.get_access_token()
            assert token2 == 'refreshed_token'
            assert len(responses.calls) == 2


class TestPaymentCreation:
    """Test payment creation functionality"""
    
    @responses.activate
    def test_create_payment_success(self):
        """Test successful payment creation"""
        # Mock access token
        responses.add(
            responses.POST,
            'https://api-m.sandbox.paypal.com/v1/oauth2/token',
            json={'access_token': 'test_token', 'expires_in': 3600},
            status=200
        )
        
        # Mock payment creation
        responses.add(
            responses.POST,
            'https://api-m.sandbox.paypal.com/v1/payments/payment',
            json={
                'id': 'PAY-123456789',
                'state': 'created',
                'links': [
                    {
                        'href': 'https://www.sandbox.paypal.com/cgi-bin/webscr?cmd=_express-checkout&token=EC-123',
                        'rel': 'approval_url',
                        'method': 'REDIRECT'
                    }
                ]
            },
            status=201
        )
        
        paypal_service = PayPalService()
        payment = paypal_service.create_payment(
            amount=49.00,
            currency='USD',
            description='VectorCraft Access',
            return_url='http://example.com/success',
            cancel_url='http://example.com/cancel'
        )
        
        assert payment is not None
        assert payment['id'] == 'PAY-123456789'
        assert payment['state'] == 'created'
        assert 'approval_url' in payment
        assert 'approval_url' in payment['approval_url']
    
    @responses.activate
    def test_create_payment_invalid_amount(self):
        """Test payment creation with invalid amount"""
        paypal_service = PayPalService()
        
        with pytest.raises(ValueError, match="Amount must be positive"):
            paypal_service.create_payment(
                amount=-10.00,
                currency='USD',
                description='Test',
                return_url='http://example.com/success',
                cancel_url='http://example.com/cancel'
            )
    
    @responses.activate
    def test_create_payment_invalid_currency(self):
        """Test payment creation with invalid currency"""
        paypal_service = PayPalService()
        
        with pytest.raises(ValueError, match="Invalid currency"):
            paypal_service.create_payment(
                amount=49.00,
                currency='INVALID',
                description='Test',
                return_url='http://example.com/success',
                cancel_url='http://example.com/cancel'
            )
    
    @responses.activate
    def test_create_payment_api_error(self):
        """Test payment creation API error"""
        # Mock access token
        responses.add(
            responses.POST,
            'https://api-m.sandbox.paypal.com/v1/oauth2/token',
            json={'access_token': 'test_token', 'expires_in': 3600},
            status=200
        )
        
        # Mock payment creation error
        responses.add(
            responses.POST,
            'https://api-m.sandbox.paypal.com/v1/payments/payment',
            json={
                'name': 'VALIDATION_ERROR',
                'message': 'Invalid request'
            },
            status=400
        )
        
        paypal_service = PayPalService()
        
        with pytest.raises(PayPalError, match="Payment creation failed"):
            paypal_service.create_payment(
                amount=49.00,
                currency='USD',
                description='Test',
                return_url='http://example.com/success',
                cancel_url='http://example.com/cancel'
            )
    
    @responses.activate
    def test_create_payment_with_metadata(self):
        """Test payment creation with metadata"""
        # Mock access token
        responses.add(
            responses.POST,
            'https://api-m.sandbox.paypal.com/v1/oauth2/token',
            json={'access_token': 'test_token', 'expires_in': 3600},
            status=200
        )
        
        # Mock payment creation
        responses.add(
            responses.POST,
            'https://api-m.sandbox.paypal.com/v1/payments/payment',
            json={
                'id': 'PAY-123456789',
                'state': 'created',
                'links': [
                    {
                        'href': 'https://www.sandbox.paypal.com/cgi-bin/webscr?cmd=_express-checkout&token=EC-123',
                        'rel': 'approval_url',
                        'method': 'REDIRECT'
                    }
                ]
            },
            status=201
        )
        
        paypal_service = PayPalService()
        payment = paypal_service.create_payment(
            amount=49.00,
            currency='USD',
            description='VectorCraft Access',
            return_url='http://example.com/success',
            cancel_url='http://example.com/cancel',
            metadata={'user_id': '123', 'plan': 'basic'}
        )
        
        assert payment is not None
        assert payment['id'] == 'PAY-123456789'
        
        # Verify metadata was included in request
        request_body = json.loads(responses.calls[1].request.body)
        assert 'custom' in request_body['transactions'][0]


class TestPaymentExecution:
    """Test payment execution functionality"""
    
    @responses.activate
    def test_execute_payment_success(self):
        """Test successful payment execution"""
        # Mock access token
        responses.add(
            responses.POST,
            'https://api-m.sandbox.paypal.com/v1/oauth2/token',
            json={'access_token': 'test_token', 'expires_in': 3600},
            status=200
        )
        
        # Mock payment execution
        responses.add(
            responses.POST,
            'https://api-m.sandbox.paypal.com/v1/payments/payment/PAY-123456789/execute',
            json={
                'id': 'PAY-123456789',
                'state': 'approved',
                'payer': {
                    'payer_info': {
                        'email': 'test@example.com',
                        'first_name': 'Test',
                        'last_name': 'User'
                    }
                },
                'transactions': [
                    {
                        'amount': {
                            'total': '49.00',
                            'currency': 'USD'
                        },
                        'related_resources': [
                            {
                                'sale': {
                                    'id': 'SALE-123456789',
                                    'state': 'completed'
                                }
                            }
                        ]
                    }
                ]
            },
            status=200
        )
        
        paypal_service = PayPalService()
        payment = paypal_service.execute_payment('PAY-123456789', 'PAYER-123')
        
        assert payment is not None
        assert payment['id'] == 'PAY-123456789'
        assert payment['state'] == 'approved'
        assert payment['payer']['payer_info']['email'] == 'test@example.com'
    
    @responses.activate
    def test_execute_payment_invalid_payment_id(self):
        """Test payment execution with invalid payment ID"""
        paypal_service = PayPalService()
        
        with pytest.raises(ValueError, match="Payment ID is required"):
            paypal_service.execute_payment('', 'PAYER-123')
    
    @responses.activate
    def test_execute_payment_invalid_payer_id(self):
        """Test payment execution with invalid payer ID"""
        paypal_service = PayPalService()
        
        with pytest.raises(ValueError, match="Payer ID is required"):
            paypal_service.execute_payment('PAY-123456789', '')
    
    @responses.activate
    def test_execute_payment_api_error(self):
        """Test payment execution API error"""
        # Mock access token
        responses.add(
            responses.POST,
            'https://api-m.sandbox.paypal.com/v1/oauth2/token',
            json={'access_token': 'test_token', 'expires_in': 3600},
            status=200
        )
        
        # Mock payment execution error
        responses.add(
            responses.POST,
            'https://api-m.sandbox.paypal.com/v1/payments/payment/PAY-123456789/execute',
            json={
                'name': 'PAYMENT_ALREADY_DONE',
                'message': 'Payment has already been approved and executed'
            },
            status=400
        )
        
        paypal_service = PayPalService()
        
        with pytest.raises(PayPalError, match="Payment execution failed"):
            paypal_service.execute_payment('PAY-123456789', 'PAYER-123')
    
    @responses.activate
    def test_execute_payment_not_found(self):
        """Test payment execution with non-existent payment"""
        # Mock access token
        responses.add(
            responses.POST,
            'https://api-m.sandbox.paypal.com/v1/oauth2/token',
            json={'access_token': 'test_token', 'expires_in': 3600},
            status=200
        )
        
        # Mock payment not found error
        responses.add(
            responses.POST,
            'https://api-m.sandbox.paypal.com/v1/payments/payment/PAY-NONEXISTENT/execute',
            json={
                'name': 'INVALID_RESOURCE_ID',
                'message': 'The requested resource ID was not found'
            },
            status=404
        )
        
        paypal_service = PayPalService()
        
        with pytest.raises(PayPalError, match="Payment not found"):
            paypal_service.execute_payment('PAY-NONEXISTENT', 'PAYER-123')


class TestPaymentRetrieval:
    """Test payment retrieval functionality"""
    
    @responses.activate
    def test_get_payment_details_success(self):
        """Test successful payment details retrieval"""
        # Mock access token
        responses.add(
            responses.POST,
            'https://api-m.sandbox.paypal.com/v1/oauth2/token',
            json={'access_token': 'test_token', 'expires_in': 3600},
            status=200
        )
        
        # Mock payment details
        responses.add(
            responses.GET,
            'https://api-m.sandbox.paypal.com/v1/payments/payment/PAY-123456789',
            json={
                'id': 'PAY-123456789',
                'state': 'approved',
                'create_time': '2023-01-01T12:00:00Z',
                'update_time': '2023-01-01T12:01:00Z',
                'payer': {
                    'payer_info': {
                        'email': 'test@example.com'
                    }
                },
                'transactions': [
                    {
                        'amount': {
                            'total': '49.00',
                            'currency': 'USD'
                        }
                    }
                ]
            },
            status=200
        )
        
        paypal_service = PayPalService()
        payment = paypal_service.get_payment_details('PAY-123456789')
        
        assert payment is not None
        assert payment['id'] == 'PAY-123456789'
        assert payment['state'] == 'approved'
        assert payment['payer']['payer_info']['email'] == 'test@example.com'
    
    @responses.activate
    def test_get_payment_details_not_found(self):
        """Test payment details retrieval for non-existent payment"""
        # Mock access token
        responses.add(
            responses.POST,
            'https://api-m.sandbox.paypal.com/v1/oauth2/token',
            json={'access_token': 'test_token', 'expires_in': 3600},
            status=200
        )
        
        # Mock payment not found
        responses.add(
            responses.GET,
            'https://api-m.sandbox.paypal.com/v1/payments/payment/PAY-NONEXISTENT',
            json={
                'name': 'INVALID_RESOURCE_ID',
                'message': 'The requested resource ID was not found'
            },
            status=404
        )
        
        paypal_service = PayPalService()
        payment = paypal_service.get_payment_details('PAY-NONEXISTENT')
        
        assert payment is None
    
    @responses.activate
    def test_get_payment_status(self):
        """Test payment status retrieval"""
        # Mock access token
        responses.add(
            responses.POST,
            'https://api-m.sandbox.paypal.com/v1/oauth2/token',
            json={'access_token': 'test_token', 'expires_in': 3600},
            status=200
        )
        
        # Mock payment details
        responses.add(
            responses.GET,
            'https://api-m.sandbox.paypal.com/v1/payments/payment/PAY-123456789',
            json={
                'id': 'PAY-123456789',
                'state': 'approved'
            },
            status=200
        )
        
        paypal_service = PayPalService()
        status = paypal_service.get_payment_status('PAY-123456789')
        
        assert status == 'approved'
    
    @responses.activate
    def test_list_payments(self):
        """Test listing payments"""
        # Mock access token
        responses.add(
            responses.POST,
            'https://api-m.sandbox.paypal.com/v1/oauth2/token',
            json={'access_token': 'test_token', 'expires_in': 3600},
            status=200
        )
        
        # Mock payments list
        responses.add(
            responses.GET,
            'https://api-m.sandbox.paypal.com/v1/payments/payment',
            json={
                'payments': [
                    {
                        'id': 'PAY-123456789',
                        'state': 'approved',
                        'create_time': '2023-01-01T12:00:00Z'
                    },
                    {
                        'id': 'PAY-987654321',
                        'state': 'created',
                        'create_time': '2023-01-01T11:00:00Z'
                    }
                ],
                'count': 2,
                'next_id': 'PAY-NEXT'
            },
            status=200
        )
        
        paypal_service = PayPalService()
        payments = paypal_service.list_payments(count=10)
        
        assert payments is not None
        assert len(payments['payments']) == 2
        assert payments['count'] == 2
        assert payments['payments'][0]['id'] == 'PAY-123456789'


class TestWebhookHandling:
    """Test webhook handling functionality"""
    
    def test_verify_webhook_signature(self):
        """Test webhook signature verification"""
        paypal_service = PayPalService()
        
        # Mock webhook data
        webhook_data = {
            'id': 'WH-123456789',
            'event_type': 'PAYMENT.SALE.COMPLETED',
            'resource': {
                'id': 'SALE-123456789',
                'state': 'completed'
            }
        }
        
        headers = {
            'PAYPAL-TRANSMISSION-ID': 'test-transmission-id',
            'PAYPAL-CERT-ID': 'test-cert-id',
            'PAYPAL-TRANSMISSION-TIME': '2023-01-01T12:00:00Z',
            'PAYPAL-TRANSMISSION-SIG': 'test-signature'
        }
        
        # Mock signature verification
        with patch.object(paypal_service, '_verify_webhook_signature') as mock_verify:
            mock_verify.return_value = True
            
            result = paypal_service.verify_webhook(webhook_data, headers)
            assert result is True
            mock_verify.assert_called_once()
    
    def test_verify_webhook_invalid_signature(self):
        """Test webhook with invalid signature"""
        paypal_service = PayPalService()
        
        webhook_data = {
            'id': 'WH-123456789',
            'event_type': 'PAYMENT.SALE.COMPLETED'
        }
        
        headers = {
            'PAYPAL-TRANSMISSION-ID': 'test-transmission-id',
            'PAYPAL-CERT-ID': 'test-cert-id',
            'PAYPAL-TRANSMISSION-TIME': '2023-01-01T12:00:00Z',
            'PAYPAL-TRANSMISSION-SIG': 'invalid-signature'
        }
        
        # Mock signature verification failure
        with patch.object(paypal_service, '_verify_webhook_signature') as mock_verify:
            mock_verify.return_value = False
            
            result = paypal_service.verify_webhook(webhook_data, headers)
            assert result is False
    
    def test_process_webhook_payment_completed(self):
        """Test processing payment completed webhook"""
        paypal_service = PayPalService()
        
        webhook_data = {
            'id': 'WH-123456789',
            'event_type': 'PAYMENT.SALE.COMPLETED',
            'resource': {
                'id': 'SALE-123456789',
                'state': 'completed',
                'parent_payment': 'PAY-123456789',
                'amount': {
                    'total': '49.00',
                    'currency': 'USD'
                }
            }
        }
        
        processed_data = paypal_service.process_webhook(webhook_data)
        
        assert processed_data is not None
        assert processed_data['event_type'] == 'PAYMENT.SALE.COMPLETED'
        assert processed_data['payment_id'] == 'PAY-123456789'
        assert processed_data['sale_id'] == 'SALE-123456789'
        assert processed_data['amount'] == 49.00
        assert processed_data['currency'] == 'USD'
    
    def test_process_webhook_payment_failed(self):
        """Test processing payment failed webhook"""
        paypal_service = PayPalService()
        
        webhook_data = {
            'id': 'WH-123456789',
            'event_type': 'PAYMENT.SALE.DENIED',
            'resource': {
                'id': 'SALE-123456789',
                'state': 'denied',
                'parent_payment': 'PAY-123456789',
                'reason_code': 'DENIED_BY_RISK'
            }
        }
        
        processed_data = paypal_service.process_webhook(webhook_data)
        
        assert processed_data is not None
        assert processed_data['event_type'] == 'PAYMENT.SALE.DENIED'
        assert processed_data['payment_id'] == 'PAY-123456789'
        assert processed_data['reason_code'] == 'DENIED_BY_RISK'
    
    def test_process_webhook_unsupported_event(self):
        """Test processing unsupported webhook event"""
        paypal_service = PayPalService()
        
        webhook_data = {
            'id': 'WH-123456789',
            'event_type': 'UNSUPPORTED.EVENT.TYPE',
            'resource': {}
        }
        
        processed_data = paypal_service.process_webhook(webhook_data)
        
        assert processed_data is None


class TestPayPalErrorHandling:
    """Test PayPal error handling"""
    
    @responses.activate
    def test_handle_rate_limiting(self):
        """Test handling of rate limiting errors"""
        # Mock access token
        responses.add(
            responses.POST,
            'https://api-m.sandbox.paypal.com/v1/oauth2/token',
            json={'access_token': 'test_token', 'expires_in': 3600},
            status=200
        )
        
        # Mock rate limiting error
        responses.add(
            responses.GET,
            'https://api-m.sandbox.paypal.com/v1/payments/payment/PAY-123456789',
            json={
                'name': 'RATE_LIMIT_REACHED',
                'message': 'Rate limit reached'
            },
            status=429
        )
        
        paypal_service = PayPalService()
        
        with pytest.raises(PayPalError, match="Rate limit reached"):
            paypal_service.get_payment_details('PAY-123456789')
    
    @responses.activate
    def test_handle_server_error(self):
        """Test handling of server errors"""
        # Mock access token
        responses.add(
            responses.POST,
            'https://api-m.sandbox.paypal.com/v1/oauth2/token',
            json={'access_token': 'test_token', 'expires_in': 3600},
            status=200
        )
        
        # Mock server error
        responses.add(
            responses.GET,
            'https://api-m.sandbox.paypal.com/v1/payments/payment/PAY-123456789',
            json={
                'name': 'INTERNAL_SERVER_ERROR',
                'message': 'Internal server error'
            },
            status=500
        )
        
        paypal_service = PayPalService()
        
        with pytest.raises(PayPalError, match="Internal server error"):
            paypal_service.get_payment_details('PAY-123456789')
    
    @responses.activate
    def test_handle_network_timeout(self):
        """Test handling of network timeouts"""
        # Mock access token
        responses.add(
            responses.POST,
            'https://api-m.sandbox.paypal.com/v1/oauth2/token',
            json={'access_token': 'test_token', 'expires_in': 3600},
            status=200
        )
        
        paypal_service = PayPalService()
        
        # Mock network timeout
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("Request timeout")
            
            with pytest.raises(PayPalError, match="Request timeout"):
                paypal_service.get_payment_details('PAY-123456789')
    
    @responses.activate
    def test_handle_connection_error(self):
        """Test handling of connection errors"""
        # Mock access token
        responses.add(
            responses.POST,
            'https://api-m.sandbox.paypal.com/v1/oauth2/token',
            json={'access_token': 'test_token', 'expires_in': 3600},
            status=200
        )
        
        paypal_service = PayPalService()
        
        # Mock connection error
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")
            
            with pytest.raises(PayPalError, match="Connection failed"):
                paypal_service.get_payment_details('PAY-123456789')
    
    def test_retry_mechanism(self):
        """Test retry mechanism for failed requests"""
        paypal_service = PayPalService()
        
        # Mock failed requests with eventual success
        with patch('requests.get') as mock_get:
            mock_get.side_effect = [
                requests.exceptions.ConnectionError("Connection failed"),
                requests.exceptions.ConnectionError("Connection failed"),
                Mock(status_code=200, json=lambda: {'id': 'PAY-123456789'})
            ]
            
            result = paypal_service._make_request_with_retry('GET', '/test-endpoint')
            assert result['id'] == 'PAY-123456789'
            assert mock_get.call_count == 3
    
    def test_retry_exhausted(self):
        """Test retry mechanism when all retries are exhausted"""
        paypal_service = PayPalService()
        
        # Mock all retries failing
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")
            
            with pytest.raises(PayPalError, match="Connection failed"):
                paypal_service._make_request_with_retry('GET', '/test-endpoint')
            
            assert mock_get.call_count == 3  # Default retry count


class TestPayPalValidation:
    """Test PayPal validation functions"""
    
    def test_validate_amount(self):
        """Test amount validation"""
        paypal_service = PayPalService()
        
        # Valid amounts
        assert paypal_service._validate_amount(0.01) is True
        assert paypal_service._validate_amount(10.00) is True
        assert paypal_service._validate_amount(999.99) is True
        
        # Invalid amounts
        assert paypal_service._validate_amount(0.00) is False
        assert paypal_service._validate_amount(-1.00) is False
        assert paypal_service._validate_amount(10000.00) is False
    
    def test_validate_currency(self):
        """Test currency validation"""
        paypal_service = PayPalService()
        
        # Valid currencies
        assert paypal_service._validate_currency('USD') is True
        assert paypal_service._validate_currency('EUR') is True
        assert paypal_service._validate_currency('GBP') is True
        
        # Invalid currencies
        assert paypal_service._validate_currency('INVALID') is False
        assert paypal_service._validate_currency('') is False
        assert paypal_service._validate_currency(None) is False
    
    def test_validate_url(self):
        """Test URL validation"""
        paypal_service = PayPalService()
        
        # Valid URLs
        assert paypal_service._validate_url('https://example.com') is True
        assert paypal_service._validate_url('http://example.com/path') is True
        assert paypal_service._validate_url('https://example.com/path?param=value') is True
        
        # Invalid URLs
        assert paypal_service._validate_url('invalid-url') is False
        assert paypal_service._validate_url('') is False
        assert paypal_service._validate_url(None) is False
    
    def test_validate_payment_data(self):
        """Test payment data validation"""
        paypal_service = PayPalService()
        
        # Valid payment data
        valid_data = {
            'amount': 49.00,
            'currency': 'USD',
            'description': 'Test payment',
            'return_url': 'https://example.com/success',
            'cancel_url': 'https://example.com/cancel'
        }
        
        assert paypal_service._validate_payment_data(valid_data) is True
        
        # Invalid payment data
        invalid_data = {
            'amount': -10.00,  # Invalid amount
            'currency': 'INVALID',  # Invalid currency
            'description': '',  # Empty description
            'return_url': 'invalid-url',  # Invalid URL
            'cancel_url': 'invalid-url'  # Invalid URL
        }
        
        assert paypal_service._validate_payment_data(invalid_data) is False


class TestPayPalUtilities:
    """Test PayPal utility functions"""
    
    def test_format_amount(self):
        """Test amount formatting"""
        paypal_service = PayPalService()
        
        assert paypal_service._format_amount(49.0) == '49.00'
        assert paypal_service._format_amount(49.99) == '49.99'
        assert paypal_service._format_amount(49.999) == '50.00'
        assert paypal_service._format_amount(0.01) == '0.01'
    
    def test_extract_approval_url(self):
        """Test approval URL extraction"""
        paypal_service = PayPalService()
        
        payment_data = {
            'links': [
                {
                    'href': 'https://api.paypal.com/v1/payments/payment/PAY-123',
                    'rel': 'self',
                    'method': 'GET'
                },
                {
                    'href': 'https://www.paypal.com/cgi-bin/webscr?cmd=_express-checkout&token=EC-123',
                    'rel': 'approval_url',
                    'method': 'REDIRECT'
                }
            ]
        }
        
        approval_url = paypal_service._extract_approval_url(payment_data)
        assert approval_url == 'https://www.paypal.com/cgi-bin/webscr?cmd=_express-checkout&token=EC-123'
    
    def test_extract_approval_url_not_found(self):
        """Test approval URL extraction when not found"""
        paypal_service = PayPalService()
        
        payment_data = {
            'links': [
                {
                    'href': 'https://api.paypal.com/v1/payments/payment/PAY-123',
                    'rel': 'self',
                    'method': 'GET'
                }
            ]
        }
        
        approval_url = paypal_service._extract_approval_url(payment_data)
        assert approval_url is None
    
    def test_parse_webhook_timestamp(self):
        """Test webhook timestamp parsing"""
        paypal_service = PayPalService()
        
        timestamp_str = '2023-01-01T12:00:00Z'
        timestamp = paypal_service._parse_webhook_timestamp(timestamp_str)
        
        assert timestamp is not None
        assert timestamp.year == 2023
        assert timestamp.month == 1
        assert timestamp.day == 1
        assert timestamp.hour == 12
    
    def test_generate_request_id(self):
        """Test request ID generation"""
        paypal_service = PayPalService()
        
        request_id1 = paypal_service._generate_request_id()
        request_id2 = paypal_service._generate_request_id()
        
        assert request_id1 != request_id2
        assert len(request_id1) > 0
        assert len(request_id2) > 0


@pytest.mark.parametrize("amount,currency,expected_valid", [
    (49.00, 'USD', True),
    (0.01, 'USD', True),
    (999.99, 'EUR', True),
    (0.00, 'USD', False),
    (-1.00, 'USD', False),
    (49.00, 'INVALID', False),
    (10000.00, 'USD', False),
])
def test_payment_validation_parametrized(amount, currency, expected_valid):
    """Test payment validation with parametrized inputs"""
    paypal_service = PayPalService()
    
    payment_data = {
        'amount': amount,
        'currency': currency,
        'description': 'Test payment',
        'return_url': 'https://example.com/success',
        'cancel_url': 'https://example.com/cancel'
    }
    
    result = paypal_service._validate_payment_data(payment_data)
    assert result == expected_valid


class TestPayPalMocking:
    """Test PayPal service with comprehensive mocking"""
    
    def test_mock_payment_flow(self, mock_paypal_service):
        """Test complete payment flow with mocked service"""
        # Create payment
        payment = mock_paypal_service.create_payment(
            amount=49.00,
            currency='USD',
            description='Test payment',
            return_url='https://example.com/success',
            cancel_url='https://example.com/cancel'
        )
        
        assert payment is not None
        assert payment['id'] == 'test-payment-id'
        assert payment['approval_url'] == 'https://paypal.com/test-approval'
        
        # Execute payment
        executed_payment = mock_paypal_service.execute_payment(
            payment['id'],
            'test-payer-id'
        )
        
        assert executed_payment is not None
        assert executed_payment['id'] == 'test-payment-id'
        assert executed_payment['state'] == 'approved'
    
    def test_mock_payment_error_handling(self, mock_paypal_service):
        """Test error handling with mocked service"""
        # Mock service failure
        mock_paypal_service.create_payment.side_effect = PayPalError("Service unavailable")
        
        with pytest.raises(PayPalError, match="Service unavailable"):
            mock_paypal_service.create_payment(
                amount=49.00,
                currency='USD',
                description='Test payment',
                return_url='https://example.com/success',
                cancel_url='https://example.com/cancel'
            )
    
    def test_mock_webhook_processing(self, mock_paypal_service):
        """Test webhook processing with mocked service"""
        webhook_data = {
            'id': 'WH-123456789',
            'event_type': 'PAYMENT.SALE.COMPLETED',
            'resource': {
                'id': 'SALE-123456789',
                'parent_payment': 'PAY-123456789'
            }
        }
        
        headers = {
            'PAYPAL-TRANSMISSION-ID': 'test-transmission-id',
            'PAYPAL-TRANSMISSION-SIG': 'test-signature'
        }
        
        # Mock verification success
        mock_paypal_service.verify_webhook.return_value = True
        
        result = mock_paypal_service.verify_webhook(webhook_data, headers)
        assert result is True
        
        mock_paypal_service.verify_webhook.assert_called_once_with(webhook_data, headers)