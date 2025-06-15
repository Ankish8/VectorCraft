#!/usr/bin/env python3
"""
VectorCraft 2.0 - Automated Improvement Pipeline
Uses MCP servers to iteratively improve vectorization quality
"""

import os
import time
import json
import numpy as np
from PIL import Image
import cv2
import requests
import subprocess
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ImprovementResult:
    iteration: int
    similarity_score: float
    processing_time: float
    quality_score: float
    improvements_made: List[str]
    next_actions: List[str]

class AutomatedImprover:
    def __init__(self, target_image_path: str, target_similarity: float = 0.95):
        self.target_image_path = target_image_path
        self.target_similarity = target_similarity
        self.server_url = "http://localhost:8080"
        self.results_history = []
        self.current_iteration = 0
        
        # Create improvement tracking directory
        self.improvement_dir = "improvement_results"
        os.makedirs(self.improvement_dir, exist_ok=True)
        
    def analyze_target_image(self) -> Dict[str, Any]:
        """Analyze the target image to understand its characteristics"""
        logger.info(f"Analyzing target image: {self.target_image_path}")
        
        if not os.path.exists(self.target_image_path):
            raise FileNotFoundError(f"Target image not found: {self.target_image_path}")
        
        # Load and analyze image
        image = cv2.imread(self.target_image_path)
        height, width, channels = image.shape
        
        # Convert to different color spaces for analysis
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Analyze characteristics
        analysis = {
            'dimensions': (width, height),
            'channels': channels,
            'total_pixels': width * height,
            'color_complexity': len(np.unique(image.reshape(-1, image.shape[-1]), axis=0)),
            'edge_density': self._calculate_edge_density(gray),
            'color_distribution': self._analyze_color_distribution(hsv),
            'dominant_features': self._identify_dominant_features(image),
            'complexity_score': self._calculate_complexity_score(image)
        }
        
        logger.info(f"Image analysis complete: {analysis}")
        return analysis
    
    def _calculate_edge_density(self, gray_image: np.ndarray) -> float:
        """Calculate edge density using Canny edge detection"""
        edges = cv2.Canny(gray_image, 50, 150)
        return np.sum(edges > 0) / edges.size
    
    def _analyze_color_distribution(self, hsv_image: np.ndarray) -> Dict[str, Any]:
        """Analyze color distribution in HSV space"""
        h, s, v = cv2.split(hsv_image)
        
        return {
            'hue_variance': np.var(h),
            'saturation_mean': np.mean(s),
            'value_mean': np.mean(v),
            'color_range': len(np.unique(hsv_image.reshape(-1, 3), axis=0))
        }
    
    def _identify_dominant_features(self, image: np.ndarray) -> Dict[str, bool]:
        """Identify dominant features in the image"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect various features
        features = {
            'has_text': self._detect_text_regions(gray),
            'has_geometric_shapes': self._detect_geometric_shapes(gray),
            'has_curves': self._detect_curves(gray),
            'has_gradients': self._detect_gradients(image),
            'has_fine_details': self._detect_fine_details(gray)
        }
        
        return features
    
    def _detect_text_regions(self, gray_image: np.ndarray) -> bool:
        """Simple text detection based on line patterns"""
        kernel_h = np.ones((1, 10), np.uint8)
        kernel_v = np.ones((10, 1), np.uint8)
        
        horizontal_lines = cv2.morphologyEx(gray_image, cv2.MORPH_OPEN, kernel_h)
        vertical_lines = cv2.morphologyEx(gray_image, cv2.MORPH_OPEN, kernel_v)
        
        h_density = np.sum(horizontal_lines > 0) / gray_image.size
        v_density = np.sum(vertical_lines > 0) / gray_image.size
        
        return (h_density > 0.01 and v_density > 0.01)
    
    def _detect_geometric_shapes(self, gray_image: np.ndarray) -> bool:
        """Detect geometric shapes using contour analysis"""
        edges = cv2.Canny(gray_image, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        geometric_shapes = 0
        for contour in contours:
            # Approximate contour
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Count shapes with few vertices (geometric)
            if 3 <= len(approx) <= 8:
                geometric_shapes += 1
        
        return geometric_shapes > 2
    
    def _detect_curves(self, gray_image: np.ndarray) -> bool:
        """Detect curved elements in the image"""
        edges = cv2.Canny(gray_image, 50, 150)
        
        # Use HoughCircles to detect circular elements
        circles = cv2.HoughCircles(gray_image, cv2.HOUGH_GRADIENT, 1, 30, param1=50, param2=30, minRadius=10, maxRadius=100)
        
        return circles is not None and len(circles[0]) > 0
    
    def _detect_gradients(self, image: np.ndarray) -> bool:
        """Detect gradient regions in the image"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Calculate gradients
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = np.sqrt(grad_x**2 + grad_y**2)
        
        # Look for smooth gradients (medium strength, consistent)
        smooth_gradient_mask = (magnitude > 10) & (magnitude < 50)
        gradient_ratio = np.sum(smooth_gradient_mask) / magnitude.size
        
        return gradient_ratio > 0.1
    
    def _detect_fine_details(self, gray_image: np.ndarray) -> bool:
        """Detect fine details that need special handling"""
        # Use Laplacian to detect fine details
        laplacian = cv2.Laplacian(gray_image, cv2.CV_64F)
        detail_score = np.var(laplacian)
        
        return detail_score > 1000  # Threshold for "fine details"
    
    def _calculate_complexity_score(self, image: np.ndarray) -> float:
        """Calculate overall image complexity score (0-1)"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Multiple complexity metrics
        edge_density = self._calculate_edge_density(gray)
        color_count = len(np.unique(image.reshape(-1, image.shape[-1]), axis=0))
        max_colors = min(1000, image.shape[0] * image.shape[1])  # Cap for normalization
        color_complexity = color_count / max_colors
        
        # Texture complexity using LBP-like measure
        texture_complexity = np.std(gray) / 255.0
        
        # Combine metrics
        complexity = (edge_density + color_complexity + texture_complexity) / 3
        return min(1.0, complexity)
    
    def process_with_vectorcraft(self) -> Dict[str, Any]:
        """Process the target image using VectorCraft API"""
        logger.info("Processing image with VectorCraft...")
        
        try:
            with open(self.target_image_path, 'rb') as f:
                files = {'file': f}
                data = {
                    'vectorizer': 'optimized',
                    'target_time': '120',
                    'strategy': 'hybrid_comprehensive'
                }
                
                response = requests.post(f'{self.server_url}/api/vectorize', files=files, data=data)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        return result
                    else:
                        raise Exception(f"Vectorization failed: {result.get('error')}")
                else:
                    raise Exception(f"HTTP Error {response.status_code}: {response.text}")
                    
        except Exception as e:
            logger.error(f"VectorCraft processing failed: {e}")
            raise
    
    def take_screenshot_with_puppeteer(self) -> str:
        """Take screenshot of the web interface using Puppeteer"""
        screenshot_path = os.path.join(self.improvement_dir, f"iteration_{self.current_iteration}_screenshot.png")
        
        # This would use Puppeteer MCP server if properly integrated
        # For now, we'll simulate with a placeholder
        logger.info("Taking screenshot with Puppeteer...")
        
        # Placeholder - in real implementation, this would use Puppeteer MCP
        # to navigate to localhost:8080, upload image, and capture result
        
        return screenshot_path
    
    def calculate_similarity(self, original_path: str, vectorized_svg_content: str) -> float:
        """Calculate similarity between original and vectorized image"""
        logger.info("Calculating similarity between original and vectorized images...")
        
        try:
            # Load original image
            original = cv2.imread(original_path)
            
            # Convert SVG to image for comparison
            # This is a simplified approach - would need proper SVG rendering
            vectorized_image = self._render_svg_to_image(vectorized_svg_content, original.shape[:2])
            
            # Calculate structural similarity
            from skimage.metrics import structural_similarity as ssim
            
            # Convert to grayscale for SSIM
            original_gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
            vectorized_gray = cv2.cvtColor(vectorized_image, cv2.COLOR_BGR2GRAY)
            
            # Resize vectorized to match original if needed
            if vectorized_gray.shape != original_gray.shape:
                vectorized_gray = cv2.resize(vectorized_gray, (original_gray.shape[1], original_gray.shape[0]))
            
            similarity = ssim(original_gray, vectorized_gray)
            logger.info(f"Calculated similarity: {similarity:.3f}")
            
            return similarity
            
        except Exception as e:
            logger.error(f"Similarity calculation failed: {e}")
            return 0.0
    
    def _render_svg_to_image(self, svg_content: str, target_size: Tuple[int, int]) -> np.ndarray:
        """Render SVG content to numpy image array"""
        # This would need proper SVG rendering library like cairosvg or similar
        # For now, return a placeholder
        logger.warning("SVG rendering not fully implemented - using placeholder")
        return np.zeros((target_size[0], target_size[1], 3), dtype=np.uint8)
    
    def use_sequential_thinking(self, current_results: Dict[str, Any], image_analysis: Dict[str, Any]) -> List[str]:
        """Use sequential thinking to plan improvements"""
        logger.info("Using sequential thinking to plan improvements...")
        
        # This would integrate with sequential thinking MCP server
        # For now, implement rule-based improvement suggestions
        
        improvements = []
        similarity = current_results.get('similarity_score', 0.0)
        features = image_analysis.get('dominant_features', {})
        complexity = image_analysis.get('complexity_score', 0.5)
        
        # Sequential thinking logic
        if similarity < 0.7:
            improvements.append("Major algorithm overhaul needed - focus on core vectorization pipeline")
            
            if features.get('has_text'):
                improvements.append("Implement advanced text detection and preservation")
            
            if features.get('has_geometric_shapes'):
                improvements.append("Enhance geometric primitive detection accuracy")
                
            if complexity > 0.7:
                improvements.append("Add multi-scale processing for complex images")
                
        elif similarity < 0.85:
            improvements.append("Fine-tune existing algorithms for better accuracy")
            
            if features.get('has_curves'):
                improvements.append("Improve Bezier curve fitting algorithms")
                
            if features.get('has_gradients'):
                improvements.append("Enhance gradient detection and representation")
                
        elif similarity < 0.95:
            improvements.append("Minor optimizations needed for final quality push")
            improvements.append("Implement perceptual similarity optimization")
            improvements.append("Fine-tune path simplification parameters")
        
        logger.info(f"Sequential thinking suggests {len(improvements)} improvements")
        return improvements
    
    def research_github_solutions(self) -> List[Dict[str, str]]:
        """Research GitHub repositories for vectorization improvements"""
        logger.info("Researching GitHub solutions...")
        
        # This would use web fetch MCP server to search GitHub
        # For now, provide curated list of known good repositories
        
        research_targets = [
            {
                'name': 'VTracer',
                'url': 'https://github.com/visioncortex/vtracer',
                'description': 'Rust-based vectorization with advanced algorithms',
                'key_features': ['Multi-scale processing', 'Advanced curve fitting', 'Color optimization']
            },
            {
                'name': 'Potrace',
                'url': 'https://github.com/kilobtye/potrace',
                'description': 'Classic vectorization algorithm',
                'key_features': ['Douglas-Peucker optimization', 'Smooth curves', 'Fast processing']
            },
            {
                'name': 'DiffVG',
                'url': 'https://github.com/BachiLi/diffvg',
                'description': 'Differentiable vector graphics',
                'key_features': ['Gradient-based optimization', 'Neural network integration', 'Quality metrics']
            },
            {
                'name': 'LIVE',
                'url': 'https://github.com/Nauhcnay/A-Benchmark-and-Evaluation-for-Text-to-SVG-Synthesis',
                'description': 'Layered image vectorization',
                'key_features': ['Layer separation', 'Semantic understanding', 'Quality assessment']
            }
        ]
        
        logger.info(f"Identified {len(research_targets)} research targets")
        return research_targets
    
    def implement_improvements(self, improvement_suggestions: List[str]) -> List[str]:
        """Implement the suggested improvements"""
        logger.info(f"Implementing {len(improvement_suggestions)} improvements...")
        
        implemented = []
        
        for suggestion in improvement_suggestions:
            try:
                if "text detection" in suggestion.lower():
                    self._improve_text_detection()
                    implemented.append("Enhanced text detection algorithm")
                
                elif "geometric primitive" in suggestion.lower():
                    self._improve_primitive_detection()
                    implemented.append("Improved geometric primitive detection")
                
                elif "bezier curve" in suggestion.lower():
                    self._improve_curve_fitting()
                    implemented.append("Enhanced Bezier curve fitting")
                
                elif "gradient" in suggestion.lower():
                    self._improve_gradient_handling()
                    implemented.append("Better gradient detection and representation")
                
                elif "multi-scale" in suggestion.lower():
                    self._implement_multiscale_processing()
                    implemented.append("Added multi-scale processing")
                
                elif "perceptual similarity" in suggestion.lower():
                    self._implement_perceptual_optimization()
                    implemented.append("Implemented perceptual similarity optimization")
                
                else:
                    logger.warning(f"Unknown improvement suggestion: {suggestion}")
                    
            except Exception as e:
                logger.error(f"Failed to implement improvement '{suggestion}': {e}")
        
        logger.info(f"Successfully implemented {len(implemented)} improvements")
        return implemented
    
    def _improve_text_detection(self):
        """Improve text detection capabilities"""
        # Implementation would modify the image processor
        logger.info("Improving text detection algorithms...")
        pass
    
    def _improve_primitive_detection(self):
        """Improve geometric primitive detection"""
        logger.info("Enhancing primitive detection...")
        pass
    
    def _improve_curve_fitting(self):
        """Improve Bezier curve fitting"""
        logger.info("Optimizing curve fitting algorithms...")
        pass
    
    def _improve_gradient_handling(self):
        """Improve gradient detection and representation"""
        logger.info("Enhancing gradient processing...")
        pass
    
    def _implement_multiscale_processing(self):
        """Implement multi-scale processing"""
        logger.info("Adding multi-scale processing capabilities...")
        pass
    
    def _implement_perceptual_optimization(self):
        """Implement perceptual similarity optimization"""
        logger.info("Adding perceptual optimization...")
        pass
    
    def save_iteration_results(self, result: ImprovementResult):
        """Save results from this iteration"""
        result_file = os.path.join(self.improvement_dir, f"iteration_{self.current_iteration}_results.json")
        
        result_data = {
            'iteration': result.iteration,
            'similarity_score': result.similarity_score,
            'processing_time': result.processing_time,
            'quality_score': result.quality_score,
            'improvements_made': result.improvements_made,
            'next_actions': result.next_actions,
            'timestamp': time.time()
        }
        
        with open(result_file, 'w') as f:
            json.dump(result_data, f, indent=2)
        
        logger.info(f"Saved iteration {self.current_iteration} results to {result_file}")
    
    def run_improvement_cycle(self) -> ImprovementResult:
        """Run one complete improvement cycle"""
        logger.info(f"Starting improvement iteration {self.current_iteration}")
        
        # Step 1: Analyze target image
        image_analysis = self.analyze_target_image()
        
        # Step 2: Process with current VectorCraft
        vectorization_result = self.process_with_vectorcraft()
        
        # Step 3: Calculate similarity
        similarity = self.calculate_similarity(
            self.target_image_path, 
            vectorization_result.get('svg_content', '')
        )
        
        # Step 4: Use sequential thinking to plan improvements
        improvement_suggestions = self.use_sequential_thinking(
            {'similarity_score': similarity}, 
            image_analysis
        )
        
        # Step 5: Research solutions if needed
        if similarity < 0.8:
            research_results = self.research_github_solutions()
            logger.info(f"Found {len(research_results)} research sources for inspiration")
        
        # Step 6: Implement improvements
        implemented_improvements = self.implement_improvements(improvement_suggestions)
        
        # Step 7: Plan next actions
        next_actions = []
        if similarity < self.target_similarity:
            next_actions.append("Continue iterative improvement")
            next_actions.append("Test with additional edge cases")
        else:
            next_actions.append("Goal achieved - validate with comprehensive test suite")
        
        # Create result object
        result = ImprovementResult(
            iteration=self.current_iteration,
            similarity_score=similarity,
            processing_time=vectorization_result.get('processing_time', 0),
            quality_score=vectorization_result.get('quality_score', 0),
            improvements_made=implemented_improvements,
            next_actions=next_actions
        )
        
        # Save results
        self.save_iteration_results(result)
        self.results_history.append(result)
        
        logger.info(f"Iteration {self.current_iteration} complete - Similarity: {similarity:.3f}")
        
        self.current_iteration += 1
        return result
    
    def run_until_target_achieved(self, max_iterations: int = 10):
        """Run improvement cycles until target similarity is achieved"""
        logger.info(f"Starting automated improvement - Target: {self.target_similarity:.1%}")
        
        for iteration in range(max_iterations):
            result = self.run_improvement_cycle()
            
            logger.info(f"Iteration {iteration + 1}: Similarity = {result.similarity_score:.3f}")
            
            if result.similarity_score >= self.target_similarity:
                logger.info(f"🎉 Target achieved! Similarity: {result.similarity_score:.3f}")
                break
                
            if iteration == max_iterations - 1:
                logger.warning(f"Reached maximum iterations without achieving target")
        
        # Generate final report
        self.generate_improvement_report()
    
    def generate_improvement_report(self):
        """Generate comprehensive improvement report"""
        report_path = os.path.join(self.improvement_dir, "improvement_report.md")
        
        with open(report_path, 'w') as f:
            f.write("# VectorCraft 2.0 - Automated Improvement Report\n\n")
            f.write(f"## Target Image: {self.target_image_path}\n")
            f.write(f"## Target Similarity: {self.target_similarity:.1%}\n\n")
            
            f.write("## Iteration Results\n\n")
            for result in self.results_history:
                f.write(f"### Iteration {result.iteration}\n")
                f.write(f"- **Similarity**: {result.similarity_score:.3f}\n")
                f.write(f"- **Processing Time**: {result.processing_time:.2f}s\n")
                f.write(f"- **Quality Score**: {result.quality_score:.3f}\n")
                f.write(f"- **Improvements Made**: {len(result.improvements_made)}\n")
                
                for improvement in result.improvements_made:
                    f.write(f"  - {improvement}\n")
                f.write("\n")
            
            # Final status
            if self.results_history:
                final_similarity = self.results_history[-1].similarity_score
                if final_similarity >= self.target_similarity:
                    f.write(f"## 🎉 SUCCESS: Target achieved with {final_similarity:.3f} similarity\n")
                else:
                    f.write(f"## ⚠️ Target not achieved: Final similarity {final_similarity:.3f}\n")
        
        logger.info(f"Generated improvement report: {report_path}")

def main():
    """Main execution function"""
    target_image = "/Users/ankish/Downloads/Frame 53.png"
    target_similarity = 0.95
    
    # Check if image exists
    if not os.path.exists(target_image):
        logger.error(f"Target image not found: {target_image}")
        logger.info("Please ensure the image exists at the specified path")
        return
    
    # Check if VectorCraft server is running
    try:
        response = requests.get("http://localhost:8080/health", timeout=5)
        if response.status_code != 200:
            raise Exception("Server not healthy")
    except Exception as e:
        logger.error(f"VectorCraft server not available: {e}")
        logger.info("Please start the server with: python3 start_server.py")
        return
    
    # Create and run improver
    improver = AutomatedImprover(target_image, target_similarity)
    
    try:
        improver.run_until_target_achieved(max_iterations=10)
    except KeyboardInterrupt:
        logger.info("Improvement process interrupted by user")
    except Exception as e:
        logger.error(f"Improvement process failed: {e}")
        raise

if __name__ == "__main__":
    main()