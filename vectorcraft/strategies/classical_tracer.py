import numpy as np
import cv2
from typing import List, Tuple, Optional
from ..core.svg_builder import SVGBuilder

class ClassicalTracer:
    def __init__(self):
        self.contour_threshold = 50
        self.approx_epsilon = 0.01
        
    def trace(self, image: np.ndarray, edge_map: np.ndarray) -> List[List[Tuple[float, float]]]:
        """Extract contours from edge map and simplify them"""
        
        # Ensure edge_map is uint8
        if edge_map.dtype != np.uint8:
            edge_map = edge_map.astype(np.uint8)
        
        # Find contours
        contours, _ = cv2.findContours(edge_map, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        simplified_paths = []
        
        for contour in contours:
            # Filter out tiny contours
            if cv2.contourArea(contour) < self.contour_threshold:
                continue
            
            # Approximate contour to reduce points
            epsilon = self.approx_epsilon * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Convert to list of tuples
            path = [(float(point[0][0]), float(point[0][1])) for point in approx]
            
            if len(path) >= 3:  # Need at least 3 points for a meaningful shape
                simplified_paths.append(path)
        
        return simplified_paths
    
    def trace_with_colors(self, image: np.ndarray, quantized_image: np.ndarray) -> SVGBuilder:
        """Trace each color region separately"""
        h, w = image.shape[:2]
        svg_builder = SVGBuilder(w, h)
        
        # Get unique colors
        unique_colors = np.unique(quantized_image.reshape(-1, quantized_image.shape[-1]), axis=0)
        
        for color in unique_colors:
            # Create mask for this color
            mask = np.all(quantized_image == color, axis=-1).astype(np.uint8) * 255
            
            # Skip if mask is too small
            if np.sum(mask > 0) < 100:
                continue
            
            # Ensure mask is uint8
            if mask.dtype != np.uint8:
                mask = mask.astype(np.uint8)
            
            # Find contours for this color
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                if cv2.contourArea(contour) < self.contour_threshold:
                    continue
                
                # Simplify contour
                epsilon = self.approx_epsilon * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                # Convert to path points
                path_points = [(float(point[0][0]), float(point[0][1])) for point in approx]
                
                if len(path_points) >= 3:
                    svg_builder.add_path(path_points, tuple(color), fill=True)
        
        return svg_builder
    
    def douglas_peucker(self, points: List[Tuple[float, float]], epsilon: float) -> List[Tuple[float, float]]:
        """Simplify path using Douglas-Peucker algorithm"""
        if len(points) <= 2:
            return points
        
        # Find the point with maximum distance from line segment
        dmax = 0
        index = 0
        end = len(points) - 1
        
        for i in range(1, end):
            d = self._perpendicular_distance(points[i], points[0], points[end])
            if d > dmax:
                index = i
                dmax = d
        
        # If max distance is greater than epsilon, recursively simplify
        if dmax > epsilon:
            # Recursive call
            rec_results1 = self.douglas_peucker(points[:index+1], epsilon)
            rec_results2 = self.douglas_peucker(points[index:], epsilon)
            
            # Build result list
            return rec_results1[:-1] + rec_results2
        else:
            return [points[0], points[end]]
    
    def _perpendicular_distance(self, point: Tuple[float, float], 
                               line_start: Tuple[float, float], 
                               line_end: Tuple[float, float]) -> float:
        """Calculate perpendicular distance from point to line segment"""
        x0, y0 = point
        x1, y1 = line_start
        x2, y2 = line_end
        
        # Calculate the distance
        num = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
        den = np.sqrt((y2 - y1)**2 + (x2 - x1)**2)
        
        if den == 0:
            return 0
        
        return num / den
    
    def smooth_path(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Apply smoothing to reduce jaggedness"""
        if len(points) < 3:
            return points
        
        smoothed = [points[0]]  # Keep first point
        
        # Apply simple moving average
        for i in range(1, len(points) - 1):
            prev_pt = points[i - 1]
            curr_pt = points[i]
            next_pt = points[i + 1]
            
            # Weighted average (current point gets more weight)
            smooth_x = (prev_pt[0] + 2 * curr_pt[0] + next_pt[0]) / 4
            smooth_y = (prev_pt[1] + 2 * curr_pt[1] + next_pt[1]) / 4
            
            smoothed.append((smooth_x, smooth_y))
        
        smoothed.append(points[-1])  # Keep last point
        return smoothed