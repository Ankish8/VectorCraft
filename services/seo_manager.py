#!/usr/bin/env python3
"""
SEO Manager Service for VectorCraft
Handles SEO optimization, analytics integration, and search engine optimization
"""

import json
import logging
import re
import requests
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
from .content_manager import content_manager

class SEOManager:
    """Advanced SEO management and optimization service"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.content_manager = content_manager
        
        # SEO configuration
        self.min_title_length = 30
        self.max_title_length = 60
        self.min_description_length = 120
        self.max_description_length = 160
        self.min_content_length = 300
        self.max_keyword_density = 3.0
        
        # Common keywords for VectorCraft
        self.vectorcraft_keywords = [
            'vector conversion', 'image to vector', 'svg converter',
            'vectorize image', 'vector graphics', 'scalable vector',
            'svg file', 'vector art', 'convert to svg', 'vector tool'
        ]
    
    def analyze_page_seo(self, page_id: str) -> Dict[str, Any]:
        """Comprehensive SEO analysis of a page"""
        page = self.content_manager.get_page(page_id)
        if not page:
            return {'error': 'Page not found'}
        
        analysis = {
            'page_id': page_id,
            'analyzed_at': datetime.now().isoformat(),
            'score': 0,
            'issues': [],
            'recommendations': [],
            'technical_seo': {},
            'content_analysis': {},
            'mobile_optimization': {},
            'performance': {}
        }
        
        # Title analysis
        title_analysis = self.analyze_title(page.get('title', ''), page.get('meta_title'))
        analysis['technical_seo']['title'] = title_analysis
        
        # Meta description analysis
        description_analysis = self.analyze_meta_description(page.get('meta_description', ''))
        analysis['technical_seo']['meta_description'] = description_analysis
        
        # Keywords analysis
        keywords_analysis = self.analyze_keywords(page.get('meta_keywords', ''))
        analysis['technical_seo']['keywords'] = keywords_analysis
        
        # Content analysis
        content_analysis = self.analyze_content(page.get('content', {}))
        analysis['content_analysis'] = content_analysis
        
        # URL analysis
        url_analysis = self.analyze_url(page.get('slug', ''))
        analysis['technical_seo']['url'] = url_analysis
        
        # Mobile optimization
        mobile_analysis = self.analyze_mobile_optimization(page.get('content', {}))
        analysis['mobile_optimization'] = mobile_analysis
        
        # Performance analysis
        performance_analysis = self.analyze_performance(page.get('content', {}))
        analysis['performance'] = performance_analysis
        
        # Calculate overall score
        analysis['score'] = self.calculate_seo_score(analysis)
        
        # Generate recommendations
        analysis['recommendations'] = self.generate_recommendations(analysis)
        
        return analysis
    
    def analyze_title(self, page_title: str, meta_title: str = None) -> Dict[str, Any]:
        """Analyze page title for SEO"""
        title = meta_title or page_title
        
        analysis = {
            'title': title,
            'length': len(title),
            'score': 0,
            'issues': [],
            'recommendations': []
        }
        
        if not title:
            analysis['issues'].append('Missing title')
            analysis['recommendations'].append('Add a compelling title')
            return analysis
        
        # Length check
        if len(title) < self.min_title_length:
            analysis['issues'].append('Title too short')
            analysis['recommendations'].append(f'Expand title to at least {self.min_title_length} characters')
            analysis['score'] -= 20
        elif len(title) > self.max_title_length:
            analysis['issues'].append('Title too long')
            analysis['recommendations'].append(f'Shorten title to under {self.max_title_length} characters')
            analysis['score'] -= 10
        else:
            analysis['score'] += 20
        
        # Keyword analysis
        title_lower = title.lower()
        keyword_found = False
        for keyword in self.vectorcraft_keywords:
            if keyword in title_lower:
                keyword_found = True
                analysis['score'] += 15
                break
        
        if not keyword_found:
            analysis['recommendations'].append('Include relevant keywords like "vector conversion" or "image to vector"')
            analysis['score'] -= 15
        
        # Brand presence
        if 'vectorcraft' in title_lower:
            analysis['score'] += 10
        else:
            analysis['recommendations'].append('Consider including "VectorCraft" in the title for brand recognition')
        
        # Special characters and readability
        if '|' in title or '-' in title:
            analysis['score'] += 5
        
        analysis['score'] = max(0, min(100, analysis['score'] + 60))  # Base score of 60
        
        return analysis
    
    def analyze_meta_description(self, description: str) -> Dict[str, Any]:
        """Analyze meta description for SEO"""
        analysis = {
            'description': description,
            'length': len(description),
            'score': 0,
            'issues': [],
            'recommendations': []
        }
        
        if not description:
            analysis['issues'].append('Missing meta description')
            analysis['recommendations'].append('Add a compelling meta description')
            return analysis
        
        # Length check
        if len(description) < self.min_description_length:
            analysis['issues'].append('Meta description too short')
            analysis['recommendations'].append(f'Expand description to at least {self.min_description_length} characters')
            analysis['score'] -= 20
        elif len(description) > self.max_description_length:
            analysis['issues'].append('Meta description too long')
            analysis['recommendations'].append(f'Shorten description to under {self.max_description_length} characters')
            analysis['score'] -= 10
        else:
            analysis['score'] += 25
        
        # Keyword analysis
        description_lower = description.lower()
        keyword_found = False
        for keyword in self.vectorcraft_keywords:
            if keyword in description_lower:
                keyword_found = True
                analysis['score'] += 15
                break
        
        if not keyword_found:
            analysis['recommendations'].append('Include relevant keywords in meta description')
            analysis['score'] -= 15
        
        # Call to action
        cta_phrases = ['try', 'get', 'download', 'convert', 'start', 'create', 'transform']
        has_cta = any(phrase in description_lower for phrase in cta_phrases)
        if has_cta:
            analysis['score'] += 10
        else:
            analysis['recommendations'].append('Add a call-to-action phrase like "Get started" or "Try now"')
        
        analysis['score'] = max(0, min(100, analysis['score'] + 50))  # Base score of 50
        
        return analysis
    
    def analyze_keywords(self, keywords: str) -> Dict[str, Any]:
        """Analyze meta keywords"""
        analysis = {
            'keywords': keywords,
            'count': 0,
            'score': 0,
            'issues': [],
            'recommendations': []
        }
        
        if not keywords:
            analysis['recommendations'].append('Consider adding relevant meta keywords')
            analysis['score'] = 70  # Keywords are less important now
            return analysis
        
        keyword_list = [k.strip() for k in keywords.split(',')]
        analysis['count'] = len(keyword_list)
        
        if len(keyword_list) > 10:
            analysis['issues'].append('Too many keywords')
            analysis['recommendations'].append('Focus on 5-10 most relevant keywords')
            analysis['score'] -= 10
        
        # Check for VectorCraft relevant keywords
        relevant_count = 0
        for keyword in keyword_list:
            if any(vk in keyword.lower() for vk in self.vectorcraft_keywords):
                relevant_count += 1
        
        if relevant_count > 0:
            analysis['score'] += 20
        else:
            analysis['recommendations'].append('Include VectorCraft-relevant keywords')
        
        analysis['score'] = max(0, min(100, analysis['score'] + 60))
        
        return analysis
    
    def analyze_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze page content for SEO"""
        analysis = {
            'word_count': 0,
            'headings': {'h1': 0, 'h2': 0, 'h3': 0},
            'images': {'total': 0, 'with_alt': 0, 'without_alt': 0},
            'links': {'internal': 0, 'external': 0},
            'keyword_density': 0.0,
            'readability_score': 0,
            'score': 0,
            'issues': [],
            'recommendations': []
        }
        
        if not content or 'sections' not in content:
            analysis['issues'].append('No content found')
            analysis['recommendations'].append('Add meaningful content to the page')
            return analysis
        
        # Extract text from all sections
        all_text = ""
        for section in content.get('sections', []):
            section_text = self.extract_text_from_section(section)
            all_text += section_text + " "
        
        analysis['word_count'] = len(all_text.split())
        
        # Word count analysis
        if analysis['word_count'] < self.min_content_length:
            analysis['issues'].append('Content too short')
            analysis['recommendations'].append(f'Add more content (minimum {self.min_content_length} words)')
            analysis['score'] -= 20
        else:
            analysis['score'] += 20
        
        # Heading analysis
        headings = self.extract_headings_from_content(content)
        analysis['headings'] = headings
        
        if headings['h1'] == 0:
            analysis['issues'].append('Missing H1 heading')
            analysis['recommendations'].append('Add a primary heading (H1)')
            analysis['score'] -= 15
        elif headings['h1'] > 1:
            analysis['issues'].append('Multiple H1 headings')
            analysis['recommendations'].append('Use only one H1 heading per page')
            analysis['score'] -= 10
        else:
            analysis['score'] += 15
        
        if headings['h2'] == 0:
            analysis['recommendations'].append('Add H2 subheadings to improve structure')
        else:
            analysis['score'] += 10
        
        # Image analysis
        images = self.extract_images_from_content(content)
        analysis['images'] = images
        
        if images['without_alt'] > 0:
            analysis['issues'].append(f'{images["without_alt"]} images without alt text')
            analysis['recommendations'].append('Add alt text to all images')
            analysis['score'] -= 10
        
        # Keyword density
        keyword_density = self.calculate_keyword_density(all_text)
        analysis['keyword_density'] = keyword_density
        
        if keyword_density > self.max_keyword_density:
            analysis['issues'].append('Keyword density too high')
            analysis['recommendations'].append('Reduce keyword repetition to improve readability')
            analysis['score'] -= 10
        elif keyword_density < 0.5:
            analysis['recommendations'].append('Consider increasing keyword usage naturally')
        else:
            analysis['score'] += 10
        
        # Readability score
        readability = self.calculate_readability_score(all_text)
        analysis['readability_score'] = readability
        
        if readability < 60:
            analysis['issues'].append('Content may be difficult to read')
            analysis['recommendations'].append('Simplify language and use shorter sentences')
            analysis['score'] -= 5
        else:
            analysis['score'] += 5
        
        analysis['score'] = max(0, min(100, analysis['score'] + 50))
        
        return analysis
    
    def analyze_url(self, slug: str) -> Dict[str, Any]:
        """Analyze URL structure for SEO"""
        analysis = {
            'slug': slug,
            'length': len(slug),
            'score': 0,
            'issues': [],
            'recommendations': []
        }
        
        if not slug:
            analysis['issues'].append('Missing URL slug')
            analysis['recommendations'].append('Add a SEO-friendly URL slug')
            return analysis
        
        # Length check
        if len(slug) > 60:
            analysis['issues'].append('URL too long')
            analysis['recommendations'].append('Shorten URL to under 60 characters')
            analysis['score'] -= 10
        else:
            analysis['score'] += 10
        
        # Special characters
        if not re.match(r'^[a-z0-9-]+$', slug):
            analysis['issues'].append('URL contains invalid characters')
            analysis['recommendations'].append('Use only lowercase letters, numbers, and hyphens')
            analysis['score'] -= 15
        else:
            analysis['score'] += 15
        
        # Keyword presence
        slug_lower = slug.lower()
        keyword_found = False
        for keyword in self.vectorcraft_keywords:
            if any(word in slug_lower for word in keyword.split()):
                keyword_found = True
                analysis['score'] += 15
                break
        
        if not keyword_found:
            analysis['recommendations'].append('Include relevant keywords in URL')
        
        # Readability
        if '-' in slug and len(slug.split('-')) > 1:
            analysis['score'] += 10
        else:
            analysis['recommendations'].append('Use hyphens to separate words in URL')
        
        analysis['score'] = max(0, min(100, analysis['score'] + 60))
        
        return analysis
    
    def analyze_mobile_optimization(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze mobile optimization"""
        analysis = {
            'viewport_meta': True,  # Assumed present in template
            'responsive_design': True,  # Assumed from template
            'touch_friendly': True,  # Assumed from template
            'loading_speed': 'good',  # Placeholder
            'score': 0,
            'issues': [],
            'recommendations': []
        }
        
        # Check for mobile-unfriendly elements
        if content and 'sections' in content:
            for section in content['sections']:
                settings = section.get('settings', {})
                
                # Check for fixed widths
                if 'width' in settings and isinstance(settings['width'], str) and 'px' in settings['width']:
                    analysis['issues'].append('Fixed pixel widths may not be mobile-friendly')
                    analysis['recommendations'].append('Use responsive units like percentages or rem')
                    analysis['score'] -= 10
                
                # Check for small text
                if 'font_size' in settings and isinstance(settings['font_size'], (int, float)) and settings['font_size'] < 14:
                    analysis['issues'].append('Text may be too small for mobile devices')
                    analysis['recommendations'].append('Use minimum 14px font size for body text')
                    analysis['score'] -= 5
        
        # Base score for assumed mobile optimizations
        analysis['score'] = max(0, min(100, analysis['score'] + 85))
        
        return analysis
    
    def analyze_performance(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze page performance factors"""
        analysis = {
            'estimated_load_time': 0,
            'image_optimization': {'optimized': 0, 'total': 0},
            'css_optimization': 'good',
            'js_optimization': 'good',
            'score': 0,
            'issues': [],
            'recommendations': []
        }
        
        if not content or 'sections' not in content:
            return analysis
        
        # Count images and estimate load impact
        image_count = 0
        for section in content['sections']:
            section_content = section.get('content', {})
            
            # Count various image types
            if 'hero_image' in section_content:
                image_count += 1
            
            if 'features' in section_content:
                for feature in section_content['features']:
                    if 'image' in feature:
                        image_count += 1
            
            if 'testimonials' in section_content:
                for testimonial in section_content['testimonials']:
                    if 'avatar' in testimonial:
                        image_count += 1
        
        analysis['image_optimization']['total'] = image_count
        
        # Estimate load time based on content complexity
        estimated_load_time = 1.5  # Base load time
        estimated_load_time += image_count * 0.3  # Each image adds 0.3s
        estimated_load_time += len(content['sections']) * 0.1  # Each section adds 0.1s
        
        analysis['estimated_load_time'] = round(estimated_load_time, 1)
        
        # Performance recommendations
        if estimated_load_time > 3:
            analysis['issues'].append('Estimated load time is high')
            analysis['recommendations'].append('Optimize images and reduce page complexity')
            analysis['score'] -= 20
        elif estimated_load_time > 2:
            analysis['recommendations'].append('Consider optimizing images for faster loading')
            analysis['score'] -= 10
        else:
            analysis['score'] += 20
        
        if image_count > 10:
            analysis['issues'].append('High number of images may slow loading')
            analysis['recommendations'].append('Consider lazy loading or image optimization')
            analysis['score'] -= 10
        
        analysis['score'] = max(0, min(100, analysis['score'] + 70))
        
        return analysis
    
    def calculate_seo_score(self, analysis: Dict[str, Any]) -> int:
        """Calculate overall SEO score"""
        scores = []
        
        # Technical SEO (40% weight)
        technical_score = 0
        if 'technical_seo' in analysis:
            technical_score += analysis['technical_seo'].get('title', {}).get('score', 0) * 0.4
            technical_score += analysis['technical_seo'].get('meta_description', {}).get('score', 0) * 0.3
            technical_score += analysis['technical_seo'].get('keywords', {}).get('score', 0) * 0.1
            technical_score += analysis['technical_seo'].get('url', {}).get('score', 0) * 0.2
        
        # Content (30% weight)
        content_score = analysis.get('content_analysis', {}).get('score', 0)
        
        # Mobile optimization (15% weight)
        mobile_score = analysis.get('mobile_optimization', {}).get('score', 0)
        
        # Performance (15% weight)
        performance_score = analysis.get('performance', {}).get('score', 0)
        
        # Calculate weighted average
        overall_score = (
            technical_score * 0.4 +
            content_score * 0.3 +
            mobile_score * 0.15 +
            performance_score * 0.15
        )
        
        return int(round(overall_score))
    
    def generate_recommendations(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate prioritized SEO recommendations"""
        recommendations = []
        
        # Collect all recommendations with priorities
        if 'technical_seo' in analysis:
            for key, data in analysis['technical_seo'].items():
                for rec in data.get('recommendations', []):
                    recommendations.append({
                        'category': f'Technical SEO - {key.title()}',
                        'recommendation': rec,
                        'priority': 'high' if data.get('score', 0) < 50 else 'medium',
                        'impact': 'high' if key in ['title', 'meta_description'] else 'medium'
                    })
        
        if 'content_analysis' in analysis:
            for rec in analysis['content_analysis'].get('recommendations', []):
                recommendations.append({
                    'category': 'Content',
                    'recommendation': rec,
                    'priority': 'high' if analysis['content_analysis'].get('score', 0) < 50 else 'medium',
                    'impact': 'high'
                })
        
        if 'mobile_optimization' in analysis:
            for rec in analysis['mobile_optimization'].get('recommendations', []):
                recommendations.append({
                    'category': 'Mobile',
                    'recommendation': rec,
                    'priority': 'medium',
                    'impact': 'medium'
                })
        
        if 'performance' in analysis:
            for rec in analysis['performance'].get('recommendations', []):
                recommendations.append({
                    'category': 'Performance',
                    'recommendation': rec,
                    'priority': 'medium',
                    'impact': 'medium'
                })
        
        # Sort by priority (high first) and impact
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        impact_order = {'high': 3, 'medium': 2, 'low': 1}
        
        recommendations.sort(
            key=lambda x: (priority_order.get(x['priority'], 0), impact_order.get(x['impact'], 0)),
            reverse=True
        )
        
        return recommendations
    
    def extract_text_from_section(self, section: Dict[str, Any]) -> str:
        """Extract text content from a section"""
        text = ""
        content = section.get('content', {})
        
        # Extract common text fields
        for field in ['headline', 'subheadline', 'title', 'description', 'text']:
            if field in content:
                text += content[field] + " "
        
        # Extract from features
        if 'features' in content:
            for feature in content['features']:
                text += feature.get('title', '') + " "
                text += feature.get('description', '') + " "
        
        # Extract from testimonials
        if 'testimonials' in content:
            for testimonial in content['testimonials']:
                text += testimonial.get('quote', '') + " "
                text += testimonial.get('author', '') + " "
        
        # Extract from lists
        if 'features' in content and isinstance(content['features'], list):
            for feature in content['features']:
                if isinstance(feature, str):
                    text += feature + " "
        
        return text.strip()
    
    def extract_headings_from_content(self, content: Dict[str, Any]) -> Dict[str, int]:
        """Extract heading counts from content"""
        headings = {'h1': 0, 'h2': 0, 'h3': 0}
        
        for section in content.get('sections', []):
            section_content = section.get('content', {})
            section_type = section.get('type', '')
            
            # H1 headings (main headlines)
            if section_type in ['hero', 'hero-minimal', 'professional-hero', 'launch-hero']:
                if 'headline' in section_content:
                    headings['h1'] += 1
            
            # H2 headings (section titles)
            if 'title' in section_content:
                headings['h2'] += 1
            
            # H3 headings (feature titles, etc.)
            if 'features' in section_content:
                for feature in section_content['features']:
                    if 'title' in feature:
                        headings['h3'] += 1
        
        return headings
    
    def extract_images_from_content(self, content: Dict[str, Any]) -> Dict[str, int]:
        """Extract image counts from content"""
        images = {'total': 0, 'with_alt': 0, 'without_alt': 0}
        
        for section in content.get('sections', []):
            section_content = section.get('content', {})
            
            # Hero images
            if 'hero_image' in section_content:
                images['total'] += 1
                if section_content.get('hero_image_alt'):
                    images['with_alt'] += 1
                else:
                    images['without_alt'] += 1
            
            # Feature images
            if 'features' in section_content:
                for feature in section_content['features']:
                    if 'image' in feature:
                        images['total'] += 1
                        if feature.get('image_alt'):
                            images['with_alt'] += 1
                        else:
                            images['without_alt'] += 1
            
            # Testimonial avatars
            if 'testimonials' in section_content:
                for testimonial in section_content['testimonials']:
                    if 'avatar' in testimonial:
                        images['total'] += 1
                        if testimonial.get('avatar_alt'):
                            images['with_alt'] += 1
                        else:
                            images['without_alt'] += 1
        
        return images
    
    def calculate_keyword_density(self, text: str) -> float:
        """Calculate keyword density for VectorCraft keywords"""
        if not text:
            return 0.0
        
        words = text.lower().split()
        total_words = len(words)
        
        if total_words == 0:
            return 0.0
        
        keyword_count = 0
        for keyword in self.vectorcraft_keywords:
            keyword_words = keyword.split()
            if len(keyword_words) == 1:
                keyword_count += words.count(keyword_words[0])
            else:
                # Count multi-word keywords
                for i in range(len(words) - len(keyword_words) + 1):
                    if words[i:i+len(keyword_words)] == keyword_words:
                        keyword_count += 1
        
        return (keyword_count / total_words) * 100
    
    def calculate_readability_score(self, text: str) -> float:
        """Calculate a simple readability score"""
        if not text:
            return 0.0
        
        sentences = text.split('.')
        words = text.split()
        
        if len(sentences) == 0 or len(words) == 0:
            return 0.0
        
        avg_sentence_length = len(words) / len(sentences)
        avg_word_length = sum(len(word) for word in words) / len(words)
        
        # Simple readability score (higher is better)
        score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_word_length)
        
        return max(0, min(100, score))
    
    def generate_seo_report(self, page_id: str) -> Dict[str, Any]:
        """Generate comprehensive SEO report"""
        analysis = self.analyze_page_seo(page_id)
        
        report = {
            'page_id': page_id,
            'generated_at': datetime.now().isoformat(),
            'overall_score': analysis.get('score', 0),
            'grade': self.get_seo_grade(analysis.get('score', 0)),
            'summary': self.generate_seo_summary(analysis),
            'detailed_analysis': analysis,
            'action_items': self.generate_action_items(analysis),
            'competitive_analysis': self.generate_competitive_insights()
        }
        
        return report
    
    def get_seo_grade(self, score: int) -> str:
        """Convert SEO score to letter grade"""
        if score >= 90:
            return 'A+'
        elif score >= 80:
            return 'A'
        elif score >= 70:
            return 'B'
        elif score >= 60:
            return 'C'
        elif score >= 50:
            return 'D'
        else:
            return 'F'
    
    def generate_seo_summary(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate SEO summary"""
        score = analysis.get('score', 0)
        
        if score >= 80:
            status = 'Excellent'
            message = 'Your page is well-optimized for search engines.'
        elif score >= 60:
            status = 'Good'
            message = 'Your page has good SEO with room for improvement.'
        elif score >= 40:
            status = 'Fair'
            message = 'Your page needs SEO improvements to rank better.'
        else:
            status = 'Poor'
            message = 'Your page requires significant SEO work.'
        
        return {
            'status': status,
            'message': message,
            'score': score,
            'issues_count': len(analysis.get('recommendations', [])),
            'critical_issues': [
                rec for rec in analysis.get('recommendations', [])
                if rec.get('priority') == 'high'
            ]
        }
    
    def generate_action_items(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate prioritized action items"""
        action_items = []
        
        recommendations = analysis.get('recommendations', [])
        
        # Group by priority
        high_priority = [r for r in recommendations if r.get('priority') == 'high']
        medium_priority = [r for r in recommendations if r.get('priority') == 'medium']
        
        # Add high priority items
        for i, rec in enumerate(high_priority[:5]):  # Top 5 high priority
            action_items.append({
                'priority': 'high',
                'order': i + 1,
                'category': rec.get('category', 'SEO'),
                'task': rec.get('recommendation', ''),
                'impact': rec.get('impact', 'medium'),
                'estimated_effort': 'low' if 'add' in rec.get('recommendation', '').lower() else 'medium'
            })
        
        # Add medium priority items
        for i, rec in enumerate(medium_priority[:3]):  # Top 3 medium priority
            action_items.append({
                'priority': 'medium',
                'order': len(high_priority) + i + 1,
                'category': rec.get('category', 'SEO'),
                'task': rec.get('recommendation', ''),
                'impact': rec.get('impact', 'medium'),
                'estimated_effort': 'low'
            })
        
        return action_items
    
    def generate_competitive_insights(self) -> Dict[str, Any]:
        """Generate competitive SEO insights"""
        return {
            'industry': 'Vector Conversion Tools',
            'average_score': 65,
            'top_keywords': [
                {'keyword': 'vector conversion', 'difficulty': 'medium', 'volume': 'high'},
                {'keyword': 'image to vector', 'difficulty': 'medium', 'volume': 'medium'},
                {'keyword': 'svg converter', 'difficulty': 'low', 'volume': 'medium'},
                {'keyword': 'vectorize image', 'difficulty': 'low', 'volume': 'low'},
                {'keyword': 'convert to svg', 'difficulty': 'low', 'volume': 'low'}
            ],
            'recommendations': [
                'Target long-tail keywords with lower competition',
                'Focus on local SEO if applicable',
                'Create content around vector design tutorials',
                'Build backlinks from design communities'
            ]
        }
    
    def track_seo_performance(self, page_id: str, metrics: Dict[str, Any]) -> bool:
        """Track SEO performance over time"""
        try:
            # Update SEO metrics in content manager
            self.content_manager.update_seo_metrics(page_id, {
                'date': datetime.now().date(),
                'seo_score': metrics.get('seo_score', 0),
                'page_views': metrics.get('page_views', 0),
                'unique_visitors': metrics.get('unique_visitors', 0),
                'bounce_rate': metrics.get('bounce_rate', 0),
                'avg_session_duration': metrics.get('avg_session_duration', 0),
                'conversion_rate': metrics.get('conversion_rate', 0),
                'search_rankings': metrics.get('search_rankings', {})
            })
            
            return True
        except Exception as e:
            self.logger.error(f"Error tracking SEO performance: {e}")
            return False
    
    def get_seo_trends(self, page_id: str, days: int = 30) -> Dict[str, Any]:
        """Get SEO performance trends"""
        metrics = self.content_manager.get_seo_metrics(page_id, days)
        
        if not metrics:
            return {'error': 'No SEO data available'}
        
        # Calculate trends
        trends = {
            'period': f'Last {days} days',
            'data_points': len(metrics),
            'seo_score_trend': self.calculate_trend([m['seo_score'] for m in metrics]),
            'traffic_trend': self.calculate_trend([m['page_views'] for m in metrics]),
            'conversion_trend': self.calculate_trend([m['conversion_rate'] for m in metrics]),
            'latest_metrics': metrics[0] if metrics else {},
            'summary': {}
        }
        
        # Generate summary
        if trends['seo_score_trend'] > 0:
            trends['summary']['seo_score'] = 'improving'
        elif trends['seo_score_trend'] < 0:
            trends['summary']['seo_score'] = 'declining'
        else:
            trends['summary']['seo_score'] = 'stable'
        
        return trends
    
    def calculate_trend(self, values: List[float]) -> float:
        """Calculate trend direction (-1 to 1)"""
        if len(values) < 2:
            return 0.0
        
        # Simple trend calculation
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        if not first_half or not second_half:
            return 0.0
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        if first_avg == 0:
            return 0.0
        
        return (second_avg - first_avg) / first_avg

# Global SEO manager instance
seo_manager = SEOManager()