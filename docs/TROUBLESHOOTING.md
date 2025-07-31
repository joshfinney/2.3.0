# PandasAI Pod Sandbox Troubleshooting Guide

## Common Issues and Solutions

### 1. Pod Creation Failures

#### **Issue**: Pod fails to start with `ImagePullBackOff`
```bash
kubectl get pods -n pandasai-sandbox
# NAME                     READY   STATUS             RESTARTS   AGE
# python-sandbox-abc123    0/1     ImagePullBackOff   0          2m
```

**Root Causes:**
- Container image not found in registry
- Authentication issues with private registry
- Network connectivity problems

**Solutions:**
```bash
# Check image exists
docker pull your-registry/pandasai-sandbox-pod:latest

# Verify registry credentials
kubectl get secret regcred -n pandasai-sandbox -o yaml

# Create registry secret if missing
kubectl create secret docker-registry regcred \
  --docker-server=your-registry.com \
  --docker-username=your-username \
  --docker-password=your-password \
  --docker-email=your-email@company.com \
  -n pandasai-sandbox

# Update pod spec to use imagePullSecrets
```

#### **Issue**: Pod stuck in `Pending` state
```bash
kubectl describe pod python-sandbox-abc123 -n pandasai-sandbox
# Events:
# Warning  FailedScheduling  pod has unbound immediate PersistentVolumeClaims
```

**Root Causes:**
- Insufficient cluster resources
- Node selector constraints not met
- PersistentVolume issues
- Resource quotas exceeded

**Solutions:**
```bash
# Check cluster resources
kubectl top nodes
kubectl describe nodes

# Check resource quotas
kubectl describe quota sandbox-quota -n pandasai-sandbox

# Remove node selector if needed (temporarily)
kubectl patch pod python-sandbox-abc123 -n pandasai-sandbox --type='json' \
  -p='[{"op": "remove", "path": "/spec/nodeSelector"}]'

# Check available storage classes
kubectl get storageclass
```

### 2. Network Connectivity Issues

#### **Issue**: Cannot connect to pod API
```python
# Error: ConnectionRefusedError: [Errno 111] Connection refused
```

**Root Causes:**
- NetworkPolicy blocking traffic
- Service not created or misconfigured
- Pod not ready/healthy
- DNS resolution issues

**Solutions:**
```bash
# Check pod readiness
kubectl get pods -n pandasai-sandbox -o wide

# Test pod health directly
kubectl port-forward pod/python-sandbox-abc123 8080:8080 -n pandasai-sandbox &
curl http://localhost:8080/health

# Check service endpoints
kubectl get endpoints -n pandasai-sandbox

# Test DNS resolution
kubectl run debug --image=busybox --rm -it --restart=Never -- \
  nslookup python-sandbox-abc123.pandasai-sandbox.svc.cluster.local

# Temporarily disable NetworkPolicy for testing
kubectl delete networkpolicy python-sandbox-isolation -n pandasai-sandbox
```

#### **Issue**: NetworkPolicy too restrictive
```bash
# Pods cannot communicate despite service configuration
```

**Solutions:**
```bash
# Check current network policies
kubectl get networkpolicy -n pandasai-sandbox -o yaml

# Create debug pod to test connectivity
kubectl run netdebug --image=nicolaka/netshoot --rm -it --restart=Never -n pandasai-sandbox

# Inside debug pod, test connectivity
curl http://python-sandbox-abc123:8080/health

# Update NetworkPolicy to allow required traffic
```

### 3. Resource and Performance Issues

#### **Issue**: Pod gets OOMKilled (Out of Memory)
```bash
kubectl describe pod python-sandbox-abc123 -n pandasai-sandbox
# Last State: Terminated
# Reason: OOMKilled
```

**Root Causes:**
- Memory limits too low for workload
- Memory leak in analysis code
- Large datasets exceeding available memory

**Solutions:**
```bash
# Check resource usage
kubectl top pod python-sandbox-abc123 -n pandasai-sandbox

# Increase memory limits
kubectl patch pod python-sandbox-abc123 -n pandasai-sandbox --type='json' \
  -p='[{"op": "replace", "path": "/spec/containers/0/resources/limits/memory", "value": "1Gi"}]'

# Monitor memory usage over time
kubectl logs python-sandbox-abc123 -n pandasai-sandbox --previous

# Update pod template for future deployments
```

#### **Issue**: Code execution timeouts
```python
# Error: Code execution timed out after 30 seconds, pod restarted
```

**Root Causes:**
- Complex analysis taking longer than timeout
- Infinite loops in generated code
- Resource contention on nodes

**Solutions:**
```python
# Increase timeout in PodSandbox
sandbox = PodSandbox(
    namespace="pandasai-sandbox",
    timeout=120  # Increase from 30 to 120 seconds
)

# Monitor pod resource usage during execution
# Add resource requests to ensure dedicated resources
```

### 4. Authentication and Permissions

#### **Issue**: `Forbidden` errors when creating pods
```bash
# Error: pods is forbidden: User "system:serviceaccount:default:default" 
# cannot create resource "pods" in API group "" in the namespace "pandasai-sandbox"
```

**Root Causes:**
- Missing RBAC permissions
- ServiceAccount not properly configured
- Incorrect namespace permissions

**Solutions:**
```bash
# Check current permissions
kubectl auth can-i create pods --namespace=pandasai-sandbox --as=system:serviceaccount:pandasai-sandbox:default

# Create proper RBAC
kubectl apply -f - <<EOF
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: pandasai-sandbox
  name: pod-manager
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["create", "delete", "get", "list", "watch", "patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: pod-manager-binding
  namespace: pandasai-sandbox
subjects:
- kind: ServiceAccount
  name: default
  namespace: pandasai-sandbox
roleRef:
  kind: Role
  name: pod-manager
  apiGroup: rbac.authorization.k8s.io
EOF

# Verify permissions
kubectl auth can-i create pods --namespace=pandasai-sandbox
```

### 5. Code Execution Issues

#### **Issue**: Python import errors in sandbox
```python
# ModuleNotFoundError: No module named 'pandas'
```

**Root Causes:**
- Missing packages in container image
- Wrong Python environment
- Package version conflicts

**Solutions:**
```bash
# Check what's installed in the container
kubectl exec -it python-sandbox-abc123 -n pandasai-sandbox -- pip list

# Debug with interactive shell
kubectl exec -it python-sandbox-abc123 -n pandasai-sandbox -- /bin/bash

# Rebuild container with required packages
# Update pandasai_pod/Dockerfile and rebuild
```

#### **Issue**: File permission errors
```python
# PermissionError: [Errno 13] Permission denied: '/workspace/output.csv'
```

**Root Causes:**
- Volume mount permission issues
- Security context restrictions
- Read-only filesystem constraints

**Solutions:**
```bash
# Check volume mounts and permissions
kubectl describe pod python-sandbox-abc123 -n pandasai-sandbox

# Update security context in pod spec
securityContext:
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000

# Ensure writable directories exist
```

## Debugging Commands

### Essential Kubernetes Commands
```bash
# Check pod status and events
kubectl get pods -n pandasai-sandbox -o wide
kubectl describe pod <pod-name> -n pandasai-sandbox

# View pod logs
kubectl logs <pod-name> -n pandasai-sandbox -f
kubectl logs <pod-name> -n pandasai-sandbox --previous

# Debug networking
kubectl get services,endpoints -n pandasai-sandbox
kubectl get networkpolicy -n pandasai-sandbox

# Check resources
kubectl top nodes
kubectl top pods -n pandasai-sandbox
kubectl describe quota -n pandasai-sandbox

# Interactive debugging
kubectl exec -it <pod-name> -n pandasai-sandbox -- /bin/bash
kubectl port-forward <pod-name> 8080:8080 -n pandasai-sandbox
```

### Application-Level Debugging
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check sandbox status
sandbox = PodSandbox(namespace="pandasai-sandbox")
status = sandbox.get_status()
print(f"Sandbox status: {status}")

# Test connectivity manually
import requests
response = requests.get("http://service-name:8080/health")
print(f"Health check: {response.status_code}")
```

## Performance Optimization

### Resource Tuning
```yaml
# Optimized resource configuration
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
    ephemeral-storage: "2Gi"
```

### Pod Startup Optimization
```yaml
# Faster startup configuration
readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 1  # Reduce from default
  periodSeconds: 2        # Check more frequently
  
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 30
```

### Image Optimization
```dockerfile
# Multi-stage build for smaller images
FROM python:3.9-slim as builder
RUN pip install --no-cache-dir pandas numpy matplotlib

FROM python:3.9-slim
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
```

## Monitoring and Alerting

### Key Metrics to Monitor
```bash
# Pod resource usage
kubectl top pods -n pandasai-sandbox

# Pod restart count
kubectl get pods -n pandasai-sandbox -o custom-columns=NAME:.metadata.name,RESTARTS:.status.containerStatuses[0].restartCount

# Node resource availability
kubectl top nodes

# Network policy violations (if using Calico)
kubectl logs -n calico-system -l k8s-app=calico-node | grep DENY
```

### Alerting Rules (Prometheus)
```yaml
groups:
- name: pandasai-sandbox
  rules:
  - alert: PodCrashLooping
    expr: rate(kube_pod_container_status_restarts_total{namespace="pandasai-sandbox"}[15m]) > 0
    for: 5m
    
  - alert: PodOOMKilled
    expr: increase(kube_pod_container_status_terminated_reason{reason="OOMKilled",namespace="pandasai-sandbox"}[10m]) > 0
    
  - alert: PodHighMemoryUsage
    expr: container_memory_usage_bytes{namespace="pandasai-sandbox"} / container_spec_memory_limit_bytes > 0.8
```

## Best Practices for Prevention

### 1. **Resource Planning**
- Monitor actual resource usage before setting limits
- Use Horizontal Pod Autoscaler for dynamic scaling
- Implement resource quotas at namespace level

### 2. **Security Hardening** 
- Always use specific image tags, never `:latest`
- Implement Pod Security Standards
- Regular security scanning of container images

### 3. **Operational Excellence**
- Implement comprehensive monitoring and alerting
- Regular backup and disaster recovery testing  
- Documentation of runbooks and escalation procedures

### 4. **Development Practices**
- Test in staging environment first
- Use feature flags for gradual rollouts
- Implement proper error handling and retries

## Getting Help

### Community Support
- **GitHub Issues**: Report bugs and feature requests
- **Discussions**: Ask questions and share experiences
- **Slack/Discord**: Real-time community support

### Enterprise Support
- **Professional Services**: Implementation and optimization consulting
- **24/7 Support**: Critical issue resolution
- **Training**: Team education and best practices

### Documentation
- **Integration Guide**: Step-by-step implementation
- **API Reference**: Complete API documentation
- **Best Practices**: Production deployment patterns