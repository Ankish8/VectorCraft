"""
Customer Journey Management Service
Handles customer lifecycle automation, journey mapping, and stage progression.
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

class JourneyTriggerType(Enum):
    """Types of journey triggers"""
    USER_ACTION = "user_action"
    TIME_BASED = "time_based"
    BEHAVIOR_BASED = "behavior_based"
    TRANSACTION_BASED = "transaction_based"
    ENGAGEMENT_BASED = "engagement_based"
    MANUAL = "manual"

class AutomationActionType(Enum):
    """Types of automation actions"""
    SEND_EMAIL = "send_email"
    UPDATE_SCORE = "update_score"
    ASSIGN_TAG = "assign_tag"
    CREATE_TASK = "create_task"
    SEND_NOTIFICATION = "send_notification"
    WEBHOOK_CALL = "webhook_call"
    WAIT_DELAY = "wait_delay"

@dataclass
class JourneyStep:
    """Represents a step in the customer journey"""
    step_id: str
    journey_id: str
    step_name: str
    step_type: str
    step_order: int
    trigger_conditions: Dict[str, Any]
    actions: List[Dict[str, Any]]
    success_criteria: Dict[str, Any]
    failure_criteria: Dict[str, Any]
    next_step_id: Optional[str] = None
    alternative_step_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime = None
    updated_at: datetime = None

@dataclass
class CustomerJourneyInstance:
    """Represents a customer's journey instance"""
    instance_id: str
    customer_id: str
    journey_id: str
    current_step_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    progress_percentage: float = 0.0
    last_activity: datetime = None

@dataclass
class JourneyMetrics:
    """Journey performance metrics"""
    journey_id: str
    total_entries: int
    total_completions: int
    completion_rate: float
    avg_completion_time: float
    dropout_points: Dict[str, int]
    conversion_metrics: Dict[str, Any]
    updated_at: datetime

class CustomerJourneyManager:
    """Manages customer journey automation and lifecycle progression"""
    
    def __init__(self, db_pool: DatabasePool, email_service: EmailService, 
                 system_logger: SystemLogger):
        self.db_pool = db_pool
        self.email_service = email_service
        self.system_logger = system_logger
        self.logger = logging.getLogger(__name__)
        
        # Initialize database tables
        self._init_database()
        
    def _init_database(self):
        """Initialize journey database tables"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            # Customer journeys table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customer_journeys (
                    journey_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    trigger_type TEXT NOT NULL,
                    trigger_conditions TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Journey steps table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS journey_steps (
                    step_id TEXT PRIMARY KEY,
                    journey_id TEXT NOT NULL,
                    step_name TEXT NOT NULL,
                    step_type TEXT NOT NULL,
                    step_order INTEGER NOT NULL,
                    trigger_conditions TEXT,
                    actions TEXT,
                    success_criteria TEXT,
                    failure_criteria TEXT,
                    next_step_id TEXT,
                    alternative_step_id TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (journey_id) REFERENCES customer_journeys(journey_id)
                )
            ''')
            
            # Customer journey instances table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customer_journey_instances (
                    instance_id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL,
                    journey_id TEXT NOT NULL,
                    current_step_id TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    metadata TEXT,
                    progress_percentage REAL DEFAULT 0.0,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (journey_id) REFERENCES customer_journeys(journey_id)
                )
            ''')
            
            # Journey step executions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS journey_step_executions (
                    execution_id TEXT PRIMARY KEY,
                    instance_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    customer_id TEXT NOT NULL,
                    execution_status TEXT NOT NULL,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    execution_data TEXT,
                    error_message TEXT,
                    FOREIGN KEY (instance_id) REFERENCES customer_journey_instances(instance_id),
                    FOREIGN KEY (step_id) REFERENCES journey_steps(step_id)
                )
            ''')
            
            # Journey metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS journey_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    journey_id TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    measurement_date DATE NOT NULL,
                    additional_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (journey_id) REFERENCES customer_journeys(journey_id)
                )
            ''')
            
            # Customer touchpoints table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customer_touchpoints (
                    touchpoint_id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL,
                    touchpoint_type TEXT NOT NULL,
                    touchpoint_data TEXT,
                    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    journey_instance_id TEXT,
                    FOREIGN KEY (journey_instance_id) REFERENCES customer_journey_instances(instance_id)
                )
            ''')
            
            conn.commit()
            self.logger.info("Customer journey database tables initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing journey database: {str(e)}")
            raise
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def create_journey(self, journey_data: Dict[str, Any]) -> str:
        """Create a new customer journey"""
        try:
            journey_id = f"journey_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO customer_journeys
                (journey_id, name, description, trigger_type, trigger_conditions,
                 is_active, created_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                journey_id,
                journey_data['name'],
                journey_data.get('description', ''),
                journey_data['trigger_type'],
                json.dumps(journey_data.get('trigger_conditions', {})),
                journey_data.get('is_active', True),
                journey_data.get('created_by', 'system'),
                datetime.now(),
                datetime.now()
            ))
            
            conn.commit()
            self.logger.info(f"Created customer journey: {journey_data['name']} ({journey_id})")
            
            return journey_id
            
        except Exception as e:
            self.logger.error(f"Error creating journey: {str(e)}")
            raise
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def add_journey_step(self, journey_id: str, step_data: Dict[str, Any]) -> str:
        """Add a step to a customer journey"""
        try:
            step_id = f"step_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO journey_steps
                (step_id, journey_id, step_name, step_type, step_order,
                 trigger_conditions, actions, success_criteria, failure_criteria,
                 next_step_id, alternative_step_id, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                step_id,
                journey_id,
                step_data['step_name'],
                step_data['step_type'],
                step_data['step_order'],
                json.dumps(step_data.get('trigger_conditions', {})),
                json.dumps(step_data.get('actions', [])),
                json.dumps(step_data.get('success_criteria', {})),
                json.dumps(step_data.get('failure_criteria', {})),
                step_data.get('next_step_id'),
                step_data.get('alternative_step_id'),
                step_data.get('is_active', True),
                datetime.now(),
                datetime.now()
            ))
            
            conn.commit()
            self.logger.info(f"Added step to journey {journey_id}: {step_data['step_name']}")
            
            return step_id
            
        except Exception as e:
            self.logger.error(f"Error adding journey step: {str(e)}")
            raise
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def start_customer_journey(self, customer_id: str, journey_id: str, 
                             metadata: Dict[str, Any] = None) -> str:
        """Start a journey for a customer"""
        try:
            instance_id = f"instance_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Get first step of journey
            first_step = self._get_first_journey_step(journey_id)
            if not first_step:
                raise ValueError(f"No steps found for journey {journey_id}")
            
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO customer_journey_instances
                (instance_id, customer_id, journey_id, current_step_id,
                 status, started_at, metadata, last_activity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                instance_id,
                customer_id,
                journey_id,
                first_step['step_id'],
                'active',
                datetime.now(),
                json.dumps(metadata) if metadata else None,
                datetime.now()
            ))
            
            conn.commit()
            self.logger.info(f"Started journey {journey_id} for customer {customer_id}")
            
            # Execute first step
            self._execute_journey_step(instance_id, first_step['step_id'])
            
            return instance_id
            
        except Exception as e:
            self.logger.error(f"Error starting customer journey: {str(e)}")
            raise
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _get_first_journey_step(self, journey_id: str) -> Optional[Dict[str, Any]]:
        """Get the first step of a journey"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM journey_steps
                WHERE journey_id = ? AND is_active = TRUE
                ORDER BY step_order ASC
                LIMIT 1
            ''', (journey_id,))
            
            result = cursor.fetchone()
            if not result:
                return None
            
            return {
                'step_id': result[0],
                'journey_id': result[1],
                'step_name': result[2],
                'step_type': result[3],
                'step_order': result[4],
                'trigger_conditions': json.loads(result[5]) if result[5] else {},
                'actions': json.loads(result[6]) if result[6] else [],
                'success_criteria': json.loads(result[7]) if result[7] else {},
                'failure_criteria': json.loads(result[8]) if result[8] else {},
                'next_step_id': result[9],
                'alternative_step_id': result[10]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting first journey step: {str(e)}")
            return None
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _execute_journey_step(self, instance_id: str, step_id: str) -> bool:
        """Execute a specific journey step"""
        try:
            execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Get step details
            step_details = self._get_step_details(step_id)
            if not step_details:
                return False
            
            # Get customer instance
            instance = self._get_journey_instance(instance_id)
            if not instance:
                return False
            
            # Record execution start
            self._record_step_execution(execution_id, instance_id, step_id, 
                                      instance['customer_id'], 'started')
            
            # Execute step actions
            success = self._execute_step_actions(instance['customer_id'], step_details['actions'])
            
            # Update execution status
            if success:
                self._record_step_execution(execution_id, instance_id, step_id, 
                                          instance['customer_id'], 'completed')
                
                # Move to next step if available
                if step_details['next_step_id']:
                    self._move_to_next_step(instance_id, step_details['next_step_id'])
                else:
                    # Journey completed
                    self._complete_journey_instance(instance_id)
            else:
                self._record_step_execution(execution_id, instance_id, step_id, 
                                          instance['customer_id'], 'failed')
                
                # Move to alternative step if available
                if step_details['alternative_step_id']:
                    self._move_to_next_step(instance_id, step_details['alternative_step_id'])
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error executing journey step: {str(e)}")
            return False

    def _get_step_details(self, step_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific step"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM journey_steps WHERE step_id = ?
            ''', (step_id,))
            
            result = cursor.fetchone()
            if not result:
                return None
            
            return {
                'step_id': result[0],
                'journey_id': result[1],
                'step_name': result[2],
                'step_type': result[3],
                'step_order': result[4],
                'trigger_conditions': json.loads(result[5]) if result[5] else {},
                'actions': json.loads(result[6]) if result[6] else [],
                'success_criteria': json.loads(result[7]) if result[7] else {},
                'failure_criteria': json.loads(result[8]) if result[8] else {},
                'next_step_id': result[9],
                'alternative_step_id': result[10]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting step details: {str(e)}")
            return None
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _get_journey_instance(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get journey instance details"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM customer_journey_instances WHERE instance_id = ?
            ''', (instance_id,))
            
            result = cursor.fetchone()
            if not result:
                return None
            
            return {
                'instance_id': result[0],
                'customer_id': result[1],
                'journey_id': result[2],
                'current_step_id': result[3],
                'status': result[4],
                'started_at': result[5],
                'completed_at': result[6],
                'metadata': json.loads(result[7]) if result[7] else {},
                'progress_percentage': result[8],
                'last_activity': result[9]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting journey instance: {str(e)}")
            return None
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _execute_step_actions(self, customer_id: str, actions: List[Dict[str, Any]]) -> bool:
        """Execute all actions for a step"""
        try:
            for action in actions:
                action_type = action.get('type')
                
                if action_type == 'send_email':
                    self._execute_email_action(customer_id, action)
                elif action_type == 'update_score':
                    self._execute_score_update_action(customer_id, action)
                elif action_type == 'assign_tag':
                    self._execute_tag_assignment_action(customer_id, action)
                elif action_type == 'create_task':
                    self._execute_task_creation_action(customer_id, action)
                elif action_type == 'wait_delay':
                    self._execute_wait_delay_action(customer_id, action)
                else:
                    self.logger.warning(f"Unknown action type: {action_type}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing step actions: {str(e)}")
            return False

    def _execute_email_action(self, customer_id: str, action: Dict[str, Any]):
        """Execute email sending action"""
        try:
            # Get customer email
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT email FROM users WHERE id = ?', (customer_id,))
            result = cursor.fetchone()
            
            if not result:
                return
            
            email = result[0]
            
            # Send email
            template_id = action.get('template_id')
            subject = action.get('subject', 'VectorCraft Notification')
            
            self.email_service.send_template_email(
                to_email=email,
                subject=subject,
                template_id=template_id,
                template_data={'customer_id': customer_id}
            )
            
            self.logger.info(f"Sent email to customer {customer_id} as part of journey automation")
            
        except Exception as e:
            self.logger.error(f"Error executing email action: {str(e)}")
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _execute_score_update_action(self, customer_id: str, action: Dict[str, Any]):
        """Execute lead score update action"""
        try:
            # This would integrate with the marketing manager's lead scoring
            score_change = action.get('score_change', 0)
            factor = action.get('factor', 'journey_automation')
            
            # Mock implementation - in real scenario, this would call marketing_manager
            self.logger.info(f"Updated lead score for customer {customer_id} by {score_change} points")
            
        except Exception as e:
            self.logger.error(f"Error executing score update action: {str(e)}")

    def _execute_tag_assignment_action(self, customer_id: str, action: Dict[str, Any]):
        """Execute tag assignment action"""
        try:
            tag = action.get('tag')
            if tag:
                # Store tag assignment
                conn = self.db_pool.get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO customer_tags (customer_id, tag, assigned_at)
                    VALUES (?, ?, ?)
                ''', (customer_id, tag, datetime.now()))
                
                conn.commit()
                self.logger.info(f"Assigned tag '{tag}' to customer {customer_id}")
            
        except Exception as e:
            self.logger.error(f"Error executing tag assignment action: {str(e)}")
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _execute_task_creation_action(self, customer_id: str, action: Dict[str, Any]):
        """Execute task creation action"""
        try:
            task_title = action.get('task_title', 'Customer Journey Task')
            task_description = action.get('task_description', '')
            assigned_to = action.get('assigned_to', 'system')
            
            # Create task (mock implementation)
            self.logger.info(f"Created task '{task_title}' for customer {customer_id}")
            
        except Exception as e:
            self.logger.error(f"Error executing task creation action: {str(e)}")

    def _execute_wait_delay_action(self, customer_id: str, action: Dict[str, Any]):
        """Execute wait delay action"""
        try:
            delay_minutes = action.get('delay_minutes', 0)
            
            # In a real implementation, this would schedule the next step
            # For now, we'll just log the delay
            self.logger.info(f"Scheduling {delay_minutes} minute delay for customer {customer_id}")
            
        except Exception as e:
            self.logger.error(f"Error executing wait delay action: {str(e)}")

    def _record_step_execution(self, execution_id: str, instance_id: str, 
                             step_id: str, customer_id: str, status: str):
        """Record step execution in database"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            if status == 'started':
                cursor.execute('''
                    INSERT INTO journey_step_executions
                    (execution_id, instance_id, step_id, customer_id, execution_status)
                    VALUES (?, ?, ?, ?, ?)
                ''', (execution_id, instance_id, step_id, customer_id, status))
            else:
                cursor.execute('''
                    UPDATE journey_step_executions
                    SET execution_status = ?, completed_at = ?
                    WHERE execution_id = ?
                ''', (status, datetime.now(), execution_id))
            
            conn.commit()
            
        except Exception as e:
            self.logger.error(f"Error recording step execution: {str(e)}")
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _move_to_next_step(self, instance_id: str, next_step_id: str):
        """Move journey instance to next step"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE customer_journey_instances
                SET current_step_id = ?, last_activity = ?
                WHERE instance_id = ?
            ''', (next_step_id, datetime.now(), instance_id))
            
            conn.commit()
            
            # Execute next step
            self._execute_journey_step(instance_id, next_step_id)
            
        except Exception as e:
            self.logger.error(f"Error moving to next step: {str(e)}")
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _complete_journey_instance(self, instance_id: str):
        """Complete a journey instance"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE customer_journey_instances
                SET status = 'completed', completed_at = ?, progress_percentage = 100.0
                WHERE instance_id = ?
            ''', (datetime.now(), instance_id))
            
            conn.commit()
            self.logger.info(f"Completed journey instance {instance_id}")
            
        except Exception as e:
            self.logger.error(f"Error completing journey instance: {str(e)}")
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def get_customer_journey_status(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get all journey statuses for a customer"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    ji.instance_id,
                    ji.journey_id,
                    cj.name as journey_name,
                    ji.current_step_id,
                    js.step_name,
                    ji.status,
                    ji.progress_percentage,
                    ji.started_at,
                    ji.completed_at,
                    ji.last_activity
                FROM customer_journey_instances ji
                JOIN customer_journeys cj ON ji.journey_id = cj.journey_id
                LEFT JOIN journey_steps js ON ji.current_step_id = js.step_id
                WHERE ji.customer_id = ?
                ORDER BY ji.started_at DESC
            ''', (customer_id,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'instance_id': row[0],
                    'journey_id': row[1],
                    'journey_name': row[2],
                    'current_step_id': row[3],
                    'current_step_name': row[4],
                    'status': row[5],
                    'progress_percentage': row[6],
                    'started_at': row[7],
                    'completed_at': row[8],
                    'last_activity': row[9]
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error getting customer journey status: {str(e)}")
            return []
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def get_journey_analytics(self, journey_id: str) -> Dict[str, Any]:
        """Get analytics for a specific journey"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            # Get basic journey metrics
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_entries,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as total_completions,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_instances,
                    AVG(progress_percentage) as avg_progress,
                    AVG(CASE WHEN completed_at IS NOT NULL THEN 
                        (julianday(completed_at) - julianday(started_at)) END) as avg_completion_days
                FROM customer_journey_instances
                WHERE journey_id = ?
            ''', (journey_id,))
            
            basic_metrics = cursor.fetchone()
            
            # Get step-by-step analytics
            cursor.execute('''
                SELECT 
                    js.step_name,
                    js.step_order,
                    COUNT(jse.execution_id) as executions,
                    COUNT(CASE WHEN jse.execution_status = 'completed' THEN 1 END) as completions,
                    COUNT(CASE WHEN jse.execution_status = 'failed' THEN 1 END) as failures
                FROM journey_steps js
                LEFT JOIN journey_step_executions jse ON js.step_id = jse.step_id
                WHERE js.journey_id = ?
                GROUP BY js.step_id, js.step_name, js.step_order
                ORDER BY js.step_order
            ''', (journey_id,))
            
            step_analytics = []
            for row in cursor.fetchall():
                step_analytics.append({
                    'step_name': row[0],
                    'step_order': row[1],
                    'executions': row[2],
                    'completions': row[3],
                    'failures': row[4],
                    'success_rate': row[3] / row[2] if row[2] > 0 else 0
                })
            
            total_entries = basic_metrics[0] if basic_metrics[0] else 0
            total_completions = basic_metrics[1] if basic_metrics[1] else 0
            
            return {
                'journey_id': journey_id,
                'total_entries': total_entries,
                'total_completions': total_completions,
                'active_instances': basic_metrics[2] if basic_metrics[2] else 0,
                'completion_rate': total_completions / total_entries if total_entries > 0 else 0,
                'avg_progress': basic_metrics[3] if basic_metrics[3] else 0,
                'avg_completion_days': basic_metrics[4] if basic_metrics[4] else 0,
                'step_analytics': step_analytics,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting journey analytics: {str(e)}")
            return {}
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def get_all_journeys(self) -> List[Dict[str, Any]]:
        """Get all customer journeys"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    cj.journey_id,
                    cj.name,
                    cj.description,
                    cj.trigger_type,
                    cj.is_active,
                    cj.created_at,
                    COUNT(ji.instance_id) as total_instances,
                    COUNT(CASE WHEN ji.status = 'completed' THEN 1 END) as completed_instances
                FROM customer_journeys cj
                LEFT JOIN customer_journey_instances ji ON cj.journey_id = ji.journey_id
                GROUP BY cj.journey_id, cj.name, cj.description, cj.trigger_type, cj.is_active, cj.created_at
                ORDER BY cj.created_at DESC
            ''')
            
            journeys = []
            for row in cursor.fetchall():
                total_instances = row[6] if row[6] else 0
                completed_instances = row[7] if row[7] else 0
                
                journeys.append({
                    'journey_id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'trigger_type': row[3],
                    'is_active': row[4],
                    'created_at': row[5],
                    'total_instances': total_instances,
                    'completed_instances': completed_instances,
                    'completion_rate': completed_instances / total_instances if total_instances > 0 else 0
                })
            
            return journeys
            
        except Exception as e:
            self.logger.error(f"Error getting all journeys: {str(e)}")
            return []
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def record_customer_touchpoint(self, customer_id: str, touchpoint_type: str, 
                                  touchpoint_data: Dict[str, Any]):
        """Record a customer touchpoint"""
        try:
            touchpoint_id = f"touchpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO customer_touchpoints
                (touchpoint_id, customer_id, touchpoint_type, touchpoint_data, occurred_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                touchpoint_id,
                customer_id,
                touchpoint_type,
                json.dumps(touchpoint_data),
                datetime.now()
            ))
            
            conn.commit()
            
            # Check if this touchpoint should trigger any journeys
            self._check_journey_triggers(customer_id, touchpoint_type, touchpoint_data)
            
        except Exception as e:
            self.logger.error(f"Error recording customer touchpoint: {str(e)}")
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _check_journey_triggers(self, customer_id: str, touchpoint_type: str, 
                               touchpoint_data: Dict[str, Any]):
        """Check if any journeys should be triggered by this touchpoint"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            # Get active journeys with matching trigger types
            cursor.execute('''
                SELECT journey_id, trigger_conditions
                FROM customer_journeys
                WHERE is_active = TRUE AND trigger_type = ?
            ''', (touchpoint_type,))
            
            for journey_id, trigger_conditions_json in cursor.fetchall():
                trigger_conditions = json.loads(trigger_conditions_json) if trigger_conditions_json else {}
                
                # Check if conditions are met
                if self._evaluate_trigger_conditions(touchpoint_data, trigger_conditions):
                    # Check if customer is not already in this journey
                    cursor.execute('''
                        SELECT COUNT(*) FROM customer_journey_instances
                        WHERE customer_id = ? AND journey_id = ? AND status = 'active'
                    ''', (customer_id, journey_id))
                    
                    if cursor.fetchone()[0] == 0:
                        # Start journey
                        self.start_customer_journey(customer_id, journey_id, touchpoint_data)
            
        except Exception as e:
            self.logger.error(f"Error checking journey triggers: {str(e)}")
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _evaluate_trigger_conditions(self, touchpoint_data: Dict[str, Any], 
                                   trigger_conditions: Dict[str, Any]) -> bool:
        """Evaluate if trigger conditions are met"""
        try:
            # Simple condition evaluation - in real implementation, this would be more sophisticated
            for key, expected_value in trigger_conditions.items():
                if key not in touchpoint_data:
                    return False
                
                actual_value = touchpoint_data[key]
                
                if isinstance(expected_value, dict):
                    # Handle operators like {">=": 100}
                    for operator, value in expected_value.items():
                        if operator == ">=" and actual_value < value:
                            return False
                        elif operator == "<=" and actual_value > value:
                            return False
                        elif operator == "==" and actual_value != value:
                            return False
                elif actual_value != expected_value:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error evaluating trigger conditions: {str(e)}")
            return False

    def update_journey_progress(self, instance_id: str, progress_percentage: float):
        """Update journey progress percentage"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE customer_journey_instances
                SET progress_percentage = ?, last_activity = ?
                WHERE instance_id = ?
            ''', (progress_percentage, datetime.now(), instance_id))
            
            conn.commit()
            
        except Exception as e:
            self.logger.error(f"Error updating journey progress: {str(e)}")
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def get_journey_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard data for journey management"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            # Active journeys count
            cursor.execute('SELECT COUNT(*) FROM customer_journeys WHERE is_active = TRUE')
            active_journeys = cursor.fetchone()[0]
            
            # Active instances count
            cursor.execute('SELECT COUNT(*) FROM customer_journey_instances WHERE status = "active"')
            active_instances = cursor.fetchone()[0]
            
            # Completed instances today
            cursor.execute('''
                SELECT COUNT(*) FROM customer_journey_instances
                WHERE status = "completed" AND DATE(completed_at) = DATE('now')
            ''')
            completed_today = cursor.fetchone()[0]
            
            # Journey performance summary
            cursor.execute('''
                SELECT 
                    journey_id,
                    COUNT(*) as total_instances,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_instances,
                    AVG(progress_percentage) as avg_progress
                FROM customer_journey_instances
                GROUP BY journey_id
                ORDER BY total_instances DESC
                LIMIT 5
            ''')
            
            top_journeys = []
            for row in cursor.fetchall():
                total = row[1]
                completed = row[2]
                top_journeys.append({
                    'journey_id': row[0],
                    'total_instances': total,
                    'completed_instances': completed,
                    'completion_rate': completed / total if total > 0 else 0,
                    'avg_progress': row[3] if row[3] else 0
                })
            
            return {
                'active_journeys': active_journeys,
                'active_instances': active_instances,
                'completed_today': completed_today,
                'top_journeys': top_journeys,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting journey dashboard data: {str(e)}")
            return {}
        finally:
            if conn:
                self.db_pool.return_connection(conn)