---
name: security-scanning
description: Automated security scanning for dependencies and code. Use when running npm audit, pip-audit, Semgrep, secret detection, or integrating security checks into CI/CD.
---

# Security Scanning

Automate vulnerability detection in code and dependencies.

## When to Use

- Before code review completion
- After dependency updates
- In CI/CD pipelines
- Before production deployments

## Dependency Scanning

### JavaScript (npm)

```bash
# Run audit
npm audit --json > security-audit.json

# Check severity counts
CRITICAL=$(npm audit --json | jq '.metadata.vulnerabilities.critical')
HIGH=$(npm audit --json | jq '.metadata.vulnerabilities.high')

if [ "$CRITICAL" -gt 0 ] || [ "$HIGH" -gt 0 ]; then
  echo "🚨 $CRITICAL critical, $HIGH high vulnerabilities"
fi

# Auto-fix
npm audit fix
```

### Python (pip-audit)

```bash
pip-audit --format=json > security-audit.json

# Using safety
safety check --json > security-audit.json
```

## Static Analysis (SAST)

### Semgrep

```bash
# Run with security rules
semgrep --config=auto --json > semgrep-results.json

# Count findings
CRITICAL=$(cat semgrep-results.json | jq '[.results[] | select(.extra.severity == "ERROR")] | length')
```

### Bandit (Python)

```bash
bandit -r . -f json -o bandit-report.json

HIGH=$(cat bandit-report.json | jq '[.results[] | select(.issue_severity == "HIGH")] | length')
```

## Secret Detection

```bash
# TruffleHog
trufflehog git file://. --json > secrets-scan.json

# Gitleaks
gitleaks detect --source . --report-format json

# Check results
SECRET_COUNT=$(cat secrets-scan.json | jq '. | length')
if [ "$SECRET_COUNT" -gt 0 ]; then
  echo "🚨 $SECRET_COUNT secrets detected!"
fi
```

## Container Scanning

```bash
# Trivy
trivy image myapp:latest --format json > trivy-scan.json

CRITICAL=$(cat trivy-scan.json | jq '[.Results[].Vulnerabilities[]? | select(.Severity == "CRITICAL")] | length')
```

## CI Integration

```yaml
# GitHub Actions
- name: Security scan
  run: |
    npm audit --json > audit.json
    CRITICAL=$(jq '.metadata.vulnerabilities.critical' audit.json)
    if [ "$CRITICAL" -gt 0 ]; then
      echo "::error::Critical vulnerabilities found"
      exit 1
    fi
```

## Escalation Thresholds

| Severity | Threshold | Action |
|----------|-----------|--------|
| Critical | Any | BLOCK |
| High | > 5 | BLOCK |
| Moderate | > 20 | WARNING |
| Low | > 50 | WARNING |

## Evidence Recording

```typescript
context.quality_evidence.security_scan = {
  executed: true,
  tool: 'npm audit',
  critical: 2,
  high: 5,
  moderate: 10,
  timestamp: new Date().toISOString()
};
```

## Key Decisions

| Decision | Recommendation |
|----------|----------------|
| JS dependencies | npm audit |
| Python dependencies | pip-audit |
| Code analysis | Semgrep |
| Secrets | TruffleHog or Gitleaks |

## Common Mistakes

- Ignoring audit warnings
- No CI integration
- Not blocking on critical
- Missing secret scanning

## Related Skills

- `owasp-top-10` - Vulnerability context
- `devops-deployment` - CI/CD integration
- `code-review-playbook` - Review process
