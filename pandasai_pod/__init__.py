"""
PandasAI Pod Sandbox - Kubernetes-based secure Python code execution.

This module provides a professional, production-ready alternative to Docker containers
using Kubernetes pods with enhanced security, scalability, and operational features.
"""

from .pod_sandbox import PodSandbox
from .pod_manager import PodSandboxManager

__version__ = "1.0.0"
__all__ = ["PodSandbox", "PodSandboxManager"]