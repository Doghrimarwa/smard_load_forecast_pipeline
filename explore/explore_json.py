"""Download SMARD consumption data through the API and save it as JSON,
with the same columns as the SMARD CSV files.

Creates two files in data/raw/json/:
    Actual_consumption_<start>_<end>_Quarterhour.json
    Forecasted_consumption_<start>_<end>_Quarterhour.json

Run from the project folder:
    python explore/extract_json.py
"""
import json
from pathlib import Path

import pandas as pd
import requests

# --- Where to save -------------------------------------------------------------
PROJECT_DIR = Path(__file__).resolve().parent.parent
JSON_DIR = PROJECT_DIR / "data" / "raw" / "json"

# --- What to download -----------------------------------------------------------
BASE_URL = "https://www.smard.de/app/chart_data"
REGION = "50Hertz"
RESOLUTION = "quarterhour"
START = pd.Timestamp("2026-09-01", tz="Europe/Berlin")   # first day
END = pd.Timestamp("2026-10-01", tz="Europe/Berlin")     # day AFTER the last day

# The two forecast filter IDs are not documented anywhere. Find them on smard.de
# (F12 -> Network, see the explanation) and replace None with the numbers.
FORECAST_GRID_LOAD_ID = None
FORECAST_RESIDUAL_LOAD_ID = None

# For each file: which SMARD filter gives which CSV column.
# "sum" = this column has no filter; it is grid load + pumped storage.
DATASETS = {
    "Actual_consumption": {
        "grid load [MWh] Original resolutions": 410,
        "Grid load incl. hydro pumped storage [MWh] Original resolutions": "sum",
        "Hydro pumped storage [MWh] Original resolutions": 4387,
        "Residual load [MWh] Original resolutions": 4359,
    },
    "Forecasted_consumption": {
        "grid load [MWh] Original resolutions": FORECAST_GRID_LOAD_ID,
        "Residual load [MWh] Original resolutions": FORECAST_RESIDUAL_LOAD_ID,
    },
}


def get_json(url):
    """Ask SMARD for one address and return the answer as Python data."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()          # stop with an error if the answer is not OK
    return response.json()


def download_column(filter_id, column_name):
    """Download one series and return it as one column, indexed by German time."""
    # 1. The index: start time of every weekly block (milliseconds, UTC)
    index = get_json(f"{BASE_URL}/{filter_id}/{REGION}/index_{RESOLUTION}.json")
    timestamps = index["timestamps"]

    # 2. Keep the blocks that overlap our period (a block covers one week)
    first_ms = (START - pd.Timedelta(days=7)).timestamp() * 1000
    end_ms = END.timestamp() * 1000
    blocks = [t for t in timestamps if first_ms < t < end_ms]

    # 3. Download each block and collect all [time, value] pairs
    pairs = []
    for t in blocks:
        block = get_json(f"{BASE_URL}/{filter_id}/{REGION}/{filter_id}_{REGION}_{RESOLUTION}_{t}.json")
        pairs.extend(block["series"])

    # 4. Pairs -> table; milliseconds -> German local time
    df = pd.DataFrame(pairs, columns=["time_ms", "value"])
    df["start"] = pd.to_datetime(df["time_ms"], unit="ms", utc=True).dt.tz_convert("Europe/Berlin")

    # 5. Keep only our period
    df = df[(df["start"] >= START) & (df["start"] < END)]

    # 6. Two neighbouring blocks can contain the same quarter hour: keep the one with a value
    df = df.sort_values(["start", "value"], na_position="first").drop_duplicates("start", keep="last")

    print(f"  {column_name}: filter {filter_id}, {len(blocks)} blocks, {len(df)} quarter hours")
    return df.set_index("start")["value"].rename(column_name)


def build_table(columns):
    """Download every column of one file and put them side by side, like the CSV."""
    table = pd.concat(
        [download_column(fid, name) for name, fid in columns.items() if fid != "sum"],
        axis=1,
    )

    # The calculated column: grid load + pumped storage
    for name, fid in columns.items():
        if fid == "sum":
            table[name] = (table["grid load [MWh] Original resolutions"]
                           + table["Hydro pumped storage [MWh] Original resolutions"]).round(2)

    # Start date and End date, like the CSV
    table["Start date"] = table.index
    table["End date"] = table.index + pd.Timedelta(minutes=15)

    # Same column order as the CSV
    return table[["Start date", "End date", *columns.keys()]]


def save_as_json(table, path):
    """Save the table as a JSON list: one object per row, same keys as the CSV columns."""
    table = table.copy()
    table["Start date"] = table["Start date"].map(lambda t: t.isoformat())   # dates -> text
    table["End date"] = table["End date"].map(lambda t: t.isoformat())
    table = table.astype(object).where(table.notna(), None)                  # empty -> null

    rows = table.to_dict(orient="records")
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


if __name__ == "__main__":
    JSON_DIR.mkdir(parents=True, exist_ok=True)

    for name, columns in DATASETS.items():
        print(f"\n{name}")

        if None in columns.values():
            print("  skipped: set FORECAST_GRID_LOAD_ID and FORECAST_RESIDUAL_LOAD_ID first")
            continue

        table = build_table(columns)
        path = JSON_DIR / f"{name}_{START:%Y%m%d%H%M}_{END:%Y%m%d%H%M}_Quarterhour.json"
        save_as_json(table, path)
        print(f"  saved {path.name}: {len(table)} rows")