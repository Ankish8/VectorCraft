#!/usr/bin/env python3
"""
Financial Reporting Service for VectorCraft
Comprehensive financial dashboards and analytics
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
from database import db

class ReportPeriod(Enum):
    TODAY = "today"
    YESTERDAY = "yesterday"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    CUSTOM = "custom"

@dataclass
class FinancialMetrics:
    """Financial metrics data structure"""
    total_revenue: float
    total_transactions: int
    successful_transactions: int
    failed_transactions: int
    success_rate: float
    average_transaction_value: float
    total_fees: float
    net_revenue: float
    growth_rate: float
    refunds: float
    disputes: float

@dataclass
class RevenueBreakdown:
    """Revenue breakdown by categories"""
    subscription_revenue: float
    one_time_payments: float
    refunds: float
    chargebacks: float
    processing_fees: float
    net_revenue: float

class FinancialReportingService:
    """Advanced financial reporting and analytics service"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db = db
        
        # Fee structures (configurable)
        self.fee_structure = {
            'paypal_percentage': 0.029,  # 2.9%
            'paypal_fixed': 0.30,        # $0.30
            'processing_fee': 0.01,      # 1% additional
            'currency_conversion': 0.025  # 2.5% for currency conversion
        }
        
    def generate_financial_report(self, 
                                 period: ReportPeriod = ReportPeriod.MONTH,
                                 start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None) -> Dict:
        """Generate comprehensive financial report"""
        try:
            # Determine date range
            date_range = self._get_date_range(period, start_date, end_date)
            
            # Get basic financial metrics
            metrics = self._calculate_financial_metrics(date_range['start'], date_range['end'])
            
            # Get revenue breakdown
            revenue_breakdown = self._get_revenue_breakdown(date_range['start'], date_range['end'])
            
            # Get trends analysis
            trends = self._get_financial_trends(date_range['start'], date_range['end'])
            
            # Get payment method analysis
            payment_methods = self._get_payment_method_analysis(date_range['start'], date_range['end'])
            
            # Get geographical analysis
            geographical = self._get_geographical_analysis(date_range['start'], date_range['end'])
            
            # Get customer analysis
            customer_analysis = self._get_customer_analysis(date_range['start'], date_range['end'])
            
            # Get performance metrics
            performance = self._get_performance_metrics(date_range['start'], date_range['end'])
            
            return {
                'report_period': period.value,
                'date_range': date_range,
                'metrics': asdict(metrics),
                'revenue_breakdown': asdict(revenue_breakdown),
                'trends': trends,
                'payment_methods': payment_methods,
                'geographical': geographical,
                'customer_analysis': customer_analysis,
                'performance': performance,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating financial report: {str(e)}")
            return {'error': str(e)}
    
    def _get_date_range(self, period: ReportPeriod, 
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None) -> Dict:
        """Get date range for report period"""
        now = datetime.now()
        
        if period == ReportPeriod.TODAY:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif period == ReportPeriod.YESTERDAY:
            start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == ReportPeriod.WEEK:
            start = now - timedelta(days=7)
            end = now
        elif period == ReportPeriod.MONTH:
            start = now - timedelta(days=30)
            end = now
        elif period == ReportPeriod.QUARTER:
            start = now - timedelta(days=90)
            end = now
        elif period == ReportPeriod.YEAR:
            start = now - timedelta(days=365)
            end = now
        elif period == ReportPeriod.CUSTOM:
            start = start_date or (now - timedelta(days=30))
            end = end_date or now
        else:
            start = now - timedelta(days=30)
            end = now
        
        return {
            'start': start,
            'end': end,
            'period_days': (end - start).days
        }
    
    def _calculate_financial_metrics(self, start_date: datetime, end_date: datetime) -> FinancialMetrics:
        """Calculate comprehensive financial metrics"""
        try:
            with self.db.get_db_connection() as conn:
                # Get transaction data
                cursor = conn.execute('''
                    SELECT 
                        COUNT(*) as total_transactions,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_transactions,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_transactions,
                        SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) as total_revenue,
                        AVG(CASE WHEN status = 'completed' THEN amount END) as avg_transaction_value,
                        SUM(CASE WHEN status = 'refunded' THEN amount ELSE 0 END) as refunds,
                        SUM(CASE WHEN status = 'disputed' THEN amount ELSE 0 END) as disputes
                    FROM transactions
                    WHERE created_at >= ? AND created_at <= ?
                ''', (start_date.isoformat(), end_date.isoformat()))
                
                data = dict(cursor.fetchone())
                
                # Calculate derived metrics
                total_revenue = float(data['total_revenue'] or 0)
                total_transactions = int(data['total_transactions'] or 0)
                successful_transactions = int(data['successful_transactions'] or 0)
                failed_transactions = int(data['failed_transactions'] or 0)
                avg_transaction_value = float(data['avg_transaction_value'] or 0)
                refunds = float(data['refunds'] or 0)
                disputes = float(data['disputes'] or 0)
                
                success_rate = (successful_transactions / max(total_transactions, 1)) * 100
                
                # Calculate fees
                total_fees = self._calculate_processing_fees(total_revenue)
                net_revenue = total_revenue - total_fees - refunds - disputes
                
                # Calculate growth rate (compared to previous period)
                growth_rate = self._calculate_growth_rate(start_date, end_date, total_revenue)
                
                return FinancialMetrics(
                    total_revenue=total_revenue,
                    total_transactions=total_transactions,
                    successful_transactions=successful_transactions,
                    failed_transactions=failed_transactions,
                    success_rate=success_rate,
                    average_transaction_value=avg_transaction_value,
                    total_fees=total_fees,
                    net_revenue=net_revenue,
                    growth_rate=growth_rate,
                    refunds=refunds,
                    disputes=disputes
                )
                
        except Exception as e:
            self.logger.error(f"Error calculating financial metrics: {str(e)}")
            return FinancialMetrics(
                total_revenue=0.0,
                total_transactions=0,
                successful_transactions=0,
                failed_transactions=0,
                success_rate=0.0,
                average_transaction_value=0.0,
                total_fees=0.0,
                net_revenue=0.0,
                growth_rate=0.0,
                refunds=0.0,
                disputes=0.0
            )
    
    def _calculate_processing_fees(self, revenue: float) -> float:
        """Calculate processing fees based on revenue"""
        if revenue <= 0:
            return 0.0
        
        # PayPal fees: percentage + fixed per transaction
        paypal_fee = revenue * self.fee_structure['paypal_percentage']
        
        # Additional processing fees
        processing_fee = revenue * self.fee_structure['processing_fee']
        
        return paypal_fee + processing_fee
    
    def _calculate_growth_rate(self, start_date: datetime, end_date: datetime, current_revenue: float) -> float:
        """Calculate growth rate compared to previous period"""
        try:
            # Calculate previous period
            period_duration = end_date - start_date
            previous_start = start_date - period_duration
            previous_end = start_date
            
            with self.db.get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) as previous_revenue
                    FROM transactions
                    WHERE created_at >= ? AND created_at <= ?
                ''', (previous_start.isoformat(), previous_end.isoformat()))
                
                result = cursor.fetchone()
                previous_revenue = float(result[0] or 0)
                
                if previous_revenue > 0:
                    growth_rate = ((current_revenue - previous_revenue) / previous_revenue) * 100
                else:
                    growth_rate = 0.0 if current_revenue == 0 else 100.0
                
                return growth_rate
                
        except Exception as e:
            self.logger.error(f"Error calculating growth rate: {str(e)}")
            return 0.0
    
    def _get_revenue_breakdown(self, start_date: datetime, end_date: datetime) -> RevenueBreakdown:
        """Get detailed revenue breakdown"""
        try:
            with self.db.get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT 
                        SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) as total_revenue,
                        SUM(CASE WHEN status = 'refunded' THEN amount ELSE 0 END) as refunds,
                        SUM(CASE WHEN status = 'disputed' THEN amount ELSE 0 END) as chargebacks
                    FROM transactions
                    WHERE created_at >= ? AND created_at <= ?
                ''', (start_date.isoformat(), end_date.isoformat()))
                
                data = dict(cursor.fetchone())
                
                total_revenue = float(data['total_revenue'] or 0)
                refunds = float(data['refunds'] or 0)
                chargebacks = float(data['chargebacks'] or 0)
                
                # For VectorCraft, all revenue is one-time payments
                subscription_revenue = 0.0
                one_time_payments = total_revenue
                
                processing_fees = self._calculate_processing_fees(total_revenue)
                net_revenue = total_revenue - processing_fees - refunds - chargebacks
                
                return RevenueBreakdown(
                    subscription_revenue=subscription_revenue,
                    one_time_payments=one_time_payments,
                    refunds=refunds,
                    chargebacks=chargebacks,
                    processing_fees=processing_fees,
                    net_revenue=net_revenue
                )
                
        except Exception as e:
            self.logger.error(f"Error getting revenue breakdown: {str(e)}")
            return RevenueBreakdown(
                subscription_revenue=0.0,
                one_time_payments=0.0,
                refunds=0.0,
                chargebacks=0.0,
                processing_fees=0.0,
                net_revenue=0.0
            )
    
    def _get_financial_trends(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get financial trends over time"""
        try:
            with self.db.get_db_connection() as conn:
                # Daily revenue trends
                cursor = conn.execute('''
                    SELECT 
                        DATE(created_at) as date,
                        SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) as daily_revenue,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as daily_transactions,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as daily_failures
                    FROM transactions
                    WHERE created_at >= ? AND created_at <= ?
                    GROUP BY DATE(created_at)
                    ORDER BY date
                ''', (start_date.isoformat(), end_date.isoformat()))
                
                daily_trends = [dict(row) for row in cursor.fetchall()]
                
                # Hourly trends for recent data
                cursor = conn.execute('''
                    SELECT 
                        strftime('%Y-%m-%d %H:00', created_at) as hour,
                        SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) as hourly_revenue,
                        COUNT(*) as hourly_transactions
                    FROM transactions
                    WHERE created_at >= datetime('now', '-7 days')
                    GROUP BY strftime('%Y-%m-%d %H:00', created_at)
                    ORDER BY hour
                ''')
                
                hourly_trends = [dict(row) for row in cursor.fetchall()]
                
                # Calculate trend statistics
                trend_stats = self._calculate_trend_statistics(daily_trends)
                
                return {
                    'daily_trends': daily_trends,
                    'hourly_trends': hourly_trends,
                    'trend_statistics': trend_stats
                }
                
        except Exception as e:
            self.logger.error(f"Error getting financial trends: {str(e)}")
            return {'daily_trends': [], 'hourly_trends': [], 'trend_statistics': {}}
    
    def _calculate_trend_statistics(self, daily_trends: List[Dict]) -> Dict:
        """Calculate trend statistics"""
        if not daily_trends:
            return {}
        
        revenues = [float(day['daily_revenue'] or 0) for day in daily_trends]
        transactions = [int(day['daily_transactions'] or 0) for day in daily_trends]
        
        return {
            'avg_daily_revenue': sum(revenues) / len(revenues),
            'max_daily_revenue': max(revenues),
            'min_daily_revenue': min(revenues),
            'avg_daily_transactions': sum(transactions) / len(transactions),
            'max_daily_transactions': max(transactions),
            'total_days': len(daily_trends)
        }
    
    def _get_payment_method_analysis(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get payment method analysis"""
        try:
            with self.db.get_db_connection() as conn:
                # For VectorCraft, most payments are through PayPal
                cursor = conn.execute('''
                    SELECT 
                        CASE 
                            WHEN paypal_order_id IS NOT NULL THEN 'PayPal'
                            ELSE 'Other'
                        END as payment_method,
                        COUNT(*) as transaction_count,
                        SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) as revenue,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_count,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_count
                    FROM transactions
                    WHERE created_at >= ? AND created_at <= ?
                    GROUP BY payment_method
                ''', (start_date.isoformat(), end_date.isoformat()))
                
                payment_methods = [dict(row) for row in cursor.fetchall()]
                
                # Calculate success rates
                for method in payment_methods:
                    total = method['transaction_count']
                    successful = method['successful_count']
                    method['success_rate'] = (successful / max(total, 1)) * 100
                
                return {
                    'payment_methods': payment_methods,
                    'total_methods': len(payment_methods)
                }
                
        except Exception as e:
            self.logger.error(f"Error getting payment method analysis: {str(e)}")
            return {'payment_methods': [], 'total_methods': 0}
    
    def _get_geographical_analysis(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get geographical analysis (basic implementation)"""
        try:
            with self.db.get_db_connection() as conn:
                # Basic geographical analysis based on email domains
                cursor = conn.execute('''
                    SELECT 
                        CASE 
                            WHEN email LIKE '%.com' OR email LIKE '%.org' OR email LIKE '%.net' THEN 'United States'
                            WHEN email LIKE '%.ca' THEN 'Canada'
                            WHEN email LIKE '%.uk' OR email LIKE '%.co.uk' THEN 'United Kingdom'
                            WHEN email LIKE '%.au' THEN 'Australia'
                            WHEN email LIKE '%.de' THEN 'Germany'
                            WHEN email LIKE '%.in' THEN 'India'
                            ELSE 'Other'
                        END as country,
                        COUNT(*) as transaction_count,
                        SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) as revenue,
                        COUNT(DISTINCT email) as unique_customers
                    FROM transactions
                    WHERE created_at >= ? AND created_at <= ? AND status = 'completed'
                    GROUP BY country
                    ORDER BY revenue DESC
                ''', (start_date.isoformat(), end_date.isoformat()))
                
                geographical_data = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'geographical_data': geographical_data,
                    'total_countries': len(geographical_data)
                }
                
        except Exception as e:
            self.logger.error(f"Error getting geographical analysis: {str(e)}")
            return {'geographical_data': [], 'total_countries': 0}
    
    def _get_customer_analysis(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get customer analysis"""
        try:
            with self.db.get_db_connection() as conn:
                # Customer statistics
                cursor = conn.execute('''
                    SELECT 
                        COUNT(DISTINCT email) as unique_customers,
                        COUNT(DISTINCT CASE WHEN status = 'completed' THEN email END) as paying_customers,
                        AVG(amount) as avg_customer_value,
                        COUNT(*) as total_transactions
                    FROM transactions
                    WHERE created_at >= ? AND created_at <= ?
                ''', (start_date.isoformat(), end_date.isoformat()))
                
                customer_stats = dict(cursor.fetchone())
                
                # Top customers
                cursor = conn.execute('''
                    SELECT 
                        email,
                        COUNT(*) as transaction_count,
                        SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) as total_spent,
                        MAX(created_at) as last_transaction
                    FROM transactions
                    WHERE created_at >= ? AND created_at <= ?
                    GROUP BY email
                    ORDER BY total_spent DESC
                    LIMIT 10
                ''', (start_date.isoformat(), end_date.isoformat()))
                
                top_customers = [dict(row) for row in cursor.fetchall()]
                
                # Customer acquisition
                cursor = conn.execute('''
                    SELECT 
                        DATE(created_at) as date,
                        COUNT(DISTINCT email) as new_customers
                    FROM transactions
                    WHERE created_at >= ? AND created_at <= ?
                    GROUP BY DATE(created_at)
                    ORDER BY date
                ''', (start_date.isoformat(), end_date.isoformat()))
                
                acquisition_data = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'customer_stats': customer_stats,
                    'top_customers': top_customers,
                    'acquisition_data': acquisition_data
                }
                
        except Exception as e:
            self.logger.error(f"Error getting customer analysis: {str(e)}")
            return {'customer_stats': {}, 'top_customers': [], 'acquisition_data': []}
    
    def _get_performance_metrics(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get performance metrics"""
        try:
            with self.db.get_db_connection() as conn:
                # Transaction performance
                cursor = conn.execute('''
                    SELECT 
                        AVG(CASE 
                            WHEN completed_at IS NOT NULL AND created_at IS NOT NULL 
                            THEN (julianday(completed_at) - julianday(created_at)) * 86400 
                        END) as avg_processing_time,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0 / COUNT(*) as success_rate,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) * 100.0 / COUNT(*) as failure_rate,
                        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_count
                    FROM transactions
                    WHERE created_at >= ? AND created_at <= ?
                ''', (start_date.isoformat(), end_date.isoformat()))
                
                performance_data = dict(cursor.fetchone())
                
                # Payment processing metrics
                cursor = conn.execute('''
                    SELECT 
                        AVG(value) as avg_response_time,
                        COUNT(CASE WHEN status = 'error' THEN 1 END) * 100.0 / COUNT(*) as error_rate
                    FROM performance_metrics
                    WHERE metric_type = 'paypal_api_response_time'
                    AND timestamp >= ? AND timestamp <= ?
                ''', (start_date.isoformat(), end_date.isoformat()))
                
                api_performance = cursor.fetchone()
                if api_performance:
                    performance_data['api_avg_response_time'] = api_performance[0]
                    performance_data['api_error_rate'] = api_performance[1]
                
                return performance_data
                
        except Exception as e:
            self.logger.error(f"Error getting performance metrics: {str(e)}")
            return {}
    
    def export_financial_data(self, format_type: str = 'json', 
                            start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None) -> Dict:
        """Export financial data in specified format"""
        try:
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)
            if not end_date:
                end_date = datetime.now()
            
            with self.db.get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT 
                        transaction_id,
                        email,
                        amount,
                        currency,
                        status,
                        paypal_order_id,
                        paypal_payment_id,
                        created_at,
                        completed_at,
                        error_message
                    FROM transactions
                    WHERE created_at >= ? AND created_at <= ?
                    ORDER BY created_at DESC
                ''', (start_date.isoformat(), end_date.isoformat()))
                
                transactions = [dict(row) for row in cursor.fetchall()]
                
                export_data = {
                    'export_date': datetime.now().isoformat(),
                    'date_range': {
                        'start': start_date.isoformat(),
                        'end': end_date.isoformat()
                    },
                    'total_records': len(transactions),
                    'transactions': transactions
                }
                
                if format_type.lower() == 'csv':
                    return self._convert_to_csv(export_data)
                else:
                    return export_data
                
        except Exception as e:
            self.logger.error(f"Error exporting financial data: {str(e)}")
            return {'error': str(e)}
    
    def _convert_to_csv(self, data: Dict) -> Dict:
        """Convert financial data to CSV format"""
        try:
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            header = ['transaction_id', 'email', 'amount', 'currency', 'status', 
                     'paypal_order_id', 'paypal_payment_id', 'created_at', 
                     'completed_at', 'error_message']
            writer.writerow(header)
            
            # Write data
            for transaction in data['transactions']:
                row = [transaction.get(field, '') for field in header]
                writer.writerow(row)
            
            csv_content = output.getvalue()
            output.close()
            
            return {
                'format': 'csv',
                'content': csv_content,
                'filename': f'financial_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            }
            
        except Exception as e:
            self.logger.error(f"Error converting to CSV: {str(e)}")
            return {'error': str(e)}
    
    def get_dashboard_summary(self) -> Dict:
        """Get financial dashboard summary"""
        try:
            # Get today's metrics
            today_metrics = self._calculate_financial_metrics(
                datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
                datetime.now()
            )
            
            # Get this month's metrics
            month_metrics = self._calculate_financial_metrics(
                datetime.now() - timedelta(days=30),
                datetime.now()
            )
            
            # Get year-to-date metrics
            year_start = datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            ytd_metrics = self._calculate_financial_metrics(year_start, datetime.now())
            
            return {
                'today': asdict(today_metrics),
                'month': asdict(month_metrics),
                'year_to_date': asdict(ytd_metrics),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting dashboard summary: {str(e)}")
            return {'error': str(e)}

# Global financial reporting service instance
financial_reporter = FinancialReportingService()