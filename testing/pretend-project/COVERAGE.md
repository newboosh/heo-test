# Feature Coverage Matrix

Every heo-test feature mapped to the scenario that exercises it.
Features marked (auto) fire without an explicit prompt.

## Slash Commands

| Command                        | Tier       | Scenario    | Notes                                    |
|--------------------------------|------------|-------------|------------------------------------------|
| /help                          | production | 00          | First thing in setup                     |
| /setup                         | testing    | 00          | Configure plugin for project             |
| /plan                          | testing    | 01          | Plan overall architecture                |
| /context                       | production | 01          | Gather context for planning              |
| /context-payload               | testing    | 13          | Hybrid context delivery                  |
| /standards                     | production | 01          | Look up project standards                |
| /task                          | production | 01          | 4-phase task workflow                    |
| /catalog init                  | testing    | 00, 09b     | Build file catalog (09b-A init, 09b-Q rebuild) |
| /catalog build                 | testing    | 03, 09b     | Rebuild after adding files (09b-C,D,N incremental) |
| /catalog query                 | testing    | 04, 09b     | 12 query variants in 09b (E-P)           |
| /catalog status                | testing    | 09b         | Catalog health report (09b-B, 09b-M)    |
| /sprint                        | testing    | 02          | Sprint planning phases 1-5               |
| /sprint-run                    | testing    | 02          | Full sprint lifecycle                    |
| /sprint-run status             | testing    | 02          | Check sprint progress                    |
| /orchestrate                   | testing    | 08          | Execution phases 6-11                    |
| /arch-debate                   | production | 02          | Architecture decision                    |
| /tree stage                    | production | 03          | Stage features for worktrees             |
| /tree list                     | production | 03          | Show staged features                     |
| /tree build                    | production | 03          | Create worktrees                         |
| /tree sync                     | production | 03          | Sync worktree from main                  |
| /tree status                   | production | 03          | Check worktree state                     |
| /tree conflict                 | production | 08          | Analyze merge conflicts                  |
| /tree reset                    | production | 12          | Complete task and reset                  |
| /tree reset incomplete         | production | 08          | WIP save                                 |
| /tree reset --all              | production | 12          | Batch reset                              |
| /tree closedone                | production | 12          | Remove worktrees                         |
| /tree refresh                  | production | 03          | Check command availability               |
| /tree restore                  | production | 03          | Restore terminals                        |
| /branch                        | production | 03          | Branch helper                            |
| /tdd                           | production | 04          | TDD workflow for auth module             |
| /verify                        | production | 05          | Full verification suite                  |
| /verify quick                  | production | 04          | Quick check during TDD                   |
| /build-fix                     | testing    | 05          | Fix type/lint errors                     |
| /ci                            | production | 05          | Run CI locally                           |
| /code-review                   | production | 06          | Security and quality review              |
| /qa                            | production | 06          | QA agent review                          |
| /security-review (command)     | production | 06          | Security vulnerability review            |
| /diff-review (skill)          | production | 06          | Review changed files                     |
| /e2e                           | testing    | 10          | End-to-end tests with Playwright         |
| /test-coverage                 | production | 05          | Analyze coverage gaps                    |
| /refactor-clean                | testing    | 09c         | Dead code cleanup (split from 09)        |
| /bug                           | production | 07          | Bug investigation                        |
| /bug-swarm                     | production | 07          | Parallel bug investigation               |
| /health-check                  | production | 09c         | Codebase health audit (split from 09)    |
| /plan-swarm                    | testing    | 08          | Parallel sprint planning                 |
| /test-swarm                    | testing    | 08          | Parallel test writing                    |
| /review-swarm                  | production | 08          | Multi-perspective review                 |
| /push                          | production | 11          | Push with auto PR                        |
| /pr-status                     | testing    | 11          | Check PR status                          |
| /coderabbit                    | production | 11          | Single CodeRabbit review                 |
| /coderabbitloop                | production | 11          | Loop until approved                      |
| /coderabbit-status             | testing    | 11          | CodeRabbit review status                 |
| /coderabbit-process            | testing    | 11          | Fetch and fix comments                   |
| /coderabbit-conflicts          | testing    | 11          | Resolve merge conflicts                  |
| /collect-signals               | testing    | 12          | Post-merge signal gathering              |
| /checkpoint                    | testing    | 04          | Create/verify checkpoints                |
| /learn                         | testing    | 12          | Extract patterns                         |
| /update-docs                   | testing    | 09          | Sync docs (09-K,L single + multi-module) |
| /update-codemaps               | testing    | 09          | Update architecture docs (09-M,N)        |

## Skills (exercised by commands or directly)

| Skill                    | Tier       | Scenario | Trigger                                   |
|--------------------------|------------|----------|-------------------------------------------|
| setup                    | testing    | 00       | /setup command                             |
| tdd-workflow             | production | 04       | /tdd command                               |
| tree (worktree-mgmt)     | production | 03       | /tree commands                             |
| sprint                   | testing    | 02       | /sprint command                            |
| sprint-retrospective     | testing    | 12       | /sprint-retrospective via sprint-run       |
| feedback-synthesizer     | testing    | 12       | /collect-signals                           |
| verification-loop        | production | 05       | /verify command                            |
| eval-harness             | testing    | 10       | /e2e or eval-driven testing                |
| testing-strategy         | production | 04       | Referenced by /tdd                         |
| bug-investigate          | production | 07       | /bug command                               |
| backend-patterns         | testing    | 02       | Architecture planning                      |
| composition-patterns     | testing    | 13       | Advanced skill composition                 |
| team-patterns            | production | 08       | Team swarm coordination                    |
| problem-definition       | testing    | 01       | /problem-definition prompt                 |
| requirements-engineering | testing    | 01       | /requirements-engineering prompt           |
| boundary-critique        | testing    | 01       | Referenced by requirements-engineering     |
| plan-context             | production | 01       | /plan command                              |
| process-map              | production | 02       | Sprint planning                            |
| strategic-compact        | testing    | 13       | Context compaction                         |
| token-budget             | testing    | 13       | Token estimation                           |
| hybrid-payload           | testing    | 13       | /context-payload                           |
| payload-consumer         | testing    | 13       | Agent receiving hybrid payload             |
| standards-lookup         | production | 01       | /standards command                         |
| compliance-check         | production | 06       | /verify or code-review                     |
| tool-design              | testing    | 13       | Tool design reference                      |
| project-skeleton         | testing    | 00       | Project template reference                 |
| catalog                  | testing    | 00, 09b  | 17 prompts in 09b: init, build, query, status |
| librarian                | testing    | 09       | 16 prompts: audit, find, place, stale, coverage, orphans |
| gather-docs              | production | 09       | /gather-docs (09-I single, 09-J cross-module) |
| find-patterns            | production | 04       | /find-patterns during TDD                  |
| learned                  | testing    | 12       | /learn command                             |
| ack-protocol             | testing    | 13       | Structured payload delivery                |
| sub-agent-dispatch       | testing    | 08       | Context-agent sub-agents                   |
| security-review          | production | 06       | /security-review                           |
| artifact-audit           | production | 06       | Verify required artifacts                  |
| diff-review              | production | 06       | /diff-review                               |
| gate-decision            | testing    | 08       | Go/no-go decision                          |
| agent-creator            | testing    | 13       | Create custom agent                        |
| skill-creator            | testing    | 13       | Create custom skill                        |
| hook-creator             | testing    | 13       | Create custom hook                         |
| prereq-check             | testing    | 00       | Verify prerequisites                       |
| worktree-management      | testing    | 03       | Worktree skill reference                   |

## Agents (spawned by commands)

| Agent               | Tier       | Scenario | Spawned By                              |
|---------------------|------------|----------|-----------------------------------------|
| architect           | production | 02       | /arch-debate, /plan                     |
| planner             | production | 01       | /plan, /task                            |
| tdd-guide           | production | 04       | /tdd                                    |
| code-reviewer       | production | 06       | /code-review                            |
| security-reviewer   | production | 06       | /security-review                        |
| qa-agent            | production | 06       | /qa                                     |
| build-error-resolver| production | 05       | /build-fix                              |
| e2e-runner          | testing    | 10       | /e2e                                    |
| git-orchestrator    | production | 11       | /push, /tree reset                      |
| refactor-cleaner    | production | 09       | /refactor-clean                         |
| context-agent       | testing    | 01       | /context                                |
| context-monitor     | testing    | 13       | Context pressure monitoring             |
| librarian           | testing    | 09       | /librarian, /update-docs                |
| doc-updater         | testing    | 09       | /update-docs                            |

## Hooks (fire automatically)

| Hook                          | Tier       | Scenario    | Trigger                              |
|-------------------------------|------------|-------------|--------------------------------------|
| session-validate-tools        | production | 00 (auto)   | Session start                        |
| session-ensure-git-hooks      | production | 00 (auto)   | Session start                        |
| session-guard-init            | production | 00 (auto)   | Session start                        |
| pre-cross-worktree-warning    | production | 03 (auto)   | Editing outside worktree             |
| pre-git-safety-check          | production | 06 (auto)   | Git operations                       |
| post-python-format            | production | 04 (auto)   | After editing Python files           |
| context-pressure              | testing    | 13 (auto)   | During long sessions                 |
| capture-query                 | testing    | 00 (auto)   | User prompt submitted                |
| recap-on-stop                 | testing    | 12 (auto)   | Session stop                         |
| sentinel-task-context         | testing    | 08 (auto)   | Before subagent spawn                |
| post_agent_work               | testing    | 08 (auto)   | After agent completes                |
| post_task                     | testing    | 04 (auto)   | After task completes                 |
