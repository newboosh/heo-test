---
description: Restate requirements, assess risks, and create step-by-step implementation plan. WAIT for user CONFIRM before touching any code.
---

# Plan Command

This command invokes the **planner** agent to create a comprehensive implementation plan before writing any code.

## What This Command Does

1. **Restate Requirements** - Clarify what needs to be built
2. **Identify Risks** - Surface potential issues and blockers
3. **Create Step Plan** - Break down implementation into phases
4. **Wait for Confirmation** - MUST receive user approval before proceeding

## When to Use

Use `/plan` when:
- Starting a new feature
- Making significant architectural changes
- Working on complex refactoring
- Multiple files/components will be affected
- Requirements are unclear or ambiguous

## How It Works

The planner agent will:

1. **Analyze the request** and restate requirements in clear terms
2. **Break down into phases** with specific, actionable steps
3. **Identify dependencies** between components
4. **Assess risks** and potential blockers
5. **Estimate complexity** (High/Medium/Low)
6. **Present the plan** and WAIT for your explicit confirmation

## Example Usage

```
User: /plan I need to add email verification for new users

Agent (planner):
# Implementation Plan: Email Verification for New Users

## Requirements Restatement
- Send verification email when user registers
- Include unique verification link
- Verify link activates user account
- Handle expired links gracefully
- Prevent login until verified

## Affected Files
- app/models/user.py - Add verification fields
- app/services/email.py - Add verification email
- app/auth/routes.py - Add verify endpoint
- app/templates/email/verify.html - Email template
- tests/unit/test_user.py - Unit tests
- tests/integration/test_auth.py - Integration tests

## Implementation Phases

### Phase 1: Database & Models
1. Create Alembic migration for verification fields
   - `flask db migrate -m "Add email verification fields"`
2. Update User model with:
   - `is_verified: bool = False`
   - `verification_token: str`
   - `verification_sent_at: datetime`

### Phase 2: Email Service
3. Create verification email template
4. Add `send_verification_email()` to EmailService
5. Generate secure token with `secrets.token_urlsafe(32)`

### Phase 3: Routes & Logic
6. Update registration to send verification email
7. Add `/auth/verify/<token>` endpoint
8. Add login check for verified users

### Phase 4: Testing
9. Write unit tests for token generation/validation
10. Write integration tests for verification flow
11. Manual testing of full flow

## Risks
- MEDIUM: Email deliverability (SPF/DKIM required)
- LOW: Token expiration handling
- LOW: Resend verification logic

## Estimated Complexity: MEDIUM

**WAITING FOR CONFIRMATION**: Proceed with this plan? (yes/no/modify)
```

## Important Notes

**CRITICAL**: The planner agent will **NOT** write any code until you explicitly confirm the plan with "yes" or "proceed" or similar affirmative response.

If you want changes, respond with:
- "modify: [your changes]"
- "different approach: [alternative]"
- "skip phase 2 and do phase 3 first"

## Integration with Other Commands

After planning:
- Use `/tdd` to implement with test-driven development
- Use `/build-fix` if build errors occur
- Use `/code-review` to review completed implementation

## Related Agents

This command invokes the `planner` agent located at:
`.claude/agents/planner.md`
