# Security Guidelines

## Mandatory Security Checks

Before ANY commit, verify:

- [ ] No hardcoded secrets (API keys, passwords, tokens)
- [ ] All user inputs validated
- [ ] SQL injection prevention (parameterized queries/ORM)
- [ ] XSS prevention (template auto-escaping enabled)
- [ ] CSRF protection enabled
- [ ] Authentication/authorization verified
- [ ] Rate limiting on public endpoints
- [ ] Error messages don't leak sensitive data

## Secret Management

### Never Hardcode Secrets

```python
# WRONG: Hardcoded secret
API_KEY = "sk-proj-xxxxx"
DATABASE_URL = "postgresql://user:password@localhost/db"

# CORRECT: Environment variables
import os

API_KEY = os.environ.get("OPENAI_API_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")

if not API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set")
```

### Use .env Files Properly

```bash
# .env (NEVER commit this file)
OPENAI_API_KEY=sk-proj-xxxxx
DATABASE_URL=postgresql://user:password@localhost/db
SECRET_KEY=your-secret-key-here

# .env.example (commit this as template)
OPENAI_API_KEY=your-openai-api-key
DATABASE_URL=postgresql://user:password@localhost/db
SECRET_KEY=generate-a-secure-key
```

### Verify .gitignore

```gitignore
# Security - MUST be ignored
.env
.env.local
.env.*.local
*.pem
*.key
credentials.json
secrets.yaml
```

## Input Validation

### Use Pydantic for Validation

```python
from pydantic import BaseModel, EmailStr, conint, validator

class UserCreate(BaseModel):
    email: EmailStr
    age: conint(ge=0, le=150)
    username: str

    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError('username must be alphanumeric')
        return v

# Usage
try:
    user_data = UserCreate(**request.json)
except ValidationError as e:
    return {"error": e.errors()}, 400
```

### Sanitize All User Input

```python
import bleach

def sanitize_html(content: str) -> str:
    """Remove dangerous HTML tags, keep safe formatting."""
    allowed_tags = ['p', 'br', 'strong', 'em', 'ul', 'ol', 'li']
    return bleach.clean(content, tags=allowed_tags, strip=True)
```

## SQL Injection Prevention

### Always Use Parameterized Queries

```python
# WRONG: String formatting (SQL injection vulnerable)
query = f"SELECT * FROM users WHERE email = '{email}'"
db.execute(query)

# CORRECT: Parameterized query
query = "SELECT * FROM users WHERE email = :email"
db.execute(query, {"email": email})

# CORRECT: SQLAlchemy ORM (automatically parameterized)
user = User.query.filter_by(email=email).first()
```

## Authentication & Authorization

### Verify Authentication on Every Request

```python
from functools import wraps
from flask import request, jsonify

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Missing authorization"}), 401

        user = verify_token(token)
        if not user:
            return jsonify({"error": "Invalid token"}), 401

        return f(user=user, *args, **kwargs)
    return decorated
```

### Check Authorization for Resources

```python
@app.route("/api/documents/<int:doc_id>")
@require_auth
def get_document(user, doc_id):
    document = Document.query.get_or_404(doc_id)

    # ALWAYS verify ownership/permission
    if document.owner_id != user.id and not user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    return jsonify(document.to_dict())
```

## Error Handling

### Don't Leak Sensitive Information

```python
# WRONG: Leaks internal details
@app.errorhandler(Exception)
def handle_error(e):
    return jsonify({
        "error": str(e),
        "traceback": traceback.format_exc()  # NEVER in production
    }), 500

# CORRECT: Generic message, log details internally
@app.errorhandler(Exception)
def handle_error(e):
    app.logger.error(f"Unhandled exception: {e}", exc_info=True)
    return jsonify({
        "error": "An internal error occurred"
    }), 500
```

## Security Response Protocol

If a security issue is found:

1. **STOP** - Do not continue with other tasks
2. **ASSESS** - Use **security-reviewer** agent to evaluate severity
3. **FIX** - Address CRITICAL issues immediately
4. **ROTATE** - If secrets were exposed:
   - Revoke compromised credentials
   - Generate new secrets
   - Update environment variables
   - Audit access logs
5. **REVIEW** - Search codebase for similar vulnerabilities
6. **DOCUMENT** - Record the issue and fix for future reference

## Security Checklist for PRs

Before creating a PR:

- [ ] No secrets in code or commits
- [ ] All inputs validated
- [ ] Authentication checked
- [ ] Authorization verified
- [ ] Error messages are safe
- [ ] Dependencies are up to date
- [ ] Security headers configured (CSP, HSTS, etc.)
- [ ] Ran `bandit` security scanner
