# VectorCraft Docker Configuration
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libhdf5-dev \
    libopenblas-dev \
    liblapack-dev \
    gfortran \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    libopencv-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash vectorcraft
RUN chown -R vectorcraft:vectorcraft /app

# Copy requirements first for better caching
COPY requirements.txt requirements_minimal.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt || \
    pip install --no-cache-dir -r requirements_minimal.txt
RUN pip install --no-cache-dir flask-login

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads results output static/images
RUN chown -R vectorcraft:vectorcraft /app

# Switch to non-root user
USER vectorcraft

# Copy the authenticated app as the main app
RUN cp app_with_auth.py app.py

# Initialize database
RUN python database.py

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# Run the application
CMD ["python", "app.py"]