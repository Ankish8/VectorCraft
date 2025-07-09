#!/usr/bin/env python3
"""
Security Threat Detection and Analytics System
Advanced security monitoring, threat detection, and vulnerability analysis
"""

import re
import json
import time
import logging
import hashlib
import threading
from datetime import datetime, timedelta
from collections import defaultdict, deque
from ipaddress import ip_address, ip_network
from flask import request, g
from database import db
from services.monitoring.system_logger import system_logger

logger = logging.getLogger(__name__)

class SecurityThreatMonitor:
    """Advanced security monitoring and threat detection"""
    
    def __init__(self):
        # Threat detection patterns
        self.attack_patterns = {
            'sql_injection': [
                r"(\%27)|(\')|(\-\-)|(\%23)|(#)",
                r"((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))",
                r"w*((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))",
                r"((\%27)|(\'))union",
                r"exec(\s|\+)+(s|x)p\w+",
                r"UNION[^a-zA-Z]+SELECT",
                r"SELECT[^a-zA-Z]+.*FROM",
                r"INSERT[^a-zA-Z]+INTO",
                r"UPDATE[^a-zA-Z]+.*SET",
                r"DELETE[^a-zA-Z]+FROM"
            ],
            'xss': [
                r"<script[^>]*>.*?</script>",
                r"javascript:",
                r"onload\s*=",
                r"onerror\s*=",
                r"onclick\s*=",
                r"onmouseover\s*=",
                r"<iframe[^>]*>",
                r"<object[^>]*>",
                r"<embed[^>]*>",
                r"<applet[^>]*>"
            ],
            'lfi': [
                r"(\.\.\/){3,}",
                r"\.\.\\",
                r"\/etc\/passwd",
                r"\/etc\/shadow",
                r"\/proc\/version",
                r"\/windows\/system32",
                r"boot\.ini",
                r"win\.ini"
            ],
            'rfi': [
                r"https?:\/\/[^\/]+\/",
                r"ftp:\/\/[^\/]+\/",
                r"php:\/\/input",
                r"php:\/\/filter",
                r"data:text\/plain"
            ],
            'command_injection': [
                r"[;&|`]",
                r"nc\s+-l",
                r"wget\s+",
                r"curl\s+",
                r"powershell",
                r"cmd\.exe",
                r"\/bin\/bash",
                r"\/bin\/sh",
                r"python\s+-c",
                r"perl\s+-e"
            ],
            'path_traversal': [
                r"\.\.\/",
                r"\.\.\\",
                r"%2e%2e%2f",
                r"%2e%2e%5c",
                r"..%2f",
                r"..%5c"
            ]
        }
        
        # Suspicious user agents
        self.suspicious_agents = [
            r"sqlmap",
            r"nikto",
            r"nmap",
            r"masscan",
            r"dirb",
            r"gobuster",
            r"wfuzz",
            r"burp",
            r"w3af",
            r"acunetix",
            r"nessus",
            r"openvas"
        ]
        
        # IP reputation lists
        self.known_bad_ips = set()
        self.known_good_ips = set()
        self.rate_limits = defaultdict(lambda: {'count': 0, 'window_start': time.time()})
        
        # Security metrics
        self.security_stats = {
            'total_requests': 0,
            'blocked_requests': 0,
            'suspicious_requests': 0,
            'attacks_detected': defaultdict(int),
            'top_attacking_ips': defaultdict(int),
            'blocked_ips': set(),
            'last_attack': None
        }
        
        # Real-time monitoring
        self.recent_threats = deque(maxlen=1000)
        self.active_sessions = {}
        
        # Configuration
        self.rate_limit_requests = 100  # requests per minute
        self.rate_limit_window = 60  # seconds
        self.block_threshold = 5  # violations before block
        self.suspicious_threshold = 3  # violations before marking suspicious
        
        # Thread safety
        self.stats_lock = threading.Lock()
        
        # Initialize security monitoring
        self._setup_security_monitoring()
        
        logger.info("Security Threat Monitor initialized")
    
    def _setup_security_monitoring(self):
        """Set up security monitoring infrastructure"""
        try:
            # Create security monitoring tables
            self._create_security_tables()
            
            # Load threat intelligence
            self._load_threat_intelligence()
            
            # Start background monitoring
            self._start_security_monitoring()
            
        except Exception as e:
            logger.error(f"Failed to setup security monitoring: {e}")
    
    def _create_security_tables(self):
        """Create security monitoring tables"""
        security_tables = [
            '''CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                severity TEXT CHECK(severity IN ('low', 'medium', 'high', 'critical')) NOT NULL,
                source_ip TEXT NOT NULL,
                user_agent TEXT,
                endpoint TEXT,
                method TEXT,
                payload TEXT,
                attack_type TEXT,
                blocked BOOLEAN DEFAULT FALSE,
                confidence_score REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )''',
            
            '''CREATE TABLE IF NOT EXISTS ip_reputation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT UNIQUE NOT NULL,
                reputation TEXT CHECK(reputation IN ('good', 'suspicious', 'bad')) NOT NULL,
                attack_count INTEGER DEFAULT 0,
                last_attack DATETIME,
                blocked BOOLEAN DEFAULT FALSE,
                block_reason TEXT,
                first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
            )''',
            
            '''CREATE TABLE IF NOT EXISTS security_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_name TEXT UNIQUE NOT NULL,
                rule_type TEXT NOT NULL,
                pattern TEXT NOT NULL,
                enabled BOOLEAN DEFAULT TRUE,
                severity TEXT CHECK(severity IN ('low', 'medium', 'high', 'critical')) NOT NULL,
                action TEXT CHECK(action IN ('log', 'block', 'quarantine')) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )''',
            
            '''CREATE TABLE IF NOT EXISTS security_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                severity TEXT CHECK(severity IN ('low', 'medium', 'high', 'critical')) NOT NULL,
                message TEXT NOT NULL,
                source_ip TEXT,
                endpoint TEXT,
                details TEXT,
                resolved BOOLEAN DEFAULT FALSE,
                acknowledged BOOLEAN DEFAULT FALSE,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )''',
            
            '''CREATE TABLE IF NOT EXISTS file_integrity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                file_size INTEGER,
                last_modified DATETIME,
                integrity_status TEXT CHECK(integrity_status IN ('clean', 'modified', 'suspicious')) DEFAULT 'clean',
                scan_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )'''
        ]
        
        try:
            with db.get_connection() as conn:
                for table_sql in security_tables:
                    conn.execute(table_sql)
                
                # Create indexes for performance
                security_indexes = [
                    'CREATE INDEX IF NOT EXISTS idx_security_events_ip ON security_events(source_ip, timestamp)',
                    'CREATE INDEX IF NOT EXISTS idx_security_events_type ON security_events(event_type, timestamp)',
                    'CREATE INDEX IF NOT EXISTS idx_ip_reputation_ip ON ip_reputation(ip_address)',
                    'CREATE INDEX IF NOT EXISTS idx_security_rules_enabled ON security_rules(enabled, rule_type)',
                    'CREATE INDEX IF NOT EXISTS idx_security_alerts_resolved ON security_alerts(resolved, timestamp)',
                    'CREATE INDEX IF NOT EXISTS idx_file_integrity_path ON file_integrity(file_path, scan_timestamp)'
                ]
                
                for index_sql in security_indexes:
                    conn.execute(index_sql)
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to create security tables: {e}")
    
    def _load_threat_intelligence(self):
        """Load threat intelligence data"""
        try:
            # Load known bad IPs from database
            with db.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT ip_address FROM ip_reputation 
                    WHERE reputation = 'bad' AND blocked = TRUE
                ''')
                
                self.known_bad_ips.update(row[0] for row in cursor.fetchall())
            
            # Load default security rules
            self._load_default_security_rules()
            
            logger.info(f"Loaded {len(self.known_bad_ips)} known bad IPs")
            
        except Exception as e:
            logger.error(f"Failed to load threat intelligence: {e}")
    
    def _load_default_security_rules(self):
        """Load default security rules"""
        try:
            default_rules = [
                ('SQL Injection Detection', 'payload', r"(\%27)|(\')|(\-\-)|(\%23)|(#)", 'high', 'block'),
                ('XSS Detection', 'payload', r"<script[^>]*>.*?</script>", 'high', 'block'),
                ('Path Traversal', 'payload', r"\.\.\/", 'medium', 'block'),
                ('Command Injection', 'payload', r"[;&|`]", 'high', 'block'),
                ('Suspicious User Agent', 'user_agent', r"sqlmap|nikto|nmap", 'medium', 'log'),
                ('High Request Rate', 'rate_limit', r"", 'low', 'log')
            ]
            
            with db.get_connection() as conn:
                for rule_name, rule_type, pattern, severity, action in default_rules:
                    conn.execute('''
                        INSERT OR IGNORE INTO security_rules
                        (rule_name, rule_type, pattern, severity, action)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (rule_name, rule_type, pattern, severity, action))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to load default security rules: {e}")
    
    def _start_security_monitoring(self):
        """Start background security monitoring"""
        def monitor_thread():
            while True:
                try:
                    self._update_ip_reputation()
                    self._check_security_alerts()
                    self._cleanup_old_events()
                    self._update_threat_intelligence()
                    time.sleep(300)  # Run every 5 minutes
                except Exception as e:
                    logger.error(f"Background security monitoring error: {e}")
                    time.sleep(60)
        
        thread = threading.Thread(target=monitor_thread, daemon=True)
        thread.start()
    
    def _update_ip_reputation(self):
        """Update IP reputation based on recent activity"""
        try:
            with db.get_connection() as conn:
                # Find IPs with multiple security events
                cursor = conn.execute('''
                    SELECT source_ip, COUNT(*) as event_count,
                           MAX(timestamp) as last_event
                    FROM security_events
                    WHERE timestamp > datetime('now', '-24 hours')
                    GROUP BY source_ip
                    HAVING event_count >= ?
                ''', (self.suspicious_threshold,))
                
                for ip, event_count, last_event in cursor.fetchall():
                    reputation = 'suspicious' if event_count < self.block_threshold else 'bad'
                    blocked = event_count >= self.block_threshold
                    
                    # Update IP reputation
                    conn.execute('''
                        INSERT OR REPLACE INTO ip_reputation
                        (ip_address, reputation, attack_count, last_attack, blocked, last_seen)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (ip, reputation, event_count, last_event, blocked, datetime.now()))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update IP reputation: {e}")
    
    def _check_security_alerts(self):
        """Check for security alerts"""
        try:
            with self.stats_lock:
                stats = dict(self.security_stats)
            
            # Check for high attack rates
            if stats['total_requests'] > 0:
                attack_rate = stats['suspicious_requests'] / stats['total_requests']
                if attack_rate > 0.1:  # 10% attack rate
                    self._create_security_alert(
                        'high_attack_rate', 'high',
                        f'High attack rate detected: {attack_rate:.1%}',
                        details={
                            'attack_rate': attack_rate,
                            'suspicious_requests': stats['suspicious_requests'],
                            'total_requests': stats['total_requests']
                        }
                    )
            
            # Check for persistent attackers
            for ip, count in stats['top_attacking_ips'].items():
                if count > 10:  # More than 10 attacks
                    self._create_security_alert(
                        'persistent_attacker', 'high',
                        f'Persistent attacker detected: {ip}',
                        source_ip=ip,
                        details={'attack_count': count}
                    )
            
        except Exception as e:
            logger.error(f"Failed to check security alerts: {e}")
    
    def _create_security_alert(self, alert_type, severity, message, 
                             source_ip=None, endpoint=None, details=None):
        """Create a security alert"""
        try:
            with db.get_connection() as conn:
                # Check if similar alert already exists
                cursor = conn.execute('''
                    SELECT id FROM security_alerts
                    WHERE alert_type = ? AND source_ip = ? AND resolved = FALSE
                    AND timestamp > datetime('now', '-1 hour')
                ''', (alert_type, source_ip))
                
                if cursor.fetchone():
                    return  # Alert already exists
                
                # Create new alert
                conn.execute('''
                    INSERT INTO security_alerts
                    (alert_type, severity, message, source_ip, endpoint, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (alert_type, severity, message, source_ip, endpoint, 
                      json.dumps(details) if details else None))
                
                conn.commit()
                
                # Log to system logger
                system_logger.log_system_event(
                    level=severity,
                    component='security_monitor',
                    message=message,
                    details=details or {}
                )
                
        except Exception as e:
            logger.error(f"Failed to create security alert: {e}")
    
    def _cleanup_old_events(self):
        """Clean up old security events"""
        try:
            with db.get_connection() as conn:
                # Keep events for 90 days
                conn.execute('''
                    DELETE FROM security_events
                    WHERE timestamp < datetime('now', '-90 days')
                ''')
                
                # Keep resolved alerts for 30 days
                conn.execute('''
                    DELETE FROM security_alerts
                    WHERE resolved = TRUE AND timestamp < datetime('now', '-30 days')
                ''')
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to cleanup old events: {e}")
    
    def _update_threat_intelligence(self):
        """Update threat intelligence from external sources"""
        try:
            # In production, this would integrate with:
            # - Threat intelligence feeds
            # - IP reputation services
            # - CVE databases
            # - Security vendor APIs
            
            # For now, just update internal reputation
            with db.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT ip_address FROM ip_reputation
                    WHERE reputation = 'bad' AND blocked = TRUE
                ''')
                
                bad_ips = {row[0] for row in cursor.fetchall()}
                self.known_bad_ips.update(bad_ips)
                
        except Exception as e:
            logger.error(f"Failed to update threat intelligence: {e}")
    
    def analyze_request(self, request_data=None):
        """Analyze incoming request for security threats"""
        try:
            if not request_data:
                request_data = {
                    'ip': getattr(request, 'remote_addr', 'unknown'),
                    'user_agent': getattr(request, 'user_agent', {}).string if hasattr(request, 'user_agent') else '',
                    'endpoint': getattr(request, 'endpoint', 'unknown'),
                    'method': getattr(request, 'method', 'unknown'),
                    'args': dict(getattr(request, 'args', {})),
                    'form': dict(getattr(request, 'form', {})),
                    'headers': dict(getattr(request, 'headers', {}))
                }
            
            threats_detected = []
            confidence_score = 0
            
            # Check IP reputation
            if request_data['ip'] in self.known_bad_ips:
                threats_detected.append({
                    'type': 'bad_ip',
                    'severity': 'high',
                    'message': f'Request from known bad IP: {request_data["ip"]}',
                    'confidence': 0.9
                })
                confidence_score = max(confidence_score, 0.9)
            
            # Check rate limiting
            if self._check_rate_limit(request_data['ip']):
                threats_detected.append({
                    'type': 'rate_limit_exceeded',
                    'severity': 'medium',
                    'message': f'Rate limit exceeded for IP: {request_data["ip"]}',
                    'confidence': 0.8
                })
                confidence_score = max(confidence_score, 0.8)
            
            # Check for attack patterns
            payload = ' '.join([
                str(request_data.get('args', {})),
                str(request_data.get('form', {})),
                request_data.get('user_agent', ''),
                request_data.get('endpoint', '')
            ])
            
            for attack_type, patterns in self.attack_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, payload, re.IGNORECASE):
                        threats_detected.append({
                            'type': attack_type,
                            'severity': 'high',
                            'message': f'{attack_type.upper()} detected in request',
                            'pattern': pattern,
                            'confidence': 0.7
                        })
                        confidence_score = max(confidence_score, 0.7)
            
            # Check suspicious user agents
            user_agent = request_data.get('user_agent', '')
            for pattern in self.suspicious_agents:
                if re.search(pattern, user_agent, re.IGNORECASE):
                    threats_detected.append({
                        'type': 'suspicious_user_agent',
                        'severity': 'medium',
                        'message': f'Suspicious user agent detected: {user_agent}',
                        'confidence': 0.6
                    })
                    confidence_score = max(confidence_score, 0.6)
            
            # Update statistics
            self._update_security_stats(request_data, threats_detected)
            
            # Log security events
            if threats_detected:
                self._log_security_events(request_data, threats_detected, confidence_score)
            
            # Determine if request should be blocked
            should_block = any(
                threat['severity'] in ['high', 'critical'] 
                for threat in threats_detected
            ) or confidence_score > 0.8
            
            return {
                'threats_detected': threats_detected,
                'confidence_score': confidence_score,
                'should_block': should_block,
                'risk_level': self._calculate_risk_level(confidence_score)
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze request: {e}")
            return {
                'threats_detected': [],
                'confidence_score': 0,
                'should_block': False,
                'risk_level': 'unknown'
            }
    
    def _check_rate_limit(self, ip):
        """Check if IP exceeds rate limit"""
        try:
            current_time = time.time()
            rate_data = self.rate_limits[ip]
            
            # Reset window if expired
            if current_time - rate_data['window_start'] > self.rate_limit_window:
                rate_data['count'] = 0
                rate_data['window_start'] = current_time
            
            # Increment counter
            rate_data['count'] += 1
            
            # Check limit
            return rate_data['count'] > self.rate_limit_requests
            
        except Exception as e:
            logger.error(f"Failed to check rate limit: {e}")
            return False
    
    def _update_security_stats(self, request_data, threats_detected):
        """Update security statistics"""
        try:
            with self.stats_lock:
                self.security_stats['total_requests'] += 1
                
                if threats_detected:
                    self.security_stats['suspicious_requests'] += 1
                    
                    # Update attack types
                    for threat in threats_detected:
                        self.security_stats['attacks_detected'][threat['type']] += 1
                    
                    # Update attacking IPs
                    ip = request_data.get('ip', 'unknown')
                    self.security_stats['top_attacking_ips'][ip] += 1
                    
                    # Update last attack time
                    self.security_stats['last_attack'] = datetime.now().isoformat()
                    
                    # Add to recent threats
                    self.recent_threats.append({
                        'ip': ip,
                        'endpoint': request_data.get('endpoint'),
                        'threats': threats_detected,
                        'timestamp': datetime.now().isoformat()
                    })
                
        except Exception as e:
            logger.error(f"Failed to update security stats: {e}")
    
    def _log_security_events(self, request_data, threats_detected, confidence_score):
        """Log security events to database"""
        try:
            with db.get_connection() as conn:
                for threat in threats_detected:
                    conn.execute('''
                        INSERT INTO security_events
                        (event_type, severity, source_ip, user_agent, endpoint, 
                         method, payload, attack_type, confidence_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        threat['type'], threat['severity'], request_data.get('ip'),
                        request_data.get('user_agent'), request_data.get('endpoint'),
                        request_data.get('method'), json.dumps(request_data),
                        threat['type'], confidence_score
                    ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to log security events: {e}")
    
    def _calculate_risk_level(self, confidence_score):
        """Calculate risk level based on confidence score"""
        if confidence_score >= 0.8:
            return 'critical'
        elif confidence_score >= 0.6:
            return 'high'
        elif confidence_score >= 0.4:
            return 'medium'
        elif confidence_score >= 0.2:
            return 'low'
        else:
            return 'minimal'
    
    def get_security_dashboard(self):
        """Get security monitoring dashboard data"""
        try:
            dashboard_data = {
                'security_stats': dict(self.security_stats),
                'recent_threats': list(self.recent_threats)[-50:],  # Last 50 threats
                'blocked_ips': list(self.known_bad_ips)[-100:],    # Last 100 blocked IPs
                'security_alerts': self._get_active_security_alerts(),
                'attack_trends': self._get_attack_trends(),
                'threat_intelligence': self._get_threat_intelligence_summary(),
                'vulnerability_scan': self._get_vulnerability_scan_results()
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Failed to get security dashboard: {e}")
            return {}
    
    def _get_active_security_alerts(self):
        """Get active security alerts"""
        try:
            with db.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT alert_type, severity, message, source_ip, timestamp
                    FROM security_alerts
                    WHERE resolved = FALSE
                    ORDER BY timestamp DESC
                    LIMIT 100
                ''')
                
                alerts = []
                for row in cursor.fetchall():
                    alerts.append({
                        'type': row[0],
                        'severity': row[1],
                        'message': row[2],
                        'source_ip': row[3],
                        'timestamp': row[4]
                    })
                
                return alerts
                
        except Exception as e:
            logger.error(f"Failed to get active alerts: {e}")
            return []
    
    def _get_attack_trends(self):
        """Get attack trends over time"""
        try:
            with db.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT 
                        datetime(timestamp, 'localtime', 'start of hour') as hour,
                        attack_type,
                        COUNT(*) as count
                    FROM security_events
                    WHERE timestamp > datetime('now', '-24 hours')
                    GROUP BY datetime(timestamp, 'localtime', 'start of hour'), attack_type
                    ORDER BY hour, count DESC
                ''')
                
                trends = []
                for row in cursor.fetchall():
                    trends.append({
                        'hour': row[0],
                        'attack_type': row[1],
                        'count': row[2]
                    })
                
                return trends
                
        except Exception as e:
            logger.error(f"Failed to get attack trends: {e}")
            return []
    
    def _get_threat_intelligence_summary(self):
        """Get threat intelligence summary"""
        try:
            with db.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT 
                        reputation,
                        COUNT(*) as count,
                        AVG(attack_count) as avg_attacks
                    FROM ip_reputation
                    GROUP BY reputation
                ''')
                
                summary = {}
                for row in cursor.fetchall():
                    summary[row[0]] = {
                        'count': row[1],
                        'avg_attacks': row[2]
                    }
                
                return summary
                
        except Exception as e:
            logger.error(f"Failed to get threat intelligence summary: {e}")
            return {}
    
    def _get_vulnerability_scan_results(self):
        """Get vulnerability scan results"""
        try:
            # In production, this would integrate with vulnerability scanners
            # For now, return basic file integrity checks
            
            with db.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT file_path, integrity_status, scan_timestamp
                    FROM file_integrity
                    WHERE integrity_status != 'clean'
                    ORDER BY scan_timestamp DESC
                    LIMIT 20
                ''')
                
                vulnerabilities = []
                for row in cursor.fetchall():
                    vulnerabilities.append({
                        'file_path': row[0],
                        'status': row[1],
                        'timestamp': row[2]
                    })
                
                return vulnerabilities
                
        except Exception as e:
            logger.error(f"Failed to get vulnerability scan results: {e}")
            return []
    
    def block_ip(self, ip_address, reason):
        """Block an IP address"""
        try:
            with db.get_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO ip_reputation
                    (ip_address, reputation, blocked, block_reason, last_seen)
                    VALUES (?, 'bad', TRUE, ?, datetime('now'))
                ''', (ip_address, reason))
                
                conn.commit()
                
            # Add to known bad IPs
            self.known_bad_ips.add(ip_address)
            
            # Create security alert
            self._create_security_alert(
                'ip_blocked', 'high',
                f'IP address blocked: {ip_address}',
                source_ip=ip_address,
                details={'reason': reason}
            )
            
            logger.info(f"IP {ip_address} blocked: {reason}")
            
        except Exception as e:
            logger.error(f"Failed to block IP {ip_address}: {e}")
    
    def unblock_ip(self, ip_address):
        """Unblock an IP address"""
        try:
            with db.get_connection() as conn:
                conn.execute('''
                    UPDATE ip_reputation
                    SET blocked = FALSE, reputation = 'good'
                    WHERE ip_address = ?
                ''', (ip_address,))
                
                conn.commit()
                
            # Remove from known bad IPs
            self.known_bad_ips.discard(ip_address)
            
            logger.info(f"IP {ip_address} unblocked")
            
        except Exception as e:
            logger.error(f"Failed to unblock IP {ip_address}: {e}")


# Global security threat monitor instance
security_monitor = SecurityThreatMonitor()

# Convenience function for request analysis
def analyze_request_security(request_data=None):
    """Analyze request for security threats"""
    return security_monitor.analyze_request(request_data)

if __name__ == '__main__':
    # Test security threat monitoring
    print("🔒 Testing VectorCraft Security Threat Monitor...")
    
    # Test request analysis
    test_request = {
        'ip': '192.168.1.100',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'endpoint': '/api/upload',
        'method': 'POST',
        'args': {'file': 'test.jpg'},
        'form': {},
        'headers': {}
    }
    
    analysis = security_monitor.analyze_request(test_request)
    
    print(f"\n🔍 Security Analysis Results:")
    print(f"Threats detected: {len(analysis['threats_detected'])}")
    print(f"Confidence score: {analysis['confidence_score']:.2f}")
    print(f"Should block: {analysis['should_block']}")
    print(f"Risk level: {analysis['risk_level']}")
    
    # Get dashboard data
    dashboard = security_monitor.get_security_dashboard()
    
    print(f"\n📊 Security Dashboard:")
    print(f"Total requests: {dashboard.get('security_stats', {}).get('total_requests', 0)}")
    print(f"Suspicious requests: {dashboard.get('security_stats', {}).get('suspicious_requests', 0)}")
    print(f"Blocked IPs: {len(dashboard.get('blocked_ips', []))}")
    print(f"Active alerts: {len(dashboard.get('security_alerts', []))}")
    print(f"Recent threats: {len(dashboard.get('recent_threats', []))}")