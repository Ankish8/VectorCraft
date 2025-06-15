import numpy as np
import cv2
from typing import List, Tuple, Optional, Dict
import math
import logging

from ..core.svg_builder import SVGBuilder

class ExperimentalVTracerV2Strategy:
    """Experimental VTracer V2 - Hybrid approach using real VTracer + enhancements"""
    
    def __init__(self):
        # Base VTracer parameters  
        self.corner_threshold = 30
        self.filter_speckle = 4
        self.segment_length = 10.0
        
        # Experimental features
        self.text_detection_enabled = False  # Disable for performance
        self.enhanced_edge_detection = True
        self.adaptive_parameters = True
        self.post_process_optimization = True
        
        # Version tracking
        self.version = "v2.0.0-experimental-hybrid"
        
    def vectorize(self, image: np.ndarray, quantized_image: np.ndarray, edge_map: np.ndarray) -> SVGBuilder:
        """Hybrid vectorization: Real VTracer + experimental enhancements"""
        
        h, w = image.shape[:2]
        
        # Try to use real VTracer first with optimized parameters
        svg_builder = self._use_real_vtracer_with_enhancements(image)
        
        if svg_builder is None:
            # Fallback to custom implementation
            svg_builder = self._custom_vectorize_fallback(image, quantized_image, edge_map)
        
        return svg_builder
    
    def _use_real_vtracer_with_enhancements(self, image: np.ndarray) -> Optional[SVGBuilder]:
        """Use real VTracer with experimental parameter optimization"""
        try:
            # Import real VTracer strategy
            from ..strategies.real_vtracer import RealVTracerStrategy
            
            # Create VTracer instance with experimental optimizations
            vtracer = RealVTracerStrategy()
            
            # Check if available
            if not vtracer.available:
                return None
            
            # Experimental parameter optimization based on image analysis
            optimized_params = self._analyze_and_optimize_parameters(image)
            vtracer.set_custom_parameters(optimized_params)
            
            # Use VTracer
            result = vtracer.vectorize(image, None, None)
            
            # Post-process the result with experimental enhancements
            if self.post_process_optimization:
                result = self._post_process_vtracer_result(result, image)
            
            return result
            
        except Exception as e:
            logging.warning(f"Real VTracer with enhancements failed: {e}")
            return None
    
    def _analyze_and_optimize_parameters(self, image: np.ndarray) -> Dict:
        """Analyze image and optimize VTracer parameters"""
        h, w = image.shape[:2]
        
        # Convert to grayscale for analysis
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
        
        # Image analysis
        brightness = np.mean(gray)
        contrast = np.std(gray)
        
        # Edge density analysis
        edges = cv2.Canny(gray.astype(np.uint8), 50, 150)
        edge_density = np.sum(edges > 0) / (h * w)
        
        # Color analysis
        if len(image.shape) == 3:
            unique_colors = len(np.unique(image.reshape(-1, image.shape[2]), axis=0))
        else:
            unique_colors = len(np.unique(gray))
        
        # Optimize parameters based on analysis
        params = {
            'filter_speckle': 4,
            'color_precision': 8,
            'layer_difference': 8,
            'corner_threshold': 90,
            'length_threshold': 1.0,
            'splice_threshold': 20,
            'curve_fitting': 'spline'
        }
        
        # Adaptive parameter tuning
        if unique_colors > 20:
            # High color complexity
            params['color_precision'] = 12
            params['layer_difference'] = 12
        elif unique_colors < 5:
            # Low color complexity
            params['color_precision'] = 6
            params['layer_difference'] = 6
        
        if edge_density > 0.1:
            # High edge density - likely detailed image
            params['corner_threshold'] = 60  # More sensitive
            params['length_threshold'] = 0.8
            params['filter_speckle'] = 6
        elif edge_density < 0.02:
            # Low edge density - likely simple image
            params['corner_threshold'] = 120  # Less sensitive
            params['length_threshold'] = 1.5
            params['filter_speckle'] = 2
        
        if contrast < 30:
            # Low contrast image
            params['splice_threshold'] = 15
        elif contrast > 80:
            # High contrast image
            params['splice_threshold'] = 25
        
        # Image size adaptations
        total_pixels = h * w
        if total_pixels > 500000:  # Large image
            params['filter_speckle'] = max(6, params['filter_speckle'])
        elif total_pixels < 50000:  # Small image
            params['filter_speckle'] = min(2, params['filter_speckle'])
        
        logging.info(f"🧪 Experimental parameter optimization: {params}")
        return params
    
    def _post_process_vtracer_result(self, svg_builder: SVGBuilder, image: np.ndarray) -> SVGBuilder:
        """Post-process VTracer result with experimental enhancements"""
        
        if not hasattr(svg_builder, 'elements') or not svg_builder.elements:
            return svg_builder
        
        enhanced_elements = []
        
        for element in svg_builder.elements:
            # Optimize individual elements
            if hasattr(element, 'points') and len(element.points) > 4:
                # Apply experimental path optimization
                optimized_points = self._optimize_path_points(element.points)
                element.points = optimized_points
            
            enhanced_elements.append(element)
        
        svg_builder.elements = enhanced_elements
        return svg_builder
    
    def _optimize_path_points(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Optimize path points using experimental algorithms"""
        if len(points) < 4:
            return points
        
        # Apply smart Douglas-Peucker with adaptive epsilon
        path_length = self._calculate_path_length(points)
        adaptive_epsilon = max(0.5, path_length * 0.003)  # 0.3% of path length
        
        optimized = self._douglas_peucker_adaptive(points, adaptive_epsilon)
        
        # Ensure we don't over-simplify
        if len(optimized) < len(points) * 0.3:  # Keep at least 30% of points
            return points
        
        return optimized
    
    def _calculate_path_length(self, points: List[Tuple[float, float]]) -> float:
        """Calculate total path length"""
        total_length = 0
        for i in range(len(points) - 1):
            dx = points[i + 1][0] - points[i][0]
            dy = points[i + 1][1] - points[i][1]
            total_length += math.sqrt(dx * dx + dy * dy)
        return total_length
    
    def _douglas_peucker_adaptive(self, points: List[Tuple[float, float]], epsilon: float) -> List[Tuple[float, float]]:
        """Adaptive Douglas-Peucker algorithm"""
        if len(points) <= 2:
            return points
        
        # Find point with maximum distance from line
        dmax = 0
        index = 0
        
        for i in range(1, len(points) - 1):
            d = self._perpendicular_distance(points[i], points[0], points[-1])
            if d > dmax:
                index = i
                dmax = d
        
        # If max distance is greater than epsilon, recursively simplify
        if dmax > epsilon:
            # Recursive calls
            rec_results1 = self._douglas_peucker_adaptive(points[:index + 1], epsilon)
            rec_results2 = self._douglas_peucker_adaptive(points[index:], epsilon)
            
            # Build result
            return rec_results1[:-1] + rec_results2
        else:
            return [points[0], points[-1]]
    
    def _perpendicular_distance(self, point: Tuple[float, float], 
                               line_start: Tuple[float, float], 
                               line_end: Tuple[float, float]) -> float:
        """Calculate perpendicular distance from point to line"""
        x0, y0 = point
        x1, y1 = line_start
        x2, y2 = line_end
        
        num = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
        den = math.sqrt((y2 - y1)**2 + (x2 - x1)**2)
        
        return num / (den + 1e-8)
    
    def _custom_vectorize_fallback(self, image: np.ndarray, quantized_image: np.ndarray, edge_map: np.ndarray) -> SVGBuilder:
        """Fallback custom vectorization if VTracer unavailable"""
        
        h, w = image.shape[:2]
        svg_builder = SVGBuilder(w, h)
        
        # Simple contour-based vectorization
        if len(quantized_image.shape) == 3 and quantized_image.shape[2] >= 3:
            unique_colors = np.unique(quantized_image.reshape(-1, quantized_image.shape[-1]), axis=0)
        else:
            unique_colors = np.unique(quantized_image.reshape(-1))
            unique_colors = unique_colors.reshape(-1, 1)
        
        for color in unique_colors:
            # Create mask for this color
            if len(quantized_image.shape) == 3 and quantized_image.shape[2] >= 3:
                mask = np.all(quantized_image == color, axis=-1).astype(np.uint8) * 255
                color_tuple = tuple(color[:3])
            else:
                mask = (quantized_image == color).astype(np.uint8) * 255
                color_tuple = (int(color[0]), int(color[0]), int(color[0])) if hasattr(color, '__len__') else (int(color), int(color), int(color))
            
            # Find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                if cv2.contourArea(contour) > self.filter_speckle:
                    # Convert contour to path points
                    path_points = [(float(point[0][0]), float(point[0][1])) for point in contour]
                    
                    if len(path_points) >= 3:
                        # Simple optimization
                        if len(path_points) > 8:
                            path_points = self._optimize_path_points(path_points)
                        
                        svg_builder.add_path(path_points, color_tuple, fill=True)
        
        return svg_builder