## Security Scanning & Risk Acceptance

This project integrates automated security scanning into the CI pipeline:
- **Gitleaks** — scans full git history for leaked secrets/tokens on every push
- **Bandit** — static analysis of Python code (13 Low, 1 Medium findings, all reviewed and accepted — see notes below)
- **pip-audit** — dependency vulnerability scanning (0 known vulnerabilities found)
- **Trivy** — container image vulnerability scanning

### Trivy scan results & base image experiment
Initial scan on `python:3.10-slim` (Debian 13.5/Trixie): 164 vulnerabilities
(2 Critical, 18 High, 53 Medium, 63 Low, 28 Unknown).

Tested switching to `python:3.10-slim-bookworm` (Debian 12.15) expecting an
improvement, but this pinned an older, less-patched Debian base and
increased the count to 189 vulnerabilities (5 Critical, 18 High, 61 Medium,
93 Low, 12 Unknown). Reverted to `python:3.10-slim` (unpinned, tracks the
latest stable Debian release) as the better choice.

### Risk acceptance rationale
Remaining vulnerabilities originate entirely from base OS system packages
(apt, bash, bsdutils...), not from application code or Python dependencies
(0 vulnerabilities found via pip-audit). Accepted as low risk because:
- Container runs in an isolated local Vagrant VM, never exposed to internet
- No untrusted external users have access to container or host
- Most flagged CVEs require pre-existing local shell access to be exploitable
- All application-level dependencies show 0 known vulnerabilities

### Bandit findings rationale
- `B311 (random)`: used only for generating synthetic simulation data, not
  security-sensitive tokens or credentials — accepted as-is
- `B104 (bind 0.0.0.0)`: intentional, required for access from host machine
  to VM via private network (192.168.56.10) — accepted for this dev/lab context
- `B603/B607 (subprocess)`: fixed by using `sys.executable` instead of
  relying on PATH resolution, eliminating potential PATH hijacking risk
