#!/usr/bin/env python3

import requests
import json
from PIL import Image

def test_web_2color_palette():
    print("🌐 Testing 2-color palette via web API...")
    
    # Test image path
    test_image_path = "/Users/ankish/Downloads/105-freelancer.png"
    
    try:
        # First, test palette extraction
        print("\n1️⃣ Testing palette extraction...")
        with open(test_image_path, 'rb') as f:
            files = {'file': f}
            response = requests.post('http://localhost:8080/api/extract-palettes', files=files)
        
        if response.status_code == 200:
            palette_data = response.json()
            if palette_data['success']:
                palettes = palette_data['palettes']
                print(f"✅ Palette extraction successful: {list(palettes.keys())}")
                
                if '2_colors' in palettes:
                    two_color_palette = palettes['2_colors']
                    print(f"🎨 2-color palette: {two_color_palette}")
                    
                    # Now test vectorization with the 2-color palette
                    print("\n2️⃣ Testing vectorization with 2-color palette...")
                    
                    with open(test_image_path, 'rb') as f:
                        files = {'file': f}
                        data = {
                            'vectorizer': 'optimized',
                            'target_time': '60',
                            'strategy': 'experimental',
                            'use_palette': 'true',
                            'selected_palette': json.dumps(two_color_palette),
                            'filter_speckle': '4',
                            'color_precision': '8',
                            'layer_difference': '8',
                            'corner_threshold': '90',
                            'length_threshold': '1.0',
                            'splice_threshold': '20',
                            'curve_fitting': 'spline'
                        }
                        
                        response = requests.post('http://localhost:8080/api/vectorize', files=files, data=data)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result['success']:
                            print(f"✅ Vectorization successful!")
                            print(f"   Strategy used: {result['strategy_used']}")
                            print(f"   Processing time: {result['processing_time']:.2f}s")
                            print(f"   Quality score: {result['quality_score']}")
                            print(f"   Number of elements: {result['num_elements']}")
                            print(f"   Content type: {result['content_type']}")
                            
                            # Check if SVG content exists
                            if 'svg_content' in result and result['svg_content']:
                                svg_length = len(result['svg_content'])
                                print(f"   SVG content length: {svg_length} characters")
                                
                                # Check for actual path elements
                                svg_content = result['svg_content']
                                path_count = svg_content.count('<path')
                                circle_count = svg_content.count('<circle')
                                rect_count = svg_content.count('<rect')
                                
                                print(f"   SVG elements found: {path_count} paths, {circle_count} circles, {rect_count} rects")
                                
                                if path_count == 0 and circle_count == 0 and rect_count == 0:
                                    print("❌ WARNING: No actual shape elements found in SVG!")
                                    print("🔍 SVG preview:")
                                    print(svg_content[:500] + "..." if len(svg_content) > 500 else svg_content)
                                else:
                                    print("✅ SVG contains shape elements - this should display properly")
                            else:
                                print("❌ No SVG content in response!")
                        else:
                            print(f"❌ Vectorization failed: {result.get('error', 'Unknown error')}")
                    else:
                        print(f"❌ Vectorization request failed: {response.status_code}")
                        print(f"Response: {response.text}")
                else:
                    print("❌ No 2-color palette found in extracted palettes")
            else:
                print(f"❌ Palette extraction failed: {palette_data.get('error', 'Unknown error')}")
        else:
            print(f"❌ Palette extraction request failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Flask app. Make sure the app is running on http://localhost:8080")
        print("   Run: python3 app.py")
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_web_2color_palette()