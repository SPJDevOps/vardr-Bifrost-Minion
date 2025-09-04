# Optimized Dockerfile with Python 3.13 and Node.js 22
FROM nikolaik/python-nodejs:python3.13-nodejs22

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Install system dependencies and update npm in a single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Essential tools
    curl \
    ca-certificates \
    # Java for Maven
    openjdk-17-jre-headless \
    # Maven
    maven \
    # Update npm to latest version
    && npm install -g npm@latest \
    # Cleanup to reduce image size
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/* \
    && npm cache clean --force

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    # Remove pip cache and temporary files
    rm -rf ~/.cache/pip && \
    find /usr/local -depth \( -type d -a -name test -o -name tests \) -exec rm -rf '{}' +

# Copy application code
COPY . .

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Create temp directories with proper permissions
RUN mkdir -p /tmp/docker-images /tmp/maven-packages /tmp/python-packages \
    /tmp/npm-packages /tmp/file-downloads /tmp/helm-charts /tmp/website-pdfs && \
    chown -R appuser:appuser /tmp

# Switch to non-root user
USER appuser

# Health check for the application
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import app.main; print('Health check passed')" || exit 1

# Command to run the FastStream application
CMD ["python", "run.py"]