#!/usr/bin/env python3
"""
Create a side-by-side comparison of the original image and our vectorization result
"""

import os
import base64
from PIL import Image, ImageDraw, ImageFont
import cairosvg
import io

def create_comparison():
    """Create a side-by-side comparison image"""
    
    # Load original image
    original = Image.open('/Users/ankish/Downloads/Frame 53.png')
    
    # Read and render SVG result
    with open('/Users/ankish/Downloads/MA/vc2/improvement_results/frame53_current_result.svg', 'r') as f:
        svg_content = f.read()
    
    # Convert SVG to PNG using cairosvg
    png_bytes = cairosvg.svg2png(bytestring=svg_content.encode('utf-8'), 
                                output_width=original.width, 
                                output_height=original.height)
    
    # Convert to PIL Image
    vectorized = Image.open(io.BytesIO(png_bytes))
    
    # Create comparison image
    comparison_width = original.width * 2 + 60  # Space for labels and gap
    comparison_height = original.height + 80   # Space for labels
    
    comparison = Image.new('RGB', (comparison_width, comparison_height), 'white')
    
    # Paste images
    comparison.paste(original, (20, 60))
    comparison.paste(vectorized, (original.width + 40, 60))
    
    # Add labels
    draw = ImageDraw.Draw(comparison)
    font = ImageFont.load_default()
    
    # Original label
    draw.text((20, 20), "ORIGINAL (Frame 53.png)", fill='black', font=font)
    draw.text((20, 35), f"Size: {original.width}x{original.height}", fill='gray', font=font)
    
    # Vectorized label  
    draw.text((original.width + 40, 20), "VECTORIZED (primitive_focused)", fill='black', font=font)
    draw.text((original.width + 40, 35), "9 elements: 3 rects + 3 circles + 3 paths", fill='gray', font=font)
    
    # Add similarity info
    draw.text((20, comparison_height - 20), "Similarity: 72.3% | Target: 95%", fill='red', font=font)
    
    # Save comparison
    comparison_path = '/Users/ankish/Downloads/MA/vc2/comparison_result.png'
    comparison.save(comparison_path)
    
    print(f"✅ Comparison saved: {comparison_path}")
    return comparison_path

if __name__ == "__main__":
    create_comparison()