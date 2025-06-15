# VectorCraft 2.0 - Localhost Setup Guide

This guide will help you run VectorCraft 2.0 on your local machine for testing and development.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
# Install Python dependencies
pip3 install -r requirements.txt

# Install additional web dependencies (if not already installed)
pip3 install flask werkzeug requests
```

### 2. Start the Web Server
Choose one of these methods:

#### Method A: Simple Startup (Recommended)
```bash
python3 start_server.py
```
This will:
- Start the server on http://localhost:8080
- Automatically open your browser
- Check server health

#### Method B: Direct Flask App
```bash
python3 app.py
```

#### Method C: Custom Port
```bash
# Edit app.py to change port, then run:
python3 app.py
```

### 3. Access the Web Interface
- **Main Interface**: http://localhost:8080
- **API Endpoint**: http://localhost:8080/api/vectorize
- **Health Check**: http://localhost:8080/health

## 🖥️ Web Interface Features

### Upload Methods
1. **Drag & Drop**: Drag image files directly onto the upload area
2. **Click to Browse**: Click the upload area to select files
3. **Demo Samples**: Use built-in sample images for testing

### Configuration Options
- **Vectorizer Type**: Standard vs Optimized
- **Target Time**: Processing time limit (10-300 seconds)
- **Strategy**: Auto-select or manual strategy choice
  - `hybrid_fast`: Ultra-fast processing
  - `primitive_focused`: Geometric shape detection
  - `classical_refined`: High-quality tracing
  - `hybrid_comprehensive`: Best quality

### Results Display
- **Side-by-side comparison**: Original vs vectorized
- **Performance metrics**: Time, quality, elements count
- **Content analysis**: Type detection and metadata
- **Download**: SVG file download

## 🧪 Testing the Setup

### Basic Functionality Test
```bash
python3 test_basic.py
```

### API Testing
```bash
python3 test_api.py
```

### Demo Commands
```bash
# Create sample images
python3 demo.py --create-tests

# Run benchmarks
python3 demo.py --benchmark

# Compare strategies
python3 demo.py --compare
```

## 📋 Supported Features

### Input Formats
- ✅ PNG (with transparency)
- ✅ JPG/JPEG
- ✅ GIF
- ✅ BMP
- ✅ TIFF
- 📏 Max file size: 16MB

### Processing Options
- ✅ Multiple vectorization strategies
- ✅ Performance optimization
- ✅ Real-time progress tracking
- ✅ Quality assessment
- ✅ Content type detection

### Output Features
- ✅ Clean SVG generation
- ✅ Primitive shape detection
- ✅ Path optimization
- ✅ Download functionality

## 🔧 API Usage

### Health Check
```bash
curl http://localhost:8080/health
```

### Vectorize Image
```bash
curl -X POST \
  -F "file=@your_image.png" \
  -F "vectorizer=optimized" \
  -F "target_time=60" \
  -F "strategy=auto" \
  http://localhost:8080/api/vectorize
```

### Demo Endpoints
```bash
# Create sample images
curl http://localhost:8080/api/demo/create_samples

# Run benchmark
curl http://localhost:8080/api/demo/benchmark
```

## 🎮 Interactive Testing

### Web Interface Testing
1. Open http://localhost:8080
2. Click "Create Sample Images" to generate test images
3. Click "Load Example" to process a sample automatically
4. Upload your own images via drag & drop
5. Experiment with different settings

### Performance Testing
1. Use "Run Quick Benchmark" for speed testing
2. Try different target times (30s, 60s, 120s)
3. Compare strategies on the same image
4. Monitor processing times and quality scores

## 🛠️ Development Features

### Debug Mode
The server runs in debug mode by default, providing:
- Automatic reloading on code changes
- Detailed error messages
- Request logging

### File Structure
```
VectorCraft/
├── app.py                 # Flask web application
├── start_server.py        # Easy server startup
├── test_api.py           # API testing suite
├── templates/
│   └── index.html        # Web interface
├── uploads/              # Temporary file storage
├── results/              # Generated SVG files
└── static/               # Web assets
```

### Logging and Monitoring
- Server health monitoring
- Processing time tracking
- Error handling and reporting
- Performance statistics

## 🔍 Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Error: Address already in use
# Solution: Change port in app.py or kill existing process
lsof -ti:8080 | xargs kill -9
```

#### Module Import Errors
```bash
# Ensure you're in the correct directory
cd /path/to/VectorCraft

# Install missing dependencies
pip3 install -r requirements.txt
```

#### File Upload Issues
- Check file size (max 16MB)
- Verify file format (PNG, JPG, etc.)
- Check browser console for errors

#### Performance Issues
- Reduce target time for faster processing
- Use 'hybrid_fast' strategy for speed
- Try smaller images for testing

### Debug Commands
```bash
# Check server status
curl -s http://localhost:8080/health | python3 -m json.tool

# Test with sample image
python3 test_api.py

# Verify dependencies
python3 -c "from vectorcraft import HybridVectorizer; print('✅ Import successful')"
```

## 📊 Performance Expectations

### Processing Times
- **Simple logos (200x200)**: 0.1-0.5 seconds
- **Medium images (400x400)**: 0.2-1.0 seconds  
- **Complex images (800x800)**: 0.5-2.0 seconds

### Quality Metrics
- **Quality Score**: 0.7-0.9 (higher is better)
- **SVG Elements**: 5-50 typical range
- **File Size**: Usually 1-10KB for logos

## 🎯 Next Steps

### For Testing
1. ✅ Upload various logo types
2. ✅ Compare processing strategies
3. ✅ Test different time constraints
4. ✅ Evaluate output quality

### For Development
1. 🔧 Modify algorithm parameters
2. 🔧 Add custom strategies
3. 🔧 Implement new features
4. 🔧 Optimize performance

### For Production
1. 🚀 Deploy to production server
2. 🚀 Add authentication if needed
3. 🚀 Set up monitoring
4. 🚀 Scale for concurrent users

---

**🎉 Enjoy testing VectorCraft 2.0 on localhost!**

Need help? Check the main README.md or create an issue on GitHub.