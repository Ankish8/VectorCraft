#!/usr/bin/env python3
"""
Advanced Discount Engine for VectorCraft

This service provides comprehensive discount and coupon management including:
- Dynamic discount code generation
- Bulk discount campaigns
- Usage tracking and analytics
- Advanced discount rules and conditions
- Referral discount automation
- Customer segmentation discounts
- Time-based promotional campaigns
"""

import json
import logging
import uuid
import string
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from database import db


class DiscountType(Enum):
    """Discount types"""
    PERCENTAGE = "percentage"
    FIXED = "fixed"
    BOGO = "buy_one_get_one"
    SHIPPING = "free_shipping"
    BUNDLE = "bundle"


class DiscountTarget(Enum):
    """Discount target types"""
    ALL_USERS = "all_users"
    NEW_USERS = "new_users"
    RETURNING_USERS = "returning_users"
    VIP_USERS = "vip_users"
    GEOGRAPHIC = "geographic"
    EMAIL_LIST = "email_list"


class CampaignStatus(Enum):
    """Campaign status types"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    EXPIRED = "expired"


@dataclass
class DiscountCode:
    """Discount code data structure"""
    discount_id: str
    name: str
    code: str
    discount_type: str
    discount_value: float
    description: str = None
    min_amount: float = 0
    max_discount: float = None
    usage_limit: int = -1
    per_user_limit: int = -1
    is_active: bool = True
    is_public: bool = True
    valid_from: datetime = None
    valid_until: datetime = None
    applicable_tiers: List[str] = None
    target_countries: List[str] = None
    target_emails: List[str] = None
    first_time_only: bool = False


@dataclass
class DiscountCampaign:
    """Discount campaign data structure"""
    campaign_id: str
    name: str
    description: str
    discount_template: Dict
    target_audience: str
    status: str = CampaignStatus.DRAFT.value
    start_date: datetime = None
    end_date: datetime = None
    budget_limit: float = None
    usage_limit: int = -1


class DiscountEngine:
    """Advanced discount and coupon management system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db = db
        self.code_cache = {}
        self.campaign_cache = {}
        self.initialize_default_discounts()
    
    def initialize_default_discounts(self):
        """Initialize default discount codes if none exist"""
        existing_discounts = self.db.get_discounts()
        if not existing_discounts:
            self.logger.info("Initializing default discount codes")
            
            # Welcome discount for new users
            self.create_discount_code({
                'name': 'Welcome Discount',
                'code': 'WELCOME10',
                'discount_type': 'percentage',
                'discount_value': 10,
                'description': 'Welcome! Get 10% off your first purchase',
                'first_time_only': True,
                'usage_limit': 1000,
                'per_user_limit': 1,
                'valid_until': (datetime.now() + timedelta(days=365)).isoformat()
            })
            
            # Seasonal discount
            self.create_discount_code({
                'name': 'Summer Sale',
                'code': 'SUMMER25',
                'discount_type': 'percentage',
                'discount_value': 25,
                'description': 'Summer sale - 25% off all tiers',
                'min_amount': 15,
                'usage_limit': 500,
                'valid_from': datetime.now().isoformat(),
                'valid_until': (datetime.now() + timedelta(days=90)).isoformat()
            })
            
            # VIP discount
            self.create_discount_code({
                'name': 'VIP Discount',
                'code': 'VIP50',
                'discount_type': 'fixed',
                'discount_value': 5,
                'description': 'VIP customer exclusive discount',
                'is_public': False,
                'usage_limit': 100,
                'per_user_limit': 3
            })
    
    def create_discount_code(self, discount_data: Dict) -> str:
        """Create a new discount code"""
        try:
            # Generate unique discount ID
            discount_id = discount_data.get('discount_id', f"disc_{uuid.uuid4().hex[:8]}")
            
            # Generate code if not provided
            code = discount_data.get('code')
            if not code:
                code = self.generate_discount_code()
            
            # Validate code uniqueness
            existing_discount = self.db.get_discount(code=code)
            if existing_discount:
                raise ValueError(f"Discount code '{code}' already exists")
            
            # Create discount
            result = self.db.create_discount(
                discount_id=discount_id,
                name=discount_data['name'],
                code=code,
                description=discount_data.get('description'),
                discount_type=discount_data['discount_type'],
                discount_value=discount_data['discount_value'],
                min_amount=discount_data.get('min_amount', 0),
                max_discount=discount_data.get('max_discount'),
                usage_limit=discount_data.get('usage_limit', -1),
                per_user_limit=discount_data.get('per_user_limit', -1),
                is_active=discount_data.get('is_active', True),
                is_public=discount_data.get('is_public', True),
                valid_from=discount_data.get('valid_from'),
                valid_until=discount_data.get('valid_until'),
                applicable_tiers=discount_data.get('applicable_tiers'),
                target_countries=discount_data.get('target_countries'),
                target_emails=discount_data.get('target_emails'),
                first_time_only=discount_data.get('first_time_only', False)
            )
            
            if result:
                self.logger.info(f"Created discount code: {code} (ID: {discount_id})")
                # Clear cache
                self.code_cache.clear()
                return discount_id
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error creating discount code: {e}")
            return None
    
    def generate_discount_code(self, length: int = 8, prefix: str = None) -> str:
        """Generate a random discount code"""
        try:
            # Use uppercase letters and numbers
            chars = string.ascii_uppercase + string.digits
            code = ''.join(random.choice(chars) for _ in range(length))
            
            if prefix:
                code = f"{prefix}{code}"
            
            # Ensure uniqueness
            while self.db.get_discount(code=code):
                code = ''.join(random.choice(chars) for _ in range(length))
                if prefix:
                    code = f"{prefix}{code}"
            
            return code
            
        except Exception as e:
            self.logger.error(f"Error generating discount code: {e}")
            return f"DISC{uuid.uuid4().hex[:8].upper()}"
    
    def bulk_create_discount_codes(self, template: Dict, count: int, prefix: str = None) -> List[str]:
        """Create multiple discount codes from a template"""
        try:
            created_codes = []
            
            for i in range(count):
                # Generate unique code
                code = self.generate_discount_code(prefix=prefix)
                
                # Create discount data from template
                discount_data = template.copy()
                discount_data['code'] = code
                discount_data['name'] = f"{template['name']} - {code}"
                
                # Create discount
                discount_id = self.create_discount_code(discount_data)
                if discount_id:
                    created_codes.append(code)
                
                # Avoid overwhelming the database
                if i % 100 == 0 and i > 0:
                    self.logger.info(f"Created {i} discount codes...")
            
            self.logger.info(f"Bulk created {len(created_codes)} discount codes")
            return created_codes
            
        except Exception as e:
            self.logger.error(f"Error bulk creating discount codes: {e}")
            return []
    
    def validate_discount_code(self, code: str, user_email: str = None, 
                             tier_id: str = None, amount: float = None,
                             country: str = None) -> Tuple[Optional[Dict], Optional[str]]:
        """Validate discount code and return details or error message"""
        try:
            # Check cache first
            cache_key = f"{code}_{user_email}_{tier_id}_{amount}_{country}"
            if cache_key in self.code_cache:
                return self.code_cache[cache_key]
            
            # Get discount from database
            discount, error = self.db.validate_discount_code(code, user_email, tier_id, amount)
            if error:
                result = (None, error)
            else:
                # Additional validation
                if not self.validate_discount_conditions(discount, user_email, tier_id, amount, country):
                    result = (None, "Discount conditions not met")
                else:
                    result = (discount, None)
            
            # Cache result for 5 minutes
            self.code_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error validating discount code: {e}")
            return None, "Error validating discount code"
    
    def validate_discount_conditions(self, discount: Dict, user_email: str = None,
                                   tier_id: str = None, amount: float = None,
                                   country: str = None) -> bool:
        """Validate additional discount conditions"""
        try:
            # Check geographic restrictions
            if discount.get('target_countries') and country:
                if country not in discount['target_countries']:
                    return False
            
            # Check email restrictions
            if discount.get('target_emails') and user_email:
                if user_email not in discount['target_emails']:
                    return False
            
            # Check tier restrictions
            if discount.get('applicable_tiers') and tier_id:
                if tier_id not in discount['applicable_tiers']:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating discount conditions: {e}")
            return False
    
    def apply_discount(self, discount_id: str, user_id: int, user_email: str,
                      transaction_id: str, original_amount: float) -> Optional[Dict]:
        """Apply discount and record usage"""
        try:
            # Get discount details
            discount = self.db.get_discount(discount_id=discount_id)
            if not discount:
                return None
            
            # Calculate discount amount
            discount_amount = self.db.calculate_discount_amount(discount, original_amount)
            final_amount = original_amount - discount_amount
            
            # Record usage
            usage_id = self.db.apply_discount(
                discount_id=discount_id,
                user_id=user_id,
                user_email=user_email,
                transaction_id=transaction_id,
                original_amount=original_amount,
                discount_amount=discount_amount,
                final_amount=final_amount
            )
            
            if usage_id:
                self.logger.info(f"Applied discount {discount_id} to transaction {transaction_id}")
                
                # Clear cache
                self.code_cache.clear()
                
                return {
                    'discount_id': discount_id,
                    'code': discount['code'],
                    'discount_amount': discount_amount,
                    'final_amount': final_amount,
                    'savings_percentage': (discount_amount / original_amount) * 100,
                    'usage_id': usage_id
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error applying discount: {e}")
            return None
    
    def get_discount_recommendations(self, user_email: str, tier_id: str = None,
                                   amount: float = None, country: str = None) -> List[Dict]:
        """Get personalized discount recommendations"""
        try:
            recommendations = []
            
            # Get user transaction history
            transactions = self.db.get_transactions(email=user_email, status='completed')
            is_first_time = len(transactions) == 0
            
            # Get all active discounts
            discounts = self.db.get_discounts(is_active=True, is_public=True, valid_now=True)
            
            for discount in discounts:
                # Skip if not applicable
                if discount.get('first_time_only') and not is_first_time:
                    continue
                
                # Check conditions
                if not self.validate_discount_conditions(discount, user_email, tier_id, amount, country):
                    continue
                
                # Calculate potential savings
                if amount:
                    discount_amount = self.db.calculate_discount_amount(discount, amount)
                    savings_percentage = (discount_amount / amount) * 100
                else:
                    discount_amount = discount['discount_value']
                    savings_percentage = discount_amount if discount['discount_type'] == 'percentage' else 0
                
                recommendations.append({
                    'discount_id': discount['discount_id'],
                    'code': discount['code'],
                    'name': discount['name'],
                    'description': discount['description'],
                    'discount_type': discount['discount_type'],
                    'discount_value': discount['discount_value'],
                    'potential_savings': discount_amount,
                    'savings_percentage': savings_percentage,
                    'min_amount': discount.get('min_amount', 0),
                    'valid_until': discount.get('valid_until'),
                    'usage_remaining': discount.get('usage_limit', -1) - discount.get('usage_count', 0) if discount.get('usage_limit', -1) > 0 else -1
                })
            
            # Sort by potential savings
            recommendations.sort(key=lambda x: x['potential_savings'], reverse=True)
            
            return recommendations[:5]  # Return top 5
            
        except Exception as e:
            self.logger.error(f"Error getting discount recommendations: {e}")
            return []
    
    def create_referral_discount(self, referrer_email: str, referee_email: str,
                               referrer_discount: float = 10, referee_discount: float = 15) -> Dict:
        """Create referral discount codes"""
        try:
            # Generate unique codes
            referrer_code = self.generate_discount_code(prefix="REF")
            referee_code = self.generate_discount_code(prefix="NEW")
            
            # Create referrer discount
            referrer_discount_id = self.create_discount_code({
                'name': f'Referral Reward - {referrer_email}',
                'code': referrer_code,
                'discount_type': 'percentage',
                'discount_value': referrer_discount,
                'description': f'Thank you for referring {referee_email}!',
                'target_emails': [referrer_email],
                'usage_limit': 1,
                'per_user_limit': 1,
                'is_public': False,
                'valid_until': (datetime.now() + timedelta(days=30)).isoformat()
            })
            
            # Create referee discount
            referee_discount_id = self.create_discount_code({
                'name': f'Welcome Referral - {referee_email}',
                'code': referee_code,
                'discount_type': 'percentage',
                'discount_value': referee_discount,
                'description': f'Welcome! {referrer_email} sent you this discount',
                'target_emails': [referee_email],
                'usage_limit': 1,
                'per_user_limit': 1,
                'is_public': False,
                'first_time_only': True,
                'valid_until': (datetime.now() + timedelta(days=30)).isoformat()
            })
            
            # Log referral
            self.logger.info(f"Created referral discounts: {referrer_email} -> {referee_email}")
            
            return {
                'referrer': {
                    'discount_id': referrer_discount_id,
                    'code': referrer_code,
                    'discount_value': referrer_discount,
                    'email': referrer_email
                },
                'referee': {
                    'discount_id': referee_discount_id,
                    'code': referee_code,
                    'discount_value': referee_discount,
                    'email': referee_email
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error creating referral discount: {e}")
            return {}
    
    def create_discount_campaign(self, campaign_data: Dict) -> str:
        """Create a discount campaign"""
        try:
            campaign_id = campaign_data.get('campaign_id', f"camp_{uuid.uuid4().hex[:8]}")
            
            # Store campaign in database (extend schema if needed)
            # For now, we'll create individual discounts based on campaign
            
            template = campaign_data['discount_template']
            target_audience = campaign_data.get('target_audience', 'all_users')
            
            if target_audience == 'all_users':
                # Create a single public discount
                discount_id = self.create_discount_code(template)
                codes = [template.get('code', 'CAMPAIGN')]
            elif target_audience == 'bulk_codes':
                # Create multiple unique codes
                count = campaign_data.get('code_count', 100)
                codes = self.bulk_create_discount_codes(template, count)
            else:
                # Create targeted discount
                discount_id = self.create_discount_code(template)
                codes = [template.get('code', 'TARGETED')]
            
            # Cache campaign info
            self.campaign_cache[campaign_id] = {
                'campaign_id': campaign_id,
                'name': campaign_data['name'],
                'codes': codes,
                'created_at': datetime.now().isoformat(),
                'status': 'active'
            }
            
            self.logger.info(f"Created discount campaign: {campaign_id} with {len(codes)} codes")
            return campaign_id
            
        except Exception as e:
            self.logger.error(f"Error creating discount campaign: {e}")
            return None
    
    def get_discount_analytics(self, discount_id: str = None, days: int = 30) -> Dict:
        """Get comprehensive discount analytics"""
        try:
            usage_stats = self.db.get_discount_usage_stats(discount_id, days)
            
            if not usage_stats:
                return {
                    'total_discounts': 0,
                    'total_usage': 0,
                    'total_savings': 0,
                    'avg_discount': 0,
                    'conversion_impact': 0
                }
            
            analytics = {
                'total_discounts': len(usage_stats),
                'total_usage': sum(stat['total_usage'] for stat in usage_stats),
                'total_savings': sum(stat['total_discount_amount'] for stat in usage_stats),
                'avg_discount': sum(stat['avg_discount_amount'] for stat in usage_stats) / len(usage_stats),
                'top_performing_codes': sorted(usage_stats, key=lambda x: x['total_usage'], reverse=True)[:5],
                'discount_trends': self.analyze_discount_trends(usage_stats)
            }
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"Error getting discount analytics: {e}")
            return {}
    
    def analyze_discount_trends(self, usage_stats: List[Dict]) -> Dict:
        """Analyze discount usage trends"""
        try:
            trends = {
                'most_popular_type': 'percentage',
                'avg_usage_per_code': 0,
                'high_performers': [],
                'low_performers': []
            }
            
            if not usage_stats:
                return trends
            
            # Calculate averages
            total_usage = sum(stat['total_usage'] for stat in usage_stats)
            trends['avg_usage_per_code'] = total_usage / len(usage_stats)
            
            # Identify high and low performers
            for stat in usage_stats:
                if stat['total_usage'] > trends['avg_usage_per_code'] * 1.5:
                    trends['high_performers'].append(stat)
                elif stat['total_usage'] < trends['avg_usage_per_code'] * 0.5:
                    trends['low_performers'].append(stat)
            
            return trends
            
        except Exception as e:
            self.logger.error(f"Error analyzing discount trends: {e}")
            return {}
    
    def optimize_discount_strategy(self) -> Dict:
        """Provide discount optimization recommendations"""
        try:
            analytics = self.get_discount_analytics()
            
            recommendations = []
            
            # High usage discounts
            if analytics.get('total_usage', 0) > 1000:
                recommendations.append({
                    'type': 'scale_up',
                    'message': 'High discount usage detected. Consider creating more targeted campaigns.',
                    'action': 'Create segmented discount campaigns'
                })
            
            # Low usage discounts
            elif analytics.get('total_usage', 0) < 100:
                recommendations.append({
                    'type': 'increase_visibility',
                    'message': 'Low discount usage. Consider increasing visibility or reducing restrictions.',
                    'action': 'Review discount conditions and marketing'
                })
            
            # High savings rate
            if analytics.get('avg_discount', 0) > 20:
                recommendations.append({
                    'type': 'optimize_margins',
                    'message': 'High average discount rate may impact profitability.',
                    'action': 'Consider reducing discount percentages or adding minimum amounts'
                })
            
            return {
                'current_performance': analytics,
                'recommendations': recommendations,
                'optimization_score': self.calculate_discount_optimization_score(analytics)
            }
            
        except Exception as e:
            self.logger.error(f"Error optimizing discount strategy: {e}")
            return {}
    
    def calculate_discount_optimization_score(self, analytics: Dict) -> int:
        """Calculate discount optimization score (0-100)"""
        try:
            score = 50  # Base score
            
            # Usage factor
            usage = analytics.get('total_usage', 0)
            if usage > 500:
                score += 20
            elif usage > 100:
                score += 10
            elif usage < 10:
                score -= 20
            
            # Savings efficiency
            avg_discount = analytics.get('avg_discount', 0)
            if 5 <= avg_discount <= 15:
                score += 15
            elif avg_discount > 25:
                score -= 15
            
            # Variety factor
            total_discounts = analytics.get('total_discounts', 0)
            if total_discounts > 10:
                score += 10
            elif total_discounts < 3:
                score -= 10
            
            return max(0, min(100, score))
            
        except Exception as e:
            self.logger.error(f"Error calculating optimization score: {e}")
            return 50
    
    def cleanup_expired_discounts(self) -> int:
        """Clean up expired discount codes"""
        try:
            count = 0
            discounts = self.db.get_discounts(is_active=True)
            
            for discount in discounts:
                if discount.get('valid_until'):
                    expiry = datetime.fromisoformat(discount['valid_until'])
                    if expiry < datetime.now():
                        self.db.update_discount(discount['discount_id'], is_active=False)
                        count += 1
            
            if count > 0:
                self.logger.info(f"Deactivated {count} expired discount codes")
                self.code_cache.clear()
            
            return count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up expired discounts: {e}")
            return 0
    
    def get_discount_summary(self) -> Dict:
        """Get comprehensive discount summary for dashboard"""
        try:
            discounts = self.db.get_discounts()
            analytics = self.get_discount_analytics()
            
            return {
                'total_discounts': len(discounts),
                'active_discounts': len([d for d in discounts if d['is_active']]),
                'public_discounts': len([d for d in discounts if d['is_public']]),
                'usage_analytics': analytics,
                'optimization': self.optimize_discount_strategy(),
                'recent_activity': self.db.get_discount_usage_stats(days=7)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting discount summary: {e}")
            return {}


# Global discount engine instance
discount_engine = DiscountEngine()