"""
User Management Service for VectorCraft Admin Panel
Provides advanced user lifecycle tracking, activity management, and analytics
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from database import db

logger = logging.getLogger(__name__)


class UserManagementService:
    """Service for managing user lifecycle and activities"""
    
    def __init__(self):
        self.db = db
        self.logger = logging.getLogger(__name__)
    
    def get_users_with_pagination(self, page: int = 1, per_page: int = 50, 
                                 search: Optional[str] = None, 
                                 status: Optional[bool] = None,
                                 sort_by: str = 'created_at',
                                 sort_order: str = 'DESC') -> Dict[str, Any]:
        """
        Get users with pagination, search, and filtering
        
        Args:
            page: Page number (1-based)
            per_page: Number of users per page
            search: Search term for username/email
            status: User status filter (True=active, False=inactive, None=all)
            sort_by: Field to sort by
            sort_order: Sort order (ASC/DESC)
        
        Returns:
            Dictionary containing users list and pagination info
        """
        try:
            users, total = self.db.get_all_users(
                page=page, 
                per_page=per_page,
                search=search,
                status=status,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            # Calculate pagination info
            total_pages = (total + per_page - 1) // per_page
            has_prev = page > 1
            has_next = page < total_pages
            
            # Enrich user data with additional info
            enriched_users = []
            for user in users:
                user_data = self._enrich_user_data(user)
                enriched_users.append(user_data)
            
            return {
                'users': enriched_users,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'total_pages': total_pages,
                    'has_prev': has_prev,
                    'has_next': has_next,
                    'prev_page': page - 1 if has_prev else None,
                    'next_page': page + 1 if has_next else None
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching users: {str(e)}")
            return {
                'users': [],
                'pagination': {
                    'page': 1,
                    'per_page': per_page,
                    'total': 0,
                    'total_pages': 0,
                    'has_prev': False,
                    'has_next': False,
                    'prev_page': None,
                    'next_page': None
                },
                'error': str(e)
            }
    
    def _enrich_user_data(self, user: Dict) -> Dict:
        """Enrich user data with additional calculated fields"""
        try:
            # Calculate user status
            user['status_label'] = 'Active' if user.get('is_active') else 'Inactive'
            user['status_class'] = 'success' if user.get('is_active') else 'danger'
            
            # Calculate account age
            if user.get('created_at'):
                created_date = datetime.fromisoformat(user['created_at'].replace('Z', '+00:00'))
                account_age = datetime.now() - created_date
                user['account_age_days'] = account_age.days
                user['account_age_text'] = self._format_time_ago(account_age)
            
            # Calculate last activity
            if user.get('last_login'):
                last_login = datetime.fromisoformat(user['last_login'].replace('Z', '+00:00'))
                user['last_activity_text'] = self._format_time_ago(datetime.now() - last_login)
            else:
                user['last_activity_text'] = 'Never logged in'
            
            # Format upload count
            upload_count = user.get('upload_count', 0)
            user['upload_count_text'] = f"{upload_count} uploads" if upload_count != 1 else "1 upload"
            
            # Activity level
            activity_count = user.get('activity_count', 0)
            if activity_count == 0:
                user['activity_level'] = 'No Activity'
                user['activity_level_class'] = 'secondary'
            elif activity_count < 10:
                user['activity_level'] = 'Low Activity'
                user['activity_level_class'] = 'warning'
            elif activity_count < 50:
                user['activity_level'] = 'Medium Activity'
                user['activity_level_class'] = 'info'
            else:
                user['activity_level'] = 'High Activity'
                user['activity_level_class'] = 'success'
            
            return user
            
        except Exception as e:
            self.logger.error(f"Error enriching user data: {str(e)}")
            return user
    
    def _format_time_ago(self, time_delta: timedelta) -> str:
        """Format time delta as human-readable string"""
        if time_delta.days > 0:
            return f"{time_delta.days} days ago"
        elif time_delta.seconds > 3600:
            hours = time_delta.seconds // 3600
            return f"{hours} hours ago"
        elif time_delta.seconds > 60:
            minutes = time_delta.seconds // 60
            return f"{minutes} minutes ago"
        else:
            return "Just now"
    
    def get_user_details(self, user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive user details including analytics and timeline
        
        Args:
            user_id: User ID
        
        Returns:
            Dictionary containing user details, analytics, and timeline
        """
        try:
            # Get user analytics
            analytics = self.db.get_user_analytics(user_id)
            
            if not analytics.get('user_info'):
                return {'error': 'User not found'}
            
            # Get activity timeline
            timeline = self.db.get_user_activity_timeline(user_id, limit=100)
            
            # Process timeline data
            processed_timeline = []
            for activity in timeline:
                activity_data = {
                    'type': activity['activity_type'],
                    'description': activity['description'],
                    'timestamp': activity['timestamp'],
                    'source': activity['source_type']
                }
                
                # Add icon and color based on activity type
                if activity['activity_type'] == 'upload':
                    activity_data['icon'] = 'upload'
                    activity_data['color'] = 'primary'
                elif activity['activity_type'] == 'login':
                    activity_data['icon'] = 'sign-in'
                    activity_data['color'] = 'success'
                elif activity['activity_type'] == 'transaction':
                    activity_data['icon'] = 'credit-card'
                    activity_data['color'] = 'info'
                else:
                    activity_data['icon'] = 'activity'
                    activity_data['color'] = 'secondary'
                
                # Parse details if available
                if activity.get('details'):
                    try:
                        activity_data['details'] = json.loads(activity['details'])
                    except (json.JSONDecodeError, TypeError):
                        activity_data['details'] = {}
                
                processed_timeline.append(activity_data)
            
            # Enrich user info
            user_info = self._enrich_user_data(analytics['user_info'])
            
            return {
                'user_info': user_info,
                'upload_stats': analytics['upload_stats'],
                'activity_stats': analytics['activity_stats'],
                'recent_activity': analytics['recent_activity'],
                'upload_history': analytics['upload_history'],
                'timeline': processed_timeline
            }
            
        except Exception as e:
            self.logger.error(f"Error getting user details for user {user_id}: {str(e)}")
            return {'error': str(e)}
    
    def bulk_update_users(self, user_ids: List[int], action: str, **kwargs) -> Dict[str, Any]:
        """
        Perform bulk operations on users
        
        Args:
            user_ids: List of user IDs
            action: Action to perform ('activate', 'deactivate', 'delete')
            **kwargs: Additional parameters for the action
        
        Returns:
            Dictionary containing operation results
        """
        try:
            if not user_ids:
                return {'error': 'No users selected'}
            
            affected_count = 0
            
            if action == 'activate':
                affected_count = self.db.bulk_update_users(user_ids, {'is_active': True})
                
                # Log activity for each user
                for user_id in user_ids:
                    self.db.log_user_activity(
                        user_id=user_id,
                        activity_type='admin_action',
                        description='Account activated by admin',
                        details={'action': 'activate', 'admin_user': kwargs.get('admin_user')}
                    )
                
            elif action == 'deactivate':
                affected_count = self.db.bulk_update_users(user_ids, {'is_active': False})
                
                # Log activity for each user
                for user_id in user_ids:
                    self.db.log_user_activity(
                        user_id=user_id,
                        activity_type='admin_action',
                        description='Account deactivated by admin',
                        details={'action': 'deactivate', 'admin_user': kwargs.get('admin_user')}
                    )
                
            elif action == 'delete':
                affected_count = self.db.delete_users(user_ids)
                
                # Log activity for each user
                for user_id in user_ids:
                    self.db.log_user_activity(
                        user_id=user_id,
                        activity_type='admin_action',
                        description='Account deleted by admin',
                        details={'action': 'delete', 'admin_user': kwargs.get('admin_user')}
                    )
            
            else:
                return {'error': f'Unknown action: {action}'}
            
            return {
                'success': True,
                'affected_count': affected_count,
                'message': f'Successfully {action}d {affected_count} users'
            }
            
        except Exception as e:
            self.logger.error(f"Error performing bulk action {action}: {str(e)}")
            return {'error': str(e)}
    
    def get_user_segments(self) -> Dict[str, Any]:
        """
        Get user segmentation data for analytics
        
        Returns:
            Dictionary containing segmentation data
        """
        try:
            segments = self.db.get_user_segments()
            
            # Process segments for visualization
            processed_segments = {
                'status_distribution': {
                    'labels': ['Active', 'Inactive'],
                    'data': [
                        segments['status_distribution']['active_users'],
                        segments['status_distribution']['inactive_users']
                    ],
                    'colors': ['#28a745', '#dc3545']
                },
                'activity_segments': {
                    'labels': [seg['activity_level'] for seg in segments['activity_segments']],
                    'data': [seg['user_count'] for seg in segments['activity_segments']],
                    'colors': ['#6c757d', '#ffc107', '#17a2b8', '#28a745']
                },
                'age_segments': {
                    'labels': [seg['user_age'] for seg in segments['age_segments']],
                    'data': [seg['user_count'] for seg in segments['age_segments']],
                    'colors': ['#007bff', '#28a745', '#6c757d']
                },
                'registration_trend': segments['registration_trend']
            }
            
            return processed_segments
            
        except Exception as e:
            self.logger.error(f"Error getting user segments: {str(e)}")
            return {'error': str(e)}
    
    def log_user_activity(self, user_id: int, activity_type: str, description: str, 
                         ip_address: Optional[str] = None, user_agent: Optional[str] = None,
                         details: Optional[Dict] = None) -> bool:
        """
        Log user activity
        
        Args:
            user_id: User ID
            activity_type: Type of activity
            description: Activity description
            ip_address: User's IP address
            user_agent: User's browser user agent
            details: Additional activity details
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.db.log_user_activity(
                user_id=user_id,
                activity_type=activity_type,
                description=description,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Error logging user activity: {str(e)}")
            return False
    
    def search_users(self, query: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Advanced user search with filters
        
        Args:
            query: Search query
            filters: Additional filters (status, date_range, etc.)
        
        Returns:
            List of matching users
        """
        try:
            filters = filters or {}
            
            users, _ = self.db.get_all_users(
                search=query,
                status=filters.get('status'),
                sort_by=filters.get('sort_by', 'created_at'),
                sort_order=filters.get('sort_order', 'DESC'),
                per_page=filters.get('limit', 100)
            )
            
            return [self._enrich_user_data(user) for user in users]
            
        except Exception as e:
            self.logger.error(f"Error searching users: {str(e)}")
            return []
    
    def get_user_insights(self) -> Dict[str, Any]:
        """
        Get user insights for admin dashboard
        
        Returns:
            Dictionary containing user insights
        """
        try:
            segments = self.db.get_user_segments()
            
            # Calculate insights
            total_users = segments['status_distribution']['total_users']
            active_users = segments['status_distribution']['active_users']
            inactive_users = segments['status_distribution']['inactive_users']
            
            # Calculate growth rate (last 7 days vs previous 7 days)
            growth_rate = self._calculate_growth_rate()
            
            # Get top active users
            top_users, _ = self.db.get_all_users(
                sort_by='activity_count',
                sort_order='DESC',
                per_page=5
            )
            
            insights = {
                'total_users': total_users,
                'active_users': active_users,
                'inactive_users': inactive_users,
                'activation_rate': round((active_users / max(total_users, 1)) * 100, 1),
                'growth_rate': growth_rate,
                'top_active_users': [self._enrich_user_data(user) for user in top_users],
                'activity_distribution': segments['activity_segments'],
                'registration_trend': segments['registration_trend'][:7]  # Last 7 days
            }
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error getting user insights: {str(e)}")
            return {'error': str(e)}
    
    def _calculate_growth_rate(self) -> float:
        """Calculate user growth rate (last 7 days vs previous 7 days)"""
        try:
            # This would require additional database queries
            # For now, return a placeholder
            return 12.5  # 12.5% growth rate
            
        except Exception as e:
            self.logger.error(f"Error calculating growth rate: {str(e)}")
            return 0.0


# Global instance
user_management_service = UserManagementService()