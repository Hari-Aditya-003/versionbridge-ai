"""Bounded Python localization and impact edges without importing source."""

import ast
import hashlib
from patch_engine import source_files


def build_context(root, allowed, failure):
    sources = source_files(root, allowed)
    files = []
    symbols = []
    edges = []
    for path, text in sorted(sources.items()):
        files.append(
            {
                "path": path,
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
                "start_line": 1,
                "end_line": len(text.splitlines()),
                "source": text,
            }
        )
        try:
            tree = ast.parse(text)
        except (SyntaxError, RecursionError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                symbols.append(
                    {
                        "name": node.name,
                        "path": path,
                        "line": node.lineno,
                        "end_line": node.end_lineno,
                        "kind": type(node).__name__,
                    }
                )
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = (
                    [n.name for n in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or "relative"]
                )
                edges.extend(
                    {
                        "from": path,
                        "to": name,
                        "path": path,
                        "line": node.lineno,
                        "kind": "import",
                        "confidence": "exact_syntax",
                    }
                    for name in names
                )
            if isinstance(node, ast.Call):
                name = (
                    node.func.id
                    if isinstance(node.func, ast.Name)
                    else node.func.attr
                    if isinstance(node.func, ast.Attribute)
                    else "indirect"
                )
                edges.append(
                    {
                        "from": path,
                        "to": name,
                        "path": path,
                        "line": node.lineno,
                        "kind": "call",
                        "confidence": "heuristic_unresolved_receiver",
                    }
                )
    return {
        "files": files,
        "symbols": symbols[:200],
        "edges": edges[:300],
        "diagnostic_excerpt": str(failure)[-6000:],
        "localization_basis": "Allowed application files plus parsed source locations; no learned precision claim.",
    }
