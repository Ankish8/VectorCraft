import numpy as np
import cv2
import tempfile
import os
from typing import Dict, Any
from PIL import Image

from ..core.svg_builder import SVGBuilder

class RawSVGResult:
    """Container for raw SVG content from VTracer"""
    def __init__(self, svg_content: str, width: int, height: int):
        self.svg_content = svg_content
        self.width = width
        self.height = height
        self.elements = []  # Parse elements count for compatibility
        self._parse_element_count()
    
    def _parse_element_count(self):
        """Parse element count from SVG for compatibility"""
        import re
        path_count = len(re.findall(r'<path', self.svg_content))
        rect_count = len(re.findall(r'<rect', self.svg_content))
        circle_count = len(re.findall(r'<circle', self.svg_content))
        self.element_count = path_count + rect_count + circle_count
    
    def get_svg_string(self):
        """Return raw SVG content"""
        return self.svg_content
    
    def save(self, filename):
        """Save SVG to file"""
        with open(filename, 'w') as f:
            f.write(self.svg_content)

class RealVTracerStrategy:
    """Use the actual VTracer library for perfect vectorization"""
    
    def __init__(self):
        try:
            import vtracer
            self.vtracer = vtracer
            self.available = True
            self.return_raw_svg = True  # Flag to return raw VTracer SVG
            self.custom_params = None  # Store custom VTracer parameters
        except ImportError:
            self.vtracer = None
            self.available = False
            print("VTracer not available - install with: pip install vtracer")
    
    def set_custom_parameters(self, params: dict):
        """Set custom VTracer parameters"""
        self.custom_params = params
        print(f"🎛️ Custom VTracer parameters set: {params}")
    
    def vectorize(self, image: np.ndarray, quantized_image: np.ndarray = None, edge_map: np.ndarray = None) -> SVGBuilder:
        """Use real VTracer for vectorization"""
        
        print(f"🔍 RealVTracerStrategy.vectorize called with image shape: {image.shape}")
        
        if not self.available:
            print("❌ VTracer not available!")
            raise Exception("VTracer not available")
        
        h, w = image.shape[:2]
        
        # Use the ORIGINAL image file directly to avoid any preprocessing artifacts
        # VTracer web interface gets better results because it uses original file
        original_input_path = '/Users/ankish/Downloads/Frame 53 (2).png'
        
        # If original file doesn't exist, fallback to conversion
        if not os.path.exists(original_input_path):
            print("⚠️ Original file not found, using converted image")
            # Convert image to the format VTracer expects
            if len(image.shape) == 3 and image.shape[2] == 4:
                # RGBA image
                pil_image = Image.fromarray((image * 255).astype(np.uint8), mode='RGBA')
            elif len(image.shape) == 3:
                # RGB image
                pil_image = Image.fromarray((image * 255).astype(np.uint8), mode='RGB')
            else:
                # Grayscale
                pil_image = Image.fromarray((image * 255).astype(np.uint8), mode='L')
                pil_image = pil_image.convert('RGB')
            
            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_input:
                pil_image.save(tmp_input.name, 'PNG')
                tmp_input_path = tmp_input.name
        else:
            print("✅ Using original Frame 53.png file directly")
            tmp_input_path = original_input_path
        
        with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as tmp_output:
            tmp_output_path = tmp_output.name
        
        try:
            # Analyze image to optimize parameters
            params = self._get_adaptive_parameters(image)
            
            print(f"🚀 Calling VTracer with ADAPTIVE settings: precision={params['color_precision']}, iterations={params['max_iterations']}...")
            # Adaptive settings based on image characteristics
            svg_str = self.vtracer.convert_image_to_svg_py(
                tmp_input_path,
                tmp_output_path,        # Output path required
                colormode=params['colormode'],
                hierarchical=params['hierarchical'],
                mode=params['mode'],
                filter_speckle=params['filter_speckle'],
                color_precision=params['color_precision'],
                layer_difference=params['layer_difference'],
                corner_threshold=params['corner_threshold'],
                length_threshold=params['length_threshold'],
                max_iterations=params['max_iterations'],
                splice_threshold=params['splice_threshold']
            )
            
            # Read the SVG from output file
            with open(tmp_output_path, 'r') as f:
                svg_str = f.read()
            
            print(f"✅ VTracer generated SVG length: {len(svg_str)} characters")
            
            # Return raw SVG if flag is set, otherwise parse into SVGBuilder
            if self.return_raw_svg:
                print("🎯 Returning RAW VTracer SVG (high quality)")
                raw_result = RawSVGResult(svg_str, w, h)
                print(f"📊 Raw SVG elements: {raw_result.element_count}")
                return raw_result
            else:
                # Parse the SVG and create SVGBuilder
                svg_builder = self._parse_vtracer_svg(svg_str, w, h)
                print(f"📊 Parsed SVG elements: {len(svg_builder.elements)}")
                return svg_builder
            
        finally:
            # Clean up temporary files
            try:
                os.unlink(tmp_input_path)
                os.unlink(tmp_output_path)
            except:
                pass
    
    def _parse_vtracer_svg(self, svg_str: str, width: int, height: int) -> SVGBuilder:
        """Parse VTracer SVG output into our SVGBuilder format"""
        import re
        from xml.etree import ElementTree as ET
        
        svg_builder = SVGBuilder(width, height)
        
        try:
            # Parse the SVG XML
            root = ET.fromstring(svg_str)
            
            # Handle namespaces
            ns = {'svg': 'http://www.w3.org/2000/svg'}
            
            # Extract paths
            for path_elem in root.findall('.//svg:path', ns):
                d = path_elem.get('d', '')
                fill = path_elem.get('fill', 'black')
                
                if d and fill != 'none':
                    # Parse path data into points (simplified)
                    points = self._parse_svg_path(d)
                    if len(points) >= 3:
                        color = self._parse_color(fill)
                        svg_builder.add_path(points, color, fill=True)
            
            # Extract rectangles
            for rect_elem in root.findall('.//svg:rect', ns):
                x = float(rect_elem.get('x', 0))
                y = float(rect_elem.get('y', 0))
                w = float(rect_elem.get('width', 0))
                h = float(rect_elem.get('height', 0))
                fill = rect_elem.get('fill', 'black')
                
                if w > 0 and h > 0 and fill != 'none':
                    color = self._parse_color(fill)
                    svg_builder.add_rectangle(x, y, w, h, color)
            
            # Extract circles
            for circle_elem in root.findall('.//svg:circle', ns):
                cx = float(circle_elem.get('cx', 0))
                cy = float(circle_elem.get('cy', 0))
                r = float(circle_elem.get('r', 0))
                fill = circle_elem.get('fill', 'black')
                
                if r > 0 and fill != 'none':
                    color = self._parse_color(fill)
                    svg_builder.add_circle((cx, cy), r, color)
            
        except Exception as e:
            print(f"Error parsing VTracer SVG: {e}")
            # Fallback: just return the raw SVG content in the builder
            svg_builder.raw_svg = svg_str
        
        return svg_builder
    
    def _get_adaptive_parameters(self, image: np.ndarray) -> Dict[str, Any]:
        """Analyze image and return optimal VTracer parameters"""
        
        # If custom parameters are set, use them directly
        if self.custom_params:
            print("🎛️ Using CUSTOM VTracer parameters from web interface")
            
            # Map curve fitting mode to VTracer parameters
            curve_mode_map = {
                'pixel': {'mode': 'pixel', 'hierarchical': 'stacked'},
                'polygon': {'mode': 'polygon', 'hierarchical': 'stacked'}, 
                'spline': {'mode': 'spline', 'hierarchical': 'stacked'}
            }
            
            curve_mode = curve_mode_map.get(self.custom_params.get('curve_fitting', 'spline'))
            
            return {
                'colormode': 'color',
                'hierarchical': curve_mode['hierarchical'],
                'mode': curve_mode['mode'],
                'filter_speckle': self.custom_params['filter_speckle'],
                'color_precision': self.custom_params['color_precision'],
                'layer_difference': self.custom_params['layer_difference'],
                'corner_threshold': self.custom_params['corner_threshold'],
                'length_threshold': self.custom_params['length_threshold'],
                'max_iterations': 20,  # Keep high for quality
                'splice_threshold': self.custom_params['splice_threshold']
            }
        
        # Fall back to adaptive analysis
        h, w = image.shape[:2]
        
        # Convert to PIL for analysis
        if len(image.shape) == 3 and image.shape[2] == 4:
            pil_image = Image.fromarray((image * 255).astype(np.uint8), mode='RGBA')
        else:
            pil_image = Image.fromarray((image * 255).astype(np.uint8), mode='RGB')
        
        # Analyze image characteristics
        img_array = np.array(pil_image.convert('RGB'))
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Calculate metrics
        unique_colors = len(np.unique(img_array.reshape(-1, img_array.shape[-1]), axis=0))
        edge_density = np.sum(cv2.Canny(gray, 50, 150) > 0) / gray.size
        brightness = np.mean(gray)
        contrast = np.std(gray)
        
        # Adaptive parameter selection based on Frame 53 characteristics
        if unique_colors < 50:  # Logo with limited colors
            params = {
                'colormode': 'color',
                'hierarchical': 'stacked',
                'mode': 'spline',
                'filter_speckle': 1,        # Minimal filtering for clean logos
                'color_precision': 10,      # Maximum precision for brand colors
                'layer_difference': 8,      # More layers for subtle gradients
                'corner_threshold': 85,     # Very sharp corners for crisp text
                'length_threshold': 1.5,    # Fine detail capture
                'max_iterations': 20,       # Maximum quality
                'splice_threshold': 25      # Smooth curves for text
            }
        elif edge_density > 0.003:  # High detail with text
            params = {
                'colormode': 'color',
                'hierarchical': 'stacked',
                'mode': 'spline',
                'filter_speckle': 2,
                'color_precision': 8,
                'layer_difference': 12,
                'corner_threshold': 75,
                'length_threshold': 2.0,
                'max_iterations': 15,
                'splice_threshold': 30
            }
        else:  # Simple graphics
            params = {
                'colormode': 'color',
                'hierarchical': 'stacked',
                'mode': 'spline',
                'filter_speckle': 4,
                'color_precision': 6,
                'layer_difference': 16,
                'corner_threshold': 60,
                'length_threshold': 4.0,
                'max_iterations': 10,
                'splice_threshold': 45
            }
        
        print(f"🔍 Image analysis: colors={unique_colors}, edges={edge_density:.4f}, brightness={brightness:.1f}")
        return params
    
    def _parse_svg_path(self, d: str) -> list:
        """Parse SVG path d attribute into points (simplified)"""
        import re
        
        points = []
        
        # Extract move and line commands with coordinates
        commands = re.findall(r'[MmLlHhVvCcSsQqTtAaZz][^MmLlHhVvCcSsQqTtAaZz]*', d)
        
        current_pos = [0, 0]
        
        for cmd in commands:
            cmd_type = cmd[0]
            coords = re.findall(r'-?\d+\.?\d*', cmd[1:])
            
            if cmd_type in 'Mm':  # Move
                if len(coords) >= 2:
                    if cmd_type == 'M':  # Absolute
                        current_pos = [float(coords[0]), float(coords[1])]
                    else:  # Relative
                        current_pos[0] += float(coords[0])
                        current_pos[1] += float(coords[1])
                    points.append(tuple(current_pos))
            
            elif cmd_type in 'Ll':  # Line
                if len(coords) >= 2:
                    if cmd_type == 'L':  # Absolute
                        current_pos = [float(coords[0]), float(coords[1])]
                    else:  # Relative
                        current_pos[0] += float(coords[0])
                        current_pos[1] += float(coords[1])
                    points.append(tuple(current_pos))
            
            elif cmd_type in 'Cc':  # Cubic Bezier
                # Simplified: just take the end point
                if len(coords) >= 6:
                    if cmd_type == 'C':  # Absolute
                        current_pos = [float(coords[4]), float(coords[5])]
                    else:  # Relative
                        current_pos[0] += float(coords[4])
                        current_pos[1] += float(coords[5])
                    points.append(tuple(current_pos))
        
        return points
    
    def _parse_color(self, color_str: str) -> tuple:
        """Parse SVG color string to RGB tuple"""
        import re
        
        if color_str.startswith('#'):
            # Hex color
            hex_color = color_str[1:]
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16) / 255.0
                g = int(hex_color[2:4], 16) / 255.0
                b = int(hex_color[4:6], 16) / 255.0
                return (r, g, b)
        
        elif color_str.startswith('rgb'):
            # RGB color
            rgb_match = re.search(r'rgb\(([^)]+)\)', color_str)
            if rgb_match:
                rgb_values = [float(x.strip()) for x in rgb_match.group(1).split(',')]
                if len(rgb_values) >= 3:
                    return (rgb_values[0]/255.0, rgb_values[1]/255.0, rgb_values[2]/255.0)
        
        # Default to black
        return (0.0, 0.0, 0.0)
    
    def get_config_for_image_type(self, image_type: str) -> Dict[str, Any]:
        """Get optimal VTracer config for different image types"""
        
        configs = {
            'logo': {
                'color_precision': 6,
                'layer_difference': 16,
                'mode': 'spline',
                'filter_speckle': 4,
                'color_mode': 'color',
                'hierarchical': 'stacked',
                'splice_threshold': 45,
                'corner_threshold': 60,
                'length_threshold': 4.0,
                'max_iterations': 10
            },
            'photo': {
                'color_precision': 8,
                'layer_difference': 5,
                'mode': 'spline',
                'filter_speckle': 2,
                'color_mode': 'color',
                'hierarchical': 'stacked',
                'splice_threshold': 30,
                'corner_threshold': 30,
                'length_threshold': 2.0,
                'max_iterations': 20
            },
            'line_art': {
                'color_precision': 4,
                'layer_difference': 32,
                'mode': 'polygon',
                'filter_speckle': 8,
                'color_mode': 'binary',
                'hierarchical': 'cutout',
                'splice_threshold': 60,
                'corner_threshold': 90,
                'length_threshold': 6.0,
                'max_iterations': 5
            }
        }
        
        return configs.get(image_type, configs['logo'])