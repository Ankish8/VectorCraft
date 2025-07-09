#!/usr/bin/env python3
"""
Rule Engine Service
Advanced business rule engine with visual rule builder and decision trees
"""

import json
import logging
import uuid
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from contextlib import contextmanager
import operator
import ast
import importlib

logger = logging.getLogger(__name__)

class RuleOperator(Enum):
    """Available rule operators"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX_MATCH = "regex_match"
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    BETWEEN = "between"
    NOT_BETWEEN = "not_between"

class LogicalOperator(Enum):
    """Logical operators for combining rules"""
    AND = "and"
    OR = "or"
    NOT = "not"

class ActionType(Enum):
    """Types of actions that can be executed"""
    SET_VARIABLE = "set_variable"
    SEND_EMAIL = "send_email"
    SEND_NOTIFICATION = "send_notification"
    HTTP_REQUEST = "http_request"
    DATABASE_UPDATE = "database_update"
    WORKFLOW_TRIGGER = "workflow_trigger"
    SCRIPT_EXECUTION = "script_execution"
    CONDITIONAL_BRANCH = "conditional_branch"
    LOOP_ACTION = "loop_action"
    FUNCTION_CALL = "function_call"

class RuleStatus(Enum):
    """Rule execution status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TESTING = "testing"
    DEPRECATED = "deprecated"

@dataclass
class RuleCondition:
    """Individual rule condition"""
    id: str
    field: str
    operator: RuleOperator
    value: Any
    value_type: str
    case_sensitive: bool = True
    description: str = ""

@dataclass
class RuleGroup:
    """Group of conditions with logical operator"""
    id: str
    logical_operator: LogicalOperator
    conditions: List[RuleCondition]
    groups: List['RuleGroup']
    description: str = ""

@dataclass
class RuleAction:
    """Action to be executed when rule matches"""
    id: str
    action_type: ActionType
    configuration: Dict[str, Any]
    priority: int = 100
    async_execution: bool = False
    retry_count: int = 0
    timeout_seconds: int = 30
    description: str = ""

@dataclass
class DecisionNode:
    """Decision tree node"""
    id: str
    condition: RuleCondition
    true_branch: Optional[Union['DecisionNode', str]]
    false_branch: Optional[Union['DecisionNode', str]]
    description: str = ""

@dataclass
class BusinessRule:
    """Complete business rule definition"""
    id: str
    name: str
    description: str
    category: str
    priority: int
    status: RuleStatus
    rule_type: str
    conditions: RuleGroup
    actions: List[RuleAction]
    decision_tree: Optional[DecisionNode]
    variables: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    created_by: str
    version: int
    tags: List[str]
    test_cases: List[Dict[str, Any]]

@dataclass
class RuleExecutionContext:
    """Context for rule execution"""
    rule_id: str
    execution_id: str
    input_data: Dict[str, Any]
    variables: Dict[str, Any]
    execution_start: datetime
    triggered_by: str
    metadata: Dict[str, Any]

@dataclass
class RuleExecutionResult:
    """Result of rule execution"""
    execution_id: str
    rule_id: str
    success: bool
    conditions_met: bool
    actions_executed: List[Dict[str, Any]]
    execution_time: float
    error_message: Optional[str]
    output_data: Dict[str, Any]
    metadata: Dict[str, Any]

class RuleEngine:
    """Advanced business rule engine"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or 'vectorcraft.db'
        self.logger = logging.getLogger(__name__)
        self.init_database()
        
        # Rule cache for performance
        self.rule_cache = {}
        self.function_registry = {}
        
        # Operator implementations
        self.operators = {
            RuleOperator.EQUALS: operator.eq,
            RuleOperator.NOT_EQUALS: operator.ne,
            RuleOperator.GREATER_THAN: operator.gt,
            RuleOperator.LESS_THAN: operator.lt,
            RuleOperator.GREATER_EQUAL: operator.ge,
            RuleOperator.LESS_EQUAL: operator.le,
            RuleOperator.CONTAINS: lambda a, b: b in str(a),
            RuleOperator.NOT_CONTAINS: lambda a, b: b not in str(a),
            RuleOperator.STARTS_WITH: lambda a, b: str(a).startswith(str(b)),
            RuleOperator.ENDS_WITH: lambda a, b: str(a).endswith(str(b)),
            RuleOperator.REGEX_MATCH: lambda a, b: bool(re.match(str(b), str(a))),
            RuleOperator.IN_LIST: lambda a, b: a in (b if isinstance(b, list) else [b]),
            RuleOperator.NOT_IN_LIST: lambda a, b: a not in (b if isinstance(b, list) else [b]),
            RuleOperator.IS_NULL: lambda a, b: a is None,
            RuleOperator.IS_NOT_NULL: lambda a, b: a is not None,
            RuleOperator.BETWEEN: lambda a, b: b[0] <= a <= b[1] if isinstance(b, list) and len(b) == 2 else False,
            RuleOperator.NOT_BETWEEN: lambda a, b: not (b[0] <= a <= b[1]) if isinstance(b, list) and len(b) == 2 else True,
        }
        
        # Register default functions
        self._register_default_functions()
    
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
        """Initialize rule engine database tables"""
        with sqlite3.connect(self.db_path) as conn:
            # Business rules table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS business_rules_engine (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    priority INTEGER DEFAULT 100,
                    status TEXT DEFAULT 'active',
                    rule_type TEXT NOT NULL,
                    conditions TEXT NOT NULL,
                    actions TEXT NOT NULL,
                    decision_tree TEXT,
                    variables TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    tags TEXT,
                    test_cases TEXT
                )
            ''')
            
            # Rule execution history
            conn.execute('''
                CREATE TABLE IF NOT EXISTS rule_execution_history (
                    id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    execution_id TEXT NOT NULL,
                    input_data TEXT,
                    output_data TEXT,
                    success BOOLEAN DEFAULT 1,
                    conditions_met BOOLEAN DEFAULT 0,
                    actions_executed TEXT,
                    execution_time REAL,
                    error_message TEXT,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    triggered_by TEXT,
                    metadata TEXT,
                    FOREIGN KEY (rule_id) REFERENCES business_rules_engine (id)
                )
            ''')
            
            # Rule testing results
            conn.execute('''
                CREATE TABLE IF NOT EXISTS rule_test_results (
                    id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    test_case_id TEXT NOT NULL,
                    test_name TEXT NOT NULL,
                    expected_result TEXT NOT NULL,
                    actual_result TEXT NOT NULL,
                    passed BOOLEAN DEFAULT 0,
                    execution_time REAL,
                    tested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    tested_by TEXT,
                    error_message TEXT,
                    metadata TEXT,
                    FOREIGN KEY (rule_id) REFERENCES business_rules_engine (id)
                )
            ''')
            
            # Rule performance metrics
            conn.execute('''
                CREATE TABLE IF NOT EXISTS rule_performance_metrics (
                    id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    value REAL NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    execution_id TEXT,
                    metadata TEXT,
                    FOREIGN KEY (rule_id) REFERENCES business_rules_engine (id)
                )
            ''')
            
            # Rule versions
            conn.execute('''
                CREATE TABLE IF NOT EXISTS rule_versions (
                    id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    rule_data TEXT NOT NULL,
                    change_summary TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 0,
                    FOREIGN KEY (rule_id) REFERENCES business_rules_engine (id)
                )
            ''')
            
            # Rule dependencies
            conn.execute('''
                CREATE TABLE IF NOT EXISTS rule_dependencies (
                    id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    dependent_rule_id TEXT NOT NULL,
                    dependency_type TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (rule_id) REFERENCES business_rules_engine (id),
                    FOREIGN KEY (dependent_rule_id) REFERENCES business_rules_engine (id)
                )
            ''')
            
            # Custom functions registry
            conn.execute('''
                CREATE TABLE IF NOT EXISTS custom_functions (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    function_code TEXT NOT NULL,
                    parameters TEXT,
                    return_type TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    metadata TEXT
                )
            ''')
            
            # Rule categories
            conn.execute('''
                CREATE TABLE IF NOT EXISTS rule_categories (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    parent_category TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # Create indexes
            conn.execute('CREATE INDEX IF NOT EXISTS idx_rules_status ON business_rules_engine(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_rules_category ON business_rules_engine(category)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_rules_priority ON business_rules_engine(priority)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_execution_history_rule_id ON rule_execution_history(rule_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_execution_history_executed_at ON rule_execution_history(executed_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_test_results_rule_id ON rule_test_results(rule_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_performance_metrics_rule_id ON rule_performance_metrics(rule_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_rule_versions_rule_id ON rule_versions(rule_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_rule_dependencies_rule_id ON rule_dependencies(rule_id)')
            
            conn.commit()
    
    def _register_default_functions(self):
        """Register default functions for rule engine"""
        self.function_registry.update({
            'current_date': lambda: datetime.now().date(),
            'current_time': lambda: datetime.now().time(),
            'current_datetime': lambda: datetime.now(),
            'date_add': lambda date, days: date + timedelta(days=days),
            'date_subtract': lambda date, days: date - timedelta(days=days),
            'string_length': lambda s: len(str(s)),
            'string_upper': lambda s: str(s).upper(),
            'string_lower': lambda s: str(s).lower(),
            'string_trim': lambda s: str(s).strip(),
            'math_abs': lambda x: abs(x),
            'math_round': lambda x, digits=0: round(x, digits),
            'math_max': lambda *args: max(args),
            'math_min': lambda *args: min(args),
            'list_length': lambda lst: len(lst) if isinstance(lst, list) else 0,
            'list_contains': lambda lst, item: item in lst if isinstance(lst, list) else False,
            'dict_get': lambda d, key, default=None: d.get(key, default) if isinstance(d, dict) else default,
            'dict_has_key': lambda d, key: key in d if isinstance(d, dict) else False,
        })
    
    def create_rule(self, rule: BusinessRule) -> str:
        """Create a new business rule"""
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO business_rules_engine 
                (id, name, description, category, priority, status, rule_type, conditions, 
                 actions, decision_tree, variables, metadata, created_by, version, tags, test_cases)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                rule.id, rule.name, rule.description, rule.category, rule.priority,
                rule.status.value, rule.rule_type, json.dumps(asdict(rule.conditions)),
                json.dumps([asdict(action) for action in rule.actions]),
                json.dumps(asdict(rule.decision_tree)) if rule.decision_tree else None,
                json.dumps(rule.variables), json.dumps(rule.metadata),
                rule.created_by, rule.version, json.dumps(rule.tags),
                json.dumps(rule.test_cases)
            ))
            conn.commit()
        
        # Cache the rule
        self.rule_cache[rule.id] = rule
        
        # Create version record
        self._create_rule_version(rule)
        
        self.logger.info(f"Created business rule: {rule.name} ({rule.id})")
        return rule.id
    
    def get_rule(self, rule_id: str) -> Optional[BusinessRule]:
        """Get a business rule by ID"""
        # Check cache first
        if rule_id in self.rule_cache:
            return self.rule_cache[rule_id]
        
        with self.get_db_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM business_rules_engine WHERE id = ?
            ''', (rule_id,))
            row = cursor.fetchone()
            
            if row:
                conditions_data = json.loads(row['conditions'])
                actions_data = json.loads(row['actions'])
                decision_tree_data = json.loads(row['decision_tree']) if row['decision_tree'] else None
                
                # Reconstruct objects
                conditions = self._reconstruct_rule_group(conditions_data)
                actions = [self._reconstruct_rule_action(action_data) for action_data in actions_data]
                decision_tree = self._reconstruct_decision_node(decision_tree_data) if decision_tree_data else None
                
                rule = BusinessRule(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'],
                    category=row['category'],
                    priority=row['priority'],
                    status=RuleStatus(row['status']),
                    rule_type=row['rule_type'],
                    conditions=conditions,
                    actions=actions,
                    decision_tree=decision_tree,
                    variables=json.loads(row['variables'] or '{}'),
                    metadata=json.loads(row['metadata'] or '{}'),
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    created_by=row['created_by'],
                    version=row['version'],
                    tags=json.loads(row['tags'] or '[]'),
                    test_cases=json.loads(row['test_cases'] or '[]')
                )
                
                # Cache the rule
                self.rule_cache[rule_id] = rule
                return rule
        
        return None
    
    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """Update a business rule"""
        rule = self.get_rule(rule_id)
        if not rule:
            return False
        
        # Update rule object
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        rule.updated_at = datetime.now()
        rule.version += 1
        
        # Update database
        with self.get_db_connection() as conn:
            conn.execute('''
                UPDATE business_rules_engine 
                SET name = ?, description = ?, category = ?, priority = ?, status = ?, 
                    conditions = ?, actions = ?, decision_tree = ?, variables = ?, 
                    metadata = ?, updated_at = ?, version = ?, tags = ?, test_cases = ?
                WHERE id = ?
            ''', (
                rule.name, rule.description, rule.category, rule.priority, rule.status.value,
                json.dumps(asdict(rule.conditions)), json.dumps([asdict(action) for action in rule.actions]),
                json.dumps(asdict(rule.decision_tree)) if rule.decision_tree else None,
                json.dumps(rule.variables), json.dumps(rule.metadata),
                rule.updated_at.isoformat(), rule.version, json.dumps(rule.tags),
                json.dumps(rule.test_cases), rule_id
            ))
            conn.commit()
        
        # Update cache
        self.rule_cache[rule_id] = rule
        
        # Create version record
        self._create_rule_version(rule)
        
        return True
    
    def execute_rule(self, rule_id: str, input_data: Dict[str, Any],
                    triggered_by: str = None) -> RuleExecutionResult:
        """Execute a business rule"""
        execution_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            rule = self.get_rule(rule_id)
            if not rule:
                raise ValueError(f"Rule not found: {rule_id}")
            
            if rule.status != RuleStatus.ACTIVE:
                raise ValueError(f"Rule is not active: {rule_id}")
            
            # Create execution context
            context = RuleExecutionContext(
                rule_id=rule_id,
                execution_id=execution_id,
                input_data=input_data,
                variables=rule.variables.copy(),
                execution_start=start_time,
                triggered_by=triggered_by or 'system',
                metadata={}
            )
            
            # Execute rule based on type
            if rule.rule_type == 'decision_tree' and rule.decision_tree:
                conditions_met, output_data = self._execute_decision_tree(rule.decision_tree, context)
            else:
                conditions_met = self._evaluate_rule_group(rule.conditions, context)
                output_data = context.variables.copy()
            
            # Execute actions if conditions are met
            actions_executed = []
            if conditions_met:
                for action in rule.actions:
                    action_result = self._execute_action(action, context)
                    actions_executed.append(action_result)
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Create result
            result = RuleExecutionResult(
                execution_id=execution_id,
                rule_id=rule_id,
                success=True,
                conditions_met=conditions_met,
                actions_executed=actions_executed,
                execution_time=execution_time,
                error_message=None,
                output_data=output_data,
                metadata=context.metadata
            )
            
            # Log execution
            self._log_rule_execution(result, context)
            
            # Record performance metrics
            self._record_performance_metrics(rule_id, execution_id, execution_time)
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = RuleExecutionResult(
                execution_id=execution_id,
                rule_id=rule_id,
                success=False,
                conditions_met=False,
                actions_executed=[],
                execution_time=execution_time,
                error_message=str(e),
                output_data={},
                metadata={}
            )
            
            # Log failed execution
            self._log_rule_execution(result, None)
            
            return result
    
    def _evaluate_rule_group(self, group: RuleGroup, context: RuleExecutionContext) -> bool:
        """Evaluate a rule group"""
        condition_results = []
        
        # Evaluate individual conditions
        for condition in group.conditions:
            result = self._evaluate_condition(condition, context)
            condition_results.append(result)
        
        # Evaluate nested groups
        for nested_group in group.groups:
            result = self._evaluate_rule_group(nested_group, context)
            condition_results.append(result)
        
        # Apply logical operator
        if group.logical_operator == LogicalOperator.AND:
            return all(condition_results)
        elif group.logical_operator == LogicalOperator.OR:
            return any(condition_results)
        elif group.logical_operator == LogicalOperator.NOT:
            return not all(condition_results)
        
        return False
    
    def _evaluate_condition(self, condition: RuleCondition, context: RuleExecutionContext) -> bool:
        """Evaluate a single condition"""
        try:
            # Get field value from context
            field_value = self._get_field_value(condition.field, context)
            
            # Convert value types
            expected_value = self._convert_value(condition.value, condition.value_type)
            
            # Handle case sensitivity for string operations
            if not condition.case_sensitive and isinstance(field_value, str) and isinstance(expected_value, str):
                field_value = field_value.lower()
                expected_value = expected_value.lower()
            
            # Get operator function
            operator_func = self.operators.get(condition.operator)
            if not operator_func:
                raise ValueError(f"Unknown operator: {condition.operator}")
            
            # Evaluate condition
            return operator_func(field_value, expected_value)
            
        except Exception as e:
            self.logger.error(f"Error evaluating condition {condition.id}: {e}")
            return False
    
    def _execute_decision_tree(self, node: DecisionNode, context: RuleExecutionContext) -> tuple[bool, Dict[str, Any]]:
        """Execute a decision tree"""
        try:
            # Evaluate current node condition
            condition_met = self._evaluate_condition(node.condition, context)
            
            # Navigate to appropriate branch
            if condition_met:
                if isinstance(node.true_branch, DecisionNode):
                    return self._execute_decision_tree(node.true_branch, context)
                else:
                    # Leaf node - execute action or return result
                    return self._execute_decision_leaf(node.true_branch, context)
            else:
                if isinstance(node.false_branch, DecisionNode):
                    return self._execute_decision_tree(node.false_branch, context)
                else:
                    # Leaf node - execute action or return result
                    return self._execute_decision_leaf(node.false_branch, context)
                    
        except Exception as e:
            self.logger.error(f"Error executing decision tree node {node.id}: {e}")
            return False, {}
    
    def _execute_decision_leaf(self, leaf_action: str, context: RuleExecutionContext) -> tuple[bool, Dict[str, Any]]:
        """Execute a decision tree leaf action"""
        try:
            # Parse leaf action (could be a result value, action reference, etc.)
            if leaf_action.startswith('action:'):
                # Execute specific action
                action_id = leaf_action.replace('action:', '')
                # Find and execute action
                return True, context.variables.copy()
            elif leaf_action.startswith('result:'):
                # Return specific result
                result_value = leaf_action.replace('result:', '')
                return True, {'result': result_value}
            else:
                # Default behavior
                return True, {'result': leaf_action}
                
        except Exception as e:
            self.logger.error(f"Error executing decision leaf {leaf_action}: {e}")
            return False, {}
    
    def _execute_action(self, action: RuleAction, context: RuleExecutionContext) -> Dict[str, Any]:
        """Execute a rule action"""
        try:
            action_type = action.action_type
            config = action.configuration
            
            if action_type == ActionType.SET_VARIABLE:
                return self._execute_set_variable_action(config, context)
            elif action_type == ActionType.SEND_EMAIL:
                return self._execute_send_email_action(config, context)
            elif action_type == ActionType.SEND_NOTIFICATION:
                return self._execute_send_notification_action(config, context)
            elif action_type == ActionType.HTTP_REQUEST:
                return self._execute_http_request_action(config, context)
            elif action_type == ActionType.DATABASE_UPDATE:
                return self._execute_database_update_action(config, context)
            elif action_type == ActionType.WORKFLOW_TRIGGER:
                return self._execute_workflow_trigger_action(config, context)
            elif action_type == ActionType.SCRIPT_EXECUTION:
                return self._execute_script_action(config, context)
            elif action_type == ActionType.FUNCTION_CALL:
                return self._execute_function_call_action(config, context)
            else:
                return {
                    'success': False,
                    'error': f'Unknown action type: {action_type}',
                    'action_id': action.id
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'action_id': action.id
            }
    
    def _execute_set_variable_action(self, config: Dict[str, Any], context: RuleExecutionContext) -> Dict[str, Any]:
        """Execute set variable action"""
        variable_name = config.get('variable_name')
        value_expression = config.get('value_expression')
        
        if not variable_name:
            return {'success': False, 'error': 'Variable name is required'}
        
        try:
            # Evaluate value expression
            value = self._evaluate_expression(value_expression, context)
            context.variables[variable_name] = value
            
            return {
                'success': True,
                'variable_name': variable_name,
                'value': value
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _execute_send_email_action(self, config: Dict[str, Any], context: RuleExecutionContext) -> Dict[str, Any]:
        """Execute send email action"""
        try:
            from services.email_service import EmailService
            email_service = EmailService()
            
            to_email = self._substitute_variables(config.get('to_email', ''), context)
            subject = self._substitute_variables(config.get('subject', ''), context)
            body = self._substitute_variables(config.get('body', ''), context)
            
            result = email_service.send_email(to_email, subject, body)
            
            return {
                'success': True,
                'email_sent': True,
                'recipient': to_email,
                'result': result
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _execute_send_notification_action(self, config: Dict[str, Any], context: RuleExecutionContext) -> Dict[str, Any]:
        """Execute send notification action"""
        try:
            from database import db
            
            notification_id = str(uuid.uuid4())
            user_id = context.input_data.get('user_id')
            title = self._substitute_variables(config.get('title', ''), context)
            message = self._substitute_variables(config.get('message', ''), context)
            priority = config.get('priority', 'medium')
            
            db.create_notification(notification_id, user_id, 'rule_engine', title, message, priority)
            
            return {
                'success': True,
                'notification_id': notification_id,
                'title': title
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _execute_http_request_action(self, config: Dict[str, Any], context: RuleExecutionContext) -> Dict[str, Any]:
        """Execute HTTP request action"""
        try:
            import requests
            
            url = self._substitute_variables(config.get('url', ''), context)
            method = config.get('method', 'POST')
            headers = config.get('headers', {})
            data = config.get('data', {})
            
            # Substitute variables in headers and data
            for key, value in headers.items():
                if isinstance(value, str):
                    headers[key] = self._substitute_variables(value, context)
            
            for key, value in data.items():
                if isinstance(value, str):
                    data[key] = self._substitute_variables(value, context)
            
            response = requests.request(method, url, headers=headers, json=data)
            
            return {
                'success': True,
                'status_code': response.status_code,
                'response_data': response.text
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _execute_database_update_action(self, config: Dict[str, Any], context: RuleExecutionContext) -> Dict[str, Any]:
        """Execute database update action"""
        try:
            table = config.get('table')
            operation = config.get('operation', 'update')
            conditions = config.get('conditions', {})
            data = config.get('data', {})
            
            # Substitute variables in conditions and data
            for key, value in conditions.items():
                if isinstance(value, str):
                    conditions[key] = self._substitute_variables(value, context)
            
            for key, value in data.items():
                if isinstance(value, str):
                    data[key] = self._substitute_variables(value, context)
            
            # Execute database operation
            # This is a simplified implementation - in production, you'd want proper query building
            if operation == 'update':
                # Perform update operation
                pass
            elif operation == 'insert':
                # Perform insert operation
                pass
            elif operation == 'delete':
                # Perform delete operation
                pass
            
            return {
                'success': True,
                'operation': operation,
                'table': table
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _execute_workflow_trigger_action(self, config: Dict[str, Any], context: RuleExecutionContext) -> Dict[str, Any]:
        """Execute workflow trigger action"""
        try:
            from services.workflow_engine import workflow_engine
            
            workflow_id = config.get('workflow_id')
            trigger_data = config.get('trigger_data', {})
            
            # Substitute variables in trigger data
            for key, value in trigger_data.items():
                if isinstance(value, str):
                    trigger_data[key] = self._substitute_variables(value, context)
            
            # Add context data to trigger data
            trigger_data.update(context.input_data)
            
            instance_id = workflow_engine.trigger_workflow(workflow_id, trigger_data, context.triggered_by)
            
            return {
                'success': True,
                'workflow_id': workflow_id,
                'instance_id': instance_id
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _execute_script_action(self, config: Dict[str, Any], context: RuleExecutionContext) -> Dict[str, Any]:
        """Execute script action"""
        try:
            script_code = config.get('script_code', '')
            script_language = config.get('language', 'python')
            
            if script_language == 'python':
                # Execute Python script safely
                local_vars = {
                    'context': context,
                    'input_data': context.input_data,
                    'variables': context.variables,
                    'functions': self.function_registry
                }
                
                # Compile and execute script
                compiled_code = compile(script_code, '<rule_script>', 'exec')
                exec(compiled_code, {'__builtins__': {}}, local_vars)
                
                # Extract results
                result = local_vars.get('result', 'Script executed successfully')
                
                return {
                    'success': True,
                    'result': result,
                    'language': script_language
                }
            else:
                return {'success': False, 'error': f'Unsupported script language: {script_language}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _execute_function_call_action(self, config: Dict[str, Any], context: RuleExecutionContext) -> Dict[str, Any]:
        """Execute function call action"""
        try:
            function_name = config.get('function_name')
            parameters = config.get('parameters', {})
            
            if function_name not in self.function_registry:
                return {'success': False, 'error': f'Function not found: {function_name}'}
            
            # Substitute variables in parameters
            processed_params = {}
            for key, value in parameters.items():
                if isinstance(value, str):
                    processed_params[key] = self._substitute_variables(value, context)
                else:
                    processed_params[key] = value
            
            # Call function
            function = self.function_registry[function_name]
            result = function(**processed_params)
            
            return {
                'success': True,
                'function_name': function_name,
                'result': result
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _get_field_value(self, field_path: str, context: RuleExecutionContext) -> Any:
        """Get field value from context using dot notation"""
        if field_path.startswith('input.'):
            # Get from input data
            path = field_path[6:]  # Remove 'input.'
            return self._get_nested_value(context.input_data, path)
        elif field_path.startswith('variables.'):
            # Get from variables
            path = field_path[10:]  # Remove 'variables.'
            return self._get_nested_value(context.variables, path)
        elif field_path.startswith('functions.'):
            # Call function
            func_name = field_path[10:]  # Remove 'functions.'
            if func_name in self.function_registry:
                return self.function_registry[func_name]()
            return None
        else:
            # Try input data first, then variables
            if field_path in context.input_data:
                return context.input_data[field_path]
            elif field_path in context.variables:
                return context.variables[field_path]
            else:
                return None
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested value from dictionary using dot notation"""
        keys = path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def _convert_value(self, value: Any, value_type: str) -> Any:
        """Convert value to specified type"""
        if value_type == 'string':
            return str(value)
        elif value_type == 'integer':
            return int(value)
        elif value_type == 'float':
            return float(value)
        elif value_type == 'boolean':
            return bool(value)
        elif value_type == 'date':
            if isinstance(value, str):
                return datetime.fromisoformat(value).date()
            return value
        elif value_type == 'datetime':
            if isinstance(value, str):
                return datetime.fromisoformat(value)
            return value
        elif value_type == 'list':
            if isinstance(value, str):
                return json.loads(value)
            return value
        elif value_type == 'dict':
            if isinstance(value, str):
                return json.loads(value)
            return value
        else:
            return value
    
    def _substitute_variables(self, text: str, context: RuleExecutionContext) -> str:
        """Substitute variables in text"""
        import re
        
        def replace_var(match):
            var_path = match.group(1)
            value = self._get_field_value(var_path, context)
            return str(value) if value is not None else f'{{{{{var_path}}}}}'
        
        return re.sub(r'\{\{([^}]+)\}\}', replace_var, text)
    
    def _evaluate_expression(self, expression: str, context: RuleExecutionContext) -> Any:
        """Evaluate expression safely"""
        try:
            # Create safe evaluation environment
            safe_dict = {
                'input': context.input_data,
                'variables': context.variables,
                'functions': self.function_registry,
                # Add safe built-ins
                'abs': abs,
                'max': max,
                'min': min,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'list': list,
                'dict': dict,
            }
            
            # Evaluate expression
            result = eval(expression, {"__builtins__": {}}, safe_dict)
            return result
            
        except Exception as e:
            self.logger.error(f"Error evaluating expression '{expression}': {e}")
            return None
    
    def test_rule(self, rule_id: str, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Test a rule with a test case"""
        test_id = str(uuid.uuid4())
        test_name = test_case.get('name', 'Unnamed Test')
        input_data = test_case.get('input_data', {})
        expected_result = test_case.get('expected_result', {})
        
        # Execute rule
        result = self.execute_rule(rule_id, input_data, f'test:{test_id}')
        
        # Compare results
        passed = self._compare_test_results(result, expected_result)
        
        # Log test result
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO rule_test_results 
                (id, rule_id, test_case_id, test_name, expected_result, actual_result, 
                 passed, execution_time, tested_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                test_id, rule_id, test_case.get('id', test_id), test_name,
                json.dumps(expected_result), json.dumps(asdict(result)),
                passed, result.execution_time, 'test_runner'
            ))
            conn.commit()
        
        return {
            'test_id': test_id,
            'test_name': test_name,
            'passed': passed,
            'execution_result': result,
            'expected_result': expected_result
        }
    
    def _compare_test_results(self, actual: RuleExecutionResult, expected: Dict[str, Any]) -> bool:
        """Compare test results"""
        # Check if conditions_met matches
        if 'conditions_met' in expected and actual.conditions_met != expected['conditions_met']:
            return False
        
        # Check if success matches
        if 'success' in expected and actual.success != expected['success']:
            return False
        
        # Check output data
        if 'output_data' in expected:
            for key, value in expected['output_data'].items():
                if key not in actual.output_data or actual.output_data[key] != value:
                    return False
        
        # Check actions executed
        if 'actions_executed_count' in expected:
            if len(actual.actions_executed) != expected['actions_executed_count']:
                return False
        
        return True
    
    def get_rule_analytics(self, rule_id: str = None, days: int = 30) -> Dict[str, Any]:
        """Get rule analytics"""
        query_base = '''
            SELECT 
                rule_id,
                COUNT(*) as total_executions,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_executions,
                SUM(CASE WHEN conditions_met = 1 THEN 1 ELSE 0 END) as conditions_met_count,
                AVG(execution_time) as avg_execution_time,
                MAX(execution_time) as max_execution_time,
                MIN(execution_time) as min_execution_time
            FROM rule_execution_history
            WHERE executed_at >= date('now', '-{} days')
        '''.format(days)
        
        params = []
        if rule_id:
            query_base += ' AND rule_id = ?'
            params.append(rule_id)
        
        query_base += ' GROUP BY rule_id'
        
        with self.get_db_connection() as conn:
            cursor = conn.execute(query_base, params)
            analytics = [dict(row) for row in cursor.fetchall()]
            
            # Calculate success rates
            for item in analytics:
                total = item['total_executions']
                item['success_rate'] = (item['successful_executions'] / total) * 100 if total > 0 else 0
                item['conditions_met_rate'] = (item['conditions_met_count'] / total) * 100 if total > 0 else 0
            
            return analytics
    
    def get_rule_performance_metrics(self, rule_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get rule performance metrics"""
        with self.get_db_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM rule_performance_metrics
                WHERE rule_id = ? AND timestamp >= date('now', '-{} days')
                ORDER BY timestamp DESC
            '''.format(days), (rule_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def _log_rule_execution(self, result: RuleExecutionResult, context: RuleExecutionContext):
        """Log rule execution"""
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO rule_execution_history 
                (id, rule_id, execution_id, input_data, output_data, success, 
                 conditions_met, actions_executed, execution_time, error_message, 
                 triggered_by, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(uuid.uuid4()), result.rule_id, result.execution_id,
                json.dumps(context.input_data if context else {}),
                json.dumps(result.output_data), result.success,
                result.conditions_met, json.dumps(result.actions_executed),
                result.execution_time, result.error_message,
                context.triggered_by if context else 'system',
                json.dumps(result.metadata)
            ))
            conn.commit()
    
    def _record_performance_metrics(self, rule_id: str, execution_id: str, execution_time: float):
        """Record performance metrics"""
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO rule_performance_metrics 
                (id, rule_id, metric_type, value, execution_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (str(uuid.uuid4()), rule_id, 'execution_time', execution_time, execution_id))
            conn.commit()
    
    def _create_rule_version(self, rule: BusinessRule):
        """Create a rule version record"""
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO rule_versions 
                (id, rule_id, version, rule_data, created_by, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                str(uuid.uuid4()), rule.id, rule.version,
                json.dumps(asdict(rule)), rule.created_by,
                rule.status == RuleStatus.ACTIVE
            ))
            conn.commit()
    
    def _reconstruct_rule_group(self, data: Dict[str, Any]) -> RuleGroup:
        """Reconstruct RuleGroup from dictionary"""
        conditions = [self._reconstruct_rule_condition(cond) for cond in data.get('conditions', [])]
        groups = [self._reconstruct_rule_group(group) for group in data.get('groups', [])]
        
        return RuleGroup(
            id=data['id'],
            logical_operator=LogicalOperator(data['logical_operator']),
            conditions=conditions,
            groups=groups,
            description=data.get('description', '')
        )
    
    def _reconstruct_rule_condition(self, data: Dict[str, Any]) -> RuleCondition:
        """Reconstruct RuleCondition from dictionary"""
        return RuleCondition(
            id=data['id'],
            field=data['field'],
            operator=RuleOperator(data['operator']),
            value=data['value'],
            value_type=data['value_type'],
            case_sensitive=data.get('case_sensitive', True),
            description=data.get('description', '')
        )
    
    def _reconstruct_rule_action(self, data: Dict[str, Any]) -> RuleAction:
        """Reconstruct RuleAction from dictionary"""
        return RuleAction(
            id=data['id'],
            action_type=ActionType(data['action_type']),
            configuration=data['configuration'],
            priority=data.get('priority', 100),
            async_execution=data.get('async_execution', False),
            retry_count=data.get('retry_count', 0),
            timeout_seconds=data.get('timeout_seconds', 30),
            description=data.get('description', '')
        )
    
    def _reconstruct_decision_node(self, data: Dict[str, Any]) -> DecisionNode:
        """Reconstruct DecisionNode from dictionary"""
        condition = self._reconstruct_rule_condition(data['condition'])
        
        true_branch = None
        if data.get('true_branch'):
            if isinstance(data['true_branch'], dict):
                true_branch = self._reconstruct_decision_node(data['true_branch'])
            else:
                true_branch = data['true_branch']
        
        false_branch = None
        if data.get('false_branch'):
            if isinstance(data['false_branch'], dict):
                false_branch = self._reconstruct_decision_node(data['false_branch'])
            else:
                false_branch = data['false_branch']
        
        return DecisionNode(
            id=data['id'],
            condition=condition,
            true_branch=true_branch,
            false_branch=false_branch,
            description=data.get('description', '')
        )

# Global instance
rule_engine = RuleEngine()