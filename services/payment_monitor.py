#!/usr/bin/env python3
"""
Payment Processing Monitor for VectorCraft
Real-time payment flow monitoring and alerting system
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor
import json
from database import db
from services.paypal_service import paypal_service
from services.monitoring.alert_manager import alert_manager

class PaymentStatus(Enum):
    INITIATED = "initiated"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"
    REFUNDED = "refunded"

@dataclass
class PaymentHealth:
    """Payment system health metrics"""
    paypal_api_status: str
    paypal_response_time: float
    success_rate: float
    error_rate: float
    pending_transactions: int
    failed_transactions: int
    avg_processing_time: float
    last_successful_transaction: Optional[datetime]
    last_failed_transaction: Optional[datetime]

@dataclass
class PaymentAlert:
    """Payment system alert"""
    alert_type: str
    severity: str
    message: str
    component: str
    timestamp: datetime
    resolved: bool = False

class PaymentMonitor:
    """Advanced payment processing monitoring system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db = db
        self.paypal_service = paypal_service
        self.alert_manager = alert_manager
        self.monitoring_active = False
        self.health_metrics = {}
        self.alert_thresholds = {
            'max_response_time': 5000,  # ms
            'min_success_rate': 0.95,   # 95%
            'max_error_rate': 0.05,     # 5%
            'max_pending_time': 300,    # 5 minutes
            'max_failed_consecutive': 3
        }
        
    def start_monitoring(self):
        """Start payment monitoring service"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.logger.info("Payment monitoring started")
        
        # Start monitoring threads
        threading.Thread(target=self._monitor_payment_health, daemon=True).start()
        threading.Thread(target=self._monitor_pending_transactions, daemon=True).start()
        threading.Thread(target=self._monitor_paypal_api, daemon=True).start()
        
    def stop_monitoring(self):
        """Stop payment monitoring service"""
        self.monitoring_active = False
        self.logger.info("Payment monitoring stopped")
        
    def get_payment_health(self) -> PaymentHealth:
        """Get current payment system health"""
        try:
            # Check PayPal API health
            paypal_health = self._check_paypal_health()
            
            # Get transaction statistics
            recent_transactions = self._get_recent_transactions(hours=24)
            
            total_transactions = len(recent_transactions)
            completed_transactions = [t for t in recent_transactions if t['status'] == 'completed']
            failed_transactions = [t for t in recent_transactions if t['status'] == 'failed']
            pending_transactions = [t for t in recent_transactions if t['status'] == 'pending']
            
            success_rate = len(completed_transactions) / max(total_transactions, 1)
            error_rate = len(failed_transactions) / max(total_transactions, 1)
            
            # Calculate average processing time
            avg_processing_time = self._calculate_avg_processing_time(completed_transactions)
            
            # Get last transaction timestamps
            last_successful = self._get_last_transaction_time(completed_transactions)
            last_failed = self._get_last_transaction_time(failed_transactions)
            
            return PaymentHealth(
                paypal_api_status=paypal_health['status'],
                paypal_response_time=paypal_health['response_time'],
                success_rate=success_rate,
                error_rate=error_rate,
                pending_transactions=len(pending_transactions),
                failed_transactions=len(failed_transactions),
                avg_processing_time=avg_processing_time,
                last_successful_transaction=last_successful,
                last_failed_transaction=last_failed
            )
            
        except Exception as e:
            self.logger.error(f"Error getting payment health: {str(e)}")
            return PaymentHealth(
                paypal_api_status="error",
                paypal_response_time=0.0,
                success_rate=0.0,
                error_rate=1.0,
                pending_transactions=0,
                failed_transactions=0,
                avg_processing_time=0.0,
                last_successful_transaction=None,
                last_failed_transaction=None
            )
    
    def _check_paypal_health(self) -> Dict:
        """Check PayPal API health"""
        try:
            start_time = time.time()
            
            # Try to get access token
            access_token = self.paypal_service._get_access_token()
            
            response_time = (time.time() - start_time) * 1000
            
            if access_token:
                status = "healthy"
            else:
                status = "unhealthy"
                
            return {
                'status': status,
                'response_time': response_time,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"PayPal health check failed: {str(e)}")
            return {
                'status': "error",
                'response_time': 0.0,
                'timestamp': datetime.now(),
                'error': str(e)
            }
    
    def _get_recent_transactions(self, hours: int = 24) -> List[Dict]:
        """Get recent transactions"""
        try:
            start_time = datetime.now() - timedelta(hours=hours)
            
            with self.db.get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM transactions 
                    WHERE created_at >= ?
                    ORDER BY created_at DESC
                ''', (start_time.isoformat(),))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Error getting recent transactions: {str(e)}")
            return []
    
    def _calculate_avg_processing_time(self, transactions: List[Dict]) -> float:
        """Calculate average processing time for completed transactions"""
        if not transactions:
            return 0.0
        
        processing_times = []
        
        for transaction in transactions:
            if transaction['created_at'] and transaction['completed_at']:
                try:
                    created = datetime.fromisoformat(transaction['created_at'].replace('Z', '+00:00'))
                    completed = datetime.fromisoformat(transaction['completed_at'].replace('Z', '+00:00'))
                    processing_time = (completed - created).total_seconds()
                    processing_times.append(processing_time)
                except Exception as e:
                    self.logger.warning(f"Error calculating processing time: {str(e)}")
                    continue
        
        return sum(processing_times) / len(processing_times) if processing_times else 0.0
    
    def _get_last_transaction_time(self, transactions: List[Dict]) -> Optional[datetime]:
        """Get timestamp of last transaction"""
        if not transactions:
            return None
        
        try:
            latest_transaction = max(transactions, key=lambda x: x['created_at'])
            return datetime.fromisoformat(latest_transaction['created_at'].replace('Z', '+00:00'))
        except Exception as e:
            self.logger.error(f"Error getting last transaction time: {str(e)}")
            return None
    
    def _monitor_payment_health(self):
        """Monitor payment system health continuously"""
        while self.monitoring_active:
            try:
                health = self.get_payment_health()
                
                # Check for alerts
                self._check_health_alerts(health)
                
                # Store health metrics
                self.health_metrics[datetime.now()] = asdict(health)
                
                # Clean up old metrics (keep last 24 hours)
                self._cleanup_old_metrics()
                
                # Log health summary
                self.logger.debug(f"Payment health: Success rate: {health.success_rate:.2%}, "
                                f"PayPal API: {health.paypal_api_status}, "
                                f"Pending: {health.pending_transactions}")
                
            except Exception as e:
                self.logger.error(f"Error in payment health monitoring: {str(e)}")
            
            time.sleep(60)  # Check every minute
    
    def _check_health_alerts(self, health: PaymentHealth):
        """Check for alert conditions"""
        try:
            # PayPal API response time alert
            if health.paypal_response_time > self.alert_thresholds['max_response_time']:
                self._create_alert(
                    alert_type="performance",
                    severity="warning",
                    message=f"PayPal API response time high: {health.paypal_response_time:.0f}ms",
                    component="paypal_api"
                )
            
            # Success rate alert
            if health.success_rate < self.alert_thresholds['min_success_rate']:
                self._create_alert(
                    alert_type="reliability",
                    severity="critical",
                    message=f"Payment success rate low: {health.success_rate:.2%}",
                    component="payment_processing"
                )
            
            # Error rate alert
            if health.error_rate > self.alert_thresholds['max_error_rate']:
                self._create_alert(
                    alert_type="error",
                    severity="high",
                    message=f"Payment error rate high: {health.error_rate:.2%}",
                    component="payment_processing"
                )
            
            # PayPal API health alert
            if health.paypal_api_status != "healthy":
                self._create_alert(
                    alert_type="service",
                    severity="critical",
                    message=f"PayPal API unhealthy: {health.paypal_api_status}",
                    component="paypal_api"
                )
            
        except Exception as e:
            self.logger.error(f"Error checking health alerts: {str(e)}")
    
    def _monitor_pending_transactions(self):
        """Monitor pending transactions for timeouts"""
        while self.monitoring_active:
            try:
                # Get pending transactions
                pending_transactions = self._get_pending_transactions()
                
                for transaction in pending_transactions:
                    # Check if transaction is too old
                    created_time = datetime.fromisoformat(transaction['created_at'].replace('Z', '+00:00'))
                    age_seconds = (datetime.now() - created_time).total_seconds()
                    
                    if age_seconds > self.alert_thresholds['max_pending_time']:
                        self._create_alert(
                            alert_type="timeout",
                            severity="warning",
                            message=f"Transaction {transaction['transaction_id']} pending for {age_seconds:.0f}s",
                            component="transaction_processing"
                        )
                        
                        # Try to update transaction status
                        self._investigate_pending_transaction(transaction)
                
            except Exception as e:
                self.logger.error(f"Error monitoring pending transactions: {str(e)}")
            
            time.sleep(30)  # Check every 30 seconds
    
    def _get_pending_transactions(self) -> List[Dict]:
        """Get currently pending transactions"""
        try:
            with self.db.get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM transactions 
                    WHERE status = 'pending'
                    ORDER BY created_at ASC
                ''')
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Error getting pending transactions: {str(e)}")
            return []
    
    def _investigate_pending_transaction(self, transaction: Dict):
        """Investigate a pending transaction"""
        try:
            if transaction['paypal_order_id']:
                # Check PayPal order status
                order_details = self.paypal_service.get_order_details(transaction['paypal_order_id'])
                
                if order_details:
                    if order_details.get('status') == 'APPROVED':
                        # Try to capture the payment
                        capture_result = self.paypal_service.capture_order(transaction['paypal_order_id'])
                        
                        if capture_result and capture_result.get('success'):
                            self.db.update_transaction(
                                transaction['transaction_id'],
                                status='completed',
                                paypal_payment_id=capture_result['payment_id'],
                                completed_at=True
                            )
                            self.logger.info(f"Recovered pending transaction: {transaction['transaction_id']}")
                    
                    elif order_details.get('status') in ['CANCELLED', 'EXPIRED']:
                        # Mark as failed
                        self.db.update_transaction(
                            transaction['transaction_id'],
                            status='failed',
                            error_message=f"PayPal order {order_details.get('status', 'unknown status')}"
                        )
                        self.logger.info(f"Failed pending transaction: {transaction['transaction_id']}")
                
        except Exception as e:
            self.logger.error(f"Error investigating pending transaction {transaction['transaction_id']}: {str(e)}")
    
    def _monitor_paypal_api(self):
        """Monitor PayPal API performance"""
        while self.monitoring_active:
            try:
                # Perform health check
                health_result = self._check_paypal_health()
                
                # Log performance metrics
                self.db.log_performance_metric(
                    metric_type='paypal_api_response_time',
                    endpoint='paypal_oauth',
                    value=health_result['response_time'],
                    status=health_result['status']
                )
                
                # Check for consecutive failures
                if health_result['status'] == 'error':
                    self._handle_paypal_error(health_result)
                
            except Exception as e:
                self.logger.error(f"Error monitoring PayPal API: {str(e)}")
            
            time.sleep(120)  # Check every 2 minutes
    
    def _handle_paypal_error(self, health_result: Dict):
        """Handle PayPal API errors"""
        try:
            # Check for consecutive failures
            recent_failures = self._get_recent_paypal_failures()
            
            if len(recent_failures) >= self.alert_thresholds['max_failed_consecutive']:
                self._create_alert(
                    alert_type="service",
                    severity="critical",
                    message=f"PayPal API failed {len(recent_failures)} consecutive times",
                    component="paypal_api"
                )
            
        except Exception as e:
            self.logger.error(f"Error handling PayPal error: {str(e)}")
    
    def _get_recent_paypal_failures(self) -> List[Dict]:
        """Get recent PayPal API failures"""
        try:
            with self.db.get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM performance_metrics
                    WHERE metric_type = 'paypal_api_response_time'
                    AND status = 'error'
                    AND timestamp >= datetime('now', '-1 hour')
                    ORDER BY timestamp DESC
                ''')
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Error getting recent PayPal failures: {str(e)}")
            return []
    
    def _create_alert(self, alert_type: str, severity: str, message: str, component: str):
        """Create payment system alert"""
        try:
            # Check if similar alert already exists
            existing_alerts = self.alert_manager.get_alerts(resolved=False, limit=10)
            
            for alert in existing_alerts:
                if (alert.get('message') == message and 
                    alert.get('component') == component and
                    not alert.get('resolved')):
                    return  # Don't create duplicate alert
            
            # Create new alert
            alert_id = self.db.create_alert(
                alert_type=f"payment_{alert_type}",
                title=f"Payment System Alert: {severity.upper()}",
                message=message,
                component=component
            )
            
            self.logger.warning(f"Payment alert created: {message}")
            
            # Send critical alerts immediately
            if severity == "critical":
                self.alert_manager.send_alert_email(alert_id)
                
        except Exception as e:
            self.logger.error(f"Error creating payment alert: {str(e)}")
    
    def _cleanup_old_metrics(self):
        """Clean up old health metrics"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            # Remove old metrics
            old_keys = [key for key in self.health_metrics.keys() if key < cutoff_time]
            for key in old_keys:
                del self.health_metrics[key]
                
        except Exception as e:
            self.logger.error(f"Error cleaning up old metrics: {str(e)}")
    
    def get_payment_statistics(self, days: int = 30) -> Dict:
        """Get payment statistics for dashboard"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            with self.db.get_db_connection() as conn:
                # Get basic statistics
                cursor = conn.execute('''
                    SELECT 
                        COUNT(*) as total_transactions,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_transactions,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_transactions,
                        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_transactions,
                        SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) as total_revenue,
                        AVG(CASE WHEN status = 'completed' THEN amount END) as avg_transaction_value
                    FROM transactions
                    WHERE created_at >= ?
                ''', (start_date.isoformat(),))
                
                stats = dict(cursor.fetchone())
                
                # Calculate rates
                total = stats['total_transactions']
                stats['success_rate'] = (stats['completed_transactions'] / max(total, 1)) * 100
                stats['failure_rate'] = (stats['failed_transactions'] / max(total, 1)) * 100
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Error getting payment statistics: {str(e)}")
            return {}
    
    def get_processing_performance(self) -> Dict:
        """Get payment processing performance metrics"""
        try:
            with self.db.get_db_connection() as conn:
                # Get average processing times
                cursor = conn.execute('''
                    SELECT 
                        AVG(value) as avg_response_time,
                        MIN(value) as min_response_time,
                        MAX(value) as max_response_time,
                        COUNT(*) as total_requests
                    FROM performance_metrics
                    WHERE metric_type = 'paypal_api_response_time'
                    AND timestamp >= datetime('now', '-24 hours')
                ''')
                
                performance = dict(cursor.fetchone())
                
                # Get error rate
                cursor = conn.execute('''
                    SELECT 
                        COUNT(CASE WHEN status = 'error' THEN 1 END) * 100.0 / COUNT(*) as error_rate
                    FROM performance_metrics
                    WHERE metric_type = 'paypal_api_response_time'
                    AND timestamp >= datetime('now', '-24 hours')
                ''')
                
                error_data = cursor.fetchone()
                performance['error_rate'] = error_data[0] if error_data and error_data[0] else 0.0
                
                return performance
                
        except Exception as e:
            self.logger.error(f"Error getting processing performance: {str(e)}")
            return {}

# Global payment monitor instance
payment_monitor = PaymentMonitor()