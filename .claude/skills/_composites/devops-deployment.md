---
name: devops-deployment
description: Complete CI/CD, containerization, and Kubernetes deployment
version: 1.0.0
tags: [devops, cicd, kubernetes, docker, deployment]
size: composite
atomics:
  - devops/cicd-pipeline
  - devops/docker-containers
  - devops/kubernetes-deployments
  - devops/k8s-health-probes
  - devops/deployment-strategies
  - devops/terraform-iac
  - devops/gitops-argocd
---

# DevOps & Deployment Composite

Complete deployment knowledge from CI/CD to production Kubernetes.

## When to Use

- Setting up CI/CD pipelines
- Containerizing applications
- Deploying to Kubernetes
- Implementing GitOps workflows
- Managing infrastructure as code

## Atomic Skills

### 1. CI/CD Pipeline (`cicd-pipeline`)
Pipeline stages, caching, artifacts, matrix testing.

### 2. Docker Containers (`docker-containers`)
Multi-stage builds, layer optimization, security.

### 3. Kubernetes Deployments (`kubernetes-deployments`)
Deployments, services, ingress, HPA, PDB.

### 4. Health Probes (`k8s-health-probes`)
Liveness, readiness, startup probes.

### 5. Deployment Strategies (`deployment-strategies`)
Rolling, blue-green, canary deployments.

### 6. Terraform IaC (`terraform-iac`)
Infrastructure as code with Terraform.

### 7. GitOps ArgoCD (`gitops-argocd`)
GitOps workflows with ArgoCD.

## Quick Reference

```
┌─────────────────────────────────────────────────────────────┐
│  DEPLOYMENT FLOW                                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Code ──▶ CI/CD ──▶ Docker Build ──▶ Push to Registry       │
│                                              │              │
│                                              ▼              │
│  ArgoCD watches repo ──▶ Syncs K8s manifests               │
│                                              │              │
│                                              ▼              │
│  Deployment (Rolling/Canary) ──▶ Health checks ──▶ Live    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Load Order

1. `cicd-pipeline` - Automated builds and tests
2. `docker-containers` - Containerization
3. `kubernetes-deployments` - K8s manifests
4. `k8s-health-probes` - Health checks
5. `deployment-strategies` - Rollout strategies
6. `terraform-iac` - Infrastructure
7. `gitops-argocd` - GitOps automation
