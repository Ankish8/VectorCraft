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
        # Enhanced text detection for logos like Frame 53
        kernel_h = np.ones((1, 5), np.uint8)
        kernel_v = np.ones((5, 1), np.uint8)
        
        horizontal_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, kernel_h)
        vertical_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, kernel_v)
        
        h_density = np.sum(horizontal_lines > 0) / edges.size
        v_density = np.sum(vertical_lines > 0) / edges.size
        
        # Look for text regions using connected components
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        text_like_regions = 0
        total_regions = len(contours)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 20:  # Minimum area for text
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                # Text characters typically have certain aspect ratios
                if 0.1 < aspect_ratio < 5.0 and area < 2000:  # Not too large
                    text_like_regions += 1
        
        # Enhanced text score considering character-like regions
        base_score = min(h_density, v_density) * 10
        region_score = (text_like_regions / max(1, total_regions)) * 5
        
        # For logos like Frame 53, text is often in bottom portion
        bottom_half = edges[edges.shape[0]//2:, :]
        bottom_text_density = np.sum(bottom_half > 0) / bottom_half.size
        
        total_score = base_score + region_score + bottom_text_density * 8
        return min(1.0, total_score)
    
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
        # VTracer-inspired hierarchical color clustering
        rgb_image = image[:, :, :3] if image.shape[2] == 4 else image
        h, w, c = rgb_image.shape
        
        # Use VTracer-style hierarchical clustering
        clustered = self.hierarchical_color_clustering(rgb_image, n_colors)
        return clustered
    
    def hierarchical_color_clustering(self, image: np.ndarray, n_colors: int = 8) -> np.ndarray:
        """VTracer-inspired hierarchical clustering for better color separation"""
        h, w, c = image.shape
        
        # Convert to LAB for perceptual clustering (VTracer approach)
        lab_image = cv2.cvtColor((image * 255).astype(np.uint8), cv2.COLOR_RGB2LAB)
        lab_pixels = lab_image.reshape(-1, 3).astype(np.float32)
        
        # Hierarchical clustering with stacking strategy
        clusters = self._hierarchical_cluster_colors(lab_pixels, n_colors)
        
        # Create stacked representation (VTracer's compact approach)
        quantized_lab = clusters.reshape(h, w, 3).astype(np.uint8)
        quantized_rgb = cv2.cvtColor(quantized_lab, cv2.COLOR_LAB2RGB)
        
        return quantized_rgb.astype(np.float32) / 255.0
    
    def _hierarchical_cluster_colors(self, lab_pixels: np.ndarray, n_colors: int) -> np.ndarray:
        """Implement VTracer-style hierarchical clustering"""
        from scipy.cluster.hierarchy import linkage, fcluster
        import numpy as np
        
        # Sample for performance (like VTracer's O(n) approach)
        n_samples = min(10000, len(lab_pixels))
        sample_indices = np.random.choice(len(lab_pixels), n_samples, replace=False)
        sample_pixels = lab_pixels[sample_indices]
        
        # Hierarchical clustering
        try:
            linkage_matrix = linkage(sample_pixels, method='ward')
            cluster_labels = fcluster(linkage_matrix, n_colors, criterion='maxclust')
            
            # Compute cluster centers
            centers = np.zeros((n_colors, 3))
            for i in range(1, n_colors + 1):
                mask = cluster_labels == i
                if np.any(mask):
                    centers[i-1] = np.mean(sample_pixels[mask], axis=0)
            
            # Assign all pixels to nearest cluster center
            distances = np.sqrt(((lab_pixels[:, np.newaxis, :] - centers[np.newaxis, :, :]) ** 2).sum(axis=2))
            assignments = np.argmin(distances, axis=1)
            
            return centers[assignments]
            
        except ImportError:
            # Fallback to k-means if scipy not available
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
            _, labels, centers = cv2.kmeans(lab_pixels, n_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
            return centers[labels.flatten()]
    
    def _extract_dominant_colors(self, pixels: np.ndarray, n_colors: int = 5) -> list:
        # Simple histogram-based dominant color extraction
        unique_pixels = np.unique(pixels.reshape(-1, pixels.shape[-1]), axis=0)
        
        if len(unique_pixels) <= n_colors:
            return unique_pixels.tolist()
        
        # Sample representative colors
        indices = np.linspace(0, len(unique_pixels)-1, n_colors, dtype=int)
        return unique_pixels[indices].tolist()
    
    def _quantize_colors(self, image: np.ndarray, n_colors: int) -> np.ndarray:
        # Use perceptual color quantization for better results
        return self.perceptual_color_quantization(image, n_colors)
    
    def perceptual_color_quantization(self, image: np.ndarray, n_colors: int = 8) -> np.ndarray:
        """Perceptual color quantization preserving important colors"""
        rgb_image = image[:, :, :3] if image.shape[2] == 4 else image
        h, w, c = rgb_image.shape
        
        # Convert to LAB color space for perceptual uniformity
        lab_image = cv2.cvtColor((rgb_image * 255).astype(np.uint8), cv2.COLOR_RGB2LAB)
        lab_pixels = lab_image.reshape(-1, 3).astype(np.float32)
        
        # Use k-means with LAB space
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        _, labels, centers = cv2.kmeans(lab_pixels, n_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        
        # Convert centers back to RGB
        centers_lab = centers.reshape(-1, 1, 3).astype(np.uint8)
        centers_rgb = cv2.cvtColor(centers_lab, cv2.COLOR_LAB2RGB).reshape(-1, 3)
        
        # Reconstruct quantized image
        quantized_lab = centers[labels.flatten()]
        quantized_lab = quantized_lab.reshape(h, w, 3).astype(np.uint8)
        quantized_rgb = cv2.cvtColor(quantized_lab, cv2.COLOR_LAB2RGB)
        
        return quantized_rgb.astype(np.float32) / 255.0

    def adaptive_color_quantization(self, image: np.ndarray, target_similarity: float = 0.95) -> np.ndarray:
        """Adaptive color quantization that preserves visual fidelity"""
        best_n_colors = 8
        best_similarity = 0.0
        best_quantized = None
        
        # Try different numbers of colors
        for n_colors in range(4, 16):
            quantized = self.perceptual_color_quantization(image, n_colors)
            
            # Estimate similarity (simplified)
            mse = np.mean((image - quantized) ** 2)
            similarity = 1.0 / (1.0 + mse * 100)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_quantized = quantized
                best_n_colors = n_colors
                
            # Stop if we reach target similarity
            if similarity >= target_similarity:
                break
        
        print(f"Selected {best_n_colors} colors for similarity {best_similarity:.3f}")
        return best_quantized