import svgwrite
import numpy as np
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class PathElement:
    points: List[Tuple[float, float]]
    color: Tuple[float, float, float]
    fill: bool = True
    stroke_width: float = 0.0

@dataclass
class CircleElement:
    center: Tuple[float, float]
    radius: float
    color: Tuple[float, float, float]
    fill: bool = True
    stroke_width: float = 0.0

@dataclass
class RectElement:
    x: float
    y: float
    width: float
    height: float
    color: Tuple[float, float, float]
    fill: bool = True
    stroke_width: float = 0.0

class SVGBuilder:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.elements = []
        
    def add_path(self, points: List[Tuple[float, float]], color: Tuple[float, float, float], 
                 fill: bool = True, stroke_width: float = 0.0):
        self.elements.append(PathElement(points, color, fill, stroke_width))
    
    def add_circle(self, center: Tuple[float, float], radius: float, 
                   color: Tuple[float, float, float], fill: bool = True, stroke_width: float = 0.0):
        self.elements.append(CircleElement(center, radius, color, fill, stroke_width))
    
    def add_rectangle(self, x: float, y: float, width: float, height: float,
                     color: Tuple[float, float, float], fill: bool = True, stroke_width: float = 0.0):
        self.elements.append(RectElement(x, y, width, height, color, fill, stroke_width))
    
    def build(self) -> svgwrite.Drawing:
        dwg = svgwrite.Drawing(size=(self.width, self.height))
        
        for element in self.elements:
            if isinstance(element, PathElement):
                self._add_path_to_svg(dwg, element)
            elif isinstance(element, CircleElement):
                self._add_circle_to_svg(dwg, element)
            elif isinstance(element, RectElement):
                self._add_rect_to_svg(dwg, element)
        
        return dwg
    
    def _add_path_to_svg(self, dwg: svgwrite.Drawing, path: PathElement):
        if len(path.points) < 2:
            return
        
        # Convert to SVG path format
        path_data = f"M {path.points[0][0]},{path.points[0][1]}"
        
        # Add bezier curves for smooth paths
        if len(path.points) >= 4:
            for i in range(1, len(path.points) - 2, 3):
                if i + 2 < len(path.points):
                    cp1 = path.points[i]
                    cp2 = path.points[i + 1]
                    end = path.points[i + 2]
                    path_data += f" C {cp1[0]},{cp1[1]} {cp2[0]},{cp2[1]} {end[0]},{end[1]}"
        else:
            # Simple line segments
            for point in path.points[1:]:
                path_data += f" L {point[0]},{point[1]}"
        
        if path.fill:
            path_data += " Z"
        
        color_str = f"rgb({int(path.color[0]*255)},{int(path.color[1]*255)},{int(path.color[2]*255)})"
        
        svg_path = dwg.path(
            d=path_data,
            fill=color_str if path.fill else "none",
            stroke=color_str if path.stroke_width > 0 else "none",
            stroke_width=path.stroke_width
        )
        dwg.add(svg_path)
    
    def _add_circle_to_svg(self, dwg: svgwrite.Drawing, circle: CircleElement):
        color_str = f"rgb({int(circle.color[0]*255)},{int(circle.color[1]*255)},{int(circle.color[2]*255)})"
        
        svg_circle = dwg.circle(
            center=circle.center,
            r=circle.radius,
            fill=color_str if circle.fill else "none",
            stroke=color_str if circle.stroke_width > 0 else "none",
            stroke_width=circle.stroke_width
        )
        dwg.add(svg_circle)
    
    def _add_rect_to_svg(self, dwg: svgwrite.Drawing, rect: RectElement):
        color_str = f"rgb({int(rect.color[0]*255)},{int(rect.color[1]*255)},{int(rect.color[2]*255)})"
        
        svg_rect = dwg.rect(
            insert=(rect.x, rect.y),
            size=(rect.width, rect.height),
            fill=color_str if rect.fill else "none",
            stroke=color_str if rect.stroke_width > 0 else "none",
            stroke_width=rect.stroke_width
        )
        dwg.add(svg_rect)
    
    def save(self, filename: str):
        dwg = self.build()
        dwg.saveas(filename)
    
    def get_svg_string(self) -> str:
        dwg = self.build()
        return dwg.tostring()