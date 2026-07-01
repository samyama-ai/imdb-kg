"""
IMDB Movies Knowledge Graph ETL Loader
=======================================
Loads IMDB non-commercial TSV datasets into a Samyama property graph. Creates
Movie, Series, Person, Genre, Rating and (optionally) AlternateTitle nodes and
relationship edges for cast, crew, genres and ratings.

Schema: 6 node labels, 7 edge types.
  Movie{tconst,title,year,runtime_minutes,title_type}
  Series{tconst,title,year,end_year}
  Person{nconst,name,birth_year,death_year}
  Genre{name}
  Rating{average_rating,num_votes}
  AlternateTitle{title,region,language}

  (:Movie|:Series)-[:HAS_GENRE]->(:Genre)
  (:Movie|:Series)-[:HAS_RATING]->(:Rating)
  (:Movie|:Series)-[:HAS_ALTERNATE_TITLE]->(:AlternateTitle)
  (:Person)-[:ACTED_IN]->(:Movie|:Series)
  (:Person)-[:DIRECTED]->(:Movie|:Series)
  (:Person)-[:WROTE]->(:Movie|:Series)
  (:Person)-[:PRODUCED]->(:Movie|:Series)

Required files in --data-dir (plain .tsv or .tsv.gz):
  title.basics.tsv      title.ratings.tsv
  name.basics.tsv       title.principals.tsv
Optional:
  --akas PATH            title.akas.tsv to add AlternateTitle nodes

Data source: https://developer.imdb.com/non-commercial-datasets/
License: IMDB Non-Commercial Use Only

Usage:
    python -m etl.loader --data-dir data --min-votes 5000
    python -m etl.loader --data-dir data --max-titles 5000 --akas data/title.akas.tsv
"""

import gzip
import os
import sys
import time
from pathlib import Path
from samyama import SamyamaClient

GRAPH = "default"

# _batch_create_edges builds one MATCH ... WHERE <AND-chain> ... CREATE query per call.
# Empirically, the graph engine's query parser stack-overflows (a native, uncatchable
# crash — not a Python exception) somewhere between 550-600 edges in a single such query.
# Keep every edge batch well under that so real (multi-genre, multi-cast) loads don't crash.
EDGE_BATCH_SIZE = 300

CAST_CREW_CATEGORIES = {"actor", "actress", "director", "writer", "producer"}
EDGE_BY_CATEGORY = {
    "actor": "ACTED_IN",
    "actress": "ACTED_IN",
    "director": "DIRECTED",
    "writer": "WROTE",
    "producer": "PRODUCED",
}


# ---------------------------------------------------------------------------
# Cypher helpers
# ---------------------------------------------------------------------------

def _escape(value) -> str:
    if value is None:
        return ""
    return str(value).replace('"', '').replace("\n", " ").replace("\r", "")


def _q(val) -> str:
    return f'"{_escape(val)}"'


def _prop_str(props: dict) -> str:
    parts = []
    for key, val in props.items():
        if val is None:
            continue
        if isinstance(val, (int, float)):
            parts.append(f"{key}: {val}")
        else:
            parts.append(f'{key}: {_q(val)}')
    return "{" + ", ".join(parts) + "}"


def _match_to_where(var_name, match_str):
    """Convert 'prop: "value"' to 'var.prop = "value"' for WHERE clause.

    Index scans only trigger with WHERE, not inline MATCH properties.
    """
    return f"{var_name}.{match_str.replace(': ', ' = ', 1)}"


def _batch_create_nodes(client, nodes):
    """Create multiple nodes in a single CREATE query. Each node: (label, props)."""
    if not nodes:
        return
    parts = [f"(:{label} {_prop_str(props)})" for label, props in nodes]
    client.query(f"CREATE {', '.join(parts)}", GRAPH)


def _batch_create_title_rating(client, titles):
    """Create Movie/Series nodes each connected to a fresh Rating node.

    Each item: (title_label, title_props, rating_props)

    Note: both endpoints need variable names — the graph engine silently
    drops the edge (while still creating both nodes) when a CREATE pattern
    connects two anonymous (unnamed) nodes.
    """
    if not titles:
        return
    parts = []
    for i, (label, title_props, rating_props) in enumerate(titles):
        parts.append(
            f"(t{i}:{label} {_prop_str(title_props)})"
            f"-[:HAS_RATING]->(r{i}:Rating {_prop_str(rating_props)})"
        )
    client.query(f"CREATE {', '.join(parts)}", GRAPH)


def _batch_create_edges(client, edges):
    """Create multiple edges between EXISTING nodes in one MATCH...WHERE...CREATE query.

    Each edge: (src_label, src_match_str, rel_type, tgt_label, tgt_match_str, props_or_None)
    Deduplicates MATCH patterns so each unique node is matched once.
    """
    if not edges:
        return
    var_map = {}
    match_parts = []
    where_parts = []
    create_parts = []

    for src_label, src_match, rel, tgt_label, tgt_match, props in edges:
        src_key = (src_label, src_match)
        tgt_key = (tgt_label, tgt_match)

        if src_key not in var_map:
            vname = f"n{len(var_map)}"
            var_map[src_key] = vname
            match_parts.append(f"({vname}:{src_label})")
            where_parts.append(_match_to_where(vname, src_match))

        if tgt_key not in var_map:
            vname = f"n{len(var_map)}"
            var_map[tgt_key] = vname
            match_parts.append(f"({vname}:{tgt_label})")
            where_parts.append(_match_to_where(vname, tgt_match))

        src_var = var_map[src_key]
        tgt_var = var_map[tgt_key]
        prop_part = f" {_prop_str(props)}" if props else ""
        create_parts.append(f"({src_var})-[:{rel}{prop_part}]->({tgt_var})")

    q = (f"MATCH {', '.join(match_parts)} "
         f"WHERE {' AND '.join(where_parts)} "
         f"CREATE {', '.join(create_parts)}")
    client.query(q, GRAPH)


def _batch_create_target_node_edges(client, items):
    """Create a NEW target node attached to an EXISTING source node, one MATCH per item.

    Each item: (src_label, src_match_str, rel_type, tgt_label, tgt_props)

    Note: the target node needs a variable name — the graph engine silently
    drops the edge (while still creating the node) when a CREATE pattern
    connects to an anonymous (unnamed) node.
    """
    if not items:
        return
    match_parts = []
    where_parts = []
    create_parts = []

    for i, (src_label, src_match, rel, tgt_label, tgt_props) in enumerate(items):
        vname = f"n{i}"
        tvname = f"t{i}"
        match_parts.append(f"({vname}:{src_label})")
        where_parts.append(_match_to_where(vname, src_match))
        create_parts.append(f"({vname})-[:{rel}]->({tvname}:{tgt_label} {_prop_str(tgt_props)})")

    q = (f"MATCH {', '.join(match_parts)} "
         f"WHERE {' AND '.join(where_parts)} "
         f"CREATE {', '.join(create_parts)}")
    client.query(q, GRAPH)


# ---------------------------------------------------------------------------
# TSV parsing helpers
# ---------------------------------------------------------------------------

def _open_tsv(path):
    """Open a plain .tsv or gzip-compressed .tsv.gz file, returning (header_cols, line_iter).

    Uses universal-newline translation so a trailing \\r isn't left dangling on the
    last column when the file has CRLF line endings (e.g. fixtures written on Windows).
    """
    gz_path = Path(str(path) + ".gz")
    path = Path(path)
    if path.exists():
        f = open(path, "r", encoding="utf-8")
    elif gz_path.exists():
        f = gzip.open(gz_path, "rt", encoding="utf-8")
    else:
        raise FileNotFoundError(f"File not found: {path} (also tried {gz_path})")
    header = f.readline().rstrip("\r\n").split("\t")
    return header, f


def _col_idx(headers, name):
    return headers.index(name)


def _field(fields, idx):
    return fields[idx].strip() if idx < len(fields) else ""


def _imdb_str(s):
    return None if (s == r"\N" or s == "") else s


def _imdb_int(s):
    s = _imdb_str(s)
    try:
        return int(s) if s is not None else None
    except ValueError:
        return None


def _imdb_float(s):
    s = _imdb_str(s)
    try:
        return float(s) if s is not None else None
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_imdb(
    client: SamyamaClient,
    data_dir: str = "data",
    min_votes: int = 1000,
    min_votes_series: int = 500,
    min_year: int = 1950,
    akas_path: str = None,
    max_titles: int = 0,
) -> dict:
    """
    Load IMDB non-commercial data into Samyama.

    Args:
        client: SamyamaClient instance.
        data_dir: Directory containing title.basics.tsv, title.ratings.tsv,
                  name.basics.tsv, title.principals.tsv (plain or .gz).
        min_votes: Minimum vote count for movies to be included.
        min_votes_series: Minimum vote count for TV series to be included.
        min_year: Earliest startYear to include.
        akas_path: Optional path to title.akas.tsv for AlternateTitle nodes.
        max_titles: Max titles to load (0 = all). Useful for quick tests.

    Returns:
        Dict with counts of all created entities.
    """
    indexes = [("Movie", "tconst"), ("Series", "tconst"), ("Person", "nconst"), ("Genre", "name")]
    for label, prop in indexes:
        try:
            client.query(f"CREATE INDEX ON :{label}({prop})", GRAPH)
        except Exception:
            pass
    print(f"Created {len(indexes)} indexes", flush=True)

    # --- Phase 1: ratings -> {tconst: (avg, votes)} ---
    print("Phase 1/4: Loading ratings ...", flush=True)
    ratings = {}
    headers, f = _open_tsv(os.path.join(data_dir, "title.ratings.tsv"))
    c_tconst, c_rating, c_votes = (_col_idx(headers, n) for n in ("tconst", "averageRating", "numVotes"))
    lower = min(min_votes, min_votes_series)
    for line in f:
        fields = line.rstrip("\n").split("\t")
        tconst = _field(fields, c_tconst)
        if not tconst:
            continue
        votes = _imdb_int(_field(fields, c_votes)) or 0
        if votes < lower:
            continue
        avg = _imdb_float(_field(fields, c_rating)) or 0.0
        ratings[tconst] = (avg, votes)
    f.close()
    print(f"  Titles with sufficient votes: {len(ratings):,}", flush=True)

    # --- Phase 2: titles -> Movie/Series + Rating + Genre nodes ---
    print("Phase 2/4: Loading titles and genres ...", flush=True)
    title_label = {}    # tconst -> "Movie" | "Series"
    known_genres = set()
    movie_count = 0
    series_count = 0
    rating_count = 0
    genre_edge_count = 0

    headers, f = _open_tsv(os.path.join(data_dir, "title.basics.tsv"))
    c_tconst, c_type, c_title, c_year, c_end, c_runtime, c_genres = (
        _col_idx(headers, n) for n in
        ("tconst", "titleType", "primaryTitle", "startYear", "endYear", "runtimeMinutes", "genres")
    )

    title_batch = []
    genre_node_batch = []
    genre_edge_batch = []
    t0 = time.time()
    processed = 0

    def flush_titles():
        nonlocal title_batch, genre_node_batch, genre_edge_batch
        if genre_node_batch:
            _batch_create_nodes(client, genre_node_batch)
            genre_node_batch = []
        if title_batch:
            _batch_create_title_rating(client, title_batch)
            title_batch = []
        if genre_edge_batch:
            _batch_create_edges(client, genre_edge_batch)
            genre_edge_batch = []

    for line in f:
        if max_titles and processed >= max_titles:
            break
        fields = line.rstrip("\n").split("\t")
        tconst = _field(fields, c_tconst)
        title_type = _field(fields, c_type)

        is_movie = title_type in ("movie", "tvMovie")
        is_series = title_type == "tvSeries"
        if not is_movie and not is_series:
            continue

        rating = ratings.get(tconst)
        if rating is None:
            continue
        avg_rating, num_votes = rating

        threshold = min_votes if is_movie else min_votes_series
        if num_votes < threshold:
            continue

        start_year = _imdb_int(_field(fields, c_year)) or 0
        if start_year and start_year < min_year:
            continue

        label = "Movie" if is_movie else "Series"
        primary_title = _field(fields, c_title)

        title_props = {"tconst": tconst, "title": primary_title}
        if start_year:
            title_props["year"] = start_year
        if is_movie:
            title_props["title_type"] = title_type
            rt = _imdb_int(_field(fields, c_runtime))
            if rt is not None:
                title_props["runtime_minutes"] = rt
        else:
            ey = _imdb_int(_field(fields, c_end))
            if ey is not None:
                title_props["end_year"] = ey

        title_batch.append((label, title_props, {"average_rating": avg_rating, "num_votes": num_votes}))
        title_label[tconst] = label
        rating_count += 1
        if is_movie:
            movie_count += 1
        else:
            series_count += 1

        genres_raw = _imdb_str(_field(fields, c_genres))
        if genres_raw:
            for genre in genres_raw.split(","):
                genre = genre.strip()
                if not genre:
                    continue
                if genre not in known_genres:
                    known_genres.add(genre)
                    genre_node_batch.append(("Genre", {"name": genre}))
                genre_edge_batch.append((label, f"tconst: {_q(tconst)}", "HAS_GENRE", "Genre", f"name: {_q(genre)}", None))
                genre_edge_count += 1

        processed += 1
        if len(genre_edge_batch) >= EDGE_BATCH_SIZE or len(title_batch) >= EDGE_BATCH_SIZE:
            flush_titles()
        if processed % 5000 == 0:
            elapsed = time.time() - t0
            print(f"  [{processed:,}] {elapsed:.0f}s — {movie_count:,} movies, {series_count:,} series", flush=True)

    flush_titles()
    f.close()
    print(f"  Movies: {movie_count:,}   Series: {series_count:,}   Genres: {len(known_genres):,}", flush=True)

    # --- Phase 3: principals -> collect (tconst, nconst, category, characters) ---
    print("Phase 3/4: Loading principals and persons ...", flush=True)
    headers, f = _open_tsv(os.path.join(data_dir, "title.principals.tsv"))
    c_tconst, c_nconst, c_category, c_characters = (
        _col_idx(headers, n) for n in ("tconst", "nconst", "category", "characters")
    )

    principal_recs = []
    nconst_set = set()
    scanned = 0
    t0 = time.time()
    for line in f:
        fields = line.rstrip("\n").split("\t")
        scanned += 1
        if scanned % 2_000_000 == 0:
            print(f"  Scanned {scanned // 1_000_000}M principal rows — {len(principal_recs):,} matched"
                  f" — {time.time() - t0:.0f}s", flush=True)

        tconst = _field(fields, c_tconst)
        category = _field(fields, c_category)
        if tconst not in title_label or category not in CAST_CREW_CATEGORIES:
            continue

        nconst = _field(fields, c_nconst)
        characters = _imdb_str(_field(fields, c_characters))
        if characters:
            characters = characters.replace("[", "").replace("]", "").replace('"', "").strip()
            characters = characters or None

        nconst_set.add(nconst)
        principal_recs.append((tconst, nconst, category, characters))
    f.close()
    print(f"  Matched {len(principal_recs):,} principal records ({len(nconst_set):,} unique persons)", flush=True)

    # --- Phase 4: names -> Person nodes ---
    headers, f = _open_tsv(os.path.join(data_dir, "name.basics.tsv"))
    c_nconst, c_name, c_birth, c_death = (
        _col_idx(headers, n) for n in ("nconst", "primaryName", "birthYear", "deathYear")
    )

    known_persons = set()
    person_batch = []
    scanned = 0
    t0 = time.time()
    for line in f:
        fields = line.rstrip("\n").split("\t")
        nconst = _field(fields, c_nconst)
        scanned += 1
        if scanned % 2_000_000 == 0:
            print(f"  Scanned {scanned // 1_000_000}M names — {len(known_persons):,} matched"
                  f" — {time.time() - t0:.0f}s", flush=True)

        if nconst not in nconst_set:
            continue

        props = {"nconst": nconst, "name": _field(fields, c_name)}
        by = _imdb_int(_field(fields, c_birth))
        if by is not None:
            props["birth_year"] = by
        dy = _imdb_int(_field(fields, c_death))
        if dy is not None:
            props["death_year"] = dy

        person_batch.append(("Person", props))
        known_persons.add(nconst)
        if len(person_batch) >= 2000:
            _batch_create_nodes(client, person_batch)
            person_batch = []
    if person_batch:
        _batch_create_nodes(client, person_batch)
    f.close()
    print(f"  Persons created: {len(known_persons):,}", flush=True)

    # Person -> Title edges
    print("  Creating person-title edges ...", flush=True)
    cast_crew_edges = 0
    edge_batch = []
    for tconst, nconst, category, characters in principal_recs:
        if nconst not in known_persons:
            continue
        rel = EDGE_BY_CATEGORY.get(category)
        if rel is None:
            continue
        props = {"characters": characters} if characters else None
        edge_batch.append(("Person", f"nconst: {_q(nconst)}", rel, title_label[tconst], f"tconst: {_q(tconst)}", props))
        cast_crew_edges += 1
        if len(edge_batch) >= EDGE_BATCH_SIZE:
            _batch_create_edges(client, edge_batch)
            edge_batch = []
    if edge_batch:
        _batch_create_edges(client, edge_batch)
    print(f"  Cast/crew edges: {cast_crew_edges:,}", flush=True)

    # --- Phase 5 (optional): akas -> AlternateTitle nodes ---
    # AlternateTitle nodes carry a synthetic, per-row-unique `_akas_seq` correlation key so
    # they can be created with a standalone CREATE and then wired up with a separate
    # MATCH (existing) ... CREATE (edge) query — the graph engine does not persist a
    # brand-new node when its CREATE pattern is chained directly after a MATCH clause, so
    # node creation and edge creation must be two distinct queries here (unlike the
    # title+rating batch, which has no preceding MATCH). The key must be unique per row
    # (not just per tconst) so a title with multiple alternate titles doesn't get its edges
    # re-matched-and-recreated when a later flush touches the same tconst again.
    alt_title_count = 0
    if akas_path:
        print("Phase 5/5: Loading alternate titles ...", flush=True)
        headers, f = _open_tsv(akas_path)
        c_title_id, c_title, c_region, c_language, c_original = (
            _col_idx(headers, n) for n in ("titleId", "title", "region", "language", "isOriginalTitle")
        )

        akas_node_batch = []
        akas_edge_batch = []
        akas_seq = 0
        scanned = 0
        t0 = time.time()

        def flush_akas():
            nonlocal akas_node_batch, akas_edge_batch
            if akas_node_batch:
                _batch_create_nodes(client, akas_node_batch)
                akas_node_batch = []
            if akas_edge_batch:
                _batch_create_edges(client, akas_edge_batch)
                akas_edge_batch = []

        for line in f:
            fields = line.rstrip("\n").split("\t")
            scanned += 1
            if scanned % 2_000_000 == 0:
                print(f"  Scanned {scanned // 1_000_000}M akas rows — {alt_title_count:,} alt titles"
                      f" — {time.time() - t0:.0f}s", flush=True)

            title_id = _field(fields, c_title_id)
            label = title_label.get(title_id)
            if label is None:
                continue
            if _field(fields, c_original) == "1":
                continue
            alt_title = _imdb_str(_field(fields, c_title))
            if not alt_title:
                continue

            akas_seq += 1
            props = {"title": alt_title, "tconst": title_id, "_akas_seq": akas_seq}
            region = _imdb_str(_field(fields, c_region))
            if region:
                props["region"] = region
            language = _imdb_str(_field(fields, c_language))
            if language:
                props["language"] = language

            akas_node_batch.append(("AlternateTitle", props))
            akas_edge_batch.append((
                label, f"tconst: {_q(title_id)}",
                "HAS_ALTERNATE_TITLE",
                "AlternateTitle", f"_akas_seq: {akas_seq}",
                None,
            ))
            alt_title_count += 1
            if len(akas_edge_batch) >= EDGE_BATCH_SIZE:
                flush_akas()
        flush_akas()
        f.close()
        print(f"  AlternateTitles created: {alt_title_count:,}", flush=True)

    counts = {
        "movies": movie_count,
        "series": series_count,
        "persons": len(known_persons),
        "genres": len(known_genres),
        "ratings": rating_count,
        "alternate_titles": alt_title_count,
        "genre_edges": genre_edge_count,
        "cast_crew_edges": cast_crew_edges,
        "nodes": movie_count + series_count + len(known_persons) + len(known_genres) + rating_count + alt_title_count,
        "edges": rating_count + genre_edge_count + cast_crew_edges + alt_title_count,
    }

    print(f"\n{'='*60}", flush=True)
    print("IMDB KG load complete", flush=True)
    print(f"{'='*60}", flush=True)
    for k, v in counts.items():
        print(f"  {k:<17s} {v:,}", flush=True)
    return counts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Load IMDB non-commercial datasets into Samyama")
    ap.add_argument("--data-dir", default="data", help="Path to IMDB .tsv files")
    ap.add_argument("--min-votes", type=int, default=1000, help="Min votes for movies (default: 1000)")
    ap.add_argument("--min-votes-series", type=int, default=500, help="Min votes for series (default: 500)")
    ap.add_argument("--min-year", type=int, default=1950, help="Earliest start year (default: 1950)")
    ap.add_argument("--akas", default=None, help="Path to title.akas.tsv for AlternateTitle nodes")
    ap.add_argument("--max-titles", type=int, default=0, help="Max titles to load (0=all)")
    ap.add_argument("--url", default=None, help="Samyama server URL (omit for embedded)")
    args = ap.parse_args()

    c = SamyamaClient.connect(args.url) if args.url else SamyamaClient.embedded()
    load_imdb(
        c,
        data_dir=args.data_dir,
        min_votes=args.min_votes,
        min_votes_series=args.min_votes_series,
        min_year=args.min_year,
        akas_path=args.akas,
        max_titles=args.max_titles,
    )
