#!/usr/bin/env python3
"""
Quick visual comparison of strategies
"""

import sys
import os
import time

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vectorcraft.core.optimized_vectorizer import OptimizedVectorizer

def compare_strategies():
    """Compare VTracer vs Experimental output visually"""
    
    print("🔍 Visual Comparison: VTracer vs Experimental")
    print("=" * 50)
    
    vectorizer = OptimizedVectorizer(target_time=60.0, enable_gpu=False, enable_caching=True)
    image_path = "/Users/ankish/Downloads/Frame 54.png"
    
    if not os.path.exists(image_path):
        print(f"❌ Test image not found: {image_path}")
        return
    
    strategies = ['vtracer_high_fidelity', 'experimental']
    
    for strategy in strategies:
        print(f"\n🎯 Processing with {strategy}...")
        
        # Override strategy selection
        if hasattr(vectorizer, 'adaptive_optimizer'):
            original_optimize = vectorizer.adaptive_optimizer.optimize_strategy_selection
            vectorizer.adaptive_optimizer.optimize_strategy_selection = lambda metadata, elapsed: strategy
        
        try:
            start_time = time.time()
            result = vectorizer.vectorize(image_path, target_time=30.0)
            processing_time = time.time() - start_time
            
            # Get SVG content
            if hasattr(result, 'svg_builder') and result.svg_builder:
                svg_content = result.svg_builder.get_svg_string()
            else:
                svg_content = result.get_svg_string()
            
            # Save for comparison
            output_file = f"output/compare_{strategy}.svg"
            with open(output_file, 'w') as f:
                f.write(svg_content)
            
            # Count elements and paths
            path_count = svg_content.count('<path')
            circle_count = svg_content.count('<circle')
            rect_count = svg_content.count('<rect')
            total_elements = path_count + circle_count + rect_count
            
            print(f"  ✓ Processing time: {processing_time:.2f}s")
            print(f"  📊 Quality score: {result.quality_score:.3f}")
            print(f"  🔢 Total elements: {total_elements}")
            print(f"    - Paths: {path_count}")
            print(f"    - Circles: {circle_count}")
            print(f"    - Rectangles: {rect_count}")
            print(f"  📝 SVG size: {len(svg_content)} characters")
            print(f"  💾 Saved to: {output_file}")
            
            # Show first few lines of SVG for inspection
            lines = svg_content.split('\n')[:5]
            print(f"  📄 First lines:")
            for line in lines:
                print(f"    {line[:80]}...")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        finally:
            # Restore original strategy selection
            if hasattr(vectorizer, 'adaptive_optimizer'):
                vectorizer.adaptive_optimizer.optimize_strategy_selection = original_optimize
    
    print(f"\n🔍 COMPARISON COMPLETE")
    print("Check the SVG files in your browser to see visual differences")

if __name__ == '__main__':
    compare_strategies()