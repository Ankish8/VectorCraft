#!/usr/bin/env python3
"""
Performance comparison between standard and optimized vectorizers
"""

import time
import numpy as np
from PIL import Image, ImageDraw
import os
from typing import List, Tuple

from vectorcraft.core.hybrid_vectorizer import HybridVectorizer
from vectorcraft.core.optimized_vectorizer import OptimizedVectorizer

def create_complex_test_image(filename: str, size: Tuple[int, int] = (400, 400)):
    """Create a more complex test image for performance testing"""
    img = Image.new('RGBA', size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Multiple geometric shapes
    draw.ellipse([50, 50, 150, 150], fill=(255, 0, 0, 255), outline=(0, 0, 0, 255), width=2)
    draw.rectangle([200, 50, 350, 200], fill=(0, 255, 0, 255), outline=(0, 0, 0, 255), width=2)
    draw.polygon([(100, 250), (150, 300), (200, 250), (175, 350), (125, 350)], 
                fill=(0, 0, 255, 255), outline=(0, 0, 0, 255), width=2)
    
    # Some text
    try:
        draw.text((50, 350), "COMPLEX LOGO", fill=(0, 0, 0, 255))
    except:
        pass  # In case font is not available
    
    # Gradient-like effect
    for i in range(20):
        color_val = int(255 * i / 20)
        draw.rectangle([i*10, 10, (i+1)*10, 40], fill=(color_val, 100, 255-color_val, 255))
    
    # Some small details
    for i in range(10):
        for j in range(10):
            if (i + j) % 2 == 0:
                draw.rectangle([300 + i*5, 250 + j*5, 305 + i*5, 255 + j*5], 
                             fill=(128, 128, 128, 255))
    
    img.save(filename)
    return filename

def benchmark_vectorizer(vectorizer, image_path: str, target_time: float = 60.0, runs: int = 3):
    """Benchmark a vectorizer with multiple runs"""
    times = []
    qualities = []
    element_counts = []
    
    print(f"Running {runs} benchmarks on {vectorizer.__class__.__name__}...")
    
    for run in range(runs):
        print(f"  Run {run + 1}/{runs}...")
        
        start_time = time.time()
        result = vectorizer.vectorize(image_path, target_time=target_time)
        total_time = time.time() - start_time
        
        times.append(result.processing_time)
        qualities.append(result.quality_score)
        element_counts.append(result.metadata['num_elements'])
        
        print(f"    Time: {result.processing_time:.2f}s, Quality: {result.quality_score:.3f}, Elements: {result.metadata['num_elements']}")
    
    return {
        'avg_time': np.mean(times),
        'std_time': np.std(times),
        'min_time': np.min(times),
        'max_time': np.max(times),
        'avg_quality': np.mean(qualities),
        'avg_elements': np.mean(element_counts),
        'all_times': times,
        'all_qualities': qualities,
        'all_elements': element_counts
    }

def compare_vectorizers(image_path: str, target_times: List[float] = [30, 60, 120]):
    """Compare standard vs optimized vectorizers at different time targets"""
    
    print("=" * 60)
    print("VECTORIZER PERFORMANCE COMPARISON")
    print("=" * 60)
    print(f"Test image: {image_path}")
    
    # Initialize vectorizers
    standard_vectorizer = HybridVectorizer()
    optimized_vectorizer = OptimizedVectorizer()
    
    results = {}
    
    for target_time in target_times:
        print(f"\n--- Target Time: {target_time}s ---")
        
        # Benchmark standard vectorizer
        print("Testing Standard Vectorizer...")
        standard_results = benchmark_vectorizer(standard_vectorizer, image_path, target_time, runs=2)
        
        # Benchmark optimized vectorizer
        print("Testing Optimized Vectorizer...")
        optimized_results = benchmark_vectorizer(optimized_vectorizer, image_path, target_time, runs=2)
        
        results[target_time] = {
            'standard': standard_results,
            'optimized': optimized_results
        }
        
        # Print comparison
        print(f"\nComparison for {target_time}s target:")
        print(f"{'Metric':<20} {'Standard':<15} {'Optimized':<15} {'Improvement':<15}")
        print("-" * 65)
        
        # Time comparison
        standard_time = standard_results['avg_time']
        optimized_time = optimized_results['avg_time']
        time_improvement = ((standard_time - optimized_time) / standard_time) * 100
        print(f"{'Avg Time (s)':<20} {standard_time:<15.2f} {optimized_time:<15.2f} {time_improvement:<15.1f}%")
        
        # Quality comparison
        standard_quality = standard_results['avg_quality']
        optimized_quality = optimized_results['avg_quality']
        quality_change = ((optimized_quality - standard_quality) / standard_quality) * 100
        print(f"{'Avg Quality':<20} {standard_quality:<15.3f} {optimized_quality:<15.3f} {quality_change:<15.1f}%")
        
        # Element count comparison
        standard_elements = standard_results['avg_elements']
        optimized_elements = optimized_results['avg_elements']
        elements_change = ((optimized_elements - standard_elements) / standard_elements) * 100
        print(f"{'Avg Elements':<20} {standard_elements:<15.1f} {optimized_elements:<15.1f} {elements_change:<15.1f}%")
    
    return results

def stress_test(vectorizer, base_image_path: str, sizes: List[Tuple[int, int]] = [(200, 200), (400, 400), (800, 800)]):
    """Stress test with different image sizes"""
    print(f"\n--- Stress Test: {vectorizer.__class__.__name__} ---")
    
    results = {}
    
    for size in sizes:
        print(f"Testing size {size[0]}x{size[1]}...")
        
        # Create test image at this size
        test_image_path = f"stress_test_{size[0]}x{size[1]}.png"
        create_complex_test_image(test_image_path, size)
        
        try:
            start_time = time.time()
            result = vectorizer.vectorize(test_image_path, target_time=60.0)
            processing_time = time.time() - start_time
            
            pixels = size[0] * size[1]
            results[size] = {
                'time': result.processing_time,
                'quality': result.quality_score,
                'elements': result.metadata['num_elements'],
                'pixels': pixels,
                'time_per_pixel': result.processing_time / pixels * 1000000  # microseconds per pixel
            }
            
            print(f"  Time: {result.processing_time:.2f}s")
            print(f"  Quality: {result.quality_score:.3f}")
            print(f"  Elements: {result.metadata['num_elements']}")
            print(f"  Time per megapixel: {result.processing_time / (pixels/1000000):.2f}s")
            
        except Exception as e:
            print(f"  Failed: {e}")
            results[size] = None
        
        # Cleanup
        if os.path.exists(test_image_path):
            os.remove(test_image_path)
    
    return results

def main():
    print("VectorCraft 2.0 Performance Testing Suite")
    print("==========================================")
    
    # Create test images
    os.makedirs("perf_test_images", exist_ok=True)
    
    # Create different complexity test images
    simple_image = create_complex_test_image("perf_test_images/simple.png", (200, 200))
    medium_image = create_complex_test_image("perf_test_images/medium.png", (400, 400))
    complex_image = create_complex_test_image("perf_test_images/complex.png", (600, 600))
    
    test_images = [
        ("Simple (200x200)", simple_image),
        ("Medium (400x400)", medium_image),
        ("Complex (600x600)", complex_image)
    ]
    
    # Run comparisons
    all_results = {}
    
    for name, image_path in test_images:
        print(f"\n{'='*60}")
        print(f"Testing: {name}")
        print(f"{'='*60}")
        
        results = compare_vectorizers(image_path, target_times=[30, 60, 120])
        all_results[name] = results
    
    # Stress test
    print(f"\n{'='*60}")
    print("STRESS TESTING")
    print(f"{'='*60}")
    
    standard_vectorizer = HybridVectorizer()
    optimized_vectorizer = OptimizedVectorizer()
    
    print("\nStandard Vectorizer Stress Test:")
    standard_stress = stress_test(standard_vectorizer, simple_image)
    
    print("\nOptimized Vectorizer Stress Test:")
    optimized_stress = stress_test(optimized_vectorizer, simple_image)
    
    # Summary
    print(f"\n{'='*60}")
    print("PERFORMANCE SUMMARY")
    print(f"{'='*60}")
    
    print("\nKey Findings:")
    
    # Calculate overall performance improvements
    total_standard_time = 0
    total_optimized_time = 0
    count = 0
    
    for test_name, test_results in all_results.items():
        for target_time, comparison in test_results.items():
            total_standard_time += comparison['standard']['avg_time']
            total_optimized_time += comparison['optimized']['avg_time']
            count += 1
    
    if count > 0:
        overall_improvement = ((total_standard_time - total_optimized_time) / total_standard_time) * 100
        print(f"• Overall average speed improvement: {overall_improvement:.1f}%")
        print(f"• Average processing time - Standard: {total_standard_time/count:.2f}s")
        print(f"• Average processing time - Optimized: {total_optimized_time/count:.2f}s")
    
    # Check if target times are being met
    print(f"\nTarget Time Compliance:")
    for test_name, test_results in all_results.items():
        print(f"\n{test_name}:")
        for target_time, comparison in test_results.items():
            standard_met = comparison['standard']['avg_time'] <= target_time
            optimized_met = comparison['optimized']['avg_time'] <= target_time
            print(f"  {target_time}s target: Standard {'✓' if standard_met else '✗'}, Optimized {'✓' if optimized_met else '✗'}")
    
    print(f"\n🎉 Performance testing complete!")
    print(f"Results saved to perf_test_images/ directory")

if __name__ == "__main__":
    main()