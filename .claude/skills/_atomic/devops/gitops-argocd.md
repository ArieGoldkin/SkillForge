---
name: gitops-argocd
description: GitOps with ArgoCD for Kubernetes
version: 1.0.0
tags: [gitops, argocd, kubernetes, deployment]
size: atomic
domain: devops
---

# GitOps with ArgoCD

## Application Definition

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp
  namespace: argocd
spec:
  project: default

  source:
    repoURL: https://github.com/org/myapp-manifests
    targetRevision: main
    path: environments/production

  destination:
    server: https://kubernetes.default.svc
    namespace: production

  syncPolicy:
    automated:
      prune: true      # Delete removed resources
      selfHeal: true   # Revert manual changes
    syncOptions:
      - CreateNamespace=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        maxDuration: 3m
        factor: 2
```

## Directory Structure

```
manifests/
├── base/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── kustomization.yaml
└── environments/
    ├── staging/
    │   └── kustomization.yaml
    └── production/
        └── kustomization.yaml
```

## Kustomization

```yaml
# environments/production/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: production

resources:
  - ../../base

replicas:
  - name: myapp
    count: 5

images:
  - name: myapp
    newTag: v1.2.3
```

## Sync Commands

```bash
# Sync application
argocd app sync myapp

# Force sync (ignore hooks)
argocd app sync myapp --force

# Rollback
argocd app rollback myapp 3
```

## GitOps Workflow

```
Developer ──▶ PR to manifests repo
    │
    ▼
CI validates YAML + security scan
    │
    ▼
Merge to main
    │
    ▼
ArgoCD detects change ──▶ Syncs cluster
    │
    ▼
Self-healing on drift
```
