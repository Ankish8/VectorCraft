"""
File service layer for VectorCraft
Handles file operations, validation, and management
"""

import os
import uuid
import hashlib
import mimetypes
import logging
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from werkzeug.utils import secure_filename

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
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure required directories exist"""
        directories = [self.upload_dir, self.results_dir, self.temp_dir]
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
    
    # Test temp file cleanup
    cleaned = file_service.cleanup_temp_files(max_age_hours=1)
    logger.info(f"Cleaned {cleaned} temporary files")
    
    logger.info("File service test completed successfully!")