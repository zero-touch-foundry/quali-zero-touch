---
name: k8s-operations
description: >
  Use this skill when the user asks about "Kubernetes troubleshooting", "pod issues",
  "k8s debugging", "cluster management", "namespace configuration", "kubectl commands",
  "Kubernetes networking", "ingress setup", "service mesh", "pod scheduling",
  "resource limits", "HPA", "node management", or needs help diagnosing Kubernetes
  problems, writing manifests, or managing clusters. Also trigger when investigating
  Torque environment issues that involve Kubernetes resources.
version: 0.1.0
---

# Kubernetes Operations

Guide users through Kubernetes troubleshooting, manifest authoring, and cluster management.

## Troubleshooting Workflow

When diagnosing issues, follow this systematic approach:

### 1. Check pod status

```
kubectl get pods -n <namespace> -o wide
kubectl describe pod <pod-name> -n <namespace>
```

Look for: CrashLoopBackOff, ImagePullBackOff, Pending, OOMKilled, Evicted.

### 2. Inspect logs

```
kubectl logs <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace> --previous   # crashed container
kubectl logs <pod-name> -c <container> -n <namespace>  # specific container
```

### 3. Check events

```
kubectl get events -n <namespace> --sort-by=.metadata.creationTimestamp
```

### 4. Resource pressure

```
kubectl top pods -n <namespace>
kubectl top nodes
kubectl describe node <node-name>  # check Conditions and Allocatable
```

## Common Issues & Fixes

**CrashLoopBackOff**: Check logs for application errors. Verify config maps, secrets, and environment variables. Check resource limits (OOMKilled = increase memory limit).

**ImagePullBackOff**: Verify image name and tag. Check image pull secrets. Confirm registry accessibility from the cluster.

**Pending pods**: Check node resources (`kubectl describe node`). Verify node selectors, tolerations, and affinity rules. Check PVC binding for storage-dependent pods.

**Service connectivity**: Verify service selectors match pod labels. Check endpoints (`kubectl get endpoints`). Test DNS resolution from within a pod. Verify network policies.

## Manifest Best Practices

- Always set resource requests AND limits for CPU and memory.
- Use liveness and readiness probes for all production workloads.
- Define pod disruption budgets for high-availability services.
- Use namespaces to isolate workloads and apply resource quotas.
- Label everything consistently: `app`, `version`, `environment`, `team`.
- Use ConfigMaps for non-sensitive config; Secrets for credentials.
- Set `imagePullPolicy: Always` in non-production, pin image tags in production.

## Scaling

- **HPA (Horizontal Pod Autoscaler)**: Scale based on CPU, memory, or custom metrics.
- **VPA (Vertical Pod Autoscaler)**: Auto-adjust resource requests and limits.
- **Cluster Autoscaler**: Scale nodes based on pending pod demand.
- **KEDA**: Event-driven autoscaling for queue-based workloads.

## Networking

- **Services**: ClusterIP (internal), NodePort (external basic), LoadBalancer (cloud LB).
- **Ingress**: HTTP/HTTPS routing; use ingress controllers (nginx, ALB, Traefik).
- **Network Policies**: Control pod-to-pod traffic; default-deny is the secure baseline.
- **DNS**: CoreDNS resolves `<service>.<namespace>.svc.cluster.local`.

## Torque + Kubernetes

When working with Torque Kubernetes or Helm grains:

- Target namespaces must exist before deployment.
- Service accounts need permissions for the grain's resource types.
- Avoid using Torque agent namespaces as targets.
- No concurrent environments from the same blueprint on the same namespace.
- Use post-install scripts to extract outputs via `kubectl` and export as env vars.
