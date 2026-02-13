---
name: process-map
description: Identify affected business processes and data structures. Used by Context Agent to understand system impact before work begins.
---

# Process Map

Identify the processes and data structures affected by a task.

## Input

- **task**: Description of the work to be done
- **files**: Known affected files (optional)

## Process

### 1. Identify Affected Processes

**Search for process documentation:**
```
Glob: "docs/processes/**/*.md"
Glob: "docs/workflows/**/*.md"
Glob: "**/PROCESS.md"
Glob: "**/WORKFLOW.md"
```

**Infer from code structure:**

*Python:*
```
Grep: "class.*Service"
Grep: "class.*Pipeline"
Grep: "class.*Workflow"
Grep: "def process_"
Grep: "@on_event"
Grep: "def handle_"
```

*TypeScript/JavaScript:*
```
Grep: "class.*Service"
Grep: "export.*Service"
Grep: "async function process"
Grep: "@EventHandler"
Grep: "on\(['\"].*['\"]"
```

*Go:*
```
Grep: "type.*Service struct"
Grep: "func.*Process"
Grep: "func.*Handle"
Grep: "type.*Handler"
```

*Java/Kotlin:*
```
Grep: "class.*Service"
Grep: "@Service"
Grep: "@EventListener"
Grep: "void process"
Grep: "void handle"
```

*Rust:*
```
Grep: "struct.*Service"
Grep: "impl.*Service"
Grep: "fn process"
Grep: "fn handle"
```

**Map the process:**
- What triggers this process?
- What are the steps?
- What does it output?
- What are upstream dependencies?
- What downstream processes depend on it?

### 2. Identify Affected Data Structures

**Find models (language-aware):**

*Python:*
```
Glob: "app/models/**/*.py"
Glob: "**/models.py"
Glob: "**/schema*.py"

Grep: "class.*\(.*Model\)"      # SQLAlchemy/Django
Grep: "class.*\(db.Model\)"     # Flask-SQLAlchemy
Grep: "class.*\(BaseModel\)"    # Pydantic
Grep: "class.*Schema"           # Marshmallow
Grep: "@dataclass"              # dataclasses
Grep: "class.*\(TypedDict\)"    # TypedDict
```

*TypeScript/JavaScript:*
```
Glob: "**/models/**/*.ts"
Glob: "**/entities/**/*.ts"
Glob: "**/types/**/*.ts"

Grep: "interface.*{"            # TypeScript interfaces
Grep: "@Entity"                 # TypeORM
Grep: "type.*="                 # Type aliases
Grep: "z\.object"               # Zod schemas
```

*Go:*
```
Glob: "**/models/*.go"
Glob: "**/entity/*.go"

Grep: "type.*struct"            # Structs
```

*Java/Kotlin:*
```
Glob: "**/entity/**/*.java"
Glob: "**/model/**/*.java"

Grep: "@Entity"                 # JPA
Grep: "@Table"                  # JPA
Grep: "data class"              # Kotlin
```

**Map the data:**
- What fields/columns exist?
- What are the relationships?
- What validates this data?
- What transforms this data?

### 3. Trace Data Flow

Use Explore agent to trace:
```
Task(subagent_type="Explore", prompt="Trace the data flow for [entity].
Where is it created? How is it transformed? Where is it consumed?")
```

## Output

```markdown
## Affected Processes

### Payment Processing
- **Location:** `app/services/payment_service.py`
- **Trigger:** API call to `/api/payments`
- **Steps:**
  1. Validate payment request
  2. Check user balance
  3. Create transaction record
  4. Call payment gateway
  5. Update balances
  6. Emit payment.completed event
- **Upstream:** User authentication, Order creation
- **Downstream:** Receipt generation, Notification service

### Order Fulfillment (impacted)
- **Location:** `app/services/order_service.py`
- **Impact:** Waits for payment.completed event
- **Change Needed:** Handle new payment statuses

## Affected Data Structures

### Payment Model
- **Location:** `app/models/payment.py`
- **Fields:**
  - `id`: Primary key
  - `user_id`: FK to User
  - `amount`: Decimal
  - `status`: Enum (pending, completed, failed)
  - `created_at`: DateTime
- **Relationships:**
  - `user`: Many-to-one with User
  - `order`: One-to-one with Order
- **Change Needed:** Add `refund_amount` field

### PaymentRequest Schema
- **Location:** `app/schemas/payment.py`
- **Used By:** POST /api/payments
- **Fields:** amount, currency, order_id
- **Change Needed:** Add optional `metadata` field

## Data Flow

```
User Request
    ↓
PaymentRequest (validation)
    ↓
PaymentService.create_payment()
    ↓
Payment model (database)
    ↓
PaymentGateway (external)
    ↓
payment.completed event
    ↓
OrderService (downstream)
```

## Impact Summary

| Component | Type | Impact Level |
|-----------|------|--------------|
| PaymentService | Process | High - core changes |
| Payment model | Data | Medium - new field |
| OrderService | Process | Low - handle new status |
| User model | Data | None |
```

## Empty State Handling

**If no processes found:**
```markdown
## Affected Processes
- **Status:** No formal process documentation or service classes found
- **Recommendation:** Check if this is a utility/library project (no business processes)
- **Alternative:** Look for entry points in `main.py`, `index.ts`, `cmd/`, etc.
```

**If no data structures found:**
```markdown
## Affected Data Structures
- **Status:** No models/schemas found in standard locations
- **Recommendation:** Check for inline type definitions or external schema files
```

## Usage

**Context Agent:** Map processes and data structures after gathering plan context, before diving into code patterns. This provides the "what changes" context.

## Language Detection

Detect primary language from:
1. File extensions in project root
2. `package.json` (JS/TS), `pyproject.toml` (Python), `go.mod` (Go), `Cargo.toml` (Rust), `pom.xml` (Java)
3. Most common file extension in `src/` or `app/`
