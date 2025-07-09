"""
Marketing Manager Service - Core Marketing Automation Platform
Provides comprehensive marketing automation, customer journey management, and engagement tools.
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
from services.analytics_service import AnalyticsService
from services.monitoring.system_logger import SystemLogger

logger = logging.getLogger(__name__)

class CustomerLifecycleStage(Enum):
    """Customer lifecycle stages for journey management"""
    VISITOR = "visitor"
    LEAD = "lead"
    PROSPECT = "prospect"
    CUSTOMER = "customer"
    ADVOCATE = "advocate"
    INACTIVE = "inactive"

class CampaignType(Enum):
    """Types of marketing campaigns"""
    EMAIL = "email"
    SOCIAL = "social"
    CONTENT = "content"
    PAID_ADS = "paid_ads"
    REFERRAL = "referral"
    RETENTION = "retention"
    ONBOARDING = "onboarding"
    WINBACK = "winback"

class CampaignStatus(Enum):
    """Campaign status options"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

@dataclass
class CustomerJourneyStage:
    """Represents a stage in the customer journey"""
    stage_id: str
    name: str
    description: str
    stage_order: int
    entry_conditions: Dict[str, Any]
    exit_conditions: Dict[str, Any]
    automation_rules: List[Dict[str, Any]]
    avg_duration_days: int
    success_rate: float
    created_at: datetime
    updated_at: datetime

@dataclass
class MarketingCampaign:
    """Represents a marketing campaign"""
    campaign_id: str
    name: str
    campaign_type: CampaignType
    status: CampaignStatus
    target_audience: Dict[str, Any]
    content_config: Dict[str, Any]
    schedule_config: Dict[str, Any]
    budget_config: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    created_by: str
    created_at: datetime
    updated_at: datetime
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

@dataclass
class LeadScore:
    """Lead scoring information"""
    lead_id: str
    user_id: Optional[str]
    email: str
    score: int
    score_factors: Dict[str, Any]
    qualification_status: str
    last_activity: datetime
    created_at: datetime
    updated_at: datetime

@dataclass
class CustomerInsight:
    """Customer behavioral insights"""
    customer_id: str
    insight_type: str
    insight_data: Dict[str, Any]
    confidence_score: float
    actionable_recommendations: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None

class MarketingManager:
    """Core marketing automation and customer engagement manager"""
    
    def __init__(self, db_pool: DatabasePool, email_service: EmailService, 
                 analytics_service: AnalyticsService, system_logger: SystemLogger):
        self.db_pool = db_pool
        self.email_service = email_service
        self.analytics_service = analytics_service
        self.system_logger = system_logger
        self.logger = logging.getLogger(__name__)
        
        # Initialize database tables
        self._init_database()
        
    def _init_database(self):
        """Initialize marketing database tables"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            # Customer journey stages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customer_journey_stages (
                    stage_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    stage_order INTEGER NOT NULL,
                    entry_conditions TEXT,
                    exit_conditions TEXT,
                    automation_rules TEXT,
                    avg_duration_days INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Customer journey tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customer_journey_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id TEXT NOT NULL,
                    current_stage TEXT NOT NULL,
                    previous_stage TEXT,
                    stage_entry_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    stage_duration_days INTEGER DEFAULT 0,
                    conversion_score REAL DEFAULT 0.0,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (current_stage) REFERENCES customer_journey_stages(stage_id)
                )
            ''')
            
            # Marketing campaigns table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS marketing_campaigns (
                    campaign_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    campaign_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    target_audience TEXT,
                    content_config TEXT,
                    schedule_config TEXT,
                    budget_config TEXT,
                    performance_metrics TEXT,
                    created_by TEXT NOT NULL,
                    start_date TIMESTAMP,
                    end_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Lead scoring table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS lead_scoring (
                    lead_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    email TEXT NOT NULL,
                    score INTEGER DEFAULT 0,
                    score_factors TEXT,
                    qualification_status TEXT DEFAULT 'unqualified',
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Customer insights table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customer_insights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id TEXT NOT NULL,
                    insight_type TEXT NOT NULL,
                    insight_data TEXT,
                    confidence_score REAL DEFAULT 0.0,
                    actionable_recommendations TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            ''')
            
            # Marketing automation rules table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS marketing_automation_rules (
                    rule_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    trigger_type TEXT NOT NULL,
                    trigger_conditions TEXT,
                    actions TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    execution_count INTEGER DEFAULT 0,
                    last_executed TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Campaign analytics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS campaign_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campaign_id TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    metric_date DATE NOT NULL,
                    additional_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (campaign_id) REFERENCES marketing_campaigns(campaign_id)
                )
            ''')
            
            # A/B test results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ab_test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_id TEXT NOT NULL,
                    variant_name TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    sample_size INTEGER NOT NULL,
                    confidence_level REAL DEFAULT 0.95,
                    is_winner BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            self.logger.info("Marketing database tables initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing marketing database: {str(e)}")
            raise
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    # Customer Journey Management
    def create_journey_stage(self, stage_data: Dict[str, Any]) -> CustomerJourneyStage:
        """Create a new customer journey stage"""
        try:
            stage_id = f"stage_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            stage = CustomerJourneyStage(
                stage_id=stage_id,
                name=stage_data['name'],
                description=stage_data.get('description', ''),
                stage_order=stage_data['stage_order'],
                entry_conditions=stage_data.get('entry_conditions', {}),
                exit_conditions=stage_data.get('exit_conditions', {}),
                automation_rules=stage_data.get('automation_rules', []),
                avg_duration_days=stage_data.get('avg_duration_days', 0),
                success_rate=stage_data.get('success_rate', 0.0),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO customer_journey_stages
                (stage_id, name, description, stage_order, entry_conditions, exit_conditions,
                 automation_rules, avg_duration_days, success_rate, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                stage.stage_id, stage.name, stage.description, stage.stage_order,
                json.dumps(stage.entry_conditions), json.dumps(stage.exit_conditions),
                json.dumps(stage.automation_rules), stage.avg_duration_days,
                stage.success_rate, stage.created_at, stage.updated_at
            ))
            
            conn.commit()
            self.logger.info(f"Created customer journey stage: {stage.name}")
            
            return stage
            
        except Exception as e:
            self.logger.error(f"Error creating journey stage: {str(e)}")
            raise
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def get_customer_journey_stages(self) -> List[CustomerJourneyStage]:
        """Get all customer journey stages"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM customer_journey_stages
                ORDER BY stage_order
            ''')
            
            stages = []
            for row in cursor.fetchall():
                stage = CustomerJourneyStage(
                    stage_id=row[0],
                    name=row[1],
                    description=row[2],
                    stage_order=row[3],
                    entry_conditions=json.loads(row[4]) if row[4] else {},
                    exit_conditions=json.loads(row[5]) if row[5] else {},
                    automation_rules=json.loads(row[6]) if row[6] else [],
                    avg_duration_days=row[7],
                    success_rate=row[8],
                    created_at=row[9],
                    updated_at=row[10]
                )
                stages.append(stage)
            
            return stages
            
        except Exception as e:
            self.logger.error(f"Error getting journey stages: {str(e)}")
            return []
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def update_customer_journey_stage(self, customer_id: str, new_stage: str, 
                                    metadata: Dict[str, Any] = None) -> bool:
        """Update a customer's journey stage"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            # Get current stage
            cursor.execute('''
                SELECT current_stage, stage_entry_date FROM customer_journey_tracking
                WHERE customer_id = ?
                ORDER BY created_at DESC LIMIT 1
            ''', (customer_id,))
            
            result = cursor.fetchone()
            previous_stage = result[0] if result else None
            stage_entry_date = result[1] if result else datetime.now()
            
            # Calculate stage duration
            stage_duration = (datetime.now() - stage_entry_date).days if result else 0
            
            # Insert new stage tracking record
            cursor.execute('''
                INSERT INTO customer_journey_tracking
                (customer_id, current_stage, previous_stage, stage_entry_date,
                 stage_duration_days, conversion_score, last_activity, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                customer_id, new_stage, previous_stage, datetime.now(),
                stage_duration, 0.0, datetime.now(), 
                json.dumps(metadata) if metadata else None
            ))
            
            conn.commit()
            self.logger.info(f"Updated customer {customer_id} journey stage to {new_stage}")
            
            # Trigger automation rules for new stage
            self._trigger_stage_automation(customer_id, new_stage)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating customer journey stage: {str(e)}")
            return False
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _trigger_stage_automation(self, customer_id: str, stage: str):
        """Trigger automation rules for a specific journey stage"""
        try:
            # Get automation rules for this stage
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT automation_rules FROM customer_journey_stages
                WHERE stage_id = ?
            ''', (stage,))
            
            result = cursor.fetchone()
            if not result:
                return
            
            automation_rules = json.loads(result[0]) if result[0] else []
            
            for rule in automation_rules:
                self._execute_automation_rule(customer_id, rule)
                
        except Exception as e:
            self.logger.error(f"Error triggering stage automation: {str(e)}")
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _execute_automation_rule(self, customer_id: str, rule: Dict[str, Any]):
        """Execute a specific automation rule"""
        try:
            rule_type = rule.get('type')
            
            if rule_type == 'email':
                self._send_automated_email(customer_id, rule)
            elif rule_type == 'lead_score_update':
                self._update_lead_score(customer_id, rule)
            elif rule_type == 'campaign_enrollment':
                self._enroll_in_campaign(customer_id, rule)
            elif rule_type == 'notification':
                self._send_internal_notification(customer_id, rule)
                
        except Exception as e:
            self.logger.error(f"Error executing automation rule: {str(e)}")

    def _send_automated_email(self, customer_id: str, rule: Dict[str, Any]):
        """Send automated email as part of journey automation"""
        try:
            # Get customer email
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT email FROM users WHERE id = ?', (customer_id,))
            result = cursor.fetchone()
            
            if not result:
                return
            
            email = result[0]
            template_id = rule.get('template_id')
            delay_hours = rule.get('delay_hours', 0)
            
            # Schedule email (implement scheduling logic)
            if delay_hours > 0:
                # Add to email queue with delay
                pass
            else:
                # Send immediately
                self.email_service.send_template_email(
                    to_email=email,
                    template_id=template_id,
                    template_data={'customer_id': customer_id}
                )
                
        except Exception as e:
            self.logger.error(f"Error sending automated email: {str(e)}")
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    # Campaign Management
    def create_campaign(self, campaign_data: Dict[str, Any]) -> MarketingCampaign:
        """Create a new marketing campaign"""
        try:
            campaign_id = f"campaign_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            campaign = MarketingCampaign(
                campaign_id=campaign_id,
                name=campaign_data['name'],
                campaign_type=CampaignType(campaign_data['campaign_type']),
                status=CampaignStatus(campaign_data.get('status', 'draft')),
                target_audience=campaign_data.get('target_audience', {}),
                content_config=campaign_data.get('content_config', {}),
                schedule_config=campaign_data.get('schedule_config', {}),
                budget_config=campaign_data.get('budget_config', {}),
                performance_metrics=campaign_data.get('performance_metrics', {}),
                created_by=campaign_data['created_by'],
                start_date=campaign_data.get('start_date'),
                end_date=campaign_data.get('end_date'),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO marketing_campaigns
                (campaign_id, name, campaign_type, status, target_audience,
                 content_config, schedule_config, budget_config, performance_metrics,
                 created_by, start_date, end_date, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                campaign.campaign_id, campaign.name, campaign.campaign_type.value,
                campaign.status.value, json.dumps(campaign.target_audience),
                json.dumps(campaign.content_config), json.dumps(campaign.schedule_config),
                json.dumps(campaign.budget_config), json.dumps(campaign.performance_metrics),
                campaign.created_by, campaign.start_date, campaign.end_date,
                campaign.created_at, campaign.updated_at
            ))
            
            conn.commit()
            self.logger.info(f"Created marketing campaign: {campaign.name}")
            
            return campaign
            
        except Exception as e:
            self.logger.error(f"Error creating campaign: {str(e)}")
            raise
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def get_campaigns(self, status: Optional[str] = None, 
                     campaign_type: Optional[str] = None) -> List[MarketingCampaign]:
        """Get marketing campaigns with optional filtering"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            query = 'SELECT * FROM marketing_campaigns'
            params = []
            conditions = []
            
            if status:
                conditions.append('status = ?')
                params.append(status)
            
            if campaign_type:
                conditions.append('campaign_type = ?')
                params.append(campaign_type)
            
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            
            query += ' ORDER BY created_at DESC'
            
            cursor.execute(query, params)
            
            campaigns = []
            for row in cursor.fetchall():
                campaign = MarketingCampaign(
                    campaign_id=row[0],
                    name=row[1],
                    campaign_type=CampaignType(row[2]),
                    status=CampaignStatus(row[3]),
                    target_audience=json.loads(row[4]) if row[4] else {},
                    content_config=json.loads(row[5]) if row[5] else {},
                    schedule_config=json.loads(row[6]) if row[6] else {},
                    budget_config=json.loads(row[7]) if row[7] else {},
                    performance_metrics=json.loads(row[8]) if row[8] else {},
                    created_by=row[9],
                    start_date=row[10],
                    end_date=row[11],
                    created_at=row[12],
                    updated_at=row[13]
                )
                campaigns.append(campaign)
            
            return campaigns
            
        except Exception as e:
            self.logger.error(f"Error getting campaigns: {str(e)}")
            return []
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    # Lead Scoring
    def update_lead_score(self, email: str, score_change: int, 
                         factor: str, user_id: Optional[str] = None) -> LeadScore:
        """Update lead score based on actions"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            # Get current lead score
            cursor.execute('''
                SELECT lead_id, score, score_factors FROM lead_scoring
                WHERE email = ?
            ''', (email,))
            
            result = cursor.fetchone()
            
            if result:
                # Update existing lead
                lead_id, current_score, score_factors_json = result
                score_factors = json.loads(score_factors_json) if score_factors_json else {}
                
                new_score = max(0, current_score + score_change)
                score_factors[factor] = score_factors.get(factor, 0) + score_change
                
                cursor.execute('''
                    UPDATE lead_scoring
                    SET score = ?, score_factors = ?, last_activity = ?, updated_at = ?
                    WHERE lead_id = ?
                ''', (new_score, json.dumps(score_factors), datetime.now(), 
                      datetime.now(), lead_id))
                
            else:
                # Create new lead
                lead_id = f"lead_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                score_factors = {factor: score_change}
                new_score = max(0, score_change)
                
                cursor.execute('''
                    INSERT INTO lead_scoring
                    (lead_id, user_id, email, score, score_factors, last_activity)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (lead_id, user_id, email, new_score, json.dumps(score_factors), 
                      datetime.now()))
            
            conn.commit()
            
            # Determine qualification status
            qualification_status = self._determine_qualification_status(new_score)
            
            cursor.execute('''
                UPDATE lead_scoring
                SET qualification_status = ?
                WHERE lead_id = ?
            ''', (qualification_status, lead_id))
            
            conn.commit()
            
            return LeadScore(
                lead_id=lead_id,
                user_id=user_id,
                email=email,
                score=new_score,
                score_factors=score_factors,
                qualification_status=qualification_status,
                last_activity=datetime.now(),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error updating lead score: {str(e)}")
            raise
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _determine_qualification_status(self, score: int) -> str:
        """Determine lead qualification status based on score"""
        if score >= 80:
            return 'hot'
        elif score >= 60:
            return 'warm'
        elif score >= 40:
            return 'qualified'
        else:
            return 'unqualified'

    def get_lead_scores(self, qualification_status: Optional[str] = None,
                       limit: int = 100) -> List[LeadScore]:
        """Get lead scores with optional filtering"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            query = '''
                SELECT lead_id, user_id, email, score, score_factors,
                       qualification_status, last_activity, created_at, updated_at
                FROM lead_scoring
            '''
            params = []
            
            if qualification_status:
                query += ' WHERE qualification_status = ?'
                params.append(qualification_status)
            
            query += ' ORDER BY score DESC, last_activity DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            
            leads = []
            for row in cursor.fetchall():
                lead = LeadScore(
                    lead_id=row[0],
                    user_id=row[1],
                    email=row[2],
                    score=row[3],
                    score_factors=json.loads(row[4]) if row[4] else {},
                    qualification_status=row[5],
                    last_activity=row[6],
                    created_at=row[7],
                    updated_at=row[8]
                )
                leads.append(lead)
            
            return leads
            
        except Exception as e:
            self.logger.error(f"Error getting lead scores: {str(e)}")
            return []
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    # Analytics and Insights
    def generate_customer_insights(self, customer_id: str) -> List[CustomerInsight]:
        """Generate behavioral insights for a customer"""
        try:
            insights = []
            
            # Analyze customer behavior patterns
            behavioral_insight = self._analyze_customer_behavior(customer_id)
            if behavioral_insight:
                insights.append(behavioral_insight)
            
            # Analyze purchase patterns
            purchase_insight = self._analyze_purchase_patterns(customer_id)
            if purchase_insight:
                insights.append(purchase_insight)
            
            # Analyze engagement patterns
            engagement_insight = self._analyze_engagement_patterns(customer_id)
            if engagement_insight:
                insights.append(engagement_insight)
            
            # Store insights in database
            self._store_customer_insights(insights)
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error generating customer insights: {str(e)}")
            return []

    def _analyze_customer_behavior(self, customer_id: str) -> Optional[CustomerInsight]:
        """Analyze customer behavior patterns"""
        try:
            # Get customer activity data
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) as login_count, MAX(last_login) as last_login
                FROM users WHERE id = ?
            ''', (customer_id,))
            
            result = cursor.fetchone()
            if not result:
                return None
            
            login_count, last_login = result
            
            # Analyze patterns
            insight_data = {
                'login_frequency': login_count,
                'last_activity': last_login,
                'activity_level': 'high' if login_count > 10 else 'moderate' if login_count > 5 else 'low'
            }
            
            # Generate recommendations
            recommendations = []
            if login_count > 20:
                recommendations.append("Customer shows high engagement - consider premium features")
            elif login_count < 3:
                recommendations.append("Low engagement - send re-engagement campaign")
            
            return CustomerInsight(
                customer_id=customer_id,
                insight_type='behavioral',
                insight_data=insight_data,
                confidence_score=0.8,
                actionable_recommendations=recommendations,
                created_at=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing customer behavior: {str(e)}")
            return None
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _analyze_purchase_patterns(self, customer_id: str) -> Optional[CustomerInsight]:
        """Analyze customer purchase patterns"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) as transaction_count, SUM(amount) as total_spent,
                       MAX(created_at) as last_purchase
                FROM transactions WHERE username = (
                    SELECT username FROM users WHERE id = ?
                ) AND status = 'completed'
            ''', (customer_id,))
            
            result = cursor.fetchone()
            if not result:
                return None
            
            transaction_count, total_spent, last_purchase = result
            
            insight_data = {
                'transaction_count': transaction_count or 0,
                'total_spent': float(total_spent) if total_spent else 0.0,
                'last_purchase': last_purchase,
                'customer_value': 'high' if (total_spent or 0) > 100 else 'medium' if (total_spent or 0) > 50 else 'low'
            }
            
            recommendations = []
            if transaction_count > 3:
                recommendations.append("Loyal customer - offer loyalty rewards")
            elif transaction_count == 1:
                recommendations.append("First-time buyer - send follow-up campaign")
            
            return CustomerInsight(
                customer_id=customer_id,
                insight_type='purchase',
                insight_data=insight_data,
                confidence_score=0.9,
                actionable_recommendations=recommendations,
                created_at=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing purchase patterns: {str(e)}")
            return None
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _analyze_engagement_patterns(self, customer_id: str) -> Optional[CustomerInsight]:
        """Analyze customer engagement patterns"""
        try:
            # This would analyze email opens, clicks, app usage, etc.
            # For now, we'll create a basic engagement analysis
            
            insight_data = {
                'engagement_level': 'moderate',
                'preferred_channels': ['email', 'web'],
                'response_rate': 0.25,
                'best_contact_time': '10:00-12:00'
            }
            
            recommendations = [
                "Schedule campaigns for 10-12 AM for better engagement",
                "Focus on email and web channels"
            ]
            
            return CustomerInsight(
                customer_id=customer_id,
                insight_type='engagement',
                insight_data=insight_data,
                confidence_score=0.7,
                actionable_recommendations=recommendations,
                created_at=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing engagement patterns: {str(e)}")
            return None

    def _store_customer_insights(self, insights: List[CustomerInsight]):
        """Store customer insights in database"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            for insight in insights:
                cursor.execute('''
                    INSERT INTO customer_insights
                    (customer_id, insight_type, insight_data, confidence_score,
                     actionable_recommendations, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    insight.customer_id,
                    insight.insight_type,
                    json.dumps(insight.insight_data),
                    insight.confidence_score,
                    json.dumps(insight.actionable_recommendations),
                    insight.created_at,
                    insight.expires_at
                ))
            
            conn.commit()
            
        except Exception as e:
            self.logger.error(f"Error storing customer insights: {str(e)}")
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def get_marketing_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive marketing dashboard data"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            # Campaign metrics
            cursor.execute('''
                SELECT status, COUNT(*) as count
                FROM marketing_campaigns
                GROUP BY status
            ''')
            campaign_metrics = dict(cursor.fetchall())
            
            # Lead metrics
            cursor.execute('''
                SELECT qualification_status, COUNT(*) as count
                FROM lead_scoring
                GROUP BY qualification_status
            ''')
            lead_metrics = dict(cursor.fetchall())
            
            # Journey stage metrics
            cursor.execute('''
                SELECT current_stage, COUNT(*) as count
                FROM customer_journey_tracking
                GROUP BY current_stage
            ''')
            journey_metrics = dict(cursor.fetchall())
            
            # Recent insights
            cursor.execute('''
                SELECT insight_type, COUNT(*) as count
                FROM customer_insights
                WHERE created_at >= date('now', '-7 days')
                GROUP BY insight_type
            ''')
            recent_insights = dict(cursor.fetchall())
            
            # Performance trends (mock data for now)
            performance_trends = {
                'conversion_rate': 0.15,
                'engagement_rate': 0.35,
                'customer_acquisition_cost': 45.50,
                'lifetime_value': 150.75
            }
            
            return {
                'campaign_metrics': campaign_metrics,
                'lead_metrics': lead_metrics,
                'journey_metrics': journey_metrics,
                'recent_insights': recent_insights,
                'performance_trends': performance_trends,
                'total_campaigns': sum(campaign_metrics.values()),
                'total_leads': sum(lead_metrics.values()),
                'active_customers': sum(journey_metrics.values()),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting marketing dashboard data: {str(e)}")
            return {}
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def get_campaign_performance(self, campaign_id: str) -> Dict[str, Any]:
        """Get detailed campaign performance metrics"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            # Get campaign details
            cursor.execute('''
                SELECT * FROM marketing_campaigns
                WHERE campaign_id = ?
            ''', (campaign_id,))
            
            campaign_data = cursor.fetchone()
            if not campaign_data:
                return {}
            
            # Get analytics data
            cursor.execute('''
                SELECT metric_name, metric_value, metric_date
                FROM campaign_analytics
                WHERE campaign_id = ?
                ORDER BY metric_date DESC
            ''', (campaign_id,))
            
            analytics_data = cursor.fetchall()
            
            # Process analytics into performance metrics
            metrics = {}
            for metric_name, metric_value, metric_date in analytics_data:
                if metric_name not in metrics:
                    metrics[metric_name] = []
                metrics[metric_name].append({
                    'date': metric_date,
                    'value': metric_value
                })
            
            return {
                'campaign_id': campaign_id,
                'campaign_name': campaign_data[1],
                'status': campaign_data[3],
                'metrics': metrics,
                'performance_summary': {
                    'total_reach': sum([m['value'] for m in metrics.get('reach', [])]),
                    'total_engagement': sum([m['value'] for m in metrics.get('engagement', [])]),
                    'conversion_rate': metrics.get('conversion_rate', [{'value': 0}])[-1]['value']
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting campaign performance: {str(e)}")
            return {}
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def run_ab_test(self, test_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run A/B test for marketing campaigns"""
        try:
            test_id = f"abtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Mock A/B test results for demonstration
            results = {
                'test_id': test_id,
                'test_name': test_config.get('name', 'Unnamed Test'),
                'variants': [
                    {
                        'name': 'Control',
                        'conversion_rate': 0.12,
                        'sample_size': 1000,
                        'confidence_level': 0.95
                    },
                    {
                        'name': 'Variant A',
                        'conversion_rate': 0.15,
                        'sample_size': 1000,
                        'confidence_level': 0.95
                    }
                ],
                'winner': 'Variant A',
                'statistical_significance': True,
                'created_at': datetime.now().isoformat()
            }
            
            # Store results in database
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            for variant in results['variants']:
                cursor.execute('''
                    INSERT INTO ab_test_results
                    (test_id, variant_name, metric_name, metric_value,
                     sample_size, confidence_level, is_winner)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    test_id,
                    variant['name'],
                    'conversion_rate',
                    variant['conversion_rate'],
                    variant['sample_size'],
                    variant['confidence_level'],
                    variant['name'] == results['winner']
                ))
            
            conn.commit()
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error running A/B test: {str(e)}")
            return {}
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def get_customer_lifetime_value(self, customer_id: str) -> float:
        """Calculate customer lifetime value"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            # Get customer transaction history
            cursor.execute('''
                SELECT SUM(amount) as total_spent, COUNT(*) as transaction_count,
                       MIN(created_at) as first_purchase
                FROM transactions
                WHERE username = (SELECT username FROM users WHERE id = ?)
                AND status = 'completed'
            ''', (customer_id,))
            
            result = cursor.fetchone()
            if not result:
                return 0.0
            
            total_spent, transaction_count, first_purchase = result
            
            if not total_spent or not transaction_count:
                return 0.0
            
            # Calculate average order value
            avg_order_value = total_spent / transaction_count
            
            # Calculate customer lifespan (in months)
            first_purchase_date = datetime.fromisoformat(first_purchase.replace('Z', '+00:00'))
            lifespan_months = (datetime.now() - first_purchase_date).days / 30.44
            
            if lifespan_months < 1:
                lifespan_months = 1
            
            # Calculate purchase frequency (orders per month)
            purchase_frequency = transaction_count / lifespan_months
            
            # Simple CLV calculation
            clv = avg_order_value * purchase_frequency * 12  # Annual CLV
            
            return round(clv, 2)
            
        except Exception as e:
            self.logger.error(f"Error calculating customer lifetime value: {str(e)}")
            return 0.0
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def predict_churn_risk(self, customer_id: str) -> Dict[str, Any]:
        """Predict customer churn risk"""
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            # Get customer data
            cursor.execute('''
                SELECT last_login, created_at FROM users WHERE id = ?
            ''', (customer_id,))
            
            user_data = cursor.fetchone()
            if not user_data:
                return {}
            
            last_login, created_at = user_data
            
            # Get transaction data
            cursor.execute('''
                SELECT MAX(created_at) as last_purchase, COUNT(*) as total_purchases
                FROM transactions
                WHERE username = (SELECT username FROM users WHERE id = ?)
                AND status = 'completed'
            ''', (customer_id,))
            
            transaction_data = cursor.fetchone()
            
            # Simple churn prediction logic
            days_since_last_login = (datetime.now() - datetime.fromisoformat(last_login.replace('Z', '+00:00'))).days
            total_purchases = transaction_data[1] if transaction_data[1] else 0
            
            # Calculate risk score
            risk_score = 0.0
            
            if days_since_last_login > 30:
                risk_score += 0.4
            elif days_since_last_login > 14:
                risk_score += 0.2
            
            if total_purchases == 0:
                risk_score += 0.3
            elif total_purchases == 1:
                risk_score += 0.2
            
            # Determine risk level
            if risk_score >= 0.7:
                risk_level = 'high'
            elif risk_score >= 0.4:
                risk_level = 'medium'
            else:
                risk_level = 'low'
            
            return {
                'customer_id': customer_id,
                'risk_score': risk_score,
                'risk_level': risk_level,
                'factors': {
                    'days_since_last_login': days_since_last_login,
                    'total_purchases': total_purchases
                },
                'recommendations': self._get_churn_prevention_recommendations(risk_level),
                'predicted_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error predicting churn risk: {str(e)}")
            return {}
        finally:
            if conn:
                self.db_pool.return_connection(conn)

    def _get_churn_prevention_recommendations(self, risk_level: str) -> List[str]:
        """Get churn prevention recommendations based on risk level"""
        recommendations = {
            'high': [
                "Send immediate re-engagement campaign",
                "Offer personalized discount or incentive",
                "Assign to customer success team",
                "Conduct customer satisfaction survey"
            ],
            'medium': [
                "Send educational content about product features",
                "Invite to webinar or product demo",
                "Provide usage tips and best practices",
                "Offer limited-time promotion"
            ],
            'low': [
                "Continue regular engagement campaigns",
                "Monitor for changes in behavior",
                "Collect feedback on product experience",
                "Maintain consistent communication"
            ]
        }
        
        return recommendations.get(risk_level, [])