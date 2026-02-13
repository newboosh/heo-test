---
name: standards-lookup
description: Canonical standards reference for Context Agent and QA Agent. Checks project-standards.yaml first, then falls back to defaults. Ensures both agents give consistent answers.
---

# Standards Lookup

Single source of truth for project standards. Both **Context Agent** and **QA Agent** use this to ensure consistent answers.

## Lookup Procedure

```
1. Read .claude/project-standards.yaml
   │
   ├─► If standard specified → Use project choice
   │
   └─► If not specified → Use default from standards/*.md
```

## Project Config Location

```
.claude/project-standards.yaml
```

## Config Structure

```yaml
diagrams:
  dfd: yourdon-demarco | gane-sarson
  erd: crows-foot | chen | idef1x
  sequence: uml-2.5
  flowchart: iso-5807
  architecture: c4

documentation:
  docstrings: google | numpy | sphinx
  adr: adr | madr
  changelog: keep-a-changelog

api:
  response_format: standard | jsonapi
  error_format: rfc-7807 | custom
  datetime: iso-8601

code:
  python_style: pep8
  type_annotations: required | optional
  error_handling: lbyl | eafp

testing:
  framework: pytest
  structure: aaa
  e2e_framework: playwright | selenium | cypress

vcs:
  commit_format: conventional-commits | angular
```

---

## Quick Reference (Defaults)

| Work Type | Default Standard | Reference |
|-----------|------------------|-----------|
| Data Flow Diagram | Yourdon-DeMarco | DeMarco, 1979 |
| Sequence Diagram | UML 2.5 | OMG formal/2017-12-05 |
| ERD | Crow's Foot (IE) | Martin, 1990 |
| Flowchart | ISO 5807:1985 | ISO 5807:1985 |
| Architecture | C4 Model | c4model.com |
| Unit Tests | pytest + AAA | xUnit Patterns |
| E2E Tests | Playwright + POM | Playwright docs |
| Docstrings | Google style | PEP 257 |
| REST API | REST conventions | RFC 7231 |
| API Response | JSON + RFC 7807 | RFC 7807 |
| Dates/Times | ISO 8601 | RFC 3339 |
| Python Style | PEP 8 | peps.python.org |
| Type Annotations | PEP 484/604 | peps.python.org |
| Commit Messages | Conventional Commits | conventionalcommits.org |

---

## Standards Documents

| Document | Contents |
|----------|----------|
| `standards/diagram_standards.md` | DFD, Sequence, ERD, State, Flowchart, Architecture |
| `standards/testing_standards.md` | Unit, Integration, E2E, Test Data, CI |
| `standards/documentation_standards.md` | Docstrings, Comments, README, ADR, Changelog |
| `standards/api_standards.md` | REST, Response Format, Status Codes, Pagination |
| `standards/code_style_standards.md` | Python Style, Types, Error Handling |
| `standards/conventional_commits_full_spec.md` | Commit Message Format |

---

## Usage by Agents

### Context Agent (Before Work)
1. Read `.claude/project-standards.yaml`
2. Identify work type from task description
3. Look up project's chosen standard (or default)
4. Read full standard from `standards/`
5. Include in context briefing

### QA Agent (After Work)
1. Read `.claude/project-standards.yaml`
2. Identify what was produced
3. Look up project's chosen standard (or default)
4. Verify against standard
5. Report violations with standard reference

---

## Empty State Handling

**If project-standards.yaml not found:**
```markdown
**Note:** No `.claude/project-standards.yaml` found. Using defaults.
Consider creating this file to customize standards for your project.
```

**If standard not found:**
```markdown
**Standard:** [query]
**Status:** No specific standard found

**Recommendation:**
- Check if query matches a known work type (see Quick Reference)
- For custom standards, add to `.claude/project-standards.yaml`
- Default general practices apply
```

---

## Skill Dependency Graph

```
standards-lookup (this skill)
    ↑
    ├── context-agent (reads standards before work)
    ├── qa-agent (verifies against standards after work)
    ├── compliance-check (detailed standard verification)
    └── gather-docs (includes applicable standards)
```

This skill is a **leaf dependency** - it does not invoke other skills.

---

**Both agents must check project-standards.yaml first to respect project choices.**
