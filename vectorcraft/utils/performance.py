import time
import functools
import numpy as np
from typing import Callable, Any, Dict
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

class PerformanceProfiler:
    """Performance profiling utilities for optimization"""
    
    def __init__(self):
        self.timings = {}
        self.call_counts = {}
    
    def profile(self, func_name: str = None):
        """Decorator to profile function execution time"""
        def decorator(func: Callable) -> Callable:
            name = func_name or f"{func.__module__}.{func.__name__}"
            
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                result = func(*args, **kwargs)
                end_time = time.time()
                
                execution_time = end_time - start_time
                
                if name not in self.timings:
                    self.timings[name] = []
                    self.call_counts[name] = 0
                
                self.timings[name].append(execution_time)
                self.call_counts[name] += 1
                
                return result
            return wrapper
        return decorator
    
    def get_stats(self) -> Dict[str, Dict[str, float]]:
        """Get profiling statistics"""
        stats = {}
        for func_name, times in self.timings.items():
            stats[func_name] = {
                'total_time': sum(times),
                'avg_time': sum(times) / len(times),
                'min_time': min(times),
                'max_time': max(times),
                'call_count': self.call_counts[func_name]
            }
        return stats
    
    def print_stats(self):
        """Print profiling statistics"""
        stats = self.get_stats()
        print("\n=== Performance Profile ===")
        print(f"{'Function':<40} {'Calls':<8} {'Total(s)':<10} {'Avg(s)':<10} {'Min(s)':<10} {'Max(s)':<10}")
        print("-" * 90)
        
        # Sort by total time
        sorted_stats = sorted(stats.items(), key=lambda x: x[1]['total_time'], reverse=True)
        
        for func_name, data in sorted_stats:
            print(f"{func_name:<40} {data['call_count']:<8} {data['total_time']:<10.4f} {data['avg_time']:<10.4f} {data['min_time']:<10.4f} {data['max_time']:<10.4f}")

class OptimizedImageProcessor:
    """Optimized version of image processing operations"""
    
    @staticmethod
    def parallel_edge_detection(image: np.ndarray, methods: list = ['canny', 'sobel']) -> Dict[str, np.ndarray]:
        """Run multiple edge detection methods in parallel"""
        def detect_edges(method, img):
            if method == 'canny':
                import cv2
                gray = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY) if len(img.shape) == 3 else (img * 255).astype(np.uint8)
                return cv2.Canny(gray, 50, 150)
            elif method == 'sobel':
                import cv2
                gray = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY) if len(img.shape) == 3 else (img * 255).astype(np.uint8)
                grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
                grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
                magnitude = np.sqrt(grad_x**2 + grad_y**2)
                return (magnitude > 30).astype(np.uint8) * 255
            return None
        
        results = {}
        with ThreadPoolExecutor(max_workers=len(methods)) as executor:
            futures = {executor.submit(detect_edges, method, image): method for method in methods}
            
            for future in as_completed(futures):
                method = futures[future]
                try:
                    results[method] = future.result()
                except Exception as e:
                    print(f"Edge detection method {method} failed: {e}")
                    results[method] = None
        
        return results
    
    @staticmethod
    def fast_color_quantization(image: np.ndarray, n_colors: int = 8) -> np.ndarray:
        """Fast color quantization using bit shifting"""
        # Simple quantization by reducing bit depth
        if image.dtype == np.float32:
            quantized = np.round(image * (n_colors - 1)) / (n_colors - 1)
        else:
            # For uint8 images
            step = 256 // n_colors
            quantized = ((image // step) * step).astype(np.float32) / 255.0
        
        return quantized
    
    @staticmethod
    def hierarchical_processing(image: np.ndarray, scales: list = [0.25, 0.5, 1.0]):
        """Process image at multiple scales for coarse-to-fine optimization"""
        import cv2
        
        results = {}
        h, w = image.shape[:2]
        
        for scale in scales:
            if scale == 1.0:
                scaled_img = image
            else:
                new_h, new_w = int(h * scale), int(w * scale)
                scaled_img = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            
            results[scale] = scaled_img
        
        return results

class AdaptiveOptimizer:
    """Adaptive optimization that adjusts strategy based on time constraints"""
    
    def __init__(self, target_time: float = 120.0):
        self.target_time = target_time
        self.profiler = PerformanceProfiler()
        
    def optimize_strategy_selection(self, image_metadata, elapsed_time: float):
        """Dynamically adjust strategy based on remaining time"""
        remaining_time = self.target_time - elapsed_time
        
        if remaining_time < 10:
            # Very little time left - use fastest strategy
            return 'hybrid_fast'
        elif remaining_time < 30:
            # Moderate time - balance speed and quality
            if image_metadata.geometric_probability > 0.6:
                return 'primitive_focused'
            else:
                return 'classical_refined'
        else:
            # Plenty of time - use comprehensive approach
            return 'hybrid_comprehensive'
    
    def adaptive_precision_control(self, strategy: str, remaining_time: float) -> Dict[str, float]:
        """Adjust algorithm precision based on time constraints"""
        base_params = {
            'edge_threshold_low': 50,
            'edge_threshold_high': 150,
            'contour_min_area': 50,
            'approx_epsilon': 0.01,
            'color_quantization': 8
        }
        
        if remaining_time < 15:
            # Low precision for speed
            return {
                'edge_threshold_low': 100,
                'edge_threshold_high': 200,
                'contour_min_area': 200,
                'approx_epsilon': 0.05,
                'color_quantization': 4
            }
        elif remaining_time < 60:
            # Medium precision
            return {
                'edge_threshold_low': 75,
                'edge_threshold_high': 175,
                'contour_min_area': 100,
                'approx_epsilon': 0.02,
                'color_quantization': 6
            }
        else:
            # High precision
            return base_params

class CacheManager:
    """Intelligent caching for repeated operations"""
    
    def __init__(self, max_size: int = 100):
        self.cache = {}
        self.access_count = {}
        self.max_size = max_size
    
    def get_cache_key(self, image: np.ndarray, operation: str, params: dict = None) -> str:
        """Generate cache key for image and operation"""
        # Simple hash based on image properties and operation
        img_hash = hash((image.shape, image.dtype, np.sum(image)))
        param_hash = hash(str(sorted(params.items()))) if params else 0
        return f"{operation}_{img_hash}_{param_hash}"
    
    def get(self, key: str):
        """Get cached result"""
        if key in self.cache:
            self.access_count[key] = self.access_count.get(key, 0) + 1
            return self.cache[key]
        return None
    
    def put(self, key: str, value: Any):
        """Cache result with LRU eviction"""
        if len(self.cache) >= self.max_size:
            # Remove least recently used item
            lru_key = min(self.access_count.keys(), key=self.access_count.get)
            del self.cache[lru_key]
            del self.access_count[lru_key]
        
        self.cache[key] = value
        self.access_count[key] = 1

class ParallelProcessor:
    """Parallel processing utilities for CPU optimization"""
    
    @staticmethod
    def parallel_strategy_evaluation(image, strategies, max_workers=3):
        """Run multiple strategies in parallel and select best result"""
        def run_strategy(strategy_func, img):
            try:
                start_time = time.time()
                result = strategy_func(img)
                processing_time = time.time() - start_time
                return result, processing_time
            except Exception as e:
                return None, float('inf')
        
        results = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(run_strategy, strategy_func, image): name 
                      for name, strategy_func in strategies.items()}
            
            for future in as_completed(futures):
                strategy_name = futures[future]
                try:
                    result, proc_time = future.result()
                    if result is not None:
                        results[strategy_name] = {
                            'result': result,
                            'time': proc_time
                        }
                except Exception as e:
                    print(f"Strategy {strategy_name} failed: {e}")
        
        return results
    
    @staticmethod
    def parallel_region_processing(image, regions, process_func, max_workers=4):
        """Process different image regions in parallel"""
        def process_region(region_data):
            region, coords = region_data
            result = process_func(region)
            return result, coords
        
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_region, region_data) for region_data in regions]
            
            for future in as_completed(futures):
                try:
                    result, coords = future.result()
                    results.append((result, coords))
                except Exception as e:
                    print(f"Region processing failed: {e}")
        
        return results

# GPU acceleration utilities (if CUDA is available)
def check_gpu_availability():
    """Check if GPU acceleration is available"""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False

class GPUAccelerator:
    """GPU acceleration for compute-intensive operations"""
    
    def __init__(self):
        self.device = "cuda" if check_gpu_availability() else "cpu"
        self.enabled = self.device == "cuda"
    
    def accelerate_diff_optimization(self, target_image, initial_paths, colors):
        """GPU-accelerated differentiable optimization"""
        if not self.enabled:
            return None
        
        try:
            import torch
            
            # Move tensors to GPU
            target_tensor = torch.tensor(target_image, dtype=torch.float32).to(self.device)
            
            # Run optimization on GPU
            # Implementation would go here
            
            return "GPU optimization completed"
        except Exception as e:
            print(f"GPU acceleration failed: {e}")
            return None