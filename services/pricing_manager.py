#!/usr/bin/env python3
"""
Advanced Pricing Manager Service for VectorCraft

This service provides comprehensive pricing management capabilities including:
- Dynamic pricing tiers with real-time updates
- Regional pricing with currency conversion
- Time-based pricing and promotional periods
- Advanced pricing rules and conditions
- Revenue optimization and analytics
- A/B testing for pricing strategies
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from database import db


class PricingStrategy(Enum):
    """Pricing strategy types"""
    FIXED = "fixed"
    PERCENTAGE = "percentage"
    DYNAMIC = "dynamic"
    TIERED = "tiered"
    VOLUME = "volume"
    TEMPORAL = "temporal"


class PricingCondition(Enum):
    """Pricing rule condition types"""
    LOCATION = "location"
    USER_TYPE = "user_type"
    TIME_PERIOD = "time_period"
    VOLUME = "volume"
    FIRST_TIME = "first_time"
    REFERRAL = "referral"
    SUBSCRIPTION = "subscription"


@dataclass
class PricingTier:
    """Pricing tier data structure"""
    tier_id: str
    name: str
    base_price: float
    currency: str = 'USD'
    description: str = None
    max_uploads: int = -1
    max_file_size: int = -1
    priority_processing: bool = False
    features: List[str] = None
    is_active: bool = True
    sort_order: int = 0


@dataclass
class PricingRule:
    """Pricing rule data structure"""
    rule_id: str
    name: str
    rule_type: str
    tier_id: str
    condition_type: str
    condition_value: str
    action_type: str
    action_value: str
    priority: int = 0
    is_active: bool = True
    valid_from: datetime = None
    valid_until: datetime = None
    usage_limit: int = -1
    usage_count: int = 0


class PricingManager:
    """Advanced pricing management system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db = db
        self.cache = {}
        self.currency_rates = {
            'USD': 1.0,
            'EUR': 0.85,
            'GBP': 0.73,
            'JPY': 110.0,
            'INR': 74.0,
            'CAD': 1.25,
            'AUD': 1.35
        }
        self.initialize_default_tiers()
    
    def initialize_default_tiers(self):
        """Initialize default pricing tiers if none exist"""
        existing_tiers = self.db.get_pricing_tiers()
        if not existing_tiers:
            self.logger.info("Initializing default pricing tiers")
            
            # Basic tier
            self.db.create_pricing_tier(
                tier_id='basic',
                name='Basic',
                base_price=9.99,
                description='Perfect for individual users',
                max_uploads=50,
                max_file_size=5 * 1024 * 1024,  # 5MB
                features=['High-quality vectorization', 'Basic support', 'SVG output'],
                sort_order=1
            )
            
            # Premium tier
            self.db.create_pricing_tier(
                tier_id='premium',
                name='Premium',
                base_price=19.99,
                description='Best for professionals',
                max_uploads=200,
                max_file_size=20 * 1024 * 1024,  # 20MB
                priority_processing=True,
                features=['High-quality vectorization', 'Priority processing', 'Advanced options', 'Priority support'],
                sort_order=2
            )
            
            # Enterprise tier
            self.db.create_pricing_tier(
                tier_id='enterprise',
                name='Enterprise',
                base_price=49.99,
                description='For teams and businesses',
                max_uploads=-1,  # Unlimited
                max_file_size=100 * 1024 * 1024,  # 100MB
                priority_processing=True,
                features=['Unlimited vectorization', 'Priority processing', 'Advanced options', 'Dedicated support', 'API access'],
                sort_order=3
            )
    
    def get_pricing_tiers(self, currency: str = 'USD', country: str = None, 
                         user_type: str = None, user_email: str = None) -> List[Dict]:
        """Get pricing tiers with dynamic pricing applied"""
        try:
            # Get base tiers
            tiers = self.db.get_pricing_tiers(is_active=True)
            
            # Apply dynamic pricing
            for tier in tiers:
                original_price = tier['base_price']
                
                # Apply regional pricing
                tier['base_price'] = self.convert_currency(original_price, 'USD', currency)
                tier['currency'] = currency
                
                # Apply dynamic pricing rules
                adjusted_price = self.apply_pricing_rules(
                    tier['tier_id'], 
                    tier['base_price'], 
                    country=country,
                    user_type=user_type,
                    user_email=user_email
                )
                
                tier['final_price'] = adjusted_price
                tier['discount_amount'] = original_price - adjusted_price if adjusted_price < original_price else 0
                tier['savings_percentage'] = ((original_price - adjusted_price) / original_price * 100) if adjusted_price < original_price else 0
                
                # Format features
                if isinstance(tier['features'], str):
                    try:
                        tier['features'] = json.loads(tier['features'])
                    except:
                        tier['features'] = []
                
                # Add tier analytics
                tier['analytics'] = self.get_tier_analytics(tier['tier_id'])
            
            return tiers
            
        except Exception as e:
            self.logger.error(f"Error getting pricing tiers: {e}")
            return []
    
    def get_pricing_tier(self, tier_id: str, currency: str = 'USD', 
                        country: str = None, user_type: str = None, 
                        user_email: str = None) -> Optional[Dict]:
        """Get single pricing tier with dynamic pricing"""
        try:
            tier = self.db.get_pricing_tier(tier_id)
            if not tier:
                return None
            
            original_price = tier['base_price']
            
            # Apply regional pricing
            tier['base_price'] = self.convert_currency(original_price, 'USD', currency)
            tier['currency'] = currency
            
            # Apply dynamic pricing rules
            adjusted_price = self.apply_pricing_rules(
                tier_id, 
                tier['base_price'], 
                country=country,
                user_type=user_type,
                user_email=user_email
            )
            
            tier['final_price'] = adjusted_price
            tier['discount_amount'] = original_price - adjusted_price if adjusted_price < original_price else 0
            tier['savings_percentage'] = ((original_price - adjusted_price) / original_price * 100) if adjusted_price < original_price else 0
            
            return tier
            
        except Exception as e:
            self.logger.error(f"Error getting pricing tier {tier_id}: {e}")
            return None
    
    def convert_currency(self, amount: float, from_currency: str, to_currency: str) -> float:
        """Convert currency using exchange rates"""
        try:
            if from_currency == to_currency:
                return amount
            
            # Convert to USD first, then to target currency
            usd_amount = amount / self.currency_rates.get(from_currency, 1.0)
            converted_amount = usd_amount * self.currency_rates.get(to_currency, 1.0)
            
            return round(converted_amount, 2)
            
        except Exception as e:
            self.logger.error(f"Error converting currency: {e}")
            return amount
    
    def apply_pricing_rules(self, tier_id: str, base_price: float, **context) -> float:
        """Apply dynamic pricing rules to calculate final price"""
        try:
            # Get active pricing rules for this tier
            rules = self.get_active_pricing_rules(tier_id)
            
            final_price = base_price
            applied_rules = []
            
            # Sort rules by priority (higher priority first)
            rules.sort(key=lambda x: x.get('priority', 0), reverse=True)
            
            for rule in rules:
                if self.evaluate_rule_condition(rule, **context):
                    adjustment = self.calculate_rule_adjustment(rule, final_price)
                    final_price = adjustment
                    applied_rules.append(rule)
                    
                    # Log rule application
                    self.logger.info(f"Applied pricing rule {rule['rule_id']} to tier {tier_id}")
            
            return max(0, final_price)  # Ensure price is not negative
            
        except Exception as e:
            self.logger.error(f"Error applying pricing rules: {e}")
            return base_price
    
    def get_active_pricing_rules(self, tier_id: str = None) -> List[Dict]:
        """Get active pricing rules"""
        try:
            with self.db.get_db_connection() as conn:
                query = '''
                    SELECT * FROM pricing_rules 
                    WHERE is_active = 1 
                    AND (valid_from IS NULL OR valid_from <= CURRENT_TIMESTAMP)
                    AND (valid_until IS NULL OR valid_until >= CURRENT_TIMESTAMP)
                '''
                params = []
                
                if tier_id:
                    query += ' AND (tier_id = ? OR tier_id IS NULL)'
                    params.append(tier_id)
                
                query += ' ORDER BY priority DESC'
                
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Error getting active pricing rules: {e}")
            return []
    
    def evaluate_rule_condition(self, rule: Dict, **context) -> bool:
        """Evaluate if a pricing rule condition is met"""
        try:
            condition_type = rule['condition_type']
            condition_value = rule['condition_value']
            
            if condition_type == 'location':
                return context.get('country') in json.loads(condition_value)
            
            elif condition_type == 'user_type':
                return context.get('user_type') == condition_value
            
            elif condition_type == 'time_period':
                time_config = json.loads(condition_value)
                now = datetime.now()
                
                if 'start_hour' in time_config and 'end_hour' in time_config:
                    return time_config['start_hour'] <= now.hour <= time_config['end_hour']
                
                if 'day_of_week' in time_config:
                    return now.weekday() in time_config['day_of_week']
            
            elif condition_type == 'first_time':
                user_email = context.get('user_email')
                if user_email:
                    transactions = self.db.get_transactions(email=user_email, status='completed')
                    return len(transactions) == 0
            
            elif condition_type == 'referral':
                return context.get('referral_code') is not None
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error evaluating rule condition: {e}")
            return False
    
    def calculate_rule_adjustment(self, rule: Dict, current_price: float) -> float:
        """Calculate price adjustment based on rule action"""
        try:
            action_type = rule['action_type']
            action_value = float(rule['action_value'])
            
            if action_type == 'percentage_discount':
                return current_price * (1 - action_value / 100)
            
            elif action_type == 'fixed_discount':
                return current_price - action_value
            
            elif action_type == 'fixed_price':
                return action_value
            
            elif action_type == 'percentage_increase':
                return current_price * (1 + action_value / 100)
            
            return current_price
            
        except Exception as e:
            self.logger.error(f"Error calculating rule adjustment: {e}")
            return current_price
    
    def create_pricing_tier(self, tier_data: Dict) -> str:
        """Create a new pricing tier"""
        try:
            tier_id = tier_data.get('tier_id', f"tier_{uuid.uuid4().hex[:8]}")
            
            result = self.db.create_pricing_tier(
                tier_id=tier_id,
                name=tier_data['name'],
                base_price=tier_data['base_price'],
                currency=tier_data.get('currency', 'USD'),
                description=tier_data.get('description'),
                max_uploads=tier_data.get('max_uploads', -1),
                max_file_size=tier_data.get('max_file_size', -1),
                priority_processing=tier_data.get('priority_processing', False),
                features=tier_data.get('features', []),
                is_active=tier_data.get('is_active', True),
                sort_order=tier_data.get('sort_order', 0)
            )
            
            if result:
                self.logger.info(f"Created pricing tier: {tier_id}")
                # Clear cache
                self.cache.clear()
                return tier_id
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error creating pricing tier: {e}")
            return None
    
    def update_pricing_tier(self, tier_id: str, updates: Dict) -> bool:
        """Update pricing tier with change tracking"""
        try:
            # Get current tier for change tracking
            current_tier = self.db.get_pricing_tier(tier_id)
            if not current_tier:
                return False
            
            # Log price change if price is being updated
            if 'base_price' in updates and updates['base_price'] != current_tier['base_price']:
                self.db.log_pricing_change(
                    tier_id=tier_id,
                    old_price=current_tier['base_price'],
                    new_price=updates['base_price'],
                    change_reason=updates.get('change_reason', 'Manual update'),
                    changed_by=updates.get('changed_by', 'System')
                )
            
            # Update tier
            self.db.update_pricing_tier(tier_id, **updates)
            
            self.logger.info(f"Updated pricing tier: {tier_id}")
            # Clear cache
            self.cache.clear()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating pricing tier {tier_id}: {e}")
            return False
    
    def create_pricing_rule(self, rule_data: Dict) -> str:
        """Create a new pricing rule"""
        try:
            rule_id = rule_data.get('rule_id', f"rule_{uuid.uuid4().hex[:8]}")
            
            with self.db.get_db_connection() as conn:
                cursor = conn.execute('''
                    INSERT INTO pricing_rules 
                    (rule_id, name, rule_type, tier_id, condition_type, condition_value,
                     action_type, action_value, priority, is_active, valid_from, valid_until,
                     usage_limit)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    rule_id,
                    rule_data['name'],
                    rule_data['rule_type'],
                    rule_data.get('tier_id'),
                    rule_data['condition_type'],
                    rule_data['condition_value'],
                    rule_data['action_type'],
                    rule_data['action_value'],
                    rule_data.get('priority', 0),
                    int(rule_data.get('is_active', True)),
                    rule_data.get('valid_from'),
                    rule_data.get('valid_until'),
                    rule_data.get('usage_limit', -1)
                ))
                conn.commit()
            
            self.logger.info(f"Created pricing rule: {rule_id}")
            return rule_id
            
        except Exception as e:
            self.logger.error(f"Error creating pricing rule: {e}")
            return None
    
    def get_tier_analytics(self, tier_id: str, days: int = 30) -> Dict:
        """Get analytics for a pricing tier"""
        try:
            analytics = self.db.get_pricing_analytics(days=days, tier_id=tier_id)
            
            if not analytics:
                return {
                    'total_views': 0,
                    'total_purchases': 0,
                    'total_revenue': 0,
                    'conversion_rate': 0,
                    'avg_discount': 0
                }
            
            summary = {
                'total_views': sum(a['views'] for a in analytics),
                'total_purchases': sum(a['purchases'] for a in analytics),
                'total_revenue': sum(a['revenue'] for a in analytics),
                'conversion_rate': 0,
                'avg_discount': sum(a['avg_discount'] for a in analytics) / len(analytics) if analytics else 0
            }
            
            if summary['total_views'] > 0:
                summary['conversion_rate'] = (summary['total_purchases'] / summary['total_views']) * 100
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting tier analytics: {e}")
            return {}
    
    def record_pricing_view(self, tier_id: str, country: str = None):
        """Record a pricing view for analytics"""
        try:
            self.db.record_pricing_view(tier_id, country)
            
        except Exception as e:
            self.logger.error(f"Error recording pricing view: {e}")
    
    def record_pricing_purchase(self, tier_id: str, discount_id: str, country: str, 
                               revenue: float, discount_amount: float = 0):
        """Record a pricing purchase for analytics"""
        try:
            self.db.record_pricing_purchase(tier_id, discount_id, country, revenue, discount_amount)
            
        except Exception as e:
            self.logger.error(f"Error recording pricing purchase: {e}")
    
    def get_revenue_forecast(self, tier_id: str = None, days: int = 30) -> Dict:
        """Generate revenue forecast based on historical data"""
        try:
            # Get historical data
            analytics = self.db.get_pricing_analytics(days=days*2, tier_id=tier_id)
            
            if len(analytics) < 7:  # Need at least a week of data
                return {
                    'forecast_revenue': 0,
                    'forecast_sales': 0,
                    'confidence_level': 0,
                    'trend': 'insufficient_data'
                }
            
            # Simple linear trend analysis
            recent_data = analytics[:days] if len(analytics) >= days else analytics
            older_data = analytics[days:] if len(analytics) >= days*2 else []
            
            recent_avg_revenue = sum(a['revenue'] for a in recent_data) / len(recent_data)
            recent_avg_sales = sum(a['purchases'] for a in recent_data) / len(recent_data)
            
            if older_data:
                older_avg_revenue = sum(a['revenue'] for a in older_data) / len(older_data)
                older_avg_sales = sum(a['purchases'] for a in older_data) / len(older_data)
                
                revenue_trend = (recent_avg_revenue - older_avg_revenue) / older_avg_revenue if older_avg_revenue > 0 else 0
                sales_trend = (recent_avg_sales - older_avg_sales) / older_avg_sales if older_avg_sales > 0 else 0
            else:
                revenue_trend = 0
                sales_trend = 0
            
            # Project forward
            forecast_revenue = recent_avg_revenue * (1 + revenue_trend) * days
            forecast_sales = recent_avg_sales * (1 + sales_trend) * days
            
            # Simple confidence calculation
            confidence_level = min(95, 50 + (len(analytics) * 2))
            
            trend = 'up' if revenue_trend > 0.1 else 'down' if revenue_trend < -0.1 else 'stable'
            
            return {
                'forecast_revenue': round(forecast_revenue, 2),
                'forecast_sales': int(forecast_sales),
                'confidence_level': confidence_level,
                'trend': trend,
                'revenue_trend_percentage': round(revenue_trend * 100, 2),
                'sales_trend_percentage': round(sales_trend * 100, 2)
            }
            
        except Exception as e:
            self.logger.error(f"Error generating revenue forecast: {e}")
            return {}
    
    def optimize_pricing(self, tier_id: str) -> Dict:
        """Suggest pricing optimizations based on analytics"""
        try:
            analytics = self.get_tier_analytics(tier_id)
            tier = self.db.get_pricing_tier(tier_id)
            
            if not analytics or not tier:
                return {}
            
            suggestions = []
            
            # Low conversion rate
            if analytics['conversion_rate'] < 2:
                suggestions.append({
                    'type': 'price_reduction',
                    'message': 'Consider reducing price by 10-15% to improve conversion rate',
                    'suggested_price': tier['base_price'] * 0.9,
                    'reason': 'Low conversion rate indicates price resistance'
                })
            
            # High conversion rate
            elif analytics['conversion_rate'] > 15:
                suggestions.append({
                    'type': 'price_increase',
                    'message': 'Consider increasing price by 5-10% to maximize revenue',
                    'suggested_price': tier['base_price'] * 1.05,
                    'reason': 'High conversion rate indicates room for price increase'
                })
            
            # High discount usage
            if analytics['avg_discount'] > tier['base_price'] * 0.2:
                suggestions.append({
                    'type': 'reduce_discounts',
                    'message': 'Consider reducing discount rates to maintain margins',
                    'reason': 'High discount usage may be eroding profitability'
                })
            
            return {
                'tier_id': tier_id,
                'current_analytics': analytics,
                'suggestions': suggestions,
                'optimization_score': self.calculate_optimization_score(analytics)
            }
            
        except Exception as e:
            self.logger.error(f"Error optimizing pricing: {e}")
            return {}
    
    def calculate_optimization_score(self, analytics: Dict) -> int:
        """Calculate optimization score (0-100)"""
        try:
            score = 50  # Base score
            
            # Conversion rate factor
            conversion_rate = analytics.get('conversion_rate', 0)
            if conversion_rate > 10:
                score += 20
            elif conversion_rate > 5:
                score += 10
            elif conversion_rate < 1:
                score -= 20
            
            # Revenue factor
            revenue = analytics.get('total_revenue', 0)
            if revenue > 1000:
                score += 15
            elif revenue > 500:
                score += 10
            elif revenue < 100:
                score -= 15
            
            # Discount factor
            avg_discount = analytics.get('avg_discount', 0)
            if avg_discount > 10:
                score -= 10
            elif avg_discount < 5:
                score += 5
            
            return max(0, min(100, score))
            
        except Exception as e:
            self.logger.error(f"Error calculating optimization score: {e}")
            return 50
    
    def get_pricing_summary(self) -> Dict:
        """Get comprehensive pricing summary for dashboard"""
        try:
            tiers = self.db.get_pricing_tiers(is_active=True)
            revenue_summary = self.db.get_revenue_summary()
            
            return {
                'total_tiers': len(tiers),
                'active_tiers': len([t for t in tiers if t['is_active']]),
                'revenue_summary': revenue_summary,
                'tier_performance': [
                    {
                        'tier_id': tier['tier_id'],
                        'name': tier['name'],
                        'price': tier['base_price'],
                        'analytics': self.get_tier_analytics(tier['tier_id'])
                    }
                    for tier in tiers
                ],
                'optimization_opportunities': [
                    self.optimize_pricing(tier['tier_id'])
                    for tier in tiers
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting pricing summary: {e}")
            return {}


# Global pricing manager instance
pricing_manager = PricingManager()