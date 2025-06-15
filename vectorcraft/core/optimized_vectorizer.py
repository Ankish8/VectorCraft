import numpy as np
import cv2
import time
import os
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

from .hybrid_vectorizer import HybridVectorizer, VectorizationResult
from ..utils.performance import (
    PerformanceProfiler, OptimizedImageProcessor, AdaptiveOptimizer,
    CacheManager, ParallelProcessor, GPUAccelerator
)

class OptimizedVectorizer(HybridVectorizer):
    """High-performance optimized version of the hybrid vectorizer"""
    
    def __init__(self, target_time: float = 120.0, enable_gpu: bool = True, enable_caching: bool = True):
        super().__init__()
        
        self.profiler = PerformanceProfiler()
        self.adaptive_optimizer = AdaptiveOptimizer(target_time)
        self.cache_manager = CacheManager() if enable_caching else None
        self.gpu_accelerator = GPUAccelerator() if enable_gpu else None
        self.parallel_processor = ParallelProcessor()
        
        # Performance settings
        self.target_time = target_time
        self.enable_parallel = True
        self.enable_hierarchical = True
        
        # Wrap key methods with profiling
        self._wrap_methods_with_profiling()
    
    def _wrap_methods_with_profiling(self):
        """Add profiling to key methods"""
        self.image_processor.analyze_content = self.profiler.profile("analyze_content")(
            self.image_processor.analyze_content
        )
        self.classical_tracer.trace_with_colors = self.profiler.profile("classical_trace")(
            self.classical_tracer.trace_with_colors
        )
        self.primitive_detector.detect_all_primitives = self.profiler.profile("primitive_detect")(
            self.primitive_detector.detect_all_primitives
        )
    
    @PerformanceProfiler().profile("optimized_vectorize")
    def vectorize(self, image_path: str, target_time: float = None) -> VectorizationResult:
        """Optimized vectorization with adaptive performance tuning"""
        start_time = time.time()
        target_time = target_time or self.target_time
        
        # Load and preprocess with caching
        image = self._cached_load_image(image_path)
        
        # Adaptive preprocessing based on image size and target time
        processed_image, metadata = self._adaptive_preprocessing(image, target_time)
        
        # Smart strategy selection
        elapsed = time.time() - start_time
        strategy = self.adaptive_optimizer.optimize_strategy_selection(metadata, elapsed)
        
        # Execute with performance monitoring
        result = self._execute_optimized_strategy(
            strategy, processed_image, metadata, target_time, start_time
        )
        
        processing_time = time.time() - start_time
        quality_score = self._estimate_quality(result, processed_image)
        
        # Print performance stats if requested
        if processing_time > target_time * 0.8:  # If we're close to time limit
            print(f"Warning: Processing took {processing_time:.2f}s (target: {target_time:.2f}s)")
            self.profiler.print_stats()
        
        # Handle both SVGBuilder and RawSVGResult
        if hasattr(result, 'element_count'):
            # RawSVGResult
            num_elements = result.element_count
        else:
            # SVGBuilder
            num_elements = len(result.elements)
        
        return VectorizationResult(
            svg_builder=result,
            processing_time=processing_time,
            strategy_used=strategy,
            quality_score=quality_score,
            metadata={
                'content_type': self._classify_content(metadata),
                'image_metadata': metadata,
                'num_elements': num_elements,
                'performance_stats': self.profiler.get_stats()
            }
        )
    
    def _cached_load_image(self, image_path: str) -> np.ndarray:
        """Load image with caching"""
        if self.cache_manager:
            cache_key = f"load_{image_path}_{os.path.getmtime(image_path)}"
            cached_result = self.cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            image = self.image_processor.load_image(image_path)
            self.cache_manager.put(cache_key, image)
            return image
        else:
            return self.image_processor.load_image(image_path)
    
    def _adaptive_preprocessing(self, image: np.ndarray, target_time: float) -> Tuple[np.ndarray, Any]:
        """Adaptive preprocessing based on target time and image characteristics"""
        
        # Quick size check for preprocessing strategy
        h, w = image.shape[:2]
        total_pixels = h * w
        
        # Adaptive downsampling for very large images or tight time constraints
        if target_time < 30 or total_pixels > 1000000:  # 1MP threshold
            # Aggressive downsampling
            max_dimension = 512
            if max(h, w) > max_dimension:
                scale = max_dimension / max(h, w)
                new_h, new_w = int(h * scale), int(w * scale)
                image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        elif target_time < 60 or total_pixels > 500000:
            # Moderate downsampling
            max_dimension = 800
            if max(h, w) > max_dimension:
                scale = max_dimension / max(h, w)
                new_h, new_w = int(h * scale), int(w * scale)
                image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        # Preprocess image
        processed_image = self.image_processor.preprocess(image)
        
        # Parallel content analysis and edge detection
        if self.enable_parallel:
            import threading
            
            metadata_result = [None]
            edge_results = {}
            
            def analyze_content():
                metadata_result[0] = self.image_processor.analyze_content(processed_image)
            
            def detect_edges():
                edge_results.update(
                    OptimizedImageProcessor.parallel_edge_detection(processed_image)
                )
            
            # Run in parallel
            threads = [
                threading.Thread(target=analyze_content),
                threading.Thread(target=detect_edges)
            ]
            
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            
            metadata = metadata_result[0]
            # Store edge results for later use
            self._edge_cache = edge_results
        else:
            metadata = self.image_processor.analyze_content(processed_image)
        
        return processed_image, metadata
    
    def _execute_optimized_strategy(self, strategy: str, image: np.ndarray, 
                                   metadata: Any, target_time: float, start_time: float) -> Any:
        """Execute strategy with performance optimizations"""
        
        elapsed = time.time() - start_time
        remaining_time = target_time - elapsed
        
        # Get adaptive parameters
        params = self.adaptive_optimizer.adaptive_precision_control(strategy, remaining_time)
        
        # Update algorithm parameters
        self.classical_tracer.approx_epsilon = params['approx_epsilon']
        self.classical_tracer.contour_threshold = params['contour_min_area']
        
        # Get or compute edge map with caching
        edge_map = self._get_cached_edge_map(image, params)
        
        # Fast color quantization
        n_colors = int(params['color_quantization'])
        quantized_image = OptimizedImageProcessor.fast_color_quantization(image, n_colors)
        
        # Execute strategy with optimizations
        if strategy == 'vtracer_high_fidelity':
            print("🎯 OptimizedVectorizer calling _vtracer_high_fidelity_strategy")
            return self._vtracer_high_fidelity_strategy(image, edge_map, quantized_image, metadata)
        elif strategy == 'experimental':
            print("🧪 OptimizedVectorizer calling _experimental_strategy_v2")
            return self._experimental_strategy_v2(image, edge_map, quantized_image, metadata)
        else:
            # Default to VTracer for any unknown strategy
            print("🎯 Defaulting to VTracer for unknown strategy:", strategy)
            return self._vtracer_high_fidelity_strategy(image, edge_map, quantized_image, metadata)
    
    def _get_cached_edge_map(self, image: np.ndarray, params: Dict) -> np.ndarray:
        """Get edge map with caching"""
        if self.cache_manager:
            cache_key = self.cache_manager.get_cache_key(image, "edge_detection", params)
            cached_edges = self.cache_manager.get(cache_key)
            if cached_edges is not None:
                return cached_edges
        
        # Check if we have parallel edge detection results
        if hasattr(self, '_edge_cache') and 'enhanced' in self._edge_cache:
            edge_map = self._edge_cache['enhanced']
        else:
            edge_map = self.image_processor.create_edge_map(image, method='enhanced')
        
        if self.cache_manager:
            self.cache_manager.put(cache_key, edge_map)
        
        return edge_map
    
    def _experimental_strategy_v2(self, image: np.ndarray, edge_map: np.ndarray,
                              quantized_image: np.ndarray, metadata: Any) -> Any:
        """Experimental strategy V3 focusing on actual VTracer limitations"""
        from ..strategies.experimental_vtracer_v3 import ExperimentalVTracerV3Strategy
        
        experimental_tracer = ExperimentalVTracerV3Strategy()
        return experimental_tracer.vectorize(image, quantized_image, edge_map)
    
