"""
Vectorization service layer for VectorCraft
Handles vectorization operations, file processing, and optimization
"""

import os
import time
import uuid
import json
import logging
import statistics
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from collections import defaultdict

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
        
        # Analytics tracking
        self.analytics_data = {
            'daily_stats': defaultdict(lambda: {
                'total_vectorizations': 0,
                'total_processing_time': 0,
                'avg_quality_score': 0,
                'strategy_usage': defaultdict(int),
                'error_count': 0,
                'file_size_distribution': defaultdict(int)
            }),
            'real_time_metrics': {
                'active_vectorizations': 0,
                'queue_size': 0,
                'avg_processing_time': 0,
                'success_rate': 0
            }
        }
    
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
    
    # === ANALYTICS AND MONITORING METHODS ===
    
    def get_vectorization_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive vectorization analytics"""
        try:
            # Get data from database
            analytics = self.db.get_vectorization_analytics(days)
            
            # Process and enhance data
            processed_analytics = {
                'summary': {
                    'total_vectorizations': analytics.get('total_vectorizations', 0),
                    'total_processing_time': analytics.get('total_processing_time', 0),
                    'avg_processing_time': analytics.get('avg_processing_time', 0),
                    'avg_quality_score': analytics.get('avg_quality_score', 0),
                    'success_rate': analytics.get('success_rate', 0),
                    'total_file_size': analytics.get('total_file_size', 0)
                },
                'daily_breakdown': analytics.get('daily_breakdown', []),
                'strategy_performance': analytics.get('strategy_performance', {}),
                'file_size_distribution': analytics.get('file_size_distribution', {}),
                'quality_trends': analytics.get('quality_trends', []),
                'error_analysis': analytics.get('error_analysis', {}),
                'performance_metrics': self._calculate_performance_metrics(analytics)
            }
            
            return processed_analytics
            
        except Exception as e:
            self.logger.error(f"Error getting vectorization analytics: {e}")
            return self._get_default_analytics()
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time vectorization metrics"""
        try:
            # Get current active vectorizations
            active_count = self._get_active_vectorizations_count()
            
            # Get recent performance data
            recent_metrics = self.db.get_recent_vectorization_metrics(hours=1)
            
            # Calculate real-time metrics
            metrics = {
                'active_vectorizations': active_count,
                'queue_size': self._get_queue_size(),
                'recent_completions': recent_metrics.get('completions', 0),
                'recent_errors': recent_metrics.get('errors', 0),
                'avg_processing_time': recent_metrics.get('avg_processing_time', 0),
                'success_rate': recent_metrics.get('success_rate', 0),
                'throughput_per_hour': recent_metrics.get('throughput', 0),
                'system_load': self._get_system_load(),
                'memory_usage': self._get_memory_usage(),
                'disk_usage': self._get_disk_usage()
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error getting real-time metrics: {e}")
            return self._get_default_real_time_metrics()
    
    def get_quality_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get quality analysis metrics"""
        try:
            quality_data = self.db.get_quality_metrics(days)
            
            # Process quality data
            quality_metrics = {
                'average_quality': quality_data.get('avg_quality', 0),
                'quality_distribution': quality_data.get('distribution', {}),
                'quality_trends': quality_data.get('trends', []),
                'strategy_quality': quality_data.get('strategy_quality', {}),
                'improvement_opportunities': self._analyze_quality_improvements(quality_data),
                'quality_benchmarks': {
                    'excellent': {'min': 0.9, 'count': quality_data.get('excellent_count', 0)},
                    'good': {'min': 0.7, 'count': quality_data.get('good_count', 0)},
                    'fair': {'min': 0.5, 'count': quality_data.get('fair_count', 0)},
                    'poor': {'min': 0.0, 'count': quality_data.get('poor_count', 0)}
                }
            }
            
            return quality_metrics
            
        except Exception as e:
            self.logger.error(f"Error getting quality metrics: {e}")
            return self._get_default_quality_metrics()
    
    def get_storage_analytics(self) -> Dict[str, Any]:
        """Get storage and file analytics"""
        try:
            storage_data = self.db.get_storage_analytics()
            
            # Calculate storage metrics
            storage_metrics = {
                'total_files': storage_data.get('total_files', 0),
                'total_size': storage_data.get('total_size', 0),
                'avg_file_size': storage_data.get('avg_file_size', 0),
                'file_type_distribution': storage_data.get('file_types', {}),
                'storage_growth': storage_data.get('growth_trend', []),
                'large_files': storage_data.get('large_files', []),
                'optimization_suggestions': self._get_storage_optimization_suggestions(storage_data),
                'disk_usage': {
                    'uploads': self._get_directory_size('uploads'),
                    'results': self._get_directory_size('results'),
                    'temp': self._get_directory_size('temp')
                }
            }
            
            return storage_metrics
            
        except Exception as e:
            self.logger.error(f"Error getting storage analytics: {e}")
            return self._get_default_storage_analytics()
    
    def get_performance_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """Get performance optimization suggestions"""
        try:
            suggestions = []
            
            # Analyze recent performance
            recent_data = self.db.get_recent_vectorization_metrics(hours=24)
            
            # Check processing times
            if recent_data.get('avg_processing_time', 0) > 45:
                suggestions.append({
                    'type': 'performance',
                    'priority': 'high',
                    'title': 'High Processing Times Detected',
                    'description': 'Average processing time is above 45 seconds',
                    'recommendation': 'Consider optimizing vectorization parameters or upgrading hardware',
                    'impact': 'User experience and throughput'
                })
            
            # Check error rates
            if recent_data.get('error_rate', 0) > 0.1:
                suggestions.append({
                    'type': 'reliability',
                    'priority': 'high',
                    'title': 'High Error Rate Detected',
                    'description': f'Error rate is {recent_data.get("error_rate", 0):.1%}',
                    'recommendation': 'Review error logs and improve error handling',
                    'impact': 'System reliability and user satisfaction'
                })
            
            # Check storage usage
            storage_data = self.get_storage_analytics()
            if storage_data.get('total_size', 0) > 10 * 1024 * 1024 * 1024:  # 10GB
                suggestions.append({
                    'type': 'storage',
                    'priority': 'medium',
                    'title': 'High Storage Usage',
                    'description': 'Storage usage is above 10GB',
                    'recommendation': 'Implement file cleanup policies and compression',
                    'impact': 'Storage costs and system performance'
                })
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error getting optimization suggestions: {e}")
            return []
    
    def optimize_vectorization_parameters(self, image_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize vectorization parameters based on image characteristics"""
        try:
            # Get base parameters
            params = self.get_default_vectorization_params()
            
            # Optimize based on image size
            width = image_metadata.get('width', 0)
            height = image_metadata.get('height', 0)
            
            if width > 2048 or height > 2048:
                # High resolution images
                params['filter_speckle'] = 8
                params['color_precision'] = 6
                params['layer_difference'] = 12
            elif width < 512 or height < 512:
                # Low resolution images
                params['filter_speckle'] = 2
                params['color_precision'] = 12
                params['layer_difference'] = 4
            
            # Optimize based on content type
            edge_density = image_metadata.get('edge_density', 0.5)
            if edge_density > 0.7:
                # High detail images
                params['corner_threshold'] = 70
                params['length_threshold'] = 0.5
            elif edge_density < 0.3:
                # Simple images
                params['corner_threshold'] = 110
                params['length_threshold'] = 2.0
            
            return params
            
        except Exception as e:
            self.logger.error(f"Error optimizing parameters: {e}")
            return self.get_default_vectorization_params()
    
    def _calculate_performance_metrics(self, analytics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate performance metrics from analytics data"""
        try:
            total_vectorizations = analytics.get('total_vectorizations', 0)
            total_processing_time = analytics.get('total_processing_time', 0)
            
            if total_vectorizations == 0:
                return {'throughput': 0, 'efficiency': 0, 'utilization': 0}
            
            # Calculate throughput (vectorizations per hour)
            throughput = total_vectorizations / (total_processing_time / 3600) if total_processing_time > 0 else 0
            
            # Calculate efficiency (quality score per processing time)
            avg_quality = analytics.get('avg_quality_score', 0)
            avg_processing_time = analytics.get('avg_processing_time', 0)
            efficiency = avg_quality / avg_processing_time if avg_processing_time > 0 else 0
            
            # Calculate utilization (actual vs optimal processing time)
            optimal_time = 30  # seconds
            utilization = optimal_time / avg_processing_time if avg_processing_time > 0 else 0
            
            return {
                'throughput': throughput,
                'efficiency': efficiency,
                'utilization': min(utilization, 1.0)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
            return {'throughput': 0, 'efficiency': 0, 'utilization': 0}
    
    def _analyze_quality_improvements(self, quality_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze quality data and suggest improvements"""
        improvements = []
        
        try:
            avg_quality = quality_data.get('avg_quality', 0)
            strategy_quality = quality_data.get('strategy_quality', {})
            
            # Find best performing strategy
            if strategy_quality:
                best_strategy = max(strategy_quality.items(), key=lambda x: x[1])
                if best_strategy[1] > avg_quality + 0.1:
                    improvements.append({
                        'type': 'strategy_optimization',
                        'suggestion': f'Consider using {best_strategy[0]} more frequently',
                        'potential_improvement': f'+{(best_strategy[1] - avg_quality):.1%} quality',
                        'confidence': 'high'
                    })
            
            # Check for low quality patterns
            if avg_quality < 0.7:
                improvements.append({
                    'type': 'parameter_tuning',
                    'suggestion': 'Review and optimize vectorization parameters',
                    'potential_improvement': 'Up to +15% quality improvement',
                    'confidence': 'medium'
                })
            
            return improvements
            
        except Exception as e:
            self.logger.error(f"Error analyzing quality improvements: {e}")
            return []
    
    def _get_storage_optimization_suggestions(self, storage_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get storage optimization suggestions"""
        suggestions = []
        
        try:
            total_size = storage_data.get('total_size', 0)
            large_files = storage_data.get('large_files', [])
            
            # Check for large files
            if len(large_files) > 0:
                suggestions.append({
                    'type': 'compression',
                    'suggestion': f'Consider compressing {len(large_files)} large files',
                    'potential_savings': f'{sum(f.get("size", 0) for f in large_files) * 0.3 / 1024/1024:.1f}MB',
                    'impact': 'Storage cost reduction'
                })
            
            # Check for old files
            if total_size > 5 * 1024 * 1024 * 1024:  # 5GB
                suggestions.append({
                    'type': 'cleanup',
                    'suggestion': 'Implement automated cleanup for old files',
                    'potential_savings': f'{total_size * 0.2 / 1024/1024/1024:.1f}GB',
                    'impact': 'Storage optimization'
                })
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error getting storage optimization suggestions: {e}")
            return []
    
    def _get_active_vectorizations_count(self) -> int:
        """Get count of currently active vectorizations"""
        try:
            return self.analytics_data['real_time_metrics']['active_vectorizations']
        except:
            return 0
    
    def _get_queue_size(self) -> int:
        """Get current queue size"""
        try:
            return self.analytics_data['real_time_metrics']['queue_size']
        except:
            return 0
    
    def _get_system_load(self) -> float:
        """Get system load average"""
        try:
            import psutil
            return psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0.0
        except:
            return 0.0
    
    def _get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return {
                'total': memory.total,
                'available': memory.available,
                'percent': memory.percent,
                'used': memory.used
            }
        except:
            return {'total': 0, 'available': 0, 'percent': 0, 'used': 0}
    
    def _get_disk_usage(self) -> Dict[str, Any]:
        """Get disk usage statistics"""
        try:
            import psutil
            disk = psutil.disk_usage('.')
            return {
                'total': disk.total,
                'free': disk.free,
                'used': disk.used,
                'percent': (disk.used / disk.total) * 100
            }
        except:
            return {'total': 0, 'free': 0, 'used': 0, 'percent': 0}
    
    def _get_directory_size(self, directory: str) -> int:
        """Get size of directory in bytes"""
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(file_path)
                    except OSError:
                        pass
            return total_size
        except:
            return 0
    
    def _get_default_analytics(self) -> Dict[str, Any]:
        """Get default analytics structure"""
        return {
            'summary': {
                'total_vectorizations': 0,
                'total_processing_time': 0,
                'avg_processing_time': 0,
                'avg_quality_score': 0,
                'success_rate': 0,
                'total_file_size': 0
            },
            'daily_breakdown': [],
            'strategy_performance': {},
            'file_size_distribution': {},
            'quality_trends': [],
            'error_analysis': {},
            'performance_metrics': {'throughput': 0, 'efficiency': 0, 'utilization': 0}
        }
    
    def _get_default_real_time_metrics(self) -> Dict[str, Any]:
        """Get default real-time metrics"""
        return {
            'active_vectorizations': 0,
            'queue_size': 0,
            'recent_completions': 0,
            'recent_errors': 0,
            'avg_processing_time': 0,
            'success_rate': 0,
            'throughput_per_hour': 0,
            'system_load': 0.0,
            'memory_usage': {'total': 0, 'available': 0, 'percent': 0, 'used': 0},
            'disk_usage': {'total': 0, 'free': 0, 'used': 0, 'percent': 0}
        }
    
    def _get_default_quality_metrics(self) -> Dict[str, Any]:
        """Get default quality metrics"""
        return {
            'average_quality': 0,
            'quality_distribution': {},
            'quality_trends': [],
            'strategy_quality': {},
            'improvement_opportunities': [],
            'quality_benchmarks': {
                'excellent': {'min': 0.9, 'count': 0},
                'good': {'min': 0.7, 'count': 0},
                'fair': {'min': 0.5, 'count': 0},
                'poor': {'min': 0.0, 'count': 0}
            }
        }
    
    def _get_default_storage_analytics(self) -> Dict[str, Any]:
        """Get default storage analytics"""
        return {
            'total_files': 0,
            'total_size': 0,
            'avg_file_size': 0,
            'file_type_distribution': {},
            'storage_growth': [],
            'large_files': [],
            'optimization_suggestions': [],
            'disk_usage': {
                'uploads': 0,
                'results': 0,
                'temp': 0
            }
        }


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