
# ============================================
# CineAnalytics - Phase 3
# Automated Movie Ratings Analysis Report
# ============================================

from pathlib import Path
from datetime import datetime

import pandas as pd


# ============================================
# 1. PROJECT SETUP
# ============================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

OUTPUT_DIR.mkdir(exist_ok=True)

print("=" * 50)
print("                 CINEANALYTICS")
print("           AUTOMATED REPORT GENERATOR")
print("=" * 50)


# ============================================
# 2. CHECK REQUIRED FILES
# ============================================

ratings_path = DATA_DIR / "ratings.csv"
genres_path = OUTPUT_DIR / "genre_statistics.csv"
matched_path = OUTPUT_DIR / "movies_with_genres.csv"

required_files = [
    ratings_path,
    genres_path,
    matched_path
]

missing_files = [
    str(file.name)
    for file in required_files
    if not file.exists()
]

if missing_files:
    raise SystemExit(
        "Missing files: " + ", ".join(missing_files)
        + "\nRun main.py and genre_analysis.py first."
    )

print("\nLoading analysis data...")


# ============================================
# 3. LOAD AND CLEAN RATINGS
# ============================================

ratings = pd.read_csv(ratings_path)

ratings = ratings.dropna(
    subset=["Name", "Year", "Rating"]
).copy()

ratings["Rating"] = pd.to_numeric(
    ratings["Rating"],
    errors="coerce"
)

ratings["Year"] = pd.to_numeric(
    ratings["Year"],
    errors="coerce"
)

ratings["Date"] = pd.to_datetime(
    ratings["Date"],
    errors="coerce"
)

ratings = ratings.dropna(
    subset=["Year", "Rating"]
).copy()

ratings = ratings[
    ratings["Rating"].between(0.5, 5.0)
].copy()

if "Letterboxd URI" in ratings.columns:
    ratings = ratings.drop_duplicates(
        subset=["Letterboxd URI"],
        keep="last"
    )

ratings["Year"] = ratings["Year"].astype(int)

genres = pd.read_csv(genres_path)
matched = pd.read_csv(matched_path)


# ============================================
# 4. BASIC STATISTICS
# ============================================

total_movies = len(ratings)

average_rating = ratings["Rating"].mean()
median_rating = ratings["Rating"].median()

five_star_movies = (
    ratings["Rating"] == 5.0
).sum()

high_ratings = (
    ratings["Rating"] >= 4.0
).sum()

high_rating_percentage = (
    high_ratings / total_movies * 100
    if total_movies else 0
)

rating_distribution = (
    ratings["Rating"]
    .value_counts()
    .sort_index()
)

most_common_rating = rating_distribution.idxmax()

print("\n--- OVERALL STATISTICS ---")

print("Movies rated:", total_movies)
print("Average rating:", round(average_rating, 2))
print("Median rating:", median_rating)
print("Five-star movies:", five_star_movies)
print("Most common rating:", most_common_rating)
print(
    "Movies rated 4+ stars:",
    high_ratings
)


# ============================================
# 5. RELEASE DECADE ANALYSIS
# ============================================

ratings["Decade"] = (
    ratings["Year"] // 10
) * 10

decade_stats = (
    ratings.groupby("Decade")
    .agg(
        Movie_Count=("Rating", "count"),
        Average_Rating=("Rating", "mean")
    )
    .reset_index()
)

most_common_decade = decade_stats.loc[
    decade_stats["Movie_Count"].idxmax()
]

most_common_decade_name = (
    f"{int(most_common_decade['Decade'])}s"
)

most_common_decade_count = int(
    most_common_decade["Movie_Count"]
)

print("\n--- DECADE ANALYSIS ---")
print(decade_stats.to_string(index=False))


# ============================================
# 6. GENRE ANALYSIS
# ============================================

genres["Movie_Count"] = pd.to_numeric(
    genres["Movie_Count"],
    errors="coerce"
)

genres["Average_Rating"] = pd.to_numeric(
    genres["Average_Rating"],
    errors="coerce"
)

genres = genres.dropna(
    subset=["Genre", "Movie_Count", "Average_Rating"]
).copy()

genres = genres.sort_values(
    by="Movie_Count",
    ascending=False
)

most_common_genre = genres.iloc[0]

# Use at least 10 movies for average ranking
qualified_genres = genres[
    genres["Movie_Count"] >= 10
].copy()

qualified_genres = qualified_genres.sort_values(
    by="Average_Rating",
    ascending=False
)

top_genre = qualified_genres.iloc[0]

matched_count = int(
    (matched["Match_Status"] == "Matched").sum()
)

unmatched_count = len(matched) - matched_count

match_percentage = (
    matched_count / len(matched) * 100
    if len(matched) else 0
)

print("\n--- GENRE ANALYSIS ---")
print("Most frequent genre:", most_common_genre["Genre"])
print("Highest average genre:", top_genre["Genre"])
print("Movies matched:", matched_count)
print("Unmatched movies:", unmatched_count)


# ============================================
# 7. MONTHLY RATING ACTIVITY
# ============================================

dated_ratings = ratings.dropna(
    subset=["Date"]
).copy()

dated_ratings["Month"] = (
    dated_ratings["Date"].dt.to_period("M")
)

monthly_activity = (
    dated_ratings.groupby("Month")
    .size()
    .sort_index()
)

if not monthly_activity.empty:
    peak_month = str(monthly_activity.idxmax())
    peak_month_count = int(monthly_activity.max())
else:
    peak_month = "Not available"
    peak_month_count = 0


# ============================================
# 8. GENERATE MARKDOWN TABLES
# ============================================

rating_table = (
    "| Star Rating | Movies |\n"
    "|---|---:|\n"
)

for rating, count in rating_distribution.items():
    rating_table += (
        f"| {rating:.1f} | {count} |\n"
    )

decade_table = (
    "| Release Decade | Movies | Average Rating |\n"
    "|---|---:|---:|\n"
)

for _, row in decade_stats.iterrows():
    decade_table += (
        f"| {int(row['Decade'])}s "
        f"| {int(row['Movie_Count'])} "
        f"| {row['Average_Rating']:.2f} |\n"
    )

genre_table = (
    "| Genre | Rated Movies | Average Rating |\n"
    "|---|---:|---:|\n"
)

for _, row in genres.iterrows():
    genre_table += (
        f"| {row['Genre']} "
        f"| {int(row['Movie_Count'])} "
        f"| {row['Average_Rating']:.2f} |\n"
    )


# ============================================
# 9. GENERATE KEY FINDINGS
# ============================================

findings = [
    (
        f"The dataset contains {total_movies} movie ratings, "
        f"with an overall average of {average_rating:.2f}/5."
    ),
    (
        f"The most frequently awarded rating is "
        f"{most_common_rating:.1f} stars."
    ),
    (
        f"{high_ratings} movies ({high_rating_percentage:.1f}%) "
        f"received ratings of at least 4 stars."
    ),
    (
        f"The {most_common_decade_name} is the most represented "
        f"release decade, with {most_common_decade_count} movies."
    ),
    (
        f"{most_common_genre['Genre']} is the most frequently "
        f"rated genre, appearing in "
        f"{int(most_common_genre['Movie_Count'])} matched movies."
    ),
    (
        f"{top_genre['Genre']} has the highest average rating "
        f"among genres with at least 10 movies, "
        f"at {top_genre['Average_Rating']:.2f}/5."
    )
]

findings_text = "\n".join(
    f"{i}. {finding}"
    for i, finding in enumerate(findings, start=1)
)


# ============================================
# 10. GENERATE FULL REPORT
# ============================================

report_date = datetime.now().strftime("%B %d, %Y")

report = f"""# CineAnalytics
## Personal Movie Ratings & Data Analysis Report

**Generated:** {report_date}

**Tools:** Python, Pandas, SQLite, Matplotlib, TMDB API

---

## 1. Executive Summary

CineAnalytics is a data analytics project that explores
personal movie ratings exported from Letterboxd.

The analysis examines rating distributions, release
decades, genre preferences, and rating activity.

The dataset contains **{total_movies} rated movies**,
with an overall average rating of **{average_rating:.2f}/5**.

Genre information was retrieved from TMDB for
**{matched_count} movies**, representing
**{match_percentage:.1f}%** of the rated collection.

---

## 2. Overall Rating Statistics

| Metric | Value |
|---|---:|
| Movies Rated | {total_movies} |
| Average Rating | {average_rating:.2f}/5 |
| Median Rating | {median_rating:.1f}/5 |
| Five-Star Movies | {five_star_movies} |
| Most Common Rating | {most_common_rating:.1f}/5 |
| Movies Rated 4+ Stars | {high_ratings} |
| Percentage Rated 4+ Stars | {high_rating_percentage:.1f}% |

### Rating Distribution

{rating_table}

![Rating Distribution](rating_distribution.png)

---

## 3. Release Decade Analysis

The most represented decade is the
**{most_common_decade_name}**, with
**{most_common_decade_count} rated movies**.

{decade_table}

![Movies by Decade](movies_by_decade.png)

![Average Rating by Decade](average_rating_by_decade.png)

---

## 4. Genre Analysis

TMDB metadata was matched to
**{matched_count} of {total_movies} movies**.

**Most frequently rated genre:**
{most_common_genre['Genre']}

**Highest-rated qualifying genre:**
{top_genre['Genre']}
({top_genre['Average_Rating']:.2f}/5)

Only genres containing at least 10 movies
were considered when identifying the
highest-rated genre.

### Genre Statistics

{genre_table}

![Most Frequently Rated Genres](most_rated_genres.png)

![Highest Rated Genres](highest_rated_genres.png)

---

## 5. Monthly Rating Activity

The month with the most recorded ratings was
**{peak_month}**, with **{peak_month_count} ratings**.

![Monthly Rating Activity](monthly_activity.png)

These values represent the dates ratings were
recorded on Letterboxd. They do not necessarily
represent when the movies were watched.

---

## 6. Key Findings

{findings_text}

---

## 7. Methodology

1. Exported movie ratings from Letterboxd.
2. Loaded and cleaned the data using Pandas.
3. Calculated rating statistics and release decade trends.
4. Retrieved additional movie metadata using the TMDB API.
5. Matched movies using title and release year.
6. Analyzed movie genres using Pandas and SQLite.
7. Generated visualizations using Matplotlib.
8. Combined the findings into this automated report.

---

## 8. Limitations

- The dataset represents one person's ratings,
  not the opinions of the wider movie audience.
- {unmatched_count} movies could not be reliably
  matched to TMDB and were excluded from genre analysis.
- Genre statistics count movies in each applicable genre,
  so movies with multiple genres appear more than once.
- TMDB matches are automated and may contain occasional
  metadata errors.
- Some genres and decades have small sample sizes,
  making their average ratings less representative.
- Letterboxd rating dates are not necessarily watch dates.
- This is a descriptive analysis and does not establish
  causal relationships.

---

## 9. Conclusion

CineAnalytics demonstrates a basic end-to-end
data analytics workflow using Python, Pandas,
SQL, API integration, and data visualization.

The project highlights how personal rating data
can be processed, summarized, and presented
through reproducible analytical methods.

---

**Dataset:** Personal Letterboxd ratings export

**Movie metadata:** TMDB API

**Project:** CineAnalytics
"""


# ============================================
# 11. SAVE REPORT
# ============================================

report_path = OUTPUT_DIR / "cineanalytics_report.md"

report_path.write_text(
    report,
    encoding="utf-8"
)

print("\n" + "=" * 50)
print("       REPORT GENERATED SUCCESSFULLY!")
print("=" * 50)

print("\nReport:", report_path)
print("Movies analyzed:", total_movies)
print("Genre matches:", matched_count)
print("Matching rate:", f"{match_percentage:.1f}%")
print("Key findings generated:", len(findings))

print("\nOpen cineanalytics_report.md to view your report.")
print("\nCineAnalytics Phase 3 complete!")
