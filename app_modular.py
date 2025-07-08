"""
VectorCraft v2.0.0 - Modular Blueprint Architecture
Main application entry point using application factory pattern
"""

import os
import logging
from app_factory import create_app, _log_startup_info

# Determine environment
env = os.getenv('FLASK_ENV', 'development')

# Create application using factory pattern
app = create_app(env)

# Initialize vectorizers (moved from factory to avoid circular imports)
try:
    from vectorcraft import HybridVectorizer, OptimizedVectorizer
    
    # Initialize vectorizers and store in app context
    with app.app_context():
        app.standard_vectorizer = HybridVectorizer()
        app.optimized_vectorizer = OptimizedVectorizer()
        
    app.logger.info("✅ Vectorization engines initialized successfully")
    
except Exception as e:
    app.logger.error(f"❌ Failed to initialize vectorization engines: {e}")
    # Application can still run without vectorizers for basic functionality

if __name__ == '__main__':
    # Log startup information
    _log_startup_info(app)
    
    # Run application
    debug_mode = env != 'production'
    
    app.logger.info("🎨 VectorCraft v2.0.0 starting...")
    app.logger.info("🏗️  Architecture: Modular Flask Blueprints")
    app.logger.info("🚀 Server starting on http://localhost:8080")
    
    try:
        app.run(debug=debug_mode, host='0.0.0.0', port=8080)
    except KeyboardInterrupt:
        app.logger.info("🛑 Server stopped by user")
    except Exception as e:
        app.logger.error(f"❌ Server error: {e}")