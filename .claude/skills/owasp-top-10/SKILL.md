---
name: owasp-top-10
description: OWASP Top 10 security vulnerabilities and mitigations. Use when conducting security audits, implementing security controls, or reviewing code for common vulnerabilities.
---

# OWASP Top 10

Protect against the most critical web security risks.

## When to Use

- Security audits
- Code review for vulnerabilities
- Designing secure systems
- Compliance requirements

## 1. Broken Access Control

```python
# ❌ Bad: No authorization check
@app.route('/api/users/<user_id>')
def get_user(user_id):
    return db.query(f"SELECT * FROM users WHERE id = {user_id}")

# ✅ Good: Verify user can access resource
@app.route('/api/users/<user_id>')
@login_required
def get_user(user_id):
    if current_user.id != user_id and not current_user.is_admin:
        abort(403)
    return db.query("SELECT * FROM users WHERE id = ?", [user_id])
```

## 2. Cryptographic Failures

```python
# ❌ Bad: Weak hashing
import hashlib
password_hash = hashlib.md5(password.encode()).hexdigest()

# ✅ Good: Strong hashing
from argon2 import PasswordHasher
ph = PasswordHasher()
password_hash = ph.hash(password)
```

## 3. Injection

```python
# ❌ Bad: SQL injection vulnerable
query = f"SELECT * FROM users WHERE email = '{email}'"

# ✅ Good: Parameterized query
query = "SELECT * FROM users WHERE email = ?"
db.execute(query, [email])
```

## 4. Insecure Design

- No rate limiting on login
- Sequential/guessable IDs
- No CAPTCHA on sensitive operations

**Fix:** Use UUIDs, implement rate limiting, threat model early.

## 5. Security Misconfiguration

```python
# ❌ Bad: Debug mode in production
app.debug = True

# ✅ Good: Environment-based config
app.debug = os.getenv('FLASK_ENV') == 'development'
```

## 6. Vulnerable Components

```bash
# Scan for vulnerabilities
npm audit
pip-audit

# Fix vulnerabilities
npm audit fix
```

## 7. Authentication Failures

```python
# ✅ Strong password requirements
def validate_password(password):
    if len(password) < 12:
        return "Password must be 12+ characters"
    if not re.search(r"[A-Z]", password):
        return "Must contain uppercase"
    if not re.search(r"[0-9]", password):
        return "Must contain number"
    return None
```

## 8. Data Integrity Failures

```html
<!-- Use SRI for CDN scripts -->
<script src="https://cdn.example.com/lib.js"
        integrity="sha384-..."
        crossorigin="anonymous"></script>
```

## 9. Logging Failures

```python
# ✅ Log security events
@app.route('/login', methods=['POST'])
def login():
    user = authenticate(email, password)
    if user:
        logger.info(f"Successful login: {email}")
    else:
        logger.warning(f"Failed login: {email}")
```

## 10. SSRF (Server-Side Request Forgery)

```python
# ❌ Bad: Fetch any URL
response = requests.get(user_provided_url)

# ✅ Good: Allowlist domains
ALLOWED = ['api.example.com']
if urlparse(url).hostname not in ALLOWED:
    abort(400)
```

## Quick Checklist

- [ ] Authorization on all endpoints
- [ ] Passwords hashed with bcrypt/argon2
- [ ] Parameterized queries only
- [ ] Rate limiting enabled
- [ ] Debug mode off in production
- [ ] Dependencies scanned regularly
- [ ] Security events logged

## Related Skills

- `auth-patterns` - Authentication implementation
- `input-validation` - Sanitization patterns
- `security-scanning` - Automated scanning
