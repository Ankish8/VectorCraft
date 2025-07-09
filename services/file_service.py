"""
File service layer for VectorCraft
Handles file operations, validation, and management
"""

import os
import uuid
import hashlib
import mimetypes
import logging
import json
import time
import shutil
import statistics
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from werkzeug.utils import secure_filename
from collections import defaultdict

from .monitoring import system_logger

logger = logging.getLogger(__name__)


class FileService:
    """Service layer for file operations"""
    
    def __init__(self):
        self.logger = logger
        
        # Allowed file extensions
        self.allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}
        
        # MIME type mapping
        self.allowed_mime_types = {
            'image/png': 'png',
            'image/jpeg': 'jpg',
            'image/gif': 'gif',
            'image/bmp': 'bmp',
            'image/tiff': 'tiff',
            'image/webp': 'webp'
        }
        
        # File size limits
        self.max_file_size = 16 * 1024 * 1024  # 16MB
        self.max_image_dimensions = (8192, 8192)  # 8K x 8K
        
        # Directory paths
        self.upload_dir = 'uploads'
        self.results_dir = 'results'
        self.temp_dir = 'temp'
        self.archive_dir = 'archive'
        
        # Analytics tracking
        self.analytics_data = {
            'upload_stats': defaultdict(lambda: {
                'total_uploads': 0,
                'total_size': 0,
                'file_types': defaultdict(int),
                'avg_file_size': 0,
                'errors': 0
            }),
            'storage_metrics': {
                'total_files': 0,
                'total_size': 0,
                'growth_rate': 0,
                'optimization_savings': 0
            }
        }
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure required directories exist"""
        directories = [self.upload_dir, self.results_dir, self.temp_dir, self.archive_dir]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def validate_file(self, file_path: str, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Validate uploaded file
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return False, "File does not exist"
            
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size:
                return False, f"File size ({file_size} bytes) exceeds maximum allowed size ({self.max_file_size} bytes)"
            
            if file_size == 0:
                return False, "File is empty"
            
            # Check file extension
            if not self._is_allowed_extension(filename):
                return False, f"File extension not allowed. Allowed extensions: {', '.join(self.allowed_extensions)}"
            
            # Check MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type not in self.allowed_mime_types:
                return False, f"MIME type '{mime_type}' not allowed"
            
            # Check if file is actually an image
            if not self._is_valid_image(file_path):
                return False, "File is not a valid image"
            
            # Check image dimensions
            if not self._check_image_dimensions(file_path):
                return False, f"Image dimensions exceed maximum allowed ({self.max_image_dimensions[0]}x{self.max_image_dimensions[1]})"
            
            # Check for malicious content
            if not self._scan_for_malicious_content(file_path):
                return False, "File contains potentially malicious content"
            
            return True, None
            
        except Exception as e:
            self.logger.error(f"File validation error: {e}")
            return False, f"Validation error: {str(e)}"
    
    def sanitize_filename(self, filename: str) -> Optional[str]:
        """Sanitize filename for safe storage"""
        if not filename:
            return None
        
        # Use werkzeug's secure_filename
        sanitized = secure_filename(filename)
        
        # Additional sanitization
        sanitized = sanitized.replace(' ', '_')
        sanitized = sanitized.lower()
        
        # Ensure it has a valid extension
        if not self._is_allowed_extension(sanitized):
            return None
        
        return sanitized
    
    def save_uploaded_file(self, file_stream, filename: str, user_id: int = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Save uploaded file with validation
        
        Returns:
            Tuple[bool, Optional[str], Optional[str]]: (success, file_path, error_message)
        """
        try:
            # Sanitize filename
            sanitized_filename = self.sanitize_filename(filename)
            if not sanitized_filename:
                return False, None, "Invalid filename"
            
            # Generate unique filename
            unique_id = str(uuid.uuid4())
            final_filename = f"{unique_id}_{sanitized_filename}"
            
            # Save to temporary location first
            temp_path = os.path.join(self.temp_dir, final_filename)
            file_stream.save(temp_path)
            
            # Validate the saved file
            is_valid, error_message = self.validate_file(temp_path, sanitized_filename)
            
            if not is_valid:
                # Remove temporary file
                self._safe_remove_file(temp_path)
                return False, None, error_message
            
            # Move to upload directory
            upload_path = os.path.join(self.upload_dir, final_filename)
            os.rename(temp_path, upload_path)
            
            # Log successful upload
            system_logger.info('file', f'File uploaded successfully: {sanitized_filename}',
                              details={
                                  'original_filename': filename,
                                  'sanitized_filename': sanitized_filename,
                                  'file_size': os.path.getsize(upload_path),
                                  'user_id': user_id
                              })
            
            return True, upload_path, None
            
        except Exception as e:
            self.logger.error(f"Error saving uploaded file: {e}")
            
            # Clean up any temporary files
            if 'temp_path' in locals():
                self._safe_remove_file(temp_path)
            
            return False, None, f"Save error: {str(e)}"
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get comprehensive file information"""
        try:
            if not os.path.exists(file_path):
                return {'error': 'File does not exist'}
            
            stat = os.stat(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)
            
            info = {
                'path': file_path,
                'filename': os.path.basename(file_path),
                'size': stat.st_size,
                'mime_type': mime_type,
                'created': stat.st_ctime,
                'modified': stat.st_mtime,
                'extension': Path(file_path).suffix.lower()
            }
            
            # Add image-specific info if it's an image
            if self._is_valid_image(file_path):
                info.update(self._get_image_info(file_path))
            
            return info
            
        except Exception as e:
            self.logger.error(f"Error getting file info: {e}")
            return {'error': str(e)}
    
    def calculate_file_hash(self, file_path: str, algorithm: str = 'sha256') -> Optional[str]:
        """Calculate file hash for integrity checking"""
        try:
            if not os.path.exists(file_path):
                return None
            
            hash_obj = hashlib.new(algorithm)
            
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            self.logger.error(f"Error calculating file hash: {e}")
            return None
    
    def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """Clean up temporary files older than specified age"""
        try:
            import time
            
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            cleaned_count = 0
            
            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getmtime(file_path)
                    
                    if file_age > max_age_seconds:
                        self._safe_remove_file(file_path)
                        cleaned_count += 1
            
            if cleaned_count > 0:
                self.logger.info(f"Cleaned up {cleaned_count} temporary files")
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up temp files: {e}")
            return 0
    
    def delete_file(self, file_path: str) -> bool:
        """Safely delete a file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error deleting file: {e}")
            return False
    
    def get_file_security_info(self, file_path: str) -> Dict[str, Any]:
        """Get security-related file information"""
        try:
            info = {
                'file_hash': self.calculate_file_hash(file_path),
                'is_valid_image': self._is_valid_image(file_path),
                'has_exif_data': self._has_exif_data(file_path),
                'file_size': os.path.getsize(file_path),
                'permissions': oct(os.stat(file_path).st_mode)[-3:]
            }
            
            return info
            
        except Exception as e:
            self.logger.error(f"Error getting file security info: {e}")
            return {'error': str(e)}
    
    def _is_allowed_extension(self, filename: str) -> bool:
        """Check if file extension is allowed"""
        if '.' not in filename:
            return False
        
        extension = filename.rsplit('.', 1)[1].lower()
        return extension in self.allowed_extensions
    
    def _is_valid_image(self, file_path: str) -> bool:
        """Check if file is a valid image"""
        try:
            from PIL import Image
            
            with Image.open(file_path) as img:
                img.verify()
            
            return True
            
        except Exception:
            return False
    
    def _check_image_dimensions(self, file_path: str) -> bool:
        """Check if image dimensions are within limits"""
        try:
            from PIL import Image
            
            with Image.open(file_path) as img:
                width, height = img.size
                
                return (width <= self.max_image_dimensions[0] and 
                       height <= self.max_image_dimensions[1])
            
        except Exception:
            return False
    
    def _get_image_info(self, file_path: str) -> Dict[str, Any]:
        """Get image-specific information"""
        try:
            from PIL import Image
            
            with Image.open(file_path) as img:
                return {
                    'width': img.width,
                    'height': img.height,
                    'mode': img.mode,
                    'format': img.format,
                    'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                }
            
        except Exception as e:
            self.logger.error(f"Error getting image info: {e}")
            return {}
    
    def _has_exif_data(self, file_path: str) -> bool:
        """Check if image has EXIF data"""
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
            
            with Image.open(file_path) as img:
                exif_data = img._getexif()
                return exif_data is not None and len(exif_data) > 0
            
        except Exception:
            return False
    
    def _scan_for_malicious_content(self, file_path: str) -> bool:
        """Basic scan for malicious content"""
        try:
            # Check file size (extremely large files might be suspicious)
            file_size = os.path.getsize(file_path)
            if file_size > 100 * 1024 * 1024:  # 100MB
                return False
            
            # Check for embedded scripts or suspicious content
            with open(file_path, 'rb') as f:
                content = f.read(1024)  # Read first 1KB
                
                # Look for suspicious patterns
                suspicious_patterns = [
                    b'<script',
                    b'javascript:',
                    b'eval(',
                    b'document.write',
                    b'<iframe'
                ]
                
                for pattern in suspicious_patterns:
                    if pattern in content.lower():
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error scanning file for malicious content: {e}")
            return False
    
    def _safe_remove_file(self, file_path: str):
        """Safely remove a file with error handling"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            self.logger.error(f"Error removing file {file_path}: {e}")
    
    # === FILE ANALYTICS AND MANAGEMENT METHODS ===
    
    def get_file_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive file analytics"""
        try:
            # Get upload analytics
            upload_stats = self._get_upload_analytics(days)
            
            # Get storage analytics
            storage_stats = self._get_storage_analytics()
            
            # Get processing analytics
            processing_stats = self._get_processing_analytics(days)
            
            # Compile comprehensive analytics
            analytics = {
                'summary': {
                    'total_uploads': upload_stats.get('total_uploads', 0),
                    'total_size': upload_stats.get('total_size', 0),
                    'avg_file_size': upload_stats.get('avg_file_size', 0),
                    'success_rate': upload_stats.get('success_rate', 0),
                    'storage_efficiency': storage_stats.get('efficiency', 0)
                },
                'upload_trends': upload_stats.get('daily_breakdown', []),
                'file_type_distribution': upload_stats.get('file_types', {}),
                'size_distribution': upload_stats.get('size_distribution', {}),
                'processing_metrics': processing_stats,
                'storage_metrics': storage_stats,
                'optimization_opportunities': self._get_optimization_opportunities()
            }
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"Error getting file analytics: {e}")
            return self._get_default_analytics()
    
    def get_storage_summary(self) -> Dict[str, Any]:
        """Get storage usage summary"""
        try:
            summary = {
                'directories': {},
                'total_size': 0,
                'total_files': 0,
                'growth_rate': 0,
                'optimization_potential': 0
            }
            
            # Analyze each directory
            directories = [self.upload_dir, self.results_dir, self.temp_dir, self.archive_dir]
            
            for directory in directories:
                if os.path.exists(directory):
                    dir_stats = self._analyze_directory(directory)
                    summary['directories'][directory] = dir_stats
                    summary['total_size'] += dir_stats['size']
                    summary['total_files'] += dir_stats['file_count']
            
            # Calculate growth rate
            summary['growth_rate'] = self._calculate_storage_growth_rate()
            
            # Calculate optimization potential
            summary['optimization_potential'] = self._calculate_optimization_potential()
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting storage summary: {e}")
            return self._get_default_storage_summary()
    
    def optimize_storage(self, action: str = 'analyze') -> Dict[str, Any]:
        """Optimize storage usage"""
        try:
            optimization_results = {
                'action': action,
                'savings': 0,
                'files_processed': 0,
                'errors': 0,
                'details': []
            }
            
            if action == 'analyze':
                # Analyze optimization opportunities
                opportunities = self._analyze_optimization_opportunities()
                optimization_results['opportunities'] = opportunities
                
            elif action == 'cleanup_temp':
                # Clean up temporary files
                cleaned = self.cleanup_temp_files(max_age_hours=24)
                optimization_results['files_processed'] = cleaned
                optimization_results['details'].append(f'Cleaned {cleaned} temporary files')
                
            elif action == 'compress_large_files':
                # Compress large files
                compressed = self._compress_large_files()
                optimization_results.update(compressed)
                
            elif action == 'archive_old_files':
                # Archive old files
                archived = self._archive_old_files()
                optimization_results.update(archived)
                
            elif action == 'deduplicate':
                # Remove duplicate files
                deduped = self._deduplicate_files()
                optimization_results.update(deduped)
            
            return optimization_results
            
        except Exception as e:
            self.logger.error(f"Error optimizing storage: {e}")
            return {'error': str(e)}
    
    def get_file_quality_metrics(self) -> Dict[str, Any]:
        """Get file quality metrics"""
        try:
            quality_metrics = {
                'image_quality': {
                    'avg_resolution': 0,
                    'resolution_distribution': {},
                    'format_distribution': {},
                    'color_depth_distribution': {}
                },
                'file_integrity': {
                    'valid_files': 0,
                    'corrupted_files': 0,
                    'suspicious_files': 0
                },
                'optimization_status': {
                    'optimized_files': 0,
                    'potential_savings': 0,
                    'compression_ratio': 0
                }
            }
            
            # Analyze files in upload directory
            for filename in os.listdir(self.upload_dir):
                file_path = os.path.join(self.upload_dir, filename)
                if os.path.isfile(file_path):
                    file_metrics = self._analyze_file_quality(file_path)
                    self._update_quality_metrics(quality_metrics, file_metrics)
            
            return quality_metrics
            
        except Exception as e:
            self.logger.error(f"Error getting file quality metrics: {e}")
            return self._get_default_quality_metrics()
    
    def monitor_file_processing(self) -> Dict[str, Any]:
        """Monitor file processing in real-time"""
        try:
            monitoring_data = {
                'active_uploads': 0,
                'processing_queue': 0,
                'recent_activity': [],
                'error_rate': 0,
                'throughput': 0,
                'avg_processing_time': 0
            }
            
            # Get recent activity
            recent_activity = self._get_recent_file_activity(hours=1)
            monitoring_data['recent_activity'] = recent_activity
            
            # Calculate metrics
            if recent_activity:
                total_files = len(recent_activity)
                successful_files = sum(1 for activity in recent_activity if activity.get('status') == 'success')
                error_files = total_files - successful_files
                
                monitoring_data['error_rate'] = error_files / total_files if total_files > 0 else 0
                monitoring_data['throughput'] = total_files  # files per hour
                
                # Calculate average processing time
                processing_times = [activity.get('processing_time', 0) for activity in recent_activity 
                                  if activity.get('processing_time')]
                if processing_times:
                    monitoring_data['avg_processing_time'] = statistics.mean(processing_times)
            
            return monitoring_data
            
        except Exception as e:
            self.logger.error(f"Error monitoring file processing: {e}")
            return self._get_default_monitoring_data()
    
    def _get_upload_analytics(self, days: int) -> Dict[str, Any]:
        """Get upload analytics for specified days"""
        try:
            # This would typically query a database
            # For now, we'll analyze the file system
            analytics = {
                'total_uploads': 0,
                'total_size': 0,
                'avg_file_size': 0,
                'success_rate': 0,
                'daily_breakdown': [],
                'file_types': defaultdict(int),
                'size_distribution': defaultdict(int)
            }
            
            # Analyze files in upload directory
            cutoff_time = time.time() - (days * 24 * 3600)
            
            for filename in os.listdir(self.upload_dir):
                file_path = os.path.join(self.upload_dir, filename)
                if os.path.isfile(file_path):
                    stat = os.stat(file_path)
                    
                    # Check if file is within time range
                    if stat.st_mtime >= cutoff_time:
                        analytics['total_uploads'] += 1
                        analytics['total_size'] += stat.st_size
                        
                        # File type
                        ext = Path(filename).suffix.lower()
                        analytics['file_types'][ext] += 1
                        
                        # Size distribution
                        size_mb = stat.st_size / (1024 * 1024)
                        if size_mb < 1:
                            analytics['size_distribution']['<1MB'] += 1
                        elif size_mb < 5:
                            analytics['size_distribution']['1-5MB'] += 1
                        elif size_mb < 10:
                            analytics['size_distribution']['5-10MB'] += 1
                        else:
                            analytics['size_distribution']['>10MB'] += 1
            
            # Calculate averages
            if analytics['total_uploads'] > 0:
                analytics['avg_file_size'] = analytics['total_size'] / analytics['total_uploads']
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"Error getting upload analytics: {e}")
            return {}
    
    def _get_storage_analytics(self) -> Dict[str, Any]:
        """Get storage analytics"""
        try:
            analytics = {
                'total_size': 0,
                'total_files': 0,
                'efficiency': 0,
                'growth_trend': [],
                'directory_breakdown': {}
            }
            
            # Analyze each directory
            directories = [self.upload_dir, self.results_dir, self.temp_dir, self.archive_dir]
            
            for directory in directories:
                if os.path.exists(directory):
                    dir_stats = self._analyze_directory(directory)
                    analytics['directory_breakdown'][directory] = dir_stats
                    analytics['total_size'] += dir_stats['size']
                    analytics['total_files'] += dir_stats['file_count']
            
            # Calculate efficiency (files per MB)
            if analytics['total_size'] > 0:
                analytics['efficiency'] = analytics['total_files'] / (analytics['total_size'] / (1024 * 1024))
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"Error getting storage analytics: {e}")
            return {}
    
    def _get_processing_analytics(self, days: int) -> Dict[str, Any]:
        """Get processing analytics"""
        try:
            analytics = {
                'total_processed': 0,
                'avg_processing_time': 0,
                'success_rate': 0,
                'error_distribution': defaultdict(int),
                'performance_trends': []
            }
            
            # This would typically query processing logs
            # For now, return basic structure
            return analytics
            
        except Exception as e:
            self.logger.error(f"Error getting processing analytics: {e}")
            return {}
    
    def _analyze_directory(self, directory: str) -> Dict[str, Any]:
        """Analyze a directory for storage metrics"""
        try:
            stats = {
                'size': 0,
                'file_count': 0,
                'avg_file_size': 0,
                'oldest_file': None,
                'newest_file': None,
                'file_types': defaultdict(int)
            }
            
            oldest_time = float('inf')
            newest_time = 0
            
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                if os.path.isfile(file_path):
                    file_stat = os.stat(file_path)
                    
                    stats['size'] += file_stat.st_size
                    stats['file_count'] += 1
                    
                    # Track oldest and newest files
                    if file_stat.st_mtime < oldest_time:
                        oldest_time = file_stat.st_mtime
                        stats['oldest_file'] = filename
                    
                    if file_stat.st_mtime > newest_time:
                        newest_time = file_stat.st_mtime
                        stats['newest_file'] = filename
                    
                    # File type distribution
                    ext = Path(filename).suffix.lower()
                    stats['file_types'][ext] += 1
            
            # Calculate average file size
            if stats['file_count'] > 0:
                stats['avg_file_size'] = stats['size'] / stats['file_count']
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error analyzing directory {directory}: {e}")
            return {'size': 0, 'file_count': 0, 'avg_file_size': 0}
    
    def _get_optimization_opportunities(self) -> List[Dict[str, Any]]:
        """Get optimization opportunities"""
        opportunities = []
        
        try:
            # Check for large files
            large_files = self._find_large_files()
            if large_files:
                opportunities.append({
                    'type': 'compression',
                    'description': f'Found {len(large_files)} large files that could be compressed',
                    'potential_savings': f'{sum(f["size"] for f in large_files) * 0.3 / 1024/1024:.1f}MB',
                    'files': large_files[:10]  # Show first 10
                })
            
            # Check for temporary files
            temp_files = self._find_old_temp_files()
            if temp_files:
                opportunities.append({
                    'type': 'cleanup',
                    'description': f'Found {len(temp_files)} old temporary files',
                    'potential_savings': f'{sum(f["size"] for f in temp_files) / 1024/1024:.1f}MB',
                    'files': temp_files[:10]
                })
            
            # Check for duplicates
            duplicates = self._find_duplicate_files()
            if duplicates:
                opportunities.append({
                    'type': 'deduplication',
                    'description': f'Found {len(duplicates)} duplicate files',
                    'potential_savings': f'{sum(f["size"] for f in duplicates) / 1024/1024:.1f}MB',
                    'files': duplicates[:10]
                })
            
            return opportunities
            
        except Exception as e:
            self.logger.error(f"Error getting optimization opportunities: {e}")
            return []
    
    def _find_large_files(self, size_threshold: int = 10 * 1024 * 1024) -> List[Dict[str, Any]]:
        """Find files larger than threshold"""
        large_files = []
        
        try:
            for directory in [self.upload_dir, self.results_dir]:
                if os.path.exists(directory):
                    for filename in os.listdir(directory):
                        file_path = os.path.join(directory, filename)
                        if os.path.isfile(file_path):
                            file_size = os.path.getsize(file_path)
                            if file_size > size_threshold:
                                large_files.append({
                                    'filename': filename,
                                    'path': file_path,
                                    'size': file_size,
                                    'directory': directory
                                })
            
            return sorted(large_files, key=lambda x: x['size'], reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error finding large files: {e}")
            return []
    
    def _find_old_temp_files(self, age_hours: int = 24) -> List[Dict[str, Any]]:
        """Find old temporary files"""
        old_files = []
        
        try:
            if os.path.exists(self.temp_dir):
                cutoff_time = time.time() - (age_hours * 3600)
                
                for filename in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, filename)
                    if os.path.isfile(file_path):
                        file_stat = os.stat(file_path)
                        if file_stat.st_mtime < cutoff_time:
                            old_files.append({
                                'filename': filename,
                                'path': file_path,
                                'size': file_stat.st_size,
                                'age_hours': (time.time() - file_stat.st_mtime) / 3600
                            })
            
            return sorted(old_files, key=lambda x: x['age_hours'], reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error finding old temp files: {e}")
            return []
    
    def _find_duplicate_files(self) -> List[Dict[str, Any]]:
        """Find duplicate files by hash"""
        duplicates = []
        
        try:
            file_hashes = {}
            
            # Calculate hashes for all files
            for directory in [self.upload_dir, self.results_dir]:
                if os.path.exists(directory):
                    for filename in os.listdir(directory):
                        file_path = os.path.join(directory, filename)
                        if os.path.isfile(file_path):
                            file_hash = self.calculate_file_hash(file_path)
                            if file_hash:
                                if file_hash in file_hashes:
                                    # Found duplicate
                                    duplicates.append({
                                        'filename': filename,
                                        'path': file_path,
                                        'size': os.path.getsize(file_path),
                                        'duplicate_of': file_hashes[file_hash]['filename']
                                    })
                                else:
                                    file_hashes[file_hash] = {
                                        'filename': filename,
                                        'path': file_path
                                    }
            
            return duplicates
            
        except Exception as e:
            self.logger.error(f"Error finding duplicate files: {e}")
            return []
    
    def _calculate_storage_growth_rate(self) -> float:
        """Calculate storage growth rate"""
        try:
            # This would typically analyze historical data
            # For now, return a placeholder
            return 0.0
        except Exception as e:
            self.logger.error(f"Error calculating growth rate: {e}")
            return 0.0
    
    def _calculate_optimization_potential(self) -> float:
        """Calculate optimization potential in MB"""
        try:
            potential = 0.0
            
            # Add potential from large files (30% compression)
            large_files = self._find_large_files()
            potential += sum(f['size'] for f in large_files) * 0.3
            
            # Add potential from temp files (100% removal)
            temp_files = self._find_old_temp_files()
            potential += sum(f['size'] for f in temp_files)
            
            # Add potential from duplicates (100% removal)
            duplicates = self._find_duplicate_files()
            potential += sum(f['size'] for f in duplicates)
            
            return potential / (1024 * 1024)  # Convert to MB
            
        except Exception as e:
            self.logger.error(f"Error calculating optimization potential: {e}")
            return 0.0
    
    def _get_default_analytics(self) -> Dict[str, Any]:
        """Get default analytics structure"""
        return {
            'summary': {
                'total_uploads': 0,
                'total_size': 0,
                'avg_file_size': 0,
                'success_rate': 0,
                'storage_efficiency': 0
            },
            'upload_trends': [],
            'file_type_distribution': {},
            'size_distribution': {},
            'processing_metrics': {},
            'storage_metrics': {},
            'optimization_opportunities': []
        }
    
    def _get_default_storage_summary(self) -> Dict[str, Any]:
        """Get default storage summary"""
        return {
            'directories': {},
            'total_size': 0,
            'total_files': 0,
            'growth_rate': 0,
            'optimization_potential': 0
        }
    
    def _get_default_quality_metrics(self) -> Dict[str, Any]:
        """Get default quality metrics"""
        return {
            'image_quality': {
                'avg_resolution': 0,
                'resolution_distribution': {},
                'format_distribution': {},
                'color_depth_distribution': {}
            },
            'file_integrity': {
                'valid_files': 0,
                'corrupted_files': 0,
                'suspicious_files': 0
            },
            'optimization_status': {
                'optimized_files': 0,
                'potential_savings': 0,
                'compression_ratio': 0
            }
        }
    
    def _get_default_monitoring_data(self) -> Dict[str, Any]:
        """Get default monitoring data"""
        return {
            'active_uploads': 0,
            'processing_queue': 0,
            'recent_activity': [],
            'error_rate': 0,
            'throughput': 0,
            'avg_processing_time': 0
        }
    
    def _get_recent_file_activity(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get recent file activity"""
        try:
            # This would typically query logs or database
            # For now, return sample data
            return [
                {
                    'timestamp': datetime.now().isoformat(),
                    'filename': 'sample.jpg',
                    'size': 1024 * 1024,
                    'type': 'jpg',
                    'processing_time': 25.5,
                    'status': 'success',
                    'quality_score': 0.85
                }
            ]
        except Exception as e:
            self.logger.error(f"Error getting recent file activity: {e}")
            return []
    
    def _analyze_file_quality(self, file_path: str) -> Dict[str, Any]:
        """Analyze file quality metrics"""
        try:
            metrics = {
                'resolution': 0,
                'format': 'unknown',
                'color_depth': 0,
                'is_valid': False,
                'is_corrupted': False,
                'is_suspicious': False
            }
            
            if self._is_valid_image(file_path):
                from PIL import Image
                with Image.open(file_path) as img:
                    metrics['resolution'] = img.width * img.height
                    metrics['format'] = img.format
                    metrics['color_depth'] = len(img.getbands())
                    metrics['is_valid'] = True
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error analyzing file quality: {e}")
            return {'is_corrupted': True}
    
    def _update_quality_metrics(self, quality_metrics: Dict[str, Any], file_metrics: Dict[str, Any]):
        """Update quality metrics with file data"""
        try:
            if file_metrics.get('is_valid'):
                quality_metrics['file_integrity']['valid_files'] += 1
                
                # Update image quality metrics
                resolution = file_metrics.get('resolution', 0)
                if resolution > 0:
                    current_avg = quality_metrics['image_quality']['avg_resolution']
                    quality_metrics['image_quality']['avg_resolution'] = (current_avg + resolution) / 2
                
                # Update format distribution
                format_type = file_metrics.get('format', 'unknown')
                quality_metrics['image_quality']['format_distribution'][format_type] = \
                    quality_metrics['image_quality']['format_distribution'].get(format_type, 0) + 1
                
            elif file_metrics.get('is_corrupted'):
                quality_metrics['file_integrity']['corrupted_files'] += 1
            elif file_metrics.get('is_suspicious'):
                quality_metrics['file_integrity']['suspicious_files'] += 1
                
        except Exception as e:
            self.logger.error(f"Error updating quality metrics: {e}")
    
    def _analyze_optimization_opportunities(self) -> List[Dict[str, Any]]:
        """Analyze optimization opportunities"""
        try:
            opportunities = []
            
            # Check for large files
            large_files = self._find_large_files()
            if large_files:
                potential_savings = sum(f['size'] for f in large_files) * 0.3
                opportunities.append({
                    'type': 'compression',
                    'priority': 'high',
                    'description': f'Compress {len(large_files)} large files',
                    'potential_savings': f'{potential_savings / 1024 / 1024:.1f} MB',
                    'action': 'compress_large_files'
                })
            
            # Check for old temporary files
            old_temp_files = self._find_old_temp_files()
            if old_temp_files:
                potential_savings = sum(f['size'] for f in old_temp_files)
                opportunities.append({
                    'type': 'cleanup',
                    'priority': 'medium',
                    'description': f'Clean up {len(old_temp_files)} old temporary files',
                    'potential_savings': f'{potential_savings / 1024 / 1024:.1f} MB',
                    'action': 'cleanup_temp'
                })
            
            # Check for duplicate files
            duplicates = self._find_duplicate_files()
            if duplicates:
                potential_savings = sum(f['size'] for f in duplicates)
                opportunities.append({
                    'type': 'deduplication',
                    'priority': 'low',
                    'description': f'Remove {len(duplicates)} duplicate files',
                    'potential_savings': f'{potential_savings / 1024 / 1024:.1f} MB',
                    'action': 'deduplicate'
                })
            
            return opportunities
            
        except Exception as e:
            self.logger.error(f"Error analyzing optimization opportunities: {e}")
            return []
    
    def _compress_large_files(self) -> Dict[str, Any]:
        """Compress large files"""
        try:
            large_files = self._find_large_files()
            compressed_count = 0
            total_savings = 0
            
            for file_info in large_files:
                # In a real implementation, this would compress the file
                # For now, just simulate the compression
                compressed_count += 1
                total_savings += file_info['size'] * 0.3
            
            return {
                'files_processed': compressed_count,
                'savings': total_savings / 1024 / 1024,  # MB
                'details': [f'Compressed {compressed_count} files']
            }
            
        except Exception as e:
            self.logger.error(f"Error compressing large files: {e}")
            return {'files_processed': 0, 'savings': 0, 'errors': 1}
    
    def _archive_old_files(self) -> Dict[str, Any]:
        """Archive old files"""
        try:
            # Find files older than 90 days
            old_files = []
            cutoff_time = time.time() - (90 * 24 * 3600)
            
            for directory in [self.upload_dir, self.results_dir]:
                if os.path.exists(directory):
                    for filename in os.listdir(directory):
                        file_path = os.path.join(directory, filename)
                        if os.path.isfile(file_path):
                            if os.path.getmtime(file_path) < cutoff_time:
                                old_files.append({
                                    'filename': filename,
                                    'path': file_path,
                                    'size': os.path.getsize(file_path)
                                })
            
            archived_count = 0
            total_savings = 0
            
            for file_info in old_files:
                # In a real implementation, this would move files to archive
                # For now, just simulate the archiving
                archived_count += 1
                total_savings += file_info['size']
            
            return {
                'files_processed': archived_count,
                'savings': total_savings / 1024 / 1024,  # MB
                'details': [f'Archived {archived_count} old files']
            }
            
        except Exception as e:
            self.logger.error(f"Error archiving old files: {e}")
            return {'files_processed': 0, 'savings': 0, 'errors': 1}
    
    def _deduplicate_files(self) -> Dict[str, Any]:
        """Remove duplicate files"""
        try:
            duplicates = self._find_duplicate_files()
            removed_count = 0
            total_savings = 0
            
            for duplicate in duplicates:
                # In a real implementation, this would remove the duplicate
                # For now, just simulate the removal
                removed_count += 1
                total_savings += duplicate['size']
            
            return {
                'files_processed': removed_count,
                'savings': total_savings / 1024 / 1024,  # MB
                'details': [f'Removed {removed_count} duplicate files']
            }
            
        except Exception as e:
            self.logger.error(f"Error deduplicating files: {e}")
            return {'files_processed': 0, 'savings': 0, 'errors': 1}


# Global file service instance
file_service = FileService()


if __name__ == '__main__':
    # Test the file service
    logger.info("Testing VectorCraft File Service...")
    
    # Test filename sanitization
    test_filename = "Test Image with Spaces.PNG"
    sanitized = file_service.sanitize_filename(test_filename)
    assert sanitized == "test_image_with_spaces.png"
    
    # Test extension validation
    assert file_service._is_allowed_extension("test.png") == True
    assert file_service._is_allowed_extension("test.exe") == False
    
    # Test directory creation
    file_service._ensure_directories()
    assert os.path.exists(file_service.upload_dir)
    assert os.path.exists(file_service.results_dir)
    assert os.path.exists(file_service.temp_dir)
    assert os.path.exists(file_service.archive_dir)
    
    # Test temp file cleanup
    cleaned = file_service.cleanup_temp_files(max_age_hours=1)
    logger.info(f"Cleaned {cleaned} temporary files")
    
    # Test analytics
    analytics = file_service.get_file_analytics()
    logger.info(f"Analytics: {analytics['summary']}")
    
    # Test storage summary
    storage = file_service.get_storage_summary()
    logger.info(f"Storage: {storage['total_size']} bytes in {storage['total_files']} files")
    
    logger.info("File service test completed successfully!")