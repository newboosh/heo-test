---
name: security-review
description: Use this skill when adding authentication, handling user input, working with secrets, creating API endpoints, or implementing sensitive features. Provides comprehensive security checklist for Flask applications.
---

# Security Review Skill

This skill ensures all code follows security best practices and identifies potential vulnerabilities in Flask applications.

## When to Activate

- Implementing authentication or authorization
- Handling user input or file uploads
- Creating new API endpoints
- Working with secrets or credentials
- Implementing payment features
- Storing or transmitting sensitive data
- Integrating third-party APIs

## Security Checklist

### 1. Secrets Management

#### NEVER Do This
```python
api_key = "sk-proj-xxxxx"  # Hardcoded secret
db_password = "password123"  # In source code
```

#### ALWAYS Do This
```python
import os

api_key = os.environ.get('OPENAI_API_KEY')
db_url = os.environ.get('DATABASE_URL')

# Verify secrets exist
if api_key is None:
    raise RuntimeError('OPENAI_API_KEY not configured')
```

#### Verification Steps
- [ ] No hardcoded API keys, tokens, or passwords
- [ ] All secrets in environment variables
- [ ] `.env` and `.env.local` in .gitignore
- [ ] No secrets in git history
- [ ] Production secrets in hosting platform

### 2. Input Validation

#### Always Validate User Input
```python
from marshmallow import Schema, fields, validate, ValidationError

class CreateUserSchema(Schema):
    email = fields.Email(required=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    age = fields.Int(validate=validate.Range(min=0, max=150))

def create_user():
    schema = CreateUserSchema()
    try:
        data = schema.load(request.get_json())
        return UserService.create(data)
    except ValidationError as err:
        return jsonify({'success': False, 'errors': err.messages}), 400
```

#### File Upload Validation
```python
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def validate_file_upload(file):
    # Size check
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)

    if size > MAX_FILE_SIZE:
        raise ValueError('File too large (max 5MB)')

    # Extension check
    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError('Invalid file type')

    # Content type check
    allowed_mimes = {'image/jpeg', 'image/png', 'image/gif'}
    if file.content_type not in allowed_mimes:
        raise ValueError('Invalid content type')

    return True
```

#### Verification Steps
- [ ] All user inputs validated with schemas
- [ ] File uploads restricted (size, type, extension)
- [ ] No direct use of user input in queries
- [ ] Whitelist validation (not blacklist)
- [ ] Error messages don't leak sensitive info

### 3. SQL Injection Prevention

#### NEVER Concatenate SQL
```python
# DANGEROUS - SQL Injection vulnerability
query = f"SELECT * FROM users WHERE email = '{user_email}'"
db.execute(query)
```

#### ALWAYS Use Parameterized Queries
```python
# Safe - SQLAlchemy ORM
user = User.query.filter_by(email=user_email).first()

# Safe - parameterized query
result = db.session.execute(
    text("SELECT * FROM users WHERE email = :email"),
    {"email": user_email}
)
```

#### Verification Steps
- [ ] All database queries use parameterized queries
- [ ] No string concatenation in SQL
- [ ] SQLAlchemy ORM used correctly
- [ ] Raw SQL uses text() with parameters

### 4. Authentication & Authorization

#### Password Handling
```python
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    password_hash = db.Column(db.String(256))

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
```

#### Session Security
```python
# In Flask config
SESSION_COOKIE_SECURE = True  # HTTPS only
SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
```

#### Authorization Checks
```python
from functools import wraps
from flask import g, jsonify

def require_role(role: str):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if g.current_user is None:
                return jsonify({'error': 'Unauthorized'}), 401

            if g.current_user.role != role:
                return jsonify({'error': 'Forbidden'}), 403

            return f(*args, **kwargs)
        return decorated
    return decorator

@bp.route('/admin/users', methods=['DELETE'])
@require_role('admin')
def delete_user(user_id: int):
    # Only admins can reach here
    pass
```

#### Verification Steps
- [ ] Passwords hashed with strong algorithm (bcrypt/argon2)
- [ ] Session cookies secure, httpOnly, sameSite
- [ ] Authorization checks before sensitive operations
- [ ] Role-based access control implemented
- [ ] Session timeout configured

### 5. XSS Prevention

#### Sanitize User Content
```python
import bleach

ALLOWED_TAGS = ['b', 'i', 'em', 'strong', 'p', 'br']
ALLOWED_ATTRIBUTES = {}

def sanitize_html(content: str) -> str:
    return bleach.clean(
        content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )

# In template, use |safe only after sanitizing
# {{ content|safe }}  # Only if content was sanitized
```

#### Content Security Policy
```python
from flask_talisman import Talisman

csp = {
    'default-src': "'self'",
    'script-src': "'self'",
    'style-src': "'self' 'unsafe-inline'",
    'img-src': "'self' data: https:",
}

Talisman(app, content_security_policy=csp)
```

#### Verification Steps
- [ ] User-provided HTML sanitized with bleach
- [ ] CSP headers configured
- [ ] Jinja2 auto-escaping enabled (default)
- [ ] |safe filter used only on sanitized content

### 6. CSRF Protection

```python
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)

# In templates
<form method="post">
    {{ csrf_token() }}
    ...
</form>

# For AJAX
<script>
const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
fetch('/api/endpoint', {
    method: 'POST',
    headers: {
        'X-CSRFToken': csrfToken
    }
});
</script>
```

#### Verification Steps
- [ ] CSRF protection enabled globally
- [ ] CSRF tokens on all state-changing forms
- [ ] AJAX requests include CSRF token

### 7. Rate Limiting

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per minute"]
)

@bp.route('/api/search')
@limiter.limit("10 per minute")
def search():
    # Expensive operation with stricter limit
    pass

@bp.route('/auth/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    # Prevent brute force
    pass
```

#### Verification Steps
- [ ] Rate limiting on all API endpoints
- [ ] Stricter limits on expensive operations
- [ ] Stricter limits on auth endpoints
- [ ] IP-based rate limiting

### 8. Sensitive Data Exposure

#### Logging
```python
# WRONG: Logging sensitive data
app.logger.info(f'User login: {email}, password: {password}')

# CORRECT: Redact sensitive data
app.logger.info(f'User login: {email}')
```

#### Error Messages
```python
# WRONG: Exposing internal details
@app.errorhandler(Exception)
def handle_error(error):
    return jsonify({
        'error': str(error),
        'traceback': traceback.format_exc()
    }), 500

# CORRECT: Generic error messages
@app.errorhandler(Exception)
def handle_error(error):
    app.logger.exception('Internal error')
    return jsonify({
        'error': 'An error occurred. Please try again.'
    }), 500
```

#### Verification Steps
- [ ] No passwords, tokens, or secrets in logs
- [ ] Error messages generic for users
- [ ] Detailed errors only in server logs
- [ ] No stack traces exposed to users

### 9. Dependency Security

```bash
# Check for vulnerabilities
pip-audit

# Or with safety
safety check

# Update dependencies
pip install --upgrade package-name

# Check for outdated packages
pip list --outdated
```

#### Verification Steps
- [ ] Dependencies up to date
- [ ] No known vulnerabilities (pip-audit clean)
- [ ] requirements.txt or poetry.lock committed
- [ ] Dependabot enabled on GitHub

## Security Tools

```bash
# Static analysis for security
bandit -r app/ -ll

# Check for hardcoded secrets
detect-secrets scan .

# Full security audit
pip-audit && bandit -r app/ -ll
```

## Pre-Deployment Security Checklist

Before ANY production deployment:

- [ ] **Secrets**: No hardcoded secrets, all in env vars
- [ ] **Input Validation**: All user inputs validated
- [ ] **SQL Injection**: All queries parameterized
- [ ] **XSS**: User content sanitized
- [ ] **CSRF**: Protection enabled
- [ ] **Authentication**: Secure password handling
- [ ] **Authorization**: Role checks in place
- [ ] **Rate Limiting**: Enabled on all endpoints
- [ ] **HTTPS**: Enforced in production
- [ ] **Security Headers**: CSP, X-Frame-Options configured
- [ ] **Error Handling**: No sensitive data in errors
- [ ] **Logging**: No sensitive data logged
- [ ] **Dependencies**: Up to date, no vulnerabilities

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security](https://flask.palletsprojects.com/en/latest/security/)
- [Flask-Talisman](https://github.com/GoogleCloudPlatform/flask-talisman)
- [Bandit](https://bandit.readthedocs.io/)

---

**Remember**: Security is not optional. One vulnerability can compromise the entire platform. When in doubt, err on the side of caution.
