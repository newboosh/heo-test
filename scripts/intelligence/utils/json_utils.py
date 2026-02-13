"""JSON serialization utilities with custom handlers.

Provides:
- Safe JSON encoding with custom type handlers
- Pretty-printing and minification options
- Type-safe serialization
"""

import json
from typing import Any, Dict, Optional
from pathlib import Path
from datetime import datetime


class IntelligenceEncoder(json.JSONEncoder):
    """Custom JSON encoder for intelligence system objects.

    Handles:
    - Path objects
    - Datetime objects
    - Sets (converts to sorted lists)
    - Custom objects with __dict__
    """

    def default(self, obj: Any) -> Any:
        """Encode non-standard types.

        Args:
            obj: Object to encode.

        Returns:
            JSON-serializable representation.
        """
        if isinstance(obj, Path):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, set):
            return sorted(list(obj))
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return super().default(obj)


def dumps(data: Any, pretty: bool = False) -> str:
    """Serialize object to JSON string.

    Args:
        data: Object to serialize.
        pretty: If True, format with indentation.

    Returns:
        JSON string.
    """
    if pretty:
        return json.dumps(data, cls=IntelligenceEncoder, indent=2, sort_keys=True)
    else:
        return json.dumps(data, cls=IntelligenceEncoder, separators=(',', ':'))


def loads(json_str: str) -> Any:
    """Deserialize JSON string to object.

    Args:
        json_str: JSON string.

    Returns:
        Deserialized object.

    Raises:
        json.JSONDecodeError: If JSON is invalid.
    """
    return json.loads(json_str)


def dump_file(file_path: str, data: Any, pretty: bool = True) -> bool:
    """Write object to JSON file.

    Args:
        file_path: Path to output file (creates parent directories).
        data: Object to write.
        pretty: If True, format with indentation.

    Returns:
        True if successful, False otherwise.
    """
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(dumps(data, pretty=pretty))
        return True
    except (IOError, PermissionError, TypeError):
        return False


def load_file(file_path: str) -> Optional[Any]:
    """Load object from JSON file.

    Args:
        file_path: Path to JSON file.

    Returns:
        Deserialized object or None if load fails.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return loads(f.read())
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def merge_dicts(*dicts: Dict) -> Dict:
    """Recursively merge dictionaries.

    Later dicts override earlier ones.

    Args:
        *dicts: Variable number of dictionaries.

    Returns:
        Merged dictionary.
    """
    result = {}
    for d in dicts:
        for key, value in d.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = merge_dicts(result[key], value)
            else:
                result[key] = value
    return result


def filter_dict(data: Dict, keys: list) -> Dict:
    """Filter dictionary to only include specified keys.

    Args:
        data: Dictionary to filter.
        keys: List of keys to keep.

    Returns:
        Filtered dictionary.
    """
    return {k: v for k, v in data.items() if k in keys}
