#!/usr/bin/env python3
"""
Transaction Analytics Service for VectorCraft
Advanced transaction analysis and reporting system
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
from database import db

class TransactionStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    DISPUTED = "disputed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"

@dataclass
class TransactionAnalytics:
    """Transaction analytics data structure"""
    total_transactions: int
    total_revenue: float
    success_rate: float
    avg_transaction_value: float
    completion_rate: float
    dispute_rate: float
    refund_rate: float
    hourly_trends: List[Dict]
    daily_trends: List[Dict]
    geographical_data: List[Dict]
    payment_methods: List[Dict]

@dataclass
class FraudIndicator:
    """Fraud detection indicator"""
    transaction_id: str
    risk_score: float
    risk_level: str
    indicators: List[str]
    timestamp: datetime

class TransactionAnalyticsService:
    """Advanced transaction analytics and reporting service"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db = db
        
    def get_transaction_analytics(self, 
                                 start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None,
                                 email_filter: Optional[str] = None) -> TransactionAnalytics:
        """Get comprehensive transaction analytics"""
        try:
            # Default to last 30 days if no date range specified
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)
            if not end_date:
                end_date = datetime.now()
            
            # Get base transaction data
            transactions = self._get_transactions_in_range(start_date, end_date, email_filter)
            
            # Calculate basic metrics
            total_transactions = len(transactions)
            completed_transactions = [t for t in transactions if t['status'] == 'completed']
            failed_transactions = [t for t in transactions if t['status'] == 'failed']
            disputed_transactions = [t for t in transactions if t['status'] == 'disputed']
            refunded_transactions = [t for t in transactions if t['status'] == 'refunded']
            
            total_revenue = sum(float(t['amount'] or 0) for t in completed_transactions)
            success_rate = len(completed_transactions) / max(total_transactions, 1) * 100
            avg_transaction_value = total_revenue / max(len(completed_transactions), 1)
            completion_rate = len(completed_transactions) / max(total_transactions, 1) * 100
            dispute_rate = len(disputed_transactions) / max(total_transactions, 1) * 100
            refund_rate = len(refunded_transactions) / max(total_transactions, 1) * 100
            
            # Get trend data
            hourly_trends = self._get_hourly_trends(transactions)
            daily_trends = self._get_daily_trends(transactions)
            
            # Get geographical data (simulated for now)
            geographical_data = self._get_geographical_data(transactions)
            
            # Get payment method data
            payment_methods = self._get_payment_method_data(transactions)
            
            return TransactionAnalytics(
                total_transactions=total_transactions,
                total_revenue=total_revenue,
                success_rate=success_rate,
                avg_transaction_value=avg_transaction_value,
                completion_rate=completion_rate,
                dispute_rate=dispute_rate,
                refund_rate=refund_rate,
                hourly_trends=hourly_trends,
                daily_trends=daily_trends,
                geographical_data=geographical_data,
                payment_methods=payment_methods
            )
            
        except Exception as e:
            self.logger.error(f"Error generating transaction analytics: {str(e)}")
            return TransactionAnalytics(
                total_transactions=0,
                total_revenue=0.0,
                success_rate=0.0,
                avg_transaction_value=0.0,
                completion_rate=0.0,
                dispute_rate=0.0,
                refund_rate=0.0,
                hourly_trends=[],
                daily_trends=[],
                geographical_data=[],
                payment_methods=[]
            )
    
    def _get_transactions_in_range(self, start_date: datetime, end_date: datetime, 
                                  email_filter: Optional[str] = None) -> List[Dict]:
        """Get transactions within date range"""
        try:
            with self.db.get_db_connection() as conn:
                query = '''
                    SELECT * FROM transactions 
                    WHERE created_at >= ? AND created_at <= ?
                '''
                params = [start_date.isoformat(), end_date.isoformat()]
                
                if email_filter:
                    query += ' AND email LIKE ?'
                    params.append(f'%{email_filter}%')
                
                query += ' ORDER BY created_at DESC'
                
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Error fetching transactions: {str(e)}")
            return []
    
    def _get_hourly_trends(self, transactions: List[Dict]) -> List[Dict]:
        """Get hourly transaction trends"""
        hourly_data = {}
        
        for transaction in transactions:
            try:
                created_at = datetime.fromisoformat(transaction['created_at'].replace('Z', '+00:00'))
                hour_key = created_at.strftime('%Y-%m-%d %H:00')
                
                if hour_key not in hourly_data:
                    hourly_data[hour_key] = {
                        'timestamp': hour_key,
                        'total_transactions': 0,
                        'completed_transactions': 0,
                        'failed_transactions': 0,
                        'total_revenue': 0.0,
                        'avg_response_time': 0.0
                    }
                
                hourly_data[hour_key]['total_transactions'] += 1
                
                if transaction['status'] == 'completed':
                    hourly_data[hour_key]['completed_transactions'] += 1
                    hourly_data[hour_key]['total_revenue'] += float(transaction['amount'] or 0)
                elif transaction['status'] == 'failed':
                    hourly_data[hour_key]['failed_transactions'] += 1
                    
            except Exception as e:
                self.logger.error(f"Error processing hourly trend for transaction {transaction.get('id')}: {str(e)}")
                continue
        
        # Sort by timestamp and return as list
        return sorted(hourly_data.values(), key=lambda x: x['timestamp'])
    
    def _get_daily_trends(self, transactions: List[Dict]) -> List[Dict]:
        """Get daily transaction trends"""
        daily_data = {}
        
        for transaction in transactions:
            try:
                created_at = datetime.fromisoformat(transaction['created_at'].replace('Z', '+00:00'))
                day_key = created_at.strftime('%Y-%m-%d')
                
                if day_key not in daily_data:
                    daily_data[day_key] = {
                        'date': day_key,
                        'total_transactions': 0,
                        'completed_transactions': 0,
                        'failed_transactions': 0,
                        'total_revenue': 0.0,
                        'unique_customers': set(),
                        'avg_transaction_value': 0.0
                    }
                
                daily_data[day_key]['total_transactions'] += 1
                daily_data[day_key]['unique_customers'].add(transaction['email'])
                
                if transaction['status'] == 'completed':
                    daily_data[day_key]['completed_transactions'] += 1
                    daily_data[day_key]['total_revenue'] += float(transaction['amount'] or 0)
                elif transaction['status'] == 'failed':
                    daily_data[day_key]['failed_transactions'] += 1
                    
            except Exception as e:
                self.logger.error(f"Error processing daily trend for transaction {transaction.get('id')}: {str(e)}")
                continue
        
        # Process final calculations and convert set to count
        for day_data in daily_data.values():
            day_data['unique_customers'] = len(day_data['unique_customers'])
            if day_data['completed_transactions'] > 0:
                day_data['avg_transaction_value'] = day_data['total_revenue'] / day_data['completed_transactions']
            else:
                day_data['avg_transaction_value'] = 0.0
        
        return sorted(daily_data.values(), key=lambda x: x['date'])
    
    def _get_geographical_data(self, transactions: List[Dict]) -> List[Dict]:
        """Get geographical transaction data (simulated)"""
        # In a real implementation, this would parse IP addresses or billing info
        geographical_data = [
            {'country': 'United States', 'transactions': 0, 'revenue': 0.0},
            {'country': 'Canada', 'transactions': 0, 'revenue': 0.0},
            {'country': 'United Kingdom', 'transactions': 0, 'revenue': 0.0},
            {'country': 'Australia', 'transactions': 0, 'revenue': 0.0},
            {'country': 'Germany', 'transactions': 0, 'revenue': 0.0},
            {'country': 'India', 'transactions': 0, 'revenue': 0.0},
            {'country': 'Other', 'transactions': 0, 'revenue': 0.0}
        ]
        
        # Simple distribution simulation based on email domains
        for transaction in transactions:
            if transaction['status'] == 'completed':
                email = transaction['email']
                amount = float(transaction['amount'] or 0)
                
                if any(domain in email for domain in ['.com', '.org', '.net']):
                    geographical_data[0]['transactions'] += 1
                    geographical_data[0]['revenue'] += amount
                elif '.ca' in email:
                    geographical_data[1]['transactions'] += 1
                    geographical_data[1]['revenue'] += amount
                elif '.uk' in email or '.co.uk' in email:
                    geographical_data[2]['transactions'] += 1
                    geographical_data[2]['revenue'] += amount
                elif '.au' in email:
                    geographical_data[3]['transactions'] += 1
                    geographical_data[3]['revenue'] += amount
                elif '.de' in email:
                    geographical_data[4]['transactions'] += 1
                    geographical_data[4]['revenue'] += amount
                elif '.in' in email:
                    geographical_data[5]['transactions'] += 1
                    geographical_data[5]['revenue'] += amount
                else:
                    geographical_data[6]['transactions'] += 1
                    geographical_data[6]['revenue'] += amount
        
        return [item for item in geographical_data if item['transactions'] > 0]
    
    def _get_payment_method_data(self, transactions: List[Dict]) -> List[Dict]:
        """Get payment method distribution"""
        payment_methods = {
            'PayPal': {'transactions': 0, 'revenue': 0.0},
            'Credit Card': {'transactions': 0, 'revenue': 0.0},
            'Bank Transfer': {'transactions': 0, 'revenue': 0.0},
            'Other': {'transactions': 0, 'revenue': 0.0}
        }
        
        for transaction in transactions:
            if transaction['status'] == 'completed':
                amount = float(transaction['amount'] or 0)
                
                # Determine payment method (for now, assume all are PayPal)
                if transaction['paypal_order_id']:
                    payment_methods['PayPal']['transactions'] += 1
                    payment_methods['PayPal']['revenue'] += amount
                else:
                    payment_methods['Other']['transactions'] += 1
                    payment_methods['Other']['revenue'] += amount
        
        return [
            {'method': method, **data} 
            for method, data in payment_methods.items() 
            if data['transactions'] > 0
        ]
    
    def get_transaction_details(self, transaction_id: str) -> Dict:
        """Get detailed transaction information"""
        try:
            transaction = self.db.get_transaction(transaction_id)
            if not transaction:
                return {'error': 'Transaction not found'}
            
            # Get additional details
            details = {
                'basic_info': transaction,
                'timeline': self._get_transaction_timeline(transaction_id),
                'fraud_score': self._calculate_fraud_score(transaction),
                'related_transactions': self._get_related_transactions(transaction['email'])
            }
            
            return details
            
        except Exception as e:
            self.logger.error(f"Error getting transaction details: {str(e)}")
            return {'error': str(e)}
    
    def _get_transaction_timeline(self, transaction_id: str) -> List[Dict]:
        """Get transaction timeline events"""
        # This would typically pull from a more detailed audit log
        # For now, return basic timeline based on transaction data
        transaction = self.db.get_transaction(transaction_id)
        if not transaction:
            return []
        
        timeline = []
        
        # Transaction created
        timeline.append({
            'timestamp': transaction['created_at'],
            'event': 'Transaction Created',
            'description': f'Transaction {transaction_id} initiated',
            'status': 'info'
        })
        
        # PayPal order created
        if transaction['paypal_order_id']:
            timeline.append({
                'timestamp': transaction['created_at'],
                'event': 'PayPal Order Created',
                'description': f'PayPal order {transaction["paypal_order_id"]} created',
                'status': 'info'
            })
        
        # User creation
        if transaction['user_created']:
            timeline.append({
                'timestamp': transaction['created_at'],
                'event': 'User Account Created',
                'description': f'User account created for {transaction["email"]}',
                'status': 'success'
            })
        
        # Email sent
        if transaction['email_sent']:
            timeline.append({
                'timestamp': transaction['created_at'],
                'event': 'Credentials Email Sent',
                'description': f'Login credentials sent to {transaction["email"]}',
                'status': 'success'
            })
        
        # Transaction completed
        if transaction['status'] == 'completed' and transaction['completed_at']:
            timeline.append({
                'timestamp': transaction['completed_at'],
                'event': 'Transaction Completed',
                'description': f'Payment of ${transaction["amount"]} completed successfully',
                'status': 'success'
            })
        elif transaction['status'] == 'failed':
            timeline.append({
                'timestamp': transaction['created_at'],
                'event': 'Transaction Failed',
                'description': transaction['error_message'] or 'Transaction failed',
                'status': 'error'
            })
        
        return sorted(timeline, key=lambda x: x['timestamp'])
    
    def _calculate_fraud_score(self, transaction: Dict) -> Dict:
        """Calculate fraud risk score for transaction"""
        risk_score = 0.0
        risk_factors = []
        
        # Basic fraud indicators
        if transaction['amount'] and float(transaction['amount']) > 100:
            risk_score += 0.1
            risk_factors.append('High transaction amount')
        
        if transaction['status'] == 'failed':
            risk_score += 0.3
            risk_factors.append('Failed transaction')
        
        # Check for rapid transactions from same email
        related_transactions = self._get_related_transactions(transaction['email'], hours=1)
        if len(related_transactions) > 3:
            risk_score += 0.4
            risk_factors.append('Multiple rapid transactions')
        
        # Determine risk level
        if risk_score <= 0.3:
            risk_level = 'Low'
        elif risk_score <= 0.6:
            risk_level = 'Medium'
        else:
            risk_level = 'High'
        
        return {
            'risk_score': min(risk_score, 1.0),
            'risk_level': risk_level,
            'risk_factors': risk_factors
        }
    
    def _get_related_transactions(self, email: str, hours: int = 24) -> List[Dict]:
        """Get related transactions for an email"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            with self.db.get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM transactions 
                    WHERE email = ? AND created_at >= ?
                    ORDER BY created_at DESC
                ''', (email, cutoff_time.isoformat()))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Error getting related transactions: {str(e)}")
            return []
    
    def get_revenue_analytics(self, days: int = 30) -> Dict:
        """Get revenue analytics for specified period"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            end_date = datetime.now()
            
            with self.db.get_db_connection() as conn:
                # Get revenue by day
                cursor = conn.execute('''
                    SELECT 
                        DATE(created_at) as date,
                        COUNT(*) as transaction_count,
                        SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) as daily_revenue,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_transactions,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_transactions
                    FROM transactions 
                    WHERE created_at >= ? AND created_at <= ?
                    GROUP BY DATE(created_at)
                    ORDER BY date
                ''', (start_date.isoformat(), end_date.isoformat()))
                
                daily_revenue = [dict(row) for row in cursor.fetchall()]
                
                # Get total metrics
                cursor = conn.execute('''
                    SELECT 
                        COUNT(*) as total_transactions,
                        SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) as total_revenue,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_transactions,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_transactions,
                        AVG(CASE WHEN status = 'completed' THEN amount END) as avg_transaction_value
                    FROM transactions 
                    WHERE created_at >= ? AND created_at <= ?
                ''', (start_date.isoformat(), end_date.isoformat()))
                
                totals = dict(cursor.fetchone())
                
                return {
                    'daily_revenue': daily_revenue,
                    'totals': totals,
                    'period': f'{days} days'
                }
                
        except Exception as e:
            self.logger.error(f"Error getting revenue analytics: {str(e)}")
            return {'error': str(e)}
    
    def get_customer_analytics(self) -> Dict:
        """Get customer analytics"""
        try:
            with self.db.get_db_connection() as conn:
                # Get customer statistics
                cursor = conn.execute('''
                    SELECT 
                        COUNT(DISTINCT email) as total_customers,
                        COUNT(DISTINCT CASE WHEN status = 'completed' THEN email END) as paying_customers,
                        COUNT(*) as total_transactions,
                        AVG(amount) as avg_transaction_value
                    FROM transactions
                ''')
                
                stats = dict(cursor.fetchone())
                
                # Get top customers
                cursor = conn.execute('''
                    SELECT 
                        email,
                        COUNT(*) as transaction_count,
                        SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) as total_spent,
                        MAX(created_at) as last_transaction
                    FROM transactions
                    GROUP BY email
                    ORDER BY total_spent DESC
                    LIMIT 10
                ''')
                
                top_customers = [dict(row) for row in cursor.fetchall()]
                
                # Get customer acquisition over time
                cursor = conn.execute('''
                    SELECT 
                        DATE(created_at) as date,
                        COUNT(DISTINCT email) as new_customers
                    FROM transactions
                    WHERE created_at >= date('now', '-30 days')
                    GROUP BY DATE(created_at)
                    ORDER BY date
                ''')
                
                acquisition_data = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'stats': stats,
                    'top_customers': top_customers,
                    'acquisition_data': acquisition_data
                }
                
        except Exception as e:
            self.logger.error(f"Error getting customer analytics: {str(e)}")
            return {'error': str(e)}

# Global transaction analytics service instance
transaction_analytics = TransactionAnalyticsService()