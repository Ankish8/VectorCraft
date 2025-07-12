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
            flash('Please log in to access admin features.', 'error')
            return redirect(url_for('login', next=request.url))
        
        # Check if user is admin (username 'admin' or email contains 'admin')
        if current_user.username != 'admin' and 'admin' not in current_user.email.lower():
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
        system_logger.log_event(
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
        system_logger.log_event(
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
        system_logger.log_event(
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
        system_logger.log_event(
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
        system_logger.log_event(
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
        system_logger.log_event(
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
        system_logger.log_event(
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
        system_logger.log_event(
            level='ERROR',
            component='admin',
            message=f'PayPal test failed with exception: {str(e)}',
            user_email=current_user.email
        )
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

@app.route('/admin-test')
def admin_test():
    """Test page to verify admin monitoring system is working"""
    return render_template('admin_test.html')

if __name__ == '__main__':
    # Determine debug mode based on environment
    debug_mode = os.getenv('FLASK_ENV') != 'production'
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
    
    app.run(debug=debug_mode, host='0.0.0.0', port=8080)