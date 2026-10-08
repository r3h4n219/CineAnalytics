
# ============================================
# CineAnalytics - Complete Update Pipeline
# ============================================

import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

scripts = [
    "main.py",
    "genre_analysis.py",
    "report_generator.py"
]

print("=" * 45)
print("       CINEANALYTICS UPDATE")
print("=" * 45)

for script in scripts:
    print(f"\nRunning {script}...", flush=True)

    result = subprocess.run(
        [sys.executable, str(BASE_DIR / script)],
        cwd=BASE_DIR
    )

    if result.returncode != 0:
        print(f"\nError: {script} failed.")
        print("Update stopped.")
        sys.exit(result.returncode)

print("\n" + "=" * 45)
print("    ALL ANALYSES COMPLETED!")
print("=" * 45)

print("\nYour charts and report are updated.")
