---
name: alerting-strategy
description: Alert fatigue prevention and escalation policies
version: 1.0.0
tags: [alerting, prometheus, pagerduty, observability]
size: atomic
domain: devops
---

# Alerting Strategy

## Severity Levels

| Level | Response | Examples |
|-------|----------|----------|
| Critical (P1) | <15 min | Service down, data loss |
| High (P2) | <1 hour | Major feature broken |
| Medium (P3) | <4 hours | Increased errors |
| Low (P4) | Next day | Warnings |

## Alert Rules

```yaml
groups:
- name: app-alerts
  rules:
  - alert: HighErrorRate
    expr: |
      sum(rate(http_requests_total{status=~"5.."}[5m])) /
      sum(rate(http_requests_total[5m])) > 0.05
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Error rate {{ $value | humanizePercentage }}"
      runbook_url: "https://wiki/runbooks/high-error-rate"

  - alert: HighLatency
    expr: histogram_quantile(0.95, rate(..._bucket[5m])) > 2
    for: 5m
    labels:
      severity: warning
```

## Alert Grouping

```yaml
route:
  group_by: ['alertname', 'cluster']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

  routes:
  - match:
      severity: critical
    receiver: pagerduty
  - match:
      severity: warning
    receiver: slack
```

## Inhibition Rules

```yaml
inhibit_rules:
# Suppress HighErrorRate when ServiceDown fires
- source_match:
    alertname: ServiceDown
  target_match_re:
    alertname: (HighErrorRate|HighLatency)
  equal: ['service']
```

## Runbook Template

1. What the alert means
2. Impact on users
3. Common causes
4. Investigation steps
5. Remediation steps
6. Escalation contacts
