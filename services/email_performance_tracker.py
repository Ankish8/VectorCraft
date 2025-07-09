#!/usr/bin/env python3
"""
Email Performance Tracker Service
Advanced email performance monitoring and analytics for VectorCraft
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import threading
import time
import uuid

logger = logging.getLogger(__name__)

@dataclass
class EmailMetric:
    """Email performance metric data class"""
    timestamp: datetime
    email_id: str
    template_id: Optional[str]
    recipient_email: str
    subject: str
    email_type: str
    status: str
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    bounced_at: Optional[datetime] = None
    complaint_at: Optional[datetime] = None
    delivery_time: Optional[float] = None  # seconds
    open_time: Optional[float] = None  # seconds after delivery
    click_time: Optional[float] = None  # seconds after open
    smtp_response_time: Optional[float] = None  # seconds
    retry_count: int = 0
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class PerformanceSummary:
    """Performance summary data class"""
    total_emails: int
    sent_count: int
    delivered_count: int
    opened_count: int
    clicked_count: int
    bounced_count: int
    complaint_count: int
    failed_count: int
    delivery_rate: float
    open_rate: float
    click_rate: float
    bounce_rate: float
    complaint_rate: float
    avg_delivery_time: float
    avg_open_time: float
    avg_click_time: float
    avg_smtp_response_time: float
    
class EmailPerformanceTracker:
    """Advanced email performance tracking and analytics service"""
    
    def __init__(self, db_instance=None):
        self.logger = logging.getLogger(__name__)
        
        # Import database
        if db_instance:
            self.db = db_instance
        else:
            from database import db
            self.db = db
        
        # Performance metrics cache
        self.metrics_cache = {}
        self.cache_expiry = 300  # 5 minutes
        
        # Real-time tracking
        self.active_emails = {}  # email_id -> EmailMetric
        self.tracking_enabled = True
        
        # Performance thresholds
        self.thresholds = {
            'delivery_rate_warning': 95.0,
            'delivery_rate_critical': 90.0,
            'bounce_rate_warning': 5.0,
            'bounce_rate_critical': 10.0,
            'complaint_rate_warning': 0.1,
            'complaint_rate_critical': 0.5,
            'avg_delivery_time_warning': 30.0,  # seconds
            'avg_delivery_time_critical': 60.0,  # seconds
        }
        
        # Start background monitoring
        self.monitoring_thread = threading.Thread(target=self._background_monitor, daemon=True)
        self.monitoring_thread.start()
        
        self.logger.info("Email Performance Tracker initialized")
    
    def track_email_sent(self, email_id: str, template_id: str, recipient_email: str, 
                        subject: str, email_type: str, metadata: Dict[str, Any] = None) -> str:
        """Track email sending event"""
        try:
            metric = EmailMetric(
                timestamp=datetime.now(),
                email_id=email_id,
                template_id=template_id,
                recipient_email=recipient_email,
                subject=subject,
                email_type=email_type,
                status='sent',
                sent_at=datetime.now(),
                metadata=metadata
            )
            
            # Store in active emails for real-time tracking
            self.active_emails[email_id] = metric
            
            # Log to database
            self._log_performance_event(metric, 'sent')
            
            self.logger.debug(f"Email sent tracked: {email_id} to {recipient_email}")
            return email_id
            
        except Exception as e:
            self.logger.error(f"Error tracking email sent: {str(e)}")
            return None
    
    def track_email_delivered(self, email_id: str, delivery_time: float = None, 
                             smtp_response_time: float = None) -> bool:
        """Track email delivery event"""
        try:
            if email_id in self.active_emails:
                metric = self.active_emails[email_id]
                metric.delivered_at = datetime.now()
                metric.status = 'delivered'
                metric.delivery_time = delivery_time
                metric.smtp_response_time = smtp_response_time
                
                # Update database
                self._log_performance_event(metric, 'delivered')
                
                self.logger.debug(f"Email delivery tracked: {email_id}")
                return True
            else:
                self.logger.warning(f"Email not found in active tracking: {email_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error tracking email delivery: {str(e)}")
            return False
    
    def track_email_opened(self, email_id: str, open_time: float = None) -> bool:
        """Track email open event"""
        try:
            if email_id in self.active_emails:
                metric = self.active_emails[email_id]
                metric.opened_at = datetime.now()
                metric.open_time = open_time
                
                # Update database
                self._log_performance_event(metric, 'opened')
                
                self.logger.debug(f"Email open tracked: {email_id}")
                return True
            else:
                # Try to find in database and track
                return self._track_event_from_db(email_id, 'opened')
                
        except Exception as e:
            self.logger.error(f"Error tracking email open: {str(e)}")
            return False
    
    def track_email_clicked(self, email_id: str, click_time: float = None, 
                           link_url: str = None) -> bool:
        """Track email click event"""
        try:
            if email_id in self.active_emails:
                metric = self.active_emails[email_id]
                metric.clicked_at = datetime.now()
                metric.click_time = click_time
                
                # Add click metadata
                if not metric.metadata:
                    metric.metadata = {}
                metric.metadata['clicked_link'] = link_url
                
                # Update database
                self._log_performance_event(metric, 'clicked')
                
                self.logger.debug(f"Email click tracked: {email_id}")
                return True
            else:
                return self._track_event_from_db(email_id, 'clicked', {'link_url': link_url})
                
        except Exception as e:
            self.logger.error(f"Error tracking email click: {str(e)}")
            return False
    
    def track_email_bounced(self, email_id: str, bounce_type: str = 'hard', 
                           bounce_reason: str = None) -> bool:
        """Track email bounce event"""
        try:
            if email_id in self.active_emails:
                metric = self.active_emails[email_id]
                metric.bounced_at = datetime.now()
                metric.status = 'bounced'
                metric.error_type = bounce_type
                metric.error_message = bounce_reason
                
                # Update database
                self._log_performance_event(metric, 'bounced')
                
                self.logger.debug(f"Email bounce tracked: {email_id}")
                return True
            else:
                return self._track_event_from_db(email_id, 'bounced', {
                    'bounce_type': bounce_type,
                    'bounce_reason': bounce_reason
                })
                
        except Exception as e:
            self.logger.error(f"Error tracking email bounce: {str(e)}")
            return False
    
    def track_email_complaint(self, email_id: str, complaint_type: str = 'spam', 
                             complaint_reason: str = None) -> bool:
        """Track email complaint event"""
        try:
            if email_id in self.active_emails:
                metric = self.active_emails[email_id]
                metric.complaint_at = datetime.now()
                metric.error_type = complaint_type
                metric.error_message = complaint_reason
                
                # Update database
                self._log_performance_event(metric, 'complaint')
                
                self.logger.debug(f"Email complaint tracked: {email_id}")
                return True
            else:
                return self._track_event_from_db(email_id, 'complaint', {
                    'complaint_type': complaint_type,
                    'complaint_reason': complaint_reason
                })
                
        except Exception as e:
            self.logger.error(f"Error tracking email complaint: {str(e)}")
            return False
    
    def track_email_failed(self, email_id: str, error_type: str = 'smtp_error', 
                          error_message: str = None, retry_count: int = 0) -> bool:
        """Track email failure event"""
        try:
            if email_id in self.active_emails:
                metric = self.active_emails[email_id]
                metric.status = 'failed'
                metric.error_type = error_type
                metric.error_message = error_message
                metric.retry_count = retry_count
                
                # Update database
                self._log_performance_event(metric, 'failed')
                
                self.logger.debug(f"Email failure tracked: {email_id}")
                return True
            else:
                return self._track_event_from_db(email_id, 'failed', {
                    'error_type': error_type,
                    'error_message': error_message,
                    'retry_count': retry_count
                })
                
        except Exception as e:
            self.logger.error(f"Error tracking email failure: {str(e)}")
            return False
    
    def get_performance_summary(self, hours: int = 24, template_id: str = None, 
                               email_type: str = None) -> PerformanceSummary:
        """Get performance summary for specified time period"""
        try:
            cache_key = f"summary_{hours}_{template_id}_{email_type}"
            
            # Check cache
            if cache_key in self.metrics_cache:
                cached_data, timestamp = self.metrics_cache[cache_key]
                if (datetime.now() - timestamp).seconds < self.cache_expiry:
                    return cached_data
            
            # Get email performance data from database
            performance_data = self.db.get_email_performance_summary(hours)
            
            # Calculate metrics
            total_emails = performance_data.get('total_emails', 0)
            sent_count = performance_data.get('delivered', 0)
            delivered_count = performance_data.get('delivered', 0)
            opened_count = performance_data.get('opened', 0)
            clicked_count = performance_data.get('clicked', 0)
            bounced_count = performance_data.get('bounced', 0)
            complaint_count = performance_data.get('complained', 0)
            failed_count = performance_data.get('failed', 0)
            
            # Calculate rates
            delivery_rate = (delivered_count / max(total_emails, 1)) * 100
            open_rate = (opened_count / max(delivered_count, 1)) * 100
            click_rate = (clicked_count / max(opened_count, 1)) * 100
            bounce_rate = (bounced_count / max(total_emails, 1)) * 100
            complaint_rate = (complaint_count / max(total_emails, 1)) * 100
            
            # Get timing metrics
            timing_data = self._get_timing_metrics(hours, template_id, email_type)
            
            summary = PerformanceSummary(
                total_emails=total_emails,
                sent_count=sent_count,
                delivered_count=delivered_count,
                opened_count=opened_count,
                clicked_count=clicked_count,
                bounced_count=bounced_count,
                complaint_count=complaint_count,
                failed_count=failed_count,
                delivery_rate=delivery_rate,
                open_rate=open_rate,
                click_rate=click_rate,
                bounce_rate=bounce_rate,
                complaint_rate=complaint_rate,
                avg_delivery_time=timing_data.get('avg_delivery_time', 0),
                avg_open_time=timing_data.get('avg_open_time', 0),
                avg_click_time=timing_data.get('avg_click_time', 0),
                avg_smtp_response_time=timing_data.get('avg_smtp_response_time', 0)
            )
            
            # Cache result
            self.metrics_cache[cache_key] = (summary, datetime.now())
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting performance summary: {str(e)}")
            return PerformanceSummary(
                total_emails=0, sent_count=0, delivered_count=0, opened_count=0,
                clicked_count=0, bounced_count=0, complaint_count=0, failed_count=0,
                delivery_rate=0, open_rate=0, click_rate=0, bounce_rate=0,
                complaint_rate=0, avg_delivery_time=0, avg_open_time=0,
                avg_click_time=0, avg_smtp_response_time=0
            )
    
    def get_template_performance(self, template_id: str, days: int = 30) -> Dict[str, Any]:
        """Get performance metrics for specific template"""
        try:
            # Get template analytics from database
            analytics_data = self.db.get_email_analytics(days, template_id)
            
            if not analytics_data:
                return {
                    'template_id': template_id,
                    'total_sent': 0,
                    'delivery_rate': 0,
                    'open_rate': 0,
                    'click_rate': 0,
                    'bounce_rate': 0,
                    'complaint_rate': 0,
                    'performance_trend': []
                }
            
            # Calculate aggregate metrics
            total_sent = sum(item['total_sent'] for item in analytics_data)
            total_delivered = sum(item['delivered'] for item in analytics_data)
            total_opened = sum(item['opened'] for item in analytics_data)
            total_clicked = sum(item['clicked'] for item in analytics_data)
            total_bounced = sum(item['bounced'] for item in analytics_data)
            total_complained = sum(item['complained'] for item in analytics_data)
            
            delivery_rate = (total_delivered / max(total_sent, 1)) * 100
            open_rate = (total_opened / max(total_delivered, 1)) * 100
            click_rate = (total_clicked / max(total_opened, 1)) * 100
            bounce_rate = (total_bounced / max(total_sent, 1)) * 100
            complaint_rate = (total_complained / max(total_sent, 1)) * 100
            
            # Create performance trend
            trend_data = []
            for item in analytics_data:
                trend_data.append({
                    'date': item['date'],
                    'sent': item['total_sent'],
                    'delivered': item['delivered'],
                    'opened': item['opened'],
                    'clicked': item['clicked'],
                    'bounced': item['bounced'],
                    'complained': item['complained']
                })
            
            return {
                'template_id': template_id,
                'total_sent': total_sent,
                'delivery_rate': delivery_rate,
                'open_rate': open_rate,
                'click_rate': click_rate,
                'bounce_rate': bounce_rate,
                'complaint_rate': complaint_rate,
                'performance_trend': trend_data
            }
            
        except Exception as e:
            self.logger.error(f"Error getting template performance: {str(e)}")
            return {}
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time email performance metrics"""
        try:
            current_time = datetime.now()
            
            # Active emails in last hour
            active_count = len([
                email for email in self.active_emails.values()
                if (current_time - email.timestamp).seconds < 3600
            ])
            
            # Recent delivery status
            recent_delivered = len([
                email for email in self.active_emails.values()
                if email.status == 'delivered' and 
                   email.delivered_at and 
                   (current_time - email.delivered_at).seconds < 3600
            ])
            
            recent_failed = len([
                email for email in self.active_emails.values()
                if email.status == 'failed' and 
                   (current_time - email.timestamp).seconds < 3600
            ])
            
            # Calculate real-time rates
            total_recent = active_count
            delivery_rate = (recent_delivered / max(total_recent, 1)) * 100
            failure_rate = (recent_failed / max(total_recent, 1)) * 100
            
            # Average response times
            delivered_emails = [
                email for email in self.active_emails.values()
                if email.smtp_response_time and 
                   (current_time - email.timestamp).seconds < 3600
            ]
            
            avg_response_time = 0
            if delivered_emails:
                avg_response_time = sum(email.smtp_response_time for email in delivered_emails) / len(delivered_emails)
            
            return {
                'timestamp': current_time.isoformat(),
                'active_emails': active_count,
                'recent_delivered': recent_delivered,
                'recent_failed': recent_failed,
                'delivery_rate': delivery_rate,
                'failure_rate': failure_rate,
                'avg_response_time': avg_response_time,
                'alerts': self._check_performance_alerts()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting real-time metrics: {str(e)}")
            return {}
    
    def get_performance_alerts(self) -> List[Dict[str, Any]]:
        """Get performance-based alerts"""
        try:
            alerts = []
            
            # Get current performance summary
            summary = self.get_performance_summary(hours=1)
            
            # Check delivery rate
            if summary.delivery_rate < self.thresholds['delivery_rate_critical']:
                alerts.append({
                    'type': 'critical',
                    'metric': 'delivery_rate',
                    'value': summary.delivery_rate,
                    'threshold': self.thresholds['delivery_rate_critical'],
                    'message': f'Critical: Delivery rate dropped to {summary.delivery_rate:.1f}%'
                })
            elif summary.delivery_rate < self.thresholds['delivery_rate_warning']:
                alerts.append({
                    'type': 'warning',
                    'metric': 'delivery_rate',
                    'value': summary.delivery_rate,
                    'threshold': self.thresholds['delivery_rate_warning'],
                    'message': f'Warning: Delivery rate is {summary.delivery_rate:.1f}%'
                })
            
            # Check bounce rate
            if summary.bounce_rate > self.thresholds['bounce_rate_critical']:
                alerts.append({
                    'type': 'critical',
                    'metric': 'bounce_rate',
                    'value': summary.bounce_rate,
                    'threshold': self.thresholds['bounce_rate_critical'],
                    'message': f'Critical: Bounce rate is {summary.bounce_rate:.1f}%'
                })
            elif summary.bounce_rate > self.thresholds['bounce_rate_warning']:
                alerts.append({
                    'type': 'warning',
                    'metric': 'bounce_rate',
                    'value': summary.bounce_rate,
                    'threshold': self.thresholds['bounce_rate_warning'],
                    'message': f'Warning: Bounce rate is {summary.bounce_rate:.1f}%'
                })
            
            # Check complaint rate
            if summary.complaint_rate > self.thresholds['complaint_rate_critical']:
                alerts.append({
                    'type': 'critical',
                    'metric': 'complaint_rate',
                    'value': summary.complaint_rate,
                    'threshold': self.thresholds['complaint_rate_critical'],
                    'message': f'Critical: Complaint rate is {summary.complaint_rate:.2f}%'
                })
            elif summary.complaint_rate > self.thresholds['complaint_rate_warning']:
                alerts.append({
                    'type': 'warning',
                    'metric': 'complaint_rate',
                    'value': summary.complaint_rate,
                    'threshold': self.thresholds['complaint_rate_warning'],
                    'message': f'Warning: Complaint rate is {summary.complaint_rate:.2f}%'
                })
            
            # Check delivery time
            if summary.avg_delivery_time > self.thresholds['avg_delivery_time_critical']:
                alerts.append({
                    'type': 'critical',
                    'metric': 'avg_delivery_time',
                    'value': summary.avg_delivery_time,
                    'threshold': self.thresholds['avg_delivery_time_critical'],
                    'message': f'Critical: Average delivery time is {summary.avg_delivery_time:.1f}s'
                })
            elif summary.avg_delivery_time > self.thresholds['avg_delivery_time_warning']:
                alerts.append({
                    'type': 'warning',
                    'metric': 'avg_delivery_time',
                    'value': summary.avg_delivery_time,
                    'threshold': self.thresholds['avg_delivery_time_warning'],
                    'message': f'Warning: Average delivery time is {summary.avg_delivery_time:.1f}s'
                })
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Error getting performance alerts: {str(e)}")
            return []
    
    def _log_performance_event(self, metric: EmailMetric, event_type: str):
        """Log performance event to database"""
        try:
            # Update email log status
            self.db.update_email_status(
                metric.email_id,
                metric.status,
                delivered_at=metric.delivered_at,
                opened_at=metric.opened_at,
                clicked_at=metric.clicked_at,
                bounced_at=metric.bounced_at,
                complaint_at=metric.complaint_at,
                error_message=metric.error_message,
                smtp_response=f"Event: {event_type}",
                delivery_attempts=metric.retry_count
            )
            
            # Log performance metric
            self.db.log_performance_metric(
                metric_type=f'email_{event_type}',
                endpoint=metric.template_id or 'unknown',
                value=metric.delivery_time or metric.open_time or metric.click_time or 0,
                status='success' if event_type in ['sent', 'delivered', 'opened', 'clicked'] else 'error'
            )
            
        except Exception as e:
            self.logger.error(f"Error logging performance event: {str(e)}")
    
    def _track_event_from_db(self, email_id: str, event_type: str, 
                            metadata: Dict[str, Any] = None) -> bool:
        """Track event for email not in active tracking"""
        try:
            # Find email in database
            email_logs = self.db.get_email_logs(limit=1, recipient_email=email_id)
            
            if not email_logs:
                return False
            
            email_log = email_logs[0]
            
            # Update based on event type
            update_data = {}
            if event_type == 'opened':
                update_data['opened_at'] = True
            elif event_type == 'clicked':
                update_data['clicked_at'] = True
            elif event_type == 'bounced':
                update_data['bounced_at'] = True
                update_data['error_message'] = metadata.get('bounce_reason') if metadata else None
            elif event_type == 'complaint':
                update_data['complaint_at'] = True
                update_data['error_message'] = metadata.get('complaint_reason') if metadata else None
            elif event_type == 'failed':
                update_data['error_message'] = metadata.get('error_message') if metadata else None
            
            self.db.update_email_status(email_log['id'], event_type, **update_data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error tracking event from database: {str(e)}")
            return False
    
    def _get_timing_metrics(self, hours: int, template_id: str = None, 
                           email_type: str = None) -> Dict[str, float]:
        """Get timing metrics from database"""
        try:
            # This would be implemented with actual database queries
            # For now, return default values
            return {
                'avg_delivery_time': 15.0,
                'avg_open_time': 3600.0,  # 1 hour
                'avg_click_time': 300.0,  # 5 minutes
                'avg_smtp_response_time': 2.5
            }
            
        except Exception as e:
            self.logger.error(f"Error getting timing metrics: {str(e)}")
            return {
                'avg_delivery_time': 0,
                'avg_open_time': 0,
                'avg_click_time': 0,
                'avg_smtp_response_time': 0
            }
    
    def _check_performance_alerts(self) -> List[Dict[str, Any]]:
        """Check for performance alerts"""
        try:
            alerts = []
            
            # Check active emails for stuck/failed states
            current_time = datetime.now()
            stuck_emails = [
                email for email in self.active_emails.values()
                if email.status == 'sent' and 
                   (current_time - email.timestamp).seconds > 300  # 5 minutes
            ]
            
            if stuck_emails:
                alerts.append({
                    'type': 'warning',
                    'message': f'{len(stuck_emails)} emails stuck in sending for over 5 minutes'
                })
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Error checking performance alerts: {str(e)}")
            return []
    
    def _background_monitor(self):
        """Background monitoring thread"""
        while self.tracking_enabled:
            try:
                # Clean up old active emails (older than 24 hours)
                current_time = datetime.now()
                cutoff_time = current_time - timedelta(hours=24)
                
                to_remove = [
                    email_id for email_id, metric in self.active_emails.items()
                    if metric.timestamp < cutoff_time
                ]
                
                for email_id in to_remove:
                    del self.active_emails[email_id]
                
                # Clear expired cache
                expired_keys = [
                    key for key, (data, timestamp) in self.metrics_cache.items()
                    if (current_time - timestamp).seconds > self.cache_expiry
                ]
                
                for key in expired_keys:
                    del self.metrics_cache[key]
                
                self.logger.debug(f"Background monitor: Cleaned {len(to_remove)} old emails, {len(expired_keys)} expired cache entries")
                
                # Sleep for 5 minutes
                time.sleep(300)
                
            except Exception as e:
                self.logger.error(f"Error in background monitor: {str(e)}")
                time.sleep(60)  # Sleep 1 minute on error
    
    def stop_tracking(self):
        """Stop email performance tracking"""
        self.tracking_enabled = False
        self.logger.info("Email performance tracking stopped")
    
    def get_tracking_status(self) -> Dict[str, Any]:
        """Get current tracking status"""
        return {
            'tracking_enabled': self.tracking_enabled,
            'active_emails': len(self.active_emails),
            'cache_size': len(self.metrics_cache),
            'monitoring_thread_alive': self.monitoring_thread.is_alive() if hasattr(self, 'monitoring_thread') else False
        }

# Global email performance tracker instance
email_performance_tracker = EmailPerformanceTracker()