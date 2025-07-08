"""
Upload management API endpoints
"""

import os
import logging
from flask import jsonify, current_app, send_file
from flask_login import current_user, login_required

from . import api_bp
from blueprints.auth.utils import login_required_api
from database import db

logger = logging.getLogger(__name__)


@api_bp.route('/uploads', methods=['GET'])
@login_required_api
def get_user_uploads():
    """Get user's upload history"""
    try:
        limit = request.args.get('limit', 20, type=int)
        uploads = db.get_user_uploads(current_user.id, limit=limit)
        
        return jsonify({
            'success': True,
            'uploads': uploads,
            'count': len(uploads)
        })
        
    except Exception as e:
        logger.error(f"Error getting user uploads: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/uploads/stats', methods=['GET'])
@login_required_api
def get_upload_stats():
    """Get user's upload statistics"""
    try:
        stats = db.get_upload_stats(current_user.id)
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting upload stats: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/download/<filename>')
@login_required
def download_result(filename):
    """Download SVG result file"""
    try:
        # Verify that the file belongs to the current user
        uploads = db.get_user_uploads(current_user.id, limit=1000)
        user_files = [upload['svg_filename'] for upload in uploads if upload['svg_filename']]
        
        if filename not in user_files:
            return jsonify({'error': 'File not found or access denied'}), 404
        
        file_path = os.path.join(current_app.config['RESULTS_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
            
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/view/<filename>')
@login_required
def view_result(filename):
    """View SVG result file for preview"""
    try:
        # Verify that the file belongs to the current user
        uploads = db.get_user_uploads(current_user.id, limit=1000)
        user_files = [upload['svg_filename'] for upload in uploads if upload['svg_filename']]
        
        if filename not in user_files:
            return jsonify({'error': 'File not found or access denied'}), 404
        
        file_path = os.path.join(current_app.config['RESULTS_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, mimetype='image/svg+xml')
        else:
            return jsonify({'error': 'File not found'}), 404
            
    except Exception as e:
        logger.error(f"View error: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/demo/<demo_type>')
@login_required_api
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
                from PIL import Image
                import base64
                
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
            from vectorcraft import HybridVectorizer
            
            test_images = create_test_images()
            standard_vectorizer = HybridVectorizer()
            
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
        logger.error(f"Demo error: {e}")
        return jsonify({'error': f'Demo failed: {str(e)}'}), 500