"""Trusted edit scope and conservative Python structural safety checks."""
import ast
from pathlib import PurePosixPath

PROTECTED = {'tests','test','fixture','fixtures','.git','.github','security','deploy','providers','knowledge'}
SAFE_IMPORTS = {'collections','datetime','typing','math','decimal','bisect','json','re','dataclasses',
                'pydantic','pydantic_settings','pandas','numpy','enum','functools','itertools','statistics'}
DANGEROUS = {'eval','exec','compile','open','__import__','breakpoint','setattr','delattr','globals','locals',
             'system','popen','unlink','remove','rmdir','write_text','write_bytes','execve','load','loads'}


def safe_path(path):
    if (not isinstance(path,str) or not path or len(path)>180 or '\\' in path or '\x00' in path
            or ':' in path or any(ord(c)<32 for c in path)):
        raise ValueError('Invalid source path.')
    parts=PurePosixPath(path).parts
    if PurePosixPath(path).is_absolute() or '..' in parts or str(PurePosixPath(path))!=path:
        raise ValueError('Source path must be normalized and relative.')
    if any(p.lower() in PROTECTED or p.startswith('.') for p in parts):
        raise ValueError('Protected directory cannot be edited.')
    name=parts[-1].lower()
    if (name.startswith(('test_','conftest','pytest','security')) or name.endswith(('_test.py','.lock'))
            or any(s in name for s in ('credential','secret')) or not name.endswith('.py')):
        raise ValueError('Protected or unsupported source file.')
    return path


def parse_safe_change(before,after):
    try:
        original=ast.parse(before);candidate=ast.parse(after)
    except (SyntaxError,ValueError,RecursionError) as exc:
        raise ValueError('Python syntax check failed.') from exc
    def signatures(tree):
        return [(type(n).__name__,n.name,ast.dump(n.args) if hasattr(n,'args') else '')
                for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))]
    if signatures(original)!=signatures(candidate):
        raise ValueError('Changing function/class contracts is outside this policy.')
    if [ast.dump(n) for n in ast.walk(original) if isinstance(n,ast.Assert)] != [ast.dump(n) for n in ast.walk(candidate) if isinstance(n,ast.Assert)]:
        raise ValueError('Assertions cannot change.')
    original_nodes={ast.dump(n) for n in ast.walk(original)}
    for node in ast.walk(candidate):
        if ast.dump(node) in original_nodes:
            continue
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            names=[n.name for n in node.names] if isinstance(node,ast.Import) else [node.module or '']
            if any(name.split('.')[0] not in SAFE_IMPORTS for name in names):
                raise ValueError('New import is outside the migration policy.')
        if isinstance(node,ast.Attribute) and node.attr.startswith('__'):
            raise ValueError('New private runtime introspection is prohibited.')
        if isinstance(node,ast.Call):
            name=node.func.id if isinstance(node.func,ast.Name) else node.func.attr if isinstance(node.func,ast.Attribute) else ''
            if name in DANGEROUS or not name:
                raise ValueError('New sensitive or indirect call is prohibited.')
    return {'check':'python_ast_policy','passed':True,'scope':'conservative syntax and structural checks; not proof of safety'}
