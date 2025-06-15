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
        """Enhanced circle detection with multiple methods"""
        gray = cv2.cvtColor((image * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY) if len(image.shape) == 3 else (image * 255).astype(np.uint8)
        
        circles_combined = []
        
        # Method 1: Standard HoughCircles with adaptive parameters
        circles = cv2.HoughCircles(
            gray, cv2.HOUGH_GRADIENT, dp=1, minDist=15,  # Closer circles allowed
            param1=30, param2=15,  # Lower thresholds for subtle circles
            minRadius=3, maxRadius=min(gray.shape) // 2
        )
        
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            for (x, y, r) in circles:
                confidence = self._calculate_circle_confidence_enhanced(edge_map, (x, y), r)
                if confidence > 0.2:  # Lower threshold for subtle shapes
                    circles_combined.append(Circle((float(x), float(y)), float(r), confidence))
        
        # Method 2: Contour-based circle detection
        contours, _ = cv2.findContours(edge_map, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            if len(contour) >= 5:  # Need at least 5 points for ellipse fitting
                try:
                    ellipse = cv2.fitEllipse(contour)
                    center, axes, angle = ellipse
                    
                    # Check if it's approximately circular
                    ratio = min(axes) / max(axes) if max(axes) > 0 else 0
                    if ratio > 0.7:  # Fairly circular
                        radius = np.mean(axes) / 2
                        confidence = ratio * 0.6  # Base confidence on circularity
                        if radius > 3:  # Minimum meaningful radius
                            circles_combined.append(Circle(center, radius, confidence))
                except:
                    continue  # Skip if ellipse fitting fails
        
        return self._filter_duplicate_circles(circles_combined)
    
    def _calculate_circle_confidence_enhanced(self, edge_map: np.ndarray, center: Tuple[int, int], radius: int) -> float:
        """Enhanced circle confidence calculation"""
        x, y = center
        
        # Sample more points around the circle
        angles = np.linspace(0, 2*np.pi, 32)  # More sample points
        edge_hits = 0
        
        for angle in angles:
            # Sample points at multiple radii around the target radius
            for r_offset in [-2, -1, 0, 1, 2]:
                px = int(x + (radius + r_offset) * np.cos(angle))
                py = int(y + (radius + r_offset) * np.sin(angle))
                
                if 0 <= px < edge_map.shape[1] and 0 <= py < edge_map.shape[0]:
                    if edge_map[py, px] > 0:
                        edge_hits += 1
                        break  # Found edge at this angle
        
        return edge_hits / len(angles)
    
    def _filter_duplicate_circles(self, circles: List[Circle]) -> List[Circle]:
        """Filter out duplicate/overlapping circles"""
        if not circles:
            return circles
        
        # Sort by confidence
        circles.sort(key=lambda c: c.confidence, reverse=True)
        
        filtered = []
        for circle in circles:
            is_duplicate = False
            for existing in filtered:
                # Check distance between centers
                dist = np.sqrt((circle.center[0] - existing.center[0])**2 + 
                              (circle.center[1] - existing.center[1])**2)
                # If centers are close and radii similar, it's a duplicate
                if dist < max(circle.radius, existing.radius) * 0.5:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                filtered.append(circle)
        
        return filtered
    
    def detect_rectangles(self, edge_map: np.ndarray) -> List[Rectangle]:
        """Enhanced rectangle detection with better approximation"""
        # Ensure edge_map is uint8
        if edge_map.dtype != np.uint8:
            edge_map = edge_map.astype(np.uint8)
        
        contours, _ = cv2.findContours(edge_map, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        rectangles = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 200:  # Increased minimum area to reduce noise
                continue
                
            # Try multiple epsilon values for better approximation
            for epsilon_factor in [0.01, 0.02, 0.03]:
                epsilon = epsilon_factor * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                # Check if it's rectangular (4-5 corners for better accuracy)
                if 4 <= len(approx) <= 5:
                    # Get rotated rectangle
                    rect = cv2.minAreaRect(contour)
                    (center_x, center_y), (width, height), angle = rect
                    
                    # Skip very thin rectangles (likely noise)
                    if min(width, height) < 3:
                        continue
                    
                    # Calculate confidence based on how well it fits a rectangle
                    confidence = self._calculate_rect_confidence_enhanced(contour, rect, len(approx))
                    
                    if confidence > 0.5:  # Higher threshold for better quality rectangles
                        x = center_x - width / 2
                        y = center_y - height / 2
                        
                        rectangles.append(Rectangle(x, y, width, height, angle, confidence))
                        break  # Found good approximation, no need to try other epsilons
        
        return self._filter_duplicate_rectangles(rectangles)
    
    def _calculate_rect_confidence_enhanced(self, contour: np.ndarray, rect: Tuple, num_corners: int) -> float:
        """Enhanced rectangle confidence calculation with angle validation"""
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
        
        # Bonus for having close to 4 corners
        corner_bonus = 1.0 if num_corners == 4 else (0.8 if num_corners == 5 else 0.6)
        
        # Angle regularity check - rectangles should have ~90° corners
        angle_regularity = self._calculate_angle_regularity(box)
        
        # Aspect ratio reasonableness (not too thin)
        (_, _), (width, height), _ = rect
        aspect_ratio = max(width, height) / max(min(width, height), 1)
        aspect_penalty = 1.0 if aspect_ratio <= 10 else (0.8 if aspect_ratio <= 20 else 0.5)
        
        # Enhanced confidence formula with geometric validation
        confidence = (area_ratio * 0.3 + perimeter_ratio * 0.3 + 
                     corner_bonus * 0.2 + angle_regularity * 0.15 + aspect_penalty * 0.05)
        
        return confidence
    
    def _calculate_angle_regularity(self, box: np.ndarray) -> float:
        """Calculate how regular the angles are (closer to 90° = better)"""
        angles = []
        for i in range(4):
            p1 = box[i]
            p2 = box[(i + 1) % 4]
            p3 = box[(i + 2) % 4]
            
            # Calculate vectors
            v1 = p1 - p2
            v2 = p3 - p2
            
            # Calculate angle between vectors
            cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
            cos_angle = np.clip(cos_angle, -1, 1)
            angle = np.arccos(cos_angle) * 180 / np.pi
            angles.append(angle)
        
        # Check how close angles are to 90°
        angle_deviations = [abs(angle - 90) for angle in angles]
        avg_deviation = np.mean(angle_deviations)
        
        # Convert to regularity score (lower deviation = higher score)
        regularity = max(0, 1.0 - avg_deviation / 45.0)  # 45° max deviation
        return regularity
    
    def _filter_duplicate_rectangles(self, rectangles: List[Rectangle]) -> List[Rectangle]:
        """Filter out duplicate/overlapping rectangles"""
        if not rectangles:
            return rectangles
        
        # Sort by confidence
        rectangles.sort(key=lambda r: r.confidence, reverse=True)
        
        filtered = []
        for rect in rectangles:
            is_duplicate = False
            for existing in filtered:
                # Check overlap using center distance and size similarity
                center_dist = np.sqrt((rect.x + rect.width/2 - existing.x - existing.width/2)**2 + 
                                    (rect.y + rect.height/2 - existing.y - existing.height/2)**2)
                avg_size = (rect.width + rect.height + existing.width + existing.height) / 4
                
                if center_dist < avg_size * 0.3:  # Close centers
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                filtered.append(rect)
        
        return filtered
    
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