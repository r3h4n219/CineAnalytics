
# ============================================
# CineAnalytics
# Personal Movie Ratings & Data Analysis
# ============================================

from pathlib import Path
import sqlite3

import pandas as pd
import matplotlib.pyplot as plt


# ============================================
# 1. SET UP FILE PATHS
# ============================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

OUTPUT_DIR.mkdir(exist_ok=True)

print("=" * 45)
print("         CINEANALYTICS")
print("     Personal Movie Ratings Analysis")
print("=" * 45)


# ============================================
# 2. LOAD YOUR LETTERBOXD RATINGS
# ============================================

file_path = DATA_DIR / "ratings.csv"

movies = pd.read_csv(file_path)

print("\nDataset loaded successfully!")
print("Total records:", len(movies))
print("\nDataset columns:")
print(movies.columns.tolist())


# ============================================
# 3. CLEAN THE DATA
# ============================================

# Remove duplicate records
movies = movies.drop_duplicates()

# Remove rows with missing important values
movies = movies.dropna(
    subset=["Name", "Year", "Rating"]
).copy()

# Convert values to the correct data types
movies["Rating"] = pd.to_numeric(
    movies["Rating"], errors="coerce"
)

movies["Year"] = pd.to_numeric(
    movies["Year"], errors="coerce"
)

movies["Date"] = pd.to_datetime(
    movies["Date"], errors="coerce"
)

# Keep ratings between 0.5 and 5 stars
movies = movies[
    movies["Rating"].between(0.5, 5)
]

# Remove invalid release years
movies = movies.dropna(
    subset=["Year"]
).copy()

movies["Year"] = movies["Year"].astype(int)

# Remove repeated movie entries, if any
movies = movies.drop_duplicates(
    subset=["Letterboxd URI"],
    keep="last"
)

print("\nData cleaning completed!")
print("Clean records:", len(movies))


# ============================================
# 4. BASIC MOVIE STATISTICS
# ============================================

total_movies = len(movies)
average_rating = movies["Rating"].mean()
median_rating = movies["Rating"].median()

five_star_movies = len(
    movies[movies["Rating"] == 5]
)

print("\n--- BASIC STATISTICS ---")
print("Total movies rated:", total_movies)
print("Average rating:", round(average_rating, 2))
print("Median rating:", median_rating)
print("5-star movies:", five_star_movies)


# ============================================
# 5. HIGHEST-RATED MOVIES
# ============================================

top_movies = movies.sort_values(
    by=["Rating", "Name"],
    ascending=[False, True]
).head(15)

print("\n--- TOP 15 HIGHEST-RATED MOVIES ---")

print(
    top_movies[
        ["Name", "Year", "Rating"]
    ].to_string(index=False)
)

top_movies[
    ["Name", "Year", "Rating"]
].to_csv(
    OUTPUT_DIR / "top_movies.csv",
    index=False
)


# ============================================
# 6. RATING DISTRIBUTION
# ============================================

rating_counts = (
    movies["Rating"]
    .value_counts()
    .reindex(
        [0.5, 1, 1.5, 2, 2.5,
         3, 3.5, 4, 4.5, 5],
        fill_value=0
    )
    .sort_index()
)

print("\n--- RATING DISTRIBUTION ---")
print(rating_counts)

rating_counts.rename_axis(
    "Rating"
).reset_index(
    name="Count"
).to_csv(
    OUTPUT_DIR / "rating_distribution.csv",
    index=False
)


# ============================================
# 7. MOVIES BY RELEASE DECADE
# ============================================

movies["Decade"] = (
    movies["Year"] // 10
) * 10

decade_counts = (
    movies.groupby("Decade")
    .size()
    .sort_index()
)

decade_averages = (
    movies.groupby("Decade")["Rating"]
    .mean()
    .round(2)
)

print("\n--- MOVIES BY DECADE ---")
print(decade_counts)

print("\n--- AVERAGE RATING BY DECADE ---")
print(decade_averages)

decade_summary = pd.DataFrame({
    "Movie Count": decade_counts,
    "Average Rating": decade_averages
})

decade_summary.to_csv(
    OUTPUT_DIR / "decade_analysis.csv"
)


# ============================================
# 8. RATING ACTIVITY BY MONTH
# ============================================

# Letterboxd Date is the date the rating
# was recorded, not necessarily watched.

dated_movies = movies.dropna(
    subset=["Date"]
).copy()

dated_movies["Month"] = (
    dated_movies["Date"].dt.to_period("M")
)

monthly_activity = (
    dated_movies.groupby("Month")
    .size()
    .sort_index()
)

print("\n--- MONTHLY RATING ACTIVITY ---")
print(monthly_activity)

monthly_activity.rename_axis(
    "Month"
).reset_index(
    name="Ratings Recorded"
).assign(
    Month=lambda df: df["Month"].astype(str)
).to_csv(
    OUTPUT_DIR / "monthly_activity.csv",
    index=False
)


# ============================================
# 9. SQL ANALYSIS
# ============================================

# Create an SQLite database file
database_path = BASE_DIR / "cineanalytics.db"

connection = sqlite3.connect(database_path)

# Store cleaned movie data in SQL
movies.to_sql(
    "ratings",
    connection,
    if_exists="replace",
    index=False
)

print("\n--- SQL ANALYSIS ---")

# Query 1: Find average movie rating
query1 = """
SELECT ROUND(AVG(Rating), 2) AS AverageRating
FROM ratings;
"""

sql_average = pd.read_sql_query(
    query1, connection
)

print("\nAverage rating using SQL:")
print(sql_average.to_string(index=False))


# Query 2: Count movies by rating
query2 = """
SELECT
    Rating,
    COUNT(*) AS TotalMovies
FROM ratings
GROUP BY Rating
ORDER BY Rating DESC;
"""

sql_distribution = pd.read_sql_query(
    query2, connection
)

print("\nMovie ratings using SQL:")
print(sql_distribution.to_string(index=False))


# Query 3: Best average rating by decade
query3 = """
SELECT
    Decade,
    COUNT(*) AS TotalMovies,
    ROUND(AVG(Rating), 2) AS AverageRating
FROM ratings
GROUP BY Decade
ORDER BY AverageRating DESC;
"""

sql_decades = pd.read_sql_query(
    query3, connection
)

print("\nDecade analysis using SQL:")
print(sql_decades.to_string(index=False))

sql_decades.to_csv(
    OUTPUT_DIR / "sql_decade_analysis.csv",
    index=False
)

connection.close()


# ============================================
# 10. GRAPH 1: RATING DISTRIBUTION
# ============================================

plt.figure(figsize=(10, 6))

plt.bar(
    rating_counts.index.astype(str),
    rating_counts.values,
    color="steelblue"
)

plt.title("CineAnalytics: Rating Distribution")
plt.xlabel("Star Rating")
plt.ylabel("Number of Movies")
plt.grid(axis="y", alpha=0.3)
plt.tight_layout()

plt.savefig(
    OUTPUT_DIR / "rating_distribution.png",
    dpi=150
)

plt.close()


# ============================================
# 11. GRAPH 2: MOVIES BY DECADE
# ============================================

plt.figure(figsize=(10, 6))

plt.bar(
    decade_counts.index.astype(str),
    decade_counts.values,
    color="mediumseagreen"
)

plt.title("CineAnalytics: Movies by Decade")
plt.xlabel("Release Decade")
plt.ylabel("Number of Rated Movies")
plt.grid(axis="y", alpha=0.3)
plt.tight_layout()

plt.savefig(
    OUTPUT_DIR / "movies_by_decade.png",
    dpi=150
)

plt.close()


# ============================================
# 12. GRAPH 3: MONTHLY RATING ACTIVITY
# ============================================

plt.figure(figsize=(12, 6))

plt.plot(
    monthly_activity.index.astype(str),
    monthly_activity.values,
    marker="o",
    color="darkorange"
)

plt.title("CineAnalytics: Monthly Rating Activity")
plt.xlabel("Month")
plt.ylabel("Ratings Recorded")
plt.xticks(rotation=45, ha="right")
plt.grid(alpha=0.3)
plt.tight_layout()

plt.savefig(
    OUTPUT_DIR / "monthly_activity.png",
    dpi=150
)

plt.close()


# ============================================
# 13. GRAPH 4: AVERAGE RATING BY DECADE
# ============================================

plt.figure(figsize=(10, 6))

plt.bar(
    decade_averages.index.astype(str),
    decade_averages.values,
    color="mediumpurple"
)

plt.title("CineAnalytics: Average Rating by Decade")
plt.xlabel("Release Decade")
plt.ylabel("Average Rating")
plt.ylim(0, 5)
plt.grid(axis="y", alpha=0.3)
plt.tight_layout()

plt.savefig(
    OUTPUT_DIR / "average_rating_by_decade.png",
    dpi=150
)

plt.close()


# ============================================
# 14. FINAL SUMMARY
# ============================================

print("\n" + "=" * 45)
print("       ANALYSIS COMPLETED!")
print("=" * 45)

print("Movies analyzed:", total_movies)
print("Average rating:", round(average_rating, 2))
print("5-star movies:", five_star_movies)

print("\nGenerated 4 charts.")
print("CSV reports saved in the output folder.")
print("SQLite database: cineanalytics.db")

print("\nThank you for using CineAnalytics!")
