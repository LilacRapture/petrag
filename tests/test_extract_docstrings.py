"""
Tests for ingestion/extract_docstrings.py — AST-based extraction with
qualified symbol names (ADR-007) and excluded-directory filtering (ADR-008).
"""
from ingestion.extract_docstrings import extract


def test_extract_module_and_function_docstrings(tmp_path):
    (tmp_path / "sample.py").write_text(
        '"""Module-level docstring."""\n\n'
        "def greet(name: str) -> str:\n"
        '    """Return a greeting."""\n'
        "    return f\"hello {name}\"\n"
    )

    chunks = list(extract("myproject", str(tmp_path)))

    module_chunks = [c for c in chunks if c.extra.get("node_type") == "module"]
    func_chunks = [c for c in chunks if c.extra.get("node_type") == "function"]

    assert len(module_chunks) == 1
    assert "Module-level docstring." in module_chunks[0].text

    assert len(func_chunks) == 1
    assert func_chunks[0].extra["symbol_name"] == "greet"
    assert "def greet(name: str) -> str:" in func_chunks[0].text


def test_extract_qualifies_nested_method_names(tmp_path):
    """
    The core reason ADR-007 exists: two classes with a same-named method
    must NOT collide on symbol_name.
    """
    (tmp_path / "sample.py").write_text(
        "class Foo:\n"
        "    def run(self):\n"
        '        """Foo\'s run method."""\n'
        "        pass\n\n"
        "class Bar:\n"
        "    def run(self):\n"
        '        """Bar\'s run method."""\n'
        "        pass\n"
    )

    chunks = list(extract("myproject", str(tmp_path)))
    symbol_names = {c.extra["symbol_name"] for c in chunks if c.extra.get("node_type") == "function"}

    assert symbol_names == {"Foo.run", "Bar.run"}


def test_extract_skips_functions_without_docstrings(tmp_path):
    (tmp_path / "sample.py").write_text(
        "def documented():\n"
        '    """Has a docstring."""\n'
        "    pass\n\n"
        "def undocumented():\n"
        "    pass\n"
    )

    chunks = list(extract("myproject", str(tmp_path)))
    symbol_names = {c.extra["symbol_name"] for c in chunks}

    assert symbol_names == {"documented"}


def test_extract_excludes_migrations_and_venv_dirs(tmp_path):
    """See ADR-008: these directories must never be walked."""
    (tmp_path / "migrations").mkdir()
    (tmp_path / "migrations" / "0001_initial.py").write_text(
        'def upgrade():\n    """Should never be indexed."""\n    pass\n'
    )
    (tmp_path / ".venv" / "lib").mkdir(parents=True)
    (tmp_path / ".venv" / "lib" / "somedep.py").write_text(
        'def helper():\n    """Third-party code, should never be indexed."""\n    pass\n'
    )
    (tmp_path / "real_code.py").write_text(
        'def actual_logic():\n    """Should be indexed."""\n    pass\n'
    )

    chunks = list(extract("myproject", str(tmp_path)))
    symbol_names = {c.extra["symbol_name"] for c in chunks}

    assert symbol_names == {"actual_logic"}


def test_extract_skips_files_with_syntax_errors(tmp_path):
    (tmp_path / "broken.py").write_text("def broken(:\n    pass\n")
    (tmp_path / "fine.py").write_text('def fine():\n    """Fine."""\n    pass\n')

    chunks = list(extract("myproject", str(tmp_path)))

    assert {c.extra["symbol_name"] for c in chunks} == {"fine"}
    