import numpy as np
import cv2
from typing import List, Tuple, Optional, Dict
from scipy.spatial.distance import pdist, squareform
from sklearn.cluster import DBSCAN
import math
import logging

# Text detection imports
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

from ..core.svg_builder import SVGBuilder

class ExperimentalVTracerStrategy:
    """Experimental VTracer strategy with advanced text detection and Vector Magic features"""
    
    def __init__(self):
        # Base VTracer parameters
        self.corner_threshold = 30  # degrees
        self.filter_speckle = 4     # minimum area in pixels  
        self.segment_length = 10.0  # smoothing parameter
        
        # Experimental features (optimized for performance)
        self.text_detection_enabled = False  # Disable for performance
        self.color_layer_separation = True
        self.adaptive_thresholding = True
        self.gradient_aware = True
        self.noise_reduction_enabled = True
        self.fast_mode = True  # Enable fast mode for testing
        
        # Text detection setup
        self.ocr_reader = None
        if EASYOCR_AVAILABLE:
            try:
                self.ocr_reader = easyocr.Reader(['en'])
                logging.info("EasyOCR initialized successfully")
            except Exception as e:
                logging.warning(f"EasyOCR initialization failed: {e}")
        
        # Version tracking
        self.version = "v1.0.0-experimental"
        
    def vectorize(self, image: np.ndarray, quantized_image: np.ndarray, edge_map: np.ndarray) -> SVGBuilder:
        """Enhanced vectorization with experimental features"""
        
        h, w = image.shape[:2]
        svg_builder = SVGBuilder(w, h)
        
        if self.fast_mode:
            # Fast mode - minimal processing for performance testing
            processed_image = image  # Skip expensive preprocessing
            enhanced_quantized = quantized_image  # Skip quantization enhancement
            enhanced_edges = edge_map  # Skip edge enhancement
            text_regions = []  # Skip text detection
            
            # Basic path extraction
            raw_paths = self._extract_paths_text_aware(enhanced_quantized, enhanced_edges, text_regions)
            
            # Simple path processing
            simplified_paths = raw_paths  # Skip advanced simplification
            
            # Basic curve fitting
            final_paths = []
            for path_data in simplified_paths:
                points = path_data['points']
                color = path_data['color']
                if len(points) >= 3:
                    final_paths.append((points, color, 'basic'))
        else:
            # Full experimental processing
            processed_image = self._experimental_preprocessing(image)
            enhanced_quantized = self._enhance_quantization(processed_image, quantized_image)
            enhanced_edges = self._enhance_edge_detection(processed_image, edge_map)
            
            # Text detection and handling
            text_regions = []
            if self.text_detection_enabled:
                text_regions = self._detect_text_regions(processed_image)
            
            # Color layer separation (Vector Magic style)
            color_layers = []
            if self.color_layer_separation:
                color_layers = self._separate_color_layers(enhanced_quantized)
            
            # Enhanced path extraction with text awareness
            raw_paths = self._extract_paths_text_aware(enhanced_quantized, enhanced_edges, text_regions)
            
            # Advanced path simplification
            simplified_paths = self._advanced_simplify_paths(raw_paths)
            
            # Gradient-aware curve fitting
            final_paths = self._gradient_aware_curve_fitting(simplified_paths, processed_image)
        
        # Add paths to SVG with enhanced features
        for path_data in final_paths:
            path_points, color, curve_type = path_data
            if len(path_points) >= 3:
                svg_builder.add_path(path_points, color, fill=True)
        
        # Add text regions as separate elements (only in full mode)
        if not self.fast_mode:
            for text_region in text_regions:
                self._add_text_to_svg(svg_builder, text_region)
        
        return svg_builder
    
    def _experimental_preprocessing(self, image: np.ndarray) -> np.ndarray:
        """Advanced preprocessing with noise reduction and enhancement"""
        processed = image.copy()
        
        if self.noise_reduction_enabled and not self.fast_mode:
            # Bilateral filter for noise reduction while preserving edges
            processed = cv2.bilateralFilter(processed, 9, 75, 75)
            
            # Morphological operations to clean up
            kernel = np.ones((3,3), np.uint8)
            processed = cv2.morphologyEx(processed, cv2.MORPH_CLOSE, kernel)
        elif self.noise_reduction_enabled and self.fast_mode:
            # Fast noise reduction - just Gaussian blur
            processed = cv2.GaussianBlur(processed, (3, 3), 0.5)
        
        return processed
    
    def _enhance_quantization(self, image: np.ndarray, quantized_image: np.ndarray) -> np.ndarray:
        """Enhanced quantization with adaptive clustering"""
        # For now, just return the original quantized image to avoid errors
        # TODO: Implement advanced quantization when needed
        return quantized_image
    
    def _enhance_edge_detection(self, image: np.ndarray, edge_map: np.ndarray) -> np.ndarray:
        """Multi-scale edge detection with adaptive thresholding"""
        if not self.adaptive_thresholding:
            return edge_map
        
        # Ensure proper image format for Canny
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
        
        # Ensure uint8 format
        if gray.dtype != np.uint8:
            gray = (gray * 255).astype(np.uint8) if gray.max() <= 1.0 else gray.astype(np.uint8)
        
        # Multi-scale edge detection
        edges_scale1 = cv2.Canny(gray, 50, 150)
        edges_scale2 = cv2.Canny(gray, 100, 200)
        
        # Combine scales
        combined_edges = cv2.bitwise_or(edges_scale1, edges_scale2)
        
        # Morphological operations to connect edges
        kernel = np.ones((3,3), np.uint8)
        enhanced_edges = cv2.morphologyEx(combined_edges, cv2.MORPH_CLOSE, kernel)
        
        return enhanced_edges
    
    def _detect_text_regions(self, image: np.ndarray) -> List[Dict]:
        """Detect text regions using OCR"""
        text_regions = []
        
        if not (TESSERACT_AVAILABLE or EASYOCR_AVAILABLE):
            return text_regions
        
        try:
            if self.ocr_reader is not None:  # EasyOCR
                results = self.ocr_reader.readtext(image)
                for (bbox, text, confidence) in results:
                    if confidence > 0.5:  # Confidence threshold
                        # Convert bbox to rectangle
                        bbox_array = np.array(bbox)
                        x_min, y_min = bbox_array.min(axis=0).astype(int)
                        x_max, y_max = bbox_array.max(axis=0).astype(int)
                        
                        text_regions.append({
                            'bbox': (x_min, y_min, x_max, y_max),
                            'text': text,
                            'confidence': confidence,
                            'method': 'easyocr'
                        })
            
            elif TESSERACT_AVAILABLE:
                # Fallback to Tesseract
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if len(image.shape) == 3 else image
                
                # Get bounding boxes
                boxes = pytesseract.image_to_boxes(gray)
                h, w = gray.shape
                
                for box in boxes.splitlines():
                    b = box.split(' ')
                    if len(b) >= 5:
                        x_min, y_min, x_max, y_max = int(b[1]), int(b[2]), int(b[3]), int(b[4])
                        # Tesseract uses bottom-left origin, convert to top-left
                        y_min, y_max = h - y_max, h - y_min
                        
                        text_regions.append({
                            'bbox': (x_min, y_min, x_max, y_max),
                            'text': b[0],
                            'confidence': 0.8,  # Default confidence
                            'method': 'tesseract'
                        })
        
        except Exception as e:
            logging.warning(f"Text detection failed: {e}")
        
        return text_regions
    
    def _separate_color_layers(self, quantized_image: np.ndarray) -> List[Dict]:
        """Separate image into color layers like Vector Magic"""
        # Handle different image shapes safely
        if len(quantized_image.shape) == 3 and quantized_image.shape[2] >= 3:
            # RGB or RGBA image
            unique_colors = np.unique(quantized_image.reshape(-1, quantized_image.shape[-1]), axis=0)
        else:
            # Grayscale image
            unique_colors = np.unique(quantized_image.reshape(-1))
            unique_colors = unique_colors.reshape(-1, 1)
        
        color_layers = []
        for i, color in enumerate(unique_colors):
            # Create mask for this color
            if len(quantized_image.shape) == 3 and quantized_image.shape[2] >= 3:
                mask = np.all(quantized_image == color, axis=-1).astype(np.uint8) * 255
                color_tuple = tuple(color[:3])  # Take only RGB
            else:
                mask = (quantized_image == color).astype(np.uint8) * 255
                color_tuple = (int(color[0]), int(color[0]), int(color[0])) if hasattr(color, '__len__') else (int(color), int(color), int(color))
            
            # Calculate layer properties
            area = np.sum(mask > 0)
            coverage = area / (quantized_image.shape[0] * quantized_image.shape[1])
            
            color_layers.append({
                'color': color_tuple,
                'mask': mask,
                'area': area,
                'coverage': coverage,
                'layer_id': i
            })
        
        # Sort by coverage (largest first)
        color_layers.sort(key=lambda x: x['coverage'], reverse=True)
        
        return color_layers
    
    def _extract_paths_text_aware(self, quantized_image: np.ndarray, edge_map: np.ndarray, text_regions: List[Dict]) -> List[Dict]:
        """Extract paths with text region awareness"""
        h, w = quantized_image.shape[:2]
        
        # Create text mask
        text_mask = np.zeros((h, w), dtype=np.uint8)
        for text_region in text_regions:
            x_min, y_min, x_max, y_max = text_region['bbox']
            text_mask[y_min:y_max, x_min:x_max] = 255
        
        # Get unique colors - handle different image formats
        if len(quantized_image.shape) == 3 and quantized_image.shape[2] >= 3:
            unique_colors = np.unique(quantized_image.reshape(-1, quantized_image.shape[-1]), axis=0)
        else:
            unique_colors = np.unique(quantized_image.reshape(-1))
            unique_colors = unique_colors.reshape(-1, 1)
        
        raw_paths = []
        
        for color in unique_colors:
            # Create mask for this color
            if len(quantized_image.shape) == 3 and quantized_image.shape[2] >= 3:
                mask = np.all(quantized_image == color, axis=-1).astype(np.uint8) * 255
                color_tuple = tuple(color[:3])  # Take only RGB
            else:
                mask = (quantized_image == color).astype(np.uint8) * 255
                color_tuple = (int(color[0]), int(color[0]), int(color[0])) if hasattr(color, '__len__') else (int(color), int(color), int(color))
            
            # Exclude text regions for better vectorization
            mask_no_text = cv2.bitwise_and(mask, cv2.bitwise_not(text_mask))
            
            # Filter speckles
            mask_filtered = self._filter_speckles(mask_no_text, self.filter_speckle)
            
            if np.sum(mask_filtered > 0) < 20:
                continue
            
            # Find contours
            contours, _ = cv2.findContours(mask_filtered, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            
            for contour in contours:
                if cv2.contourArea(contour) > self.filter_speckle:
                    path_points = [(float(point[0][0]), float(point[0][1])) for point in contour]
                    
                    raw_paths.append({
                        'points': path_points,
                        'color': color_tuple,
                        'area': cv2.contourArea(contour),
                        'closed': True,
                        'is_text': False
                    })
        
        return raw_paths
    
    def _advanced_simplify_paths(self, raw_paths: List[Dict]) -> List[Dict]:
        """Advanced path simplification with improved algorithms"""
        simplified_paths = []
        
        for path_data in raw_paths:
            points = path_data['points']
            if len(points) < 3:
                continue
            
            # Enhanced splice point detection
            splice_points = self._enhanced_find_splice_points(points)
            
            # Create segments
            segments = self._create_segments(points, splice_points)
            
            # Adaptive simplification
            simplified_segments = []
            for segment in segments:
                # Adaptive epsilon based on segment characteristics
                segment_length = self._calculate_segment_length(segment)
                adaptive_epsilon = max(1.0, segment_length * 0.01)
                
                simplified = self._douglas_peucker_segment(segment, epsilon=adaptive_epsilon)
                simplified_segments.extend(simplified)
            
            if len(simplified_segments) >= 3:
                path_data['points'] = simplified_segments
                simplified_paths.append(path_data)
        
        return simplified_paths
    
    def _enhanced_find_splice_points(self, points: List[Tuple[float, float]]) -> List[int]:
        """Enhanced splice point detection with better corner detection"""
        if len(points) < 5:
            return []
        
        splice_points = []
        
        # Use sliding window for better corner detection
        window_size = min(5, len(points) // 4)
        
        for i in range(window_size, len(points) - window_size):
            # Calculate curvature over window
            curvatures = []
            for j in range(i - window_size//2, i + window_size//2):
                if j > 0 and j < len(points) - 1:
                    p1 = np.array(points[j-1])
                    p2 = np.array(points[j])
                    p3 = np.array(points[j+1])
                    
                    v1 = p2 - p1
                    v2 = p3 - p2
                    
                    angle = self._signed_angle_difference(v1, v2)
                    curvatures.append(abs(angle))
            
            if curvatures:
                avg_curvature = np.mean(curvatures)
                if avg_curvature > math.radians(self.corner_threshold):
                    splice_points.append(i)
        
        return splice_points
    
    def _calculate_segment_length(self, segment: List[Tuple[float, float]]) -> float:
        """Calculate total length of a segment"""
        total_length = 0
        for i in range(len(segment) - 1):
            p1 = np.array(segment[i])
            p2 = np.array(segment[i + 1])
            total_length += np.linalg.norm(p2 - p1)
        return total_length
    
    def _gradient_aware_curve_fitting(self, simplified_paths: List[Dict], image: np.ndarray) -> List[Tuple[List[Tuple[float, float]], Tuple[float, float, float], str]]:
        """Gradient-aware curve fitting for smoother results"""
        final_paths = []
        
        for path_data in simplified_paths:
            points = path_data['points']
            color = path_data['color']
            
            if len(points) < 3:
                continue
            
            # Analyze local gradients around the path
            curve_type = self._analyze_path_gradients(points, image)
            
            if curve_type == 'smooth_spline':
                fitted_points = self._fit_smooth_spline(points)
            elif curve_type == 'adaptive_polygon':
                fitted_points = self._fit_adaptive_polygon(points)
            else:
                fitted_points = points
            
            if len(fitted_points) >= 3:
                final_paths.append((fitted_points, color, curve_type))
        
        return final_paths
    
    def _analyze_path_gradients(self, points: List[Tuple[float, float]], image: np.ndarray) -> str:
        """Analyze gradients around path to determine best fitting method"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
        
        # Calculate gradients along path
        gradients = []
        for x, y in points:
            x_int, y_int = int(x), int(y)
            if 0 <= x_int < gray.shape[1] and 0 <= y_int < gray.shape[0]:
                # Sobel gradients
                gx = cv2.Sobel(gray[max(0, y_int-1):y_int+2, max(0, x_int-1):x_int+2], cv2.CV_64F, 1, 0, ksize=3)
                gy = cv2.Sobel(gray[max(0, y_int-1):y_int+2, max(0, x_int-1):x_int+2], cv2.CV_64F, 0, 1, ksize=3)
                
                if gx.size > 0 and gy.size > 0:
                    gradient_magnitude = np.sqrt(gx**2 + gy**2).mean()
                    gradients.append(gradient_magnitude)
        
        if not gradients:
            return 'pixel'
        
        gradient_variance = np.var(gradients)
        gradient_mean = np.mean(gradients)
        
        # Decision logic based on gradient characteristics
        if gradient_variance > 100 and gradient_mean > 50:
            return 'smooth_spline'
        elif gradient_variance < 50:
            return 'adaptive_polygon'
        else:
            return 'pixel'
    
    def _fit_smooth_spline(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Fit smooth spline with better interpolation"""
        if len(points) < 4:
            return points
        
        # For performance in fast mode, use simpler spline
        if self.fast_mode:
            return self._fit_spline_curve(points)
        
        # Convert to numpy array for easier manipulation
        points_array = np.array(points)
        
        # Generate parameter values
        t = np.linspace(0, 1, len(points))
        
        # Create smooth interpolation
        try:
            from scipy.interpolate import interp1d
            # Cubic spline interpolation
            fx = interp1d(t, points_array[:, 0], kind='cubic', bounds_error=False, fill_value='extrapolate')
            fy = interp1d(t, points_array[:, 1], kind='cubic', bounds_error=False, fill_value='extrapolate')
            
            # Generate smoother points
            t_new = np.linspace(0, 1, max(len(points), 20))
            smooth_points = [(float(fx(ti)), float(fy(ti))) for ti in t_new]
            
            return smooth_points
        except:
            # Fallback to original implementation
            return self._fit_spline_curve(points)
    
    def _fit_adaptive_polygon(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Fit polygon with adaptive simplification"""
        # Adaptive epsilon based on path complexity
        path_length = self._calculate_segment_length(points)
        adaptive_epsilon = max(1.0, path_length * 0.005)
        
        return self._douglas_peucker_segment(points, adaptive_epsilon)
    
    def _add_text_to_svg(self, svg_builder: SVGBuilder, text_region: Dict):
        """Add text region to SVG (placeholder for future text handling)"""
        # For now, just add a rectangle to mark text regions
        x_min, y_min, x_max, y_max = text_region['bbox']
        
        # Add a subtle rectangle to indicate text region
        rect_points = [
            (x_min, y_min),
            (x_max, y_min),
            (x_max, y_max),
            (x_min, y_max)
        ]
        
        # Use a semi-transparent overlay color
        svg_builder.add_path(rect_points, (200, 200, 200), fill=True, opacity=0.3)
    
    # Copy existing methods from original VTracer
    def _signed_angle_difference(self, v1: np.ndarray, v2: np.ndarray) -> float:
        """Calculate signed angle difference between two vectors"""
        v1_norm = v1 / (np.linalg.norm(v1) + 1e-8)
        v2_norm = v2 / (np.linalg.norm(v2) + 1e-8)
        
        angle1 = math.atan2(v1_norm[1], v1_norm[0])
        angle2 = math.atan2(v2_norm[1], v2_norm[0])
        
        diff = angle2 - angle1
        
        while diff > math.pi:
            diff -= 2 * math.pi
        while diff < -math.pi:
            diff += 2 * math.pi
            
        return diff
    
    def _create_segments(self, points: List[Tuple[float, float]], splice_points: List[int]) -> List[List[Tuple[float, float]]]:
        """Create segments between splice points"""
        if not splice_points:
            return [points]
        
        segments = []
        start_idx = 0
        
        for splice_idx in splice_points:
            if splice_idx > start_idx:
                segment = points[start_idx:splice_idx + 1]
                if len(segment) > 1:
                    segments.append(segment)
                start_idx = splice_idx
        
        if start_idx < len(points) - 1:
            segment = points[start_idx:]
            if len(segment) > 1:
                segments.append(segment)
        
        return segments
    
    def _douglas_peucker_segment(self, segment: List[Tuple[float, float]], epsilon: float) -> List[Tuple[float, float]]:
        """Douglas-Peucker simplification for a segment"""
        if len(segment) <= 2:
            return segment
        
        dmax = 0
        index = 0
        
        for i in range(1, len(segment) - 1):
            d = self._perpendicular_distance(segment[i], segment[0], segment[-1])
            if d > dmax:
                index = i
                dmax = d
        
        if dmax > epsilon:
            rec_results1 = self._douglas_peucker_segment(segment[:index + 1], epsilon)
            rec_results2 = self._douglas_peucker_segment(segment[index:], epsilon)
            
            return rec_results1[:-1] + rec_results2
        else:
            return [segment[0], segment[-1]]
    
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
    
    def _fit_spline_curve(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Fit spline curve to points"""
        if len(points) < 4:
            return points
        
        spline_points = []
        spline_points.append(points[0])
        
        for i in range(len(points) - 1):
            p0 = np.array(points[max(0, i-1)])
            p1 = np.array(points[i])
            p2 = np.array(points[min(len(points)-1, i+1)])
            p3 = np.array(points[min(len(points)-1, i+2)])
            
            for t in np.linspace(0, 1, 3):
                if t == 0 and i > 0:
                    continue
                    
                point = 0.5 * (
                    2 * p1 +
                    (-p0 + p2) * t +
                    (2*p0 - 5*p1 + 4*p2 - p3) * t*t +
                    (-p0 + 3*p1 - 3*p2 + p3) * t*t*t
                )
                
                spline_points.append((float(point[0]), float(point[1])))
        
        return spline_points
    
    def _filter_speckles(self, mask: np.ndarray, min_area: int) -> np.ndarray:
        """Filter out small speckles like VTracer"""
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
        
        filtered_mask = np.zeros_like(mask)
        
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if area >= min_area:
                filtered_mask[labels == i] = 255
        
        return filtered_mask