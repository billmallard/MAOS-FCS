# Security Policy

This repository is public. Treat all commits as permanently public data.

## Supported Branches

- `main`
- `develop`

## Reporting a Vulnerability

If you discover a security issue, do not open a public issue with exploit details.

Use one of the following:

- GitHub Security Advisories (preferred)
- Direct contact with the repository owner

Include:

- Affected files/paths
- Reproduction steps
- Impact and severity assessment
- Suggested remediation

## Secret Management Rules

- Never commit credentials, API keys, private keys, certificates, or tokens.
- Use environment variables or local secret stores for development values.
- Keep secret-bearing files out of git history and add local ignore rules as needed.

## Scanning in This Repository

### GitHub Actions (server-side)

- CodeQL SAST runs on pushes, pull requests, and weekly schedule.
- Gitleaks secret scanning runs on pushes, pull requests, and weekly schedule.

### Local pre-commit (developer-side)

Install and enable pre-commit hooks:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

Notes:

- Local hook implementation is in `tools/security/scan_secrets.py`.
- The hook is configured as `language: system` to avoid platform-specific virtualenv bootstrap failures.

## Recommended GitHub Repository Settings

Enable these in repository settings if not already enabled:

- Secret scanning
- Push protection for secrets
- Dependabot alerts
- Dependabot security updates

## If a Secret Is Accidentally Committed

1. Revoke/rotate the secret immediately at the provider.
2. Remove secret from repository files.
3. Rewrite git history to purge the secret.
4. Force-push rewritten history and notify collaborators.
5. Validate with secret scanning before resuming normal work.
