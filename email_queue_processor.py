#!/usr/bin/env python3
"""
Email Queue Processor for VectorCraft
Background service to process and send queued emails from the email automation system
"""

import time
import logging
import threading
from datetime import datetime
from database import db
from services.email_service import email_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('email_queue_processor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class EmailQueueProcessor:
    """Background processor for email queue"""
    
    def __init__(self, check_interval=60):
        """
        Initialize the email queue processor
        
        Args:
            check_interval (int): How often to check for pending emails (seconds)
        """
        self.check_interval = check_interval
        self.running = False
        self.thread = None
        
    def start(self):
        """Start the background email processor"""
        if self.running:
            logger.warning("Email queue processor is already running")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        self.thread.start()
        logger.info(f"Email queue processor started with {self.check_interval}s interval")
        
    def stop(self):
        """Stop the background email processor"""
        if not self.running:
            logger.warning("Email queue processor is not running")
            return
            
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("Email queue processor stopped")
        
    def _process_loop(self):
        """Main processing loop"""
        while self.running:
            try:
                self.process_pending_emails()
            except Exception as e:
                logger.error(f"Error in email processing loop: {e}")
            
            # Sleep for the check interval
            time.sleep(self.check_interval)
            
    def process_pending_emails(self, limit=50):
        """
        Process pending emails from the queue
        
        Args:
            limit (int): Maximum number of emails to process per batch
        """
        try:
            # Get pending emails that are ready to be sent
            pending_emails = db.get_pending_emails(limit=limit)
            
            if not pending_emails:
                logger.debug("No pending emails to process")
                return
                
            logger.info(f"Processing {len(pending_emails)} pending emails")
            
            for email_data in pending_emails:
                try:
                    self._send_email(email_data)
                except Exception as e:
                    logger.error(f"Failed to send email {email_data['id']}: {e}")
                    self._mark_email_failed(email_data['id'], str(e))
                    
        except Exception as e:
            logger.error(f"Error processing pending emails: {e}")
            
    def _send_email(self, email_data):
        """
        Send a single email from the queue
        
        Args:
            email_data (dict): Email data from database
        """
        try:
            # Mark email as sending
            db.update_email_status(email_data['id'], 'sending')
            
            # Prepare email variables if they exist
            variables = {}
            if email_data.get('variables_json'):
                import json
                try:
                    variables = json.loads(email_data['variables_json'])
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in variables for email {email_data['id']}")
            
            # Send the email using the email service
            success = email_service.send_automated_email(
                to_email=email_data['recipient_email'],
                subject=email_data['subject'],
                content_html=email_data['content_html'],
                tracking_id=email_data.get('tracking_id'),
                variables=variables
            )
            
            if success:
                # Mark email as sent and record tracking
                db.update_email_status(email_data['id'], 'sent', sent_at=datetime.now())
                
                # Record email tracking
                if email_data.get('tracking_id'):
                    db.record_email_tracking(
                        tracking_id=email_data['tracking_id'],
                        event_type='sent',
                        queue_id=email_data['id'],
                        metadata={
                            'email_address': email_data['recipient_email'],
                            'template_id': email_data.get('template_id'),
                            'automation_id': email_data.get('automation_id'),
                            'campaign_id': email_data.get('campaign_id')
                        }
                    )
                
                logger.info(f"Successfully sent email {email_data['id']} to {email_data['recipient_email']}")
                
                # Log to system logs
                from services.monitoring import system_logger
                system_logger.info('email', f'Automated email sent to {email_data["recipient_email"]}', 
                                 details={
                                     'email_id': email_data['id'],
                                     'template_id': email_data.get('template_id'),
                                     'automation_id': email_data.get('automation_id'),
                                     'tracking_id': email_data.get('tracking_id')
                                 })
            else:
                self._mark_email_failed(email_data['id'], 'Email service returned failure')
                
        except Exception as e:
            logger.error(f"Error sending email {email_data['id']}: {e}")
            self._mark_email_failed(email_data['id'], str(e))
            raise
            
    def _mark_email_failed(self, email_id, error_message):
        """
        Mark an email as failed
        
        Args:
            email_id (int): Email ID
            error_message (str): Error message
        """
        try:
            db.update_email_status(email_id, 'failed', error_message=error_message)
            logger.error(f"Marked email {email_id} as failed: {error_message}")
            
            # Log to system logs
            from services.monitoring import system_logger
            system_logger.error('email', f'Email send failed: {error_message}', 
                               details={'email_id': email_id})
        except Exception as e:
            logger.error(f"Error marking email {email_id} as failed: {e}")

# Create global processor instance
email_processor = EmailQueueProcessor()

def start_email_processor():
    """Start the email queue processor"""
    email_processor.start()

def stop_email_processor():
    """Stop the email queue processor"""
    email_processor.stop()

if __name__ == "__main__":
    """Run the email processor as a standalone script"""
    logger.info("Starting VectorCraft Email Queue Processor")
    
    try:
        # Start the processor
        email_processor.start()
        
        # Keep the script running
        while True:
            time.sleep(10)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        email_processor.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        email_processor.stop()