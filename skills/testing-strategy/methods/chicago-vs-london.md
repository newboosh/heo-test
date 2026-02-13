# TDD Schools: Chicago (Classicist) vs London (Mockist)

## Chicago School — The Default

**Unit of test:** A unit of *behavior*, which may span multiple classes.
**Collaborators:** Use real objects. Mock only at architectural boundaries (DB, HTTP, queues).
**Direction:** Inside-out. Start with domain core, build outward.
**Key text:** *Test-Driven Development By Example* (Beck, 2002)

### Why Default to Chicago

- **Refactoring resilience.** Renaming a private method, extracting a helper class, changing internal structure — Chicago tests don't break because they test *what* the code does, not *how*.
- **Tests as specifications.** A reader understands the behavior without knowing the implementation. Tests become living documentation of what the system promises.
- **Lower maintenance cost.** Mock-heavy tests compound maintenance. Every structural change requires updating both implementation AND test mocks. Over 12 months, Chicago test suites cost significantly less to maintain.

### The Real Costs of Chicago

- **Harder failure isolation.** When a test fails, the bug might be in any collaborator in the chain, not just the tested code. You debug through layers.
  - *Mitigation:* Keep collaborator graphs shallow. Write focused tests that limit the blast radius.

- **Slower design feedback.** You discover interface problems late because you build concrete implementations first. London forces you to design interfaces upfront.
  - *Mitigation:* Sketch interfaces before coding (even without mocks). Use type annotations to define contracts.

- **Real collaborators can be expensive.** If constructing the real object requires database seeds, network connections, or complex setup, test ergonomics suffer.
  - *Mitigation:* Use in-memory fakes (not mocks) at true infrastructure boundaries. A fake repository backed by a dict is cheap to construct and behaves like the real thing.

### Chicago Example (pytest)

```python
class TestOrderTotal:
    def test_calculates_total_with_tax(self, db_session):
        # Real objects, real behavior
        product = Product(name="Widget", price=Decimal("10.00"))
        order = Order(items=[OrderItem(product=product, quantity=3)])

        total = order.calculate_total(tax_rate=Decimal("0.08"))

        assert total == Decimal("32.40")

    def test_applies_discount_before_tax(self, db_session):
        product = Product(name="Widget", price=Decimal("100.00"))
        order = Order(items=[OrderItem(product=product, quantity=1)])
        order.apply_discount(percent=Decimal("10"))

        total = order.calculate_total(tax_rate=Decimal("0.08"))

        assert total == Decimal("97.20")
```

---

## London School — At Boundaries Only

**Unit of test:** A single class. All collaborators are mocked.
**Collaborators:** Mocks, stubs, and spies for everything.
**Direction:** Outside-in. Start at the API surface, stub your way inward.
**Key text:** *Growing Object-Oriented Software, Guided by Tests* (Freeman & Pryce, 2009)

### When London Is the Right Tool

- **Verifying interaction protocols.** "Did we publish the event?" "Did we call the payment gateway with the right parameters?" These are inherently about interactions, not return values.
- **Architectural boundary tests.** The adapter layer in hexagonal architecture exists to translate between your domain and the outside world. Mocking the port and testing the adapter is exactly right.
- **Deep collaborator chains you can't construct.** If building the real object requires 8 layers of dependencies and a running message broker, mocking is pragmatic, not dogmatic.
- **Driving interface discovery.** When you don't yet know what interface a collaborator should have, London-style outside-in TDD forces you to design it from the consumer's perspective.

### When London Goes Wrong

- **Over-specification.** Testing that method A calls method B with argument C in order D. Now changing any internal detail breaks tests. The tests become a mirror of the implementation — if you can derive the test from the code, the test adds no information.
- **False confidence.** All mocks return happy-path values you defined. The real collaborator might behave differently. Your tests pass, production breaks.
- **Refactoring paralysis.** Developers avoid improving code because "it'll break 47 tests." This is the most damaging long-term effect. Teams stop refactoring, code quality degrades, and the test suite actively harms the codebase.

### London Example (pytest + mocker)

```python
class TestPaymentAdapter:
    def test_charges_gateway_with_correct_amount(self, mocker):
        # Mock the EXTERNAL boundary, not internal collaborators
        mock_gateway = mocker.patch("app.adapters.stripe.client")
        mock_gateway.charges.create.return_value = {
            "id": "ch_123",
            "status": "succeeded",
        }

        adapter = StripePaymentAdapter()
        result = adapter.charge(amount=Decimal("32.40"), currency="usd")

        mock_gateway.charges.create.assert_called_once_with(
            amount=3240,  # Stripe uses cents
            currency="usd",
        )
        assert result.transaction_id == "ch_123"
```

---

## The Hybrid: What Practitioners Actually Do

Almost everyone who practices TDD for years converges on a hybrid. This isn't a compromise — it's recognition that different parts of a system have different testing needs.

### The Boundary Principle

**If the collaborator is *yours* (you wrote it, you control it), use the real thing.**
**If it's *theirs* (external API, database, message broker), mock it.**

This maps to architecture layers:

| Layer | Testing Style | Reason |
|-------|--------------|--------|
| Controllers / API | Integration (test client) | Thin layer, test through HTTP |
| Services / Domain | Chicago (real objects) | Business logic, behavior matters |
| Adapters / Ports | London (mock external) | Boundary translation, verify protocol |

### Deeper Insight

The choice isn't about mocking philosophy — it's about **what constitutes a meaningful boundary**. London says every class is a boundary. Chicago says only architectural seams are boundaries. The right answer depends on the coupling characteristics of your code:

- **Tightly coupled internal code** (domain objects that work together) → Chicago. Mocking creates artificial seams that fight the design.
- **Loosely coupled boundary code** (adapters, gateways, event publishers) → London. The boundary IS the interesting part.

### Mocking Rules for This Project

1. **DO mock:** External HTTP APIs, database connections, Redis, Celery task queues, email services, file systems in production paths
2. **DON'T mock:** Your own services, models, utility functions, value objects, anything you wrote and control
3. **Use fakes instead of mocks when possible:** A `FakeUserRepository(dict)` is better than `Mock(spec=UserRepository)` because it has real behavior, catches more bugs, and doesn't need updating when the interface changes
4. **Always use `spec=`:** If you must mock, use `spec=RealClass` so the mock fails if the real interface changes. Unspecced mocks silently accept anything.
