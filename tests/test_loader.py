"""Tests for the IMDB ETL loader against embedded Samyama."""

import os
import tempfile

import pytest
from samyama import SamyamaClient

from etl.loader import load_imdb

TITLE_BASICS = "\t".join(
    ["tconst", "titleType", "primaryTitle", "originalTitle", "isAdult",
     "startYear", "endYear", "runtimeMinutes", "genres"]
) + "\n" + "\n".join([
    "tt0000001\tmovie\tTest Movie One\tTest Movie One\t0\t2010\t\\N\t120\tAction,Drama",
    "tt0000002\tmovie\tTest Movie Two\tTest Movie Two\t0\t1980\t\\N\t95\tComedy",
    "tt0000003\ttvSeries\tTest Series\tTest Series\t0\t2015\t2020\t\\N\tDrama,Crime",
    "tt0000004\tshort\tIgnored Short\tIgnored Short\t0\t2010\t\\N\t5\tComedy",
    "tt0000005\tmovie\tLow Vote Movie\tLow Vote Movie\t0\t2012\t\\N\t90\tDrama",
]) + "\n"

TITLE_RATINGS = "\t".join(["tconst", "averageRating", "numVotes"]) + "\n" + "\n".join([
    "tt0000001\t8.5\t100000",
    "tt0000002\t6.0\t1500",
    "tt0000003\t9.0\t20000",
    "tt0000005\t5.0\t500",
]) + "\n"

NAME_BASICS = "\t".join(
    ["nconst", "primaryName", "birthYear", "deathYear", "primaryProfession", "knownForTitles"]
) + "\n" + "\n".join([
    "nm0000001\tDirector One\t1950\t\\N\tdirector\ttt0000001",
    "nm0000002\tActor One\t1960\t\\N\tactor\ttt0000001",
    "nm0000003\tActor Two\t1970\t\\N\tactress\ttt0000001",
    "nm0000004\tWriter One\t1965\t\\N\twriter\ttt0000002",
]) + "\n"

TITLE_PRINCIPALS = "\t".join(
    ["tconst", "ordering", "nconst", "category", "job", "characters"]
) + "\n" + "\n".join([
    'tt0000001\t1\tnm0000001\tdirector\t\\N\t\\N',
    'tt0000001\t2\tnm0000002\tactor\t\\N\t["John"]',
    'tt0000001\t3\tnm0000003\tactress\t\\N\t["Jane"]',
    'tt0000002\t1\tnm0000001\tdirector\t\\N\t\\N',
    'tt0000002\t2\tnm0000004\twriter\t\\N\t\\N',
    'tt0000003\t1\tnm0000001\tdirector\t\\N\t\\N',
    'tt0000003\t2\tnm0000002\tactor\t\\N\t["Lead"]',
]) + "\n"

TITLE_AKAS = "\t".join(
    ["titleId", "ordering", "title", "region", "language", "types", "attributes", "isOriginalTitle"]
) + "\n" + "\n".join([
    "tt0000001\t1\tTest Movie One\tUS\ten\t\\N\t\\N\t1",
    "tt0000001\t2\tPelicula de Prueba Uno\tES\tes\t\\N\t\\N\t0",
]) + "\n"


def _write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


@pytest.fixture(scope="module")
def loaded_graph():
    """Load the synthetic fixture dataset into an embedded graph."""
    c = SamyamaClient.embedded()
    with tempfile.TemporaryDirectory() as tmpdir:
        _write(os.path.join(tmpdir, "title.basics.tsv"), TITLE_BASICS)
        _write(os.path.join(tmpdir, "title.ratings.tsv"), TITLE_RATINGS)
        _write(os.path.join(tmpdir, "name.basics.tsv"), NAME_BASICS)
        _write(os.path.join(tmpdir, "title.principals.tsv"), TITLE_PRINCIPALS)
        akas_path = os.path.join(tmpdir, "title.akas.tsv")
        _write(akas_path, TITLE_AKAS)
        stats = load_imdb(
            c, data_dir=tmpdir,
            min_votes=1000, min_votes_series=500, min_year=1950,
            akas_path=akas_path,
        )
    return c, stats


def _q(client, cypher):
    r = client.query_readonly(cypher, "default")
    return [dict(zip(r.columns, row)) for row in r.records]


class TestTitles:
    def test_movie_and_series_counts(self, loaded_graph):
        c, stats = loaded_graph
        assert stats["movies"] == 2
        assert stats["series"] == 1

    def test_short_is_excluded(self, loaded_graph):
        c, _ = loaded_graph
        rows = _q(c, "MATCH (m:Movie {tconst: 'tt0000004'}) RETURN m")
        assert len(rows) == 0

    def test_movie_properties(self, loaded_graph):
        c, _ = loaded_graph
        rows = _q(c, "MATCH (m:Movie {tconst: 'tt0000001'}) "
                      "RETURN m.title, m.year, m.runtime_minutes, m.title_type")
        assert len(rows) == 1
        m = rows[0]
        assert m["m.title"] == "Test Movie One"
        assert m["m.year"] == 2010
        assert m["m.runtime_minutes"] == 120
        assert m["m.title_type"] == "movie"

    def test_series_properties(self, loaded_graph):
        c, _ = loaded_graph
        rows = _q(c, "MATCH (s:Series {tconst: 'tt0000003'}) RETURN s.title, s.year, s.end_year")
        assert len(rows) == 1
        assert rows[0]["s.title"] == "Test Series"
        assert rows[0]["s.year"] == 2015
        assert rows[0]["s.end_year"] == 2020


class TestRatings:
    def test_rating_count(self, loaded_graph):
        c, stats = loaded_graph
        assert stats["ratings"] == 3

    def test_has_rating_edge(self, loaded_graph):
        c, _ = loaded_graph
        rows = _q(c, "MATCH (m:Movie {tconst: 'tt0000001'})-[:HAS_RATING]->(r:Rating) "
                      "RETURN r.average_rating, r.num_votes")
        assert len(rows) == 1
        assert rows[0]["r.average_rating"] == 8.5
        assert rows[0]["r.num_votes"] == 100000

    def test_low_vote_movie_excluded(self, loaded_graph):
        """A movie below min_votes (500 < 1000) never gets created."""
        c, _ = loaded_graph
        rows = _q(c, "MATCH (m {tconst: 'tt0000005'}) RETURN m")
        assert len(rows) == 0


class TestGenres:
    def test_genre_count(self, loaded_graph):
        c, stats = loaded_graph
        assert stats["genres"] == 4  # Action, Drama, Comedy, Crime

    def test_genre_dedup(self, loaded_graph):
        """Drama is shared by Movie One and Series — should be a single node."""
        c, _ = loaded_graph
        rows = _q(c, "MATCH (g:Genre {name: 'Drama'}) RETURN g")
        assert len(rows) == 1

    def test_has_genre_edges(self, loaded_graph):
        c, _ = loaded_graph
        rows = _q(c, "MATCH (:Movie {tconst: 'tt0000001'})-[:HAS_GENRE]->(g:Genre) "
                      "RETURN g.name ORDER BY g.name")
        names = [r["g.name"] for r in rows]
        assert names == ["Action", "Drama"]


class TestPersons:
    def test_person_count(self, loaded_graph):
        c, stats = loaded_graph
        assert stats["persons"] == 4

    def test_person_properties(self, loaded_graph):
        c, _ = loaded_graph
        rows = _q(c, "MATCH (p:Person {nconst: 'nm0000001'}) RETURN p.name, p.birth_year")
        assert rows[0]["p.name"] == "Director One"
        assert rows[0]["p.birth_year"] == 1950


class TestCastCrewEdges:
    def test_directed_edge(self, loaded_graph):
        c, _ = loaded_graph
        rows = _q(c, "MATCH (p:Person {nconst: 'nm0000001'})-[:DIRECTED]->(m) RETURN m.tconst ORDER BY m.tconst")
        tconsts = [r["m.tconst"] for r in rows]
        assert tconsts == ["tt0000001", "tt0000002", "tt0000003"]

    def test_acted_in_with_characters(self, loaded_graph):
        c, _ = loaded_graph
        rows = _q(c, "MATCH (p:Person {nconst: 'nm0000002'})-[r:ACTED_IN]->(m:Movie {tconst: 'tt0000001'}) "
                      "RETURN r.characters")
        assert len(rows) == 1
        assert rows[0]["r.characters"] == "John"

    def test_wrote_edge(self, loaded_graph):
        c, _ = loaded_graph
        rows = _q(c, "MATCH (p:Person {nconst: 'nm0000004'})-[:WROTE]->(m:Movie {tconst: 'tt0000002'}) RETURN m")
        assert len(rows) == 1


class TestAlternateTitles:
    def test_alt_title_count(self, loaded_graph):
        c, stats = loaded_graph
        assert stats["alternate_titles"] == 1  # only the non-original row

    def test_alt_title_edge(self, loaded_graph):
        c, _ = loaded_graph
        rows = _q(c, "MATCH (:Movie {tconst: 'tt0000001'})-[:HAS_ALTERNATE_TITLE]->(a:AlternateTitle) "
                      "RETURN a.title, a.region, a.language")
        assert len(rows) == 1
        assert rows[0]["a.title"] == "Pelicula de Prueba Uno"
        assert rows[0]["a.region"] == "ES"


class TestMultiHopQueries:
    def test_director_actor_pairs(self, loaded_graph):
        """Multi-hop: director -> movie <- actor."""
        c, _ = loaded_graph
        rows = _q(c, """
            MATCH (d:Person {nconst: 'nm0000001'})-[:DIRECTED]->(m:Movie)<-[:ACTED_IN]-(a:Person)
            RETURN a.name ORDER BY a.name
        """)
        names = {r["a.name"] for r in rows}
        assert "Actor One" in names
        assert "Actor Two" in names

    def test_genre_to_director(self, loaded_graph):
        """Multi-hop: genre -> movie <- director.

        Director One directs both the Drama-tagged movie and the Drama-tagged
        series, so the (deduped in Python — see note below) result is one name
        appearing across two underlying paths.
        """
        c, _ = loaded_graph
        rows = _q(c, """
            MATCH (g:Genre {name: 'Drama'})<-[:HAS_GENRE]-(m)<-[:DIRECTED]-(d:Person)
            RETURN d.name
        """)
        # NOTE: this embedded build does not dedupe `RETURN DISTINCT <expr>` (verified via a
        # minimal repro query), so we dedupe client-side instead of relying on DISTINCT.
        names = {r["d.name"] for r in rows}
        assert names == {"Director One"}
