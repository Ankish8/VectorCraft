#!/usr/bin/env python3
"""
Security Middleware for VectorCraft
Integrates security monitoring into the application request/response cycle
"""

from flask import request, session, jsonify, g
from functools import wraps
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from services.security_service import security_service

logger = logging.getLogger(__name__)

class SecurityMiddleware:
    """Security middleware to monitor and protect application requests"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the security middleware with Flask app"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        app.teardown_appcontext(self.teardown)
        
        # Add security headers
        @app.after_request
        def add_security_headers(response):
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:;"
            return response
    
    def before_request(self):
        """Security checks before processing each request"""
        try:
            # Start request timing
            g.start_time = time.time()
            
            # Get request information
            source_ip = self.get_client_ip()
            endpoint = request.endpoint
            method = request.method
            user_agent = request.user_agent.string
            
            # Store request info in g for later use
            g.security_info = {
                'source_ip': source_ip,
                'endpoint': endpoint,
                'method': method,
                'user_agent': user_agent,
                'timestamp': datetime.utcnow()
            }
            
            # Skip security checks for static files
            if endpoint and endpoint.startswith('static'):
                return
            
            # Check if IP is blocked
            if security_service.check_ip_blocked(source_ip):
                security_service.log_security_event(
                    'BLOCKED_IP_ACCESS',
                    'HIGH',
                    source_ip,
                    session.get('user_id'),
                    'Access attempt from blocked IP',
                    {'endpoint': endpoint, 'method': method}
                )
                return jsonify({'error': 'Access denied'}), 403
            
            # Check rate limiting
            if not security_service.check_rate_limit(source_ip, endpoint or 'unknown'):
                security_service.log_security_event(
                    'RATE_LIMIT_EXCEEDED',
                    'MEDIUM',
                    source_ip,
                    session.get('user_id'),
                    f'Rate limit exceeded for endpoint {endpoint}',
                    {'endpoint': endpoint, 'method': method}
                )
                return jsonify({'error': 'Rate limit exceeded'}), 429
            
            # Check for suspicious patterns
            self.check_suspicious_patterns(source_ip, endpoint, method, user_agent)
            
            # Log request for audit trail
            user_id = session.get('user_id') or session.get('admin_user')
            if user_id and endpoint:
                security_service.log_audit_event(
                    user_id,
                    f'{method}_{endpoint}',
                    endpoint or 'unknown',
                    source_ip,
                    user_agent,
                    True,  # Will be updated in after_request if needed
                    {'request_size': request.content_length or 0}
                )
            
        except Exception as e:
            logger.error(f"Security middleware before_request error: {e}")
            # Don't block request on middleware errors
    
    def after_request(self, response):
        """Security checks after processing each request"""
        try:
            # Calculate request duration
            duration = time.time() - getattr(g, 'start_time', time.time())
            
            security_info = getattr(g, 'security_info', {})
            source_ip = security_info.get('source_ip')
            endpoint = security_info.get('endpoint')
            method = security_info.get('method')
            
            # Log slow requests as potential DoS attempts
            if duration > 5.0:  # 5 seconds threshold
                security_service.log_security_event(
                    'SLOW_REQUEST',
                    'MEDIUM',
                    source_ip,
                    session.get('user_id'),
                    f'Slow request detected: {duration:.2f}s',
                    {
                        'endpoint': endpoint,
                        'method': method,
                        'duration': duration,
                        'status_code': response.status_code
                    }
                )
            
            # Log failed requests (4xx, 5xx status codes)
            if response.status_code >= 400:
                severity = 'HIGH' if response.status_code >= 500 else 'MEDIUM'
                security_service.log_security_event(
                    'REQUEST_ERROR',
                    severity,
                    source_ip,
                    session.get('user_id'),
                    f'Request failed with status {response.status_code}',
                    {
                        'endpoint': endpoint,
                        'method': method,
                        'status_code': response.status_code,
                        'duration': duration
                    }
                )
            
            # Update audit log with response status
            user_id = session.get('user_id') or session.get('admin_user')
            if user_id and endpoint:
                # Note: In a real implementation, you'd want to update the existing audit log entry
                # rather than creating a new one. This is a simplified approach.
                pass
            
        except Exception as e:
            logger.error(f"Security middleware after_request error: {e}")
        
        return response
    
    def teardown(self, exception):
        """Clean up after request"""
        try:
            # Clean up any request-specific security data
            if hasattr(g, 'security_info'):
                del g.security_info
            if hasattr(g, 'start_time'):
                del g.start_time
        except Exception as e:
            logger.error(f"Security middleware teardown error: {e}")
    
    def get_client_ip(self) -> str:
        """Get the real client IP address"""
        # Check for forwarded headers (when behind proxy/load balancer)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        # Fallback to remote_addr
        return request.remote_addr or 'unknown'
    
    def check_suspicious_patterns(self, source_ip: str, endpoint: str, method: str, user_agent: str):
        """Check for suspicious request patterns"""
        try:
            # Check for common attack patterns in user agent
            suspicious_user_agents = [
                'sqlmap', 'nikto', 'nmap', 'masscan', 'dirbuster', 'gobuster',
                'burp', 'owasp zap', 'acunetix', 'nessus', 'openvas'
            ]
            
            if user_agent and any(pattern in user_agent.lower() for pattern in suspicious_user_agents):
                security_service.log_security_event(
                    'SUSPICIOUS_USER_AGENT',
                    'HIGH',
                    source_ip,
                    session.get('user_id'),
                    f'Suspicious user agent detected: {user_agent}',
                    {'endpoint': endpoint, 'method': method, 'user_agent': user_agent}
                )
                
                # Add threat indicator
                security_service.add_threat_indicator(
                    'user_agent',
                    user_agent,
                    'HIGH',
                    'Suspicious user agent associated with security tools'
                )
            
            # Check for path traversal attempts
            if endpoint and any(pattern in endpoint for pattern in ['../', '..\\']):
                security_service.log_security_event(
                    'PATH_TRAVERSAL_ATTEMPT',
                    'HIGH',
                    source_ip,
                    session.get('user_id'),
                    f'Path traversal attempt detected: {endpoint}',
                    {'endpoint': endpoint, 'method': method}
                )
            
            # Check for SQL injection patterns in query parameters
            query_string = request.query_string.decode('utf-8', errors='ignore')
            sql_patterns = [
                'union select', 'drop table', 'insert into', 'delete from',
                'update set', 'alter table', 'create table', 'or 1=1',
                'and 1=1', 'having 1=1', 'order by', 'group by'
            ]
            
            if query_string and any(pattern in query_string.lower() for pattern in sql_patterns):
                security_service.log_security_event(
                    'SQL_INJECTION_ATTEMPT',
                    'HIGH',
                    source_ip,
                    session.get('user_id'),
                    f'SQL injection attempt detected: {query_string[:100]}',
                    {'endpoint': endpoint, 'method': method, 'query_string': query_string}
                )
            
            # Check for XSS patterns
            xss_patterns = [
                '<script', 'javascript:', 'onerror=', 'onload=', 'onclick=',
                'onmouseover=', 'alert(', 'prompt(', 'confirm('
            ]
            
            if query_string and any(pattern in query_string.lower() for pattern in xss_patterns):
                security_service.log_security_event(
                    'XSS_ATTEMPT',
                    'HIGH',
                    source_ip,
                    session.get('user_id'),
                    f'XSS attempt detected: {query_string[:100]}',
                    {'endpoint': endpoint, 'method': method, 'query_string': query_string}
                )
            
        except Exception as e:
            logger.error(f"Error checking suspicious patterns: {e}")

def require_permission(resource: str, permission: str):
    """Decorator to require specific permissions for accessing resources"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id')
            if not user_id:
                security_service.log_security_event(
                    'UNAUTHORIZED_ACCESS',
                    'MEDIUM',
                    request.remote_addr,
                    None,
                    f'Unauthorized access attempt to {resource}',
                    {'resource': resource, 'permission': permission}
                )
                return jsonify({'error': 'Authentication required'}), 401
            
            if not security_service.check_permission(user_id, resource, permission):
                security_service.log_security_event(
                    'PERMISSION_DENIED',
                    'MEDIUM',
                    request.remote_addr,
                    user_id,
                    f'Permission denied for {resource}:{permission}',
                    {'resource': resource, 'permission': permission}
                )
                return jsonify({'error': 'Permission denied'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_security_event(event_type: str, severity: str = 'LOW', description: str = '', details: Dict = None):
    """Decorator to log security events for specific functions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            source_ip = request.remote_addr
            user_id = session.get('user_id')
            
            try:
                result = f(*args, **kwargs)
                
                # Log successful execution
                security_service.log_security_event(
                    event_type,
                    severity,
                    source_ip,
                    user_id,
                    description or f'Function {f.__name__} executed successfully',
                    details or {}
                )
                
                return result
                
            except Exception as e:
                # Log failed execution
                security_service.log_security_event(
                    event_type + '_FAILED',
                    'HIGH',
                    source_ip,
                    user_id,
                    f'Function {f.__name__} failed: {str(e)}',
                    {'error': str(e), 'function': f.__name__}
                )
                raise
                
        return decorated_function
    return decorator

def validate_file_upload(f):
    """Decorator to validate file uploads using the security service"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save file temporarily for validation
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # Validate file using security service
            is_valid, sanitized_path, error_message = security_service.validate_and_sanitize_upload(
                temp_path, file.filename
            )
            
            if not is_valid:
                source_ip = request.remote_addr
                user_id = session.get('user_id')
                
                security_service.log_security_event(
                    'MALICIOUS_FILE_UPLOAD',
                    'HIGH',
                    source_ip,
                    user_id,
                    f'Malicious file upload blocked: {error_message}',
                    {'filename': file.filename, 'error': error_message}
                )
                
                return jsonify({'error': f'File validation failed: {error_message}'}), 400
            
            # Replace original file with sanitized version
            if sanitized_path:
                os.replace(sanitized_path, temp_path)
            
            # Add sanitized file path to request context
            g.validated_file_path = temp_path
            
            return f(*args, **kwargs)
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    return decorated_function

# Global security middleware instance
security_middleware = SecurityMiddleware()