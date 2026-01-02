---
name: input-sanitization
description: Input validation, sanitization, XSS and injection prevention
version: 1.0.0
tags: [security, validation, xss, injection]
size: atomic
domain: security
---

# Input Validation & Sanitization

## Core Principle

**ALL input is untrusted**: query params, headers, cookies, POST data, file uploads.

## Validation with Pydantic

```python
from pydantic import BaseModel, EmailStr, Field, constr

class UserCreate(BaseModel):
    email: EmailStr
    name: constr(min_length=2, max_length=100)
    age: int = Field(ge=0, le=150)

# Usage
try:
    user = UserCreate(**request.json)
except ValidationError as e:
    return {"errors": e.errors()}, 400
```

## Allowlist Validation

```python
def validate_sort_column(column: str) -> str:
    allowed = ['name', 'email', 'created_at']
    if column not in allowed:
        raise ValueError("Invalid sort column")
    return column

def validate_status(status: str) -> str:
    allowed = ['pending', 'active', 'completed']
    if status not in allowed:
        raise ValueError(f"Status must be one of: {allowed}")
    return status
```

## SQL Injection Prevention

```python
# BAD - String concatenation
query = f"SELECT * FROM users WHERE email = '{email}'"

# GOOD - Parameterized queries
query = "SELECT * FROM users WHERE email = %s"
cursor.execute(query, (email,))

# GOOD - ORM
user = User.query.filter_by(email=email).first()
```

## XSS Prevention

```python
from markupsafe import escape

# Escape HTML in user content
safe_content = escape(user_input)

# In templates (Jinja2 auto-escapes)
{{ user.name }}  # Auto-escaped
{{ user.bio | safe }}  # Explicitly mark as safe (dangerous!)
```

```typescript
// React auto-escapes by default
<div>{userInput}</div>  // Safe

// Dangerous - avoid unless necessary
<div dangerouslySetInnerHTML={{ __html: userInput }} />
```

## Command Injection Prevention

```python
import subprocess

# BAD - shell=True with user input
subprocess.run(f"cat {filename}", shell=True)

# GOOD - Use list arguments
subprocess.run(["cat", filename], shell=False)

# GOOD - Validate allowed commands
ALLOWED_COMMANDS = ['ls', 'cat', 'head']
if command not in ALLOWED_COMMANDS:
    raise ValueError("Command not allowed")
```

## Path Traversal Prevention

```python
import os

def safe_join(base_dir: str, user_path: str) -> str:
    """Safely join paths, preventing traversal."""
    # Resolve absolute path
    full_path = os.path.realpath(os.path.join(base_dir, user_path))

    # Ensure it's within base directory
    if not full_path.startswith(os.path.realpath(base_dir)):
        raise ValueError("Path traversal detected")

    return full_path

# Usage
safe_path = safe_join("/uploads", "../../../etc/passwd")  # Raises!
```

## File Upload Validation

```python
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_upload(file) -> bool:
    # Check extension
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Extension not allowed: {ext}")

    # Check file size
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset
    if size > MAX_FILE_SIZE:
        raise ValueError("File too large")

    # Check magic bytes (content type)
    header = file.read(8)
    file.seek(0)
    if not is_valid_image_header(header):
        raise ValueError("Invalid file content")

    return True
```

## Security Headers

```python
@app.after_request
def set_security_headers(response):
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000'
    return response
```

## Checklist

- [ ] All input validated before use
- [ ] SQL uses parameterized queries
- [ ] HTML output escaped
- [ ] File uploads validated (type, size, content)
- [ ] Paths validated against traversal
- [ ] Commands use allowlists
- [ ] Security headers set
