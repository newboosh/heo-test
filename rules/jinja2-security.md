# Jinja2 Template Security Rules

Rules for secure Jinja2 template development in Flask applications.

## Critical Rules

### 1. Never Disable Auto-Escaping
```html
<!-- NEVER do this -->
{% autoescape false %}
  {{ user_content }}
{% endautoescape %}

<!-- Auto-escaping is ON by default - keep it that way -->
{{ user_content }}  <!-- Automatically escaped -->
```

### 2. Sanitize Before Using |safe Filter
The `|safe` filter marks content as safe HTML and BYPASSES auto-escaping.

```python
# In Python - sanitize BEFORE passing to template
import bleach

ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'blockquote']
ALLOWED_ATTRIBUTES = {}

def sanitize_html(content: str) -> str:
    return bleach.clean(
        content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )

# Pass sanitized content to template
return render_template('article.html', content=sanitize_html(article.content))
```

```html
<!-- In template - only use |safe on pre-sanitized content -->
{{ content|safe }}  <!-- OK because sanitized in Python -->
```

### 3. Always Use CSP Nonce for Inline Scripts/Styles
```html
<!-- CORRECT: Use nonce for inline content -->
<style nonce="{{ csp_nonce }}">
    .my-class { color: blue; }
</style>

<script nonce="{{ csp_nonce }}">
    // Inline JavaScript
</script>

<!-- WRONG: No nonce -->
<style>
    .my-class { color: blue; }
</style>
```

### 4. Never Construct JavaScript with User Data
```html
<!-- DANGEROUS: XSS via JavaScript context -->
<script>
    var userId = {{ user.id }};  <!-- OK for numbers -->
    var userName = "{{ user.name }}";  <!-- DANGEROUS! -->
</script>

<!-- SAFE: Use data attributes -->
<div id="app" data-user-id="{{ user.id }}" data-user-name="{{ user.name|e }}">
</div>
<script nonce="{{ csp_nonce }}">
    const app = document.getElementById('app');
    const userId = app.dataset.userId;
    const userName = app.dataset.userName;
</script>

<!-- SAFE: Use JSON filter for complex data -->
<script nonce="{{ csp_nonce }}">
    const config = {{ config|tojson|safe }};
</script>
```

### 5. Escape URL Parameters
```html
<!-- Use |urlencode for URL parameters -->
<a href="/search?q={{ query|urlencode }}">Search</a>

<!-- Use url_for for Flask routes -->
<a href="{{ url_for('search', q=query) }}">Search</a>
```

## Template Best Practices

### Use Template Inheritance
```html
<!-- base.html -->
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}{% endblock %}</title>
    {% block extra_css %}{% endblock %}
</head>
<body>
    {% block content %}{% endblock %}
    {% block extra_js %}{% endblock %}
</body>
</html>

<!-- page.html -->
{% extends "base.html" %}

{% block title %}My Page{% endblock %}

{% block content %}
    <h1>Hello World</h1>
{% endblock %}
```

### Use Macros for Reusable Components
```html
<!-- macros/forms.html -->
{% macro input(name, label, type='text', value='', required=false) %}
<div class="form-group">
    <label for="{{ name }}">{{ label }}</label>
    <input type="{{ type }}"
           name="{{ name }}"
           id="{{ name }}"
           value="{{ value }}"
           {% if required %}required{% endif %}>
</div>
{% endmacro %}

<!-- In templates -->
{% from "macros/forms.html" import input %}
{{ input('email', 'Email Address', type='email', required=true) }}
```

### Include CSRF Token in Forms
```html
<form method="post">
    {{ csrf_token() }}
    <!-- form fields -->
    <button type="submit">Submit</button>
</form>
```

## Dangerous Patterns to Avoid

| Pattern | Risk | Fix |
|---------|------|-----|
| `{{ user_input\|safe }}` | XSS | Sanitize with bleach first |
| `{% autoescape false %}` | XSS | Keep auto-escape on |
| `<script>var x = "{{ data }}"</script>` | XSS | Use data attributes or tojson |
| `<a href="{{ url }}">` | XSS | Validate URL scheme |
| `{% include user_input %}` | Template injection | Never include user input |
| `{{ data\|e\|safe }}` | Confusing, potential XSS | Just use `{{ data }}` |

## Linting Commands

```bash
# Check for |safe usage
grep -rn "|safe" app/templates/ --include="*.html"

# Check for autoescape false
grep -rn "autoescape false" app/templates/ --include="*.html"

# Check for inline scripts without nonce
grep -rn "<script>" app/templates/ --include="*.html" | grep -v "nonce="

# Check for inline styles without nonce
grep -rn "<style>" app/templates/ --include="*.html" | grep -v "nonce="
```

## Template Security Checklist

Before committing template changes:

- [ ] No new `|safe` usage without sanitization
- [ ] No `{% autoescape false %}`
- [ ] All inline `<script>` tags have `nonce="{{ csp_nonce }}"`
- [ ] All inline `<style>` tags have `nonce="{{ csp_nonce }}"`
- [ ] User data in JavaScript uses `|tojson` or data attributes
- [ ] Forms include CSRF token
- [ ] URLs use `url_for()` or `|urlencode`
- [ ] No user input in `{% include %}` statements
