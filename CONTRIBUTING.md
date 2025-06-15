# Contributing to VectorCraft 2.0

Thank you for your interest in contributing to VectorCraft 2.0! This document provides guidelines for contributing to the project.

## 🚀 Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/VectorCraft.git
   cd VectorCraft
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Run tests** to ensure everything works:
   ```bash
   python test_basic.py
   ```

## 🛠 Development Setup

### Prerequisites
- Python 3.8+
- OpenCV (opencv-python)
- PyTorch
- NumPy, Pillow, svgwrite

### Running Tests
```bash
# Basic functionality test
python test_basic.py

# Demo with test images
python demo.py --create-tests

# Strategy comparison
python demo.py --compare

# Performance benchmarks
python performance_test.py
```

## 📝 How to Contribute

### Reporting Bugs
- Use the GitHub issue tracker
- Include Python version, OS, and error messages
- Provide minimal reproduction steps
- Include sample images if relevant

### Suggesting Features
- Open an issue with the "enhancement" label
- Clearly describe the feature and use case
- Consider backward compatibility

### Code Contributions

#### 1. Create a Feature Branch
```bash
git checkout -b feature/your-feature-name
```

#### 2. Make Your Changes
- Follow the existing code style
- Add docstrings for new functions/classes
- Include type hints where appropriate
- Write tests for new functionality

#### 3. Test Your Changes
```bash
# Run all tests
python test_basic.py
python demo.py --benchmark
python performance_test.py

# Test specific functionality
python -c "from vectorcraft import HybridVectorizer; print('Import test passed')"
```

#### 4. Commit Your Changes
```bash
git add .
git commit -m "Add feature: description of your changes"
```

#### 5. Push and Create Pull Request
```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## 🏗 Code Guidelines

### Code Style
- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Keep functions focused and small
- Add comments for complex algorithms

### Documentation
- Update README.md if adding new features
- Add docstrings for public methods
- Include usage examples for new features

### Performance
- Profile new code with the built-in performance tools
- Aim to maintain or improve processing speed
- Consider memory usage for large images

## 🎯 Areas for Contribution

### High Priority
- **New Vectorization Strategies**: Implement novel algorithms
- **Performance Optimizations**: Speed improvements and memory efficiency
- **Quality Improvements**: Better edge detection, primitive recognition
- **GPU Acceleration**: CUDA implementations for compute-intensive operations

### Medium Priority
- **Format Support**: Additional input/output formats
- **Interactive Features**: User-guided refinement tools
- **Batch Processing**: Efficient multi-image processing
- **Documentation**: Tutorials, examples, API docs

### Low Priority
- **UI/Web Interface**: Web-based or GUI interface
- **Cloud Integration**: API for cloud processing
- **Mobile Support**: iOS/Android compatibility

## 🧪 Testing Guidelines

### Required Tests
- New features must include test cases
- Performance regressions should be avoided
- Test edge cases and error conditions

### Test Categories
1. **Unit Tests**: Individual component testing
2. **Integration Tests**: End-to-end workflow testing
3. **Performance Tests**: Speed and memory benchmarks
4. **Visual Tests**: Quality assessment (manual review)

## 📊 Performance Benchmarks

When contributing performance improvements:
- Run before/after benchmarks
- Include timing comparisons
- Test on different image sizes and types
- Consider both speed and quality trade-offs

## 🤝 Code Review Process

1. **Automated Checks**: Ensure tests pass
2. **Code Review**: Maintainer review for quality and design
3. **Performance Review**: Check for regressions
4. **Documentation Review**: Ensure docs are updated
5. **Merge**: After approval, changes are merged

## 🏆 Recognition

Contributors will be recognized in:
- README.md acknowledgments
- Release notes for significant contributions
- GitHub contributor graphs

## 📞 Getting Help

- **Issues**: Use GitHub issues for bug reports and questions
- **Discussions**: Use GitHub discussions for general questions
- **Email**: Contact maintainers for private concerns

## 📄 License

By contributing to VectorCraft 2.0, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to VectorCraft 2.0! Together we can make vector conversion better for everyone. 🎨✨