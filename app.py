#!/usr/bin/env python3
"""
VectorCraft - Professional Vector Conversion with Authentication
Flask web application for high-quality image to vector conversion
"""

import os
import time
import uuid
import logging
import secrets
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
from flask import Flask, render_template, request, jsonify, send_file, url_for, redirect, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import base64
from io import BytesIO
from PIL import Image

from vectorcraft import HybridVectorizer, OptimizedVectorizer
from database import db
from services.email_service import email_service
from services.paypal_service import paypal_service
from services.monitoring import health_monitor, system_logger, alert_manager
from email_queue_processor import start_email_processor

app = Flask(__name__)
# Use environment variable for secret key, generate secure fallback
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULTS_FOLDER'] = 'results'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Setup logging for production
if os.getenv('FLASK_ENV') == 'production':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('vectorcraft.log'),
            logging.StreamHandler()
        ]
    )
    app.logger.setLevel(logging.INFO)
else:
    logging.basicConfig(level=logging.DEBUG)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access VectorCraft.'
login_manager.login_message_category = 'info'

# Create directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)
os.makedirs('static/images', exist_ok=True)

# Initialize vectorizers
standard_vectorizer = HybridVectorizer()
optimized_vectorizer = OptimizedVectorizer()

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

class User(UserMixin):
    """User class for Flask-Login"""
    def __init__(self, user_data):
        self.id = str(user_data['id'])
        self.username = user_data['username']
        self.email = user_data['email']
        self.created_at = user_data['created_at']
        self.last_login = user_data['last_login']

@login_manager.user_loader
def load_user(user_id):
    """Load user from database"""
    user_data = db.get_user_by_id(int(user_id))
    if user_data:
        return User(user_data)
    return None

# Security headers for production
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Add HTTPS security headers in production
    if os.getenv('FLASK_ENV') == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    return response

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Admin authentication decorator
def admin_required(f):
    """Decorator to require admin authentication"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            # For API endpoints, return JSON error instead of redirect
            if request.path.startswith('/admin/api/'):
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            flash('Please log in to access admin features.', 'error')
            return redirect(url_for('login', next=request.url))
        
        # Check if user is admin (username 'admin' or email contains 'admin')
        if current_user.username != 'admin' and 'admin' not in current_user.email.lower():
            # For API endpoints, return JSON error instead of redirect
            if request.path.startswith('/admin/api/'):
                return jsonify({'success': False, 'error': 'Admin access required'}), 403
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

# Global error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    app.logger.warning(f"404 error: {request.url}")
    return render_template('error.html', 
                         code=404, 
                         message="The page you're looking for doesn't exist.",
                         title="Page Not Found"), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    app.logger.error(f"500 error: {error}")
    return render_template('error.html', 
                         code=500, 
                         message="An internal server error occurred. Please try again later.",
                         title="Server Error"), 500

@app.errorhandler(413)
def too_large(error):
    """Handle file too large errors"""
    app.logger.warning(f"File too large error: {error}")
    return render_template('error.html',
                         code=413,
                         message="The file you uploaded is too large. Maximum size is 16MB.",
                         title="File Too Large"), 413

@app.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    return '', 204

@app.route('/')
def index():
    """Main page - show landing page if not authenticated"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/app')
@login_required
def vectorcraft_app():
    """Main VectorCraft application interface"""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    # Check for message parameter
    message = request.args.get('message')
    if message == 'credentials_sent':
        flash('Login credentials have been sent to your email. Please check your inbox.', 'info')
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = bool(request.form.get('remember_me'))
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('login.html', error='Please enter both username and password.')
        
        # Authenticate user
        user_data = db.authenticate_user(username, password)
        if user_data:
            user = User(user_data)
            login_user(user, remember=remember)
            session['login_success'] = True
            
            # Redirect to next page or appropriate dashboard
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            
            # Check if user is admin and redirect to admin dashboard
            if user_data['username'] == 'admin' or 'admin' in user_data['email'].lower():
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
            return render_template('login.html', error='Invalid username or password.')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout user"""
    logout_user()
    session.clear()  # Clear all session data
    flash('You have been signed out successfully.', 'info')
    return redirect(url_for('index'))  # Redirect to landing page

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard with upload history and stats"""
    # Get user's upload history
    uploads = db.get_user_uploads(current_user.id, limit=20)
    
    # Get user's statistics
    stats = db.get_upload_stats(current_user.id)
    
    # Clear login success message after showing dashboard
    session.pop('login_success', None)
    
    return render_template('dashboard.html', uploads=uploads, stats=stats)

@app.route('/api/extract-palettes', methods=['POST'])
@login_required
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
@login_required
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
@login_required
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
        
        # Log vectorization start
        system_logger.info('vectorization', f'Vectorization started by {current_user.username}',
                          user_email=current_user.email, 
                          details={'filename': file.filename, 'file_size': len(file.read())})
        file.seek(0)  # Reset file pointer after reading for size
        
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
        
        # Get file size for database recording
        file_size = os.path.getsize(input_path)
        
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
        
        print(f"🎯 WEB INTERFACE: Using {strategy} strategy for {filename} (User: {current_user.username})")
        
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
        
        # Record upload in database
        try:
            db.record_upload(
                user_id=int(current_user.id),
                filename=f"{unique_id}_{filename}",
                original_filename=filename,
                file_size=file_size,
                svg_filename=svg_filename,
                processing_time=processing_time,
                strategy_used=result.strategy_used
            )
            print(f"📝 Recorded upload for user {current_user.username}")
            
            # Log successful vectorization completion
            system_logger.info('vectorization', f'Vectorization completed successfully',
                              user_email=current_user.email,
                              details={
                                  'filename': filename,
                                  'processing_time': processing_time,
                                  'strategy_used': result.strategy_used,
                                  'quality_score': result.quality_score,
                                  'svg_filename': svg_filename,
                                  'file_size': file_size
                              })
        except Exception as e:
            print(f"❌ Failed to record upload: {e}")
            # Log database error
            system_logger.error('vectorization', f'Failed to record upload in database: {str(e)}',
                              user_email=current_user.email,
                              details={'filename': filename})
        
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
        
        # Log vectorization error
        system_logger.error('vectorization', f'Vectorization failed: {str(e)}',
                          user_email=current_user.email,
                          details={
                              'filename': file.filename if 'file' in locals() and file else 'unknown',
                              'error_message': str(e)
                          })
        
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/api/demo/<demo_type>')
@login_required
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
@login_required
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

@app.route('/results/<filename>')
@login_required
def view_result(filename):
    """View SVG result file for preview"""
    try:
        file_path = os.path.join(app.config['RESULTS_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, mimetype='image/svg+xml')
        else:
            return "File not found", 404
    except Exception as e:
        return f"View error: {str(e)}", 500

@app.route('/buy')
def buy_now():
    """Buy now page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('buy.html')

@app.route('/api/create-paypal-order', methods=['POST'])
def create_paypal_order():
    """Create PayPal order for VectorCraft purchase"""
    transaction_id = None
    try:
        data = request.get_json()
        email = data.get('email')
        amount = data.get('amount', 49.00)
        
        if not email:
            system_logger.warning('payment', 'PayPal order creation failed: No email provided')
            return jsonify({'error': 'Email is required'}), 400
        
        # Generate transaction ID for tracking
        transaction_id = f"VC_{int(time.time())}_{secrets.token_hex(4)}"
        
        # Log transaction creation
        system_logger.info('payment', f'Creating PayPal order for {email}', 
                          user_email=email, transaction_id=transaction_id,
                          details={'amount': amount, 'email': email})
        
        # Create initial transaction record
        db.log_transaction(
            transaction_id=transaction_id,
            email=email,
            amount=amount,
            currency='USD',
            status='pending'
        )
        
        # Create PayPal order
        order_result = paypal_service.create_order(amount=amount, customer_email=email)
        
        if not order_result or not order_result.get('success'):
            # Update transaction with failure
            db.update_transaction(transaction_id, 
                                status='failed', 
                                error_message='Failed to create PayPal order')
            
            system_logger.error('payment', 'PayPal order creation failed', 
                              user_email=email, transaction_id=transaction_id,
                              details={'error': 'PayPal service error'})
            return jsonify({'error': 'Failed to create PayPal order'}), 500
        
        # Update transaction with PayPal order ID
        db.update_transaction(transaction_id, 
                            paypal_order_id=order_result['order_id'],
                            status='awaiting_payment')
        
        # Store order info in session for later processing
        session['pending_order'] = {
            'email': email,
            'amount': amount,
            'paypal_order_id': order_result['order_id'],
            'transaction_id': transaction_id,
            'created_at': time.time()
        }
        
        system_logger.info('payment', f'PayPal order created successfully: {order_result["order_id"]}',
                          user_email=email, transaction_id=transaction_id)
        
        return jsonify({
            'success': True,
            'order_id': order_result['order_id'],
            'approval_url': order_result['approval_url']
        })
        
    except Exception as e:
        error_msg = f"PayPal order creation error: {e}"
        print(f"❌ {error_msg}")
        
        if transaction_id:
            db.update_transaction(transaction_id, 
                                status='error', 
                                error_message=str(e))
            system_logger.error('payment', error_msg, transaction_id=transaction_id)
        else:
            system_logger.error('payment', error_msg)
            
        return jsonify({'error': str(e)}), 500

@app.route('/api/capture-paypal-order', methods=['POST'])
def capture_paypal_order():
    """Capture PayPal payment and create user account"""
    transaction_id = None
    try:
        system_logger.info('payment', 'Processing PayPal payment capture')
        data = request.get_json()
        order_id = data.get('order_id')
        
        if not order_id:
            system_logger.warning('payment', 'PayPal capture failed: No order ID provided')
            return jsonify({'error': 'Order ID is required'}), 400
        
        # Get pending order from session
        pending_order = session.get('pending_order')
        transaction_id = pending_order.get('transaction_id') if pending_order else None
        
        if not pending_order or pending_order['paypal_order_id'] != order_id:
            system_logger.error('payment', 'Invalid order session for PayPal capture',
                              transaction_id=transaction_id,
                              details={'order_id': order_id})
            return jsonify({'error': 'Invalid order session'}), 400
        
        system_logger.info('payment', f'Capturing PayPal payment for order {order_id}',
                          transaction_id=transaction_id)
        
        # Capture PayPal payment
        capture_result = paypal_service.capture_order(order_id)
        
        if not capture_result or not capture_result.get('success'):
            # Update transaction with failure
            if transaction_id:
                db.update_transaction(transaction_id, 
                                    status='failed', 
                                    error_message='PayPal capture failed')
            
            system_logger.error('payment', 'PayPal capture failed',
                              transaction_id=transaction_id,
                              details={'order_id': order_id, 'capture_result': capture_result})
            return jsonify({'error': 'Failed to capture PayPal payment'}), 500
        
        # Use email from capture result if available, otherwise from session
        paypal_email = capture_result.get('payer_email') or pending_order['email']
        amount = capture_result.get('amount', pending_order['amount'])
        
        # LIVE ENVIRONMENT: Use actual PayPal payer email
        email = paypal_email
        
        # Generate username and password
        import random
        username = f"user_{random.randint(10000, 99999)}"
        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        
        system_logger.info('payment', f'Creating user account for {email}',
                          user_email=email, transaction_id=transaction_id,
                          details={'username': username, 'amount': amount})
        
        # Create user account
        try:
            # Check if user already exists
            existing_user = db.get_user_by_email(email)
            if existing_user:
                # Update transaction with error
                if transaction_id:
                    db.update_transaction(transaction_id, 
                                        status='failed', 
                                        error_message=f'User with email {email} already exists')
                
                system_logger.warning('payment', f'User account already exists: {email}',
                                     user_email=email, transaction_id=transaction_id)
                return jsonify({'error': f'User with email {email} already exists'}), 400
            
            user_id = db.create_user(username, email, password)
            
            if not user_id:
                # Update transaction with error
                if transaction_id:
                    db.update_transaction(transaction_id, 
                                        status='failed', 
                                        error_message='Failed to create user account')
                
                system_logger.error('payment', 'User creation returned None/False',
                                  user_email=email, transaction_id=transaction_id)
                return jsonify({'error': 'Failed to create user account - database returned None'}), 500
                
        except Exception as e:
            # Update transaction with error
            if transaction_id:
                db.update_transaction(transaction_id, 
                                    status='failed', 
                                    error_message=f'User creation failed: {str(e)}')
            
            system_logger.error('payment', f'User creation exception: {str(e)}',
                              user_email=email, transaction_id=transaction_id)
            return jsonify({'error': f'User creation failed: {str(e)}'}), 500
        
        # Update transaction with success and user details
        if transaction_id:
            db.update_transaction(transaction_id,
                                status='completed',
                                username=username,
                                paypal_payment_id=capture_result.get('payment_id'),
                                user_created=True,
                                completed_at=True,
                                metadata={
                                    'paypal_transaction_id': capture_result.get('transaction_id'),
                                    'payer_email': email,
                                    'amount': amount,
                                    'currency': 'USD'
                                })
        
        # Prepare order details
        order_details = {
            'amount': amount,
            'order_id': order_id,
            'payment_id': capture_result.get('payment_id'),
            'transaction_id': capture_result.get('transaction_id'),
            'username': username,
            'payer_email': email
        }
        
        # Send emails
        system_logger.info('email', f'Sending purchase confirmation to {email}',
                          user_email=email, transaction_id=transaction_id)
        confirm_result = email_service.send_purchase_confirmation(email, order_details)
        
        system_logger.info('email', f'Sending credentials email to {email}',
                          user_email=email, transaction_id=transaction_id)
        email_sent = email_service.send_credentials_email(email, username, password, order_details)
        
        # Update transaction with email status
        if transaction_id:
            db.update_transaction(transaction_id, email_sent=email_sent)
        
        if not email_sent:
            system_logger.warning('email', f'Failed to send credentials email to {email}',
                                 user_email=email, transaction_id=transaction_id)
        else:
            system_logger.info('email', f'Credentials email sent successfully to {email}',
                             user_email=email, transaction_id=transaction_id)
        
        # Send admin notification
        admin_result = email_service.send_admin_notification(
            "New PayPal Purchase",
            f"New customer: {email} (username: {username})\nAmount: ${amount:.2f}\nPayPal Order: {order_id}\nTransaction: {capture_result.get('transaction_id')}"
        )
        
        # Trigger email automations for purchase event
        try:
            trigger_email_automations('purchase', {
                'email': email,
                'username': username,
                'password': password,  # Include password for credentials email
                'amount': amount,
                'order_id': order_id,
                'transaction_id': transaction_id
            })
        except Exception as e:
            system_logger.warning('email', f'Failed to trigger email automations: {str(e)}',
                                 user_email=email, transaction_id=transaction_id)
        
        # Log successful payment completion
        system_logger.info('payment', f'Payment completed successfully - ${amount:.2f}',
                          user_email=email, transaction_id=transaction_id,
                          details={
                              'order_id': order_id,
                              'username': username,
                              'amount': amount,
                              'email_sent': email_sent
                          })
        
        # Clear session
        session.pop('pending_order', None)
        
        return jsonify({
            'success': True,
            'message': 'Payment completed successfully',
            'username': username,
            'email_sent': email_sent,
            'order_id': order_id,
            'debug_email': email  # Add debug info
        })
        
    except Exception as e:
        error_msg = f"PayPal capture error: {str(e)}"
        
        # Update transaction with error if we have transaction_id
        if transaction_id:
            db.update_transaction(transaction_id, 
                                status='error', 
                                error_message=str(e))
        
        # Log error for monitoring
        system_logger.error('payment', error_msg, 
                           transaction_id=transaction_id,
                           details={'order_id': order_id if 'order_id' in locals() else 'unknown'})
        
        app.logger.error(f"PayPal capture failed - Order: {order_id if 'order_id' in locals() else 'unknown'}, Error: {str(e)}")
        
        return jsonify({'error': str(e)}), 500

@app.route('/payment/success')
def payment_success():
    """PayPal payment success redirect"""
    return render_template('payment_success.html')

@app.route('/payment/cancel')
def payment_cancel():
    """PayPal payment cancel redirect"""
    return render_template('payment_cancel.html')

@app.route('/api/create-order', methods=['POST'])
def create_order_legacy():
    """Legacy order creation endpoint for testing/simulation"""
    try:
        data = request.get_json()
        email = data.get('email')
        username = data.get('username', '')
        amount = data.get('amount', 49.00)
        simulate = data.get('simulate', True)  # Default to simulation for legacy
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Generate username if not provided
        if not username:
            import random
            username = f"user_{random.randint(10000, 99999)}"
        
        # Generate secure password
        import secrets
        import string
        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        
        # Create user account
        try:
            user_id = db.create_user(username, email, password)
            if not user_id:
                return jsonify({'error': 'Failed to create user account'}), 500
        except Exception as e:
            return jsonify({'error': f'User creation failed: {str(e)}'}), 500
        
        # Send credentials email
        order_details = {
            'amount': amount,
            'order_id': f"SIM_{int(time.time())}_{user_id}",
            'username': username
        }
        
        # Send purchase confirmation
        email_service.send_purchase_confirmation(email, order_details)
        
        # Send credentials email
        email_sent = email_service.send_credentials_email(email, username, password, order_details)
        
        if not email_sent:
            print(f"⚠️  Failed to send email to {email} - but user account created successfully")
        
        # Send admin notification
        email_service.send_admin_notification(
            "New Simulated Purchase",
            f"New customer: {email} (username: {username})\nAmount: ${amount:.2f}"
        )
        
        return jsonify({
            'success': True,
            'message': 'Order created successfully',
            'username': username,
            'email_sent': True
        })
        
    except Exception as e:
        print(f"❌ Order creation error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/clear-session')
def clear_session():
    """Clear session for testing"""
    logout_user()
    session.clear()
    return jsonify({
        'message': 'Session cleared',
        'authenticated': current_user.is_authenticated,
        'redirect_to': '/'
    })


@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0',
        'name': 'VectorCraft',
        'authentication': 'enabled',
        'authenticated': current_user.is_authenticated,
        'vectorizers': ['standard', 'advanced'],
        'supported_formats': list(ALLOWED_EXTENSIONS)
    })

# Email Tracking Routes
@app.route('/track/open/<tracking_id>')
def track_email_open(tracking_id):
    """Track email open event"""
    try:
        # Record the open event
        db.record_email_tracking(
            tracking_id=tracking_id,
            event_type='opened',
            user_agent=request.headers.get('User-Agent', ''),
            ip_address=request.remote_addr
        )
        
        # Return a 1x1 transparent pixel
        from flask import Response
        import base64
        
        # 1x1 transparent PNG pixel
        pixel_data = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAGAhQAAAg==')
        
        response = Response(pixel_data, mimetype='image/png')
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
        
    except Exception as e:
        print(f"Error tracking email open: {e}")
        # Still return the pixel even if tracking fails
        pixel_data = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAGAhQAAAg==')
        return Response(pixel_data, mimetype='image/png')

@app.route('/track/click/<tracking_id>')
def track_email_click(tracking_id):
    """Track email click event and redirect"""
    try:
        # Get the original URL from query parameters
        original_url = request.args.get('url', '')
        
        if original_url:
            # Record the click event
            db.record_email_tracking(
                tracking_id=tracking_id,
                event_type='clicked',
                user_agent=request.headers.get('User-Agent', ''),
                ip_address=request.remote_addr,
                metadata={'clicked_url': original_url}
            )
            
            # Redirect to the original URL
            return redirect(original_url)
        else:
            return "Invalid tracking link", 400
            
    except Exception as e:
        print(f"Error tracking email click: {e}")
        # Still redirect if tracking fails
        original_url = request.args.get('url', '')
        if original_url:
            return redirect(original_url)
        return "Invalid tracking link", 400

# Admin Dashboard Routes
@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard overview"""
    try:
        # Get system health status
        health_status = health_monitor.get_overall_status()
        
        # Get recent transactions
        recent_transactions = db.get_transactions(limit=10)
        
        # Get alert summary
        alert_summary = alert_manager.get_alert_summary()
        
        # Calculate daily metrics
        today_transactions = [tx for tx in recent_transactions if tx['created_at'].startswith(datetime.now().strftime('%Y-%m-%d'))]
        today_revenue = sum(float(tx['amount'] or 0) for tx in today_transactions if tx['status'] == 'completed')
        
        # Get error summary
        error_summary = system_logger.get_error_summary(hours=24)
        
        dashboard_data = {
            'health_status': health_status,
            'today_stats': {
                'revenue': today_revenue,
                'transactions': len(today_transactions),
                'success_rate': len([tx for tx in today_transactions if tx['status'] == 'completed']) / max(len(today_transactions), 1) * 100
            },
            'alert_summary': alert_summary,
            'error_summary': error_summary,
            'recent_transactions': recent_transactions[:5]
        }
        
        return render_template('admin/dashboard.html', data=dashboard_data)
        
    except Exception as e:
        system_logger.error('admin', f'Admin dashboard error: {str(e)}', user_email=current_user.email)
        flash(f'Dashboard error: {str(e)}', 'error')
        return render_template('admin/dashboard.html', data={})

@app.route('/admin/api/health')
@admin_required
def admin_api_health():
    """API endpoint for system health status"""
    try:
        health_results = health_monitor.check_all_components()
        overall_status = health_monitor.get_overall_status()
        
        response = jsonify({
            'success': True,
            'health_results': health_results,
            'overall_status': overall_status,
            'timestamp': datetime.now().isoformat()
        })
        
        # Add cache-busting headers
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/transactions')
@admin_required  
def admin_api_transactions():
    """API endpoint for transaction data"""
    try:
        limit = request.args.get('limit', 50, type=int)
        status = request.args.get('status')
        email = request.args.get('email')
        
        transactions = db.get_transactions(limit=limit, status=status, email=email)
        
        return jsonify({
            'success': True,
            'transactions': transactions,
            'count': len(transactions)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/logs')
@admin_required
def admin_api_logs():
    """API endpoint for system logs"""
    try:
        limit = request.args.get('limit', 100, type=int)
        level = request.args.get('level')
        component = request.args.get('component')
        hours = request.args.get('hours', 24, type=int)
        
        logs = system_logger.get_recent_logs(hours=hours, level=level, component=component, limit=limit)
        
        return jsonify({
            'success': True,
            'logs': logs,
            'count': len(logs)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/alerts')
@admin_required
def admin_api_alerts():
    """API endpoint for admin alerts"""
    try:
        resolved = request.args.get('resolved')
        if resolved is not None:
            resolved = resolved.lower() == 'true'
        
        alerts = db.get_alerts(resolved=resolved)
        alert_summary = alert_manager.get_alert_summary()
        
        return jsonify({
            'success': True,
            'alerts': alerts,
            'summary': alert_summary
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/alerts/<int:alert_id>/resolve', methods=['POST'])
@admin_required
def admin_api_resolve_alert(alert_id):
    """API endpoint to resolve an alert"""
    try:
        success = alert_manager.resolve_alert(alert_id, current_user.email)
        
        if success:
            return jsonify({'success': True, 'message': 'Alert resolved'})
        else:
            return jsonify({'success': False, 'error': 'Failed to resolve alert'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/analytics')
@admin_required
def admin_api_analytics():
    """API endpoint for analytics data"""
    try:
        # Get transaction analytics
        transactions = db.get_transactions(limit=100)
        
        # Calculate metrics
        completed_transactions = [tx for tx in transactions if tx['status'] == 'completed']
        total_revenue = sum(float(tx['amount'] or 0) for tx in completed_transactions)
        
        # Group by date for charts
        from collections import defaultdict
        daily_stats = defaultdict(lambda: {'revenue': 0, 'count': 0})
        
        for tx in completed_transactions:
            date = tx['created_at'][:10]  # Get YYYY-MM-DD
            daily_stats[date]['revenue'] += float(tx['amount'] or 0)
            daily_stats[date]['count'] += 1
        
        # Format for charts
        chart_data = [
            {
                'date': date,
                'revenue': stats['revenue'],
                'transactions': stats['count']
            }
            for date, stats in sorted(daily_stats.items())
        ]
        
        return jsonify({
            'success': True,
            'analytics': {
                'total_revenue': total_revenue,
                'total_transactions': len(completed_transactions),
                'avg_order_value': total_revenue / max(len(completed_transactions), 1),
                'daily_data': chart_data[-7:]  # Last 7 days
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/smtp')
@admin_required
def admin_api_smtp_get():
    """API endpoint to get current SMTP settings"""
    try:
        settings = db.get_smtp_settings(decrypt_password=False)  # Don't decrypt for security
        
        return jsonify({
            'success': True,
            'settings': settings
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/smtp/save', methods=['POST'])
@admin_required
def admin_api_smtp_save():
    """API endpoint to save SMTP settings"""
    try:
        # Get form data
        smtp_server = request.form.get('smtp_server', '').strip()
        smtp_port = request.form.get('smtp_port', 587, type=int)
        username = request.form.get('smtp_username', '').strip()
        password = request.form.get('smtp_password', '').strip()
        from_email = request.form.get('from_email', '').strip()
        use_tls = request.form.get('use_tls') == 'on'
        use_ssl = request.form.get('use_ssl') == 'on'
        
        # Validate required fields
        if not all([smtp_server, username, password, from_email]):
            return jsonify({'success': False, 'error': 'All fields are required'}), 400
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, username) or not re.match(email_pattern, from_email):
            return jsonify({'success': False, 'error': 'Invalid email format'}), 400
        
        # Save settings
        db.save_smtp_settings(
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            username=username,
            password=password,
            from_email=from_email,
            use_tls=use_tls,
            use_ssl=use_ssl
        )
        
        # Log the configuration change
        system_logger.log(
            level='INFO',
            component='admin',
            message='SMTP configuration updated',
            user_email=current_user.email,
            details={'smtp_server': smtp_server, 'smtp_port': smtp_port, 'from_email': from_email}
        )
        
        return jsonify({
            'success': True,
            'message': 'SMTP configuration saved successfully'
        })
        
    except Exception as e:
        system_logger.log(
            level='ERROR',
            component='admin',
            message=f'Failed to save SMTP configuration: {str(e)}',
            user_email=current_user.email
        )
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/smtp/test', methods=['POST'])
@admin_required
def admin_api_smtp_test():
    """API endpoint to test SMTP connection"""
    try:
        # Get form data
        smtp_server = request.form.get('smtp_server', '').strip()
        smtp_port = request.form.get('smtp_port', 587, type=int)
        username = request.form.get('smtp_username', '').strip()
        password = request.form.get('smtp_password', '').strip()
        use_tls = request.form.get('use_tls') == 'on'
        use_ssl = request.form.get('use_ssl') == 'on'
        
        # Validate required fields
        if not all([smtp_server, username, password]):
            return jsonify({'success': False, 'error': 'Server, username, and password are required for testing'}), 400
        
        # Test connection
        success, message = db.test_smtp_connection(
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            username=username,
            password=password,
            use_tls=use_tls,
            use_ssl=use_ssl
        )
        
        # Log the test
        system_logger.log(
            level='INFO' if success else 'WARNING',
            component='admin',
            message=f'SMTP connection test: {message}',
            user_email=current_user.email,
            details={'smtp_server': smtp_server, 'smtp_port': smtp_port}
        )
        
        return jsonify({
            'success': success,
            'message': message
        })
        
    except Exception as e:
        system_logger.log(
            level='ERROR',
            component='admin',
            message=f'SMTP test failed with exception: {str(e)}',
            user_email=current_user.email
        )
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/paypal')
@admin_required
def admin_api_paypal_get():
    """API endpoint to get current PayPal settings"""
    try:
        settings = db.get_paypal_settings(decrypt_secret=False)  # Don't decrypt for security
        
        return jsonify({
            'success': True,
            'settings': settings
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/paypal/save', methods=['POST'])
@admin_required
def admin_api_paypal_save():
    """API endpoint to save PayPal settings"""
    try:
        # Get form data
        client_id = request.form.get('paypal_client_id', '').strip()
        client_secret = request.form.get('paypal_client_secret', '').strip()
        environment = request.form.get('paypal_environment', 'sandbox').strip()
        
        # Validate required fields
        if not all([client_id, client_secret]):
            return jsonify({'success': False, 'error': 'Client ID and Client Secret are required'}), 400
        
        # Validate environment
        if environment not in ['sandbox', 'live']:
            return jsonify({'success': False, 'error': 'Environment must be either sandbox or live'}), 400
        
        # Save settings
        db.save_paypal_settings(
            client_id=client_id,
            client_secret=client_secret,
            environment=environment
        )
        
        # Log the configuration change
        system_logger.log(
            level='INFO',
            component='admin',
            message='PayPal configuration updated',
            user_email=current_user.email,
            details={'environment': environment, 'client_id': client_id[:20] + '...'}
        )
        
        return jsonify({
            'success': True,
            'message': 'PayPal configuration saved successfully'
        })
        
    except Exception as e:
        system_logger.log(
            level='ERROR',
            component='admin',
            message=f'Failed to save PayPal configuration: {str(e)}',
            user_email=current_user.email
        )
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/paypal/test', methods=['POST'])
@admin_required
def admin_api_paypal_test():
    """API endpoint to test PayPal connection"""
    try:
        # Get form data
        client_id = request.form.get('paypal_client_id', '').strip()
        client_secret = request.form.get('paypal_client_secret', '').strip()
        environment = request.form.get('paypal_environment', 'sandbox').strip()
        
        # Validate required fields
        if not all([client_id, client_secret]):
            return jsonify({'success': False, 'error': 'Client ID and Client Secret are required for testing'}), 400
        
        # Validate environment
        if environment not in ['sandbox', 'live']:
            return jsonify({'success': False, 'error': 'Environment must be either sandbox or live'}), 400
        
        # Test connection
        success, message = db.test_paypal_connection(
            client_id=client_id,
            client_secret=client_secret,
            environment=environment
        )
        
        # Log the test
        system_logger.log(
            level='INFO' if success else 'WARNING',
            component='admin',
            message=f'PayPal connection test ({environment}): {message}',
            user_email=current_user.email,
            details={'environment': environment, 'client_id': client_id[:20] + '...'}
        )
        
        return jsonify({
            'success': success,
            'message': message
        })
        
    except Exception as e:
        system_logger.log(
            level='ERROR',
            component='admin',
            message=f'PayPal test failed with exception: {str(e)}',
            user_email=current_user.email
        )
        return jsonify({'success': False, 'error': str(e)}), 500

# Email Marketing API Endpoints
@app.route('/admin/api/email/templates')
@admin_required
def admin_api_email_templates():
    """API endpoint to get email templates"""
    try:
        category = request.args.get('category')
        templates = db.get_email_templates(category=category)
        
        return jsonify({
            'success': True,
            'templates': templates,
            'total': len(templates)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/email/templates', methods=['POST'])
@admin_required  
def admin_api_email_templates_create():
    """API endpoint to create email template"""
    try:
        data = request.get_json()
        
        if not data or not data.get('name') or not data.get('subject') or not data.get('content_html'):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        template_id = db.create_email_template(
            name=data['name'],
            subject=data['subject'],
            content_html=data['content_html'],
            content_json=data.get('content_json'),
            variables=data.get('variables'),
            description=data.get('description'),
            category=data.get('category', 'general')
        )
        
        if template_id:
            # Log the action
            system_logger.log(
                level='INFO',
                component='email',
                message=f'Email template created: {data["name"]}',
                user_email=current_user.email,
                details={'template_id': template_id, 'category': data.get('category', 'general')}
            )
            
            return jsonify({
                'success': True,
                'template_id': template_id,
                'message': 'Template created successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to create template'}), 500
            
    except Exception as e:
        system_logger.log(
            level='ERROR',
            component='email',
            message=f'Failed to create email template: {str(e)}',
            user_email=current_user.email
        )
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/email/templates/<int:template_id>')
@admin_required
def admin_api_email_template_get(template_id):
    """API endpoint to get specific email template"""
    try:
        template = db.get_email_template(template_id)
        
        if template:
            return jsonify({
                'success': True,
                'template': template
            })
        else:
            return jsonify({'success': False, 'error': 'Template not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/email/templates/<int:template_id>', methods=['PUT'])
@admin_required
def admin_api_email_template_update(template_id):
    """API endpoint to update email template"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        success = db.update_email_template(
            template_id=template_id,
            name=data.get('name'),
            subject=data.get('subject'),
            content_html=data.get('content_html'),
            content_json=data.get('content_json'),
            variables=data.get('variables'),
            description=data.get('description'),
            category=data.get('category')
        )
        
        if success:
            # Log the action
            system_logger.log(
                level='INFO',
                component='email',
                message=f'Email template updated: {template_id}',
                user_email=current_user.email,
                details={'template_id': template_id}
            )
            
            return jsonify({
                'success': True,
                'message': 'Template updated successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to update template or template not found'}), 404
            
    except Exception as e:
        system_logger.log(
            level='ERROR',
            component='email',
            message=f'Failed to update email template {template_id}: {str(e)}',
            user_email=current_user.email
        )
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/email/templates/<int:template_id>', methods=['DELETE'])
@admin_required
def admin_api_email_template_delete(template_id):
    """API endpoint to delete email template"""
    try:
        success = db.delete_email_template(template_id)
        
        if success:
            # Log the action
            system_logger.log(
                level='INFO',
                component='email',
                message=f'Email template deleted: {template_id}',
                user_email=current_user.email,
                details={'template_id': template_id}
            )
            
            return jsonify({
                'success': True,
                'message': 'Template deleted successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to delete template or template not found'}), 404
            
    except Exception as e:
        system_logger.log(
            level='ERROR',
            component='email',
            message=f'Failed to delete email template {template_id}: {str(e)}',
            user_email=current_user.email
        )
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/email/automations')
@admin_required
def admin_api_email_automations():
    """API endpoint to get email automations"""
    try:
        # Get ALL automations (both active and inactive) so user can manage them
        automations = db.get_email_automations(active_only=False)
        
        return jsonify({
            'success': True,
            'automations': automations,
            'total': len(automations)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/email/automations', methods=['POST'])
@admin_required  
def admin_api_email_automations_create():
    """API endpoint to create email automation"""
    try:
        data = request.get_json()
        
        required_fields = ['name', 'trigger_type', 'template_id']
        if not data or not all(field in data for field in required_fields):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        automation_id = db.create_email_automation(
            name=data['name'],
            trigger_type=data['trigger_type'],
            template_id=data['template_id'],
            delay_hours=data.get('delay_hours', 0),
            trigger_condition=data.get('trigger_condition'),
            description=data.get('description'),
            send_time=data.get('send_time')
        )
        
        if automation_id:
            # Log the action
            system_logger.log(
                level='INFO',
                component='email',
                message=f'Email automation created: {data["name"]}',
                user_email=current_user.email,
                details={'automation_id': automation_id, 'trigger_type': data['trigger_type']}
            )
            
            return jsonify({
                'success': True,
                'automation_id': automation_id,
                'message': 'Automation created successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to create automation'}), 500
            
    except Exception as e:
        system_logger.log(
            level='ERROR',
            component='email',
            message=f'Failed to create email automation: {str(e)}',
            user_email=current_user.email
        )
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/email/automations/<int:automation_id>')
@admin_required
def admin_api_email_automation_get(automation_id):
    """API endpoint to get specific email automation"""
    try:
        automation = db.get_email_automation(automation_id)
        
        if automation:
            return jsonify({
                'success': True,
                'automation': automation
            })
        else:
            return jsonify({'success': False, 'error': 'Automation not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/email/automations/<int:automation_id>', methods=['PUT'])
@admin_required
def admin_api_email_automation_update(automation_id):
    """API endpoint to update email automation"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        success = db.update_email_automation(
            automation_id=automation_id,
            name=data.get('name'),
            trigger_type=data.get('trigger_type'),
            template_id=data.get('template_id'),
            delay_hours=data.get('delay_hours'),
            trigger_condition=data.get('trigger_condition'),
            description=data.get('description'),
            send_time=data.get('send_time'),
            is_active=data.get('is_active')
        )
        
        if success:
            # Log the action
            system_logger.log(
                level='INFO',
                component='email',
                message=f'Email automation updated: {automation_id}',
                user_email=current_user.email,
                details={'automation_id': automation_id}
            )
            
            return jsonify({
                'success': True,
                'message': 'Automation updated successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to update automation or automation not found'}), 404
            
    except Exception as e:
        system_logger.log(
            level='ERROR',
            component='email',
            message=f'Failed to update email automation {automation_id}: {str(e)}',
            user_email=current_user.email
        )
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/email/automations/<int:automation_id>', methods=['DELETE'])
@admin_required
def admin_api_email_automation_delete(automation_id):
    """API endpoint to delete email automation"""
    try:
        success = db.delete_email_automation(automation_id)
        
        if success:
            # Log the action
            system_logger.log(
                level='INFO',
                component='email',
                message=f'Email automation deleted: {automation_id}',
                user_email=current_user.email,
                details={'automation_id': automation_id}
            )
            
            return jsonify({
                'success': True,
                'message': 'Automation deleted successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to delete automation or automation not found'}), 404
            
    except Exception as e:
        system_logger.log(
            level='ERROR',
            component='email',
            message=f'Failed to delete email automation {automation_id}: {str(e)}',
            user_email=current_user.email
        )
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/email/queue')
@admin_required
def admin_api_email_queue():
    """API endpoint to get email queue status"""
    try:
        limit = request.args.get('limit', 50, type=int)
        pending_emails = db.get_pending_emails(limit=limit)
        
        return jsonify({
            'success': True,
            'queue': pending_emails,
            'total': len(pending_emails)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/email/analytics')
@admin_required
def admin_api_email_analytics():
    """API endpoint to get email analytics"""
    try:
        days = request.args.get('days', 30, type=int)
        analytics = db.get_email_analytics(days=days)
        
        return jsonify({
            'success': True,
            'analytics': analytics,
            'period_days': days
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/email/templates/top')
@admin_required
def admin_api_email_templates_top():
    """API endpoint to get top performing email templates"""
    try:
        days = request.args.get('days', 30, type=int)
        limit = request.args.get('limit', 5, type=int)
        
        templates = db.get_top_performing_templates(limit=limit, days=days)
        return jsonify({
            'success': True,
            'templates': templates
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/email/activity/recent')
@admin_required
def admin_api_email_activity_recent():
    """API endpoint to get recent email activity"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        activities = db.get_recent_email_activity(limit=limit)
        
        # Format timestamps for display
        for activity in activities:
            if activity.get('timestamp'):
                from datetime import datetime
                try:
                    timestamp = datetime.fromisoformat(activity['timestamp'].replace('Z', '+00:00'))
                    now = datetime.now()
                    
                    # Calculate time difference
                    diff = now - timestamp
                    
                    if diff.seconds < 60:
                        activity['time_ago'] = 'Just now'
                    elif diff.seconds < 3600:
                        minutes = diff.seconds // 60
                        activity['time_ago'] = f'{minutes} minute{"s" if minutes != 1 else ""} ago'
                    elif diff.days == 0:
                        hours = diff.seconds // 3600
                        activity['time_ago'] = f'{hours} hour{"s" if hours != 1 else ""} ago'
                    elif diff.days == 1:
                        activity['time_ago'] = 'Yesterday'
                    else:
                        activity['time_ago'] = f'{diff.days} days ago'
                except:
                    activity['time_ago'] = 'Recently'
            else:
                activity['time_ago'] = 'Unknown'
        
        return jsonify({
            'success': True,
            'activities': activities
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/email/test', methods=['POST'])
@admin_required
def admin_api_email_test():
    """API endpoint to send test email"""
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('template_id'):
            return jsonify({'success': False, 'error': 'Missing email or template_id'}), 400
        
        # Get template
        template = db.get_email_template(data['template_id'])
        if not template:
            return jsonify({'success': False, 'error': 'Template not found'}), 404
        
        # Parse variables for template replacement
        try:
            variables = json.loads(data.get('variables', '{}'))
        except json.JSONDecodeError:
            return jsonify({'success': False, 'error': 'Invalid JSON in variables'}), 400
        
        # Replace variables in template content BEFORE queuing
        subject_with_vars = email_service._replace_variables(template['subject'], variables)
        content_with_vars = email_service._replace_variables(template['content_html'], variables)
        
        # Queue test email with variables already replaced
        queue_id, tracking_id = db.queue_email(
            recipient_email=data['email'],
            recipient_name=data.get('name', 'Test User'),
            template_id=template['id'],
            subject=f"[TEST] {subject_with_vars}",
            content_html=content_with_vars,
            variables_json=json.dumps({})  # Variables already replaced
        )
        
        if queue_id:
            # Log the action
            system_logger.log(
                level='INFO',
                component='email',
                message=f'Test email queued for {data["email"]}',
                user_email=current_user.email,
                details={'template_id': template['id'], 'tracking_id': tracking_id}
            )
            
            return jsonify({
                'success': True,
                'message': 'Test email queued successfully',
                'tracking_id': tracking_id
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to queue test email'}), 500
            
    except Exception as e:
        system_logger.log(
            level='ERROR',
            component='email',
            message=f'Failed to send test email: {str(e)}',
            user_email=current_user.email
        )
        return jsonify({'success': False, 'error': str(e)}), 500

# Email Testing API Routes
@app.route('/admin/api/email/test/smtp-status')
@admin_required
def admin_api_email_test_smtp_status():
    """Check SMTP configuration status"""
    try:
        smtp_configured = email_service.enabled
        smtp_server = getattr(email_service, 'smtp_server', None)
        from_email = getattr(email_service, 'from_email', None)
        
        return jsonify({
            'success': True,
            'smtp_configured': smtp_configured,
            'smtp_server': smtp_server,
            'from_email': from_email,
            'config_source': getattr(email_service, 'config_source', 'unknown')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/email/test/smtp', methods=['POST'])
@admin_required
def admin_api_email_test_smtp():
    """Send a simple SMTP test email"""
    try:
        data = request.get_json()
        
        if not data or not data.get('email'):
            return jsonify({'success': False, 'message': 'Email address is required'}), 400
        
        # Send test email directly via email service
        from datetime import datetime
        from services.email_service import email_service
        
        subject = data.get('subject', 'SMTP Test - VectorCraft')
        message = data.get('message', 'This is a test email from VectorCraft SMTP configuration.')
        
        # Replace variables in message
        message = message.replace('{{ current_time }}', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        message = message.replace('{{ smtp_server }}', getattr(email_service, 'smtp_server', 'Unknown'))
        
        success = email_service.send_plain_email(data['email'], subject, message)
        
        if success:
            system_logger.info('email', f'SMTP test email sent to {data["email"]}', 
                             user_email=current_user.email)
            return jsonify({
                'success': True,
                'message': 'Test email sent successfully!',
                'details': f'Email sent to {data["email"]} via {getattr(email_service, "smtp_server", "SMTP server")}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to send test email',
                'details': 'Check SMTP configuration and server logs'
            })
            
    except Exception as e:
        system_logger.error('email', f'SMTP test failed: {str(e)}', user_email=current_user.email)
        return jsonify({
            'success': False,
            'message': 'SMTP test failed',
            'details': str(e)
        }), 500

@app.route('/admin/api/email/test/template', methods=['POST'])
@admin_required
def admin_api_email_test_template():
    """Send a template test email with variables"""
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('template_id'):
            return jsonify({'success': False, 'message': 'Email and template_id are required'}), 400
        
        # Get template
        template = db.get_email_template(data['template_id'])
        if not template:
            return jsonify({'success': False, 'message': 'Template not found'}), 404
        
        # Generate tracking ID
        tracking_id = str(uuid.uuid4())
        
        # Send email directly via email service with variables
        variables = data.get('variables', {})
        variables['domain_url'] = os.getenv('DOMAIN_URL', 'http://localhost:8080')
        
        success = email_service.send_automated_email(
            to_email=data['email'],
            subject=f"[TEST] {template['subject']}",
            content_html=template['content_html'],
            tracking_id=tracking_id,
            variables=variables
        )
        
        if success:
            # Record tracking
            db.record_email_tracking(
                tracking_id=tracking_id,
                event_type='sent',
                metadata={
                    'email_address': data['email'],
                    'template_id': template['id'],
                    'test_email': True
                }
            )
            
            system_logger.info('email', f'Template test email sent to {data["email"]}', 
                             user_email=current_user.email,
                             details={'template_id': template['id'], 'tracking_id': tracking_id})
            
            return jsonify({
                'success': True,
                'message': 'Template email sent successfully!',
                'tracking_id': tracking_id
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to send template email'
            })
            
    except Exception as e:
        system_logger.error('email', f'Template test failed: {str(e)}', user_email=current_user.email)
        return jsonify({'success': False, 'message': f'Template test failed: {str(e)}'}), 500

@app.route('/admin/api/email/test/automation', methods=['POST'])
@admin_required
def admin_api_email_test_automation():
    """Test email automation by triggering it manually"""
    try:
        data = request.get_json()
        
        if not data or not data.get('email'):
            return jsonify({'success': False, 'message': 'Email address is required'}), 400
        
        # Create test context for purchase automation
        test_context = {
            'email': data['email'],
            'username': data.get('username', 'testuser'),
            'amount': data.get('amount', 19.99),
            'transaction_id': data.get('transaction_id', f'TEST_{int(time.time())}')
        }
        
        # Trigger purchase automation
        trigger_email_automations('purchase', test_context)
        
        # Count queued emails for this user
        import sqlite3
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM email_queue WHERE recipient_email = ? AND status = "pending"', (data['email'],))
            queued_count = cursor.fetchone()[0]
        
        system_logger.info('email', f'Purchase automation triggered for {data["email"]}', 
                         user_email=current_user.email,
                         details=test_context)
        
        return jsonify({
            'success': True,
            'message': 'Purchase automation triggered successfully!',
            'emails_queued': queued_count
        })
        
    except Exception as e:
        system_logger.error('email', f'Automation test failed: {str(e)}', user_email=current_user.email)
        return jsonify({'success': False, 'message': f'Automation test failed: {str(e)}'}), 500

@app.route('/admin/api/email/test/preview', methods=['POST'])
@admin_required
def admin_api_email_test_preview():
    """Preview email template with variables"""
    try:
        data = request.get_json()
        
        if not data or not data.get('template_id'):
            return jsonify({'success': False, 'message': 'Template ID is required'}), 400
        
        # Get template
        template = db.get_email_template(data['template_id'])
        if not template:
            return jsonify({'success': False, 'message': 'Template not found'}), 404
        
        # Apply variables
        variables = data.get('variables', {})
        variables['domain_url'] = os.getenv('DOMAIN_URL', 'https://thevectorcraft.com')
        
        preview_html = email_service._replace_variables(template['content_html'], variables)
        preview_subject = email_service._replace_variables(template['subject'], variables)
        
        return jsonify({
            'success': True,
            'preview_html': preview_html,
            'preview_subject': preview_subject
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Preview failed: {str(e)}'}), 500

@app.route('/admin/api/email/test/process-queue', methods=['POST'])
@admin_required
def admin_api_email_test_process_queue():
    """Manually process email queue"""
    try:
        from email_queue_processor import email_processor
        
        # Get pending emails count before processing
        pending_before = len(db.get_pending_emails(100))
        
        # Process emails
        email_processor.process_pending_emails(limit=50)
        
        # Get pending emails count after processing
        pending_after = len(db.get_pending_emails(100))
        processed_count = pending_before - pending_after
        
        system_logger.info('email', f'Manual queue processing: {processed_count} emails processed', 
                         user_email=current_user.email)
        
        return jsonify({
            'success': True,
            'message': f'Queue processed successfully!',
            'processed_count': processed_count,
            'remaining_pending': pending_after
        })
        
    except Exception as e:
        system_logger.error('email', f'Queue processing failed: {str(e)}', user_email=current_user.email)
        return jsonify({'success': False, 'message': f'Queue processing failed: {str(e)}'}), 500

@app.route('/admin/api/email/queue/status')
@admin_required
def admin_api_email_queue_status():
    """Get email queue status"""
    try:
        pending_emails = db.get_pending_emails(100)
        
        # Get last processed email
        import sqlite3
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.execute('SELECT sent_at FROM email_queue WHERE status = "sent" ORDER BY sent_at DESC LIMIT 1')
            result = cursor.fetchone()
            last_processed = result[0] if result else None
        
        return jsonify({
            'success': True,
            'pending_count': len(pending_emails),
            'last_processed': last_processed
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/transactions')
@admin_required
def admin_transactions():
    """Admin transactions page"""
    return render_template('admin/transactions.html')

@app.route('/admin/system') 
@admin_required
def admin_system():
    """Admin system health page"""
    return render_template('admin/system.html')

@app.route('/admin/logs')
@admin_required
def admin_logs():
    """Admin system logs page"""
    return render_template('admin/logs.html')

@app.route('/admin/alerts')
@admin_required
def admin_alerts():
    """Admin alerts page"""
    return render_template('admin/alerts.html')

@app.route('/admin/analytics')
@admin_required
def admin_analytics():
    """Admin analytics page"""
    return render_template('admin/analytics.html')

@app.route('/admin/settings')
@admin_required
def admin_settings():
    """Admin settings page"""
    return render_template('admin/settings.html')

@app.route('/admin/email')
@admin_required
def admin_email():
    """Email marketing dashboard"""
    return render_template('admin/email/dashboard.html')

@app.route('/admin/email/templates')
@admin_required
def admin_email_templates():
    """Email templates management page"""
    return render_template('admin/email/templates.html')

@app.route('/admin/email/templates/new')
@admin_required
def admin_email_templates_new():
    """Create new email template page"""
    return render_template('admin/email/template_editor_new.html')

@app.route('/admin/email/templates/<int:template_id>/edit')
@admin_required
def admin_email_templates_edit(template_id):
    """Edit email template page"""
    return render_template('admin/email/template_editor_new.html', template_id=template_id)

@app.route('/admin/email/automations')
@admin_required
def admin_email_automations():
    """Email automations management page"""
    return render_template('admin/email/automations.html')

@app.route('/admin/email/automations/new')
@admin_required
def admin_email_automations_new():
    """Create new email automation page"""
    return render_template('admin/email/automation_editor.html')

@app.route('/admin/email/automations/<int:automation_id>/edit')
@admin_required
def admin_email_automations_edit(automation_id):
    """Edit email automation page"""
    return render_template('admin/email/automation_editor.html', automation_id=automation_id)

@app.route('/admin/email/campaigns')
@admin_required
def admin_email_campaigns():
    """Email campaigns management page"""
    return render_template('admin/email/campaigns.html')

# Campaign API Routes
@app.route('/admin/api/email/campaigns')
@admin_required
def admin_api_email_campaigns_get():
    """API endpoint to get all email campaigns"""
    try:
        campaigns = db.get_all_email_campaigns()
        return jsonify({
            'success': True,
            'campaigns': campaigns
        })
    except Exception as e:
        system_logger.log(
            level='ERROR',
            component='email',
            message=f'Failed to get email campaigns: {str(e)}',
            user_email=current_user.email
        )
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/email/campaigns', methods=['POST'])
@admin_required
def admin_api_email_campaigns_create():
    """API endpoint to create email campaign"""
    try:
        data = request.get_json()
        
        if not data or not data.get('name'):
            return jsonify({'success': False, 'error': 'Campaign name is required'}), 400
        
        campaign_id = db.create_email_campaign(
            name=data.get('name'),
            description=data.get('description'),
            template_id=data.get('template_id'),
            status=data.get('status', 'draft'),
            send_at=data.get('send_at'),
            recipient_list=data.get('recipient_list'),
            subject_override=data.get('subject_override')
        )
        
        if campaign_id:
            system_logger.log(
                level='INFO',
                component='email',
                message=f'Email campaign created: {campaign_id}',
                user_email=current_user.email,
                details={'campaign_id': campaign_id, 'name': data.get('name')}
            )
            
            return jsonify({
                'success': True,
                'message': 'Campaign created successfully',
                'campaign_id': campaign_id
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to create campaign'}), 500
            
    except Exception as e:
        system_logger.log(
            level='ERROR',
            component='email',
            message=f'Failed to create email campaign: {str(e)}',
            user_email=current_user.email
        )
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/email/campaigns/<int:campaign_id>')
@admin_required
def admin_api_email_campaign_get(campaign_id):
    """API endpoint to get specific email campaign"""
    try:
        campaign = db.get_email_campaign(campaign_id)
        
        if campaign:
            return jsonify({
                'success': True,
                'campaign': campaign
            })
        else:
            return jsonify({'success': False, 'error': 'Campaign not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/email/campaigns/<int:campaign_id>', methods=['PUT'])
@admin_required
def admin_api_email_campaign_update(campaign_id):
    """API endpoint to update email campaign"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        success = db.update_email_campaign(campaign_id, **data)
        
        if success:
            system_logger.log(
                level='INFO',
                component='email',
                message=f'Email campaign updated: {campaign_id}',
                user_email=current_user.email,
                details={'campaign_id': campaign_id}
            )
            
            return jsonify({
                'success': True,
                'message': 'Campaign updated successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to update campaign or campaign not found'}), 404
            
    except Exception as e:
        system_logger.log(
            level='ERROR',
            component='email',
            message=f'Failed to update email campaign {campaign_id}: {str(e)}',
            user_email=current_user.email
        )
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/email/campaigns/<int:campaign_id>', methods=['DELETE'])
@admin_required
def admin_api_email_campaign_delete(campaign_id):
    """API endpoint to delete email campaign"""
    try:
        success = db.delete_email_campaign(campaign_id)
        
        if success:
            system_logger.log(
                level='INFO',
                component='email',
                message=f'Email campaign deleted: {campaign_id}',
                user_email=current_user.email,
                details={'campaign_id': campaign_id}
            )
            
            return jsonify({
                'success': True,
                'message': 'Campaign deleted successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Campaign not found'}), 404
            
    except Exception as e:
        system_logger.log(
            level='ERROR',
            component='email',
            message=f'Failed to delete email campaign {campaign_id}: {str(e)}',
            user_email=current_user.email
        )
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/email/campaigns/stats')
@admin_required
def admin_api_email_campaigns_stats():
    """API endpoint to get campaign statistics"""
    try:
        stats = db.get_campaign_statistics()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        system_logger.log(
            level='ERROR',
            component='email',
            message=f'Failed to get campaign statistics: {str(e)}',
            user_email=current_user.email
        )
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/email/analytics')
@admin_required
def admin_email_analytics():
    """Email analytics page"""
    return render_template('admin/email/analytics.html')

@app.route('/admin/email/test')
@admin_required
def admin_email_test():
    """Email testing page"""
    return render_template('admin/email/test_email.html')

# Email tracking endpoints
@app.route('/email/track/<tracking_id>/open.png')
def email_track_open(tracking_id):
    """Track email opens with 1x1 transparent pixel"""
    try:
        # Get user agent and IP
        user_agent = request.headers.get('User-Agent', '')
        ip_address = request.remote_addr
        
        # Track the open event
        db.track_email_event(tracking_id, 'opened', user_agent=user_agent, ip_address=ip_address)
        
        # Return 1x1 transparent pixel
        from io import BytesIO
        import base64
        
        # 1x1 transparent PNG in base64
        pixel_data = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')
        
        response = app.response_class(
            pixel_data,
            mimetype='image/png',
            headers={
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        )
        return response
        
    except Exception as e:
        print(f"Error tracking email open: {e}")
        # Still return pixel even if tracking fails
        pixel_data = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')
        return app.response_class(pixel_data, mimetype='image/png')

@app.route('/email/track/<tracking_id>/click')
def email_track_click(tracking_id):
    """Track email clicks and redirect"""
    try:
        # Get redirect URL from query parameter
        redirect_url = request.args.get('url', '/')
        
        # Get user agent and IP
        user_agent = request.headers.get('User-Agent', '')
        ip_address = request.remote_addr
        
        # Track the click event
        db.track_email_event(tracking_id, 'clicked', event_data=redirect_url, user_agent=user_agent, ip_address=ip_address)
        
        # Redirect to the target URL
        return redirect(redirect_url)
        
    except Exception as e:
        print(f"Error tracking email click: {e}")
        # Still redirect even if tracking fails
        redirect_url = request.args.get('url', '/')
        return redirect(redirect_url)

@app.route('/admin-test')
def admin_test():
    """Test page to verify admin monitoring system is working"""
    return render_template('admin_test.html')

def trigger_email_automations(trigger_type, context_data):
    """
    Trigger email automations based on events
    
    Args:
        trigger_type (str): Type of trigger (purchase, welcome, followup, etc.)
        context_data (dict): Data context for email variables
    """
    try:
        # Get all active automations for this trigger type
        automations = db.get_email_automations_by_trigger(trigger_type)
        
        if not automations:
            return
        
        email = context_data.get('email')
        if not email:
            raise ValueError("Email address is required in context_data")
        
        for automation in automations:
            try:
                # Calculate send time based on delay (use UTC)
                send_time = datetime.utcnow()
                if automation.get('delay_hours', 0) > 0:
                    from datetime import timedelta
                    send_time += timedelta(hours=automation['delay_hours'])
                
                # Get template details
                template = db.get_email_template(automation['template_id'])
                if not template:
                    system_logger.warning('email', f'Template {automation["template_id"]} not found for automation {automation["id"]}')
                    continue
                
                # Check if email is not unsubscribed
                if db.is_email_unsubscribed(email):
                    system_logger.info('email', f'Skipping automation for unsubscribed email: {email}')
                    continue
                
                # Generate unique tracking ID
                tracking_id = str(uuid.uuid4())
                
                # Replace variables in email content
                email_content = replace_email_variables(template['content_html'], context_data, tracking_id)
                email_subject = replace_email_variables(template['subject'], context_data, tracking_id)
                
                # Queue the email
                queue_id, _ = db.queue_email(
                    to_email=email,
                    subject=email_subject,
                    content_html=email_content,
                    template_id=template['id'],
                    automation_id=automation['id'],
                    tracking_id=tracking_id,
                    send_time=send_time,
                    context_data=context_data
                )
                
                if queue_id:
                    system_logger.info('email', f'Queued automation email: {automation["name"]} for {email}',
                                     details={
                                         'automation_id': automation['id'],
                                         'template_id': template['id'],
                                         'tracking_id': tracking_id,
                                         'send_time': send_time.isoformat()
                                     })
                else:
                    system_logger.warning('email', f'Failed to queue automation email: {automation["name"]} for {email}')
                    
            except Exception as e:
                system_logger.error('email', f'Error processing automation {automation["id"]}: {str(e)}')
                continue
                
    except Exception as e:
        system_logger.error('email', f'Error triggering email automations for {trigger_type}: {str(e)}')
        raise

def replace_email_variables(content, context_data, tracking_id):
    """
    Replace variables in email content with actual values
    
    Args:
        content (str): Email content with variables like {{username}}
        context_data (dict): Data to replace variables
        tracking_id (str): Unique tracking ID for this email
    
    Returns:
        str: Content with variables replaced
    """
    try:
        if not content:
            return content
        
        # Standard variables
        variables = {
            'username': context_data.get('username', ''),
            'email': context_data.get('email', ''),
            'password': context_data.get('password', ''),
            'amount': context_data.get('amount', ''),
            'order_id': context_data.get('order_id', ''),
            'transaction_id': context_data.get('transaction_id', ''),
            'tracking_pixel_url': f"{os.getenv('DOMAIN_URL', 'http://localhost:8080')}/email/tracking/{tracking_id}",
            'unsubscribe_url': f"{os.getenv('DOMAIN_URL', 'http://localhost:8080')}/email/unsubscribe/{context_data.get('email', '')}",
            'company_name': 'VectorCraft',
            'current_year': str(datetime.now().year),
            'current_date': datetime.now().strftime('%B %d, %Y')
        }
        
        # Replace tracking pixel placeholder
        content = content.replace('{{tracking_pixel_url}}', variables['tracking_pixel_url'])
        
        # Replace all other variables
        for key, value in variables.items():
            placeholder = f'{{{{{key}}}}}'
            content = content.replace(placeholder, str(value))
        
        return content
        
    except Exception as e:
        system_logger.error('email', f'Error replacing email variables: {str(e)}')
        return content

if __name__ == '__main__':
    # Determine debug mode based on environment
    debug_mode = True  # Enable debug mode to see errors
    env_name = os.getenv('FLASK_ENV', 'development')
    
    print("🚀 Starting VectorCraft - Professional Vector Conversion with Authentication...")
    print("📊 Initializing advanced vectorization engines...")
    print("🔐 Authentication system enabled")
    print(f"🌍 Environment: {env_name}")
    print(f"🔧 Debug mode: {'ON' if debug_mode else 'OFF'}")
    print("✅ Ready!")
    print("\n🌐 Access VectorCraft at: http://localhost:8080")
    print("🔧 API endpoint: http://localhost:8080/api/vectorize")
    print("📋 Health check: http://localhost:8080/health")
    
    if debug_mode:
        print("🔑 Login with demo credentials: admin/admin123 or demo/demo123")
    
    print("\n💡 Convert any image to a crisp, scalable vector!")
    print(" Press Ctrl+C to stop the server")
    
    # Start the email queue processor
    print("📧 Starting email automation processor...")
    start_email_processor()
    print("✅ Email automation ready!")
    
    app.run(debug=debug_mode, host='0.0.0.0', port=5004)