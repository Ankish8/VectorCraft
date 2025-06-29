#!/usr/bin/env python3
"""
System Logger Service
Centralized logging for monitoring and debugging
"""

import json
from datetime import datetime
from database import db


class SystemLogger:
    """Centralized system logger for monitoring"""
    
    # Log levels
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'
    
    def __init__(self):
        self.components = {
            'auth': 'Authentication System',
            'payment': 'Payment Processing',
            'vectorization': 'Vector Processing',
            'email': 'Email Service',
            'database': 'Database Operations',
            'api': 'API Endpoints',
            'admin': 'Admin Dashboard',
            'health': 'Health Monitoring',
            'security': 'Security Events'
        }
    
    def log(self, level, component, message, details=None, user_email=None, transaction_id=None):
        """Log a system event"""
        try:
            # Store in database
            db.log_system_event(
                level=level,
                component=component,
                message=message,
                details=details,
                user_email=user_email,
                transaction_id=transaction_id
            )
            
            # Also log to console for development
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            level_emoji = {
                'DEBUG': '🔍',
                'INFO': 'ℹ️',
                'WARNING': '⚠️',
                'ERROR': '❌',
                'CRITICAL': '🚨'
            }.get(level, '📝')
            
            log_entry = f"{timestamp} {level_emoji} [{level}] {component}: {message}"
            if user_email:
                log_entry += f" (User: {user_email})"
            if transaction_id:
                log_entry += f" (TX: {transaction_id})"
            
            print(log_entry)
            
            if details:
                print(f"   Details: {json.dumps(details, indent=2)}")
                
        except Exception as e:
            # Fallback logging to console if database fails
            print(f"❌ Logging failed: {e}")
            print(f"   Original log: [{level}] {component}: {message}")
    
    def debug(self, component, message, **kwargs):
        """Log debug message"""
        self.log(self.DEBUG, component, message, **kwargs)
    
    def info(self, component, message, **kwargs):
        """Log info message"""
        self.log(self.INFO, component, message, **kwargs)
    
    def warning(self, component, message, **kwargs):
        """Log warning message"""
        self.log(self.WARNING, component, message, **kwargs)
    
    def error(self, component, message, **kwargs):
        """Log error message"""
        self.log(self.ERROR, component, message, **kwargs)
    
    def critical(self, component, message, **kwargs):
        """Log critical message"""
        self.log(self.CRITICAL, component, message, **kwargs)
    
    # Specific logging methods for common events
    def log_user_action(self, action, user_email, details=None):
        """Log user action"""
        self.info('auth', f"User action: {action}", user_email=user_email, details=details)
    
    def log_payment_event(self, event, transaction_id, amount=None, user_email=None, details=None):
        """Log payment-related event"""
        message = f"Payment {event}"
        if amount:
            message += f" (${amount:.2f})"
        
        self.info('payment', message, 
                 user_email=user_email, 
                 transaction_id=transaction_id, 
                 details=details)
    
    def log_payment_error(self, error, transaction_id, user_email=None, details=None):
        """Log payment error"""
        self.error('payment', f"Payment failed: {error}", 
                  user_email=user_email, 
                  transaction_id=transaction_id, 
                  details=details)
    
    def log_vectorization_event(self, event, user_email, processing_time=None, strategy=None, details=None):
        """Log vectorization event"""
        message = f"Vectorization {event}"
        if processing_time:
            message += f" ({processing_time:.2f}s)"
        if strategy:
            message += f" using {strategy}"
        
        event_details = details or {}
        if processing_time:
            event_details['processing_time'] = processing_time
        if strategy:
            event_details['strategy'] = strategy
        
        self.info('vectorization', message, user_email=user_email, details=event_details)
    
    def log_email_event(self, event, recipient, email_type=None, success=True, error=None):
        """Log email sending event"""
        if success:
            message = f"Email sent: {event}"
            if email_type:
                message += f" ({email_type})"
            self.info('email', message, user_email=recipient)
        else:
            message = f"Email failed: {event}"
            if error:
                message += f" - {error}"
            self.error('email', message, user_email=recipient, details={'error': error})
    
    def log_security_event(self, event, details=None, user_email=None, severity='warning'):
        """Log security-related event"""
        level = getattr(self, severity.upper(), self.WARNING)
        self.log(level, 'security', f"Security event: {event}", 
                details=details, user_email=user_email)
    
    def log_admin_action(self, action, admin_user, details=None):
        """Log admin dashboard action"""
        self.info('admin', f"Admin action: {action}", user_email=admin_user, details=details)
    
    def log_health_event(self, component, status, details=None):
        """Log health monitoring event"""
        if status == 'critical':
            level = self.ERROR
        elif status == 'warning':
            level = self.WARNING
        else:
            level = self.INFO
        
        self.log(level, 'health', f"Health check: {component} is {status}", details=details)
    
    def log_api_request(self, endpoint, method, user_email=None, response_time=None, status_code=None, error=None):
        """Log API request"""
        message = f"API {method} {endpoint}"
        
        details = {}
        if response_time:
            details['response_time'] = response_time
            message += f" ({response_time:.3f}s)"
        if status_code:
            details['status_code'] = status_code
            message += f" -> {status_code}"
        
        if error:
            details['error'] = error
            self.error('api', message, user_email=user_email, details=details)
        elif status_code and status_code >= 400:
            self.warning('api', message, user_email=user_email, details=details)
        else:
            self.info('api', message, user_email=user_email, details=details)
    
    def get_recent_logs(self, hours=24, level=None, component=None, limit=100):
        """Get recent system logs"""
        return db.get_system_logs(limit=limit, level=level, component=component, hours=hours)
    
    def get_error_summary(self, hours=24):
        """Get summary of recent errors"""
        error_logs = db.get_system_logs(limit=100, level='ERROR', hours=hours)
        critical_logs = db.get_system_logs(limit=100, level='CRITICAL', hours=hours)
        
        all_errors = error_logs + critical_logs
        
        # Group by component
        component_errors = {}
        for log in all_errors:
            component = log['component']
            if component not in component_errors:
                component_errors[component] = []
            component_errors[component].append(log)
        
        return {
            'total_errors': len(all_errors),
            'by_component': {
                component: len(errors) 
                for component, errors in component_errors.items()
            },
            'recent_errors': all_errors[:10]  # Most recent 10 errors
        }
    
    def analyze_error_patterns(self, hours=24):
        """Analyze error patterns for alerting"""
        logs = self.get_recent_logs(hours=hours, level='ERROR')
        
        # Count errors by component and time
        error_counts = {}
        for log in logs:
            component = log['component']
            error_counts[component] = error_counts.get(component, 0) + 1
        
        # Identify high error rates (>10 errors in time period)
        high_error_components = {
            component: count 
            for component, count in error_counts.items() 
            if count > 10
        }
        
        return {
            'total_errors': len(logs),
            'error_rate': len(logs) / hours,  # errors per hour
            'high_error_components': high_error_components,
            'needs_alert': len(logs) > 20 or len(high_error_components) > 0
        }


# Global system logger instance
system_logger = SystemLogger()

if __name__ == '__main__':
    # Test system logging
    print("📝 Testing VectorCraft System Logger...")
    
    # Test different log levels
    system_logger.debug('test', 'Debug message for testing')
    system_logger.info('test', 'Info message for testing')
    system_logger.warning('test', 'Warning message for testing')
    system_logger.error('test', 'Error message for testing')
    
    # Test specific event logging
    system_logger.log_user_action('login', 'test@example.com', {'ip': '127.0.0.1'})
    system_logger.log_payment_event('completed', 'TEST123', 49.99, 'test@example.com')
    system_logger.log_vectorization_event('completed', 'test@example.com', 2.5, 'vtracer_high_fidelity')
    system_logger.log_email_event('credentials sent', 'test@example.com', 'welcome', True)
    
    # Test error analysis
    error_summary = system_logger.get_error_summary(hours=1)
    print(f"\n📊 Error Summary: {error_summary['total_errors']} total errors")
    
    recent_logs = system_logger.get_recent_logs(hours=1, limit=5)
    print(f"\n📋 Recent Logs ({len(recent_logs)} entries):")
    for log in recent_logs:
        print(f"   {log['level']} - {log['component']}: {log['message']}")