#!/usr/bin/env python3
"""
System Health Monitor Service
Handles health checks for all system components
"""

import time
import requests
import sqlite3
import smtplib
import os
from datetime import datetime
from database import db


class HealthMonitor:
    """Monitor system health across all components"""
    
    def __init__(self):
        self.components = [
            'database',
            'paypal_api',
            'email_service',
            'application'
        ]
    
    def check_all_components(self):
        """Run health checks on all components"""
        results = {}
        
        for component in self.components:
            try:
                result = self._check_component(component)
                results[component] = result
                
                # Log health check result
                db.log_health_check(
                    component=component,
                    status=result['status'],
                    response_time=result.get('response_time'),
                    error_message=result.get('error_message')
                )
                
            except Exception as e:
                error_result = {
                    'status': 'critical',
                    'error_message': str(e),
                    'response_time': None,
                    'checked_at': datetime.now().isoformat()
                }
                results[component] = error_result
                
                # Log failed health check
                db.log_health_check(
                    component=component,
                    status='critical',
                    error_message=str(e)
                )
        
        return results
    
    def _check_component(self, component):
        """Check individual component health"""
        start_time = time.time()
        
        if component == 'database':
            return self._check_database(start_time)
        elif component == 'paypal_api':
            return self._check_paypal_api(start_time)
        elif component == 'email_service':
            return self._check_email_service(start_time)
        elif component == 'application':
            return self._check_application(start_time)
        else:
            raise ValueError(f"Unknown component: {component}")
    
    def _check_database(self, start_time):
        """Check database connectivity and performance"""
        try:
            # Test basic database connectivity
            with sqlite3.connect(db.db_path, timeout=5) as conn:
                cursor = conn.execute('SELECT 1')
                cursor.fetchone()
            
            response_time = int((time.time() - start_time) * 1000)
            
            # Check if response time is acceptable
            if response_time > 1000:  # > 1 second
                status = 'warning'
                error_message = f'Slow database response: {response_time}ms'
            else:
                status = 'healthy'
                error_message = None
            
            return {
                'status': status,
                'response_time': response_time,
                'error_message': error_message,
                'checked_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'critical',
                'error_message': f'Database error: {str(e)}',
                'response_time': None,
                'checked_at': datetime.now().isoformat()
            }
    
    def _check_paypal_api(self, start_time):
        """Check PayPal API connectivity"""
        try:
            # Import PayPal service
            from services.paypal_service import paypal_service
            
            # Check if PayPal service is configured
            if not hasattr(paypal_service, 'client_id') or not paypal_service.client_id:
                return {
                    'status': 'warning',
                    'error_message': 'PayPal not configured',
                    'response_time': None,
                    'checked_at': datetime.now().isoformat()
                }
            
            # Test PayPal API connectivity with a simple auth check
            # This is a lightweight check that doesn't create orders
            auth_url = f"{paypal_service.base_url}/v1/oauth2/token"
            
            response = requests.post(
                auth_url,
                headers={'Accept': 'application/json'},
                auth=(paypal_service.client_id, paypal_service.client_secret),
                data={'grant_type': 'client_credentials'},
                timeout=10
            )
            
            response_time = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                if response_time > 5000:  # > 5 seconds
                    status = 'warning'
                    error_message = f'Slow PayPal API response: {response_time}ms'
                else:
                    status = 'healthy'
                    error_message = None
            else:
                status = 'critical'
                error_message = f'PayPal API error: HTTP {response.status_code}'
            
            return {
                'status': status,
                'response_time': response_time,
                'error_message': error_message,
                'checked_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'critical',
                'error_message': f'PayPal API error: {str(e)}',
                'response_time': None,
                'checked_at': datetime.now().isoformat()
            }
    
    def _check_email_service(self, start_time):
        """Check email service (SMTP) connectivity"""
        try:
            # Import email service
            from services.email_service import email_service
            
            # Check SMTP configuration
            smtp_server = os.getenv('SMTP_SERVER')
            smtp_port = int(os.getenv('SMTP_PORT', 587))
            smtp_username = os.getenv('SMTP_USERNAME')
            smtp_password = os.getenv('SMTP_PASSWORD')
            
            if not all([smtp_server, smtp_username, smtp_password]):
                return {
                    'status': 'warning',
                    'error_message': 'Email service not configured',
                    'response_time': None,
                    'checked_at': datetime.now().isoformat()
                }
            
            # Test SMTP connectivity
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.quit()
            
            response_time = int((time.time() - start_time) * 1000)
            
            if response_time > 8000:  # > 8 seconds
                status = 'warning'
                error_message = f'Slow email service response: {response_time}ms'
            else:
                status = 'healthy'
                error_message = None
            
            return {
                'status': status,
                'response_time': response_time,
                'error_message': error_message,
                'checked_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'critical',
                'error_message': f'Email service error: {str(e)}',
                'response_time': None,
                'checked_at': datetime.now().isoformat()
            }
    
    def _check_application(self, start_time):
        """Check application server health"""
        try:
            import psutil
            
            # Check memory usage
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            response_time = int((time.time() - start_time) * 1000)
            
            # Determine status based on resource usage
            if memory.percent > 90 or disk.percent > 90:
                status = 'critical'
                error_message = f'High resource usage - Memory: {memory.percent}%, Disk: {disk.percent}%'
            elif memory.percent > 80 or disk.percent > 80:
                status = 'warning'
                error_message = f'Resource usage warning - Memory: {memory.percent}%, Disk: {disk.percent}%'
            else:
                status = 'healthy'
                error_message = None
            
            return {
                'status': status,
                'response_time': response_time,
                'error_message': error_message,
                'memory_percent': memory.percent,
                'disk_percent': disk.percent,
                'checked_at': datetime.now().isoformat()
            }
            
        except ImportError:
            # psutil not available, do basic check
            response_time = int((time.time() - start_time) * 1000)
            return {
                'status': 'healthy',
                'response_time': response_time,
                'error_message': None,
                'checked_at': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'critical',
                'error_message': f'Application health check error: {str(e)}',
                'response_time': None,
                'checked_at': datetime.now().isoformat()
            }
    
    def get_overall_status(self):
        """Get overall system health status"""
        health_results = db.get_health_status(hours=1)
        
        if not health_results:
            return {
                'status': 'unknown',
                'message': 'No recent health checks available'
            }
        
        # Determine overall status
        statuses = [result['status'] for result in health_results]
        
        if 'critical' in statuses:
            overall_status = 'critical'
            message = f"{statuses.count('critical')} critical issues detected"
        elif 'warning' in statuses:
            overall_status = 'warning'
            message = f"{statuses.count('warning')} warnings detected"
        else:
            overall_status = 'healthy'
            message = 'All systems operational'
        
        return {
            'status': overall_status,
            'message': message,
            'components': health_results,
            'last_check': max(result['last_check'] for result in health_results)
        }


# Global health monitor instance
health_monitor = HealthMonitor()

if __name__ == '__main__':
    # Test health monitoring
    print("🏥 Testing VectorCraft Health Monitor...")
    
    results = health_monitor.check_all_components()
    
    print("\n📊 Health Check Results:")
    for component, result in results.items():
        status_emoji = {
            'healthy': '🟢',
            'warning': '🟡', 
            'critical': '🔴'
        }.get(result['status'], '⚪')
        
        print(f"{status_emoji} {component}: {result['status']}")
        if result.get('response_time'):
            print(f"   Response time: {result['response_time']}ms")
        if result.get('error_message'):
            print(f"   Error: {result['error_message']}")
    
    print(f"\n🏥 Overall System Status:")
    overall = health_monitor.get_overall_status()
    status_emoji = {
        'healthy': '🟢',
        'warning': '🟡',
        'critical': '🔴',
        'unknown': '⚪'
    }.get(overall['status'], '⚪')
    
    print(f"{status_emoji} {overall['status'].upper()}: {overall['message']}")