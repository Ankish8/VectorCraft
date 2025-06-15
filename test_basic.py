#!/usr/bin/env python3
"""
Basic test script to verify VectorCraft 2.0 installation and functionality
"""

import numpy as np
from PIL import Image, ImageDraw
import os

def test_imports():
    """Test if all modules can be imported"""
    print("Testing imports...")
    try:
        from vectorcraft.utils.image_processor import ImageProcessor
        from vectorcraft.strategies.classical_tracer import ClassicalTracer
        from vectorcraft.primitives.detector import PrimitiveDetector
        from vectorcraft.core.svg_builder import SVGBuilder
        from vectorcraft.core.hybrid_vectorizer import HybridVectorizer
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_image_processing():
    """Test basic image processing functionality"""
    print("\nTesting image processing...")
    try:
        # Create a simple test image
        img = Image.new('RGB', (100, 100), color='white')
        draw = ImageDraw.Draw(img)
        draw.ellipse([25, 25, 75, 75], fill='red')
        
        # Save and process
        test_path = "test_circle.png"
        img.save(test_path)
        
        from vectorcraft.utils.image_processor import ImageProcessor
        processor = ImageProcessor()
        
        # Load and analyze
        image_array = processor.load_image(test_path)
        metadata = processor.analyze_content(image_array)
        
        print(f"✓ Image processed: {metadata.width}x{metadata.height}")
        print(f"✓ Edge density: {metadata.edge_density:.3f}")
        
        # Cleanup
        os.remove(test_path)
        return True
        
    except Exception as e:
        print(f"✗ Image processing failed: {e}")
        return False

def test_svg_builder():
    """Test SVG builder functionality"""
    print("\nTesting SVG builder...")
    try:
        from vectorcraft.core.svg_builder import SVGBuilder
        
        builder = SVGBuilder(200, 200)
        builder.add_circle((100, 100), 50, (1.0, 0.0, 0.0))
        builder.add_rectangle(50, 150, 100, 30, (0.0, 1.0, 0.0))
        
        svg_string = builder.get_svg_string()
        
        if 'circle' in svg_string and 'rect' in svg_string:
            print("✓ SVG builder working correctly")
            return True
        else:
            print("✗ SVG builder output missing elements")
            return False
            
    except Exception as e:
        print(f"✗ SVG builder failed: {e}")
        return False

def test_basic_vectorization():
    """Test basic vectorization without heavy dependencies"""
    print("\nTesting basic vectorization...")
    try:
        # Create simple test image
        img = Image.new('RGB', (100, 100), color='white')
        draw = ImageDraw.Draw(img)
        draw.rectangle([20, 20, 80, 80], fill='blue', outline='black', width=2)
        
        test_path = "test_rect.png"
        img.save(test_path)
        
        # Simple processing test
        from vectorcraft.utils.image_processor import ImageProcessor
        from vectorcraft.strategies.classical_tracer import ClassicalTracer
        from vectorcraft.core.svg_builder import SVGBuilder
        
        processor = ImageProcessor()
        tracer = ClassicalTracer()
        
        image_array = processor.load_image(test_path)
        processed = processor.preprocess(image_array)
        quantized = processor.segment_colors(processed, n_colors=4)
        
        svg_result = tracer.trace_with_colors(processed, quantized)
        
        if len(svg_result.elements) > 0:
            print(f"✓ Basic vectorization successful: {len(svg_result.elements)} elements")
            
            # Save test result
            svg_result.save("test_output.svg")
            print("✓ SVG saved successfully")
            
            # Cleanup
            os.remove(test_path)
            if os.path.exists("test_output.svg"):
                os.remove("test_output.svg")
            
            return True
        else:
            print("✗ No elements generated")
            return False
            
    except Exception as e:
        print(f"✗ Basic vectorization failed: {e}")
        return False

def main():
    print("VectorCraft 2.0 - Basic Functionality Test")
    print("=" * 45)
    
    tests = [
        test_imports,
        test_image_processing, 
        test_svg_builder,
        test_basic_vectorization
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\nTest Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! VectorCraft 2.0 is ready to use.")
        print("\nTry running: python demo.py --create-tests")
    else:
        print("❌ Some tests failed. Check dependencies and installation.")
        
        # Basic dependency check
        print("\nChecking basic dependencies...")
        required_packages = ['numpy', 'opencv-python', 'Pillow', 'torch', 'svgwrite']
        
        for package in required_packages:
            try:
                if package == 'opencv-python':
                    import cv2
                    print(f"✓ {package} (cv2) available")
                elif package == 'Pillow':
                    import PIL
                    print(f"✓ {package} (PIL) available")
                else:
                    __import__(package)
                    print(f"✓ {package} available")
            except ImportError:
                print(f"✗ {package} missing - install with: pip install {package}")

if __name__ == "__main__":
    main()