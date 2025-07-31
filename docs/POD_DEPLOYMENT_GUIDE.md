# Kubernetes Pod Sandbox Deployment Guide

## Overview

This guide walks you through deploying PandasAI's pod-based sandbox architecture in your Kubernetes cluster for secure, scalable Python code execution.

## Prerequisites

### Required Tools
- **Kubernetes cluster** (1.20+) with RBAC enabled
- **kubectl** configured to access your cluster
- **Docker** for building container images
- **Python 3.9+** with pip

### Cluster Requirements
- **Minimum Resources**: 2 CPU cores, 4GB RAM per node
- **Network Policies**: CNI plugin supporting NetworkPolicy (Calico, Cilium, etc.)
- **Storage**: Persistent volumes for chart storage (optional)
- **RBAC**: ServiceAccount with pod creation/deletion permissions

## Step 1: Prepare Your Kubernetes Cluster

### Option A: Local Development (minikube/kind)
```bash
# Start minikube with required features
minikube start --cpus=4 --memory=8192 --addons=metrics-server,ingress

# Enable network policies (if using Calico)
minikube addons enable calico
```

### Option B: Cloud Provider Setup
```bash
# AWS EKS
eksctl create cluster --name pandasai-cluster --nodes 3 --node-type t3.medium

# Google GKE
gcloud container clusters create pandasai-cluster --num-nodes=3 --machine-type=e2-standard-4

# Azure AKS
az aks create --resource-group myResourceGroup --name pandasai-cluster --node-count 3 --node-vm-size Standard_D2s_v3
```

### Verify Cluster Setup
```bash
kubectl cluster-info
kubectl get nodes
kubectl auth can-i create pods --namespace=default
```

## Step 2: Build and Deploy Container Image

### Build the Sandbox Image
```bash
cd pandasai_pod/
docker build -t pandasai-sandbox-pod:latest .

# Tag for your registry
docker tag pandasai-sandbox-pod:latest your-registry/pandasai-sandbox-pod:latest
docker push your-registry/pandasai-sandbox-pod:latest
```

### Update Image References
```bash
# Update k8s/python-sandbox-pod.yaml
sed -i 's|pandasai-sandbox-pod:latest|your-registry/pandasai-sandbox-pod:latest|g' ../k8s/python-sandbox-pod.yaml
```

## Step 3: Configure Kubernetes Resources

### Create Namespace (Recommended)
```bash
kubectl create namespace pandasai-sandbox
kubectl config set-context --current --namespace=pandasai-sandbox
```

### Apply Network Security
```bash
# Deploy network policies for isolation
kubectl apply -f k8s/network-policy.yaml -n pandasai-sandbox
```

### Set Up RBAC
```bash
cat << 'EOF' | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: pandasai-sandbox-sa
  namespace: pandasai-sandbox
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: pandasai-sandbox
  name: pod-manager
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["create", "delete", "get", "list", "watch"]
- apiGroups: [""]
  resources: ["pods/exec"]
  verbs: ["create"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: pod-manager-binding
  namespace: pandasai-sandbox
subjects:
- kind: ServiceAccount
  name: pandasai-sandbox-sa
  namespace: pandasai-sandbox
roleRef:
  kind: Role
  name: pod-manager
  apiGroup: rbac.authorization.k8s.io
EOF
```

## Step 4: Configure Resource Limits

### Create Resource Quotas
```bash
cat << 'EOF' | kubectl apply -f -
apiVersion: v1
kind: ResourceQuota
metadata:
  name: sandbox-quota
  namespace: pandasai-sandbox
spec:
  hard:
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
    pods: "10"
    persistentvolumeclaims: "5"
EOF
```

### Set Default Limits
```bash
cat << 'EOF' | kubectl apply -f -
apiVersion: v1
kind: LimitRange
metadata:
  name: sandbox-limits
  namespace: pandasai-sandbox
spec:
  limits:
  - default:
      cpu: "500m"
      memory: "512Mi"
    defaultRequest:
      cpu: "250m"
      memory: "256Mi"
    type: Container
EOF
```

## Step 5: Node Configuration (Optional)

### Label Nodes for Sandbox Workloads
```bash
# Label specific nodes for sandbox workloads
kubectl label nodes worker-node-1 workload-type=sandbox
kubectl label nodes worker-node-2 workload-type=sandbox

# Add taints to dedicated sandbox nodes
kubectl taint nodes worker-node-1 sandbox=true:NoSchedule
kubectl taint nodes worker-node-2 sandbox=true:NoSchedule
```

## Step 6: Deploy Monitoring (Optional)

### Deploy Prometheus ServiceMonitor
```bash
cat << 'EOF' | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: pandasai-sandbox-metrics
  namespace: pandasai-sandbox
spec:
  selector:
    matchLabels:
      app: python-sandbox
  endpoints:
  - port: api
    path: /metrics
    interval: 30s
EOF
```

## Step 7: Verify Deployment

### Test Pod Creation
```bash
# Test manual pod deployment
kubectl apply -f k8s/python-sandbox-pod.yaml -n pandasai-sandbox

# Check pod status
kubectl get pods -n pandasai-sandbox
kubectl describe pod python-sandbox-test -n pandasai-sandbox

# Test API connectivity
kubectl port-forward pod/python-sandbox-test 8080:8080 -n pandasai-sandbox &
curl http://localhost:8080/health

# Cleanup test pod
kubectl delete pod python-sandbox-test -n pandasai-sandbox
```

## Configuration Files Summary

Your deployment should include:
- **k8s/python-sandbox-pod.yaml** - Pod template
- **k8s/network-policy.yaml** - Network isolation
- **RBAC resources** - Service accounts and permissions
- **Resource quotas** - Cluster resource management
- **Node labels/taints** - Workload placement (optional)

## Security Hardening

### Pod Security Standards
```bash
cat << 'EOF' | kubectl apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: pandasai-sandbox
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
EOF
```

### Network Policies Best Practices
- Default deny all ingress/egress
- Allow only necessary communication paths
- Separate sandbox pods from production workloads
- Monitor network traffic with service mesh

## Next Steps

1. **Test Integration**: Use the integration guide to connect your PandasAI code
2. **Monitor Resources**: Set up dashboards for pod resource usage
3. **Scale Configuration**: Configure HPA for automatic scaling
4. **Backup Strategy**: Plan for persistent data if needed
5. **Security Audit**: Regular security reviews and updates

## Troubleshooting

See the troubleshooting section for common deployment issues and solutions.