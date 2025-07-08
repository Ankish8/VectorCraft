"""
Vectorization API endpoints
"""

import os
import time
import uuid
import json
import base64
import logging
from datetime import datetime
from io import BytesIO
from PIL import Image
import numpy as np

from flask import request, jsonify, current_app, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from . import api_bp
from blueprints.auth.utils import login_required_api, rate_limit_decorator
from database import db
from services.monitoring import system_logger
from services.security_service import security_service
from vectorcraft import HybridVectorizer, OptimizedVectorizer

logger = logging.getLogger(__name__)

# Initialize vectorizers
standard_vectorizer = HybridVectorizer()
optimized_vectorizer = OptimizedVectorizer()

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@api_bp.route('/vectorize', methods=['POST'])
@login_required_api
@rate_limit_decorator(max_attempts=30, cooldown_minutes=60)
def vectorize_image():
    """Main vectorization endpoint"""
    try:
        # Validate file upload
        if 'file' not in request.files:
            logger.warning(f"No file uploaded in vectorize request from {current_user.username}")
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            logger.warning(f"Empty filename in vectorize request from {current_user.username}")
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            logger.warning(f"Invalid file type in vectorize request from {current_user.username}")
            return jsonify({'error': 'Invalid file type'}), 400
        
        # Save uploaded file temporarily for security validation
        temp_upload_path = os.path.join(
            current_app.config['UPLOAD_FOLDER'], 
            f"temp_{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        )
        file.save(temp_upload_path)
        
        # Comprehensive security validation and sanitization
        is_valid, sanitized_path, error_message = security_service.validate_and_sanitize_upload(
            temp_upload_path, file.filename
        )
        
        if not is_valid:
            # Remove temporary file
            if os.path.exists(temp_upload_path):
                os.remove(temp_upload_path)
            logger.warning(f"File upload failed security validation for {current_user.username}: {error_message}")
            return jsonify({'error': f'File upload failed security validation: {error_message}'}), 400
        
        # Use sanitized file and secure filename
        filename = secure_filename(file.filename)
        upload_path = sanitized_path
        
        # Log vectorization start
        file_size = os.path.getsize(upload_path)
        system_logger.info('vectorization', f'Vectorization started by {current_user.username}',
                          user_email=current_user.email, 
                          details={'filename': filename, 'file_size': file_size})
        
        # Validate strategy parameter
        valid_strategies = ['vtracer_high_fidelity', 'experimental_v2', 'vtracer_experimental']
        strategy = request.form.get('strategy', 'vtracer_high_fidelity')
        if strategy not in valid_strategies:
            logger.warning(f"Invalid strategy selected by {current_user.username}: {strategy}")
            strategy = 'vtracer_high_fidelity'
        
        # Extract vectorization parameters
        vectorization_params = _extract_vectorization_params(request.form)
        
        # Process the image
        result = _process_vectorization(
            upload_path, 
            filename, 
            strategy, 
            vectorization_params,
            request.form
        )
        
        # Save result and update database
        svg_filename, download_url = _save_vectorization_result(
            result, 
            filename, 
            strategy, 
            file_size,
            request.form
        )
        
        # Clean up uploaded file
        if os.path.exists(upload_path):
            os.remove(upload_path)
        
        # Log successful completion
        system_logger.info('vectorization', f'Vectorization completed successfully',
                          user_email=current_user.email,
                          details={
                              'filename': filename,
                              'processing_time': result.processing_time,
                              'strategy_used': result.strategy_used,
                              'quality_score': result.quality_score,
                              'svg_filename': svg_filename,
                              'file_size': file_size
                          })
        
        return _format_vectorization_response(result, filename, download_url)
        
    except Exception as e:
        # Clean up files on error
        if 'upload_path' in locals() and os.path.exists(upload_path):
            os.remove(upload_path)
        
        # Log vectorization error
        system_logger.error('vectorization', f'Vectorization failed: {str(e)}',
                          user_email=current_user.email,
                          details={
                              'filename': file.filename if 'file' in locals() and file else 'unknown',
                              'error_message': str(e)
                          })
        
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500


@api_bp.route('/extract-palettes', methods=['POST'])
@login_required_api
def extract_palettes():
    """Extract color palettes from uploaded image"""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file'}), 400
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())
        filename_with_id = f"{unique_id}_{filename}"
        input_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename_with_id)
        file.save(input_path)
        
        # Load image for palette extraction
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
        logger.error(f"Palette extraction error: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/palette-preview', methods=['POST'])
@login_required_api
def generate_palette_preview():
    """Generate preview with selected palette"""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file'}), 400
        
        # Get selected palette
        selected_palette_json = request.form.get('selected_palette')
        if not selected_palette_json:
            return jsonify({'error': 'No palette selected'}), 400
        
        selected_palette = json.loads(selected_palette_json)
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())
        filename_with_id = f"{unique_id}_{filename}"
        input_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename_with_id)
        file.save(input_path)
        
        # Load image for preview generation
        image = Image.open(input_path)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        image_array = np.array(image)
        
        # Generate preview using experimental strategy
        from vectorcraft.strategies.experimental_vtracer_v3 import ExperimentalVTracerV3Strategy
        experimental_strategy = ExperimentalVTracerV3Strategy()
        
        preview_image = experimental_strategy.create_quantized_preview(image_array, selected_palette)
        
        # Convert preview back to PIL Image and encode as base64
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
        logger.error(f"Palette preview error: {e}")
        return jsonify({'error': str(e)}), 500


def _extract_vectorization_params(form_data):
    """Extract vectorization parameters from form data"""
    return {
        'filter_speckle': int(form_data.get('filter_speckle', 4)),
        'color_precision': int(form_data.get('color_precision', 8)),
        'layer_difference': int(form_data.get('layer_difference', 8)),
        'corner_threshold': int(form_data.get('corner_threshold', 90)),
        'length_threshold': float(form_data.get('length_threshold', 1.0)),
        'splice_threshold': int(form_data.get('splice_threshold', 20)),
        'curve_fitting': form_data.get('curve_fitting', 'spline')
    }


def _process_vectorization(upload_path, filename, strategy, vectorization_params, form_data):
    """Process vectorization with given parameters"""
    # Use optimized vectorization approach
    vectorizer = optimized_vectorizer
    target_time = float(form_data.get('target_time', 60))
    
    # Set custom VTracer parameters 
    if hasattr(vectorizer, 'real_vtracer') and vectorizer.real_vtracer.available:
        vectorizer.real_vtracer.set_custom_parameters(vectorization_params)
        logger.debug(f"Set VTracer parameters: {vectorization_params}")
    
    # Override strategy selection for high quality results
    if hasattr(vectorizer, 'adaptive_optimizer'):
        original_optimize = vectorizer.adaptive_optimizer.optimize_strategy_selection
        vectorizer.adaptive_optimizer.optimize_strategy_selection = lambda metadata, elapsed: strategy
    
    logger.info(f"Using {strategy} strategy for {filename} (User: {current_user.username})")
    
    # Check if palette-based vectorization is requested
    use_palette = form_data.get('use_palette', 'false').lower() == 'true'
    selected_palette = None
    
    if use_palette and form_data.get('selected_palette'):
        try:
            selected_palette = json.loads(form_data.get('selected_palette'))
            logger.debug(f"Using custom palette with {len(selected_palette)} colors")
        except Exception as e:
            logger.warning(f"Failed to parse selected palette: {e}, using standard vectorization")
            use_palette = False
    
    # Vectorize image
    start_time = time.time()
    
    if use_palette and selected_palette and strategy == 'experimental':
        result = _process_palette_vectorization(upload_path, selected_palette)
    else:
        result = vectorizer.vectorize(upload_path, target_time=target_time)
    
    # Restore original strategy selection
    if hasattr(vectorizer, 'adaptive_optimizer'):
        vectorizer.adaptive_optimizer.optimize_strategy_selection = original_optimize
    
    # Clear custom VTracer parameters for next request
    if hasattr(vectorizer, 'real_vtracer') and vectorizer.real_vtracer.available:
        vectorizer.real_vtracer.custom_params = None
    
    return result


def _process_palette_vectorization(upload_path, selected_palette):
    """Process vectorization with custom palette"""
    from vectorcraft.strategies.experimental_vtracer_v3 import ExperimentalVTracerV3Strategy
    
    # Load image for palette-based processing
    image = Image.open(upload_path)
    if image.mode != 'RGB':
        image = image.convert('RGB')
    image_array = np.array(image)
    
    # Use experimental strategy with palette
    experimental_strategy = ExperimentalVTracerV3Strategy()
    palette_result = experimental_strategy.vectorize_with_palette(
        image_array, selected_palette, None, None
    )
    
    # Create a result-like object
    class ImageMetadata:
        def __init__(self, image):
            self.width = image.width
            self.height = image.height
            self.edge_density = 0.5
            self.text_probability = 0.1
            self.geometric_probability = 0.8
            self.gradient_probability = 0.2
    
    class PaletteResult:
        def __init__(self, svg_builder, processing_time, image):
            self.svg_builder = svg_builder
            self.processing_time = processing_time
            self.strategy_used = f"experimental_palette_{len(selected_palette)}_colors"
            self.quality_score = 0.85
            self.metadata = {
                'content_type': 'palette_based',
                'num_elements': len(svg_builder.elements) if hasattr(svg_builder, 'elements') else 0,
                'palette_colors': len(selected_palette),
                'image_metadata': ImageMetadata(image),
                'performance_stats': {}
            }
    
    return PaletteResult(palette_result, time.time() - start_time, image)


def _save_vectorization_result(result, filename, strategy, file_size, form_data):
    """Save vectorization result and update database"""
    unique_id = str(uuid.uuid4())
    
    # Create result filenames
    use_palette = form_data.get('use_palette', 'false').lower() == 'true'
    selected_palette = None
    
    if use_palette and form_data.get('selected_palette'):
        try:
            selected_palette = json.loads(form_data.get('selected_palette'))
        except:
            pass
    
    version_suffix = "_v1.0.0-experimental" if strategy == 'experimental' else ""
    palette_suffix = f"_palette_{len(selected_palette)}colors" if use_palette and selected_palette else ""
    svg_filename = f"{unique_id}_result{version_suffix}{palette_suffix}.svg"
    svg_path = os.path.join(current_app.config['RESULTS_FOLDER'], svg_filename)
    
    # Also save to output folder with timestamp
    timestamp = int(time.time())
    output_filename = f"{timestamp}_{strategy}_result.svg"
    output_path = os.path.join("output", output_filename)
    os.makedirs("output", exist_ok=True)
    
    # Save the SVG result
    if hasattr(result, 'svg_builder') and result.svg_builder:
        result.svg_builder.save(svg_path)
        result.svg_builder.save(output_path)
    else:
        with open(svg_path, 'w') as f:
            f.write(result.get_svg_string())
        with open(output_path, 'w') as f:
            f.write(result.get_svg_string())
    
    # Record upload in database
    try:
        db.record_upload(
            user_id=int(current_user.id),
            filename=f"{unique_id}_{filename}",
            original_filename=filename,
            file_size=file_size,
            svg_filename=svg_filename,
            processing_time=result.processing_time,
            strategy_used=result.strategy_used
        )
        logger.info(f"Recorded upload for user {current_user.username}")
    except Exception as e:
        logger.error(f"Failed to record upload: {e}")
    
    download_url = url_for('main.download_result', filename=svg_filename)
    return svg_filename, download_url


def _format_vectorization_response(result, filename, download_url):
    """Format vectorization response"""
    # Get SVG content
    if hasattr(result, 'svg_builder') and result.svg_builder:
        svg_content = result.svg_builder.get_svg_string()
    else:
        svg_content = result.get_svg_string()
    
    # Convert SVG to base64 for embedding
    svg_b64 = base64.b64encode(svg_content.encode()).decode()
    
    return jsonify({
        'success': True,
        'processing_time': result.processing_time,
        'strategy_used': result.strategy_used,
        'quality_score': result.quality_score,
        'num_elements': result.metadata.get('num_elements', 0),
        'content_type': result.metadata.get('content_type', 'standard'),
        'svg_content': svg_content,
        'svg_b64': svg_b64,
        'download_url': download_url,
        'metadata': {
            'image_size': f"{result.metadata['image_metadata'].width}x{result.metadata['image_metadata'].height}",
            'edge_density': result.metadata['image_metadata'].edge_density,
            'text_probability': result.metadata['image_metadata'].text_probability,
            'geometric_probability': result.metadata['image_metadata'].geometric_probability,
            'gradient_probability': result.metadata['image_metadata'].gradient_probability,
            'performance_stats': result.metadata.get('performance_stats', {})
        }
    })