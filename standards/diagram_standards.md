# Diagram Standards

Canonical specifications for all diagrams. Each section references the authoritative standard.

---

## Data Flow Diagrams (DFD)

**Standard:** Yourdon-DeMarco notation
**Reference:** *Structured Analysis and System Specification* (DeMarco, 1979)

| Symbol | Meaning |
|--------|---------|
| Circle/Bubble | Process |
| Open rectangle (parallel lines) | Data store |
| Rectangle | External entity |
| Arrow | Data flow |

**Rules:**
- Processes numbered hierarchically (1.0, 1.1, 2.0)
- Data stores prefixed "D" (D1, D2)
- Data flows labeled with nouns, not verbs
- Level 0 = context diagram; Level 1+ = decomposition

---

## Sequence Diagrams

**Standard:** UML 2.5
**Reference:** OMG Unified Modeling Language v2.5.1 (OMG Document formal/2017-12-05)

| Element | Symbol |
|---------|--------|
| Lifeline | Dashed vertical line |
| Synchronous message | Solid arrow, filled head |
| Asynchronous message | Solid arrow, open head |
| Return | Dashed arrow |
| Fragment (alt/loop/opt) | Labeled box |

**Rules:**
- Time flows top-to-bottom
- Objects: `name:Class` or `:Class`
- Messages labeled with method signature

---

## Entity-Relationship Diagrams (ERD)

**Standard:** Crow's Foot (IE) notation
**Reference:** *Information Engineering* (Martin, 1990); ISO/IEC 11179 for metadata

| Cardinality | Symbol |
|-------------|--------|
| One | Single line |
| Many | Crow's foot |
| Zero or one | Circle + line |
| One (mandatory) | Line + perpendicular bar |

**Rules:**
- Entity names singular (User, not Users)
- PK/FK marked explicitly
- Relationships labeled with verb phrases

---

## State Diagrams

**Standard:** UML 2.5 State Machine
**Reference:** OMG Unified Modeling Language v2.5.1, Section 14

| Symbol | Meaning |
|--------|---------|
| Rounded rectangle | State |
| Filled circle | Initial state |
| Circled filled circle | Final state |
| Arrow | Transition |

**Transition format:** `trigger [guard] / action`

---

## Flowcharts

**Standard:** ISO 5807:1985
**Reference:** ISO 5807:1985 - Information processing — Documentation symbols and conventions for data, program and system flowcharts

| Symbol | Meaning |
|--------|---------|
| Rounded rectangle | Terminal (start/end) |
| Rectangle | Process |
| Diamond | Decision |
| Parallelogram | Input/Output |

**Rules:**
- One start, one or more ends
- Decisions have exactly two exits (Yes/No)
- Flow top-to-bottom, left-to-right

---

## Architecture Diagrams

**Standard:** C4 Model
**Reference:** c4model.com (Simon Brown)

| Level | Shows |
|-------|-------|
| 1 - Context | System + external actors |
| 2 - Container | Applications, databases, services |
| 3 - Component | Components within a container |
| 4 - Code | Classes/modules (use UML) |

**Rules:**
- Each box: Name, Type, Description
- Relationships labeled with technology/protocol

---

## Component Diagrams

**Standard:** UML 2.5 Component Diagram
**Reference:** OMG Unified Modeling Language v2.5.1, Section 11

| Symbol | Meaning |
|--------|---------|
| Rectangle + icon | Component |
| Lollipop (circle) | Provided interface |
| Socket (half-circle) | Required interface |

---

## Preferred Tools

1. **Mermaid** - Markdown-embeddable (sequence, flowchart, ERD)
2. **PlantUML** - Text-based UML
3. **Draw.io** - General diagramming
4. **Excalidraw** - Quick sketches

---

## Verification Checklist

- [ ] Correct notation for diagram type
- [ ] All elements labeled
- [ ] No notation anti-patterns
- [ ] Appropriate detail level
