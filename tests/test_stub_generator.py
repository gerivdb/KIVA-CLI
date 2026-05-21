"""
Tests for Stub Generator (PRD-KIVA-002).

Validates:
- TestFileAnalyzer correctly parses test files via AST
- StubCodeGenerator produces valid Python stubs
- StubGenerator orchestrates the full flow
- Generated stubs are syntactically valid Python
"""

import ast
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiva_cli.core.stub_generator import (
    ExtractedClass,
    ExtractedFunction,
    GeneratedStub,
    StubCodeGenerator,
    StubGenerator,
    TestFileAnalyzer,
)


# =============================================================================
# Test Fixtures
# =============================================================================

SAMPLE_TEST_FILE = '''
"""Test file for ProjectManager."""

import pytest
from kiva_cli.core.project_manager import ProjectManager, FrameworkType
from kiva_cli.core.types import ValidationState, ProjectConfig


def test_scaffold_project_creates_main_py():
    pm = ProjectManager()
    success, config, msg = pm.scaffold_project("demo", FrameworkType.FASTAPI)
    assert success is True
    assert (config.repo_path / "main.py").exists()


def test_deploy_docker_builds_image():
    pm = ProjectManager()
    result = pm.deploy("docker", target="production")
    assert result.returncode == 0


def test_get_status_returns_state():
    pm = ProjectManager()
    status = pm.get_status()
    assert status is not None
'''


class TestTestFileAnalyzer:
    """Tests for the AST-based test file analyzer."""

    def test_extract_imports(self):
        analyzer = TestFileAnalyzer(SAMPLE_TEST_FILE, "test_foo.py")
        analyzer.analyze()
        assert len(analyzer.imports) >= 3
        module_names = [imp.module for imp in analyzer.imports]
        assert "kiva_cli.core.project_manager" in module_names

    def test_extract_test_functions(self):
        analyzer = TestFileAnalyzer(SAMPLE_TEST_FILE, "test_foo.py")
        analyzer.analyze()
        func_names = [f.name for f in analyzer.functions]
        assert "test_scaffold_project_creates_main_py" in func_names
        assert "test_deploy_docker_builds_image" in func_names

    def test_extract_class_usage(self):
        analyzer = TestFileAnalyzer(SAMPLE_TEST_FILE, "test_foo.py")
        analyzer.analyze()
        class_names = [c.name for c in analyzer.classes]
        assert "ProjectManager" in class_names

    def test_extract_methods_from_class_usage(self):
        analyzer = TestFileAnalyzer(SAMPLE_TEST_FILE, "test_foo.py")
        analyzer.analyze()
        pm_class = next((c for c in analyzer.classes if c.name == "ProjectManager"), None)
        assert pm_class is not None
        method_names = [m.name for m in pm_class.methods]
        assert "scaffold_project" in method_names
        assert "deploy" in method_names
        assert "get_status" in method_names

    def test_extract_body_hints(self):
        analyzer = TestFileAnalyzer(SAMPLE_TEST_FILE, "test_foo.py")
        analyzer.analyze()
        func = next((f for f in analyzer.functions if f.name == "test_scaffold_project_creates_main_py"), None)
        assert func is not None
        assert len(func.body_hints) > 0

    def test_handles_syntax_error_gracefully(self):
        bad_source = "def foo(:\n    pass"
        with pytest.raises(SyntaxError):
            analyzer = TestFileAnalyzer(bad_source, "bad.py")

    def test_empty_test_file(self):
        analyzer = TestFileAnalyzer("", "empty.py")
        analyzer.analyze()
        assert len(analyzer.classes) == 0
        assert len(analyzer.functions) == 0


class TestStubCodeGenerator:
    """Tests for the code generation component."""

    def test_generate_class_stub(self):
        gen = StubCodeGenerator(use_canonical_types=True)
        cls = ExtractedClass(
            name="ProjectManager",
            methods=[
                ExtractedFunction(name="scaffold_project", parameters=[("self", None)], is_method=True, source_class="ProjectManager"),
                ExtractedFunction(name="deploy", parameters=[("self", None)], is_method=True, source_class="ProjectManager"),
            ],
        )
        stub = gen.generate_class_stub(cls, source_test="test_pm.py")
        assert stub.target_class == "ProjectManager"
        assert "class ProjectManager:" in stub.content
        assert "def scaffold_project" in stub.content
        assert "def deploy" in stub.content
        assert "kiva_cli.core.types" in stub.content

    def test_generate_class_stub_without_canonical_types(self):
        gen = StubCodeGenerator(use_canonical_types=False)
        cls = ExtractedClass(name="MyClass", methods=[])
        stub = gen.generate_class_stub(cls)
        assert "kiva_cli.core.types" not in stub.content
        assert "class MyClass:" in stub.content

    def test_generate_function_stub(self):
        gen = StubCodeGenerator(use_canonical_types=True)
        func = ExtractedFunction(
            name="process_data",
            parameters=[("data", "List[str]")],
            return_type="Dict[str, Any]",
        )
        stub = gen.generate_function_stub(func, source_test="test_data.py")
        assert "def process_data" in stub.content
        assert "List[str]" in stub.content
        assert "Dict[str, Any]" in stub.content

    def test_generated_stub_is_valid_python(self):
        gen = StubCodeGenerator(use_canonical_types=True)
        cls = ExtractedClass(
            name="TestClass",
            methods=[
                ExtractedFunction(name="method_a", parameters=[("self", None)], is_method=True),
                ExtractedFunction(name="method_b", parameters=[("self", "str")], return_type="bool", is_method=True),
            ],
        )
        stub = gen.generate_class_stub(cls)
        # Verify the generated code is syntactically valid
        ast.parse(stub.content)

    def test_intent_hash_generated(self):
        gen = StubCodeGenerator(use_canonical_types=True)
        cls = ExtractedClass(name="Foo", methods=[])
        stub = gen.generate_class_stub(cls, source_test="test.py")
        assert len(stub.intent_hash) == 16

    def test_default_return_values(self):
        gen = StubCodeGenerator(use_canonical_types=True)
        assert gen._get_default_return("bool") == "False"
        assert gen._get_default_return("int") == "0"
        assert gen._get_default_return("str") == '""'
        # List[...] should return [] not ""
        assert gen._get_default_return("List[str]") == "[]"
        assert gen._get_default_return("Dict[str, Any]") == "{}"
        assert gen._get_default_return("Optional[str]") == "None"


class TestStubGenerator:
    """Integration tests for the full StubGenerator."""

    def test_generate_from_source(self):
        gen = StubGenerator(language="python", use_canonical_types=True)
        stubs = gen.generate_from_source(SAMPLE_TEST_FILE, "test_pm.py")
        assert len(stubs) >= 1
        assert any(s.target_class == "ProjectManager" for s in stubs)

    def test_generate_from_test_file(self, tmp_path):
        test_file = tmp_path / "test_example.py"
        test_file.write_text(SAMPLE_TEST_FILE)
        gen = StubGenerator(language="python", use_canonical_types=True)
        stubs = gen.generate_from_test_file(str(test_file))
        assert len(stubs) >= 1

    def test_generate_from_nonexistent_file(self):
        gen = StubGenerator()
        stubs = gen.generate_from_test_file("/nonexistent/test.py")
        assert stubs == []

    def test_write_stubs(self, tmp_path):
        gen = StubGenerator(language="python", use_canonical_types=True)
        stubs = gen.generate_from_source(SAMPLE_TEST_FILE, "test_pm.py")
        output_dir = tmp_path / "generated"
        written = gen.write_stubs(stubs, output_dir=str(output_dir))
        assert len(written) >= 1
        for path in written:
            assert Path(path).exists()
            # Verify written file is valid Python
            ast.parse(Path(path).read_text())

    def test_write_stubs_skips_existing(self, tmp_path):
        gen = StubGenerator(language="python", use_canonical_types=True)
        stubs = gen.generate_from_source(SAMPLE_TEST_FILE, "test_pm.py")
        output_dir = tmp_path / "generated"
        # Write once
        gen.write_stubs(stubs, output_dir=str(output_dir))
        # Write again — should skip
        written = gen.write_stubs(stubs, output_dir=str(output_dir))
        assert len(written) == 0  # All skipped

    def test_summary(self):
        gen = StubGenerator()
        stubs = gen.generate_from_source(SAMPLE_TEST_FILE, "test_pm.py")
        summary = gen.summary(stubs)
        assert summary["total_stubs"] == len(stubs)
        assert len(summary["classes"]) == len(stubs)
        assert all(h.startswith("0x") for h in summary["intent_hashes"])

    def test_no_classes_falls_back_to_functions(self):
        source = '''
def test_something():
    result = do_something("hello")
    assert result is not None
'''
        gen = StubGenerator()
        stubs = gen.generate_from_source(source, "test.py")
        # Should generate function stubs since no classes found
        assert len(stubs) >= 1


class TestGeneratedStub:
    """Tests for the GeneratedStub dataclass."""

    def test_default_values(self):
        # intent_hash is auto-generated in __post_init__, so it won't be empty
        stub = GeneratedStub(filename="test.py", content="x = 1", target_class="Test")
        assert len(stub.intent_hash) == 16
        assert stub.source_test == ""

    def test_intent_hash_auto_generated(self):
        stub = GeneratedStub(filename="test.py", content="x = 1", target_class="Test")
        # Post-init should generate hash
        assert len(stub.intent_hash) == 16
