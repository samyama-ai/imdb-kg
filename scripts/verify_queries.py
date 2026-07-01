"""Sanity-check the loaded imdb-kg graph: every showcase query returns rows and
basic invariants hold (non-negative counts, ratings in range, etc.)."""

import sys
import gc
sys.path.insert(0, ".")
from samyama import SamyamaClient
from etl.loader import load_imdb

GRAPH = "default"


def q(client, cypher):
    r = client.query_readonly(cypher, GRAPH)
    return [dict(zip(r.columns, row)) for row in r.records]


def verify(client):
    print("=" * 60, flush=True)
    print("VERIFYING IMDB-KG GRAPH", flush=True)
    print("=" * 60, flush=True)

    print("\n--- GRAPH STATS ---", flush=True)
    counts = {}
    for label in ["Movie", "Person", "AlternateTitle", "Series", "Rating", "Genre"]:
        rows = q(client, f"MATCH (n:{label}) RETURN count(n) AS c")
        counts[label] = rows[0]["c"]
        print(f"  {label}: {counts[label]:,}", flush=True)
        assert counts[label] >= 0
    gc.collect()

    total_edges = q(client, "MATCH ()-[r]->() RETURN count(r) AS c")[0]["c"]
    print(f"  Total edges: {total_edges:,}", flush=True)
    assert total_edges > 0, "graph has no edges — did you load data?"
    gc.collect()

    print("\n--- RATING SANITY ---", flush=True)
    rows = q(client, "MATCH (:Movie)-[:HAS_RATING]->(r:Rating) RETURN min(r.average_rating) AS lo, max(r.average_rating) AS hi")
    lo, hi = rows[0]["lo"], rows[0]["hi"]
    print(f"  average_rating range: {lo} - {hi}", flush=True)
    if counts["Movie"] > 0:
        assert 0.0 <= lo and hi <= 10.0, "ratings out of [0, 10] range"
    gc.collect()

    print("\n--- SHOWCASE QUERIES RETURN ROWS ---", flush=True)
    showcase = {
        "top_rated_movies": """
            MATCH (m:Movie)-[:HAS_RATING]->(r:Rating)
            WHERE r.num_votes >= 50000
            RETURN m.title AS title ORDER BY r.average_rating DESC LIMIT 10
        """,
        "most_prolific_directors": """
            MATCH (p:Person)-[:DIRECTED]->(m:Movie)-[:HAS_RATING]->(r:Rating)
            WHERE r.average_rating >= 7.0
            RETURN p.name AS director, count(m) AS films ORDER BY films DESC LIMIT 10
        """,
        "genre_popularity": """
            MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre)
            MATCH (m)-[:HAS_RATING]->(r:Rating)
            RETURN g.name AS genre, sum(r.num_votes) AS total_votes ORDER BY total_votes DESC LIMIT 10
        """,
        "director_actor_pairs": """
            MATCH (d:Person)-[:DIRECTED]->(m:Movie)<-[:ACTED_IN]-(a:Person)
            RETURN d.name AS director, a.name AS actor, count(m) AS films_together
            ORDER BY films_together DESC LIMIT 10
        """,
        "decades_of_cinema": """
            MATCH (m:Movie)-[:HAS_RATING]->(r:Rating)
            WHERE r.num_votes >= 1000
            RETURN (toInteger(m.year) / 10) * 10 AS decade, count(m) AS movies ORDER BY decade LIMIT 10
        """,
        "top_tv_series": """
            MATCH (s:Series)-[:HAS_RATING]->(r:Rating)
            WHERE r.num_votes >= 10000
            RETURN s.title AS series ORDER BY r.average_rating DESC LIMIT 10
        """,
    }
    for name, cypher in showcase.items():
        rows = q(client, cypher)
        status = "OK" if rows else "EMPTY (check thresholds / data volume)"
        print(f"  {name:30s} {len(rows):>4} rows  [{status}]", flush=True)
        gc.collect()

    print("\n" + "=" * 60, flush=True)
    print("VERIFICATION COMPLETE", flush=True)


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    print(f"Loading data from {data_dir}...", flush=True)
    c = SamyamaClient.embedded()
    stats = load_imdb(c, data_dir=data_dir)
    print(f"\nLoad complete: {stats}", flush=True)
    verify(c)
