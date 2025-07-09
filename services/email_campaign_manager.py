#!/usr/bin/env python3
"""
Advanced Email Campaign Manager Service
Comprehensive email marketing automation platform for VectorCraft
"""

import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import time
from collections import defaultdict
import re
from jinja2 import Template, Environment, BaseLoader
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

class CampaignStatus(Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TriggerType(Enum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    BEHAVIOR = "behavior"
    EVENT = "event"
    API = "api"

class SegmentationType(Enum):
    ALL = "all"
    CUSTOM = "custom"
    BEHAVIOR = "behavior"
    DEMOGRAPHIC = "demographic"
    ENGAGEMENT = "engagement"

@dataclass
class EmailTemplate:
    """Email template data class"""
    template_id: str
    name: str
    subject: str
    html_content: str
    text_content: str
    variables: List[str]
    preview_text: str
    template_type: str
    is_responsive: bool = True
    created_at: datetime = None
    updated_at: datetime = None
    version: int = 1

@dataclass
class Campaign:
    """Email campaign data class"""
    campaign_id: str
    name: str
    description: str
    template_id: str
    segment_id: str
    status: CampaignStatus
    trigger_type: TriggerType
    scheduled_at: Optional[datetime] = None
    send_time: Optional[str] = None  # "immediate", "optimal", or specific time
    timezone: str = "UTC"
    tags: List[str] = None
    settings: Dict[str, Any] = None
    created_at: datetime = None
    updated_at: datetime = None
    created_by: str = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.settings is None:
            self.settings = {}
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class Segment:
    """Customer segment data class"""
    segment_id: str
    name: str
    description: str
    segment_type: SegmentationType
    conditions: List[Dict[str, Any]]
    size: int = 0
    created_at: datetime = None
    updated_at: datetime = None
    is_dynamic: bool = True

@dataclass
class Workflow:
    """Marketing automation workflow data class"""
    workflow_id: str
    name: str
    description: str
    trigger_conditions: Dict[str, Any]
    steps: List[Dict[str, Any]]
    is_active: bool = True
    created_at: datetime = None
    updated_at: datetime = None

class EmailCampaignManager:
    """Advanced email campaign management and automation service"""
    
    def __init__(self, db_instance=None):
        self.logger = logging.getLogger(__name__)
        
        # Import database
        if db_instance:
            self.db = db_instance
        else:
            from database import db
            self.db = db
        
        # Import email service
        from services.email_service import email_service
        self.email_service = email_service
        
        # Import performance tracker
        from services.email_performance_tracker import email_performance_tracker
        self.performance_tracker = email_performance_tracker
        
        # Initialize Jinja2 environment for templates
        self.jinja_env = Environment(loader=BaseLoader())
        
        # Campaign execution engine
        self.campaign_queue = []
        self.active_campaigns = {}
        self.automation_workflows = {}
        self.is_running = True
        
        # A/B testing configuration
        self.ab_test_configs = {}
        
        # Personalization engine
        self.personalization_rules = {}
        
        # Start background processing
        self.processing_thread = threading.Thread(target=self._process_campaigns, daemon=True)
        self.processing_thread.start()
        
        self.logger.info("Email Campaign Manager initialized")
    
    # Campaign Management
    def create_campaign(self, name: str, description: str, template_id: str, 
                       segment_id: str, trigger_type: str = "manual", 
                       scheduled_at: datetime = None, settings: Dict[str, Any] = None,
                       created_by: str = None) -> str:
        """Create a new email campaign"""
        try:
            campaign_id = str(uuid.uuid4())
            
            # Validate template and segment exist
            template = self.get_template(template_id)
            segment = self.get_segment(segment_id)
            
            if not template:
                raise ValueError(f"Template {template_id} not found")
            if not segment:
                raise ValueError(f"Segment {segment_id} not found")
            
            campaign = Campaign(
                campaign_id=campaign_id,
                name=name,
                description=description,
                template_id=template_id,
                segment_id=segment_id,
                status=CampaignStatus.DRAFT,
                trigger_type=TriggerType(trigger_type),
                scheduled_at=scheduled_at,
                settings=settings or {},
                created_by=created_by
            )
            
            # Save to database
            self.db.create_campaign(
                campaign_id=campaign_id,
                name=name,
                description=description,
                template_id=template_id,
                segment_id=segment_id,
                status=campaign.status.value,
                trigger_type=campaign.trigger_type.value,
                scheduled_at=scheduled_at,
                settings=json.dumps(campaign.settings),
                created_by=created_by
            )
            
            self.logger.info(f"Campaign created: {campaign_id} - {name}")
            return campaign_id
            
        except Exception as e:
            self.logger.error(f"Error creating campaign: {str(e)}")
            raise
    
    def update_campaign(self, campaign_id: str, **kwargs) -> bool:
        """Update an existing campaign"""
        try:
            # Get current campaign
            campaign = self.get_campaign(campaign_id)
            if not campaign:
                raise ValueError(f"Campaign {campaign_id} not found")
            
            # Update allowed fields
            allowed_fields = ['name', 'description', 'template_id', 'segment_id', 'scheduled_at', 'settings']
            update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}
            
            if 'settings' in update_data:
                update_data['settings'] = json.dumps(update_data['settings'])
            
            update_data['updated_at'] = datetime.now()
            
            # Update in database
            success = self.db.update_campaign(campaign_id, **update_data)
            
            if success:
                self.logger.info(f"Campaign updated: {campaign_id}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating campaign: {str(e)}")
            return False
    
    def get_campaign(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get campaign details"""
        try:
            campaign_data = self.db.get_campaign(campaign_id)
            if campaign_data and 'settings' in campaign_data:
                campaign_data['settings'] = json.loads(campaign_data['settings'] or '{}')
            return campaign_data
            
        except Exception as e:
            self.logger.error(f"Error getting campaign: {str(e)}")
            return None
    
    def get_campaigns(self, status: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of campaigns"""
        try:
            campaigns = self.db.get_campaigns(status=status, limit=limit)
            
            # Parse settings JSON for each campaign
            for campaign in campaigns:
                if 'settings' in campaign:
                    campaign['settings'] = json.loads(campaign['settings'] or '{}')
            
            return campaigns
            
        except Exception as e:
            self.logger.error(f"Error getting campaigns: {str(e)}")
            return []
    
    def launch_campaign(self, campaign_id: str, send_immediately: bool = False) -> bool:
        """Launch a campaign"""
        try:
            campaign = self.get_campaign(campaign_id)
            if not campaign:
                raise ValueError(f"Campaign {campaign_id} not found")
            
            # Validate campaign is ready to launch
            if campaign['status'] not in ['draft', 'scheduled', 'paused']:
                raise ValueError(f"Campaign {campaign_id} cannot be launched from status: {campaign['status']}")
            
            # Update campaign status
            if send_immediately:
                new_status = CampaignStatus.RUNNING
                self.db.update_campaign(campaign_id, status=new_status.value, 
                                      launched_at=datetime.now())
                
                # Add to processing queue
                self.campaign_queue.append({
                    'campaign_id': campaign_id,
                    'action': 'send',
                    'priority': 'high',
                    'queued_at': datetime.now()
                })
            else:
                new_status = CampaignStatus.SCHEDULED
                self.db.update_campaign(campaign_id, status=new_status.value)
            
            self.logger.info(f"Campaign launched: {campaign_id} - Status: {new_status.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error launching campaign: {str(e)}")
            return False
    
    def pause_campaign(self, campaign_id: str) -> bool:
        """Pause a running campaign"""
        try:
            campaign = self.get_campaign(campaign_id)
            if not campaign:
                raise ValueError(f"Campaign {campaign_id} not found")
            
            if campaign['status'] != 'running':
                raise ValueError(f"Campaign {campaign_id} is not running")
            
            # Update status
            success = self.db.update_campaign(campaign_id, status=CampaignStatus.PAUSED.value,
                                            paused_at=datetime.now())
            
            # Remove from active campaigns
            if campaign_id in self.active_campaigns:
                del self.active_campaigns[campaign_id]
            
            self.logger.info(f"Campaign paused: {campaign_id}")
            return success
            
        except Exception as e:
            self.logger.error(f"Error pausing campaign: {str(e)}")
            return False
    
    def stop_campaign(self, campaign_id: str) -> bool:
        """Stop a campaign"""
        try:
            campaign = self.get_campaign(campaign_id)
            if not campaign:
                raise ValueError(f"Campaign {campaign_id} not found")
            
            # Update status
            success = self.db.update_campaign(campaign_id, status=CampaignStatus.CANCELLED.value,
                                            stopped_at=datetime.now())
            
            # Remove from active campaigns and queue
            if campaign_id in self.active_campaigns:
                del self.active_campaigns[campaign_id]
            
            # Remove from queue
            self.campaign_queue = [
                item for item in self.campaign_queue 
                if item['campaign_id'] != campaign_id
            ]
            
            self.logger.info(f"Campaign stopped: {campaign_id}")
            return success
            
        except Exception as e:
            self.logger.error(f"Error stopping campaign: {str(e)}")
            return False
    
    # Template Management
    def create_template(self, name: str, subject: str, html_content: str, 
                       text_content: str, template_type: str = "email",
                       preview_text: str = "") -> str:
        """Create a new email template"""
        try:
            template_id = str(uuid.uuid4())
            
            # Extract variables from template content
            variables = self._extract_template_variables(html_content, text_content, subject)
            
            template = EmailTemplate(
                template_id=template_id,
                name=name,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                variables=variables,
                preview_text=preview_text,
                template_type=template_type,
                created_at=datetime.now()
            )
            
            # Save to database
            self.db.create_email_template(
                template_id=template_id,
                name=name,
                subject=subject,
                body_html=html_content,
                body_text=text_content,
                template_type=template_type,
                variables=variables,
                preview_text=preview_text
            )
            
            self.logger.info(f"Template created: {template_id} - {name}")
            return template_id
            
        except Exception as e:
            self.logger.error(f"Error creating template: {str(e)}")
            raise
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get template details"""
        try:
            return self.db.get_email_template(template_id)
            
        except Exception as e:
            self.logger.error(f"Error getting template: {str(e)}")
            return None
    
    def get_templates(self, template_type: str = None, is_active: bool = True) -> List[Dict[str, Any]]:
        """Get list of templates"""
        try:
            return self.db.get_email_templates(template_type=template_type, is_active=is_active)
            
        except Exception as e:
            self.logger.error(f"Error getting templates: {str(e)}")
            return []
    
    def preview_template(self, template_id: str, variables: Dict[str, Any] = None) -> Dict[str, str]:
        """Preview template with variables"""
        try:
            template = self.get_template(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            variables = variables or {}
            
            # Render template with variables
            html_template = self.jinja_env.from_string(template['body_html'])
            text_template = self.jinja_env.from_string(template['body_text'])
            subject_template = self.jinja_env.from_string(template['subject'])
            
            rendered_html = html_template.render(**variables)
            rendered_text = text_template.render(**variables)
            rendered_subject = subject_template.render(**variables)
            
            return {
                'html_content': rendered_html,
                'text_content': rendered_text,
                'subject': rendered_subject
            }
            
        except Exception as e:
            self.logger.error(f"Error previewing template: {str(e)}")
            return {
                'html_content': '',
                'text_content': '',
                'subject': ''
            }
    
    def test_template(self, template_id: str, test_email: str, 
                     variables: Dict[str, Any] = None) -> bool:
        """Send test email using template"""
        try:
            preview = self.preview_template(template_id, variables)
            
            # Send test email
            message = self.email_service._create_message(
                test_email,
                preview['subject'],
                preview['text_content'],
                preview['html_content']
            )
            
            success = self.email_service._send_email(message, email_type='test')
            
            if success:
                self.logger.info(f"Test email sent for template: {template_id}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending test email: {str(e)}")
            return False
    
    # Segment Management
    def create_segment(self, name: str, description: str, segment_type: str,
                      conditions: List[Dict[str, Any]], is_dynamic: bool = True) -> str:
        """Create a customer segment"""
        try:
            segment_id = str(uuid.uuid4())
            
            segment = Segment(
                segment_id=segment_id,
                name=name,
                description=description,
                segment_type=SegmentationType(segment_type),
                conditions=conditions,
                is_dynamic=is_dynamic,
                created_at=datetime.now()
            )
            
            # Calculate initial segment size
            segment_size = self._calculate_segment_size(conditions)
            
            # Save to database
            self.db.create_segment(
                segment_id=segment_id,
                name=name,
                description=description,
                segment_type=segment_type,
                conditions=json.dumps(conditions),
                size=segment_size,
                is_dynamic=is_dynamic
            )
            
            self.logger.info(f"Segment created: {segment_id} - {name} (Size: {segment_size})")
            return segment_id
            
        except Exception as e:
            self.logger.error(f"Error creating segment: {str(e)}")
            raise
    
    def get_segment(self, segment_id: str) -> Optional[Dict[str, Any]]:
        """Get segment details"""
        try:
            segment_data = self.db.get_segment(segment_id)
            if segment_data and 'conditions' in segment_data:
                segment_data['conditions'] = json.loads(segment_data['conditions'] or '[]')
            return segment_data
            
        except Exception as e:
            self.logger.error(f"Error getting segment: {str(e)}")
            return None
    
    def get_segments(self, segment_type: str = None) -> List[Dict[str, Any]]:
        """Get list of segments"""
        try:
            segments = self.db.get_segments(segment_type=segment_type)
            
            # Parse conditions JSON for each segment
            for segment in segments:
                if 'conditions' in segment:
                    segment['conditions'] = json.loads(segment['conditions'] or '[]')
            
            return segments
            
        except Exception as e:
            self.logger.error(f"Error getting segments: {str(e)}")
            return []
    
    def update_segment_size(self, segment_id: str) -> int:
        """Update segment size based on current conditions"""
        try:
            segment = self.get_segment(segment_id)
            if not segment:
                return 0
            
            new_size = self._calculate_segment_size(segment['conditions'])
            
            # Update in database
            self.db.update_segment(segment_id, size=new_size, updated_at=datetime.now())
            
            return new_size
            
        except Exception as e:
            self.logger.error(f"Error updating segment size: {str(e)}")
            return 0
    
    # A/B Testing
    def create_ab_test(self, campaign_id: str, test_name: str, 
                      variants: List[Dict[str, Any]], traffic_split: List[float],
                      success_metric: str = "open_rate") -> str:
        """Create A/B test for campaign"""
        try:
            test_id = str(uuid.uuid4())
            
            # Validate traffic split
            if abs(sum(traffic_split) - 1.0) > 0.01:
                raise ValueError("Traffic split must sum to 1.0")
            
            if len(variants) != len(traffic_split):
                raise ValueError("Number of variants must match traffic split")
            
            ab_test_config = {
                'test_id': test_id,
                'campaign_id': campaign_id,
                'test_name': test_name,
                'variants': variants,
                'traffic_split': traffic_split,
                'success_metric': success_metric,
                'created_at': datetime.now().isoformat(),
                'is_active': True
            }
            
            # Save to database
            self.db.create_ab_test(
                test_id=test_id,
                campaign_id=campaign_id,
                test_name=test_name,
                variants=json.dumps(variants),
                traffic_split=json.dumps(traffic_split),
                success_metric=success_metric
            )
            
            # Store in memory for quick access
            self.ab_test_configs[test_id] = ab_test_config
            
            self.logger.info(f"A/B test created: {test_id} for campaign {campaign_id}")
            return test_id
            
        except Exception as e:
            self.logger.error(f"Error creating A/B test: {str(e)}")
            raise
    
    def get_ab_test_results(self, test_id: str) -> Dict[str, Any]:
        """Get A/B test results"""
        try:
            # Get test configuration
            test_config = self.ab_test_configs.get(test_id)
            if not test_config:
                test_data = self.db.get_ab_test(test_id)
                if not test_data:
                    return {}
                test_config = test_data
            
            # Get performance data for each variant
            variant_results = []
            for i, variant in enumerate(test_config['variants']):
                # Get campaign performance for this variant
                performance = self.performance_tracker.get_performance_summary(
                    template_id=variant.get('template_id')
                )
                
                variant_results.append({
                    'variant_id': variant.get('variant_id', f'variant_{i}'),
                    'name': variant.get('name', f'Variant {i+1}'),
                    'traffic_percentage': test_config['traffic_split'][i] * 100,
                    'sent_count': performance.sent_count,
                    'open_rate': performance.open_rate,
                    'click_rate': performance.click_rate,
                    'conversion_rate': performance.open_rate * performance.click_rate / 100,
                    'performance_score': self._calculate_performance_score(performance)
                })
            
            # Determine winner
            success_metric = test_config['success_metric']
            winner = max(variant_results, key=lambda x: x.get(success_metric, 0))
            
            return {
                'test_id': test_id,
                'test_name': test_config['test_name'],
                'success_metric': success_metric,
                'variants': variant_results,
                'winner': winner,
                'confidence_level': self._calculate_confidence_level(variant_results, success_metric),
                'is_significant': self._is_statistically_significant(variant_results, success_metric)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting A/B test results: {str(e)}")
            return {}
    
    # Marketing Automation
    def create_workflow(self, name: str, description: str, 
                       trigger_conditions: Dict[str, Any], 
                       steps: List[Dict[str, Any]]) -> str:
        """Create marketing automation workflow"""
        try:
            workflow_id = str(uuid.uuid4())
            
            workflow = Workflow(
                workflow_id=workflow_id,
                name=name,
                description=description,
                trigger_conditions=trigger_conditions,
                steps=steps,
                created_at=datetime.now()
            )
            
            # Save to database
            self.db.create_workflow(
                workflow_id=workflow_id,
                name=name,
                description=description,
                trigger_conditions=json.dumps(trigger_conditions),
                steps=json.dumps(steps)
            )
            
            # Store in memory for quick access
            self.automation_workflows[workflow_id] = workflow
            
            self.logger.info(f"Workflow created: {workflow_id} - {name}")
            return workflow_id
            
        except Exception as e:
            self.logger.error(f"Error creating workflow: {str(e)}")
            raise
    
    def trigger_workflow(self, workflow_id: str, user_data: Dict[str, Any]) -> bool:
        """Trigger a marketing automation workflow"""
        try:
            workflow = self.automation_workflows.get(workflow_id)
            if not workflow:
                # Load from database
                workflow_data = self.db.get_workflow(workflow_id)
                if not workflow_data:
                    return False
                workflow = workflow_data
            
            # Check trigger conditions
            if not self._check_trigger_conditions(workflow.trigger_conditions, user_data):
                return False
            
            # Execute workflow steps
            for step in workflow.steps:
                success = self._execute_workflow_step(step, user_data)
                if not success and step.get('required', True):
                    self.logger.error(f"Required workflow step failed: {step}")
                    return False
            
            self.logger.info(f"Workflow triggered: {workflow_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error triggering workflow: {str(e)}")
            return False
    
    # Analytics and Reporting
    def get_campaign_analytics(self, campaign_id: str) -> Dict[str, Any]:
        """Get comprehensive campaign analytics"""
        try:
            campaign = self.get_campaign(campaign_id)
            if not campaign:
                return {}
            
            # Get basic performance metrics
            performance = self.performance_tracker.get_template_performance(
                campaign['template_id']
            )
            
            # Get segment information
            segment = self.get_segment(campaign['segment_id'])
            
            # Get timeline data
            timeline = self.db.get_campaign_timeline(campaign_id)
            
            # Calculate ROI if available
            roi_data = self._calculate_campaign_roi(campaign_id)
            
            return {
                'campaign_id': campaign_id,
                'campaign_name': campaign['name'],
                'status': campaign['status'],
                'template_id': campaign['template_id'],
                'segment_name': segment['name'] if segment else 'Unknown',
                'segment_size': segment['size'] if segment else 0,
                'performance': performance,
                'timeline': timeline,
                'roi': roi_data,
                'created_at': campaign['created_at'],
                'launched_at': campaign.get('launched_at'),
                'completed_at': campaign.get('completed_at')
            }
            
        except Exception as e:
            self.logger.error(f"Error getting campaign analytics: {str(e)}")
            return {}
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get dashboard metrics for email campaigns"""
        try:
            # Get overall performance
            overall_performance = self.performance_tracker.get_performance_summary(hours=24)
            
            # Get campaign statistics
            campaigns = self.get_campaigns()
            campaign_stats = {
                'total_campaigns': len(campaigns),
                'active_campaigns': len([c for c in campaigns if c['status'] == 'running']),
                'scheduled_campaigns': len([c for c in campaigns if c['status'] == 'scheduled']),
                'completed_campaigns': len([c for c in campaigns if c['status'] == 'completed'])
            }
            
            # Get template statistics
            templates = self.get_templates()
            template_stats = {
                'total_templates': len(templates),
                'active_templates': len([t for t in templates if t.get('is_active', True)])
            }
            
            # Get segment statistics
            segments = self.get_segments()
            total_contacts = sum(s.get('size', 0) for s in segments)
            
            segment_stats = {
                'total_segments': len(segments),
                'total_contacts': total_contacts,
                'avg_segment_size': total_contacts / max(len(segments), 1)
            }
            
            # Get recent activity
            recent_campaigns = self.get_campaigns(limit=5)
            recent_activity = [{
                'campaign_id': c['campaign_id'],
                'name': c['name'],
                'status': c['status'],
                'created_at': c['created_at']
            } for c in recent_campaigns]
            
            return {
                'performance': overall_performance.__dict__,
                'campaign_stats': campaign_stats,
                'template_stats': template_stats,
                'segment_stats': segment_stats,
                'recent_activity': recent_activity,
                'updated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting dashboard metrics: {str(e)}")
            return {}
    
    # Helper Methods
    def _extract_template_variables(self, html_content: str, text_content: str, 
                                  subject: str) -> List[str]:
        """Extract template variables from content"""
        try:
            # Find all variables in {{variable}} format
            pattern = r'\{\{\s*(\w+)\s*\}\}'
            
            variables = set()
            variables.update(re.findall(pattern, html_content))
            variables.update(re.findall(pattern, text_content))
            variables.update(re.findall(pattern, subject))
            
            return list(variables)
            
        except Exception as e:
            self.logger.error(f"Error extracting template variables: {str(e)}")
            return []
    
    def _calculate_segment_size(self, conditions: List[Dict[str, Any]]) -> int:
        """Calculate segment size based on conditions"""
        try:
            # This is a simplified implementation
            # In a real system, this would query the database with the conditions
            
            # For now, return a mock size based on conditions
            if not conditions:
                return 0
            
            # Calculate based on condition types
            base_size = 100
            for condition in conditions:
                condition_type = condition.get('type', 'default')
                if condition_type == 'email_engagement':
                    base_size = int(base_size * 0.8)
                elif condition_type == 'purchase_history':
                    base_size = int(base_size * 0.6)
                elif condition_type == 'demographic':
                    base_size = int(base_size * 0.7)
            
            return max(base_size, 1)
            
        except Exception as e:
            self.logger.error(f"Error calculating segment size: {str(e)}")
            return 0
    
    def _calculate_performance_score(self, performance) -> float:
        """Calculate overall performance score"""
        try:
            # Weighted score based on multiple metrics
            weights = {
                'delivery_rate': 0.2,
                'open_rate': 0.3,
                'click_rate': 0.3,
                'conversion_rate': 0.2
            }
            
            score = 0
            score += performance.delivery_rate * weights['delivery_rate']
            score += performance.open_rate * weights['open_rate']
            score += performance.click_rate * weights['click_rate']
            # Mock conversion rate
            score += (performance.click_rate * 0.1) * weights['conversion_rate']
            
            return round(score, 2)
            
        except Exception as e:
            self.logger.error(f"Error calculating performance score: {str(e)}")
            return 0.0
    
    def _calculate_confidence_level(self, variants: List[Dict[str, Any]], 
                                  metric: str) -> float:
        """Calculate statistical confidence level"""
        try:
            # Simplified confidence calculation
            # In reality, this would use proper statistical methods
            
            if len(variants) < 2:
                return 0.0
            
            values = [v.get(metric, 0) for v in variants]
            if not values:
                return 0.0
            
            # Mock confidence based on sample size and variance
            max_val = max(values)
            min_val = min(values)
            
            if max_val == 0:
                return 0.0
            
            variance = (max_val - min_val) / max_val
            
            # Higher variance = lower confidence
            confidence = max(0.5, 1.0 - variance)
            
            return round(confidence * 100, 1)
            
        except Exception as e:
            self.logger.error(f"Error calculating confidence level: {str(e)}")
            return 0.0
    
    def _is_statistically_significant(self, variants: List[Dict[str, Any]], 
                                    metric: str) -> bool:
        """Check if A/B test results are statistically significant"""
        try:
            confidence = self._calculate_confidence_level(variants, metric)
            return confidence >= 95.0  # 95% confidence threshold
            
        except Exception as e:
            self.logger.error(f"Error checking statistical significance: {str(e)}")
            return False
    
    def _check_trigger_conditions(self, conditions: Dict[str, Any], 
                                user_data: Dict[str, Any]) -> bool:
        """Check if trigger conditions are met"""
        try:
            # Simplified condition checking
            for key, expected_value in conditions.items():
                user_value = user_data.get(key)
                if user_value != expected_value:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking trigger conditions: {str(e)}")
            return False
    
    def _execute_workflow_step(self, step: Dict[str, Any], 
                             user_data: Dict[str, Any]) -> bool:
        """Execute a single workflow step"""
        try:
            step_type = step.get('type', 'email')
            
            if step_type == 'email':
                return self._execute_email_step(step, user_data)
            elif step_type == 'wait':
                return self._execute_wait_step(step, user_data)
            elif step_type == 'condition':
                return self._execute_condition_step(step, user_data)
            elif step_type == 'update_profile':
                return self._execute_update_profile_step(step, user_data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing workflow step: {str(e)}")
            return False
    
    def _execute_email_step(self, step: Dict[str, Any], 
                          user_data: Dict[str, Any]) -> bool:
        """Execute email workflow step"""
        try:
            template_id = step.get('template_id')
            recipient_email = user_data.get('email')
            
            if not template_id or not recipient_email:
                return False
            
            # Send email using template
            return self.test_template(template_id, recipient_email, user_data)
            
        except Exception as e:
            self.logger.error(f"Error executing email step: {str(e)}")
            return False
    
    def _execute_wait_step(self, step: Dict[str, Any], 
                         user_data: Dict[str, Any]) -> bool:
        """Execute wait workflow step"""
        try:
            # In a real implementation, this would schedule the next step
            # For now, just return True
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing wait step: {str(e)}")
            return False
    
    def _execute_condition_step(self, step: Dict[str, Any], 
                              user_data: Dict[str, Any]) -> bool:
        """Execute condition workflow step"""
        try:
            conditions = step.get('conditions', {})
            return self._check_trigger_conditions(conditions, user_data)
            
        except Exception as e:
            self.logger.error(f"Error executing condition step: {str(e)}")
            return False
    
    def _execute_update_profile_step(self, step: Dict[str, Any], 
                                   user_data: Dict[str, Any]) -> bool:
        """Execute update profile workflow step"""
        try:
            # In a real implementation, this would update user profile
            # For now, just return True
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing update profile step: {str(e)}")
            return False
    
    def _calculate_campaign_roi(self, campaign_id: str) -> Dict[str, Any]:
        """Calculate campaign ROI"""
        try:
            # Mock ROI calculation
            return {
                'total_cost': 50.0,
                'total_revenue': 250.0,
                'roi_percentage': 400.0,
                'cost_per_conversion': 5.0,
                'revenue_per_email': 2.50
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating campaign ROI: {str(e)}")
            return {}
    
    def _process_campaigns(self):
        """Background thread to process campaign queue"""
        while self.is_running:
            try:
                if not self.campaign_queue:
                    time.sleep(10)
                    continue
                
                # Process next campaign in queue
                campaign_task = self.campaign_queue.pop(0)
                self._process_campaign_task(campaign_task)
                
            except Exception as e:
                self.logger.error(f"Error processing campaigns: {str(e)}")
                time.sleep(30)
    
    def _process_campaign_task(self, task: Dict[str, Any]):
        """Process a single campaign task"""
        try:
            campaign_id = task['campaign_id']
            action = task['action']
            
            if action == 'send':
                self._send_campaign(campaign_id)
            elif action == 'schedule':
                self._schedule_campaign(campaign_id)
            
        except Exception as e:
            self.logger.error(f"Error processing campaign task: {str(e)}")
    
    def _send_campaign(self, campaign_id: str):
        """Send campaign to all recipients"""
        try:
            campaign = self.get_campaign(campaign_id)
            if not campaign:
                return
            
            # Get segment and template
            segment = self.get_segment(campaign['segment_id'])
            template = self.get_template(campaign['template_id'])
            
            if not segment or not template:
                return
            
            # Get recipients from segment
            recipients = self._get_segment_recipients(segment)
            
            # Send emails to all recipients
            sent_count = 0
            for recipient in recipients:
                try:
                    # Personalize email for recipient
                    personalized_content = self._personalize_email(template, recipient)
                    
                    # Send email
                    message = self.email_service._create_message(
                        recipient['email'],
                        personalized_content['subject'],
                        personalized_content['text_content'],
                        personalized_content['html_content']
                    )
                    
                    success = self.email_service._send_email(
                        message, 
                        email_type='campaign',
                        transaction_id=campaign_id
                    )
                    
                    if success:
                        sent_count += 1
                        
                        # Track sending
                        self.performance_tracker.track_email_sent(
                            str(uuid.uuid4()),
                            campaign['template_id'],
                            recipient['email'],
                            personalized_content['subject'],
                            'campaign'
                        )
                    
                except Exception as e:
                    self.logger.error(f"Error sending email to {recipient.get('email', 'unknown')}: {str(e)}")
                    continue
            
            # Update campaign status
            self.db.update_campaign(
                campaign_id,
                status=CampaignStatus.COMPLETED.value,
                completed_at=datetime.now(),
                sent_count=sent_count
            )
            
            self.logger.info(f"Campaign sent: {campaign_id} - {sent_count} emails")
            
        except Exception as e:
            self.logger.error(f"Error sending campaign: {str(e)}")
    
    def _schedule_campaign(self, campaign_id: str):
        """Schedule campaign for later execution"""
        try:
            campaign = self.get_campaign(campaign_id)
            if not campaign:
                return
            
            scheduled_at = campaign.get('scheduled_at')
            if not scheduled_at:
                return
            
            # Check if it's time to send
            if datetime.now() >= scheduled_at:
                self.campaign_queue.append({
                    'campaign_id': campaign_id,
                    'action': 'send',
                    'priority': 'normal',
                    'queued_at': datetime.now()
                })
            
        except Exception as e:
            self.logger.error(f"Error scheduling campaign: {str(e)}")
    
    def _get_segment_recipients(self, segment: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get recipients for a segment"""
        try:
            # This is a simplified implementation
            # In a real system, this would query the database based on segment conditions
            
            # For now, return mock recipients
            return [
                {'email': 'test1@example.com', 'name': 'Test User 1'},
                {'email': 'test2@example.com', 'name': 'Test User 2'}
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting segment recipients: {str(e)}")
            return []
    
    def _personalize_email(self, template: Dict[str, Any], 
                         recipient: Dict[str, Any]) -> Dict[str, str]:
        """Personalize email content for recipient"""
        try:
            # Use Jinja2 to render template with recipient data
            html_template = self.jinja_env.from_string(template['body_html'])
            text_template = self.jinja_env.from_string(template['body_text'])
            subject_template = self.jinja_env.from_string(template['subject'])
            
            # Add default variables
            template_vars = {
                'name': recipient.get('name', 'Valued Customer'),
                'email': recipient.get('email', ''),
                'first_name': recipient.get('name', '').split(' ')[0] if recipient.get('name') else 'Friend'
            }
            
            # Add any custom variables
            template_vars.update(recipient)
            
            return {
                'html_content': html_template.render(**template_vars),
                'text_content': text_template.render(**template_vars),
                'subject': subject_template.render(**template_vars)
            }
            
        except Exception as e:
            self.logger.error(f"Error personalizing email: {str(e)}")
            return {
                'html_content': template.get('body_html', ''),
                'text_content': template.get('body_text', ''),
                'subject': template.get('subject', '')
            }
    
    def stop(self):
        """Stop the campaign manager"""
        self.is_running = False
        self.logger.info("Email Campaign Manager stopped")

# Global email campaign manager instance
email_campaign_manager = EmailCampaignManager()