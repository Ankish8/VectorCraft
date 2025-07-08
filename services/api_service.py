"""
API Service Layer with caching and optimization
"""

import os
import json
import time
import hashlib
import logging
from functools import wraps
from typing import Dict, Any, Optional, List, Tuple, Callable
from datetime import datetime, timedelta

from flask import request, jsonify, current_app
from werkzeug.exceptions import RequestEntityTooLarge

from services.redis_service import redis_service
from services.task_queue_manager import task_queue_manager
from services.vectorization_service import vectorization_service
from services.monitoring.system_logger import system_logger

logger = logging.getLogger(__name__)


class APIService:
    """Service layer for API operations with caching and optimization"""
    
    def __init__(self):
        self.redis = redis_service
        self.task_manager = task_queue_manager
        self.vectorization_service = vectorization_service
        
        # Cache configuration
        self.cache_ttl = {
            'short': 300,      # 5 minutes
            'medium': 3600,    # 1 hour
            'long': 86400,     # 24 hours
            'very_long': 604800  # 7 days
        }
        
        # API limits
        self.max_file_size = 16 * 1024 * 1024  # 16MB
        self.max_batch_size = 10
        self.allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
        
        # Response compression threshold
        self.compression_threshold = 1024  # bytes
        
        logger.info("API Service initialized")
    
    def cache_response(self, key: str, ttl: int = None, prefix: str = 'api_cache'):
        """
        Decorator to cache API responses
        
        Args:
            key: Cache key template (can use placeholders)
            ttl: Time to live in seconds
            prefix: Cache key prefix
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    # Generate cache key
                    cache_key = self._generate_cache_key(key, args, kwargs)
                    
                    # Try to get from cache
                    cached_response = self.redis.get(cache_key, prefix=prefix)
                    if cached_response:
                        logger.debug(f"Cache hit for key: {cache_key}")
                        return cached_response
                    
                    # Execute function
                    response = func(*args, **kwargs)
                    
                    # Cache response
                    cache_ttl = ttl or self.cache_ttl['medium']
                    self.redis.set(cache_key, response, ttl=cache_ttl, prefix=prefix)
                    
                    logger.debug(f"Response cached for key: {cache_key}")
                    
                    return response
                    
                except Exception as e:
                    logger.error(f"Cache error in {func.__name__}: {e}")
                    # Execute function without caching
                    return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def rate_limit(self, limit: int, window: int = 3600, key_func: Callable = None):
        """
        Rate limiting decorator
        
        Args:
            limit: Maximum requests per window
            window: Time window in seconds
            key_func: Function to generate rate limit key
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    # Generate rate limit key
                    if key_func:
                        rate_key = key_func(*args, **kwargs)
                    else:
                        rate_key = f"rate_limit:{request.remote_addr}:{func.__name__}"
                    
                    # Check current count
                    current_count = self.redis.get(rate_key, prefix='rate_limit') or 0
                    
                    if current_count >= limit:
                        return jsonify({
                            'error': 'Rate limit exceeded',
                            'limit': limit,
                            'window': window,
                            'retry_after': self.redis.ttl(rate_key, prefix='rate_limit')
                        }), 429
                    
                    # Execute function
                    response = func(*args, **kwargs)
                    
                    # Update count
                    if current_count == 0:
                        self.redis.set(rate_key, 1, ttl=window, prefix='rate_limit')
                    else:
                        self.redis.increment(rate_key, prefix='rate_limit')
                    
                    return response
                    
                except Exception as e:
                    logger.error(f"Rate limit error in {func.__name__}: {e}")
                    return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def validate_request(self, required_fields: List[str] = None, 
                        file_required: bool = False, 
                        max_file_size: int = None):
        """
        Request validation decorator
        
        Args:
            required_fields: List of required fields
            file_required: Whether file upload is required
            max_file_size: Maximum file size in bytes
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    # Validate required fields
                    if required_fields:
                        missing_fields = []
                        for field in required_fields:
                            if field not in request.form and field not in request.json:
                                missing_fields.append(field)
                        
                        if missing_fields:
                            return jsonify({
                                'error': 'Missing required fields',
                                'missing_fields': missing_fields
                            }), 400
                    
                    # Validate file upload
                    if file_required:
                        if 'file' not in request.files:
                            return jsonify({'error': 'No file uploaded'}), 400
                        
                        file = request.files['file']
                        if file.filename == '':
                            return jsonify({'error': 'No file selected'}), 400
                        
                        # Check file extension
                        if not self._allowed_file(file.filename):
                            return jsonify({
                                'error': 'Invalid file type',
                                'allowed_types': list(self.allowed_extensions)
                            }), 400
                        
                        # Check file size
                        file_size = max_file_size or self.max_file_size
                        if hasattr(file, 'content_length') and file.content_length > file_size:
                            return jsonify({
                                'error': 'File too large',
                                'max_size': file_size
                            }), 413
                    
                    return func(*args, **kwargs)
                    
                except RequestEntityTooLarge:
                    return jsonify({
                        'error': 'File too large',
                        'max_size': max_file_size or self.max_file_size
                    }), 413
                except Exception as e:
                    logger.error(f"Request validation error in {func.__name__}: {e}")
                    return jsonify({'error': 'Request validation failed'}), 400
            
            return wrapper
        return decorator
    
    def async_vectorize(self, user_id: int, file_path: str, filename: str,
                       strategy: str = 'vtracer_high_fidelity', 
                       target_time: float = 60.0,
                       vectorization_params: Dict[str, Any] = None,
                       use_palette: bool = False,
                       selected_palette: List[List[int]] = None) -> Dict[str, Any]:
        """
        Submit vectorization task asynchronously
        
        Args:
            user_id: User ID
            file_path: Path to the image file
            filename: Original filename
            strategy: Vectorization strategy
            target_time: Target processing time
            vectorization_params: Custom vectorization parameters
            use_palette: Whether to use custom palette
            selected_palette: Custom color palette
            
        Returns:
            Dict containing task information
        """
        try:
            # Submit task to queue
            task_id = self.task_manager.submit_task(
                task_name='vectorization_tasks.vectorize_image',
                args=[user_id, file_path, filename],
                kwargs={
                    'strategy': strategy,
                    'target_time': target_time,
                    'vectorization_params': vectorization_params,
                    'use_palette': use_palette,
                    'selected_palette': selected_palette
                },
                queue='vectorization',
                user_id=user_id
            )
            
            return {
                'success': True,
                'task_id': task_id,
                'status': 'submitted',
                'estimated_time': target_time,
                'message': 'Vectorization task submitted successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to submit async vectorization task: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def async_batch_vectorize(self, user_id: int, file_paths: List[str], 
                             filenames: List[str],
                             strategy: str = 'vtracer_high_fidelity',
                             target_time: float = 60.0,
                             vectorization_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Submit batch vectorization task asynchronously
        
        Args:
            user_id: User ID
            file_paths: List of file paths
            filenames: List of original filenames
            strategy: Vectorization strategy
            target_time: Target processing time per file
            vectorization_params: Custom vectorization parameters
            
        Returns:
            Dict containing task information
        """
        try:
            # Validate batch size
            if len(file_paths) > self.max_batch_size:
                return {
                    'success': False,
                    'error': f'Batch size exceeds maximum ({self.max_batch_size})'
                }
            
            # Submit batch task to queue
            task_id = self.task_manager.submit_task(
                task_name='vectorization_tasks.batch_vectorize',
                args=[user_id, file_paths, filenames],
                kwargs={
                    'strategy': strategy,
                    'target_time': target_time,
                    'vectorization_params': vectorization_params
                },
                queue='batch_processing',
                user_id=user_id
            )
            
            return {
                'success': True,
                'task_id': task_id,
                'status': 'submitted',
                'total_files': len(file_paths),
                'estimated_time': target_time * len(file_paths),
                'message': 'Batch vectorization task submitted successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to submit batch vectorization task: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def async_extract_palettes(self, file_path: str, filename: str) -> Dict[str, Any]:
        """
        Submit palette extraction task asynchronously
        
        Args:
            file_path: Path to the image file
            filename: Original filename
            
        Returns:
            Dict containing task information
        """
        try:
            # Submit task to queue
            task_id = self.task_manager.submit_task(
                task_name='vectorization_tasks.extract_palettes',
                args=[file_path, filename],
                queue='image_analysis'
            )
            
            return {
                'success': True,
                'task_id': task_id,
                'status': 'submitted',
                'message': 'Palette extraction task submitted successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to submit palette extraction task: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get task status and progress
        
        Args:
            task_id: Task ID
            
        Returns:
            Dict containing task status
        """
        try:
            # Get task info
            task_info = self.task_manager.get_task_info(task_id)
            
            if not task_info:
                return {
                    'success': False,
                    'error': 'Task not found'
                }
            
            # Get progress if available
            progress = self.task_manager.get_task_progress(task_id)
            
            return {
                'success': True,
                'task_id': task_id,
                'status': task_info.status.value,
                'progress': progress,
                'created_at': task_info.created_at.isoformat(),
                'started_at': task_info.started_at.isoformat() if task_info.started_at else None,
                'completed_at': task_info.completed_at.isoformat() if task_info.completed_at else None,
                'error': task_info.error,
                'runtime': task_info.runtime
            }
            
        except Exception as e:
            logger.error(f"Failed to get task status for {task_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_task_result(self, task_id: str, timeout: float = None) -> Dict[str, Any]:
        """
        Get task result
        
        Args:
            task_id: Task ID
            timeout: Wait timeout in seconds
            
        Returns:
            Dict containing task result
        """
        try:
            success, result = self.task_manager.get_task_result(task_id, timeout)
            
            if success:
                return {
                    'success': True,
                    'task_id': task_id,
                    'result': result
                }
            else:
                return {
                    'success': False,
                    'task_id': task_id,
                    'error': result
                }
                
        except Exception as e:
            logger.error(f"Failed to get task result for {task_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cancel_task(self, task_id: str, user_id: int = None) -> Dict[str, Any]:
        """
        Cancel a task
        
        Args:
            task_id: Task ID
            user_id: User ID for authorization
            
        Returns:
            Dict containing cancellation result
        """
        try:
            success = self.task_manager.cancel_task(task_id, user_id)
            
            if success:
                return {
                    'success': True,
                    'task_id': task_id,
                    'message': 'Task cancelled successfully'
                }
            else:
                return {
                    'success': False,
                    'task_id': task_id,
                    'error': 'Failed to cancel task'
                }
                
        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @cache_response(key='user_uploads:{user_id}:{limit}', ttl=300)
    def get_user_uploads(self, user_id: int, limit: int = 20) -> Dict[str, Any]:
        """
        Get user's upload history (cached)
        
        Args:
            user_id: User ID
            limit: Maximum number of uploads to return
            
        Returns:
            Dict containing upload history
        """
        try:
            uploads = self.vectorization_service.get_user_uploads(user_id, limit)
            
            return {
                'success': True,
                'uploads': uploads,
                'count': len(uploads)
            }
            
        except Exception as e:
            logger.error(f"Failed to get user uploads for {user_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @cache_response(key='user_stats:{user_id}', ttl=600)
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get user's statistics (cached)
        
        Args:
            user_id: User ID
            
        Returns:
            Dict containing user statistics
        """
        try:
            stats = self.vectorization_service.get_user_upload_stats(user_id)
            
            return {
                'success': True,
                'stats': stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get user stats for {user_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @cache_response(key='supported_strategies', ttl=86400)
    def get_supported_strategies(self) -> Dict[str, Any]:
        """
        Get supported vectorization strategies (cached)
        
        Returns:
            Dict containing supported strategies
        """
        try:
            strategies = self.vectorization_service.get_supported_strategies()
            
            return {
                'success': True,
                'strategies': strategies
            }
            
        except Exception as e:
            logger.error(f"Failed to get supported strategies: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @cache_response(key='system_health', ttl=60)
    def get_system_health(self) -> Dict[str, Any]:
        """
        Get system health status (cached)
        
        Returns:
            Dict containing system health
        """
        try:
            # Check various system components
            health_status = {
                'overall_healthy': True,
                'components': {},
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Check task queue
            task_health = self.task_manager.health_check()
            health_status['components']['task_queue'] = task_health
            
            # Check Redis
            redis_health = self.redis.health_check()
            health_status['components']['redis'] = redis_health
            
            # Check vectorization service
            try:
                strategies = self.vectorization_service.get_supported_strategies()
                health_status['components']['vectorization'] = {
                    'healthy': len(strategies) > 0,
                    'strategies_available': len(strategies)
                }
            except Exception as e:
                health_status['components']['vectorization'] = {
                    'healthy': False,
                    'error': str(e)
                }
            
            # Update overall health
            health_status['overall_healthy'] = all(
                component.get('healthy', False) 
                for component in health_status['components'].values()
            )
            
            return {
                'success': True,
                'health': health_status
            }
            
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_api_metrics(self) -> Dict[str, Any]:
        """
        Get API metrics
        
        Returns:
            Dict containing API metrics
        """
        try:
            # Get task metrics
            task_metrics = self.task_manager.get_task_metrics()
            
            # Get queue stats
            queue_stats = self.task_manager.get_queue_stats()
            
            # Get worker stats
            worker_stats = self.task_manager.get_worker_stats()
            
            # Get Redis info
            redis_info = self.redis.get_info()
            
            return {
                'success': True,
                'metrics': {
                    'tasks': task_metrics,
                    'queues': queue_stats,
                    'workers': worker_stats,
                    'redis': redis_info,
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get API metrics: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def invalidate_cache(self, pattern: str = None, prefix: str = 'api_cache') -> Dict[str, Any]:
        """
        Invalidate cache entries
        
        Args:
            pattern: Cache key pattern to invalidate
            prefix: Cache prefix
            
        Returns:
            Dict containing invalidation result
        """
        try:
            if pattern:
                # Invalidate specific pattern
                keys = self.redis.keys(pattern, prefix=prefix)
                for key in keys:
                    self.redis.delete(key, prefix=prefix)
                
                return {
                    'success': True,
                    'invalidated_keys': len(keys)
                }
            else:
                # Flush entire prefix
                success = self.redis.flush_prefix(prefix)
                
                return {
                    'success': success,
                    'message': f'Cache prefix {prefix} flushed'
                }
                
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_cache_key(self, key_template: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key from template and arguments"""
        try:
            # Simple placeholder replacement
            cache_key = key_template
            
            # Replace placeholders with actual values
            for i, arg in enumerate(args):
                cache_key = cache_key.replace(f'{{{i}}}', str(arg))
            
            for k, v in kwargs.items():
                cache_key = cache_key.replace(f'{{{k}}}', str(v))
            
            # Add request parameters for uniqueness
            if hasattr(request, 'args'):
                request_params = dict(request.args)
                if request_params:
                    params_hash = hashlib.md5(
                        json.dumps(request_params, sort_keys=True).encode()
                    ).hexdigest()[:8]
                    cache_key = f"{cache_key}:{params_hash}"
            
            return cache_key
            
        except Exception as e:
            logger.error(f"Failed to generate cache key: {e}")
            return f"fallback_key:{int(time.time())}"
    
    def _allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions


# Global API service instance
api_service = APIService()


if __name__ == '__main__':
    # Test API service
    logger.info("Testing API service...")
    
    # Test system health
    health = api_service.get_system_health()
    print(f"System health: {health}")
    
    # Test supported strategies
    strategies = api_service.get_supported_strategies()
    print(f"Supported strategies: {strategies}")
    
    # Test metrics
    metrics = api_service.get_api_metrics()
    print(f"API metrics: {metrics}")
    
    logger.info("API service test completed!")