#!/usr/bin/env python3
"""
Pod-based sandbox API server that runs inside the Kubernetes pod.
Handles code execution requests with proper isolation and security.
"""

import asyncio
import logging
import os
import sys
import traceback
from contextlib import asynccontextmanager
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Add pandas and required libraries
sys.path.insert(0, '/app')


class CodeExecutionRequest(BaseModel):
    code: str
    timeout: int = 30
    session_id: str


class CodeExecutionResponse(BaseModel):
    success: bool
    result: Any = None
    error: str = None
    execution_time: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logging.info("Sandbox API starting up...")
    yield
    logging.info("Sandbox API shutting down...")


app = FastAPI(
    title="Python Sandbox API",
    description="Secure Python code execution in Kubernetes pod",
    version="1.0.0",
    lifespan=lifespan
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes liveness probe."""
    return {"status": "healthy", "session_id": os.getenv("SESSION_ID")}


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint for Kubernetes readiness probe."""
    try:
        # Test basic Python functionality
        import pandas as pd
        import numpy as np
        return {"status": "ready", "session_id": os.getenv("SESSION_ID")}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Not ready: {e}")


@app.post("/execute", response_model=CodeExecutionResponse)
async def execute_code(request: CodeExecutionRequest):
    """Execute Python code in the sandbox with security constraints."""
    import time
    start_time = time.time()
    
    logger.info(f"Executing code for session {request.session_id}")
    
    try:
        # Create execution environment with necessary imports
        exec_globals = {
            '__builtins__': {
                # Safe builtins only
                'abs': abs, 'all': all, 'any': any, 'bool': bool,
                'dict': dict, 'enumerate': enumerate, 'filter': filter,
                'float': float, 'int': int, 'len': len, 'list': list,
                'map': map, 'max': max, 'min': min, 'print': print,
                'range': range, 'round': round, 'sorted': sorted,
                'str': str, 'sum': sum, 'tuple': tuple, 'type': type,
                'zip': zip
            }
        }
        exec_locals = {}
        
        # Add safe imports
        safe_modules = {
            'pandas': __import__('pandas'),
            'pd': __import__('pandas'),
            'numpy': __import__('numpy'),
            'np': __import__('numpy'),
            'matplotlib': __import__('matplotlib'),
            'plt': __import__('matplotlib.pyplot'),
            'seaborn': __import__('seaborn'),
            'plotly': __import__('plotly'),
            'os': type('SafeOS', (), {
                'path': __import__('os.path', fromlist=['path']),
                'getcwd': lambda: '/workspace',
                'listdir': lambda path='/workspace': __import__('os').listdir(path)
            })()
        }
        exec_globals.update(safe_modules)
        
        # Execute code with timeout
        try:
            # Run with asyncio timeout
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: exec(request.code, exec_globals, exec_locals)
                ), 
                timeout=request.timeout
            )
            
            # Extract result from locals if available
            execution_result = exec_locals.get('result', 'Code executed successfully')
            
            execution_time = time.time() - start_time
            logger.info(f"Code executed successfully in {execution_time:.2f}s")
            
            return CodeExecutionResponse(
                success=True,
                result=execution_result,
                execution_time=execution_time
            )
            
        except asyncio.TimeoutError:
            logger.error(f"Code execution timed out after {request.timeout}s")
            return CodeExecutionResponse(
                success=False,
                error=f"Execution timed out after {request.timeout} seconds",
                execution_time=time.time() - start_time
            )
            
    except Exception as e:
        execution_time = time.time() - start_time
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Code execution failed: {error_msg}")
        logger.error(traceback.format_exc())
        
        return CodeExecutionResponse(
            success=False,
            error=error_msg,
            execution_time=execution_time
        )


@app.get("/metrics")
async def get_metrics():
    """Get pod resource usage metrics."""
    import psutil
    
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory": {
            "total": psutil.virtual_memory().total,
            "available": psutil.virtual_memory().available,
            "percent": psutil.virtual_memory().percent
        },
        "disk": {
            "total": psutil.disk_usage('/').total,
            "free": psutil.disk_usage('/').free,
            "percent": psutil.disk_usage('/').percent
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "sandbox_api:app",
        host="0.0.0.0",
        port=8080,
        log_level="info"
    )