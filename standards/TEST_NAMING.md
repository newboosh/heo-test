# Test Naming Standard

## Grammar

```
test_<SUBJECT>_<PREPOSITION>_<SCENARIO>
```

| Part | Description | Required |
|------|-------------|----------|
| `test_` | Pytest prefix | Yes |
| `SUBJECT` | Function, method, or class being tested | Yes |
| `PREPOSITION` | Links subject to scenario | Yes |
| `SCENARIO` | The condition, input, or expected outcome | Yes |

## Prepositions

| Preposition | Use when... | Example |
|-------------|-------------|---------|
| `with` | Testing specific input type | `test_parse_config_with_invalid_yaml` |
| `when` | Testing specific state/condition | `test_login_when_token_expired` |
| `returns` | Asserting return value | `test_validate_email_returns_false` |
| `raises` | Asserting exception | `test_load_file_raises_on_missing` |
| `for` | Testing specific case/format | `test_format_date_for_iso8601` |
| `accepts` | Positive validation test | `test_validate_email_accepts_plus_addressing` |
| `rejects` | Negative validation test | `test_validate_email_rejects_empty_string` |
| `creates` | Testing side effect (file, record) | `test_build_index_creates_output_file` |
| `updates` | Testing mutation | `test_save_user_updates_timestamp` |
| `deletes` | Testing removal | `test_cleanup_deletes_temp_files` |
| `preserves` | Testing invariant property | `test_sort_preserves_element_count` |
| `satisfies` | Testing general property | `test_add_satisfies_commutativity` |

## Subject Matching

The SUBJECT must match a symbol name in the codebase:

```python
# Function: validate_email
def validate_email(email: str) -> bool: ...

# Tests for this function:
test_validate_email_with_empty_string      # ✓ SUBJECT matches
test_validate_email_returns_true           # ✓ SUBJECT matches
test_email_validation_works                # ✗ SUBJECT doesn't match
```

For methods, include the class name with underscore:

```python
# Method: UserService.create_user
class UserService:
    def create_user(self, data): ...

# Tests:
test_user_service_create_user_with_valid_data    # ✓
test_UserService_create_user_with_valid_data     # ✓ (CamelCase ok)
```

## Scenario Guidelines

Keep scenarios concise but descriptive:

| Good | Bad |
|------|-----|
| `with_empty_string` | `with_an_empty_string_passed_as_input` |
| `when_not_authenticated` | `when_user_is_not_authenticated` |
| `raises_on_missing` | `raises_file_not_found_error_when_file_missing` |

Use underscores to separate words within the scenario:

```
test_parse_json_with_nested_objects     # ✓
test_parse_json_withNestedObjects       # ✗
```

## Examples

```python
# Good: Clear subject and scenario
def test_classify_file_with_directory_rule(): ...
def test_build_symbol_index_returns_empty_for_no_files(): ...
def test_extract_docstring_with_google_style(): ...
def test_hash_symbol_raises_on_syntax_error(): ...

# Bad: Subject unclear or doesn't match function
def test_classification_works(): ...           # What function?
def test_it_should_validate_correctly(): ...   # No subject
def test_error_handling(): ...                 # Too vague
```

## Property-Based Test Naming

Property-based tests (Hypothesis) declare universal properties rather than specific examples. Map property categories to the naming grammar:

| Property Type | Preposition | Example |
|---------------|-------------|---------|
| Roundtrip | `returns` | `test_compress_returns_original_after_roundtrip` |
| Idempotence | `returns` or `when` | `test_slugify_returns_same_when_applied_twice` |
| Invariant | `preserves` | `test_sort_preserves_element_count` |
| General property | `satisfies` | `test_add_satisfies_commutativity` |
| Identity | `returns` | `test_add_returns_input_when_identity_applied` |
| Bounds | `satisfies` | `test_apply_discount_satisfies_bounds` |

The SUBJECT must still match a function or method name in the codebase. The SCENARIO should name the property being tested, not restate the implementation.

See `/testing-strategy` methods/property-based.md for when to use property-based testing.

## Rationale

This naming convention enables:

1. **Automated mapping**: Tests can be linked to symbols by parsing the SUBJECT
2. **Behavior extraction**: PREPOSITION + SCENARIO describe what the code does
3. **Searchability**: `grep test_validate_email` finds all tests for that function
4. **Documentation**: Test names read as specifications

## Parsing Reference

For automated extraction:

```python
import re

TEST_PATTERN = re.compile(
    r'^test_'
    r'(?P<subject>[a-z][a-z0-9_]*?)'
    r'_(?P<preposition>with|when|returns|raises|for|accepts|rejects|creates|updates|deletes|preserves|satisfies)'
    r'_(?P<scenario>.+)$'
)

# Example:
match = TEST_PATTERN.match("test_validate_email_with_empty_string")
# subject: "validate_email"
# preposition: "with"
# scenario: "empty_string"
```
