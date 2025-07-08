"""
Admin dashboard utilities and helpers
"""

import logging
from datetime import datetime, timedelta
from collections import defaultdict
from database import db
from services.monitoring import health_monitor, system_logger, alert_manager

logger = logging.getLogger(__name__)


class AdminDashboard:
    """Admin dashboard data aggregator"""
    
    def __init__(self):
        self.health_monitor = health_monitor
        self.system_logger = system_logger
        self.alert_manager = alert_manager
        self.db = db
    
    def get_overview_data(self):
        """Get overview data for admin dashboard"""
        try:
            # System health
            health_status = self.health_monitor.get_overall_status()
            
            # Recent transactions
            recent_transactions = self.db.get_transactions(limit=50)
            
            # Alert summary
            alert_summary = self.alert_manager.get_alert_summary()
            
            # Calculate daily metrics
            today_date = datetime.now().strftime('%Y-%m-%d')
            today_transactions = [
                tx for tx in recent_transactions 
                if tx['created_at'].startswith(today_date)
            ]
            
            today_revenue = sum(
                float(tx['amount'] or 0) for tx in today_transactions 
                if tx['status'] == 'completed'
            )
            
            # Success rate
            success_rate = (
                len([tx for tx in today_transactions if tx['status'] == 'completed']) / 
                max(len(today_transactions), 1) * 100
            )
            
            # Error summary
            error_summary = self.system_logger.get_error_summary(hours=24)
            
            # Architecture information
            architecture_info = self._get_architecture_info()
            
            return {
                'health_status': health_status,
                'today_stats': {
                    'revenue': today_revenue,
                    'transactions': len(today_transactions),
                    'success_rate': success_rate
                },
                'alert_summary': alert_summary,
                'error_summary': error_summary,
                'recent_transactions': recent_transactions[:10],
                'architecture_info': architecture_info
            }
            
        except Exception as e:
            logger.error(f"Error getting overview data: {e}")
            return {'error': str(e)}
    
    def get_transaction_analytics(self, days=30):
        """Get transaction analytics for specified days"""
        try:
            # Get transactions for the period
            date_from = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            transactions = self.db.get_transactions(limit=1000, date_from=date_from)
            
            # Group by date
            daily_stats = defaultdict(lambda: {
                'revenue': 0, 
                'count': 0, 
                'completed': 0, 
                'failed': 0
            })
            
            for tx in transactions:
                date = tx['created_at'][:10]
                daily_stats[date]['count'] += 1
                
                if tx['status'] == 'completed':
                    daily_stats[date]['revenue'] += float(tx['amount'] or 0)
                    daily_stats[date]['completed'] += 1
                elif tx['status'] == 'failed':
                    daily_stats[date]['failed'] += 1
            
            # Format for charts
            chart_data = []
            for date, stats in sorted(daily_stats.items()):
                chart_data.append({
                    'date': date,
                    'revenue': stats['revenue'],
                    'transactions': stats['count'],
                    'completed': stats['completed'],
                    'failed': stats['failed'],
                    'success_rate': (stats['completed'] / max(stats['count'], 1)) * 100
                })
            
            # Calculate totals
            total_revenue = sum(stats['revenue'] for stats in daily_stats.values())
            total_transactions = sum(stats['count'] for stats in daily_stats.values())
            avg_order_value = total_revenue / max(total_transactions, 1)
            
            return {
                'chart_data': chart_data,
                'totals': {
                    'revenue': total_revenue,
                    'transactions': total_transactions,
                    'avg_order_value': avg_order_value
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting transaction analytics: {e}")
            return {'error': str(e)}
    
    def get_system_performance(self):
        """Get system performance metrics"""
        try:
            import psutil
            import os
            
            # System metrics
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Database metrics
            db_path = self.db.db_path
            db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
            
            # Health check history
            health_history = self.db.get_health_status(hours=24)
            
            # Recent errors
            recent_errors = self.system_logger.get_recent_logs(
                hours=24, 
                level='ERROR', 
                limit=20
            )
            
            return {
                'system': {
                    'memory_percent': memory.percent,
                    'disk_percent': disk.percent,
                    'memory_total': memory.total,
                    'disk_total': disk.total
                },
                'database': {
                    'size': db_size,
                    'path': db_path
                },
                'health_history': health_history,
                'recent_errors': recent_errors
            }
            
        except Exception as e:
            logger.error(f"Error getting system performance: {e}")
            return {'error': str(e)}
    
    def _get_architecture_info(self):
        """Get architecture information"""
        return {
            'type': 'modular_blueprint',
            'version': '2.0.0',
            'blueprints': [
                {
                    'name': 'auth',
                    'description': 'Authentication & Session Management',
                    'routes': 6,
                    'features': ['Login/Logout', 'Rate Limiting', 'Session Management']
                },
                {
                    'name': 'api',
                    'description': 'Vectorization & File Processing',
                    'routes': 8,
                    'features': ['Vectorization', 'File Upload', 'Health Checks']
                },
                {
                    'name': 'admin',
                    'description': 'Administrative Functions',
                    'routes': 15,
                    'features': ['Dashboard', 'Monitoring', 'Analytics']
                },
                {
                    'name': 'payment',
                    'description': 'Payment Processing',
                    'routes': 4,
                    'features': ['PayPal Integration', 'Transaction Logging']
                },
                {
                    'name': 'main',
                    'description': 'Core Application Routes',
                    'routes': 5,
                    'features': ['Landing Page', 'Dashboard', 'File Downloads']
                }
            ],
            'improvements': [
                'Separation of Concerns',
                'Better Error Handling',
                'Enhanced Security',
                'Improved Logging',
                'Modular Architecture'
            ]
        }
    
    def get_user_activity(self, hours=24):
        """Get user activity summary"""
        try:
            # Get recent uploads
            recent_uploads = []
            
            # Get all transactions to see user activity
            transactions = self.db.get_transactions(limit=100)
            
            # Group by user
            user_activity = defaultdict(lambda: {
                'uploads': 0,
                'transactions': 0,
                'last_activity': None
            })
            
            for tx in transactions:
                email = tx['email']
                user_activity[email]['transactions'] += 1
                
                if not user_activity[email]['last_activity'] or tx['created_at'] > user_activity[email]['last_activity']:
                    user_activity[email]['last_activity'] = tx['created_at']
            
            # Convert to list and sort by activity
            activity_list = []
            for email, data in user_activity.items():
                activity_list.append({
                    'email': email,
                    'uploads': data['uploads'],
                    'transactions': data['transactions'],
                    'last_activity': data['last_activity']
                })
            
            # Sort by last activity
            activity_list.sort(key=lambda x: x['last_activity'] or '', reverse=True)
            
            return {
                'user_activity': activity_list[:20],  # Top 20 most active
                'total_users': len(activity_list),
                'active_users_24h': len([
                    u for u in activity_list 
                    if u['last_activity'] and 
                    u['last_activity'] > (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
                ])
            }
            
        except Exception as e:
            logger.error(f"Error getting user activity: {e}")
            return {'error': str(e)}


# Global dashboard instance
admin_dashboard = AdminDashboard()