"""Python AST indexing. Calls are resolved conservatively within lexical scopes."""
import ast
import hashlib
from pathlib import Path

EXCLUDED = {".git", ".venv", "venv", "node_modules", "__pycache__", "build", "dist"}

def index_python(root, store, max_file_bytes=1_000_000):
    root = Path(root).resolve()
    nodes, edges, skipped = [], [], []
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root)
        if any(part in EXCLUDED for part in relative.parts) or path.is_symlink():
            continue
        if not path.resolve().is_relative_to(root):
            continue
        name = relative.as_posix()
        try:
            raw = path.read_bytes()
            if len(raw) > max_file_bytes:
                skipped.append({"path": name, "reason": "size_limit"})
                continue
            # ast.parse accepts bytes and honors Python encoding declarations.
            tree = ast.parse(raw, filename=name)
            import tokenize
            import io
            encoding, _ = tokenize.detect_encoding(io.BytesIO(raw).readline)
            text = raw.decode(encoding)
        except (OSError, SyntaxError, UnicodeError) as error:
            skipped.append({"path": name, "reason": type(error).__name__})
            continue
        lines = text.splitlines()
        digest = hashlib.sha256(raw).hexdigest()
        file_id = name + "::module"
        nodes.append({"id": file_id, "kind": "Module", "path": name, "name": name,
                      "start_line": 1, "end_line": max(1, len(lines)),
                      "text": text, "sha256": digest})
        ids, parents, definitions = {}, {}, {}
        scopes = {file_id: {}}

        def collect(body, parent, qualified=""):
            for item in body:
                # Also descend through conditionals/try blocks, preserving lexical scope.
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    label = qualified + item.name
                    identifier = f"{name}::{label}@{item.lineno}"
                    ids[id(item)] = identifier
                    parents[identifier] = parent
                    definitions[identifier] = item
                    scopes.setdefault(parent, {}).setdefault(item.name, []).append(identifier)
                    scopes[identifier] = {}
                    kind = "Class" if isinstance(item, ast.ClassDef) else "Function"
                    if parent in definitions and isinstance(definitions[parent], ast.ClassDef) and kind == "Function":
                        kind = "Method"
                    start = min([item.lineno] + [d.lineno for d in item.decorator_list])
                    nodes.append({"id": identifier, "kind": kind, "path": name,
                                  "name": label, "start_line": start,
                                  "end_line": item.end_lineno,
                                  "text": "\n".join(lines[start - 1:item.end_lineno]),
                                  "sha256": digest})
                    edges.append({"source": parent, "target": identifier, "type": "contains"})
                    collect(item.body, identifier, label + ".")
                else:
                    for field, value in ast.iter_fields(item):
                        if isinstance(value, list):
                            collect([v for v in value if isinstance(v, ast.AST)], parent, qualified)
                        elif isinstance(value, ast.AST):
                            collect([value], parent, qualified)
        collect(tree.body, file_id)

        def resolve(symbol, scope):
            while scope:
                matches = scopes.get(scope, {}).get(symbol, [])
                if matches:
                    return matches[0] if len(matches) == 1 else None
                scope = parents.get(scope)
            return None

        class Calls(ast.NodeVisitor):
            def __init__(self):
                self.scope = file_id
            def visit_FunctionDef(self, item):
                previous = self.scope
                self.scope = ids[id(item)]
                for child in item.body:
                    self.visit(child)
                self.scope = previous
            visit_AsyncFunctionDef = visit_FunctionDef
            visit_ClassDef = visit_FunctionDef
            def visit_Call(self, item):
                if isinstance(item.func, ast.Name):
                    target = resolve(item.func.id, self.scope)
                    if target:
                        edges.append({"source": self.scope, "target": target, "type": "calls"})
                self.generic_visit(item)
        Calls().visit(tree)
    store.replace(nodes, edges, {"schema_version": 1, "parser": "python-ast",
                  "skipped": skipped, "limitations": [
                      "No cross-file resolution or dynamic dispatch",
                      "Lexical name resolution is approximate and does not model assignments",
                      "Decorators, defaults and annotations are not call-indexed"]})
    return {"nodes": len(nodes), "edges": len({(e["source"], e["target"], e["type"]) for e in edges}),
            "skipped": skipped}
