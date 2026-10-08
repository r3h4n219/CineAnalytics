
# ============================================
# CineAnalytics - Phase 2
# Movie Genre Analysis using TMDB
# ============================================

from pathlib import Path
import os
import sqlite3
import time
import re
import unicodedata

import pandas as pd
import matplotlib.pyplot as plt
import requests
from dotenv import load_dotenv


# ============================================
# 1. PROJECT SETUP
# ============================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

OUTPUT_DIR.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env")

TMDB_TOKEN = os.getenv("TMDB_TOKEN")

if not TMDB_TOKEN:
    raise SystemExit(
        "TMDB_TOKEN not found. Check your .env file."
    )

HEADERS = {
    "Authorization": f"Bearer {TMDB_TOKEN}",
    "accept": "application/json"
}

API_URL = "https://api.themoviedb.org/3"

session = requests.Session()
session.headers.update(HEADERS)

print("=" * 45)
print("          CINEANALYTICS")
print("       MOVIE GENRE ANALYSIS")
print("=" * 45)


# ============================================
# 2. HELPER FUNCTION FOR TMDB REQUESTS
# ============================================

def tmdb_get(endpoint, params=None):
    """Send a request to TMDB with basic error handling."""

    url = API_URL + endpoint

    for attempt in range(3):
        try:
            response = session.get(
                url,
                params=params,
                timeout=20
            )

            if response.status_code == 429:
                print("Rate limit reached. Waiting...")
                time.sleep(5)
                continue

            response.raise_for_status()
            return response.json()

        except requests.RequestException as error:
            print("TMDB request issue:", error)

            if attempt < 2:
                time.sleep(2)

    return None


# ============================================
# 3. LOAD LETTERBOXD RATINGS
# ============================================

movies = pd.read_csv(DATA_DIR / "ratings.csv")

required = ["Name", "Year", "Rating"]

if not all(col in movies.columns for col in required):
    raise SystemExit(
        "ratings.csv is missing required columns."
    )

movies = movies.dropna(subset=required).copy()

movies["Year"] = pd.to_numeric(
    movies["Year"], errors="coerce"
)

movies["Rating"] = pd.to_numeric(
    movies["Rating"], errors="coerce"
)

movies = movies.dropna(
    subset=["Year", "Rating"]
)

movies = movies[
    movies["Rating"].between(0.5, 5.0)
].copy()

movies["Year"] = movies["Year"].astype(int)

# Keep one rating per movie
if "Letterboxd URI" in movies.columns:
    movies = movies.drop_duplicates(
        subset=["Letterboxd URI"],
        keep="last"
    )

print("\nRatings loaded:", len(movies))


# ============================================
# 4. LOAD PREVIOUSLY MATCHED MOVIES
# ============================================

# Save metadata locally to avoid repeated API calls.
cache_path = DATA_DIR / "movie_genres_cache.csv"

if cache_path.exists():
    cache = pd.read_csv(cache_path)
else:
    cache = pd.DataFrame(
        columns=[
            "Name", "Year", "TMDB_ID", "Genres",
            "Match_Status"
        ]
    )

cache["Year"] = pd.to_numeric(
    cache["Year"], errors="coerce"
)

cached_records = {}

for _, row in cache.iterrows():
    key = (str(row["Name"]), row["Year"])

    if pd.notna(row["Year"]):
        cached_records[key] = row.to_dict()


# ============================================
# 5. GET GENRE NAMES FROM TMDB
# ============================================

genre_response = tmdb_get(
    "/genre/movie/list",
    {"language": "en-US"}
)

if not genre_response:
    raise SystemExit(
        "Could not connect to TMDB. Check your token."
    )

genre_map = {
    genre["id"]: genre["name"]
    for genre in genre_response["genres"]
}

print("TMDB connection successful!")


# ============================================
# 6. FIND MOVIES ON TMDB
# ============================================

def normalize_title(title):
    """
    Make movie titles easier to compare.

    Examples:
    Mission: Impossible – Fallout
    Mission Impossible - Fallout

    Both become:
    mission impossible fallout
    """

    title = unicodedata.normalize("NFKD", str(title))

    title = "".join(
        char for char in title
        if not unicodedata.combining(char)
    )

    title = re.sub(r"[^\w\s]", " ", title)

    title = " ".join(title.lower().split())

    return title



def find_movie(title, year):
    """Find a movie by normalized title and release year."""

    response = tmdb_get(
        "/search/movie",
        {
            "query": title,
            "include_adult": "false"
        }
    )

    if response is None:
        return {
            "Name": title,
            "Year": year,
            "TMDB_ID": None,
            "Genres": "",
            "Match_Status": "Request Failed"
        }

    candidates = []

    normalized_search = normalize_title(title)

    for result in response.get("results", []):
        tmdb_year = str(
            result.get("release_date", "")
        )[:4]

        possible_titles = [
            result.get("title", ""),
            result.get("original_title", "")
        ]

        title_matches = any(
            normalize_title(candidate) == normalized_search
            for candidate in possible_titles
        )

        # Only accept movies from the same year.
        year_matches = tmdb_year == str(year)

        if title_matches and year_matches:
            candidates.append(result)

    if len(candidates) == 1:
        match = candidates[0]

        genres = [
            genre_map[genre_id]
            for genre_id in match.get("genre_ids", [])
            if genre_id in genre_map
        ]

        return {
            "Name": title,
            "Year": year,
            "TMDB_ID": match["id"],
            "Genres": "|".join(genres),
            "Match_Status": "Matched"
        }

    return {
        "Name": title,
        "Year": year,
        "TMDB_ID": None,
        "Genres": "",
        "Match_Status": (
            "Ambiguous" if candidates else "Not Found"
        )
    }



# ============================================
# 7. COLLECT MOVIE GENRES
# ============================================

print("\nFinding movie genres...")

new_records = 0
results = []

for index, row in movies.iterrows():
    title = str(row["Name"])
    year = int(row["Year"])
    key = (title, year)

    if key in cached_records:
        result = cached_records[key]
    else:
        result = find_movie(title, year)

        # Save successful matches to the cache.
        if result["Match_Status"] == "Matched":
            cached_records[key] = result
            new_records += 1

        time.sleep(0.25)

    results.append(result)

    if len(results) % 25 == 0:
        print(
            f"Processed {len(results)} / {len(movies)}"
        )

# Save the cache
pd.DataFrame(
    list(cached_records.values())
).to_csv(cache_path, index=False)

metadata = pd.DataFrame(results)

combined = movies.merge(
    metadata,
    on=["Name", "Year"],
    how="left"
)

combined.to_csv(
    OUTPUT_DIR / "movies_with_genres.csv",
    index=False
)

unmatched = combined[
    combined["Match_Status"] != "Matched"
]

unmatched.to_csv(
    OUTPUT_DIR / "unmatched_movies.csv",
    index=False
)

print("\nNew matches retrieved:", new_records)
print("Movies successfully matched:",
      len(combined) - len(unmatched))
print("Unmatched movies:", len(unmatched))


# ============================================
# 8. PREPARE GENRE ANALYSIS
# ============================================

genre_data = combined[
    (combined["Match_Status"] == "Matched") &
    (combined["Genres"].notna()) &
    (combined["Genres"] != "")
].copy()

if genre_data.empty:
    raise SystemExit(
        "No usable genres found. Check unmatched_movies.csv."
    )

# A movie can belong to multiple genres.
genre_data["Genre"] = genre_data["Genres"].str.split("|")

genre_data = genre_data.explode("Genre")

genre_stats = (
    genre_data.groupby("Genre")
    .agg(
        Movie_Count=("Rating", "count"),
        Average_Rating=("Rating", "mean")
    )
    .reset_index()
)

genre_stats["Average_Rating"] = (
    genre_stats["Average_Rating"].round(2)
)

genre_stats = genre_stats.sort_values(
    by="Movie_Count",
    ascending=False
)

print("\n--- GENRE STATISTICS ---")
print(genre_stats.to_string(index=False))

genre_stats.to_csv(
    OUTPUT_DIR / "genre_statistics.csv",
    index=False
)


# ============================================
# 9. SQL GENRE ANALYSIS
# ============================================

connection = sqlite3.connect(
    BASE_DIR / "cineanalytics.db"
)

genre_data.to_sql(
    "movie_genres",
    connection,
    if_exists="replace",
    index=False
)

query = """
SELECT
    Genre,
    COUNT(*) AS MovieCount,
    ROUND(AVG(Rating), 2) AS AverageRating
FROM movie_genres
GROUP BY Genre
ORDER BY MovieCount DESC;
"""

sql_result = pd.read_sql_query(
    query, connection
)

print("\n--- SQL GENRE ANALYSIS ---")
print(sql_result.to_string(index=False))

sql_result.to_csv(
    OUTPUT_DIR / "sql_genre_analysis.csv",
    index=False
)

connection.close()


# ============================================
# 10. GRAPH 1 - MOST WATCHED GENRES
# ============================================

top_genres = genre_stats.head(10)

plt.figure(figsize=(11, 6))

plt.barh(
    top_genres["Genre"],
    top_genres["Movie_Count"],
    color="steelblue"
)

plt.title("CineAnalytics: Most Frequently Rated Genres")
plt.xlabel("Number of Rated Movies")
plt.ylabel("Genre")

plt.gca().invert_yaxis()
plt.tight_layout()

plt.savefig(
    OUTPUT_DIR / "most_rated_genres.png",
    dpi=150
)

plt.close()


# ============================================
# 11. GRAPH 2 - HIGHEST-RATED GENRES
# ============================================

# Only include genres with at least 10 movies.
reliable_genres = genre_stats[
    genre_stats["Movie_Count"] >= 10
]

top_average = reliable_genres.sort_values(
    by="Average_Rating",
    ascending=False
).head(10)

if not top_average.empty:
    plt.figure(figsize=(11, 6))

    plt.barh(
        top_average["Genre"],
        top_average["Average_Rating"],
        color="mediumseagreen"
    )

    plt.title(
        "CineAnalytics: Highest-Rated Genres (10+ Movies)"
    )
    plt.xlabel("Average Personal Rating")
    plt.xlim(0, 5)

    plt.gca().invert_yaxis()
    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR / "highest_rated_genres.png",
        dpi=150
    )

    plt.close()


# ============================================
# 12. FINAL REPORT
# ============================================

print("\n" + "=" * 45)
print("       GENRE ANALYSIS COMPLETE!")
print("=" * 45)

print("Total movies:", len(movies))
print("Matched movies:", len(combined) - len(unmatched))
print("Unmatched movies:", len(unmatched))

print("\nResults saved to the output folder.")
print("Movie metadata cached for future runs.")
print("\nCineAnalytics Phase 2 complete!")
