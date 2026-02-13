# Example: Semantic Search Sprint

This example shows a complete sprint workflow for adding semantic search to a markets API.

## Session Transcript

### User Input
```text
/sprint Add semantic search to the markets API so users can find markets using natural language queries
```

### Phase 1: Developer Input

Claude asks clarifying questions:

```text
Starting sprint planning for: Add semantic search to markets API

I need a few details to build complete requirements:

┌─────────────────────────────────────────────────────────────┐
│ Question 1: Search Capability                               │
├─────────────────────────────────────────────────────────────┤
│ What type of search do you need?                            │
│                                                             │
│ ○ Vector/semantic only (AI-powered similarity)              │
│ ○ Full-text only (keyword matching)                         │
│ ● Hybrid (semantic with full-text fallback) (Recommended)   │
│ ○ Other                                                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Question 2: Constraints                                     │
├─────────────────────────────────────────────────────────────┤
│ Any technical constraints I should know about?              │
│                                                             │
│ ☑ Must use existing Redis/vector store                      │
│ ☑ API backwards compatible                                  │
│ ☐ Specific latency requirements                             │
│ ☐ Other                                                     │
└─────────────────────────────────────────────────────────────┘
```

**Generated:** `.sprint/input.yaml`

```yaml
phase: 1
phase_name: intake
role: developer
status: complete
timestamp: "2026-01-28T10:30:00Z"
depends_on: null

what: |
  Add semantic search capability to the markets API endpoint.
  Users should be able to search for markets using natural language
  queries like "elections in 2026" or "cryptocurrency price predictions".

why: |
  Current search only supports exact keyword matching, which fails
  when users describe what they want in different terms than the
  market titles use. Semantic search will improve discovery.

who:
  primary: "API consumers (web app, mobile app)"
  secondary: "Direct API users"

constraints:
  technical:
    - "Use existing Redis vector store"
    - "API must remain backwards compatible"
    - "Response time < 500ms p95"
  scope:
    - "Only /api/markets/search endpoint"
    - "No changes to market creation"

context:
  existing_systems:
    - name: "Redis Vector Store"
      relevance: "Already stores embeddings for recommendations"
    - name: "OpenAI API"
      relevance: "Currently used for other embeddings"
  related_files:
    - "src/api/markets.py"
    - "src/services/market_service.py"
    - "src/rag/embeddings.py"
```

### Phase 2: Product Management

```text
✓ Phase 1: Intake → .sprint/input.yaml

Proceeding to Phase 2: Refinement...

Analyzing input to generate product requirements...
```

**Generated:** `.sprint/product.yaml`

```yaml
phase: 2
phase_name: refinement
role: product_manager
status: complete
timestamp: "2026-01-28T10:32:00Z"
depends_on: intake

epic:
  title: "Semantic Market Search"
  description: |
    Enable natural language search for markets so users can
    find relevant markets without knowing exact keywords.
  business_value: |
    Improve market discovery and user engagement by making
    search more intuitive and forgiving.

user_stories:
  - id: US-001
    as_a: "market browser"
    i_want: "to search for markets using natural language"
    so_that: "I can find relevant markets without exact keywords"
    acceptance_criteria:
      - "Given a query 'elections', when I search, then I see election-related markets"
      - "Given a query 'crypto prices', when I search, then I see cryptocurrency markets"
      - "Given an empty query, when I search, then I get an empty result (not error)"
    priority: must

  - id: US-002
    as_a: "API consumer"
    i_want: "search to fall back gracefully when vector store is down"
    so_that: "search always works even if degraded"
    acceptance_criteria:
      - "Given Redis is unavailable, when I search, then I get keyword-based results"
      - "Given Redis is unavailable, when I search, then response includes degraded flag"
    priority: must

  - id: US-003
    as_a: "developer"
    i_want: "backwards compatible API"
    so_that: "existing integrations don't break"
    acceptance_criteria:
      - "Existing query parameter still works"
      - "Response schema unchanged (new fields additive only)"
    priority: must

success_metrics:
  - metric: "Search relevance improvement"
    measurement: "> 30% more clicks on first-page results"
  - metric: "API response time"
    measurement: "< 500ms p95"

scope:
  in_scope:
    - "GET /api/markets/search endpoint enhancement"
    - "Semantic similarity scoring"
    - "Graceful degradation"
  out_of_scope:
    - "Search analytics dashboard"
    - "Personalized search results"
    - "Auto-complete/suggestions"
```

### Phase 3: Design

**Generated:** `.sprint/design.yaml`

```yaml
phase: 3
phase_name: design
role: ux_designer
status: complete
timestamp: "2026-01-28T10:35:00Z"
depends_on: refinement

design_mode: frontend

ux_requirements:
  flows:
    - name: "Semantic Search Flow"
      trigger: "GET /api/markets/search?q=<query>"
      steps:
        - step: 1
          action: "Client sends search query"
          response: "API receives request"
        - step: 2
          action: "API generates embedding"
          response: "Query converted to vector"
        - step: 3
          action: "Vector similarity search"
          response: "Top N similar markets retrieved"
        - step: 4
          action: "Format response"
          response: "JSON with markets and scores"

    - name: "Fallback Flow"
      trigger: "Vector store unavailable"
      steps:
        - step: 1
          action: "Vector search fails"
          response: "Catch exception, log warning"
        - step: 2
          action: "Fall back to keyword search"
          response: "Use LIKE query on titles"
        - step: 3
          action: "Add degraded flag"
          response: "Response includes search_mode: degraded"

  components:
    - name: "Search Response"
      type: display
      states:
        success:
          display: '{"markets": [...], "search_mode": "semantic", "total": N}'
        degraded:
          display: '{"markets": [...], "search_mode": "keyword", "total": N}'
        empty:
          display: '{"markets": [], "search_mode": "semantic", "total": 0}'
        error:
          display: '{"error": "message", "code": "ERROR_CODE"}'

  validations:
    - field: "q (query parameter)"
      rules:
        required: false  # Empty returns empty, not error
        max_length: 500
      error_messages:
        too_long: "Query must be under 500 characters"

  edge_cases:
    - scenario: "Empty query"
      handling: "Return empty array, not error"
    - scenario: "Very long query"
      handling: "Truncate to 500 chars, search anyway"
    - scenario: "Non-ASCII characters"
      handling: "Support UTF-8 queries"
    - scenario: "Query with only stop words"
      handling: "Return empty array"
```

### Phase 4: Technical Planning

**Generated:** `.sprint/technical.yaml`

```yaml
phase: 4
phase_name: technical_planning
role: tech_lead
status: complete
timestamp: "2026-01-28T10:40:00Z"
depends_on: design
_schema_version: "1.0"
summary: |
  Planned implementation with 3 modified files, 2 risks identified.
outputs:
  - .sprint/technical.yaml
open_issues: []
signals:
  pass: true
  confidence: high
  blockers: []

architecture:
  approach: |
    Enhance existing search endpoint with vector similarity search.
    Use existing embeddings infrastructure. Add fallback layer.

  patterns:
    - name: "Strategy Pattern"
      usage: "Switch between semantic and keyword search"
    - name: "Circuit Breaker"
      usage: "Detect and handle Redis failures"

changes:
  modified_files:
    - path: "src/services/market_service.py"
      changes:
        - "Add search_markets_semantic() method"
        - "Add fallback logic"
      reason: "Core search logic"

    - path: "src/api/markets.py"
      changes:
        - "Update search endpoint to use semantic search"
        - "Add search_mode to response"
      reason: "API layer changes"

    - path: "src/rag/embeddings.py"
      changes:
        - "Add generate_query_embedding() if not exists"
      reason: "Query embedding generation"

dependencies:
  internal:
    - module: "src/rag/embeddings.py"
      usage: "Embedding generation"
    - module: "src/redis_client.py"
      usage: "Vector store access"
  external: []  # No new dependencies

api:
  endpoints:
    - method: GET
      path: "/api/markets/search"
      description: "Search markets (enhanced with semantic)"
      request:
        params:
          q: "Search query (optional)"
          limit: "Max results (default 10)"
      response:
        success:
          status: 200
          body: |
            {
              "markets": [...],
              "total": 42,
              "search_mode": "semantic|keyword"
            }

risks:
  - risk: "Embedding API latency adds to response time"
    likelihood: medium
    impact: medium
    mitigation: "Cache common query embeddings"

  - risk: "Vector store returns irrelevant results"
    likelihood: low
    impact: medium
    mitigation: "Add minimum similarity threshold"
```

### Phase 5: Sprint Backlog

**Generated:** `.sprint/backlog.yaml`

```yaml
phase: 5
phase_name: backlog
role: tech_lead
status: complete
timestamp: "2026-01-28T10:45:00Z"
depends_on: technical_planning

sprint_backlog:
  - id: TASK-001
    title: "Write unit tests for semantic search"
    type: test
    story_ref: US-001
    description: "TDD: Write tests before implementing semantic search"
    acceptance_criteria:
      - "Tests for successful semantic search"
      - "Tests for empty query handling"
      - "Tests for fallback behavior"
    files:
      write:
        - "tests/unit/test_market_service.py"
    dependencies:
      blocked_by: []
      blocks: [TASK-002]
    estimate: M

  - id: TASK-002
    title: "Implement semantic search in MarketService"
    type: feature
    story_ref: US-001
    description: "Add search_markets_semantic() method with fallback"
    acceptance_criteria:
      - "All unit tests pass"
      - "Uses existing embedding infrastructure"
      - "Falls back to keyword search on Redis failure"
    files:
      read:
        - "src/rag/embeddings.py"
      write:
        - "src/services/market_service.py"
    dependencies:
      blocked_by: [TASK-001]
      blocks: [TASK-003]
    estimate: M

  - id: TASK-003
    title: "Write integration tests for search API"
    type: test
    story_ref: US-001
    description: "TDD: Integration tests for API endpoint"
    acceptance_criteria:
      - "Tests verify response schema"
      - "Tests verify search_mode field"
      - "Tests verify backwards compatibility"
    files:
      write:
        - "tests/integration/test_markets_api.py"
    dependencies:
      blocked_by: [TASK-002]
      blocks: [TASK-004]
    estimate: S

  - id: TASK-004
    title: "Update search endpoint"
    type: feature
    story_ref: US-001
    description: "Wire up semantic search to API endpoint"
    acceptance_criteria:
      - "Integration tests pass"
      - "Response includes search_mode"
      - "Backwards compatible"
    files:
      write:
        - "src/api/markets.py"
    dependencies:
      blocked_by: [TASK-003]
      blocks: []
    estimate: S

task_order:
  - TASK-001
  - TASK-002
  - TASK-003
  - TASK-004

task_summary:
  total_tasks: 4
  by_type:
    feature: 2
    test: 2
  by_estimate:
    S: 2
    M: 2
```

### Phase 6: Execution

```text
✓ Phase 5: Backlog → .sprint/backlog.yaml

Ready to execute 4 tasks:
────────────────────────────────────────
1. [TEST] Write unit tests for semantic search (M)
2. [FEATURE] Implement semantic search in MarketService (M)
3. [TEST] Write integration tests for search API (S)
4. [FEATURE] Update search endpoint (S)
────────────────────────────────────────

Delegating to /orchestrate sprint...
```

```text
Starting execution...

─── TASK-001: Write unit tests for semantic search ───
Status: In Progress...

Reading existing test patterns...
Creating tests/unit/test_market_service.py...
```

[Claude writes the tests, implements the service, etc.]

**Final:** `.sprint/execution-log.md`

```markdown
# Sprint Execution Log

**Sprint:** Semantic Market Search
**Started:** 2026-01-28T10:50:00Z
**Completed:** 2026-01-28T11:30:00Z
**Status:** Complete ✓

## Summary

- Total Tasks: 4
- Completed: 4
- Failed: 0
- Duration: ~40 minutes

## Tasks

### TASK-001: Write unit tests for semantic search ✓
- Started: 10:50
- Completed: 11:00
- Files: tests/unit/test_market_service.py

### TASK-002: Implement semantic search in MarketService ✓
- Started: 11:00
- Completed: 11:15
- Files: src/services/market_service.py
- Notes: Added similarity threshold of 0.7

### TASK-003: Write integration tests for search API ✓
- Started: 11:15
- Completed: 11:22
- Files: tests/integration/test_markets_api.py

### TASK-004: Update search endpoint ✓
- Started: 11:22
- Completed: 11:28
- Files: src/api/markets.py

## Test Results

All tests passing:
- Unit: 8 passed
- Integration: 5 passed
- Coverage: 87%

## Files Changed

- `src/services/market_service.py` - Added semantic search
- `src/api/markets.py` - Updated endpoint
- `tests/unit/test_market_service.py` - New tests
- `tests/integration/test_markets_api.py` - New tests
```

## Key Takeaways

1. **Autonomous by default** - All context inferred from input text and codebase; no human prompts
2. **Attended mode available** - Use `attended` flag for interactive checkpoints when needed
3. **TDD enforced** - Tests written before implementation
4. **Traceable requirements** - Each task links to user story
5. **Complete audit trail** - All artifacts preserved in `.sprint/`
