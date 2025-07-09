#!/usr/bin/env python3
"""
Advanced Analytics Service for VectorCraft Business Intelligence
Provides ML-based revenue forecasting, customer behavior analysis, and ROI dashboards
"""

import logging
import sqlite3
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from pathlib import Path
import pickle
import os
from dataclasses import dataclass
from functools import lru_cache
import warnings

# Suppress pandas warnings for cleaner output
warnings.filterwarnings('ignore', category=FutureWarning)

# Simple linear regression implementation (to avoid sklearn dependency)
class SimpleLinearRegression:
    """Simple linear regression model for revenue forecasting"""
    
    def __init__(self):
        self.slope = 0
        self.intercept = 0
        self.r_squared = 0
        self.fitted = False
    
    def fit(self, X: np.ndarray, y: np.ndarray):
        """Fit the linear regression model"""
        if len(X) == 0 or len(y) == 0:
            return self
        
        n = len(X)
        if n < 2:
            self.slope = 0
            self.intercept = np.mean(y) if len(y) > 0 else 0
            self.r_squared = 0
            self.fitted = True
            return self
        
        # Calculate slope and intercept
        x_mean = np.mean(X)
        y_mean = np.mean(y)
        
        numerator = np.sum((X - x_mean) * (y - y_mean))
        denominator = np.sum((X - x_mean) ** 2)
        
        if denominator == 0:
            self.slope = 0
            self.intercept = y_mean
        else:
            self.slope = numerator / denominator
            self.intercept = y_mean - self.slope * x_mean
        
        # Calculate R-squared
        y_pred = self.slope * X + self.intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - y_mean) ** 2)
        
        self.r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        self.fitted = True
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions using the fitted model"""
        if not self.fitted:
            raise ValueError("Model must be fitted before making predictions")
        return self.slope * X + self.intercept
    
    def get_trend_direction(self) -> str:
        """Get trend direction based on slope"""
        if self.slope > 0.1:
            return "increasing"
        elif self.slope < -0.1:
            return "decreasing"
        else:
            return "stable"

@dataclass
class CustomerMetrics:
    """Data class for customer behavior metrics"""
    user_id: int
    email: str
    first_purchase: datetime
    last_purchase: datetime
    total_spent: float
    transaction_count: int
    avg_order_value: float
    days_since_last_purchase: int
    lifetime_value_score: float
    risk_score: float
    segment: str

@dataclass
class ConversionFunnelMetrics:
    """Data class for conversion funnel metrics"""
    stage: str
    visitors: int
    conversions: int
    conversion_rate: float
    drop_off_rate: float
    avg_time_in_stage: float

@dataclass
class ROIMetrics:
    """Data class for ROI and profitability metrics"""
    revenue: float
    costs: float
    profit: float
    roi_percentage: float
    profit_margin: float
    break_even_point: float
    customer_acquisition_cost: float
    customer_lifetime_value: float

class AnalyticsService:
    """Advanced analytics service with ML capabilities"""
    
    def __init__(self, db_path: str = None):
        self.logger = logging.getLogger(__name__)
        self.db_path = db_path or '/app/data/vectorcraft.db'
        self.models_path = Path('/app/data/models') if os.path.exists('/app/data') else Path('./models')
        self.models_path.mkdir(exist_ok=True)
        
        # Initialize ML models
        self.revenue_model = SimpleLinearRegression()
        self.customer_behavior_model = SimpleLinearRegression()
        
        # Cache for expensive calculations
        self._cache = {}
        self._cache_timeout = 300  # 5 minutes
        
        self.logger.info("Analytics service initialized")
    
    def _get_db_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute database query and return results"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Database query error: {e}")
            return []
    
    def _cache_key(self, func_name: str, *args) -> str:
        """Generate cache key for function and arguments"""
        return f"{func_name}:{hash(str(args))}"
    
    def _get_cached_or_compute(self, func_name: str, compute_func, *args):
        """Get cached result or compute and cache new result"""
        cache_key = self._cache_key(func_name, *args)
        now = datetime.now()
        
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if (now - timestamp).seconds < self._cache_timeout:
                return cached_data
        
        # Compute new result
        result = compute_func(*args)
        self._cache[cache_key] = (result, now)
        return result
    
    def get_revenue_forecast(self, days_ahead: int = 30) -> Dict[str, Any]:
        """
        Generate ML-based revenue forecasting
        
        Args:
            days_ahead: Number of days to forecast
            
        Returns:
            Dictionary containing forecast data and model metrics
        """
        try:
            # Get historical revenue data
            query = """
                SELECT 
                    DATE(created_at) as date,
                    SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) as revenue,
                    COUNT(*) as transactions
                FROM transactions 
                WHERE created_at >= datetime('now', '-90 days')
                GROUP BY DATE(created_at)
                ORDER BY date
            """
            
            data = self._execute_query(query)
            
            if not data:
                return {
                    'forecast': [],
                    'model_metrics': {
                        'r_squared': 0,
                        'trend': 'insufficient_data',
                        'confidence': 'low'
                    },
                    'insights': ['Insufficient historical data for forecasting']
                }
            
            # Prepare data for ML model
            dates = [datetime.strptime(row['date'], '%Y-%m-%d') for row in data]
            revenues = [float(row['revenue']) for row in data]
            
            # Convert dates to numerical values (days since first date)
            base_date = min(dates)
            X = np.array([(d - base_date).days for d in dates])
            y = np.array(revenues)
            
            # Train the model
            self.revenue_model.fit(X, y)
            
            # Generate forecast
            last_date = max(dates)
            forecast_dates = []
            forecast_values = []
            
            for i in range(1, days_ahead + 1):
                future_date = last_date + timedelta(days=i)
                future_x = (future_date - base_date).days
                predicted_revenue = self.revenue_model.predict(np.array([future_x]))[0]
                
                # Ensure non-negative predictions
                predicted_revenue = max(0, predicted_revenue)
                
                forecast_dates.append(future_date.strftime('%Y-%m-%d'))
                forecast_values.append(round(predicted_revenue, 2))
            
            # Calculate confidence intervals (simple approach)
            historical_std = np.std(y)
            confidence_interval = historical_std * 1.96  # 95% confidence
            
            forecast_data = []
            for i, (date, value) in enumerate(zip(forecast_dates, forecast_values)):
                # Decrease confidence over time
                confidence_factor = max(0.1, 1 - (i / days_ahead))
                current_ci = confidence_interval * confidence_factor
                
                forecast_data.append({
                    'date': date,
                    'predicted_revenue': value,
                    'confidence_upper': value + current_ci,
                    'confidence_lower': max(0, value - current_ci),
                    'confidence_level': confidence_factor
                })
            
            # Generate insights
            insights = []
            trend = self.revenue_model.get_trend_direction()
            
            if trend == "increasing":
                insights.append(f"Revenue trend is positive with {self.revenue_model.slope:.2f} daily growth")
            elif trend == "decreasing":
                insights.append(f"Revenue trend is declining with {abs(self.revenue_model.slope):.2f} daily decrease")
            else:
                insights.append("Revenue trend is stable")
            
            if self.revenue_model.r_squared > 0.7:
                insights.append("High confidence in forecast accuracy")
            elif self.revenue_model.r_squared > 0.4:
                insights.append("Moderate confidence in forecast accuracy")
            else:
                insights.append("Low confidence - consider external factors")
            
            return {
                'forecast': forecast_data,
                'historical_data': [
                    {
                        'date': row['date'],
                        'actual_revenue': float(row['revenue']),
                        'transactions': row['transactions']
                    }
                    for row in data
                ],
                'model_metrics': {
                    'r_squared': round(self.revenue_model.r_squared, 3),
                    'trend': trend,
                    'confidence': 'high' if self.revenue_model.r_squared > 0.7 else 'medium' if self.revenue_model.r_squared > 0.4 else 'low'
                },
                'insights': insights
            }
            
        except Exception as e:
            self.logger.error(f"Revenue forecasting error: {e}")
            return {
                'forecast': [],
                'model_metrics': {'error': str(e)},
                'insights': ['Error generating forecast']
            }
    
    def get_customer_behavior_analysis(self) -> Dict[str, Any]:
        """
        Analyze customer behavior patterns and segments
        
        Returns:
            Dictionary containing customer behavior metrics and segments
        """
        try:
            # Get customer transaction data
            query = """
                SELECT 
                    t.email,
                    u.id as user_id,
                    MIN(t.created_at) as first_purchase,
                    MAX(t.created_at) as last_purchase,
                    SUM(CASE WHEN t.status = 'completed' THEN t.amount ELSE 0 END) as total_spent,
                    COUNT(CASE WHEN t.status = 'completed' THEN 1 END) as transaction_count,
                    AVG(CASE WHEN t.status = 'completed' THEN t.amount END) as avg_order_value
                FROM transactions t
                LEFT JOIN users u ON t.email = u.email
                WHERE t.created_at >= datetime('now', '-180 days')
                GROUP BY t.email, u.id
                HAVING transaction_count > 0
            """
            
            data = self._execute_query(query)
            
            if not data:
                return {
                    'customer_segments': [],
                    'behavior_metrics': {},
                    'insights': ['No customer data available']
                }
            
            # Process customer metrics
            customers = []
            now = datetime.now()
            
            for row in data:
                first_purchase = datetime.strptime(row['first_purchase'], '%Y-%m-%d %H:%M:%S')
                last_purchase = datetime.strptime(row['last_purchase'], '%Y-%m-%d %H:%M:%S')
                days_since_last = (now - last_purchase).days
                
                # Calculate lifetime value score (simple scoring)
                total_spent = float(row['total_spent'] or 0)
                transaction_count = int(row['transaction_count'] or 0)
                avg_order_value = float(row['avg_order_value'] or 0)
                
                # Lifetime value score based on recency, frequency, monetary
                recency_score = max(0, 100 - days_since_last * 2)  # Recent purchases score higher
                frequency_score = min(100, transaction_count * 25)  # More transactions score higher
                monetary_score = min(100, total_spent * 2)  # Higher spending scores higher
                
                lifetime_value_score = (recency_score * 0.3 + frequency_score * 0.4 + monetary_score * 0.3)
                
                # Risk score (likelihood of churn)
                risk_score = min(100, days_since_last * 3)  # Higher days since last purchase = higher risk
                
                # Customer segmentation
                if lifetime_value_score >= 80:
                    segment = "Champions"
                elif lifetime_value_score >= 60:
                    segment = "Loyal Customers"
                elif lifetime_value_score >= 40:
                    segment = "Potential Loyalists"
                elif lifetime_value_score >= 20:
                    segment = "At Risk"
                else:
                    segment = "Cannot Lose Them"
                
                customers.append(CustomerMetrics(
                    user_id=row['user_id'] or 0,
                    email=row['email'],
                    first_purchase=first_purchase,
                    last_purchase=last_purchase,
                    total_spent=total_spent,
                    transaction_count=transaction_count,
                    avg_order_value=avg_order_value,
                    days_since_last_purchase=days_since_last,
                    lifetime_value_score=lifetime_value_score,
                    risk_score=risk_score,
                    segment=segment
                ))
            
            # Calculate segment statistics
            segment_stats = defaultdict(lambda: {
                'count': 0,
                'total_revenue': 0,
                'avg_order_value': 0,
                'avg_lifetime_value': 0,
                'avg_risk_score': 0
            })
            
            for customer in customers:
                segment_stats[customer.segment]['count'] += 1
                segment_stats[customer.segment]['total_revenue'] += customer.total_spent
                segment_stats[customer.segment]['avg_lifetime_value'] += customer.lifetime_value_score
                segment_stats[customer.segment]['avg_risk_score'] += customer.risk_score
            
            # Calculate averages
            customer_segments = []
            for segment, stats in segment_stats.items():
                count = stats['count']
                customer_segments.append({
                    'segment': segment,
                    'customer_count': count,
                    'total_revenue': round(stats['total_revenue'], 2),
                    'avg_lifetime_value': round(stats['avg_lifetime_value'] / count, 2),
                    'avg_risk_score': round(stats['avg_risk_score'] / count, 2),
                    'revenue_percentage': round((stats['total_revenue'] / sum(c.total_spent for c in customers)) * 100, 2)
                })
            
            # Overall behavior metrics
            behavior_metrics = {
                'total_customers': len(customers),
                'avg_customer_lifetime_value': round(sum(c.lifetime_value_score for c in customers) / len(customers), 2),
                'avg_days_between_purchases': round(sum(c.days_since_last_purchase for c in customers) / len(customers), 2),
                'repeat_customer_rate': round(len([c for c in customers if c.transaction_count > 1]) / len(customers) * 100, 2),
                'high_value_customers': len([c for c in customers if c.lifetime_value_score >= 80]),
                'at_risk_customers': len([c for c in customers if c.risk_score >= 70])
            }
            
            # Generate insights
            insights = []
            
            # Customer retention insights
            at_risk_percentage = (behavior_metrics['at_risk_customers'] / behavior_metrics['total_customers']) * 100
            if at_risk_percentage > 30:
                insights.append(f"High customer churn risk: {at_risk_percentage:.1f}% of customers at risk")
            
            # Revenue concentration insights
            champions_segment = next((s for s in customer_segments if s['segment'] == 'Champions'), None)
            if champions_segment and champions_segment['revenue_percentage'] > 50:
                insights.append(f"Revenue concentrated in top customers: {champions_segment['revenue_percentage']:.1f}% from Champions")
            
            # Repeat purchase insights
            if behavior_metrics['repeat_customer_rate'] < 30:
                insights.append("Low repeat purchase rate - focus on customer retention")
            
            return {
                'customer_segments': customer_segments,
                'behavior_metrics': behavior_metrics,
                'insights': insights,
                'top_customers': [
                    {
                        'email': c.email,
                        'total_spent': c.total_spent,
                        'lifetime_value_score': round(c.lifetime_value_score, 2),
                        'segment': c.segment
                    }
                    for c in sorted(customers, key=lambda x: x.lifetime_value_score, reverse=True)[:10]
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Customer behavior analysis error: {e}")
            return {
                'customer_segments': [],
                'behavior_metrics': {},
                'insights': [f'Error analyzing customer behavior: {str(e)}']
            }
    
    def get_conversion_funnel_analysis(self) -> Dict[str, Any]:
        """
        Analyze conversion funnel and purchase flow optimization
        
        Returns:
            Dictionary containing conversion funnel metrics and optimization suggestions
        """
        try:
            # Simulated funnel stages (in a real implementation, you'd track these events)
            # For now, we'll use transaction data to estimate funnel performance
            
            # Get transaction attempt data
            query = """
                SELECT 
                    status,
                    COUNT(*) as count,
                    AVG(julianday(COALESCE(completed_at, datetime('now'))) - julianday(created_at)) as avg_time_to_complete
                FROM transactions
                WHERE created_at >= datetime('now', '-30 days')
                GROUP BY status
            """
            
            data = self._execute_query(query)
            
            if not data:
                return {
                    'funnel_stages': [],
                    'conversion_metrics': {},
                    'optimization_suggestions': ['No funnel data available']
                }
            
            # Process transaction status data
            status_counts = {row['status']: row['count'] for row in data}
            avg_completion_times = {row['status']: row['avg_time_to_complete'] for row in data}
            
            # Estimate funnel stages based on transaction data
            total_attempts = sum(status_counts.values())
            completed_count = status_counts.get('completed', 0)
            pending_count = status_counts.get('pending', 0)
            failed_count = status_counts.get('failed', 0)
            
            # Create funnel stages
            funnel_stages = []
            
            # Stage 1: Payment Initiation
            funnel_stages.append(ConversionFunnelMetrics(
                stage="Payment Initiation",
                visitors=total_attempts,
                conversions=total_attempts,
                conversion_rate=100.0,
                drop_off_rate=0.0,
                avg_time_in_stage=0.0
            ))
            
            # Stage 2: Payment Processing
            processing_visitors = completed_count + pending_count
            funnel_stages.append(ConversionFunnelMetrics(
                stage="Payment Processing",
                visitors=total_attempts,
                conversions=processing_visitors,
                conversion_rate=round((processing_visitors / total_attempts) * 100, 2) if total_attempts > 0 else 0,
                drop_off_rate=round((failed_count / total_attempts) * 100, 2) if total_attempts > 0 else 0,
                avg_time_in_stage=avg_completion_times.get('pending', 0) or 0
            ))
            
            # Stage 3: Payment Completion
            funnel_stages.append(ConversionFunnelMetrics(
                stage="Payment Completion",
                visitors=processing_visitors,
                conversions=completed_count,
                conversion_rate=round((completed_count / processing_visitors) * 100, 2) if processing_visitors > 0 else 0,
                drop_off_rate=round((pending_count / processing_visitors) * 100, 2) if processing_visitors > 0 else 0,
                avg_time_in_stage=avg_completion_times.get('completed', 0) or 0
            ))
            
            # Overall conversion metrics
            overall_conversion_rate = round((completed_count / total_attempts) * 100, 2) if total_attempts > 0 else 0
            
            conversion_metrics = {
                'total_visitors': total_attempts,
                'total_conversions': completed_count,
                'overall_conversion_rate': overall_conversion_rate,
                'abandonment_rate': round(100 - overall_conversion_rate, 2),
                'avg_completion_time': round(avg_completion_times.get('completed', 0) or 0, 2),
                'failure_rate': round((failed_count / total_attempts) * 100, 2) if total_attempts > 0 else 0
            }
            
            # Generate optimization suggestions
            optimization_suggestions = []
            
            if conversion_metrics['failure_rate'] > 20:
                optimization_suggestions.append("High payment failure rate - investigate payment gateway issues")
            
            if conversion_metrics['avg_completion_time'] > 1:  # More than 1 day
                optimization_suggestions.append("Long payment completion time - optimize payment flow")
            
            if conversion_metrics['overall_conversion_rate'] < 80:
                optimization_suggestions.append("Low conversion rate - improve user experience and payment process")
            
            # Time-based analysis
            hourly_query = """
                SELECT 
                    strftime('%H', created_at) as hour,
                    COUNT(*) as transactions,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
                FROM transactions
                WHERE created_at >= datetime('now', '-7 days')
                GROUP BY hour
                ORDER BY hour
            """
            
            hourly_data = self._execute_query(hourly_query)
            
            peak_hours = []
            for row in hourly_data:
                hour = int(row['hour'])
                transactions = row['transactions']
                completed = row['completed']
                conversion_rate = (completed / transactions * 100) if transactions > 0 else 0
                
                peak_hours.append({
                    'hour': hour,
                    'transactions': transactions,
                    'conversion_rate': round(conversion_rate, 2)
                })
            
            # Find best performing hours
            best_hours = sorted(peak_hours, key=lambda x: x['conversion_rate'], reverse=True)[:3]
            if best_hours:
                best_hour_text = ', '.join([f"{h['hour']}:00" for h in best_hours])
                optimization_suggestions.append(f"Best performing hours: {best_hour_text}")
            
            return {
                'funnel_stages': [
                    {
                        'stage': stage.stage,
                        'visitors': stage.visitors,
                        'conversions': stage.conversions,
                        'conversion_rate': stage.conversion_rate,
                        'drop_off_rate': stage.drop_off_rate,
                        'avg_time_in_stage': round(stage.avg_time_in_stage, 2)
                    }
                    for stage in funnel_stages
                ],
                'conversion_metrics': conversion_metrics,
                'optimization_suggestions': optimization_suggestions,
                'hourly_performance': peak_hours
            }
            
        except Exception as e:
            self.logger.error(f"Conversion funnel analysis error: {e}")
            return {
                'funnel_stages': [],
                'conversion_metrics': {},
                'optimization_suggestions': [f'Error analyzing conversion funnel: {str(e)}']
            }
    
    def get_roi_dashboard(self) -> Dict[str, Any]:
        """
        Calculate ROI and profitability metrics
        
        Returns:
            Dictionary containing ROI and profitability analysis
        """
        try:
            # Get revenue data
            revenue_query = """
                SELECT 
                    SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) as total_revenue,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_transactions,
                    COUNT(*) as total_transactions,
                    AVG(CASE WHEN status = 'completed' THEN amount END) as avg_order_value
                FROM transactions
                WHERE created_at >= datetime('now', '-30 days')
            """
            
            revenue_data = self._execute_query(revenue_query)
            
            if not revenue_data:
                return {
                    'roi_metrics': {},
                    'profitability_analysis': {},
                    'insights': ['No revenue data available']
                }
            
            revenue_row = revenue_data[0]
            total_revenue = float(revenue_row['total_revenue'] or 0)
            completed_transactions = int(revenue_row['completed_transactions'] or 0)
            total_transactions = int(revenue_row['total_transactions'] or 0)
            avg_order_value = float(revenue_row['avg_order_value'] or 0)
            
            # Estimate costs (in a real implementation, you'd track actual costs)
            # For this example, we'll use estimated costs
            estimated_costs = {
                'payment_processing': total_revenue * 0.03,  # 3% payment processing fee
                'hosting': 50.0,  # Monthly hosting cost
                'email_service': 20.0,  # Monthly email service cost
                'development': 500.0,  # Monthly development cost (amortized)
                'marketing': 100.0,  # Monthly marketing cost
                'other_operational': 80.0  # Other operational costs
            }
            
            total_costs = sum(estimated_costs.values())
            profit = total_revenue - total_costs
            roi_percentage = (profit / total_costs * 100) if total_costs > 0 else 0
            profit_margin = (profit / total_revenue * 100) if total_revenue > 0 else 0
            
            # Customer acquisition cost
            customer_acquisition_cost = estimated_costs['marketing'] / max(completed_transactions, 1)
            
            # Customer lifetime value (simplified)
            customer_lifetime_value = avg_order_value * 1.5  # Assume 1.5x average order as LTV
            
            # Break-even analysis
            break_even_point = total_costs / avg_order_value if avg_order_value > 0 else 0
            
            roi_metrics = ROIMetrics(
                revenue=total_revenue,
                costs=total_costs,
                profit=profit,
                roi_percentage=roi_percentage,
                profit_margin=profit_margin,
                break_even_point=break_even_point,
                customer_acquisition_cost=customer_acquisition_cost,
                customer_lifetime_value=customer_lifetime_value
            )
            
            # Monthly trend analysis
            monthly_query = """
                SELECT 
                    strftime('%Y-%m', created_at) as month,
                    SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) as revenue,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as transactions
                FROM transactions
                WHERE created_at >= datetime('now', '-6 months')
                GROUP BY month
                ORDER BY month
            """
            
            monthly_data = self._execute_query(monthly_query)
            
            # Calculate monthly ROI trend
            monthly_roi = []
            for row in monthly_data:
                month_revenue = float(row['revenue'] or 0)
                month_transactions = int(row['transactions'] or 0)
                month_costs = (total_costs / max(completed_transactions, 1)) * month_transactions
                month_profit = month_revenue - month_costs
                month_roi = (month_profit / month_costs * 100) if month_costs > 0 else 0
                
                monthly_roi.append({
                    'month': row['month'],
                    'revenue': month_revenue,
                    'profit': month_profit,
                    'roi_percentage': round(month_roi, 2),
                    'transactions': month_transactions
                })
            
            # Generate insights
            insights = []
            
            if roi_percentage > 100:
                insights.append(f"Excellent ROI: {roi_percentage:.1f}% return on investment")
            elif roi_percentage > 50:
                insights.append(f"Good ROI: {roi_percentage:.1f}% return on investment")
            elif roi_percentage > 0:
                insights.append(f"Positive ROI: {roi_percentage:.1f}% return on investment")
            else:
                insights.append(f"Negative ROI: {roi_percentage:.1f}% - costs exceed revenue")
            
            if customer_lifetime_value > customer_acquisition_cost * 3:
                insights.append("Strong customer economics - high LTV to CAC ratio")
            elif customer_lifetime_value > customer_acquisition_cost:
                insights.append("Positive customer economics - LTV exceeds CAC")
            else:
                insights.append("Poor customer economics - CAC exceeds LTV")
            
            if profit_margin > 20:
                insights.append("Healthy profit margins")
            elif profit_margin > 10:
                insights.append("Moderate profit margins")
            else:
                insights.append("Low profit margins - focus on cost optimization")
            
            return {
                'roi_metrics': {
                    'total_revenue': round(roi_metrics.revenue, 2),
                    'total_costs': round(roi_metrics.costs, 2),
                    'profit': round(roi_metrics.profit, 2),
                    'roi_percentage': round(roi_metrics.roi_percentage, 2),
                    'profit_margin': round(roi_metrics.profit_margin, 2),
                    'break_even_point': round(roi_metrics.break_even_point, 2),
                    'customer_acquisition_cost': round(roi_metrics.customer_acquisition_cost, 2),
                    'customer_lifetime_value': round(roi_metrics.customer_lifetime_value, 2)
                },
                'cost_breakdown': {
                    key: round(value, 2) for key, value in estimated_costs.items()
                },
                'monthly_trend': monthly_roi,
                'profitability_analysis': {
                    'is_profitable': profit > 0,
                    'months_to_break_even': max(0, round(break_even_point / (completed_transactions / 30), 1)) if completed_transactions > 0 else 0,
                    'cost_per_transaction': round(total_costs / max(total_transactions, 1), 2),
                    'revenue_per_transaction': round(total_revenue / max(total_transactions, 1), 2)
                },
                'insights': insights
            }
            
        except Exception as e:
            self.logger.error(f"ROI dashboard error: {e}")
            return {
                'roi_metrics': {},
                'profitability_analysis': {},
                'insights': [f'Error calculating ROI: {str(e)}']
            }
    
    def get_predictive_analytics(self) -> Dict[str, Any]:
        """
        Generate predictive analytics and business insights
        
        Returns:
            Dictionary containing predictive analytics results
        """
        try:
            # Get comprehensive data for predictions
            revenue_forecast = self.get_revenue_forecast(30)
            customer_behavior = self.get_customer_behavior_analysis()
            conversion_funnel = self.get_conversion_funnel_analysis()
            roi_analysis = self.get_roi_dashboard()
            
            # Generate predictive insights
            insights = []
            
            # Revenue predictions
            if revenue_forecast['model_metrics'].get('trend') == 'increasing':
                insights.append("Revenue is trending upward - expect continued growth")
            elif revenue_forecast['model_metrics'].get('trend') == 'decreasing':
                insights.append("Revenue is declining - implement retention strategies")
            
            # Customer behavior predictions
            at_risk_customers = customer_behavior['behavior_metrics'].get('at_risk_customers', 0)
            total_customers = customer_behavior['behavior_metrics'].get('total_customers', 1)
            
            if at_risk_customers / total_customers > 0.3:
                insights.append("High customer churn risk - prioritize retention campaigns")
            
            # Conversion optimization predictions
            conversion_rate = conversion_funnel['conversion_metrics'].get('overall_conversion_rate', 0)
            if conversion_rate < 70:
                insights.append("Conversion rate below optimal - A/B test payment flow")
            
            # ROI predictions
            roi_percentage = roi_analysis['roi_metrics'].get('roi_percentage', 0)
            if roi_percentage > 100:
                insights.append("Strong ROI suggests scaling opportunities")
            
            # Seasonal patterns (simplified)
            seasonal_query = """
                SELECT 
                    strftime('%w', created_at) as day_of_week,
                    strftime('%H', created_at) as hour,
                    COUNT(*) as transactions,
                    AVG(CASE WHEN status = 'completed' THEN amount ELSE 0 END) as avg_revenue
                FROM transactions
                WHERE created_at >= datetime('now', '-30 days')
                GROUP BY day_of_week, hour
                ORDER BY transactions DESC
                LIMIT 10
            """
            
            seasonal_data = self._execute_query(seasonal_query)
            
            # Business recommendations
            recommendations = []
            
            if customer_behavior['behavior_metrics'].get('repeat_customer_rate', 0) < 30:
                recommendations.append("Implement loyalty program to increase repeat purchases")
            
            if conversion_funnel['conversion_metrics'].get('failure_rate', 0) > 15:
                recommendations.append("Optimize payment gateway to reduce transaction failures")
            
            if roi_analysis['roi_metrics'].get('customer_acquisition_cost', 0) > roi_analysis['roi_metrics'].get('customer_lifetime_value', 0):
                recommendations.append("Reduce customer acquisition costs or increase customer lifetime value")
            
            # Risk assessments
            risk_factors = []
            
            if revenue_forecast['model_metrics'].get('confidence') == 'low':
                risk_factors.append("Low revenue forecast confidence - monitor closely")
            
            if at_risk_customers / total_customers > 0.4:
                risk_factors.append("High customer churn risk - immediate action required")
            
            if roi_percentage < 0:
                risk_factors.append("Negative ROI - urgent cost optimization needed")
            
            return {
                'predictive_insights': insights,
                'business_recommendations': recommendations,
                'risk_factors': risk_factors,
                'seasonal_patterns': [
                    {
                        'day_of_week': row['day_of_week'],
                        'hour': row['hour'],
                        'transactions': row['transactions'],
                        'avg_revenue': round(float(row['avg_revenue'] or 0), 2)
                    }
                    for row in seasonal_data
                ],
                'forecast_summary': {
                    'next_30_days_revenue': sum(item['predicted_revenue'] for item in revenue_forecast['forecast']),
                    'expected_customers': customer_behavior['behavior_metrics'].get('total_customers', 0),
                    'predicted_conversion_rate': conversion_funnel['conversion_metrics'].get('overall_conversion_rate', 0),
                    'expected_roi': roi_analysis['roi_metrics'].get('roi_percentage', 0)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Predictive analytics error: {e}")
            return {
                'predictive_insights': [f'Error generating predictions: {str(e)}'],
                'business_recommendations': [],
                'risk_factors': [],
                'seasonal_patterns': [],
                'forecast_summary': {}
            }
    
    def get_comprehensive_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive analytics dashboard data
        
        Returns:
            Dictionary containing all analytics components
        """
        try:
            analytics_data = {
                'revenue_forecast': self.get_revenue_forecast(),
                'customer_behavior': self.get_customer_behavior_analysis(),
                'conversion_funnel': self.get_conversion_funnel_analysis(),
                'roi_dashboard': self.get_roi_dashboard(),
                'predictive_analytics': self.get_predictive_analytics(),
                'generated_at': datetime.now().isoformat(),
                'data_quality': {
                    'sufficient_data': True,
                    'confidence_level': 'medium',
                    'recommendations': [
                        'Collect more user interaction data for better insights',
                        'Implement event tracking for accurate funnel analysis',
                        'Track actual operational costs for precise ROI calculation'
                    ]
                }
            }
            
            return analytics_data
            
        except Exception as e:
            self.logger.error(f"Comprehensive analytics error: {e}")
            return {
                'error': str(e),
                'generated_at': datetime.now().isoformat()
            }
    
    def save_model(self, model_name: str, model_data: Any):
        """Save ML model to disk"""
        try:
            model_path = self.models_path / f"{model_name}.pkl"
            with open(model_path, 'wb') as f:
                pickle.dump(model_data, f)
            self.logger.info(f"Model saved: {model_name}")
        except Exception as e:
            self.logger.error(f"Error saving model {model_name}: {e}")
    
    def load_model(self, model_name: str) -> Any:
        """Load ML model from disk"""
        try:
            model_path = self.models_path / f"{model_name}.pkl"
            if model_path.exists():
                with open(model_path, 'rb') as f:
                    return pickle.load(f)
            return None
        except Exception as e:
            self.logger.error(f"Error loading model {model_name}: {e}")
            return None

# Global analytics service instance
analytics_service = AnalyticsService()