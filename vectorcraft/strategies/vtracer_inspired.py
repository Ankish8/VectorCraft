import numpy as np
import cv2
from typing import List, Tuple, Optional, Dict
from scipy.spatial.distance import pdist, squareform
from sklearn.cluster import DBSCAN
import math

from ..core.svg_builder import SVGBuilder

class VTracerInspiredStrategy:
    """VTracer-inspired vectorization strategy with 3-stage process"""
    
    def __init__(self):
        self.corner_threshold = 30  # degrees
        self.filter_speckle = 4     # minimum area in pixels
        self.segment_length = 10.0  # smoothing parameter
        
    def vectorize(self, image: np.ndarray, quantized_image: np.ndarray, edge_map: np.ndarray) -> SVGBuilder:
        """VTracer's 3-stage process: Path Extraction -> Path Simplification -> Curve Fitting"""
        
        h, w = image.shape[:2]
        svg_builder = SVGBuilder(w, h)
        
        # Stage 1: Path Extraction using walker-based tracing
        raw_paths = self._extract_paths_walker(quantized_image, edge_map)
        
        # Stage 2: Path Simplification with splice point detection
        simplified_paths = self._simplify_paths_splice(raw_paths)
        
        # Stage 3: Curve Fitting with multiple modes
        final_paths = self._fit_curves_adaptive(simplified_paths)
        
        # Add paths to SVG with colors
        for path_data in final_paths:
            path_points, color, curve_type = path_data
            if len(path_points) >= 3:
                svg_builder.add_path(path_points, color, fill=True)
        
        return svg_builder
    
    def _extract_paths_walker(self, quantized_image: np.ndarray, edge_map: np.ndarray) -> List[Dict]:
        """Stage 1: Path extraction using VTracer's walker approach"""
        h, w = quantized_image.shape[:2]
        
        # Get unique colors (clusters from hierarchical clustering)
        unique_colors = np.unique(quantized_image.reshape(-1, quantized_image.shape[-1]), axis=0)
        
        raw_paths = []
        
        for color in unique_colors:
            # Create mask for this color cluster
            if len(quantized_image.shape) == 3:
                mask = np.all(quantized_image == color, axis=-1).astype(np.uint8) * 255
            else:
                mask = (quantized_image == color).astype(np.uint8) * 255
            
            # Filter speckles (VTracer approach)
            mask = self._filter_speckles(mask, self.filter_speckle)
            
            if np.sum(mask > 0) < 20:  # Skip tiny regions
                continue
            
            # Build image tree and trace outlines
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            
            for contour in contours:
                if cv2.contourArea(contour) > self.filter_speckle:
                    # Convert contour to path points
                    path_points = [(float(point[0][0]), float(point[0][1])) for point in contour]
                    
                    raw_paths.append({
                        'points': path_points,
                        'color': tuple(color) if len(color.shape) > 0 else (color, color, color),
                        'area': cv2.contourArea(contour),
                        'closed': True
                    })
        
        return raw_paths
    
    def _simplify_paths_splice(self, raw_paths: List[Dict]) -> List[Dict]:
        """Stage 2: Path simplification using signed angle differences for splice points"""
        simplified_paths = []
        
        for path_data in raw_paths:
            points = path_data['points']
            if len(points) < 3:
                continue
                
            # Find splice points using signed angle differences
            splice_points = self._find_splice_points(points)
            
            # Create segments between splice points
            segments = self._create_segments(points, splice_points)
            
            # Simplify each segment
            simplified_segments = []
            for segment in segments:
                simplified = self._douglas_peucker_segment(segment, epsilon=2.0)
                simplified_segments.extend(simplified)
            
            if len(simplified_segments) >= 3:
                path_data['points'] = simplified_segments
                simplified_paths.append(path_data)
        
        return simplified_paths
    
    def _find_splice_points(self, points: List[Tuple[float, float]]) -> List[int]:
        """Find splice points using VTracer's signed angle difference method"""
        if len(points) < 5:
            return []
            
        splice_points = []
        
        for i in range(2, len(points) - 2):
            # Calculate vectors
            p1 = np.array(points[i-1])
            p2 = np.array(points[i])
            p3 = np.array(points[i+1])
            
            v1 = p2 - p1
            v2 = p3 - p2
            
            # Calculate signed angle difference
            angle = self._signed_angle_difference(v1, v2)
            
            # Check if it's a corner (VTracer's corner threshold)
            if abs(angle) > math.radians(self.corner_threshold):
                splice_points.append(i)
        
        return splice_points
    
    def _signed_angle_difference(self, v1: np.ndarray, v2: np.ndarray) -> float:
        """Calculate signed angle difference between two vectors"""
        # Normalize vectors
        v1_norm = v1 / (np.linalg.norm(v1) + 1e-8)
        v2_norm = v2 / (np.linalg.norm(v2) + 1e-8)
        
        # Calculate angle using atan2 for proper quadrant handling
        angle1 = math.atan2(v1_norm[1], v1_norm[0])
        angle2 = math.atan2(v2_norm[1], v2_norm[0])
        
        # Calculate signed difference
        diff = angle2 - angle1
        
        # Normalize to [-π, π]
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
        
        # Add final segment
        if start_idx < len(points) - 1:
            segment = points[start_idx:]
            if len(segment) > 1:
                segments.append(segment)
        
        return segments
    
    def _douglas_peucker_segment(self, segment: List[Tuple[float, float]], epsilon: float) -> List[Tuple[float, float]]:
        """Douglas-Peucker simplification for a segment"""
        if len(segment) <= 2:
            return segment
        
        # Find point with maximum distance
        dmax = 0
        index = 0
        
        for i in range(1, len(segment) - 1):
            d = self._perpendicular_distance(segment[i], segment[0], segment[-1])
            if d > dmax:
                index = i
                dmax = d
        
        # If max distance is greater than epsilon, recursively simplify
        if dmax > epsilon:
            # Recursive calls
            rec_results1 = self._douglas_peucker_segment(segment[:index + 1], epsilon)
            rec_results2 = self._douglas_peucker_segment(segment[index:], epsilon)
            
            # Build result
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
    
    def _fit_curves_adaptive(self, simplified_paths: List[Dict]) -> List[Tuple[List[Tuple[float, float]], Tuple[float, float, float], str]]:
        """Stage 3: Adaptive curve fitting with multiple modes"""
        final_paths = []
        
        for path_data in simplified_paths:
            points = path_data['points']
            color = path_data['color']
            
            if len(points) < 3:
                continue
            
            # Determine best curve fitting mode based on path characteristics
            curve_type = self._determine_curve_mode(points)
            
            if curve_type == 'spline':
                fitted_points = self._fit_spline_curve(points)
            elif curve_type == 'polygon':
                fitted_points = self._fit_polygon(points)
            else:  # pixel mode
                fitted_points = points
            
            if len(fitted_points) >= 3:
                final_paths.append((fitted_points, color, curve_type))
        
        return final_paths
    
    def _determine_curve_mode(self, points: List[Tuple[float, float]]) -> str:
        """Determine optimal curve fitting mode for path"""
        if len(points) < 4:
            return 'pixel'
        
        # Calculate curvature variance
        curvatures = []
        for i in range(1, len(points) - 1):
            p1 = np.array(points[i-1])
            p2 = np.array(points[i])
            p3 = np.array(points[i+1])
            
            # Simple curvature approximation
            v1 = p2 - p1
            v2 = p3 - p2
            
            if np.linalg.norm(v1) > 0 and np.linalg.norm(v2) > 0:
                curvature = abs(self._signed_angle_difference(v1, v2))
                curvatures.append(curvature)
        
        if not curvatures:
            return 'pixel'
        
        curvature_variance = np.var(curvatures)
        
        # Decision logic based on curvature characteristics
        if curvature_variance > 0.5:  # High variance -> use spline
            return 'spline'
        elif curvature_variance < 0.1:  # Low variance -> use polygon
            return 'polygon'
        else:
            return 'pixel'
    
    def _fit_spline_curve(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Fit spline curve to points"""
        if len(points) < 4:
            return points
        
        # Simple spline approximation using control points
        spline_points = []
        
        # Add first point
        spline_points.append(points[0])
        
        # Generate intermediate points using cubic interpolation
        for i in range(len(points) - 1):
            p0 = np.array(points[max(0, i-1)])
            p1 = np.array(points[i])
            p2 = np.array(points[min(len(points)-1, i+1)])
            p3 = np.array(points[min(len(points)-1, i+2)])
            
            # Simple cubic interpolation
            for t in np.linspace(0, 1, 3):
                if t == 0 and i > 0:  # Skip duplicate points
                    continue
                    
                # Catmull-Rom spline approximation
                point = 0.5 * (
                    2 * p1 +
                    (-p0 + p2) * t +
                    (2*p0 - 5*p1 + 4*p2 - p3) * t*t +
                    (-p0 + 3*p1 - 3*p2 + p3) * t*t*t
                )
                
                spline_points.append((float(point[0]), float(point[1])))
        
        return spline_points
    
    def _fit_polygon(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Fit polygon to points (simplified representation)"""
        # Use more aggressive Douglas-Peucker for polygon mode
        epsilon = max(2.0, len(points) * 0.1)  # Adaptive epsilon
        return self._douglas_peucker_segment(points, epsilon)
    
    def _filter_speckles(self, mask: np.ndarray, min_area: int) -> np.ndarray:
        """Filter out small speckles like VTracer"""
        # Find connected components
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
        
        # Create filtered mask
        filtered_mask = np.zeros_like(mask)
        
        for i in range(1, num_labels):  # Skip background (label 0)
            area = stats[i, cv2.CC_STAT_AREA]
            if area >= min_area:
                filtered_mask[labels == i] = 255
        
        return filtered_mask