"""
Webhook service for async notifications
"""

import os
import json
import time
import logging
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum

import requests
from celery import Celery
from celery.signals import task_success, task_failure, task_retry

from services.redis_service import redis_service
from services.monitoring.system_logger import system_logger
from database import db

logger = logging.getLogger(__name__)


class WebhookEvent(Enum):
    """Webhook event types"""
    TASK_SUBMITTED = "task.submitted"
    TASK_STARTED = "task.started"
    TASK_PROGRESS = "task.progress"
    TASK_SUCCESS = "task.success"
    TASK_FAILURE = "task.failure"
    TASK_RETRY = "task.retry"
    TASK_CANCELLED = "task.cancelled"
    BATCH_STARTED = "batch.started"
    BATCH_PROGRESS = "batch.progress"
    BATCH_COMPLETED = "batch.completed"
    SYSTEM_HEALTH = "system.health"


@dataclass
class WebhookConfig:
    """Webhook configuration"""
    url: str
    secret: Optional[str] = None
    events: List[WebhookEvent] = None
    headers: Dict[str, str] = None
    timeout: int = 30
    retry_count: int = 3
    retry_delay: int = 5
    enabled: bool = True
    user_id: Optional[int] = None


@dataclass
class WebhookPayload:
    """Webhook payload structure"""
    event: WebhookEvent
    timestamp: str
    task_id: str
    user_id: Optional[int] = None
    data: Dict[str, Any] = None
    metadata: Dict[str, Any] = None


class WebhookService:
    """Service for managing webhooks and notifications"""
    
    def __init__(self):
        self.redis = redis_service
        self.webhook_prefix = 'webhooks'
        self.webhook_log_prefix = 'webhook_logs'
        
        # Default configuration
        self.default_timeout = 30
        self.default_retry_count = 3
        self.default_retry_delay = 5
        self.max_payload_size = 10 * 1024 * 1024  # 10MB
        
        # Rate limiting
        self.rate_limit_window = 3600  # 1 hour
        self.rate_limit_max_requests = 100
        
        logger.info("Webhook service initialized")
    
    def register_webhook(self, user_id: int, config: WebhookConfig) -> str:
        """
        Register a webhook for a user
        
        Args:
            user_id: User ID
            config: Webhook configuration
            
        Returns:
            Webhook ID
        """
        try:
            # Generate webhook ID
            webhook_id = f"webhook_{user_id}_{int(time.time())}"
            
            # Validate URL
            if not self._validate_url(config.url):
                raise ValueError(f"Invalid webhook URL: {config.url}")
            
            # Set default events if not provided
            if not config.events:
                config.events = [
                    WebhookEvent.TASK_SUCCESS,
                    WebhookEvent.TASK_FAILURE,
                    WebhookEvent.BATCH_COMPLETED
                ]
            
            # Store webhook configuration
            webhook_data = {
                'id': webhook_id,
                'user_id': user_id,
                'url': config.url,
                'secret': config.secret,
                'events': [event.value for event in config.events],
                'headers': config.headers or {},
                'timeout': config.timeout,
                'retry_count': config.retry_count,
                'retry_delay': config.retry_delay,
                'enabled': config.enabled,
                'created_at': datetime.utcnow().isoformat(),
                'last_triggered': None,
                'success_count': 0,
                'failure_count': 0
            }
            
            # Store in Redis
            self.redis.set(webhook_id, webhook_data, ttl=86400*30, prefix=self.webhook_prefix)  # 30 days
            
            # Add to user's webhook list
            user_webhooks = self.get_user_webhooks(user_id)
            user_webhooks.append(webhook_id)
            self.redis.set(f"user_{user_id}_webhooks", user_webhooks, 
                          ttl=86400*30, prefix=self.webhook_prefix)
            
            # Log registration
            system_logger.info('webhook_registered', 
                             f'Webhook registered for user {user_id}',
                             user_email=self._get_user_email(user_id),
                             webhook_id=webhook_id,
                             details={
                                 'url': config.url,
                                 'events': [event.value for event in config.events]
                             })
            
            return webhook_id
            
        except Exception as e:
            logger.error(f"Failed to register webhook: {e}")
            raise
    
    def unregister_webhook(self, user_id: int, webhook_id: str) -> bool:
        """
        Unregister a webhook
        
        Args:
            user_id: User ID
            webhook_id: Webhook ID
            
        Returns:
            Success status
        """
        try:
            # Get webhook config
            webhook_data = self.redis.get(webhook_id, prefix=self.webhook_prefix)
            if not webhook_data:
                return False
            
            # Check ownership
            if webhook_data['user_id'] != user_id:
                return False
            
            # Remove from Redis
            self.redis.delete(webhook_id, prefix=self.webhook_prefix)
            
            # Remove from user's webhook list
            user_webhooks = self.get_user_webhooks(user_id)
            if webhook_id in user_webhooks:
                user_webhooks.remove(webhook_id)
                self.redis.set(f"user_{user_id}_webhooks", user_webhooks,
                              ttl=86400*30, prefix=self.webhook_prefix)
            
            # Log unregistration
            system_logger.info('webhook_unregistered', 
                             f'Webhook unregistered for user {user_id}',
                             user_email=self._get_user_email(user_id),
                             webhook_id=webhook_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister webhook: {e}")
            return False
    
    def get_user_webhooks(self, user_id: int) -> List[str]:
        """
        Get user's registered webhooks
        
        Args:
            user_id: User ID
            
        Returns:
            List of webhook IDs
        """
        try:
            user_webhooks = self.redis.get(f"user_{user_id}_webhooks", prefix=self.webhook_prefix)
            return user_webhooks or []
            
        except Exception as e:
            logger.error(f"Failed to get user webhooks: {e}")
            return []
    
    def get_webhook_config(self, webhook_id: str) -> Optional[Dict[str, Any]]:
        """
        Get webhook configuration
        
        Args:
            webhook_id: Webhook ID
            
        Returns:
            Webhook configuration or None
        """
        try:
            return self.redis.get(webhook_id, prefix=self.webhook_prefix)
            
        except Exception as e:
            logger.error(f"Failed to get webhook config: {e}")
            return None
    
    def enable_webhook(self, user_id: int, webhook_id: str) -> bool:
        """Enable a webhook"""
        return self._update_webhook_status(user_id, webhook_id, True)
    
    def disable_webhook(self, user_id: int, webhook_id: str) -> bool:
        """Disable a webhook"""
        return self._update_webhook_status(user_id, webhook_id, False)
    
    def trigger_webhook(self, webhook_id: str, payload: WebhookPayload) -> bool:
        """
        Trigger a webhook
        
        Args:
            webhook_id: Webhook ID
            payload: Webhook payload
            
        Returns:
            Success status
        """
        try:
            # Get webhook config
            webhook_config = self.get_webhook_config(webhook_id)
            if not webhook_config or not webhook_config.get('enabled', True):
                return False
            
            # Check if event is subscribed
            if payload.event.value not in webhook_config.get('events', []):
                return False
            
            # Check rate limiting
            if not self._check_rate_limit(webhook_id):
                logger.warning(f"Rate limit exceeded for webhook {webhook_id}")
                return False
            
            # Prepare payload
            webhook_payload = self._prepare_payload(payload)
            
            # Sign payload if secret is provided
            signature = None
            if webhook_config.get('secret'):
                signature = self._sign_payload(webhook_payload, webhook_config['secret'])
            
            # Send webhook
            success = self._send_webhook(
                url=webhook_config['url'],
                payload=webhook_payload,
                signature=signature,
                headers=webhook_config.get('headers', {}),
                timeout=webhook_config.get('timeout', self.default_timeout),
                retry_count=webhook_config.get('retry_count', self.default_retry_count),
                retry_delay=webhook_config.get('retry_delay', self.default_retry_delay)
            )
            
            # Update webhook statistics
            self._update_webhook_stats(webhook_id, success)
            
            # Log webhook trigger
            system_logger.info('webhook_triggered', 
                             f'Webhook triggered: {webhook_id}',
                             webhook_id=webhook_id,
                             task_id=payload.task_id,
                             details={
                                 'event': payload.event.value,
                                 'success': success,
                                 'url': webhook_config['url']
                             })
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to trigger webhook {webhook_id}: {e}")
            return False
    
    def trigger_event(self, event: WebhookEvent, task_id: str, user_id: Optional[int] = None,
                     data: Dict[str, Any] = None, metadata: Dict[str, Any] = None) -> List[str]:
        """
        Trigger webhooks for an event
        
        Args:
            event: Webhook event
            task_id: Task ID
            user_id: User ID (optional)
            data: Event data
            metadata: Event metadata
            
        Returns:
            List of successfully triggered webhook IDs
        """
        try:
            # Create payload
            payload = WebhookPayload(
                event=event,
                timestamp=datetime.utcnow().isoformat(),
                task_id=task_id,
                user_id=user_id,
                data=data or {},
                metadata=metadata or {}
            )
            
            triggered_webhooks = []
            
            # Get webhooks to trigger
            if user_id:
                # User-specific webhooks
                user_webhooks = self.get_user_webhooks(user_id)
                
                for webhook_id in user_webhooks:
                    if self.trigger_webhook(webhook_id, payload):
                        triggered_webhooks.append(webhook_id)
            
            # Global webhooks (admin notifications, etc.)
            # This could be extended to support system-wide webhooks
            
            return triggered_webhooks
            
        except Exception as e:
            logger.error(f"Failed to trigger event {event.value}: {e}")
            return []
    
    def get_webhook_logs(self, webhook_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get webhook trigger logs
        
        Args:
            webhook_id: Webhook ID
            limit: Maximum number of logs to return
            
        Returns:
            List of webhook logs
        """
        try:
            logs = self.redis.list_pop(f"logs_{webhook_id}", prefix=self.webhook_log_prefix)
            return logs or []
            
        except Exception as e:
            logger.error(f"Failed to get webhook logs: {e}")
            return []
    
    def test_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Test a webhook endpoint
        
        Args:
            webhook_id: Webhook ID
            
        Returns:
            Test result
        """
        try:
            # Get webhook config
            webhook_config = self.get_webhook_config(webhook_id)
            if not webhook_config:
                return {'success': False, 'error': 'Webhook not found'}
            
            # Create test payload
            test_payload = WebhookPayload(
                event=WebhookEvent.SYSTEM_HEALTH,
                timestamp=datetime.utcnow().isoformat(),
                task_id='test_task_id',
                user_id=webhook_config['user_id'],
                data={'test': True, 'message': 'This is a test webhook'},
                metadata={'webhook_test': True}
            )
            
            # Trigger webhook
            success = self.trigger_webhook(webhook_id, test_payload)
            
            return {
                'success': success,
                'webhook_id': webhook_id,
                'url': webhook_config['url'],
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to test webhook {webhook_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _validate_url(self, url: str) -> bool:
        """Validate webhook URL"""
        try:
            # Basic URL validation
            if not url.startswith(('http://', 'https://')):
                return False
            
            # Additional validation could be added here
            return True
            
        except Exception:
            return False
    
    def _check_rate_limit(self, webhook_id: str) -> bool:
        """Check webhook rate limiting"""
        try:
            rate_key = f"rate_{webhook_id}"
            current_count = self.redis.get(rate_key, prefix=self.webhook_prefix) or 0
            
            if current_count >= self.rate_limit_max_requests:
                return False
            
            # Update count
            if current_count == 0:
                self.redis.set(rate_key, 1, ttl=self.rate_limit_window, prefix=self.webhook_prefix)
            else:
                self.redis.increment(rate_key, prefix=self.webhook_prefix)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to check rate limit: {e}")
            return True  # Allow on error
    
    def _prepare_payload(self, payload: WebhookPayload) -> Dict[str, Any]:
        """Prepare webhook payload for sending"""
        return {
            'event': payload.event.value,
            'timestamp': payload.timestamp,
            'task_id': payload.task_id,
            'user_id': payload.user_id,
            'data': payload.data,
            'metadata': payload.metadata
        }
    
    def _sign_payload(self, payload: Dict[str, Any], secret: str) -> str:
        """Sign webhook payload with HMAC"""
        try:
            payload_json = json.dumps(payload, sort_keys=True)
            signature = hmac.new(
                secret.encode('utf-8'),
                payload_json.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return f"sha256={signature}"
            
        except Exception as e:
            logger.error(f"Failed to sign payload: {e}")
            return ""
    
    def _send_webhook(self, url: str, payload: Dict[str, Any], signature: Optional[str] = None,
                     headers: Dict[str, str] = None, timeout: int = 30,
                     retry_count: int = 3, retry_delay: int = 5) -> bool:
        """Send webhook HTTP request"""
        try:
            # Prepare headers
            request_headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'VectorCraft-Webhook/1.0'
            }
            
            if headers:
                request_headers.update(headers)
            
            if signature:
                request_headers['X-Webhook-Signature'] = signature
            
            # Convert payload to JSON
            payload_json = json.dumps(payload)
            
            # Check payload size
            if len(payload_json.encode('utf-8')) > self.max_payload_size:
                logger.error(f"Webhook payload too large: {len(payload_json)} bytes")
                return False
            
            # Send request with retries
            for attempt in range(retry_count):
                try:
                    response = requests.post(
                        url,
                        data=payload_json,
                        headers=request_headers,
                        timeout=timeout
                    )
                    
                    # Check response
                    if response.status_code in [200, 201, 202, 204]:
                        return True
                    else:
                        logger.warning(f"Webhook returned status {response.status_code}: {response.text}")
                        
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Webhook request failed (attempt {attempt + 1}): {e}")
                    
                    if attempt < retry_count - 1:
                        time.sleep(retry_delay)
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to send webhook: {e}")
            return False
    
    def _update_webhook_stats(self, webhook_id: str, success: bool):
        """Update webhook statistics"""
        try:
            webhook_config = self.get_webhook_config(webhook_id)
            if not webhook_config:
                return
            
            # Update counters
            if success:
                webhook_config['success_count'] = webhook_config.get('success_count', 0) + 1
            else:
                webhook_config['failure_count'] = webhook_config.get('failure_count', 0) + 1
            
            # Update last triggered time
            webhook_config['last_triggered'] = datetime.utcnow().isoformat()
            
            # Store updated config
            self.redis.set(webhook_id, webhook_config, ttl=86400*30, prefix=self.webhook_prefix)
            
        except Exception as e:
            logger.error(f"Failed to update webhook stats: {e}")
    
    def _update_webhook_status(self, user_id: int, webhook_id: str, enabled: bool) -> bool:
        """Update webhook enabled status"""
        try:
            webhook_config = self.get_webhook_config(webhook_id)
            if not webhook_config or webhook_config['user_id'] != user_id:
                return False
            
            webhook_config['enabled'] = enabled
            webhook_config['updated_at'] = datetime.utcnow().isoformat()
            
            self.redis.set(webhook_id, webhook_config, ttl=86400*30, prefix=self.webhook_prefix)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update webhook status: {e}")
            return False
    
    def _get_user_email(self, user_id: int) -> Optional[str]:
        """Get user email for logging"""
        try:
            user = db.get_user_by_id(user_id)
            return user['email'] if user else None
        except:
            return None


# Global webhook service instance
webhook_service = WebhookService()


# Celery signal handlers for automatic webhook triggers
@task_success.connect
def task_success_handler(sender=None, task_id=None, result=None, retries=None, einfo=None, **kwargs):
    """Handle task success event"""
    try:
        # Extract user ID from result if available
        user_id = None
        if isinstance(result, dict) and 'user_id' in result:
            user_id = result['user_id']
        
        # Trigger webhook
        webhook_service.trigger_event(
            event=WebhookEvent.TASK_SUCCESS,
            task_id=task_id,
            user_id=user_id,
            data=result,
            metadata={'sender': sender, 'retries': retries}
        )
        
    except Exception as e:
        logger.error(f"Failed to handle task success webhook: {e}")


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, einfo=None, **kwargs):
    """Handle task failure event"""
    try:
        # Trigger webhook
        webhook_service.trigger_event(
            event=WebhookEvent.TASK_FAILURE,
            task_id=task_id,
            data={'error': str(exception), 'traceback': str(einfo)},
            metadata={'sender': sender}
        )
        
    except Exception as e:
        logger.error(f"Failed to handle task failure webhook: {e}")


@task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, einfo=None, **kwargs):
    """Handle task retry event"""
    try:
        # Trigger webhook
        webhook_service.trigger_event(
            event=WebhookEvent.TASK_RETRY,
            task_id=task_id,
            data={'reason': str(reason), 'traceback': str(einfo)},
            metadata={'sender': sender}
        )
        
    except Exception as e:
        logger.error(f"Failed to handle task retry webhook: {e}")


if __name__ == '__main__':
    # Test webhook service
    logger.info("Testing webhook service...")
    
    # Test webhook registration
    config = WebhookConfig(
        url='https://httpbin.org/post',
        events=[WebhookEvent.TASK_SUCCESS, WebhookEvent.TASK_FAILURE]
    )
    
    webhook_id = webhook_service.register_webhook(1, config)
    print(f"Registered webhook: {webhook_id}")
    
    # Test webhook trigger
    payload = WebhookPayload(
        event=WebhookEvent.TASK_SUCCESS,
        timestamp=datetime.utcnow().isoformat(),
        task_id='test_task_123',
        user_id=1,
        data={'result': 'success', 'quality_score': 0.95}
    )
    
    success = webhook_service.trigger_webhook(webhook_id, payload)
    print(f"Webhook trigger success: {success}")
    
    # Test webhook test
    test_result = webhook_service.test_webhook(webhook_id)
    print(f"Webhook test result: {test_result}")
    
    logger.info("Webhook service test completed!")