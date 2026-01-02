---
name: security-scanning
description: Automated security scanning tools and workflows
version: 1.0.0
tags: [security, scanning, audit, sast]
size: atomic
domain: security
---

# Automated Security Scanning

## Dependency Scanning

### JavaScript/TypeScript

```bash
# npm audit (built-in)
npm audit
npm audit --json > audit.json
npm audit fix  # Auto-fix

# Parse results
CRITICAL=$(npm audit --json | jq '.metadata.vulnerabilities.critical')
if [ "$CRITICAL" -gt 0 ]; then
  echo "CRITICAL vulnerabilities found!"
  exit 1
fi
```

### Python

```bash
# pip-audit (official)
pip install pip-audit
pip-audit
pip-audit --format=json > audit.json

# safety (alternative)
pip install safety
safety check --json > safety.json
```

## Static Analysis (SAST)

### Semgrep (Multi-language)

```bash
# Install
pip install semgrep

# Run with auto-config
semgrep --config=auto .

# Run with security rules
semgrep --config=p/security-audit .

# JSON output
semgrep --config=auto --json > semgrep.json
```

### Bandit (Python)

```bash
# Install
pip install bandit

# Scan directory
bandit -r app/ -f json -o bandit.json

# Common findings
# - B101: assert used
# - B105: hardcoded password
# - B108: /tmp usage
# - B301: pickle usage
```

## Secret Detection

```bash
# TruffleHog
trufflehog git file://. --json > secrets.json

# Gitleaks
gitleaks detect --source . -v

# detect-secrets
pip install detect-secrets
detect-secrets scan > .secrets.baseline
```

## Container Scanning

```bash
# Trivy (recommended)
trivy image myapp:latest --format json > trivy.json

# Scan severity
trivy image myapp:latest --severity HIGH,CRITICAL
```

## CI/CD Integration

```yaml
# GitHub Actions
name: Security Scan

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Dependency Audit
        run: npm audit --audit-level=high

      - name: Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: p/security-audit

      - name: Gitleaks
        uses: gitleaks/gitleaks-action@v2
```

## Thresholds

| Severity | Action |
|----------|--------|
| Critical | BLOCK deployment |
| High (>5) | BLOCK deployment |
| High (1-5) | WARNING, review required |
| Moderate (>20) | WARNING |
| Low | Log only |

## Evidence Recording

```python
security_evidence = {
    "executed": True,
    "timestamp": datetime.now().isoformat(),
    "tools": ["npm audit", "semgrep"],
    "findings": {
        "critical": 0,
        "high": 2,
        "moderate": 5,
        "low": 10
    },
    "passed": True  # False if critical > 0 or high > 5
}
```

## Quick Commands

```bash
# Full security scan
npm audit && semgrep --config=auto . && gitleaks detect

# Python project
pip-audit && bandit -r . && detect-secrets scan

# Before commit
npx husky add .husky/pre-commit "npm audit --audit-level=high"
```

## Tool Comparison

| Tool | Language | Type | Speed |
|------|----------|------|-------|
| npm audit | JS/TS | Dependencies | Fast |
| pip-audit | Python | Dependencies | Fast |
| Semgrep | Multi | SAST | Medium |
| Bandit | Python | SAST | Fast |
| TruffleHog | Any | Secrets | Medium |
| Trivy | Containers | All | Fast |
