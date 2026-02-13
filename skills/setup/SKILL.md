---
description: Configure the frosty plugin for your project
---

# Frosty Plugin Setup

Help the user configure the frosty plugin for their project.

## What This Skill Does

1. **Check current configuration** - Look for existing `.env.local` in the user's project
2. **Identify needed features** - Ask what plugin features they want to use
3. **Create/update configuration** - Generate `.env.local` with required variables
4. **Validate setup** - Verify the configuration works

## Configuration Groups

### 1. Production Deployment (`/deploy`, `/health-check`, `/logs`)

Required variables:
```bash
PRODUCTION_DOMAIN=your-domain.example.com
PRODUCTION_SERVER_IP=123.45.67.89
```

Optional variables:
```bash
APP_NAME=my-app
SSH_USER=root
SSH_KEY_NAME=server_key
COMPOSE_PROJECT=deployment
```

### 2. GitHub Integration (PR workflows, /push)

Required variables:
```bash
REPO_ORIGIN_URL=https://github.com/username/repo.git
REPO_ORIGIN_PAT=ghp_xxxxxxxxxxxxxxxxxxxx
```

Legacy variable (still supported):
```bash
GITHUB_PAT=ghp_xxxxxxxxxxxxxxxxxxxx
```

### 3. Worktree Management (`/tree`)

No environment variables required - works out of the box.

## Setup Process

When the user runs `/setup`:

1. **Check for existing config:**
   ```bash
   cat .env.local 2>/dev/null || echo "No .env.local found"
   ```

2. **Ask which features they need:**
   - Production deployment (SSH to server, deploy, logs)
   - GitHub integration (PR collaboration)
   - Worktree management (no config needed)

3. **For Production Deployment, ask:**
   - What is your production domain?
   - What is your server's IP address?
   - What SSH key name do you use? (default: server_key)
   - What is your app name? (default: my-app)

4. **For GitHub Integration, ask:**
   - Do you have a GitHub Personal Access Token?
   - Guide them to create one if not: https://github.com/settings/tokens

5. **Create `.env.local`:**
   - Generate the file with their values
   - Ensure it's in `.gitignore`

6. **Validate:**
   - For production: Test SSH connection if possible
   - For GitHub: Verify PAT has correct scopes

## Example Output

```
Frosty Plugin Setup

Checking existing configuration...
No .env.local found.

Which features do you want to configure?
1. Production Deployment (SSH, deploy, logs)
2. GitHub Integration (PR workflows)
3. Worktree Management (no config needed)

Selected: Production Deployment

Production Domain: example.com
Server IP: 123.45.67.89
SSH Key Name [server_key]:
App Name [my-app]: myproject

Created .env.local with:
  PRODUCTION_DOMAIN=example.com
  PRODUCTION_SERVER_IP=123.45.67.89
  SSH_KEY_NAME=server_key
  APP_NAME=myproject

Verified .env.local is in .gitignore.

Setup complete! You can now use /deploy, /health-check, and /logs.
```

## Important Notes

- Never commit `.env.local` - it contains secrets
- The plugin's `.env.example` shows all available options
- Users can also set these as system environment variables
