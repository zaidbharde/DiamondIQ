# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please do **not** open a public issue.

Instead, send a private report to the repository maintainer via GitHub's **Security Advisories** tab at:

https://github.com/zaidbharde/DiamondIQ/security/advisories

You should receive a response within 48 hours. If you do not, please follow up.

## What to Include

- Type of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (optional)

## What We Promise

- Acknowledge receipt within 48 hours
- Provide an estimated timeline for a fix
- Credit you in the release notes (unless you prefer anonymity)

## Security Practices

### API Keys and Secrets
- All API keys are loaded from `.env` file (never committed)
- `.env` is in `.gitignore`
- Use `AI_PROVIDER=auto` to let the app select the best available key

### Data Protection
- No user data is sent to external servers except AI vision API calls
- Prediction data is stored locally in SQLite
- Uploaded certificate images are deleted immediately after processing

### Web Security
- CSRF tokens on all state-changing requests
- Rate limiting (configurable, default 30 req/min)
- Security headers (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy)
- Input sanitization via `markupsafe.escape`

### Safe Uploads
- File type validation (whitelist approach)
- File size limits
- Temporary files cleaned up in `finally` blocks
- UUID-based filenames to prevent path traversal
