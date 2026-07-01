"""IMDB KG MCP Server — auto-generated via samyama-mcp-serve.

Usage:
    # Embedded mode (loads demo data on startup):
    python -m mcp_server.server --max-titles 5000

    # Connect to running Samyama server with pre-loaded data:
    python -m mcp_server.server --url http://localhost:8080

    # List all auto-generated + custom tools:
    python -m mcp_server.server --max-titles 5000 --list-tools

    # Claude Desktop config (embedded with 5000 titles):
    # {"mcpServers": {"imdb-kg": {
    #     "command": "python", "args": ["-m", "mcp_server.server", "--max-titles", "5000"]}}}
"""

from __future__ import annotations

import argparse
import os
import sys


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="imdb-kg-mcp",
        description="IMDB Movies Knowledge Graph MCP Server (powered by samyama-mcp-serve)",
    )
    parser.add_argument(
        "--url",
        default=None,
        help="Connect to a running Samyama server (skip embedded loading).",
    )
    parser.add_argument(
        "--max-titles",
        type=int,
        default=5000,
        help="Number of titles to load in embedded mode (default: 5000, 0 = all).",
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Path to IMDB .tsv files (default: data).",
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="Print discovered tools and exit.",
    )
    parser.add_argument(
        "--name",
        default="IMDB KG",
        help="MCP server name.",
    )

    args = parser.parse_args(argv)

    from samyama import SamyamaClient

    if args.url:
        client = SamyamaClient.connect(args.url)
    else:
        client = SamyamaClient.embedded()
        _load_data(client, args.data_dir, args.max_titles)

    # Resolve config path relative to this file
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")

    from samyama_mcp.config import ToolConfig
    from samyama_mcp.server import SamyamaMCPServer

    config = ToolConfig.from_yaml(config_path)
    server = SamyamaMCPServer(
        client, server_name=args.name, config=config
    )

    if args.list_tools:
        tools = server.list_tools()
        print(f"IMDB KG: {len(tools)} tools\n")
        for name in sorted(tools):
            print(f"  - {name}")
        sys.exit(0)

    server.run()


def _load_data(client, data_dir: str, max_titles: int) -> None:
    """Load IMDB data from title.basics/title.ratings/name.basics/title.principals TSVs."""
    if not os.path.isdir(data_dir):
        print(
            f"Warning: data directory '{data_dir}' not found. "
            f"Starting with empty graph.",
            file=sys.stderr,
        )
        return

    from etl.loader import load_imdb

    stats = load_imdb(client, data_dir=data_dir, max_titles=max_titles)
    print(
        f"Loaded {stats.get('movies', 0)} movies, {stats.get('series', 0)} series "
        f"({stats.get('nodes', 0)} nodes, {stats.get('edges', 0)} edges)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
