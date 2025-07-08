"""
Task Queue Manager for Celery task monitoring and management
"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from celery import Celery
from celery.result import AsyncResult
from celery.events.state import State
from celery.events import EventReceiver
from celery.app.control import Control

from celery_config import celery_app
from services.redis_service import redis_service
from services.monitoring.system_logger import system_logger

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task status enumeration"""
    PENDING = "PENDING"
    STARTED = "STARTED"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"


@dataclass
class TaskInfo:
    """Task information data class"""
    task_id: str
    name: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    progress: Optional[Dict[str, Any]] = None
    worker: Optional[str] = None
    queue: Optional[str] = None
    eta: Optional[datetime] = None
    expires: Optional[datetime] = None
    args: Optional[List] = None
    kwargs: Optional[Dict] = None
    runtime: Optional[float] = None


class TaskQueueManager:
    """Manager for Celery task queue operations"""
    
    def __init__(self, celery_app: Celery = None):
        self.celery_app = celery_app or celery_app
        self.control = Control(self.celery_app)
        self.redis = redis_service
        
        # Task tracking
        self.task_cache_prefix = 'task_queue'
        self.task_ttl = 86400  # 24 hours
        
        # Queue names
        self.queues = {
            'vectorization': 'vectorization',
            'batch_processing': 'batch_processing',
            'image_analysis': 'image_analysis',
            'maintenance': 'maintenance',
            'default': 'celery'
        }
        
        # Task metrics
        self.metrics_prefix = 'task_metrics'
        self.metrics_ttl = 3600  # 1 hour
        
        logger.info("TaskQueueManager initialized")
    
    def submit_task(self, task_name: str, args: List = None, kwargs: Dict = None,
                   queue: str = None, eta: datetime = None, expires: datetime = None,
                   retry_policy: Dict = None, user_id: int = None) -> str:
        """
        Submit a task to the queue
        
        Args:
            task_name: Name of the task
            args: Task arguments
            kwargs: Task keyword arguments
            queue: Queue name
            eta: Estimated time of arrival
            expires: Task expiration time
            retry_policy: Retry policy
            user_id: User ID for tracking
            
        Returns:
            Task ID
        """
        try:
            # Prepare task options
            task_options = {}
            
            if queue:
                task_options['queue'] = queue
            
            if eta:
                task_options['eta'] = eta
            
            if expires:
                task_options['expires'] = expires
            
            if retry_policy:
                task_options.update(retry_policy)
            
            # Submit task
            result = self.celery_app.send_task(
                task_name,
                args=args or [],
                kwargs=kwargs or {},
                **task_options
            )
            
            task_id = result.id
            
            # Cache task info
            task_info = TaskInfo(
                task_id=task_id,
                name=task_name,
                status=TaskStatus.PENDING,
                created_at=datetime.utcnow(),
                queue=queue,
                eta=eta,
                expires=expires,
                args=args,
                kwargs=kwargs
            )
            
            self._cache_task_info(task_info)
            
            # Update metrics
            self._update_task_metrics('submitted', task_name, user_id)
            
            # Log task submission
            system_logger.info('task_submitted', 
                             f'Task submitted: {task_name} ({task_id})',
                             task_id=task_id,
                             user_email=self._get_user_email(user_id) if user_id else None,
                             details={
                                 'task_name': task_name,
                                 'queue': queue,
                                 'user_id': user_id
                             })
            
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to submit task {task_name}: {e}")
            raise
    
    def get_task_info(self, task_id: str) -> Optional[TaskInfo]:
        """Get task information"""
        try:
            # Try to get from cache first
            cached_info = self.redis.get(f"task_info:{task_id}", prefix=self.task_cache_prefix)
            if cached_info:
                return TaskInfo(**cached_info)
            
            # Get from Celery
            result = AsyncResult(task_id, app=self.celery_app)
            
            if result.state == 'PENDING':
                return None
            
            # Create TaskInfo from result
            task_info = TaskInfo(
                task_id=task_id,
                name=result.name or 'unknown',
                status=TaskStatus(result.state),
                created_at=datetime.utcnow(),  # Approximate
                result=result.result,
                error=str(result.result) if result.state == 'FAILURE' else None
            )
            
            # Update cache
            self._cache_task_info(task_info)
            
            return task_info
            
        except Exception as e:
            logger.error(f"Failed to get task info for {task_id}: {e}")
            return None
    
    def get_task_result(self, task_id: str, timeout: Optional[float] = None) -> Tuple[bool, Any]:
        """
        Get task result
        
        Args:
            task_id: Task ID
            timeout: Wait timeout in seconds
            
        Returns:
            Tuple of (success, result)
        """
        try:
            result = AsyncResult(task_id, app=self.celery_app)
            
            if timeout:
                # Wait for result with timeout
                try:
                    task_result = result.get(timeout=timeout)
                    return True, task_result
                except Exception as e:
                    return False, str(e)
            else:
                # Get current result
                if result.ready():
                    if result.successful():
                        return True, result.result
                    else:
                        return False, str(result.result)
                else:
                    return False, "Task not ready"
                    
        except Exception as e:
            logger.error(f"Failed to get task result for {task_id}: {e}")
            return False, str(e)
    
    def cancel_task(self, task_id: str, user_id: int = None) -> bool:
        """Cancel a task"""
        try:
            # Revoke task
            self.celery_app.control.revoke(task_id, terminate=True)
            
            # Update task info
            task_info = self.get_task_info(task_id)
            if task_info:
                task_info.status = TaskStatus.REVOKED
                task_info.completed_at = datetime.utcnow()
                self._cache_task_info(task_info)
            
            # Update metrics
            self._update_task_metrics('cancelled', task_info.name if task_info else 'unknown', user_id)
            
            # Log cancellation
            system_logger.info('task_cancelled', 
                             f'Task cancelled: {task_id}',
                             task_id=task_id,
                             user_email=self._get_user_email(user_id) if user_id else None)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False
    
    def get_queue_stats(self, queue: str = None) -> Dict[str, Any]:
        """Get queue statistics"""
        try:
            # Get active tasks
            active_tasks = self.control.inspect().active()
            
            # Get scheduled tasks
            scheduled_tasks = self.control.inspect().scheduled()
            
            # Get reserved tasks
            reserved_tasks = self.control.inspect().reserved()
            
            # Aggregate stats
            stats = {
                'active_tasks': 0,
                'scheduled_tasks': 0,
                'reserved_tasks': 0,
                'workers': []
            }
            
            if active_tasks:
                for worker, tasks in active_tasks.items():
                    worker_stats = {
                        'worker': worker,
                        'active_tasks': len(tasks),
                        'tasks': tasks
                    }
                    
                    if queue:
                        # Filter by queue
                        worker_stats['active_tasks'] = len([t for t in tasks if t.get('delivery_info', {}).get('routing_key') == queue])
                    
                    stats['workers'].append(worker_stats)
                    stats['active_tasks'] += worker_stats['active_tasks']
            
            if scheduled_tasks:
                for worker, tasks in scheduled_tasks.items():
                    scheduled_count = len(tasks)
                    if queue:
                        scheduled_count = len([t for t in tasks if t.get('delivery_info', {}).get('routing_key') == queue])
                    stats['scheduled_tasks'] += scheduled_count
            
            if reserved_tasks:
                for worker, tasks in reserved_tasks.items():
                    reserved_count = len(tasks)
                    if queue:
                        reserved_count = len([t for t in tasks if t.get('delivery_info', {}).get('routing_key') == queue])
                    stats['reserved_tasks'] += reserved_count
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {}
    
    def get_worker_stats(self) -> Dict[str, Any]:
        """Get worker statistics"""
        try:
            # Get worker stats
            stats = self.control.inspect().stats()
            
            # Get worker info
            info = self.control.inspect().info()
            
            # Get registered tasks
            registered = self.control.inspect().registered()
            
            worker_stats = {}
            
            if stats:
                for worker, worker_data in stats.items():
                    worker_stats[worker] = {
                        'broker': worker_data.get('broker', {}),
                        'pool': worker_data.get('pool', {}),
                        'rusage': worker_data.get('rusage', {}),
                        'total_tasks': worker_data.get('total', {})
                    }
            
            if info:
                for worker, worker_info in info.items():
                    if worker not in worker_stats:
                        worker_stats[worker] = {}
                    
                    worker_stats[worker]['info'] = {
                        'hostname': worker_info.get('hostname'),
                        'pid': worker_info.get('pid'),
                        'software_version': worker_info.get('sw_ver'),
                        'software_identity': worker_info.get('sw_ident'),
                        'clock': worker_info.get('clock'),
                        'loadavg': worker_info.get('loadavg')
                    }
            
            if registered:
                for worker, tasks in registered.items():
                    if worker not in worker_stats:
                        worker_stats[worker] = {}
                    
                    worker_stats[worker]['registered_tasks'] = tasks
            
            return worker_stats
            
        except Exception as e:
            logger.error(f"Failed to get worker stats: {e}")
            return {}
    
    def get_task_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get task metrics for the specified time period"""
        try:
            # Get metrics from cache
            metrics_key = f"metrics:{hours}h"
            cached_metrics = self.redis.get(metrics_key, prefix=self.metrics_prefix)
            
            if cached_metrics:
                return cached_metrics
            
            # Calculate metrics (this is a simplified version)
            # In a real implementation, you'd track these metrics over time
            metrics = {
                'total_tasks': 0,
                'successful_tasks': 0,
                'failed_tasks': 0,
                'cancelled_tasks': 0,
                'avg_processing_time': 0.0,
                'tasks_by_type': {},
                'tasks_by_queue': {},
                'tasks_by_hour': {},
                'success_rate': 0.0,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Cache metrics
            self.redis.set(metrics_key, metrics, ttl=self.metrics_ttl, prefix=self.metrics_prefix)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get task metrics: {e}")
            return {}
    
    def purge_queue(self, queue: str) -> bool:
        """Purge all tasks from a queue"""
        try:
            # Purge queue
            self.celery_app.control.purge()
            
            # Log purge
            system_logger.warning('queue_purged', f'Queue purged: {queue}')
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to purge queue {queue}: {e}")
            return False
    
    def get_failed_tasks(self, limit: int = 50) -> List[TaskInfo]:
        """Get failed tasks"""
        try:
            # This is a simplified implementation
            # In production, you'd track failed tasks in a database or Redis
            failed_tasks = []
            
            # Get from cache or database
            # ... implementation depends on your storage strategy
            
            return failed_tasks
            
        except Exception as e:
            logger.error(f"Failed to get failed tasks: {e}")
            return []
    
    def retry_failed_task(self, task_id: str, user_id: int = None) -> bool:
        """Retry a failed task"""
        try:
            # Get task info
            task_info = self.get_task_info(task_id)
            if not task_info:
                return False
            
            # Submit retry
            new_task_id = self.submit_task(
                task_name=task_info.name,
                args=task_info.args,
                kwargs=task_info.kwargs,
                queue=task_info.queue,
                user_id=user_id
            )
            
            # Log retry
            system_logger.info('task_retry_manual', 
                             f'Task retry submitted: {task_id} -> {new_task_id}',
                             task_id=new_task_id,
                             user_email=self._get_user_email(user_id) if user_id else None)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to retry task {task_id}: {e}")
            return False
    
    def get_task_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task progress"""
        try:
            result = AsyncResult(task_id, app=self.celery_app)
            
            if result.state == 'PROCESSING':
                return result.info
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get task progress for {task_id}: {e}")
            return None
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on task queue system"""
        try:
            start_time = datetime.now()
            
            # Check Celery connectivity
            celery_healthy = True
            try:
                # Test basic Celery operations
                self.control.inspect().ping()
            except Exception as e:
                celery_healthy = False
                logger.error(f"Celery health check failed: {e}")
            
            # Check Redis connectivity (used as broker)
            redis_healthy = redis_service.is_connected()
            
            # Get basic stats
            try:
                queue_stats = self.get_queue_stats()
                worker_stats = self.get_worker_stats()
            except Exception as e:
                queue_stats = {}
                worker_stats = {}
                logger.error(f"Failed to get queue/worker stats: {e}")
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            health_status = {
                'healthy': celery_healthy and redis_healthy,
                'celery_healthy': celery_healthy,
                'redis_healthy': redis_healthy,
                'response_time_ms': response_time,
                'active_workers': len(worker_stats),
                'total_active_tasks': queue_stats.get('active_tasks', 0),
                'total_scheduled_tasks': queue_stats.get('scheduled_tasks', 0),
                'timestamp': datetime.now().isoformat()
            }
            
            return health_status
            
        except Exception as e:
            logger.error(f"Task queue health check failed: {e}")
            return {
                'healthy': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _cache_task_info(self, task_info: TaskInfo):
        """Cache task information"""
        try:
            # Convert to dict for serialization
            task_data = {
                'task_id': task_info.task_id,
                'name': task_info.name,
                'status': task_info.status.value,
                'created_at': task_info.created_at.isoformat(),
                'started_at': task_info.started_at.isoformat() if task_info.started_at else None,
                'completed_at': task_info.completed_at.isoformat() if task_info.completed_at else None,
                'result': task_info.result,
                'error': task_info.error,
                'retry_count': task_info.retry_count,
                'progress': task_info.progress,
                'worker': task_info.worker,
                'queue': task_info.queue,
                'eta': task_info.eta.isoformat() if task_info.eta else None,
                'expires': task_info.expires.isoformat() if task_info.expires else None,
                'args': task_info.args,
                'kwargs': task_info.kwargs,
                'runtime': task_info.runtime
            }
            
            self.redis.set(f"task_info:{task_info.task_id}", task_data, 
                          ttl=self.task_ttl, prefix=self.task_cache_prefix)
            
        except Exception as e:
            logger.error(f"Failed to cache task info: {e}")
    
    def _update_task_metrics(self, event: str, task_name: str, user_id: int = None):
        """Update task metrics"""
        try:
            # Update metrics in Redis
            metrics_key = f"metrics:{event}:{task_name}"
            self.redis.increment(metrics_key, prefix=self.metrics_prefix)
            
            # Set expiration for metrics
            self.redis.expire(metrics_key, self.metrics_ttl, prefix=self.metrics_prefix)
            
        except Exception as e:
            logger.error(f"Failed to update task metrics: {e}")
    
    def _get_user_email(self, user_id: int) -> Optional[str]:
        """Get user email for logging"""
        try:
            from database import db
            user = db.get_user_by_id(user_id)
            return user['email'] if user else None
        except:
            return None


# Global task queue manager instance
task_queue_manager = TaskQueueManager()


if __name__ == '__main__':
    # Test task queue manager
    logger.info("Testing Task Queue Manager...")
    
    # Test health check
    health = task_queue_manager.health_check()
    print(f"Health check: {health}")
    
    # Test queue stats
    stats = task_queue_manager.get_queue_stats()
    print(f"Queue stats: {stats}")
    
    # Test worker stats
    worker_stats = task_queue_manager.get_worker_stats()
    print(f"Worker stats: {worker_stats}")
    
    logger.info("Task Queue Manager test completed!")