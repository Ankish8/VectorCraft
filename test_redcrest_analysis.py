#!/usr/bin/env python3
"""
REDCREST Logo Analysis
Debug the vectorization failure shown in the web interface
"""

import requests
import json
import base64
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os

def create_redcrest_test_logo():
    """Create a test logo similar to REDCREST for analysis"""
    # Create canvas
    width, height = 500, 200
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # Draw red/orange rectangles (similar to REDCREST bars)
    orange_color = (220, 65, 30)  # Similar to original
    
    bar_positions = [
        (80, 50, 110, 120),   # First bar
        (120, 40, 150, 130),  # Second bar  
        (160, 45, 190, 125),  # Third bar
        (200, 35, 230, 135),  # Fourth bar
    ]
    
    for pos in bar_positions:
        draw.rectangle(pos, fill=orange_color)
    
    # Add text (simplified)
    try:
        # Try to use a system font
        font = ImageFont.load_default()
        draw.text((80, 150), "REDCREST", fill='black', font=font)
        draw.text((80, 170), "E-COMMERCE PVT. LTD.", fill='black', font=font)
    except:
        # Fallback if font fails
        draw.text((80, 150), "REDCREST", fill='black')
        draw.text((80, 170), "E-COMMERCE PVT. LTD.", fill='black')
    
    # Save test image
    test_path = 'test_redcrest_logo.png'
    image.save(test_path)
    print(f"📝 Created test REDCREST logo: {test_path}")
    return test_path

def analyze_image_content(image_path):
    """Analyze the image to understand why vectorization failed"""
    from vectorcraft.utils.image_processor import ImageProcessor
    import cv2
    
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"❌ Could not load image: {image_path}")
        return None
    
    processor = ImageProcessor()
    
    # Convert to our format
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image_normalized = image_rgb.astype(np.float32) / 255.0
    
    # Analyze content
    metadata = processor.analyze_content(image_normalized)
    
    print(f"📊 Image Analysis:")
    print(f"   Dimensions: {image.shape[1]}x{image.shape[0]}")
    print(f"   Edge density: {metadata.edge_density:.6f}")
    print(f"   Text probability: {metadata.text_probability:.3f}")
    print(f"   Geometric probability: {metadata.geometric_probability:.3f}")
    print(f"   Gradient probability: {metadata.gradient_probability:.3f}")
    
    return metadata

def test_with_vectorcraft(image_path, strategy='auto'):
    """Test the image with VectorCraft web interface"""
    server_url = "http://localhost:8080"
    
    try:
        # Test server health
        health_response = requests.get(f"{server_url}/health", timeout=5)
        if health_response.status_code != 200:
            print("❌ VectorCraft server not healthy")
            return None
        
        print(f"✅ Testing with strategy: {strategy}")
        
        # Process the image
        with open(image_path, 'rb') as f:
            files = {'file': f}
            data = {
                'vectorizer': 'optimized',
                'target_time': '60',
                'strategy': strategy
            }
            
            response = requests.post(f'{server_url}/api/vectorize', files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"✅ Vectorization successful!")
                    print(f"   Strategy used: {result['strategy_used']}")
                    print(f"   Quality score: {result['quality_score']:.3f}")
                    print(f"   SVG elements: {result['num_elements']}")
                    print(f"   Processing time: {result['processing_time']:.2f}s")
                    print(f"   Content type: {result['content_type']}")
                    
                    # Save SVG result
                    svg_content = result['svg_content']
                    output_path = f"redcrest_result_{strategy}.svg"
                    with open(output_path, 'w') as f:
                        f.write(svg_content)
                    print(f"💾 SVG saved: {output_path}")
                    
                    return result
                else:
                    print(f"❌ Processing failed: {result.get('error')}")
                    return None
            else:
                print(f"❌ HTTP Error {response.status_code}: {response.text}")
                return None
                
    except Exception as e:
        print(f"❌ Error testing with VectorCraft: {e}")
        return None

def compare_strategies():
    """Compare different strategies on the test logo"""
    test_image = create_redcrest_test_logo()
    
    print("\n" + "="*60)
    print("🔍 ANALYZING REDCREST-STYLE LOGO")
    print("="*60)
    
    # Analyze image content
    metadata = analyze_image_content(test_image)
    if metadata is None:
        return
    
    print(f"\n🎯 STRATEGY ANALYSIS:")
    print(f"   Based on edge density ({metadata.edge_density:.6f}):")
    if metadata.edge_density < 0.01:
        print("   ➜ Low edge density - good for VTracer")
    else:
        print("   ➜ High edge density - may need primitive detection")
        
    print(f"   Based on geometric probability ({metadata.geometric_probability:.3f}):")
    if metadata.geometric_probability > 0.7:
        print("   ➜ High geometric content - rectangles/shapes detected")
    else:
        print("   ➜ Low geometric content - complex curves")
        
    print(f"   Based on text probability ({metadata.text_probability:.3f}):")
    if metadata.text_probability > 0.1:
        print("   ➜ Text detected - need text-specific handling")
    else:
        print("   ➜ No significant text detected")
    
    # Test different strategies
    strategies = [
        'auto',
        'vtracer_high_fidelity', 
        'hybrid_comprehensive',
        'primitive_focused'
    ]
    
    results = {}
    
    for strategy in strategies:
        print(f"\n🧪 TESTING STRATEGY: {strategy}")
        print("-" * 40)
        result = test_with_vectorcraft(test_image, strategy)
        if result:
            results[strategy] = result
        print()
    
    # Compare results
    print("\n📊 STRATEGY COMPARISON:")
    print("="*60)
    for strategy, result in results.items():
        print(f"{strategy:20} | Elements: {result['num_elements']:2d} | "
              f"Quality: {result['quality_score']:.3f} | "
              f"Time: {result['processing_time']:.2f}s")
    
    return results

def main():
    """Main analysis workflow"""
    print("🚀 REDCREST Logo Analysis & Strategy Comparison")
    print("🎯 Goal: Understand vectorization failure and improve")
    
    try:
        results = compare_strategies()
        
        if results:
            print(f"\n✅ Analysis complete! Results saved.")
            print(f"📁 Check generated SVG files for visual comparison")
            
            # Find best performing strategy
            best_strategy = max(results.items(), key=lambda x: x[1]['quality_score'])
            print(f"\n🏆 Best performing strategy: {best_strategy[0]}")
            print(f"   Quality score: {best_strategy[1]['quality_score']:.3f}")
            print(f"   Elements: {best_strategy[1]['num_elements']}")
        else:
            print("❌ No successful results to compare")
            
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()