"""SQLite graph and BM25 retrieval with bounded, deterministic outputs."""
import hashlib
import json
import re
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS nodes(
 id TEXT PRIMARY KEY, kind TEXT NOT NULL, path TEXT NOT NULL,
 name TEXT NOT NULL, start_line INTEGER NOT NULL, end_line INTEGER NOT NULL,
 text TEXT NOT NULL, sha256 TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS edges(
 source TEXT NOT NULL REFERENCES nodes(id), target TEXT NOT NULL REFERENCES nodes(id),
 type TEXT NOT NULL, PRIMARY KEY(source,target,type));
CREATE INDEX IF NOT EXISTS edges_target ON edges(target,type);
CREATE INDEX IF NOT EXISTS edges_source ON edges(source,type);
CREATE VIRTUAL TABLE IF NOT EXISTS search USING fts5(id UNINDEXED, name, path, text);
"""

def limit(value, maximum=1000):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise ValueError(f"limit must be an integer between 0 and {maximum}")
    return value

def safe_path(value):
    value = str(value).replace("\\", "/")
    if not value or value.startswith("/") or ":" in value or ".." in value.split("/"):
        raise ValueError("node paths must be repository-relative")
    return value

def identifier_terms(text):
    """Split snake_case, camelCase and acronym boundaries without changing source."""
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return text.replace("_", " ")

class GraphStore:
    def __init__(self, database):
        self.db = sqlite3.connect(database)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(SCHEMA)

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def replace(self, nodes, edges, metadata=None):
        """Atomically replace a snapshot. Failed imports preserve the prior graph."""
        normalized = []
        seen = set()
        for node in nodes:
            node = dict(node)
            identifier = node["id"]
            if not isinstance(identifier, str) or not identifier or identifier in seen:
                raise ValueError("node identifiers must be nonempty unique strings")
            seen.add(identifier)
            path = safe_path(node["path"])
            start, end = node.get("start_line", 1), node.get("end_line", 1)
            if type(start) is not int or type(end) is not int or not 1 <= start <= end:
                raise ValueError("invalid source span")
            content = node.get("text", "")
            if not isinstance(content, str):
                raise ValueError("node text must be a string")
            normalized.append((identifier, node["kind"], path, node.get("name", identifier),
                               start, end, content, node.get("sha256", "")))
        relations = []
        for edge in edges:
            if edge["source"] not in seen or edge["target"] not in seen:
                raise ValueError("edge endpoint is missing")
            if not isinstance(edge["type"], str) or not edge["type"]:
                raise ValueError("edge type must be a nonempty string")
            relations.append((edge["source"], edge["target"], edge["type"]))
        with self.db:
            self.db.execute("DELETE FROM edges")
            self.db.execute("DELETE FROM nodes")
            self.db.execute("DELETE FROM search")
            self.db.execute("DELETE FROM metadata")
            self.db.executemany("INSERT INTO nodes VALUES(?,?,?,?,?,?,?,?)", normalized)
            self.db.executemany("INSERT INTO search(id,name,path,text) VALUES(?,?,?,?)",
                                [(n[0], identifier_terms(n[3]), identifier_terms(n[2]),
                                  identifier_terms(n[6])) for n in normalized])
            self.db.executemany("INSERT OR IGNORE INTO edges VALUES(?,?,?)", relations)
            self.db.executemany("INSERT INTO metadata VALUES(?,?)",
                                [(k, json.dumps(v)) for k, v in (metadata or {}).items()])

    def node(self, identifier):
        row = self.db.execute("SELECT * FROM nodes WHERE id=?", (identifier,)).fetchone()
        return dict(row) if row else None

    def search(self, query, k=10):
        """BM25 over escaped literal tokens; this is lexical, not dense search."""
        limit(k)
        tokens = list(dict.fromkeys(re.findall(r"\w+", identifier_terms(query), flags=re.UNICODE)))[:64]
        if not tokens or not k:
            return []
        expression = " OR ".join('"' + token + '"' for token in tokens)
        rows = self.db.execute(
            "SELECT id,bm25(search,0,5,2,1) AS score FROM search "
            "WHERE search MATCH ? ORDER BY score,id LIMIT ?", (expression, k))
        return [{"id": row["id"], "score": -row["score"], "source": "lexical"} for row in rows]

    def get_code_neighbors(self, node, edge_type=None, max_neighbors=50):
        limit(max_neighbors)
        rows = self.db.execute(
            "SELECT source,target,type FROM edges WHERE (source=? OR target=?) "
            "AND (? IS NULL OR type=?) ORDER BY type,source,target LIMIT ?",
            (node, node, edge_type, edge_type, max_neighbors))
        return [dict(row) for row in rows]

    def get_code_subgraph(self, nodes):
        """Induced subgraph; no implicit expansion."""
        identifiers = list(dict.fromkeys(nodes))
        limit(len(identifiers), 500)
        if not identifiers:
            return {"nodes": [], "edges": []}
        marks = ",".join("?" for _ in identifiers)
        rows = self.db.execute(f"SELECT * FROM nodes WHERE id IN ({marks}) ORDER BY id",
                               identifiers)
        edges = self.db.execute(
            f"SELECT * FROM edges WHERE source IN ({marks}) AND target IN ({marks}) "
            "ORDER BY source,target,type", identifiers + identifiers)
        return {"nodes": [dict(row) for row in rows], "edges": [dict(row) for row in edges]}

    def is_fresh(self, identifier, root):
        node = self.node(identifier)
        if node is None or not node["sha256"]:
            return False
        root = Path(root).resolve()
        path = (root / node["path"]).resolve()
        if not path.is_relative_to(root):
            return False
        try:
            return hashlib.sha256(path.read_bytes()).hexdigest() == node["sha256"]
        except OSError:
            return False
