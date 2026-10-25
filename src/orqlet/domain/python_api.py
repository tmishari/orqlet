"""The public API of a Python module, read from its source text and never by running it.

The rules follow the proposal (17.4.1). The public names of a module are the literal entries of
`__all__` when it is a literal list or tuple, and otherwise every module-level class, function and
assignment whose name does not start with an underscore, including those under a module-level `if`
or `try`. An import is public only when `__all__` lists it or, in a package `__init__.py`, when it
is written `import y as y` or `from x import y as y`. `from __future__` imports and `TYPE_CHECKING`
blocks are ignored.

Two definitions of one public name are an error, except `@overload` stubs, the getter and setter
of a `@property` and a `try`/`except ImportError` fallback, which count as one name. A non-literal
`__all__`, any change made to `__all__`, a module `__getattr__` or a star import makes the whole
surface `manual`: no extractor can see what the module really exports.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

from orqlet.domain.digest import sha256_hex


@dataclass(frozen=True, slots=True)
class Symbol:
    name: str
    kind: str  # function, class, assignment, alias or import
    signature: str  # canonical text; its digest is the fingerprint

    @property
    def digest(self) -> str:
        return sha256_hex(self.signature.encode("utf-8"))


@dataclass(frozen=True, slots=True)
class ModuleApi:
    symbols: dict[str, Symbol] = field(default_factory=dict)
    manual: tuple[str, ...] = ()  # why the surface cannot be extracted
    errors: tuple[str, ...] = ()  # why the module breaks the rules of a public API


def canonical_signature(text: str) -> str | None:
    """A declared signature as the extractor would write it, or `None` if it is not one."""
    try:
        tree = ast.parse(text.strip().rstrip(":") + ":\n    pass\n")
    except SyntaxError:
        return None
    if len(tree.body) != 1:
        return None
    node = tree.body[0]
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        return _function_signature(node)
    if isinstance(node, ast.ClassDef):
        return _class_signature(node)
    return None


def signature_digest(signature: str) -> str:
    return sha256_hex(signature.encode("utf-8"))


def extract_module_api(source: str, *, is_package_init: bool = False) -> ModuleApi:
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return ModuleApi(manual=(f"the module cannot be parsed ({error.msg})",))
    manual: list[str] = []
    errors: list[str] = []
    statements = list(_module_statements(tree.body, in_fallback=False))
    exported = _exported_names(tree, manual)
    if any(
        isinstance(s.node, ast.FunctionDef | ast.AsyncFunctionDef) and s.node.name == "__getattr__"
        for s in statements
    ):
        manual.append("the module defines `__getattr__`")
    if any(
        isinstance(s.node, ast.ImportFrom) and any(a.name == "*" for a in s.node.names)
        for s in statements
    ):
        manual.append("the module uses a star import")
    symbols = _collect(statements, exported, is_package_init, errors)
    if exported is not None:
        symbols = {
            name: symbols.get(name, Symbol(name, "export", "<undefined>")) for name in exported
        }
    return ModuleApi(symbols, tuple(manual), tuple(errors))


# --- reading the statements -----------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class _Statement:
    node: ast.stmt
    in_fallback: bool  # inside `try:` with an `except ImportError`


def _module_statements(body: list[ast.stmt], *, in_fallback: bool) -> list[_Statement]:
    found: list[_Statement] = []
    for node in body:
        if isinstance(node, ast.If):
            if _is_type_checking(node.test):
                found += _module_statements(node.orelse, in_fallback=in_fallback)
            else:
                found += _module_statements(node.body, in_fallback=in_fallback)
                found += _module_statements(node.orelse, in_fallback=in_fallback)
        elif isinstance(node, ast.Try):
            fallback = any(_catches_import_error(h) for h in node.handlers)
            found += _module_statements(node.body, in_fallback=in_fallback)
            for handler in node.handlers:
                found += _module_statements(handler.body, in_fallback=in_fallback or fallback)
            found += _module_statements(node.orelse, in_fallback=in_fallback)
            found += _module_statements(node.finalbody, in_fallback=in_fallback)
        else:
            found.append(_Statement(node, in_fallback))
    return found


def _is_type_checking(test: ast.expr) -> bool:
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    )


def _catches_import_error(handler: ast.ExceptHandler) -> bool:
    kinds = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    return any(
        isinstance(k, ast.Name) and k.id in {"ImportError", "ModuleNotFoundError"} for k in kinds
    )


def _exported_names(tree: ast.Module, manual: list[str]) -> list[str] | None:
    """The entries of a literal `__all__`, or `None` when there is none or it is not literal."""
    literal: list[str] | None = None
    for node in ast.walk(tree):
        assigned = _assigned_to_all(node)
        if assigned is not None:
            literal = _literal_strings(assigned, manual)
        elif isinstance(node, ast.AugAssign) and _is_all(node.target):
            manual.append("`__all__` is changed with an augmented assignment")
        elif isinstance(node, ast.Delete) and any(_mentions_all(t) for t in node.targets):
            manual.append("`__all__` is changed with `del`")
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and _is_all(node.func.value)
        ):
            manual.append(f"`__all__` is changed with `{node.func.attr}`")
    return literal


def _assigned_to_all(node: ast.AST) -> ast.expr | None:
    """The value assigned to `__all__` by a plain or annotated assignment, if this is one."""
    if isinstance(node, ast.Assign) and any(_is_all(t) for t in node.targets):
        return node.value
    if isinstance(node, ast.AnnAssign) and _is_all(node.target):
        return node.value
    return None


def _is_all(node: ast.expr) -> bool:
    return isinstance(node, ast.Name) and node.id == "__all__"


def _mentions_all(node: ast.expr) -> bool:
    return _is_all(node) or (isinstance(node, ast.Subscript) and _is_all(node.value))


def _literal_strings(value: ast.expr, manual: list[str]) -> list[str] | None:
    if isinstance(value, ast.List | ast.Tuple) and all(
        isinstance(item, ast.Constant) and isinstance(item.value, str) for item in value.elts
    ):
        return [str(item.value) for item in value.elts if isinstance(item, ast.Constant)]
    manual.append("`__all__` is not a literal list or tuple of strings")
    return None


# --- collecting the symbols -----------------------------------------------------------------
def _collect(
    statements: list[_Statement], exported: list[str] | None, init: bool, errors: list[str]
) -> dict[str, Symbol]:
    found: dict[str, list[tuple[Symbol, _Statement]]] = {}
    for statement in statements:
        for declared in _symbols_of(statement.node):
            found.setdefault(declared.name, []).append((declared, statement))
            if isinstance(statement.node, ast.ClassDef):
                for member, node in _members(statement.node):
                    found.setdefault(member.name, []).append(
                        (member, _Statement(node, statement.in_fallback))
                    )
    symbols: dict[str, Symbol] = {}
    for name, entries in found.items():
        if not _is_public(name, entries, exported, init):
            continue
        chosen = _one_symbol(name, entries, errors)
        if chosen is not None:
            symbols[name] = chosen
    return symbols


def _is_public(
    name: str,
    entries: list[tuple[Symbol, _Statement]],
    exported: list[str] | None,
    init: bool,
) -> bool:
    head = name.split(".")[0]
    if exported is not None:
        return head in exported
    if head.startswith("_") or any(part.startswith("_") for part in name.split(".")):
        return False
    first = entries[0][0]
    if first.kind == "import":
        return (
            init
            and first.signature.endswith(f" as {head}")
            and first.signature.startswith("reexport ")
        )
    return True


def _symbols_of(node: ast.stmt) -> list[Symbol]:
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        return [Symbol(node.name, "function", _function_signature(node))]
    if isinstance(node, ast.ClassDef):
        return [Symbol(node.name, "class", _class_signature(node))]
    if isinstance(node, ast.Assign):
        return [
            _assignment(t.id, node.value, None) for t in node.targets if isinstance(t, ast.Name)
        ]
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return [_assignment(node.target.id, node.value, node.annotation)]
    if isinstance(node, ast.Import | ast.ImportFrom):
        return _imports(node)
    return []


def _assignment(name: str, value: ast.expr | None, annotation: ast.expr | None) -> Symbol:
    if isinstance(value, ast.Name | ast.Attribute):
        return Symbol(name, "alias", f"{name} = {ast.unparse(value)}")
    if annotation is not None:
        return Symbol(name, "assignment", f"{name}: {ast.unparse(annotation)}")
    return Symbol(name, "assignment", name)


def _imports(node: ast.Import | ast.ImportFrom) -> list[Symbol]:
    if isinstance(node, ast.ImportFrom) and node.module == "__future__":
        return []
    prefix = (
        f"from {'.' * node.level}{node.module or ''} " if isinstance(node, ast.ImportFrom) else ""
    )
    symbols = []
    for alias in node.names:
        if alias.name == "*":
            continue
        shown = alias.asname or alias.name.split(".")[0]
        # `import y as y` and `from x import y as y` are the explicit re-export convention.
        reexport = alias.asname is not None and alias.asname == alias.name
        signature = f"{'reexport ' if reexport else ''}{prefix}import {alias.name} as {shown}"
        symbols.append(Symbol(shown, "import", signature))
    return symbols


def _members(node: ast.ClassDef) -> list[tuple[Symbol, ast.stmt]]:
    """The public methods of a class, each with the statement that defines it."""
    members: list[tuple[Symbol, ast.stmt]] = []
    for child in node.body:
        if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef) and not child.name.startswith(
            "_"
        ):
            symbol = Symbol(f"{node.name}.{child.name}", "function", _function_signature(child))
            members.append((symbol, child))
    return members


def _one_symbol(
    name: str, entries: list[tuple[Symbol, _Statement]], errors: list[str]
) -> Symbol | None:
    if len(entries) == 1:
        return entries[0][0]
    if all(_is_overload(s.node) for _, s in entries[:-1]):
        return entries[-1][0]  # the implementation, or the last stub of a stub-only group
    if all(_is_property_part(s.node) for _, s in entries):
        return entries[0][0]
    if all(s.in_fallback for _, s in entries[1:]):
        return entries[0][0]
    errors.append(f"`{name}` is defined {len(entries)} times")
    return entries[-1][0]


def _decorators(node: ast.stmt) -> list[str]:
    if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        return []
    return [ast.unparse(d).split("(")[0] for d in node.decorator_list]


def _is_overload(node: ast.stmt) -> bool:
    return any(d.split(".")[-1] == "overload" for d in _decorators(node))


def _is_property_part(node: ast.stmt) -> bool:
    return any(
        d == "property" or d.endswith((".setter", ".getter", ".deleter")) for d in _decorators(node)
    )


def _function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    returns = f" -> {ast.unparse(node.returns)}" if node.returns is not None else ""
    return f"{prefix} {node.name}({ast.unparse(node.args)}){returns}"


def _class_signature(node: ast.ClassDef) -> str:
    bases = [ast.unparse(b) for b in node.bases] + [
        f"{k.arg}={ast.unparse(k.value)}" for k in node.keywords if k.arg
    ]
    return f"class {node.name}({', '.join(bases)})" if bases else f"class {node.name}"
