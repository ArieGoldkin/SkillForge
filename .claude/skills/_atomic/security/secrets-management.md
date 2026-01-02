---
name: secrets-management
description: Secrets detection, environment variables, credential management
version: 1.0.0
tags: [security, secrets, credentials, env]
size: atomic
domain: security
---

# Secrets Management

## Never Hardcode Secrets

```python
# BAD - Hardcoded secrets
API_KEY = "sk-1234567890abcdef"
DATABASE_URL = "postgres://user:password@localhost/db"

# GOOD - Environment variables
import os
API_KEY = os.environ["API_KEY"]
DATABASE_URL = os.environ["DATABASE_URL"]
```

## Environment Variables

```bash
# .env (NEVER commit this file)
API_KEY=sk-1234567890abcdef
DATABASE_URL=postgres://user:password@localhost/db
SECRET_KEY=your-secret-key-here
```

```python
# Load with python-dotenv
from dotenv import load_dotenv
load_dotenv()

# Or pydantic-settings
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_key: str
    database_url: str
    secret_key: str

    class Config:
        env_file = ".env"

settings = Settings()
```

## .gitignore

```gitignore
# Secrets
.env
.env.local
.env.*.local
*.pem
*.key
credentials.json
secrets.yaml

# IDE
.idea/
.vscode/

# Dependencies
node_modules/
__pycache__/
```

## Secret Detection Tools

```bash
# TruffleHog - scan git history
trufflehog git file://. --json

# Gitleaks - fast secret scanner
gitleaks detect --source . --verbose

# Pre-commit hook
pip install detect-secrets
detect-secrets scan > .secrets.baseline
```

## Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

## Rotating Secrets

```python
# Support multiple keys during rotation
CURRENT_KEY = os.environ["API_KEY"]
PREVIOUS_KEY = os.environ.get("API_KEY_PREVIOUS")

def verify_api_key(key: str) -> bool:
    if key == CURRENT_KEY:
        return True
    if PREVIOUS_KEY and key == PREVIOUS_KEY:
        # Log deprecation warning
        logger.warning("Using deprecated API key")
        return True
    return False
```

## Secret Storage Options

| Option | Use Case | Security Level |
|--------|----------|----------------|
| Env vars | Local dev, simple apps | Basic |
| .env files | Local dev only | Basic |
| AWS Secrets Manager | Production AWS | High |
| HashiCorp Vault | Enterprise | Very High |
| 1Password/Doppler | Team secrets | High |

## AWS Secrets Manager

```python
import boto3
import json

def get_secret(secret_name: str) -> dict:
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# Usage
secrets = get_secret("prod/myapp/credentials")
db_password = secrets["db_password"]
```

## Common Mistakes

```python
# BAD - Logging secrets
logger.info(f"Connecting with key: {api_key}")

# BAD - Error messages with secrets
raise Exception(f"Auth failed for key {api_key}")

# BAD - Committing .env
# Always add .env to .gitignore FIRST

# BAD - Secrets in URLs
url = f"https://user:{password}@example.com"  # Visible in logs!
```

## Checklist

- [ ] No hardcoded secrets in code
- [ ] .env in .gitignore
- [ ] Secret detection in CI/CD
- [ ] Pre-commit hooks for secrets
- [ ] Secrets rotated regularly
- [ ] Separate secrets per environment
- [ ] Audit log for secret access
