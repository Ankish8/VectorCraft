#!/usr/bin/env python3
"""
Test runner for VectorCraft application
Provides various test execution options and reporting
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def run_command(cmd, capture_output=False):
    """Run a command and return the result"""
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, shell=True)
            return result.returncode
    except Exception as e:
        print(f"Error running command: {e}")
        return 1

def run_unit_tests():
    """Run unit tests"""
    print("🧪 Running unit tests...")
    cmd = "python -m pytest tests/unit/ -v --tb=short"
    return run_command(cmd)

def run_integration_tests():
    """Run integration tests"""
    print("🔗 Running integration tests...")
    cmd = "python -m pytest tests/integration/ -v --tb=short"
    return run_command(cmd)

def run_security_tests():
    """Run security tests"""
    print("🔒 Running security tests...")
    cmd = "python -m pytest tests/security/ -v --tb=short -m security"
    return run_command(cmd)

def run_performance_tests():
    """Run performance tests"""
    print("⚡ Running performance tests...")
    cmd = "python -m pytest tests/performance/ -v --tb=short -m performance"
    return run_command(cmd)

def run_all_tests():
    """Run all tests"""
    print("🚀 Running all tests...")
    cmd = "python -m pytest tests/ -v --tb=short"
    return run_command(cmd)

def run_fast_tests():
    """Run fast tests only"""
    print("⚡ Running fast tests...")
    cmd = "python -m pytest tests/ -v --tb=short -m 'not slow'"
    return run_command(cmd)

def run_coverage_report():
    """Run tests with coverage report"""
    print("📊 Running tests with coverage report...")
    cmd = "python -m pytest tests/ --cov=. --cov-report=html --cov-report=term-missing --cov-fail-under=80"
    return run_command(cmd)

def run_tests_parallel():
    """Run tests in parallel"""
    print("🏃 Running tests in parallel...")
    cmd = "python -m pytest tests/ -v --tb=short -n auto"
    return run_command(cmd)

def run_specific_test(test_path):
    """Run a specific test file or function"""
    print(f"🎯 Running specific test: {test_path}")
    cmd = f"python -m pytest {test_path} -v --tb=short"
    return run_command(cmd)

def run_tests_with_markers(markers):
    """Run tests with specific markers"""
    print(f"🏷️ Running tests with markers: {markers}")
    cmd = f"python -m pytest tests/ -v --tb=short -m '{markers}'"
    return run_command(cmd)

def check_test_environment():
    """Check if test environment is properly set up"""
    print("🔍 Checking test environment...")
    
    # Check if required packages are installed
    required_packages = [
        'pytest',
        'pytest-flask',
        'pytest-cov',
        'pytest-mock',
        'pytest-html',
        'pytest-xdist',
        'pytest-timeout',
        'pytest-benchmark',
        'coverage',
        'responses',
        'locust',
        'psutil'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("Install missing packages with: pip install -r requirements.txt")
        return False
    
    # Check if test directories exist
    test_dirs = ['tests/unit', 'tests/integration', 'tests/security', 'tests/performance']
    for test_dir in test_dirs:
        if not os.path.exists(test_dir):
            print(f"❌ Test directory missing: {test_dir}")
            return False
    
    print("✅ Test environment is properly set up")
    return True

def generate_test_report():
    """Generate comprehensive test report"""
    print("📋 Generating comprehensive test report...")
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    report_dir = f"test_reports_{timestamp}"
    os.makedirs(report_dir, exist_ok=True)
    
    # Run tests with various options
    test_commands = [
        ("unit_tests", "python -m pytest tests/unit/ --html={}/unit_tests.html --self-contained-html"),
        ("integration_tests", "python -m pytest tests/integration/ --html={}/integration_tests.html --self-contained-html"),
        ("security_tests", "python -m pytest tests/security/ --html={}/security_tests.html --self-contained-html"),
        ("performance_tests", "python -m pytest tests/performance/ --html={}/performance_tests.html --self-contained-html"),
        ("coverage_report", "python -m pytest tests/ --cov=. --cov-report=html:{}/coverage --cov-report=term-missing")
    ]
    
    for test_name, cmd in test_commands:
        print(f"Running {test_name}...")
        formatted_cmd = cmd.format(report_dir)
        run_command(formatted_cmd)
    
    print(f"📄 Test reports generated in: {report_dir}")

def run_smoke_tests():
    """Run smoke tests for quick validation"""
    print("💨 Running smoke tests...")
    
    # Run a subset of critical tests
    smoke_tests = [
        "tests/unit/test_auth.py::TestAuthService::test_create_user_success",
        "tests/unit/test_database.py::TestDatabaseInitialization::test_database_creation",
        "tests/integration/test_api_endpoints.py::TestAuthenticationEndpoints::test_login_page_get",
        "tests/security/test_security.py::TestAuthenticationSecurity::test_password_hashing_security"
    ]
    
    for test in smoke_tests:
        print(f"Running {test}...")
        result = run_command(f"python -m pytest {test} -v")
        if result != 0:
            print(f"❌ Smoke test failed: {test}")
            return result
    
    print("✅ All smoke tests passed")
    return 0

def run_regression_tests():
    """Run regression tests"""
    print("🔄 Running regression tests...")
    
    # Run tests that check for regressions
    regression_markers = "not slow and not e2e"
    cmd = f"python -m pytest tests/ -v --tb=short -m '{regression_markers}'"
    return run_command(cmd)

def lint_and_format():
    """Run linting and formatting checks"""
    print("🧹 Running linting and formatting checks...")
    
    # Check if flake8 is available
    try:
        import flake8
        print("Running flake8...")
        result = run_command("python -m flake8 tests/ --max-line-length=100 --ignore=E501,W503")
        if result != 0:
            print("❌ Linting issues found")
            return result
    except ImportError:
        print("⚠️  flake8 not installed, skipping linting")
    
    # Check if black is available
    try:
        import black
        print("Running black...")
        result = run_command("python -m black --check tests/")
        if result != 0:
            print("❌ Formatting issues found")
            return result
    except ImportError:
        print("⚠️  black not installed, skipping formatting check")
    
    print("✅ Linting and formatting checks passed")
    return 0

def main():
    """Main function to run tests based on command line arguments"""
    parser = argparse.ArgumentParser(description="VectorCraft Test Runner")
    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--security", action="store_true", help="Run security tests")
    parser.add_argument("--performance", action="store_true", help="Run performance tests")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--fast", action="store_true", help="Run fast tests only")
    parser.add_argument("--coverage", action="store_true", help="Run tests with coverage")
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("--smoke", action="store_true", help="Run smoke tests")
    parser.add_argument("--regression", action="store_true", help="Run regression tests")
    parser.add_argument("--report", action="store_true", help="Generate comprehensive test report")
    parser.add_argument("--check-env", action="store_true", help="Check test environment")
    parser.add_argument("--lint", action="store_true", help="Run linting and formatting checks")
    parser.add_argument("--test", type=str, help="Run specific test file or function")
    parser.add_argument("--markers", type=str, help="Run tests with specific markers")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Set verbose mode
    if args.verbose:
        os.environ['PYTEST_VERBOSITY'] = '-vvv'
    
    # Check environment first if requested
    if args.check_env:
        if not check_test_environment():
            sys.exit(1)
        return
    
    # Run linting if requested
    if args.lint:
        result = lint_and_format()
        sys.exit(result)
    
    # Run specific test
    if args.test:
        result = run_specific_test(args.test)
        sys.exit(result)
    
    # Run tests with markers
    if args.markers:
        result = run_tests_with_markers(args.markers)
        sys.exit(result)
    
    # Run various test suites
    if args.unit:
        result = run_unit_tests()
        sys.exit(result)
    
    if args.integration:
        result = run_integration_tests()
        sys.exit(result)
    
    if args.security:
        result = run_security_tests()
        sys.exit(result)
    
    if args.performance:
        result = run_performance_tests()
        sys.exit(result)
    
    if args.fast:
        result = run_fast_tests()
        sys.exit(result)
    
    if args.coverage:
        result = run_coverage_report()
        sys.exit(result)
    
    if args.parallel:
        result = run_tests_parallel()
        sys.exit(result)
    
    if args.smoke:
        result = run_smoke_tests()
        sys.exit(result)
    
    if args.regression:
        result = run_regression_tests()
        sys.exit(result)
    
    if args.report:
        generate_test_report()
        return
    
    if args.all:
        result = run_all_tests()
        sys.exit(result)
    
    # Default: run smoke tests
    if not any(vars(args).values()):
        print("No specific test option provided. Running smoke tests...")
        result = run_smoke_tests()
        sys.exit(result)

if __name__ == "__main__":
    main()