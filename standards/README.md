# Project Standards

This directory contains all coding standards and conventions for this project.

## Standard Documents

| File | Purpose | Enforced By |
|------|---------|-------------|
| [DOCSTRING_STYLE.md](DOCSTRING_STYLE.md) | Google-style docstring format | `python -m scripts.intelligence lint docstrings` |
| [TEST_NAMING.md](TEST_NAMING.md) | Test function naming convention | Manual review + test mapper |
| [code_style_standards.md](code_style_standards.md) | Python code style (PEP 8 + extras) | `ruff`, `black` |
| [testing_standards.md](testing_standards.md) | Testing practices and pytest patterns | Manual review |
| [api_standards.md](api_standards.md) | REST API design conventions | Manual review |
| [documentation_standards.md](documentation_standards.md) | General documentation guidelines | Manual review |
| [diagram_standards.md](diagram_standards.md) | Diagram and visualization standards | Manual review |
| [conventional_commits_full_spec.md](conventional_commits_full_spec.md) | Commit message format | Git hooks |

## Meta-Standard: How to Write Standards

All standard documents in this directory **MUST** follow this format:

### Required Sections

1. **Title** - Clear, descriptive (e.g., "Docstring Style Standard")

2. **Summary** - One-paragraph overview of what this standard covers

3. **Rationale** - Why this standard exists (optional but recommended)

4. **Rules** or **Specification**
   - Clear, numbered or bulleted rules
   - Use "MUST", "SHOULD", "MAY" keywords (RFC 2119 style)
   - Include examples (good ✅ and bad ❌)

5. **Enforcement** - How compliance is checked:
   - Automated linting/tooling
   - Manual review
   - Pre-commit hooks
   - CI/CD checks

6. **Examples** - Real-world code examples demonstrating compliance

7. **References** (if applicable) - Links to external specs, PEPs, industry standards

### Optional Sections

- **Migration Guide** - How to adopt this standard in existing code
- **FAQ** - Common questions
- **Exceptions** - When it's OK to violate the standard

### Formatting Requirements

- Use Markdown
- Keep line length ≤ 100 characters for readability
- Use code fences with language tags (```python, ```yaml, etc.)
- Use tables for comparisons
- Use callouts for important notes:
  ```markdown
  > **Note**: Important clarification
  > **Warning**: Common pitfall
  ```

---

## Standard Keywords (RFC 2119)

Use these keywords consistently:

- **MUST** / **REQUIRED** - Absolute requirement
- **MUST NOT** - Absolute prohibition
- **SHOULD** / **RECOMMENDED** - Strong suggestion, exceptions possible
- **SHOULD NOT** - Strong discouragement
- **MAY** / **OPTIONAL** - Truly optional

Example:
```markdown
- Public functions **MUST** have docstrings
- Private functions **SHOULD** have docstrings if complex
- Test helper functions **MAY** omit docstrings
```

---

## Enforcement Matrix

| Standard | Tool | Pre-commit | CI/CD | Manual |
|----------|------|------------|-------|--------|
| Code Style | `ruff`, `black` | ✓ | ✓ | - |
| Docstrings | `intelligence lint` | ✓ | ✓ | - |
| Test Naming | - | - | ✓ (warning) | ✓ |
| Conventional Commits | `commitlint` | ✓ | - | - |
| API Design | - | - | - | ✓ |
| Documentation | `markdownlint` | ✓ | ✓ | ✓ |
| Diagrams | - | - | - | ✓ |
| Testing Practices | `pytest` | - | ✓ | ✓ |

**Legend**:
- ✓ = Enforced
- ✓ (warning) = Checked but doesn't block
- \- = Not enforced automatically

---

## Adding a New Standard

1. **Justify**: Why is this standard needed? What problem does it solve?

2. **Draft**: Write the standard following the meta-standard format

3. **Review**: Get feedback from team (or AI agent if solo)

4. **Automation**: If possible, create tooling to enforce it

5. **Document**: Add entry to this README

6. **Migrate**: Apply to existing codebase (if applicable)

---

## Updating Existing Standards

- Version standards if making breaking changes
- Add "Updated: YYYY-MM-DD" footer
- Document changes in commit message
- Update enforcement tooling if needed

---

## Conflict Resolution

If standards conflict:

1. **Specific beats general** - API standards override code style for API code
2. **Automated beats manual** - If a linter enforces it, that's the standard
3. **Industry standard beats custom** - PEP 8 > our preferences
4. **Explicit beats implicit** - Written standard > unwritten convention

If still unclear, open an issue for discussion.

---

## Compliance Checking

Run all automated checks:

```bash
# Code style
ruff check .
black --check .

# Docstrings
python -m scripts.intelligence lint docstrings

# Tests
pytest

# Docs
markdownlint docs/ standards/

# Commits (on pre-commit)
commitlint --from HEAD~1
```

---

## Standard Review Schedule

Standards should be reviewed:

- **Quarterly**: Check if standards are being followed
- **Annually**: Review if standards still make sense
- **On major changes**: When adopting new tools or paradigms

Add review notes to `standards/REVIEWS.md` (create if needed).

---

**Maintained By**: Intelligence System
**Last Updated**: 2026-02-02
**Version**: 1.0
