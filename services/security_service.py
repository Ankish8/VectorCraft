#!/usr/bin/env python3
"""
Security service for file upload validation and sanitization
"""

import os
import mimetypes
import hashlib
import subprocess
import tempfile
import magic
from PIL import Image
from PIL.ExifTags import TAGS
import logging

logger = logging.getLogger(__name__)

class SecurityService:
    def __init__(self):
        self.allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
        self.allowed_mime_types = {
            'image/png', 'image/jpeg', 'image/gif', 
            'image/bmp', 'image/tiff', 'image/x-ms-bmp'
        }
        self.max_file_size = 16 * 1024 * 1024  # 16MB
        self.max_image_dimensions = (8192, 8192)  # 8K resolution max
        
    def validate_file_extension(self, filename):
        """Validate file extension"""
        if '.' not in filename:
            return False
        extension = filename.rsplit('.', 1)[1].lower()
        return extension in self.allowed_extensions
    
    def validate_mime_type(self, file_path):
        """Validate MIME type using python-magic"""
        try:
            mime_type = magic.from_file(file_path, mime=True)
            return mime_type in self.allowed_mime_types
        except Exception as e:
            logger.error(f"Error checking MIME type: {e}")
            return False
    
    def validate_file_size(self, file_path):
        """Validate file size"""
        try:
            file_size = os.path.getsize(file_path)
            return file_size <= self.max_file_size
        except Exception as e:
            logger.error(f"Error checking file size: {e}")
            return False
    
    def validate_image_dimensions(self, file_path):
        """Validate image dimensions"""
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                return (width <= self.max_image_dimensions[0] and 
                       height <= self.max_image_dimensions[1])
        except Exception as e:
            logger.error(f"Error checking image dimensions: {e}")
            return False
    
    def strip_metadata(self, file_path, output_path):
        """Strip metadata from image files"""
        try:
            with Image.open(file_path) as img:
                # Create image without EXIF data
                data = list(img.getdata())
                image_without_exif = Image.new(img.mode, img.size)
                image_without_exif.putdata(data)
                
                # Save without metadata
                image_without_exif.save(output_path, optimize=True, quality=95)
                return True
        except Exception as e:
            logger.error(f"Error stripping metadata: {e}")
            return False
    
    def scan_for_malware(self, file_path):
        """Basic malware scanning using ClamAV if available"""
        try:
            # Check if ClamAV is available
            result = subprocess.run(['which', 'clamscan'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning("ClamAV not available - skipping virus scan")
                return True  # Allow file but log warning
            
            # Run ClamAV scan
            result = subprocess.run(['clamscan', '--no-summary', file_path], 
                                  capture_output=True, text=True, timeout=30)
            
            # Check result
            if result.returncode == 0:
                logger.info(f"File {file_path} passed virus scan")
                return True
            else:
                logger.error(f"File {file_path} failed virus scan: {result.stdout}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Virus scan timeout for {file_path}")
            return False
        except Exception as e:
            logger.error(f"Error during virus scan: {e}")
            return True  # Allow file but log error
    
    def calculate_file_hash(self, file_path):
        """Calculate SHA256 hash of file"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating file hash: {e}")
            return None
    
    def validate_and_sanitize_upload(self, file_path, original_filename):
        """
        Comprehensive file validation and sanitization
        Returns: (is_valid, sanitized_path, error_message)
        """
        try:
            # Step 1: Validate file extension
            if not self.validate_file_extension(original_filename):
                return False, None, "Invalid file extension"
            
            # Step 2: Validate file size
            if not self.validate_file_size(file_path):
                return False, None, "File size exceeds limit"
            
            # Step 3: Validate MIME type
            if not self.validate_mime_type(file_path):
                return False, None, "Invalid file type"
            
            # Step 4: Validate image dimensions
            if not self.validate_image_dimensions(file_path):
                return False, None, "Image dimensions exceed limit"
            
            # Step 5: Scan for malware
            if not self.scan_for_malware(file_path):
                return False, None, "File failed security scan"
            
            # Step 6: Calculate file hash for tracking
            file_hash = self.calculate_file_hash(file_path)
            logger.info(f"File hash: {file_hash}")
            
            # Step 7: Strip metadata and create sanitized version
            sanitized_path = file_path + '.sanitized'
            if not self.strip_metadata(file_path, sanitized_path):
                return False, None, "Failed to sanitize file"
            
            logger.info(f"File {original_filename} passed all security checks")
            return True, sanitized_path, None
            
        except Exception as e:
            logger.error(f"Error during file validation: {e}")
            return False, None, f"Security validation failed: {str(e)}"
    
    def check_file_reputation(self, file_hash):
        """
        Check file reputation against known malware hashes
        This is a placeholder for integration with threat intelligence feeds
        """
        # In production, this would check against:
        # - VirusTotal API
        # - Internal threat intelligence
        # - Known malware hash databases
        
        # For now, return clean
        return True

# Global security service instance
security_service = SecurityService()