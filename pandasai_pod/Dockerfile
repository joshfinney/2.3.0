FROM python:3.9-slim

LABEL image_name="pandasai-sandbox-pod"
LABEL maintainer="PandasAI Team"
LABEL description="Secure Python sandbox for Kubernetes pod execution"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir \
    pandas==2.2.3 \
    numpy \
    matplotlib \
    seaborn \
    plotly \
    fastapi \
    uvicorn \
    psutil \
    aiofiles

# Create non-root user for security
RUN useradd -m -u 1000 sandbox && \
    mkdir -p /workspace /tmp && \
    chown -R sandbox:sandbox /workspace /tmp

# Set working directory
WORKDIR /app

# Copy API server
COPY sandbox_api.py /app/

# Switch to non-root user
USER sandbox

# Create workspace directory
RUN mkdir -p /workspace/charts /workspace/data

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')"

# Run the API server
CMD ["python", "sandbox_api.py"]