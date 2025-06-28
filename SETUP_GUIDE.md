# VectorCraft Setup Guide

## Quick Start

1. **Run the setup script:**
   ```bash
   python3 setup_environment.py
   ```

2. **Start the application:**
   ```bash
   python3 app.py
   ```

3. **Open in browser:**
   ```
   http://localhost:5000
   ```

## VTracer Integration

This project includes multiple ways to use VTracer:

### ✅ Bundled Binary (Recommended)
- **File**: `./vtracer_binary`
- **Pros**: Always available, no installation needed
- **Architecture**: ARM64 (Apple Silicon)

### Python Package
- **Install**: `pip3 install vtracer`
- **Pros**: Better Python integration
- **Cons**: Requires separate installation

### System Installation
- **Install**: `cargo install vtracer`
- **Pros**: System-wide availability
- **Cons**: Requires Rust/Cargo

## Dependencies

### Required
- Python 3.8+
- NumPy
- OpenCV
- Pillow
- Flask

### Optional (for full features)
- PyTorch
- scikit-image
- matplotlib
- scipy

## Troubleshooting

### "VTracer not found"
The bundled binary (`./vtracer_binary`) should work out of the box. If not:
1. Check file permissions: `chmod +x ./vtracer_binary`
2. Install system version: `cargo install vtracer`
3. Install Python version: `pip3 install vtracer`

### Python Dependencies
If you get import errors:
1. Use virtual environment: `python3 -m venv venv && source venv/bin/activate`
2. Install with user flag: `pip3 install --user -r requirements.txt`
3. Use system packages: `pip3 install --break-system-packages -r requirements.txt`

### Permission Issues
If the app can't write files:
```bash
chmod 755 uploads results
```

## File Structure

```
VectorCraft/
├── app.py                    # Main Flask application
├── vtracer_binary           # Bundled VTracer (ARM64)
├── setup_environment.py    # Setup script
├── requirements.txt         # Python dependencies
├── vectorcraft/            # Core library
│   ├── core/               # Main algorithms
│   ├── strategies/         # Vectorization strategies
│   └── utils/              # Utilities including vtracer_wrapper
├── templates/              # Web interface
├── uploads/                # Uploaded images
└── results/                # Generated SVGs
```