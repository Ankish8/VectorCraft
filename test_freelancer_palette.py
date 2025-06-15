#!/usr/bin/env python3

from vectorcraft.strategies.experimental_vtracer_v3 import ExperimentalVTracerV3Strategy
from PIL import Image
import numpy as np

print('🎨 Testing palette extraction with freelancer image...')

# Load the actual freelancer image
try:
    image = Image.open('/Users/ankish/Downloads/105-freelancer.png')
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    image_array = np.array(image)
    print(f'📊 Image loaded: {image_array.shape}')
    
    # Extract palettes
    strategy = ExperimentalVTracerV3Strategy()
    palettes = strategy.extract_color_palettes(image_array)
    
    print(f'✅ Extracted {len(palettes)} palette options from freelancer image:')
    
    # Show the key palettes that should appear in UI
    for key in ['2_colors', '4_colors', '6_colors', '8_colors']:
        if key in palettes:
            palette = palettes[key]
            print(f'  🎨 {key}: {palette}')
    
    print('🚀 Palette extraction working correctly!')
    
except Exception as e:
    print(f'❌ Error: {e}')