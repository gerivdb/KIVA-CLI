"""
Stub Generator from Tests (PRD-KIVA-002)

Analyzes pytest test files via AST extraction and generates minimal stub
implementations (classes, functions, dataclasses, enums) so that tests compile
and run (even if they still fail on logic).

Usage:
    generator = StubGenerator(language="python", use_canonical_types=True)
    stubs = generator.generate_from_test_file("tests/test_foo.py")
    generator.write_stubs(stubs, output_dir="src/generated/")

CLI:
    kiva generate stubs --from-tests tests/test_foo.py --output src/generated/
"""

from __future__ import annotations

import ast
import hashlib
import logging
import os
import re
import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from kiva_cli.core.types import FrameworkType, LifecycleState, ValidationState

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class ExtractedFunction:
    """A function/method extracted from a test file."""
    name: str
    parameters: List[Tuple[str, Optional[str]]]  # (name, type_annotation)
    return_type: Optional[str] = None
    is_async: bool = False
    is_method: bool = False  # True if first param is 'self'
    body_hints: List[str] = field(default_factory=list)  # assertions, calls found in test
    source_class: Optional[str] = None  # class this method belongs to (inferred)


@dataclass
class ExtractedClass:
    """A class extracted from test usage patterns."""
    name: str
    methods: List[ExtractedFunction] = field(default_factory=list)
    base_classes: List[str] = field(default_factory=list)


@dataclass
class ExtractedImport:
    """An import extracted from a test file."""
    module: str
    names: List[str] = field(default_factory=list)
    is_from_import: bool = False


@dataclass
class GeneratedStub:
    """A generated stub file ready to be written."""
    filename: str
    content: str
    target_class: str
    intent_hash: str = ""
    source_test: str = ""

    def __post_init__(self):
        if not self.intent_hash:
            self.intent_hash = hashlib.sha256(self.content.encode()).hexdigest()[:16]


# =============================================================================
# Test File Analyzer (AST-based)
# =============================================================================

class TestFileAnalyzer:
    """
    Parses a pytest test file using AST to extract:
    - Classes under test (from instantiation patterns)
    - Function/method signatures (from call patterns)
    - Import dependencies
    - Type hints from assertions
    """

    def __init__(self, source_code: str, filename: str = "<unknown>"):
        self.source_code = source_code
        self.filename = filename
        self.tree = ast.parse(source_code)
        self.imports: List[ExtractedImport] = []
        self.classes: List[ExtractedClass] = []
        self.functions: List[ExtractedFunction] = []
        self._class_usage: Dict[str, Dict[str, Any]] = {}  # class_name -> {methods, attrs}

    def analyze(self) -> "TestFileAnalyzer":
        """Run full analysis on the test file."""
        self._extract_imports()
        self._extract_test_functions()
        self._extract_class_usage()
        self._build_class_definitions()
        return self

    def _extract_imports(self) -> None:
        """Extract all imports from the test file."""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.imports.append(ExtractedImport(
                        module=alias.name,
                        names=[alias.asname or alias.name],
                    ))
            elif isinstance(node, ast.ImportFrom):
                names = [alias.name for alias in node.names]
                self.imports.append(ExtractedImport(
                    module=node.module or "",
                    names=names,
                    is_from_import=True,
                ))

    def _extract_test_functions(self) -> None:
        """Extract test function definitions."""
        for node in ast.iter_child_nodes(self.tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                params = self._extract_params(node)
                func = ExtractedFunction(
                    name=node.name,
                    parameters=params,
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                )
                # Extract body hints (assertions, calls)
                func.body_hints = self._extract_body_hints(node)
                self.functions.append(func)

    def _extract_params(self, node: ast.FunctionDef) -> List[Tuple[str, Optional[str]]]:
        """Extract function parameters with type annotations."""
        params = []
        for arg in node.args.args:
            annotation = None
            if arg.annotation:
                annotation = ast.dump(arg.annotation)
                # Simplify common annotations
                annotation = self._simplify_annotation(arg.annotation)
            params.append((arg.arg, annotation))
        return params

    def _simplify_annotation(self, node: ast.expr) -> str:
        """Convert AST annotation node to a readable string."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Subscript):
            base = self._simplify_annotation(node.value)
            slice_node = node.slice
            if isinstance(slice_node, ast.Name):
                return f"{base}[{slice_node.id}]"
            elif isinstance(slice_node, ast.Tuple):
                elements = [self._simplify_annotation(e) for e in slice_node.elts]
                return f"{base}[{', '.join(elements)}]"
            return f"{base}[...]"
        elif isinstance(node, ast.Attribute):
            return f"{self._simplify_annotation(node.value)}.{node.attr}"
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            # Handle X | Y syntax (Python 3.10+)
            left = self._simplify_annotation(node.left)
            right = self._simplify_annotation(node.right)
            return f"{left} | {right}"
        return ast.dump(node)

    def _extract_body_hints(self, node: ast.FunctionDef) -> List[str]:
        """Extract assertion and call patterns from test body."""
        hints = []
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Assert):
                hints.append(f"assert: {ast.dump(stmt.test)[:100]}")
            elif isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Attribute):
                    hints.append(f"call: {stmt.func.attr}")
                elif isinstance(stmt.func, ast.Name):
                    hints.append(f"call: {stmt.func.id}")
        return hints

    def _extract_class_usage(self) -> None:
        """
        Extract class usage patterns from test functions.
        Looks for: ClassName() instantiation, method calls, attribute access.
        Tracks variable assignments: obj = ClassName() -> obj.method() maps to ClassName.
        """
        # First pass: find all direct ClassName() calls and assignments
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                class_name = node.func.id
                if class_name[0].isupper() and class_name not in self._class_usage:
                    self._class_usage[class_name] = {"methods": set(), "attrs": set()}

        # Second pass: find assignments like `pm = ClassName()` within function scopes
        var_to_class: Dict[str, str] = {}
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                # Walk this function's body to find assignments
                for stmt in ast.walk(node):
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Name) and isinstance(stmt.value, ast.Call):
                                if isinstance(stmt.value.func, ast.Name):
                                    class_name = stmt.value.func.id
                                    if class_name[0].isupper():
                                        var_to_class[target.id] = class_name
                                        if class_name not in self._class_usage:
                                            self._class_usage[class_name] = {"methods": set(), "attrs": set()}

        # Third pass: find method calls on known objects
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                method_name = node.func.attr
                if isinstance(node.func.value, ast.Name):
                    obj_name = node.func.value.id
                    # Direct: obj was assigned from ClassName()
                    if obj_name in var_to_class:
                        cls_name = var_to_class[obj_name]
                        self._class_usage[cls_name]["methods"].add(method_name)
                    # Fuzzy match: obj_name resembles a known class
                    else:
                        for cls_name in self._class_usage:
                            if obj_name.lower() in cls_name.lower() or cls_name.lower() in obj_name.lower():
                                self._class_usage[cls_name]["methods"].add(method_name)

            # Attribute access: obj.attr
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                obj_name = node.value.id
                if obj_name in var_to_class:
                    self._class_usage[var_to_class[obj_name]]["attrs"].add(node.attr)
                else:
                    for cls_name in self._class_usage:
                        if obj_name.lower() in cls_name.lower():
                            self._class_usage[cls_name]["attrs"].add(node.attr)

    def _build_class_definitions(self) -> None:
        """Build ExtractedClass objects from usage patterns."""
        for class_name, usage in self._class_usage.items():
            cls = ExtractedClass(name=class_name)
            for method_name in usage["methods"]:
                # Skip __init__ and dunder methods
                if method_name.startswith("__"):
                    continue
                func = ExtractedFunction(
                    name=method_name,
                    parameters=[("self", None)],
                    is_method=True,
                    source_class=class_name,
                )
                cls.methods.append(func)
            self.classes.append(cls)

    def get_imports_for_stub(self) -> List[ExtractedImport]:
        """Return imports that should be included in the generated stub."""
        return self.imports


# =============================================================================
# Code Generator
# =============================================================================

class StubCodeGenerator:
    """
    Generates minimal Python stub code from extracted test information.
    """

    # Canonical type imports to use when use_canonical_types is True
    CANONICAL_IMPORTS = [
        "from kiva_cli.core.types import (",
        "    ValidationState,",
        "    LifecycleState,",
        "    FrameworkType,",
        "    ProjectConfig,",
        "    KivaResult,",
        "    DeploymentResult,",
        "    IntentHash,",
        "    Template,",
        "    DeploymentStrategy,",
        ")",
    ]

    # Default return values by type annotation
    DEFAULT_RETURNS: Dict[str, str] = {
        "bool": "False",
        "int": "0",
        "float": "0.0",
        "str": '""',
        "list": "[]",
        "dict": "{}",
        "List": "[]",
        "Dict": "{}",
        "Optional": "None",
        "Tuple": "()",
        "None": "None",
    }

    def __init__(self, use_canonical_types: bool = True):
        self.use_canonical_types = use_canonical_types

    def generate_class_stub(self, cls: ExtractedClass, source_test: str = "") -> GeneratedStub:
        """Generate a complete class stub."""
        lines = []

        # Header with IntentHash
        intent_hash = hashlib.sha256(f"{cls.name}:{source_test}".encode()).hexdigest()[:16]
        lines.append(f'# Generated by KIVA Stub Generator - IntentHash: 0x{intent_hash}')
        lines.append(f'# Source: {source_test}')
        lines.append(f'# Generated: {datetime.now().isoformat()}')
        lines.append("")

        # Imports
        if self.use_canonical_types:
            lines.extend(self.CANONICAL_IMPORTS)
            lines.append("")

        lines.append("from dataclasses import dataclass, field")
        lines.append("from typing import Optional, List, Dict, Tuple, Any")
        lines.append("from pathlib import Path")
        lines.append("")

        # Class definition
        lines.append(f"class {cls.name}:")
        lines.append(f'    """TODO: Auto-generated stub for {cls.name}."""')
        lines.append("")

        if not cls.methods:
            lines.append("    pass")
        else:
            for method in cls.methods:
                method_lines = self._generate_method_stub(method)
                lines.extend(method_lines)
                lines.append("")

        content = "\n".join(lines)
        filename = f"{cls.name.lower()}.py"

        return GeneratedStub(
            filename=filename,
            content=content,
            target_class=cls.name,
            intent_hash=intent_hash,
            source_test=source_test,
        )

    def _generate_method_stub(self, func: ExtractedFunction) -> List[str]:
        """Generate a method stub."""
        lines = []

        # Build parameter list
        params = []
        for param_name, param_type in func.parameters:
            if param_name == "self":
                params.append("self")
            elif param_type:
                params.append(f"{param_name}: {param_type}")
            else:
                params.append(param_name)

        param_str = ", ".join(params)

        # Determine return type
        return_type = func.return_type or "Any"
        if func.return_type is None:
            # Try to infer from body hints
            for hint in func.body_hints:
                if "assert" in hint and "True" in hint:
                    return_type = "bool"
                    break

        # Method signature
        async_prefix = "async " if func.is_async else ""
        lines.append(f"    {async_prefix}def {func.name}({param_str}) -> {return_type}:")

        # Docstring
        lines.append(f'        """TODO: Implement {func.name}."""')

        # Body — minimal return or raise
        default_return = self._get_default_return(return_type)
        if default_return == "raise":
            lines.append(f'        raise NotImplementedError("{func.name} — auto-generated stub")')
        else:
            lines.append(f"        return {default_return}")

        return lines

    def _get_default_return(self, return_type: str) -> str:
        """Get a default return value for a given type."""
        # Check exact match first
        if return_type in self.DEFAULT_RETURNS:
            return self.DEFAULT_RETURNS[return_type]

        # Check partial matches — sort by key length descending to match
        # more specific patterns first (e.g. "List[str]" before "str")
        for type_key in sorted(self.DEFAULT_RETURNS.keys(), key=len, reverse=True):
            if type_key in return_type:
                # Don't match "str" inside "List[str]" if we already matched "List"
                if type_key == "str" and any(k in return_type for k in ("List", "Dict", "Tuple", "Optional")):
                    continue
                return self.DEFAULT_RETURNS[type_key]

        # For complex types, return None or raise
        if "Tuple" in return_type:
            return "()"
        if "bool" in return_type.lower():
            return "False"

        # Default: raise NotImplemented for non-trivial types
        return "raise"

    def generate_function_stub(self, func: ExtractedFunction, source_test: str = "") -> GeneratedStub:
        """Generate a standalone function stub."""
        lines = []

        intent_hash = hashlib.sha256(f"{func.name}:{source_test}".encode()).hexdigest()[:16]
        lines.append(f'# Generated by KIVA Stub Generator - IntentHash: 0x{intent_hash}')
        lines.append(f'# Source: {source_test}')
        lines.append("")

        if self.use_canonical_types:
            lines.extend(self.CANONICAL_IMPORTS)
            lines.append("")

        lines.append("from typing import Optional, List, Dict, Tuple, Any")
        lines.append("")

        # Build parameter list
        params = []
        for param_name, param_type in func.parameters:
            if param_name == "self":
                continue  # Skip self for standalone functions
            if param_type:
                params.append(f"{param_name}: {param_type}")
            else:
                params.append(param_name)

        param_str = ", ".join(params)
        return_type = func.return_type or "Any"
        async_prefix = "async " if func.is_async else ""

        lines.append(f"{async_prefix}def {func.name}({param_str}) -> {return_type}:")
        lines.append(f'    """TODO: Implement {func.name}."""')

        default_return = self._get_default_return(return_type)
        if default_return == "raise":
            lines.append(f'    raise NotImplementedError("{func.name} — auto-generated stub")')
        else:
            lines.append(f"    return {default_return}")

        content = "\n".join(lines)
        filename = f"{func.name}.py"

        return GeneratedStub(
            filename=filename,
            content=content,
            target_class=func.name,
            intent_hash=intent_hash,
            source_test=source_test,
        )


# =============================================================================
# Main Stub Generator (Orchestrator)
# =============================================================================

class StubGenerator:
    """
    Main entry point for generating stubs from test files.

    Usage:
        generator = StubGenerator(language="python", use_canonical_types=True)
        stubs = generator.generate_from_test_file("tests/test_foo.py")
        generator.write_stubs(stubs, output_dir="src/generated/")
    """

    def __init__(
        self,
        language: str = "python",
        use_canonical_types: bool = True,
    ):
        self.language = language
        self.use_canonical_types = use_canonical_types
        self.code_generator = StubCodeGenerator(use_canonical_types=use_canonical_types)

    def generate_from_test_file(self, test_file: str) -> List[GeneratedStub]:
        """Parse a test file and generate stubs for all discovered classes/functions."""
        test_path = Path(test_file)
        if not test_path.exists():
            logger.error(f"Test file not found: {test_file}")
            return []

        source = test_path.read_text(encoding="utf-8")
        return self.generate_from_source(source, filename=str(test_path))

    def generate_from_source(self, source_code: str, filename: str = "<unknown>") -> List[GeneratedStub]:
        """Parse source code and generate stubs."""
        try:
            analyzer = TestFileAnalyzer(source_code, filename)
            analyzer.analyze()
        except SyntaxError as e:
            logger.error(f"Syntax error in {filename}: {e}")
            return []

        stubs: List[GeneratedStub] = []

        # Generate class stubs
        for cls in analyzer.classes:
            stub = self.code_generator.generate_class_stub(cls, source_test=filename)
            stubs.append(stub)

        # If no classes found, generate function stubs from test functions
        if not stubs:
            for func in analyzer.functions:
                stub = self.code_generator.generate_function_stub(func, source_test=filename)
                stubs.append(stub)

        return stubs

    def write_stubs(
        self,
        stubs: List[GeneratedStub],
        output_dir: str = "kiva_cli/core/generated",
    ) -> List[str]:
        """Write generated stubs to disk. Returns list of written file paths."""
        output_path = Path(output_dir)
        written: List[str] = []

        for stub in stubs:
            file_path = output_path / stub.filename
            file_path.parent.mkdir(parents=True, exist_ok=True)

            if file_path.exists():
                logger.warning(f"Stub file already exists (skipping): {file_path}")
                continue

            file_path.write_text(stub.content, encoding="utf-8")
            written.append(str(file_path))
            logger.info(f"Generated stub: {file_path}")

        return written

    def summary(self, stubs: List[GeneratedStub]) -> Dict[str, Any]:
        """Return a summary of generated stubs."""
        return {
            "total_stubs": len(stubs),
            "classes": [s.target_class for s in stubs],
            "files": [s.filename for s in stubs],
            "intent_hashes": [f"0x{s.intent_hash}" for s in stubs],
        }
