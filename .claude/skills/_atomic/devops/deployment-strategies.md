---
name: deployment-strategies
description: Rolling, blue-green, and canary deployments
version: 1.0.0
tags: [deployment, rolling, blue-green, canary]
size: atomic
domain: devops
---

# Deployment Strategies

## Comparison

| Strategy | Risk | Resources | Rollback |
|----------|------|-----------|----------|
| Rolling | Low | Normal | Auto |
| Blue-Green | Medium | 2x | Instant |
| Canary | Low | +10-50% | Fast |

## Rolling Update (Default)

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 25%       # Extra pods during update
    maxUnavailable: 0   # Zero downtime
```

**Process**:
1. Create new pod
2. Wait for ready
3. Terminate old pod
4. Repeat

## Blue-Green

```yaml
# Blue (current)
apiVersion: v1
kind: Service
metadata:
  name: myapp
spec:
  selector:
    app: myapp
    version: blue  # ← Switch to 'green' for deployment

---
# Green (new)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-green
spec:
  replicas: 3
  template:
    metadata:
      labels:
        version: green
```

**Process**:
1. Deploy green alongside blue
2. Test green
3. Switch service selector
4. Delete blue

## Canary

```yaml
# Istio VirtualService
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
spec:
  http:
  - route:
    - destination:
        host: myapp
        subset: stable
      weight: 90
    - destination:
        host: myapp
        subset: canary
      weight: 10  # 10% → 50% → 100%
```

**Process**:
1. Deploy canary (10% traffic)
2. Monitor metrics
3. Increase traffic gradually
4. Full rollout or rollback

## Rollback

```bash
# Kubernetes
kubectl rollout undo deployment/myapp

# Helm
helm rollback myapp 3
```
