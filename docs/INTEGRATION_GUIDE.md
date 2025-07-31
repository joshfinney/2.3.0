# PandasAI Pod Sandbox Integration Guide

## Overview

This guide shows you how to integrate the Kubernetes pod-based sandbox into your PandasAI applications, replacing Docker containers with secure, scalable pods.

## Quick Start

### Basic Integration
```python
import pandas as pd
from pandasai import Agent
from pandasai_pod import PodSandbox

# Load your data
df = pd.read_csv("your_data.csv")

# Create pod sandbox (replaces DockerSandbox)
sandbox = PodSandbox(
    namespace="pandasai-sandbox",    # Your K8s namespace
    image="your-registry/pandasai-sandbox-pod:latest",
    timeout=60  # Execution timeout in seconds
)

# Create agent with pod sandbox
agent = Agent(df, sandbox=sandbox)

# Use normally - pods are managed automatically
result = agent.chat("Analyze the sales trends by region")
print(result)
```

## Configuration Options

### Sandbox Configuration
```python
sandbox = PodSandbox(
    namespace="pandasai-sandbox",           # Kubernetes namespace
    image="pandasai-sandbox-pod:latest",    # Container image
    timeout=60,                             # Code execution timeout
)
```

### Environment-Specific Configuration
```python
import os

# Development configuration
if os.getenv("ENVIRONMENT") == "development":
    sandbox = PodSandbox(
        namespace="pandasai-dev",
        image="pandasai-sandbox-pod:dev",
        timeout=120  # Longer timeout for debugging
    )

# Production configuration  
elif os.getenv("ENVIRONMENT") == "production":
    sandbox = PodSandbox(
        namespace="pandasai-prod",
        image="your-registry/pandasai-sandbox-pod:v1.0.0",
        timeout=30  # Shorter timeout for efficiency
    )
```

## Migration from Docker

### Before (Docker)
```python
from pandasai_docker import DockerSandbox

sandbox = DockerSandbox(
    image_name="pandasai-sandbox",
    dockerfile_path="./Dockerfile"
)
agent = Agent(df, sandbox=sandbox)
```

### After (Kubernetes Pods)
```python
from pandasai_pod import PodSandbox

sandbox = PodSandbox(
    namespace="pandasai-sandbox",
    image="pandasai-sandbox-pod:latest"
)
agent = Agent(df, sandbox=sandbox)
```

**Migration Benefits:**
- ✅ **Auto-scaling**: Pods scale based on demand
- ✅ **Better isolation**: Network policies and security contexts
- ✅ **Resource management**: Kubernetes handles resource allocation
- ✅ **Health monitoring**: Built-in health checks and restart policies
- ✅ **Multi-project**: Share the same infrastructure across projects

## Advanced Usage Patterns

### Async/Await Pattern
```python
import asyncio
from pandasai_pod import PodSandbox

async def analyze_data():
    # Use async context manager for automatic cleanup
    async with PodSandbox(namespace="pandasai-sandbox") as sandbox:
        agent = Agent(df, sandbox=sandbox)
        
        # Run multiple analyses concurrently
        tasks = [
            agent.chat_async("Analyze Q1 performance"),
            agent.chat_async("Show top 10 customers"),
            agent.chat_async("Create revenue trend chart")
        ]
        
        results = await asyncio.gather(*tasks)
        return results

# Run async analysis
results = asyncio.run(analyze_data())
```

### Multi-Dataset Analysis
```python
# Analyze multiple datasets with shared pod infrastructure
datasets = {
    "sales": pd.read_csv("sales.csv"),
    "customers": pd.read_csv("customers.csv"),
    "products": pd.read_csv("products.csv")
}

sandbox = PodSandbox(namespace="pandasai-sandbox")

agents = {}
for name, df in datasets.items():
    agents[name] = Agent(df, sandbox=sandbox)  # Reuse same sandbox

# Cross-dataset analysis
sales_trends = agents["sales"].chat("Show monthly sales trends")
customer_segments = agents["customers"].chat("Segment customers by value")
product_performance = agents["products"].chat("Top performing products")
```

### Production Deployment Pattern
```python
import logging
from contextlib import contextmanager
from pandasai_pod import PodSandbox

class PandasAIService:
    def __init__(self, namespace="pandasai-prod"):
        self.namespace = namespace
        self.sandbox = None
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """Initialize the sandbox for the service."""
        self.sandbox = PodSandbox(
            namespace=self.namespace,
            image="your-registry/pandasai-sandbox-prod:latest",
            timeout=30
        )
        self.sandbox.start()
        self.logger.info("PandasAI service started")
    
    def stop(self):
        """Cleanup sandbox resources."""
        if self.sandbox:
            self.sandbox.stop()
            self.logger.info("PandasAI service stopped")
    
    def analyze(self, df: pd.DataFrame, query: str) -> str:
        """Perform analysis with error handling."""
        if not self.sandbox:
            raise RuntimeError("Service not started")
        
        try:
            agent = Agent(df, sandbox=self.sandbox)
            return agent.chat(query)
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            # Pod automatically restarts on failure
            raise

# Usage in production
service = PandasAIService()
service.start()

try:
    result = service.analyze(df, "Analyze customer churn")
    print(result)
finally:
    service.stop()
```

## Integration with Different Frameworks

### Flask Web Application
```python
from flask import Flask, request, jsonify
from pandasai_pod import PodSandbox
import pandas as pd

app = Flask(__name__)

# Initialize sandbox once at startup
sandbox = PodSandbox(namespace="pandasai-web")
sandbox.start()

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # Get data from request
        data = request.json
        df = pd.DataFrame(data['data'])
        query = data['query']
        
        # Perform analysis
        agent = Agent(df, sandbox=sandbox)
        result = agent.chat(query)
        
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.teardown_appcontext
def cleanup(error):
    # Cleanup handled automatically by pod lifecycle
    pass

if __name__ == '__main__':
    app.run()
```

### FastAPI Async Application
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pandasai_pod import PodSandbox
import pandas as pd

app = FastAPI()

class AnalysisRequest(BaseModel):
    data: list
    query: str

@app.on_event("startup")
async def startup():
    global sandbox
    sandbox = PodSandbox(namespace="pandasai-api")
    await sandbox.start()

@app.on_event("shutdown") 
async def shutdown():
    await sandbox.stop()

@app.post("/analyze")
async def analyze(request: AnalysisRequest):
    try:
        df = pd.DataFrame(request.data)
        agent = Agent(df, sandbox=sandbox)
        result = await agent.chat_async(request.query)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Jupyter Notebook Integration
```python
# Cell 1: Setup
from pandasai_pod import PodSandbox
import pandas as pd

# Start sandbox for notebook session
sandbox = PodSandbox(namespace="pandasai-jupyter")
print("Starting pod sandbox...")
sandbox.start()
print("✅ Sandbox ready!")

# Cell 2: Load Data
df = pd.read_csv("your_data.csv")
agent = Agent(df, sandbox=sandbox)

# Cell 3: Interactive Analysis
query = input("Enter your analysis query: ")
result = agent.chat(query)
print(result)

# Final Cell: Cleanup (optional - handled automatically)
sandbox.stop()
```

## Environment Variables

Configure behavior through environment variables:

```bash
# Kubernetes configuration
export KUBECONFIG=/path/to/kubeconfig
export PANDASAI_NAMESPACE=pandasai-sandbox
export PANDASAI_IMAGE=your-registry/pandasai-sandbox-pod:latest

# Timeout settings
export PANDASAI_TIMEOUT=60
export PANDASAI_HEALTH_CHECK_INTERVAL=10

# Security settings
export PANDASAI_ENFORCE_NETWORK_POLICY=true
export PANDASAI_READ_ONLY_ROOT=true
```

## Error Handling Best Practices

### Robust Error Handling
```python
import time
from pandasai_pod import PodSandbox

def safe_analysis(df, query, max_retries=3):
    sandbox = None
    
    for attempt in range(max_retries):
        try:
            sandbox = PodSandbox(namespace="pandasai-sandbox")
            sandbox.start()
            
            agent = Agent(df, sandbox=sandbox)
            result = agent.chat(query)
            
            return result
            
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if sandbox:
                sandbox.stop()
            
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise
        
        finally:
            if sandbox:
                sandbox.stop()

# Usage with automatic retries
result = safe_analysis(df, "Analyze sales data")
```

## Performance Optimization

### Connection Pooling
```python
from pandasai_pod import PodSandboxManager
import asyncio
from asyncio import Queue

class SandboxPool:
    def __init__(self, namespace, size=5):
        self.namespace = namespace
        self.size = size
        self.pool = Queue(maxsize=size)
        
    async def initialize(self):
        for _ in range(self.size):
            sandbox = PodSandbox(namespace=self.namespace)
            await sandbox.start()
            await self.pool.put(sandbox)
    
    async def get_sandbox(self):
        return await self.pool.get()
    
    async def return_sandbox(self, sandbox):
        await self.pool.put(sandbox)

# Usage
pool = SandboxPool(namespace="pandasai-pool", size=3)
await pool.initialize()

sandbox = await pool.get_sandbox()
try:
    agent = Agent(df, sandbox=sandbox)
    result = agent.chat("Your query")
finally:
    await pool.return_sandbox(sandbox)
```

## Monitoring and Observability

### Health Check Integration
```python
from pandasai_pod import PodSandbox

def check_sandbox_health():
    try:
        sandbox = PodSandbox(namespace="pandasai-sandbox")
        status = sandbox.get_status()
        
        return {
            "healthy": status.get("ready", False),
            "phase": status.get("phase"),
            "restarts": status.get("restarts", 0)
        }
    except Exception as e:
        return {"healthy": False, "error": str(e)}

# Use in health check endpoints
health = check_sandbox_health()
print(f"Sandbox health: {health}")
```

## Next Steps

1. **Deploy to Cluster**: Follow the deployment guide to set up your Kubernetes cluster
2. **Test Integration**: Start with the basic integration pattern
3. **Scale Up**: Implement pooling and async patterns for production
4. **Monitor**: Set up logging and metrics collection
5. **Optimize**: Fine-tune resource limits and timeout settings

## Support

- Check the troubleshooting guide for common issues
- Review Kubernetes logs: `kubectl logs -l app=python-sandbox -n pandasai-sandbox`
- Monitor pod status: `kubectl get pods -n pandasai-sandbox --watch`