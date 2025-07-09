#!/usr/bin/env python3
"""
Workflow Engine Service
Advanced workflow management and automation system for VectorCraft
"""

import json
import logging
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from contextlib import contextmanager
import threading
import time

logger = logging.getLogger(__name__)

class WorkflowTriggerType(Enum):
    """Types of workflow triggers"""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EVENT = "event"
    WEBHOOK = "webhook"
    API_CALL = "api_call"
    EMAIL_RECEIVED = "email_received"
    PAYMENT_COMPLETED = "payment_completed"
    USER_REGISTERED = "user_registered"
    FILE_UPLOADED = "file_uploaded"
    CONDITION_MET = "condition_met"

class StepType(Enum):
    """Types of workflow steps"""
    ACTION = "action"
    CONDITION = "condition"
    LOOP = "loop"
    PARALLEL = "parallel"
    WAIT = "wait"
    APPROVAL = "approval"
    SUBPROCESS = "subprocess"
    TRANSFORM = "transform"
    VALIDATION = "validation"
    NOTIFICATION = "notification"

class WorkflowPriority(Enum):
    """Workflow execution priority"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class WorkflowStep:
    """Individual workflow step"""
    id: str
    name: str
    type: StepType
    configuration: Dict[str, Any]
    next_steps: List[str]
    error_handler: Optional[str]
    timeout_seconds: int
    retry_count: int
    conditions: Dict[str, Any]
    variables: Dict[str, Any]
    is_active: bool

@dataclass
class WorkflowDefinition:
    """Complete workflow definition"""
    id: str
    name: str
    description: str
    version: str
    trigger_type: WorkflowTriggerType
    trigger_config: Dict[str, Any]
    steps: List[WorkflowStep]
    variables: Dict[str, Any]
    priority: WorkflowPriority
    timeout_minutes: int
    max_retries: int
    error_handling: str
    notification_settings: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: str
    tags: List[str]

@dataclass
class WorkflowInstance:
    """Running workflow instance"""
    id: str
    workflow_id: str
    status: str
    current_step: str
    execution_context: Dict[str, Any]
    step_results: Dict[str, Any]
    error_log: List[Dict[str, Any]]
    started_at: datetime
    completed_at: Optional[datetime]
    triggered_by: str
    priority: WorkflowPriority
    retry_count: int
    variables: Dict[str, Any]
    metadata: Dict[str, Any]

class WorkflowEngine:
    """Advanced workflow execution engine"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or 'vectorcraft.db'
        self.logger = logging.getLogger(__name__)
        self.init_database()
        
        # Workflow execution state
        self.running_workflows = {}
        self.workflow_queue = []
        self.step_handlers = {}
        self.trigger_handlers = {}
        self.approval_handlers = {}
        
        # Execution threads
        self.execution_thread = None
        self.scheduler_thread = None
        self.running = False
        
        # Register default step handlers
        self._register_default_handlers()
    
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
        """Initialize workflow database tables"""
        with sqlite3.connect(self.db_path) as conn:
            # Workflow definitions table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS workflow_definitions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    version TEXT DEFAULT '1.0',
                    trigger_type TEXT NOT NULL,
                    trigger_config TEXT NOT NULL,
                    steps TEXT NOT NULL,
                    variables TEXT,
                    priority TEXT DEFAULT 'medium',
                    timeout_minutes INTEGER DEFAULT 60,
                    max_retries INTEGER DEFAULT 3,
                    error_handling TEXT DEFAULT 'stop',
                    notification_settings TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT NOT NULL,
                    tags TEXT
                )
            ''')
            
            # Workflow instances table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS workflow_instances (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    current_step TEXT,
                    execution_context TEXT,
                    step_results TEXT,
                    error_log TEXT,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    triggered_by TEXT NOT NULL,
                    priority TEXT DEFAULT 'medium',
                    retry_count INTEGER DEFAULT 0,
                    variables TEXT,
                    metadata TEXT,
                    FOREIGN KEY (workflow_id) REFERENCES workflow_definitions (id)
                )
            ''')
            
            # Workflow schedules table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS workflow_schedules (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    schedule_type TEXT NOT NULL,
                    schedule_config TEXT NOT NULL,
                    next_run TIMESTAMP NOT NULL,
                    last_run TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (workflow_id) REFERENCES workflow_definitions (id)
                )
            ''')
            
            # Workflow approvals table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS workflow_approvals (
                    id TEXT PRIMARY KEY,
                    workflow_instance_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    approver_id TEXT,
                    approver_email TEXT,
                    approval_message TEXT,
                    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    approved_at TIMESTAMP,
                    rejected_at TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    comments TEXT,
                    metadata TEXT,
                    FOREIGN KEY (workflow_instance_id) REFERENCES workflow_instances (id)
                )
            ''')
            
            # Workflow triggers table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS workflow_triggers (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    trigger_type TEXT NOT NULL,
                    trigger_data TEXT NOT NULL,
                    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed BOOLEAN DEFAULT 0,
                    instance_id TEXT,
                    metadata TEXT,
                    FOREIGN KEY (workflow_id) REFERENCES workflow_definitions (id)
                )
            ''')
            
            # Workflow metrics table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS workflow_metrics (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    instance_id TEXT,
                    metric_type TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    step_id TEXT,
                    metadata TEXT,
                    FOREIGN KEY (workflow_id) REFERENCES workflow_definitions (id)
                )
            ''')
            
            # SLA tracking table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS workflow_sla_tracking (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    instance_id TEXT NOT NULL,
                    sla_type TEXT NOT NULL,
                    target_minutes INTEGER NOT NULL,
                    actual_minutes INTEGER,
                    status TEXT DEFAULT 'active',
                    breached BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (workflow_id) REFERENCES workflow_definitions (id)
                )
            ''')
            
            # Create indexes
            conn.execute('CREATE INDEX IF NOT EXISTS idx_workflow_instances_status ON workflow_instances(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_workflow_instances_workflow_id ON workflow_instances(workflow_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_workflow_schedules_next_run ON workflow_schedules(next_run)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_workflow_approvals_status ON workflow_approvals(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_workflow_triggers_processed ON workflow_triggers(processed)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_workflow_metrics_workflow_id ON workflow_metrics(workflow_id)')
            
            conn.commit()
    
    def _register_default_handlers(self):
        """Register default step handlers"""
        self.step_handlers = {
            StepType.ACTION: self._handle_action_step,
            StepType.CONDITION: self._handle_condition_step,
            StepType.LOOP: self._handle_loop_step,
            StepType.PARALLEL: self._handle_parallel_step,
            StepType.WAIT: self._handle_wait_step,
            StepType.APPROVAL: self._handle_approval_step,
            StepType.SUBPROCESS: self._handle_subprocess_step,
            StepType.TRANSFORM: self._handle_transform_step,
            StepType.VALIDATION: self._handle_validation_step,
            StepType.NOTIFICATION: self._handle_notification_step
        }
        
        self.trigger_handlers = {
            WorkflowTriggerType.SCHEDULED: self._handle_scheduled_trigger,
            WorkflowTriggerType.EVENT: self._handle_event_trigger,
            WorkflowTriggerType.WEBHOOK: self._handle_webhook_trigger,
            WorkflowTriggerType.API_CALL: self._handle_api_trigger,
            WorkflowTriggerType.EMAIL_RECEIVED: self._handle_email_trigger,
            WorkflowTriggerType.PAYMENT_COMPLETED: self._handle_payment_trigger,
            WorkflowTriggerType.USER_REGISTERED: self._handle_user_registered_trigger,
            WorkflowTriggerType.FILE_UPLOADED: self._handle_file_uploaded_trigger,
            WorkflowTriggerType.CONDITION_MET: self._handle_condition_met_trigger
        }
    
    def start_engine(self):
        """Start the workflow engine"""
        if self.running:
            return
        
        self.running = True
        self.execution_thread = threading.Thread(target=self._execution_loop, daemon=True)
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        
        self.execution_thread.start()
        self.scheduler_thread.start()
        
        self.logger.info("Workflow engine started")
    
    def stop_engine(self):
        """Stop the workflow engine"""
        self.running = False
        
        if self.execution_thread:
            self.execution_thread.join(timeout=5)
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        self.logger.info("Workflow engine stopped")
    
    def _execution_loop(self):
        """Main execution loop for processing workflows"""
        while self.running:
            try:
                # Process workflow queue
                if self.workflow_queue:
                    instance = self.workflow_queue.pop(0)
                    self._execute_workflow_instance(instance)
                
                # Check for timed-out workflows
                self._check_workflow_timeouts()
                
                # Process pending approvals
                self._process_pending_approvals()
                
                time.sleep(1)  # Small delay to prevent busy waiting
                
            except Exception as e:
                self.logger.error(f"Error in execution loop: {e}")
                time.sleep(5)  # Longer delay on error
    
    def _scheduler_loop(self):
        """Scheduler loop for triggering scheduled workflows"""
        while self.running:
            try:
                self._check_scheduled_workflows()
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)
    
    def create_workflow(self, definition: WorkflowDefinition) -> str:
        """Create a new workflow definition"""
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO workflow_definitions 
                (id, name, description, version, trigger_type, trigger_config, steps, 
                 variables, priority, timeout_minutes, max_retries, error_handling, 
                 notification_settings, created_by, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                definition.id, definition.name, definition.description, definition.version,
                definition.trigger_type.value, json.dumps(definition.trigger_config),
                json.dumps([asdict(step) for step in definition.steps]),
                json.dumps(definition.variables), definition.priority.value,
                definition.timeout_minutes, definition.max_retries, definition.error_handling,
                json.dumps(definition.notification_settings), definition.created_by,
                json.dumps(definition.tags)
            ))
            conn.commit()
        
        # Set up scheduled trigger if needed
        if definition.trigger_type == WorkflowTriggerType.SCHEDULED:
            self._setup_workflow_schedule(definition)
        
        self.logger.info(f"Created workflow: {definition.name} ({definition.id})")
        return definition.id
    
    def trigger_workflow(self, workflow_id: str, trigger_data: Dict[str, Any] = None,
                        triggered_by: str = None, priority: WorkflowPriority = None) -> str:
        """Trigger a workflow execution"""
        workflow_def = self.get_workflow_definition(workflow_id)
        if not workflow_def or not workflow_def.is_active:
            raise ValueError(f"Workflow {workflow_id} not found or inactive")
        
        # Create workflow instance
        instance_id = str(uuid.uuid4())
        instance = WorkflowInstance(
            id=instance_id,
            workflow_id=workflow_id,
            status='pending',
            current_step=workflow_def.steps[0].id if workflow_def.steps else None,
            execution_context=trigger_data or {},
            step_results={},
            error_log=[],
            started_at=datetime.now(),
            completed_at=None,
            triggered_by=triggered_by or 'system',
            priority=priority or workflow_def.priority,
            retry_count=0,
            variables=workflow_def.variables.copy(),
            metadata={}
        )
        
        # Save instance to database
        self._save_workflow_instance(instance)
        
        # Add to execution queue
        self.workflow_queue.append(instance)
        self.workflow_queue.sort(key=lambda x: self._get_priority_value(x.priority), reverse=True)
        
        self.logger.info(f"Triggered workflow {workflow_id}: instance {instance_id}")
        return instance_id
    
    def _execute_workflow_instance(self, instance: WorkflowInstance):
        """Execute a workflow instance"""
        try:
            workflow_def = self.get_workflow_definition(instance.workflow_id)
            if not workflow_def:
                raise ValueError(f"Workflow definition not found: {instance.workflow_id}")
            
            # Update status to running
            instance.status = 'running'
            self._update_workflow_instance(instance)
            
            # Track SLA
            self._start_sla_tracking(instance)
            
            # Execute steps
            step_results = {}
            current_step_id = instance.current_step
            
            while current_step_id:
                step = self._find_step_by_id(workflow_def.steps, current_step_id)
                if not step:
                    raise ValueError(f"Step not found: {current_step_id}")
                
                # Execute step
                step_result = self._execute_step(step, instance, step_results)
                step_results[current_step_id] = step_result
                
                # Update instance
                instance.step_results = step_results
                instance.current_step = current_step_id
                self._update_workflow_instance(instance)
                
                # Determine next step
                if step_result.get('success', True):
                    current_step_id = self._get_next_step(step, step_result, instance)
                else:
                    # Handle error
                    if workflow_def.error_handling == 'stop':
                        instance.status = 'failed'
                        instance.error_log.append({
                            'step_id': current_step_id,
                            'error': step_result.get('error', 'Unknown error'),
                            'timestamp': datetime.now().isoformat()
                        })
                        break
                    elif workflow_def.error_handling == 'continue':
                        current_step_id = self._get_next_step(step, step_result, instance)
                    elif workflow_def.error_handling == 'retry':
                        if instance.retry_count < workflow_def.max_retries:
                            instance.retry_count += 1
                            continue
                        else:
                            instance.status = 'failed'
                            break
            
            # Complete workflow
            if instance.status == 'running':
                instance.status = 'completed'
                instance.completed_at = datetime.now()
            
            self._update_workflow_instance(instance)
            self._complete_sla_tracking(instance)
            
            # Send notifications
            self._send_workflow_notifications(instance, workflow_def)
            
        except Exception as e:
            instance.status = 'failed'
            instance.error_log.append({
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            self._update_workflow_instance(instance)
            self.logger.error(f"Workflow execution failed: {e}")
    
    def _execute_step(self, step: WorkflowStep, instance: WorkflowInstance, 
                     step_results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single workflow step"""
        try:
            # Check step conditions
            if not self._evaluate_step_conditions(step.conditions, instance, step_results):
                return {'success': True, 'skipped': True, 'reason': 'Conditions not met'}
            
            # Get step handler
            handler = self.step_handlers.get(step.type)
            if not handler:
                raise ValueError(f"No handler for step type: {step.type}")
            
            # Execute step with timeout
            start_time = time.time()
            result = handler(step, instance, step_results)
            execution_time = time.time() - start_time
            
            # Record metrics
            self._record_step_metrics(instance.workflow_id, instance.id, step.id, 
                                    'execution_time', execution_time)
            
            return result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_action_step(self, step: WorkflowStep, instance: WorkflowInstance,
                          step_results: Dict[str, Any]) -> Dict[str, Any]:
        """Handle action step"""
        action_type = step.configuration.get('action_type')
        
        if action_type == 'email':
            return self._execute_email_action(step, instance)
        elif action_type == 'http_request':
            return self._execute_http_request(step, instance)
        elif action_type == 'database_operation':
            return self._execute_database_operation(step, instance)
        elif action_type == 'file_operation':
            return self._execute_file_operation(step, instance)
        elif action_type == 'custom_function':
            return self._execute_custom_function(step, instance)
        else:
            return {'success': False, 'error': f'Unknown action type: {action_type}'}
    
    def _handle_condition_step(self, step: WorkflowStep, instance: WorkflowInstance,
                             step_results: Dict[str, Any]) -> Dict[str, Any]:
        """Handle condition step"""
        conditions = step.configuration.get('conditions', {})
        result = self._evaluate_conditions(conditions, instance, step_results)
        
        return {'success': True, 'condition_result': result}
    
    def _handle_loop_step(self, step: WorkflowStep, instance: WorkflowInstance,
                         step_results: Dict[str, Any]) -> Dict[str, Any]:
        """Handle loop step"""
        loop_type = step.configuration.get('loop_type', 'for')
        
        if loop_type == 'for':
            return self._execute_for_loop(step, instance, step_results)
        elif loop_type == 'while':
            return self._execute_while_loop(step, instance, step_results)
        elif loop_type == 'foreach':
            return self._execute_foreach_loop(step, instance, step_results)
        else:
            return {'success': False, 'error': f'Unknown loop type: {loop_type}'}
    
    def _handle_parallel_step(self, step: WorkflowStep, instance: WorkflowInstance,
                            step_results: Dict[str, Any]) -> Dict[str, Any]:
        """Handle parallel step"""
        parallel_branches = step.configuration.get('branches', [])
        results = []
        
        # Execute all branches in parallel (simulated)
        for branch in parallel_branches:
            branch_result = self._execute_branch(branch, instance, step_results)
            results.append(branch_result)
        
        # Determine success based on configuration
        success_criteria = step.configuration.get('success_criteria', 'all')
        
        if success_criteria == 'all':
            success = all(r.get('success', True) for r in results)
        elif success_criteria == 'any':
            success = any(r.get('success', True) for r in results)
        else:
            success = True
        
        return {'success': success, 'branch_results': results}
    
    def _handle_wait_step(self, step: WorkflowStep, instance: WorkflowInstance,
                         step_results: Dict[str, Any]) -> Dict[str, Any]:
        """Handle wait step"""
        wait_type = step.configuration.get('wait_type', 'duration')
        
        if wait_type == 'duration':
            duration = step.configuration.get('duration', 60)
            # In a real implementation, this would be handled asynchronously
            time.sleep(min(duration, 10))  # Cap at 10 seconds for demo
            return {'success': True, 'waited': duration}
        
        elif wait_type == 'condition':
            # Wait for condition to be met
            return self._wait_for_condition(step, instance, step_results)
        
        elif wait_type == 'external_event':
            # Wait for external event
            return self._wait_for_external_event(step, instance, step_results)
        
        else:
            return {'success': False, 'error': f'Unknown wait type: {wait_type}'}
    
    def _handle_approval_step(self, step: WorkflowStep, instance: WorkflowInstance,
                            step_results: Dict[str, Any]) -> Dict[str, Any]:
        """Handle approval step"""
        approver_config = step.configuration.get('approver', {})
        message = step.configuration.get('message', 'Approval required')
        
        # Create approval request
        approval_id = str(uuid.uuid4())
        
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO workflow_approvals 
                (id, workflow_instance_id, step_id, approver_email, approval_message)
                VALUES (?, ?, ?, ?, ?)
            ''', (approval_id, instance.id, step.id, 
                  approver_config.get('email'), message))
            conn.commit()
        
        # Send approval notification
        self._send_approval_notification(approval_id, approver_config, message)
        
        return {'success': True, 'approval_pending': True, 'approval_id': approval_id}
    
    def _handle_subprocess_step(self, step: WorkflowStep, instance: WorkflowInstance,
                              step_results: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subprocess step"""
        subprocess_id = step.configuration.get('subprocess_workflow_id')
        
        # Trigger subprocess
        subprocess_instance_id = self.trigger_workflow(
            subprocess_id, 
            instance.execution_context.copy(),
            f"subprocess:{instance.id}"
        )
        
        return {'success': True, 'subprocess_instance_id': subprocess_instance_id}
    
    def _handle_transform_step(self, step: WorkflowStep, instance: WorkflowInstance,
                             step_results: Dict[str, Any]) -> Dict[str, Any]:
        """Handle transform step"""
        transformations = step.configuration.get('transformations', [])
        
        for transform in transformations:
            source_path = transform.get('source_path')
            target_path = transform.get('target_path')
            operation = transform.get('operation', 'copy')
            
            # Apply transformation
            source_value = self._get_value_from_path(instance, source_path)
            transformed_value = self._apply_transformation(source_value, operation, transform)
            self._set_value_to_path(instance, target_path, transformed_value)
        
        return {'success': True, 'transformations_applied': len(transformations)}
    
    def _handle_validation_step(self, step: WorkflowStep, instance: WorkflowInstance,
                              step_results: Dict[str, Any]) -> Dict[str, Any]:
        """Handle validation step"""
        validations = step.configuration.get('validations', [])
        validation_results = []
        
        for validation in validations:
            field = validation.get('field')
            rules = validation.get('rules', [])
            
            field_value = self._get_value_from_path(instance, field)
            field_valid = self._validate_field(field_value, rules)
            
            validation_results.append({
                'field': field,
                'valid': field_valid,
                'value': field_value
            })
        
        all_valid = all(r['valid'] for r in validation_results)
        
        return {
            'success': all_valid,
            'validation_results': validation_results,
            'all_valid': all_valid
        }
    
    def _handle_notification_step(self, step: WorkflowStep, instance: WorkflowInstance,
                                step_results: Dict[str, Any]) -> Dict[str, Any]:
        """Handle notification step"""
        notification_type = step.configuration.get('type', 'email')
        
        if notification_type == 'email':
            return self._send_email_notification(step, instance)
        elif notification_type == 'sms':
            return self._send_sms_notification(step, instance)
        elif notification_type == 'slack':
            return self._send_slack_notification(step, instance)
        elif notification_type == 'webhook':
            return self._send_webhook_notification(step, instance)
        else:
            return {'success': False, 'error': f'Unknown notification type: {notification_type}'}
    
    def get_workflow_definition(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Get workflow definition by ID"""
        with self.get_db_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM workflow_definitions WHERE id = ?
            ''', (workflow_id,))
            row = cursor.fetchone()
            
            if row:
                steps_data = json.loads(row['steps'])
                steps = [WorkflowStep(**step_data) for step_data in steps_data]
                
                return WorkflowDefinition(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'],
                    version=row['version'],
                    trigger_type=WorkflowTriggerType(row['trigger_type']),
                    trigger_config=json.loads(row['trigger_config']),
                    steps=steps,
                    variables=json.loads(row['variables'] or '{}'),
                    priority=WorkflowPriority(row['priority']),
                    timeout_minutes=row['timeout_minutes'],
                    max_retries=row['max_retries'],
                    error_handling=row['error_handling'],
                    notification_settings=json.loads(row['notification_settings'] or '{}'),
                    is_active=bool(row['is_active']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    created_by=row['created_by'],
                    tags=json.loads(row['tags'] or '[]')
                )
        return None
    
    def get_workflow_instance(self, instance_id: str) -> Optional[WorkflowInstance]:
        """Get workflow instance by ID"""
        with self.get_db_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM workflow_instances WHERE id = ?
            ''', (instance_id,))
            row = cursor.fetchone()
            
            if row:
                return WorkflowInstance(
                    id=row['id'],
                    workflow_id=row['workflow_id'],
                    status=row['status'],
                    current_step=row['current_step'],
                    execution_context=json.loads(row['execution_context'] or '{}'),
                    step_results=json.loads(row['step_results'] or '{}'),
                    error_log=json.loads(row['error_log'] or '[]'),
                    started_at=datetime.fromisoformat(row['started_at']),
                    completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
                    triggered_by=row['triggered_by'],
                    priority=WorkflowPriority(row['priority']),
                    retry_count=row['retry_count'],
                    variables=json.loads(row['variables'] or '{}'),
                    metadata=json.loads(row['metadata'] or '{}')
                )
        return None
    
    def get_workflow_analytics(self, workflow_id: str = None, days: int = 30) -> Dict[str, Any]:
        """Get workflow analytics"""
        query_base = '''
            SELECT 
                workflow_id,
                COUNT(*) as total_executions,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running,
                AVG(
                    CASE 
                        WHEN completed_at IS NOT NULL 
                        THEN (julianday(completed_at) - julianday(started_at)) * 86400 
                        ELSE NULL 
                    END
                ) as avg_execution_time,
                MIN(started_at) as first_execution,
                MAX(started_at) as last_execution
            FROM workflow_instances
            WHERE started_at >= date('now', '-{} days')
        '''.format(days)
        
        params = []
        if workflow_id:
            query_base += ' AND workflow_id = ?'
            params.append(workflow_id)
        
        query_base += ' GROUP BY workflow_id'
        
        with self.get_db_connection() as conn:
            cursor = conn.execute(query_base, params)
            analytics = [dict(row) for row in cursor.fetchall()]
            
            # Calculate success rates
            for item in analytics:
                total = item['total_executions']
                item['success_rate'] = (item['completed'] / total) * 100 if total > 0 else 0
                item['failure_rate'] = (item['failed'] / total) * 100 if total > 0 else 0
            
            return analytics
    
    def _save_workflow_instance(self, instance: WorkflowInstance):
        """Save workflow instance to database"""
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO workflow_instances 
                (id, workflow_id, status, current_step, execution_context, step_results, 
                 error_log, triggered_by, priority, retry_count, variables, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                instance.id, instance.workflow_id, instance.status, instance.current_step,
                json.dumps(instance.execution_context), json.dumps(instance.step_results),
                json.dumps(instance.error_log), instance.triggered_by, instance.priority.value,
                instance.retry_count, json.dumps(instance.variables), json.dumps(instance.metadata)
            ))
            conn.commit()
    
    def _update_workflow_instance(self, instance: WorkflowInstance):
        """Update workflow instance in database"""
        with self.get_db_connection() as conn:
            conn.execute('''
                UPDATE workflow_instances 
                SET status = ?, current_step = ?, execution_context = ?, step_results = ?, 
                    error_log = ?, completed_at = ?, retry_count = ?, variables = ?, metadata = ?
                WHERE id = ?
            ''', (
                instance.status, instance.current_step, json.dumps(instance.execution_context),
                json.dumps(instance.step_results), json.dumps(instance.error_log),
                instance.completed_at.isoformat() if instance.completed_at else None,
                instance.retry_count, json.dumps(instance.variables), json.dumps(instance.metadata),
                instance.id
            ))
            conn.commit()
    
    def _record_step_metrics(self, workflow_id: str, instance_id: str, step_id: str,
                           metric_type: str, value: float):
        """Record step execution metrics"""
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO workflow_metrics 
                (id, workflow_id, instance_id, metric_type, metric_value, step_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (str(uuid.uuid4()), workflow_id, instance_id, metric_type, value, step_id))
            conn.commit()
    
    def _get_priority_value(self, priority: WorkflowPriority) -> int:
        """Get numeric priority value"""
        priority_map = {
            WorkflowPriority.LOW: 1,
            WorkflowPriority.MEDIUM: 2,
            WorkflowPriority.HIGH: 3,
            WorkflowPriority.URGENT: 4
        }
        return priority_map.get(priority, 2)
    
    def _find_step_by_id(self, steps: List[WorkflowStep], step_id: str) -> Optional[WorkflowStep]:
        """Find step by ID"""
        for step in steps:
            if step.id == step_id:
                return step
        return None
    
    def _get_next_step(self, current_step: WorkflowStep, step_result: Dict[str, Any],
                      instance: WorkflowInstance) -> Optional[str]:
        """Determine next step based on current step result"""
        if not current_step.next_steps:
            return None
        
        # Simple implementation - just return first next step
        # In a real implementation, this would handle conditional branching
        return current_step.next_steps[0] if current_step.next_steps else None
    
    def _evaluate_step_conditions(self, conditions: Dict[str, Any], instance: WorkflowInstance,
                                 step_results: Dict[str, Any]) -> bool:
        """Evaluate step conditions"""
        if not conditions:
            return True
        
        # Simple condition evaluation
        # In a real implementation, this would be more sophisticated
        return True
    
    def _evaluate_conditions(self, conditions: Dict[str, Any], instance: WorkflowInstance,
                           step_results: Dict[str, Any]) -> bool:
        """Evaluate complex conditions"""
        if not conditions:
            return True
        
        # Placeholder for complex condition evaluation
        return True
    
    # Additional helper methods would continue here...
    # For brevity, I'll include some key placeholder methods
    
    def _execute_email_action(self, step: WorkflowStep, instance: WorkflowInstance) -> Dict[str, Any]:
        """Execute email action"""
        try:
            config = step.configuration
            # Email sending logic here
            return {'success': True, 'email_sent': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _execute_http_request(self, step: WorkflowStep, instance: WorkflowInstance) -> Dict[str, Any]:
        """Execute HTTP request"""
        try:
            config = step.configuration
            # HTTP request logic here
            return {'success': True, 'response_received': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _check_scheduled_workflows(self):
        """Check for scheduled workflows that need to run"""
        with self.get_db_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM workflow_schedules 
                WHERE is_active = 1 AND next_run <= ?
            ''', (datetime.now().isoformat(),))
            
            for row in cursor.fetchall():
                schedule = dict(row)
                try:
                    # Trigger workflow
                    self.trigger_workflow(schedule['workflow_id'], {}, 'scheduler')
                    
                    # Update next run time
                    next_run = self._calculate_next_run(schedule)
                    conn.execute('''
                        UPDATE workflow_schedules 
                        SET next_run = ?, last_run = ?
                        WHERE id = ?
                    ''', (next_run.isoformat(), datetime.now().isoformat(), schedule['id']))
                    
                except Exception as e:
                    self.logger.error(f"Error triggering scheduled workflow: {e}")
            
            conn.commit()
    
    def _calculate_next_run(self, schedule: Dict[str, Any]) -> datetime:
        """Calculate next run time for scheduled workflow"""
        schedule_config = json.loads(schedule['schedule_config'])
        schedule_type = schedule['schedule_type']
        
        if schedule_type == 'interval':
            minutes = schedule_config.get('interval_minutes', 60)
            return datetime.now() + timedelta(minutes=minutes)
        elif schedule_type == 'cron':
            # Cron calculation logic would go here
            return datetime.now() + timedelta(hours=1)  # Placeholder
        else:
            return datetime.now() + timedelta(hours=24)  # Default daily
    
    def _start_sla_tracking(self, instance: WorkflowInstance):
        """Start SLA tracking for workflow instance"""
        workflow_def = self.get_workflow_definition(instance.workflow_id)
        if workflow_def and workflow_def.timeout_minutes:
            with self.get_db_connection() as conn:
                conn.execute('''
                    INSERT INTO workflow_sla_tracking 
                    (id, workflow_id, instance_id, sla_type, target_minutes)
                    VALUES (?, ?, ?, ?, ?)
                ''', (str(uuid.uuid4()), instance.workflow_id, instance.id, 
                      'execution_time', workflow_def.timeout_minutes))
                conn.commit()
    
    def _complete_sla_tracking(self, instance: WorkflowInstance):
        """Complete SLA tracking for workflow instance"""
        if instance.completed_at:
            execution_minutes = (instance.completed_at - instance.started_at).total_seconds() / 60
            
            with self.get_db_connection() as conn:
                conn.execute('''
                    UPDATE workflow_sla_tracking 
                    SET actual_minutes = ?, status = 'completed', completed_at = ?,
                        breached = ?
                    WHERE instance_id = ?
                ''', (execution_minutes, instance.completed_at.isoformat(),
                      1 if execution_minutes > 0 else 0, instance.id))
                conn.commit()
    
    def _send_workflow_notifications(self, instance: WorkflowInstance, 
                                   workflow_def: WorkflowDefinition):
        """Send workflow completion notifications"""
        # Notification logic would go here
        pass
    
    def _send_approval_notification(self, approval_id: str, approver_config: Dict[str, Any],
                                  message: str):
        """Send approval notification"""
        # Approval notification logic would go here
        pass
    
    def _check_workflow_timeouts(self):
        """Check for workflows that have timed out"""
        # Timeout checking logic would go here
        pass
    
    def _process_pending_approvals(self):
        """Process pending approvals"""
        # Approval processing logic would go here
        pass

# Global instance
workflow_engine = WorkflowEngine()