---
name: auth-patterns
description: Authentication and authorization patterns
version: 1.0.0
tags: [security, auth, jwt, sessions]
size: atomic
domain: security
---

# Authentication & Authorization Patterns

## Password Security

```python
from argon2 import PasswordHasher

ph = PasswordHasher()

# Hash password
hash = ph.hash(password)

# Verify password
try:
    ph.verify(hash, password)
    # Correct
except:
    # Incorrect
    pass
```

**Requirements**:
- Minimum 12 characters
- Mixed case, numbers, symbols
- Check against breached passwords (haveibeenpwned)
- Use bcrypt, argon2, or scrypt

## Session Management

```python
# Secure session cookies
app.config['SESSION_COOKIE_SECURE'] = True      # HTTPS only
app.config['SESSION_COOKIE_HTTPONLY'] = True    # No JS access
app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'  # CSRF protection
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
```

## JWT Tokens

```python
import jwt
from datetime import datetime, timedelta

def create_token(user_id: str) -> str:
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=1),
        'iat': datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
```

## Authorization Patterns

### Role-Based Access Control (RBAC)

```python
from functools import wraps

def require_role(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator

@app.route('/admin')
@require_role('admin', 'superadmin')
def admin_panel():
    return render_template('admin.html')
```

### Resource Ownership

```python
@app.route('/api/posts/<post_id>')
@login_required
def get_post(post_id):
    post = Post.query.get_or_404(post_id)

    # Check ownership or admin
    if post.author_id != current_user.id and not current_user.is_admin:
        abort(403, "You don't have access to this resource")

    return jsonify(post.to_dict())
```

## Rate Limiting

```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=get_remote_address)

@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")  # 5 attempts per minute
def login():
    # ...
```

## Multi-Factor Authentication

```python
import pyotp

# Generate secret for user
secret = pyotp.random_base32()

# Generate TOTP
totp = pyotp.TOTP(secret)
current_otp = totp.now()

# Verify TOTP
def verify_mfa(user_secret: str, code: str) -> bool:
    totp = pyotp.TOTP(user_secret)
    return totp.verify(code, valid_window=1)  # Allow 30s window
```

## Security Best Practices

- [ ] Rate limit login attempts
- [ ] Don't reveal if email exists
- [ ] Invalidate sessions on logout
- [ ] Implement account lockout
- [ ] Log all auth events
- [ ] Use HTTPS only
- [ ] Rotate secrets regularly
