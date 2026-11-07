# Snapshot interchange format v1

Import with `lcg --db codegraph.sqlite ingest snapshot.json`.

```json
{
  "metadata": {"schema_version": 1, "repo": "owner/name", "commit": "<full SHA>"},
  "nodes": [
    {"id": "src/parser.py::decode@10", "kind": "Function", "path": "src/parser.py",
     "name": "decode", "start_line": 10, "end_line": 12,
     "text": "def decode(value):\n    return value.strip()",
     "sha256": "<SHA256 of complete source file bytes>"}
  ],
  "edges": []
}
```

Node IDs are opaque unique strings. The built-in Python extractor includes line numbers, so IDs are snapshot-specific and are not stable across edits. Paths must be repository-relative. Source spans are one-indexed and inclusive. File hashes cover raw file bytes, not symbol snippets.

Edges use source, target and type; endpoints must exist. The importer accepts nonempty edge types; the built-in extractor produces contains and calls. External importers can supply imports, inherits and references when supported by their actual analysis.

get_code_neighbors returns bounded incoming/outgoing edge records, optionally filtered by type. get_code_subgraph returns the induced subgraph of at most 500 unique input IDs. These are standalone Python methods, not a verified harness response contract.

Imports replace the complete snapshot atomically. Do not mix commits in one database. A failed validation or SQL insert preserves the previous snapshot. Import only assets whose provenance and distribution rights have been checked.
