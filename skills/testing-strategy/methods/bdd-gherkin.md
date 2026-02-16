# BDD Gherkin (Given/When/Then)

**Purpose:** Cross-role collaboration through human-readable executable specifications.
**Python framework:** pytest-bdd or behave
**Key text:** *BDD in Action* (Smart, 2014); Dan North's original blog posts (2006)

## The Honest Assessment

Gherkin was designed for **cross-role collaboration**: product owners, developers, and QA writing scenarios together ("three amigos"). When this collaboration exists, Gherkin is powerful. When it doesn't, Gherkin is a translation layer with no audience.

## The Collaboration Test

Before adopting Gherkin, answer honestly:

```
Will non-developers actually read feature files?
├── Yes — they participate in writing/reviewing scenarios
│   └── USE Gherkin. The abstraction cost is justified.
│
├── "They could" / "They should" / "Eventually"
│   └── DON'T USE Gherkin. Hope is not a strategy.
│       Use Given/When/Then as comments in regular tests.
│
└── No — only developers touch tests
    └── DON'T USE Gherkin. You're paying abstraction tax
        for zero benefit. Write clear pytest functions.
```

## When Gherkin Genuinely Wins

### 1. Regulated Industries
When you need auditable acceptance criteria tied to requirements (healthcare, finance, government). Feature files become compliance evidence that auditors can read.

### 2. Domain-Driven Design With Established Ubiquitous Language
When the team has agreed on precise domain terms, Gherkin encodes that shared language into executable specs. The feature files become the authoritative reference for what the system does.

### 3. Complex Business Rules ARE the Product
Insurance pricing, tax calculations, compliance rules — when the rules themselves are the value proposition, encoding them in readable scenarios prevents misunderstanding between business and engineering.

### 4. Separate QA Team
When QA writes acceptance criteria before development starts and verifies them after, Gherkin is the contract between roles. QA owns the feature files; devs implement step definitions.

## Why Gherkin Often Fails

### The Step Definition Trap

```gherkin
Given a user exists with email "test@example.com"
```

Requires:
```python
@given('a user exists with email "{email}"')
def step_user_exists(context, email):
    user = User(email=email, name="Test User")
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    context.user = user
```

Now multiply by every scenario step. You build a **parallel codebase** of step definitions that needs its own maintenance, refactoring, and debugging. Step libraries grow, become inconsistent, and develop their own technical debt.

### The Combinatorial Explosion

A feature with 5 conditions and 3 states each produces 243 scenarios. Writing and maintaining these in Gherkin is painful. Property-based testing handles combinatorics better.

### The Regex Fragility

`Given a user with name "John"` and `Given a user with the name "John"` are different step patterns. Teams spend time on regex maintenance instead of testing.

### The Abstraction Tax

Every Gherkin line hides implementation details. When a step fails, you debug through two layers of indirection: the feature file tells you *what* failed, the step definition tells you *how* it was implemented, and neither tells you *why* it broke.

## The Better Alternative: Structured Tests Without Gherkin Tooling

Use Given/When/Then as a **thinking framework**, not a tooling framework:

```python
class TestOrderCheckout:
    def test_applies_promo_code_to_order_total(self, client, auth_headers):
        # Given an order with items totaling $100
        order = create_order_with_total(Decimal("100.00"))

        # When a 20% promo code is applied
        response = client.post(
            f"/api/orders/{order.id}/promo",
            json={"code": "SAVE20"},
            headers=auth_headers,
        )

        # Then the total reflects the discount
        assert response.status_code == 200
        assert response.json["total"] == "80.00"
```

You get structured thinking, readable tests, and zero abstraction overhead. The test IS the specification.

## If You Do Use Gherkin

### Feature File Structure

```gherkin
# features/checkout.feature

Feature: Order Checkout
  As a customer
  I want to apply promotional codes
  So that I receive discounts on my orders

  Background:
    Given a registered customer
    And an order with items totaling $100.00

  Scenario: Valid promo code reduces order total
    Given a valid promo code "SAVE20" for 20% off
    When the customer applies the promo code
    Then the order total should be $80.00

  Scenario: Expired promo code is rejected
    Given an expired promo code "OLD10"
    When the customer applies the promo code
    Then the promo code should be rejected
    And the order total should remain $100.00

  Scenario Outline: Discount tiers
    Given a valid promo code "<code>" for <percent>% off
    When the customer applies the promo code
    Then the order total should be $<expected>

    Examples:
      | code   | percent | expected |
      | SAVE10 | 10      | 90.00    |
      | SAVE20 | 20      | 80.00    |
      | SAVE50 | 50      | 50.00    |
```

### Rules for Sustainable Gherkin

1. **Keep scenarios under 8 steps.** If longer, decompose into multiple scenarios or use Background.
2. **Declarative, not imperative.** Write `Given an order` not `Given I click "New Order" and fill in the form`.
3. **One assertion concept per scenario.** Don't test 5 things in one scenario.
4. **Background for shared setup.** Don't repeat Given steps across every scenario.
5. **Scenario Outlines for parameterized cases.** Don't copy-paste scenarios that differ only in values.
6. **Organize step definitions by domain.** Group by entity (user_steps, order_steps), not by feature file.
7. **Name feature files by capability, not screen.** `checkout.feature` not `checkout_page.feature`.

### Framework Choice for Python

| Framework | Pros | Cons |
|-----------|------|------|
| **pytest-bdd** | Integrates with pytest ecosystem, fixtures work | Less feature-complete than behave |
| **behave** | Full Gherkin support, mature | Separate test runner, doesn't use pytest fixtures |

**Recommendation for this project:** pytest-bdd, because the project is standardized on pytest and fixture reuse is valuable.
