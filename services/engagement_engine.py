"""
Engagement Automation Engine
Handles multi-channel customer engagement, personalization, and automated communication.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import sqlite3
from services.database_pool import DatabasePool
from services.email_service import EmailService
from services.monitoring.system_logger import SystemLogger

logger = logging.getLogger(__name__)

class EngagementChannel(Enum):
    """Types of engagement channels"""
    EMAIL = "email"
    SMS = "sms"
    PUSH_NOTIFICATION = "push_notification"
    IN_APP = "in_app"
    SOCIAL_MEDIA = "social_media"
    WEBHOOK = "webhook"

class EngagementTrigger(Enum):
    """Types of engagement triggers"""
    USER_BEHAVIOR = "user_behavior"
    TIME_BASED = "time_based"
    MILESTONE = "milestone"
    LIFECYCLE_STAGE = "lifecycle_stage"
    CUSTOM_EVENT = "custom_event"
    MANUAL = "manual"

class EngagementStatus(Enum):
    """Status of engagement campaigns"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

@dataclass
class EngagementRule:
    """Represents an engagement automation rule"""
    rule_id: str
    name: str
    description: str
    trigger_type: EngagementTrigger
    trigger_conditions: Dict[str, Any]
    target_audience: Dict[str, Any]
    channels: List[EngagementChannel]
    content_templates: Dict[str, Any]
    scheduling: Dict[str, Any]
    personalization: Dict[str, Any]
    frequency_limits: Dict[str, Any]
    is_active: bool = True
    created_at: datetime = None
    updated_at: datetime = None

@dataclass
class EngagementExecution:
    """Represents an engagement execution"""
    execution_id: str
    rule_id: str
    customer_id: str
    channel: EngagementChannel
    content: Dict[str, Any]
    status: str
    scheduled_at: datetime
    executed_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

@dataclass
class PersonalizationProfile:
    """Customer personalization profile"""
    customer_id: str
    preferences: Dict[str, Any]
    behavioral_data: Dict[str, Any]
    demographic_data: Dict[str, Any]
    engagement_history: Dict[str, Any]
    optimal_times: Dict[str, Any]
    channel_preferences: List[str]
    updated_at: datetime

class EngagementAutomationEngine:
    """Multi-channel engagement automation engine"""
    
    def __init__(self, db_pool: DatabasePool, email_service: EmailService, 
                 system_logger: SystemLogger):
        self.db_pool = db_pool
        self.email_service = email_service
        self.system_logger = system_logger
        self.logger = logging.getLogger(__name__)
        
        # Initialize database tables
        self._init_database()
        
    def _init_database(self):
        """Initialize engagement database tables"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            # Engagement rules table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS engagement_rules (
                    rule_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    trigger_type TEXT NOT NULL,
                    trigger_conditions TEXT,
                    target_audience TEXT,
                    channels TEXT,
                    content_templates TEXT,
                    scheduling TEXT,
                    personalization TEXT,
                    frequency_limits TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Engagement executions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS engagement_executions (
                    execution_id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    customer_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    content TEXT,
                    status TEXT NOT NULL DEFAULT 'scheduled',
                    scheduled_at TIMESTAMP NOT NULL,
                    executed_at TIMESTAMP,
                    delivered_at TIMESTAMP,
                    response_data TEXT,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (rule_id) REFERENCES engagement_rules(rule_id)
                )
            ''')
            
            # Personalization profiles table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS personalization_profiles (
                    customer_id TEXT PRIMARY KEY,
                    preferences TEXT,
                    behavioral_data TEXT,
                    demographic_data TEXT,
                    engagement_history TEXT,
                    optimal_times TEXT,
                    channel_preferences TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Engagement metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS engagement_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    metric_date DATE NOT NULL,
                    additional_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (rule_id) REFERENCES engagement_rules(rule_id)
                )
            ''')
            
            # Customer engagement history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customer_engagement_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id TEXT NOT NULL,
                    engagement_type TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    content_id TEXT,
                    action TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # Content templates table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS content_templates (
                    template_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    template_data TEXT,
                    personalization_fields TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Engagement segments table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS engagement_segments (
                    segment_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    criteria TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Customer segments mapping table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customer_segments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id TEXT NOT NULL,
                    segment_id TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (segment_id) REFERENCES engagement_segments(segment_id)
                )
            ''')
            
            conn.commit()
            self.logger.info("Engagement automation database tables initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing engagement database: {str(e)}")
            raise
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def create_engagement_rule(self, rule_data: Dict[str, Any]) -> str:
        """Create a new engagement automation rule"""
        try:
            rule_id = f"rule_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO engagement_rules
                (rule_id, name, description, trigger_type, trigger_conditions,
                 target_audience, channels, content_templates, scheduling,
                 personalization, frequency_limits, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                rule_id,
                rule_data['name'],
                rule_data.get('description', ''),
                rule_data['trigger_type'],
                json.dumps(rule_data.get('trigger_conditions', {})),
                json.dumps(rule_data.get('target_audience', {})),
                json.dumps(rule_data.get('channels', [])),
                json.dumps(rule_data.get('content_templates', {})),
                json.dumps(rule_data.get('scheduling', {})),
                json.dumps(rule_data.get('personalization', {})),
                json.dumps(rule_data.get('frequency_limits', {})),
                rule_data.get('is_active', True)
            ))
            
            conn.commit()
            self.logger.info(f"Created engagement rule: {rule_data['name']} ({rule_id})")
            
            return rule_id
            
        except Exception as e:
            self.logger.error(f"Error creating engagement rule: {str(e)}")
            raise
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def update_personalization_profile(self, customer_id: str, 
                                     profile_data: Dict[str, Any]) -> bool:
        """Update customer personalization profile"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO personalization_profiles
                (customer_id, preferences, behavioral_data, demographic_data,
                 engagement_history, optimal_times, channel_preferences, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                customer_id,
                json.dumps(profile_data.get('preferences', {})),
                json.dumps(profile_data.get('behavioral_data', {})),
                json.dumps(profile_data.get('demographic_data', {})),
                json.dumps(profile_data.get('engagement_history', {})),
                json.dumps(profile_data.get('optimal_times', {})),
                json.dumps(profile_data.get('channel_preferences', [])),
                datetime.now()
            ))
            
            conn.commit()
            self.logger.info(f"Updated personalization profile for customer {customer_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating personalization profile: {str(e)}")
            return False
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def trigger_engagement(self, customer_id: str, trigger_type: str, 
                         trigger_data: Dict[str, Any]) -> List[str]:
        """Trigger engagement based on customer action or event"""
        try:
            triggered_executions = []
            
            # Get matching engagement rules
            rules = self._get_matching_rules(trigger_type, trigger_data)
            
            for rule in rules:
                # Check if customer matches target audience
                if self._customer_matches_audience(customer_id, rule['target_audience']):
                    # Check frequency limits
                    if self._check_frequency_limits(customer_id, rule['rule_id'], 
                                                  rule['frequency_limits']):
                        # Create engagement executions for each channel
                        for channel in rule['channels']:
                            execution_id = self._create_engagement_execution(
                                rule['rule_id'], customer_id, channel, 
                                rule['content_templates'], rule['scheduling'],
                                rule['personalization']
                            )
                            if execution_id:
                                triggered_executions.append(execution_id)
            
            return triggered_executions
            
        except Exception as e:
            self.logger.error(f"Error triggering engagement: {str(e)}")
            return []

    def _get_matching_rules(self, trigger_type: str, 
                          trigger_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get engagement rules that match the trigger"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM engagement_rules
                WHERE trigger_type = ? AND is_active = TRUE
            ''', (trigger_type,))
            
            matching_rules = []
            for row in cursor.fetchall():
                rule = {
                    'rule_id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'trigger_type': row[3],
                    'trigger_conditions': json.loads(row[4]) if row[4] else {},
                    'target_audience': json.loads(row[5]) if row[5] else {},
                    'channels': json.loads(row[6]) if row[6] else [],
                    'content_templates': json.loads(row[7]) if row[7] else {},
                    'scheduling': json.loads(row[8]) if row[8] else {},
                    'personalization': json.loads(row[9]) if row[9] else {},
                    'frequency_limits': json.loads(row[10]) if row[10] else {}
                }
                
                # Check if trigger conditions are met
                if self._evaluate_trigger_conditions(trigger_data, rule['trigger_conditions']):
                    matching_rules.append(rule)
            
            return matching_rules
            
        except Exception as e:
            self.logger.error(f"Error getting matching rules: {str(e)}")
            return []
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _evaluate_trigger_conditions(self, trigger_data: Dict[str, Any], 
                                   conditions: Dict[str, Any]) -> bool:
        """Evaluate if trigger conditions are met"""
        try:
            if not conditions:
                return True
            
            for key, expected_value in conditions.items():
                if key not in trigger_data:
                    return False
                
                actual_value = trigger_data[key]
                
                if isinstance(expected_value, dict):
                    # Handle operators
                    for operator, value in expected_value.items():
                        if operator == "equals" and actual_value != value:
                            return False
                        elif operator == "greater_than" and actual_value <= value:
                            return False
                        elif operator == "less_than" and actual_value >= value:
                            return False
                        elif operator == "contains" and value not in str(actual_value):
                            return False
                elif actual_value != expected_value:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error evaluating trigger conditions: {str(e)}")
            return False

    def _customer_matches_audience(self, customer_id: str, 
                                 audience_criteria: Dict[str, Any]) -> bool:
        """Check if customer matches target audience criteria"""
        try:
            if not audience_criteria:
                return True
            
            # Get customer data
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            # Get user basic info
            cursor.execute('''
                SELECT email, created_at, last_login FROM users WHERE id = ?
            ''', (customer_id,))
            
            user_data = cursor.fetchone()
            if not user_data:
                return False
            
            # Get personalization profile
            cursor.execute('''
                SELECT preferences, behavioral_data, demographic_data
                FROM personalization_profiles WHERE customer_id = ?
            ''', (customer_id,))
            
            profile_data = cursor.fetchone()
            
            # Evaluate audience criteria
            for criterion, value in audience_criteria.items():
                if criterion == "segments":
                    # Check if customer is in required segments
                    if not self._customer_in_segments(customer_id, value):
                        return False
                elif criterion == "user_age_days":
                    # Check user age
                    created_at = datetime.fromisoformat(user_data[2].replace('Z', '+00:00'))
                    age_days = (datetime.now() - created_at).days
                    if not self._evaluate_numeric_condition(age_days, value):
                        return False
                elif criterion == "has_purchased":
                    # Check purchase history
                    if not self._customer_has_purchased(customer_id) != value:
                        return False
                # Add more criteria as needed
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking audience match: {str(e)}")
            return False
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _customer_in_segments(self, customer_id: str, required_segments: List[str]) -> bool:
        """Check if customer is in required segments"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT segment_id FROM customer_segments WHERE customer_id = ?
            ''', (customer_id,))
            
            customer_segments = {row[0] for row in cursor.fetchall()}
            
            return any(segment in customer_segments for segment in required_segments)
            
        except Exception as e:
            self.logger.error(f"Error checking customer segments: {str(e)}")
            return False
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _customer_has_purchased(self, customer_id: str) -> bool:
        """Check if customer has made any purchases"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) FROM transactions t
                JOIN users u ON t.username = u.username
                WHERE u.id = ? AND t.status = 'completed'
            ''', (customer_id,))
            
            return cursor.fetchone()[0] > 0
            
        except Exception as e:
            self.logger.error(f"Error checking purchase history: {str(e)}")
            return False
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _evaluate_numeric_condition(self, actual_value: float, 
                                  condition: Dict[str, Any]) -> bool:
        """Evaluate numeric condition"""
        try:
            if isinstance(condition, dict):
                for operator, value in condition.items():
                    if operator == "greater_than" and actual_value <= value:
                        return False
                    elif operator == "less_than" and actual_value >= value:
                        return False
                    elif operator == "equals" and actual_value != value:
                        return False
            else:
                return actual_value == condition
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error evaluating numeric condition: {str(e)}")
            return False

    def _check_frequency_limits(self, customer_id: str, rule_id: str, 
                              limits: Dict[str, Any]) -> bool:
        """Check if frequency limits allow sending"""
        try:
            if not limits:
                return True
            
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            # Check daily limit
            if 'daily_limit' in limits:
                cursor.execute('''
                    SELECT COUNT(*) FROM engagement_executions
                    WHERE customer_id = ? AND rule_id = ? 
                    AND DATE(executed_at) = DATE('now')
                    AND status = 'delivered'
                ''', (customer_id, rule_id))
                
                daily_count = cursor.fetchone()[0]
                if daily_count >= limits['daily_limit']:
                    return False
            
            # Check weekly limit
            if 'weekly_limit' in limits:
                cursor.execute('''
                    SELECT COUNT(*) FROM engagement_executions
                    WHERE customer_id = ? AND rule_id = ? 
                    AND executed_at >= datetime('now', '-7 days')
                    AND status = 'delivered'
                ''', (customer_id, rule_id))
                
                weekly_count = cursor.fetchone()[0]
                if weekly_count >= limits['weekly_limit']:
                    return False
            
            # Check minimum interval
            if 'min_interval_hours' in limits:
                cursor.execute('''
                    SELECT MAX(executed_at) FROM engagement_executions
                    WHERE customer_id = ? AND rule_id = ?
                    AND status = 'delivered'
                ''', (customer_id, rule_id))
                
                last_execution = cursor.fetchone()[0]
                if last_execution:
                    last_exec_time = datetime.fromisoformat(last_execution.replace('Z', '+00:00'))
                    hours_since = (datetime.now() - last_exec_time).total_seconds() / 3600
                    if hours_since < limits['min_interval_hours']:
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking frequency limits: {str(e)}")
            return False
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _create_engagement_execution(self, rule_id: str, customer_id: str, 
                                   channel: str, content_templates: Dict[str, Any],
                                   scheduling: Dict[str, Any], 
                                   personalization: Dict[str, Any]) -> Optional[str]:
        """Create an engagement execution"""
        try:
            execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Get personalized content
            content = self._generate_personalized_content(
                customer_id, channel, content_templates, personalization
            )
            
            # Calculate scheduling
            scheduled_at = self._calculate_scheduled_time(customer_id, scheduling)
            
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO engagement_executions
                (execution_id, rule_id, customer_id, channel, content,
                 status, scheduled_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                execution_id,
                rule_id,
                customer_id,
                channel,
                json.dumps(content),
                'scheduled',
                scheduled_at
            ))
            
            conn.commit()
            
            # If scheduled for now, execute immediately
            if scheduled_at <= datetime.now():
                self._execute_engagement(execution_id)
            
            return execution_id
            
        except Exception as e:
            self.logger.error(f"Error creating engagement execution: {str(e)}")
            return None
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _generate_personalized_content(self, customer_id: str, channel: str,
                                     content_templates: Dict[str, Any],
                                     personalization: Dict[str, Any]) -> Dict[str, Any]:
        """Generate personalized content for customer"""
        try:
            # Get customer personalization data
            profile = self._get_personalization_profile(customer_id)
            
            # Get base content template
            template = content_templates.get(channel, {})
            
            # Apply personalization
            personalized_content = template.copy()
            
            if profile and personalization:
                # Replace personalization tokens
                for field, value in personalized_content.items():
                    if isinstance(value, str):
                        # Replace {{customer_name}} with actual name
                        if '{{customer_name}}' in value:
                            name = profile.get('demographic_data', {}).get('name', 'Valued Customer')
                            value = value.replace('{{customer_name}}', name)
                        
                        # Replace {{preferred_time}} with optimal time
                        if '{{preferred_time}}' in value:
                            optimal_time = profile.get('optimal_times', {}).get('email', '10:00 AM')
                            value = value.replace('{{preferred_time}}', optimal_time)
                        
                        personalized_content[field] = value
            
            return personalized_content
            
        except Exception as e:
            self.logger.error(f"Error generating personalized content: {str(e)}")
            return content_templates.get(channel, {})

    def _get_personalization_profile(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get customer personalization profile"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT preferences, behavioral_data, demographic_data,
                       engagement_history, optimal_times, channel_preferences
                FROM personalization_profiles WHERE customer_id = ?
            ''', (customer_id,))
            
            result = cursor.fetchone()
            if not result:
                return None
            
            return {
                'preferences': json.loads(result[0]) if result[0] else {},
                'behavioral_data': json.loads(result[1]) if result[1] else {},
                'demographic_data': json.loads(result[2]) if result[2] else {},
                'engagement_history': json.loads(result[3]) if result[3] else {},
                'optimal_times': json.loads(result[4]) if result[4] else {},
                'channel_preferences': json.loads(result[5]) if result[5] else []
            }
            
        except Exception as e:
            self.logger.error(f"Error getting personalization profile: {str(e)}")
            return None
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _calculate_scheduled_time(self, customer_id: str, 
                                scheduling: Dict[str, Any]) -> datetime:
        """Calculate optimal scheduled time for engagement"""
        try:
            # Get customer's optimal times
            profile = self._get_personalization_profile(customer_id)
            
            base_time = datetime.now()
            
            if scheduling.get('immediate', False):
                return base_time
            
            # Add delay if specified
            if 'delay_hours' in scheduling:
                base_time += timedelta(hours=scheduling['delay_hours'])
            
            # Adjust for optimal time if available
            if profile and 'optimal_times' in profile:
                optimal_hour = profile['optimal_times'].get('general', 10)  # Default to 10 AM
                
                # Adjust to optimal hour
                base_time = base_time.replace(hour=optimal_hour, minute=0, second=0, microsecond=0)
                
                # If that time has passed today, schedule for tomorrow
                if base_time <= datetime.now():
                    base_time += timedelta(days=1)
            
            return base_time
            
        except Exception as e:
            self.logger.error(f"Error calculating scheduled time: {str(e)}")
            return datetime.now()

    def _execute_engagement(self, execution_id: str) -> bool:
        """Execute a scheduled engagement"""
        try:
            # Get execution details
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT rule_id, customer_id, channel, content, status
                FROM engagement_executions WHERE execution_id = ?
            ''', (execution_id,))
            
            result = cursor.fetchone()
            if not result or result[4] != 'scheduled':
                return False
            
            rule_id, customer_id, channel, content_json, status = result
            content = json.loads(content_json) if content_json else {}
            
            # Update status to executing
            cursor.execute('''
                UPDATE engagement_executions
                SET status = 'executing', executed_at = ?
                WHERE execution_id = ?
            ''', (datetime.now(), execution_id))
            
            conn.commit()
            
            # Execute based on channel
            success = False
            if channel == 'email':
                success = self._execute_email_engagement(customer_id, content)
            elif channel == 'sms':
                success = self._execute_sms_engagement(customer_id, content)
            elif channel == 'push_notification':
                success = self._execute_push_notification(customer_id, content)
            elif channel == 'in_app':
                success = self._execute_in_app_engagement(customer_id, content)
            
            # Update execution status
            if success:
                cursor.execute('''
                    UPDATE engagement_executions
                    SET status = 'delivered', delivered_at = ?
                    WHERE execution_id = ?
                ''', (datetime.now(), execution_id))
                
                # Record engagement history
                self._record_engagement_history(customer_id, 'automated', channel, 
                                              execution_id, 'delivered')
            else:
                cursor.execute('''
                    UPDATE engagement_executions
                    SET status = 'failed', error_message = ?
                    WHERE execution_id = ?
                ''', ('Delivery failed', execution_id))
            
            conn.commit()
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error executing engagement: {str(e)}")
            return False
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _execute_email_engagement(self, customer_id: str, content: Dict[str, Any]) -> bool:
        """Execute email engagement"""
        try:
            # Get customer email
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT email FROM users WHERE id = ?', (customer_id,))
            result = cursor.fetchone()
            
            if not result:
                return False
            
            email = result[0]
            
            # Send email
            success = self.email_service.send_email(
                to_email=email,
                subject=content.get('subject', 'VectorCraft Update'),
                body=content.get('body', ''),
                html_body=content.get('html_body', '')
            )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error executing email engagement: {str(e)}")
            return False
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _execute_sms_engagement(self, customer_id: str, content: Dict[str, Any]) -> bool:
        """Execute SMS engagement (mock implementation)"""
        try:
            # Mock SMS sending
            self.logger.info(f"Sending SMS to customer {customer_id}: {content.get('message', '')}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing SMS engagement: {str(e)}")
            return False

    def _execute_push_notification(self, customer_id: str, content: Dict[str, Any]) -> bool:
        """Execute push notification (mock implementation)"""
        try:
            # Mock push notification
            self.logger.info(f"Sending push notification to customer {customer_id}: {content.get('title', '')}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing push notification: {str(e)}")
            return False

    def _execute_in_app_engagement(self, customer_id: str, content: Dict[str, Any]) -> bool:
        """Execute in-app engagement (mock implementation)"""
        try:
            # Mock in-app message
            self.logger.info(f"Showing in-app message to customer {customer_id}: {content.get('message', '')}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing in-app engagement: {str(e)}")
            return False

    def _record_engagement_history(self, customer_id: str, engagement_type: str,
                                 channel: str, content_id: str, action: str):
        """Record customer engagement history"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO customer_engagement_history
                (customer_id, engagement_type, channel, content_id, action, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (customer_id, engagement_type, channel, content_id, action, datetime.now()))
            
            conn.commit()
            
        except Exception as e:
            self.logger.error(f"Error recording engagement history: {str(e)}")
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def process_scheduled_engagements(self):
        """Process all scheduled engagements that are ready to execute"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            # Get scheduled engagements ready to execute
            cursor.execute('''
                SELECT execution_id FROM engagement_executions
                WHERE status = 'scheduled' AND scheduled_at <= ?
                ORDER BY scheduled_at
            ''', (datetime.now(),))
            
            execution_ids = [row[0] for row in cursor.fetchall()]
            
            for execution_id in execution_ids:
                self._execute_engagement(execution_id)
            
            return len(execution_ids)
            
        except Exception as e:
            self.logger.error(f"Error processing scheduled engagements: {str(e)}")
            return 0
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def get_engagement_analytics(self, rule_id: Optional[str] = None,
                               days: int = 30) -> Dict[str, Any]:
        """Get engagement analytics"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            # Base query conditions
            conditions = ["executed_at >= datetime('now', '-{} days')".format(days)]
            params = []
            
            if rule_id:
                conditions.append("rule_id = ?")
                params.append(rule_id)
            
            where_clause = " AND ".join(conditions)
            
            # Delivery rates by channel
            cursor.execute(f'''
                SELECT 
                    channel,
                    COUNT(*) as total_sent,
                    COUNT(CASE WHEN status = 'delivered' THEN 1 END) as delivered,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed
                FROM engagement_executions
                WHERE {where_clause}
                GROUP BY channel
            ''', params)
            
            channel_performance = {}
            for row in cursor.fetchall():
                channel, total, delivered, failed = row
                channel_performance[channel] = {
                    'total_sent': total,
                    'delivered': delivered,
                    'failed': failed,
                    'delivery_rate': delivered / total if total > 0 else 0
                }
            
            # Daily engagement trends
            cursor.execute(f'''
                SELECT 
                    DATE(executed_at) as date,
                    COUNT(*) as total_engagements,
                    COUNT(CASE WHEN status = 'delivered' THEN 1 END) as successful
                FROM engagement_executions
                WHERE {where_clause}
                GROUP BY DATE(executed_at)
                ORDER BY date
            ''', params)
            
            daily_trends = []
            for row in cursor.fetchall():
                date, total, successful = row
                daily_trends.append({
                    'date': date,
                    'total_engagements': total,
                    'successful_engagements': successful,
                    'success_rate': successful / total if total > 0 else 0
                })
            
            # Top performing rules
            cursor.execute(f'''
                SELECT 
                    ee.rule_id,
                    er.name,
                    COUNT(*) as total_executions,
                    COUNT(CASE WHEN ee.status = 'delivered' THEN 1 END) as successful_executions
                FROM engagement_executions ee
                JOIN engagement_rules er ON ee.rule_id = er.rule_id
                WHERE {where_clause}
                GROUP BY ee.rule_id, er.name
                ORDER BY successful_executions DESC
                LIMIT 10
            ''', params)
            
            top_rules = []
            for row in cursor.fetchall():
                rule_id, name, total, successful = row
                top_rules.append({
                    'rule_id': rule_id,
                    'name': name,
                    'total_executions': total,
                    'successful_executions': successful,
                    'success_rate': successful / total if total > 0 else 0
                })
            
            return {
                'channel_performance': channel_performance,
                'daily_trends': daily_trends,
                'top_rules': top_rules,
                'summary': {
                    'total_channels': len(channel_performance),
                    'total_engagements': sum(cp['total_sent'] for cp in channel_performance.values()),
                    'total_delivered': sum(cp['delivered'] for cp in channel_performance.values()),
                    'overall_delivery_rate': sum(cp['delivered'] for cp in channel_performance.values()) / 
                                           sum(cp['total_sent'] for cp in channel_performance.values()) 
                                           if sum(cp['total_sent'] for cp in channel_performance.values()) > 0 else 0
                },
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting engagement analytics: {str(e)}")
            return {}
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def get_customer_engagement_profile(self, customer_id: str) -> Dict[str, Any]:
        """Get comprehensive engagement profile for a customer"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            # Get engagement history
            cursor.execute('''
                SELECT engagement_type, channel, action, COUNT(*) as count
                FROM customer_engagement_history
                WHERE customer_id = ?
                GROUP BY engagement_type, channel, action
                ORDER BY count DESC
            ''', (customer_id,))
            
            engagement_history = []
            for row in cursor.fetchall():
                engagement_history.append({
                    'engagement_type': row[0],
                    'channel': row[1],
                    'action': row[2],
                    'count': row[3]
                })
            
            # Get recent executions
            cursor.execute('''
                SELECT channel, content, status, executed_at
                FROM engagement_executions
                WHERE customer_id = ?
                ORDER BY executed_at DESC
                LIMIT 10
            ''', (customer_id,))
            
            recent_executions = []
            for row in cursor.fetchall():
                recent_executions.append({
                    'channel': row[0],
                    'content': json.loads(row[1]) if row[1] else {},
                    'status': row[2],
                    'executed_at': row[3]
                })
            
            # Get personalization profile
            profile = self._get_personalization_profile(customer_id)
            
            return {
                'customer_id': customer_id,
                'engagement_history': engagement_history,
                'recent_executions': recent_executions,
                'personalization_profile': profile,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting customer engagement profile: {str(e)}")
            return {}
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def create_customer_segment(self, segment_data: Dict[str, Any]) -> str:
        """Create a customer segment"""
        try:
            segment_id = f"segment_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO engagement_segments
                (segment_id, name, description, criteria, is_active)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                segment_id,
                segment_data['name'],
                segment_data.get('description', ''),
                json.dumps(segment_data.get('criteria', {})),
                segment_data.get('is_active', True)
            ))
            
            conn.commit()
            
            # Update customer segments based on criteria
            self._update_customer_segments(segment_id, segment_data.get('criteria', {}))
            
            return segment_id
            
        except Exception as e:
            self.logger.error(f"Error creating customer segment: {str(e)}")
            raise
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _update_customer_segments(self, segment_id: str, criteria: Dict[str, Any]):
        """Update customer segments based on criteria"""
        try:
            # This is a simplified implementation
            # In a real scenario, this would evaluate complex criteria
            
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            # Get all customers
            cursor.execute('SELECT id FROM users')
            customers = [row[0] for row in cursor.fetchall()]
            
            for customer_id in customers:
                if self._customer_matches_segment_criteria(customer_id, criteria):
                    cursor.execute('''
                        INSERT OR REPLACE INTO customer_segments
                        (customer_id, segment_id, added_at)
                        VALUES (?, ?, ?)
                    ''', (customer_id, segment_id, datetime.now()))
            
            conn.commit()
            
        except Exception as e:
            self.logger.error(f"Error updating customer segments: {str(e)}")
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _customer_matches_segment_criteria(self, customer_id: str, 
                                         criteria: Dict[str, Any]) -> bool:
        """Check if customer matches segment criteria"""
        try:
            # Simplified criteria evaluation
            # In practice, this would be more sophisticated
            
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            # Check purchase criteria
            if 'has_purchased' in criteria:
                cursor.execute('''
                    SELECT COUNT(*) FROM transactions t
                    JOIN users u ON t.username = u.username
                    WHERE u.id = ? AND t.status = 'completed'
                ''', (customer_id,))
                
                has_purchased = cursor.fetchone()[0] > 0
                if has_purchased != criteria['has_purchased']:
                    return False
            
            # Check registration date criteria
            if 'registered_days_ago' in criteria:
                cursor.execute('SELECT created_at FROM users WHERE id = ?', (customer_id,))
                result = cursor.fetchone()
                if result:
                    created_at = datetime.fromisoformat(result[0].replace('Z', '+00:00'))
                    days_ago = (datetime.now() - created_at).days
                    
                    condition = criteria['registered_days_ago']
                    if not self._evaluate_numeric_condition(days_ago, condition):
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking segment criteria: {str(e)}")
            return False
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def get_engagement_dashboard_data(self) -> Dict[str, Any]:
        """Get engagement dashboard data"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            # Active rules count
            cursor.execute('SELECT COUNT(*) FROM engagement_rules WHERE is_active = TRUE')
            active_rules = cursor.fetchone()[0]
            
            # Executions today
            cursor.execute('''
                SELECT COUNT(*) FROM engagement_executions
                WHERE DATE(executed_at) = DATE('now')
            ''')
            executions_today = cursor.fetchone()[0]
            
            # Delivery rate today
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN status = 'delivered' THEN 1 END) as delivered
                FROM engagement_executions
                WHERE DATE(executed_at) = DATE('now')
            ''')
            
            result = cursor.fetchone()
            total_today = result[0] if result[0] else 0
            delivered_today = result[1] if result[1] else 0
            delivery_rate = delivered_today / total_today if total_today > 0 else 0
            
            # Channel distribution
            cursor.execute('''
                SELECT channel, COUNT(*) as count
                FROM engagement_executions
                WHERE executed_at >= datetime('now', '-7 days')
                GROUP BY channel
                ORDER BY count DESC
            ''')
            
            channel_distribution = dict(cursor.fetchall())
            
            return {
                'active_rules': active_rules,
                'executions_today': executions_today,
                'delivery_rate_today': delivery_rate,
                'channel_distribution': channel_distribution,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting engagement dashboard data: {str(e)}")
            return {}
        finally:
            if conn:
                self.db_pool.return_connection(conn)