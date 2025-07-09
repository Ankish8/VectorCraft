#!/usr/bin/env python3
"""
Marketing Automation Service
Advanced behavioral triggers and automated email sequences for VectorCraft
"""

import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import time
from collections import defaultdict, deque
import schedule

logger = logging.getLogger(__name__)

class TriggerEvent(Enum):
    USER_SIGNUP = "user_signup"
    FIRST_LOGIN = "first_login"
    PURCHASE_COMPLETE = "purchase_complete"
    CART_ABANDONMENT = "cart_abandonment"
    PROFILE_UPDATE = "profile_update"
    FEATURE_USAGE = "feature_usage"
    INACTIVITY = "inactivity"
    SUBSCRIPTION_EXPIRY = "subscription_expiry"
    FEEDBACK_SUBMITTED = "feedback_submitted"
    SUPPORT_TICKET = "support_ticket"
    EMAIL_OPENED = "email_opened"
    EMAIL_CLICKED = "email_clicked"
    ANNIVERSARY = "anniversary"
    BIRTHDAY = "birthday"
    CONVERSION_GOAL = "conversion_goal"

class ActionType(Enum):
    SEND_EMAIL = "send_email"
    WAIT = "wait"
    CONDITION_CHECK = "condition_check"
    UPDATE_PROFILE = "update_profile"
    ADD_TO_SEGMENT = "add_to_segment"
    REMOVE_FROM_SEGMENT = "remove_from_segment"
    TRIGGER_WEBHOOK = "trigger_webhook"
    SCHEDULE_FOLLOWUP = "schedule_followup"
    SEND_NOTIFICATION = "send_notification"
    LOG_EVENT = "log_event"

class AutomationStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class TriggerCondition:
    """Trigger condition for automation"""
    event_type: TriggerEvent
    conditions: Dict[str, Any]
    delay_minutes: int = 0
    max_triggers: int = 0  # 0 = unlimited
    cooldown_hours: int = 0
    
@dataclass
class AutomationAction:
    """Action to execute in automation"""
    action_type: ActionType
    parameters: Dict[str, Any]
    delay_minutes: int = 0
    condition: Optional[Dict[str, Any]] = None
    is_required: bool = True
    
@dataclass
class AutomationRule:
    """Marketing automation rule"""
    rule_id: str
    name: str
    description: str
    trigger: TriggerCondition
    actions: List[AutomationAction]
    is_active: bool = True
    created_at: datetime = None
    updated_at: datetime = None
    created_by: str = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class AutomationExecution:
    """Automation execution instance"""
    execution_id: str
    rule_id: str
    user_id: str
    trigger_data: Dict[str, Any]
    current_step: int = 0
    status: AutomationStatus = AutomationStatus.ACTIVE
    started_at: datetime = None
    completed_at: datetime = None
    error_message: str = None
    
    def __post_init__(self):
        if self.started_at is None:
            self.started_at = datetime.now()

class MarketingAutomation:
    """Advanced marketing automation service"""
    
    def __init__(self, db_instance=None):
        self.logger = logging.getLogger(__name__)
        
        # Import database
        if db_instance:
            self.db = db_instance
        else:
            from database import db
            self.db = db
        
        # Import services
        try:
            from services.email_campaign_manager import email_campaign_manager
            self.campaign_manager = email_campaign_manager
        except ImportError:
            self.campaign_manager = None
            
        try:
            from services.email_service import email_service
            self.email_service = email_service
        except ImportError:
            self.email_service = None
        
        # Automation rules and executions
        self.automation_rules = {}
        self.active_executions = {}
        self.pending_actions = deque()
        
        # Event tracking
        self.event_history = defaultdict(list)
        self.user_states = {}
        
        # Performance tracking
        self.automation_metrics = defaultdict(lambda: {
            'triggered': 0,
            'completed': 0,
            'failed': 0,
            'conversion_rate': 0
        })
        
        # Configuration
        self.is_running = True
        self.max_concurrent_executions = 100
        self.execution_timeout_hours = 24
        
        # Start background services
        self._start_background_services()
        
        # Load existing rules
        self._load_automation_rules()
        
        self.logger.info("Marketing Automation service initialized")
    
    def _start_background_services(self):
        """Start background processing threads"""
        # Action executor thread
        self.executor_thread = threading.Thread(target=self._execute_actions, daemon=True)
        self.executor_thread.start()
        
        # Scheduler thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        # Cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_executions, daemon=True)
        self.cleanup_thread.start()
    
    def _load_automation_rules(self):
        """Load automation rules from database"""
        try:
            rules_data = self.db.get_automation_rules()
            for rule_data in rules_data:
                rule = self._deserialize_rule(rule_data)
                self.automation_rules[rule.rule_id] = rule
                
            self.logger.info(f"Loaded {len(self.automation_rules)} automation rules")
            
        except Exception as e:
            self.logger.error(f"Error loading automation rules: {str(e)}")
    
    # Rule Management
    def create_automation_rule(self, name: str, description: str, 
                             trigger: Dict[str, Any], actions: List[Dict[str, Any]],
                             created_by: str = None, tags: List[str] = None) -> str:
        """Create a new automation rule"""
        try:
            rule_id = str(uuid.uuid4())
            
            # Convert trigger and actions to dataclasses
            trigger_condition = TriggerCondition(
                event_type=TriggerEvent(trigger['event_type']),
                conditions=trigger.get('conditions', {}),
                delay_minutes=trigger.get('delay_minutes', 0),
                max_triggers=trigger.get('max_triggers', 0),
                cooldown_hours=trigger.get('cooldown_hours', 0)
            )
            
            automation_actions = []
            for action in actions:
                automation_actions.append(AutomationAction(
                    action_type=ActionType(action['action_type']),
                    parameters=action.get('parameters', {}),
                    delay_minutes=action.get('delay_minutes', 0),
                    condition=action.get('condition'),
                    is_required=action.get('is_required', True)
                ))
            
            rule = AutomationRule(
                rule_id=rule_id,
                name=name,
                description=description,
                trigger=trigger_condition,
                actions=automation_actions,
                created_by=created_by,
                tags=tags or []
            )
            
            # Save to database
            self.db.create_automation_rule(
                rule_id=rule_id,
                name=name,
                description=description,
                trigger=json.dumps(asdict(trigger_condition)),
                actions=json.dumps([asdict(action) for action in automation_actions]),
                created_by=created_by,
                tags=json.dumps(tags or [])
            )
            
            # Store in memory
            self.automation_rules[rule_id] = rule
            
            self.logger.info(f"Automation rule created: {rule_id} - {name}")
            return rule_id
            
        except Exception as e:
            self.logger.error(f"Error creating automation rule: {str(e)}")
            raise
    
    def update_automation_rule(self, rule_id: str, **kwargs) -> bool:
        """Update an existing automation rule"""
        try:
            if rule_id not in self.automation_rules:
                return False
            
            rule = self.automation_rules[rule_id]
            
            # Update allowed fields
            if 'name' in kwargs:
                rule.name = kwargs['name']
            if 'description' in kwargs:
                rule.description = kwargs['description']
            if 'is_active' in kwargs:
                rule.is_active = kwargs['is_active']
            if 'tags' in kwargs:
                rule.tags = kwargs['tags']
            
            rule.updated_at = datetime.now()
            
            # Update in database
            update_data = {k: v for k, v in kwargs.items() if k in ['name', 'description', 'is_active']}
            if 'tags' in kwargs:
                update_data['tags'] = json.dumps(kwargs['tags'])
            update_data['updated_at'] = rule.updated_at
            
            success = self.db.update_automation_rule(rule_id, **update_data)
            
            if success:
                self.logger.info(f"Automation rule updated: {rule_id}")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error updating automation rule: {str(e)}")
            return False
    
    def get_automation_rule(self, rule_id: str) -> Optional[AutomationRule]:
        """Get automation rule by ID"""
        return self.automation_rules.get(rule_id)
    
    def get_automation_rules(self, is_active: bool = None, 
                           tags: List[str] = None) -> List[AutomationRule]:
        """Get list of automation rules"""
        rules = list(self.automation_rules.values())
        
        if is_active is not None:
            rules = [r for r in rules if r.is_active == is_active]
        
        if tags:
            rules = [r for r in rules if any(tag in r.tags for tag in tags)]
        
        return rules
    
    def delete_automation_rule(self, rule_id: str) -> bool:
        """Delete automation rule"""
        try:
            if rule_id not in self.automation_rules:
                return False
            
            # Cancel any active executions
            executions_to_cancel = [
                exec_id for exec_id, execution in self.active_executions.items()
                if execution.rule_id == rule_id
            ]
            
            for exec_id in executions_to_cancel:
                self.cancel_execution(exec_id)
            
            # Remove from database
            success = self.db.delete_automation_rule(rule_id)
            
            if success:
                # Remove from memory
                del self.automation_rules[rule_id]
                self.logger.info(f"Automation rule deleted: {rule_id}")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error deleting automation rule: {str(e)}")
            return False
    
    # Event Processing
    def trigger_event(self, event_type: str, user_id: str, 
                     event_data: Dict[str, Any] = None) -> List[str]:
        """Trigger automation based on event"""
        try:
            event_data = event_data or {}
            event_enum = TriggerEvent(event_type)
            
            # Log event
            self.event_history[user_id].append({
                'event_type': event_type,
                'event_data': event_data,
                'timestamp': datetime.now()
            })
            
            # Keep only last 100 events per user
            if len(self.event_history[user_id]) > 100:
                self.event_history[user_id] = self.event_history[user_id][-100:]
            
            # Find matching rules
            matching_rules = []
            for rule in self.automation_rules.values():
                if not rule.is_active:
                    continue
                    
                if rule.trigger.event_type == event_enum:
                    if self._check_trigger_conditions(rule.trigger, user_id, event_data):
                        matching_rules.append(rule)
            
            # Execute matching rules
            execution_ids = []
            for rule in matching_rules:
                execution_id = self._start_execution(rule, user_id, event_data)
                if execution_id:
                    execution_ids.append(execution_id)
            
            self.logger.info(f"Event triggered: {event_type} for user {user_id} - {len(execution_ids)} automations started")
            return execution_ids
            
        except Exception as e:
            self.logger.error(f"Error triggering event: {str(e)}")
            return []
    
    def _check_trigger_conditions(self, trigger: TriggerCondition, user_id: str, 
                                event_data: Dict[str, Any]) -> bool:
        """Check if trigger conditions are met"""
        try:
            # Check cooldown
            if trigger.cooldown_hours > 0:
                last_trigger = self._get_last_trigger_time(trigger.event_type, user_id)
                if last_trigger:
                    cooldown_end = last_trigger + timedelta(hours=trigger.cooldown_hours)
                    if datetime.now() < cooldown_end:
                        return False
            
            # Check max triggers
            if trigger.max_triggers > 0:
                trigger_count = self._get_trigger_count(trigger.event_type, user_id)
                if trigger_count >= trigger.max_triggers:
                    return False
            
            # Check custom conditions
            for condition_key, condition_value in trigger.conditions.items():
                if not self._evaluate_condition(condition_key, condition_value, user_id, event_data):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking trigger conditions: {str(e)}")
            return False
    
    def _evaluate_condition(self, condition_key: str, condition_value: Any, 
                          user_id: str, event_data: Dict[str, Any]) -> bool:
        """Evaluate a single condition"""
        try:
            if condition_key.startswith('event.'):
                # Event data condition
                event_key = condition_key[6:]  # Remove 'event.' prefix
                actual_value = event_data.get(event_key)
                
                if isinstance(condition_value, dict):
                    # Complex condition (e.g., {'>=': 100})
                    for operator, expected_value in condition_value.items():
                        if operator == '>=':
                            return actual_value >= expected_value
                        elif operator == '<=':
                            return actual_value <= expected_value
                        elif operator == '>':
                            return actual_value > expected_value
                        elif operator == '<':
                            return actual_value < expected_value
                        elif operator == '==':
                            return actual_value == expected_value
                        elif operator == '!=':
                            return actual_value != expected_value
                        elif operator == 'in':
                            return actual_value in expected_value
                        elif operator == 'not_in':
                            return actual_value not in expected_value
                else:
                    # Simple equality
                    return actual_value == condition_value
                    
            elif condition_key.startswith('user.'):
                # User attribute condition
                user_key = condition_key[5:]  # Remove 'user.' prefix
                user_data = self._get_user_data(user_id)
                actual_value = user_data.get(user_key)
                return actual_value == condition_value
                
            elif condition_key.startswith('history.'):
                # Event history condition
                history_key = condition_key[8:]  # Remove 'history.' prefix
                return self._evaluate_history_condition(history_key, condition_value, user_id)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error evaluating condition: {str(e)}")
            return False
    
    def _evaluate_history_condition(self, history_key: str, condition_value: Any, 
                                  user_id: str) -> bool:
        """Evaluate history-based condition"""
        try:
            user_history = self.event_history.get(user_id, [])
            
            if history_key == 'event_count':
                # Count events of specific type
                event_type = condition_value.get('event_type')
                days = condition_value.get('days', 30)
                min_count = condition_value.get('min_count', 1)
                
                cutoff_date = datetime.now() - timedelta(days=days)
                count = sum(1 for event in user_history 
                           if event['event_type'] == event_type and 
                           event['timestamp'] >= cutoff_date)
                
                return count >= min_count
                
            elif history_key == 'last_event':
                # Check when last event occurred
                event_type = condition_value.get('event_type')
                max_hours_ago = condition_value.get('max_hours_ago', 24)
                
                cutoff_time = datetime.now() - timedelta(hours=max_hours_ago)
                
                for event in reversed(user_history):
                    if event['event_type'] == event_type:
                        return event['timestamp'] >= cutoff_time
                
                return False
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error evaluating history condition: {str(e)}")
            return False
    
    # Execution Management
    def _start_execution(self, rule: AutomationRule, user_id: str, 
                        trigger_data: Dict[str, Any]) -> Optional[str]:
        """Start automation execution"""
        try:
            execution_id = str(uuid.uuid4())
            
            execution = AutomationExecution(
                execution_id=execution_id,
                rule_id=rule.rule_id,
                user_id=user_id,
                trigger_data=trigger_data
            )
            
            # Store execution
            self.active_executions[execution_id] = execution
            
            # Log execution start
            self.db.log_automation_execution(
                execution_id=execution_id,
                rule_id=rule.rule_id,
                user_id=user_id,
                trigger_data=json.dumps(trigger_data),
                status='started'
            )
            
            # Schedule first action
            if rule.actions:
                first_action = rule.actions[0]
                self._schedule_action(execution_id, 0, first_action.delay_minutes)
            
            # Update metrics
            self.automation_metrics[rule.rule_id]['triggered'] += 1
            
            self.logger.info(f"Automation execution started: {execution_id} for rule {rule.rule_id}")
            return execution_id
            
        except Exception as e:
            self.logger.error(f"Error starting execution: {str(e)}")
            return None
    
    def _schedule_action(self, execution_id: str, action_index: int, delay_minutes: int = 0):
        """Schedule action for execution"""
        try:
            execute_at = datetime.now() + timedelta(minutes=delay_minutes)
            
            action_item = {
                'execution_id': execution_id,
                'action_index': action_index,
                'execute_at': execute_at,
                'scheduled_at': datetime.now()
            }
            
            self.pending_actions.append(action_item)
            
        except Exception as e:
            self.logger.error(f"Error scheduling action: {str(e)}")
    
    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel automation execution"""
        try:
            if execution_id not in self.active_executions:
                return False
            
            execution = self.active_executions[execution_id]
            execution.status = AutomationStatus.CANCELLED
            execution.completed_at = datetime.now()
            
            # Update database
            self.db.update_automation_execution(
                execution_id,
                status='cancelled',
                completed_at=execution.completed_at
            )
            
            # Remove from active executions
            del self.active_executions[execution_id]
            
            self.logger.info(f"Automation execution cancelled: {execution_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cancelling execution: {str(e)}")
            return False
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution status"""
        try:
            if execution_id in self.active_executions:
                execution = self.active_executions[execution_id]
                return {
                    'execution_id': execution_id,
                    'rule_id': execution.rule_id,
                    'user_id': execution.user_id,
                    'current_step': execution.current_step,
                    'status': execution.status.value,
                    'started_at': execution.started_at.isoformat(),
                    'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
                    'error_message': execution.error_message
                }
            
            # Check database for completed executions
            execution_data = self.db.get_automation_execution(execution_id)
            return execution_data
            
        except Exception as e:
            self.logger.error(f"Error getting execution status: {str(e)}")
            return None
    
    def get_user_executions(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get executions for a user"""
        try:
            # Get active executions
            active_executions = [
                {
                    'execution_id': execution.execution_id,
                    'rule_id': execution.rule_id,
                    'status': execution.status.value,
                    'started_at': execution.started_at.isoformat(),
                    'current_step': execution.current_step
                }
                for execution in self.active_executions.values()
                if execution.user_id == user_id
            ]
            
            # Get completed executions from database
            completed_executions = self.db.get_user_automation_executions(user_id, limit)
            
            # Combine and sort
            all_executions = active_executions + completed_executions
            all_executions.sort(key=lambda x: x.get('started_at', ''), reverse=True)
            
            return all_executions[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting user executions: {str(e)}")
            return []
    
    # Action Execution
    def _execute_actions(self):
        """Background thread to execute pending actions"""
        while self.is_running:
            try:
                if not self.pending_actions:
                    time.sleep(5)
                    continue
                
                # Get actions ready for execution
                current_time = datetime.now()
                ready_actions = []
                
                # Process actions in order
                while self.pending_actions:
                    action = self.pending_actions[0]
                    if action['execute_at'] <= current_time:
                        ready_actions.append(self.pending_actions.popleft())
                    else:
                        break
                
                # Execute ready actions
                for action in ready_actions:
                    self._execute_action(action)
                
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error in action executor: {str(e)}")
                time.sleep(10)
    
    def _execute_action(self, action_item: Dict[str, Any]):
        """Execute a single action"""
        try:
            execution_id = action_item['execution_id']
            action_index = action_item['action_index']
            
            # Get execution
            execution = self.active_executions.get(execution_id)
            if not execution or execution.status != AutomationStatus.ACTIVE:
                return
            
            # Get rule and action
            rule = self.automation_rules.get(execution.rule_id)
            if not rule or action_index >= len(rule.actions):
                return
            
            action = rule.actions[action_index]
            
            # Check action condition
            if action.condition:
                if not self._evaluate_action_condition(action.condition, execution):
                    # Skip to next action
                    self._proceed_to_next_action(execution, action_index)
                    return
            
            # Execute action
            success = self._execute_action_by_type(action, execution)
            
            if success or not action.is_required:
                # Proceed to next action
                self._proceed_to_next_action(execution, action_index)
            else:
                # Mark execution as failed
                execution.status = AutomationStatus.FAILED
                execution.completed_at = datetime.now()
                execution.error_message = f"Required action failed: {action.action_type.value}"
                
                # Update database
                self.db.update_automation_execution(
                    execution_id,
                    status='failed',
                    completed_at=execution.completed_at,
                    error_message=execution.error_message
                )
                
                # Remove from active executions
                del self.active_executions[execution_id]
                
                # Update metrics
                self.automation_metrics[rule.rule_id]['failed'] += 1
            
        except Exception as e:
            self.logger.error(f"Error executing action: {str(e)}")
    
    def _execute_action_by_type(self, action: AutomationAction, 
                              execution: AutomationExecution) -> bool:
        """Execute action based on type"""
        try:
            if action.action_type == ActionType.SEND_EMAIL:
                return self._execute_send_email_action(action, execution)
            elif action.action_type == ActionType.WAIT:
                return self._execute_wait_action(action, execution)
            elif action.action_type == ActionType.CONDITION_CHECK:
                return self._execute_condition_check_action(action, execution)
            elif action.action_type == ActionType.UPDATE_PROFILE:
                return self._execute_update_profile_action(action, execution)
            elif action.action_type == ActionType.ADD_TO_SEGMENT:
                return self._execute_add_to_segment_action(action, execution)
            elif action.action_type == ActionType.REMOVE_FROM_SEGMENT:
                return self._execute_remove_from_segment_action(action, execution)
            elif action.action_type == ActionType.TRIGGER_WEBHOOK:
                return self._execute_trigger_webhook_action(action, execution)
            elif action.action_type == ActionType.SCHEDULE_FOLLOWUP:
                return self._execute_schedule_followup_action(action, execution)
            elif action.action_type == ActionType.SEND_NOTIFICATION:
                return self._execute_send_notification_action(action, execution)
            elif action.action_type == ActionType.LOG_EVENT:
                return self._execute_log_event_action(action, execution)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error executing action by type: {str(e)}")
            return False
    
    def _execute_send_email_action(self, action: AutomationAction, 
                                 execution: AutomationExecution) -> bool:
        """Execute send email action"""
        try:
            template_id = action.parameters.get('template_id')
            subject = action.parameters.get('subject')
            
            if not template_id and not subject:
                return False
            
            # Get user data
            user_data = self._get_user_data(execution.user_id)
            if not user_data or not user_data.get('email'):
                return False
            
            # Prepare email variables
            email_variables = {
                'user_id': execution.user_id,
                'name': user_data.get('name', 'Valued Customer'),
                'email': user_data.get('email'),
                'first_name': user_data.get('name', '').split(' ')[0] if user_data.get('name') else 'Friend'
            }
            
            # Add trigger data
            email_variables.update(execution.trigger_data)
            
            # Add custom variables
            email_variables.update(action.parameters.get('variables', {}))
            
            if template_id and self.campaign_manager:
                # Use template
                success = self.campaign_manager.test_template(
                    template_id,
                    user_data['email'],
                    email_variables
                )
            else:
                # Use direct email
                body_text = action.parameters.get('body_text', '')
                body_html = action.parameters.get('body_html', '')
                
                # Simple variable replacement
                for var, value in email_variables.items():
                    subject = subject.replace(f'{{{{{var}}}}}', str(value))
                    body_text = body_text.replace(f'{{{{{var}}}}}', str(value))
                    body_html = body_html.replace(f'{{{{{var}}}}}', str(value))
                
                # Send email
                message = self.email_service._create_message(
                    user_data['email'],
                    subject,
                    body_text,
                    body_html
                )
                
                success = self.email_service._send_email(
                    message,
                    email_type='automation',
                    transaction_id=execution.execution_id
                )
            
            if success:
                self.logger.info(f"Automation email sent to {user_data['email']}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error executing send email action: {str(e)}")
            return False
    
    def _execute_wait_action(self, action: AutomationAction, 
                           execution: AutomationExecution) -> bool:
        """Execute wait action"""
        try:
            # Wait is handled by scheduling next action with delay
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing wait action: {str(e)}")
            return False
    
    def _execute_condition_check_action(self, action: AutomationAction, 
                                      execution: AutomationExecution) -> bool:
        """Execute condition check action"""
        try:
            conditions = action.parameters.get('conditions', {})
            user_data = self._get_user_data(execution.user_id)
            
            for condition_key, condition_value in conditions.items():
                if not self._evaluate_condition(condition_key, condition_value, 
                                              execution.user_id, user_data):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing condition check action: {str(e)}")
            return False
    
    def _execute_update_profile_action(self, action: AutomationAction, 
                                     execution: AutomationExecution) -> bool:
        """Execute update profile action"""
        try:
            updates = action.parameters.get('updates', {})
            
            # Update user profile in database
            success = self.db.update_user_profile(execution.user_id, updates)
            
            if success:
                self.logger.info(f"Profile updated for user {execution.user_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error executing update profile action: {str(e)}")
            return False
    
    def _execute_add_to_segment_action(self, action: AutomationAction, 
                                     execution: AutomationExecution) -> bool:
        """Execute add to segment action"""
        try:
            segment_id = action.parameters.get('segment_id')
            if not segment_id:
                return False
            
            # Add user to segment
            success = self.db.add_user_to_segment(execution.user_id, segment_id)
            
            if success:
                self.logger.info(f"User {execution.user_id} added to segment {segment_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error executing add to segment action: {str(e)}")
            return False
    
    def _execute_remove_from_segment_action(self, action: AutomationAction, 
                                          execution: AutomationExecution) -> bool:
        """Execute remove from segment action"""
        try:
            segment_id = action.parameters.get('segment_id')
            if not segment_id:
                return False
            
            # Remove user from segment
            success = self.db.remove_user_from_segment(execution.user_id, segment_id)
            
            if success:
                self.logger.info(f"User {execution.user_id} removed from segment {segment_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error executing remove from segment action: {str(e)}")
            return False
    
    def _execute_trigger_webhook_action(self, action: AutomationAction, 
                                      execution: AutomationExecution) -> bool:
        """Execute trigger webhook action"""
        try:
            import requests
            
            url = action.parameters.get('url')
            method = action.parameters.get('method', 'POST')
            headers = action.parameters.get('headers', {})
            
            if not url:
                return False
            
            # Prepare payload
            payload = {
                'execution_id': execution.execution_id,
                'user_id': execution.user_id,
                'trigger_data': execution.trigger_data,
                'timestamp': datetime.now().isoformat()
            }
            
            # Add custom data
            payload.update(action.parameters.get('data', {}))
            
            # Send webhook
            response = requests.request(
                method,
                url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code < 400:
                self.logger.info(f"Webhook triggered successfully: {url}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error executing trigger webhook action: {str(e)}")
            return False
    
    def _execute_schedule_followup_action(self, action: AutomationAction, 
                                        execution: AutomationExecution) -> bool:
        """Execute schedule followup action"""
        try:
            # Schedule a new automation execution
            rule_id = action.parameters.get('rule_id')
            delay_hours = action.parameters.get('delay_hours', 24)
            
            if not rule_id:
                return False
            
            # Schedule for later execution
            execute_at = datetime.now() + timedelta(hours=delay_hours)
            
            # Create scheduled task
            self.db.create_scheduled_task(
                task_type='automation_followup',
                user_id=execution.user_id,
                rule_id=rule_id,
                execute_at=execute_at,
                parameters=json.dumps(action.parameters)
            )
            
            self.logger.info(f"Followup scheduled for user {execution.user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing schedule followup action: {str(e)}")
            return False
    
    def _execute_send_notification_action(self, action: AutomationAction, 
                                        execution: AutomationExecution) -> bool:
        """Execute send notification action"""
        try:
            notification_type = action.parameters.get('type', 'info')
            title = action.parameters.get('title', '')
            message = action.parameters.get('message', '')
            
            # Create notification
            notification_id = str(uuid.uuid4())
            
            success = self.db.create_notification(
                notification_id=notification_id,
                user_id=execution.user_id,
                notification_type=notification_type,
                title=title,
                message=message,
                category='automation'
            )
            
            if success:
                self.logger.info(f"Notification sent to user {execution.user_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error executing send notification action: {str(e)}")
            return False
    
    def _execute_log_event_action(self, action: AutomationAction, 
                                execution: AutomationExecution) -> bool:
        """Execute log event action"""
        try:
            event_type = action.parameters.get('event_type', 'automation_event')
            event_data = action.parameters.get('event_data', {})
            
            # Log event
            self.db.log_user_event(
                user_id=execution.user_id,
                event_type=event_type,
                event_data=json.dumps(event_data),
                source='automation'
            )
            
            self.logger.info(f"Event logged for user {execution.user_id}: {event_type}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing log event action: {str(e)}")
            return False
    
    def _proceed_to_next_action(self, execution: AutomationExecution, current_index: int):
        """Proceed to next action in sequence"""
        try:
            rule = self.automation_rules.get(execution.rule_id)
            if not rule:
                return
            
            next_index = current_index + 1
            execution.current_step = next_index
            
            if next_index < len(rule.actions):
                # Schedule next action
                next_action = rule.actions[next_index]
                self._schedule_action(execution.execution_id, next_index, next_action.delay_minutes)
            else:
                # Execution completed
                execution.status = AutomationStatus.COMPLETED
                execution.completed_at = datetime.now()
                
                # Update database
                self.db.update_automation_execution(
                    execution.execution_id,
                    status='completed',
                    completed_at=execution.completed_at
                )
                
                # Remove from active executions
                del self.active_executions[execution.execution_id]
                
                # Update metrics
                self.automation_metrics[rule.rule_id]['completed'] += 1
                
                self.logger.info(f"Automation execution completed: {execution.execution_id}")
            
        except Exception as e:
            self.logger.error(f"Error proceeding to next action: {str(e)}")
    
    def _evaluate_action_condition(self, condition: Dict[str, Any], 
                                 execution: AutomationExecution) -> bool:
        """Evaluate action condition"""
        try:
            user_data = self._get_user_data(execution.user_id)
            
            for condition_key, condition_value in condition.items():
                if not self._evaluate_condition(condition_key, condition_value, 
                                              execution.user_id, user_data):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error evaluating action condition: {str(e)}")
            return False
    
    # Helper Methods
    def _get_user_data(self, user_id: str) -> Dict[str, Any]:
        """Get user data from database"""
        try:
            return self.db.get_user_data(user_id) or {}
            
        except Exception as e:
            self.logger.error(f"Error getting user data: {str(e)}")
            return {}
    
    def _get_last_trigger_time(self, event_type: TriggerEvent, user_id: str) -> Optional[datetime]:
        """Get last trigger time for event type"""
        try:
            user_history = self.event_history.get(user_id, [])
            
            for event in reversed(user_history):
                if event['event_type'] == event_type.value:
                    return event['timestamp']
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting last trigger time: {str(e)}")
            return None
    
    def _get_trigger_count(self, event_type: TriggerEvent, user_id: str) -> int:
        """Get trigger count for event type"""
        try:
            user_history = self.event_history.get(user_id, [])
            
            count = sum(1 for event in user_history 
                       if event['event_type'] == event_type.value)
            
            return count
            
        except Exception as e:
            self.logger.error(f"Error getting trigger count: {str(e)}")
            return 0
    
    def _deserialize_rule(self, rule_data: Dict[str, Any]) -> AutomationRule:
        """Deserialize rule from database"""
        try:
            trigger_data = json.loads(rule_data['trigger'])
            actions_data = json.loads(rule_data['actions'])
            
            trigger = TriggerCondition(
                event_type=TriggerEvent(trigger_data['event_type']),
                conditions=trigger_data['conditions'],
                delay_minutes=trigger_data.get('delay_minutes', 0),
                max_triggers=trigger_data.get('max_triggers', 0),
                cooldown_hours=trigger_data.get('cooldown_hours', 0)
            )
            
            actions = []
            for action_data in actions_data:
                actions.append(AutomationAction(
                    action_type=ActionType(action_data['action_type']),
                    parameters=action_data['parameters'],
                    delay_minutes=action_data.get('delay_minutes', 0),
                    condition=action_data.get('condition'),
                    is_required=action_data.get('is_required', True)
                ))
            
            return AutomationRule(
                rule_id=rule_data['rule_id'],
                name=rule_data['name'],
                description=rule_data['description'],
                trigger=trigger,
                actions=actions,
                is_active=rule_data.get('is_active', True),
                created_at=rule_data.get('created_at'),
                updated_at=rule_data.get('updated_at'),
                created_by=rule_data.get('created_by'),
                tags=json.loads(rule_data.get('tags', '[]'))
            )
            
        except Exception as e:
            self.logger.error(f"Error deserializing rule: {str(e)}")
            raise
    
    def _run_scheduler(self):
        """Run scheduled tasks"""
        while self.is_running:
            try:
                # Run scheduled tasks
                schedule.run_pending()
                
                # Clean up old data
                self._cleanup_old_data()
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in scheduler: {str(e)}")
                time.sleep(60)
    
    def _cleanup_executions(self):
        """Clean up old executions"""
        while self.is_running:
            try:
                current_time = datetime.now()
                timeout_cutoff = current_time - timedelta(hours=self.execution_timeout_hours)
                
                # Find timed out executions
                timed_out_executions = []
                for execution_id, execution in self.active_executions.items():
                    if execution.started_at < timeout_cutoff:
                        timed_out_executions.append(execution_id)
                
                # Cancel timed out executions
                for execution_id in timed_out_executions:
                    self.cancel_execution(execution_id)
                
                if timed_out_executions:
                    self.logger.info(f"Cleaned up {len(timed_out_executions)} timed out executions")
                
                time.sleep(3600)  # Check every hour
                
            except Exception as e:
                self.logger.error(f"Error in cleanup: {str(e)}")
                time.sleep(3600)
    
    def _cleanup_old_data(self):
        """Clean up old data"""
        try:
            # Clean up old event history
            cutoff_date = datetime.now() - timedelta(days=90)
            
            for user_id in list(self.event_history.keys()):
                user_events = self.event_history[user_id]
                self.event_history[user_id] = [
                    event for event in user_events 
                    if event['timestamp'] >= cutoff_date
                ]
                
                # Remove empty histories
                if not self.event_history[user_id]:
                    del self.event_history[user_id]
                    
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {str(e)}")
    
    # Analytics and Reporting
    def get_automation_metrics(self) -> Dict[str, Any]:
        """Get automation performance metrics"""
        try:
            total_rules = len(self.automation_rules)
            active_rules = len([r for r in self.automation_rules.values() if r.is_active])
            active_executions = len(self.active_executions)
            
            # Calculate overall metrics
            total_triggered = sum(metrics['triggered'] for metrics in self.automation_metrics.values())
            total_completed = sum(metrics['completed'] for metrics in self.automation_metrics.values())
            total_failed = sum(metrics['failed'] for metrics in self.automation_metrics.values())
            
            completion_rate = (total_completed / max(total_triggered, 1)) * 100
            failure_rate = (total_failed / max(total_triggered, 1)) * 100
            
            # Rule performance
            rule_performance = []
            for rule_id, rule in self.automation_rules.items():
                metrics = self.automation_metrics[rule_id]
                rule_performance.append({
                    'rule_id': rule_id,
                    'name': rule.name,
                    'triggered': metrics['triggered'],
                    'completed': metrics['completed'],
                    'failed': metrics['failed'],
                    'completion_rate': (metrics['completed'] / max(metrics['triggered'], 1)) * 100,
                    'is_active': rule.is_active
                })
            
            return {
                'total_rules': total_rules,
                'active_rules': active_rules,
                'active_executions': active_executions,
                'total_triggered': total_triggered,
                'total_completed': total_completed,
                'total_failed': total_failed,
                'completion_rate': completion_rate,
                'failure_rate': failure_rate,
                'rule_performance': rule_performance,
                'updated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting automation metrics: {str(e)}")
            return {}
    
    def stop(self):
        """Stop the marketing automation service"""
        self.is_running = False
        self.logger.info("Marketing Automation service stopped")

# Global marketing automation instance
marketing_automation = MarketingAutomation()