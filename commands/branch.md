# Branch Helper

Create and validate branch names following `<type>/<scope>/<description>` convention.

> **Canonical reference:** `.claude/rules/git-naming.md`

## Usage
- `/branch` - Show current branch and validate
- `/branch <description>` - Suggest branch name based on description
- `/branch create <type>/<scope>/<name>` - Create branch with validation

---

## Branch Format

```
<type>/<scope>/<description>
```

### Types

`feat` `fix` `docs` `refactor` `test` `chore` `perf` `ci` `style` `build` `revert`

| Type | Keywords to detect |
|------|-------------------|
| `feat` | add, new, implement, create |
| `fix` | fix, bug, error, crash, issue |
| `docs` | doc, readme, guide, comment |
| `refactor` | refactor, restructure, clean, reorganize |
| `test` | test, spec, e2e, unit |
| `chore` | update, upgrade, deps, maintenance |
| `perf` | fast, slow, optimize, cache, perf |
| `ci` | ci, cd, workflow, action, pipeline |

### Scopes

**Modules:** `ai` `analytics` `cache` `content` `core` `dashboard` `db` `email` `input` `integration` `links` `observability` `output` `realtime` `resilience` `scheduling` `scraping` `security` `storage` `users` `prefs` `utils` `workflow`

**Meta:** `deps` `config` `ci` `docker` `scripts` `api` `auth` `migrations` `frontend` `tests`

| Scope | Keywords to detect |
|-------|-------------------|
| `ai` | ai, gemini, llm, analysis |
| `dashboard` | dashboard, ui, frontend |
| `db` | database, model, query, schema |
| `content` | content, resume, cover, template |
| `email` | email, gmail, smtp |
| `scraping` | scrape, scraping, jobs |
| `storage` | storage, s3, gcs, files |
| `users` | user, account |
| `prefs` | preferences, settings |
| `deps` | deps, package, requirement |
| `config` | config, env, settings |
| `api` | api, endpoint, route |

## Instructions

### When showing current branch (`/branch`):

1. Get current branch: `git branch --show-current`
2. Parse into type/scope/description
3. Validate each segment
4. Report validation status

### When suggesting a name (`/branch <description>`):

1. Analyze description for type keywords
2. Analyze description for scope keywords
3. Generate kebab-case description
4. Output: `<type>/<scope>/<description>`

### When creating (`/branch create <branch-name>`):

1. Validate format: must be `type/scope/description`
2. Validate type is in allowed list
3. Validate scope is in allowed list
4. Check branch doesn't exist
5. Create: `git checkout -b <branch-name>`

## Examples

```
/branch "add user preferences to dashboard"
→ feat/dashboard/user-preferences

/branch "fix null pointer in database seeds"
→ fix/db/null-pointer-seeds

/branch "upgrade flask dependency"
→ chore/deps/upgrade-flask

/branch "improve cache performance"
→ perf/cache/optimization

/branch "add e2e tests for ai analysis"
→ test/ai/e2e-analysis
```

## Validation Output

```
Current branch: fix/dashboard/null-handling

✓ Type 'fix' is valid
✓ Scope 'dashboard' maps to modules/dashboard
✓ Description 'null-handling' follows conventions

Branch name is valid!
```

$ARGUMENTS
