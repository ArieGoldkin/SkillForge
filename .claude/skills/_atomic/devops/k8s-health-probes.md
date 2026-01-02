---
name: k8s-health-probes
description: Kubernetes liveness, readiness, and startup probes
version: 1.0.0
tags: [kubernetes, health-checks, probes]
size: atomic
domain: devops
---

# Kubernetes Health Probes

## Three Probe Types

| Probe | Purpose | On Failure |
|-------|---------|------------|
| Startup | Is app finished starting? | Keep waiting |
| Liveness | Is app running? | Restart pod |
| Readiness | Ready for traffic? | Remove from LB |

## Configuration

```yaml
spec:
  containers:
  - name: app
    # Startup (slow apps get time to boot)
    startupProbe:
      httpGet:
        path: /health/startup
        port: 8080
      initialDelaySeconds: 0
      periodSeconds: 5
      failureThreshold: 30  # 30 * 5s = 150s max

    # Liveness (restarts if failing)
    livenessProbe:
      httpGet:
        path: /health/liveness
        port: 8080
      initialDelaySeconds: 60
      periodSeconds: 10
      failureThreshold: 3

    # Readiness (removes from service)
    readinessProbe:
      httpGet:
        path: /health/readiness
        port: 8080
      initialDelaySeconds: 10
      periodSeconds: 5
      failureThreshold: 2
```

## Endpoint Implementation

```python
@app.get("/health/startup")
async def startup():
    """Check DB connection established."""
    if not db.is_connected():
        raise HTTPException(503, "DB not ready")
    return {"status": "ok"}

@app.get("/health/liveness")
async def liveness():
    """Basic process check."""
    return {"status": "alive"}

@app.get("/health/readiness")
async def readiness():
    """Check all dependencies healthy."""
    if not redis.ping() or not db.health_check():
        raise HTTPException(503, "Dependencies unhealthy")
    return {"status": "ready"}
```

## Response Format

```json
{
  "status": "healthy",
  "checks": {
    "database": {"status": "pass", "latency_ms": 5},
    "redis": {"status": "pass", "latency_ms": 2}
  },
  "version": "1.0.0",
  "uptime": 3600
}
```
