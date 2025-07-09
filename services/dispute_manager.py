#!/usr/bin/env python3
"""
Transaction Dispute Management System for VectorCraft
Handle disputes, chargebacks, and refunds
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
from database import db
from services.monitoring.alert_manager import alert_manager
from services.email_service import email_service

class DisputeType(Enum):
    CHARGEBACK = "chargeback"
    REFUND_REQUEST = "refund_request"
    BILLING_INQUIRY = "billing_inquiry"
    UNAUTHORIZED_TRANSACTION = "unauthorized_transaction"
    ITEM_NOT_RECEIVED = "item_not_received"
    ITEM_NOT_AS_DESCRIBED = "item_not_as_described"
    DUPLICATE_TRANSACTION = "duplicate_transaction"
    PROCESSING_ERROR = "processing_error"

class DisputeStatus(Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    PENDING_RESPONSE = "pending_response"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"
    LOST = "lost"
    WON = "won"

class DisputePriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class DisputeCase:
    """Dispute case data structure"""
    case_id: str
    transaction_id: str
    customer_email: str
    dispute_type: DisputeType
    status: DisputeStatus
    priority: DisputePriority
    amount: float
    currency: str
    description: str
    customer_message: str
    created_at: datetime
    due_date: Optional[datetime]
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
    assigned_to: Optional[str]
    paypal_case_id: Optional[str]
    evidence_files: List[str]
    communication_log: List[Dict]

@dataclass
class DisputeMetrics:
    """Dispute metrics for reporting"""
    total_disputes: int
    open_disputes: int
    resolved_disputes: int
    disputed_amount: float
    resolution_rate: float
    avg_resolution_time: float
    dispute_rate: float
    chargeback_rate: float

class DisputeManager:
    """Advanced dispute management system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db = db
        self.alert_manager = alert_manager
        self.email_service = email_service
        
        # Dispute handling configuration
        self.config = {
            'auto_response_enabled': True,
            'escalation_threshold_hours': 48,
            'max_resolution_days': 14,
            'priority_thresholds': {
                'urgent': 500.0,    # Amount > $500
                'high': 100.0,      # Amount > $100
                'medium': 50.0,     # Amount > $50
                'low': 0.0          # Amount <= $50
            },
            'auto_refund_threshold': 25.0,  # Auto-approve refunds <= $25
            'evidence_requirements': {
                'chargeback': ['transaction_receipt', 'service_delivery_proof'],
                'refund_request': ['transaction_receipt', 'refund_policy'],
                'unauthorized_transaction': ['transaction_receipt', 'security_logs']
            }
        }
        
        # Initialize dispute tracking table
        self._init_dispute_tables()
    
    def _init_dispute_tables(self):
        """Initialize dispute tracking tables"""
        try:
            with self.db.get_db_connection() as conn:
                # Dispute cases table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS dispute_cases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        case_id TEXT UNIQUE NOT NULL,
                        transaction_id TEXT NOT NULL,
                        customer_email TEXT NOT NULL,
                        dispute_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        priority TEXT NOT NULL,
                        amount DECIMAL(10,2) NOT NULL,
                        currency TEXT DEFAULT 'USD',
                        description TEXT,
                        customer_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        due_date TIMESTAMP,
                        resolved_at TIMESTAMP,
                        resolution_notes TEXT,
                        assigned_to TEXT,
                        paypal_case_id TEXT,
                        evidence_files TEXT,
                        communication_log TEXT,
                        FOREIGN KEY (transaction_id) REFERENCES transactions (transaction_id)
                    )
                ''')
                
                # Dispute actions table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS dispute_actions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        case_id TEXT NOT NULL,
                        action_type TEXT NOT NULL,
                        actor TEXT NOT NULL,
                        description TEXT,
                        details TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (case_id) REFERENCES dispute_cases (case_id)
                    )
                ''')
                
                # Dispute evidence table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS dispute_evidence (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        case_id TEXT NOT NULL,
                        evidence_type TEXT NOT NULL,
                        file_path TEXT,
                        description TEXT,
                        uploaded_by TEXT,
                        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (case_id) REFERENCES dispute_cases (case_id)
                    )
                ''')
                
                # Create indexes
                conn.execute('CREATE INDEX IF NOT EXISTS idx_dispute_cases_status ON dispute_cases(status)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_dispute_cases_priority ON dispute_cases(priority)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_dispute_cases_created_at ON dispute_cases(created_at)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_dispute_actions_case_id ON dispute_actions(case_id)')
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error initializing dispute tables: {str(e)}")
    
    def create_dispute(self, transaction_id: str, dispute_type: DisputeType, 
                      customer_message: str, metadata: Dict = None) -> str:
        """Create a new dispute case"""
        try:
            # Get transaction details
            transaction = self.db.get_transaction(transaction_id)
            if not transaction:
                raise ValueError(f"Transaction not found: {transaction_id}")
            
            # Generate case ID
            case_id = f"DISP_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{transaction_id[-6:]}"
            
            # Calculate priority
            priority = self._calculate_dispute_priority(float(transaction['amount'] or 0), dispute_type)
            
            # Calculate due date
            due_date = self._calculate_due_date(dispute_type, priority)
            
            # Create dispute case
            with self.db.get_db_connection() as conn:
                conn.execute('''
                    INSERT INTO dispute_cases (
                        case_id, transaction_id, customer_email, dispute_type, status, priority,
                        amount, currency, description, customer_message, due_date, evidence_files,
                        communication_log
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    case_id,
                    transaction_id,
                    transaction['email'],
                    dispute_type.value,
                    DisputeStatus.OPEN.value,
                    priority.value,
                    transaction['amount'],
                    transaction.get('currency', 'USD'),
                    f"Customer dispute: {dispute_type.value}",
                    customer_message,
                    due_date.isoformat() if due_date else None,
                    json.dumps([]),
                    json.dumps([])
                ))
                
                conn.commit()
            
            # Log dispute creation
            self._log_dispute_action(
                case_id,
                "dispute_created",
                "system",
                f"New dispute case created: {dispute_type.value}",
                {
                    'transaction_id': transaction_id,
                    'customer_email': transaction['email'],
                    'amount': transaction['amount'],
                    'priority': priority.value
                }
            )
            
            # Send auto-response if enabled
            if self.config['auto_response_enabled']:
                self._send_auto_response(case_id)
            
            # Create alert for high-priority disputes
            if priority in [DisputePriority.HIGH, DisputePriority.URGENT]:
                self._create_dispute_alert(case_id, dispute_type, priority)
            
            # Check for auto-resolution
            if self._should_auto_resolve(dispute_type, float(transaction['amount'] or 0)):
                self._auto_resolve_dispute(case_id, dispute_type)
            
            self.logger.info(f"Dispute case created: {case_id}")
            return case_id
            
        except Exception as e:
            self.logger.error(f"Error creating dispute: {str(e)}")
            raise
    
    def _calculate_dispute_priority(self, amount: float, dispute_type: DisputeType) -> DisputePriority:
        """Calculate dispute priority based on amount and type"""
        # Higher priority for certain dispute types
        if dispute_type in [DisputeType.CHARGEBACK, DisputeType.UNAUTHORIZED_TRANSACTION]:
            if amount >= self.config['priority_thresholds']['urgent']:
                return DisputePriority.URGENT
            elif amount >= self.config['priority_thresholds']['high']:
                return DisputePriority.HIGH
            else:
                return DisputePriority.MEDIUM
        
        # Standard priority calculation
        if amount >= self.config['priority_thresholds']['urgent']:
            return DisputePriority.URGENT
        elif amount >= self.config['priority_thresholds']['high']:
            return DisputePriority.HIGH
        elif amount >= self.config['priority_thresholds']['medium']:
            return DisputePriority.MEDIUM
        else:
            return DisputePriority.LOW
    
    def _calculate_due_date(self, dispute_type: DisputeType, priority: DisputePriority) -> Optional[datetime]:
        """Calculate dispute due date"""
        if dispute_type == DisputeType.CHARGEBACK:
            # Chargebacks have strict timelines
            return datetime.now() + timedelta(days=7)
        elif priority == DisputePriority.URGENT:
            return datetime.now() + timedelta(days=1)
        elif priority == DisputePriority.HIGH:
            return datetime.now() + timedelta(days=3)
        else:
            return datetime.now() + timedelta(days=self.config['max_resolution_days'])
    
    def _should_auto_resolve(self, dispute_type: DisputeType, amount: float) -> bool:
        """Check if dispute should be auto-resolved"""
        if dispute_type == DisputeType.REFUND_REQUEST and amount <= self.config['auto_refund_threshold']:
            return True
        return False
    
    def _auto_resolve_dispute(self, case_id: str, dispute_type: DisputeType):
        """Auto-resolve low-value disputes"""
        try:
            resolution_notes = f"Auto-resolved {dispute_type.value} for low amount"
            
            self.update_dispute_status(
                case_id,
                DisputeStatus.RESOLVED,
                resolution_notes,
                "system"
            )
            
            # Process refund if needed
            if dispute_type == DisputeType.REFUND_REQUEST:
                self._process_refund(case_id)
            
        except Exception as e:
            self.logger.error(f"Error auto-resolving dispute {case_id}: {str(e)}")
    
    def update_dispute_status(self, case_id: str, status: DisputeStatus, 
                            notes: str = None, updated_by: str = None):
        """Update dispute status"""
        try:
            with self.db.get_db_connection() as conn:
                update_fields = ['status = ?']
                params = [status.value]
                
                if notes:
                    update_fields.append('resolution_notes = ?')
                    params.append(notes)
                
                if status in [DisputeStatus.RESOLVED, DisputeStatus.CLOSED, DisputeStatus.LOST, DisputeStatus.WON]:
                    update_fields.append('resolved_at = CURRENT_TIMESTAMP')
                
                params.append(case_id)
                
                conn.execute(f'''
                    UPDATE dispute_cases 
                    SET {', '.join(update_fields)}
                    WHERE case_id = ?
                ''', params)
                
                conn.commit()
            
            # Log the action
            self._log_dispute_action(
                case_id,
                "status_updated",
                updated_by or "system",
                f"Status updated to {status.value}",
                {'notes': notes}
            )
            
            # Send status update email
            self._send_status_update_email(case_id, status)
            
        except Exception as e:
            self.logger.error(f"Error updating dispute status: {str(e)}")
            raise
    
    def add_dispute_evidence(self, case_id: str, evidence_type: str, 
                           file_path: str, description: str, uploaded_by: str):
        """Add evidence to dispute case"""
        try:
            with self.db.get_db_connection() as conn:
                conn.execute('''
                    INSERT INTO dispute_evidence (
                        case_id, evidence_type, file_path, description, uploaded_by
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (case_id, evidence_type, file_path, description, uploaded_by))
                
                conn.commit()
            
            # Update evidence files list in main case
            self._update_evidence_list(case_id)
            
            # Log the action
            self._log_dispute_action(
                case_id,
                "evidence_added",
                uploaded_by,
                f"Added evidence: {evidence_type}",
                {'file_path': file_path, 'description': description}
            )
            
        except Exception as e:
            self.logger.error(f"Error adding dispute evidence: {str(e)}")
            raise
    
    def _update_evidence_list(self, case_id: str):
        """Update evidence files list in dispute case"""
        try:
            with self.db.get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT evidence_type, file_path, description
                    FROM dispute_evidence
                    WHERE case_id = ?
                    ORDER BY uploaded_at
                ''', (case_id,))
                
                evidence_files = [dict(row) for row in cursor.fetchall()]
                
                conn.execute('''
                    UPDATE dispute_cases
                    SET evidence_files = ?
                    WHERE case_id = ?
                ''', (json.dumps(evidence_files), case_id))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error updating evidence list: {str(e)}")
    
    def _log_dispute_action(self, case_id: str, action_type: str, actor: str, 
                           description: str, details: Dict = None):
        """Log dispute action"""
        try:
            with self.db.get_db_connection() as conn:
                conn.execute('''
                    INSERT INTO dispute_actions (
                        case_id, action_type, actor, description, details
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (case_id, action_type, actor, description, json.dumps(details) if details else None))
                
                conn.commit()
            
            # Update communication log
            self._update_communication_log(case_id)
            
        except Exception as e:
            self.logger.error(f"Error logging dispute action: {str(e)}")
    
    def _update_communication_log(self, case_id: str):
        """Update communication log in dispute case"""
        try:
            with self.db.get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT action_type, actor, description, details, created_at
                    FROM dispute_actions
                    WHERE case_id = ?
                    ORDER BY created_at DESC
                    LIMIT 20
                ''', (case_id,))
                
                actions = [dict(row) for row in cursor.fetchall()]
                
                conn.execute('''
                    UPDATE dispute_cases
                    SET communication_log = ?
                    WHERE case_id = ?
                ''', (json.dumps(actions), case_id))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error updating communication log: {str(e)}")
    
    def _send_auto_response(self, case_id: str):
        """Send auto-response to customer"""
        try:
            dispute = self.get_dispute_details(case_id)
            if not dispute:
                return
            
            # Send acknowledgment email
            self.email_service.send_email(
                to_email=dispute['customer_email'],
                subject=f"Dispute Case Acknowledgment - {case_id}",
                body=f"""
                Dear Customer,
                
                We have received your dispute case regarding transaction {dispute['transaction_id']}.
                
                Case ID: {case_id}
                Dispute Type: {dispute['dispute_type']}
                Amount: ${dispute['amount']} {dispute['currency']}
                
                We are reviewing your case and will respond within 2 business days.
                
                Best regards,
                VectorCraft Support Team
                """,
                email_type="dispute_acknowledgment"
            )
            
            # Log communication
            self._log_dispute_action(
                case_id,
                "auto_response_sent",
                "system",
                "Auto-response acknowledgment sent to customer"
            )
            
        except Exception as e:
            self.logger.error(f"Error sending auto-response: {str(e)}")
    
    def _send_status_update_email(self, case_id: str, status: DisputeStatus):
        """Send status update email to customer"""
        try:
            dispute = self.get_dispute_details(case_id)
            if not dispute:
                return
            
            status_messages = {
                DisputeStatus.INVESTIGATING: "We are currently investigating your dispute case.",
                DisputeStatus.RESOLVED: "Your dispute case has been resolved.",
                DisputeStatus.CLOSED: "Your dispute case has been closed.",
                DisputeStatus.ESCALATED: "Your dispute case has been escalated to our senior team."
            }
            
            message = status_messages.get(status, f"Your dispute status has been updated to {status.value}")
            
            self.email_service.send_email(
                to_email=dispute['customer_email'],
                subject=f"Dispute Status Update - {case_id}",
                body=f"""
                Dear Customer,
                
                Your dispute case {case_id} has been updated.
                
                Status: {status.value}
                
                {message}
                
                If you have any questions, please contact our support team.
                
                Best regards,
                VectorCraft Support Team
                """,
                email_type="dispute_status_update"
            )
            
        except Exception as e:
            self.logger.error(f"Error sending status update email: {str(e)}")
    
    def _create_dispute_alert(self, case_id: str, dispute_type: DisputeType, priority: DisputePriority):
        """Create alert for high-priority disputes"""
        try:
            severity = "critical" if priority == DisputePriority.URGENT else "high"
            
            message = f"High-priority dispute case created: {case_id} ({dispute_type.value})"
            
            alert_id = self.db.create_alert(
                alert_type="dispute_management",
                title=f"Dispute Alert: {severity.upper()}",
                message=message,
                component="dispute_management"
            )
            
            # Send immediate notification for urgent cases
            if priority == DisputePriority.URGENT:
                self.alert_manager.send_alert_email(alert_id)
            
        except Exception as e:
            self.logger.error(f"Error creating dispute alert: {str(e)}")
    
    def _process_refund(self, case_id: str):
        """Process refund for dispute case"""
        try:
            dispute = self.get_dispute_details(case_id)
            if not dispute:
                return
            
            # Update transaction status
            self.db.update_transaction(
                dispute['transaction_id'],
                status='refunded',
                metadata={'refund_case_id': case_id}
            )
            
            # Log refund processing
            self._log_dispute_action(
                case_id,
                "refund_processed",
                "system",
                f"Refund processed for ${dispute['amount']} {dispute['currency']}"
            )
            
        except Exception as e:
            self.logger.error(f"Error processing refund: {str(e)}")
    
    def get_dispute_details(self, case_id: str) -> Optional[Dict]:
        """Get detailed dispute information"""
        try:
            with self.db.get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM dispute_cases WHERE case_id = ?
                ''', (case_id,))
                
                dispute = cursor.fetchone()
                if not dispute:
                    return None
                
                dispute_dict = dict(dispute)
                
                # Parse JSON fields
                dispute_dict['evidence_files'] = json.loads(dispute_dict['evidence_files'] or '[]')
                dispute_dict['communication_log'] = json.loads(dispute_dict['communication_log'] or '[]')
                
                return dispute_dict
                
        except Exception as e:
            self.logger.error(f"Error getting dispute details: {str(e)}")
            return None
    
    def get_dispute_metrics(self, days: int = 30) -> DisputeMetrics:
        """Get dispute metrics for reporting"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            with self.db.get_db_connection() as conn:
                # Get dispute statistics
                cursor = conn.execute('''
                    SELECT 
                        COUNT(*) as total_disputes,
                        COUNT(CASE WHEN status IN ('open', 'investigating', 'pending_response', 'escalated') THEN 1 END) as open_disputes,
                        COUNT(CASE WHEN status IN ('resolved', 'closed', 'won') THEN 1 END) as resolved_disputes,
                        SUM(amount) as disputed_amount,
                        AVG(CASE 
                            WHEN resolved_at IS NOT NULL 
                            THEN (julianday(resolved_at) - julianday(created_at)) * 24 
                        END) as avg_resolution_time
                    FROM dispute_cases
                    WHERE created_at >= ?
                ''', (start_date.isoformat(),))
                
                data = dict(cursor.fetchone())
                
                # Get transaction statistics for rates
                cursor = conn.execute('''
                    SELECT 
                        COUNT(*) as total_transactions,
                        SUM(amount) as total_amount
                    FROM transactions
                    WHERE created_at >= ? AND status = 'completed'
                ''', (start_date.isoformat(),))
                
                transaction_data = dict(cursor.fetchone())
                
                # Calculate rates
                total_disputes = data['total_disputes'] or 0
                total_transactions = transaction_data['total_transactions'] or 0
                
                dispute_rate = (total_disputes / max(total_transactions, 1)) * 100
                resolution_rate = ((data['resolved_disputes'] or 0) / max(total_disputes, 1)) * 100
                
                # Get chargeback rate
                cursor = conn.execute('''
                    SELECT COUNT(*) as chargebacks
                    FROM dispute_cases
                    WHERE dispute_type = 'chargeback' AND created_at >= ?
                ''', (start_date.isoformat(),))
                
                chargeback_data = cursor.fetchone()
                chargeback_rate = ((chargeback_data[0] or 0) / max(total_transactions, 1)) * 100
                
                return DisputeMetrics(
                    total_disputes=total_disputes,
                    open_disputes=data['open_disputes'] or 0,
                    resolved_disputes=data['resolved_disputes'] or 0,
                    disputed_amount=float(data['disputed_amount'] or 0),
                    resolution_rate=resolution_rate,
                    avg_resolution_time=float(data['avg_resolution_time'] or 0),
                    dispute_rate=dispute_rate,
                    chargeback_rate=chargeback_rate
                )
                
        except Exception as e:
            self.logger.error(f"Error getting dispute metrics: {str(e)}")
            return DisputeMetrics(
                total_disputes=0,
                open_disputes=0,
                resolved_disputes=0,
                disputed_amount=0.0,
                resolution_rate=0.0,
                avg_resolution_time=0.0,
                dispute_rate=0.0,
                chargeback_rate=0.0
            )
    
    def get_open_disputes(self, limit: int = 50) -> List[Dict]:
        """Get open dispute cases"""
        try:
            with self.db.get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM dispute_cases
                    WHERE status IN ('open', 'investigating', 'pending_response', 'escalated')
                    ORDER BY priority DESC, created_at ASC
                    LIMIT ?
                ''', (limit,))
                
                disputes = [dict(row) for row in cursor.fetchall()]
                
                # Parse JSON fields
                for dispute in disputes:
                    dispute['evidence_files'] = json.loads(dispute['evidence_files'] or '[]')
                    dispute['communication_log'] = json.loads(dispute['communication_log'] or '[]')
                
                return disputes
                
        except Exception as e:
            self.logger.error(f"Error getting open disputes: {str(e)}")
            return []

# Global dispute manager instance
dispute_manager = DisputeManager()