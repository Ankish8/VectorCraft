#!/usr/bin/env python3
"""
Test script for experimental VTracer strategy
"""

import sys
import os
import time
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vectorcraft.core.optimized_vectorizer import OptimizedVectorizer

def test_experimental_strategy():
    """Test the experimental strategy with Frame 54.png"""
    
    print("🧪 Testing Experimental VTracer Strategy")
    print("=" * 50)
    
    # Initialize vectorizer
    print("📊 Initializing OptimizedVectorizer...")
    vectorizer = OptimizedVectorizer(target_time=120.0, enable_gpu=False, enable_caching=True)
    
    # Test image path
    image_path = "/Users/ankish/Downloads/Frame 54.png"
    
    if not os.path.exists(image_path):
        print(f"❌ Test image not found: {image_path}")
        return
    
    print(f"🖼️  Test image: {image_path}")
    
    # Test different strategies for comparison
    strategies = ['vtracer_high_fidelity', 'experimental']
    results = {}
    
    for strategy in strategies:
        print(f"\n🎯 Testing strategy: {strategy}")
        print("-" * 30)
        
        start_time = time.time()
        
        # Override strategy selection
        if hasattr(vectorizer, 'adaptive_optimizer'):
            original_optimize = vectorizer.adaptive_optimizer.optimize_strategy_selection
            vectorizer.adaptive_optimizer.optimize_strategy_selection = lambda metadata, elapsed: strategy
        
        try:
            # Vectorize
            result = vectorizer.vectorize(image_path, target_time=60.0)
            processing_time = time.time() - start_time
            
            # Save result with timestamp
            timestamp = int(time.time())
            output_file = f"output/{timestamp}_{strategy}_test_result.svg"
            os.makedirs("output", exist_ok=True)
            
            if hasattr(result, 'svg_builder') and result.svg_builder:
                result.svg_builder.save(output_file)
                svg_content = result.svg_builder.get_svg_string()
            else:
                with open(output_file, 'w') as f:
                    f.write(result.get_svg_string())
                svg_content = result.get_svg_string()
            
            # Calculate stats
            char_count = len(svg_content)
            num_elements = result.metadata.get('num_elements', 0)
            quality_score = result.quality_score
            
            results[strategy] = {
                'processing_time': processing_time,
                'strategy_used': result.strategy_used,
                'quality_score': quality_score,
                'num_elements': num_elements,
                'char_count': char_count,
                'output_file': output_file,
                'content_type': result.metadata.get('content_type', 'unknown')
            }
            
            print(f"✅ Processing time: {processing_time:.2f}s")
            print(f"📊 Quality score: {quality_score:.3f}")
            print(f"🔢 SVG elements: {num_elements}")
            print(f"📝 SVG character count: {char_count}")
            print(f"💾 Saved to: {output_file}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results[strategy] = {'error': str(e)}
        
        finally:
            # Restore original strategy selection
            if hasattr(vectorizer, 'adaptive_optimizer'):
                vectorizer.adaptive_optimizer.optimize_strategy_selection = original_optimize
    
    # Compare results
    print("\n🏆 COMPARISON RESULTS")
    print("=" * 50)
    
    if 'vtracer_high_fidelity' in results and 'experimental' in results:
        baseline = results['vtracer_high_fidelity']
        experimental = results['experimental']
        
        if 'error' not in baseline and 'error' not in experimental:
            print(f"Processing Time:")
            print(f"  Baseline:     {baseline['processing_time']:.2f}s")
            print(f"  Experimental: {experimental['processing_time']:.2f}s")
            print(f"  Improvement:  {baseline['processing_time'] - experimental['processing_time']:.2f}s")
            
            print(f"\nQuality Score:")
            print(f"  Baseline:     {baseline['quality_score']:.3f}")
            print(f"  Experimental: {experimental['quality_score']:.3f}")
            print(f"  Improvement:  {experimental['quality_score'] - baseline['quality_score']:.3f}")
            
            print(f"\nSVG Elements:")
            print(f"  Baseline:     {baseline['num_elements']}")
            print(f"  Experimental: {experimental['num_elements']}")
            print(f"  Difference:   {experimental['num_elements'] - baseline['num_elements']}")
            
            print(f"\nComplexity (characters):")
            print(f"  Baseline:     {baseline['char_count']}")
            print(f"  Experimental: {experimental['char_count']}")
            print(f"  Improvement:  {experimental['char_count'] - baseline['char_count']}")
            
            # Determine if experimental is better
            improvements = 0
            if experimental['quality_score'] > baseline['quality_score']:
                improvements += 1
            if experimental['num_elements'] >= baseline['num_elements']:
                improvements += 1
            if experimental['processing_time'] <= baseline['processing_time'] * 1.1:  # Allow 10% slower
                improvements += 1
            
            print(f"\n🎯 VERDICT:")
            if improvements >= 2:
                print("✅ Experimental strategy shows improvement!")
            else:
                print("⚠️  Experimental strategy needs more work")
            
            print(f"\nOutput files created:")
            for strategy, result in results.items():
                if 'output_file' in result:
                    print(f"  {strategy}: {result['output_file']}")
    
    print("\n🧪 Test completed!")
    return results

if __name__ == '__main__':
    test_experimental_strategy()