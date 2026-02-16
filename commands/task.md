---
description: Start the 4-phase task workflow (Discovery -> PRD → Tasks → Execution)
---

# /task Command - Hybrid Workflow System

## Command Syntax

```text
/task [template] [instructions]
```

**Usage patterns:**
- `/task` - Interactive prompt for task description
- `/task [instructions]` - Direct task with default workflow
- `/task go [instructions]` - High-velocity workflow (autonomous)
- `/task slow [instructions]` - Methodical workflow (with user checkpoints)
- `/task communicate [instructions]` - Human-friendly documentation
- `/task analyze [instructions]` - Analysis without implementation
- `/task research [instructions]` - Research and evaluation

---

## Template Selection

### Default Workflow (No Template)
**When to use:** Standard feature implementation

**Workflow:**
1. Research phase (automatic)
2. PRD creation 
3. Task generation 
4. Execution

**References:**
- Discovery: `/.claude/templates/discovery/standard.mdc`
- PRD: `/.claude/templates/task-phases/create-prd.mdc`
- Tasks: `/.claude/templates/task-phases/generate-tasks.mdc`
- Execution: `/.claude/templates/task-phases/process-tasks.mdc`

---

### `go` - Autonomous Workflow (Minimize User Time)
**When to use:** User wants to minimize interruptions and work on other things

**Philosophy:** User's time is precious. Take whatever time needed for thorough work. Goal is to minimize user involvement, NOT to rush.

**Workflow:**
1. **Discovery (Thorough & Autonomous):** `/.claude/templates/discovery/standard.mdc`
   - Deep research and thinking
   - Avoid asking questions - use your best judgment
   - Only ask if absolutely critical

2. **PRD & Task Generation (Autonomous):** `/.claude/templates/task-phases/create-prd.mdc` + `/.claude/templates/task-phases/generate-tasks.mdc`
   - Generate parent + sub-tasks immediately (no "Go" checkpoint)
   - No user review required

3. **Implementation (Continuous):** `/.claude/templates/task-phases/process-tasks.mdc`
   - Execute all sub-tasks autonomously
   - No approval between sub-tasks
   - On errors/blockers find workarounds

**Workflow guide:** `/.claude/workflows/go-autonomous.mdc`

**Communication style:**
- Minimal status updates
- Focus on action over explanation
- Report only when complete or blocked

---

### `slow` - Methodical Workflow
**When to use:** Complex tasks, user wants involvement in decisions

**Workflow:**
1. **Discovery (Thorough):** `/.claude/templates/discovery/thorough.mdc`
   - Comprehensive search and analysis
   - Detailed clarifying questions
   - Multiple user review checkpoints:
     - Initial understanding confirmation
     - Discovery findings review
     - Question responses
     - Discovery summary approval

2. **PRD Creation (Collaborative):** `/.claude/templates/task-phases/create-prd.mdc`
   - Generate PRD
   - User reviews entire PRD
   - Wait for approval

3. **Task Generation (Reviewed):** `/.claude/templates/task-phases/generate-tasks.mdc`
   - Generate parent tasks → user review
   - Generate sub-tasks → user review entire task list
   - Wait for approval to proceed

4. **Implementation (Controlled):** `/.claude/templates/task-phases/process-tasks.mdc`
   - Execute ONE sub-task at a time
   - Pause after EACH sub-task for approval
   - Wait for commit approval after each parent task

**Workflow guide:** `/.claude/workflows/slow-methodical.mdc`

**Communication style:**
- Detailed explanations
- Transparent decision-making
- Educational and collaborative
- Patient pacing

---

### `communicate` - Human-Friendly Documentation
**When to use:** Creating reports, summaries, retrospectives for humans

**Purpose:** Generate engaging, narrative-driven documentation with personality

**Template guide:** `/.claude/templates/output-types/communicate.mdc`

**Output:**
- Story-driven narrative (not dry facts)
- Emotional authenticity and personality
- Visual elements (charts, progress bars, timelines)
- Emojis and conversational tone
- Before/after comparisons
- Celebrates wins and acknowledges challenges

**Examples:**
- Project status reports for stakeholders
- Sprint retrospectives
- Development journey documentation
- Milestone celebrations
- Non-technical summaries

**No implementation - documentation only**

---

### `analyze` - Deep Analysis Without Implementation
**When to use:** Understanding, evaluating, recommending (no coding)

**Purpose:** Comprehensive analysis with recommendations

**Template guide:** `/.claude/templates/output-types/analyze.mdc`

**Output:**
- Current state documentation
- Findings (strengths, weaknesses, opportunities, risks)
- Detailed analysis with evidence
- Comparative analysis
- Actionable recommendations
- Implementation roadmap (if extensive)

**Analysis types:**
- Performance analysis
- Security review
- Architecture assessment
- Code quality evaluation

**No implementation - analysis only**

---

### `research` - Technology Evaluation & Investigation
**When to use:** Evaluating technologies, comparing options, feasibility studies

**Purpose:** Comprehensive research with evidence-based recommendations

**Template guide:** `/.claude/templates/output-types/research.mdc`

**Output:**
- Executive summary
- Options evaluated (comprehensive pros/cons)
- Side-by-side comparison
- Real-world usage examples
- Risk assessment
- Implementation considerations
- Clear recommendations with justification
- Cited sources

**Research types:**
- Library/framework comparison
- Best practices investigation
- Feasibility studies
- Technology evaluation

**No implementation - research only**

---

## Execution Instructions

### For Default Workflow:
**Your task:** {{TASK_DESCRIPTION}}

Follow the standard 4-phase workflow with user checkpoints:

**Phase 0: Research (Automatic)**
1. Determine research depth (Level 1/2/3)
2. Execute time-boxed research (2/5/15 min max)
3. Document findings in `/tasks/[feature-name]/research.md`
4. Present **Options A/B/C** based on findings
5. **Wait for user to select approach**
6. Use research + chosen approach to inform clarifying questions

**Phase 1: Create PRD (After Research)**
1. Acknowledge this as a task request
2. Create directory: `/tasks/[feature-name]/`
3. Ask clarifying questions (use lettered/numbered lists for easy response)
4. **Wait for user responses**
5. Generate comprehensive PRD following template
6. Save to `/tasks/[feature-name]/prd.md`
7. **Ask: "Would you like me to proceed with Phase 2: Task Generation?"**
8. **Wait for approval**

**Phase 2: Generate Tasks (After PRD Approval)**
1. Create parent tasks (4–7 tasks)
2. **ALWAYS include Documentation parent task (REQUIRED)**
3. Generate sub-tasks (3–8 per parent)
4. Create TodoWrite entries for all tasks
5. Save to `/tasks/[feature-name]/tasklist_1.md`
6. **Ask: "Would you like me to proceed with Phase 3: Task Execution?"**
7. **Wait for approval**

**Phase 3: Execute (After Task List Approval)**
- One sub-task at a time
- Mark `in_progress` in TodoWrite AND markdown (same response)
- Execute with comprehensive inline documentation
- Mark `completed` in TodoWrite AND markdown (same response)
- When parent complete: test, document, commit
- Update version in CLAUDE.md

---

### For Template-Based Workflows:

**Detected template:** `[TEMPLATE_NAME]`
**Task instructions:** {{TASK_DESCRIPTION}}

**Action:**
1. Load the template guide:
   - If template is `go` or `slow`: `/.claude/workflows/[TEMPLATE_NAME]-autonomous.mdc` (go) or `/.claude/workflows/[TEMPLATE_NAME]-methodical.mdc` (slow)
   - Otherwise: `/.claude/templates/output-types/[TEMPLATE_NAME].mdc`
2. Follow template-specific workflow
3. Apply template-specific communication style
4. Produce template-specific output format

---

## Quick Reference

**Guides** (available in worktree-local `.trees/task-guiding-docs/` when present):
- Quick Reference Checklist
- Documentation Requirements
- Complete Workflow Guide
- TodoWrite-Markdown Sync

**Templates:**
- Discovery (standard): `/.claude/templates/discovery/standard.mdc`
- Discovery (thorough): `/.claude/templates/discovery/thorough.mdc`
- PRD Creation: `/.claude/templates/task-phases/create-prd.mdc`
- Task Generation: `/.claude/templates/task-phases/generate-tasks.mdc`
- Task Execution: `/.claude/templates/task-phases/process-tasks.mdc`
- Workflow Go: `/.claude/workflows/go-autonomous.mdc`
- Workflow Slow: `/.claude/workflows/slow-methodical.mdc`
- Communicate: `/.claude/templates/output-types/communicate.mdc`
- Analyze: `/.claude/templates/output-types/analyze.mdc`
- Research: `/.claude/templates/output-types/research.mdc`

---

**Now begin the appropriate workflow based on the command syntax used.**
