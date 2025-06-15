import numpy as np
import cv2
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class Circle:
    center: Tuple[float, float]
    radius: float
    confidence: float

@dataclass
class Rectangle:
    x: float
    y: float
    width: float
    height: float
    angle: float
    confidence: float

@dataclass
class Line:
    start: Tuple[float, float]
    end: Tuple[float, float]
    confidence: float

class PrimitiveDetector:
    def __init__(self):
        self.circle_min_radius = 10
        self.circle_max_radius = 200
        self.line_threshold = 30
        self.rect_min_area = 100
        
    def detect_circles(self, image: np.ndarray, edge_map: np.ndarray) -> List[Circle]:
        """Detect circles using HoughCircles"""
        gray = cv2.cvtColor((image * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY) if len(image.shape) == 3 else (image * 255).astype(np.uint8)
        
        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=30,
            param1=50,
            param2=30,
            minRadius=self.circle_min_radius,
            maxRadius=self.circle_max_radius
        )
        
        detected_circles = []
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            for (x, y, r) in circles:
                # Calculate confidence based on edge alignment
                confidence = self._calculate_circle_confidence(edge_map, (x, y), r)
                detected_circles.append(Circle((float(x), float(y)), float(r), confidence))
        
        return detected_circles
    
    def detect_rectangles(self, edge_map: np.ndarray) -> List[Rectangle]:
        """Detect rectangles from contours"""
        # Ensure edge_map is uint8
        if edge_map.dtype != np.uint8:
            edge_map = edge_map.astype(np.uint8)
        
        contours, _ = cv2.findContours(edge_map, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        rectangles = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.rect_min_area:
                continue
                
            # Approximate contour to polygon
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Check if it's roughly rectangular (4 corners)
            if len(approx) == 4:
                # Get rotated rectangle
                rect = cv2.minAreaRect(contour)
                (center_x, center_y), (width, height), angle = rect
                
                # Calculate confidence based on how well it fits a rectangle
                confidence = self._calculate_rect_confidence(contour, rect)
                
                x = center_x - width / 2
                y = center_y - height / 2
                
                rectangles.append(Rectangle(x, y, width, height, angle, confidence))
        
        return rectangles
    
    def detect_lines(self, edge_map: np.ndarray) -> List[Line]:
        """Detect straight lines using HoughLines"""
        # Ensure edge_map is uint8
        if edge_map.dtype != np.uint8:
            edge_map = edge_map.astype(np.uint8)
        
        lines = cv2.HoughLinesP(
            edge_map,
            rho=1,
            theta=np.pi/180,
            threshold=self.line_threshold,
            minLineLength=30,
            maxLineGap=10
        )
        
        detected_lines = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                
                # Calculate line length for confidence
                length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                confidence = min(1.0, length / 100.0)  # Longer lines = higher confidence
                
                detected_lines.append(Line((float(x1), float(y1)), (float(x2), float(y2)), confidence))
        
        return detected_lines
    
    def detect_all_primitives(self, image: np.ndarray, edge_map: np.ndarray) -> Dict[str, List[Any]]:
        """Detect all primitive types"""
        return {
            'circles': self.detect_circles(image, edge_map),
            'rectangles': self.detect_rectangles(edge_map),
            'lines': self.detect_lines(edge_map)
        }
    
    def _calculate_circle_confidence(self, edge_map: np.ndarray, center: Tuple[int, int], radius: int) -> float:
        """Calculate how well detected circle matches edge pixels"""
        x, y = center
        
        # Sample points around the circle
        angles = np.linspace(0, 2*np.pi, 32)
        edge_hits = 0
        total_points = len(angles)
        
        for angle in angles:
            px = int(x + radius * np.cos(angle))
            py = int(y + radius * np.sin(angle))
            
            if 0 <= px < edge_map.shape[1] and 0 <= py < edge_map.shape[0]:
                # Check if there's an edge pixel nearby
                if self._has_edge_nearby(edge_map, px, py, radius=3):
                    edge_hits += 1
        
        return edge_hits / total_points
    
    def _calculate_rect_confidence(self, contour: np.ndarray, rect: Tuple) -> float:
        """Calculate how well contour matches rectangle"""
        # Get the four corner points of the rectangle
        box = cv2.boxPoints(rect)
        box = np.int0(box)
        
        # Calculate area ratio
        contour_area = cv2.contourArea(contour)
        rect_area = cv2.contourArea(box)
        
        if rect_area == 0:
            return 0.0
            
        area_ratio = min(contour_area, rect_area) / max(contour_area, rect_area)
        
        # Calculate perimeter ratio
        contour_perimeter = cv2.arcLength(contour, True)
        rect_perimeter = cv2.arcLength(box, True)
        
        if rect_perimeter == 0:
            return 0.0
            
        perimeter_ratio = min(contour_perimeter, rect_perimeter) / max(contour_perimeter, rect_perimeter)
        
        # Combine ratios
        return (area_ratio + perimeter_ratio) / 2
    
    def _has_edge_nearby(self, edge_map: np.ndarray, x: int, y: int, radius: int = 3) -> bool:
        """Check if there's an edge pixel within radius"""
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                px, py = x + dx, y + dy
                if 0 <= px < edge_map.shape[1] and 0 <= py < edge_map.shape[0]:
                    if edge_map[py, px] > 0:
                        return True
        return False
    
    def filter_overlapping_primitives(self, primitives: Dict[str, List[Any]], 
                                    overlap_threshold: float = 0.5) -> Dict[str, List[Any]]:
        """Remove overlapping primitives, keeping higher confidence ones"""
        filtered = {key: [] for key in primitives.keys()}
        
        # Process circles
        circles = sorted(primitives['circles'], key=lambda c: c.confidence, reverse=True)
        for circle in circles:
            overlapping = False
            for existing in filtered['circles']:
                if self._circles_overlap(circle, existing, overlap_threshold):
                    overlapping = True
                    break
            if not overlapping:
                filtered['circles'].append(circle)
        
        # Process rectangles
        rectangles = sorted(primitives['rectangles'], key=lambda r: r.confidence, reverse=True)
        for rect in rectangles:
            overlapping = False
            for existing in filtered['rectangles']:
                if self._rectangles_overlap(rect, existing, overlap_threshold):
                    overlapping = True
                    break
            if not overlapping:
                filtered['rectangles'].append(rect)
        
        # Lines don't typically need overlap filtering
        filtered['lines'] = primitives['lines']
        
        return filtered
    
    def _circles_overlap(self, c1: Circle, c2: Circle, threshold: float) -> bool:
        """Check if two circles overlap significantly"""
        center_dist = np.sqrt((c1.center[0] - c2.center[0])**2 + (c1.center[1] - c2.center[1])**2)
        return center_dist < (c1.radius + c2.radius) * threshold
    
    def _rectangles_overlap(self, r1: Rectangle, r2: Rectangle, threshold: float) -> bool:
        """Check if two rectangles overlap significantly"""
        # Simple bounding box overlap check
        x1_min, x1_max = r1.x, r1.x + r1.width
        y1_min, y1_max = r1.y, r1.y + r1.height
        x2_min, x2_max = r2.x, r2.x + r2.width
        y2_min, y2_max = r2.y, r2.y + r2.height
        
        # Calculate overlap area
        overlap_x = max(0, min(x1_max, x2_max) - max(x1_min, x2_min))
        overlap_y = max(0, min(y1_max, y2_max) - max(y1_min, y2_min))
        overlap_area = overlap_x * overlap_y
        
        # Calculate union area
        area1 = r1.width * r1.height
        area2 = r2.width * r2.height
        union_area = area1 + area2 - overlap_area
        
        if union_area == 0:
            return False
            
        return overlap_area / union_area > threshold