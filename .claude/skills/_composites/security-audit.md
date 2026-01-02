---
name: security-audit
description: Complete security audit composite - OWASP, auth, secrets, scanning
version: 1.0.0
type: composite
includes:
  - security/owasp-top10
  - security/auth-patterns
  - security/input-sanitization
  - security/secrets-management
  - security/security-scanning
tags: [security, audit, composite]
---

# Security Audit Composite

Complete security audit combining all atomic security skills.

## Included Skills

| Skill | Purpose |
|-------|---------|
| owasp-top10 | Top 10 vulnerabilities & mitigations |
| auth-patterns | Authentication & authorization |
| input-sanitization | Validation, XSS, injection prevention |
| secrets-management | Credentials, env vars, secret detection |
| security-scanning | Automated security tools |

## Quick Audit Workflow

```bash
# 1. Dependency scan
npm audit              # JavaScript
pip-audit              # Python

# 2. Static analysis
semgrep --config=auto .
bandit -r app/         # Python

# 3. Secret detection
gitleaks detect --source .

# 4. Review results
```

## Audit Checklist

### OWASP Top 10
- [ ] Access control on all endpoints
- [ ] Passwords hashed (bcrypt/argon2)
- [ ] Parameterized queries (no SQL injection)
- [ ] Rate limiting on sensitive endpoints
- [ ] Debug mode disabled in production
- [ ] Dependencies scanned for vulnerabilities

### Authentication
- [ ] Strong password requirements (12+ chars)
- [ ] MFA available
- [ ] Secure session cookies (HTTPOnly, Secure, SameSite)
- [ ] JWT tokens expire appropriately
- [ ] Rate limited login attempts

### Input Validation
- [ ] All input validated before use
- [ ] HTML output escaped (XSS prevention)
- [ ] File uploads validated (type, size, content)
- [ ] Path traversal prevented
- [ ] Security headers set

### Secrets
- [ ] No hardcoded secrets in code
- [ ] .env in .gitignore
- [ ] Secret detection in CI/CD
- [ ] Secrets rotated regularly

### Scanning
- [ ] Dependency audit in CI
- [ ] SAST (Semgrep/Bandit) in CI
- [ ] Secret scanning in pre-commit
- [ ] Container scanning (if applicable)

## Severity Thresholds

| Severity | Action |
|----------|--------|
| **Critical** | BLOCK - Must fix before merge |
| **High (>5)** | BLOCK - Review required |
| **High (1-5)** | WARNING - Document and plan fix |
| **Moderate** | INFO - Track in backlog |

## CI/CD Integration

```yaml
security-scan:
  runs-on: ubuntu-latest
  steps:
    - name: Dependency Audit
      run: npm audit --audit-level=high

    - name: Semgrep SAST
      uses: returntocorp/semgrep-action@v1

    - name: Secret Detection
      uses: gitleaks/gitleaks-action@v2
```

## Output Template

```markdown
## Security Audit Report

### Summary
- Critical: 0
- High: 2
- Moderate: 5
- Status: **WARNING** (High vulnerabilities require review)

### Findings
1. **HIGH** - lodash@4.17.19 (Prototype Pollution)
   - Fix: npm update lodash
2. **HIGH** - SQL injection risk in users.py:45
   - Fix: Use parameterized query

### Recommendations
1. Update vulnerable dependencies
2. Add input validation to user endpoints
3. Enable MFA for admin accounts
```
