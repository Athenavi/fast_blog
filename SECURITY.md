# Security Policy

## 🔒 Supported Versions

| Version | Supported             |
|---------|-----------------------|
| 0.x.x   | ✅ Active support      |
| < 0.x   | ❌ No longer supported |

## 🐛 Reporting a Vulnerability

Please **do NOT** report security vulnerabilities through public GitHub issues.

Report via email to **[athenavi@qq.com](mailto:athenavi@qq.com)**.

You should receive a response within **48 hours**.

### What to Include

- Type of vulnerability (SQL injection, XSS, CSRF, etc.)
- Affected source files and location (tag/branch/commit)
- Steps to reproduce and proof-of-concept (if possible)
- Impact assessment

### Response Timeline

| Severity    | Timeline             |
|-------------|----------------------|
| 🔴 Critical | 24-48 hours          |
| 🟠 High     | 7 days               |
| 🟡 Medium   | 30 days              |
| 🟢 Low      | Next regular release |

### Safe Harbor

We support responsible disclosure and will not take legal action against good-faith researchers.

## 🛡️ Deployment Checklist

- [ ] Changed all default passwords and secret keys
- [ ] Set `DEBUG=False` in production
- [ ] Configured HTTPS with valid certificates (TLS 1.2+)
- [ ] Set up proper CORS allowed origins
- [ ] Enabled rate limiting in Nginx
- [ ] Enabled audit logging
- [ ] Configured automated backups
- [ ] Keep dependencies updated (`pip audit` + `npm audit`)

## 🔐 Built-in Security Features

- JWT authentication with refresh tokens
- Two-factor authentication (TOTP)
- RBAC role-based access control
- SQL injection prevention (SQLAlchemy ORM)
- XSS protection (output sanitization)
- Rate limiting (configurable per endpoint)
- Password hashing (bcrypt)
- Audit logging for sensitive operations
