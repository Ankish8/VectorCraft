"""
Vectorization service layer for VectorCraft
Handles vectorization operations, file processing, and optimization
"""

import os
import time
import uuid
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

from database_optimized import db_optimized
from .monitoring import system_logger
from .file_service import file_service

logger = logging.getLogger(__name__)


class VectorizationService:
    """Service layer for vectorization operations"""
    
    def __init__(self, db=None):
        self.db = db or db_optimized
        self.logger = logger
        self.file_service = file_service
        
        # Initialize vectorizers lazily
        self._standard_vectorizer = None
        self._optimized_vectorizer = None
        
        # Vectorization settings
        self.supported_strategies = [
            'vtracer_high_fidelity',
            'experimental_v2',
            'vtracer_experimental'
        ]
        
        self.default_strategy = 'vtracer_high_fidelity'
        self.default_target_time = 60.0
    
    @property
    def standard_vectorizer(self):
        """Lazy initialization of standard vectorizer"""
        if self._standard_vectorizer is None:
            try:
                from vectorcraft import HybridVectorizer
                self._standard_vectorizer = HybridVectorizer()
                self.logger.info("Standard vectorizer initialized")
            except ImportError as e:
                self.logger.error(f"Failed to import HybridVectorizer: {e}")
                raise
        return self._standard_vectorizer
    
    @property
    def optimized_vectorizer(self):
        """Lazy initialization of optimized vectorizer"""
        if self._optimized_vectorizer is None:
            try:
                from vectorcraft import OptimizedVectorizer
                self._optimized_vectorizer = OptimizedVectorizer()
                self.logger.info("Optimized vectorizer initialized")
            except ImportError as e:
                self.logger.error(f"Failed to import OptimizedVectorizer: {e}")
                raise
        return self._optimized_vectorizer
    
    def vectorize_image(self, 
                       user_id: int,
                       file_path: str,
                       filename: str,
                       strategy: str = None,
                       target_time: float = None,
                       vectorization_params: Dict[str, Any] = None,
                       use_palette: bool = False,
                       selected_palette: List[List[int]] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Vectorize an image file
        
        Returns:
            Tuple[bool, Dict[str, Any]]: (success, result_data)
        """
        try:
            # Validate inputs
            if not self._validate_vectorization_inputs(user_id, file_path, filename, strategy):
                return False, {'error': 'Invalid input parameters'}
            
            # Set defaults
            strategy = strategy or self.default_strategy
            target_time = target_time or self.default_target_time
            vectorization_params = vectorization_params or {}
            
            # Get file info
            file_size = os.path.getsize(file_path)
            
            # Log vectorization start
            system_logger.info('vectorization', f'Vectorization started for {filename}',
                              user_email=self._get_user_email(user_id),
                              details={
                                  'filename': filename,
                                  'file_size': file_size,
                                  'strategy': strategy,
                                  'user_id': user_id
                              })
            
            # Prepare vectorizer
            vectorizer = self.optimized_vectorizer
            
            # Set custom parameters if provided
            if vectorization_params and hasattr(vectorizer, 'real_vtracer'):
                if vectorizer.real_vtracer.available:
                    vectorizer.real_vtracer.set_custom_parameters(vectorization_params)
            
            # Override strategy selection if needed
            if hasattr(vectorizer, 'adaptive_optimizer'):
                original_optimize = vectorizer.adaptive_optimizer.optimize_strategy_selection
                vectorizer.adaptive_optimizer.optimize_strategy_selection = lambda metadata, elapsed: strategy
            
            # Perform vectorization
            start_time = time.time()
            
            if use_palette and selected_palette and strategy == 'experimental':
                result = self._vectorize_with_palette(file_path, selected_palette)
            else:
                result = vectorizer.vectorize(file_path, target_time=target_time)
            
            processing_time = time.time() - start_time
            
            # Restore original strategy selection
            if hasattr(vectorizer, 'adaptive_optimizer'):
                vectorizer.adaptive_optimizer.optimize_strategy_selection = original_optimize
            
            # Clear custom parameters
            if vectorization_params and hasattr(vectorizer, 'real_vtracer'):
                if vectorizer.real_vtracer.available:
                    vectorizer.real_vtracer.custom_params = None
            
            # Save result
            success, result_data = self._save_vectorization_result(
                user_id, result, filename, strategy, file_size, 
                use_palette, selected_palette, processing_time
            )
            
            if success:
                # Log successful completion
                system_logger.info('vectorization', f'Vectorization completed successfully',
                                  user_email=self._get_user_email(user_id),
                                  details={
                                      'filename': filename,
                                      'processing_time': processing_time,
                                      'strategy': strategy,
                                      'quality_score': result.quality_score,
                                      'file_size': file_size
                                  })
                
                return True, result_data
            else:
                return False, result_data
                
        except Exception as e:
            error_msg = f"Vectorization failed: {str(e)}"
            self.logger.error(error_msg)
            
            # Log error
            system_logger.error('vectorization', error_msg,
                               user_email=self._get_user_email(user_id),
                               details={
                                   'filename': filename,
                                   'error': str(e),
                                   'user_id': user_id
                               })
            
            return False, {'error': error_msg}
    
    def extract_color_palettes(self, file_path: str) -> Tuple[bool, Dict[str, Any]]:
        """Extract color palettes from an image"""
        try:
            # Load image
            from PIL import Image
            import numpy as np
            
            image = Image.open(file_path)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            image_array = np.array(image)
            
            # Extract palettes using experimental strategy
            from vectorcraft.strategies.experimental_vtracer_v3 import ExperimentalVTracerV3Strategy
            experimental_strategy = ExperimentalVTracerV3Strategy()
            
            palettes = experimental_strategy.extract_color_palettes(image_array)
            
            # Convert numpy int64 to regular Python int for JSON serialization
            json_palettes = {}
            for key, palette in palettes.items():
                json_palettes[key] = [[int(color[0]), int(color[1]), int(color[2])] for color in palette]
            
            return True, {'palettes': json_palettes}
            
        except Exception as e:
            self.logger.error(f"Palette extraction failed: {e}")
            return False, {'error': str(e)}
    
    def generate_palette_preview(self, file_path: str, selected_palette: List[List[int]]) -> Tuple[bool, Dict[str, Any]]:
        """Generate a preview with selected palette"""
        try:
            # Load image
            from PIL import Image
            import numpy as np
            import base64
            from io import BytesIO
            
            image = Image.open(file_path)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            image_array = np.array(image)
            
            # Generate preview using experimental strategy
            from vectorcraft.strategies.experimental_vtracer_v3 import ExperimentalVTracerV3Strategy
            experimental_strategy = ExperimentalVTracerV3Strategy()
            
            preview_image = experimental_strategy.create_quantized_preview(image_array, selected_palette)
            
            # Convert preview to base64
            preview_pil = Image.fromarray(preview_image.astype('uint8'))
            buffer = BytesIO()
            preview_pil.save(buffer, format='PNG')
            buffer.seek(0)
            
            preview_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return True, {'preview_image': f'data:image/png;base64,{preview_base64}'}
            
        except Exception as e:
            self.logger.error(f"Palette preview generation failed: {e}")
            return False, {'error': str(e)}
    
    def get_user_uploads(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get user's upload history"""
        try:
            return self.db.get_user_uploads(user_id, limit=limit)
        except Exception as e:
            self.logger.error(f"Error getting user uploads: {e}")
            return []
    
    def get_user_upload_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user's upload statistics"""
        try:
            return self.db.get_upload_stats(user_id)
        except Exception as e:
            self.logger.error(f"Error getting upload stats: {e}")
            return {
                'total_uploads': 0,
                'avg_processing_time': 0,
                'total_file_size': 0,
                'avg_quality_score': 0
            }
    
    def get_supported_strategies(self) -> List[str]:
        """Get list of supported vectorization strategies"""
        return self.supported_strategies.copy()
    
    def validate_strategy(self, strategy: str) -> bool:
        """Validate if strategy is supported"""
        return strategy in self.supported_strategies
    
    def get_default_vectorization_params(self) -> Dict[str, Any]:
        """Get default vectorization parameters"""
        return {
            'filter_speckle': 4,
            'color_precision': 8,
            'layer_difference': 8,
            'corner_threshold': 90,
            'length_threshold': 1.0,
            'splice_threshold': 20,
            'curve_fitting': 'spline'
        }
    
    def _validate_vectorization_inputs(self, user_id: int, file_path: str, filename: str, strategy: str) -> bool:
        """Validate vectorization inputs"""
        # Check user_id
        if not user_id or user_id <= 0:
            return False
        
        # Check file path
        if not file_path or not os.path.exists(file_path):
            return False
        
        # Check filename
        if not filename or len(filename) == 0:
            return False
        
        # Check strategy
        if strategy and not self.validate_strategy(strategy):
            return False
        
        return True
    
    def _vectorize_with_palette(self, file_path: str, selected_palette: List[List[int]]):
        """Vectorize image with custom palette"""
        from PIL import Image
        import numpy as np
        from vectorcraft.strategies.experimental_vtracer_v3 import ExperimentalVTracerV3Strategy
        
        # Load image
        image = Image.open(file_path)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        image_array = np.array(image)
        
        # Use experimental strategy with palette
        experimental_strategy = ExperimentalVTracerV3Strategy()
        palette_result = experimental_strategy.vectorize_with_palette(
            image_array, selected_palette, None, None
        )
        
        # Create result-like object
        class ImageMetadata:
            def __init__(self, image):
                self.width = image.width
                self.height = image.height
                self.edge_density = 0.5
                self.text_probability = 0.1
                self.geometric_probability = 0.8
                self.gradient_probability = 0.2
        
        class PaletteResult:
            def __init__(self, svg_builder, processing_time, image):
                self.svg_builder = svg_builder
                self.processing_time = processing_time
                self.strategy_used = f"experimental_palette_{len(selected_palette)}_colors"
                self.quality_score = 0.85
                self.metadata = {
                    'content_type': 'palette_based',
                    'num_elements': len(svg_builder.elements) if hasattr(svg_builder, 'elements') else 0,
                    'palette_colors': len(selected_palette),
                    'image_metadata': ImageMetadata(image),
                    'performance_stats': {}
                }
        
        return PaletteResult(palette_result, time.time() - time.time(), image)
    
    def _save_vectorization_result(self, user_id: int, result, filename: str, strategy: str, 
                                  file_size: int, use_palette: bool, selected_palette: List[List[int]], 
                                  processing_time: float) -> Tuple[bool, Dict[str, Any]]:
        """Save vectorization result to database and file system"""
        try:
            unique_id = str(uuid.uuid4())
            
            # Create result filenames
            version_suffix = "_v1.0.0-experimental" if strategy == 'experimental' else ""
            palette_suffix = f"_palette_{len(selected_palette)}colors" if use_palette and selected_palette else ""
            svg_filename = f"{unique_id}_result{version_suffix}{palette_suffix}.svg"
            
            # Save SVG file
            svg_path = os.path.join('results', svg_filename)
            output_path = os.path.join('output', f"{int(time.time())}_{strategy}_result.svg")
            
            # Ensure directories exist
            os.makedirs('results', exist_ok=True)
            os.makedirs('output', exist_ok=True)
            
            # Get SVG content
            if hasattr(result, 'svg_builder') and result.svg_builder:
                svg_content = result.svg_builder.get_svg_string()
                result.svg_builder.save(svg_path)
                result.svg_builder.save(output_path)
            else:
                svg_content = result.get_svg_string()
                with open(svg_path, 'w') as f:
                    f.write(svg_content)
                with open(output_path, 'w') as f:
                    f.write(svg_content)
            
            # Record in database
            self.db.record_upload(
                user_id=user_id,
                filename=f"{unique_id}_{filename}",
                original_filename=filename,
                file_size=file_size,
                svg_filename=svg_filename,
                processing_time=processing_time,
                strategy_used=result.strategy_used,
                quality_score=result.quality_score
            )
            
            # Convert SVG to base64
            import base64
            svg_b64 = base64.b64encode(svg_content.encode()).decode()
            
            result_data = {
                'success': True,
                'processing_time': processing_time,
                'strategy_used': result.strategy_used,
                'quality_score': result.quality_score,
                'num_elements': result.metadata.get('num_elements', 0),
                'content_type': result.metadata.get('content_type', 'standard'),
                'svg_content': svg_content,
                'svg_b64': svg_b64,
                'svg_filename': svg_filename,
                'metadata': {
                    'image_size': f"{result.metadata['image_metadata'].width}x{result.metadata['image_metadata'].height}",
                    'edge_density': result.metadata['image_metadata'].edge_density,
                    'text_probability': result.metadata['image_metadata'].text_probability,
                    'geometric_probability': result.metadata['image_metadata'].geometric_probability,
                    'gradient_probability': result.metadata['image_metadata'].gradient_probability,
                    'performance_stats': result.metadata.get('performance_stats', {})
                }
            }
            
            return True, result_data
            
        except Exception as e:
            self.logger.error(f"Error saving vectorization result: {e}")
            return False, {'error': str(e)}
    
    def _get_user_email(self, user_id: int) -> Optional[str]:
        """Get user email for logging"""
        try:
            user = self.db.get_user_by_id(user_id)
            return user['email'] if user else None
        except:
            return None


# Global vectorization service instance
vectorization_service = VectorizationService()


if __name__ == '__main__':
    # Test the vectorization service
    logger.info("Testing VectorCraft Vectorization Service...")
    
    # Test strategy validation
    assert vectorization_service.validate_strategy('vtracer_high_fidelity') == True
    assert vectorization_service.validate_strategy('invalid_strategy') == False
    
    # Test default parameters
    params = vectorization_service.get_default_vectorization_params()
    assert 'filter_speckle' in params
    assert 'color_precision' in params
    
    # Test supported strategies
    strategies = vectorization_service.get_supported_strategies()
    assert len(strategies) > 0
    assert 'vtracer_high_fidelity' in strategies
    
    logger.info("Vectorization service test completed successfully!")