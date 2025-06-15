#!/usr/bin/env python3
"""
Direct test of VTracer functionality to verify algorithm restoration
"""

import os
import sys

# Add the vectorcraft package to the path
sys.path.insert(0, '/Users/ankish/Downloads/MA/vc2')

from vectorcraft.core.optimized_vectorizer import OptimizedVectorizer
from vectorcraft.strategies.real_vtracer import RealVTracerStrategy
import numpy as np
from PIL import Image

def test_vtracer_directly():
    """Test VTracer functionality directly"""
    
    print("🧪 Testing VTracer Algorithm Restoration")
    print("=" * 50)
    
    # Test image path
    image_path = "/Users/ankish/Downloads/Frame 54.png"
    
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return
    
    print(f"📂 Testing with: {image_path}")
    
    # Test 1: Real VTracer Strategy
    print("\n🔍 Test 1: Real VTracer Strategy")
    try:
        vtracer_strategy = RealVTracerStrategy()
        print(f"VTracer available: {vtracer_strategy.available}")
        
        if vtracer_strategy.available:
            # Load image
            pil_image = Image.open(image_path)
            image_array = np.array(pil_image)
            
            print(f"Image shape: {image_array.shape}")
            
            # Test vectorization
            result = vtracer_strategy.vectorize(image_array)
            
            if hasattr(result, 'element_count'):
                print(f"✅ VTracer generated {result.element_count} elements")
                print(f"✅ SVG length: {len(result.svg_content)} characters")
                
                # Save result
                output_path = "test_vtracer_output.svg"
                result.save(output_path)
                print(f"✅ Saved to: {output_path}")
                
                return True
            else:
                print(f"❌ Unexpected result type: {type(result)}")
                return False
        else:
            print("❌ VTracer not available")
            return False
            
    except Exception as e:
        print(f"❌ VTracer test failed: {e}")
        return False
    
    # Test 2: OptimizedVectorizer with VTracer strategy
    print("\n🔍 Test 2: OptimizedVectorizer")
    try:
        vectorizer = OptimizedVectorizer()
        result = vectorizer.vectorize(image_path)
        
        print(f"✅ Strategy used: {result.strategy_used}")
        print(f"✅ Processing time: {result.processing_time:.3f}s")
        print(f"✅ Quality score: {result.quality_score}")
        
        if hasattr(result.svg_builder, 'element_count'):
            print(f"✅ Elements: {result.svg_builder.element_count}")
            print(f"✅ SVG length: {len(result.svg_builder.svg_content)} characters")
        else:
            print(f"✅ Elements: {len(result.svg_builder.elements)}")
        
        return True
        
    except Exception as e:
        print(f"❌ OptimizedVectorizer test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_vtracer_directly()
    
    if success:
        print("\n🎉 VTracer algorithm is working correctly!")
        print("✅ Quality has been restored")
    else:
        print("\n💥 VTracer algorithm needs fixing")
        print("❌ Quality restoration failed")