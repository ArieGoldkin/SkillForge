---
name: owasp-top10
description: OWASP Top 10 vulnerabilities and mitigations
version: 1.0.0
tags: [security, owasp, vulnerabilities]
size: atomic
domain: security
---

# OWASP Top 10 (2021)

## 1. Broken Access Control

**Vulnerability**: Users access resources they shouldn't.

```python
# BAD: No authorization check
@app.route('/api/users/<user_id>')
def get_user(user_id):
    return db.query(f"SELECT * FROM users WHERE id = {user_id}")

# GOOD: Verify ownership
@app.route('/api/users/<user_id>')
@login_required
def get_user(user_id):
    if current_user.id != user_id and not current_user.is_admin:
        abort(403)
    return db.query("SELECT * FROM users WHERE id = ?", [user_id])
```

**Mitigations**: Deny by default, enforce ownership, RBAC, log failures.

## 2. Cryptographic Failures

```python
# BAD: Weak hashing
hashlib.md5(password.encode()).hexdigest()

# GOOD: Strong hashing
from argon2 import PasswordHasher
ph = PasswordHasher()
hash = ph.hash(password)
```

**Use**: bcrypt, argon2, scrypt. **Never**: MD5, SHA1 for passwords.

## 3. Injection

```python
# BAD: SQL injection
query = f"SELECT * FROM users WHERE email = '{email}'"

# GOOD: Parameterized
query = "SELECT * FROM users WHERE email = ?"
db.execute(query, [email])
```

**Mitigations**: Parameterized queries, ORMs, avoid eval/exec.

## 4. Insecure Design

- Rate limit login/password reset
- Use UUIDs not sequential IDs
- Require email verification
- Design for secure defaults

## 5. Security Misconfiguration

```python
# BAD
app.debug = True  # In production

# GOOD
app.debug = os.getenv('ENV') == 'development'
```

**Checklist**: Disable debug, remove defaults, set security headers, update dependencies.

## 6. Vulnerable Components

```bash
npm audit          # JavaScript
pip-audit          # Python
```

Pin versions, scan regularly, subscribe to advisories.

## 7. Auth Failures

```python
# Strong password validation
def validate_password(password):
    if len(password) < 12:
        return "Min 12 characters"
    if not re.search(r"[A-Z]", password):
        return "Need uppercase"
    if not re.search(r"[0-9]", password):
        return "Need number"
    return None
```

**Mitigations**: MFA, rate limiting, secure sessions, don't reveal user existence.

## 8. Integrity Failures

```html
<!-- Use SRI for CDN scripts -->
<script src="https://cdn.example.com/lib.js"
        integrity="sha384-..."
        crossorigin="anonymous"></script>
```

## 9. Logging Failures

```python
# Log security events
logger.info(f"Login success: {email}")
logger.warning(f"Login failed: {email}")
# NEVER log passwords or tokens
```

## 10. SSRF

```python
# BAD: Fetching user URL
response = requests.get(user_url)

# GOOD: Allowlist domains
ALLOWED = ['api.example.com']
if urlparse(url).hostname not in ALLOWED:
    abort(400)
```

**Block**: Internal IPs (127.0.0.1, 10.x, 192.168.x).
