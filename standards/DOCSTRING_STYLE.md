# Docstring Style Standard

## Style: Google

This project uses **Google-style docstrings** as defined in the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings).

## Format

### Functions and Methods

```python
def function_name(param1: str, param2: int = 0) -> bool:
    """Short one-line summary ending with period.

    Longer description if needed. Can span multiple paragraphs.
    Explain the purpose, not the implementation.

    Args:
        param1: Description of param1. No type here (use annotations).
        param2: Description of param2. Mention default behavior if relevant.

    Returns:
        Description of return value. For bool, describe True/False meaning.

    Raises:
        ValueError: When param1 is empty.
        TypeError: When param2 is not an integer.

    Example:
        >>> function_name("hello", 5)
        True
    """
```

### Classes

```python
class ClassName:
    """Short one-line summary of the class.

    Longer description explaining the purpose and usage of the class.

    Attributes:
        attr1: Description of public attribute.
        attr2: Description of another attribute.

    Example:
        >>> obj = ClassName("value")
        >>> obj.do_something()
    """
```

### Modules

```python
"""Short one-line summary of module purpose.

Longer description if needed. Explain what this module provides
and when to use it.

Example:
    from module import function
    result = function(data)
"""
```

## Rules

### Required

| Element | Docstring required? |
|---------|---------------------|
| Public functions | Yes |
| Public methods | Yes |
| Public classes | Yes |
| Modules with public API | Yes |
| Private functions (`_name`) | No, but encouraged for complex logic |
| Dunder methods (`__init__`) | Yes, describe parameters |

### Summary Line

- First line is a **complete sentence** ending with a period
- Fits on one line (< 80 chars)
- Uses imperative mood: "Return the user" not "Returns the user"
- Describes what the function **does**, not how

```python
# Good
"""Validate email format against RFC 5322."""

# Bad
"""This function validates an email."""  # Don't say "this function"
"""validate email"""                      # Not a sentence
"""Validates the email format"""          # Descriptive, not imperative
```

### Args Section

- One line per parameter
- Parameter name followed by colon and description
- Don't repeat type annotations in docstring
- Describe meaning, not just restate the name

```python
# Good
Args:
    email: The email address to validate.
    strict: If True, reject addresses with plus signs.

# Bad
Args:
    email (str): The email parameter.  # Don't include type
    strict: strict flag                  # Don't restate the name
```

### Returns Section

- Describe the return value's meaning
- For booleans, explain True and False cases
- For None returns, omit the section or explain side effects

```python
# Good
Returns:
    True if the email is valid, False otherwise.

Returns:
    The parsed configuration dictionary, or None if file not found.

# Bad
Returns:
    bool  # Just the type, no meaning
```

### Raises Section

- List exceptions that the function explicitly raises
- Don't list exceptions from called functions unless caught/reraised
- Include the condition that triggers each exception

```python
# Good
Raises:
    ValueError: If email is empty or None.
    ValidationError: If email format is invalid.

# Bad
Raises:
    Exception: If something goes wrong.  # Too vague
```

## Examples

### Complete Function

```python
def resolve_symbol(name: str, index: SymbolIndex) -> ResolvedSymbol | None:
    """Resolve a symbol name to its location in the codebase.

    Looks up the symbol in the index and returns its file path and line
    number. For ambiguous symbols (defined in multiple files), returns
    None and logs a warning.

    Args:
        name: The symbol name to resolve. Can be qualified (e.g., "Class.method").
        index: The symbol index to search in.

    Returns:
        ResolvedSymbol with file path and line number, or None if not found
        or ambiguous.

    Raises:
        IndexError: If the index is empty or corrupted.

    Example:
        >>> symbol = resolve_symbol("validate_email", index)
        >>> print(f"{symbol.file}:{symbol.line}")
        app/validators.py:42
    """
```

### Complete Class

```python
class SymbolIndex:
    """Index of all symbols defined in the codebase.

    Maintains a mapping from symbol names to their locations, supporting
    fast lookup for documentation cross-referencing.

    Attributes:
        symbols: Dict mapping symbol names to lists of SymbolEntry.
        file_count: Number of files indexed.
        generated: ISO timestamp of when the index was built.

    Example:
        >>> index = SymbolIndex.build(root_path)
        >>> entries = index.symbols.get("validate_email", [])
    """
```

## Automated Extraction

The librarian system parses docstrings to extract:

1. **Summary**: First line, used for content profile index
2. **Args**: Parameter documentation
3. **Returns**: Return value documentation
4. **Raises**: Exception documentation

Docstrings that don't follow this format will be stored as `style: "plain"` with reduced extraction quality.

## Validation

Docstring validation is performed automatically during the intelligence build process. The `DocstringLinter` component checks for:

- Missing docstrings on public functions/classes
- Docstring format compliance (summary line, sections)
- Parameter documentation matching function signature
- Return type documentation

To run the full intelligence build (which includes docstring linting):

```bash
python -m scripts.intelligence build
```
