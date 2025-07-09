#!/usr/bin/env python3
"""
Threat Intelligence & Response System for VectorCraft Security Command Center
Advanced threat detection, intelligence gathering, and automated response capabilities
"""

import os
import json
import logging
import hashlib
import secrets
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import threading
from collections import defaultdict, deque
import ipaddress
import re
from urllib.parse import urlparse
import dns.resolver
import socket
import geoip2.database
import geoip2.errors

logger = logging.getLogger(__name__)

class ThreatType(Enum):
    MALWARE = "malware"
    PHISHING = "phishing"
    BOTNET = "botnet"
    RANSOMWARE = "ransomware"
    APT = "apt"
    SPAM = "spam"
    SUSPICIOUS = "suspicious"
    FRAUD = "fraud"

class IndicatorType(Enum):
    IP = "ip"
    DOMAIN = "domain"
    URL = "url"
    FILE_HASH = "file_hash"
    EMAIL = "email"
    USER_AGENT = "user_agent"
    CERTIFICATE = "certificate"
    REGISTRY_KEY = "registry_key"

class ResponseAction(Enum):
    BLOCK = "block"
    MONITOR = "monitor"
    ALERT = "alert"
    ISOLATE = "isolate"
    INVESTIGATE = "investigate"
    NOTIFY = "notify"

class ThreatLevel(Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ThreatIndicator:
    """Comprehensive threat indicator"""
    id: str
    indicator_type: IndicatorType
    indicator_value: str
    threat_type: ThreatType
    threat_level: ThreatLevel
    confidence: float
    source: str
    first_seen: datetime
    last_seen: datetime
    times_seen: int
    description: str
    context: Dict[str, Any]
    tags: List[str]
    related_indicators: List[str]
    false_positive: bool
    whitelist: bool
    expiration: Optional[datetime]

@dataclass
class ThreatResponse:
    """Threat response action"""
    id: str
    threat_id: str
    action: ResponseAction
    description: str
    automated: bool
    executed_at: datetime
    executed_by: str
    success: bool
    result: Dict[str, Any]
    rollback_info: Optional[Dict[str, Any]]

@dataclass
class ThreatInvestigation:
    """Threat investigation record"""
    id: str
    threat_id: str
    investigator: str
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime
    findings: List[Dict[str, Any]]
    artifacts: List[str]
    timeline: List[Dict[str, Any]]
    verdict: Optional[str]
    recommendations: List[str]

@dataclass
class ThreatCampaign:
    """Threat campaign tracking"""
    id: str
    name: str
    threat_type: ThreatType
    first_seen: datetime
    last_seen: datetime
    indicators: List[str]
    techniques: List[str]
    targets: List[str]
    attribution: Optional[str]
    description: str
    active: bool

class ThreatIntelligenceEngine:
    """Advanced Threat Intelligence Engine"""
    
    def __init__(self, db_path: str = 'vectorcraft.db'):
        self.db_path = db_path
        self.indicators = {}
        self.campaigns = {}
        self.investigations = {}
        self.responses = {}
        
        # Threat intelligence feeds
        self.ti_feeds = {
            'internal': [],
            'commercial': [],
            'open_source': [],
            'government': []
        }
        
        # Response playbooks
        self.playbooks = {}
        
        # Threat hunting rules
        self.hunting_rules = []
        
        # Geolocation database
        self.geo_db = None
        self._init_geo_database()
        
        # Initialize database
        self._init_database()
        
        # Load configurations
        self._load_threat_indicators()
        self._load_response_playbooks()
        self._load_hunting_rules()
        
        # Start background services
        self._start_background_services()
        
        logger.info("Threat Intelligence Engine initialized")
    
    def _init_geo_database(self):
        """Initialize GeoIP database"""
        try:
            geo_db_path = 'GeoLite2-City.mmdb'
            if os.path.exists(geo_db_path):
                self.geo_db = geoip2.database.Reader(geo_db_path)
                logger.info("GeoIP database loaded")
            else:
                logger.warning("GeoIP database not found - geographic analysis disabled")
        except Exception as e:
            logger.error(f"Failed to initialize GeoIP database: {e}")
    
    def _init_database(self):
        """Initialize threat intelligence database tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Threat indicators table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS threat_indicators_v2 (
                    id TEXT PRIMARY KEY,
                    indicator_type TEXT NOT NULL,
                    indicator_value TEXT NOT NULL,
                    threat_type TEXT NOT NULL,
                    threat_level TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    source TEXT NOT NULL,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    times_seen INTEGER DEFAULT 1,
                    description TEXT,
                    context TEXT,
                    tags TEXT,
                    related_indicators TEXT,
                    false_positive BOOLEAN DEFAULT 0,
                    whitelist BOOLEAN DEFAULT 0,
                    expiration TIMESTAMP,
                    UNIQUE(indicator_type, indicator_value, source)
                )
            ''')
            
            # Threat responses table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS threat_responses (
                    id TEXT PRIMARY KEY,
                    threat_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    description TEXT,
                    automated BOOLEAN DEFAULT 0,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    executed_by TEXT,
                    success BOOLEAN DEFAULT 0,
                    result TEXT,
                    rollback_info TEXT
                )
            ''')
            
            # Threat investigations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS threat_investigations (
                    id TEXT PRIMARY KEY,
                    threat_id TEXT NOT NULL,
                    investigator TEXT NOT NULL,
                    status TEXT DEFAULT 'OPEN',
                    priority TEXT DEFAULT 'MEDIUM',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    findings TEXT,
                    artifacts TEXT,
                    timeline TEXT,
                    verdict TEXT,
                    recommendations TEXT
                )
            ''')
            
            # Threat campaigns table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS threat_campaigns (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    threat_type TEXT NOT NULL,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    indicators TEXT,
                    techniques TEXT,
                    targets TEXT,
                    attribution TEXT,
                    description TEXT,
                    active BOOLEAN DEFAULT 1
                )
            ''')
            
            # Threat hunting queries table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS threat_hunting_queries (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    query TEXT NOT NULL,
                    threat_type TEXT,
                    severity TEXT DEFAULT 'MEDIUM',
                    enabled BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_executed TIMESTAMP,
                    execution_count INTEGER DEFAULT 0,
                    matches_found INTEGER DEFAULT 0
                )
            ''')
            
            # Threat intelligence feeds table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS threat_feeds (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    url TEXT,
                    feed_type TEXT NOT NULL,
                    format TEXT NOT NULL,
                    update_interval INTEGER DEFAULT 3600,
                    last_updated TIMESTAMP,
                    enabled BOOLEAN DEFAULT 1,
                    credentials TEXT,
                    indicators_added INTEGER DEFAULT 0,
                    errors TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Threat intelligence database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize threat intelligence database: {e}")
            raise
    
    def _load_threat_indicators(self):
        """Load threat indicators from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM threat_indicators_v2 
                WHERE (expiration IS NULL OR expiration > datetime('now'))
                AND whitelist = 0
            ''')
            
            for row in cursor.fetchall():
                indicator = ThreatIndicator(
                    id=row[0],
                    indicator_type=IndicatorType(row[1]),
                    indicator_value=row[2],
                    threat_type=ThreatType(row[3]),
                    threat_level=ThreatLevel(row[4]),
                    confidence=row[5],
                    source=row[6],
                    first_seen=datetime.fromisoformat(row[7]),
                    last_seen=datetime.fromisoformat(row[8]),
                    times_seen=row[9],
                    description=row[10] or "",
                    context=json.loads(row[11]) if row[11] else {},
                    tags=json.loads(row[12]) if row[12] else [],
                    related_indicators=json.loads(row[13]) if row[13] else [],
                    false_positive=bool(row[14]),
                    whitelist=bool(row[15]),
                    expiration=datetime.fromisoformat(row[16]) if row[16] else None
                )
                self.indicators[indicator.id] = indicator
            
            conn.close()
            logger.info(f"Loaded {len(self.indicators)} threat indicators")
            
        except Exception as e:
            logger.error(f"Failed to load threat indicators: {e}")
    
    def _load_response_playbooks(self):
        """Load response playbooks"""
        try:
            # Default playbooks
            self.playbooks = {
                'malware_detection': {
                    'name': 'Malware Detection Response',
                    'triggers': ['malware', 'suspicious_file'],
                    'actions': [
                        {'action': 'isolate', 'priority': 1},
                        {'action': 'alert', 'priority': 2},
                        {'action': 'investigate', 'priority': 3}
                    ]
                },
                'phishing_detection': {
                    'name': 'Phishing Detection Response',
                    'triggers': ['phishing', 'suspicious_url'],
                    'actions': [
                        {'action': 'block', 'priority': 1},
                        {'action': 'alert', 'priority': 2},
                        {'action': 'notify', 'priority': 3}
                    ]
                },
                'botnet_detection': {
                    'name': 'Botnet Detection Response',
                    'triggers': ['botnet', 'c2_communication'],
                    'actions': [
                        {'action': 'block', 'priority': 1},
                        {'action': 'monitor', 'priority': 2},
                        {'action': 'investigate', 'priority': 3}
                    ]
                }
            }
            
            logger.info(f"Loaded {len(self.playbooks)} response playbooks")
            
        except Exception as e:
            logger.error(f"Failed to load response playbooks: {e}")
    
    def _load_hunting_rules(self):
        """Load threat hunting rules"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM threat_hunting_queries WHERE enabled = 1')
            
            for row in cursor.fetchall():
                rule = {
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'query': row[3],
                    'threat_type': row[4],
                    'severity': row[5],
                    'enabled': bool(row[6])
                }
                self.hunting_rules.append(rule)
            
            conn.close()
            logger.info(f"Loaded {len(self.hunting_rules)} threat hunting rules")
            
        except Exception as e:
            logger.error(f"Failed to load hunting rules: {e}")
    
    def _start_background_services(self):
        """Start background threat intelligence services"""
        # Feed updater thread
        feed_thread = threading.Thread(target=self._feed_updater, daemon=True)
        feed_thread.start()
        
        # Threat hunting thread
        hunting_thread = threading.Thread(target=self._threat_hunter, daemon=True)
        hunting_thread.start()
        
        # Indicator enrichment thread
        enrichment_thread = threading.Thread(target=self._indicator_enricher, daemon=True)
        enrichment_thread.start()
        
        # Campaign detection thread
        campaign_thread = threading.Thread(target=self._campaign_detector, daemon=True)
        campaign_thread.start()
        
        logger.info("Threat intelligence background services started")
    
    # ========== THREAT INDICATOR MANAGEMENT ==========
    
    def add_indicator(self, indicator_type: IndicatorType, indicator_value: str,
                     threat_type: ThreatType, threat_level: ThreatLevel,
                     confidence: float, source: str, description: str = "",
                     context: Dict = None, tags: List[str] = None,
                     expiration: Optional[datetime] = None) -> str:
        """Add new threat indicator"""
        try:
            indicator_id = f"ti_{int(time.time())}_{secrets.token_hex(8)}"
            
            # Validate and enrich indicator
            validated_value = self._validate_indicator(indicator_type, indicator_value)
            if not validated_value:
                raise ValueError(f"Invalid indicator value: {indicator_value}")
            
            # Create indicator
            indicator = ThreatIndicator(
                id=indicator_id,
                indicator_type=indicator_type,
                indicator_value=validated_value,
                threat_type=threat_type,
                threat_level=threat_level,
                confidence=confidence,
                source=source,
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                times_seen=1,
                description=description,
                context=context or {},
                tags=tags or [],
                related_indicators=[],
                false_positive=False,
                whitelist=False,
                expiration=expiration
            )
            
            # Enrich with additional context
            self._enrich_indicator(indicator)
            
            # Store in database
            self._store_indicator(indicator)
            
            # Add to memory cache
            self.indicators[indicator_id] = indicator
            
            logger.info(f"Added threat indicator: {indicator_type.value}:{indicator_value}")
            return indicator_id
            
        except Exception as e:
            logger.error(f"Failed to add indicator: {e}")
            raise
    
    def update_indicator(self, indicator_id: str, **kwargs) -> bool:
        """Update existing threat indicator"""
        try:
            if indicator_id not in self.indicators:
                return False
            
            indicator = self.indicators[indicator_id]
            
            # Update fields
            for key, value in kwargs.items():
                if hasattr(indicator, key):
                    setattr(indicator, key, value)
            
            indicator.last_seen = datetime.utcnow()
            
            # Update database
            self._store_indicator(indicator)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update indicator: {e}")
            return False
    
    def check_indicators(self, context: Dict) -> List[Dict]:
        """Check context against threat indicators"""
        try:
            matches = []
            
            for indicator in self.indicators.values():
                if indicator.false_positive or indicator.whitelist:
                    continue
                
                if indicator.expiration and indicator.expiration < datetime.utcnow():
                    continue
                
                if self._match_indicator(indicator, context):
                    match = {
                        'indicator_id': indicator.id,
                        'indicator_type': indicator.indicator_type.value,
                        'indicator_value': indicator.indicator_value,
                        'threat_type': indicator.threat_type.value,
                        'threat_level': indicator.threat_level.value,
                        'confidence': indicator.confidence,
                        'source': indicator.source,
                        'description': indicator.description,
                        'context': indicator.context,
                        'tags': indicator.tags
                    }
                    matches.append(match)
                    
                    # Update last seen
                    indicator.last_seen = datetime.utcnow()
                    indicator.times_seen += 1
                    self._store_indicator(indicator)
            
            return matches
            
        except Exception as e:
            logger.error(f"Indicator check error: {e}")
            return []
    
    def _validate_indicator(self, indicator_type: IndicatorType, value: str) -> Optional[str]:
        """Validate and normalize indicator value"""
        try:
            if indicator_type == IndicatorType.IP:
                # Validate IP address
                ipaddress.ip_address(value)
                return value
            elif indicator_type == IndicatorType.DOMAIN:
                # Validate domain
                if re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
                    return value.lower()
            elif indicator_type == IndicatorType.URL:
                # Validate URL
                parsed = urlparse(value)
                if parsed.scheme and parsed.netloc:
                    return value.lower()
            elif indicator_type == IndicatorType.FILE_HASH:
                # Validate hash (MD5, SHA1, SHA256)
                if re.match(r'^[a-fA-F0-9]{32}$', value):  # MD5
                    return value.lower()
                elif re.match(r'^[a-fA-F0-9]{40}$', value):  # SHA1
                    return value.lower()
                elif re.match(r'^[a-fA-F0-9]{64}$', value):  # SHA256
                    return value.lower()
            elif indicator_type == IndicatorType.EMAIL:
                # Validate email
                if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
                    return value.lower()
            else:
                return value
            
            return None
            
        except Exception as e:
            logger.error(f"Indicator validation error: {e}")
            return None
    
    def _enrich_indicator(self, indicator: ThreatIndicator):
        """Enrich indicator with additional context"""
        try:
            if indicator.indicator_type == IndicatorType.IP:
                self._enrich_ip_indicator(indicator)
            elif indicator.indicator_type == IndicatorType.DOMAIN:
                self._enrich_domain_indicator(indicator)
            elif indicator.indicator_type == IndicatorType.URL:
                self._enrich_url_indicator(indicator)
                
        except Exception as e:
            logger.error(f"Indicator enrichment error: {e}")
    
    def _enrich_ip_indicator(self, indicator: ThreatIndicator):
        """Enrich IP indicator with geolocation and network info"""
        try:
            ip = indicator.indicator_value
            
            # Geolocation
            if self.geo_db:
                try:
                    response = self.geo_db.city(ip)
                    indicator.context.update({
                        'country': response.country.name,
                        'city': response.city.name,
                        'latitude': float(response.location.latitude) if response.location.latitude else None,
                        'longitude': float(response.location.longitude) if response.location.longitude else None,
                        'isp': response.traits.isp if hasattr(response.traits, 'isp') else None
                    })
                except geoip2.errors.AddressNotFoundError:
                    pass
            
            # Network information
            try:
                hostname = socket.gethostbyaddr(ip)[0]
                indicator.context['hostname'] = hostname
            except socket.herror:
                pass
            
            # Check if IP is in private ranges
            ip_obj = ipaddress.ip_address(ip)
            indicator.context['private'] = ip_obj.is_private
            
        except Exception as e:
            logger.error(f"IP enrichment error: {e}")
    
    def _enrich_domain_indicator(self, indicator: ThreatIndicator):
        """Enrich domain indicator with DNS and reputation info"""
        try:
            domain = indicator.indicator_value
            
            # DNS resolution
            try:
                answers = dns.resolver.resolve(domain, 'A')
                ips = [str(rdata) for rdata in answers]
                indicator.context['resolved_ips'] = ips
            except dns.resolver.NXDOMAIN:
                indicator.context['dns_status'] = 'NXDOMAIN'
            except Exception:
                pass
            
            # Check for suspicious TLD
            suspicious_tlds = ['.tk', '.ml', '.ga', '.cf', '.top', '.work', '.click']
            if any(domain.endswith(tld) for tld in suspicious_tlds):
                indicator.context['suspicious_tld'] = True
            
            # Domain age (simplified - would need WHOIS lookup)
            indicator.context['domain_age'] = 'unknown'
            
        except Exception as e:
            logger.error(f"Domain enrichment error: {e}")
    
    def _enrich_url_indicator(self, indicator: ThreatIndicator):
        """Enrich URL indicator with content analysis"""
        try:
            url = indicator.indicator_value
            parsed = urlparse(url)
            
            indicator.context.update({
                'scheme': parsed.scheme,
                'domain': parsed.netloc,
                'path': parsed.path,
                'query': parsed.query
            })
            
            # Check for suspicious patterns
            suspicious_patterns = [
                r'bit\.ly', r'tinyurl\.com', r'goo\.gl',  # URL shorteners
                r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}',  # IP addresses
                r'[a-zA-Z0-9]{20,}',  # Long random strings
            ]
            
            for pattern in suspicious_patterns:
                if re.search(pattern, url):
                    indicator.context['suspicious_pattern'] = pattern
                    break
            
        except Exception as e:
            logger.error(f"URL enrichment error: {e}")
    
    def _match_indicator(self, indicator: ThreatIndicator, context: Dict) -> bool:
        """Check if indicator matches context"""
        try:
            if indicator.indicator_type == IndicatorType.IP:
                return context.get('source_ip') == indicator.indicator_value
            elif indicator.indicator_type == IndicatorType.DOMAIN:
                domains = context.get('domains', [])
                return indicator.indicator_value in domains
            elif indicator.indicator_type == IndicatorType.URL:
                urls = context.get('urls', [])
                return any(indicator.indicator_value in url for url in urls)
            elif indicator.indicator_type == IndicatorType.FILE_HASH:
                hashes = context.get('file_hashes', [])
                return indicator.indicator_value in hashes
            elif indicator.indicator_type == IndicatorType.EMAIL:
                emails = context.get('emails', [])
                return indicator.indicator_value in emails
            elif indicator.indicator_type == IndicatorType.USER_AGENT:
                user_agent = context.get('user_agent', '')
                return indicator.indicator_value in user_agent
            
            return False
            
        except Exception as e:
            logger.error(f"Indicator matching error: {e}")
            return False
    
    def _store_indicator(self, indicator: ThreatIndicator):
        """Store indicator in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO threat_indicators_v2 
                (id, indicator_type, indicator_value, threat_type, threat_level, confidence, 
                 source, first_seen, last_seen, times_seen, description, context, tags, 
                 related_indicators, false_positive, whitelist, expiration)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                indicator.id, indicator.indicator_type.value, indicator.indicator_value,
                indicator.threat_type.value, indicator.threat_level.value, indicator.confidence,
                indicator.source, indicator.first_seen, indicator.last_seen, indicator.times_seen,
                indicator.description, json.dumps(indicator.context), json.dumps(indicator.tags),
                json.dumps(indicator.related_indicators), indicator.false_positive,
                indicator.whitelist, indicator.expiration
            ))
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store indicator: {e}")
    
    # ========== THREAT RESPONSE ==========
    
    def execute_response(self, threat_id: str, action: ResponseAction, 
                        context: Dict = None, automated: bool = True) -> str:
        """Execute threat response action"""
        try:
            response_id = f"response_{int(time.time())}_{secrets.token_hex(8)}"
            
            # Get threat details
            threat = self.indicators.get(threat_id)
            if not threat:
                raise ValueError(f"Threat not found: {threat_id}")
            
            # Execute action
            result = self._execute_action(action, threat, context or {})
            
            # Create response record
            response = ThreatResponse(
                id=response_id,
                threat_id=threat_id,
                action=action,
                description=f"Executed {action.value} for {threat.threat_type.value}",
                automated=automated,
                executed_at=datetime.utcnow(),
                executed_by='system' if automated else 'admin',
                success=result.get('success', False),
                result=result,
                rollback_info=result.get('rollback_info')
            )
            
            # Store response
            self._store_response(response)
            self.responses[response_id] = response
            
            logger.info(f"Executed response {action.value} for threat {threat_id}")
            return response_id
            
        except Exception as e:
            logger.error(f"Failed to execute response: {e}")
            raise
    
    def _execute_action(self, action: ResponseAction, threat: ThreatIndicator, 
                       context: Dict) -> Dict:
        """Execute specific response action"""
        try:
            if action == ResponseAction.BLOCK:
                return self._block_action(threat, context)
            elif action == ResponseAction.MONITOR:
                return self._monitor_action(threat, context)
            elif action == ResponseAction.ALERT:
                return self._alert_action(threat, context)
            elif action == ResponseAction.ISOLATE:
                return self._isolate_action(threat, context)
            elif action == ResponseAction.INVESTIGATE:
                return self._investigate_action(threat, context)
            elif action == ResponseAction.NOTIFY:
                return self._notify_action(threat, context)
            else:
                return {'success': False, 'error': 'Unknown action'}
                
        except Exception as e:
            logger.error(f"Action execution error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _block_action(self, threat: ThreatIndicator, context: Dict) -> Dict:
        """Execute block action"""
        try:
            # This would integrate with firewall/blocking systems
            if threat.indicator_type == IndicatorType.IP:
                # Block IP address
                pass
            elif threat.indicator_type == IndicatorType.DOMAIN:
                # Block domain
                pass
            elif threat.indicator_type == IndicatorType.URL:
                # Block URL
                pass
            
            return {
                'success': True,
                'action': 'blocked',
                'target': threat.indicator_value,
                'rollback_info': {
                    'action': 'unblock',
                    'target': threat.indicator_value
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _monitor_action(self, threat: ThreatIndicator, context: Dict) -> Dict:
        """Execute monitor action"""
        try:
            # Add to monitoring list
            return {
                'success': True,
                'action': 'monitoring',
                'target': threat.indicator_value
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _alert_action(self, threat: ThreatIndicator, context: Dict) -> Dict:
        """Execute alert action"""
        try:
            # Send alert (email, Slack, etc.)
            return {
                'success': True,
                'action': 'alert_sent',
                'target': threat.indicator_value
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _isolate_action(self, threat: ThreatIndicator, context: Dict) -> Dict:
        """Execute isolate action"""
        try:
            # Isolate affected system
            return {
                'success': True,
                'action': 'isolated',
                'target': threat.indicator_value
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _investigate_action(self, threat: ThreatIndicator, context: Dict) -> Dict:
        """Execute investigate action"""
        try:
            # Create investigation
            investigation_id = self.create_investigation(threat.id, 'system', 'HIGH')
            
            return {
                'success': True,
                'action': 'investigation_created',
                'investigation_id': investigation_id
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _notify_action(self, threat: ThreatIndicator, context: Dict) -> Dict:
        """Execute notify action"""
        try:
            # Send notification
            return {
                'success': True,
                'action': 'notification_sent',
                'target': threat.indicator_value
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _store_response(self, response: ThreatResponse):
        """Store response in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO threat_responses 
                (id, threat_id, action, description, automated, executed_at, 
                 executed_by, success, result, rollback_info)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                response.id, response.threat_id, response.action.value, response.description,
                response.automated, response.executed_at, response.executed_by,
                response.success, json.dumps(response.result), 
                json.dumps(response.rollback_info) if response.rollback_info else None
            ))
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store response: {e}")
    
    # ========== THREAT INVESTIGATION ==========
    
    def create_investigation(self, threat_id: str, investigator: str, 
                           priority: str = 'MEDIUM') -> str:
        """Create threat investigation"""
        try:
            investigation_id = f"inv_{int(time.time())}_{secrets.token_hex(8)}"
            
            investigation = ThreatInvestigation(
                id=investigation_id,
                threat_id=threat_id,
                investigator=investigator,
                status='OPEN',
                priority=priority,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                findings=[],
                artifacts=[],
                timeline=[{
                    'timestamp': datetime.utcnow().isoformat(),
                    'action': 'CREATED',
                    'description': 'Investigation created',
                    'investigator': investigator
                }],
                verdict=None,
                recommendations=[]
            )
            
            # Store investigation
            self._store_investigation(investigation)
            self.investigations[investigation_id] = investigation
            
            logger.info(f"Created investigation {investigation_id} for threat {threat_id}")
            return investigation_id
            
        except Exception as e:
            logger.error(f"Failed to create investigation: {e}")
            raise
    
    def _store_investigation(self, investigation: ThreatInvestigation):
        """Store investigation in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO threat_investigations 
                (id, threat_id, investigator, status, priority, created_at, updated_at,
                 findings, artifacts, timeline, verdict, recommendations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                investigation.id, investigation.threat_id, investigation.investigator,
                investigation.status, investigation.priority, investigation.created_at,
                investigation.updated_at, json.dumps(investigation.findings),
                json.dumps(investigation.artifacts), json.dumps(investigation.timeline),
                investigation.verdict, json.dumps(investigation.recommendations)
            ))
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store investigation: {e}")
    
    # ========== BACKGROUND SERVICES ==========
    
    def _feed_updater(self):
        """Background feed updater"""
        while True:
            try:
                self._update_threat_feeds()
                time.sleep(3600)  # Update every hour
            except Exception as e:
                logger.error(f"Feed updater error: {e}")
                time.sleep(3600)
    
    def _threat_hunter(self):
        """Background threat hunter"""
        while True:
            try:
                self._run_hunting_queries()
                time.sleep(1800)  # Run every 30 minutes
            except Exception as e:
                logger.error(f"Threat hunter error: {e}")
                time.sleep(1800)
    
    def _indicator_enricher(self):
        """Background indicator enricher"""
        while True:
            try:
                self._enrich_indicators()
                time.sleep(3600)  # Enrich every hour
            except Exception as e:
                logger.error(f"Indicator enricher error: {e}")
                time.sleep(3600)
    
    def _campaign_detector(self):
        """Background campaign detector"""
        while True:
            try:
                self._detect_campaigns()
                time.sleep(7200)  # Detect every 2 hours
            except Exception as e:
                logger.error(f"Campaign detector error: {e}")
                time.sleep(7200)
    
    def _update_threat_feeds(self):
        """Update threat intelligence feeds"""
        try:
            # This would update from external feeds
            logger.info("Updating threat intelligence feeds")
            
        except Exception as e:
            logger.error(f"Feed update error: {e}")
    
    def _run_hunting_queries(self):
        """Run threat hunting queries"""
        try:
            logger.info("Running threat hunting queries")
            
        except Exception as e:
            logger.error(f"Hunting query error: {e}")
    
    def _enrich_indicators(self):
        """Enrich existing indicators with new data"""
        try:
            logger.info("Enriching threat indicators")
            
        except Exception as e:
            logger.error(f"Indicator enrichment error: {e}")
    
    def _detect_campaigns(self):
        """Detect threat campaigns"""
        try:
            logger.info("Detecting threat campaigns")
            
        except Exception as e:
            logger.error(f"Campaign detection error: {e}")
    
    # ========== PUBLIC API ==========
    
    def get_threat_statistics(self) -> Dict:
        """Get threat intelligence statistics"""
        try:
            stats = {
                'total_indicators': len(self.indicators),
                'active_investigations': len([i for i in self.investigations.values() if i.status == 'OPEN']),
                'responses_executed': len(self.responses),
                'campaigns_detected': len(self.campaigns),
                'by_threat_type': defaultdict(int),
                'by_threat_level': defaultdict(int),
                'by_source': defaultdict(int)
            }
            
            for indicator in self.indicators.values():
                stats['by_threat_type'][indicator.threat_type.value] += 1
                stats['by_threat_level'][indicator.threat_level.value] += 1
                stats['by_source'][indicator.source] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get threat statistics: {e}")
            return {}
    
    def get_recent_threats(self, limit: int = 20) -> List[Dict]:
        """Get recent threat indicators"""
        try:
            indicators = sorted(
                self.indicators.values(),
                key=lambda x: x.last_seen,
                reverse=True
            )[:limit]
            
            return [asdict(indicator) for indicator in indicators]
            
        except Exception as e:
            logger.error(f"Failed to get recent threats: {e}")
            return []

# Global threat intelligence engine instance
threat_intelligence = ThreatIntelligenceEngine()