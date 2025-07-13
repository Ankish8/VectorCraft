# VectorCraft Docker Configuration
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including Rust for VTracer and Node.js for CSS build
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
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for CSS build process
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Note: VTracer installation requires Rust compilation which is slow
# For now, the app will work without VTracer (using fallback strategies)

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash vectorcraft
RUN chown -R vectorcraft:vectorcraft /app

# Copy requirements first for better caching
COPY requirements.txt requirements_minimal.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip
# Install cryptography first (needs system dependencies)
RUN pip install --no-cache-dir cryptography>=3.4.0
RUN pip install --no-cache-dir -r requirements.txt || \
    pip install --no-cache-dir -r requirements_minimal.txt
# Install VTracer - it should work on most systems with precompiled wheels
RUN pip install --no-cache-dir vtracer

# Copy package.json and build CSS first
COPY package.json tailwind.config.js ./
COPY static/admin/scss/ ./static/admin/scss/

# Install Node dependencies and build CSS
RUN npm install && npm run build-css-prod

# Copy application code
COPY . .

# Copy and set up entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create necessary directories
RUN mkdir -p uploads results output static/images data

# Initialize database (before switching to non-root user)
RUN python database.py

# Set ownership and switch to non-root user
RUN chown -R vectorcraft:vectorcraft /app
USER vectorcraft

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# Email configuration
ENV SMTP_SERVER=smtpout.secureserver.net
ENV SMTP_PORT=587
ENV SMTP_USERNAME=support@thevectorcraft.com
ENV SMTP_PASSWORD=Ankish@its123
ENV FROM_EMAIL=support@thevectorcraft.com
ENV ADMIN_EMAIL=support@thevectorcraft.com
ENV DOMAIN_URL=http://localhost:8080

# Use entrypoint script that ensures VTracer is available
ENTRYPOINT ["/app/entrypoint.sh"]