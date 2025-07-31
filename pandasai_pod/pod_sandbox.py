"""
Pod-based sandbox implementation that replaces Docker container management.
Provides secure, scalable Python code execution using Kubernetes pods.
"""

import asyncio
import logging
from typing import Optional, Dict, Any

from pandasai.sandbox import Sandbox
from .pod_manager import PodSandboxManager

logger = logging.getLogger(__name__)


class PodSandbox(Sandbox):
    """Kubernetes pod-based sandbox for secure Python code execution."""
    
    def __init__(
        self, 
        namespace: str = "default",
        image: str = "pandasai-sandbox-pod:latest",
        timeout: int = 30
    ):
        super().__init__()
        self.namespace = namespace
        self.image = image
        self.timeout = timeout
        self._pod_manager: Optional[PodSandboxManager] = None
        
    def start(self):
        """Start the pod sandbox."""
        if not self._started:
            logger.info("Starting pod sandbox...")
            
            # Create pod manager
            self._pod_manager = PodSandboxManager(
                namespace=self.namespace,
                image=self.image
            )
            
            # Start pod asynchronously
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If event loop is already running, create task
                task = loop.create_task(self._pod_manager.start_pod())
                # Wait for completion
                while not task.done():
                    loop.run_until_complete(asyncio.sleep(0.1))
                result = task.result()
            else:
                # If no event loop, run directly  
                result = loop.run_until_complete(self._pod_manager.start_pod())
            
            logger.info(f"Pod sandbox started: {result}")
            self._started = True
    
    def stop(self):
        """Stop the pod sandbox."""
        if self._started and self._pod_manager:
            logger.info("Stopping pod sandbox...")
            
            loop = asyncio.get_event_loop()
            if loop.is_running():
                task = loop.create_task(self._pod_manager.stop_pod())
                while not task.done():
                    loop.run_until_complete(asyncio.sleep(0.1))
                result = task.result()
            else:
                result = loop.run_until_complete(self._pod_manager.stop_pod())
            
            logger.info(f"Pod sandbox stopped: {result}")
            self._started = False
            self._pod_manager = None
    
    def _exec_code(self, code: str, environment: dict) -> dict:
        """Execute Python code in the pod sandbox."""
        if not self._started or not self._pod_manager:
            raise RuntimeError("Pod sandbox is not started")
        
        logger.info("Executing code in pod sandbox...")
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                task = loop.create_task(
                    self._pod_manager.execute_code(code, timeout=self.timeout)
                )
                while not task.done():
                    loop.run_until_complete(asyncio.sleep(0.1))
                result = task.result()
            else:
                result = loop.run_until_complete(
                    self._pod_manager.execute_code(code, timeout=self.timeout)
                )
            
            if result.get("success"):
                return {"result": result.get("result")}
            else:
                raise RuntimeError(result.get("error", "Unknown execution error"))
                
        except Exception as e:
            logger.error(f"Code execution failed: {e}")
            # Restart pod on failure for robustness
            self._restart_pod()
            raise RuntimeError(f"Code execution failed: {e}")
    
    def _restart_pod(self):
        """Restart the pod (useful for cleanup after errors)."""
        if self._pod_manager:
            logger.info("Restarting pod due to error...")
            loop = asyncio.get_event_loop()
            if loop.is_running():
                task = loop.create_task(self._pod_manager.restart_pod())
                while not task.done():
                    loop.run_until_complete(asyncio.sleep(0.1))
            else:
                loop.run_until_complete(self._pod_manager.restart_pod())
    
    def get_status(self) -> Dict[str, Any]:
        """Get current pod status."""
        if not self._pod_manager:
            return {"status": "not_initialized"}
        
        loop = asyncio.get_event_loop()
        if loop.is_running():
            task = loop.create_task(self._pod_manager.get_pod_status())
            while not task.done():
                loop.run_until_complete(asyncio.sleep(0.1))
            return task.result()
        else:
            return loop.run_until_complete(self._pod_manager.get_pod_status())
    
    def __del__(self):
        """Cleanup on deletion."""
        if self._started:
            self.stop()