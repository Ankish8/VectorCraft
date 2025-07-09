#!/usr/bin/env python3
"""
Business Logic Manager Service
Comprehensive business logic management system for VectorCraft
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class RuleType(Enum):
    """Types of business rules"""
    CONDITIONAL = "conditional"
    DECISION_TREE = "decision_tree"
    CALCULATION = "calculation"
    VALIDATION = "validation"
    AUTOMATION = "automation"
    ESCALATION = "escalation"

class WorkflowStatus(Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

class ActionType(Enum):
    """Types of actions in workflows"""
    EMAIL = "email"
    NOTIFICATION = "notification"
    HTTP_REQUEST = "http_request"
    DATABASE_UPDATE = "database_update"
    PAYMENT_PROCESS = "payment_process"
    USER_CREATION = "user_creation"
    CONDITIONAL_BRANCH = "conditional_branch"
    WAIT = "wait"
    APPROVAL = "approval"

@dataclass
class BusinessRule:
    """Business rule data structure"""
    id: str
    name: str
    description: str
    rule_type: RuleType
    conditions: Dict[str, Any]
    actions: List[Dict[str, Any]]
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: str
    category: str
    tags: List[str]
    version: int
    metadata: Dict[str, Any]

@dataclass
class Workflow:
    """Workflow data structure"""
    id: str
    name: str
    description: str
    trigger_type: str
    trigger_conditions: Dict[str, Any]
    steps: List[Dict[str, Any]]
    status: WorkflowStatus
    created_at: datetime
    updated_at: datetime
    created_by: str
    category: str
    tags: List[str]
    version: int
    is_active: bool
    metadata: Dict[str, Any]

@dataclass
class WorkflowExecution:
    """Workflow execution instance"""
    id: str
    workflow_id: str
    status: WorkflowStatus
    started_at: datetime
    completed_at: Optional[datetime]
    current_step: int
    execution_context: Dict[str, Any]
    results: Dict[str, Any]
    error_message: Optional[str]
    triggered_by: str
    metadata: Dict[str, Any]

class BusinessLogicManager:
    """Main business logic management service"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or 'vectorcraft.db'
        self.logger = logging.getLogger(__name__)
        self.init_database()
        self._rule_cache = {}
        self._workflow_cache = {}
        self._active_executions = {}
    
    @contextmanager
    def get_db_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize business logic database tables"""
        with sqlite3.connect(self.db_path) as conn:
            # Business rules table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS business_rules (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    rule_type TEXT NOT NULL,
                    conditions TEXT NOT NULL,
                    actions TEXT NOT NULL,
                    priority INTEGER DEFAULT 100,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT NOT NULL,
                    category TEXT,
                    tags TEXT,
                    version INTEGER DEFAULT 1,
                    metadata TEXT
                )
            ''')
            
            # Workflows table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    trigger_type TEXT NOT NULL,
                    trigger_conditions TEXT NOT NULL,
                    steps TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT NOT NULL,
                    category TEXT,
                    tags TEXT,
                    version INTEGER DEFAULT 1,
                    is_active BOOLEAN DEFAULT 1,
                    metadata TEXT
                )
            ''')
            
            # Workflow executions table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS workflow_executions (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    current_step INTEGER DEFAULT 0,
                    execution_context TEXT,
                    results TEXT,
                    error_message TEXT,
                    triggered_by TEXT NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (workflow_id) REFERENCES workflows (id)
                )
            ''')
            
            # Rule execution history
            conn.execute('''
                CREATE TABLE IF NOT EXISTS rule_executions (
                    id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    execution_context TEXT,
                    results TEXT,
                    success BOOLEAN DEFAULT 1,
                    execution_time REAL,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error_message TEXT,
                    triggered_by TEXT,
                    metadata TEXT,
                    FOREIGN KEY (rule_id) REFERENCES business_rules (id)
                )
            ''')
            
            # Business processes table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS business_processes (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    process_type TEXT NOT NULL,
                    configuration TEXT NOT NULL,
                    sla_minutes INTEGER,
                    owner TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # Process metrics table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS process_metrics (
                    id TEXT PRIMARY KEY,
                    process_id TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    value REAL NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (process_id) REFERENCES business_processes (id)
                )
            ''')
            
            # Customer lifecycle stages
            conn.execute('''
                CREATE TABLE IF NOT EXISTS customer_lifecycle_stages (
                    id TEXT PRIMARY KEY,
                    stage_name TEXT NOT NULL,
                    description TEXT,
                    sequence_order INTEGER NOT NULL,
                    entry_rules TEXT,
                    exit_rules TEXT,
                    automated_actions TEXT,
                    sla_hours INTEGER,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # Customer journey tracking
            conn.execute('''
                CREATE TABLE IF NOT EXISTS customer_journey (
                    id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL,
                    customer_email TEXT NOT NULL,
                    current_stage TEXT NOT NULL,
                    stage_entered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    previous_stage TEXT,
                    journey_data TEXT,
                    automated_actions_taken TEXT,
                    next_action_due TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # API integrations table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS api_integrations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    api_type TEXT NOT NULL,
                    endpoint_url TEXT NOT NULL,
                    authentication_config TEXT,
                    rate_limits TEXT,
                    retry_config TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # Integration logs
            conn.execute('''
                CREATE TABLE IF NOT EXISTS integration_logs (
                    id TEXT PRIMARY KEY,
                    integration_id TEXT NOT NULL,
                    request_type TEXT NOT NULL,
                    request_data TEXT,
                    response_data TEXT,
                    response_status INTEGER,
                    execution_time REAL,
                    success BOOLEAN DEFAULT 1,
                    error_message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (integration_id) REFERENCES api_integrations (id)
                )
            ''')
            
            # Create indexes for performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_business_rules_active ON business_rules(is_active)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_business_rules_category ON business_rules(category)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_workflows_active ON workflows(is_active)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_workflow_executions_status ON workflow_executions(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_workflow_executions_workflow_id ON workflow_executions(workflow_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_rule_executions_rule_id ON rule_executions(rule_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_process_metrics_process_id ON process_metrics(process_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_customer_journey_customer_id ON customer_journey(customer_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_customer_journey_stage ON customer_journey(current_stage)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_integration_logs_integration_id ON integration_logs(integration_id)')
            
            conn.commit()
    
    # Business Rules Management
    def create_business_rule(self, name: str, description: str, rule_type: RuleType,
                           conditions: Dict[str, Any], actions: List[Dict[str, Any]],
                           created_by: str, category: str = None, tags: List[str] = None,
                           priority: int = 100, metadata: Dict[str, Any] = None) -> str:
        """Create a new business rule"""
        rule_id = str(uuid.uuid4())
        
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO business_rules 
                (id, name, description, rule_type, conditions, actions, priority, 
                 created_by, category, tags, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (rule_id, name, description, rule_type.value, 
                  json.dumps(conditions), json.dumps(actions), priority,
                  created_by, category, json.dumps(tags or []), 
                  json.dumps(metadata or {})))
            conn.commit()
        
        self.logger.info(f"Created business rule: {name} ({rule_id})")
        return rule_id
    
    def get_business_rule(self, rule_id: str) -> Optional[BusinessRule]:
        """Get a business rule by ID"""
        with self.get_db_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM business_rules WHERE id = ?
            ''', (rule_id,))
            row = cursor.fetchone()
            
            if row:
                return BusinessRule(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'],
                    rule_type=RuleType(row['rule_type']),
                    conditions=json.loads(row['conditions']),
                    actions=json.loads(row['actions']),
                    priority=row['priority'],
                    is_active=bool(row['is_active']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    created_by=row['created_by'],
                    category=row['category'],
                    tags=json.loads(row['tags'] or '[]'),
                    version=row['version'],
                    metadata=json.loads(row['metadata'] or '{}')
                )
        return None
    
    def update_business_rule(self, rule_id: str, **kwargs) -> bool:
        """Update a business rule"""
        valid_fields = ['name', 'description', 'conditions', 'actions', 'priority', 
                       'is_active', 'category', 'tags', 'metadata']
        
        updates = ['updated_at = CURRENT_TIMESTAMP']
        values = []
        
        for field, value in kwargs.items():
            if field in valid_fields:
                if field in ['conditions', 'actions', 'tags', 'metadata']:
                    value = json.dumps(value)
                elif field == 'is_active':
                    value = int(value)
                updates.append(f"{field} = ?")
                values.append(value)
        
        if len(updates) > 1:
            values.append(rule_id)
            with self.get_db_connection() as conn:
                cursor = conn.execute(f'''
                    UPDATE business_rules SET {', '.join(updates)}
                    WHERE id = ?
                ''', values)
                conn.commit()
                return cursor.rowcount > 0
        return False
    
    def get_business_rules(self, category: str = None, is_active: bool = None,
                          limit: int = 100) -> List[BusinessRule]:
        """Get business rules with optional filtering"""
        query = 'SELECT * FROM business_rules WHERE 1=1'
        params = []
        
        if category:
            query += ' AND category = ?'
            params.append(category)
        
        if is_active is not None:
            query += ' AND is_active = ?'
            params.append(int(is_active))
        
        query += ' ORDER BY priority DESC, created_at DESC LIMIT ?'
        params.append(limit)
        
        rules = []
        with self.get_db_connection() as conn:
            cursor = conn.execute(query, params)
            for row in cursor.fetchall():
                rules.append(BusinessRule(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'],
                    rule_type=RuleType(row['rule_type']),
                    conditions=json.loads(row['conditions']),
                    actions=json.loads(row['actions']),
                    priority=row['priority'],
                    is_active=bool(row['is_active']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    created_by=row['created_by'],
                    category=row['category'],
                    tags=json.loads(row['tags'] or '[]'),
                    version=row['version'],
                    metadata=json.loads(row['metadata'] or '{}')
                ))
        
        return rules
    
    def execute_rule(self, rule_id: str, context: Dict[str, Any], 
                    triggered_by: str = None) -> Dict[str, Any]:
        """Execute a business rule"""
        rule = self.get_business_rule(rule_id)
        if not rule or not rule.is_active:
            return {'success': False, 'error': 'Rule not found or inactive'}
        
        execution_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            # Evaluate conditions
            conditions_met = self._evaluate_conditions(rule.conditions, context)
            
            results = {'conditions_met': conditions_met, 'actions_executed': []}
            
            if conditions_met:
                # Execute actions
                for action in rule.actions:
                    action_result = self._execute_action(action, context)
                    results['actions_executed'].append(action_result)
            
            # Log execution
            execution_time = (datetime.now() - start_time).total_seconds()
            self._log_rule_execution(execution_id, rule_id, context, results, 
                                   True, execution_time, triggered_by)
            
            return {'success': True, 'results': results}
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._log_rule_execution(execution_id, rule_id, context, {}, 
                                   False, execution_time, triggered_by, str(e))
            return {'success': False, 'error': str(e)}
    
    def _evaluate_conditions(self, conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate rule conditions against context"""
        condition_type = conditions.get('type', 'and')
        rules = conditions.get('rules', [])
        
        if condition_type == 'and':
            return all(self._evaluate_single_condition(rule, context) for rule in rules)
        elif condition_type == 'or':
            return any(self._evaluate_single_condition(rule, context) for rule in rules)
        else:
            return self._evaluate_single_condition(conditions, context)
    
    def _evaluate_single_condition(self, condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate a single condition"""
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')
        
        if field not in context:
            return False
        
        context_value = context[field]
        
        if operator == 'equals':
            return context_value == value
        elif operator == 'not_equals':
            return context_value != value
        elif operator == 'greater_than':
            return context_value > value
        elif operator == 'less_than':
            return context_value < value
        elif operator == 'greater_than_or_equal':
            return context_value >= value
        elif operator == 'less_than_or_equal':
            return context_value <= value
        elif operator == 'contains':
            return value in str(context_value)
        elif operator == 'not_contains':
            return value not in str(context_value)
        elif operator == 'starts_with':
            return str(context_value).startswith(str(value))
        elif operator == 'ends_with':
            return str(context_value).endswith(str(value))
        elif operator == 'in':
            return context_value in value
        elif operator == 'not_in':
            return context_value not in value
        
        return False
    
    def _execute_action(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single action"""
        action_type = action.get('type')
        
        if action_type == 'email':
            return self._execute_email_action(action, context)
        elif action_type == 'notification':
            return self._execute_notification_action(action, context)
        elif action_type == 'database_update':
            return self._execute_database_action(action, context)
        elif action_type == 'http_request':
            return self._execute_http_action(action, context)
        elif action_type == 'conditional_branch':
            return self._execute_conditional_branch(action, context)
        else:
            return {'success': False, 'error': f'Unknown action type: {action_type}'}
    
    def _execute_email_action(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute email action"""
        try:
            # Get email service
            from services.email_service import EmailService
            email_service = EmailService()
            
            to_email = self._substitute_variables(action.get('to_email', ''), context)
            subject = self._substitute_variables(action.get('subject', ''), context)
            body = self._substitute_variables(action.get('body', ''), context)
            
            result = email_service.send_email(to_email, subject, body)
            return {'success': True, 'result': result}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _execute_notification_action(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute notification action"""
        try:
            # Create notification in database
            from database import db
            
            notification_id = str(uuid.uuid4())
            user_id = context.get('user_id')
            title = self._substitute_variables(action.get('title', ''), context)
            message = self._substitute_variables(action.get('message', ''), context)
            priority = action.get('priority', 'medium')
            
            db.create_notification(notification_id, user_id, 'business_rule', 
                                 title, message, priority)
            
            return {'success': True, 'notification_id': notification_id}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _execute_database_action(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute database action"""
        try:
            # This would need to be implemented based on specific database operations
            # For now, just log the action
            self.logger.info(f"Database action executed: {action}")
            return {'success': True, 'action': 'database_update'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _execute_http_action(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute HTTP request action"""
        try:
            import requests
            
            url = self._substitute_variables(action.get('url', ''), context)
            method = action.get('method', 'POST')
            headers = action.get('headers', {})
            data = action.get('data', {})
            
            # Substitute variables in data
            for key, value in data.items():
                if isinstance(value, str):
                    data[key] = self._substitute_variables(value, context)
            
            response = requests.request(method, url, headers=headers, json=data)
            
            return {
                'success': True,
                'status_code': response.status_code,
                'response': response.text
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _execute_conditional_branch(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute conditional branch action"""
        try:
            conditions = action.get('conditions', {})
            then_actions = action.get('then_actions', [])
            else_actions = action.get('else_actions', [])
            
            if self._evaluate_conditions(conditions, context):
                actions_to_execute = then_actions
            else:
                actions_to_execute = else_actions
            
            results = []
            for sub_action in actions_to_execute:
                result = self._execute_action(sub_action, context)
                results.append(result)
            
            return {'success': True, 'results': results}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _substitute_variables(self, text: str, context: Dict[str, Any]) -> str:
        """Substitute variables in text with context values"""
        import re
        
        # Replace {{variable}} with context values
        def replace_var(match):
            var_name = match.group(1)
            return str(context.get(var_name, f'{{{{{var_name}}}}}'))
        
        return re.sub(r'\{\{(\w+)\}\}', replace_var, text)
    
    def _log_rule_execution(self, execution_id: str, rule_id: str, context: Dict[str, Any],
                          results: Dict[str, Any], success: bool, execution_time: float,
                          triggered_by: str = None, error_message: str = None):
        """Log rule execution"""
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO rule_executions 
                (id, rule_id, execution_context, results, success, execution_time, 
                 triggered_by, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (execution_id, rule_id, json.dumps(context), json.dumps(results),
                  success, execution_time, triggered_by, error_message))
            conn.commit()
    
    # Workflow Management
    def create_workflow(self, name: str, description: str, trigger_type: str,
                       trigger_conditions: Dict[str, Any], steps: List[Dict[str, Any]],
                       created_by: str, category: str = None, tags: List[str] = None,
                       metadata: Dict[str, Any] = None) -> str:
        """Create a new workflow"""
        workflow_id = str(uuid.uuid4())
        
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO workflows 
                (id, name, description, trigger_type, trigger_conditions, steps, 
                 created_by, category, tags, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (workflow_id, name, description, trigger_type,
                  json.dumps(trigger_conditions), json.dumps(steps),
                  created_by, category, json.dumps(tags or []),
                  json.dumps(metadata or {})))
            conn.commit()
        
        self.logger.info(f"Created workflow: {name} ({workflow_id})")
        return workflow_id
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID"""
        with self.get_db_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM workflows WHERE id = ?
            ''', (workflow_id,))
            row = cursor.fetchone()
            
            if row:
                return Workflow(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'],
                    trigger_type=row['trigger_type'],
                    trigger_conditions=json.loads(row['trigger_conditions']),
                    steps=json.loads(row['steps']),
                    status=WorkflowStatus(row['status']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    created_by=row['created_by'],
                    category=row['category'],
                    tags=json.loads(row['tags'] or '[]'),
                    version=row['version'],
                    is_active=bool(row['is_active']),
                    metadata=json.loads(row['metadata'] or '{}')
                )
        return None
    
    def execute_workflow(self, workflow_id: str, context: Dict[str, Any],
                        triggered_by: str = None) -> str:
        """Execute a workflow"""
        workflow = self.get_workflow(workflow_id)
        if not workflow or not workflow.is_active:
            raise ValueError('Workflow not found or inactive')
        
        execution_id = str(uuid.uuid4())
        
        # Create execution record
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO workflow_executions 
                (id, workflow_id, execution_context, triggered_by)
                VALUES (?, ?, ?, ?)
            ''', (execution_id, workflow_id, json.dumps(context), triggered_by))
            conn.commit()
        
        # Start workflow execution (this would typically be async)
        self._execute_workflow_steps(execution_id, workflow, context)
        
        return execution_id
    
    def _execute_workflow_steps(self, execution_id: str, workflow: Workflow, 
                               context: Dict[str, Any]):
        """Execute workflow steps"""
        try:
            self._update_execution_status(execution_id, WorkflowStatus.RUNNING)
            
            results = {}
            for step_index, step in enumerate(workflow.steps):
                self._update_execution_current_step(execution_id, step_index)
                
                step_result = self._execute_workflow_step(step, context, results)
                results[f'step_{step_index}'] = step_result
                
                # Check if step failed and should stop execution
                if not step_result.get('success', True):
                    if step.get('on_failure') == 'stop':
                        self._update_execution_status(execution_id, WorkflowStatus.FAILED,
                                                    step_result.get('error'))
                        return
            
            # Mark as completed
            self._update_execution_status(execution_id, WorkflowStatus.COMPLETED)
            self._update_execution_results(execution_id, results)
            
        except Exception as e:
            self._update_execution_status(execution_id, WorkflowStatus.FAILED, str(e))
    
    def _execute_workflow_step(self, step: Dict[str, Any], context: Dict[str, Any],
                              previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single workflow step"""
        step_type = step.get('type')
        
        if step_type == 'action':
            return self._execute_action(step.get('action', {}), context)
        elif step_type == 'condition':
            return self._execute_condition_step(step, context)
        elif step_type == 'wait':
            return self._execute_wait_step(step, context)
        elif step_type == 'approval':
            return self._execute_approval_step(step, context)
        elif step_type == 'parallel':
            return self._execute_parallel_step(step, context, previous_results)
        else:
            return {'success': False, 'error': f'Unknown step type: {step_type}'}
    
    def _execute_condition_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute condition step"""
        conditions = step.get('conditions', {})
        result = self._evaluate_conditions(conditions, context)
        
        return {'success': True, 'condition_result': result}
    
    def _execute_wait_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute wait step"""
        wait_type = step.get('wait_type', 'duration')
        
        if wait_type == 'duration':
            # For now, just log the wait (in real implementation, this would be async)
            duration = step.get('duration', 60)  # seconds
            self.logger.info(f"Wait step: {duration} seconds")
            return {'success': True, 'waited': duration}
        
        return {'success': True, 'wait_type': wait_type}
    
    def _execute_approval_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute approval step"""
        approver = step.get('approver')
        message = step.get('message', 'Approval required')
        
        # Create approval notification
        from database import db
        notification_id = str(uuid.uuid4())
        
        db.create_notification(notification_id, None, 'approval_required',
                             'Workflow Approval Required', message, 'high')
        
        return {'success': True, 'approval_pending': True, 'notification_id': notification_id}
    
    def _execute_parallel_step(self, step: Dict[str, Any], context: Dict[str, Any],
                              previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute parallel step"""
        parallel_steps = step.get('parallel_steps', [])
        results = []
        
        for parallel_step in parallel_steps:
            result = self._execute_workflow_step(parallel_step, context, previous_results)
            results.append(result)
        
        return {'success': True, 'parallel_results': results}
    
    def _update_execution_status(self, execution_id: str, status: WorkflowStatus, 
                               error_message: str = None):
        """Update workflow execution status"""
        with self.get_db_connection() as conn:
            if status == WorkflowStatus.COMPLETED:
                conn.execute('''
                    UPDATE workflow_executions 
                    SET status = ?, completed_at = CURRENT_TIMESTAMP, error_message = ?
                    WHERE id = ?
                ''', (status.value, error_message, execution_id))
            else:
                conn.execute('''
                    UPDATE workflow_executions 
                    SET status = ?, error_message = ?
                    WHERE id = ?
                ''', (status.value, error_message, execution_id))
            conn.commit()
    
    def _update_execution_current_step(self, execution_id: str, current_step: int):
        """Update current step in execution"""
        with self.get_db_connection() as conn:
            conn.execute('''
                UPDATE workflow_executions 
                SET current_step = ?
                WHERE id = ?
            ''', (current_step, execution_id))
            conn.commit()
    
    def _update_execution_results(self, execution_id: str, results: Dict[str, Any]):
        """Update execution results"""
        with self.get_db_connection() as conn:
            conn.execute('''
                UPDATE workflow_executions 
                SET results = ?
                WHERE id = ?
            ''', (json.dumps(results), execution_id))
            conn.commit()
    
    def get_workflow_executions(self, workflow_id: str = None, status: WorkflowStatus = None,
                              limit: int = 100) -> List[WorkflowExecution]:
        """Get workflow executions"""
        query = 'SELECT * FROM workflow_executions WHERE 1=1'
        params = []
        
        if workflow_id:
            query += ' AND workflow_id = ?'
            params.append(workflow_id)
        
        if status:
            query += ' AND status = ?'
            params.append(status.value)
        
        query += ' ORDER BY started_at DESC LIMIT ?'
        params.append(limit)
        
        executions = []
        with self.get_db_connection() as conn:
            cursor = conn.execute(query, params)
            for row in cursor.fetchall():
                executions.append(WorkflowExecution(
                    id=row['id'],
                    workflow_id=row['workflow_id'],
                    status=WorkflowStatus(row['status']),
                    started_at=datetime.fromisoformat(row['started_at']),
                    completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
                    current_step=row['current_step'],
                    execution_context=json.loads(row['execution_context'] or '{}'),
                    results=json.loads(row['results'] or '{}'),
                    error_message=row['error_message'],
                    triggered_by=row['triggered_by'],
                    metadata=json.loads(row['metadata'] or '{}')
                ))
        
        return executions
    
    # Analytics and Reporting
    def get_business_logic_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get business logic analytics"""
        with self.get_db_connection() as conn:
            # Rule execution stats
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_executions,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_executions,
                    AVG(execution_time) as avg_execution_time,
                    COUNT(DISTINCT rule_id) as active_rules
                FROM rule_executions
                WHERE executed_at >= date('now', '-{} days')
            '''.format(days))
            rule_stats = dict(cursor.fetchone())
            
            # Workflow execution stats
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_executions,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_executions,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_executions,
                    COUNT(DISTINCT workflow_id) as active_workflows
                FROM workflow_executions
                WHERE started_at >= date('now', '-{} days')
            '''.format(days))
            workflow_stats = dict(cursor.fetchone())
            
            # Top executed rules
            cursor = conn.execute('''
                SELECT 
                    r.name,
                    r.category,
                    COUNT(*) as execution_count,
                    AVG(re.execution_time) as avg_execution_time
                FROM rule_executions re
                JOIN business_rules r ON re.rule_id = r.id
                WHERE re.executed_at >= date('now', '-{} days')
                GROUP BY r.id
                ORDER BY execution_count DESC
                LIMIT 10
            '''.format(days))
            top_rules = [dict(row) for row in cursor.fetchall()]
            
            # Top executed workflows
            cursor = conn.execute('''
                SELECT 
                    w.name,
                    w.category,
                    COUNT(*) as execution_count,
                    AVG(
                        CASE 
                            WHEN we.completed_at IS NOT NULL 
                            THEN (julianday(we.completed_at) - julianday(we.started_at)) * 86400 
                            ELSE NULL 
                        END
                    ) as avg_execution_time
                FROM workflow_executions we
                JOIN workflows w ON we.workflow_id = w.id
                WHERE we.started_at >= date('now', '-{} days')
                GROUP BY w.id
                ORDER BY execution_count DESC
                LIMIT 10
            '''.format(days))
            top_workflows = [dict(row) for row in cursor.fetchall()]
            
            return {
                'rule_stats': rule_stats,
                'workflow_stats': workflow_stats,
                'top_rules': top_rules,
                'top_workflows': top_workflows,
                'period_days': days
            }
    
    def get_process_performance_metrics(self, process_id: str = None, days: int = 30) -> Dict[str, Any]:
        """Get process performance metrics"""
        query = '''
            SELECT 
                metric_type,
                AVG(value) as avg_value,
                MIN(value) as min_value,
                MAX(value) as max_value,
                COUNT(*) as data_points
            FROM process_metrics
            WHERE timestamp >= date('now', '-{} days')
        '''.format(days)
        
        params = []
        if process_id:
            query += ' AND process_id = ?'
            params.append(process_id)
        
        query += ' GROUP BY metric_type'
        
        with self.get_db_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_integration_health(self) -> Dict[str, Any]:
        """Get integration health status"""
        with self.get_db_connection() as conn:
            cursor = conn.execute('''
                SELECT 
                    i.name,
                    i.api_type,
                    i.is_active,
                    COUNT(il.id) as total_requests,
                    SUM(CASE WHEN il.success = 1 THEN 1 ELSE 0 END) as successful_requests,
                    AVG(il.execution_time) as avg_response_time,
                    MAX(il.timestamp) as last_request
                FROM api_integrations i
                LEFT JOIN integration_logs il ON i.id = il.integration_id
                WHERE il.timestamp >= date('now', '-7 days')
                GROUP BY i.id
                ORDER BY total_requests DESC
            ''')
            
            integrations = []
            for row in cursor.fetchall():
                integration = dict(row)
                integration['success_rate'] = (
                    (integration['successful_requests'] / integration['total_requests']) * 100
                    if integration['total_requests'] > 0 else 0
                )
                integrations.append(integration)
            
            return integrations

# Global instance
business_logic_manager = BusinessLogicManager()