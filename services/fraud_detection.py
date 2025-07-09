#!/usr/bin/env python3
"""
Fraud Detection System for VectorCraft
Basic fraud detection and prevention mechanisms
"""

import logging
import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict
import ipaddress
from database import db
from services.monitoring.alert_manager import alert_manager

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class FraudIndicator:
    """Fraud detection indicator"""
    indicator_type: str
    description: str
    weight: float
    value: str
    threshold: Optional[str] = None

@dataclass
class FraudAnalysis:
    """Fraud analysis result"""
    transaction_id: str
    email: str
    risk_score: float
    risk_level: RiskLevel
    indicators: List[FraudIndicator]
    recommended_action: str
    timestamp: datetime
    is_blocked: bool = False

class FraudDetectionService:
    """Advanced fraud detection and prevention service"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db = db
        self.alert_manager = alert_manager
        
        # Fraud detection rules and thresholds
        self.rules = {
            'max_transactions_per_hour': 5,
            'max_transactions_per_day': 20,
            'max_amount_per_transaction': 1000.0,
            'max_failed_attempts': 3,
            'min_time_between_transactions': 60,  # seconds
            'suspicious_email_patterns': [
                r'[0-9]{10,}@',  # Long numeric prefix
                r'test.*@',      # Test emails
                r'temp.*@',      # Temporary emails
                r'[a-z]{1,2}@',  # Very short usernames
            ],
            'blocked_email_domains': [
                '10minutemail.com',
                'tempmail.org',
                'guerrillamail.com',
                'mailinator.com',
                'throwaway.email'
            ],
            'velocity_thresholds': {
                'same_email_1_hour': 3,
                'same_email_24_hours': 10,
                'same_ip_1_hour': 10,
                'same_ip_24_hours': 50
            }
        }
        
        # Risk scoring weights
        self.risk_weights = {
            'velocity_violation': 0.3,
            'suspicious_email': 0.2,
            'failed_attempts': 0.25,
            'amount_anomaly': 0.15,
            'time_anomaly': 0.1,
            'blocked_domain': 0.5,
            'duplicate_attempt': 0.2,
            'pattern_match': 0.3
        }
    
    def analyze_transaction(self, transaction: Dict, metadata: Dict = None) -> FraudAnalysis:
        """Analyze transaction for fraud indicators"""
        try:
            indicators = []
            total_risk_score = 0.0
            
            # Extract transaction data
            transaction_id = transaction['transaction_id']
            email = transaction['email']
            amount = float(transaction.get('amount', 0) or 0)
            
            # Check various fraud indicators
            indicators.extend(self._check_email_fraud(email))
            indicators.extend(self._check_velocity_fraud(email, transaction_id))
            indicators.extend(self._check_amount_fraud(amount))
            indicators.extend(self._check_pattern_fraud(transaction))
            indicators.extend(self._check_timing_fraud(email))
            
            # If metadata is provided, check IP-based indicators
            if metadata:
                indicators.extend(self._check_ip_fraud(metadata))
            
            # Calculate total risk score
            for indicator in indicators:
                total_risk_score += indicator.weight
            
            # Normalize risk score (0-1 scale)
            risk_score = min(total_risk_score, 1.0)
            
            # Determine risk level
            risk_level = self._calculate_risk_level(risk_score)
            
            # Determine recommended action
            recommended_action = self._get_recommended_action(risk_level, indicators)
            
            # Check if transaction should be blocked
            is_blocked = self._should_block_transaction(risk_level, indicators)
            
            analysis = FraudAnalysis(
                transaction_id=transaction_id,
                email=email,
                risk_score=risk_score,
                risk_level=risk_level,
                indicators=indicators,
                recommended_action=recommended_action,
                timestamp=datetime.now(),
                is_blocked=is_blocked
            )
            
            # Log fraud analysis
            self._log_fraud_analysis(analysis)
            
            # Create alerts for high-risk transactions
            if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                self._create_fraud_alert(analysis)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing transaction for fraud: {str(e)}")
            return FraudAnalysis(
                transaction_id=transaction.get('transaction_id', 'unknown'),
                email=transaction.get('email', 'unknown'),
                risk_score=0.0,
                risk_level=RiskLevel.LOW,
                indicators=[],
                recommended_action="allow",
                timestamp=datetime.now(),
                is_blocked=False
            )
    
    def _check_email_fraud(self, email: str) -> List[FraudIndicator]:
        """Check for email-based fraud indicators"""
        indicators = []
        
        # Check for suspicious email patterns
        for pattern in self.rules['suspicious_email_patterns']:
            if re.search(pattern, email.lower()):
                indicators.append(FraudIndicator(
                    indicator_type="suspicious_email_pattern",
                    description=f"Email matches suspicious pattern: {pattern}",
                    weight=self.risk_weights['suspicious_email'],
                    value=email
                ))
        
        # Check for blocked domains
        domain = email.split('@')[1] if '@' in email else ''
        if domain.lower() in self.rules['blocked_email_domains']:
            indicators.append(FraudIndicator(
                indicator_type="blocked_domain",
                description=f"Email from blocked domain: {domain}",
                weight=self.risk_weights['blocked_domain'],
                value=domain
            ))
        
        # Check for disposable email services (basic check)
        disposable_indicators = ['temp', 'throw', 'fake', 'mail', 'trash']
        if any(indicator in domain.lower() for indicator in disposable_indicators):
            indicators.append(FraudIndicator(
                indicator_type="disposable_email",
                description=f"Potential disposable email service: {domain}",
                weight=self.risk_weights['suspicious_email'],
                value=domain
            ))
        
        return indicators
    
    def _check_velocity_fraud(self, email: str, transaction_id: str) -> List[FraudIndicator]:
        """Check for velocity-based fraud indicators"""
        indicators = []
        
        try:
            # Check transactions in the last hour
            recent_transactions_1h = self._get_recent_transactions(
                email=email, 
                hours=1, 
                exclude_transaction_id=transaction_id
            )
            
            if len(recent_transactions_1h) >= self.rules['velocity_thresholds']['same_email_1_hour']:
                indicators.append(FraudIndicator(
                    indicator_type="velocity_violation",
                    description=f"Too many transactions in 1 hour: {len(recent_transactions_1h)}",
                    weight=self.risk_weights['velocity_violation'],
                    value=str(len(recent_transactions_1h)),
                    threshold=str(self.rules['velocity_thresholds']['same_email_1_hour'])
                ))
            
            # Check transactions in the last 24 hours
            recent_transactions_24h = self._get_recent_transactions(
                email=email, 
                hours=24, 
                exclude_transaction_id=transaction_id
            )
            
            if len(recent_transactions_24h) >= self.rules['velocity_thresholds']['same_email_24_hours']:
                indicators.append(FraudIndicator(
                    indicator_type="velocity_violation",
                    description=f"Too many transactions in 24 hours: {len(recent_transactions_24h)}",
                    weight=self.risk_weights['velocity_violation'],
                    value=str(len(recent_transactions_24h)),
                    threshold=str(self.rules['velocity_thresholds']['same_email_24_hours'])
                ))
            
            # Check for rapid consecutive transactions
            if recent_transactions_1h:
                latest_transaction = max(recent_transactions_1h, key=lambda x: x['created_at'])
                time_diff = self._calculate_time_diff(latest_transaction['created_at'])
                
                if time_diff < self.rules['min_time_between_transactions']:
                    indicators.append(FraudIndicator(
                        indicator_type="timing_anomaly",
                        description=f"Transaction too soon after previous: {time_diff}s",
                        weight=self.risk_weights['time_anomaly'],
                        value=str(time_diff),
                        threshold=str(self.rules['min_time_between_transactions'])
                    ))
            
        except Exception as e:
            self.logger.error(f"Error checking velocity fraud: {str(e)}")
        
        return indicators
    
    def _check_amount_fraud(self, amount: float) -> List[FraudIndicator]:
        """Check for amount-based fraud indicators"""
        indicators = []
        
        # Check for unusually high amounts
        if amount > self.rules['max_amount_per_transaction']:
            indicators.append(FraudIndicator(
                indicator_type="amount_anomaly",
                description=f"Transaction amount exceeds threshold: ${amount}",
                weight=self.risk_weights['amount_anomaly'],
                value=str(amount),
                threshold=str(self.rules['max_amount_per_transaction'])
            ))
        
        # Check for suspicious round numbers (potential testing)
        if amount > 0 and amount == int(amount) and amount % 100 == 0:
            indicators.append(FraudIndicator(
                indicator_type="suspicious_amount",
                description=f"Suspicious round number amount: ${amount}",
                weight=self.risk_weights['pattern_match'] * 0.5,
                value=str(amount)
            ))
        
        return indicators
    
    def _check_pattern_fraud(self, transaction: Dict) -> List[FraudIndicator]:
        """Check for pattern-based fraud indicators"""
        indicators = []
        
        # Check for duplicate transaction attempts
        similar_transactions = self._find_similar_transactions(transaction)
        
        if len(similar_transactions) > 1:
            indicators.append(FraudIndicator(
                indicator_type="duplicate_attempt",
                description=f"Similar transaction attempts found: {len(similar_transactions)}",
                weight=self.risk_weights['duplicate_attempt'],
                value=str(len(similar_transactions))
            ))
        
        # Check for failed attempts from same email
        failed_attempts = self._get_failed_attempts(transaction['email'])
        
        if len(failed_attempts) >= self.rules['max_failed_attempts']:
            indicators.append(FraudIndicator(
                indicator_type="failed_attempts",
                description=f"Multiple failed attempts: {len(failed_attempts)}",
                weight=self.risk_weights['failed_attempts'],
                value=str(len(failed_attempts)),
                threshold=str(self.rules['max_failed_attempts'])
            ))
        
        return indicators
    
    def _check_timing_fraud(self, email: str) -> List[FraudIndicator]:
        """Check for timing-based fraud indicators"""
        indicators = []
        
        # Check for transactions at unusual hours (basic implementation)
        current_hour = datetime.now().hour
        
        # Flag transactions during very late/early hours (2-6 AM)
        if current_hour >= 2 and current_hour <= 6:
            indicators.append(FraudIndicator(
                indicator_type="timing_anomaly",
                description=f"Transaction during unusual hours: {current_hour}:00",
                weight=self.risk_weights['time_anomaly'] * 0.3,
                value=str(current_hour)
            ))
        
        return indicators
    
    def _check_ip_fraud(self, metadata: Dict) -> List[FraudIndicator]:
        """Check for IP-based fraud indicators"""
        indicators = []
        
        # Basic IP fraud checks (would need actual IP data)
        # This is a placeholder for IP-based fraud detection
        
        return indicators
    
    def _get_recent_transactions(self, email: str, hours: int = 24, 
                               exclude_transaction_id: str = None) -> List[Dict]:
        """Get recent transactions for an email"""
        try:
            start_time = datetime.now() - timedelta(hours=hours)
            
            with self.db.get_db_connection() as conn:
                query = '''
                    SELECT * FROM transactions 
                    WHERE email = ? AND created_at >= ?
                '''
                params = [email, start_time.isoformat()]
                
                if exclude_transaction_id:
                    query += ' AND transaction_id != ?'
                    params.append(exclude_transaction_id)
                
                query += ' ORDER BY created_at DESC'
                
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Error getting recent transactions: {str(e)}")
            return []
    
    def _find_similar_transactions(self, transaction: Dict) -> List[Dict]:
        """Find similar transactions (potential duplicates)"""
        try:
            with self.db.get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM transactions 
                    WHERE email = ? AND amount = ? AND status = 'pending'
                    AND created_at >= datetime('now', '-1 hour')
                    ORDER BY created_at DESC
                ''', (transaction['email'], transaction.get('amount')))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Error finding similar transactions: {str(e)}")
            return []
    
    def _get_failed_attempts(self, email: str) -> List[Dict]:
        """Get failed transaction attempts for an email"""
        try:
            start_time = datetime.now() - timedelta(hours=24)
            
            with self.db.get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM transactions 
                    WHERE email = ? AND status = 'failed' AND created_at >= ?
                    ORDER BY created_at DESC
                ''', (email, start_time.isoformat()))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Error getting failed attempts: {str(e)}")
            return []
    
    def _calculate_time_diff(self, timestamp_str: str) -> int:
        """Calculate time difference in seconds"""
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return int((datetime.now() - timestamp).total_seconds())
        except Exception as e:
            self.logger.error(f"Error calculating time diff: {str(e)}")
            return 0
    
    def _calculate_risk_level(self, risk_score: float) -> RiskLevel:
        """Calculate risk level based on score"""
        if risk_score >= 0.8:
            return RiskLevel.CRITICAL
        elif risk_score >= 0.6:
            return RiskLevel.HIGH
        elif risk_score >= 0.3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _get_recommended_action(self, risk_level: RiskLevel, 
                              indicators: List[FraudIndicator]) -> str:
        """Get recommended action based on risk level"""
        if risk_level == RiskLevel.CRITICAL:
            return "block"
        elif risk_level == RiskLevel.HIGH:
            return "manual_review"
        elif risk_level == RiskLevel.MEDIUM:
            return "monitor"
        else:
            return "allow"
    
    def _should_block_transaction(self, risk_level: RiskLevel, 
                                 indicators: List[FraudIndicator]) -> bool:
        """Determine if transaction should be blocked"""
        # Block critical risk transactions
        if risk_level == RiskLevel.CRITICAL:
            return True
        
        # Block if blocked domain is detected
        for indicator in indicators:
            if indicator.indicator_type == "blocked_domain":
                return True
        
        # Block if too many failed attempts
        for indicator in indicators:
            if (indicator.indicator_type == "failed_attempts" and 
                int(indicator.value) >= self.rules['max_failed_attempts']):
                return True
        
        return False
    
    def _log_fraud_analysis(self, analysis: FraudAnalysis):
        """Log fraud analysis result"""
        try:
            self.db.log_system_event(
                level="warning" if analysis.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] else "info",
                component="fraud_detection",
                message=f"Fraud analysis: {analysis.risk_level.value} risk for {analysis.email}",
                details={
                    'transaction_id': analysis.transaction_id,
                    'risk_score': analysis.risk_score,
                    'risk_level': analysis.risk_level.value,
                    'indicators': [asdict(indicator) for indicator in analysis.indicators],
                    'recommended_action': analysis.recommended_action,
                    'is_blocked': analysis.is_blocked
                },
                user_email=analysis.email,
                transaction_id=analysis.transaction_id
            )
            
        except Exception as e:
            self.logger.error(f"Error logging fraud analysis: {str(e)}")
    
    def _create_fraud_alert(self, analysis: FraudAnalysis):
        """Create fraud alert for high-risk transactions"""
        try:
            severity = "critical" if analysis.risk_level == RiskLevel.CRITICAL else "high"
            
            message = (f"High-risk transaction detected: {analysis.transaction_id} "
                      f"(Risk: {analysis.risk_level.value}, Score: {analysis.risk_score:.2f})")
            
            alert_id = self.db.create_alert(
                alert_type="fraud_detection",
                title=f"Fraud Alert: {severity.upper()}",
                message=message,
                component="fraud_detection"
            )
            
            self.logger.warning(f"Fraud alert created: {message}")
            
            # Send critical alerts immediately
            if severity == "critical":
                self.alert_manager.send_alert_email(alert_id)
                
        except Exception as e:
            self.logger.error(f"Error creating fraud alert: {str(e)}")
    
    def get_fraud_statistics(self, days: int = 30) -> Dict:
        """Get fraud detection statistics"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            with self.db.get_db_connection() as conn:
                # Get fraud-related logs
                cursor = conn.execute('''
                    SELECT 
                        COUNT(*) as total_analyses,
                        COUNT(CASE WHEN level = 'warning' THEN 1 END) as high_risk_count,
                        COUNT(CASE WHEN message LIKE '%blocked%' THEN 1 END) as blocked_count
                    FROM system_logs
                    WHERE component = 'fraud_detection' AND created_at >= ?
                ''', (start_date.isoformat(),))
                
                stats = dict(cursor.fetchone())
                
                # Get fraud alerts
                cursor = conn.execute('''
                    SELECT COUNT(*) as fraud_alerts
                    FROM admin_alerts
                    WHERE type = 'fraud_detection' AND created_at >= ?
                ''', (start_date.isoformat(),))
                
                alert_data = cursor.fetchone()
                stats['fraud_alerts'] = alert_data[0] if alert_data else 0
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Error getting fraud statistics: {str(e)}")
            return {}
    
    def get_fraud_patterns(self) -> Dict:
        """Get fraud pattern analysis"""
        try:
            with self.db.get_db_connection() as conn:
                # Get common fraud indicators
                cursor = conn.execute('''
                    SELECT 
                        component,
                        COUNT(*) as frequency,
                        message
                    FROM system_logs
                    WHERE component = 'fraud_detection' 
                    AND level = 'warning'
                    AND created_at >= datetime('now', '-7 days')
                    GROUP BY message
                    ORDER BY frequency DESC
                    LIMIT 10
                ''')
                
                patterns = [dict(row) for row in cursor.fetchall()]
                
                return {'common_patterns': patterns}
                
        except Exception as e:
            self.logger.error(f"Error getting fraud patterns: {str(e)}")
            return {}
    
    def update_fraud_rules(self, new_rules: Dict):
        """Update fraud detection rules"""
        try:
            # Validate new rules
            for key, value in new_rules.items():
                if key in self.rules:
                    self.rules[key] = value
                    self.logger.info(f"Updated fraud rule: {key} = {value}")
            
            # Log the update
            self.db.log_system_event(
                level="info",
                component="fraud_detection",
                message="Fraud detection rules updated",
                details=new_rules
            )
            
        except Exception as e:
            self.logger.error(f"Error updating fraud rules: {str(e)}")

# Global fraud detection service instance
fraud_detector = FraudDetectionService()