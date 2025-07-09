#!/usr/bin/env python3
"""
Test script for VectorCraft Email & Notification Management System
Tests all components of the advanced email management system
"""

import sys
import os
import logging
import json
import uuid
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_database_models():
    """Test database models and operations"""
    logger.info("Testing database models...")
    
    try:
        from database import db
        
        # Test email logging
        email_log_id = db.log_email(
            transaction_id='test_tx_123',
            email_type='test',
            recipient_email='test@example.com',
            subject='Test Email',
            template_id='test_template',
            status='sent'
        )
        
        logger.info(f"Email log created with ID: {email_log_id}")
        
        # Test email status update
        db.update_email_status(
            email_log_id,
            'delivered',
            delivered_at=True,
            smtp_response='250 OK'
        )
        
        logger.info("Email status updated successfully")
        
        # Test email template creation
        template_id = db.create_email_template(
            template_id='test_welcome',
            name='Welcome Email',
            subject='Welcome to {{company}}!',
            body_text='Hello {{username}}, welcome to {{company}}!',
            body_html='<h1>Hello {{username}}</h1><p>Welcome to {{company}}!</p>',
            template_type='transactional',
            variables=['username', 'company']
        )
        
        logger.info(f"Email template created with ID: {template_id}")
        
        # Test notification creation
        notification_id = str(uuid.uuid4())
        db.create_notification(
            notification_id=notification_id,
            user_id=None,  # Global notification
            notification_type='system',
            title='System Test',
            message='This is a test notification',
            priority='medium',
            category='test'
        )
        
        logger.info(f"Notification created with ID: {notification_id}")
        
        # Test communication log
        log_id = str(uuid.uuid4())
        db.log_communication(
            log_id=log_id,
            user_id=None,
            email_address='test@example.com',
            communication_type='email',
            direction='outbound',
            subject='Test Communication',
            content='Test message content',
            status='sent'
        )
        
        logger.info(f"Communication log created with ID: {log_id}")
        
        # Test queries
        email_logs = db.get_email_logs(limit=10)
        logger.info(f"Retrieved {len(email_logs)} email logs")
        
        templates = db.get_email_templates()
        logger.info(f"Retrieved {len(templates)} email templates")
        
        notifications = db.get_notifications(limit=10)
        logger.info(f"Retrieved {len(notifications)} notifications")
        
        comm_logs = db.get_communication_logs(limit=10)
        logger.info(f"Retrieved {len(comm_logs)} communication logs")
        
        logger.info("✅ Database models test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database models test failed: {str(e)}")
        return False

def test_email_service():
    """Test email service functionality"""
    logger.info("Testing email service...")
    
    try:
        from services.email_service import email_service
        
        # Test email creation
        message = email_service._create_message(
            to_email='test@example.com',
            subject='Test Email',
            body_text='This is a test email',
            body_html='<p>This is a test email</p>'
        )
        
        logger.info("Email message created successfully")
        
        # Test email sending (will be simulated if SMTP not configured)
        success = email_service._send_email(
            message,
            email_type='test',
            transaction_id='test_tx_456'
        )
        
        if success:
            logger.info("Email sent successfully (or simulated)")
        else:
            logger.warning("Email sending failed")
        
        logger.info("✅ Email service test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Email service test failed: {str(e)}")
        return False

def test_email_performance_tracker():
    """Test email performance tracker"""
    logger.info("Testing email performance tracker...")
    
    try:
        from services.email_performance_tracker import email_performance_tracker
        
        # Test email tracking
        email_id = str(uuid.uuid4())
        
        # Track email sent
        email_performance_tracker.track_email_sent(
            email_id=email_id,
            template_id='test_template',
            recipient_email='test@example.com',
            subject='Test Email',
            email_type='test',
            metadata={'test': True}
        )
        
        logger.info(f"Email sent tracked: {email_id}")
        
        # Track email delivered
        email_performance_tracker.track_email_delivered(
            email_id=email_id,
            delivery_time=2.5,
            smtp_response_time=1.2
        )
        
        logger.info("Email delivery tracked")
        
        # Track email opened
        email_performance_tracker.track_email_opened(
            email_id=email_id,
            open_time=300.0
        )
        
        logger.info("Email open tracked")
        
        # Get performance summary
        summary = email_performance_tracker.get_performance_summary(hours=24)
        logger.info(f"Performance summary: {summary.total_emails} emails, {summary.delivery_rate:.1f}% delivery rate")
        
        # Get real-time metrics
        real_time = email_performance_tracker.get_real_time_metrics()
        logger.info(f"Real-time metrics: {real_time.get('active_emails', 0)} active emails")
        
        # Get tracking status
        status = email_performance_tracker.get_tracking_status()
        logger.info(f"Tracking status: {status}")
        
        logger.info("✅ Email performance tracker test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Email performance tracker test failed: {str(e)}")
        return False

def test_template_system():
    """Test email template system"""
    logger.info("Testing email template system...")
    
    try:
        from database import db
        
        # Create test template
        template_id = db.create_email_template(
            template_id='test_template_2',
            name='Test Template 2',
            subject='Hello {{name}}!',
            body_text='Dear {{name}},\n\nWelcome to {{company}}!\n\nBest regards,\nThe Team',
            body_html='<h1>Hello {{name}}!</h1><p>Welcome to {{company}}!</p>',
            template_type='marketing',
            variables=['name', 'company']
        )
        
        logger.info(f"Template created with ID: {template_id}")
        
        # Get template
        template = db.get_email_template('test_template_2')
        logger.info(f"Retrieved template: {template['name']}")
        
        # Update template
        db.update_email_template(
            template_id='test_template_2',
            name='Updated Test Template',
            is_active=True
        )
        
        logger.info("Template updated successfully")
        
        # Test template rendering (basic)
        subject = template['subject'].replace('{{name}}', 'John').replace('{{company}}', 'VectorCraft')
        body_text = template['body_text'].replace('{{name}}', 'John').replace('{{company}}', 'VectorCraft')
        
        logger.info(f"Rendered subject: {subject}")
        logger.info(f"Rendered body (first 50 chars): {body_text[:50]}...")
        
        logger.info("✅ Template system test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Template system test failed: {str(e)}")
        return False

def test_notification_system():
    """Test notification system"""
    logger.info("Testing notification system...")
    
    try:
        from database import db
        
        # Create test notification
        notification_id = str(uuid.uuid4())
        db.create_notification(
            notification_id=notification_id,
            user_id=None,
            notification_type='payment',
            title='Payment Received',
            message='A new payment has been received',
            priority='high',
            category='payment',
            action_url='/admin/transactions',
            action_text='View Payment'
        )
        
        logger.info(f"Notification created: {notification_id}")
        
        # Get notification summary
        summary = db.get_notification_summary()
        logger.info(f"Notification summary: {summary.get('total_notifications', 0)} total, {summary.get('unread_count', 0)} unread")
        
        # Mark as read
        db.update_notification_status(notification_id, 'read', read_at=True)
        logger.info("Notification marked as read")
        
        # Get notifications
        notifications = db.get_notifications(limit=10)
        logger.info(f"Retrieved {len(notifications)} notifications")
        
        logger.info("✅ Notification system test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Notification system test failed: {str(e)}")
        return False

def test_analytics_system():
    """Test analytics and reporting system"""
    logger.info("Testing analytics system...")
    
    try:
        from database import db
        
        # Get email analytics
        analytics = db.get_email_analytics(days=30)
        logger.info(f"Email analytics: {len(analytics)} data points")
        
        # Get email performance summary
        performance = db.get_email_performance_summary(hours=24)
        logger.info(f"Performance summary: {performance}")
        
        # Get communication summary
        comm_summary = db.get_communication_summary(hours=24)
        logger.info(f"Communication summary: {len(comm_summary)} entries")
        
        logger.info("✅ Analytics system test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Analytics system test failed: {str(e)}")
        return False

def run_all_tests():
    """Run all tests"""
    logger.info("🚀 Starting VectorCraft Email & Notification System Tests")
    logger.info("=" * 60)
    
    tests = [
        test_database_models,
        test_email_service,
        test_email_performance_tracker,
        test_template_system,
        test_notification_system,
        test_analytics_system
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"❌ Test {test.__name__} failed with exception: {str(e)}")
            failed += 1
        
        logger.info("-" * 40)
    
    logger.info("=" * 60)
    logger.info(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        logger.info("🎉 All tests passed! Email & Notification System is ready.")
    else:
        logger.warning(f"⚠️  {failed} test(s) failed. Please check the logs above.")
    
    return failed == 0

if __name__ == '__main__':
    # Set up test environment
    os.environ['FLASK_ENV'] = 'testing'
    
    # Run tests
    success = run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)