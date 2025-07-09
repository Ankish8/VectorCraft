#!/usr/bin/env python3
"""
Admin Content Management Routes for VectorCraft
Handles content management, landing page builder, and SEO optimization
"""

import json
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session, current_app
from werkzeug.utils import secure_filename
import os

from services.content_manager import content_manager
from services.page_builder import page_builder
from services.seo_manager import seo_manager

# Import admin blueprint
from . import admin_bp
from blueprints.auth.utils import admin_required

@admin_bp.route('/content')
@admin_required
def content_dashboard():
    """Content management dashboard"""
    try:
        # Get content analytics
        analytics = content_manager.get_content_analytics()
        
        # Get recent pages
        recent_pages = content_manager.get_pages(limit=10)
        
        # Get templates
        templates = content_manager.get_templates()
        
        # Get scheduled actions
        scheduled_actions = content_manager.get_scheduled_actions()
        
        return render_template('admin/content/dashboard.html',
                             analytics=analytics,
                             recent_pages=recent_pages,
                             templates=templates,
                             scheduled_actions=scheduled_actions)
    except Exception as e:
        current_app.logger.error(f"Error in content dashboard: {e}")
        flash('Error loading content dashboard', 'error')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/content/pages')
@admin_required
def pages():
    """List all pages"""
    try:
        page_type = request.args.get('type', '')
        status = request.args.get('status', '')
        search = request.args.get('search', '')
        
        # Get pages with filtering
        if search:
            pages = content_manager.search_content(search, page_type, status == 'published')
        else:
            pages = content_manager.get_pages(page_type, status, status == 'published')
        
        # Get page types for filter
        page_types = list(set(p['page_type'] for p in pages))
        
        return render_template('admin/content/pages.html',
                             pages=pages,
                             page_types=page_types,
                             current_type=page_type,
                             current_status=status,
                             search=search)
    except Exception as e:
        current_app.logger.error(f"Error loading pages: {e}")
        flash('Error loading pages', 'error')
        return redirect(url_for('admin_content.dashboard'))

@admin_bp.route('/content/pages/create')
@admin_required
def create_page():
    """Create new page form"""
    try:
        template_id = request.args.get('template')
        
        # Get templates
        templates = content_manager.get_templates()
        
        # Get page builder components
        components = page_builder.get_page_components()
        
        return render_template('admin/content/create_page.html',
                             templates=templates,
                             components=components,
                             selected_template=template_id)
    except Exception as e:
        current_app.logger.error(f"Error loading create page: {e}")
        flash('Error loading page creator', 'error')
        return redirect(url_for('admin_content.pages'))

@admin_bp.route('/content/pages/create', methods=['POST'])
def create_page_post():
    """Create new page"""
    try:
        data = request.json if request.is_json else request.form
        
        # Validate required fields
        required_fields = ['name', 'title', 'slug', 'page_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create from template or blank
        if data.get('template_id'):
            page_id = page_builder.create_page_from_template(
                data['template_id'],
                {
                    'name': data['name'],
                    'title': data['title'],
                    'slug': data['slug'],
                    'meta': {
                        'meta_title': data.get('meta_title'),
                        'meta_description': data.get('meta_description'),
                        'meta_keywords': data.get('meta_keywords')
                    }
                },
                author_id=session.get('user_id')
            )
        else:
            # Create blank page
            page_id = content_manager.create_page(
                name=data['name'],
                title=data['title'],
                slug=data['slug'],
                page_type=data['page_type'],
                content_json=data.get('content_json', '{"sections": [], "settings": {}}'),
                author_id=session.get('user_id'),
                meta_title=data.get('meta_title'),
                meta_description=data.get('meta_description'),
                meta_keywords=data.get('meta_keywords')
            )
        
        if page_id:
            if request.is_json:
                return jsonify({'success': True, 'page_id': page_id})
            else:
                flash('Page created successfully', 'success')
                return redirect(url_for('admin_content.edit_page', page_id=page_id))
        else:
            if request.is_json:
                return jsonify({'error': 'Failed to create page'}), 500
            else:
                flash('Failed to create page', 'error')
                return redirect(url_for('admin_content.create_page'))
    
    except Exception as e:
        current_app.logger.error(f"Error creating page: {e}")
        if request.is_json:
            return jsonify({'error': str(e)}), 500
        else:
            flash('Error creating page', 'error')
            return redirect(url_for('admin_content.create_page'))

@admin_bp.route('/content/pages/<page_id>')
def edit_page(page_id):
    """Edit page"""
    try:
        page = content_manager.get_page(page_id)
        if not page:
            flash('Page not found', 'error')
            return redirect(url_for('admin_content.pages'))
        
        # Get page versions
        versions = content_manager.get_page_versions(page_id)
        
        # Get page statistics
        stats = content_manager.get_page_statistics(page_id)
        
        # Get page builder components
        components = page_builder.get_page_components()
        
        # Get SEO analysis
        seo_analysis = seo_manager.analyze_page_seo(page_id)
        
        return render_template('admin/content/edit_page.html',
                             page=page,
                             versions=versions,
                             stats=stats,
                             components=components,
                             seo_analysis=seo_analysis)
    except Exception as e:
        current_app.logger.error(f"Error loading edit page: {e}")
        flash('Error loading page editor', 'error')
        return redirect(url_for('admin_content.pages'))

@admin_bp.route('/content/pages/<page_id>', methods=['POST'])
def update_page(page_id):
    """Update page"""
    try:
        data = request.json if request.is_json else request.form
        
        # Prepare updates
        updates = {}
        for field in ['name', 'title', 'slug', 'content_json', 'meta_title', 
                     'meta_description', 'meta_keywords', 'custom_css', 'custom_js', 
                     'status', 'is_published']:
            if field in data:
                updates[field] = data[field]
        
        # Add change summary
        if 'changes_summary' in data:
            updates['changes_summary'] = data['changes_summary']
        
        success = content_manager.update_page(page_id, updates, session.get('user_id'))
        
        if success:
            if request.is_json:
                return jsonify({'success': True})
            else:
                flash('Page updated successfully', 'success')
                return redirect(url_for('admin_content.edit_page', page_id=page_id))
        else:
            if request.is_json:
                return jsonify({'error': 'Failed to update page'}), 500
            else:
                flash('Failed to update page', 'error')
                return redirect(url_for('admin_content.edit_page', page_id=page_id))
    
    except Exception as e:
        current_app.logger.error(f"Error updating page: {e}")
        if request.is_json:
            return jsonify({'error': str(e)}), 500
        else:
            flash('Error updating page', 'error')
            return redirect(url_for('admin_content.edit_page', page_id=page_id))

@admin_bp.route('/content/pages/<page_id>/delete', methods=['POST'])
def delete_page(page_id):
    """Delete page"""
    try:
        success = content_manager.delete_page(page_id)
        
        if success:
            flash('Page deleted successfully', 'success')
        else:
            flash('Failed to delete page', 'error')
        
        return redirect(url_for('admin_content.pages'))
    
    except Exception as e:
        current_app.logger.error(f"Error deleting page: {e}")
        flash('Error deleting page', 'error')
        return redirect(url_for('admin_content.pages'))

@admin_bp.route('/content/pages/<page_id>/duplicate', methods=['POST'])
def duplicate_page(page_id):
    """Duplicate page"""
    try:
        data = request.json if request.is_json else request.form
        
        new_name = data.get('name') or f"Copy of {page_id}"
        new_slug = data.get('slug') or f"copy-of-{page_id}"
        
        new_page_id = content_manager.duplicate_page(
            page_id, new_name, new_slug, session.get('user_id')
        )
        
        if new_page_id:
            if request.is_json:
                return jsonify({'success': True, 'page_id': new_page_id})
            else:
                flash('Page duplicated successfully', 'success')
                return redirect(url_for('admin_content.edit_page', page_id=new_page_id))
        else:
            if request.is_json:
                return jsonify({'error': 'Failed to duplicate page'}), 500
            else:
                flash('Failed to duplicate page', 'error')
                return redirect(url_for('admin_content.edit_page', page_id=page_id))
    
    except Exception as e:
        current_app.logger.error(f"Error duplicating page: {e}")
        if request.is_json:
            return jsonify({'error': str(e)}), 500
        else:
            flash('Error duplicating page', 'error')
            return redirect(url_for('admin_content.edit_page', page_id=page_id))

@admin_bp.route('/content/pages/<page_id>/preview')
def preview_page(page_id):
    """Preview page"""
    try:
        html = page_builder.generate_page_preview(page_id)
        return html
    except Exception as e:
        current_app.logger.error(f"Error generating preview: {e}")
        return "<p>Error generating preview</p>"

@admin_bp.route('/content/pages/<page_id>/export')
def export_page(page_id):
    """Export page code"""
    try:
        format = request.args.get('format', 'html')
        code = page_builder.export_page_code(page_id, format)
        
        if not code:
            return jsonify({'error': 'Invalid format'}), 400
        
        return jsonify({'code': code, 'format': format})
    
    except Exception as e:
        current_app.logger.error(f"Error exporting page: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/content/pages/<page_id>/versions')
def page_versions(page_id):
    """Get page versions"""
    try:
        versions = content_manager.get_page_versions(page_id)
        return jsonify({'versions': versions})
    except Exception as e:
        current_app.logger.error(f"Error getting versions: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/content/pages/<page_id>/versions/<version_id>/restore', methods=['POST'])
def restore_version(page_id, version_id):
    """Restore page version"""
    try:
        success = content_manager.restore_version(page_id, version_id, session.get('user_id'))
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to restore version'}), 500
    
    except Exception as e:
        current_app.logger.error(f"Error restoring version: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/content/templates')
def templates():
    """List templates"""
    try:
        category = request.args.get('category', '')
        templates = content_manager.get_templates(category)
        
        # Get categories
        categories = list(set(t['category'] for t in templates))
        
        return render_template('admin/content/templates.html',
                             templates=templates,
                             categories=categories,
                             current_category=category)
    except Exception as e:
        current_app.logger.error(f"Error loading templates: {e}")
        flash('Error loading templates', 'error')
        return redirect(url_for('admin_content.dashboard'))

@admin_bp.route('/content/templates/create')
def create_template():
    """Create template form"""
    try:
        return render_template('admin/content/create_template.html')
    except Exception as e:
        current_app.logger.error(f"Error loading create template: {e}")
        flash('Error loading template creator', 'error')
        return redirect(url_for('admin_content.templates'))

@admin_bp.route('/content/templates/create', methods=['POST'])
def create_template_post():
    """Create template"""
    try:
        data = request.json if request.is_json else request.form
        
        # Validate required fields
        required_fields = ['name', 'category', 'template_json']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        template_id = content_manager.create_template(
            name=data['name'],
            category=data['category'],
            template_json=data['template_json'],
            description=data.get('description'),
            preview_image=data.get('preview_image'),
            is_premium=data.get('is_premium', False)
        )
        
        if template_id:
            if request.is_json:
                return jsonify({'success': True, 'template_id': template_id})
            else:
                flash('Template created successfully', 'success')
                return redirect(url_for('admin_content.templates'))
        else:
            if request.is_json:
                return jsonify({'error': 'Failed to create template'}), 500
            else:
                flash('Failed to create template', 'error')
                return redirect(url_for('admin_content.create_template'))
    
    except Exception as e:
        current_app.logger.error(f"Error creating template: {e}")
        if request.is_json:
            return jsonify({'error': str(e)}), 500
        else:
            flash('Error creating template', 'error')
            return redirect(url_for('admin_content.create_template'))

@admin_bp.route('/content/seo')
def seo_dashboard():
    """SEO dashboard"""
    try:
        # Get pages with SEO data
        pages = content_manager.get_pages(limit=20)
        
        # Get SEO analytics for each page
        seo_data = []
        for page in pages:
            seo_analysis = seo_manager.analyze_page_seo(page['page_id'])
            seo_data.append({
                'page': page,
                'seo_score': seo_analysis.get('score', 0),
                'issues_count': len(seo_analysis.get('recommendations', [])),
                'last_analyzed': seo_analysis.get('analyzed_at')
            })
        
        # Sort by SEO score
        seo_data.sort(key=lambda x: x['seo_score'], reverse=True)
        
        return render_template('admin/content/seo_dashboard.html',
                             seo_data=seo_data)
    except Exception as e:
        current_app.logger.error(f"Error loading SEO dashboard: {e}")
        flash('Error loading SEO dashboard', 'error')
        return redirect(url_for('admin_content.dashboard'))

@admin_bp.route('/content/seo/<page_id>')
def seo_analysis(page_id):
    """SEO analysis for specific page"""
    try:
        page = content_manager.get_page(page_id)
        if not page:
            flash('Page not found', 'error')
            return redirect(url_for('admin_content.seo_dashboard'))
        
        # Get comprehensive SEO report
        seo_report = seo_manager.generate_seo_report(page_id)
        
        # Get SEO trends
        seo_trends = seo_manager.get_seo_trends(page_id)
        
        return render_template('admin/content/seo_analysis.html',
                             page=page,
                             seo_report=seo_report,
                             seo_trends=seo_trends)
    except Exception as e:
        current_app.logger.error(f"Error loading SEO analysis: {e}")
        flash('Error loading SEO analysis', 'error')
        return redirect(url_for('admin_content.seo_dashboard'))

@admin_bp.route('/content/seo/<page_id>/optimize', methods=['POST'])
def optimize_seo(page_id):
    """Optimize page SEO"""
    try:
        recommendations = page_builder.optimize_page_for_seo(page_id)
        return jsonify(recommendations)
    except Exception as e:
        current_app.logger.error(f"Error optimizing SEO: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/content/assets')
def assets():
    """Asset manager"""
    try:
        file_type = request.args.get('type', '')
        assets = content_manager.get_assets(file_type)
        
        # Get file types
        file_types = list(set(a['file_type'] for a in assets))
        
        return render_template('admin/content/assets.html',
                             assets=assets,
                             file_types=file_types,
                             current_type=file_type)
    except Exception as e:
        current_app.logger.error(f"Error loading assets: {e}")
        flash('Error loading assets', 'error')
        return redirect(url_for('admin_content.dashboard'))

@admin_bp.route('/content/assets/upload', methods=['POST'])
def upload_asset():
    """Upload asset"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file:
            # Secure filename
            filename = secure_filename(file.filename)
            
            # Create uploads directory if it doesn't exist
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'assets')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Save file
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            
            # Get file info
            file_size = os.path.getsize(file_path)
            file_type = filename.split('.')[-1].lower()
            
            # Create asset record
            asset_id = content_manager.create_asset(
                name=request.form.get('name', filename),
                file_path=f'/static/uploads/assets/{filename}',
                file_type=file_type,
                file_size=file_size,
                mime_type=file.mimetype,
                alt_text=request.form.get('alt_text'),
                caption=request.form.get('caption'),
                tags=request.form.get('tags')
            )
            
            if asset_id:
                return jsonify({
                    'success': True,
                    'asset_id': asset_id,
                    'file_path': f'/static/uploads/assets/{filename}'
                })
            else:
                return jsonify({'error': 'Failed to save asset'}), 500
    
    except Exception as e:
        current_app.logger.error(f"Error uploading asset: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/content/schedule')
def schedule():
    """Content schedule"""
    try:
        status = request.args.get('status', 'pending')
        scheduled_actions = content_manager.get_scheduled_actions(status)
        
        return render_template('admin/content/schedule.html',
                             scheduled_actions=scheduled_actions,
                             current_status=status)
    except Exception as e:
        current_app.logger.error(f"Error loading schedule: {e}")
        flash('Error loading schedule', 'error')
        return redirect(url_for('admin_content.dashboard'))

@admin_bp.route('/content/schedule/create', methods=['POST'])
def create_schedule():
    """Create scheduled action"""
    try:
        data = request.json if request.is_json else request.form
        
        # Validate required fields
        required_fields = ['page_id', 'action', 'scheduled_at']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Parse scheduled datetime
        scheduled_at = datetime.fromisoformat(data['scheduled_at'])
        
        schedule_id = content_manager.schedule_content_action(
            page_id=data['page_id'],
            action=data['action'],
            scheduled_at=scheduled_at
        )
        
        if schedule_id:
            return jsonify({'success': True, 'schedule_id': schedule_id})
        else:
            return jsonify({'error': 'Failed to create schedule'}), 500
    
    except Exception as e:
        current_app.logger.error(f"Error creating schedule: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/content/api/validate-content', methods=['POST'])
def validate_content():
    """Validate page content structure"""
    try:
        data = request.json
        content = data.get('content', {})
        
        validation = page_builder.validate_page_structure(content)
        return jsonify(validation)
    
    except Exception as e:
        current_app.logger.error(f"Error validating content: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/content/api/components')
def get_components():
    """Get page builder components"""
    try:
        components = page_builder.get_page_components()
        return jsonify(components)
    except Exception as e:
        current_app.logger.error(f"Error getting components: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/content/api/analytics')
def get_analytics():
    """Get content analytics"""
    try:
        days = request.args.get('days', 30, type=int)
        analytics = content_manager.get_content_analytics(days)
        return jsonify(analytics)
    except Exception as e:
        current_app.logger.error(f"Error getting analytics: {e}")
        return jsonify({'error': str(e)}), 500

# Error handlers
@content_bp.errorhandler(404)
def not_found(error):
    return render_template('admin/content/error.html', 
                         error_code=404, 
                         error_message="Page not found"), 404

@content_bp.errorhandler(500)
def internal_error(error):
    return render_template('admin/content/error.html', 
                         error_code=500, 
                         error_message="Internal server error"), 500