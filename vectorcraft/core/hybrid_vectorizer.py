import numpy as np
import cv2
import time
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

from ..utils.image_processor import ImageProcessor, ImageMetadata
from ..strategies.classical_tracer import ClassicalTracer
from ..strategies.diff_optimizer import DifferentiableOptimizer
from ..primitives.detector import PrimitiveDetector
from .svg_builder import SVGBuilder

@dataclass
class VectorizationResult:
    svg_builder: SVGBuilder
    processing_time: float
    strategy_used: str
    quality_score: float
    metadata: Dict[str, Any]

class HybridVectorizer:
    def __init__(self):
        self.image_processor = ImageProcessor()
        self.classical_tracer = ClassicalTracer()
        self.diff_optimizer = DifferentiableOptimizer()
        self.primitive_detector = PrimitiveDetector()
        
        # Strategy weights based on content type
        self.strategy_weights = {
            'text': {'classical': 0.7, 'primitive': 0.2, 'diff': 0.1},
            'geometric': {'classical': 0.3, 'primitive': 0.6, 'diff': 0.1},
            'gradient': {'classical': 0.2, 'primitive': 0.1, 'diff': 0.7},
            'mixed': {'classical': 0.4, 'primitive': 0.3, 'diff': 0.3}
        }
    
    def vectorize(self, image_path: str, target_time: float = 120.0) -> VectorizationResult:
        """Main vectorization pipeline"""
        start_time = time.time()
        
        # Load and analyze image
        image = self.image_processor.load_image(image_path)
        metadata = self.image_processor.analyze_content(image)
        
        # Preprocessing
        processed_image = self.image_processor.preprocess(image)
        edge_map = self.image_processor.create_edge_map(processed_image)
        quantized_image = self.image_processor.segment_colors(processed_image, n_colors=8)
        
        # Determine content type and strategy
        content_type = self._classify_content(metadata)
        strategy = self._select_strategy(content_type, metadata, target_time)
        
        # Execute vectorization strategy
        if strategy == 'hybrid_fast':
            result = self._hybrid_fast_strategy(processed_image, edge_map, quantized_image, metadata)
        elif strategy == 'primitive_focused':
            result = self._primitive_focused_strategy(processed_image, edge_map, quantized_image, metadata)
        elif strategy == 'classical_refined':
            result = self._classical_refined_strategy(processed_image, edge_map, quantized_image, metadata)
        elif strategy == 'diff_optimized':
            result = self._diff_optimized_strategy(processed_image, edge_map, quantized_image, metadata)
        else:
            # Default to hybrid approach
            result = self._hybrid_comprehensive_strategy(processed_image, edge_map, quantized_image, metadata, target_time)
        
        processing_time = time.time() - start_time
        
        # Calculate quality score
        quality_score = self._estimate_quality(result, processed_image)
        
        return VectorizationResult(
            svg_builder=result,
            processing_time=processing_time,
            strategy_used=strategy,
            quality_score=quality_score,
            metadata={
                'content_type': content_type,
                'image_metadata': metadata,
                'num_elements': len(result.elements)
            }
        )
    
    def _classify_content(self, metadata: ImageMetadata) -> str:
        """Classify image content type"""
        scores = {
            'text': metadata.text_probability,
            'geometric': metadata.geometric_probability,
            'gradient': metadata.gradient_probability
        }
        
        max_score = max(scores.values())
        
        if max_score < 0.3:
            return 'mixed'
        
        return max(scores, key=scores.get)
    
    def _select_strategy(self, content_type: str, metadata: ImageMetadata, target_time: float) -> str:
        """Select optimal strategy based on content and time constraints"""
        
        if target_time < 30:  # Very fast processing needed
            return 'hybrid_fast'
        elif content_type == 'geometric' and metadata.geometric_probability > 0.7:
            return 'primitive_focused'
        elif content_type == 'text' and metadata.text_probability > 0.6:
            return 'classical_refined'
        elif content_type == 'gradient' and metadata.gradient_probability > 0.5:
            return 'diff_optimized'
        else:
            return 'hybrid_comprehensive'
    
    def _hybrid_fast_strategy(self, image: np.ndarray, edge_map: np.ndarray, 
                             quantized_image: np.ndarray, metadata: ImageMetadata) -> SVGBuilder:
        """Fast hybrid approach - prioritize speed"""
        
        # Quick classical tracing with reduced precision
        self.classical_tracer.approx_epsilon = 0.05  # Less precise but faster
        svg_builder = self.classical_tracer.trace_with_colors(image, quantized_image)
        
        # Quick primitive detection for obvious shapes
        primitives = self.primitive_detector.detect_all_primitives(image, edge_map)
        filtered_primitives = self.primitive_detector.filter_overlapping_primitives(primitives, 0.7)
        
        # Add high-confidence primitives
        for circle in filtered_primitives['circles']:
            if circle.confidence > 0.8:
                color = self._sample_color_at_point(quantized_image, circle.center)
                svg_builder.add_circle(circle.center, circle.radius, color)
        
        for rect in filtered_primitives['rectangles']:
            if rect.confidence > 0.8:
                color = self._sample_color_at_point(quantized_image, (rect.x + rect.width/2, rect.y + rect.height/2))
                svg_builder.add_rectangle(rect.x, rect.y, rect.width, rect.height, color)
        
        return svg_builder
    
    def _primitive_focused_strategy(self, image: np.ndarray, edge_map: np.ndarray,
                                   quantized_image: np.ndarray, metadata: ImageMetadata) -> SVGBuilder:
        """Focus on detecting and using geometric primitives"""
        
        h, w = image.shape[:2]
        svg_builder = SVGBuilder(w, h)
        
        # Comprehensive primitive detection
        primitives = self.primitive_detector.detect_all_primitives(image, edge_map)
        filtered_primitives = self.primitive_detector.filter_overlapping_primitives(primitives, 0.3)
        
        # Add all high-quality primitives first
        for circle in filtered_primitives['circles']:
            if circle.confidence > 0.5:
                color = self._sample_color_at_point(quantized_image, circle.center)
                svg_builder.add_circle(circle.center, circle.radius, color)
        
        for rect in filtered_primitives['rectangles']:
            if rect.confidence > 0.5:
                color = self._sample_color_at_point(quantized_image, (rect.x + rect.width/2, rect.y + rect.height/2))
                svg_builder.add_rectangle(rect.x, rect.y, rect.width, rect.height, color)
        
        # Fill remaining areas with classical tracing
        # Create mask of areas not covered by primitives
        covered_mask = self._create_primitive_mask(filtered_primitives, w, h)
        uncovered_edge_map = edge_map * (1 - covered_mask)
        
        # Trace uncovered areas
        remaining_paths = self.classical_tracer.trace(image, uncovered_edge_map)
        for path in remaining_paths:
            if len(path) > 3:
                center_point = self._get_path_center(path)
                color = self._sample_color_at_point(quantized_image, center_point)
                svg_builder.add_path(path, color)
        
        return svg_builder
    
    def _classical_refined_strategy(self, image: np.ndarray, edge_map: np.ndarray,
                                   quantized_image: np.ndarray, metadata: ImageMetadata) -> SVGBuilder:
        """Classical tracing with refinement - good for text and clean graphics"""
        
        # Use higher precision for classical tracing
        self.classical_tracer.approx_epsilon = 0.005
        svg_builder = self.classical_tracer.trace_with_colors(image, quantized_image)
        
        # Post-process paths for better quality
        refined_elements = []
        for element in svg_builder.elements:
            if hasattr(element, 'points'):
                # Smooth and simplify paths
                smoothed_points = self.classical_tracer.smooth_path(element.points)
                simplified_points = self.classical_tracer.douglas_peucker(smoothed_points, 2.0)
                element.points = simplified_points
            refined_elements.append(element)
        
        svg_builder.elements = refined_elements
        return svg_builder
    
    def _diff_optimized_strategy(self, image: np.ndarray, edge_map: np.ndarray,
                                quantized_image: np.ndarray, metadata: ImageMetadata) -> SVGBuilder:
        """Differentiable optimization - good for gradients and complex shapes"""
        
        # Start with classical tracing as initialization
        initial_svg = self.classical_tracer.trace_with_colors(image, quantized_image)
        
        # Extract paths and colors for optimization
        initial_paths = []
        colors = []
        for element in initial_svg.elements:
            if hasattr(element, 'points') and len(element.points) >= 2:
                initial_paths.append(element.points)
                colors.append(element.color)
        
        if initial_paths:
            # Optimize paths using differentiable optimization
            try:
                optimized_paths = self.diff_optimizer.optimize_paths(image, initial_paths, colors)
                
                # Rebuild SVG with optimized paths
                h, w = image.shape[:2]
                svg_builder = SVGBuilder(w, h)
                for path, color in zip(optimized_paths, colors):
                    svg_builder.add_path(path, color)
                
                return svg_builder
            except Exception as e:
                # Fall back to classical if optimization fails
                print(f"Optimization failed: {e}")
                return initial_svg
        
        return initial_svg
    
    def _hybrid_comprehensive_strategy(self, image: np.ndarray, edge_map: np.ndarray,
                                     quantized_image: np.ndarray, metadata: ImageMetadata,
                                     target_time: float) -> SVGBuilder:
        """Comprehensive hybrid approach using all strategies"""
        
        h, w = image.shape[:2]
        svg_builder = SVGBuilder(w, h)
        
        time_per_strategy = target_time / 3  # Rough time allocation
        
        # Strategy 1: Primitive detection (fast)
        start_time = time.time()
        primitives = self.primitive_detector.detect_all_primitives(image, edge_map)
        filtered_primitives = self.primitive_detector.filter_overlapping_primitives(primitives)
        
        # Add primitives
        for circle in filtered_primitives['circles']:
            if circle.confidence > 0.6:
                color = self._sample_color_at_point(quantized_image, circle.center)
                svg_builder.add_circle(circle.center, circle.radius, color)
        
        for rect in filtered_primitives['rectangles']:
            if rect.confidence > 0.6:
                color = self._sample_color_at_point(quantized_image, (rect.x + rect.width/2, rect.y + rect.height/2))
                svg_builder.add_rectangle(rect.x, rect.y, rect.width, rect.height, color)
        
        # Strategy 2: Classical tracing for remaining areas
        covered_mask = self._create_primitive_mask(filtered_primitives, w, h)
        uncovered_edge_map = edge_map * (1 - covered_mask)
        
        classical_svg = self.classical_tracer.trace_with_colors(image, quantized_image)
        
        # Add non-overlapping classical paths
        for element in classical_svg.elements:
            if hasattr(element, 'points'):
                if not self._overlaps_with_primitives(element.points, filtered_primitives):
                    svg_builder.add_path(element.points, element.color, element.fill, element.stroke_width)
        
        # Strategy 3: Selective optimization (if time allows)
        if time.time() - start_time < target_time * 0.8:
            # Find paths that could benefit from optimization (gradients, complex curves)
            candidates_for_optimization = self._identify_optimization_candidates(svg_builder.elements, image)
            
            for element in candidates_for_optimization[:3]:  # Limit to prevent timeout
                if hasattr(element, 'points'):
                    try:
                        region = self._extract_path_region(image, element.points)
                        optimized_points = self.diff_optimizer.refine_single_path(
                            element.points, region, element.color
                        )
                        element.points = optimized_points
                    except:
                        continue  # Skip optimization if it fails
        
        return svg_builder
    
    def _sample_color_at_point(self, image: np.ndarray, point: Tuple[float, float]) -> Tuple[float, float, float]:
        """Sample color from image at given point"""
        x, y = int(point[0]), int(point[1])
        h, w = image.shape[:2]
        
        x = max(0, min(w-1, x))
        y = max(0, min(h-1, y))
        
        if len(image.shape) == 3:
            return tuple(image[y, x, :3])
        else:
            gray_val = image[y, x]
            return (gray_val, gray_val, gray_val)
    
    def _create_primitive_mask(self, primitives: Dict, width: int, height: int) -> np.ndarray:
        """Create mask showing areas covered by primitives"""
        mask = np.zeros((height, width), dtype=np.float32)
        
        for circle in primitives['circles']:
            cv2.circle(mask, (int(circle.center[0]), int(circle.center[1])), 
                      int(circle.radius), 1.0, -1)
        
        for rect in primitives['rectangles']:
            cv2.rectangle(mask, 
                         (int(rect.x), int(rect.y)),
                         (int(rect.x + rect.width), int(rect.y + rect.height)),
                         1.0, -1)
        
        return mask
    
    def _get_path_center(self, path: List[Tuple[float, float]]) -> Tuple[float, float]:
        """Get center point of path"""
        if not path:
            return (0, 0)
        
        x_coords = [p[0] for p in path]
        y_coords = [p[1] for p in path]
        
        return (sum(x_coords) / len(x_coords), sum(y_coords) / len(y_coords))
    
    def _overlaps_with_primitives(self, path_points: List[Tuple[float, float]], 
                                 primitives: Dict) -> bool:
        """Check if path overlaps significantly with detected primitives"""
        # Simple overlap check - could be more sophisticated
        path_center = self._get_path_center(path_points)
        
        for circle in primitives['circles']:
            dist = np.sqrt((path_center[0] - circle.center[0])**2 + 
                          (path_center[1] - circle.center[1])**2)
            if dist < circle.radius * 0.8:
                return True
        
        for rect in primitives['rectangles']:
            if (rect.x <= path_center[0] <= rect.x + rect.width and
                rect.y <= path_center[1] <= rect.y + rect.height):
                return True
        
        return False
    
    def _identify_optimization_candidates(self, elements: List, image: np.ndarray) -> List:
        """Identify elements that would benefit from differentiable optimization"""
        candidates = []
        
        for element in elements:
            if hasattr(element, 'points') and len(element.points) > 4:
                # Complex paths are good candidates
                candidates.append(element)
        
        # Sort by complexity (more complex = higher priority for optimization)
        candidates.sort(key=lambda e: len(e.points) if hasattr(e, 'points') else 0, reverse=True)
        
        return candidates
    
    def _extract_path_region(self, image: np.ndarray, path_points: List[Tuple[float, float]]) -> np.ndarray:
        """Extract image region around path for targeted optimization"""
        if not path_points:
            return image
        
        # Get bounding box
        x_coords = [p[0] for p in path_points]
        y_coords = [p[1] for p in path_points]
        
        min_x, max_x = int(min(x_coords)), int(max(x_coords))
        min_y, max_y = int(min(y_coords)), int(max(y_coords))
        
        # Add padding
        padding = 10
        min_x = max(0, min_x - padding)
        min_y = max(0, min_y - padding)
        max_x = min(image.shape[1], max_x + padding)
        max_y = min(image.shape[0], max_y + padding)
        
        return image[min_y:max_y, min_x:max_x]
    
    def _estimate_quality(self, svg_builder: SVGBuilder, original_image: np.ndarray) -> float:
        """Estimate quality of vectorization result"""
        # Simple quality metric based on number of elements and complexity
        num_elements = len(svg_builder.elements)
        
        # Prefer fewer, more meaningful elements
        if num_elements == 0:
            return 0.0
        elif num_elements < 5:
            return 0.9
        elif num_elements < 20:
            return 0.8
        elif num_elements < 50:
            return 0.7
        else:
            return 0.6  # Too many elements might indicate over-segmentation