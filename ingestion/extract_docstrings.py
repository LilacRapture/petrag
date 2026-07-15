"""
ingestion/extract_docstrings.py

Walks *.py files under source_path with the `ast` module and yields one
Chunk per class/function/module docstring — signature + docstring text,
never just the raw string, so retrieval sees *what* the docstring is
describing, not only the description itself.
"""
import ast
import logging
from collections.abc import Iterator
from pathlib import Path

from .chunking import Chunk

logger = logging.getLogger(__name__)


_EXCLUDED_DIR_NAMES = {"migrations", "__pycache__", ".venv", "venv", "site-packages", ".git"}


def _iter_python_files(source_path: str) -> Iterator[Path]:
    root = Path(source_path)
    for path in sorted(root.rglob("*.py")):
        if _EXCLUDED_DIR_NAMES & set(path.parts):
            continue
        yield path


def _format_function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    args_repr = ast.unparse(node.args)
    returns_repr = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    return f"{prefix} {node.name}({args_repr}){returns_repr}:"


def _format_class_signature(node: ast.ClassDef) -> str:
    bases = ", ".join(ast.unparse(base) for base in node.bases)
    bases_repr = f"({bases})" if bases else ""
    return f"class {node.name}{bases_repr}:"


class _DocstringCollector(ast.NodeVisitor):
    """
    Tracks the enclosing class name(s) while walking the tree, so nested
    method docstrings get a qualified symbol_name like
    "RBACPermission.has_permission" instead of a bare "has_permission"
    that would collide across unrelated classes.
    """

    def __init__(self) -> None:
        self.found: list[tuple[str, str, str]] = []  # (symbol_name, node_type, chunk_text)
        self._class_stack: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        docstring = ast.get_docstring(node)
        symbol_name = ".".join([*self._class_stack, node.name])
        if docstring:
            text = f"{_format_class_signature(node)}\n\n{docstring}"
            self.found.append((symbol_name, "class", text))

        self._class_stack.append(node.name)
        self.generic_visit(node)  # descend to catch nested classes/methods
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        docstring = ast.get_docstring(node)
        symbol_name = ".".join([*self._class_stack, node.name])
        if docstring:
            text = f"{_format_function_signature(node)}\n\n{docstring}"
            self.found.append((symbol_name, "function", text))
        # Deliberately NOT calling generic_visit here — this codebase has
        # no nested function definitions worth indexing separately, and
        # skipping avoids accidentally picking up e.g. docstrings of
        # locally-defined closures as if they were top-level symbols.


def extract(project: str, source_path: str) -> Iterator[Chunk]:
    for py_file in _iter_python_files(source_path):
        source = py_file.read_text(encoding="utf-8")
        relative_path = str(py_file.relative_to(source_path))

        try:
            tree = ast.parse(source, filename=relative_path)
        except SyntaxError:
            logger.warning("Skipping %s: failed to parse (SyntaxError)", relative_path)
            continue

        module_doc = ast.get_docstring(tree)
        if module_doc:
            yield Chunk(
                text=module_doc,
                source_file=relative_path,
                chunk_type="docstring",
                project=project,
                extra={"symbol_name": "", "node_type": "module"},
            )

        collector = _DocstringCollector()
        collector.visit(tree)

        for symbol_name, node_type, text in collector.found:
            yield Chunk(
                text=text,
                source_file=relative_path,
                chunk_type="docstring",
                project=project,
                extra={"symbol_name": symbol_name, "node_type": node_type},
            )
            