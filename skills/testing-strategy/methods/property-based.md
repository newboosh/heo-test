# Property-Based Testing

**Key text:** *Property-Based Testing with PropEr, Erlang, and Elixir* (Hebert, 2019)
**Python framework:** Hypothesis

## What It Actually Is

Instead of choosing specific inputs and asserting specific outputs, you declare **universal properties** and let the framework generate hundreds of inputs to try to violate them.

This is NOT "random testing." It's **specification testing** — you formalize what must always be true.

## Property Categories (Ranked by Usefulness)

### Tier 1 — High Value, Easy to Write

| Property | Pattern | Example |
|----------|---------|---------|
| **Roundtrip** | `decode(encode(x)) == x` | JSON serialization, URL encoding, compression |
| **Idempotence** | `f(f(x)) == f(x)` | Normalization, deduplication, formatting |
| **Invariant** | Output preserves a property of input | `len(sort(xs)) == len(xs)`, no elements lost |

### Tier 2 — Valuable, Requires Thought

| Property | Pattern | Example |
|----------|---------|---------|
| **Oracle** | `fast_impl(x) == reference_impl(x)` | Compare optimized code against naive-but-correct version |
| **Metamorphic** | Relating outputs of related inputs | `search(q1+q2) ⊆ search(q1)` |
| **Commutativity** | Order doesn't matter | `merge(a, b) == merge(b, a)` |

### Tier 3 — Powerful but Complex

| Property | Pattern | Example |
|----------|---------|---------|
| **Model-based** | System matches a state machine model | Stateful protocol testing |
| **Algebraic** | Laws from mathematics apply | Monoid laws, functor laws |

## The Restated-Implementation Trap

The most common mistake. If your property is just the implementation rewritten, you've tested nothing.

```python
# BAD — restates the implementation
@given(st.integers(), st.integers())
def test_add(a, b):
    assert add(a, b) == a + b  # This IS the implementation

# GOOD — tests a property that's true regardless of implementation
@given(st.integers(), st.integers())
def test_add_satisfies_commutativity(a, b):
    assert add(a, b) == add(b, a)

@given(st.integers())
def test_add_returns_input_when_identity_applied(a):
    assert add(a, 0) == a
```

**The test:** Can you write this property without looking at the implementation? If yes, it's a real property. If you need to trace through the code to write it, you're restating.

## Practical Considerations

### Generator Investment

Custom types need custom generators. For a `User` object, you need a strategy that produces valid users. For complex domain objects, this is substantial work.

```python
# Simple — use built-in strategies
@given(st.lists(st.integers()))
def test_sort_preserves_length(xs):
    assert len(sorted(xs)) == len(xs)

# Complex — custom strategy needed
user_strategy = st.builds(
    User,
    email=st.emails(),
    name=st.text(min_size=1, max_size=100),
    age=st.integers(min_value=0, max_value=150),
)
```

**Start with primitives and built-in types.** Only build custom generators when you've proven the approach works for simpler cases.

### Shrinking

When a property fails for input `[847, -3, 0, 291, 44]`, the framework shrinks to the minimal failing case (maybe `[0, -1]`). This is incredibly valuable for debugging.

**Warning:** Custom generators with `filter()` or complex `assume()` calls produce bad shrinks. Prefer `st.builds()` and `st.from_regex()` over filtering.

### Runtime

Property tests run hundreds of cases per test function. A module with 20 property tests at 200 examples each = 4000 test executions. This is slower than example-based tests.

**Mitigations:**
- Use `@settings(max_examples=50)` for fast feedback during development
- Use `@settings(max_examples=500)` in CI for thorough checking
- Profile your generators — slow generators multiply runtime

## Decision: When to Use It

```
Is the function pure (input → output, no side effects)?
├── Yes
│   ├── Does it transform data? (parse, encode, sort, filter)
│   │   └── YES → Property-based (roundtrip, invariant)
│   ├── Does it compute? (math, aggregation, scoring)
│   │   └── YES → Property-based (oracle, algebraic)
│   └── Is the input space large? (strings, lists, nested structures)
│       └── YES → Property-based (find edge cases humans miss)
└── No (side effects, I/O, state)
    └── Stick with example-based tests
```

## Integration With Example Tests

Property tests are NOT a replacement for example tests. They serve different purposes:
- **Example tests** document specific scenarios for humans ("when the cart is empty, total is zero")
- **Property tests** explore the input space for machines ("for ALL carts, total >= 0")

Best used together. Write examples first for documentation, then add properties for coverage.

## Examples for This Project (Hypothesis)

```python
from hypothesis import given, settings, strategies as st

@given(st.text())
def test_slugify_returns_same_when_applied_twice(text):
    """Slugifying twice gives the same result as once."""
    assert slugify(slugify(text)) == slugify(text)

@given(st.lists(st.integers()))
def test_sort_preserves_element_count(xs):
    """Sorting doesn't add or remove elements."""
    sorted_xs = sorted(xs)
    assert len(sorted_xs) == len(xs)
    assert sorted(sorted_xs) == sorted(xs)  # Same multiset

@given(st.binary())
def test_compress_returns_original_after_roundtrip(data):
    """Compression roundtrips perfectly."""
    assert decompress(compress(data)) == data

@given(st.decimals(min_value=0, max_value=10000, places=2))
def test_apply_discount_satisfies_bounds(price):
    """No discount produces a negative or higher total."""
    for pct in [Decimal("0"), Decimal("10"), Decimal("50"), Decimal("100")]:
        discounted = apply_discount(price, pct)
        assert Decimal("0") <= discounted <= price
```
