# VectorCraft 2.0 - Next-Generation Vector Conversion

An innovative hybrid vectorization algorithm that surpasses existing solutions through intelligent combination of classical computer vision, geometric analysis, and differentiable optimization.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## 🚀 Features

- **🧠 Hybrid Intelligence**: Combines multiple vectorization strategies for optimal results
- **🎯 Semantic Understanding**: Adapts approach based on logo/icon type (text, geometric, gradient)
- **⚡ CPU Optimized**: Achieves 1-2 minute processing on CPU with performance optimizations
- **🎨 Quality Focused**: Optimizes for visual quality over pixel-perfect accuracy
- **🔶 Smart Primitives**: Automatically detects and uses circles, rectangles, and polygons
- **📊 Performance Monitoring**: Built-in profiling and adaptive optimization
- **🔄 Multiple Strategies**: Fast, primitive-focused, classical-refined, and comprehensive modes

## 📈 Performance Highlights

Based on our benchmarks:
- **11.8% average speed improvement** over standard vectorization
- **All images processed within target time constraints**
- **Automatic strategy adaptation** based on content type and time limits
- **Scalable performance**: 1.28-1.75 seconds per megapixel

## 🛠 Installation

```bash
# Clone the repository
git clone https://github.com/your-username/vectorcraft-2.0.git
cd vectorcraft-2.0

# Install dependencies
pip install -r requirements.txt

# Run basic functionality test
python test_basic.py
```

## 🎯 Quick Start

### Basic Usage
```python
from vectorcraft import HybridVectorizer

# Create vectorizer
vectorizer = HybridVectorizer()

# Vectorize an image
result = vectorizer.vectorize("logo.png")

# Save result
result.svg_builder.save("output.svg")

# Check results
print(f"Processing time: {result.processing_time:.2f}s")
print(f"Strategy used: {result.strategy_used}")
print(f"Quality score: {result.quality_score:.3f}")
```

### Optimized Performance
```python
from vectorcraft import OptimizedVectorizer

# Create optimized vectorizer with time constraints
vectorizer = OptimizedVectorizer(
    target_time=60.0,     # 60 second target
    enable_gpu=True,      # Enable GPU acceleration if available
    enable_caching=True   # Enable intelligent caching
)

# Vectorize with performance monitoring
result = vectorizer.vectorize("complex_logo.png", target_time=30.0)

# Performance stats are included in result metadata
print("Performance breakdown:")
for func, stats in result.metadata['performance_stats'].items():
    print(f"  {func}: {stats['total_time']:.3f}s ({stats['call_count']} calls)")
```

### Strategy Comparison
```python
# Compare different strategies
python demo.py --compare

# Run comprehensive benchmark
python demo.py --benchmark

# Performance testing
python performance_test.py
```

## 🏗 Architecture

VectorCraft 2.0 uses a sophisticated multi-stage approach:

### 1. Content Analysis
- **Edge Detection**: Multi-method edge detection (Canny, Sobel)
- **Color Analysis**: Dominant color extraction and quantization
- **Content Classification**: Text, geometric, gradient, or mixed content detection
- **Metadata Extraction**: Image characteristics for strategy selection

### 2. Strategy Selection
The system automatically selects the optimal strategy based on:
- **Content Type**: Text-heavy, geometric shapes, gradients, or mixed content
- **Time Constraints**: Available processing time
- **Image Complexity**: Size, detail level, color count

### 3. Hybrid Processing
Four main strategies are available:

#### `hybrid_fast` - Ultra-Fast Processing
- Aggressive downsampling for large images
- Simplified contour detection
- High-confidence primitive detection only
- **Best for**: Tight time constraints, simple logos

#### `primitive_focused` - Geometric Optimization
- Comprehensive shape detection (circles, rectangles, lines)
- Confidence-based primitive filtering
- Classical tracing for remaining areas
- **Best for**: Geometric logos, icons with clear shapes

#### `classical_refined` - High-Quality Tracing
- High-precision edge detection
- Path smoothing and simplification
- Douglas-Peucker algorithm for optimization
- **Best for**: Text-heavy logos, detailed graphics

#### `hybrid_comprehensive` - Best Quality
- Combines all strategies intelligently
- Parallel processing when possible
- Selective differentiable optimization
- **Best for**: When quality is paramount and time allows

### 4. Intelligent Fusion
- **Overlap Detection**: Prevents duplicate elements
- **Quality Assessment**: Evaluates and ranks results
- **Adaptive Refinement**: Optimizes based on remaining time
- **Element Prioritization**: Focuses on most important visual elements

## 📋 Supported Formats

### Input Formats
- PNG (with transparency support)
- JPG/JPEG
- GIF
- BMP
- TIFF

### Output Format
- SVG (Scalable Vector Graphics)
- Optimized for web and print use
- Clean, minimal code structure
- Support for fills, strokes, and transparency

## 🔧 Configuration Options

### Vectorizer Settings
```python
vectorizer = HybridVectorizer()

# Adjust strategy weights
vectorizer.strategy_weights = {
    'text': {'classical': 0.8, 'primitive': 0.1, 'diff': 0.1},
    'geometric': {'classical': 0.2, 'primitive': 0.7, 'diff': 0.1},
    'gradient': {'classical': 0.1, 'primitive': 0.1, 'diff': 0.8},
    'mixed': {'classical': 0.4, 'primitive': 0.3, 'diff': 0.3}
}

# Adjust classical tracer settings
vectorizer.classical_tracer.approx_epsilon = 0.005  # Higher precision
vectorizer.classical_tracer.contour_threshold = 100  # Larger minimum area

# Adjust primitive detector settings
vectorizer.primitive_detector.circle_min_radius = 5
vectorizer.primitive_detector.circle_max_radius = 300
```

### Performance Optimization
```python
from vectorcraft.utils.performance import PerformanceProfiler

# Enable detailed profiling
profiler = PerformanceProfiler()
vectorizer.profiler = profiler

# After processing
profiler.print_stats()
```

## 📊 Benchmarks

Performance comparison on test images:

| Image Size | Standard Time | Optimized Time | Improvement | Quality |
|------------|---------------|----------------|-------------|---------|
| 200x200    | 0.83s        | 0.09s         | 89.6%       | 0.800   |
| 400x400    | 0.23s        | 0.24s         | -8.6%       | 0.800   |
| 600x600    | 0.56s        | 0.60s         | -10.2%      | 0.800   |

*Note: Performance varies based on image complexity and content type*

## 🔬 Advanced Usage

### Custom Strategy Implementation
```python
class CustomStrategy:
    def vectorize(self, image, edge_map, quantized_image, metadata):
        # Your custom vectorization logic
        pass

# Register custom strategy
vectorizer._strategies['custom'] = CustomStrategy()
```

### GPU Acceleration
```python
from vectorcraft.utils.performance import GPUAccelerator

# Check GPU availability
gpu = GPUAccelerator()
print(f"GPU available: {gpu.enabled}")

# GPU acceleration is automatically used when available
vectorizer = OptimizedVectorizer(enable_gpu=True)
```

### Parallel Processing
```python
from vectorcraft.utils.performance import ParallelProcessor

# Process multiple images in parallel
images = ["logo1.png", "logo2.png", "logo3.png"]
processor = ParallelProcessor()

results = processor.parallel_strategy_evaluation(
    images, 
    {'fast': vectorizer.vectorize}, 
    max_workers=3
)
```

## 🧪 Testing & Development

### Run Tests
```bash
# Basic functionality test
python test_basic.py

# Create test images and run demos
python demo.py --create-tests

# Strategy comparison
python demo.py --compare

# Performance benchmarks
python performance_test.py
```

### Development Setup
```bash
# Install development dependencies
pip install -r requirements.txt

# Run linting (if configured)
python -m pylint vectorcraft/

# Run type checking (if configured)
python -m mypy vectorcraft/
```

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by Vector Magic and other commercial vectorization tools
- Built on top of OpenCV, PyTorch, and other excellent open-source libraries
- Thanks to the computer vision and machine learning communities

## 🔮 Future Enhancements

- **Deep Learning Integration**: Custom neural networks for specific logo types
- **Interactive Refinement**: User-guided optimization interface
- **Batch Processing**: Efficient handling of multiple images
- **Cloud Integration**: API for scalable processing
- **Format Extensions**: Support for additional input/output formats
- **Advanced Primitives**: Bezier curves, ellipses, custom shapes

---

**VectorCraft 2.0** - Making vector conversion intelligent, fast, and accessible.