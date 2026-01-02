---
name: auth-patterns
description: Authentication and authorization patterns. Use when implementing login flows, JWT tokens, session management, password security, or role-based access control.
---

# Authentication Patterns

Implement secure authentication and authorization.

## When to Use

- Login/signup flows
- JWT token management
- Session security
- Role-based access control

## Password Hashing

```python
from argon2 import PasswordHasher

ph = PasswordHasher()

# Hash password
password_hash = ph.hash(password)

# Verify password
try:
    ph.verify(password_hash, password)
    # Password correct
except:
    # Password incorrect
    pass
```

**Requirements:**
- Minimum 12 characters
- Mixed case + numbers + symbols
- Use bcrypt, argon2, or scrypt
- Check against common password lists

## Session Management

```python
# Secure session cookies
app.config['SESSION_COOKIE_SECURE'] = True      # HTTPS only
app.config['SESSION_COOKIE_HTTPONLY'] = True    # No JS access
app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'
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

## Rate Limiting

```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=get_remote_address)

@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")  # 5 attempts per minute
def login():
    # Login logic
    pass
```

## Role-Based Access Control

```python
from functools import wraps

def require_role(role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if current_user.role != role:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator

@app.route('/admin/users')
@login_required
@require_role('admin')
def admin_users():
    return get_all_users()
```

## Multi-Factor Authentication

```python
import pyotp

def generate_totp_secret() -> str:
    return pyotp.random_base32()

def verify_totp(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code)
```

## Key Decisions

| Decision | Recommendation |
|----------|----------------|
| Password hash | Argon2 or bcrypt |
| Token expiry | 1-24 hours |
| Session cookie | HTTPOnly, Secure, SameSite |
| Rate limit | 5 attempts per 15 min |

## Common Mistakes

- Storing passwords in plaintext
- No rate limiting on login
- Long-lived tokens
- Revealing if email exists
- No MFA option

## Related Skills

- `owasp-top-10` - Security fundamentals
- `input-validation` - Data validation
- `api-design-framework` - API security
