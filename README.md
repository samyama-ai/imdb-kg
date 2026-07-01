# IMDB Movies Knowledge Graph

**1.94M nodes. 2.63M edges. Movies, TV series, directors, actors, writers and genres from IMDB's non-commercial dataset.**

> Part of the **Samyama** ecosystem — loaded into and queried via the graph engine at [samyama-ai/samyama-graph](https://github.com/samyama-ai/samyama-graph).
> This repo holds the loader and source-data specifics for the KG.

<a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="License"></a>

---

We loaded movies, series, cast and crew from IMDB, then asked:

> *"Who keeps casting the same actors, and how does that pay off?"*

```cypher
MATCH (d:Person)-[:DIRECTED]->(m:Movie)<-[:ACTED_IN]-(a:Person)
RETURN d.name AS director, a.name AS actor, count(m) AS films_together
ORDER BY films_together DESC LIMIT 5
```

**Flat title tables give you ratings. A graph gives you connections** -- director-actor power pairs, genre-quality trends, multi-hop cast/crew traversals. Powered by [Samyama Graph](https://github.com/samyama-ai/samyama-graph).

---

## Schema

**6 node labels** -- Movie (49,632), Person (293,550), AlternateTitle (1,517,802), Series (14,858), Rating (64,490), Genre (28)

**7 edge types** -- HAS_ALTERNATE_TITLE, ACTED_IN, DIRECTED, WROTE, PRODUCED, HAS_RATING, HAS_GENRE

| Node label | Key properties |
|------------|----------------|
| Movie | tconst, title, year, runtime_minutes, title_type |
| Person | nconst, name, birth_year, death_year |
| AlternateTitle | title, region, language |
| Series | tconst, title, year, end_year |
| Rating | average_rating, num_votes |
| Genre | name |

The **director-actor collaboration network** -- `(:Person)-[:DIRECTED]->(:Movie)<-[:ACTED_IN]-(:Person)` -- is the star: a bipartite graph that turns "power pairs" into a first-class queryable structure.

**Data source** -- [IMDB Non-Commercial Datasets](https://developer.imdb.com/non-commercial-datasets/) (`title.basics.tsv`, `title.ratings.tsv`, `name.basics.tsv`, `title.principals.tsv`, `title.akas.tsv`)

## Quick Start

### Load from snapshot (recommended)

```bash
# Download
curl -LO https://github.com/samyama-ai/samyama-graph/releases/download/kg-snapshots-v8/imdb.sgsnap

# Start Samyama and import
./target/release/samyama
curl -X POST http://localhost:8080/api/tenants \
  -H 'Content-Type: application/json' \
  -d '{"id":"imdb","name":"IMDB KG"}'
curl -X POST http://localhost:8080/api/tenants/imdb/snapshot/import \
  -F "file=@imdb.sgsnap"
```

### Build from source

```bash
git clone https://github.com/samyama-ai/imdb-kg.git && cd imdb-kg
pip install -e ".[dev]"
mkdir -p data
curl -LO https://datasets.imdbws.com/title.basics.tsv.gz -o data/title.basics.tsv.gz
curl -LO https://datasets.imdbws.com/title.ratings.tsv.gz -o data/title.ratings.tsv.gz
curl -LO https://datasets.imdbws.com/name.basics.tsv.gz -o data/name.basics.tsv.gz
curl -LO https://datasets.imdbws.com/title.principals.tsv.gz -o data/title.principals.tsv.gz
curl -LO https://datasets.imdbws.com/title.akas.tsv.gz -o data/title.akas.tsv.gz
python -m etl.loader --data-dir data --min-votes 1000 --min-votes-series 500 --min-year 1950 --akas data/title.akas.tsv.gz
python -m etl.loader --data-dir data --max-titles 5000   # Quick test
```

## Example Queries

```cypher
-- Top-rated movies (min 50K votes)
MATCH (m:Movie)-[:HAS_RATING]->(r:Rating)
WHERE r.num_votes >= 50000
RETURN m.title, m.year, r.average_rating ORDER BY r.average_rating DESC LIMIT 5

-- Director-actor power pairs
MATCH (d:Person)-[:DIRECTED]->(m:Movie)<-[:ACTED_IN]-(a:Person)
RETURN d.name, a.name, count(m) AS films_together ORDER BY films_together DESC LIMIT 5
```

See the full **[100-query showcase](docs/100-queries.md)** -- from single-table aggregations to network intelligence that SQL cannot express.

## MCP Server

```bash
python -m mcp_server.server --max-titles 5000          # embedded, quick test
python -m mcp_server.server --url http://localhost:8080 # against a running Samyama server
python -m mcp_server.server --list-tools                # see all auto-generated + custom tools
```

## Links

| | |
|---|---|
| Samyama Graph | [github.com/samyama-ai/samyama-graph](https://github.com/samyama-ai/samyama-graph) |
| The Book | [samyama-ai.github.io/samyama-graph-book](https://samyama-ai.github.io/samyama-graph-book/) |
| IMDB Non-Commercial Datasets | [developer.imdb.com/non-commercial-datasets](https://developer.imdb.com/non-commercial-datasets/) |
| Contact | [samyama.dev/contact](https://samyama.dev/contact) |

## License

Apache 2.0. Data from IMDB Non-Commercial Datasets is for personal, non-commercial use only — see [IMDB terms](https://developer.imdb.com/non-commercial-datasets/) for full conditions.
