#!/usr/bin/env python3

import numpy as np
from PIL import Image
from vectorcraft.strategies.experimental_vtracer_v3 import ExperimentalVTracerV3Strategy

def debug_2color_palette():
    print("🔍 Debugging 2-color palette issue...")
    
    # Test with a sample image (you can replace this with your test image)
    test_image_path = "/Users/ankish/Downloads/105-freelancer.png"
    
    try:
        # Load image
        image = Image.open(test_image_path)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        image_array = np.array(image)
        
        print(f"📊 Image shape: {image_array.shape}")
        
        # Create strategy
        strategy = ExperimentalVTracerV3Strategy()
        
        # Extract palettes
        palettes = strategy.extract_color_palettes(image_array)
        
        if '2_colors' in palettes:
            two_color_palette = palettes['2_colors']
            print(f"🎨 2-color palette: {two_color_palette}")
            
            # Test color layer creation
            layers = strategy.create_color_separated_layers(image_array, two_color_palette)
            
            print(f"\n📋 Layer analysis:")
            total_pixels = image_array.shape[0] * image_array.shape[1]
            covered_pixels = 0
            
            for layer_name, layer_data in layers.items():
                pixel_count = layer_data['pixel_count']
                covered_pixels += pixel_count
                percentage = (pixel_count / total_pixels) * 100
                print(f"  {layer_name}: {pixel_count} pixels ({percentage:.1f}%)")
            
            coverage_percentage = (covered_pixels / total_pixels) * 100
            print(f"\n📈 Total coverage: {covered_pixels}/{total_pixels} pixels ({coverage_percentage:.1f}%)")
            
            if coverage_percentage < 80:
                print("⚠️  WARNING: Low pixel coverage - threshold might be too strict!")
                
                # Test with higher threshold
                print("\n🔧 Testing with higher threshold...")
                strategy_loose = ExperimentalVTracerV3Strategy()
                # Temporarily modify threshold for testing
                original_create_mask = strategy_loose._create_color_mask
                
                def loose_create_mask(image, target_color, threshold=50):  # Higher threshold
                    return original_create_mask(image, target_color, threshold)
                
                strategy_loose._create_color_mask = loose_create_mask
                
                loose_layers = strategy_loose.create_color_separated_layers(image_array, two_color_palette)
                loose_covered = sum(layer_data['pixel_count'] for layer_data in loose_layers.values())
                loose_percentage = (loose_covered / total_pixels) * 100
                print(f"   With threshold=50: {loose_percentage:.1f}% coverage")
            
            # Test vectorization
            print(f"\n🖼️  Testing vectorization...")
            svg_result = strategy.vectorize_with_palette(image_array, two_color_palette, None, None)
            
            if hasattr(svg_result, 'elements'):
                print(f"✅ SVG created with {len(svg_result.elements)} elements")
                
                # Check if any elements were created
                if len(svg_result.elements) == 0:
                    print("❌ No SVG elements created! This is the issue.")
                else:
                    print("✅ SVG elements successfully created")
                    
                    # Test SVG content generation
                    svg_content = svg_result.get_svg_string()
                    print(f"📄 SVG content length: {len(svg_content)} characters")
                    print(f"📄 SVG preview: {svg_content[:300]}...")
                    
                    # Check for actual shape elements
                    path_count = svg_content.count('<path')
                    circle_count = svg_content.count('<circle')
                    rect_count = svg_content.count('<rect')
                    print(f"📊 SVG elements: {path_count} paths, {circle_count} circles, {rect_count} rects")
            else:
                print("❌ SVG result doesn't have elements attribute")
                
        else:
            print("❌ No 2-color palette found in extracted palettes")
            print(f"Available palettes: {list(palettes.keys())}")
            
    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_2color_palette()