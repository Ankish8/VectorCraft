#!/usr/bin/env python3
"""
Alert Manager Service
Intelligent alerting system for critical issues
"""

import time
from datetime import datetime, timedelta
from database import db
from services.monitoring.system_logger import system_logger


class AlertManager:
    """Manage intelligent alerts for system monitoring"""
    
    # Alert types
    CRITICAL = 'critical'
    WARNING = 'warning'
    INFO = 'info'
    
    # Alert thresholds
    THRESHOLDS = {
        'high_error_rate': {
            'errors_per_5min': 10,
            'errors_per_hour': 50
        },
        'revenue_drop': {
            'percentage_drop': 50,
            'time_window_hours': 24
        },
        'payment_failure_rate': {
            'failure_rate': 0.1,  # 10%
            'min_transactions': 5
        },
        'system_response_time': {
            'warning_ms': 3000,
            'critical_ms': 10000
        }
    }
    
    def __init__(self):
        self.email_service = None
        self._load_email_service()
    
    def _load_email_service(self):
        """Load email service for sending alerts"""
        try:
            from services.email_service import email_service
            self.email_service = email_service
        except ImportError:
            system_logger.warning('alert_manager', 'Email service not available for alerts')
    
    def check_all_conditions(self):
        """Check all alert conditions and create alerts as needed"""
        alerts_created = []
        
        # Check error rate conditions
        error_rate_alert = self._check_error_rate()
        if error_rate_alert:
            alerts_created.append(error_rate_alert)
        
        # Check system health conditions
        health_alerts = self._check_system_health()
        alerts_created.extend(health_alerts)
        
        # Check payment conditions
        payment_alerts = self._check_payment_conditions()
        alerts_created.extend(payment_alerts)
        
        # Check revenue conditions
        revenue_alert = self._check_revenue_drop()
        if revenue_alert:
            alerts_created.append(revenue_alert)
        
        # Send critical alerts immediately
        for alert in alerts_created:
            if alert['type'] == self.CRITICAL:
                self._send_immediate_alert(alert)
        
        return alerts_created
    
    def _check_error_rate(self):
        """Check for high error rates"""
        # Check 5-minute error rate
        recent_errors = db.get_system_logs(
            level='ERROR', 
            hours=1,  # Look at last hour
            limit=100
        )
        
        # Count errors in last 5 minutes
        five_min_ago = datetime.now() - timedelta(minutes=5)
        recent_errors_5min = [
            log for log in recent_errors 
            if datetime.fromisoformat(log['created_at'].replace('Z', '')) >= five_min_ago
        ]
        
        if len(recent_errors_5min) >= self.THRESHOLDS['high_error_rate']['errors_per_5min']:
            alert_id = db.create_alert(
                alert_type=self.CRITICAL,
                title='High Error Rate Detected',
                message=f'{len(recent_errors_5min)} errors in last 5 minutes',
                component='system'
            )
            
            system_logger.critical(
                'alert_manager', 
                f'High error rate alert created: {len(recent_errors_5min)} errors in 5 minutes',
                details={'alert_id': alert_id, 'error_count': len(recent_errors_5min)}
            )
            
            return {
                'id': alert_id,
                'type': self.CRITICAL,
                'title': 'High Error Rate Detected',
                'message': f'{len(recent_errors_5min)} errors in last 5 minutes',
                'component': 'system'
            }
        
        return None
    
    def _check_system_health(self):
        """Check system health for critical issues"""
        alerts = []
        
        # Get recent health status
        health_status = db.get_health_status(hours=1)
        
        for component_health in health_status:
            component = component_health['component']
            status = component_health['status']
            error_message = component_health.get('error_message')
            
            if status == 'critical':
                # Check if we already have an unresolved alert for this component
                existing_alerts = db.get_alerts(resolved=False, limit=10)
                component_has_alert = any(
                    alert['component'] == component and 'critical' in alert['message'].lower()
                    for alert in existing_alerts
                )
                
                if not component_has_alert:
                    alert_id = db.create_alert(
                        alert_type=self.CRITICAL,
                        title=f'{component.title()} Service Critical',
                        message=f'{component} is in critical state: {error_message or "Unknown error"}',
                        component=component
                    )
                    
                    system_logger.critical(
                        'alert_manager',
                        f'Critical system health alert for {component}',
                        details={'alert_id': alert_id, 'component': component, 'error': error_message}
                    )
                    
                    alerts.append({
                        'id': alert_id,
                        'type': self.CRITICAL,
                        'title': f'{component.title()} Service Critical',
                        'message': f'{component} is in critical state: {error_message or "Unknown error"}',
                        'component': component
                    })
        
        return alerts
    
    def _check_payment_conditions(self):
        """Check payment-related conditions"""
        alerts = []
        
        # Get recent transactions
        recent_transactions = db.get_transactions(limit=50)
        
        if len(recent_transactions) >= self.THRESHOLDS['payment_failure_rate']['min_transactions']:
            # Calculate failure rate
            failed_transactions = [
                tx for tx in recent_transactions 
                if tx['status'] in ['failed', 'error']
            ]
            
            failure_rate = len(failed_transactions) / len(recent_transactions)
            
            if failure_rate >= self.THRESHOLDS['payment_failure_rate']['failure_rate']:
                alert_id = db.create_alert(
                    alert_type=self.CRITICAL,
                    title='High Payment Failure Rate',
                    message=f'{failure_rate:.1%} payment failure rate ({len(failed_transactions)}/{len(recent_transactions)} transactions)',
                    component='payment'
                )
                
                system_logger.critical(
                    'alert_manager',
                    f'High payment failure rate: {failure_rate:.1%}',
                    details={
                        'alert_id': alert_id,
                        'failure_rate': failure_rate,
                        'failed_count': len(failed_transactions),
                        'total_count': len(recent_transactions)
                    }
                )
                
                alerts.append({
                    'id': alert_id,
                    'type': self.CRITICAL,
                    'title': 'High Payment Failure Rate',
                    'message': f'{failure_rate:.1%} payment failure rate',
                    'component': 'payment'
                })
        
        return alerts
    
    def _check_revenue_drop(self):
        """Check for significant revenue drops"""
        # Get transactions from last 24 hours and previous 24 hours
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        previous_24h = last_24h - timedelta(hours=24)
        
        # Current period transactions
        current_transactions = db.get_transactions(
            date_from=last_24h.isoformat(),
            status='completed'
        )
        
        # Previous period transactions (this is a simplified check)
        # In a real implementation, you'd want to compare with the same day last week
        # or use a more sophisticated baseline
        
        current_revenue = sum(
            float(tx['amount'] or 0) 
            for tx in current_transactions 
            if tx['status'] == 'completed'
        )
        
        # For now, use a simple threshold of $100 as minimum expected daily revenue
        # In production, this would be based on historical data
        expected_daily_revenue = 100.0
        
        if current_revenue < expected_daily_revenue * (1 - self.THRESHOLDS['revenue_drop']['percentage_drop'] / 100):
            alert_id = db.create_alert(
                alert_type=self.WARNING,
                title='Revenue Drop Detected',
                message=f'Daily revenue is ${current_revenue:.2f}, below expected ${expected_daily_revenue:.2f}',
                component='payment'
            )
            
            system_logger.warning(
                'alert_manager',
                f'Revenue drop detected: ${current_revenue:.2f}',
                details={
                    'alert_id': alert_id,
                    'current_revenue': current_revenue,
                    'expected_revenue': expected_daily_revenue
                }
            )
            
            return {
                'id': alert_id,
                'type': self.WARNING,
                'title': 'Revenue Drop Detected',
                'message': f'Daily revenue is ${current_revenue:.2f}, below expected',
                'component': 'payment'
            }
        
        return None
    
    def _send_immediate_alert(self, alert):
        """Send immediate email alert for critical issues"""
        if not self.email_service:
            system_logger.error('alert_manager', 'Cannot send alert email - email service not available')
            return False
        
        try:
            # Prepare alert email
            subject = f"🚨 VectorCraft Alert: {alert['title']}"
            
            message = f"""
CRITICAL ALERT: {alert['title']}

Component: {alert.get('component', 'Unknown')}
Message: {alert['message']}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Alert ID: {alert['id']}

This is an automated alert from VectorCraft monitoring system.
Please investigate immediately.

---
VectorCraft Monitoring System
"""
            
            # Send to admin email
            admin_email = self.email_service.admin_email
            result = self.email_service.send_admin_notification(subject, message)
            
            if result:
                # Mark alert as emailed
                db.update_transaction(alert['id'], email_sent=True)
                system_logger.info(
                    'alert_manager',
                    f'Critical alert email sent for alert {alert["id"]}',
                    details={'alert_id': alert['id'], 'recipient': admin_email}
                )
                return True
            else:
                system_logger.error(
                    'alert_manager',
                    f'Failed to send critical alert email for alert {alert["id"]}',
                    details={'alert_id': alert['id']}
                )
                return False
                
        except Exception as e:
            system_logger.error(
                'alert_manager',
                f'Exception sending critical alert email: {str(e)}',
                details={'alert_id': alert['id'], 'error': str(e)}
            )
            return False
    
    def resolve_alert(self, alert_id, resolver_email=None):
        """Resolve an alert"""
        try:
            db.resolve_alert(alert_id)
            
            system_logger.info(
                'alert_manager',
                f'Alert {alert_id} resolved',
                user_email=resolver_email,
                details={'alert_id': alert_id}
            )
            
            return True
            
        except Exception as e:
            system_logger.error(
                'alert_manager',
                f'Failed to resolve alert {alert_id}: {str(e)}',
                details={'alert_id': alert_id, 'error': str(e)}
            )
            return False
    
    def get_active_alerts(self):
        """Get all unresolved alerts"""
        return db.get_alerts(resolved=False)
    
    def get_alert_summary(self):
        """Get summary of alert status"""
        active_alerts = self.get_active_alerts()
        
        critical_count = sum(1 for alert in active_alerts if alert['type'] == self.CRITICAL)
        warning_count = sum(1 for alert in active_alerts if alert['type'] == self.WARNING)
        
        return {
            'total_active': len(active_alerts),
            'critical': critical_count,
            'warning': warning_count,
            'info': len(active_alerts) - critical_count - warning_count,
            'needs_attention': critical_count > 0
        }


# Global alert manager instance
alert_manager = AlertManager()

if __name__ == '__main__':
    # Test alert manager
    print("🚨 Testing VectorCraft Alert Manager...")
    
    # Check all conditions
    alerts = alert_manager.check_all_conditions()
    print(f"✅ Alert check complete. {len(alerts)} new alerts created.")
    
    # Get alert summary
    summary = alert_manager.get_alert_summary()
    print(f"\n📊 Alert Summary:")
    print(f"   Total active: {summary['total_active']}")
    print(f"   Critical: {summary['critical']}")
    print(f"   Warning: {summary['warning']}")
    print(f"   Needs attention: {'Yes' if summary['needs_attention'] else 'No'}")
    
    # Show active alerts
    active_alerts = alert_manager.get_active_alerts()
    if active_alerts:
        print(f"\n🚨 Active Alerts:")
        for alert in active_alerts[:5]:  # Show first 5
            print(f"   {alert['type'].upper()}: {alert['title']}")
    else:
        print("\n✅ No active alerts")