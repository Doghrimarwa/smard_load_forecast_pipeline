"""Convert the SMARD forecast CSV files into JSON (same data, different format).

Run from the project folder:
    python explore/csv_to_json.py
"""

from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
CSV_DIR = PROJECT_DIR / "data" / "raw" / "csv"
JSON_DIR = PROJECT_DIR / "data" / "raw" / "json"
JSON_DIR.mkdir(parents=True, exist_ok=True)

for csv_path in sorted(CSV_DIR.glob("Forecasted_consumption_*.csv")):
    # Read the CSV exactly like in explore_csv.py
    df = pd.read_csv(csv_path, sep=";", encoding="utf-8-sig", thousands=",", na_values="-")

    # Text dates -> real dates in German time, then -> ISO text (e.g. 2026-09-01T00:00:00+02:00)
    for col in ["Start date", "End date"]:
        dates = pd.to_datetime(df[col], format="%b %d, %Y %I:%M %p")
        df[col] = dates.dt.tz_localize("Europe/Berlin", ambiguous="infer").map(lambda t: t.isoformat())

    # One JSON object per row; empty values become null
    json_path = JSON_DIR / (csv_path.stem + ".json")
    df.to_json(json_path, orient="records", indent=2, force_ascii=False)
    print(f"{csv_path.name} -> {json_path.name}: {len(df)} rows")
   # should be 0    