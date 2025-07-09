#!/usr/bin/env python3
"""
VectorCraft Admin System Testing Script
Comprehensive validation of all admin functionality after fixes

This script tests:
1. Navigation links and route handlers
2. Template rendering and errors
3. Form functionality
4. UI consistency
5. Integration between modules
"""

import sys
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, '/Users/ankish/Downloads/VC2')

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('admin_system_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class AdminSystemTester:
    """Comprehensive testing suite for VectorCraft admin system"""
    
    def __init__(self):
        self.test_results = {
            'navigation_tests': [],
            'template_tests': [],
            'form_tests': [],
            'integration_tests': [],
            'ui_consistency_tests': []
        }
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all test suites"""
        logger.info("🧪 Starting VectorCraft Admin System Testing")
        logger.info("=" * 60)
        
        # Test Navigation System
        self._test_navigation_links()
        
        # Test Template Rendering
        self._test_template_rendering()
        
        # Test Form Functionality
        self._test_form_functionality()
        
        # Test UI Consistency
        self._test_ui_consistency()
        
        # Test Integration
        self._test_module_integration()
        
        # Generate Report
        return self._generate_test_report()
    
    def _test_navigation_links(self):
        """Test all navigation links and route handlers"""
        logger.info("🔗 Testing Navigation Links")
        
        # Define expected navigation routes
        expected_routes = [
            ('admin.admin_dashboard', '/admin/dashboard'),
            ('admin.system_config', '/admin/system-config'),
            ('admin.system_control', '/admin/system-control'),
            ('admin.pricing_dashboard', '/admin/pricing/dashboard'),
            ('admin.email_campaigns', '/admin/email-campaigns'),
            ('admin.marketing_dashboard', '/admin/marketing'),
            ('admin.permissions_dashboard', '/admin/permissions'),
            ('admin.security_dashboard', '/admin/security'),
            ('admin.content_dashboard', '/admin/content'),
            ('admin.performance_dashboard', '/admin/performance'),
            ('admin.business_logic_dashboard', '/admin/business-logic'),
        ]
        
        # Test route handler functions exist
        blueprint_files = [
            'routes.py',
            'system_config.py',
            'system_control.py',
            'pricing.py',
            'email_campaigns.py',
            'marketing.py',
            'permissions.py',
            'security.py',
            'content.py',
            'performance.py',
            'business_logic.py'
        ]
        
        for route_name, route_path in expected_routes:
            test_name = f"Navigation: {route_name}"
            try:
                # Check if route handler function exists
                function_name = route_name.split('.')[-1]
                if self._check_route_function_exists(function_name):
                    self._record_test_result(test_name, True, "Route handler function exists")
                else:
                    self._record_test_result(test_name, False, f"Route handler function '{function_name}' not found")
            except Exception as e:
                self._record_test_result(test_name, False, f"Error testing route: {str(e)}")
    
    def _test_template_rendering(self):
        """Test template existence and rendering"""
        logger.info("📄 Testing Template Rendering")
        
        # Define required templates
        required_templates = [
            'admin/base.html',
            'admin/dashboard.html',
            'admin/system_config.html',
            'admin/system_control.html',
            'admin/pricing_dashboard.html',
            'admin/email_campaigns.html',
            'admin/marketing/dashboard.html',
            'admin/permissions/dashboard.html',
            'admin/security/dashboard.html',
            'admin/content/dashboard.html',
            'admin/performance.html',
            'admin/business_logic.html',
            'admin/error.html',
            'admin/architecture.html',
            'admin/performance_tuning.html',
            'admin/benchmarks.html',
            'admin/optimization.html',
            'admin/pricing_tiers.html',
            'admin/create_tier.html',
            'admin/edit_tier.html',
            'admin/pricing_analytics.html',
            'admin/discount_codes.html',
            'admin/revenue_reports.html',
            'admin/subscription_management.html',
            'admin/payment_gateway.html',
            'admin/billing_settings.html'
        ]
        
        template_dir = Path('/Users/ankish/Downloads/VC2/templates')
        
        for template_path in required_templates:
            test_name = f"Template: {template_path}"
            try:
                full_path = template_dir / template_path
                if full_path.exists():
                    # Check for basic template syntax
                    with open(full_path, 'r') as f:
                        content = f.read()
                        if self._validate_template_syntax(content):
                            self._record_test_result(test_name, True, "Template exists and has valid syntax")
                        else:
                            self._record_test_result(test_name, False, "Template has syntax errors")
                else:
                    self._record_test_result(test_name, False, "Template file not found")
            except Exception as e:
                self._record_test_result(test_name, False, f"Error testing template: {str(e)}")
    
    def _test_form_functionality(self):
        """Test form elements and validation"""
        logger.info("📝 Testing Form Functionality")
        
        # Test forms in key templates
        form_templates = [
            ('admin/system_config.html', ['paypal-config-form', 'email-config-form']),
            ('admin/create_tier.html', ['createTierForm']),
            ('admin/edit_tier.html', ['editTierForm']),
            ('admin/discount_codes.html', ['discountCodeForm']),
            ('admin/billing_settings.html', ['billingConfigForm', 'invoiceSettingsForm']),
            ('admin/permissions/dashboard.html', ['create-permission-form', 'create-role-form'])
        ]
        
        template_dir = Path('/Users/ankish/Downloads/VC2/templates')
        
        for template_path, form_ids in form_templates:
            full_path = template_dir / template_path
            if full_path.exists():
                try:
                    with open(full_path, 'r') as f:
                        content = f.read()
                        for form_id in form_ids:
                            test_name = f"Form: {template_path} - {form_id}"
                            if f'id="{form_id}"' in content or f"id='{form_id}'" in content:
                                # Check for form validation
                                has_validation = 'required' in content and 'validation' in content.lower()
                                self._record_test_result(test_name, True, 
                                    f"Form exists {'with validation' if has_validation else 'without validation'}")
                            else:
                                self._record_test_result(test_name, False, f"Form {form_id} not found")
                except Exception as e:
                    self._record_test_result(f"Form: {template_path}", False, f"Error testing forms: {str(e)}")
    
    def _test_ui_consistency(self):
        """Test UI consistency across templates"""
        logger.info("🎨 Testing UI Consistency")
        
        # Check if design system CSS is included
        base_template_path = Path('/Users/ankish/Downloads/VC2/templates/admin/base.html')
        design_system_path = Path('/Users/ankish/Downloads/VC2/static/css/admin-design-system.css')
        
        test_name = "UI: Design System CSS"
        try:
            if design_system_path.exists():
                with open(base_template_path, 'r') as f:
                    base_content = f.read()
                    if 'admin-design-system.css' in base_content:
                        self._record_test_result(test_name, True, "Design system CSS included in base template")
                    else:
                        self._record_test_result(test_name, False, "Design system CSS not included in base template")
            else:
                self._record_test_result(test_name, False, "Design system CSS file not found")
        except Exception as e:
            self._record_test_result(test_name, False, f"Error testing design system: {str(e)}")
        
        # Check for consistent button classes
        templates_to_check = [
            'admin/system_config.html',
            'admin/pricing_dashboard.html',
            'admin/create_tier.html'
        ]
        
        template_dir = Path('/Users/ankish/Downloads/VC2/templates')
        
        for template_path in templates_to_check:
            full_path = template_dir / template_path
            if full_path.exists():
                test_name = f"UI Consistency: {template_path}"
                try:
                    with open(full_path, 'r') as f:
                        content = f.read()
                        # Check for consistent button classes
                        has_bootstrap_buttons = 'btn btn-' in content
                        has_consistent_styling = 'class="btn' in content
                        
                        if has_bootstrap_buttons and has_consistent_styling:
                            self._record_test_result(test_name, True, "Consistent button styling found")
                        else:
                            self._record_test_result(test_name, False, "Inconsistent button styling")
                except Exception as e:
                    self._record_test_result(test_name, False, f"Error testing UI consistency: {str(e)}")
    
    def _test_module_integration(self):
        """Test integration between modules"""
        logger.info("🔗 Testing Module Integration")
        
        # Check blueprint registration
        blueprint_init_path = Path('/Users/ankish/Downloads/VC2/blueprints/admin/__init__.py')
        
        test_name = "Integration: Blueprint Registration"
        try:
            if blueprint_init_path.exists():
                with open(blueprint_init_path, 'r') as f:
                    content = f.read()
                    
                    # Check for all required module imports
                    required_imports = [
                        'routes', 'monitoring', 'dashboard', 'analytics_routes',
                        'system_config', 'system_control', 'pricing', 'email_campaigns',
                        'marketing', 'permissions', 'performance', 'content',
                        'business_logic', 'security'
                    ]
                    
                    missing_imports = []
                    for import_name in required_imports:
                        if import_name not in content:
                            missing_imports.append(import_name)
                    
                    if not missing_imports:
                        self._record_test_result(test_name, True, "All required modules imported")
                    else:
                        self._record_test_result(test_name, False, f"Missing imports: {', '.join(missing_imports)}")
            else:
                self._record_test_result(test_name, False, "Blueprint __init__.py not found")
        except Exception as e:
            self._record_test_result(test_name, False, f"Error testing integration: {str(e)}")
    
    def _check_route_function_exists(self, function_name: str) -> bool:
        """Check if a route handler function exists in blueprint files"""
        blueprint_dir = Path('/Users/ankish/Downloads/VC2/blueprints/admin')
        
        for py_file in blueprint_dir.glob('*.py'):
            if py_file.name == '__init__.py':
                continue
                
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                    if f'def {function_name}(' in content:
                        return True
            except Exception:
                continue
        
        return False
    
    def _validate_template_syntax(self, content: str) -> bool:
        """Basic template syntax validation"""
        try:
            # Check for balanced template tags
            if content.count('{%') != content.count('%}'):
                return False
            if content.count('{{') != content.count('}}'):
                return False
            
            # Check for extends tag
            if 'extends' in content and not content.strip().startswith('{% extends'):
                return False
            
            return True
        except Exception:
            return False
    
    def _record_test_result(self, test_name: str, passed: bool, message: str):
        """Record a test result"""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            logger.info(f"✅ {test_name}: {message}")
        else:
            self.failed_tests += 1
            logger.error(f"❌ {test_name}: {message}")
        
        # Categorize test results
        if test_name.startswith('Navigation'):
            self.test_results['navigation_tests'].append({
                'name': test_name,
                'passed': passed,
                'message': message
            })
        elif test_name.startswith('Template'):
            self.test_results['template_tests'].append({
                'name': test_name,
                'passed': passed,
                'message': message
            })
        elif test_name.startswith('Form'):
            self.test_results['form_tests'].append({
                'name': test_name,
                'passed': passed,
                'message': message
            })
        elif test_name.startswith('UI'):
            self.test_results['ui_consistency_tests'].append({
                'name': test_name,
                'passed': passed,
                'message': message
            })
        elif test_name.startswith('Integration'):
            self.test_results['integration_tests'].append({
                'name': test_name,
                'passed': passed,
                'message': message
            })
    
    def _generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        success_rate = (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tests': self.total_tests,
                'passed_tests': self.passed_tests,
                'failed_tests': self.failed_tests,
                'success_rate': round(success_rate, 2)
            },
            'detailed_results': self.test_results
        }
        
        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {self.total_tests}")
        logger.info(f"Passed: {self.passed_tests}")
        logger.info(f"Failed: {self.failed_tests}")
        logger.info(f"Success Rate: {success_rate:.2f}%")
        
        # Category breakdown
        for category, tests in self.test_results.items():
            passed = sum(1 for test in tests if test['passed'])
            total = len(tests)
            category_rate = (passed / total) * 100 if total > 0 else 0
            logger.info(f"{category.replace('_', ' ').title()}: {passed}/{total} ({category_rate:.1f}%)")
        
        # Overall assessment
        if success_rate >= 90:
            logger.info("🎉 EXCELLENT: System is production-ready!")
        elif success_rate >= 80:
            logger.info("✅ GOOD: System is mostly ready with minor issues")
        elif success_rate >= 70:
            logger.info("⚠️ FAIR: System needs significant improvements")
        else:
            logger.info("❌ POOR: System has critical issues that must be fixed")
        
        return report

def main():
    """Main execution function"""
    tester = AdminSystemTester()
    
    try:
        # Run all tests
        report = tester.run_all_tests()
        
        # Save report to file
        import json
        with open('admin_system_test_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"\n📄 Detailed report saved to: admin_system_test_report.json")
        
        # Return appropriate exit code
        if report['summary']['success_rate'] >= 90:
            return 0
        elif report['summary']['success_rate'] >= 70:
            return 1
        else:
            return 2
            
    except Exception as e:
        logger.error(f"❌ Critical error during testing: {str(e)}")
        return 3

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)