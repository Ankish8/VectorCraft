#!/usr/bin/env python3
"""
Advanced Security & Audit Management Service for VectorCraft
Provides comprehensive security monitoring, audit logging, access control, and threat detection
"""

import os
import mimetypes
import hashlib
import subprocess
import tempfile
import magic
from PIL import Image
from PIL.ExifTags import TAGS
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sqlite3
import threading
import ipaddress
from collections import defaultdict, deque
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SecurityEvent:
    """Security event data structure"""
    timestamp: datetime
    event_type: str
    severity: str
    source_ip: str
    user_id: Optional[str]
    description: str
    details: Dict
    resolved: bool = False
    
@dataclass
class AuditLog:
    """Audit log entry data structure"""
    timestamp: datetime
    user_id: Optional[str]
    action: str
    resource: str
    source_ip: str
    user_agent: str
    success: bool
    details: Dict
    
@dataclass
class ThreatIndicator:
    """Threat indicator data structure"""
    indicator_type: str
    value: str
    severity: str
    description: str
    first_seen: datetime
    last_seen: datetime
    count: int
    
class SecurityService:
    def __init__(self):
        # File validation settings
        self.allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
        self.allowed_mime_types = {
            'image/png', 'image/jpeg', 'image/gif', 
            'image/bmp', 'image/tiff', 'image/x-ms-bmp'
        }
        self.max_file_size = 16 * 1024 * 1024  # 16MB
        self.max_image_dimensions = (8192, 8192)  # 8K resolution max
        
        # Security monitoring settings
        self.rate_limit_window = 300  # 5 minutes
        self.max_requests_per_window = 100
        self.failed_login_threshold = 5
        self.ip_blocking_duration = 3600  # 1 hour
        
        # Initialize security components
        self.security_events = deque(maxlen=10000)
        self.audit_logs = deque(maxlen=50000)
        self.threat_indicators = {}
        self.blocked_ips = {}
        self.rate_limiting = defaultdict(lambda: defaultdict(list))
        self.failed_login_attempts = defaultdict(list)
        self.active_sessions = {}
        
        # Initialize database
        self._init_security_database()
        
        # Start background monitoring
        self._start_monitoring_threads()
        
    def _init_security_database(self):
        """Initialize security database tables"""
        try:
            conn = sqlite3.connect('vectorcraft.db')
            cursor = conn.cursor()
            
            # Security events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS security_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    source_ip TEXT,
                    user_id TEXT,
                    description TEXT NOT NULL,
                    details TEXT,
                    resolved BOOLEAN DEFAULT 0
                )
            ''')
            
            # Audit logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT,
                    action TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    source_ip TEXT,
                    user_agent TEXT,
                    success BOOLEAN NOT NULL,
                    details TEXT
                )
            ''')
            
            # Threat indicators table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS threat_indicators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    indicator_type TEXT NOT NULL,
                    value TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    description TEXT,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    count INTEGER DEFAULT 1,
                    UNIQUE(indicator_type, value)
                )
            ''')
            
            # Access control table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS access_control (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    permission TEXT NOT NULL,
                    granted_by TEXT,
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    UNIQUE(user_id, resource, permission)
                )
            ''')
            
            # IP blocking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ip_blocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip_address TEXT UNIQUE NOT NULL,
                    reason TEXT NOT NULL,
                    blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    blocked_until TIMESTAMP,
                    blocked_by TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Security database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize security database: {e}")
    
    def _start_monitoring_threads(self):
        """Start background monitoring threads"""
        # Start threat detection thread
        threat_thread = threading.Thread(target=self._threat_detection_loop, daemon=True)
        threat_thread.start()
        
        # Start cleanup thread
        cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        cleanup_thread.start()
        
        logger.info("Security monitoring threads started")
        
    # ========== SECURITY MONITORING ==========
    
    def log_security_event(self, event_type: str, severity: str, source_ip: str, 
                          user_id: Optional[str], description: str, details: Dict = None):
        """Log a security event"""
        try:
            event = SecurityEvent(
                timestamp=datetime.utcnow(),
                event_type=event_type,
                severity=severity,
                source_ip=source_ip,
                user_id=user_id,
                description=description,
                details=details or {}
            )
            
            self.security_events.append(event)
            
            # Store in database
            conn = sqlite3.connect('vectorcraft.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO security_events 
                (event_type, severity, source_ip, user_id, description, details)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (event_type, severity, source_ip, user_id, description, json.dumps(details)))
            conn.commit()
            conn.close()
            
            logger.info(f"Security event logged: {event_type} - {description}")
            # Trigger alerts for high severity events
            if severity in ['HIGH', 'CRITICAL']:
                self._trigger_security_alert(event)
                
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
    
    def log_audit_event(self, user_id: Optional[str], action: str, resource: str, 
                       source_ip: str, user_agent: str, success: bool, details: Dict = None):
        """Log an audit event"""
        try:
            audit_log = AuditLog(
                timestamp=datetime.utcnow(),
                user_id=user_id,
                action=action,
                resource=resource,
                source_ip=source_ip,
                user_agent=user_agent,
                success=success,
                details=details or {}
            )
            
            self.audit_logs.append(audit_log)
            
            # Store in database
            conn = sqlite3.connect('vectorcraft.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO audit_logs 
                (user_id, action, resource, source_ip, user_agent, success, details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, action, resource, source_ip, user_agent, success, json.dumps(details)))
            conn.commit()
            conn.close()
            
            logger.info(f"Audit event logged: {action} on {resource} by {user_id or 'anonymous'}")
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
    
    def check_rate_limit(self, source_ip: str, endpoint: str) -> bool:
        """Check if request exceeds rate limit"""
        try:\n            current_time = time.time()\n            window_start = current_time - self.rate_limit_window\n            \n            # Clean old entries\n            self.rate_limiting[source_ip][endpoint] = [\n                req_time for req_time in self.rate_limiting[source_ip][endpoint]\n                if req_time > window_start\n            ]\n            \n            # Check current count\n            request_count = len(self.rate_limiting[source_ip][endpoint])\n            \n            if request_count >= self.max_requests_per_window:\n                self.log_security_event(\n                    'RATE_LIMIT_EXCEEDED',\n                    'MEDIUM',\n                    source_ip,\n                    None,\n                    f'Rate limit exceeded for endpoint {endpoint}',\n                    {'endpoint': endpoint, 'count': request_count}\n                )\n                return False\n            \n            # Add current request\n            self.rate_limiting[source_ip][endpoint].append(current_time)\n            return True\n            \n        except Exception as e:\n            logger.error(f\"Rate limit check failed: {e}\")\n            return True  # Allow request on error\n    \n    def check_ip_blocked(self, source_ip: str) -> bool:\n        \"\"\"Check if IP is blocked\"\"\"\n        try:\n            current_time = datetime.utcnow()\n            \n            # Check memory cache first\n            if source_ip in self.blocked_ips:\n                block_info = self.blocked_ips[source_ip]\n                if block_info['until'] > current_time:\n                    return True\n                else:\n                    # Block expired\n                    del self.blocked_ips[source_ip]\n            \n            # Check database\n            conn = sqlite3.connect('vectorcraft.db')\n            cursor = conn.cursor()\n            cursor.execute('''\n                SELECT blocked_until FROM ip_blocks \n                WHERE ip_address = ? AND blocked_until > datetime('now')\n            ''', (source_ip,))\n            \n            result = cursor.fetchone()\n            conn.close()\n            \n            if result:\n                # Add to memory cache\n                self.blocked_ips[source_ip] = {\n                    'until': datetime.fromisoformat(result[0])\n                }\n                return True\n            \n            return False\n            \n        except Exception as e:\n            logger.error(f\"IP block check failed: {e}\")\n            return False\n    \n    def block_ip(self, source_ip: str, reason: str, duration_hours: int = 24, blocked_by: str = 'system'):\n        \"\"\"Block an IP address\"\"\"\n        try:\n            current_time = datetime.utcnow()\n            blocked_until = current_time + timedelta(hours=duration_hours)\n            \n            # Add to memory cache\n            self.blocked_ips[source_ip] = {\n                'until': blocked_until,\n                'reason': reason\n            }\n            \n            # Store in database\n            conn = sqlite3.connect('vectorcraft.db')\n            cursor = conn.cursor()\n            cursor.execute('''\n                INSERT OR REPLACE INTO ip_blocks \n                (ip_address, reason, blocked_until, blocked_by)\n                VALUES (?, ?, ?, ?)\n            ''', (source_ip, reason, blocked_until, blocked_by))\n            conn.commit()\n            conn.close()\n            \n            self.log_security_event(\n                'IP_BLOCKED',\n                'HIGH',\n                source_ip,\n                None,\n                f'IP blocked: {reason}',\n                {'duration_hours': duration_hours, 'blocked_by': blocked_by}\n            )\n            \n            logger.warning(f\"IP {source_ip} blocked for {duration_hours} hours: {reason}\")\n            \n        except Exception as e:\n            logger.error(f\"Failed to block IP: {e}\")\n    \n    def record_failed_login(self, source_ip: str, username: str):\n        \"\"\"Record a failed login attempt\"\"\"\n        try:\n            current_time = time.time()\n            window_start = current_time - 3600  # 1 hour window\n            \n            # Clean old entries\n            self.failed_login_attempts[source_ip] = [\n                (timestamp, user) for timestamp, user in self.failed_login_attempts[source_ip]\n                if timestamp > window_start\n            ]\n            \n            # Add current attempt\n            self.failed_login_attempts[source_ip].append((current_time, username))\n            \n            # Check threshold\n            if len(self.failed_login_attempts[source_ip]) >= self.failed_login_threshold:\n                self.block_ip(source_ip, f'Too many failed login attempts', 1)\n                \n            self.log_security_event(\n                'FAILED_LOGIN',\n                'MEDIUM',\n                source_ip,\n                username,\n                f'Failed login attempt for user {username}',\n                {'attempt_count': len(self.failed_login_attempts[source_ip])}\n            )\n            \n        except Exception as e:\n            logger.error(f\"Failed to record failed login: {e}\")\n    \n    def add_threat_indicator(self, indicator_type: str, value: str, severity: str, description: str):\n        \"\"\"Add a threat indicator\"\"\"\n        try:\n            key = f\"{indicator_type}:{value}\"\n            current_time = datetime.utcnow()\n            \n            if key in self.threat_indicators:\n                # Update existing indicator\n                indicator = self.threat_indicators[key]\n                indicator.last_seen = current_time\n                indicator.count += 1\n            else:\n                # Create new indicator\n                indicator = ThreatIndicator(\n                    indicator_type=indicator_type,\n                    value=value,\n                    severity=severity,\n                    description=description,\n                    first_seen=current_time,\n                    last_seen=current_time,\n                    count=1\n                )\n                self.threat_indicators[key] = indicator\n            \n            # Store in database\n            conn = sqlite3.connect('vectorcraft.db')\n            cursor = conn.cursor()\n            cursor.execute('''\n                INSERT OR REPLACE INTO threat_indicators \n                (indicator_type, value, severity, description, first_seen, last_seen, count)\n                VALUES (?, ?, ?, ?, ?, ?, ?)\n            ''', (indicator_type, value, severity, description, \n                 indicator.first_seen, indicator.last_seen, indicator.count))\n            conn.commit()\n            conn.close()\n            \n            logger.info(f\"Threat indicator added: {indicator_type}:{value}\")\n            \n        except Exception as e:\n            logger.error(f\"Failed to add threat indicator: {e}\")\n    \n    def _threat_detection_loop(self):\n        \"\"\"Background threat detection loop\"\"\"\n        while True:\n            try:\n                self._analyze_security_patterns()\n                time.sleep(60)  # Check every minute\n            except Exception as e:\n                logger.error(f\"Threat detection loop error: {e}\")\n                time.sleep(60)\n    \n    def _analyze_security_patterns(self):\n        \"\"\"Analyze patterns for potential threats\"\"\"\n        try:\n            # Analyze recent security events\n            recent_events = [event for event in self.security_events \n                           if event.timestamp > datetime.utcnow() - timedelta(hours=1)]\n            \n            # Check for suspicious IP patterns\n            ip_events = defaultdict(list)\n            for event in recent_events:\n                if event.source_ip:\n                    ip_events[event.source_ip].append(event)\n            \n            for ip, events in ip_events.items():\n                if len(events) > 10:  # More than 10 events in an hour\n                    self.add_threat_indicator(\n                        'ip', ip, 'MEDIUM', \n                        f'Suspicious activity: {len(events)} events in 1 hour'\n                    )\n            \n            # Check for brute force patterns\n            failed_logins = [event for event in recent_events \n                           if event.event_type == 'FAILED_LOGIN']\n            \n            login_ips = defaultdict(int)\n            for event in failed_logins:\n                login_ips[event.source_ip] += 1\n            \n            for ip, count in login_ips.items():\n                if count > 5:\n                    self.add_threat_indicator(\n                        'ip', ip, 'HIGH', \n                        f'Brute force attack detected: {count} failed logins'\n                    )\n            \n        except Exception as e:\n            logger.error(f\"Threat pattern analysis failed: {e}\")\n    \n    def _cleanup_loop(self):\n        \"\"\"Background cleanup loop\"\"\"\n        while True:\n            try:\n                self._cleanup_expired_data()\n                time.sleep(3600)  # Cleanup every hour\n            except Exception as e:\n                logger.error(f\"Cleanup loop error: {e}\")\n                time.sleep(3600)\n    \n    def _cleanup_expired_data(self):\n        \"\"\"Clean up expired security data\"\"\"\n        try:\n            current_time = datetime.utcnow()\n            \n            # Clean expired IP blocks\n            expired_ips = [ip for ip, info in self.blocked_ips.items() \n                          if info['until'] < current_time]\n            for ip in expired_ips:\n                del self.blocked_ips[ip]\n            \n            # Clean old database entries\n            conn = sqlite3.connect('vectorcraft.db')\n            cursor = conn.cursor()\n            \n            # Clean old security events (keep 30 days)\n            cursor.execute('''\n                DELETE FROM security_events \n                WHERE timestamp < datetime('now', '-30 days')\n            ''')\n            \n            # Clean old audit logs (keep 90 days)\n            cursor.execute('''\n                DELETE FROM audit_logs \n                WHERE timestamp < datetime('now', '-90 days')\n            ''')\n            \n            # Clean expired IP blocks\n            cursor.execute('''\n                DELETE FROM ip_blocks \n                WHERE blocked_until < datetime('now')\n            ''')\n            \n            conn.commit()\n            conn.close()\n            \n            logger.info(\"Security data cleanup completed\")\n            \n        except Exception as e:\n            logger.error(f\"Cleanup failed: {e}\")\n    \n    def _trigger_security_alert(self, event: SecurityEvent):\n        \"\"\"Trigger security alert for high severity events\"\"\"\n        try:\n            # In production, this would:\n            # - Send email alerts\n            # - Push notifications\n            # - Integration with SIEM systems\n            # - Slack/Teams notifications\n            \n            logger.critical(f\"SECURITY ALERT: {event.event_type} - {event.description}\")\n            \n        except Exception as e:\n            logger.error(f\"Failed to trigger security alert: {e}\")\n    \n    # ========== ACCESS CONTROL ==========\n    \n    def check_permission(self, user_id: str, resource: str, permission: str) -> bool:\n        \"\"\"Check if user has permission for resource\"\"\"\n        try:\n            conn = sqlite3.connect('vectorcraft.db')\n            cursor = conn.cursor()\n            cursor.execute('''\n                SELECT COUNT(*) FROM access_control \n                WHERE user_id = ? AND resource = ? AND permission = ?\n                AND (expires_at IS NULL OR expires_at > datetime('now'))\n            ''', (user_id, resource, permission))\n            \n            result = cursor.fetchone()\n            conn.close()\n            \n            has_permission = result[0] > 0\n            \n            self.log_audit_event(\n                user_id, 'PERMISSION_CHECK', resource, \n                '', '', has_permission,\n                {'permission': permission, 'result': has_permission}\n            )\n            \n            return has_permission\n            \n        except Exception as e:\n            logger.error(f\"Permission check failed: {e}\")\n            return False\n    \n    def grant_permission(self, user_id: str, resource: str, permission: str, \n                        granted_by: str, expires_at: Optional[datetime] = None):\n        \"\"\"Grant permission to user\"\"\"\n        try:\n            conn = sqlite3.connect('vectorcraft.db')\n            cursor = conn.cursor()\n            cursor.execute('''\n                INSERT OR REPLACE INTO access_control \n                (user_id, resource, permission, granted_by, expires_at)\n                VALUES (?, ?, ?, ?, ?)\n            ''', (user_id, resource, permission, granted_by, expires_at))\n            conn.commit()\n            conn.close()\n            \n            self.log_audit_event(\n                granted_by, 'GRANT_PERMISSION', resource, \n                '', '', True,\n                {'target_user': user_id, 'permission': permission}\n            )\n            \n            logger.info(f\"Permission granted: {user_id} -> {resource}:{permission}\")\n            \n        except Exception as e:\n            logger.error(f\"Failed to grant permission: {e}\")\n    \n    def revoke_permission(self, user_id: str, resource: str, permission: str, revoked_by: str):\n        \"\"\"Revoke permission from user\"\"\"\n        try:\n            conn = sqlite3.connect('vectorcraft.db')\n            cursor = conn.cursor()\n            cursor.execute('''\n                DELETE FROM access_control \n                WHERE user_id = ? AND resource = ? AND permission = ?\n            ''', (user_id, resource, permission))\n            conn.commit()\n            conn.close()\n            \n            self.log_audit_event(\n                revoked_by, 'REVOKE_PERMISSION', resource, \n                '', '', True,\n                {'target_user': user_id, 'permission': permission}\n            )\n            \n            logger.info(f\"Permission revoked: {user_id} -> {resource}:{permission}\")\n            \n        except Exception as e:\n            logger.error(f\"Failed to revoke permission: {e}\")\n    \n    # ========== ANALYTICS ==========\n    \n    def get_security_metrics(self) -> Dict:\n        \"\"\"Get security metrics and analytics\"\"\"\n        try:\n            conn = sqlite3.connect('vectorcraft.db')\n            cursor = conn.cursor()\n            \n            # Get event counts by type\n            cursor.execute('''\n                SELECT event_type, COUNT(*) \n                FROM security_events \n                WHERE timestamp > datetime('now', '-24 hours')\n                GROUP BY event_type\n            ''')\n            event_counts = dict(cursor.fetchall())\n            \n            # Get blocked IPs count\n            cursor.execute('''\n                SELECT COUNT(*) FROM ip_blocks \n                WHERE blocked_until > datetime('now')\n            ''')\n            blocked_ips_count = cursor.fetchone()[0]\n            \n            # Get threat indicators count\n            cursor.execute('''\n                SELECT severity, COUNT(*) \n                FROM threat_indicators \n                GROUP BY severity\n            ''')\n            threat_counts = dict(cursor.fetchall())\n            \n            # Get audit activity\n            cursor.execute('''\n                SELECT COUNT(*) \n                FROM audit_logs \n                WHERE timestamp > datetime('now', '-24 hours')\n            ''')\n            audit_activity = cursor.fetchone()[0]\n            \n            conn.close()\n            \n            return {\n                'event_counts': event_counts,\n                'blocked_ips_count': blocked_ips_count,\n                'threat_counts': threat_counts,\n                'audit_activity': audit_activity,\n                'active_sessions': len(self.active_sessions)\n            }\n            \n        except Exception as e:\n            logger.error(f\"Failed to get security metrics: {e}\")\n            return {}\n    \n    def get_recent_security_events(self, limit: int = 50) -> List[Dict]:\n        \"\"\"Get recent security events\"\"\"\n        try:\n            conn = sqlite3.connect('vectorcraft.db')\n            cursor = conn.cursor()\n            cursor.execute('''\n                SELECT timestamp, event_type, severity, source_ip, user_id, description, details\n                FROM security_events \n                ORDER BY timestamp DESC \n                LIMIT ?\n            ''', (limit,))\n            \n            events = []\n            for row in cursor.fetchall():\n                events.append({\n                    'timestamp': row[0],\n                    'event_type': row[1],\n                    'severity': row[2],\n                    'source_ip': row[3],\n                    'user_id': row[4],\n                    'description': row[5],\n                    'details': json.loads(row[6]) if row[6] else {}\n                })\n            \n            conn.close()\n            return events\n            \n        except Exception as e:\n            logger.error(f\"Failed to get recent security events: {e}\")\n            return []\n    \n    def get_audit_logs(self, limit: int = 100, user_id: Optional[str] = None) -> List[Dict]:\n        \"\"\"Get audit logs\"\"\"\n        try:\n            conn = sqlite3.connect('vectorcraft.db')\n            cursor = conn.cursor()\n            \n            if user_id:\n                cursor.execute('''\n                    SELECT timestamp, user_id, action, resource, source_ip, user_agent, success, details\n                    FROM audit_logs \n                    WHERE user_id = ?\n                    ORDER BY timestamp DESC \n                    LIMIT ?\n                ''', (user_id, limit))\n            else:\n                cursor.execute('''\n                    SELECT timestamp, user_id, action, resource, source_ip, user_agent, success, details\n                    FROM audit_logs \n                    ORDER BY timestamp DESC \n                    LIMIT ?\n                ''', (limit,))\n            \n            logs = []\n            for row in cursor.fetchall():\n                logs.append({\n                    'timestamp': row[0],\n                    'user_id': row[1],\n                    'action': row[2],\n                    'resource': row[3],\n                    'source_ip': row[4],\n                    'user_agent': row[5],\n                    'success': bool(row[6]),\n                    'details': json.loads(row[7]) if row[7] else {}\n                })\n            \n            conn.close()\n            return logs\n            \n        except Exception as e:\n            logger.error(f\"Failed to get audit logs: {e}\")\n            return []\n    \n    # ========== FILE VALIDATION (ORIGINAL METHODS) ==========\n    \n    def validate_file_extension(self, filename):
        """Validate file extension"""
        if '.' not in filename:
            return False
        extension = filename.rsplit('.', 1)[1].lower()
        return extension in self.allowed_extensions
    
    def validate_mime_type(self, file_path):
        """Validate MIME type using python-magic"""
        try:
            mime_type = magic.from_file(file_path, mime=True)
            return mime_type in self.allowed_mime_types
        except Exception as e:
            logger.error(f"Error checking MIME type: {e}")
            return False
    
    def validate_file_size(self, file_path):
        """Validate file size"""
        try:
            file_size = os.path.getsize(file_path)
            return file_size <= self.max_file_size
        except Exception as e:
            logger.error(f"Error checking file size: {e}")
            return False
    
    def validate_image_dimensions(self, file_path):
        """Validate image dimensions"""
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                return (width <= self.max_image_dimensions[0] and 
                       height <= self.max_image_dimensions[1])
        except Exception as e:
            logger.error(f"Error checking image dimensions: {e}")
            return False
    
    def strip_metadata(self, file_path, output_path):
        """Strip metadata from image files"""
        try:
            with Image.open(file_path) as img:
                # Create image without EXIF data
                data = list(img.getdata())
                image_without_exif = Image.new(img.mode, img.size)
                image_without_exif.putdata(data)
                
                # Save without metadata
                image_without_exif.save(output_path, optimize=True, quality=95)
                return True
        except Exception as e:
            logger.error(f"Error stripping metadata: {e}")
            return False
    
    def scan_for_malware(self, file_path):
        """Basic malware scanning using ClamAV if available"""
        try:
            # Check if ClamAV is available
            result = subprocess.run(['which', 'clamscan'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning("ClamAV not available - skipping virus scan")
                return True  # Allow file but log warning
            
            # Run ClamAV scan
            result = subprocess.run(['clamscan', '--no-summary', file_path], 
                                  capture_output=True, text=True, timeout=30)
            
            # Check result
            if result.returncode == 0:
                logger.info(f"File {file_path} passed virus scan")
                return True
            else:
                logger.error(f"File {file_path} failed virus scan: {result.stdout}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Virus scan timeout for {file_path}")
            return False
        except Exception as e:
            logger.error(f"Error during virus scan: {e}")
            return True  # Allow file but log error
    
    def calculate_file_hash(self, file_path):
        """Calculate SHA256 hash of file"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating file hash: {e}")
            return None
    
    def validate_and_sanitize_upload(self, file_path, original_filename):
        """
        Comprehensive file validation and sanitization
        Returns: (is_valid, sanitized_path, error_message)
        """
        try:
            # Step 1: Validate file extension
            if not self.validate_file_extension(original_filename):
                return False, None, "Invalid file extension"
            
            # Step 2: Validate file size
            if not self.validate_file_size(file_path):
                return False, None, "File size exceeds limit"
            
            # Step 3: Validate MIME type
            if not self.validate_mime_type(file_path):
                return False, None, "Invalid file type"
            
            # Step 4: Validate image dimensions
            if not self.validate_image_dimensions(file_path):
                return False, None, "Image dimensions exceed limit"
            
            # Step 5: Scan for malware
            if not self.scan_for_malware(file_path):
                return False, None, "File failed security scan"
            
            # Step 6: Calculate file hash for tracking
            file_hash = self.calculate_file_hash(file_path)
            logger.info(f"File hash: {file_hash}")
            
            # Step 7: Strip metadata and create sanitized version
            sanitized_path = file_path + '.sanitized'
            if not self.strip_metadata(file_path, sanitized_path):
                return False, None, "Failed to sanitize file"
            
            logger.info(f"File {original_filename} passed all security checks")
            return True, sanitized_path, None
            
        except Exception as e:
            logger.error(f"Error during file validation: {e}")
            return False, None, f"Security validation failed: {str(e)}"
    
    def check_file_reputation(self, file_hash):
        """
        Check file reputation against known malware hashes
        This is a placeholder for integration with threat intelligence feeds
        """
        # In production, this would check against:
        # - VirusTotal API
        # - Internal threat intelligence
        # - Known malware hash databases
        
        # For now, return clean
        return True

# Global security service instance
security_service = SecurityService()