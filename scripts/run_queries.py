"""Run all README showcase queries against a loaded imdb-kg graph."""

import sys
import time
sys.path.insert(0, ".")
from samyama import SamyamaClient
from etl.loader import load_imdb

GRAPH = "default"


def q(client, cypher):
    r = client.query_readonly(cypher, GRAPH)
    return [dict(zip(r.columns, row)) for row in r.records]


def run_all(client):
    print("=" * 70)
    print("IMDB-KG FULL DATASET QUERIES")
    print("=" * 70)

    # Graph stats
    print("\n## Graph Statistics\n")
    for label in ["Movie", "Person", "AlternateTitle", "Series", "Rating", "Genre"]:
        rows = q(client, f"MATCH (n:{label}) RETURN count(n) AS c")
        print(f"  {label:20s} {rows[0]['c']:>10,}")

    total_nodes = q(client, "MATCH (n) RETURN count(n) AS c")[0]["c"]
    total_edges = q(client, "MATCH ()-[r]->() RETURN count(r) AS c")[0]["c"]
    print(f"\n  {'Total nodes':20s} {total_nodes:>10,}")
    print(f"  {'Total edges':20s} {total_edges:>10,}")

    # Top-rated movies
    print("\n## Top-Rated Movies (min 50K votes)\n")
    rows = q(client, """
        MATCH (m:Movie)-[:HAS_RATING]->(r:Rating)
        WHERE r.num_votes >= 50000
        RETURN m.title AS title, m.year AS year, r.average_rating AS rating, r.num_votes AS votes
        ORDER BY r.average_rating DESC LIMIT 10
    """)
    print(f"  {'Title':35s} {'Year':>6s} {'Rating':>7s} {'Votes':>10s}")
    for r in rows:
        print(f"  {str(r['title'])[:35]:35s} {r['year']:>6} {r['rating']:>7.1f} {r['votes']:>10,}")

    # Most prolific directors
    print("\n## Most Prolific Directors (avg rating >= 7.0)\n")
    rows = q(client, """
        MATCH (p:Person)-[:DIRECTED]->(m:Movie)-[:HAS_RATING]->(r:Rating)
        WHERE r.average_rating >= 7.0
        RETURN p.name AS director, count(m) AS films, round(avg(r.average_rating) * 10) / 10.0 AS avg_rating
        ORDER BY films DESC LIMIT 10
    """)
    print(f"  {'Director':30s} {'Films':>6s} {'Avg Rating':>11s}")
    for r in rows:
        print(f"  {str(r['director']):30s} {r['films']:>6,} {r['avg_rating']:>11.1f}")

    # Genre popularity
    print("\n## Genre Popularity (by total votes)\n")
    rows = q(client, """
        MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre)
        MATCH (m)-[:HAS_RATING]->(r:Rating)
        RETURN g.name AS genre, count(m) AS movies, sum(r.num_votes) AS total_votes
        ORDER BY total_votes DESC LIMIT 10
    """)
    print(f"  {'Genre':20s} {'Movies':>8s} {'Total Votes':>14s}")
    for r in rows:
        print(f"  {str(r['genre']):20s} {r['movies']:>8,} {r['total_votes']:>14,}")

    # Director-actor power pairs
    print("\n## Director-Actor Power Pairs\n")
    rows = q(client, """
        MATCH (d:Person)-[:DIRECTED]->(m:Movie)<-[:ACTED_IN]-(a:Person)
        RETURN d.name AS director, a.name AS actor, count(m) AS films_together
        ORDER BY films_together DESC LIMIT 10
    """)
    print(f"  {'Director':25s} {'Actor':25s} {'Films':>6s}")
    for r in rows:
        print(f"  {str(r['director']):25s} {str(r['actor']):25s} {r['films_together']:>6,}")

    # Busiest actors by director breadth
    print("\n## Busiest Actors by Director Breadth\n")
    rows = q(client, """
        MATCH (a:Person)-[:ACTED_IN]->(m:Movie)<-[:DIRECTED]-(d:Person)
        RETURN a.name AS actor, count(DISTINCT d) AS distinct_directors, count(DISTINCT m) AS films
        ORDER BY distinct_directors DESC LIMIT 10
    """)
    print(f"  {'Actor':25s} {'Directors':>10s} {'Films':>6s}")
    for r in rows:
        print(f"  {str(r['actor']):25s} {r['distinct_directors']:>10,} {r['films']:>6,}")

    # Decades of cinema
    print("\n## Decades of Cinema\n")
    rows = q(client, """
        MATCH (m:Movie)-[:HAS_RATING]->(r:Rating)
        WHERE r.num_votes >= 1000
        RETURN (toInteger(m.year) / 10) * 10 AS decade, count(m) AS movies, round(avg(r.average_rating) * 10) / 10.0 AS avg_rating
        ORDER BY decade
    """)
    print(f"  {'Decade':8s} {'Movies':>8s} {'Avg Rating':>11s}")
    for r in rows:
        print(f"  {r['decade']:<8} {r['movies']:>8,} {r['avg_rating']:>11.1f}")

    # Top TV series
    print("\n## Top-Rated TV Series\n")
    rows = q(client, """
        MATCH (s:Series)-[:HAS_RATING]->(r:Rating)
        WHERE r.num_votes >= 10000
        RETURN s.title AS series, s.year AS start_year, r.average_rating AS rating, r.num_votes AS votes
        ORDER BY r.average_rating DESC LIMIT 10
    """)
    print(f"  {'Series':35s} {'Year':>6s} {'Rating':>7s} {'Votes':>10s}")
    for r in rows:
        print(f"  {str(r['series'])[:35]:35s} {r['start_year']:>6} {r['rating']:>7.1f} {r['votes']:>10,}")

    # Writers per director
    print("\n## Most Written-For Directors\n")
    rows = q(client, """
        MATCH (w:Person)-[:WROTE]->(m:Movie)<-[:DIRECTED]-(d:Person)
        RETURN d.name AS director, count(DISTINCT w) AS distinct_writers, count(DISTINCT m) AS films
        ORDER BY distinct_writers DESC LIMIT 10
    """)
    print(f"  {'Director':25s} {'Writers':>8s} {'Films':>6s}")
    for r in rows:
        print(f"  {str(r['director']):25s} {r['distinct_writers']:>8,} {r['films']:>6,}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else None

    if data_dir:
        print(f"Loading data from {data_dir}...")
        c = SamyamaClient.embedded()
        stats = load_imdb(c, data_dir=data_dir)
        print(f"\nLoad complete: {stats}")
        run_all(c)
    else:
        print("Usage: python scripts/run_queries.py <data-dir>")
        print("  or import and call run_all(client) with a pre-loaded client")
