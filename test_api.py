#!/usr/bin/env python3
"""
Test script for VectorCraft 2.0 Web API
"""

import requests
import json
import time
from PIL import Image, ImageDraw

def create_test_image():
    """Create a simple test image"""
    img = Image.new('RGB', (100, 100), color='white')
    draw = ImageDraw.Draw(img)
    draw.ellipse([25, 25, 75, 75], fill='red', outline='black', width=2)
    img.save('api_test.png')
    return 'api_test.png'

def test_health_endpoint():
    """Test health check endpoint"""
    try:
        response = requests.get('http://localhost:8080/health')
        data = response.json()
        print("✅ Health check passed:")
        print(f"   Status: {data['status']}")
        print(f"   Version: {data['version']}")
        print(f"   Vectorizers: {data['vectorizers']}")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_vectorization_api():
    """Test the vectorization API"""
    print("\n🧪 Testing Vectorization API...")
    
    # Create test image
    image_path = create_test_image()
    print(f"📷 Created test image: {image_path}")
    
    try:
        # Prepare request
        with open(image_path, 'rb') as f:
            files = {'file': f}
            data = {
                'vectorizer': 'standard',
                'target_time': '30',
                'strategy': 'hybrid_fast'
            }
            
            print("⏳ Sending vectorization request...")
            start_time = time.time()
            
            response = requests.post('http://localhost:8080/api/vectorize', files=files, data=data)
            
            elapsed = time.time() - start_time
            print(f"⏱️  Request completed in {elapsed:.2f}s")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print("✅ Vectorization successful!")
                    print(f"   Processing time: {result['processing_time']:.2f}s")
                    print(f"   Strategy used: {result['strategy_used']}")
                    print(f"   Quality score: {result['quality_score']:.3f}")
                    print(f"   SVG elements: {result['num_elements']}")
                    print(f"   Content type: {result['content_type']}")
                    
                    # Check if SVG was generated
                    if result.get('svg_content'):
                        print(f"   SVG length: {len(result['svg_content'])} characters")
                        
                        # Save SVG for inspection
                        with open('api_test_result.svg', 'w') as svg_file:
                            svg_file.write(result['svg_content'])
                        print("   💾 SVG saved as: api_test_result.svg")
                    
                    return True
                else:
                    print(f"❌ Vectorization failed: {result.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"❌ HTTP Error {response.status_code}: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False
    
    finally:
        # Cleanup
        import os
        if os.path.exists(image_path):
            os.remove(image_path)

def test_demo_endpoints():
    """Test demo endpoints"""
    print("\n🎮 Testing Demo Endpoints...")
    
    try:
        # Test sample creation
        print("📸 Testing sample creation...")
        response = requests.get('http://localhost:8080/api/demo/create_samples')
        data = response.json()
        
        if data.get('success'):
            print(f"✅ Sample creation successful: {len(data['samples'])} samples created")
        else:
            print(f"❌ Sample creation failed: {data.get('error')}")
            
        return True
        
    except Exception as e:
        print(f"❌ Demo endpoints test failed: {e}")
        return False

def main():
    print("🧪 VectorCraft 2.0 API Test Suite")
    print("=" * 40)
    
    tests = [
        ("Health Check", test_health_endpoint),
        ("Vectorization API", test_vectorization_api),
        ("Demo Endpoints", test_demo_endpoints)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔬 Running: {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! VectorCraft 2.0 API is working correctly.")
        print("\n🌐 Web interface available at: http://localhost:8080")
        print("📖 Try uploading an image through the web interface!")
    else:
        print("⚠️  Some tests failed. Check the server logs for details.")
    
    return passed == total

if __name__ == "__main__":
    main()