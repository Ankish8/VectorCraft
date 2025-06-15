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
        
        # Get parameters
        vectorizer_type = request.form.get('vectorizer', 'standard')
        target_time = float(request.form.get('target_time', 60))
        strategy = request.form.get('strategy', 'auto')
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_{filename}")
        file.save(input_path)
        
        # Select vectorizer
        if vectorizer_type == 'optimized':
            vectorizer = optimized_vectorizer
        else:
            vectorizer = standard_vectorizer
        
        # Override strategy selection if specified
        if strategy != 'auto':
            original_select = vectorizer._select_strategy
            vectorizer._select_strategy = lambda *args: strategy
        
        # Vectorize image
        start_time = time.time()
        result = vectorizer.vectorize(input_path, target_time=target_time)
        processing_time = time.time() - start_time
        
        # Restore original strategy selection
        if strategy != 'auto':
            vectorizer._select_strategy = original_select
        
        # Save SVG result
        svg_filename = f"{unique_id}_result.svg"
        svg_path = os.path.join(app.config['RESULTS_FOLDER'], svg_filename)
        result.svg_builder.save(svg_path)
        
        # Get SVG content for preview
        svg_content = result.svg_builder.get_svg_string()
        
        # Convert SVG to base64 for embedding
        svg_b64 = base64.b64encode(svg_content.encode()).decode()
        
        # Get original image as base64 for comparison
        with open(input_path, 'rb') as img_file:
            img_b64 = base64.b64encode(img_file.read()).decode()
            img_ext = filename.rsplit('.', 1)[1].lower()
        
        # Clean up uploaded file
        os.remove(input_path)
        
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
            'download_url': url_for('download_result', filename=svg_filename),
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