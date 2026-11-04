"""Resolve a scoped Python return edit without importing project code."""
import ast
from pathlib import PurePosixPath

from profiles import Profile


def resolve_target(project, filename, function):
    path = PurePosixPath(filename)
    if (not path.parts or path.is_absolute() or ".." in path.parts or "\\" in filename
            or path.suffix != ".py" or "tests" in path.parts or path.name == "conftest.py"
            or path.name.startswith("test_") or path.name.endswith("_test.py")
            or not function.isidentifier()):
        raise RuntimeError("Choose a Python application file and a top-level function.")
    target = project.joinpath(*path.parts)
    if not target.is_file() or target.stat().st_size > 24000:
        raise RuntimeError("The selected source file is missing or exceeds 24 KB.")
    try:
        source = target.read_text()
        tree = ast.parse(source)
    except (UnicodeError, SyntaxError, OSError) as exc:
        raise RuntimeError("The selected source file must be valid UTF-8 Python.") from exc
    matches = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == function]
    if len(matches) != 1:
        raise RuntimeError("The selected top-level function must exist exactly once.")
    node = matches[0]
    args = node.args
    names = tuple(arg.arg for arg in args.posonlyargs + args.args + args.kwonlyargs)
    line = node.body[-1]
    if (len(node.body) != 1 or not isinstance(line, ast.Return) or line.value is None
            or line.lineno != line.end_lineno or line.lineno == node.lineno or not names):
        raise RuntimeError("Select a function whose body is a single return statement on its own line.")
    original = source.split("\n")[line.lineno - 1]
    if not original.lstrip().startswith("return ") or original[:line.col_offset] != " " * line.col_offset:
        raise RuntimeError("Use spaces to indent the selected return statement.")
    profile = Profile("Python · scoped function repair", "", original, (), "", names)
    return target, source, profile, line.lineno
