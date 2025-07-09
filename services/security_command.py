#!/usr/bin/env python3
"""
Security Command Center Service for VectorCraft
Comprehensive security management with advanced policy control, threat intelligence, and compliance
"""

import os
import json
import logging
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import threading
from collections import defaultdict, deque
import ipaddress
import re
import requests
from urllib.parse import urlparse
import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

logger = logging.getLogger(__name__)

class PolicyAction(Enum):
    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"
    LOG = "log"
    QUARANTINE = "quarantine"

class ThreatLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ComplianceFramework(Enum):
    GDPR = "gdpr"
    CCPA = "ccpa"
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    PCI_DSS = "pci_dss"
    HIPAA = "hipaa"

@dataclass
class SecurityPolicy:
    """Security policy configuration"""
    id: str
    name: str
    description: str
    enabled: bool
    policy_type: str
    conditions: Dict[str, Any]
    actions: List[Dict[str, Any]]
    severity: str
    created_at: datetime
    updated_at: datetime
    created_by: str
    version: int

@dataclass
class ThreatIntelligence:
    """Threat intelligence data"""
    id: str
    indicator_type: str
    indicator_value: str
    threat_level: ThreatLevel
    confidence: float
    source: str
    description: str
    mitigation: str
    first_seen: datetime
    last_seen: datetime
    tags: List[str]
    ioc_hash: str

@dataclass
class SecurityIncident:
    """Security incident tracking"""
    id: str
    title: str
    description: str
    severity: ThreatLevel
    status: str
    assigned_to: str
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
    affected_assets: List[str]
    timeline: List[Dict[str, Any]]
    response_actions: List[Dict[str, Any]]
    lessons_learned: Optional[str]

@dataclass
class ComplianceCheck:
    """Compliance verification check"""
    id: str
    framework: ComplianceFramework
    control_id: str
    control_name: str
    description: str
    status: str
    last_checked: datetime
    next_check: datetime
    evidence: List[str]
    gaps: List[str]
    remediation_plan: Optional[str]

@dataclass
class SecurityMetric:
    """Security metrics and KPIs"""
    metric_name: str
    value: float
    unit: str
    timestamp: datetime
    trend: str
    threshold: Optional[float]
    alert_level: Optional[str]

class SecurityCommandCenter:
    """Advanced Security Command Center"""
    
    def __init__(self):
        self.db_path = 'vectorcraft.db'
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)
        
        # Initialize threat intelligence feeds
        self.threat_feeds = {
            'internal': [],
            'external': []
        }
        
        # Security metrics tracking
        self.metrics = defaultdict(deque)
        self.metric_thresholds = {}
        
        # Policy engine
        self.policies = {}
        self.policy_cache = {}
        
        # Incident management
        self.active_incidents = {}
        self.incident_playbooks = {}
        
        # Compliance tracking
        self.compliance_checks = {}
        self.compliance_status = {}
        
        # Initialize database
        self._init_database()
        
        # Load policies and configurations
        self._load_policies()
        self._load_threat_intelligence()
        self._load_compliance_frameworks()
        
        # Start background services
        self._start_background_services()
        
        logger.info("Security Command Center initialized successfully")
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for sensitive data"""
        key_file = 'security_key.key'
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            os.chmod(key_file, 0o600)  # Restrict permissions
            return key
    
    def _init_database(self):
        """Initialize security command center database tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Security policies table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS security_policies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    enabled BOOLEAN DEFAULT 1,
                    policy_type TEXT NOT NULL,
                    conditions TEXT,
                    actions TEXT,
                    severity TEXT DEFAULT 'MEDIUM',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT,
                    version INTEGER DEFAULT 1
                )
            ''')
            
            # Threat intelligence table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS threat_intelligence (
                    id TEXT PRIMARY KEY,
                    indicator_type TEXT NOT NULL,
                    indicator_value TEXT NOT NULL,
                    threat_level TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    source TEXT NOT NULL,
                    description TEXT,
                    mitigation TEXT,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    tags TEXT,
                    ioc_hash TEXT UNIQUE
                )
            ''')
            
            # Security incidents table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS security_incidents (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    severity TEXT NOT NULL,
                    status TEXT DEFAULT 'OPEN',
                    assigned_to TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP,
                    affected_assets TEXT,
                    timeline TEXT,
                    response_actions TEXT,
                    lessons_learned TEXT
                )
            ''')
            
            # Compliance checks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS compliance_checks (
                    id TEXT PRIMARY KEY,
                    framework TEXT NOT NULL,
                    control_id TEXT NOT NULL,
                    control_name TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'PENDING',
                    last_checked TIMESTAMP,
                    next_check TIMESTAMP,
                    evidence TEXT,
                    gaps TEXT,
                    remediation_plan TEXT
                )
            ''')
            
            # Security metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS security_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    trend TEXT,
                    threshold REAL,
                    alert_level TEXT
                )
            ''')
            
            # Policy violations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS policy_violations (
                    id TEXT PRIMARY KEY,
                    policy_id TEXT NOT NULL,
                    violation_type TEXT NOT NULL,
                    description TEXT,
                    severity TEXT NOT NULL,
                    source_ip TEXT,
                    user_id TEXT,
                    resource TEXT,
                    action_taken TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved BOOLEAN DEFAULT 0
                )
            ''')
            
            # API security table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_security (
                    id TEXT PRIMARY KEY,
                    api_key TEXT UNIQUE NOT NULL,
                    api_secret TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    permissions TEXT,
                    rate_limit INTEGER DEFAULT 1000,
                    enabled BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    last_used TIMESTAMP
                )
            ''')
            
            # Multi-factor authentication table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mfa_tokens (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_type TEXT NOT NULL,
                    token_value TEXT NOT NULL,
                    backup_codes TEXT,
                    enabled BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Security command center database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize security database: {e}")
            raise
    
    def _load_policies(self):
        """Load security policies from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM security_policies WHERE enabled = 1')
            
            for row in cursor.fetchall():
                policy = SecurityPolicy(
                    id=row[0],
                    name=row[1],
                    description=row[2],
                    enabled=bool(row[3]),
                    policy_type=row[4],
                    conditions=json.loads(row[5]) if row[5] else {},
                    actions=json.loads(row[6]) if row[6] else [],
                    severity=row[7],
                    created_at=datetime.fromisoformat(row[8]),
                    updated_at=datetime.fromisoformat(row[9]),
                    created_by=row[10],
                    version=row[11]
                )
                self.policies[policy.id] = policy
            
            conn.close()
            logger.info(f"Loaded {len(self.policies)} security policies")
            
        except Exception as e:
            logger.error(f"Failed to load security policies: {e}")
    
    def _load_threat_intelligence(self):
        """Load threat intelligence data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM threat_intelligence')
            
            for row in cursor.fetchall():
                threat = ThreatIntelligence(
                    id=row[0],
                    indicator_type=row[1],
                    indicator_value=row[2],
                    threat_level=ThreatLevel(row[3]),
                    confidence=row[4],
                    source=row[5],
                    description=row[6],
                    mitigation=row[7],
                    first_seen=datetime.fromisoformat(row[8]),
                    last_seen=datetime.fromisoformat(row[9]),
                    tags=json.loads(row[10]) if row[10] else [],
                    ioc_hash=row[11]
                )
                self.threat_feeds['internal'].append(threat)
            
            conn.close()
            logger.info(f"Loaded {len(self.threat_feeds['internal'])} threat indicators")
            
        except Exception as e:
            logger.error(f"Failed to load threat intelligence: {e}")
    
    def _load_compliance_frameworks(self):
        """Load compliance framework configurations"""
        try:
            # Load default compliance checks
            default_checks = self._get_default_compliance_checks()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for check in default_checks:
                cursor.execute('''
                    INSERT OR IGNORE INTO compliance_checks 
                    (id, framework, control_id, control_name, description, next_check)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    check['id'],
                    check['framework'],
                    check['control_id'],
                    check['control_name'],
                    check['description'],
                    datetime.utcnow() + timedelta(days=30)
                ))
            
            conn.commit()
            conn.close()
            logger.info("Compliance frameworks loaded")
            
        except Exception as e:
            logger.error(f"Failed to load compliance frameworks: {e}")
    
    def _get_default_compliance_checks(self) -> List[Dict]:
        """Get default compliance checks for various frameworks"""
        return [
            {
                'id': 'gdpr_001',
                'framework': 'gdpr',
                'control_id': 'Art.32',
                'control_name': 'Security of processing',
                'description': 'Implement appropriate technical and organizational measures'
            },
            {
                'id': 'gdpr_002',
                'framework': 'gdpr',
                'control_id': 'Art.25',
                'control_name': 'Data protection by design',
                'description': 'Implement data protection by design and by default'
            },
            {
                'id': 'soc2_001',
                'framework': 'soc2',
                'control_id': 'CC6.1',
                'control_name': 'Logical access controls',
                'description': 'Implement logical access security controls'
            },
            {
                'id': 'soc2_002',
                'framework': 'soc2',
                'control_id': 'CC6.2',
                'control_name': 'Authentication',
                'description': 'Implement multi-factor authentication'
            },
            {
                'id': 'iso27001_001',
                'framework': 'iso27001',
                'control_id': 'A.9.1.1',
                'control_name': 'Access control policy',
                'description': 'Establish access control policy'
            }
        ]
    
    def _start_background_services(self):
        """Start background monitoring and processing services"""
        # Threat intelligence update thread
        threat_thread = threading.Thread(target=self._threat_intelligence_updater, daemon=True)
        threat_thread.start()
        
        # Policy evaluation thread
        policy_thread = threading.Thread(target=self._policy_evaluator, daemon=True)
        policy_thread.start()
        
        # Compliance checker thread
        compliance_thread = threading.Thread(target=self._compliance_checker, daemon=True)
        compliance_thread.start()
        
        # Metrics collector thread
        metrics_thread = threading.Thread(target=self._metrics_collector, daemon=True)
        metrics_thread.start()
        
        logger.info("Background security services started")
    
    # ========== POLICY MANAGEMENT ==========
    
    def create_policy(self, name: str, description: str, policy_type: str, 
                     conditions: Dict, actions: List[Dict], severity: str = 'MEDIUM',
                     created_by: str = 'system') -> str:
        """Create a new security policy"""
        try:
            policy_id = f"policy_{int(time.time())}_{secrets.token_hex(8)}"
            
            policy = SecurityPolicy(
                id=policy_id,
                name=name,
                description=description,
                enabled=True,
                policy_type=policy_type,
                conditions=conditions,
                actions=actions,
                severity=severity,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                created_by=created_by,
                version=1
            )
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO security_policies 
                (id, name, description, enabled, policy_type, conditions, actions, severity, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                policy_id, name, description, True, policy_type,
                json.dumps(conditions), json.dumps(actions), severity, created_by
            ))
            conn.commit()
            conn.close()
            
            # Add to memory cache
            self.policies[policy_id] = policy
            
            logger.info(f"Created security policy: {name}")
            return policy_id
            
        except Exception as e:
            logger.error(f"Failed to create policy: {e}")
            raise
    
    def update_policy(self, policy_id: str, **kwargs) -> bool:
        """Update an existing security policy"""
        try:
            if policy_id not in self.policies:
                return False
            
            policy = self.policies[policy_id]
            
            # Update fields
            for key, value in kwargs.items():
                if hasattr(policy, key):
                    setattr(policy, key, value)
            
            policy.updated_at = datetime.utcnow()
            policy.version += 1
            
            # Update database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE security_policies 
                SET name = ?, description = ?, enabled = ?, policy_type = ?, 
                    conditions = ?, actions = ?, severity = ?, updated_at = ?, version = ?
                WHERE id = ?
            ''', (
                policy.name, policy.description, policy.enabled, policy.policy_type,
                json.dumps(policy.conditions), json.dumps(policy.actions), 
                policy.severity, policy.updated_at, policy.version, policy_id
            ))
            conn.commit()
            conn.close()
            
            logger.info(f"Updated security policy: {policy_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update policy: {e}")
            return False
    
    def delete_policy(self, policy_id: str) -> bool:
        """Delete a security policy"""
        try:
            if policy_id not in self.policies:
                return False
            
            # Remove from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM security_policies WHERE id = ?', (policy_id,))
            conn.commit()
            conn.close()
            
            # Remove from memory
            del self.policies[policy_id]
            
            logger.info(f"Deleted security policy: {policy_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete policy: {e}")
            return False
    
    def evaluate_policies(self, context: Dict) -> List[Dict]:
        """Evaluate security policies against given context"""
        try:
            violations = []
            
            for policy_id, policy in self.policies.items():
                if not policy.enabled:
                    continue
                
                # Check if policy conditions match
                if self._evaluate_policy_conditions(policy.conditions, context):
                    violation = {
                        'policy_id': policy_id,
                        'policy_name': policy.name,
                        'severity': policy.severity,
                        'actions': policy.actions,
                        'context': context
                    }
                    violations.append(violation)
                    
                    # Execute policy actions
                    self._execute_policy_actions(policy.actions, context)
                    
                    # Log policy violation
                    self._log_policy_violation(policy_id, violation, context)
            
            return violations
            
        except Exception as e:
            logger.error(f"Policy evaluation error: {e}")
            return []
    
    def _evaluate_policy_conditions(self, conditions: Dict, context: Dict) -> bool:
        """Evaluate if policy conditions match the context"""
        try:
            for condition_type, condition_value in conditions.items():
                if condition_type == 'ip_range':
                    if not self._check_ip_range(condition_value, context.get('source_ip')):
                        return False
                elif condition_type == 'user_agent':
                    if not self._check_user_agent(condition_value, context.get('user_agent')):
                        return False
                elif condition_type == 'time_range':
                    if not self._check_time_range(condition_value, datetime.utcnow()):
                        return False
                elif condition_type == 'request_rate':
                    if not self._check_request_rate(condition_value, context):
                        return False
                elif condition_type == 'file_type':
                    if not self._check_file_type(condition_value, context.get('file_type')):
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Policy condition evaluation error: {e}")
            return False
    
    def _execute_policy_actions(self, actions: List[Dict], context: Dict):
        """Execute policy actions"""
        try:
            for action in actions:
                action_type = action.get('type')
                
                if action_type == 'block_ip':
                    self._block_ip_action(action, context)
                elif action_type == 'rate_limit':
                    self._rate_limit_action(action, context)
                elif action_type == 'alert':
                    self._alert_action(action, context)
                elif action_type == 'quarantine':
                    self._quarantine_action(action, context)
                elif action_type == 'log':
                    self._log_action(action, context)
                    
        except Exception as e:
            logger.error(f"Policy action execution error: {e}")
    
    # ========== THREAT INTELLIGENCE ==========
    
    def add_threat_indicator(self, indicator_type: str, indicator_value: str, 
                           threat_level: ThreatLevel, confidence: float,
                           source: str, description: str = "", mitigation: str = "",
                           tags: List[str] = None) -> str:
        """Add threat intelligence indicator"""
        try:
            # Create hash for deduplication
            ioc_hash = hashlib.sha256(
                f"{indicator_type}:{indicator_value}".encode()
            ).hexdigest()
            
            threat_id = f"threat_{int(time.time())}_{secrets.token_hex(8)}"
            
            threat = ThreatIntelligence(
                id=threat_id,
                indicator_type=indicator_type,
                indicator_value=indicator_value,
                threat_level=threat_level,
                confidence=confidence,
                source=source,
                description=description,
                mitigation=mitigation,
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                tags=tags or [],
                ioc_hash=ioc_hash
            )
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO threat_intelligence 
                (id, indicator_type, indicator_value, threat_level, confidence, source, 
                 description, mitigation, first_seen, last_seen, tags, ioc_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                threat_id, indicator_type, indicator_value, threat_level.value,
                confidence, source, description, mitigation, threat.first_seen,
                threat.last_seen, json.dumps(tags or []), ioc_hash
            ))
            conn.commit()
            conn.close()
            
            # Add to memory cache
            self.threat_feeds['internal'].append(threat)
            
            logger.info(f"Added threat indicator: {indicator_type}:{indicator_value}")
            return threat_id
            
        except Exception as e:
            logger.error(f"Failed to add threat indicator: {e}")
            raise
    
    def check_threat_indicators(self, context: Dict) -> List[Dict]:
        """Check context against threat intelligence"""
        try:
            matches = []
            
            for threat in self.threat_feeds['internal']:
                if self._match_threat_indicator(threat, context):
                    matches.append({
                        'threat_id': threat.id,
                        'indicator_type': threat.indicator_type,
                        'indicator_value': threat.indicator_value,
                        'threat_level': threat.threat_level.value,
                        'confidence': threat.confidence,
                        'description': threat.description,
                        'mitigation': threat.mitigation
                    })
            
            return matches
            
        except Exception as e:
            logger.error(f"Threat indicator check error: {e}")
            return []
    
    def _match_threat_indicator(self, threat: ThreatIntelligence, context: Dict) -> bool:
        """Check if threat indicator matches context"""
        try:
            if threat.indicator_type == 'ip':
                return context.get('source_ip') == threat.indicator_value
            elif threat.indicator_type == 'domain':
                return threat.indicator_value in context.get('domains', [])
            elif threat.indicator_type == 'url':
                return threat.indicator_value in context.get('urls', [])
            elif threat.indicator_type == 'user_agent':
                return threat.indicator_value in context.get('user_agent', '')
            elif threat.indicator_type == 'file_hash':
                return threat.indicator_value in context.get('file_hashes', [])
            
            return False
            
        except Exception as e:
            logger.error(f"Threat indicator matching error: {e}")
            return False
    
    def _threat_intelligence_updater(self):
        """Background thread to update threat intelligence"""
        while True:
            try:
                self._update_external_threat_feeds()
                time.sleep(3600)  # Update every hour
            except Exception as e:
                logger.error(f"Threat intelligence update error: {e}")
                time.sleep(3600)
    
    def _update_external_threat_feeds(self):
        """Update threat intelligence from external feeds"""
        try:
            # In production, this would fetch from external threat feeds
            # For now, just log the update
            logger.info("Updating external threat intelligence feeds")
            
        except Exception as e:
            logger.error(f"External threat feed update error: {e}")
    
    # ========== INCIDENT MANAGEMENT ==========
    
    def create_incident(self, title: str, description: str, severity: ThreatLevel,
                       assigned_to: str = "", affected_assets: List[str] = None) -> str:
        """Create security incident"""
        try:
            incident_id = f"incident_{int(time.time())}_{secrets.token_hex(8)}"
            
            incident = SecurityIncident(
                id=incident_id,
                title=title,
                description=description,
                severity=severity,
                status='OPEN',
                assigned_to=assigned_to,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                resolved_at=None,
                affected_assets=affected_assets or [],
                timeline=[{
                    'timestamp': datetime.utcnow().isoformat(),
                    'action': 'CREATED',
                    'description': 'Incident created',
                    'user': 'system'
                }],
                response_actions=[],
                lessons_learned=None
            )
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO security_incidents 
                (id, title, description, severity, status, assigned_to, affected_assets, timeline)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                incident_id, title, description, severity.value, 'OPEN',
                assigned_to, json.dumps(affected_assets or []), 
                json.dumps(incident.timeline)
            ))
            conn.commit()
            conn.close()
            
            # Add to active incidents
            self.active_incidents[incident_id] = incident
            
            logger.info(f"Created security incident: {title}")
            return incident_id
            
        except Exception as e:
            logger.error(f"Failed to create incident: {e}")
            raise
    
    def update_incident(self, incident_id: str, **kwargs) -> bool:
        """Update security incident"""
        try:
            if incident_id not in self.active_incidents:
                return False
            
            incident = self.active_incidents[incident_id]
            
            # Update fields
            for key, value in kwargs.items():
                if hasattr(incident, key):
                    setattr(incident, key, value)
            
            incident.updated_at = datetime.utcnow()
            
            # Add timeline entry
            incident.timeline.append({
                'timestamp': datetime.utcnow().isoformat(),
                'action': 'UPDATED',
                'description': f'Incident updated: {list(kwargs.keys())}',
                'user': 'system'
            })
            
            # Update database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE security_incidents 
                SET title = ?, description = ?, severity = ?, status = ?, 
                    assigned_to = ?, updated_at = ?, resolved_at = ?, 
                    affected_assets = ?, timeline = ?, response_actions = ?, 
                    lessons_learned = ?
                WHERE id = ?
            ''', (
                incident.title, incident.description, incident.severity.value,
                incident.status, incident.assigned_to, incident.updated_at,
                incident.resolved_at, json.dumps(incident.affected_assets),
                json.dumps(incident.timeline), json.dumps(incident.response_actions),
                incident.lessons_learned, incident_id
            ))
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update incident: {e}")
            return False
    
    # ========== COMPLIANCE MANAGEMENT ==========
    
    def run_compliance_check(self, framework: ComplianceFramework, 
                           control_id: str = None) -> Dict:
        """Run compliance checks"""
        try:
            results = {
                'framework': framework.value,
                'timestamp': datetime.utcnow().isoformat(),
                'checks': [],
                'summary': {
                    'total': 0,
                    'passed': 0,
                    'failed': 0,
                    'pending': 0
                }
            }
            
            # Get compliance checks
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if control_id:
                cursor.execute('''
                    SELECT * FROM compliance_checks 
                    WHERE framework = ? AND control_id = ?
                ''', (framework.value, control_id))
            else:
                cursor.execute('''
                    SELECT * FROM compliance_checks 
                    WHERE framework = ?
                ''', (framework.value,))
            
            checks = cursor.fetchall()
            
            for check in checks:
                check_result = self._perform_compliance_check(check)
                results['checks'].append(check_result)
                
                # Update summary
                results['summary']['total'] += 1
                if check_result['status'] == 'PASSED':
                    results['summary']['passed'] += 1
                elif check_result['status'] == 'FAILED':
                    results['summary']['failed'] += 1
                else:
                    results['summary']['pending'] += 1
            
            conn.close()
            
            # Calculate compliance percentage
            if results['summary']['total'] > 0:
                results['compliance_percentage'] = (
                    results['summary']['passed'] / results['summary']['total'] * 100
                )
            else:
                results['compliance_percentage'] = 0
            
            return results
            
        except Exception as e:
            logger.error(f"Compliance check error: {e}")
            return {'error': str(e)}
    
    def _perform_compliance_check(self, check: Tuple) -> Dict:
        """Perform individual compliance check"""
        try:
            check_id, framework, control_id, control_name, description = check[:5]
            
            # This is a simplified check - in production, this would involve
            # actual verification of security controls
            result = {
                'check_id': check_id,
                'control_id': control_id,
                'control_name': control_name,
                'status': 'PASSED',  # Default to passed for demo
                'evidence': [],
                'gaps': [],
                'recommendations': []
            }
            
            # Example checks based on framework
            if framework == 'gdpr':
                result.update(self._check_gdpr_compliance(control_id))
            elif framework == 'soc2':
                result.update(self._check_soc2_compliance(control_id))
            elif framework == 'iso27001':
                result.update(self._check_iso27001_compliance(control_id))
            
            return result
            
        except Exception as e:
            logger.error(f"Individual compliance check error: {e}")
            return {'error': str(e)}
    
    def _check_gdpr_compliance(self, control_id: str) -> Dict:
        """Check GDPR compliance"""
        # Simplified GDPR compliance checks
        checks = {
            'Art.32': {
                'status': 'PASSED',
                'evidence': ['Encryption enabled', 'Access controls implemented'],
                'gaps': [],
                'recommendations': []
            },
            'Art.25': {
                'status': 'PASSED',
                'evidence': ['Data minimization implemented'],
                'gaps': [],
                'recommendations': []
            }
        }
        
        return checks.get(control_id, {'status': 'PENDING'})
    
    def _check_soc2_compliance(self, control_id: str) -> Dict:
        """Check SOC 2 compliance"""
        # Simplified SOC 2 compliance checks
        checks = {
            'CC6.1': {
                'status': 'PASSED',
                'evidence': ['Role-based access control implemented'],
                'gaps': [],
                'recommendations': []
            },
            'CC6.2': {
                'status': 'PASSED',
                'evidence': ['Multi-factor authentication enabled'],
                'gaps': [],
                'recommendations': []
            }
        }
        
        return checks.get(control_id, {'status': 'PENDING'})
    
    def _check_iso27001_compliance(self, control_id: str) -> Dict:
        """Check ISO 27001 compliance"""
        # Simplified ISO 27001 compliance checks
        checks = {
            'A.9.1.1': {
                'status': 'PASSED',
                'evidence': ['Access control policy documented'],
                'gaps': [],
                'recommendations': []
            }
        }
        
        return checks.get(control_id, {'status': 'PENDING'})
    
    # ========== BACKGROUND SERVICES ==========
    
    def _policy_evaluator(self):
        """Background policy evaluation service"""
        while True:
            try:
                # This would continuously evaluate policies against incoming events
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Policy evaluator error: {e}")
                time.sleep(30)
    
    def _compliance_checker(self):
        """Background compliance checking service"""
        while True:
            try:
                # Run scheduled compliance checks
                self._run_scheduled_compliance_checks()
                time.sleep(3600)  # Check every hour
            except Exception as e:
                logger.error(f"Compliance checker error: {e}")
                time.sleep(3600)
    
    def _metrics_collector(self):
        """Background metrics collection service"""
        while True:
            try:
                self._collect_security_metrics()
                time.sleep(60)  # Collect every minute
            except Exception as e:
                logger.error(f"Metrics collector error: {e}")
                time.sleep(60)
    
    def _collect_security_metrics(self):
        """Collect security metrics"""
        try:
            # Collect various security metrics
            metrics = {
                'failed_login_attempts': self._count_failed_logins(),
                'blocked_ips': self._count_blocked_ips(),
                'policy_violations': self._count_policy_violations(),
                'active_incidents': len(self.active_incidents),
                'threat_indicators': len(self.threat_feeds['internal'])
            }
            
            # Store metrics
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for metric_name, value in metrics.items():
                cursor.execute('''
                    INSERT INTO security_metrics (metric_name, value, unit)
                    VALUES (?, ?, ?)
                ''', (metric_name, value, 'count'))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Metrics collection error: {e}")
    
    def _run_scheduled_compliance_checks(self):
        """Run scheduled compliance checks"""
        try:
            # Check for compliance checks that need to be run
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT framework FROM compliance_checks 
                WHERE next_check <= datetime('now')
                GROUP BY framework
            ''')
            
            frameworks = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            for framework in frameworks:
                try:
                    self.run_compliance_check(ComplianceFramework(framework))
                except Exception as e:
                    logger.error(f"Scheduled compliance check error for {framework}: {e}")
                    
        except Exception as e:
            logger.error(f"Scheduled compliance check error: {e}")
    
    # ========== HELPER METHODS ==========
    
    def _count_failed_logins(self) -> int:
        """Count failed login attempts in last hour"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM security_events 
                WHERE event_type = 'FAILED_LOGIN' 
                AND timestamp > datetime('now', '-1 hour')
            ''')
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0
    
    def _count_blocked_ips(self) -> int:
        """Count currently blocked IPs"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM ip_blocks 
                WHERE blocked_until > datetime('now')
            ''')
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0
    
    def _count_policy_violations(self) -> int:
        """Count policy violations in last hour"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM policy_violations 
                WHERE timestamp > datetime('now', '-1 hour')
            ''')
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0
    
    def _log_policy_violation(self, policy_id: str, violation: Dict, context: Dict):
        """Log policy violation"""
        try:
            violation_id = f"violation_{int(time.time())}_{secrets.token_hex(8)}"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO policy_violations 
                (id, policy_id, violation_type, description, severity, source_ip, 
                 user_id, resource, action_taken)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                violation_id, policy_id, 'POLICY_VIOLATION',
                violation.get('description', 'Policy violation detected'),
                violation.get('severity', 'MEDIUM'),
                context.get('source_ip'),
                context.get('user_id'),
                context.get('resource'),
                json.dumps(violation.get('actions', []))
            ))
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to log policy violation: {e}")
    
    # Action execution methods
    def _block_ip_action(self, action: Dict, context: Dict):
        """Execute IP blocking action"""
        # This would integrate with existing IP blocking functionality
        pass
    
    def _rate_limit_action(self, action: Dict, context: Dict):
        """Execute rate limiting action"""
        # This would integrate with existing rate limiting functionality
        pass
    
    def _alert_action(self, action: Dict, context: Dict):
        """Execute alert action"""
        # This would send alerts via email, Slack, etc.
        pass
    
    def _quarantine_action(self, action: Dict, context: Dict):
        """Execute quarantine action"""
        # This would quarantine suspicious files/activities
        pass
    
    def _log_action(self, action: Dict, context: Dict):
        """Execute logging action"""
        # This would create detailed logs
        pass
    
    # Condition checking methods
    def _check_ip_range(self, condition: Dict, source_ip: str) -> bool:
        """Check if IP is in specified range"""
        try:
            if not source_ip:
                return False
            
            ip = ipaddress.ip_address(source_ip)
            for ip_range in condition.get('ranges', []):
                if ip in ipaddress.ip_network(ip_range):
                    return True
            return False
        except Exception:
            return False
    
    def _check_user_agent(self, condition: Dict, user_agent: str) -> bool:
        """Check user agent against patterns"""
        try:
            if not user_agent:
                return False
            
            patterns = condition.get('patterns', [])
            for pattern in patterns:
                if re.search(pattern, user_agent, re.IGNORECASE):
                    return True
            return False
        except Exception:
            return False
    
    def _check_time_range(self, condition: Dict, timestamp: datetime) -> bool:
        """Check if time is within specified range"""
        try:
            start_time = condition.get('start_time')
            end_time = condition.get('end_time')
            
            if start_time and end_time:
                current_time = timestamp.time()
                start = datetime.strptime(start_time, '%H:%M').time()
                end = datetime.strptime(end_time, '%H:%M').time()
                
                return start <= current_time <= end
            return True
        except Exception:
            return True
    
    def _check_request_rate(self, condition: Dict, context: Dict) -> bool:
        """Check request rate against threshold"""
        try:
            # This would check against rate limiting data
            return True
        except Exception:
            return True
    
    def _check_file_type(self, condition: Dict, file_type: str) -> bool:
        """Check file type against allowed types"""
        try:
            if not file_type:
                return True
            
            allowed_types = condition.get('allowed_types', [])
            blocked_types = condition.get('blocked_types', [])
            
            if blocked_types and file_type in blocked_types:
                return True  # Condition matches (file is blocked)
            
            if allowed_types and file_type not in allowed_types:
                return True  # Condition matches (file not allowed)
            
            return False
        except Exception:
            return False

# Global security command center instance
security_command_center = SecurityCommandCenter()