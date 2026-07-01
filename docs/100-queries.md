# 100 Cypher Queries for the IMDB Movies Knowledge Graph

**Movies, TV series, persons, genres and ratings from the IMDB non-commercial dataset.**

These queries are organized in five progressive levels that illustrate where relational databases hit their ceiling and where graph databases take over.

| Level | Name | SQL Equivalent | Queries |
|-------|------|----------------|---------|
| 1 | **Foundation** | Single table, GROUP BY | 1--15 |
| 2 | **Relational Joins** | 2-table JOIN | 16--35 |
| 3 | **Multi-hop Traversals** | 3--5 JOINs, self-joins | 36--60 |
| 4 | **Path & Pattern Analytics** | Recursive CTEs, breaks down | 61--80 |
| 5 | **Network Intelligence** | Impossible in SQL | 81--100 |

---

## Level 1: Foundation (SQL-equivalent)

*These queries scan a single node type or edge type. Any RDBMS handles them trivially with a single table and GROUP BY.*

### 1. Total titles by type

```cypher
MATCH (m:Movie)
RETURN m.title_type AS title_type, count(m) AS movies
ORDER BY movies DESC
```

### 2. Total movies, series, and persons in the dataset

```cypher
MATCH (n) RETURN labels(n)[0] AS label, count(n) AS total
ORDER BY total DESC
```

### 3. Movies released per decade

```cypher
MATCH (m:Movie)
RETURN (toInteger(m.year) / 10) * 10 AS decade, count(m) AS movies
ORDER BY decade
```

### 4. Top 20 highest-rated movies

```cypher
MATCH (m:Movie)-[:HAS_RATING]->(r:Rating)
WHERE r.num_votes >= 50000
RETURN m.title AS title, m.year AS year, r.average_rating AS rating, r.num_votes AS votes
ORDER BY rating DESC
LIMIT 20
```

### 5. Top 20 most-voted movies

```cypher
MATCH (m:Movie)-[:HAS_RATING]->(r:Rating)
RETURN m.title AS title, m.year AS year, r.num_votes AS votes, r.average_rating AS rating
ORDER BY votes DESC
LIMIT 20
```

### 6. Longest movies by runtime

```cypher
MATCH (m:Movie)
WHERE m.runtime_minutes IS NOT NULL
RETURN m.title AS title, m.year AS year, m.runtime_minutes AS minutes
ORDER BY minutes DESC
LIMIT 20
```

### 7. All genres and how many movies tag them

```cypher
MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre)
RETURN g.name AS genre, count(m) AS movies
ORDER BY movies DESC
```

### 8. Persons by birth decade

```cypher
MATCH (p:Person)
WHERE p.birth_year IS NOT NULL
RETURN (toInteger(p.birth_year) / 10) * 10 AS decade, count(p) AS persons
ORDER BY decade
```

### 9. Longest-running TV series

```cypher
MATCH (s:Series)
WHERE s.end_year IS NOT NULL AND s.year IS NOT NULL
RETURN s.title AS series, s.year AS start_year, s.end_year AS end_year,
       s.end_year - s.year AS years_running
ORDER BY years_running DESC
LIMIT 20
```

### 10. Movies released in the last 10 catalogued years

```cypher
MATCH (m:Movie)
WHERE m.year >= 2014
RETURN m.year AS year, count(m) AS movies
ORDER BY year DESC
```

### 11. Persons still alive (no death_year recorded)

```cypher
MATCH (p:Person)
WHERE p.birth_year IS NOT NULL AND p.death_year IS NULL
RETURN count(p) AS living_persons_on_record
```

### 12. Rating distribution buckets

```cypher
MATCH (:Movie)-[:HAS_RATING]->(r:Rating)
RETURN toInteger(r.average_rating) AS rating_bucket, count(r) AS movies
ORDER BY rating_bucket
```

### 13. Total alternate titles and the regions they cover

```cypher
MATCH (a:AlternateTitle)
WHERE a.region IS NOT NULL
RETURN a.region AS region, count(a) AS alternate_titles
ORDER BY alternate_titles DESC
LIMIT 20
```

### 14. Genre catalogue (alphabetical)

```cypher
MATCH (g:Genre)
RETURN g.name AS genre
ORDER BY genre
```

### 15. Series end-year breakdown

```cypher
MATCH (s:Series)
WHERE s.end_year IS NOT NULL
RETURN s.end_year AS ended, count(s) AS series
ORDER BY ended DESC
LIMIT 15
```

---

## Level 2: Relational Joins (SQL with 2-table JOINs)

*These queries join two entities. SQL can handle them with standard JOINs, but the queries are already more natural in Cypher.*

### 16. Top-rated movies with at least 50K votes

```cypher
MATCH (m:Movie)-[:HAS_RATING]->(r:Rating)
WHERE r.num_votes >= 50000
RETURN m.title AS title, m.year AS year, r.average_rating AS rating, r.num_votes AS votes
ORDER BY rating DESC
LIMIT 20
```

### 17. Top-rated TV series with at least 10K votes

```cypher
MATCH (s:Series)-[:HAS_RATING]->(r:Rating)
WHERE r.num_votes >= 10000
RETURN s.title AS series, s.year AS start_year, r.average_rating AS rating, r.num_votes AS votes
ORDER BY rating DESC
LIMIT 20
```

### 18. Top-rated Action movies

```cypher
MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre {name: 'Action'})
MATCH (m)-[:HAS_RATING]->(r:Rating)
WHERE r.num_votes >= 10000
RETURN m.title AS title, m.year AS year, r.average_rating AS rating
ORDER BY rating DESC
LIMIT 20
```

### 19. Most prolific actors (by credited appearances)

```cypher
MATCH (p:Person)-[:ACTED_IN]->(m)
RETURN p.name AS actor, count(m) AS credits
ORDER BY credits DESC
LIMIT 20
```

### 20. Most prolific directors

```cypher
MATCH (p:Person)-[:DIRECTED]->(m)
RETURN p.name AS director, count(m) AS credits
ORDER BY credits DESC
LIMIT 20
```

### 21. Most prolific writers

```cypher
MATCH (p:Person)-[:WROTE]->(m)
RETURN p.name AS writer, count(m) AS credits
ORDER BY credits DESC
LIMIT 20
```

### 22. Most prolific producers

```cypher
MATCH (p:Person)-[:PRODUCED]->(m)
RETURN p.name AS producer, count(m) AS credits
ORDER BY credits DESC
LIMIT 20
```

### 23. Genre popularity by total audience votes

```cypher
MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre)
MATCH (m)-[:HAS_RATING]->(r:Rating)
RETURN g.name AS genre, count(m) AS movies, sum(r.num_votes) AS total_votes
ORDER BY total_votes DESC
LIMIT 20
```

### 24. Genre quality ranking (average rating, min sample size)

```cypher
MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre)
MATCH (m)-[:HAS_RATING]->(r:Rating)
WITH g, count(m) AS movies, avg(r.average_rating) AS avg_rating
WHERE movies >= 100
RETURN g.name AS genre, movies, round(avg_rating * 10) / 10.0 AS avg_rating
ORDER BY avg_rating DESC
LIMIT 20
```

### 25. Movies with the most alternate (localized) titles

```cypher
MATCH (m:Movie)-[:HAS_ALTERNATE_TITLE]->(a:AlternateTitle)
RETURN m.title AS title, count(a) AS alternate_titles
ORDER BY alternate_titles DESC
LIMIT 20
```

### 26. Alternate titles by language

```cypher
MATCH (:Movie)-[:HAS_ALTERNATE_TITLE]->(a:AlternateTitle)
WHERE a.language IS NOT NULL
RETURN a.language AS language, count(a) AS alternate_titles
ORDER BY alternate_titles DESC
LIMIT 20
```

### 27. Most prolific deceased actors (career retrospective)

```cypher
MATCH (p:Person)-[:ACTED_IN]->(m)
WHERE p.death_year IS NOT NULL
RETURN p.name AS actor, p.birth_year AS born, p.death_year AS died, count(m) AS credits
ORDER BY credits DESC
LIMIT 20
```

### 28. Longest highly-rated movies

```cypher
MATCH (m:Movie)-[:HAS_RATING]->(r:Rating)
WHERE m.runtime_minutes IS NOT NULL AND r.average_rating >= 8.0 AND r.num_votes >= 10000
RETURN m.title AS title, m.runtime_minutes AS minutes, r.average_rating AS rating
ORDER BY minutes DESC
LIMIT 20
```

### 29. Languages most represented in alternate titles

```cypher
MATCH (:Series)-[:HAS_ALTERNATE_TITLE]->(a:AlternateTitle)
WHERE a.language IS NOT NULL
RETURN a.language AS language, count(a) AS alternate_titles
ORDER BY alternate_titles DESC
LIMIT 15
```

### 30. Decades with the most TV series launched

```cypher
MATCH (s:Series)
RETURN (toInteger(s.year) / 10) * 10 AS decade, count(s) AS series_launched
ORDER BY decade
```

### 31. Top actresses by credited appearances

```cypher
MATCH (p:Person)-[r:ACTED_IN]->(m)
WHERE r.characters IS NOT NULL
RETURN p.name AS actor, count(m) AS named_roles
ORDER BY named_roles DESC
LIMIT 20
```

### 32. Movies released in a specific year

```cypher
MATCH (m:Movie)-[:HAS_RATING]->(r:Rating)
WHERE m.year = 1994
RETURN m.title AS title, r.average_rating AS rating, r.num_votes AS votes
ORDER BY rating DESC
LIMIT 20
```

### 33. Highest-rated title per type (movie vs. TV movie)

```cypher
MATCH (m:Movie)-[:HAS_RATING]->(r:Rating)
WHERE r.num_votes >= 5000
RETURN m.title_type AS title_type, m.title AS title, r.average_rating AS rating
ORDER BY m.title_type, rating DESC
LIMIT 30
```

### 34. Persons who have only acting credits (no crew roles)

```cypher
MATCH (p:Person)-[:ACTED_IN]->(m)
WITH p, count(m) AS acted
WHERE NOT (p)-[:DIRECTED|WROTE|PRODUCED]->()
RETURN p.name AS actor, acted
ORDER BY acted DESC
LIMIT 20
```

### 35. Series ending in a specific year

```cypher
MATCH (s:Series)-[:HAS_RATING]->(r:Rating)
WHERE s.end_year = 2019
RETURN s.title AS series, r.average_rating AS rating, r.num_votes AS votes
ORDER BY rating DESC
LIMIT 15
```

---

## Level 3: Multi-hop Traversals (SQL starts struggling)

*These queries traverse 3+ entity types. In SQL, each hop requires another JOIN, subquery, or CTE. Performance degrades as hop count increases. In Cypher, the query remains readable and the graph engine optimizes traversal natively.*

### 36. Director–actor power pairs (top collaborations)

```cypher
MATCH (d:Person)-[:DIRECTED]->(m:Movie)<-[:ACTED_IN]-(a:Person)
RETURN d.name AS director, a.name AS actor, count(m) AS films_together
ORDER BY films_together DESC
LIMIT 25
```

> **Why graphs win**: This is a *self-join* on the person table through two different relationship types meeting at the same movie. In SQL: `SELECT ... FROM directed d JOIN acted_in a ON d.movie_id = a.movie_id JOIN persons ... GROUP BY ...`. In a graph, it's two edge traversals from one node.

### 37. A specific director–actor pair — complete shared filmography

```cypher
MATCH (d:Person {name: 'Christopher Nolan'})-[:DIRECTED]->(m:Movie)<-[:ACTED_IN]-(a:Person {name: 'Michael Caine'})
RETURN m.title AS title, m.year AS year
ORDER BY year
```

### 38. Top-rated movie per genre (3-hop: Genre→Movie→Rating)

*Ranks every genre/movie/rating combination; the highest-rated title per genre floats to the top.*

```cypher
MATCH (g:Genre)<-[:HAS_GENRE]-(m:Movie)-[:HAS_RATING]->(r:Rating)
WHERE r.num_votes >= 10000
WITH g, m, r
ORDER BY r.average_rating DESC
RETURN g.name AS genre, m.title AS top_movie, r.average_rating AS rating
ORDER BY rating DESC
LIMIT 20
```

### 39. Most prolific director per decade

*Ranks all director-decade film counts; the busiest director per decade floats to the top.*

```cypher
MATCH (d:Person)-[:DIRECTED]->(m:Movie)
WITH d, (toInteger(m.year) / 10) * 10 AS decade, count(m) AS films
ORDER BY films DESC
RETURN decade, d.name AS top_director, films
ORDER BY decade
LIMIT 20
```

### 40. Genre output by decade

```cypher
MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre)
WHERE g.name = 'Horror'
RETURN (toInteger(m.year) / 10) * 10 AS decade, count(m) AS movies
ORDER BY decade
```

### 41. Persons who both directed and starred in the same movie

```cypher
MATCH (p:Person)-[:DIRECTED]->(m:Movie)
MATCH (p)-[:ACTED_IN]->(m)
RETURN p.name AS actor_director, m.title AS title, m.year AS year
ORDER BY m.year DESC
LIMIT 25
```

### 42. Genres where the highest-vote movies cluster

```cypher
MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre)
MATCH (m)-[:HAS_RATING]->(r:Rating)
WHERE r.num_votes >= 100000
RETURN g.name AS genre, count(m) AS blockbusters
ORDER BY blockbusters DESC
LIMIT 20
```

### 43. Best average rating by genre (min 50 movies)

```cypher
MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre)
MATCH (m)-[:HAS_RATING]->(r:Rating)
WITH g, count(m) AS movies, avg(r.average_rating) AS avg_rating
WHERE movies >= 50
RETURN g.name AS genre, movies, round(avg_rating * 10) / 10.0 AS avg_rating
ORDER BY avg_rating DESC
LIMIT 15
```

### 44. Full performance breakdown for a specific person

```cypher
MATCH (p:Person {name: 'Tom Hanks'})-[:ACTED_IN]->(m)
RETURN labels(m)[0] AS title_type, count(m) AS credits
ORDER BY credits DESC
```

### 45. Head-to-head: shared filmography between two actors

```cypher
MATCH (a1:Person {name: 'Leonardo DiCaprio'})-[:ACTED_IN]->(m:Movie)<-[:ACTED_IN]-(a2:Person {name: 'Kate Winslet'})
RETURN m.title AS title, m.year AS year
ORDER BY year
```

### 46. Most acclaimed actors within a genre (min vote floor)

```cypher
MATCH (a:Person)-[:ACTED_IN]->(m:Movie)-[:HAS_GENRE]->(g:Genre {name: 'Sci-Fi'})
MATCH (m)-[:HAS_RATING]->(r:Rating)
WHERE r.num_votes >= 20000
RETURN a.name AS actor, count(m) AS films, round(avg(r.average_rating) * 10) / 10.0 AS avg_rating
ORDER BY films DESC
LIMIT 15
```

### 47. Directors with the widest actor roster

```cypher
MATCH (d:Person)-[:DIRECTED]->(m:Movie)<-[:ACTED_IN]-(a:Person)
RETURN d.name AS director, count(DISTINCT a) AS distinct_actors, count(DISTINCT m) AS films
ORDER BY distinct_actors DESC
LIMIT 20
```

### 48. Top writer–director combos

```cypher
MATCH (w:Person)-[:WROTE]->(m:Movie)<-[:DIRECTED]-(d:Person)
RETURN w.name AS writer, d.name AS director, count(m) AS films_together
ORDER BY films_together DESC
LIMIT 20
```

### 49. Top TV series by genre

```cypher
MATCH (s:Series)-[:HAS_GENRE]->(g:Genre {name: 'Crime'})
MATCH (s)-[:HAS_RATING]->(r:Rating)
WHERE r.num_votes >= 5000
RETURN s.title AS series, r.average_rating AS rating, r.num_votes AS votes
ORDER BY rating DESC
LIMIT 15
```

### 50. Title-type breakdown by decade

```cypher
MATCH (m:Movie)
RETURN (toInteger(m.year) / 10) * 10 AS decade, m.title_type AS title_type, count(m) AS movies
ORDER BY decade, movies DESC
```

### 51. Triple-credit persons (acted, directed, and wrote)

```cypher
MATCH (p:Person)-[:ACTED_IN]->(m1)
MATCH (p)-[:DIRECTED]->(m2)
MATCH (p)-[:WROTE]->(m3)
RETURN DISTINCT p.name AS person
LIMIT 25
```

### 52. Genre footprint for a specific person

```cypher
MATCH (p:Person {name: 'Meryl Streep'})-[:ACTED_IN]->(m:Movie)-[:HAS_GENRE]->(g:Genre)
RETURN g.name AS genre, count(m) AS films
ORDER BY films DESC
```

### 53. Average runtime by genre

```cypher
MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre)
WHERE m.runtime_minutes IS NOT NULL
RETURN g.name AS genre, round(avg(m.runtime_minutes)) AS avg_minutes, count(m) AS movies
ORDER BY avg_minutes DESC
LIMIT 20
```

### 54. Year-over-year average rating trend

```cypher
MATCH (m:Movie)-[:HAS_RATING]->(r:Rating)
WHERE r.num_votes >= 5000
RETURN m.year AS year, count(m) AS movies, round(avg(r.average_rating) * 10) / 10.0 AS avg_rating
ORDER BY year
```

### 55. Most versatile actors (distinct genres worked in)

```cypher
MATCH (p:Person)-[:ACTED_IN]->(m:Movie)-[:HAS_GENRE]->(g:Genre)
WITH p, count(DISTINCT g) AS genres, count(DISTINCT m) AS films
RETURN p.name AS actor, genres, films
ORDER BY genres DESC
LIMIT 20
```

### 56. Vote concentration by decade and genre

```cypher
MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre {name: 'Animation'})
MATCH (m)-[:HAS_RATING]->(r:Rating)
RETURN (toInteger(m.year) / 10) * 10 AS decade, sum(r.num_votes) AS total_votes
ORDER BY decade
```

### 57. Highest combined-rating director–actor team (min 3 films)

```cypher
MATCH (d:Person)-[:DIRECTED]->(m:Movie)<-[:ACTED_IN]-(a:Person)
MATCH (m)-[:HAS_RATING]->(r:Rating)
WITH d, a, count(m) AS films, avg(r.average_rating) AS avg_rating
WHERE films >= 3
RETURN d.name AS director, a.name AS actor, films, round(avg_rating * 10) / 10.0 AS avg_rating
ORDER BY avg_rating DESC
LIMIT 20
```

### 58. Co-starring pairs in the highest-vote movies

```cypher
MATCH (a1:Person)-[:ACTED_IN]->(m:Movie)<-[:ACTED_IN]-(a2:Person)
MATCH (m)-[:HAS_RATING]->(r:Rating)
WHERE a1.name < a2.name AND r.num_votes >= 200000
RETURN a1.name AS actor1, a2.name AS actor2, m.title AS title, r.num_votes AS votes
ORDER BY votes DESC
LIMIT 20
```

### 59. Most-acted-in genre per decade for the busiest actors

*Ranks all actor-decade-genre combinations; the dominant genre per decade floats to the top.*

```cypher
MATCH (a:Person)-[:ACTED_IN]->(m:Movie)-[:HAS_GENRE]->(g:Genre)
WITH (toInteger(m.year) / 10) * 10 AS decade, g, count(m) AS films
ORDER BY films DESC
RETURN decade, g.name AS top_genre, films
ORDER BY decade
LIMIT 20
```

### 60. Role breakdown for a specific person

```cypher
MATCH (p:Person {name: 'Clint Eastwood'})-[r:ACTED_IN|DIRECTED|WROTE|PRODUCED]->(m)
RETURN type(r) AS role, count(m) AS credits
ORDER BY credits DESC
```

---

## Level 4: Path & Pattern Analytics (SQL breaks down)

*These queries involve multi-entity patterns, conditional path traversal, and aggregations across connected subgraphs. In SQL, each requires recursive CTEs, multiple self-joins, or complex subqueries. Query plans explode. In a graph database, the pattern matching engine handles them natively.*

### 61. Actors who worked across the widest range of genres

```cypher
MATCH (a:Person)-[:ACTED_IN]->(m:Movie)-[:HAS_GENRE]->(g:Genre)
WITH a, collect(DISTINCT g.name) AS genres
WHERE size(genres) >= 6
RETURN a.name AS actor, genres, size(genres) AS genre_count
ORDER BY genre_count DESC
LIMIT 25
```

> **Why SQL breaks**: Requires a self-join on persons through an M:N relationship to movies, then to genres, then array aggregation and filtering by array size. Most RDBMS lack native array operations.

### 62. Career-spanning persons (active across 5+ decades)

```cypher
MATCH (p:Person)-[:ACTED_IN|DIRECTED]->(m:Movie)
WITH p, collect(DISTINCT (toInteger(m.year) / 10) * 10) AS decades
WHERE size(decades) >= 5
RETURN p.name AS person, size(decades) AS decades_active, decades
ORDER BY decades_active DESC
LIMIT 20
```

### 63. Director effectiveness by genre

```cypher
MATCH (d:Person {name: 'Martin Scorsese'})-[:DIRECTED]->(m:Movie)-[:HAS_GENRE]->(g:Genre)
MATCH (m)-[:HAS_RATING]->(r:Rating)
RETURN g.name AS genre, count(m) AS films, round(avg(r.average_rating) * 10) / 10.0 AS avg_rating
ORDER BY films DESC
LIMIT 15
```

### 64. Cross-decade performance comparison for a specific person

```cypher
MATCH (p:Person {name: 'Robert De Niro'})-[:ACTED_IN]->(m:Movie)-[:HAS_RATING]->(r:Rating)
RETURN (toInteger(m.year) / 10) * 10 AS decade, count(m) AS films,
       round(avg(r.average_rating) * 10) / 10.0 AS avg_rating
ORDER BY decade
```

### 65. Genre pairs that co-occur most often

```cypher
MATCH (m:Movie)-[:HAS_GENRE]->(g1:Genre), (m)-[:HAS_GENRE]->(g2:Genre)
WHERE g1.name < g2.name
WITH g1, g2, count(m) AS movies
WHERE movies >= 200
RETURN g1.name AS genre1, g2.name AS genre2, movies
ORDER BY movies DESC
LIMIT 20
```

### 66. Actors who starred in movies spanning the most distinct directors AND genres

```cypher
MATCH (a:Person)-[:ACTED_IN]->(m:Movie)<-[:DIRECTED]-(d:Person)
MATCH (m)-[:HAS_GENRE]->(g:Genre)
WITH a, count(DISTINCT d) AS directors, count(DISTINCT g) AS genres
WHERE directors >= 10 AND genres >= 5
RETURN a.name AS actor, directors, genres
ORDER BY directors DESC
LIMIT 20
```

### 67. Genre–region affinity via alternate titles

*Ranks all genre-region alternate-title counts; the most-localized region per genre floats up.*

```cypher
MATCH (g:Genre)<-[:HAS_GENRE]-(m)-[:HAS_ALTERNATE_TITLE]->(a:AlternateTitle)
WHERE a.region IS NOT NULL
WITH g, a.region AS region, count(a) AS alt_titles
ORDER BY g.name, alt_titles DESC
RETURN g.name AS genre, region, alt_titles
ORDER BY g.name, alt_titles DESC
LIMIT 30
```

### 68. Director–actor encounter rate (films together vs. total filmography)

```cypher
MATCH (d:Person {name: 'Tim Burton'})-[:DIRECTED]->(m:Movie)
WITH d, count(m) AS director_films
MATCH (a:Person {name: 'Johnny Depp'})-[:ACTED_IN]->(m2:Movie)
WITH d, director_films, a, count(m2) AS actor_films
OPTIONAL MATCH (d)-[:DIRECTED]->(shared:Movie)<-[:ACTED_IN]-(a)
RETURN d.name AS director, director_films, a.name AS actor, actor_films,
       count(shared) AS films_together
```

### 69. Persons who worked across the most distinct title types

```cypher
MATCH (p:Person)-[:ACTED_IN|DIRECTED|WROTE|PRODUCED]->(m)
WITH p, count(DISTINCT labels(m)[0]) AS title_types, count(DISTINCT m) AS credits
RETURN p.name AS person, title_types, credits
ORDER BY credits DESC
LIMIT 20
```

### 70. Impact actors — leads in the most universally beloved films

```cypher
MATCH (a:Person)-[:ACTED_IN]->(m:Movie)-[:HAS_RATING]->(r:Rating)
WHERE r.average_rating >= 8.5 AND r.num_votes >= 50000
RETURN a.name AS actor, count(m) AS beloved_films, collect(m.title)[0..5] AS sample
ORDER BY beloved_films DESC
LIMIT 20
```

### 71. Frequent writer pairs (co-writers on the same movie)

```cypher
MATCH (w1:Person)-[:WROTE]->(m:Movie)<-[:WROTE]-(w2:Person)
WHERE w1.name < w2.name
WITH w1, w2, count(m) AS movies_together
WHERE movies_together >= 3
RETURN w1.name AS writer1, w2.name AS writer2, movies_together
ORDER BY movies_together DESC
LIMIT 20
```

### 72. Decade-dominant director by total audience votes

*Ranks all director-decade vote totals; the most-watched director per decade floats up.*

```cypher
MATCH (d:Person)-[:DIRECTED]->(m:Movie)-[:HAS_RATING]->(r:Rating)
WITH d, (toInteger(m.year) / 10) * 10 AS decade, sum(r.num_votes) AS total_votes
ORDER BY total_votes DESC
RETURN decade, d.name AS top_director, total_votes
ORDER BY decade
LIMIT 20
```

### 73. Person performance across title types (movie vs. series)

```cypher
MATCH (p:Person {name: 'Bryan Cranston'})-[:ACTED_IN]->(m)
WHERE m:Movie OR m:Series
RETURN labels(m)[0] AS title_type, count(m) AS credits
```

### 74. Career longevity — persons still working 40+ years after debut

```cypher
MATCH (p:Person)-[:ACTED_IN|DIRECTED]->(m:Movie)
WITH p, min(m.year) AS debut, max(m.year) AS latest
WHERE latest - debut >= 40
RETURN p.name AS person, debut, latest, latest - debut AS career_span
ORDER BY career_span DESC
LIMIT 20
```

### 75. Most "original" genres (fewest alternate titles per movie)

```cypher
MATCH (g:Genre)<-[:HAS_GENRE]-(m:Movie)
OPTIONAL MATCH (m)-[:HAS_ALTERNATE_TITLE]->(a:AlternateTitle)
WITH g, count(DISTINCT m) AS movies, count(a) AS alt_titles
WHERE movies >= 100
RETURN g.name AS genre, movies, alt_titles, round(alt_titles * 100 / movies) / 100.0 AS alts_per_movie
ORDER BY alts_per_movie ASC
LIMIT 15
```

### 76. Rising directors — later films outrating earlier films

```cypher
MATCH (d:Person)-[:DIRECTED]->(m:Movie)-[:HAS_RATING]->(r:Rating)
WITH d, m, r ORDER BY m.year
WITH d, collect({year: m.year, rating: r.average_rating}) AS films
WHERE size(films) >= 5
WITH d, films, films[0].rating AS first_rating, films[-1].rating AS latest_rating
WHERE latest_rating > first_rating
RETURN d.name AS director, first_rating, latest_rating, latest_rating - first_rating AS improvement
ORDER BY improvement DESC
LIMIT 20
```

### 77. Writing partnerships across genres

```cypher
MATCH (w1:Person)-[:WROTE]->(m:Movie)<-[:WROTE]-(w2:Person)
MATCH (m)-[:HAS_GENRE]->(g:Genre)
WHERE w1.name < w2.name
RETURN w1.name AS writer1, w2.name AS writer2, collect(DISTINCT g.name) AS shared_genres
LIMIT 20
```

### 78. Highest average votes per movie by genre and decade

```cypher
MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre)
MATCH (m)-[:HAS_RATING]->(r:Rating)
WITH g, (toInteger(m.year) / 10) * 10 AS decade, count(m) AS movies, avg(r.num_votes) AS avg_votes
WHERE movies >= 20
RETURN g.name AS genre, decade, movies, round(avg_votes) AS avg_votes
ORDER BY avg_votes DESC
LIMIT 20
```

### 79. Triple-threats — acted, wrote, AND directed in at least 3 movies each

```cypher
MATCH (p:Person)-[:ACTED_IN]->(m1)
WITH p, count(DISTINCT m1) AS acted
WHERE acted >= 3
MATCH (p)-[:DIRECTED]->(m2)
WITH p, acted, count(DISTINCT m2) AS directed
WHERE directed >= 3
MATCH (p)-[:WROTE]->(m3)
WITH p, acted, directed, count(DISTINCT m3) AS wrote
WHERE wrote >= 3
RETURN p.name AS person, acted, directed, wrote
ORDER BY acted + directed + wrote DESC
LIMIT 20
```

### 80. Genre output intensity by decade

```cypher
MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre {name: 'Documentary'})
RETURN (toInteger(m.year) / 10) * 10 AS decade, count(m) AS movies
ORDER BY decade
```

---

## Level 5: Network Intelligence (Impossible in SQL)

*These queries exploit the graph's native connectivity: traversing collaboration networks, computing influence propagation, detecting communities, and finding structural patterns. These patterns are either impossible or catastrophically slow in any relational database.*

### 81. Collaboration chains — director A worked with actor B, who also acted for director C

```cypher
MATCH (a:Person)-[:DIRECTED]->(m1:Movie)<-[:ACTED_IN]-(b:Person)-[:ACTED_IN]->(m2:Movie)<-[:DIRECTED]-(c:Person)
WHERE a <> c
WITH a, b, c, count(*) AS chain_strength
ORDER BY chain_strength DESC
RETURN a.name AS director1, b.name AS bridge_actor, c.name AS director2, chain_strength
LIMIT 25
```

> **Why SQL can't do this**: This is a 3-hop traversal across two different relationship types meeting at a shared actor. SQL requires multiple self-joins on the same table, and the optimizer has no efficient way to plan this without indexes on every join key. A graph engine follows adjacency pointers in O(degree) time.

### 82. Six degrees of separation — shortest co-acting path between two actors

```cypher
MATCH path = (a:Person {name: 'Kevin Bacon'})-[:ACTED_IN*1..6]-(b:Person {name: 'Cate Blanchett'})
RETURN [n IN nodes(path) WHERE n:Person | n.name] AS chain, length(path) AS hops
ORDER BY hops ASC
LIMIT 5
```

> **Why SQL can't do this**: Variable-length path queries require recursive CTEs with cycle detection. Performance degrades exponentially with depth. Graph databases implement this with BFS/DFS natively.

### 83. Co-starring triangles — A, B, and C have all acted together pairwise

```cypher
MATCH (a:Person)-[:ACTED_IN]->(m1:Movie)<-[:ACTED_IN]-(b:Person),
      (b)-[:ACTED_IN]->(m2:Movie)<-[:ACTED_IN]-(c:Person),
      (c)-[:ACTED_IN]->(m3:Movie)<-[:ACTED_IN]-(a)
WHERE a.name < b.name AND b.name < c.name
RETURN DISTINCT a.name AS actor1, b.name AS actor2, c.name AS actor3
LIMIT 25
```

> **Why this matters**: Triangle detection is a fundamental graph operation used in fraud detection and social network analysis. It requires three self-joins in SQL and is O(n^3) without graph-native optimization.

### 84. Influence propagation — who directed the most prolific actors?

```cypher
MATCH (star:Person)-[:ACTED_IN]->(m:Movie)
WITH star, count(m) AS career_credits
ORDER BY career_credits DESC
LIMIT 50
WITH collect(star) AS top_actors
UNWIND top_actors AS star
MATCH (director:Person)-[:DIRECTED]->(:Movie)<-[:ACTED_IN]-(star)
RETURN director.name AS director, count(DISTINCT star) AS stars_directed,
       collect(DISTINCT star.name)[0..5] AS sample_stars
ORDER BY stars_directed DESC
LIMIT 15
```

### 85. Actor connectivity — degree centrality in the co-acting network

```cypher
MATCH (a:Person)-[:ACTED_IN]->(:Movie)<-[:ACTED_IN]-(other:Person)
WITH a, count(DISTINCT other) AS co_stars
RETURN a.name AS actor, co_stars
ORDER BY co_stars DESC
LIMIT 20
```

> **Graph insight**: This is degree centrality — the most fundamental network metric. It identifies the most "connected" actors in the co-acting network.

### 86. Mutual director–actor exchanges — actor directing the director who once directed them

```cypher
MATCH (a:Person)-[:DIRECTED]->(:Movie)<-[:ACTED_IN]-(b:Person),
      (b)-[:DIRECTED]->(:Movie)<-[:ACTED_IN]-(a)
WHERE a.name < b.name
RETURN a.name AS person1, b.name AS person2
LIMIT 20
```

### 87. Genre overlap network — genres sharing the most actors

```cypher
MATCH (g1:Genre)<-[:HAS_GENRE]-(m1:Movie)<-[:ACTED_IN]-(a:Person)-[:ACTED_IN]->(m2:Movie)-[:HAS_GENRE]->(g2:Genre)
WHERE g1.name < g2.name
WITH g1, g2, count(DISTINCT a) AS shared_actors
WHERE shared_actors >= 50
RETURN g1.name AS genre1, g2.name AS genre2, shared_actors
ORDER BY shared_actors DESC
LIMIT 20
```

> **Graph-native**: This is a bipartite projection — projecting the actor-genre bipartite graph into a genre-genre similarity network. Fundamental to recommendation engines.

### 88. Director hunting grounds — which actors do top directors repeatedly cast?

```cypher
MATCH (d:Person)-[:DIRECTED]->(m:Movie)
WITH d, count(m) AS films
ORDER BY films DESC
LIMIT 10
WITH collect(d) AS top_directors
UNWIND top_directors AS director
MATCH (director)-[:DIRECTED]->(m:Movie)<-[:ACTED_IN]-(actor:Person)
WITH director, actor, count(m) AS times
ORDER BY director.name, times DESC
WITH director, collect({actor: actor.name, times: times})[0..5] AS regulars
RETURN director.name AS director, regulars
```

### 89. Cross-category dominance — persons strong across acting, directing, and writing

```cypher
MATCH (p:Person)-[:ACTED_IN]->(m:Movie)-[:HAS_RATING]->(r:Rating)
WITH p, 'ACTED_IN' AS role, count(m) AS credits, avg(r.average_rating) AS avg_rating
WITH p, collect({role: role, credits: credits, avg_rating: avg_rating}) AS roles
WHERE size(roles) >= 1
RETURN p.name AS person, roles
ORDER BY size(roles) DESC
LIMIT 10
```

### 90. Genre–decade affinity network

```cypher
MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre)
WITH g, (toInteger(m.year) / 10) * 10 AS decade, count(m) AS movies
WHERE movies >= 30
RETURN g.name AS genre, decade, movies
ORDER BY movies DESC
LIMIT 30
```

### 91. Cascading collaborations — directors who repeatedly cast the same trio of actors

```cypher
MATCH (d:Person)-[:DIRECTED]->(m:Movie),
      (a1:Person)-[:ACTED_IN]->(m), (a2:Person)-[:ACTED_IN]->(m), (a3:Person)-[:ACTED_IN]->(m)
WHERE a1.name < a2.name AND a2.name < a3.name
WITH d, a1, a2, a3, count(m) AS films_together
WHERE films_together >= 2
RETURN d.name AS director, a1.name AS actor1, a2.name AS actor2, a3.name AS actor3, films_together
ORDER BY films_together DESC
LIMIT 15
```

### 92. Global co-acting network density

```cypher
MATCH (p:Person) WHERE (p)-[:ACTED_IN]->()
WITH count(p) AS actors_in_network
MATCH (:Person)-[r:ACTED_IN]->(:Movie)
WITH actors_in_network, count(r) AS total_credits
RETURN actors_in_network, total_credits,
       round(total_credits * 100 / actors_in_network) / 100.0 AS credits_per_actor
```

### 93. Person career arc — year-by-year output

```cypher
MATCH (p:Person {name: 'Steven Spielberg'})-[:DIRECTED]->(m:Movie)-[:HAS_RATING]->(r:Rating)
RETURN m.year AS year, m.title AS title, r.average_rating AS rating, r.num_votes AS votes
ORDER BY year
```

### 94. Genre ecosystem — actors who appear in both Action and Drama

```cypher
MATCH (a:Person)-[:ACTED_IN]->(m1:Movie)-[:HAS_GENRE]->(g1:Genre {name: 'Action'}),
      (a)-[:ACTED_IN]->(m2:Movie)-[:HAS_GENRE]->(g2:Genre {name: 'Drama'})
WITH DISTINCT a
MATCH (a)-[r:ACTED_IN]->(m:Movie)-[:HAS_GENRE]->(g:Genre)
WHERE g.name IN ['Action', 'Drama']
RETURN a.name AS actor, g.name AS genre, count(m) AS films
ORDER BY a.name, films DESC
LIMIT 30
```

### 95. Movie archetype clustering — runtime vs. rating by genre

```cypher
MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre)
MATCH (m)-[:HAS_RATING]->(r:Rating)
WHERE m.runtime_minutes IS NOT NULL AND r.num_votes >= 5000
WITH g, count(m) AS movies, avg(m.runtime_minutes) AS avg_runtime, avg(r.average_rating) AS avg_rating
WHERE movies >= 50
RETURN g.name AS genre, movies, round(avg_runtime) AS avg_runtime, round(avg_rating * 10) / 10.0 AS avg_rating
ORDER BY avg_rating DESC
```

### 96. Collaboration diversity — directors with the widest variety of actors

```cypher
MATCH (d:Person)-[:DIRECTED]->(:Movie)<-[:ACTED_IN]-(a:Person)
WITH d, count(DISTINCT a) AS unique_actors, count(*) AS total_castings
WHERE total_castings >= 20
RETURN d.name AS director, unique_actors, total_castings,
       round(unique_actors * 10000 / total_castings) / 100.0 AS diversity_pct
ORDER BY unique_actors DESC
LIMIT 20
```

### 97. The "Kevin Bacon number" of cinema — most reachable actor via 2-hop co-acting

```cypher
MATCH (p:Person)-[:ACTED_IN*1..2]-(other:Person)
WHERE p <> other
WITH p, count(DISTINCT other) AS reachable_in_2_hops
RETURN p.name AS actor, reachable_in_2_hops
ORDER BY reachable_in_2_hops DESC
LIMIT 15
```

> **Pure graph**: Finding 2-hop neighborhoods is the basis of influence analysis. SQL would need a recursive CTE with cycle detection and deduplication — minutes vs. milliseconds.

### 98. Genre bridge persons — persons connecting the widest spread of genres

```cypher
MATCH (p:Person)-[:ACTED_IN|DIRECTED|WROTE]->(m:Movie)-[:HAS_GENRE]->(g:Genre)
WITH p, collect(DISTINCT g.name) AS genres
WHERE size(genres) >= 8
RETURN p.name AS person, genres, size(genres) AS genre_count
ORDER BY genre_count DESC
LIMIT 20
```

### 99. Full person profile (7-hop aggregation across entire graph)

```cypher
MATCH (p:Person {name: 'Tom Hanks'})
OPTIONAL MATCH (p)-[:ACTED_IN]->(acted:Movie)-[:HAS_RATING]->(ar:Rating)
OPTIONAL MATCH (p)-[:DIRECTED]->(directed:Movie)
OPTIONAL MATCH (p)-[:WROTE]->(wrote:Movie)
OPTIONAL MATCH (p)-[:PRODUCED]->(produced:Movie)
OPTIONAL MATCH (p)-[:ACTED_IN]->(:Movie)-[:HAS_GENRE]->(genre:Genre)
WITH p,
     count(DISTINCT acted) AS acting_credits, avg(ar.average_rating) AS avg_rating,
     count(DISTINCT directed) AS directing_credits,
     count(DISTINCT wrote) AS writing_credits,
     count(DISTINCT produced) AS producing_credits,
     collect(DISTINCT genre.name) AS genres
RETURN p.name AS person, acting_credits, round(avg_rating * 10) / 10.0 AS avg_rating,
       directing_credits, writing_credits, producing_credits, genres
```

> **Why this is graph-native**: This single query touches 4 different relationship types and aggregates across 3 entity types to produce a comprehensive profile. In SQL, this would be 4+ separate queries or a massive UNION of LEFT JOINs — and the optimizer would likely choose a catastrophic plan.

### 100. The Cinema Universe — full network statistics

```cypher
MATCH (m:Movie) WITH count(m) AS movies
MATCH (s:Series) WITH movies, count(s) AS series
MATCH (p:Person) WITH movies, series, count(p) AS persons
MATCH (g:Genre) WITH movies, series, persons, count(g) AS genres
MATCH (:Movie)-[r:HAS_RATING]->() WITH movies, series, persons, genres, count(r) AS movie_ratings
MATCH (:Person)-[a:ACTED_IN]->() WITH movies, series, persons, genres, movie_ratings, count(a) AS acting_credits
MATCH (:Person)-[d:DIRECTED]->() WITH movies, series, persons, genres, movie_ratings, acting_credits, count(d) AS directing_credits
RETURN movies, series, persons, genres, movie_ratings, acting_credits, directing_credits
```

---

## Where RDBMS Stops and Graphs Take Over

| Capability | RDBMS | Graph DB |
|---|---|---|
| Single-entity aggregation (L1) | Optimal | Equivalent |
| 2-table JOINs (L2) | Good | Equivalent |
| 3+ hop traversals (L3) | Slow (n-way JOINs) | **Native, O(degree)** |
| Self-referencing patterns (L3-4) | Painful self-joins | **First-class edges** |
| Variable-length paths (L4) | Recursive CTEs, exponential | **BFS/DFS, linear** |
| Subgraph pattern matching (L4-5) | Not expressible | **MATCH pattern** |
| Network metrics (L5) | Impossible without app code | **Built-in algorithms** |
| Triangle/cycle detection (L5) | O(n^3) brute force | **Adjacency-optimized** |
| Multi-hop aggregation (L5) | Query plan explosion | **Lazy traversal** |

### The Inflection Point

**Levels 1-2** (Queries 1-35): Both RDBMS and graph databases perform well. Choose either based on your existing stack.

**Level 3** (Queries 36-60): Graph databases start outperforming. Queries are more natural to write and execute faster because each hop follows a pointer instead of scanning a hash table.

**Level 4** (Queries 61-80): RDBMS queries become fragile. Adding one more hop requires restructuring the entire query. Graph queries simply extend the pattern: `(a)-[:REL]->(b)` becomes `(a)-[:REL]->(b)-[:REL]->(c)`.

**Level 5** (Queries 81-100): RDBMS cannot express these queries at all, or they require custom application code with in-memory graph libraries. A graph database handles them as standard queries with millisecond response times.

---

## Graph Schema Reference

```
Movie  ─[HAS_GENRE]──────────────> Genre
Movie  ─[HAS_RATING]─────────────> Rating {average_rating, num_votes}
Movie  ─[HAS_ALTERNATE_TITLE]────> AlternateTitle {title, region, language}
Series ─[HAS_GENRE]──────────────> Genre
Series ─[HAS_RATING]─────────────> Rating
Series ─[HAS_ALTERNATE_TITLE]────> AlternateTitle

Person ─[ACTED_IN {characters}]──> Movie | Series
Person ─[DIRECTED]───────────────> Movie | Series
Person ─[WROTE]──────────────────> Movie | Series
Person ─[PRODUCED]───────────────> Movie | Series
```

**Dataset**: IMDB non-commercial datasets — `title.basics.tsv`, `title.ratings.tsv`, `name.basics.tsv`, `title.principals.tsv`, `title.akas.tsv` ([developer.imdb.com/non-commercial-datasets](https://developer.imdb.com/non-commercial-datasets/)) | Powered by [Samyama Graph Database](https://github.com/samyama-ai/samyama-graph)
