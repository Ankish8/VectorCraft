#!/usr/bin/env python3
"""
VectorCraft 2.0 Demo
Demonstrates the hybrid vectorization algorithm on sample images
"""

import os
import time
import numpy as np
from PIL import Image, ImageDraw
import argparse

from vectorcraft import HybridVectorizer

def create_test_images():
    """Create sample test images for demonstration"""
    os.makedirs("test_images", exist_ok=True)
    
    # Test 1: Simple geometric logo
    img = Image.new('RGBA', (200, 200), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw a simple logo with circle and rectangle  
    draw.ellipse([50, 50, 150, 150], fill=(255, 0, 0, 255), outline=(0, 0, 0, 255), width=3)
    draw.rectangle([80, 80, 120, 120], fill=(0, 255, 0, 255))
    draw.text((85, 165), "LOGO", fill=(0, 0, 0, 255))
    
    img.save("test_images/geometric_logo.png")
    print("Created test_images/geometric_logo.png")
    
    # Test 2: Text-based logo
    img = Image.new('RGBA', (300, 100), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    draw.text((10, 20), "VectorCraft", fill=(0, 0, 0, 255))
    draw.text((10, 50), "2.0", fill=(255, 0, 0, 255))
    
    img.save("test_images/text_logo.png")
    print("Created test_images/text_logo.png")
    
    # Test 3: Gradient-like logo (simulated with color bands)
    img = Image.new('RGBA', (200, 200), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Create gradient effect with multiple rectangles
    for i in range(20):
        color_val = int(255 * i / 20)
        draw.rectangle([i*10, 50, (i+1)*10, 150], fill=(color_val, 100, 255-color_val, 255))
    
    img.save("test_images/gradient_logo.png")
    print("Created test_images/gradient_logo.png")
    
    return [
        "test_images/geometric_logo.png",
        "test_images/text_logo.png", 
        "test_images/gradient_logo.png"
    ]

def benchmark_vectorization(image_path: str, vectorizer: HybridVectorizer):
    """Benchmark vectorization performance"""
    print(f"\n=== Benchmarking {os.path.basename(image_path)} ===")
    
    start_time = time.time()
    result = vectorizer.vectorize(image_path)
    total_time = time.time() - start_time
    
    print(f"Processing time: {result.processing_time:.2f}s")
    print(f"Strategy used: {result.strategy_used}")
    print(f"Quality score: {result.quality_score:.3f}")
    print(f"Content type: {result.metadata['content_type']}")
    print(f"Number of elements: {result.metadata['num_elements']}")
    
    # Save result
    output_path = image_path.replace('.png', '_vectorized.svg')
    result.svg_builder.save(output_path)
    print(f"Saved result to: {output_path}")
    
    return result

def compare_strategies(image_path: str):
    """Compare different vectorization strategies"""
    print(f"\n=== Strategy Comparison for {os.path.basename(image_path)} ===")
    
    vectorizer = HybridVectorizer()
    
    # Force different strategies by modifying target time and content analysis
    strategies_to_test = ['hybrid_fast', 'primitive_focused', 'classical_refined']
    
    results = {}
    
    for strategy in strategies_to_test:
        print(f"\nTesting {strategy} strategy...")
        
        # Create a copy of vectorizer for each test
        test_vectorizer = HybridVectorizer()
        
        # Temporarily override strategy selection
        original_select = test_vectorizer._select_strategy
        test_vectorizer._select_strategy = lambda *args: strategy
        
        try:
            start_time = time.time()
            result = test_vectorizer.vectorize(image_path)
            
            results[strategy] = {
                'time': result.processing_time,
                'quality': result.quality_score,
                'elements': result.metadata['num_elements'],
                'result': result
            }
            
            print(f"  Time: {result.processing_time:.2f}s")
            print(f"  Quality: {result.quality_score:.3f}")
            print(f"  Elements: {result.metadata['num_elements']}")
            
            # Save comparison result
            output_path = image_path.replace('.png', f'_{strategy}.svg')
            result.svg_builder.save(output_path)
            
        except Exception as e:
            print(f"  Strategy {strategy} failed: {e}")
            results[strategy] = None
        
        # Restore original method
        test_vectorizer._select_strategy = original_select
    
    # Print comparison summary
    print(f"\n--- Summary for {os.path.basename(image_path)} ---")
    for strategy, result in results.items():
        if result:
            print(f"{strategy:20s}: {result['time']:6.2f}s, quality={result['quality']:.3f}, elements={result['elements']}")
        else:
            print(f"{strategy:20s}: FAILED")

def main():
    parser = argparse.ArgumentParser(description='VectorCraft 2.0 Demo')
    parser.add_argument('--image', type=str, help='Path to image file to vectorize')
    parser.add_argument('--create-tests', action='store_true', help='Create test images')
    parser.add_argument('--benchmark', action='store_true', help='Run benchmark on test images')
    parser.add_argument('--compare', action='store_true', help='Compare different strategies')
    
    args = parser.parse_args()
    
    # Create vectorizer instance
    vectorizer = HybridVectorizer()
    
    if args.create_tests or (not args.image and not args.benchmark and not args.compare):
        print("Creating test images...")
        test_images = create_test_images()
        
        if not args.image and not args.benchmark and not args.compare:
            print("\nRunning basic demo on test images...")
            for img_path in test_images:
                benchmark_vectorization(img_path, vectorizer)
    
    if args.image:
        if os.path.exists(args.image):
            benchmark_vectorization(args.image, vectorizer)
        else:
            print(f"Error: Image file '{args.image}' not found")
    
    if args.benchmark:
        test_images = create_test_images()
        print("\n" + "="*50)
        print("VECTORCRAFT 2.0 BENCHMARK RESULTS")
        print("="*50)
        
        total_time = 0
        for img_path in test_images:
            result = benchmark_vectorization(img_path, vectorizer)
            total_time += result.processing_time
        
        print(f"\nTotal processing time for all images: {total_time:.2f}s")
        print(f"Average time per image: {total_time/len(test_images):.2f}s")
    
    if args.compare:
        test_images = create_test_images()
        print("\n" + "="*50)
        print("STRATEGY COMPARISON")
        print("="*50)
        
        for img_path in test_images:
            compare_strategies(img_path)

if __name__ == "__main__":
    main()