import numpy as np
import cv2
from typing import List, Tuple, Optional, Dict
import math
import logging
from sklearn.cluster import KMeans
from collections import Counter

from ..core.svg_builder import SVGBuilder

class ExperimentalVTracerV3Strategy:
    """Experimental VTracer V3 - Focus on actual VTracer limitations"""
    
    def __init__(self):
        # Base parameters
        self.corner_threshold = 30
        self.filter_speckle = 4
        self.segment_length = 10.0
        
        # Experimental improvements for real problems
        self.enable_small_detail_preservation = True
        self.enable_text_sharpening = True  
        self.enable_gradient_smoothing = True
        self.enable_edge_refinement = True
        
        # Vector Magic-style color palette features
        self.enable_palette_extraction = True
        self.enable_color_layer_separation = True
        self.suggested_palette_counts = [2, 3, 4, 5, 6, 7, 8, 9, 10, 12]
        
        # Version tracking
        self.version = "v3.1.0-experimental-palette"
        
    def vectorize(self, image: np.ndarray, quantized_image: np.ndarray, edge_map: np.ndarray) -> SVGBuilder:
        """Focus on real VTracer limitations rather than parameter tweaking"""
        
        h, w = image.shape[:2]
        
        # First, get the baseline VTracer result
        baseline_svg = self._get_baseline_vtracer_result(image)
        
        if baseline_svg is None:
            # Fallback to basic implementation
            return self._basic_fallback_vectorization(image, quantized_image, edge_map)
        
        # Apply experimental improvements to address VTracer's actual limitations
        improved_svg = self._apply_focused_improvements(baseline_svg, image)
        
        return improved_svg
    
    def _get_baseline_vtracer_result(self, image: np.ndarray) -> Optional[SVGBuilder]:
        """Get baseline VTracer result with standard parameters"""
        try:
            from ..strategies.real_vtracer import RealVTracerStrategy
            
            vtracer = RealVTracerStrategy()
            if not vtracer.available:
                return None
                
            # Use STANDARD parameters - not inflated ones
            standard_params = {
                'filter_speckle': 4,
                'color_precision': 8,
                'layer_difference': 8, 
                'corner_threshold': 90,
                'length_threshold': 1.0,
                'splice_threshold': 20,
                'curve_fitting': 'spline'
            }
            vtracer.set_custom_parameters(standard_params)
            
            result = vtracer.vectorize(image, None, None)
            return result
            
        except Exception as e:
            logging.warning(f"Baseline VTracer failed: {e}")
            return None
    
    def _apply_focused_improvements(self, vtracer_result, image: np.ndarray):
        """Apply improvements that address actual VTracer limitations"""
        
        # VTracer returns RawSVGResult, not SVGBuilder
        # For now, return the original result to avoid errors
        # TODO: Implement proper SVG parsing and enhancement
        
        return vtracer_result
    
    def _preserve_small_details(self, svg_builder: SVGBuilder, image: np.ndarray) -> SVGBuilder:
        """Address VTracer's tendency to lose small details"""
        
        # Detect small objects that VTracer might have missed
        h, w = image.shape[:2]
        
        # Find small high-contrast regions
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if len(image.shape) == 3 else image
        
        # Detect corners and small features
        corners = cv2.goodFeaturesToTrack(gray, maxCorners=100, qualityLevel=0.01, minDistance=5)
        
        if corners is not None and len(corners) > 0:
            # Check if these corners are represented in the existing paths
            existing_coverage = self._check_corner_coverage(corners, svg_builder)
            
            # Add small details for uncovered high-contrast corners  
            for corner in corners:
                x, y = corner.ravel()
                if not self._is_point_covered(x, y, svg_builder, threshold=3):
                    # Add a small detail element
                    self._add_small_detail(svg_builder, x, y, image)
        
        return svg_builder
    
    def _enhance_text_regions(self, svg_builder: SVGBuilder, image: np.ndarray) -> SVGBuilder:
        """Improve text rendering (VTracer's weakness)"""
        
        # Simple text detection using morphological operations  
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if len(image.shape) == 3 else image
        
        # Text has specific aspect ratios and patterns
        # Apply morphological operations to detect text-like regions
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 1))
        text_like = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
        
        # Find contours that might be text
        contours, _ = cv2.findContours(text_like, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Text-like aspect ratio and size filtering
            aspect_ratio = w / h if h > 0 else 0
            area = cv2.contourArea(contour)
            
            if 0.1 < aspect_ratio < 10 and 10 < area < 500:  # Text-like characteristics
                # Check if this region is well-represented in current SVG
                region_quality = self._assess_region_quality(svg_builder, x, y, w, h)
                
                if region_quality < 0.7:  # Poor representation
                    # Add enhanced paths for this text-like region
                    self._enhance_text_region(svg_builder, image, x, y, w, h)
        
        return svg_builder
    
    def _smooth_gradients(self, svg_builder: SVGBuilder, image: np.ndarray) -> SVGBuilder:
        """Address VTracer's stepped gradients"""
        
        # Detect gradient regions in the image
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if len(image.shape) == 3 else image
        
        # Gradient detection using Sobel
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        grad_mag = np.sqrt(grad_x**2 + grad_y**2)
        
        # Find smooth gradient regions (low gradient magnitude over large areas)
        smooth_gradients = cv2.GaussianBlur(grad_mag, (15, 15), 0) < 30
        
        # TODO: Add gradient smoothing logic for identified regions
        # This would involve creating smoother path interpolations
        
        return svg_builder
    
    def _refine_edges(self, svg_builder: SVGBuilder, image: np.ndarray) -> SVGBuilder:
        """Refine jagged edges that VTracer produces"""
        
        if not hasattr(svg_builder, 'elements'):
            return svg_builder
        
        refined_elements = []
        
        for element in svg_builder.elements:
            if hasattr(element, 'points') and len(element.points) > 5:
                # Apply edge smoothing to reduce VTracer's jaggedness
                smoothed_points = self._apply_edge_smoothing(element.points)
                element.points = smoothed_points
            
            refined_elements.append(element)
        
        svg_builder.elements = refined_elements
        return svg_builder
    
    def _apply_edge_smoothing(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Apply intelligent edge smoothing"""
        if len(points) < 5:
            return points
        
        # Convert to numpy for easier manipulation
        points_array = np.array(points)
        
        # Apply gentle smoothing using moving average
        window_size = min(3, len(points) // 3)
        
        if window_size < 2:
            return points
        
        smoothed = np.copy(points_array)
        
        for i in range(window_size, len(points) - window_size):
            # Moving average for smoothing
            window = points_array[i-window_size:i+window_size+1]
            smoothed[i] = np.mean(window, axis=0)
        
        # Convert back to list of tuples
        return [(float(p[0]), float(p[1])) for p in smoothed]
    
    def _check_corner_coverage(self, corners: np.ndarray, svg_builder: SVGBuilder) -> float:
        """Check how well corners are covered by existing paths"""
        if not hasattr(svg_builder, 'elements'):
            return 0.0
        
        covered_corners = 0
        
        for corner in corners:
            x, y = corner.ravel()
            if self._is_point_covered(x, y, svg_builder):
                covered_corners += 1
        
        return covered_corners / len(corners) if len(corners) > 0 else 0.0
    
    def _is_point_covered(self, x: float, y: float, svg_builder: SVGBuilder, threshold: float = 5.0) -> bool:
        """Check if a point is adequately covered by existing paths"""
        if not hasattr(svg_builder, 'elements'):
            return False
        
        for element in svg_builder.elements:
            if hasattr(element, 'points'):
                for px, py in element.points:
                    distance = math.sqrt((x - px)**2 + (y - py)**2)
                    if distance < threshold:
                        return True
        
        return False
    
    def _add_small_detail(self, svg_builder: SVGBuilder, x: float, y: float, image: np.ndarray):
        """Add a small detail element at the specified location"""
        # Sample color at this location
        h, w = image.shape[:2]
        
        ix, iy = int(x), int(y)
        if 0 <= ix < w and 0 <= iy < h:
            if len(image.shape) == 3:
                color = tuple(image[iy, ix])
            else:
                gray_val = image[iy, ix]
                color = (gray_val, gray_val, gray_val)
            
            # Add a small circle to represent the detail
            # Convert color from 0-255 range to 0-1 range for SVGBuilder
            normalized_color = (color[0]/255.0, color[1]/255.0, color[2]/255.0)
            svg_builder.add_circle((x, y), 1.0, normalized_color)
    
    def _assess_region_quality(self, svg_builder: SVGBuilder, x: int, y: int, w: int, h: int) -> float:
        """Assess how well a region is represented in the current SVG"""
        # Simple heuristic: check path density in the region
        if not hasattr(svg_builder, 'elements'):
            return 0.0
        
        points_in_region = 0
        total_points = 0
        
        for element in svg_builder.elements:
            if hasattr(element, 'points'):
                for px, py in element.points:
                    total_points += 1
                    if x <= px <= x + w and y <= py <= y + h:
                        points_in_region += 1
        
        if total_points == 0:
            return 0.0
        
        return points_in_region / total_points
    
    def _enhance_text_region(self, svg_builder: SVGBuilder, image: np.ndarray, x: int, y: int, w: int, h: int):
        """Add enhanced representation for a text region"""
        # Extract the region
        region = image[y:y+h, x:x+w]
        
        if region.size == 0:
            return
        
        # Simple enhancement: add high-contrast paths for text
        gray_region = cv2.cvtColor(region, cv2.COLOR_RGB2GRAY) if len(region.shape) == 3 else region
        
        # Find high-contrast edges in the text region
        edges = cv2.Canny(gray_region, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            if cv2.contourArea(contour) > 3:  # Small but significant details
                # Convert contour to global coordinates
                global_points = [(float(point[0][0] + x), float(point[0][1] + y)) for point in contour]
                
                # Sample color for this detail
                if len(global_points) > 0:
                    cx, cy = global_points[0]
                    ix, iy = int(cx), int(cy)
                    if 0 <= ix < image.shape[1] and 0 <= iy < image.shape[0]:
                        if len(image.shape) == 3:
                            color = tuple(image[iy, ix])
                        else:
                            gray_val = image[iy, ix]
                            color = (gray_val, gray_val, gray_val)
                        
                        # Convert color from 0-255 range to 0-1 range for SVGBuilder
                        normalized_color = (color[0]/255.0, color[1]/255.0, color[2]/255.0)
                        svg_builder.add_path(global_points, normalized_color, fill=False, stroke_width=0.5)
    
    def _basic_fallback_vectorization(self, image: np.ndarray, quantized_image: np.ndarray, edge_map: np.ndarray) -> SVGBuilder:
        """Basic fallback if VTracer unavailable"""
        h, w = image.shape[:2]
        svg_builder = SVGBuilder(w, h)
        
        # Simple contour-based approach
        if len(quantized_image.shape) == 3:
            unique_colors = np.unique(quantized_image.reshape(-1, quantized_image.shape[-1]), axis=0)
        else:
            unique_colors = np.unique(quantized_image.reshape(-1))
            unique_colors = unique_colors.reshape(-1, 1)
        
        for color in unique_colors:
            if len(quantized_image.shape) == 3:
                mask = np.all(quantized_image == color, axis=-1).astype(np.uint8) * 255
                color_tuple = tuple(color[:3])
            else:
                mask = (quantized_image == color).astype(np.uint8) * 255
                color_tuple = (int(color[0]), int(color[0]), int(color[0])) if hasattr(color, '__len__') else (int(color), int(color), int(color))
            
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                if cv2.contourArea(contour) > self.filter_speckle:
                    path_points = [(float(point[0][0]), float(point[0][1])) for point in contour]
                    if len(path_points) >= 3:
                        # Convert color from 0-255 range to 0-1 range for SVGBuilder
                        normalized_color = (color_tuple[0]/255.0, color_tuple[1]/255.0, color_tuple[2]/255.0)
                        svg_builder.add_path(path_points, normalized_color, fill=True)
        
        return svg_builder
    
    def extract_color_palettes(self, image: np.ndarray) -> Dict[str, List[Tuple[int, int, int]]]:
        """Extract suggested color palettes like Vector Magic"""
        h, w = image.shape[:2]
        
        # Reshape image for clustering
        if len(image.shape) == 3:
            pixels = image.reshape(-1, 3)
        else:
            gray_img = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            pixels = np.stack([gray_img.flatten()] * 3, axis=1)
        
        palettes = {}
        
        # Generate suggested palettes for different color counts
        for color_count in self.suggested_palette_counts:
            try:
                palette = self._extract_palette_with_kmeans(pixels, color_count)
                palettes[f"{color_count}_colors"] = palette
            except Exception as e:
                logging.warning(f"Failed to extract {color_count}-color palette: {e}")
                continue
        
        # Add dominant color palette (most frequent colors)
        try:
            dominant_palette = self._extract_dominant_colors(pixels)
            palettes["dominant"] = dominant_palette
        except Exception as e:
            logging.warning(f"Failed to extract dominant palette: {e}")
        
        return palettes
    
    def _extract_palette_with_kmeans(self, pixels: np.ndarray, n_colors: int) -> List[Tuple[int, int, int]]:
        """Extract palette using K-means clustering"""
        # Sample pixels if image is too large
        max_pixels = 10000
        if len(pixels) > max_pixels:
            indices = np.random.choice(len(pixels), max_pixels, replace=False)
            pixels = pixels[indices]
        
        # Perform K-means clustering
        kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
        kmeans.fit(pixels)
        
        # Get cluster centers as colors
        colors = kmeans.cluster_centers_.astype(int)
        
        # Sort colors by frequency
        labels = kmeans.labels_
        label_counts = Counter(labels)
        
        # Sort colors by frequency (most common first)
        sorted_colors = []
        for label, count in label_counts.most_common():
            color = tuple(colors[label])
            sorted_colors.append(color)
        
        return sorted_colors
    
    def _extract_dominant_colors(self, pixels: np.ndarray, max_colors: int = 8) -> List[Tuple[int, int, int]]:
        """Extract most dominant colors by frequency"""
        # Convert to tuples for counting
        color_tuples = [tuple(pixel) for pixel in pixels]
        
        # Count color frequencies
        color_counts = Counter(color_tuples)
        
        # Get most common colors
        dominant_colors = [color for color, count in color_counts.most_common(max_colors)]
        
        return dominant_colors
    
    def create_color_separated_layers(self, image: np.ndarray, palette: List[Tuple[int, int, int]]) -> Dict[str, np.ndarray]:
        """Create separated color layers like Vector Magic"""
        h, w = image.shape[:2]
        layers = {}
        
        # Convert image to RGB if needed
        if len(image.shape) == 3:
            rgb_image = image
        else:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        
        # Use improved color assignment - assign every pixel to closest palette color
        palette_array = np.array(palette)
        pixels = rgb_image.reshape(-1, 3)
        
        # Calculate distances to all palette colors at once (same as preview function)
        distances = np.sqrt(np.sum((pixels[:, np.newaxis, :] - palette_array[np.newaxis, :, :])**2, axis=2))
        closest_indices = np.argmin(distances, axis=1)
        
        # Create layers based on closest color assignment
        for i, color in enumerate(palette):
            color_name = f"color_{i}_{color[0]:02x}{color[1]:02x}{color[2]:02x}"
            
            # Create mask for pixels assigned to this color
            color_mask = (closest_indices == i).reshape(h, w)
            
            # Create layer with only this color
            layer = np.zeros_like(rgb_image)
            layer[color_mask] = color
            
            layers[color_name] = {
                'layer': layer,
                'mask': color_mask,
                'color': color,
                'pixel_count': np.sum(color_mask)
            }
        
        return layers
    
    def _create_color_mask(self, image: np.ndarray, target_color: Tuple[int, int, int], threshold: int = 30) -> np.ndarray:
        """Create a mask for pixels close to the target color"""
        # Calculate color distance for each pixel
        color_diff = np.sqrt(np.sum((image - np.array(target_color))**2, axis=2))
        
        # Create mask for pixels within threshold
        mask = color_diff <= threshold
        
        return mask
    
    def vectorize_with_palette(self, image: np.ndarray, selected_palette: List[Tuple[int, int, int]], 
                             quantized_image: np.ndarray, edge_map: np.ndarray) -> SVGBuilder:
        """Vectorize using a specific color palette - creates smooth vectors like the preview"""
        h, w = image.shape[:2]
        
        print(f"🎨 vectorize_with_palette called with palette: {selected_palette}")
        
        # SIMPLIFIED APPROACH: Just use regular VTracer on the quantized image
        print(f"🎨 Using simplified VTracer approach...")
        
        # Step 1: Create FULL RESOLUTION quantized image (not preview size!)
        quantized_full_res = self._create_full_resolution_quantized_image(image, selected_palette)
        print(f"🎨 Created FULL RESOLUTION quantized image shape: {quantized_full_res.shape}")
        
        # Step 2: Use VTracer on the full resolution quantized image
        print(f"🎨 Using VTracer on FULL RESOLUTION quantized image...")
        vtracer_result = self._use_vtracer_on_quantized_file(quantized_full_res)
        
        if vtracer_result:
            print(f"🎨 VTracer file processing succeeded!")
            return vtracer_result
        else:
            print(f"🎨 VTracer file processing failed, using smooth contours on FULL RESOLUTION...")
            return self._create_smooth_contours_from_quantized(quantized_full_res, selected_palette)
    
    def _vectorize_quantized_image_with_vtracer(self, quantized_image: np.ndarray):
        """Use real VTracer on the quantized image for smooth results"""
        try:
            from ..strategies.real_vtracer import RealVTracerStrategy
            
            vtracer = RealVTracerStrategy()
            if not vtracer.available:
                return None
                
            # Use optimal parameters for clean quantized input
            optimal_params = {
                'filter_speckle': 2,      # Lower since image is already clean
                'color_precision': 4,     # Lower since colors are already quantized
                'layer_difference': 4,    # Lower for better layer separation
                'corner_threshold': 60,   # Smoother curves
                'length_threshold': 0.5,  # Capture more detail
                'splice_threshold': 10,   # Better curve connections
                'curve_fitting': 'spline'
            }
            vtracer.set_custom_parameters(optimal_params)
            
            result = vtracer.vectorize(quantized_image, None, None)
            return result
            
        except Exception as e:
            logging.warning(f"VTracer on quantized image failed: {e}")
            return None
    
    def _vectorize_with_improved_contours(self, image: np.ndarray, selected_palette: List[Tuple[int, int, int]]) -> SVGBuilder:
        """Fallback: Improved contour method with heavy smoothing"""
        h, w = image.shape[:2]
        svg_builder = SVGBuilder(w, h)
        
        # Create color-separated layers
        color_layers = self.create_color_separated_layers(image, selected_palette)
        
        # Process each color layer with heavy smoothing
        for color_name, layer_data in color_layers.items():
            mask = layer_data['mask']
            color = layer_data['color']
            
            if layer_data['pixel_count'] < self.filter_speckle * 4:  # Higher threshold
                continue
            
            # Apply heavy smoothing to mask before contour detection
            smoothed_mask = self._smooth_mask(mask)
            contours = self._extract_layer_contours(smoothed_mask)
            
            # Add heavily smoothed paths
            for contour in contours:
                if cv2.contourArea(contour) > self.filter_speckle * 2:
                    # Apply aggressive smoothing to contour points
                    smoothed_contour = self._smooth_contour(contour)
                    path_points = [(float(point[0]), float(point[1])) for point in smoothed_contour]
                    
                    if len(path_points) >= 3:
                        normalized_color = (color[0]/255.0, color[1]/255.0, color[2]/255.0)
                        svg_builder.add_path(path_points, normalized_color, fill=True, stroke_width=0)
        
        return svg_builder
    
    def _smooth_mask(self, mask: np.ndarray) -> np.ndarray:
        """Apply heavy smoothing to binary mask"""
        # Convert to uint8
        mask_uint8 = (mask * 255).astype(np.uint8)
        
        # Apply morphological operations to smooth
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        smoothed = cv2.morphologyEx(mask_uint8, cv2.MORPH_CLOSE, kernel)
        smoothed = cv2.morphologyEx(smoothed, cv2.MORPH_OPEN, kernel)
        
        # Apply Gaussian blur for additional smoothing
        smoothed = cv2.GaussianBlur(smoothed, (7, 7), 2.0)
        
        return smoothed
    
    def _smooth_contour(self, contour: np.ndarray) -> np.ndarray:
        """Apply aggressive smoothing to contour points"""
        if len(contour) < 6:
            return contour.reshape(-1, 2)
        
        # Convert to points array
        points = contour.reshape(-1, 2).astype(np.float32)
        
        # Apply multiple passes of smoothing
        for _ in range(3):
            smoothed_points = np.copy(points)
            for i in range(1, len(points) - 1):
                # Average with neighbors
                smoothed_points[i] = (points[i-1] + 2*points[i] + points[i+1]) / 4
            points = smoothed_points
        
        return points
    
    def _create_svg_from_quantized_image(self, quantized_image: np.ndarray, selected_palette: List[Tuple[int, int, int]]) -> SVGBuilder:
        """Create clean SVG directly from quantized image using simplified shape detection"""
        h, w = quantized_image.shape[:2]
        svg_builder = SVGBuilder(w, h)
        
        print(f"🎨 Creating clean SVG from quantized image, palette: {selected_palette}")
        
        # For each color in the palette, create clean simplified shapes
        for color in selected_palette:
            print(f"🎨 Processing palette color: {color}")
            
            # Find pixels that exactly match this palette color
            color_mask = np.all(quantized_image == color, axis=2)
            pixel_count = np.sum(color_mask)
            print(f"🎨 Found {pixel_count} pixels for color {color}")
            
            if pixel_count < self.filter_speckle * 10:  # Much higher threshold
                continue
            
            # Create clean simplified shapes instead of pixel-level contours
            simplified_shapes = self._create_simplified_shapes(color_mask)
            print(f"🎨 Created {len(simplified_shapes)} simplified shapes for color {color}")
            
            # Add each simplified shape
            for shape_points in simplified_shapes:
                if len(shape_points) >= 3:
                    # Convert color from 0-255 range to 0-1 range for SVGBuilder
                    normalized_color = (color[0]/255.0, color[1]/255.0, color[2]/255.0)
                    svg_builder.add_path(shape_points, normalized_color, fill=True, stroke_width=0)
                    print(f"🎨 Added simplified shape with {len(shape_points)} points for color {color}")
        
        print(f"🎨 Clean SVG creation complete, total elements: {len(svg_builder.elements)}")
        return svg_builder
    
    def _create_simplified_shapes(self, mask: np.ndarray) -> List[List[Tuple[float, float]]]:
        """Create simplified, clean shapes from a binary mask"""
        # Step 1: Heavy morphological operations to create clean blobs
        mask_uint8 = (mask * 255).astype(np.uint8)
        
        # Apply very aggressive smoothing
        kernel_large = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        kernel_medium = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        
        # Close gaps and holes
        smoothed = cv2.morphologyEx(mask_uint8, cv2.MORPH_CLOSE, kernel_large)
        # Remove small artifacts
        smoothed = cv2.morphologyEx(smoothed, cv2.MORPH_OPEN, kernel_medium)
        # Smooth boundaries
        smoothed = cv2.morphologyEx(smoothed, cv2.MORPH_CLOSE, kernel_medium)
        
        # Apply Gaussian blur for very smooth edges
        smoothed = cv2.GaussianBlur(smoothed, (21, 21), 5.0)
        
        # Threshold back to binary with a lower threshold for smoother shapes
        _, smoothed = cv2.threshold(smoothed, 127, 255, cv2.THRESH_BINARY)
        
        # Step 2: Find contours on the heavily smoothed mask
        contours, _ = cv2.findContours(smoothed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        simplified_shapes = []
        for contour in contours:
            if cv2.contourArea(contour) > self.filter_speckle * 20:  # Much higher threshold
                # Step 3: Apply Douglas-Peucker simplification for clean geometric shapes
                epsilon = 0.02 * cv2.arcLength(contour, True)  # Aggressive simplification
                simplified = cv2.approxPolyDP(contour, epsilon, True)
                
                # Convert to list of tuples
                points = [(float(point[0][0]), float(point[0][1])) for point in simplified]
                
                # Step 4: Additional geometric smoothing
                if len(points) >= 3:
                    smoothed_points = self._apply_geometric_smoothing(points)
                    simplified_shapes.append(smoothed_points)
        
        return simplified_shapes
    
    def _apply_geometric_smoothing(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Apply geometric smoothing to create clean, rounded shapes"""
        if len(points) < 4:
            return points
        
        # Convert to numpy for easier manipulation
        points_array = np.array(points)
        
        # Apply multiple passes of geometric smoothing
        for pass_num in range(3):
            smoothed = np.copy(points_array)
            
            for i in range(len(points_array)):
                # Get neighboring points (wrap around)
                prev_idx = (i - 1) % len(points_array)
                next_idx = (i + 1) % len(points_array)
                
                # Weighted average with neighbors for smooth curves
                weight_self = 0.6
                weight_neighbor = 0.2
                
                smoothed[i] = (weight_self * points_array[i] + 
                              weight_neighbor * points_array[prev_idx] + 
                              weight_neighbor * points_array[next_idx])
            
            points_array = smoothed
        
        # Convert back to list of tuples
        return [(float(p[0]), float(p[1])) for p in points_array]
    
    def _create_high_res_quantized_image(self, image: np.ndarray, selected_palette: List[Tuple[int, int, int]], upscale_factor: int) -> np.ndarray:
        """Create a high-resolution version of the quantized image for smoother VTracer input"""
        # First create the regular quantized image
        quantized = self.create_quantized_preview(image, selected_palette)
        
        # Upscale using high-quality interpolation
        h, w = quantized.shape[:2]
        new_h, new_w = h * upscale_factor, w * upscale_factor
        
        # Use INTER_NEAREST to preserve exact color values, then apply smoothing
        upscaled = cv2.resize(quantized, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
        
        # Apply gentle smoothing to create cleaner edges for VTracer
        smoothed = cv2.GaussianBlur(upscaled, (5, 5), 1.0)
        
        return smoothed
    
    def _vectorize_with_vtracer_clean(self, high_res_image: np.ndarray, scale_factor: int):
        """Use VTracer on high-resolution clean image with optimal settings"""
        try:
            from ..strategies.real_vtracer import RealVTracerStrategy
            
            vtracer = RealVTracerStrategy()
            if not vtracer.available:
                print("🎨 VTracer not available")
                return None
            
            # Optimal parameters for high-resolution clean quantized input
            optimal_params = {
                'filter_speckle': 1,          # Very low since image is clean
                'color_precision': 2,         # Very low since colors are pre-quantized
                'layer_difference': 2,        # Low for clean separation
                'corner_threshold': 45,       # Moderate for smooth curves
                'length_threshold': 0.3,      # Capture fine detail
                'splice_threshold': 5,        # Tight connections
                'curve_fitting': 'spline'     # Smooth curves
            }
            
            print(f"🎨 Using VTracer with params: {optimal_params}")
            vtracer.set_custom_parameters(optimal_params)
            
            # Process with VTracer
            result = vtracer.vectorize(high_res_image, None, None)
            
            if result and hasattr(result, 'get_svg_string'):
                # Scale down the coordinates to match original image size
                scaled_result = self._scale_vtracer_result(result, 1.0/scale_factor)
                return scaled_result
            
            return result
            
        except Exception as e:
            print(f"🎨 VTracer processing failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _scale_vtracer_result(self, vtracer_result, scale_factor: float):
        """Scale VTracer result coordinates back to original image size"""
        try:
            # VTracer returns RawSVGResult - we need to parse and rescale the SVG
            svg_content = vtracer_result.get_svg_string()
            
            # Simple coordinate scaling in SVG content
            import re
            
            def scale_coordinate(match):
                value = float(match.group(1))
                scaled_value = value * scale_factor
                return f"{scaled_value:.2f}"
            
            # Scale all numeric values in path data and coordinates
            scaled_svg = re.sub(r'(\d+(?:\.\d+)?)', scale_coordinate, svg_content)
            
            # Create a new result with scaled SVG
            class ScaledSVGResult:
                def __init__(self, scaled_svg_content):
                    self.svg_content = scaled_svg_content
                    self.processing_time = vtracer_result.processing_time if hasattr(vtracer_result, 'processing_time') else 0.1
                    self.strategy_used = "vtracer_palette_scaled"
                    self.quality_score = 0.9
                    
                def get_svg_string(self):
                    return self.svg_content
            
            return ScaledSVGResult(scaled_svg)
            
        except Exception as e:
            print(f"🎨 Scaling VTracer result failed: {e}")
            return vtracer_result
    
    def _vectorize_simple_with_vtracer(self, quantized_image: np.ndarray):
        """Simple VTracer approach without scaling complexity"""
        try:
            from ..strategies.real_vtracer import RealVTracerStrategy
            
            vtracer = RealVTracerStrategy()
            if not vtracer.available:
                print("🎨 VTracer not available")
                return None
            
            # Very simple, conservative parameters
            simple_params = {
                'filter_speckle': 2,
                'color_precision': 4,
                'layer_difference': 4,
                'corner_threshold': 90,
                'length_threshold': 1.0,
                'splice_threshold': 20,
                'curve_fitting': 'spline'
            }
            
            print(f"🎨 Using simple VTracer with params: {simple_params}")
            vtracer.set_custom_parameters(simple_params)
            
            result = vtracer.vectorize(quantized_image, None, None)
            print(f"🎨 VTracer result type: {type(result)}")
            
            return result
            
        except Exception as e:
            print(f"🎨 Simple VTracer failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_simple_rectangles_from_quantized(self, quantized_image: np.ndarray, selected_palette: List[Tuple[int, int, int]]) -> SVGBuilder:
        """Create simple rectangular regions for each color as a basic fallback"""
        h, w = quantized_image.shape[:2]
        svg_builder = SVGBuilder(w, h)
        
        print(f"🎨 Creating simple rectangles from quantized image")
        
        # For each color, find bounding boxes of connected regions
        for color in selected_palette:
            print(f"🎨 Processing color: {color}")
            
            # Find pixels that match this color
            color_mask = np.all(quantized_image == color, axis=2)
            pixel_count = np.sum(color_mask)
            
            if pixel_count < 100:  # Skip very small regions
                continue
            
            # Find connected components
            mask_uint8 = (color_mask * 255).astype(np.uint8)
            num_labels, labels = cv2.connectedComponents(mask_uint8)
            
            for label in range(1, num_labels):  # Skip background (label 0)
                component_mask = (labels == label)
                component_pixels = np.sum(component_mask)
                
                if component_pixels < 50:  # Skip tiny components
                    continue
                
                # Find bounding box of this component
                y_coords, x_coords = np.where(component_mask)
                if len(y_coords) > 0:
                    min_x, max_x = np.min(x_coords), np.max(x_coords)
                    min_y, max_y = np.min(y_coords), np.max(y_coords)
                    
                    # Create a simple rectangle
                    rect_width = max_x - min_x + 1
                    rect_height = max_y - min_y + 1
                    
                    if rect_width > 5 and rect_height > 5:  # Only add reasonably sized rectangles
                        normalized_color = (color[0]/255.0, color[1]/255.0, color[2]/255.0)
                        # Convert numpy integers to Python floats
                        x_float = float(min_x)
                        y_float = float(min_y)
                        width_float = float(rect_width)
                        height_float = float(rect_height)
                        svg_builder.add_rectangle(x_float, y_float, width_float, height_float, normalized_color)
                        print(f"🎨 Added rectangle: {x_float},{y_float} {width_float}x{height_float}")
        
        print(f"🎨 Created {len(svg_builder.elements)} rectangle elements")
        return svg_builder
    
    def _create_smooth_contours_from_quantized(self, quantized_image: np.ndarray, selected_palette: List[Tuple[int, int, int]]) -> SVGBuilder:
        """Create smooth contours from quantized image with ultra-aggressive smoothing"""
        h, w = quantized_image.shape[:2]
        svg_builder = SVGBuilder(w, h)
        
        print(f"🎨 Creating ultra-smooth contours from quantized image")
        
        # For each color, create ultra-smooth shapes
        for color in selected_palette:
            print(f"🎨 Processing color: {color}")
            
            # Find pixels that match this color
            color_mask = np.all(quantized_image == color, axis=2)
            pixel_count = np.sum(color_mask)
            print(f"🎨 Found {pixel_count} pixels for color {color}")
            
            if pixel_count < 100:  # Skip very small regions
                continue
            
            # Create ultra-smooth shapes
            smooth_shapes = self._create_ultra_smooth_shapes(color_mask)
            print(f"🎨 Created {len(smooth_shapes)} ultra-smooth shapes for color {color}")
            
            # Add each smooth shape
            for shape_points in smooth_shapes:
                if len(shape_points) >= 3:
                    normalized_color = (color[0]/255.0, color[1]/255.0, color[2]/255.0)
                    svg_builder.add_path(shape_points, normalized_color, fill=True, stroke_width=0)
                    print(f"🎨 Added ultra-smooth shape with {len(shape_points)} points for color {color}")
        
        print(f"🎨 Ultra-smooth contour creation complete, total elements: {len(svg_builder.elements)}")
        return svg_builder
    
    def _create_ultra_smooth_shapes(self, mask: np.ndarray) -> List[List[Tuple[float, float]]]:
        """Create ultra-smooth shapes with maximum smoothing"""
        mask_uint8 = (mask * 255).astype(np.uint8)
        
        # Step 1: EXTREME morphological smoothing
        # Use very large kernels for maximum smoothing
        kernel_huge = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
        kernel_large = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        
        # Multiple passes of aggressive smoothing
        smoothed = mask_uint8
        for _ in range(2):  # Multiple passes
            smoothed = cv2.morphologyEx(smoothed, cv2.MORPH_CLOSE, kernel_huge)
            smoothed = cv2.morphologyEx(smoothed, cv2.MORPH_OPEN, kernel_large)
        
        # Step 2: EXTREME Gaussian blur for ultra-smooth edges
        smoothed = cv2.GaussianBlur(smoothed, (31, 31), 8.0)  # Much larger kernel and sigma
        
        # Step 3: Conservative threshold to maintain smooth edges
        _, smoothed = cv2.threshold(smoothed, 100, 255, cv2.THRESH_BINARY)  # Lower threshold
        
        # Step 4: Find contours on the ultra-smoothed mask
        contours, _ = cv2.findContours(smoothed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        ultra_smooth_shapes = []
        for contour in contours:
            if cv2.contourArea(contour) > 200:  # Higher threshold for meaningful shapes
                # Step 5: EXTREME Douglas-Peucker simplification
                epsilon = 0.05 * cv2.arcLength(contour, True)  # Even more aggressive simplification
                simplified = cv2.approxPolyDP(contour, epsilon, True)
                
                # Convert to list of tuples
                points = [(float(point[0][0]), float(point[0][1])) for point in simplified]
                
                # Step 6: Ultra-geometric smoothing
                if len(points) >= 3:
                    ultra_smooth_points = self._apply_ultra_geometric_smoothing(points)
                    ultra_smooth_shapes.append(ultra_smooth_points)
        
        return ultra_smooth_shapes
    
    def _apply_ultra_geometric_smoothing(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Apply ultra-aggressive geometric smoothing"""
        if len(points) < 4:
            return points
        
        points_array = np.array(points)
        
        # Apply many more passes of smoothing with stronger weights
        for pass_num in range(5):  # More passes
            smoothed = np.copy(points_array)
            
            for i in range(len(points_array)):
                prev_idx = (i - 1) % len(points_array)
                next_idx = (i + 1) % len(points_array)
                
                # Stronger neighbor influence for smoother curves
                weight_self = 0.4      # Lower self weight
                weight_neighbor = 0.3  # Higher neighbor weight
                
                smoothed[i] = (weight_self * points_array[i] + 
                              weight_neighbor * points_array[prev_idx] + 
                              weight_neighbor * points_array[next_idx])
            
            points_array = smoothed
        
        return [(float(p[0]), float(p[1])) for p in points_array]
    
    def _create_full_resolution_quantized_image(self, image: np.ndarray, selected_palette: List[Tuple[int, int, int]]) -> np.ndarray:
        """Create a full resolution quantized image (like preview but full size)"""
        h, w = image.shape[:2]
        
        # Convert image to RGB if needed
        if len(image.shape) == 3:
            rgb_image = image
        else:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        
        # NO RESIZING! Use full resolution
        print(f"🎨 Processing FULL RESOLUTION image: {rgb_image.shape}")
        
        # Convert palette to numpy array for vectorized operations
        palette_array = np.array(selected_palette)
        
        # Reshape image for vectorized distance calculation
        pixels = rgb_image.reshape(-1, 3)
        
        # Calculate distances to all palette colors at once (same logic as preview)
        distances = np.sqrt(np.sum((pixels[:, np.newaxis, :] - palette_array[np.newaxis, :, :])**2, axis=2))
        
        # Find closest color for each pixel
        closest_indices = np.argmin(distances, axis=1)
        
        # Map pixels to closest palette colors
        quantized_pixels = palette_array[closest_indices]
        
        # Reshape back to image
        quantized_image = quantized_pixels.reshape(h, w, 3)
        
        print(f"🎨 Full resolution quantization complete: {quantized_image.shape}")
        return quantized_image.astype(np.uint8)
    
    def _use_vtracer_on_quantized_file(self, quantized_image: np.ndarray):
        """Use VTracer properly on the clean quantized image"""
        try:
            from ..strategies.real_vtracer import RealVTracerStrategy
            
            vtracer = RealVTracerStrategy()
            if not vtracer.available:
                print("🎨 VTracer not available")
                return None
            
            # Use optimal parameters for clean quantized input
            optimal_params = {
                'filter_speckle': 1,      # Very low since image is clean
                'color_precision': 3,     # Low since colors are pre-quantized  
                'layer_difference': 3,    # Low for clean separation
                'corner_threshold': 45,   # Smooth curves
                'length_threshold': 0.3,  # Capture detail
                'splice_threshold': 8,    # Good connections
                'curve_fitting': 'spline' # Smooth curves
            }
            
            print(f"🎨 Using VTracer on quantized image with params: {optimal_params}")
            vtracer.set_custom_parameters(optimal_params)
            
            # Convert quantized image to proper format (0-1 range for VTracer)
            quantized_normalized = quantized_image.astype(np.float32) / 255.0
            
            # Use VTracer's existing vectorize method - it handles file conversion internally
            result = vtracer.vectorize(quantized_normalized, None, None)
            
            if result and hasattr(result, 'get_svg_string'):
                svg_content = result.get_svg_string()
                print(f"🎨 VTracer processing generated {len(svg_content)} characters of SVG")
                
                # Check if result has meaningful content
                if len(svg_content) > 1000:  # Non-trivial SVG
                    return result
                else:
                    print(f"🎨 VTracer result too small, likely empty")
                    return None
            else:
                print(f"🎨 VTracer returned invalid result")
                return None
                
        except Exception as e:
            print(f"🎨 VTracer processing failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extract_layer_contours(self, mask: np.ndarray) -> List[np.ndarray]:
        """Extract contours from a color layer mask"""
        # Convert mask to uint8
        mask_uint8 = (mask * 255).astype(np.uint8)
        
        # Find contours
        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter out very small contours
        filtered_contours = [c for c in contours if cv2.contourArea(c) > self.filter_speckle]
        
        return filtered_contours
    
    def generate_palette_preview(self, image: np.ndarray, selected_palette: List[Tuple[int, int, int]]) -> np.ndarray:
        """Generate a preview image showing only the selected palette colors"""
        h, w = image.shape[:2]
        
        # Convert image to RGB if needed
        if len(image.shape) == 3:
            rgb_image = image
        else:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        
        # Create preview image
        preview_image = np.zeros_like(rgb_image)
        
        # For each color in the palette, find matching pixels and set them
        for color in selected_palette:
            color_mask = self._create_color_mask(rgb_image, color, threshold=40)
            preview_image[color_mask] = color
        
        return preview_image
    
    def create_quantized_preview(self, image: np.ndarray, selected_palette: List[Tuple[int, int, int]]) -> np.ndarray:
        """Create a fast quantized preview that shows exactly what will be vectorized"""
        h, w = image.shape[:2]
        
        # Convert image to RGB if needed
        if len(image.shape) == 3:
            rgb_image = image
        else:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        
        # Resize for faster processing if image is large
        max_preview_size = 400
        if max(h, w) > max_preview_size:
            scale = max_preview_size / max(h, w)
            new_h, new_w = int(h * scale), int(w * scale)
            rgb_image = cv2.resize(rgb_image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            h, w = new_h, new_w
        
        # Convert palette to numpy array for vectorized operations
        palette_array = np.array(selected_palette)
        
        # Reshape image for vectorized distance calculation
        pixels = rgb_image.reshape(-1, 3)
        
        # Calculate distances to all palette colors at once
        distances = np.sqrt(np.sum((pixels[:, np.newaxis, :] - palette_array[np.newaxis, :, :])**2, axis=2))
        
        # Find closest color for each pixel
        closest_indices = np.argmin(distances, axis=1)
        
        # Map pixels to closest palette colors
        quantized_pixels = palette_array[closest_indices]
        
        # Reshape back to image
        quantized_image = quantized_pixels.reshape(h, w, 3)
        
        return quantized_image.astype(np.uint8)