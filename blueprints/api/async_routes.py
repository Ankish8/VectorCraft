"""
Async API routes for VectorCraft
"""

import os
import uuid
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from services.api_service import api_service
from services.task_queue_manager import task_queue_manager
from services.security_service import security_service
from services.monitoring.system_logger import system_logger
from services.file_service import file_service

logger = logging.getLogger(__name__)

# Create blueprint
async_bp = Blueprint('async_api', __name__, url_prefix='/api/async')


@async_bp.route('/vectorize', methods=['POST'])
@login_required
@api_service.rate_limit(limit=20, window=3600)  # 20 requests per hour
@api_service.validate_request(file_required=True)
def async_vectorize():
    """
    Submit image vectorization task asynchronously
    
    Returns:
        JSON response with task ID for tracking
    """
    try:
        file = request.files['file']
        filename = secure_filename(file.filename)
        
        # Get parameters
        strategy = request.form.get('strategy', 'vtracer_high_fidelity')
        target_time = float(request.form.get('target_time', 60.0))
        use_palette = request.form.get('use_palette', 'false').lower() == 'true'
        selected_palette = None
        
        if use_palette and request.form.get('selected_palette'):
            try:
                selected_palette = json.loads(request.form.get('selected_palette'))
            except json.JSONDecodeError:
                return jsonify({'error': 'Invalid palette format'}), 400
        
        # Parse vectorization parameters
        vectorization_params = {
            'filter_speckle': int(request.form.get('filter_speckle', 4)),
            'color_precision': int(request.form.get('color_precision', 8)),
            'layer_difference': int(request.form.get('layer_difference', 8)),
            'corner_threshold': int(request.form.get('corner_threshold', 90)),
            'length_threshold': float(request.form.get('length_threshold', 1.0)),
            'splice_threshold': int(request.form.get('splice_threshold', 20)),
            'curve_fitting': request.form.get('curve_fitting', 'spline')
        }
        
        # Save uploaded file temporarily
        unique_id = str(uuid.uuid4())
        temp_filename = f"temp_{unique_id}_{filename}"
        temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], temp_filename)
        file.save(temp_path)
        
        # Security validation
        is_valid, sanitized_path, error_message = security_service.validate_and_sanitize_upload(
            temp_path, filename
        )
        
        if not is_valid:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({'error': f'File validation failed: {error_message}'}), 400
        
        # Submit async task
        result = api_service.async_vectorize(
            user_id=int(current_user.id),
            file_path=sanitized_path,
            filename=filename,
            strategy=strategy,
            target_time=target_time,
            vectorization_params=vectorization_params,
            use_palette=use_palette,
            selected_palette=selected_palette
        )
        
        if result['success']:
            # Log task submission
            system_logger.info('async_vectorization', 
                             f'Async vectorization task submitted by {current_user.username}',
                             user_email=current_user.email,
                             task_id=result['task_id'],
                             details={
                                 'filename': filename,
                                 'strategy': strategy,
                                 'user_id': current_user.id
                             })
            
            return jsonify({
                'success': True,
                'task_id': result['task_id'],
                'status': 'submitted',
                'message': 'Vectorization task submitted successfully',
                'estimated_time': result['estimated_time'],
                'tracking_url': f'/api/async/status/{result["task_id"]}'
            })
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"Async vectorization failed: {e}")
        return jsonify({'error': str(e)}), 500


@async_bp.route('/batch-vectorize', methods=['POST'])
@login_required
@api_service.rate_limit(limit=5, window=3600)  # 5 batch requests per hour
def async_batch_vectorize():
    """
    Submit batch vectorization task asynchronously
    
    Returns:
        JSON response with task ID for tracking
    """
    try:
        # Check if files were uploaded
        if 'files' not in request.files:
            return jsonify({'error': 'No files uploaded'}), 400
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'error': 'No files selected'}), 400
        
        # Validate batch size
        if len(files) > api_service.max_batch_size:
            return jsonify({
                'error': f'Batch size exceeds maximum ({api_service.max_batch_size})'
            }), 400
        
        # Get parameters
        strategy = request.form.get('strategy', 'vtracer_high_fidelity')
        target_time = float(request.form.get('target_time', 60.0))
        
        # Parse vectorization parameters
        vectorization_params = {
            'filter_speckle': int(request.form.get('filter_speckle', 4)),
            'color_precision': int(request.form.get('color_precision', 8)),
            'layer_difference': int(request.form.get('layer_difference', 8)),
            'corner_threshold': int(request.form.get('corner_threshold', 90)),
            'length_threshold': float(request.form.get('length_threshold', 1.0)),
            'splice_threshold': int(request.form.get('splice_threshold', 20)),
            'curve_fitting': request.form.get('curve_fitting', 'spline')
        }
        
        # Save uploaded files temporarily
        file_paths = []
        filenames = []
        
        for file in files:
            if file.filename != '':
                filename = secure_filename(file.filename)
                unique_id = str(uuid.uuid4())
                temp_filename = f"batch_{unique_id}_{filename}"
                temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], temp_filename)
                file.save(temp_path)
                
                # Security validation
                is_valid, sanitized_path, error_message = security_service.validate_and_sanitize_upload(
                    temp_path, filename
                )
                
                if not is_valid:
                    # Clean up all temp files
                    for path in file_paths:
                        if os.path.exists(path):
                            os.remove(path)
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    
                    return jsonify({
                        'error': f'File validation failed for {filename}: {error_message}'
                    }), 400
                
                file_paths.append(sanitized_path)
                filenames.append(filename)
        
        # Submit batch task
        result = api_service.async_batch_vectorize(
            user_id=int(current_user.id),
            file_paths=file_paths,
            filenames=filenames,
            strategy=strategy,
            target_time=target_time,
            vectorization_params=vectorization_params
        )
        
        if result['success']:
            # Log batch submission
            system_logger.info('async_batch_vectorization', 
                             f'Batch vectorization task submitted by {current_user.username}',
                             user_email=current_user.email,
                             task_id=result['task_id'],
                             details={
                                 'total_files': len(filenames),
                                 'filenames': filenames,
                                 'strategy': strategy,
                                 'user_id': current_user.id
                             })
            
            return jsonify({
                'success': True,
                'task_id': result['task_id'],
                'status': 'submitted',
                'message': 'Batch vectorization task submitted successfully',
                'total_files': result['total_files'],
                'estimated_time': result['estimated_time'],
                'tracking_url': f'/api/async/status/{result["task_id"]}'
            })
        else:
            # Clean up files on failure
            for path in file_paths:
                if os.path.exists(path):
                    os.remove(path)
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"Async batch vectorization failed: {e}")
        return jsonify({'error': str(e)}), 500


@async_bp.route('/extract-palettes', methods=['POST'])
@login_required
@api_service.rate_limit(limit=30, window=3600)  # 30 requests per hour
@api_service.validate_request(file_required=True)
def async_extract_palettes():
    """
    Submit palette extraction task asynchronously
    
    Returns:
        JSON response with task ID for tracking
    """
    try:
        file = request.files['file']
        filename = secure_filename(file.filename)
        
        # Save uploaded file temporarily
        unique_id = str(uuid.uuid4())
        temp_filename = f"palette_{unique_id}_{filename}"
        temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], temp_filename)
        file.save(temp_path)
        
        # Security validation
        is_valid, sanitized_path, error_message = security_service.validate_and_sanitize_upload(
            temp_path, filename
        )
        
        if not is_valid:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({'error': f'File validation failed: {error_message}'}), 400
        
        # Submit async task
        result = api_service.async_extract_palettes(
            file_path=sanitized_path,
            filename=filename
        )
        
        if result['success']:
            # Log task submission
            system_logger.info('async_palette_extraction', 
                             f'Palette extraction task submitted by {current_user.username}',
                             user_email=current_user.email,
                             task_id=result['task_id'],
                             details={
                                 'filename': filename,
                                 'user_id': current_user.id
                             })
            
            return jsonify({
                'success': True,
                'task_id': result['task_id'],
                'status': 'submitted',
                'message': 'Palette extraction task submitted successfully',
                'tracking_url': f'/api/async/status/{result["task_id"]}'
            })
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"Async palette extraction failed: {e}")
        return jsonify({'error': str(e)}), 500


@async_bp.route('/status/<task_id>', methods=['GET'])
@login_required
@api_service.rate_limit(limit=100, window=3600)  # 100 status checks per hour
def get_task_status(task_id: str):
    """
    Get task status and progress
    
    Args:
        task_id: Task ID to check
        
    Returns:
        JSON response with task status
    """
    try:
        result = api_service.get_task_status(task_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 404
            
    except Exception as e:
        logger.error(f"Failed to get task status for {task_id}: {e}")
        return jsonify({'error': str(e)}), 500


@async_bp.route('/result/<task_id>', methods=['GET'])
@login_required
@api_service.rate_limit(limit=50, window=3600)  # 50 result requests per hour
def get_task_result(task_id: str):
    """
    Get task result
    
    Args:
        task_id: Task ID to get result for
        
    Returns:
        JSON response with task result
    """
    try:
        timeout = request.args.get('timeout', type=float)
        result = api_service.get_task_result(task_id, timeout)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Failed to get task result for {task_id}: {e}")
        return jsonify({'error': str(e)}), 500


@async_bp.route('/cancel/<task_id>', methods=['POST'])
@login_required
@api_service.rate_limit(limit=20, window=3600)  # 20 cancellations per hour
def cancel_task(task_id: str):
    """
    Cancel a task
    
    Args:
        task_id: Task ID to cancel
        
    Returns:
        JSON response with cancellation result
    """
    try:
        result = api_service.cancel_task(task_id, int(current_user.id))
        
        if result['success']:
            # Log task cancellation
            system_logger.info('task_cancellation', 
                             f'Task cancelled by {current_user.username}',
                             user_email=current_user.email,
                             task_id=task_id,
                             details={'user_id': current_user.id})
            
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        return jsonify({'error': str(e)}), 500


@async_bp.route('/queue-stats', methods=['GET'])
@login_required
@api_service.rate_limit(limit=30, window=3600)  # 30 requests per hour
def get_queue_stats():
    """
    Get queue statistics
    
    Returns:
        JSON response with queue statistics
    """
    try:
        queue = request.args.get('queue')
        stats = task_queue_manager.get_queue_stats(queue)
        
        return jsonify({
            'success': True,
            'queue_stats': stats,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get queue stats: {e}")
        return jsonify({'error': str(e)}), 500


@async_bp.route('/user-tasks', methods=['GET'])
@login_required
@api_service.rate_limit(limit=20, window=3600)  # 20 requests per hour
def get_user_tasks():
    """
    Get user's task history
    
    Returns:
        JSON response with user tasks
    """
    try:
        # This is a placeholder - you would implement user task tracking
        # based on your database schema
        
        # For now, return empty list
        return jsonify({
            'success': True,
            'tasks': [],
            'message': 'User task history not yet implemented'
        })
        
    except Exception as e:
        logger.error(f"Failed to get user tasks: {e}")
        return jsonify({'error': str(e)}), 500


@async_bp.route('/metrics', methods=['GET'])
@login_required
@api_service.rate_limit(limit=10, window=3600)  # 10 requests per hour
def get_api_metrics():
    """
    Get API metrics (admin only)
    
    Returns:
        JSON response with API metrics
    """
    try:
        # Check if user is admin
        if current_user.username != 'admin' and 'admin' not in current_user.email.lower():
            return jsonify({'error': 'Admin access required'}), 403
        
        result = api_service.get_api_metrics()
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"Failed to get API metrics: {e}")
        return jsonify({'error': str(e)}), 500


@async_bp.route('/cache/invalidate', methods=['POST'])
@login_required
@api_service.rate_limit(limit=5, window=3600)  # 5 requests per hour
def invalidate_cache():
    """
    Invalidate cache entries (admin only)
    
    Returns:
        JSON response with invalidation result
    """
    try:
        # Check if user is admin
        if current_user.username != 'admin' and 'admin' not in current_user.email.lower():
            return jsonify({'error': 'Admin access required'}), 403
        
        data = request.get_json() or {}
        pattern = data.get('pattern')
        prefix = data.get('prefix', 'api_cache')
        
        result = api_service.invalidate_cache(pattern, prefix)
        
        if result['success']:
            # Log cache invalidation
            system_logger.info('cache_invalidation', 
                             f'Cache invalidated by {current_user.username}',
                             user_email=current_user.email,
                             details={
                                 'pattern': pattern,
                                 'prefix': prefix,
                                 'user_id': current_user.id
                             })
            
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"Failed to invalidate cache: {e}")
        return jsonify({'error': str(e)}), 500


@async_bp.route('/health', methods=['GET'])
@api_service.cache_response(key='async_health', ttl=60)
def health_check():
    """
    Health check for async API
    
    Returns:
        JSON response with health status
    """
    try:
        result = api_service.get_system_health()
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"Async API health check failed: {e}")
        return jsonify({'error': str(e)}), 500


# Error handlers for async blueprint
@async_bp.errorhandler(413)
def request_entity_too_large(error):
    """Handle request entity too large errors"""
    return jsonify({
        'error': 'Request entity too large',
        'message': 'The uploaded file is too large'
    }), 413


@async_bp.errorhandler(400)
def bad_request(error):
    """Handle bad request errors"""
    return jsonify({
        'error': 'Bad request',
        'message': 'Invalid request format or parameters'
    }), 400


@async_bp.errorhandler(429)
def rate_limit_exceeded(error):
    """Handle rate limit exceeded errors"""
    return jsonify({
        'error': 'Rate limit exceeded',
        'message': 'Too many requests. Please try again later.'
    }), 429


@async_bp.errorhandler(500)
def internal_server_error(error):
    """Handle internal server errors"""
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500