import argparse
import json
from pathlib import Path
from .indexer import index_python
from .retrieval import context_for_task
from .store import GraphStore

def main():
    parser = argparse.ArgumentParser(description="Offline repository context toolkit")
    parser.add_argument("--db", default="codegraph.sqlite")
    commands = parser.add_subparsers(dest="command", required=True)
    index = commands.add_parser("index")
    index.add_argument("root")
    ingest = commands.add_parser("ingest")
    ingest.add_argument("snapshot", help="Normalized JSON with nodes, edges, metadata")
    search = commands.add_parser("search")
    search.add_argument("query")
    search.add_argument("-k", type=int, default=10)
    context = commands.add_parser("context")
    context.add_argument("query")
    context.add_argument("--max-chars", type=int, default=16000)
    context.add_argument("--hops", type=int, default=1)
    neighbors = commands.add_parser("neighbors")
    neighbors.add_argument("node")
    neighbors.add_argument("--edge-type")
    neighbors.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    with GraphStore(args.db) as store:
        if args.command == "index":
            result = index_python(args.root, store)
        elif args.command == "ingest":
            data = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
            store.replace(data["nodes"], data["edges"], data.get("metadata"))
            result = {"nodes": len(data["nodes"]), "edges": len(data["edges"])}
        elif args.command == "search":
            result = store.search(args.query, args.k)
        elif args.command == "context":
            result = context_for_task(store, args.query, max_chars=args.max_chars, hops=args.hops)
        else:
            result = store.get_code_neighbors(args.node, args.edge_type, args.limit)
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
