#!/usr/bin/env python3
"""
Unit tests for file upload functionality
Tests file validation, processing, and security
"""

import pytest
import os
import io
import tempfile
import shutil
from unittest.mock import patch, MagicMock, mock_open
from PIL import Image
import magic
from werkzeug.datastructures import FileStorage

from services.file_service import FileService
from services.security_service import SecurityService


class TestFileValidation:
    """Test file validation functionality"""
    
    def test_validate_image_file_valid(self, test_image_file):
        """Test validation of valid image file"""
        file_service = FileService()
        
        # Create FileStorage object
        file_storage = FileStorage(
            stream=test_image_file,
            filename='test.png',
            content_type='image/png'
        )
        
        result = file_service.validate_file(file_storage)
        
        assert result is True
    
    def test_validate_image_file_invalid_extension(self):
        """Test validation of file with invalid extension"""
        file_service = FileService()
        
        # Create text file with image extension
        text_file = io.BytesIO(b'This is not an image')
        file_storage = FileStorage(
            stream=text_file,
            filename='test.txt',
            content_type='text/plain'
        )
        
        result = file_service.validate_file(file_storage)
        
        assert result is False
    
    def test_validate_image_file_invalid_content_type(self, test_image_file):
        """Test validation of file with invalid content type"""
        file_service = FileService()
        
        file_storage = FileStorage(
            stream=test_image_file,
            filename='test.png',
            content_type='text/plain'  # Wrong content type
        )
        
        result = file_service.validate_file(file_storage)
        
        assert result is False
    
    def test_validate_image_file_no_filename(self, test_image_file):
        """Test validation of file without filename"""
        file_service = FileService()
        
        file_storage = FileStorage(
            stream=test_image_file,
            filename=None,
            content_type='image/png'
        )
        
        result = file_service.validate_file(file_storage)
        
        assert result is False
    
    def test_validate_image_file_empty_file(self):
        """Test validation of empty file"""
        file_service = FileService()
        
        empty_file = io.BytesIO(b'')
        file_storage = FileStorage(
            stream=empty_file,
            filename='test.png',
            content_type='image/png'
        )
        
        result = file_service.validate_file(file_storage)
        
        assert result is False
    
    def test_validate_image_file_too_large(self, security_test_helpers):
        """Test validation of file too large"""
        file_service = FileService()
        
        large_file = security_test_helpers.create_large_file(size_mb=20)
        file_storage = FileStorage(
            stream=large_file,
            filename='large.png',
            content_type='image/png'
        )
        
        result = file_service.validate_file(file_storage)
        
        assert result is False
    
    def test_validate_supported_formats(self, test_utils):
        """Test validation of different supported formats"""
        file_service = FileService()
        
        supported_formats = ['PNG', 'JPEG', 'JPG', 'BMP', 'GIF', 'TIFF']
        
        for format_name in supported_formats:
            image_file = test_utils.create_test_image(format=format_name)
            file_storage = FileStorage(
                stream=image_file,
                filename=f'test.{format_name.lower()}',
                content_type=f'image/{format_name.lower()}'
            )
            
            result = file_service.validate_file(file_storage)
            assert result is True, f"Format {format_name} should be supported"
    
    def test_validate_unsupported_formats(self):
        """Test validation of unsupported formats"""
        file_service = FileService()
        
        unsupported_formats = ['svg', 'pdf', 'txt', 'docx', 'exe']
        
        for format_name in unsupported_formats:
            fake_file = io.BytesIO(b'fake content')
            file_storage = FileStorage(
                stream=fake_file,
                filename=f'test.{format_name}',
                content_type=f'application/{format_name}'
            )
            
            result = file_service.validate_file(file_storage)
            assert result is False, f"Format {format_name} should not be supported"
    
    def test_validate_file_magic_bytes(self, test_image_file):
        """Test validation using magic bytes"""
        file_service = FileService()
        
        # Create file with wrong extension but correct magic bytes
        file_storage = FileStorage(
            stream=test_image_file,
            filename='test.txt',  # Wrong extension
            content_type='image/png'
        )
        
        with patch('magic.from_buffer') as mock_magic:
            mock_magic.return_value = 'PNG image data'
            
            result = file_service.validate_file_content(file_storage)
            assert result is True
    
    def test_validate_file_corrupted_image(self):
        """Test validation of corrupted image file"""
        file_service = FileService()
        
        # Create corrupted image data
        corrupted_data = b'\x89PNG\r\n\x1a\n' + b'corrupted data'
        corrupted_file = io.BytesIO(corrupted_data)
        
        file_storage = FileStorage(
            stream=corrupted_file,
            filename='test.png',
            content_type='image/png'
        )
        
        result = file_service.validate_file_content(file_storage)
        
        assert result is False
    
    def test_validate_file_dimensions(self, test_utils):
        """Test validation of file dimensions"""
        file_service = FileService()
        
        # Test minimum dimensions
        small_image = test_utils.create_test_image(width=10, height=10)
        file_storage = FileStorage(
            stream=small_image,
            filename='small.png',
            content_type='image/png'
        )
        
        result = file_service.validate_file_dimensions(file_storage)
        assert result is False  # Too small
        
        # Test maximum dimensions
        large_image = test_utils.create_test_image(width=10000, height=10000)
        file_storage = FileStorage(
            stream=large_image,
            filename='large.png',
            content_type='image/png'
        )
        
        result = file_service.validate_file_dimensions(file_storage)
        assert result is False  # Too large
        
        # Test valid dimensions
        normal_image = test_utils.create_test_image(width=500, height=500)
        file_storage = FileStorage(
            stream=normal_image,
            filename='normal.png',
            content_type='image/png'
        )
        
        result = file_service.validate_file_dimensions(file_storage)
        assert result is True


class TestFileProcessing:
    """Test file processing functionality"""
    
    def test_save_uploaded_file(self, test_image_file, temp_upload_dir):
        """Test saving uploaded file"""
        file_service = FileService()
        
        file_storage = FileStorage(
            stream=test_image_file,
            filename='test.png',
            content_type='image/png'
        )
        
        saved_path = file_service.save_uploaded_file(file_storage, temp_upload_dir)
        
        assert saved_path is not None
        assert os.path.exists(saved_path)
        assert saved_path.endswith('.png')
        
        # Verify file content
        with open(saved_path, 'rb') as f:
            content = f.read()
            assert len(content) > 0
    
    def test_save_uploaded_file_secure_filename(self, test_image_file, temp_upload_dir):
        """Test saving file with secure filename"""
        file_service = FileService()
        
        # Test with potentially dangerous filename
        file_storage = FileStorage(
            stream=test_image_file,
            filename='../../../etc/passwd.png',
            content_type='image/png'
        )
        
        saved_path = file_service.save_uploaded_file(file_storage, temp_upload_dir)
        
        assert saved_path is not None
        assert os.path.exists(saved_path)
        assert '../' not in saved_path
        assert 'etc' not in saved_path
        assert 'passwd' not in saved_path
    
    def test_save_uploaded_file_unique_filename(self, test_image_file, temp_upload_dir):
        """Test saving file with unique filename"""
        file_service = FileService()
        
        file_storage = FileStorage(
            stream=test_image_file,
            filename='test.png',
            content_type='image/png'
        )
        
        # Save same file twice
        saved_path1 = file_service.save_uploaded_file(file_storage, temp_upload_dir)
        test_image_file.seek(0)  # Reset stream
        saved_path2 = file_service.save_uploaded_file(file_storage, temp_upload_dir)
        
        assert saved_path1 != saved_path2
        assert os.path.exists(saved_path1)
        assert os.path.exists(saved_path2)
    
    def test_get_file_info(self, test_image_file, temp_upload_dir):
        """Test getting file information"""
        file_service = FileService()
        
        file_storage = FileStorage(
            stream=test_image_file,
            filename='test.png',
            content_type='image/png'
        )
        
        saved_path = file_service.save_uploaded_file(file_storage, temp_upload_dir)
        file_info = file_service.get_file_info(saved_path)
        
        assert file_info is not None
        assert 'size' in file_info
        assert 'type' in file_info
        assert 'name' in file_info
        assert 'dimensions' in file_info
        assert file_info['size'] > 0
        assert file_info['type'] == 'image/png'
        assert file_info['name'] == 'test.png'
    
    def test_process_image_optimization(self, test_image_file, temp_upload_dir):
        """Test image optimization processing"""
        file_service = FileService()
        
        file_storage = FileStorage(
            stream=test_image_file,
            filename='test.png',
            content_type='image/png'
        )
        
        saved_path = file_service.save_uploaded_file(file_storage, temp_upload_dir)
        original_size = os.path.getsize(saved_path)
        
        # Optimize image
        optimized_path = file_service.optimize_image(saved_path)
        
        assert optimized_path is not None
        assert os.path.exists(optimized_path)
        
        # Optimized file should be smaller or same size
        optimized_size = os.path.getsize(optimized_path)
        assert optimized_size <= original_size
    
    def test_generate_thumbnail(self, test_image_file, temp_upload_dir):
        """Test thumbnail generation"""
        file_service = FileService()
        
        file_storage = FileStorage(
            stream=test_image_file,
            filename='test.png',
            content_type='image/png'
        )
        
        saved_path = file_service.save_uploaded_file(file_storage, temp_upload_dir)
        
        # Generate thumbnail
        thumbnail_path = file_service.generate_thumbnail(saved_path, size=(150, 150))
        
        assert thumbnail_path is not None
        assert os.path.exists(thumbnail_path)
        
        # Verify thumbnail dimensions
        with Image.open(thumbnail_path) as img:
            assert img.size[0] <= 150
            assert img.size[1] <= 150
    
    def test_convert_image_format(self, test_image_file, temp_upload_dir):
        """Test image format conversion"""
        file_service = FileService()
        
        file_storage = FileStorage(
            stream=test_image_file,
            filename='test.png',
            content_type='image/png'
        )
        
        saved_path = file_service.save_uploaded_file(file_storage, temp_upload_dir)
        
        # Convert to JPEG
        converted_path = file_service.convert_image_format(saved_path, 'JPEG')
        
        assert converted_path is not None
        assert os.path.exists(converted_path)
        assert converted_path.endswith('.jpg')
        
        # Verify converted file is valid JPEG
        with Image.open(converted_path) as img:
            assert img.format == 'JPEG'
    
    def test_cleanup_temp_files(self, temp_upload_dir):
        """Test cleanup of temporary files"""
        file_service = FileService()
        
        # Create temporary files
        temp_files = []
        for i in range(5):
            temp_file = os.path.join(temp_upload_dir, f'temp_{i}.png')
            with open(temp_file, 'wb') as f:
                f.write(b'temp content')
            temp_files.append(temp_file)
        
        # Verify files exist
        for temp_file in temp_files:
            assert os.path.exists(temp_file)
        
        # Cleanup
        cleaned_count = file_service.cleanup_temp_files(temp_upload_dir, max_age_hours=0)
        
        assert cleaned_count == 5
        
        # Verify files are deleted
        for temp_file in temp_files:
            assert not os.path.exists(temp_file)
    
    def test_extract_metadata(self, test_image_file, temp_upload_dir):
        """Test extracting image metadata"""
        file_service = FileService()
        
        file_storage = FileStorage(
            stream=test_image_file,
            filename='test.png',
            content_type='image/png'
        )
        
        saved_path = file_service.save_uploaded_file(file_storage, temp_upload_dir)
        
        # Extract metadata
        metadata = file_service.extract_metadata(saved_path)
        
        assert metadata is not None
        assert 'format' in metadata
        assert 'mode' in metadata
        assert 'size' in metadata
        assert metadata['format'] == 'PNG'
        assert metadata['size'] == (100, 100)  # Default test image size


class TestFileSecurityScanning:
    """Test file security scanning"""
    
    def test_scan_for_malware(self, test_image_file, temp_upload_dir):
        """Test malware scanning"""
        file_service = FileService()
        
        file_storage = FileStorage(
            stream=test_image_file,
            filename='test.png',
            content_type='image/png'
        )
        
        saved_path = file_service.save_uploaded_file(file_storage, temp_upload_dir)
        
        # Mock malware scanner
        with patch('services.security_service.SecurityService.scan_for_malware') as mock_scan:
            mock_scan.return_value = True  # Clean file
            
            result = file_service.scan_file_security(saved_path)
            assert result is True
            mock_scan.assert_called_once_with(saved_path)
    
    def test_scan_malicious_file(self, security_test_helpers, temp_upload_dir):
        """Test scanning malicious file"""
        file_service = FileService()
        
        malicious_file = security_test_helpers.create_malicious_file()
        file_storage = FileStorage(
            stream=malicious_file,
            filename='malicious.png',
            content_type='image/png'
        )
        
        saved_path = file_service.save_uploaded_file(file_storage, temp_upload_dir)
        
        # Mock malware scanner detecting threat
        with patch('services.security_service.SecurityService.scan_for_malware') as mock_scan:
            mock_scan.return_value = False  # Malicious file
            
            result = file_service.scan_file_security(saved_path)
            assert result is False
            mock_scan.assert_called_once_with(saved_path)
    
    def test_validate_file_signatures(self, test_image_file):
        """Test file signature validation"""
        file_service = FileService()
        
        file_storage = FileStorage(
            stream=test_image_file,
            filename='test.png',
            content_type='image/png'
        )
        
        # Mock file signature validation
        with patch('magic.from_buffer') as mock_magic:
            mock_magic.return_value = 'PNG image data'
            
            result = file_service.validate_file_signature(file_storage)
            assert result is True
    
    def test_validate_executable_files(self):
        """Test validation rejects executable files"""
        file_service = FileService()
        
        # Create fake executable file
        exe_content = b'MZ\x90\x00'  # DOS header
        exe_file = io.BytesIO(exe_content)
        
        file_storage = FileStorage(
            stream=exe_file,
            filename='malicious.exe',
            content_type='application/octet-stream'
        )
        
        result = file_service.validate_file(file_storage)
        assert result is False
    
    def test_validate_script_files(self):
        """Test validation rejects script files"""
        file_service = FileService()
        
        # Create fake script file
        script_content = b'#!/bin/bash\nrm -rf /'
        script_file = io.BytesIO(script_content)
        
        file_storage = FileStorage(
            stream=script_file,
            filename='malicious.sh',
            content_type='application/x-sh'
        )
        
        result = file_service.validate_file(file_storage)
        assert result is False
    
    def test_validate_embedded_scripts(self):
        """Test validation detects embedded scripts"""
        file_service = FileService()
        
        # Create image with embedded script
        malicious_content = b'\x89PNG\r\n\x1a\n<script>alert("xss")</script>'
        malicious_file = io.BytesIO(malicious_content)
        
        file_storage = FileStorage(
            stream=malicious_file,
            filename='malicious.png',
            content_type='image/png'
        )
        
        result = file_service.validate_file_content(file_storage)
        assert result is False
    
    def test_quarantine_malicious_file(self, security_test_helpers, temp_upload_dir):
        """Test quarantining malicious files"""
        file_service = FileService()
        
        malicious_file = security_test_helpers.create_malicious_file()
        file_storage = FileStorage(
            stream=malicious_file,
            filename='malicious.png',
            content_type='image/png'
        )
        
        saved_path = file_service.save_uploaded_file(file_storage, temp_upload_dir)
        
        # Quarantine file
        quarantine_path = file_service.quarantine_file(saved_path)
        
        assert quarantine_path is not None
        assert os.path.exists(quarantine_path)
        assert not os.path.exists(saved_path)  # Original file should be moved
        assert 'quarantine' in quarantine_path


class TestFileUploadErrors:
    """Test file upload error handling"""
    
    def test_save_file_permission_error(self, test_image_file):
        """Test handling of permission errors"""
        file_service = FileService()
        
        file_storage = FileStorage(
            stream=test_image_file,
            filename='test.png',
            content_type='image/png'
        )
        
        # Mock permission error
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            with pytest.raises(PermissionError):
                file_service.save_uploaded_file(file_storage, '/invalid/path')
    
    def test_save_file_disk_full_error(self, test_image_file, temp_upload_dir):
        """Test handling of disk full errors"""
        file_service = FileService()
        
        file_storage = FileStorage(
            stream=test_image_file,
            filename='test.png',
            content_type='image/png'
        )
        
        # Mock disk full error
        with patch('builtins.open', side_effect=OSError("No space left on device")):
            with pytest.raises(OSError):
                file_service.save_uploaded_file(file_storage, temp_upload_dir)
    
    def test_invalid_image_processing(self, temp_upload_dir):
        """Test handling of invalid image processing"""
        file_service = FileService()
        
        # Create invalid image file
        invalid_content = b'This is not a valid image'
        invalid_file = io.BytesIO(invalid_content)
        
        file_storage = FileStorage(
            stream=invalid_file,
            filename='invalid.png',
            content_type='image/png'
        )
        
        saved_path = file_service.save_uploaded_file(file_storage, temp_upload_dir)
        
        # Try to process invalid image
        with pytest.raises(Exception):
            file_service.optimize_image(saved_path)
    
    def test_file_corruption_detection(self, temp_upload_dir):
        """Test detection of file corruption"""
        file_service = FileService()
        
        # Create corrupted PNG file
        corrupted_content = b'\x89PNG\r\n\x1a\n' + b'corrupted' * 100
        corrupted_file = io.BytesIO(corrupted_content)
        
        file_storage = FileStorage(
            stream=corrupted_file,
            filename='corrupted.png',
            content_type='image/png'
        )
        
        saved_path = file_service.save_uploaded_file(file_storage, temp_upload_dir)
        
        # Validate file integrity
        result = file_service.validate_file_integrity(saved_path)
        assert result is False
    
    def test_concurrent_file_uploads(self, test_image_files, temp_upload_dir):
        """Test concurrent file uploads"""
        file_service = FileService()
        
        import threading
        results = []
        errors = []
        
        def upload_file(file_data, filename):
            try:
                file_storage = FileStorage(
                    stream=file_data,
                    filename=filename,
                    content_type='image/png'
                )
                
                saved_path = file_service.save_uploaded_file(file_storage, temp_upload_dir)
                results.append(saved_path)
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads
        threads = []
        for i, (name, file_data) in enumerate(test_image_files.items()):
            thread = threading.Thread(target=upload_file, args=(file_data, f'{name}.png'))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All uploads should succeed
        assert len(results) == len(test_image_files)
        assert len(errors) == 0
        
        # All files should exist
        for saved_path in results:
            assert os.path.exists(saved_path)


class TestFileUploadIntegration:
    """Test file upload integration with other services"""
    
    def test_upload_with_vectorization(self, test_image_file, temp_upload_dir, mock_vectorization_service):
        """Test file upload with vectorization service"""
        file_service = FileService()
        
        file_storage = FileStorage(
            stream=test_image_file,
            filename='test.png',
            content_type='image/png'
        )
        
        saved_path = file_service.save_uploaded_file(file_storage, temp_upload_dir)
        
        # Process with vectorization service
        result = file_service.process_for_vectorization(saved_path, 'vtracer_high_fidelity')
        
        assert result is not None
        assert 'processed_path' in result
        assert 'metadata' in result
        assert os.path.exists(result['processed_path'])
    
    def test_upload_with_user_tracking(self, test_image_file, temp_upload_dir, created_user):
        """Test file upload with user tracking"""
        file_service = FileService()
        
        file_storage = FileStorage(
            stream=test_image_file,
            filename='test.png',
            content_type='image/png'
        )
        
        saved_path = file_service.save_uploaded_file(file_storage, temp_upload_dir)
        
        # Track upload for user
        file_service.track_user_upload(created_user['id'], saved_path)
        
        # Verify tracking
        user_uploads = file_service.get_user_uploads(created_user['id'])
        assert len(user_uploads) == 1
        assert user_uploads[0]['file_path'] == saved_path
    
    def test_upload_with_quota_checking(self, test_image_file, temp_upload_dir, created_user):
        """Test file upload with quota checking"""
        file_service = FileService()
        
        # Set user quota limit
        file_service.set_user_quota(created_user['id'], max_files=2, max_size_mb=10)
        
        file_storage = FileStorage(
            stream=test_image_file,
            filename='test.png',
            content_type='image/png'
        )
        
        # First upload should succeed
        saved_path1 = file_service.save_uploaded_file(file_storage, temp_upload_dir)
        assert saved_path1 is not None
        
        # Second upload should succeed
        test_image_file.seek(0)
        saved_path2 = file_service.save_uploaded_file(file_storage, temp_upload_dir)
        assert saved_path2 is not None
        
        # Third upload should fail (quota exceeded)
        test_image_file.seek(0)
        with pytest.raises(Exception, match="Quota exceeded"):
            file_service.save_uploaded_file(file_storage, temp_upload_dir)
    
    def test_upload_with_backup(self, test_image_file, temp_upload_dir):
        """Test file upload with backup creation"""
        file_service = FileService()
        
        file_storage = FileStorage(
            stream=test_image_file,
            filename='test.png',
            content_type='image/png'
        )
        
        saved_path = file_service.save_uploaded_file(file_storage, temp_upload_dir)
        
        # Create backup
        backup_path = file_service.create_backup(saved_path)
        
        assert backup_path is not None
        assert os.path.exists(backup_path)
        assert backup_path != saved_path
        
        # Verify backup content matches original
        with open(saved_path, 'rb') as f1, open(backup_path, 'rb') as f2:
            assert f1.read() == f2.read()


class TestFileUploadPerformance:
    """Test file upload performance"""
    
    def test_upload_performance_small_file(self, test_utils, temp_upload_dir, performance_test_helpers):
        """Test upload performance with small file"""
        file_service = FileService()
        
        small_image = test_utils.create_test_image(width=100, height=100)
        file_storage = FileStorage(
            stream=small_image,
            filename='small.png',
            content_type='image/png'
        )
        
        performance_test_helpers.start_timer()
        
        saved_path = file_service.save_uploaded_file(file_storage, temp_upload_dir)
        
        upload_time = performance_test_helpers.end_timer('small_upload')
        performance_test_helpers.assert_performance('small_upload', 1.0)  # Should be under 1 second
        
        assert saved_path is not None
        assert os.path.exists(saved_path)
    
    def test_upload_performance_large_file(self, test_utils, temp_upload_dir, performance_test_helpers):
        """Test upload performance with large file"""
        file_service = FileService()
        
        large_image = test_utils.create_test_image(width=2000, height=2000)
        file_storage = FileStorage(
            stream=large_image,
            filename='large.png',
            content_type='image/png'
        )
        
        performance_test_helpers.start_timer()
        
        saved_path = file_service.save_uploaded_file(file_storage, temp_upload_dir)
        
        upload_time = performance_test_helpers.end_timer('large_upload')
        performance_test_helpers.assert_performance('large_upload', 5.0)  # Should be under 5 seconds
        
        assert saved_path is not None
        assert os.path.exists(saved_path)
    
    def test_bulk_upload_performance(self, test_image_files, temp_upload_dir, performance_test_helpers):
        """Test bulk upload performance"""
        file_service = FileService()
        
        performance_test_helpers.start_timer()
        
        saved_paths = []
        for name, file_data in test_image_files.items():
            file_storage = FileStorage(
                stream=file_data,
                filename=f'{name}.png',
                content_type='image/png'
            )
            
            saved_path = file_service.save_uploaded_file(file_storage, temp_upload_dir)
            saved_paths.append(saved_path)
        
        bulk_upload_time = performance_test_helpers.end_timer('bulk_upload')
        performance_test_helpers.assert_performance('bulk_upload', 10.0)  # Should be under 10 seconds
        
        assert len(saved_paths) == len(test_image_files)
        for saved_path in saved_paths:
            assert os.path.exists(saved_path)
    
    def test_memory_usage_during_upload(self, test_utils, temp_upload_dir):
        """Test memory usage during file upload"""
        file_service = FileService()
        
        import psutil
        process = psutil.Process()
        
        initial_memory = process.memory_info().rss
        
        # Upload multiple files
        for i in range(10):
            image_file = test_utils.create_test_image(width=500, height=500)
            file_storage = FileStorage(
                stream=image_file,
                filename=f'test_{i}.png',
                content_type='image/png'
            )
            
            saved_path = file_service.save_uploaded_file(file_storage, temp_upload_dir)
            assert os.path.exists(saved_path)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024


@pytest.mark.parametrize("file_extension,content_type,expected_valid", [
    ('png', 'image/png', True),
    ('jpg', 'image/jpeg', True),
    ('jpeg', 'image/jpeg', True),
    ('gif', 'image/gif', True),
    ('bmp', 'image/bmp', True),
    ('tiff', 'image/tiff', True),
    ('svg', 'image/svg+xml', False),
    ('pdf', 'application/pdf', False),
    ('txt', 'text/plain', False),
    ('exe', 'application/octet-stream', False),
])
def test_file_validation_parametrized(file_extension, content_type, expected_valid):
    """Test file validation with parametrized inputs"""
    file_service = FileService()
    
    fake_file = io.BytesIO(b'fake content')
    file_storage = FileStorage(
        stream=fake_file,
        filename=f'test.{file_extension}',
        content_type=content_type
    )
    
    result = file_service.validate_file(file_storage)
    assert result == expected_valid


class TestFileUploadCleanup:
    """Test file upload cleanup functionality"""
    
    def test_cleanup_on_success(self, test_image_file, temp_upload_dir):
        """Test cleanup after successful upload"""
        file_service = FileService()
        
        file_storage = FileStorage(
            stream=test_image_file,
            filename='test.png',
            content_type='image/png'
        )
        
        saved_path = file_service.save_uploaded_file(file_storage, temp_upload_dir)
        
        # Process file and cleanup
        file_service.cleanup_after_processing(saved_path)
        
        # Temporary files should be cleaned up
        temp_files = file_service.get_temp_files(temp_upload_dir)
        assert len(temp_files) == 0
    
    def test_cleanup_on_failure(self, test_image_file, temp_upload_dir):
        """Test cleanup after failed upload"""
        file_service = FileService()
        
        file_storage = FileStorage(
            stream=test_image_file,
            filename='test.png',
            content_type='image/png'
        )
        
        saved_path = file_service.save_uploaded_file(file_storage, temp_upload_dir)
        
        # Simulate processing failure
        with patch('services.file_service.FileService.process_for_vectorization') as mock_process:
            mock_process.side_effect = Exception("Processing failed")
            
            with pytest.raises(Exception):
                file_service.process_for_vectorization(saved_path, 'vtracer_high_fidelity')
            
            # Cleanup should still happen
            file_service.cleanup_after_error(saved_path)
            
            # File should be removed
            assert not os.path.exists(saved_path)
    
    def test_periodic_cleanup(self, temp_upload_dir):
        """Test periodic cleanup of old files"""
        file_service = FileService()
        
        # Create old files
        import time
        old_files = []
        for i in range(5):
            old_file = os.path.join(temp_upload_dir, f'old_{i}.png')
            with open(old_file, 'wb') as f:
                f.write(b'old content')
            old_files.append(old_file)
            
            # Make file appear old
            old_time = time.time() - 3600  # 1 hour ago
            os.utime(old_file, (old_time, old_time))
        
        # Create recent file
        recent_file = os.path.join(temp_upload_dir, 'recent.png')
        with open(recent_file, 'wb') as f:
            f.write(b'recent content')
        
        # Run periodic cleanup
        cleaned_count = file_service.periodic_cleanup(temp_upload_dir, max_age_hours=0.5)
        
        assert cleaned_count == 5
        
        # Old files should be deleted
        for old_file in old_files:
            assert not os.path.exists(old_file)
        
        # Recent file should remain
        assert os.path.exists(recent_file)