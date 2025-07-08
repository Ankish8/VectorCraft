"""
Celery tasks for VectorCraft async processing
"""

import os
import time
import uuid
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from celery import Celery, Task
from celery.signals import task_prerun, task_postrun, task_failure
from celery.exceptions import WorkerLostError, SoftTimeLimitExceeded, Retry

from celery_config import celery_app
from database import db
from services.vectorization_service import vectorization_service
from services.file_service import file_service
from services.monitoring.system_logger import system_logger

logger = logging.getLogger(__name__)

# Task state constants
TASK_STATES = {
    'PENDING': 'PENDING',
    'STARTED': 'STARTED',
    'PROCESSING': 'PROCESSING',
    'SUCCESS': 'SUCCESS',
    'FAILURE': 'FAILURE',
    'RETRY': 'RETRY',
    'REVOKED': 'REVOKED'
}

class VectorizationTask(Task):
    """Base class for vectorization tasks with enhanced error handling"""
    
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 60}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        logger.error(f"Task {task_id} failed: {exc}")
        
        # Log failure in monitoring system
        system_logger.error('task_failure', f'Task {task_id} failed: {str(exc)}', 
                           task_id=task_id, details={'exception': str(exc)})
        
        # Update task status in database if possible
        try:
            self.update_task_status(task_id, 'FAILURE', {'error': str(exc)})
        except Exception as e:
            logger.error(f"Failed to update task status for {task_id}: {e}")
    
    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success"""
        logger.info(f"Task {task_id} completed successfully")
        
        # Log success in monitoring system
        system_logger.info('task_success', f'Task {task_id} completed successfully',
                          task_id=task_id)
        
        # Update task status in database if possible
        try:
            self.update_task_status(task_id, 'SUCCESS', retval)
        except Exception as e:
            logger.error(f"Failed to update task status for {task_id}: {e}")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry"""
        logger.warning(f"Task {task_id} retry attempt: {exc}")
        
        # Log retry in monitoring system
        system_logger.warning('task_retry', f'Task {task_id} retry: {str(exc)}',
                            task_id=task_id, details={'exception': str(exc)})
        
        # Update task status in database if possible
        try:
            self.update_task_status(task_id, 'RETRY', {'error': str(exc)})
        except Exception as e:
            logger.error(f"Failed to update task status for {task_id}: {e}")
    
    def update_task_status(self, task_id: str, status: str, result: Dict[str, Any] = None):
        """Update task status in database"""
        try:
            # This would be implemented based on your database schema
            # For now, we'll just log it
            logger.info(f"Task {task_id} status updated to {status}")
            
            # You could add task tracking to your database here
            # db.update_task_status(task_id, status, result)
            
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")


@celery_app.task(bind=True, base=VectorizationTask, name='vectorization_tasks.vectorize_image')
def vectorize_image(self, user_id: int, file_path: str, filename: str, 
                   strategy: str = 'vtracer_high_fidelity', target_time: float = 60.0,
                   vectorization_params: Dict[str, Any] = None, 
                   use_palette: bool = False, selected_palette: List[List[int]] = None,
                   task_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Async task for vectorizing images
    
    Args:
        user_id: User ID
        file_path: Path to the image file
        filename: Original filename
        strategy: Vectorization strategy
        target_time: Target processing time
        vectorization_params: Custom vectorization parameters
        use_palette: Whether to use custom palette
        selected_palette: Custom color palette
        task_metadata: Additional task metadata
        
    Returns:
        Dict containing vectorization result
    """
    task_id = self.request.id
    
    try:
        # Update task state
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Starting vectorization...', 'progress': 0}
        )
        
        # Log task start
        system_logger.info('vectorization_task', 
                          f'Starting vectorization task {task_id}',
                          task_id=task_id,
                          user_email=db.get_user_by_id(user_id).get('email') if user_id else None,
                          details={
                              'filename': filename,
                              'strategy': strategy,
                              'user_id': user_id
                          })
        
        # Validate inputs
        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")
        
        if not user_id or user_id <= 0:
            raise ValueError("Invalid user ID")
        
        # Update progress
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Initializing vectorization...', 'progress': 10}
        )
        
        # Perform vectorization using the service
        success, result = vectorization_service.vectorize_image(
            user_id=user_id,
            file_path=file_path,
            filename=filename,
            strategy=strategy,
            target_time=target_time,
            vectorization_params=vectorization_params,
            use_palette=use_palette,
            selected_palette=selected_palette
        )
        
        if not success:
            raise ValueError(f"Vectorization failed: {result.get('error', 'Unknown error')}")
        
        # Update progress
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Finalizing result...', 'progress': 90}
        )
        
        # Add task metadata to result
        result['task_id'] = task_id
        result['completed_at'] = datetime.utcnow().isoformat()
        
        if task_metadata:
            result['task_metadata'] = task_metadata
        
        # Clean up temporary file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup temporary file {file_path}: {e}")
        
        # Log completion
        system_logger.info('vectorization_task', 
                          f'Vectorization task {task_id} completed successfully',
                          task_id=task_id,
                          user_email=db.get_user_by_id(user_id).get('email') if user_id else None,
                          details={
                              'processing_time': result.get('processing_time'),
                              'strategy': result.get('strategy_used'),
                              'quality_score': result.get('quality_score')
                          })
        
        return result
        
    except SoftTimeLimitExceeded:
        logger.error(f"Task {task_id} exceeded soft time limit")
        self.update_state(
            state='FAILURE',
            meta={'status': 'Task timed out', 'error': 'Processing time limit exceeded'}
        )
        raise
        
    except Exception as e:
        logger.error(f"Vectorization task {task_id} failed: {e}")
        
        # Clean up temporary file on error
        try:
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
        
        # Update task state
        self.update_state(
            state='FAILURE',
            meta={'status': 'Vectorization failed', 'error': str(e)}
        )
        
        raise


@celery_app.task(bind=True, base=VectorizationTask, name='vectorization_tasks.batch_vectorize')
def batch_vectorize(self, user_id: int, file_paths: List[str], filenames: List[str],
                   strategy: str = 'vtracer_high_fidelity', target_time: float = 60.0,
                   vectorization_params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Async task for batch vectorization of multiple images
    
    Args:
        user_id: User ID
        file_paths: List of file paths
        filenames: List of original filenames
        strategy: Vectorization strategy
        target_time: Target processing time per image
        vectorization_params: Custom vectorization parameters
        
    Returns:
        Dict containing batch processing results
    """
    task_id = self.request.id
    
    try:
        if len(file_paths) != len(filenames):
            raise ValueError("file_paths and filenames must have the same length")
        
        total_files = len(file_paths)
        results = []
        failed_files = []
        
        # Log batch start
        system_logger.info('batch_vectorization', 
                          f'Starting batch vectorization task {task_id}',
                          task_id=task_id,
                          user_email=db.get_user_by_id(user_id).get('email') if user_id else None,
                          details={
                              'total_files': total_files,
                              'strategy': strategy,
                              'user_id': user_id
                          })
        
        # Process each file
        for i, (file_path, filename) in enumerate(zip(file_paths, filenames)):
            try:
                # Update progress
                progress = int((i / total_files) * 100)
                self.update_state(
                    state='PROCESSING',
                    meta={
                        'status': f'Processing file {i+1}/{total_files}: {filename}',
                        'progress': progress,
                        'current_file': filename,
                        'completed_files': i,
                        'total_files': total_files
                    }
                )
                
                # Vectorize individual file
                success, result = vectorization_service.vectorize_image(
                    user_id=user_id,
                    file_path=file_path,
                    filename=filename,
                    strategy=strategy,
                    target_time=target_time,
                    vectorization_params=vectorization_params
                )
                
                if success:
                    results.append({
                        'filename': filename,
                        'status': 'success',
                        'result': result
                    })
                else:
                    failed_files.append({
                        'filename': filename,
                        'error': result.get('error', 'Unknown error')
                    })
                
            except Exception as e:
                logger.error(f"Failed to process file {filename}: {e}")
                failed_files.append({
                    'filename': filename,
                    'error': str(e)
                })
            
            # Clean up temporary file
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup temporary file {file_path}: {e}")
        
        # Compile final results
        batch_result = {
            'task_id': task_id,
            'total_files': total_files,
            'successful_files': len(results),
            'failed_files': len(failed_files),
            'results': results,
            'failures': failed_files,
            'completed_at': datetime.utcnow().isoformat()
        }
        
        # Log completion
        system_logger.info('batch_vectorization', 
                          f'Batch vectorization task {task_id} completed',
                          task_id=task_id,
                          user_email=db.get_user_by_id(user_id).get('email') if user_id else None,
                          details={
                              'total_files': total_files,
                              'successful_files': len(results),
                              'failed_files': len(failed_files)
                          })
        
        return batch_result
        
    except Exception as e:
        logger.error(f"Batch vectorization task {task_id} failed: {e}")
        
        # Clean up temporary files on error
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
        
        # Update task state
        self.update_state(
            state='FAILURE',
            meta={'status': 'Batch processing failed', 'error': str(e)}
        )
        
        raise


@celery_app.task(bind=True, base=VectorizationTask, name='vectorization_tasks.extract_palettes')
def extract_palettes(self, file_path: str, filename: str) -> Dict[str, Any]:
    """
    Async task for extracting color palettes from images
    
    Args:
        file_path: Path to the image file
        filename: Original filename
        
    Returns:
        Dict containing extracted palettes
    """
    task_id = self.request.id
    
    try:
        # Update task state
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Extracting color palettes...', 'progress': 0}
        )
        
        # Log task start
        system_logger.info('palette_extraction', 
                          f'Starting palette extraction task {task_id}',
                          task_id=task_id,
                          details={'filename': filename})
        
        # Validate input
        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")
        
        # Extract palettes using the service
        success, result = vectorization_service.extract_color_palettes(file_path)
        
        if not success:
            raise ValueError(f"Palette extraction failed: {result.get('error', 'Unknown error')}")
        
        # Add task metadata
        result['task_id'] = task_id
        result['filename'] = filename
        result['completed_at'] = datetime.utcnow().isoformat()
        
        # Clean up temporary file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup temporary file {file_path}: {e}")
        
        # Log completion
        system_logger.info('palette_extraction', 
                          f'Palette extraction task {task_id} completed',
                          task_id=task_id,
                          details={'filename': filename})
        
        return result
        
    except Exception as e:
        logger.error(f"Palette extraction task {task_id} failed: {e}")
        
        # Clean up temporary file on error
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
        
        # Update task state
        self.update_state(
            state='FAILURE',
            meta={'status': 'Palette extraction failed', 'error': str(e)}
        )
        
        raise


@celery_app.task(bind=True, name='vectorization_tasks.cleanup_old_files')
def cleanup_old_files(self, days_to_keep: int = 7) -> Dict[str, Any]:
    """
    Periodic task to clean up old files
    
    Args:
        days_to_keep: Number of days to keep files
        
    Returns:
        Dict containing cleanup results
    """
    task_id = self.request.id
    
    try:
        # Log cleanup start
        system_logger.info('file_cleanup', 
                          f'Starting file cleanup task {task_id}',
                          task_id=task_id,
                          details={'days_to_keep': days_to_keep})
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Directories to clean
        directories_to_clean = ['uploads', 'results', 'output']
        
        cleaned_files = []
        total_size_freed = 0
        
        for directory in directories_to_clean:
            if not os.path.exists(directory):
                continue
                
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    try:
                        # Check file age
                        file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        
                        if file_time < cutoff_date:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            
                            cleaned_files.append({
                                'path': file_path,
                                'size': file_size,
                                'age_days': (datetime.now() - file_time).days
                            })
                            
                            total_size_freed += file_size
                            
                    except Exception as e:
                        logger.warning(f"Failed to process file {file_path}: {e}")
        
        result = {
            'task_id': task_id,
            'files_cleaned': len(cleaned_files),
            'total_size_freed': total_size_freed,
            'cleaned_files': cleaned_files,
            'completed_at': datetime.utcnow().isoformat()
        }
        
        # Log completion
        system_logger.info('file_cleanup', 
                          f'File cleanup task {task_id} completed',
                          task_id=task_id,
                          details={
                              'files_cleaned': len(cleaned_files),
                              'total_size_freed': total_size_freed
                          })
        
        return result
        
    except Exception as e:
        logger.error(f"File cleanup task {task_id} failed: {e}")
        
        # Update task state
        self.update_state(
            state='FAILURE',
            meta={'status': 'File cleanup failed', 'error': str(e)}
        )
        
        raise


@celery_app.task(bind=True, name='vectorization_tasks.health_check')
def health_check(self) -> Dict[str, Any]:
    """
    Periodic health check task
    
    Returns:
        Dict containing health check results
    """
    task_id = self.request.id
    
    try:
        # Check system components
        health_results = {
            'database': True,
            'vectorization_service': True,
            'file_system': True,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Test database connection
        try:
            db.get_user_by_id(1)  # Simple test query
        except Exception as e:
            health_results['database'] = False
            health_results['database_error'] = str(e)
        
        # Test vectorization service
        try:
            vectorization_service.get_supported_strategies()
        except Exception as e:
            health_results['vectorization_service'] = False
            health_results['vectorization_error'] = str(e)
        
        # Test file system access
        try:
            os.makedirs('uploads', exist_ok=True)
            os.makedirs('results', exist_ok=True)
        except Exception as e:
            health_results['file_system'] = False
            health_results['file_system_error'] = str(e)
        
        # Overall health
        health_results['overall_health'] = all([
            health_results['database'],
            health_results['vectorization_service'],
            health_results['file_system']
        ])
        
        # Log health check
        system_logger.info('health_check', 
                          f'Health check completed - Status: {"healthy" if health_results["overall_health"] else "unhealthy"}',
                          task_id=task_id,
                          details=health_results)
        
        return health_results
        
    except Exception as e:
        logger.error(f"Health check task {task_id} failed: {e}")
        
        # Update task state
        self.update_state(
            state='FAILURE',
            meta={'status': 'Health check failed', 'error': str(e)}
        )
        
        raise


# Task signal handlers
@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    """Handle task prerun"""
    logger.info(f"Task {task_id} starting: {task.name}")


@task_postrun.connect
def task_postrun_handler(task_id, task, *args, **kwargs):
    """Handle task postrun"""
    logger.info(f"Task {task_id} finished: {task.name}")


@task_failure.connect
def task_failure_handler(task_id, exception, traceback, einfo):
    """Handle task failure"""
    logger.error(f"Task {task_id} failed: {exception}")
    
    # Log failure in monitoring system
    system_logger.error('task_failure', f'Task {task_id} failed: {str(exception)}',
                       task_id=task_id, details={'exception': str(exception)})


if __name__ == '__main__':
    # Test task execution
    logger.info("Testing Celery tasks...")
    
    # Test health check
    result = health_check.delay()
    print(f"Health check task started: {result.id}")
    
    logger.info("Celery tasks test completed!")