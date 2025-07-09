#!/usr/bin/env python3
"""
Admin Blueprint for Business Logic Management
Comprehensive admin interface for managing business rules, workflows, and automation
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import login_required, current_user
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from services.business_logic_manager import business_logic_manager, RuleType, WorkflowStatus, ActionType
from services.workflow_engine import workflow_engine, WorkflowTriggerType, StepType, WorkflowPriority
from services.rule_engine import rule_engine, RuleOperator, LogicalOperator, RuleStatus, ActionType as RuleActionType
from services.rule_engine import RuleCondition, RuleGroup, RuleAction, DecisionNode, BusinessRule as RuleEngineBusinessRule
from database import db

# Import admin blueprint
from . import admin_bp

@admin_bp.route('/business-logic')
@login_required
def business_logic_dashboard():
    """Main business logic dashboard"""
    try:
        # Get overview statistics
        rule_stats = rule_engine.get_rule_analytics(days=30)
        workflow_stats = workflow_engine.get_workflow_analytics(days=30)
        business_logic_stats = business_logic_manager.get_business_logic_analytics(days=30)
        
        # Get recent activities
        recent_rule_executions = db.get_system_logs(limit=10, component='rule_engine')
        recent_workflow_executions = db.get_system_logs(limit=10, component='workflow_engine')
        
        # Get active rules and workflows count
        active_rules = len(rule_engine.get_business_rules(status=RuleStatus.ACTIVE))
        active_workflows = len(workflow_engine.get_workflow_definitions(is_active=True))
        
        # Calculate performance metrics
        total_rule_executions = sum(stat.get('total_executions', 0) for stat in rule_stats)
        total_workflow_executions = sum(stat.get('total_executions', 0) for stat in workflow_stats)
        
        avg_rule_execution_time = (
            sum(stat.get('avg_execution_time', 0) for stat in rule_stats) / len(rule_stats)
            if rule_stats else 0
        )
        
        avg_workflow_execution_time = (
            sum(stat.get('avg_execution_time', 0) for stat in workflow_stats) / len(workflow_stats)
            if workflow_stats else 0
        )
        
        dashboard_data = {
            'overview': {
                'active_rules': active_rules,
                'active_workflows': active_workflows,
                'total_rule_executions': total_rule_executions,
                'total_workflow_executions': total_workflow_executions,
                'avg_rule_execution_time': round(avg_rule_execution_time, 3),
                'avg_workflow_execution_time': round(avg_workflow_execution_time, 3)
            },
            'rule_stats': rule_stats,
            'workflow_stats': workflow_stats,
            'business_logic_stats': business_logic_stats,
            'recent_activities': {
                'rule_executions': recent_rule_executions,
                'workflow_executions': recent_workflow_executions
            }
        }
        
        return render_template('admin/business_logic.html', 
                             dashboard_data=dashboard_data,
                             current_section='dashboard')
    
    except Exception as e:
        db.log_system_event('error', 'business_logic_admin', f'Dashboard error: {str(e)}')
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('admin/business_logic.html', 
                             dashboard_data={},
                             current_section='dashboard')

@admin_bp.route('/business-logic/rules')
@login_required
def rules_management():
    """Business rules management interface"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        category = request.args.get('category')
        search = request.args.get('search', '')
        
        # Get rules with filtering
        rules = rule_engine.get_business_rules(
            status=RuleStatus(status) if status else None,
            category=category,
            limit=per_page * 5  # Get more for pagination
        )
        
        # Filter by search if provided
        if search:
            rules = [rule for rule in rules if search.lower() in rule.name.lower() or 
                    search.lower() in rule.description.lower()]
        
        # Paginate results
        total_rules = len(rules)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_rules = rules[start_idx:end_idx]
        
        # Get rule categories for filter
        categories = rule_engine.get_rule_categories()
        
        # Get rule analytics
        rule_analytics = rule_engine.get_rule_analytics(days=30)
        
        pagination_info = {
            'page': page,
            'per_page': per_page,
            'total': total_rules,
            'pages': (total_rules + per_page - 1) // per_page,
            'has_prev': page > 1,
            'has_next': page < (total_rules + per_page - 1) // per_page
        }
        
        return render_template('admin/business_logic.html',
                             rules=paginated_rules,
                             categories=categories,
                             rule_analytics=rule_analytics,
                             pagination=pagination_info,
                             filters={
                                 'status': status,
                                 'category': category,
                                 'search': search
                             },
                             current_section='rules')
    
    except Exception as e:
        db.log_system_event('error', 'business_logic_admin', f'Rules management error: {str(e)}')
        flash(f'Error loading rules: {str(e)}', 'error')
        return render_template('admin/business_logic.html', 
                             rules=[],
                             current_section='rules')

@admin_bp.route('/business-logic/rules/create', methods=['GET', 'POST'])
@login_required
def create_rule():
    """Create new business rule"""
    if request.method == 'GET':
        try:
            # Get rule categories
            categories = rule_engine.get_rule_categories()
            
            # Get available operators and action types
            operators = [{'value': op.value, 'label': op.value.replace('_', ' ').title()} 
                        for op in RuleOperator]
            action_types = [{'value': at.value, 'label': at.value.replace('_', ' ').title()} 
                           for at in RuleActionType]
            
            return render_template('admin/business_logic.html',
                                 categories=categories,
                                 operators=operators,
                                 action_types=action_types,
                                 current_section='create_rule')
        
        except Exception as e:
            db.log_system_event('error', 'business_logic_admin', f'Create rule page error: {str(e)}')
            flash(f'Error loading create rule page: {str(e)}', 'error')
            return redirect(url_for('business_logic.rules_management'))
    
    elif request.method == 'POST':
        try:
            form_data = request.get_json() or request.form
            
            # Create rule object
            rule_id = str(uuid.uuid4())
            
            # Parse conditions
            conditions_data = form_data.get('conditions', {})
            conditions = _parse_rule_conditions(conditions_data)
            
            # Parse actions
            actions_data = form_data.get('actions', [])
            actions = _parse_rule_actions(actions_data)
            
            # Parse decision tree if provided
            decision_tree = None
            if form_data.get('decision_tree'):
                decision_tree = _parse_decision_tree(form_data['decision_tree'])
            
            # Create rule
            rule = RuleEngineBusinessRule(
                id=rule_id,
                name=form_data.get('name', ''),
                description=form_data.get('description', ''),
                category=form_data.get('category', ''),
                priority=int(form_data.get('priority', 100)),
                status=RuleStatus(form_data.get('status', 'active')),
                rule_type=form_data.get('rule_type', 'conditional'),
                conditions=conditions,
                actions=actions,
                decision_tree=decision_tree,
                variables=form_data.get('variables', {}),
                metadata=form_data.get('metadata', {}),
                created_at=datetime.now(),
                updated_at=datetime.now(),
                created_by=current_user.username,
                version=1,
                tags=form_data.get('tags', []),
                test_cases=form_data.get('test_cases', [])
            )
            
            # Save rule
            rule_engine.create_rule(rule)
            
            # Log activity
            db.log_system_event('info', 'business_logic_admin', 
                              f'Rule created: {rule.name}', 
                              user_email=current_user.email)
            
            if request.is_json:
                return jsonify({'success': True, 'rule_id': rule_id, 'message': 'Rule created successfully'})
            else:
                flash('Rule created successfully', 'success')
                return redirect(url_for('business_logic.rules_management'))
        
        except Exception as e:
            db.log_system_event('error', 'business_logic_admin', f'Create rule error: {str(e)}')
            
            if request.is_json:
                return jsonify({'success': False, 'error': str(e)}), 400
            else:
                flash(f'Error creating rule: {str(e)}', 'error')
                return redirect(url_for('business_logic.rules_management'))

@admin_bp.route('/business-logic/rules/<rule_id>')
@login_required
def rule_details(rule_id):
    """View rule details"""
    try:
        rule = rule_engine.get_rule(rule_id)
        if not rule:
            flash('Rule not found', 'error')
            return redirect(url_for('business_logic.rules_management'))
        
        # Get rule execution history
        execution_history = rule_engine.get_rule_execution_history(rule_id, limit=50)
        
        # Get rule performance metrics
        performance_metrics = rule_engine.get_rule_performance_metrics(rule_id, days=30)
        
        # Get rule test results
        test_results = rule_engine.get_rule_test_results(rule_id)
        
        # Get rule analytics
        rule_analytics = rule_engine.get_rule_analytics(rule_id, days=30)
        
        return render_template('admin/business_logic.html',
                             rule=rule,
                             execution_history=execution_history,
                             performance_metrics=performance_metrics,
                             test_results=test_results,
                             rule_analytics=rule_analytics[0] if rule_analytics else {},
                             current_section='rule_details')
    
    except Exception as e:
        db.log_system_event('error', 'business_logic_admin', f'Rule details error: {str(e)}')
        flash(f'Error loading rule details: {str(e)}', 'error')
        return redirect(url_for('business_logic.rules_management'))

@admin_bp.route('/business-logic/rules/<rule_id>/test', methods=['POST'])
@login_required
def test_rule(rule_id):
    """Test a business rule"""
    try:
        test_data = request.get_json()
        
        # Execute rule with test data
        input_data = test_data.get('input_data', {})
        result = rule_engine.execute_rule(rule_id, input_data, f'test:{current_user.username}')
        
        # Log test execution
        db.log_system_event('info', 'business_logic_admin', 
                          f'Rule tested: {rule_id}', 
                          user_email=current_user.email)
        
        return jsonify({
            'success': True,
            'result': {
                'execution_id': result.execution_id,
                'success': result.success,
                'conditions_met': result.conditions_met,
                'actions_executed': result.actions_executed,
                'execution_time': result.execution_time,
                'output_data': result.output_data,
                'error_message': result.error_message
            }
        })
    
    except Exception as e:
        db.log_system_event('error', 'business_logic_admin', f'Rule test error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 400

@admin_bp.route('/business-logic/workflows')
@login_required
def workflows_management():
    """Workflow management interface"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        category = request.args.get('category')
        search = request.args.get('search', '')
        
        # Get workflows with filtering
        workflows = workflow_engine.get_workflow_definitions(
            is_active=status == 'active' if status else None,
            category=category,
            limit=per_page * 5  # Get more for pagination
        )
        
        # Filter by search if provided
        if search:
            workflows = [wf for wf in workflows if search.lower() in wf.name.lower() or 
                        search.lower() in wf.description.lower()]
        
        # Paginate results
        total_workflows = len(workflows)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_workflows = workflows[start_idx:end_idx]
        
        # Get workflow analytics
        workflow_analytics = workflow_engine.get_workflow_analytics(days=30)
        
        pagination_info = {
            'page': page,
            'per_page': per_page,
            'total': total_workflows,
            'pages': (total_workflows + per_page - 1) // per_page,
            'has_prev': page > 1,
            'has_next': page < (total_workflows + per_page - 1) // per_page
        }
        
        return render_template('admin/business_logic.html',
                             workflows=paginated_workflows,
                             workflow_analytics=workflow_analytics,
                             pagination=pagination_info,
                             filters={
                                 'status': status,
                                 'category': category,
                                 'search': search
                             },
                             current_section='workflows')
    
    except Exception as e:
        db.log_system_event('error', 'business_logic_admin', f'Workflows management error: {str(e)}')
        flash(f'Error loading workflows: {str(e)}', 'error')
        return render_template('admin/business_logic.html', 
                             workflows=[],
                             current_section='workflows')

@admin_bp.route('/business-logic/workflows/create', methods=['GET', 'POST'])
@login_required
def create_workflow():
    """Create new workflow"""
    if request.method == 'GET':
        try:
            # Get trigger types and step types
            trigger_types = [{'value': tt.value, 'label': tt.value.replace('_', ' ').title()} 
                           for tt in WorkflowTriggerType]
            step_types = [{'value': st.value, 'label': st.value.replace('_', ' ').title()} 
                         for st in StepType]
            priorities = [{'value': p.value, 'label': p.value.title()} 
                         for p in WorkflowPriority]
            
            return render_template('admin/business_logic.html',
                                 trigger_types=trigger_types,
                                 step_types=step_types,
                                 priorities=priorities,
                                 current_section='create_workflow')
        
        except Exception as e:
            db.log_system_event('error', 'business_logic_admin', f'Create workflow page error: {str(e)}')
            flash(f'Error loading create workflow page: {str(e)}', 'error')
            return redirect(url_for('business_logic.workflows_management'))
    
    elif request.method == 'POST':
        try:
            form_data = request.get_json() or request.form
            
            # Create workflow
            workflow_id = str(uuid.uuid4())
            
            # Parse workflow steps
            steps_data = form_data.get('steps', [])
            steps = _parse_workflow_steps(steps_data)
            
            # Create workflow definition
            from services.workflow_engine import WorkflowDefinition
            workflow = WorkflowDefinition(
                id=workflow_id,
                name=form_data.get('name', ''),
                description=form_data.get('description', ''),
                version=form_data.get('version', '1.0'),
                trigger_type=WorkflowTriggerType(form_data.get('trigger_type', 'manual')),
                trigger_config=form_data.get('trigger_config', {}),
                steps=steps,
                variables=form_data.get('variables', {}),
                priority=WorkflowPriority(form_data.get('priority', 'medium')),
                timeout_minutes=int(form_data.get('timeout_minutes', 60)),
                max_retries=int(form_data.get('max_retries', 3)),
                error_handling=form_data.get('error_handling', 'stop'),
                notification_settings=form_data.get('notification_settings', {}),
                is_active=form_data.get('is_active', True),
                created_at=datetime.now(),
                updated_at=datetime.now(),
                created_by=current_user.username,
                tags=form_data.get('tags', [])
            )
            
            # Save workflow
            workflow_engine.create_workflow(workflow)
            
            # Log activity
            db.log_system_event('info', 'business_logic_admin', 
                              f'Workflow created: {workflow.name}', 
                              user_email=current_user.email)
            
            if request.is_json:
                return jsonify({'success': True, 'workflow_id': workflow_id, 'message': 'Workflow created successfully'})
            else:
                flash('Workflow created successfully', 'success')
                return redirect(url_for('business_logic.workflows_management'))
        
        except Exception as e:
            db.log_system_event('error', 'business_logic_admin', f'Create workflow error: {str(e)}')
            
            if request.is_json:
                return jsonify({'success': False, 'error': str(e)}), 400
            else:
                flash(f'Error creating workflow: {str(e)}', 'error')
                return redirect(url_for('business_logic.workflows_management'))

@admin_bp.route('/business-logic/workflows/<workflow_id>/trigger', methods=['POST'])
@login_required
def trigger_workflow(workflow_id):
    """Trigger a workflow execution"""
    try:
        trigger_data = request.get_json() or {}
        
        # Trigger workflow
        instance_id = workflow_engine.trigger_workflow(
            workflow_id, 
            trigger_data.get('data', {}), 
            f'manual:{current_user.username}'
        )
        
        # Log activity
        db.log_system_event('info', 'business_logic_admin', 
                          f'Workflow triggered: {workflow_id}', 
                          user_email=current_user.email)
        
        return jsonify({
            'success': True,
            'instance_id': instance_id,
            'message': 'Workflow triggered successfully'
        })
    
    except Exception as e:
        db.log_system_event('error', 'business_logic_admin', f'Workflow trigger error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 400

@admin_bp.route('/business-logic/analytics')
@login_required
def analytics():
    """Business logic analytics dashboard"""
    try:
        # Get date range from query params
        days = request.args.get('days', 30, type=int)
        
        # Get comprehensive analytics
        rule_analytics = rule_engine.get_rule_analytics(days=days)
        workflow_analytics = workflow_engine.get_workflow_analytics(days=days)
        business_logic_analytics = business_logic_manager.get_business_logic_analytics(days=days)
        
        # Get performance metrics
        integration_health = business_logic_manager.get_integration_health()
        process_performance = business_logic_manager.get_process_performance_metrics(days=days)
        
        # Get top performing rules and workflows
        top_rules = sorted(rule_analytics, key=lambda x: x.get('total_executions', 0), reverse=True)[:10]
        top_workflows = sorted(workflow_analytics, key=lambda x: x.get('total_executions', 0), reverse=True)[:10]
        
        # Calculate trends
        rule_trends = _calculate_execution_trends('rules', days)
        workflow_trends = _calculate_execution_trends('workflows', days)
        
        analytics_data = {
            'overview': {
                'total_rules': len(rule_analytics),
                'total_workflows': len(workflow_analytics),
                'total_rule_executions': sum(r.get('total_executions', 0) for r in rule_analytics),
                'total_workflow_executions': sum(w.get('total_executions', 0) for w in workflow_analytics),
                'avg_rule_success_rate': sum(r.get('success_rate', 0) for r in rule_analytics) / len(rule_analytics) if rule_analytics else 0,
                'avg_workflow_success_rate': sum(w.get('success_rate', 0) for w in workflow_analytics) / len(workflow_analytics) if workflow_analytics else 0
            },
            'rule_analytics': rule_analytics,
            'workflow_analytics': workflow_analytics,
            'business_logic_analytics': business_logic_analytics,
            'integration_health': integration_health,
            'process_performance': process_performance,
            'top_rules': top_rules,
            'top_workflows': top_workflows,
            'trends': {
                'rules': rule_trends,
                'workflows': workflow_trends
            },
            'time_period': days
        }
        
        return render_template('admin/business_logic.html',
                             analytics_data=analytics_data,
                             current_section='analytics')
    
    except Exception as e:
        db.log_system_event('error', 'business_logic_admin', f'Analytics error: {str(e)}')
        flash(f'Error loading analytics: {str(e)}', 'error')
        return render_template('admin/business_logic.html', 
                             analytics_data={},
                             current_section='analytics')

@admin_bp.route('/business-logic/process-optimization')
@login_required
def process_optimization():
    """Business process optimization dashboard"""
    try:
        # Get process performance metrics
        process_metrics = business_logic_manager.get_process_performance_metrics(days=30)
        
        # Get bottleneck analysis
        bottlenecks = _analyze_process_bottlenecks()
        
        # Get optimization recommendations
        recommendations = _get_optimization_recommendations()
        
        # Get cost analysis
        cost_analysis = _get_cost_analysis()
        
        optimization_data = {
            'process_metrics': process_metrics,
            'bottlenecks': bottlenecks,
            'recommendations': recommendations,
            'cost_analysis': cost_analysis
        }
        
        return render_template('admin/business_logic.html',
                             optimization_data=optimization_data,
                             current_section='process_optimization')
    
    except Exception as e:
        db.log_system_event('error', 'business_logic_admin', f'Process optimization error: {str(e)}')
        flash(f'Error loading process optimization: {str(e)}', 'error')
        return render_template('admin/business_logic.html', 
                             optimization_data={},
                             current_section='process_optimization')

@admin_bp.route('/business-logic/customer-lifecycle')
@login_required
def customer_lifecycle():
    """Customer lifecycle management dashboard"""
    try:
        # Get customer journey data
        journey_data = business_logic_manager.get_customer_journey_analytics()
        
        # Get lifecycle stages
        lifecycle_stages = business_logic_manager.get_lifecycle_stages()
        
        # Get customer segments
        customer_segments = business_logic_manager.get_customer_segments()
        
        # Get automation metrics
        automation_metrics = business_logic_manager.get_lifecycle_automation_metrics()
        
        lifecycle_data = {
            'journey_data': journey_data,
            'lifecycle_stages': lifecycle_stages,
            'customer_segments': customer_segments,
            'automation_metrics': automation_metrics
        }
        
        return render_template('admin/business_logic.html',
                             lifecycle_data=lifecycle_data,
                             current_section='customer_lifecycle')
    
    except Exception as e:
        db.log_system_event('error', 'business_logic_admin', f'Customer lifecycle error: {str(e)}')
        flash(f'Error loading customer lifecycle: {str(e)}', 'error')
        return render_template('admin/business_logic.html', 
                             lifecycle_data={},
                             current_section='customer_lifecycle')

@admin_bp.route('/business-logic/integrations')
@login_required
def integrations():
    """Integration and API management dashboard"""
    try:
        # Get integration health
        integration_health = business_logic_manager.get_integration_health()
        
        # Get API metrics
        api_metrics = business_logic_manager.get_api_metrics()
        
        # Get service dependencies
        dependencies = business_logic_manager.get_service_dependencies()
        
        integration_data = {
            'health': integration_health,
            'metrics': api_metrics,
            'dependencies': dependencies
        }
        
        return render_template('admin/business_logic.html',
                             integration_data=integration_data,
                             current_section='integrations')
    
    except Exception as e:
        db.log_system_event('error', 'business_logic_admin', f'Integrations error: {str(e)}')
        flash(f'Error loading integrations: {str(e)}', 'error')
        return render_template('admin/business_logic.html', 
                             integration_data={},
                             current_section='integrations')

# Helper functions

def _parse_rule_conditions(conditions_data):
    """Parse rule conditions from form data"""
    try:
        conditions = []
        for cond_data in conditions_data.get('conditions', []):
            condition = RuleCondition(
                id=cond_data.get('id', str(uuid.uuid4())),
                field=cond_data.get('field', ''),
                operator=RuleOperator(cond_data.get('operator', 'equals')),
                value=cond_data.get('value'),
                value_type=cond_data.get('value_type', 'string'),
                case_sensitive=cond_data.get('case_sensitive', True),
                description=cond_data.get('description', '')
            )
            conditions.append(condition)
        
        groups = []
        for group_data in conditions_data.get('groups', []):
            group = _parse_rule_conditions(group_data)
            groups.append(group)
        
        return RuleGroup(
            id=conditions_data.get('id', str(uuid.uuid4())),
            logical_operator=LogicalOperator(conditions_data.get('logical_operator', 'and')),
            conditions=conditions,
            groups=groups,
            description=conditions_data.get('description', '')
        )
    
    except Exception as e:
        raise ValueError(f'Error parsing rule conditions: {str(e)}')

def _parse_rule_actions(actions_data):
    """Parse rule actions from form data"""
    try:
        actions = []
        for action_data in actions_data:
            action = RuleAction(
                id=action_data.get('id', str(uuid.uuid4())),
                action_type=RuleActionType(action_data.get('action_type', 'set_variable')),
                configuration=action_data.get('configuration', {}),
                priority=action_data.get('priority', 100),
                async_execution=action_data.get('async_execution', False),
                retry_count=action_data.get('retry_count', 0),
                timeout_seconds=action_data.get('timeout_seconds', 30),
                description=action_data.get('description', '')
            )
            actions.append(action)
        
        return actions
    
    except Exception as e:
        raise ValueError(f'Error parsing rule actions: {str(e)}')

def _parse_decision_tree(tree_data):
    """Parse decision tree from form data"""
    try:
        if not tree_data:
            return None
        
        # Parse condition
        condition_data = tree_data.get('condition', {})
        condition = RuleCondition(
            id=condition_data.get('id', str(uuid.uuid4())),
            field=condition_data.get('field', ''),
            operator=RuleOperator(condition_data.get('operator', 'equals')),
            value=condition_data.get('value'),
            value_type=condition_data.get('value_type', 'string'),
            case_sensitive=condition_data.get('case_sensitive', True),
            description=condition_data.get('description', '')
        )
        
        # Parse branches
        true_branch = None
        false_branch = None
        
        if tree_data.get('true_branch'):
            if isinstance(tree_data['true_branch'], dict):
                true_branch = _parse_decision_tree(tree_data['true_branch'])
            else:
                true_branch = tree_data['true_branch']
        
        if tree_data.get('false_branch'):
            if isinstance(tree_data['false_branch'], dict):
                false_branch = _parse_decision_tree(tree_data['false_branch'])
            else:
                false_branch = tree_data['false_branch']
        
        return DecisionNode(
            id=tree_data.get('id', str(uuid.uuid4())),
            condition=condition,
            true_branch=true_branch,
            false_branch=false_branch,
            description=tree_data.get('description', '')
        )
    
    except Exception as e:
        raise ValueError(f'Error parsing decision tree: {str(e)}')

def _parse_workflow_steps(steps_data):
    """Parse workflow steps from form data"""
    try:
        from services.workflow_engine import WorkflowStep
        
        steps = []
        for step_data in steps_data:
            step = WorkflowStep(
                id=step_data.get('id', str(uuid.uuid4())),
                name=step_data.get('name', ''),
                type=StepType(step_data.get('type', 'action')),
                configuration=step_data.get('configuration', {}),
                next_steps=step_data.get('next_steps', []),
                error_handler=step_data.get('error_handler'),
                timeout_seconds=step_data.get('timeout_seconds', 30),
                retry_count=step_data.get('retry_count', 0),
                conditions=step_data.get('conditions', {}),
                variables=step_data.get('variables', {}),
                is_active=step_data.get('is_active', True)
            )
            steps.append(step)
        
        return steps
    
    except Exception as e:
        raise ValueError(f'Error parsing workflow steps: {str(e)}')

def _calculate_execution_trends(entity_type, days):
    """Calculate execution trends for rules or workflows"""
    try:
        # This would query the database for historical data
        # For now, return dummy trend data
        return {
            'labels': ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5'],
            'data': [10, 15, 12, 18, 22]
        }
    
    except Exception as e:
        return {'labels': [], 'data': []}

def _analyze_process_bottlenecks():
    """Analyze process bottlenecks"""
    try:
        # This would analyze process performance data
        # For now, return dummy bottleneck data
        return [
            {
                'process_name': 'Customer Onboarding',
                'bottleneck_step': 'Email Verification',
                'avg_delay': 120,  # minutes
                'impact_score': 85,
                'recommended_action': 'Implement automated email verification'
            },
            {
                'process_name': 'Payment Processing',
                'bottleneck_step': 'Fraud Check',
                'avg_delay': 45,
                'impact_score': 70,
                'recommended_action': 'Optimize fraud detection rules'
            }
        ]
    
    except Exception as e:
        return []

def _get_optimization_recommendations():
    """Get process optimization recommendations"""
    try:
        # This would analyze process data and generate recommendations
        # For now, return dummy recommendations
        return [
            {
                'title': 'Automate Customer Onboarding',
                'description': 'Implement automated email verification and document processing',
                'estimated_savings': '40% time reduction',
                'priority': 'High',
                'effort': 'Medium'
            },
            {
                'title': 'Optimize Payment Workflows',
                'description': 'Streamline payment processing with better fraud detection',
                'estimated_savings': '25% time reduction',
                'priority': 'Medium',
                'effort': 'Low'
            }
        ]
    
    except Exception as e:
        return []

def _get_cost_analysis():
    """Get cost analysis for business processes"""
    try:
        # This would analyze cost data
        # For now, return dummy cost analysis
        return {
            'total_monthly_cost': 5000,
            'cost_per_execution': 2.5,
            'automation_savings': 1500,
            'roi': 30  # percentage
        }
    
    except Exception as e:
        return {}

# Error handlers
@business_logic_bp.errorhandler(404)
def not_found(error):
    return render_template('admin/business_logic.html', 
                         error='Page not found',
                         current_section='error'), 404

@business_logic_bp.errorhandler(500)
def internal_error(error):
    db.log_system_event('error', 'business_logic_admin', f'Internal server error: {str(error)}')
    return render_template('admin/business_logic.html', 
                         error='Internal server error',
                         current_section='error'), 500