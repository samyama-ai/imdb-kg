"""Tests for imdb-kg MCP server — verifies auto-generated + custom tools."""

import asyncio
import json
import os
import sys

import pytest

from samyama import SamyamaClient
from samyama_mcp.config import ToolConfig
from samyama_mcp.server import SamyamaMCPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from etl.loader import load_imdb


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def server():
    """Create a server with a small slice of titles — shared across all tests."""
    client = SamyamaClient.embedded()
    load_imdb(client, data_dir="data", max_titles=2000)
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "mcp_server", "config.yaml"
    )
    config = ToolConfig.from_yaml(config_path)
    return SamyamaMCPServer(client, server_name="IMDB KG Test", config=config)


def _call(server, tool_name, args=None):
    """Synchronously call an MCP tool and parse the JSON result."""
    async def _run():
        r = await server.mcp.call_tool(tool_name, args or {})
        return json.loads(r.content[0].text)
    return asyncio.run(_run())


# ── Tool Registration ────────────────────────────────────────────────

class TestToolRegistration:
    def test_has_generic_tools(self, server):
        tools = server.list_tools()
        assert "cypher_query" in tools
        assert "schema_info" in tools

    def test_has_node_tools(self, server):
        tools = server.list_tools()
        assert "search_movie" in tools
        assert "count_person" in tools
        assert "get_genre_by_name" in tools

    def test_has_edge_tools(self, server):
        tools = server.list_tools()
        assert "find_acted_in_connections" in tools
        assert "find_directed_connections" in tools
        assert "traverse_has_genre" in tools

    def test_has_algorithm_tools(self, server):
        tools = server.list_tools()
        assert "pagerank" in tools
        assert "shortest_path" in tools
        assert "communities" in tools

    def test_has_custom_tools(self, server):
        tools = server.list_tools()
        assert "top_rated_movies" in tools
        assert "most_prolific_directors" in tools
        assert "director_actor_pairs" in tools
        assert "genre_popularity" in tools
        assert "decades_of_cinema" in tools
        assert "top_tv_series" in tools

    def test_tool_count_at_least_41(self, server):
        assert len(server.list_tools()) >= 41


# ── Schema Info ──────────────────────────────────────────────────────

class TestSchemaInfo:
    def test_schema_has_all_labels(self, server):
        schema = _call(server, "schema_info")
        labels = {nt["label"] for nt in schema["node_types"]}
        assert {"Movie", "Person", "Series", "Rating", "Genre"} <= labels

    def test_schema_has_edge_types(self, server):
        schema = _call(server, "schema_info")
        etypes = {et["type"] for et in schema["edge_types"]}
        assert "ACTED_IN" in etypes
        assert "DIRECTED" in etypes
        assert "HAS_RATING" in etypes

    def test_schema_totals_positive(self, server):
        schema = _call(server, "schema_info")
        assert schema["total_nodes"] > 0
        assert schema["total_edges"] > 0


# ── Auto-Generated Node Tools ────────────────────────────────────────

class TestNodeTools:
    def test_search_movie(self, server):
        rows = _call(server, "search_movie", {"query": "a", "limit": 5})
        assert len(rows) > 0

    def test_count_person(self, server):
        result = _call(server, "count_person")
        assert result["count"] > 0

    def test_get_genre_not_found(self, server):
        result = _call(server, "get_genre_by_name", {"value": "Not A Real Genre"})
        assert "error" in result


# ── Auto-Generated Edge Tools ────────────────────────────────────────

class TestEdgeTools:
    def test_find_has_genre_connections(self, server):
        rows = _call(server, "find_has_genre_connections", {
            "node_label": "Genre",
            "node_property": "name",
            "node_value": "Drama",
            "direction": "incoming",
        })
        assert len(rows) >= 0


# ── Custom Tools ─────────────────────────────────────────────────────

class TestCustomTools:
    def test_top_rated_movies(self, server):
        rows = _call(server, "top_rated_movies", {"min_votes": 0, "limit": 5})
        assert len(rows) <= 5
        ratings = [r["rating"] for r in rows]
        assert ratings == sorted(ratings, reverse=True)

    def test_most_prolific_directors(self, server):
        rows = _call(server, "most_prolific_directors", {"min_rating": 0.0, "limit": 5})
        assert len(rows) >= 0
        if rows:
            assert "films" in rows[0]

    def test_genre_popularity(self, server):
        rows = _call(server, "genre_popularity", {"limit": 5})
        assert len(rows) >= 0

    def test_director_actor_pairs(self, server):
        rows = _call(server, "director_actor_pairs", {"limit": 5})
        if rows:
            assert "director" in rows[0]
            assert "actor" in rows[0]

    def test_decades_of_cinema(self, server):
        rows = _call(server, "decades_of_cinema", {"min_votes": 0})
        assert len(rows) >= 0


# ── Security ─────────────────────────────────────────────────────────

class TestSecurity:
    def test_cypher_query_rejects_write(self, server):
        result = _call(server, "cypher_query", {"cypher": "CREATE (n:Test)"})
        assert "error" in result

    def test_cypher_query_readonly_works(self, server):
        rows = _call(server, "cypher_query", {
            "cypher": "MATCH (n:Movie) RETURN count(n) AS c"
        })
        assert rows[0]["c"] >= 0
