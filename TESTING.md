# VectorCraft Testing Documentation

## Overview

This document describes the comprehensive testing framework established for VectorCraft, including test structure, execution, and coverage requirements.

## Test Structure

### Directory Organization

```
tests/
├── __init__.py
├── unit/                    # Unit tests
│   ├── __init__.py
│   ├── test_auth.py         # Authentication tests
│   ├── test_database.py     # Database tests
│   ├── test_file_upload.py  # File upload tests
│   ├── test_paypal_service.py # PayPal service tests
│   └── test_email_service.py # Email service tests
├── integration/             # Integration tests
│   ├── __init__.py
│   └── test_api_endpoints.py # API endpoint tests
├── e2e/                     # End-to-end tests
│   └── __init__.py
├── performance/             # Performance tests
│   ├── __init__.py
│   └── test_performance.py  # Performance and load tests
└── security/                # Security tests
    ├── __init__.py
    └── test_security.py     # Security vulnerability tests
```

### Test Configuration

- **pytest.ini**: Main pytest configuration with markers and coverage settings
- **conftest.py**: Global fixtures and test setup
- **run_tests.py**: Test runner script with various execution options

## Test Categories

### 1. Unit Tests

**Purpose**: Test individual components in isolation

**Coverage**:
- Authentication system (login, registration, password handling)
- Database operations (CRUD, transactions, integrity)
- File upload validation and processing
- PayPal service integration
- Email service functionality

**Key Features**:
- Mocked dependencies
- Fast execution
- High coverage (>90%)
- Isolated test environment

### 2. Integration Tests

**Purpose**: Test component interactions and API endpoints

**Coverage**:
- Authentication endpoints
- File upload workflows
- Payment processing
- Admin dashboard
- Health checks

**Key Features**:
- Full request/response cycle testing
- Database integration
- Service integration
- Error handling validation

### 3. Security Tests

**Purpose**: Test security vulnerabilities and protection measures

**Coverage**:
- Authentication security (password hashing, session management)
- Input validation (SQL injection, XSS, path traversal)
- Authorization and access control
- CSRF protection
- Security headers
- File upload security

**Key Features**:
- OWASP Top 10 coverage
- Vulnerability scanning
- Security configuration validation
- Attack simulation

### 4. Performance Tests

**Purpose**: Test application performance and scalability

**Coverage**:
- Response time testing
- Throughput testing
- Resource usage monitoring
- Load testing
- Stress testing
- Scalability testing

**Key Features**:
- Locust-based load testing
- Performance metrics collection
- Resource monitoring
- Regression detection

### 5. End-to-End Tests

**Purpose**: Test complete user workflows

**Coverage**:
- User registration and login
- Complete file upload and processing
- Payment flow
- Admin workflows

**Key Features**:
- Selenium-based browser automation
- Real workflow simulation
- Cross-browser testing (planned)

## Test Execution

### Quick Start

```bash
# Run smoke tests (quick validation)
python run_tests.py --smoke

# Run all tests
python run_tests.py --all

# Run specific test category
python run_tests.py --unit
python run_tests.py --integration
python run_tests.py --security
python run_tests.py --performance
```

### Test Runner Options

```bash
# Basic test execution
python run_tests.py --unit           # Unit tests only
python run_tests.py --integration    # Integration tests only
python run_tests.py --security       # Security tests only
python run_tests.py --performance    # Performance tests only
python run_tests.py --all            # All tests

# Advanced options
python run_tests.py --fast           # Fast tests only (excludes slow tests)
python run_tests.py --coverage       # Tests with coverage report
python run_tests.py --parallel       # Parallel test execution
python run_tests.py --smoke          # Smoke tests for quick validation
python run_tests.py --regression     # Regression tests

# Specific test execution
python run_tests.py --test tests/unit/test_auth.py
python run_tests.py --test tests/unit/test_auth.py::TestAuthService::test_create_user_success
python run_tests.py --markers "auth and not slow"

# Utilities
python run_tests.py --check-env      # Check test environment
python run_tests.py --lint           # Run linting and formatting
python run_tests.py --report         # Generate comprehensive report
```

### Direct pytest Usage

```bash
# Run specific test files
pytest tests/unit/test_auth.py -v

# Run with markers
pytest tests/ -m "unit and not slow" -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html --cov-report=term-missing

# Run in parallel
pytest tests/ -n auto

# Run with specific output
pytest tests/ --tb=short --strict-markers
```

## Test Fixtures and Utilities

### Global Fixtures (conftest.py)

- `app`: Flask application instance
- `client`: Test client for HTTP requests
- `temp_db`: Temporary database for testing
- `authenticated_client`: Client with authenticated user session
- `test_user_data`: Sample user data
- `test_image_file`: Test image file for uploads
- `mock_*_service`: Mocked service instances

### Test Utilities

- `TestUtils`: Helper functions for test data generation
- `performance_test_helpers`: Performance testing utilities
- `security_test_helpers`: Security testing utilities
- `db_test_helpers`: Database testing utilities

## Coverage Requirements

### Target Coverage

- **Overall**: 80% minimum
- **Critical modules**: 90% minimum
- **Security functions**: 95% minimum
- **API endpoints**: 85% minimum

### Coverage Reporting

```bash
# Generate HTML coverage report
pytest tests/ --cov=. --cov-report=html

# View coverage in terminal
pytest tests/ --cov=. --cov-report=term-missing

# Fail if coverage below threshold
pytest tests/ --cov=. --cov-fail-under=80
```

### Coverage Exclusions

```python
# In code, exclude from coverage
def debug_function():  # pragma: no cover
    pass
```

## Test Data Management

### Test Database

- Temporary SQLite database for each test
- Automatic cleanup after tests
- Transaction rollback for isolation
- Seed data through fixtures

### Test Files

- Generated test images for upload testing
- Temporary file cleanup
- Secure test data handling

### Mock Data

- Comprehensive mock objects for external services
- Realistic test data generation
- Parameterized test data

## Continuous Integration

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

### CI Pipeline (GitHub Actions)

```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python run_tests.py --all --coverage
```

## Test Markers

### Available Markers

- `unit`: Unit tests
- `integration`: Integration tests
- `e2e`: End-to-end tests
- `auth`: Authentication related tests
- `api`: API endpoint tests
- `database`: Database tests
- `file_upload`: File upload tests
- `paypal`: PayPal service tests
- `email`: Email service tests
- `security`: Security tests
- `performance`: Performance tests
- `slow`: Slow running tests

### Usage

```bash
# Run only unit tests
pytest -m "unit"

# Run fast tests (exclude slow)
pytest -m "not slow"

# Run auth and database tests
pytest -m "auth or database"

# Run security tests only
pytest -m "security"
```

## Performance Testing

### Load Testing with Locust

```bash
# Start Locust web interface
locust -f tests/performance/locust_tests.py --host=http://localhost:8080

# Run headless load test
locust -f tests/performance/locust_tests.py --host=http://localhost:8080 --users=50 --spawn-rate=10 --run-time=60s --headless
```

### Performance Metrics

- Response time (average, median, 95th percentile)
- Throughput (requests per second)
- Resource usage (CPU, memory)
- Database query performance
- Error rate under load

## Security Testing

### Security Test Categories

1. **Authentication Security**
   - Password hashing validation
   - Session management
   - Rate limiting
   - Account lockout

2. **Input Validation**
   - SQL injection protection
   - XSS protection
   - Path traversal protection
   - File upload security

3. **Authorization**
   - Access control validation
   - Privilege escalation protection
   - Direct object reference protection

4. **Security Headers**
   - CSP, HSTS, X-Frame-Options
   - Secure cookie flags
   - CSRF protection

### Security Tools Integration

```bash
# Run security-focused tests
pytest tests/security/ -v

# Run OWASP Top 10 tests
pytest tests/security/ -m "owasp"

# Security scan (if tools available)
bandit -r . -ll
safety check
```

## Debugging Tests

### Common Issues

1. **Test Isolation**: Use fixtures properly
2. **Mock Configuration**: Ensure mocks are reset between tests
3. **Database State**: Use transaction rollback
4. **File Cleanup**: Clean up temporary files

### Debugging Commands

```bash
# Run single test with detailed output
pytest tests/unit/test_auth.py::TestAuthService::test_create_user_success -vvv -s

# Run tests with PDB on failure
pytest tests/unit/test_auth.py --pdb

# Run tests with coverage and keep temp files
pytest tests/unit/test_auth.py --cov=. --keep-temp-files
```

## Test Maintenance

### Regular Tasks

1. **Update test data** as application evolves
2. **Review coverage reports** and add tests for uncovered code
3. **Update mocks** when external APIs change
4. **Performance baseline** updates
5. **Security test updates** for new vulnerabilities

### Test Refactoring

- Extract common test patterns into fixtures
- Parameterize similar tests
- Update test documentation
- Remove obsolete tests

## Best Practices

### Test Writing

1. **AAA Pattern**: Arrange, Act, Assert
2. **One assertion per test** (generally)
3. **Clear test names** describing what is tested
4. **Independent tests** that can run in any order
5. **Fast tests** that run quickly

### Test Organization

1. **Group related tests** in classes
2. **Use descriptive class names**
3. **Organize by functionality**, not by test type
4. **Consistent file naming**

### Mocking

1. **Mock external dependencies** (APIs, databases, file systems)
2. **Use realistic mock data**
3. **Mock at the right level** (service layer, not implementation details)
4. **Verify mock calls** when testing interactions

## Troubleshooting

### Common Test Failures

1. **Database connection errors**: Check test database setup
2. **Import errors**: Verify Python path and dependencies
3. **Fixture errors**: Check fixture dependencies and scope
4. **Mock errors**: Ensure mocks are properly configured and reset

### Environment Issues

```bash
# Check test environment
python run_tests.py --check-env

# Reinstall dependencies
pip install -r requirements.txt

# Clear Python cache
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
```

## Test Reports

### HTML Reports

Generated in `htmlcov/` directory for coverage and test results.

### Test Metrics

- Test execution time
- Coverage percentage
- Failed/passed test counts
- Performance benchmarks
- Security scan results

## Contributing

### Adding New Tests

1. Choose appropriate test category
2. Follow existing test patterns
3. Add appropriate markers
4. Update documentation
5. Ensure tests pass in CI

### Test Review Checklist

- [ ] Tests cover new functionality
- [ ] Tests follow naming conventions
- [ ] Appropriate fixtures used
- [ ] Mocks are realistic
- [ ] Tests are independent
- [ ] Documentation updated

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [Flask testing documentation](https://flask.palletsprojects.com/en/2.0.x/testing/)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [Locust documentation](https://locust.io/)

---

**Last Updated**: January 2024
**Version**: 1.0.0
**Maintainer**: VectorCraft QA Team