---
name: cicd-pipeline
description: CI/CD pipeline stages, caching, and artifacts
version: 1.0.0
tags: [cicd, github-actions, pipeline, automation]
size: atomic
domain: devops
---

# CI/CD Pipeline

## Pipeline Stages

```
Code ──▶ Build ──▶ Test ──▶ Scan ──▶ Deploy
  │        │        │        │         │
  ▼        ▼        ▼        ▼         ▼
Triggers Artifacts Reports  Vulns   Monitoring
```

### GitHub Actions Example

```yaml
name: CI/CD
on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Cache Dependencies
        uses: actions/cache@v4
        with:
          path: ~/.npm
          key: ${{ runner.os }}-npm-${{ hashFiles('**/package-lock.json') }}

      - run: npm ci
      - run: npm run lint
      - run: npm run test -- --coverage

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          severity: 'CRITICAL,HIGH'

  deploy:
    needs: [lint-and-test, security-scan]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - run: ./deploy.sh
```

## Caching Strategy

```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.npm
      node_modules
      backend/.venv
    key: ${{ runner.os }}-deps-${{ hashFiles('**/package-lock.json', '**/poetry.lock') }}
    restore-keys: |
      ${{ runner.os }}-deps-
```

**Impact**: 2-3 min → 10-20 sec (~85% savings)

## Artifact Management

```yaml
- name: Upload Build
  uses: actions/upload-artifact@v4
  with:
    name: build-${{ github.sha }}
    path: dist/
    retention-days: 7

- name: Download Build
  uses: actions/download-artifact@v4
  with:
    name: build-${{ github.sha }}
```

## Matrix Testing

```yaml
strategy:
  matrix:
    node: [18, 20, 22]
    os: [ubuntu-latest, windows-latest]
```
