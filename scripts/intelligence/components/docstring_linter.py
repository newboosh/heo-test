"""Docstring linter - validates Google-style docstrings.

Checks for:
- Missing docstrings on public functions/classes
- Docstring format compliance (first line, sections)
- Parameter documentation matches function signature
- Return type documentation present
- Exception documentation matches raises
"""

import ast
import re
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass

from scripts.intelligence.utils import ast_utils


@dataclass
class DocstringIssue:
    """A docstring validation issue."""

    name: str
    """Symbol name."""

    file: str
    """File path."""

    line: int
    """Line number."""

    severity: str
    """'error', 'warning', or 'info'."""

    issue_type: str
    """Type of issue (missing, format, args_mismatch, etc)."""

    message: str
    """Human-readable issue description."""

    suggestion: str
    """Suggestion for fixing the issue."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dict with all issue fields.
        """
        return {
            'name': self.name,
            'file': self.file,
            'line': self.line,
            'severity': self.severity,
            'issue_type': self.issue_type,
            'message': self.message,
            'suggestion': self.suggestion,
        }


class GoogleDocstringParser:
    """Parse Google-style docstrings."""

    @staticmethod
    def parse(docstring: Optional[str]) -> Dict:
        """Parse Google-style docstring into sections.

        Args:
            docstring: Raw docstring text.

        Returns:
            Dict with 'summary', 'description', 'args', 'returns', 'raises', 'example'.
        """
        if not docstring:
            return {
                'summary': None,
                'description': '',
                'args': {},
                'returns': None,
                'raises': [],
                'example': None,
            }

        lines = docstring.split('\n')
        summary = lines[0].strip() if lines else None

        # Find section headers
        result = {
            'summary': summary,
            'description': '',
            'args': {},
            'returns': None,
            'raises': [],
            'example': None,
        }

        current_section = 'description'
        current_content = []
        i = 1

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Check for section headers
            if stripped in ('Args:', 'Returns:', 'Raises:', 'Example:'):
                # Save previous section
                if current_section == 'description':
                    result['description'] = '\n'.join(current_content).strip()
                elif current_section == 'args':
                    result['args'] = GoogleDocstringParser._parse_args(current_content)
                elif current_section == 'returns':
                    result['returns'] = '\n'.join(current_content).strip()
                elif current_section == 'raises':
                    result['raises'] = GoogleDocstringParser._parse_raises(current_content)
                elif current_section == 'example':
                    result['example'] = '\n'.join(current_content).strip()

                current_section = stripped.rstrip(':').lower()
                current_content = []
            else:
                current_content.append(line)

            i += 1

        # Save final section
        if current_section == 'description':
            result['description'] = '\n'.join(current_content).strip()
        elif current_section == 'args':
            result['args'] = GoogleDocstringParser._parse_args(current_content)
        elif current_section == 'returns':
            result['returns'] = '\n'.join(current_content).strip()
        elif current_section == 'raises':
            result['raises'] = GoogleDocstringParser._parse_raises(current_content)
        elif current_section == 'example':
            result['example'] = '\n'.join(current_content).strip()

        return result

    @staticmethod
    def _parse_args(lines: List[str]) -> Dict[str, str]:
        """Parse Args section.

        Args:
            lines: Lines from the Args section.

        Returns:
            Dict mapping parameter names to descriptions.
        """
        args = {}
        current_arg = None
        current_desc = []

        # Regex to match: *args, **kwargs, param, param (type), *args (type), **kwargs (type)
        arg_line_re = re.compile(r'^\s*(\*{0,2}[A-Za-z_]\w*)(?:\s*\([^)]*\))?\s*:\s*(.*)$')

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            match = arg_line_re.match(stripped)
            if match:
                raw_name, desc = match.group(1), match.group(2)
                # Strip leading asterisks for storage (args, kwargs)
                param_name = raw_name.lstrip('*')

                # Save previous arg
                if current_arg:
                    args[current_arg] = '\n'.join(current_desc).strip()

                current_arg = param_name
                current_desc = [desc.strip()] if desc else []
            elif current_arg:
                # Continuation of description
                current_desc.append(stripped)

        if current_arg:
            args[current_arg] = '\n'.join(current_desc).strip()

        return args

    @staticmethod
    def _parse_raises(lines: List[str]) -> List[Tuple[str, str]]:
        """Parse Raises section.

        Args:
            lines: Lines from the Raises section.

        Returns:
            List of (exception_name, description) tuples.
        """
        raises = []
        current_exc = None
        current_desc = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Check if this looks like an exception line
            if ':' in stripped:
                parts = stripped.split(':', 1)
                exc_name = parts[0].strip()

                # Valid exception names are usually CamelCase and don't have spaces
                if ' ' not in exc_name and exc_name and exc_name[0].isupper():
                    # Save previous exception
                    if current_exc:
                        raises.append((current_exc, '\n'.join(current_desc).strip()))

                    current_exc = exc_name
                    current_desc = [parts[1].strip()] if len(parts) > 1 else []
                else:
                    # Not an exception, add to current description
                    if current_exc:
                        current_desc.append(stripped)
            elif current_exc:
                current_desc.append(stripped)

        if current_exc:
            raises.append((current_exc, '\n'.join(current_desc).strip()))

        return raises


class DocstringLinter:
    """Lint docstrings for Google-style compliance."""

    def __init__(self):
        """Initialize linter."""
        self.issues: List[DocstringIssue] = []

    def lint_file(self, file_path: str) -> List[DocstringIssue]:
        """Lint all docstrings in a file.

        Args:
            file_path: Path to Python file.

        Returns:
            List of docstring issues found.
        """
        self.issues = []

        tree = ast_utils.parse_python_file(file_path)
        if not tree:
            return []

        # Check module docstring
        module_doc = ast.get_docstring(tree)
        if not module_doc:
            self.issues.append(DocstringIssue(
                name='<module>',
                file=file_path,
                line=1,
                severity='warning',
                issue_type='missing',
                message='Module docstring missing.',
                suggestion='Add a docstring at the top of the file describing its purpose.'
            ))

        # Check functions and classes (including async functions)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._check_function(node, file_path)
            elif isinstance(node, ast.ClassDef):
                self._check_class(node, file_path)

        return self.issues

    def _check_function(self, func: Union[ast.FunctionDef, ast.AsyncFunctionDef],
                        file_path: str) -> None:
        """Check function docstring.

        Args:
            func: FunctionDef or AsyncFunctionDef node.
            file_path: File path.
        """
        # Skip private functions starting with _
        if func.name.startswith('_'):
            return

        docstring = ast.get_docstring(func)

        if not docstring:
            self.issues.append(DocstringIssue(
                name=func.name,
                file=file_path,
                line=func.lineno,
                severity='error',
                issue_type='missing',
                message=f"Function '{func.name}' has no docstring.",
                suggestion='Add a docstring with summary, args, and returns sections.'
            ))
            return

        # Parse docstring
        parsed = GoogleDocstringParser.parse(docstring)

        # Check summary line
        self._check_summary(func.name, file_path, func.lineno, parsed['summary'])

        # Check args match signature
        self._check_function_args(
            func, file_path, func.lineno, parsed['args']
        )

        # Check returns if function returns value
        self._check_returns(func, file_path, func.lineno, parsed['returns'])

        # Check raises match exceptions
        self._check_raises(func, file_path, func.lineno, parsed['raises'])

    def _check_class(self, cls: ast.ClassDef, file_path: str) -> None:
        """Check class docstring.

        Args:
            cls: ClassDef node.
            file_path: File path.
        """
        docstring = ast.get_docstring(cls)

        if not docstring:
            self.issues.append(DocstringIssue(
                name=cls.name,
                file=file_path,
                line=cls.lineno,
                severity='error',
                issue_type='missing',
                message=f"Class '{cls.name}' has no docstring.",
                suggestion='Add a docstring with summary and description.'
            ))
            return

        # Check summary line
        parsed = GoogleDocstringParser.parse(docstring)
        self._check_summary(cls.name, file_path, cls.lineno, parsed['summary'])

        # Check __init__ if present
        init = next(
            (n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '__init__'),
            None
        )
        if init:
            init_doc = ast.get_docstring(init)
            if not init_doc:
                self.issues.append(DocstringIssue(
                    name=f"{cls.name}.__init__",
                    file=file_path,
                    line=init.lineno,
                    severity='warning',
                    issue_type='missing',
                    message="__init__ has no docstring for parameters.",
                    suggestion='Add docstring describing constructor parameters.'
                ))

    def _check_summary(self, name: str, file_path: str, line: int,
                      summary: Optional[str]) -> None:
        """Check summary line format.

        Args:
            name: Symbol name.
            file_path: File path.
            line: Line number.
            summary: Summary line.
        """
        if not summary:
            self.issues.append(DocstringIssue(
                name=name,
                file=file_path,
                line=line,
                severity='error',
                issue_type='format',
                message="Docstring has no summary line.",
                suggestion='First line should be a complete sentence (ends with period).'
            ))
            return

        # Check if ends with proper punctuation (., !, ?)
        if not summary.endswith(('.', '!', '?')):
            self.issues.append(DocstringIssue(
                name=name,
                file=file_path,
                line=line,
                severity='warning',
                issue_type='format',
                message="Summary line should end with punctuation (., !, ?).",
                suggestion=f'Change to: "{summary}."'
            ))

        # Check if too long
        if len(summary) > 80:
            self.issues.append(DocstringIssue(
                name=name,
                file=file_path,
                line=line,
                severity='warning',
                issue_type='format',
                message="Summary line is too long (>80 chars).",
                suggestion=f'Keep it concise: "{summary[:77]}..."'
            ))

    def _check_function_args(self, func: Union[ast.FunctionDef, ast.AsyncFunctionDef],
                            file_path: str, line: int,
                            doc_args: Dict[str, str]) -> None:
        """Check function arguments documentation.

        Args:
            func: FunctionDef or AsyncFunctionDef node.
            file_path: File path.
            line: Line number.
            doc_args: Documented args from docstring.
        """
        # Get function signature args (excluding self/cls)
        sig_args = [
            arg.arg for arg in func.args.args
            if arg.arg not in ('self', 'cls')
        ]

        # Add *args if present
        if func.args.vararg:
            sig_args.append(func.args.vararg.arg)

        # Add **kwargs if present
        if func.args.kwarg:
            sig_args.append(func.args.kwarg.arg)

        # Add keyword-only args
        sig_args.extend(arg.arg for arg in func.args.kwonlyargs)

        # Check each documented arg exists in signature
        for doc_arg in doc_args:
            if doc_arg not in sig_args:
                self.issues.append(DocstringIssue(
                    name=func.name,
                    file=file_path,
                    line=line,
                    severity='warning',
                    issue_type='args_mismatch',
                    message=f"Documented arg '{doc_arg}' not in function signature.",
                    suggestion=f'Remove "{doc_arg}" from Args or add it to the function.'
                ))

        # Check each signature arg is documented
        for sig_arg in sig_args:
            if sig_arg not in doc_args:
                self.issues.append(DocstringIssue(
                    name=func.name,
                    file=file_path,
                    line=line,
                    severity='warning',
                    issue_type='args_mismatch',
                    message=f"Parameter '{sig_arg}' not documented in Args section.",
                    suggestion=f'Add "{sig_arg}:" to Args section with description.'
                ))

    def _check_returns(self, func: Union[ast.FunctionDef, ast.AsyncFunctionDef],
                      file_path: str, line: int,
                      doc_returns: Optional[str]) -> None:
        """Check return documentation.

        Args:
            func: FunctionDef or AsyncFunctionDef node.
            file_path: File path.
            line: Line number.
            doc_returns: Documented returns from docstring.
        """
        # Check if function returns a value
        has_return = any(
            isinstance(node, ast.Return) and node.value
            for node in ast.walk(func)
        )

        if has_return and not doc_returns:
            self.issues.append(DocstringIssue(
                name=func.name,
                file=file_path,
                line=line,
                severity='warning',
                issue_type='returns_missing',
                message="Function returns value but has no Returns documentation.",
                suggestion='Add Returns section describing the return value.'
            ))

    def _check_raises(self, func: Union[ast.FunctionDef, ast.AsyncFunctionDef],
                     file_path: str, line: int,
                     doc_raises: List[Tuple[str, str]]) -> None:
        """Check exception documentation.

        Args:
            func: FunctionDef or AsyncFunctionDef node.
            file_path: File path.
            line: Line number.
            doc_raises: Documented exceptions from docstring.
        """
        # Find explicit raises
        raised_exceptions = set()
        for node in ast.walk(func):
            if isinstance(node, ast.Raise) and node.exc:
                if isinstance(node.exc, ast.Call):
                    # raise ValueError(...)
                    if isinstance(node.exc.func, ast.Name):
                        raised_exceptions.add(node.exc.func.id)
                elif isinstance(node.exc, ast.Name):
                    # raise e
                    raised_exceptions.add(node.exc.id)

        # Check documented exceptions exist
        doc_exc_names = [exc for exc, _ in doc_raises]
        for doc_exc in doc_exc_names:
            if doc_exc not in raised_exceptions and doc_exc not in ('Exception', 'BaseException'):
                self.issues.append(DocstringIssue(
                    name=func.name,
                    file=file_path,
                    line=line,
                    severity='info',
                    issue_type='raises_mismatch',
                    message=f"Documented exception '{doc_exc}' not explicitly raised.",
                    suggestion=f'Remove "{doc_exc}" from Raises or ensure it is raised.'
                ))

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all issues found.

        Returns:
            Dict with 'total', 'by_severity', and 'by_type' counts.
        """
        summary = {
            'total': len(self.issues),
            'by_severity': {},
            'by_type': {},
        }

        for issue in self.issues:
            summary['by_severity'][issue.severity] = \
                summary['by_severity'].get(issue.severity, 0) + 1
            summary['by_type'][issue.issue_type] = \
                summary['by_type'].get(issue.issue_type, 0) + 1

        return summary
