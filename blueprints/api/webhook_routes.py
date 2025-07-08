"""
Webhook API routes
"""

import logging
from typing import Dict, Any

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from services.webhook_service import webhook_service, WebhookConfig, WebhookEvent
from services.api_service import api_service
from services.monitoring.system_logger import system_logger

logger = logging.getLogger(__name__)

# Create blueprint
webhook_bp = Blueprint('webhook_api', __name__, url_prefix='/api/webhooks')


@webhook_bp.route('', methods=['POST'])
@login_required
@api_service.rate_limit(limit=10, window=3600)  # 10 registrations per hour
def register_webhook():
    """
    Register a new webhook
    
    Request body:
    {
        "url": "https://your-app.com/webhook",
        "secret": "optional_secret_key",
        "events": ["task.success", "task.failure"],
        "headers": {"Authorization": "Bearer token"},
        "timeout": 30,
        "retry_count": 3,
        "retry_delay": 5
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400
        
        # Parse events
        events = []
        if 'events' in data:
            try:
                events = [WebhookEvent(event) for event in data['events']]
            except ValueError as e:
                return jsonify({'error': f'Invalid event: {e}'}), 400
        
        # Create webhook config
        config = WebhookConfig(
            url=data['url'],
            secret=data.get('secret'),
            events=events,
            headers=data.get('headers'),
            timeout=data.get('timeout', 30),
            retry_count=data.get('retry_count', 3),
            retry_delay=data.get('retry_delay', 5),
            enabled=data.get('enabled', True)
        )
        
        # Register webhook
        webhook_id = webhook_service.register_webhook(int(current_user.id), config)
        
        return jsonify({
            'success': True,
            'webhook_id': webhook_id,
            'message': 'Webhook registered successfully'
        })
        
    except Exception as e:
        logger.error(f"Failed to register webhook: {e}")
        return jsonify({'error': str(e)}), 500


@webhook_bp.route('', methods=['GET'])
@login_required
@api_service.rate_limit(limit=50, window=3600)  # 50 requests per hour
def list_webhooks():
    """
    List user's webhooks
    """
    try:
        user_id = int(current_user.id)
        webhook_ids = webhook_service.get_user_webhooks(user_id)
        
        webhooks = []
        for webhook_id in webhook_ids:
            config = webhook_service.get_webhook_config(webhook_id)
            if config:
                # Remove sensitive data
                safe_config = {
                    'id': webhook_id,
                    'url': config['url'],
                    'events': config['events'],
                    'enabled': config['enabled'],
                    'created_at': config['created_at'],
                    'last_triggered': config.get('last_triggered'),
                    'success_count': config.get('success_count', 0),
                    'failure_count': config.get('failure_count', 0),
                    'timeout': config.get('timeout', 30),
                    'retry_count': config.get('retry_count', 3)
                }
                webhooks.append(safe_config)
        
        return jsonify({
            'success': True,
            'webhooks': webhooks,
            'count': len(webhooks)
        })
        
    except Exception as e:
        logger.error(f"Failed to list webhooks: {e}")
        return jsonify({'error': str(e)}), 500


@webhook_bp.route('/<webhook_id>', methods=['GET'])
@login_required
@api_service.rate_limit(limit=100, window=3600)  # 100 requests per hour
def get_webhook(webhook_id: str):
    """
    Get webhook details
    """
    try:
        config = webhook_service.get_webhook_config(webhook_id)
        
        if not config:
            return jsonify({'error': 'Webhook not found'}), 404
        
        # Check ownership
        if config['user_id'] != int(current_user.id):
            return jsonify({'error': 'Access denied'}), 403
        
        # Remove sensitive data
        safe_config = {
            'id': webhook_id,
            'url': config['url'],
            'events': config['events'],
            'enabled': config['enabled'],
            'created_at': config['created_at'],
            'last_triggered': config.get('last_triggered'),
            'success_count': config.get('success_count', 0),
            'failure_count': config.get('failure_count', 0),
            'timeout': config.get('timeout', 30),
            'retry_count': config.get('retry_count', 3),
            'retry_delay': config.get('retry_delay', 5)
        }
        
        return jsonify({
            'success': True,
            'webhook': safe_config
        })
        
    except Exception as e:
        logger.error(f"Failed to get webhook: {e}")
        return jsonify({'error': str(e)}), 500


@webhook_bp.route('/<webhook_id>', methods=['PUT'])
@login_required
@api_service.rate_limit(limit=20, window=3600)  # 20 updates per hour
def update_webhook(webhook_id: str):
    """
    Update webhook configuration
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        config = webhook_service.get_webhook_config(webhook_id)
        
        if not config:
            return jsonify({'error': 'Webhook not found'}), 404
        
        # Check ownership
        if config['user_id'] != int(current_user.id):
            return jsonify({'error': 'Access denied'}), 403
        
        # Update configuration
        if 'url' in data:
            config['url'] = data['url']
        
        if 'secret' in data:
            config['secret'] = data['secret']
        
        if 'events' in data:
            try:
                config['events'] = [WebhookEvent(event).value for event in data['events']]
            except ValueError as e:
                return jsonify({'error': f'Invalid event: {e}'}), 400
        
        if 'headers' in data:
            config['headers'] = data['headers']
        
        if 'timeout' in data:
            config['timeout'] = data['timeout']
        
        if 'retry_count' in data:
            config['retry_count'] = data['retry_count']
        
        if 'retry_delay' in data:
            config['retry_delay'] = data['retry_delay']
        
        if 'enabled' in data:
            config['enabled'] = data['enabled']
        
        # Update timestamp
        from datetime import datetime
        config['updated_at'] = datetime.utcnow().isoformat()
        
        # Store updated config
        webhook_service.redis.set(webhook_id, config, ttl=86400*30, 
                                prefix=webhook_service.webhook_prefix)
        
        # Log update
        system_logger.info('webhook_updated', 
                          f'Webhook updated by {current_user.username}',
                          user_email=current_user.email,
                          webhook_id=webhook_id)
        
        return jsonify({
            'success': True,
            'webhook_id': webhook_id,
            'message': 'Webhook updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Failed to update webhook: {e}")
        return jsonify({'error': str(e)}), 500


@webhook_bp.route('/<webhook_id>', methods=['DELETE'])
@login_required
@api_service.rate_limit(limit=10, window=3600)  # 10 deletions per hour
def delete_webhook(webhook_id: str):
    """
    Delete webhook
    """
    try:
        success = webhook_service.unregister_webhook(int(current_user.id), webhook_id)
        
        if success:
            return jsonify({
                'success': True,
                'webhook_id': webhook_id,
                'message': 'Webhook deleted successfully'
            })
        else:
            return jsonify({'error': 'Webhook not found or access denied'}), 404
        
    except Exception as e:
        logger.error(f"Failed to delete webhook: {e}")
        return jsonify({'error': str(e)}), 500


@webhook_bp.route('/<webhook_id>/enable', methods=['POST'])
@login_required
@api_service.rate_limit(limit=20, window=3600)  # 20 requests per hour
def enable_webhook(webhook_id: str):
    """
    Enable webhook
    """
    try:
        success = webhook_service.enable_webhook(int(current_user.id), webhook_id)
        
        if success:
            return jsonify({
                'success': True,
                'webhook_id': webhook_id,
                'message': 'Webhook enabled successfully'
            })
        else:
            return jsonify({'error': 'Webhook not found or access denied'}), 404
        
    except Exception as e:
        logger.error(f"Failed to enable webhook: {e}")
        return jsonify({'error': str(e)}), 500


@webhook_bp.route('/<webhook_id>/disable', methods=['POST'])
@login_required
@api_service.rate_limit(limit=20, window=3600)  # 20 requests per hour
def disable_webhook(webhook_id: str):
    """
    Disable webhook
    """
    try:
        success = webhook_service.disable_webhook(int(current_user.id), webhook_id)
        
        if success:
            return jsonify({
                'success': True,
                'webhook_id': webhook_id,
                'message': 'Webhook disabled successfully'
            })
        else:
            return jsonify({'error': 'Webhook not found or access denied'}), 404
        
    except Exception as e:
        logger.error(f"Failed to disable webhook: {e}")
        return jsonify({'error': str(e)}), 500


@webhook_bp.route('/<webhook_id>/test', methods=['POST'])
@login_required
@api_service.rate_limit(limit=10, window=3600)  # 10 tests per hour
def test_webhook(webhook_id: str):
    """
    Test webhook endpoint
    """
    try:
        config = webhook_service.get_webhook_config(webhook_id)
        
        if not config:
            return jsonify({'error': 'Webhook not found'}), 404
        
        # Check ownership
        if config['user_id'] != int(current_user.id):
            return jsonify({'error': 'Access denied'}), 403
        
        # Test webhook
        test_result = webhook_service.test_webhook(webhook_id)
        
        return jsonify({
            'success': True,
            'test_result': test_result
        })
        
    except Exception as e:
        logger.error(f"Failed to test webhook: {e}")
        return jsonify({'error': str(e)}), 500


@webhook_bp.route('/<webhook_id>/logs', methods=['GET'])
@login_required
@api_service.rate_limit(limit=30, window=3600)  # 30 requests per hour
def get_webhook_logs(webhook_id: str):
    """
    Get webhook logs
    """
    try:
        config = webhook_service.get_webhook_config(webhook_id)
        
        if not config:
            return jsonify({'error': 'Webhook not found'}), 404
        
        # Check ownership
        if config['user_id'] != int(current_user.id):
            return jsonify({'error': 'Access denied'}), 403
        
        # Get logs
        limit = request.args.get('limit', 100, type=int)
        logs = webhook_service.get_webhook_logs(webhook_id, limit)
        
        return jsonify({
            'success': True,
            'logs': logs,
            'count': len(logs)
        })
        
    except Exception as e:
        logger.error(f"Failed to get webhook logs: {e}")
        return jsonify({'error': str(e)}), 500


@webhook_bp.route('/events', methods=['GET'])
@login_required
@api_service.rate_limit(limit=50, window=3600)  # 50 requests per hour
def get_webhook_events():
    """
    Get available webhook events
    """
    try:
        events = []
        for event in WebhookEvent:
            events.append({
                'value': event.value,
                'name': event.name,
                'description': _get_event_description(event)
            })
        
        return jsonify({
            'success': True,
            'events': events
        })
        
    except Exception as e:
        logger.error(f"Failed to get webhook events: {e}")
        return jsonify({'error': str(e)}), 500


def _get_event_description(event: WebhookEvent) -> str:
    """Get description for webhook event"""
    descriptions = {
        WebhookEvent.TASK_SUBMITTED: "Triggered when a new task is submitted",
        WebhookEvent.TASK_STARTED: "Triggered when a task starts processing",
        WebhookEvent.TASK_PROGRESS: "Triggered when task progress is updated",
        WebhookEvent.TASK_SUCCESS: "Triggered when a task completes successfully",
        WebhookEvent.TASK_FAILURE: "Triggered when a task fails",
        WebhookEvent.TASK_RETRY: "Triggered when a task is retried",
        WebhookEvent.TASK_CANCELLED: "Triggered when a task is cancelled",
        WebhookEvent.BATCH_STARTED: "Triggered when a batch process starts",
        WebhookEvent.BATCH_PROGRESS: "Triggered when batch progress is updated",
        WebhookEvent.BATCH_COMPLETED: "Triggered when a batch process completes",
        WebhookEvent.SYSTEM_HEALTH: "Triggered for system health notifications"
    }
    
    return descriptions.get(event, "No description available")


# Error handlers for webhook blueprint
@webhook_bp.errorhandler(400)
def bad_request(error):
    """Handle bad request errors"""
    return jsonify({
        'error': 'Bad request',
        'message': 'Invalid request format or parameters'
    }), 400


@webhook_bp.errorhandler(403)
def forbidden(error):
    """Handle forbidden errors"""
    return jsonify({
        'error': 'Forbidden',
        'message': 'Access denied'
    }), 403


@webhook_bp.errorhandler(404)
def not_found(error):
    """Handle not found errors"""
    return jsonify({
        'error': 'Not found',
        'message': 'Webhook not found'
    }), 404


@webhook_bp.errorhandler(429)
def rate_limit_exceeded(error):
    """Handle rate limit exceeded errors"""
    return jsonify({
        'error': 'Rate limit exceeded',
        'message': 'Too many requests. Please try again later.'
    }), 429


@webhook_bp.errorhandler(500)
def internal_server_error(error):
    """Handle internal server errors"""
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500