#!/usr/bin/env python3
"""
VectorCraft 2.0 Web Interface
Flask web application for testing vectorization locally
"""

import os
import time
import uuid
from flask import Flask, render_template, request, jsonify, send_file, url_for
from werkzeug.utils import secure_filename
import base64
from io import BytesIO
from PIL import Image

from vectorcraft import HybridVectorizer, OptimizedVectorizer

app = Flask(__name__)
app.config['SECRET_KEY'] = 'vectorcraft-2024-secret-key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULTS_FOLDER'] = 'results'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)
os.makedirs('static/images', exist_ok=True)

# Initialize vectorizers
standard_vectorizer = HybridVectorizer()
optimized_vectorizer = OptimizedVectorizer()

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/extract-palettes', methods=['POST'])
def extract_palettes():
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())
        filename_with_id = f"{unique_id}_{filename}"
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename_with_id)
        file.save(input_path)
        
        # Load image for palette extraction
        from PIL import Image
        import numpy as np
        
        image = Image.open(input_path)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        image_array = np.array(image)
        
        # Extract palettes using experimental strategy
        from vectorcraft.strategies.experimental_vtracer_v3 import ExperimentalVTracerV3Strategy
        experimental_strategy = ExperimentalVTracerV3Strategy()
        
        palettes = experimental_strategy.extract_color_palettes(image_array)
        
        # Convert numpy int64 to regular Python int for JSON serialization
        json_palettes = {}
        for key, palette in palettes.items():
            json_palettes[key] = [[int(color[0]), int(color[1]), int(color[2])] for color in palette]
        
        # Clean up temp file
        os.remove(input_path)
        
        return jsonify({
            'success': True,
            'palettes': json_palettes
        })
        
    except Exception as e:
        print(f"❌ Palette extraction error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/palette-preview', methods=['POST'])
def generate_palette_preview():
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
        
        # Get selected palette
        selected_palette_json = request.form.get('selected_palette')
        if not selected_palette_json:
            return jsonify({'error': 'No palette selected'}), 400
        
        import json
        selected_palette = json.loads(selected_palette_json)
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())
        filename_with_id = f"{unique_id}_{filename}"
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename_with_id)
        file.save(input_path)
        
        # Load image for preview generation
        from PIL import Image
        import numpy as np
        
        image = Image.open(input_path)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        image_array = np.array(image)
        
        # Generate preview using experimental strategy
        from vectorcraft.strategies.experimental_vtracer_v3 import ExperimentalVTracerV3Strategy
        experimental_strategy = ExperimentalVTracerV3Strategy()
        
        preview_image = experimental_strategy.create_quantized_preview(image_array, selected_palette)
        
        # Convert preview back to PIL Image and encode as base64
        from io import BytesIO
        import base64
        
        preview_pil = Image.fromarray(preview_image.astype('uint8'))
        buffer = BytesIO()
        preview_pil.save(buffer, format='PNG')
        buffer.seek(0)
        
        preview_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Clean up temp file
        os.remove(input_path)
        
        return jsonify({
            'success': True,
            'preview_image': f'data:image/png;base64,{preview_base64}'
        })
        
    except Exception as e:
        print(f"❌ Palette preview error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/vectorize', methods=['POST'])
def vectorize_image():
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Supported: PNG, JPG, GIF, BMP, TIFF'}), 400
        
        # Use optimized vectorization approach
        vectorizer_type = 'optimized'  # Always use optimized
        target_time = float(request.form.get('target_time', 60))
        strategy = request.form.get('strategy', 'vtracer_high_fidelity')  # Allow strategy selection
        
        # Extract vectorization parameters from form
        vectorization_params = {
            'filter_speckle': int(request.form.get('filter_speckle', 4)),
            'color_precision': int(request.form.get('color_precision', 8)),
            'layer_difference': int(request.form.get('layer_difference', 8)),
            'corner_threshold': int(request.form.get('corner_threshold', 90)),
            'length_threshold': float(request.form.get('length_threshold', 1.0)),
            'splice_threshold': int(request.form.get('splice_threshold', 20)),
            'curve_fitting': request.form.get('curve_fitting', 'spline')
        }
        
        print(f"🎛️ Vectorization parameters: {vectorization_params}")
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_{filename}")
        file.save(input_path)
        
        # Use OptimizedVectorizer with advanced algorithms
        vectorizer = optimized_vectorizer
        
        # Set custom VTracer parameters 
        if hasattr(vectorizer, 'real_vtracer') and vectorizer.real_vtracer.available:
            vectorizer.real_vtracer.set_custom_parameters(vectorization_params)
            print(f"🎛️ Set VTracer parameters: {vectorization_params}")
        
        # Use high-fidelity strategy for best quality
        if hasattr(vectorizer, 'adaptive_optimizer'):
            # Override strategy selection for high quality results
            original_optimize = vectorizer.adaptive_optimizer.optimize_strategy_selection
            vectorizer.adaptive_optimizer.optimize_strategy_selection = lambda metadata, elapsed: strategy
        
        print(f"🎯 WEB INTERFACE: Using {strategy} strategy for {filename}")
        
        # Check if palette-based vectorization is requested
        use_palette = request.form.get('use_palette', 'false').lower() == 'true'
        selected_palette = None
        
        if use_palette and request.form.get('selected_palette'):
            import json
            try:
                selected_palette = json.loads(request.form.get('selected_palette'))
                print(f"🎨 Using custom palette with {len(selected_palette)} colors: {selected_palette}")
                print(f"🎨 Strategy: {strategy}")
                print(f"🎨 Use palette: {use_palette}")
            except Exception as e:
                print(f"❌ Failed to parse selected palette: {e}, using standard vectorization")
                use_palette = False
        
        # Vectorize image
        start_time = time.time()
        
        print(f"🎨 Palette condition check: use_palette={use_palette}, has_palette={selected_palette is not None}, strategy={strategy}")
        
        if use_palette and selected_palette and strategy == 'experimental':
            # Use palette-based vectorization
            from PIL import Image
            import numpy as np
            from vectorcraft.strategies.experimental_vtracer_v3 import ExperimentalVTracerV3Strategy
            
            # Load image for palette-based processing
            image = Image.open(input_path)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            image_array = np.array(image)
            
            # Use experimental strategy with palette
            experimental_strategy = ExperimentalVTracerV3Strategy()
            print(f"🎨 Processing with palette: {selected_palette}")
            palette_result = experimental_strategy.vectorize_with_palette(
                image_array, selected_palette, None, None
            )
            print(f"🎨 Palette result elements: {len(palette_result.elements) if hasattr(palette_result, 'elements') else 'No elements'}")
            
            # Create a result-like object
            class ImageMetadata:
                def __init__(self, image):
                    self.width = image.width
                    self.height = image.height
                    self.edge_density = 0.5  # Default values
                    self.text_probability = 0.1
                    self.geometric_probability = 0.8
                    self.gradient_probability = 0.2
            
            class PaletteResult:
                def __init__(self, svg_builder, processing_time, image):
                    self.svg_builder = svg_builder
                    self.processing_time = processing_time
                    self.strategy_used = f"experimental_palette_{len(selected_palette)}_colors"
                    self.quality_score = 0.85  # Estimate for palette-based
                    self.metadata = {
                        'content_type': 'palette_based',
                        'num_elements': len(svg_builder.elements) if hasattr(svg_builder, 'elements') else 0,
                        'palette_colors': len(selected_palette),
                        'image_metadata': ImageMetadata(image),
                        'performance_stats': {}
                    }
            
            result = PaletteResult(palette_result, time.time() - start_time, image)
        else:
            # Standard vectorization
            result = vectorizer.vectorize(input_path, target_time=target_time)
        
        processing_time = time.time() - start_time
        
        # Restore original strategy selection
        if hasattr(vectorizer, 'adaptive_optimizer'):
            vectorizer.adaptive_optimizer.optimize_strategy_selection = original_optimize
        
        # Clear custom VTracer parameters for next request
        if hasattr(vectorizer, 'real_vtracer') and vectorizer.real_vtracer.available:
            vectorizer.real_vtracer.custom_params = None
        
        # Save SVG result with version info
        version_suffix = "_v1.0.0-experimental" if strategy == 'experimental' else ""
        palette_suffix = f"_palette_{len(selected_palette)}colors" if use_palette and selected_palette else ""
        svg_filename = f"{unique_id}_result{version_suffix}{palette_suffix}.svg"
        svg_path = os.path.join(app.config['RESULTS_FOLDER'], svg_filename)
        
        # Also save to output folder with timestamp for tracking improvements
        timestamp = int(time.time())
        output_filename = f"{timestamp}_{strategy}_result.svg"
        output_path = os.path.join("output", output_filename)
        os.makedirs("output", exist_ok=True)
        
        # Handle different result types from vectorization
        if hasattr(result, 'svg_builder') and result.svg_builder:
            print(f"🎨 Using svg_builder, elements: {len(result.svg_builder.elements) if hasattr(result.svg_builder, 'elements') else 'No elements'}")
            result.svg_builder.save(svg_path)
            result.svg_builder.save(output_path)  # Save to output folder too
            svg_content = result.svg_builder.get_svg_string()
            print(f"🎨 SVG content length: {len(svg_content)} characters")
            print(f"🎨 SVG preview: {svg_content[:200]}...")
        else:
            print(f"🎨 Using direct SVG result")
            # Handle direct SVG result
            with open(svg_path, 'w') as f:
                f.write(result.get_svg_string())
            with open(output_path, 'w') as f:  # Save to output folder too
                f.write(result.get_svg_string())
            svg_content = result.get_svg_string()
        
        # Convert SVG to base64 for embedding
        svg_b64 = base64.b64encode(svg_content.encode()).decode()
        
        # Get original image as base64 for comparison
        with open(input_path, 'rb') as img_file:
            img_b64 = base64.b64encode(img_file.read()).decode()
            img_ext = filename.rsplit('.', 1)[1].lower()
        
        # Clean up uploaded file
        os.remove(input_path)
        
        download_url = url_for('download_result', filename=svg_filename)
        print(f"🔗 Download URL: {download_url} (filename: {svg_filename})")
        
        return jsonify({
            'success': True,
            'processing_time': result.processing_time,
            'total_time': processing_time,
            'strategy_used': result.strategy_used,
            'quality_score': result.quality_score,
            'num_elements': result.metadata['num_elements'],
            'content_type': result.metadata['content_type'],
            'svg_content': svg_content,
            'svg_b64': svg_b64,
            'original_b64': img_b64,
            'original_ext': img_ext,
            'download_url': download_url,
            'metadata': {
                'image_size': f"{result.metadata['image_metadata'].width}x{result.metadata['image_metadata'].height}",
                'edge_density': result.metadata['image_metadata'].edge_density,
                'text_probability': result.metadata['image_metadata'].text_probability,
                'geometric_probability': result.metadata['image_metadata'].geometric_probability,
                'gradient_probability': result.metadata['image_metadata'].gradient_probability,
                'performance_stats': result.metadata.get('performance_stats', {}) if hasattr(result.metadata, 'get') else {}
            }
        })
        
    except Exception as e:
        # Clean up files on error
        if 'input_path' in locals() and os.path.exists(input_path):
            os.remove(input_path)
        
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/api/demo/<demo_type>')
def run_demo(demo_type):
    """Run predefined demos"""
    try:
        if demo_type == 'create_samples':
            # Create sample images
            from demo import create_test_images
            test_images = create_test_images()
            
            samples = []
            for img_path in test_images:
                # Get image info
                img = Image.open(img_path)
                width, height = img.size
                
                # Convert to base64
                with open(img_path, 'rb') as f:
                    img_b64 = base64.b64encode(f.read()).decode()
                
                samples.append({
                    'name': os.path.basename(img_path).replace('.png', '').replace('_', ' ').title(),
                    'path': img_path,
                    'size': f"{width}x{height}",
                    'b64': img_b64
                })
            
            return jsonify({'success': True, 'samples': samples})
            
        elif demo_type == 'benchmark':
            # Run quick benchmark
            from demo import create_test_images
            test_images = create_test_images()
            
            results = []
            for img_path in test_images[:2]:  # Limit to 2 for web demo
                result = standard_vectorizer.vectorize(img_path, target_time=30)
                results.append({
                    'image': os.path.basename(img_path),
                    'time': result.processing_time,
                    'strategy': result.strategy_used,
                    'quality': result.quality_score,
                    'elements': result.metadata['num_elements']
                })
            
            return jsonify({'success': True, 'results': results})
        
        else:
            return jsonify({'error': 'Unknown demo type'}), 400
            
    except Exception as e:
        return jsonify({'error': f'Demo failed: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_result(filename):
    """Download SVG result file"""
    try:
        file_path = os.path.join(app.config['RESULTS_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return "File not found", 404
    except Exception as e:
        return f"Download error: {str(e)}", 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '2.0.0',
        'vectorizers': ['standard', 'optimized'],
        'supported_formats': list(ALLOWED_EXTENSIONS)
    })

if __name__ == '__main__':
    print("🚀 Starting VectorCraft 2.0 Web Interface...")
    print("📊 Initializing vectorizers...")
    print("✅ Ready!")
    print("\n🌐 Access the web interface at: http://localhost:8080")
    print("🔧 API endpoint: http://localhost:8080/api/vectorize")
    print("📋 Health check: http://localhost:8080/health")
    print("\n Press Ctrl+C to stop the server")
    
    app.run(debug=True, host='0.0.0.0', port=8080)