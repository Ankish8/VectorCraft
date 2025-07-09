#!/usr/bin/env python3
"""
Content Management Service for VectorCraft
Handles dynamic content, landing pages, and marketing materials
"""

import os
import json
import logging
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from contextlib import contextmanager

class ContentManager:
    """Core content management service with database integration"""
    
    def __init__(self, db_path=None):
        self.logger = logging.getLogger(__name__)
        self.db_path = db_path or 'vectorcraft.db'
        self.init_content_tables()
        
    @contextmanager
    def get_db_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def init_content_tables(self):
        """Initialize content management database tables"""
        with sqlite3.connect(self.db_path) as conn:
            # Content pages table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS content_pages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    page_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    slug TEXT UNIQUE NOT NULL,
                    page_type TEXT NOT NULL,
                    content_json TEXT NOT NULL,
                    meta_title TEXT,
                    meta_description TEXT,
                    meta_keywords TEXT,
                    custom_css TEXT,
                    custom_js TEXT,
                    status TEXT DEFAULT 'draft',
                    is_published BOOLEAN DEFAULT 0,
                    published_at TIMESTAMP,
                    version INTEGER DEFAULT 1,
                    template_id TEXT,
                    author_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (author_id) REFERENCES users (id)
                )
            ''')
            
            # Content versions table for versioning
            conn.execute('''
                CREATE TABLE IF NOT EXISTS content_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version_id TEXT UNIQUE NOT NULL,
                    page_id TEXT NOT NULL,
                    version_number INTEGER NOT NULL,
                    content_json TEXT NOT NULL,
                    changes_summary TEXT,
                    author_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (page_id) REFERENCES content_pages (page_id),
                    FOREIGN KEY (author_id) REFERENCES users (id)
                )
            ''')
            
            # Content templates table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS content_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT,
                    template_json TEXT NOT NULL,
                    preview_image TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    is_premium BOOLEAN DEFAULT 0,
                    usage_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Content assets table for images, videos, etc.
            conn.execute('''
                CREATE TABLE IF NOT EXISTS content_assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER,
                    mime_type TEXT,
                    alt_text TEXT,
                    caption TEXT,
                    tags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Content components table for reusable components
            conn.execute('''
                CREATE TABLE IF NOT EXISTS content_components (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    content_json TEXT NOT NULL,
                    settings_json TEXT,
                    is_global BOOLEAN DEFAULT 0,
                    usage_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # A/B Testing table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS ab_tests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    page_id TEXT NOT NULL,
                    test_type TEXT NOT NULL,
                    status TEXT DEFAULT 'draft',
                    start_date TIMESTAMP,
                    end_date TIMESTAMP,
                    traffic_split REAL DEFAULT 0.5,
                    conversion_goal TEXT,
                    variant_a_id TEXT,
                    variant_b_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (page_id) REFERENCES content_pages (page_id)
                )
            ''')
            
            # A/B Test metrics table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS ab_test_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_id TEXT NOT NULL,
                    variant TEXT NOT NULL,
                    visitor_id TEXT,
                    event_type TEXT NOT NULL,
                    value REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (test_id) REFERENCES ab_tests (test_id)
                )
            ''')
            
            # Content SEO analytics table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS content_seo_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    page_id TEXT NOT NULL,
                    date DATE NOT NULL,
                    page_views INTEGER DEFAULT 0,
                    unique_visitors INTEGER DEFAULT 0,
                    bounce_rate REAL DEFAULT 0,
                    avg_session_duration REAL DEFAULT 0,
                    conversion_rate REAL DEFAULT 0,
                    seo_score INTEGER DEFAULT 0,
                    search_rankings TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (page_id) REFERENCES content_pages (page_id)
                )
            ''')
            
            # Content scheduling table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS content_schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    schedule_id TEXT UNIQUE NOT NULL,
                    page_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    scheduled_at TIMESTAMP NOT NULL,
                    status TEXT DEFAULT 'pending',
                    executed_at TIMESTAMP,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (page_id) REFERENCES content_pages (page_id)
                )
            ''')
            
            # Content comments/feedback table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS content_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    feedback_id TEXT UNIQUE NOT NULL,
                    page_id TEXT NOT NULL,
                    user_id INTEGER,
                    feedback_type TEXT NOT NULL,
                    rating INTEGER,
                    comment TEXT,
                    is_public BOOLEAN DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (page_id) REFERENCES content_pages (page_id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Create indexes for performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_content_pages_slug ON content_pages(slug)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_content_pages_status ON content_pages(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_content_pages_published ON content_pages(is_published)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_content_pages_type ON content_pages(page_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_content_versions_page_id ON content_versions(page_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_content_templates_category ON content_templates(category)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_content_assets_type ON content_assets(file_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_ab_tests_page_id ON ab_tests(page_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_ab_tests_status ON ab_tests(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_content_seo_date ON content_seo_metrics(date)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_content_schedule_scheduled ON content_schedule(scheduled_at)')
            
            conn.commit()
    
    # Page Management Methods
    def create_page(self, name: str, title: str, slug: str, page_type: str, 
                   content_json: str, author_id: int = None, **kwargs) -> str:
        """Create a new content page"""
        page_id = str(uuid.uuid4())
        
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO content_pages 
                (page_id, name, title, slug, page_type, content_json, 
                 meta_title, meta_description, meta_keywords, custom_css, 
                 custom_js, template_id, author_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (page_id, name, title, slug, page_type, content_json,
                  kwargs.get('meta_title'), kwargs.get('meta_description'),
                  kwargs.get('meta_keywords'), kwargs.get('custom_css'),
                  kwargs.get('custom_js'), kwargs.get('template_id'), author_id))
            conn.commit()
            
            # Create initial version
            self.create_version(page_id, 1, content_json, "Initial version", author_id)
            
            self.logger.info(f"Created new page: {name} (ID: {page_id})")
            return page_id
    
    def update_page(self, page_id: str, updates: Dict[str, Any], author_id: int = None) -> bool:
        """Update a content page"""
        try:
            with self.get_db_connection() as conn:
                # Get current version
                cursor = conn.execute('SELECT version FROM content_pages WHERE page_id = ?', (page_id,))
                row = cursor.fetchone()
                if not row:
                    return False
                
                current_version = row['version']
                
                # Build update query
                valid_fields = ['name', 'title', 'slug', 'content_json', 'meta_title', 
                               'meta_description', 'meta_keywords', 'custom_css', 'custom_js', 
                               'status', 'is_published', 'template_id']
                
                update_clauses = ['updated_at = CURRENT_TIMESTAMP']
                values = []
                
                for field, value in updates.items():
                    if field in valid_fields:
                        if field == 'is_published':
                            value = int(value)
                        elif field == 'content_json':
                            # Create new version for content changes
                            new_version = current_version + 1
                            update_clauses.append('version = ?')
                            values.append(new_version)
                            
                            # Save version history
                            self.create_version(page_id, new_version, value, 
                                              updates.get('changes_summary', 'Content updated'), 
                                              author_id)
                        
                        update_clauses.append(f"{field} = ?")
                        values.append(value)
                
                if updates.get('is_published'):
                    update_clauses.append('published_at = CURRENT_TIMESTAMP')
                
                if len(update_clauses) > 1:
                    values.append(page_id)
                    query = f"UPDATE content_pages SET {', '.join(update_clauses)} WHERE page_id = ?"
                    conn.execute(query, values)
                    conn.commit()
                    
                    self.logger.info(f"Updated page: {page_id}")
                    return True
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating page {page_id}: {e}")
            return False
    
    def get_page(self, page_id: str = None, slug: str = None) -> Optional[Dict]:
        """Get a content page by ID or slug"""
        with self.get_db_connection() as conn:
            if page_id:
                cursor = conn.execute('SELECT * FROM content_pages WHERE page_id = ?', (page_id,))
            elif slug:
                cursor = conn.execute('SELECT * FROM content_pages WHERE slug = ?', (slug,))
            else:
                return None
            
            row = cursor.fetchone()
            if row:
                page = dict(row)
                # Parse JSON content
                if page['content_json']:
                    try:
                        page['content'] = json.loads(page['content_json'])
                    except:
                        page['content'] = {}
                return page
            return None
    
    def get_pages(self, page_type: str = None, status: str = None, 
                  published_only: bool = False, limit: int = 50) -> List[Dict]:
        """Get content pages with filtering"""
        query = 'SELECT * FROM content_pages WHERE 1=1'
        params = []
        
        if page_type:
            query += ' AND page_type = ?'
            params.append(page_type)
        
        if status:
            query += ' AND status = ?'
            params.append(status)
        
        if published_only:
            query += ' AND is_published = 1'
        
        query += ' ORDER BY updated_at DESC LIMIT ?'
        params.append(limit)
        
        with self.get_db_connection() as conn:
            cursor = conn.execute(query, params)
            pages = [dict(row) for row in cursor.fetchall()]
            
            # Parse JSON content for each page
            for page in pages:
                if page['content_json']:
                    try:
                        page['content'] = json.loads(page['content_json'])
                    except:
                        page['content'] = {}
            
            return pages
    
    def delete_page(self, page_id: str) -> bool:
        """Delete a content page"""
        try:
            with self.get_db_connection() as conn:
                # Delete related data first
                conn.execute('DELETE FROM content_versions WHERE page_id = ?', (page_id,))
                conn.execute('DELETE FROM content_seo_metrics WHERE page_id = ?', (page_id,))
                conn.execute('DELETE FROM content_schedule WHERE page_id = ?', (page_id,))
                conn.execute('DELETE FROM content_feedback WHERE page_id = ?', (page_id,))
                conn.execute('DELETE FROM ab_tests WHERE page_id = ?', (page_id,))
                
                # Delete the page
                cursor = conn.execute('DELETE FROM content_pages WHERE page_id = ?', (page_id,))
                conn.commit()
                
                if cursor.rowcount > 0:
                    self.logger.info(f"Deleted page: {page_id}")
                    return True
                return False
                
        except Exception as e:
            self.logger.error(f"Error deleting page {page_id}: {e}")
            return False
    
    # Version Management Methods
    def create_version(self, page_id: str, version_number: int, content_json: str, 
                      changes_summary: str = None, author_id: int = None) -> str:
        """Create a new page version"""
        version_id = str(uuid.uuid4())
        
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO content_versions 
                (version_id, page_id, version_number, content_json, changes_summary, author_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (version_id, page_id, version_number, content_json, changes_summary, author_id))
            conn.commit()
            
            return version_id
    
    def get_page_versions(self, page_id: str, limit: int = 10) -> List[Dict]:
        """Get version history for a page"""
        with self.get_db_connection() as conn:
            cursor = conn.execute('''
                SELECT cv.*, u.username as author_name
                FROM content_versions cv
                LEFT JOIN users u ON cv.author_id = u.id
                WHERE cv.page_id = ?
                ORDER BY cv.version_number DESC
                LIMIT ?
            ''', (page_id, limit))
            
            versions = [dict(row) for row in cursor.fetchall()]
            
            # Parse JSON content for each version
            for version in versions:
                if version['content_json']:
                    try:
                        version['content'] = json.loads(version['content_json'])
                    except:
                        version['content'] = {}
            
            return versions
    
    def restore_version(self, page_id: str, version_id: str, author_id: int = None) -> bool:
        """Restore a page to a specific version"""
        try:
            with self.get_db_connection() as conn:
                # Get version content
                cursor = conn.execute('SELECT content_json FROM content_versions WHERE version_id = ?', (version_id,))
                row = cursor.fetchone()
                if not row:
                    return False
                
                content_json = row['content_json']
                
                # Update page with restored content
                return self.update_page(page_id, {
                    'content_json': content_json,
                    'changes_summary': f'Restored from version {version_id}'
                }, author_id)
                
        except Exception as e:
            self.logger.error(f"Error restoring version {version_id}: {e}")
            return False
    
    # Template Management Methods
    def create_template(self, name: str, category: str, template_json: str, 
                       description: str = None, **kwargs) -> str:
        """Create a new content template"""
        template_id = str(uuid.uuid4())
        
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO content_templates 
                (template_id, name, category, description, template_json, 
                 preview_image, is_premium)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (template_id, name, category, description, template_json,
                  kwargs.get('preview_image'), kwargs.get('is_premium', 0)))
            conn.commit()
            
            self.logger.info(f"Created new template: {name} (ID: {template_id})")
            return template_id
    
    def get_templates(self, category: str = None, active_only: bool = True) -> List[Dict]:
        """Get content templates"""
        query = 'SELECT * FROM content_templates WHERE 1=1'
        params = []
        
        if category:
            query += ' AND category = ?'
            params.append(category)
        
        if active_only:
            query += ' AND is_active = 1'
        
        query += ' ORDER BY usage_count DESC, created_at DESC'
        
        with self.get_db_connection() as conn:
            cursor = conn.execute(query, params)
            templates = [dict(row) for row in cursor.fetchall()]
            
            # Parse JSON content for each template
            for template in templates:
                if template['template_json']:
                    try:
                        template['content'] = json.loads(template['template_json'])
                    except:
                        template['content'] = {}
            
            return templates
    
    def get_template(self, template_id: str) -> Optional[Dict]:
        """Get a specific template"""
        with self.get_db_connection() as conn:
            cursor = conn.execute('SELECT * FROM content_templates WHERE template_id = ?', (template_id,))
            row = cursor.fetchone()
            if row:
                template = dict(row)
                if template['template_json']:
                    try:
                        template['content'] = json.loads(template['template_json'])
                    except:
                        template['content'] = {}
                return template
            return None
    
    def increment_template_usage(self, template_id: str):
        """Increment template usage counter"""
        with self.get_db_connection() as conn:
            conn.execute('UPDATE content_templates SET usage_count = usage_count + 1 WHERE template_id = ?', (template_id,))
            conn.commit()
    
    # Asset Management Methods
    def create_asset(self, name: str, file_path: str, file_type: str, 
                    file_size: int = None, mime_type: str = None, **kwargs) -> str:
        """Create a new content asset"""
        asset_id = str(uuid.uuid4())
        
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO content_assets 
                (asset_id, name, file_path, file_type, file_size, mime_type, 
                 alt_text, caption, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (asset_id, name, file_path, file_type, file_size, mime_type,
                  kwargs.get('alt_text'), kwargs.get('caption'), kwargs.get('tags')))
            conn.commit()
            
            return asset_id
    
    def get_assets(self, file_type: str = None, limit: int = 100) -> List[Dict]:
        """Get content assets"""
        query = 'SELECT * FROM content_assets WHERE 1=1'
        params = []
        
        if file_type:
            query += ' AND file_type = ?'
            params.append(file_type)
        
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        with self.get_db_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    # A/B Testing Methods
    def create_ab_test(self, name: str, page_id: str, test_type: str, 
                      conversion_goal: str, **kwargs) -> str:
        """Create a new A/B test"""
        test_id = str(uuid.uuid4())
        
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO ab_tests 
                (test_id, name, page_id, test_type, conversion_goal, 
                 traffic_split, start_date, end_date, variant_a_id, variant_b_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (test_id, name, page_id, test_type, conversion_goal,
                  kwargs.get('traffic_split', 0.5), kwargs.get('start_date'),
                  kwargs.get('end_date'), kwargs.get('variant_a_id'), 
                  kwargs.get('variant_b_id')))
            conn.commit()
            
            return test_id
    
    def log_ab_test_event(self, test_id: str, variant: str, event_type: str, 
                         visitor_id: str = None, value: float = None):
        """Log A/B test event"""
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO ab_test_metrics 
                (test_id, variant, visitor_id, event_type, value)
                VALUES (?, ?, ?, ?, ?)
            ''', (test_id, variant, visitor_id, event_type, value))
            conn.commit()
    
    def get_ab_test_results(self, test_id: str) -> Dict:
        """Get A/B test results"""
        with self.get_db_connection() as conn:
            cursor = conn.execute('''
                SELECT 
                    variant,
                    COUNT(*) as total_events,
                    COUNT(DISTINCT visitor_id) as unique_visitors,
                    SUM(CASE WHEN event_type = 'conversion' THEN 1 ELSE 0 END) as conversions,
                    AVG(CASE WHEN event_type = 'conversion' THEN value END) as avg_conversion_value
                FROM ab_test_metrics
                WHERE test_id = ?
                GROUP BY variant
            ''', (test_id,))
            
            results = {}
            for row in cursor.fetchall():
                row_dict = dict(row)
                variant = row_dict.pop('variant')
                results[variant] = row_dict
                
                # Calculate conversion rate
                if row_dict['unique_visitors'] > 0:
                    results[variant]['conversion_rate'] = (row_dict['conversions'] / row_dict['unique_visitors']) * 100
                else:
                    results[variant]['conversion_rate'] = 0
            
            return results
    
    # SEO Methods
    def update_seo_metrics(self, page_id: str, metrics: Dict[str, Any]):
        """Update SEO metrics for a page"""
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO content_seo_metrics 
                (page_id, date, page_views, unique_visitors, bounce_rate, 
                 avg_session_duration, conversion_rate, seo_score, search_rankings)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (page_id, metrics.get('date', datetime.now().date()),
                  metrics.get('page_views', 0), metrics.get('unique_visitors', 0),
                  metrics.get('bounce_rate', 0), metrics.get('avg_session_duration', 0),
                  metrics.get('conversion_rate', 0), metrics.get('seo_score', 0),
                  json.dumps(metrics.get('search_rankings', {}))))
            conn.commit()
    
    def get_seo_metrics(self, page_id: str, days: int = 30) -> List[Dict]:
        """Get SEO metrics for a page"""
        with self.get_db_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM content_seo_metrics
                WHERE page_id = ? AND date >= date('now', '-{} days')
                ORDER BY date DESC
            '''.format(days), (page_id,))
            
            metrics = [dict(row) for row in cursor.fetchall()]
            
            # Parse search rankings JSON
            for metric in metrics:
                if metric['search_rankings']:
                    try:
                        metric['search_rankings'] = json.loads(metric['search_rankings'])
                    except:
                        metric['search_rankings'] = {}
            
            return metrics
    
    # Scheduling Methods
    def schedule_content_action(self, page_id: str, action: str, scheduled_at: datetime) -> str:
        """Schedule a content action"""
        schedule_id = str(uuid.uuid4())
        
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO content_schedule 
                (schedule_id, page_id, action, scheduled_at)
                VALUES (?, ?, ?, ?)
            ''', (schedule_id, page_id, action, scheduled_at))
            conn.commit()
            
            return schedule_id
    
    def get_scheduled_actions(self, status: str = 'pending') -> List[Dict]:
        """Get scheduled content actions"""
        with self.get_db_connection() as conn:
            cursor = conn.execute('''
                SELECT cs.*, cp.name as page_name
                FROM content_schedule cs
                JOIN content_pages cp ON cs.page_id = cp.page_id
                WHERE cs.status = ?
                ORDER BY cs.scheduled_at ASC
            ''', (status,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def execute_scheduled_action(self, schedule_id: str) -> bool:
        """Execute a scheduled content action"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM content_schedule WHERE schedule_id = ?
                ''', (schedule_id,))
                
                row = cursor.fetchone()
                if not row:
                    return False
                
                schedule = dict(row)
                
                # Execute the action based on type
                if schedule['action'] == 'publish':
                    success = self.update_page(schedule['page_id'], {'is_published': True})
                elif schedule['action'] == 'unpublish':
                    success = self.update_page(schedule['page_id'], {'is_published': False})
                else:
                    success = False
                
                # Update schedule status
                if success:
                    conn.execute('''
                        UPDATE content_schedule 
                        SET status = 'completed', executed_at = CURRENT_TIMESTAMP
                        WHERE schedule_id = ?
                    ''', (schedule_id,))
                else:
                    conn.execute('''
                        UPDATE content_schedule 
                        SET status = 'failed', error_message = 'Action execution failed'
                        WHERE schedule_id = ?
                    ''', (schedule_id,))
                
                conn.commit()
                return success
                
        except Exception as e:
            self.logger.error(f"Error executing scheduled action {schedule_id}: {e}")
            return False
    
    # Analytics Methods
    def get_content_analytics(self, days: int = 30) -> Dict:
        """Get content analytics summary"""
        with self.get_db_connection() as conn:
            # Page statistics
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_pages,
                    SUM(CASE WHEN is_published = 1 THEN 1 ELSE 0 END) as published_pages,
                    SUM(CASE WHEN status = 'draft' THEN 1 ELSE 0 END) as draft_pages,
                    COUNT(DISTINCT page_type) as page_types,
                    COUNT(DISTINCT template_id) as unique_templates
                FROM content_pages
            ''')
            page_stats = dict(cursor.fetchone())
            
            # Recent activity
            cursor = conn.execute('''
                SELECT 
                    DATE(updated_at) as date,
                    COUNT(*) as updates
                FROM content_pages
                WHERE updated_at >= date('now', '-{} days')
                GROUP BY DATE(updated_at)
                ORDER BY date DESC
            '''.format(days))
            activity_trend = [dict(row) for row in cursor.fetchall()]
            
            # Template usage
            cursor = conn.execute('''
                SELECT 
                    ct.name,
                    ct.usage_count,
                    ct.category
                FROM content_templates ct
                WHERE ct.is_active = 1
                ORDER BY ct.usage_count DESC
                LIMIT 10
            ''')
            popular_templates = [dict(row) for row in cursor.fetchall()]
            
            # Page types distribution
            cursor = conn.execute('''
                SELECT 
                    page_type,
                    COUNT(*) as count
                FROM content_pages
                GROUP BY page_type
                ORDER BY count DESC
            ''')
            page_type_distribution = [dict(row) for row in cursor.fetchall()]
            
            return {
                'page_stats': page_stats,
                'activity_trend': activity_trend,
                'popular_templates': popular_templates,
                'page_type_distribution': page_type_distribution
            }
    
    # Utility Methods
    def search_content(self, query: str, page_type: str = None, 
                      published_only: bool = False, limit: int = 50) -> List[Dict]:
        """Search content pages"""
        search_query = '''
            SELECT * FROM content_pages 
            WHERE (name LIKE ? OR title LIKE ? OR meta_description LIKE ?)
        '''
        params = [f'%{query}%', f'%{query}%', f'%{query}%']
        
        if page_type:
            search_query += ' AND page_type = ?'
            params.append(page_type)
        
        if published_only:
            search_query += ' AND is_published = 1'
        
        search_query += ' ORDER BY updated_at DESC LIMIT ?'
        params.append(limit)
        
        with self.get_db_connection() as conn:
            cursor = conn.execute(search_query, params)
            results = [dict(row) for row in cursor.fetchall()]
            
            # Parse JSON content for each result
            for result in results:
                if result['content_json']:
                    try:
                        result['content'] = json.loads(result['content_json'])
                    except:
                        result['content'] = {}
            
            return results
    
    def duplicate_page(self, page_id: str, new_name: str, new_slug: str, 
                      author_id: int = None) -> Optional[str]:
        """Duplicate an existing page"""
        original_page = self.get_page(page_id)
        if not original_page:
            return None
        
        # Create new page with duplicated content
        new_page_id = self.create_page(
            name=new_name,
            title=f"Copy of {original_page['title']}",
            slug=new_slug,
            page_type=original_page['page_type'],
            content_json=original_page['content_json'],
            author_id=author_id,
            meta_title=original_page['meta_title'],
            meta_description=original_page['meta_description'],
            meta_keywords=original_page['meta_keywords'],
            custom_css=original_page['custom_css'],
            custom_js=original_page['custom_js'],
            template_id=original_page['template_id']
        )
        
        return new_page_id
    
    def get_page_statistics(self, page_id: str) -> Dict:
        """Get detailed statistics for a page"""
        with self.get_db_connection() as conn:
            # Version count
            cursor = conn.execute('SELECT COUNT(*) FROM content_versions WHERE page_id = ?', (page_id,))
            version_count = cursor.fetchone()[0]
            
            # Latest SEO metrics
            cursor = conn.execute('''
                SELECT * FROM content_seo_metrics 
                WHERE page_id = ? 
                ORDER BY date DESC 
                LIMIT 1
            ''', (page_id,))
            latest_seo = cursor.fetchone()
            seo_metrics = dict(latest_seo) if latest_seo else {}
            
            # A/B tests
            cursor = conn.execute('SELECT COUNT(*) FROM ab_tests WHERE page_id = ?', (page_id,))
            ab_test_count = cursor.fetchone()[0]
            
            # Feedback count
            cursor = conn.execute('SELECT COUNT(*) FROM content_feedback WHERE page_id = ?', (page_id,))
            feedback_count = cursor.fetchone()[0]
            
            return {
                'version_count': version_count,
                'seo_metrics': seo_metrics,
                'ab_test_count': ab_test_count,
                'feedback_count': feedback_count
            }
    
    def cleanup_old_versions(self, days: int = 30, keep_count: int = 5):
        """Clean up old page versions"""
        with self.get_db_connection() as conn:
            cursor = conn.execute('''
                SELECT page_id, COUNT(*) as version_count
                FROM content_versions
                GROUP BY page_id
                HAVING version_count > ?
            ''', (keep_count,))
            
            for row in cursor.fetchall():
                page_id = row['page_id']
                
                # Keep only the latest versions
                conn.execute('''
                    DELETE FROM content_versions 
                    WHERE page_id = ? 
                    AND version_number NOT IN (
                        SELECT version_number 
                        FROM content_versions 
                        WHERE page_id = ? 
                        ORDER BY version_number DESC 
                        LIMIT ?
                    )
                    AND created_at < date('now', '-{} days')
                '''.format(days), (page_id, page_id, keep_count))
            
            conn.commit()
            self.logger.info(f"Cleaned up old versions older than {days} days")

# Global content manager instance
content_manager = ContentManager()