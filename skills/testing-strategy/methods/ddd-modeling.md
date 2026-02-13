# DDD Modeling (Domain-Driven Design)

**Purpose:** Structure complex domains so the code reflects business reality, not technical convenience.
**Key texts:** *Domain-Driven Design* (Evans, 2003); *Implementing Domain-Driven Design* (Vernon, 2013)
**When it matters:** The domain is complex enough that getting the model wrong causes cascading bugs, misunderstandings, or architectural dead-ends.

## The Honest Assessment

DDD is powerful when domain complexity is the core challenge. It is overkill — and actively harmful to velocity — when the problem is straightforward CRUD, data pipelines, or infrastructure tooling. Most software does not need DDD. The software that does need it really needs it.

## The Complexity Test

Before adopting DDD patterns, answer honestly:

```
Does the business domain have rules that surprise developers?
├── Yes — domain experts regularly correct your assumptions
│   └── USE DDD. The modeling investment pays for itself
│       in prevented misunderstandings.
│
├── "It's complicated but I understand it"
│   └── PROBABLY DON'T. If one person holds the model in their
│       head, strong typing + clear services is enough.
│
└── No — it's mostly data in, data out
    └── DON'T USE DDD. You'll build ceremony around
        straightforward logic. Use plain services + models.
```

## When DDD Genuinely Wins

### 1. Business Rules Are the Product
Insurance pricing, lending decisions, compliance engines, scheduling systems — when the rules themselves are what you sell, getting the model wrong means the product is wrong.

### 2. Multiple Bounded Contexts Need to Communicate
When different parts of the system use the same word to mean different things (a "user" in billing vs. "user" in permissions), explicit context boundaries prevent subtle data corruption.

### 3. Domain Experts Are Available and Engaged
DDD's ubiquitous language only works if business people participate in defining it. Without that feedback loop, you're guessing at a model.

### 4. The System Will Live for Years
DDD's upfront investment in modeling pays off over long lifespans. For a 6-month project, the overhead isn't justified.

## Strategic Patterns (Architecture-Level)

These patterns determine how you carve up the system. Get these wrong and tactical patterns won't save you.

### Bounded Contexts

A bounded context is a boundary within which a domain model is consistent. The same real-world concept may have different representations in different contexts.

```
┌─────────────────────┐    ┌─────────────────────┐
│   Ordering Context   │    │   Shipping Context   │
│                      │    │                      │
│  Order               │    │  Shipment            │
│  ├─ line_items[]     │    │  ├─ tracking_number  │
│  ├─ total            │    │  ├─ weight           │
│  └─ customer_id      │    │  └─ destination      │
│                      │    │                      │
│  Customer            │    │  Recipient           │
│  ├─ email            │    │  ├─ name             │
│  ├─ payment_methods  │    │  ├─ address          │
│  └─ order_history    │    │  └─ phone            │
└─────────────────────┘    └─────────────────────┘
        │                          │
        └──── Anti-Corruption ─────┘
              Layer (ACL)
```

**Customer** in Ordering knows about payment methods and history. **Recipient** in Shipping only knows delivery details. They share a real-world person but serve different purposes. Forcing them into one model creates a god object.

### Context Relationships

| Relationship | What It Means | When to Use |
|---|---|---|
| **Shared Kernel** | Two contexts share a subset of the model | Teams are tightly coordinated and can agree on shared types |
| **Customer/Supplier** | Upstream context serves downstream; downstream has input on the API | Clear dependency direction, good-faith collaboration |
| **Conformist** | Downstream adopts upstream's model as-is | Upstream won't change for you (e.g., external API) |
| **Anti-Corruption Layer** | Downstream translates upstream's model into its own | Protecting your model from a messy or unstable upstream |
| **Separate Ways** | No integration; contexts are independent | The cost of integration exceeds the benefit |

**Default choice for this project:** Anti-Corruption Layer. It's the safest — your domain model stays clean regardless of what external systems look like.

### Context Mapping in Practice (Python)

```python
# Anti-Corruption Layer: translate external payment API into your domain

# External API returns this mess
# {"txn_id": "abc", "amt": 4999, "ccy": "usd", "stat": "ok"}

# Your domain model
@dataclass(frozen=True)
class PaymentResult:
    transaction_id: str
    amount: Decimal
    currency: str
    succeeded: bool

# ACL translates between worlds
class PaymentGatewayACL:
    def __init__(self, client: StripeClient):
        self._client = client

    def charge(self, amount: Decimal, currency: str) -> PaymentResult:
        raw = self._client.create_charge(
            amt=int(amount * 100), ccy=currency
        )
        return PaymentResult(
            transaction_id=raw["txn_id"],
            amount=Decimal(raw["amt"]) / 100,
            currency=raw["ccy"],
            succeeded=raw["stat"] == "ok",
        )
```

## Tactical Patterns (Code-Level)

These are the building blocks within a bounded context.

### Entities vs Value Objects

The single most important distinction in DDD.

| | Entity | Value Object |
|---|---|---|
| **Identity** | Has a unique ID; two entities with same data are different | Defined by attributes; two VOs with same data are equal |
| **Mutability** | Mutable (state changes over lifecycle) | Immutable (replace, don't modify) |
| **Example** | `User(id=1, name="Alice")` | `Money(amount=10, currency="USD")` |
| **Python** | Class with `id` field | `@dataclass(frozen=True)` or `NamedTuple` |

```python
# VALUE OBJECT — defined by its attributes, immutable
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Money cannot be negative")

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")
        return Money(amount=self.amount + other.amount, currency=self.currency)


# ENTITY — has identity, mutable state
class Order:
    def __init__(self, id: str, customer_id: str):
        self.id = id
        self.customer_id = customer_id
        self._items: list[OrderItem] = []
        self._status = OrderStatus.DRAFT

    def add_item(self, product_id: str, quantity: int, unit_price: Money) -> None:
        if self._status != OrderStatus.DRAFT:
            raise InvalidOperationError("Cannot modify a submitted order")
        self._items.append(OrderItem(product_id, quantity, unit_price))

    @property
    def total(self) -> Money:
        from functools import reduce
        return reduce(lambda a, b: a.add(b), (i.subtotal for i in self._items))
```

### Aggregates

An aggregate is a cluster of entities and value objects with a single entry point (the aggregate root). All modifications go through the root. This enforces consistency boundaries.

```
┌─────────── Order Aggregate ───────────┐
│                                        │
│  Order (Root)                          │
│  ├─ add_item()     ← all access       │
│  ├─ remove_item()    through root      │
│  ├─ submit()                           │
│  │                                     │
│  ├─ OrderItem (entity)                 │
│  │   ├─ product_id                     │
│  │   ├─ quantity                       │
│  │   └─ unit_price: Money (VO)         │
│  │                                     │
│  └─ ShippingAddress (VO)               │
│      ├─ street                         │
│      ├─ city                           │
│      └─ postal_code                    │
└────────────────────────────────────────┘
```

**Rules:**
1. Only the aggregate root has a globally unique ID
2. External objects reference the aggregate by root ID only
3. Modifications go through root methods (never reach in and mutate an OrderItem directly)
4. One transaction = one aggregate. If you need to update two aggregates, use domain events

### Domain Events

When something meaningful happens in the domain, publish an event. Other parts of the system react without coupling to the source.

```python
@dataclass(frozen=True)
class OrderSubmitted:
    order_id: str
    customer_id: str
    total: Money
    submitted_at: datetime

class Order:
    def submit(self) -> list[DomainEvent]:
        if self._status != OrderStatus.DRAFT:
            raise InvalidOperationError("Order already submitted")
        if not self._items:
            raise InvalidOperationError("Cannot submit empty order")

        self._status = OrderStatus.SUBMITTED

        return [OrderSubmitted(
            order_id=self.id,
            customer_id=self.customer_id,
            total=self.total,
            submitted_at=datetime.utcnow(),
        )]
```

**Why return events instead of publishing directly:** Keeps the aggregate pure. The service layer decides when and how to publish (Celery, Redis pub/sub, in-process handler).

### Repositories

A repository provides a collection-like interface for retrieving and persisting aggregates. It hides storage details from the domain.

```python
# Domain layer — interface only (protocol or ABC)
class OrderRepository(Protocol):
    def get(self, order_id: str) -> Order: ...
    def save(self, order: Order) -> None: ...
    def find_by_customer(self, customer_id: str) -> list[Order]: ...

# Infrastructure layer — implementation
class SQLAlchemyOrderRepository:
    def __init__(self, session: Session):
        self._session = session

    def get(self, order_id: str) -> Order:
        row = self._session.query(OrderModel).get(order_id)
        if not row:
            raise OrderNotFound(order_id)
        return self._to_domain(row)

    def save(self, order: Order) -> None:
        row = self._to_model(order)
        self._session.merge(row)
```

**Testing:** Use in-memory fakes (a dict-backed repository), not mocks. This aligns with Chicago TDD — the fake has real behavior.

```python
class InMemoryOrderRepository:
    def __init__(self):
        self._orders: dict[str, Order] = {}

    def get(self, order_id: str) -> Order:
        if order_id not in self._orders:
            raise OrderNotFound(order_id)
        return self._orders[order_id]

    def save(self, order: Order) -> None:
        self._orders[order.id] = order
```

## Why Claude Code Needs This Guide

Unlike TDD, planning, or refactoring — which Claude handles intuitively — DDD has specific rules that are non-obvious:

- **Aggregate boundaries** determine where transactions end. Getting them wrong causes data inconsistency or distributed transaction nightmares.
- **Value objects must be immutable.** Claude may default to mutable dataclasses unless guided.
- **Entities are equal by ID, not attributes.** Claude may generate `__eq__` based on all fields.
- **External references use root IDs only.** Claude may create direct references between aggregates.
- **Domain events decouple aggregates.** Without guidance, Claude may wire aggregates together with direct method calls.

These patterns have precise rules. "Use your judgment" doesn't work — you need to know the rules to apply them correctly.

## Anti-Patterns

| Anti-Pattern | Symptom | Fix |
|---|---|---|
| **Anemic domain model** | Entities are data bags; all logic in services | Move behavior into the entities and value objects |
| **God aggregate** | One aggregate owns everything; every change touches it | Split along true consistency boundaries |
| **Leaking persistence** | Domain objects know about SQLAlchemy/Django ORM | Separate domain models from ORM models; use repository pattern |
| **Shared kernel overuse** | Every context shares the same types | Use ACL; shared kernels require tight coordination |
| **Event storming without experts** | Developers guess at domain events alone | Involve actual domain experts or don't bother |
| **DDD for CRUD** | Full aggregate/repository ceremony for simple data | Use plain models and services; DDD adds nothing here |

## Integration With Testing Strategy

DDD code maps cleanly to the testing strategy framework:

| DDD Component | Testing Method | Why |
|---|---|---|
| Value objects | Chicago TDD + Property-based | Pure, immutable, wide input space |
| Entities / Aggregates | Chicago TDD | Behavior-rich, real collaborators |
| Domain events | Chicago TDD | Assert events returned from aggregate methods |
| Repositories (interface) | Chicago TDD with in-memory fakes | Verify collection-like behavior |
| Repositories (SQLAlchemy) | Integration tests | Real database, verify persistence |
| Anti-Corruption Layers | London TDD | Mock the external system, verify translation |
| Domain services | Chicago TDD | Orchestration logic with real aggregates |

## Decision: When to Apply

```
Is the domain complex enough that developers regularly misunderstand it?
├── Yes
│   ├── Will this system live for 2+ years?
│   │   ├── No  → Use value objects and repositories only
│   │   └── Yes → Are domain experts available to validate the model?
│   │       ├── Yes → FULL DDD (strategic + tactical patterns)
│   │       └── No  → TACTICAL ONLY (value objects, aggregates,
│   │                 repositories — skip ubiquitous language ceremony)
│
└── No — developers understand the domain well
    └── DON'T USE DDD. Strong typing + clear services is enough.
        Value objects are always welcome (they're just good code).
```

**Note:** Value objects (`@dataclass(frozen=True)` with validation) are worth using everywhere, even without DDD. They're not DDD-specific — they're just good Python.
