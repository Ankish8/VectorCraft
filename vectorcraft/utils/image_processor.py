import numpy as np
import cv2
from PIL import Image
from typing import Tuple, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ImageMetadata:
    width: int
    height: int
    has_transparency: bool
    dominant_colors: list
    edge_density: float
    text_probability: float
    geometric_probability: float
    gradient_probability: float

class ImageProcessor:
    def __init__(self):
        self.cache = {}
    
    def load_image(self, path: str) -> np.ndarray:
        if path in self.cache:
            return self.cache[path]
        
        img = Image.open(path).convert('RGBA')
        img_array = np.array(img)
        self.cache[path] = img_array
        return img_array
    
    def preprocess(self, image: np.ndarray, target_size: Optional[Tuple[int, int]] = None) -> np.ndarray:
        if target_size:
            image = cv2.resize(image, target_size, interpolation=cv2.INTER_AREA)
        
        # Normalize to 0-1 range
        if image.dtype == np.uint8:
            image = image.astype(np.float32) / 255.0
        
        return image
    
    def analyze_content(self, image: np.ndarray) -> ImageMetadata:
        h, w = image.shape[:2]
        
        # Check transparency
        has_transparency = image.shape[2] == 4 and np.any(image[:, :, 3] < 1.0)
        
        # Get dominant colors using simple clustering
        rgb_image = image[:, :, :3] if image.shape[2] == 4 else image
        pixels = rgb_image.reshape(-1, 3)
        
        # Simple dominant color extraction using histogram
        dominant_colors = self._extract_dominant_colors(pixels, n_colors=5)
        
        # Edge density analysis
        gray = cv2.cvtColor((rgb_image * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (w * h)
        
        # Content type probabilities (heuristic-based)
        text_prob = self._estimate_text_probability(gray, edges)
        geometric_prob = self._estimate_geometric_probability(edges)
        gradient_prob = self._estimate_gradient_probability(rgb_image)
        
        return ImageMetadata(
            width=w, height=h,
            has_transparency=has_transparency,
            dominant_colors=dominant_colors,
            edge_density=edge_density,
            text_probability=text_prob,
            geometric_probability=geometric_prob,
            gradient_probability=gradient_prob
        )
    
    def _estimate_text_probability(self, gray: np.ndarray, edges: np.ndarray) -> float:
        # Look for horizontal/vertical line patterns typical of text
        kernel_h = np.ones((1, 5), np.uint8)
        kernel_v = np.ones((5, 1), np.uint8)
        
        horizontal_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, kernel_h)
        vertical_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, kernel_v)
        
        h_density = np.sum(horizontal_lines > 0) / edges.size
        v_density = np.sum(vertical_lines > 0) / edges.size
        
        # Text typically has both horizontal and vertical elements
        text_score = min(h_density, v_density) * 10
        return min(1.0, text_score)
    
    def _estimate_geometric_probability(self, edges: np.ndarray) -> float:
        # Use HoughLines to detect straight lines
        lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=30)
        
        if lines is None:
            return 0.0
        
        # More lines = more geometric
        geometric_score = len(lines) / 50.0
        return min(1.0, geometric_score)
    
    def _estimate_gradient_probability(self, image: np.ndarray) -> float:
        # Analyze color transitions to detect gradients
        gray = cv2.cvtColor((image * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
        
        # Compute gradients
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        
        # Look for smooth, consistent gradients rather than sharp edges
        magnitude = np.sqrt(grad_x**2 + grad_y**2)
        
        # Gradients have medium-strength, consistent directional changes
        smooth_gradient_mask = (magnitude > 10) & (magnitude < 50)
        gradient_score = np.sum(smooth_gradient_mask) / magnitude.size
        
        return min(1.0, gradient_score * 5)
    
    def create_edge_map(self, image: np.ndarray, method: str = 'enhanced') -> np.ndarray:
        if len(image.shape) == 3:
            gray = cv2.cvtColor((image * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
        else:
            gray = (image * 255).astype(np.uint8)
        
        if method == 'enhanced':
            return self.enhanced_edge_detection(image)
        elif method == 'canny':
            return cv2.Canny(gray, 50, 150)
        elif method == 'sobel':
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            magnitude = np.sqrt(grad_x**2 + grad_y**2)
            return (magnitude > 30).astype(np.uint8) * 255
        else:
            raise ValueError(f"Unknown edge detection method: {method}")
    
    def enhanced_edge_detection(self, image: np.ndarray) -> np.ndarray:
        """Enhanced edge detection for low-contrast images like Frame 53"""
        gray = cv2.cvtColor((image * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY) if len(image.shape) == 3 else (image * 255).astype(np.uint8)
        
        # Multi-scale edge detection
        edges_multi = np.zeros_like(gray)
        
        # Different scales for comprehensive detection
        for sigma in [0.5, 1.0, 2.0]:
            # Gaussian blur for noise reduction
            blurred = cv2.GaussianBlur(gray, (0, 0), sigma)
            
            # Adaptive thresholding based on local statistics
            mean_val = np.mean(blurred)
            std_val = np.std(blurred)
            
            # Lower thresholds for low-contrast images like Frame 53
            low_thresh = max(5, mean_val - std_val * 0.5)  # More sensitive
            high_thresh = mean_val + std_val * 0.5
            
            edges = cv2.Canny(blurred, low_thresh, high_thresh)
            edges_multi = cv2.bitwise_or(edges_multi, edges)
        
        # Morphological operations to connect broken edges
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        edges_multi = cv2.morphologyEx(edges_multi, cv2.MORPH_CLOSE, kernel)
        
        # Additional edge enhancement for very low contrast areas
        # Use adaptive threshold on the original image
        adaptive_thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        adaptive_edges = cv2.Canny(255 - adaptive_thresh, 30, 60)  # Invert for dark objects
        
        # Combine all edge detection results
        final_edges = cv2.bitwise_or(edges_multi, adaptive_edges)
        
        return final_edges
    
    def segment_colors(self, image: np.ndarray, n_colors: int = 8) -> np.ndarray:
        # Color quantization using simple k-means alternative
        rgb_image = image[:, :, :3] if image.shape[2] == 4 else image
        h, w, c = rgb_image.shape
        
        # Simple color quantization
        quantized = self._quantize_colors(rgb_image, n_colors)
        return quantized
    
    def _extract_dominant_colors(self, pixels: np.ndarray, n_colors: int = 5) -> list:
        # Simple histogram-based dominant color extraction
        unique_pixels = np.unique(pixels.reshape(-1, pixels.shape[-1]), axis=0)
        
        if len(unique_pixels) <= n_colors:
            return unique_pixels.tolist()
        
        # Sample representative colors
        indices = np.linspace(0, len(unique_pixels)-1, n_colors, dtype=int)
        return unique_pixels[indices].tolist()
    
    def _quantize_colors(self, image: np.ndarray, n_colors: int) -> np.ndarray:
        # Simple color quantization
        quantized = np.round(image * (n_colors - 1)) / (n_colors - 1)
        return quantized