"""Load the SMARD CSV files (actual + forecasted consumption) into PostgreSQL.

This is the "L" (load) step of ELT:
- the data is stored almost unchanged in the schema "raw"
- only small technical fixes: short column names, numbers as numbers,
  time as a real timestamp with time zone
- cleaning and combining the data happens later in dbt

Run from the project folder (PostgreSQL must be running: docker compose up -d):
    python ingestion/load_csv_to_postgres.py
"""

import os
from pathlib import Path
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

PROJECT_DIR = Path(__file__).resolve().parent.parent
CSV_DIR = PROJECT_DIR / "data" / "raw" / "csv"

load_dotenv(PROJECT_DIR / ".env")   # reads POSTGRES_USER, POSTGRES_PASSWORD, ...

# Which files go into which table, and which columns the table has
DATASETS = {
    "actual_consumption": {
        "file_pattern": "Actual_consumption_*.csv",
        "columns": ["grid_load", "grid_load_incl_hydro_pumped_storage",
                    "hydro_pumped_storage", "residual_load"],
    },
    "forecasted_consumption": {
        "file_pattern": "Forecasted_consumption_*.csv",
        "columns": ["grid_load", "residual_load"],
    },
}


def connect():
    """Open a connection to PostgreSQL with the settings from .env."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


def read_smard_csv(path: Path) -> pd.DataFrame:
    """Read one SMARD CSV file (same rules as explore/explore_csv.py)."""
    df = pd.read_csv(path, sep=";", encoding="utf-8-sig", thousands=",", na_values="-")

    # "Sep 1, 2026 12:00 AM" -> timestamp in German time (CET/CEST).
    # ambiguous="infer": in the October night 02:00-03:00 happens twice;
    # pandas uses the order of the rows to tell summer and winter time apart.
    for col in ["Start date", "End date"]:
        local = pd.to_datetime(df[col], format="%b %d, %Y %I:%M %p")
        df[col] = local.dt.tz_localize("Europe/Berlin", ambiguous="infer")

    # Short column names: "grid load [MWh] Original resolutions" -> "grid_load"
    df.columns = [
        c.replace(" [MWh] Original resolutions", "").lower().replace(".", "").replace(" ", "_")
        for c in df.columns
    ]
    return df.rename(columns={"start_date": "start_ts", "end_date": "end_ts"})


def create_table(cur, table: str, columns: list[str]) -> None:
    """Create the schema and table once; later runs leave them as they are."""
    value_columns = ",\n    ".join(f"{c} NUMERIC" for c in columns)
    cur.execute(f"""
        CREATE SCHEMA IF NOT EXISTS raw;
        CREATE TABLE IF NOT EXISTS raw.{table} (
            start_ts    TIMESTAMPTZ PRIMARY KEY,   -- start of the quarter hour
            end_ts      TIMESTAMPTZ NOT NULL,
            {value_columns},
            source_file TEXT        NOT NULL,      -- which file the row came from
            loaded_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)


def upsert(cur, table: str, columns: list[str], df: pd.DataFrame, source_file: str) -> None:
    """Insert new rows; if a quarter hour already exists, overwrite it.

    That makes the script idempotent: running it twice gives the same result,
    no duplicates.
    """
    all_columns = ["start_ts", "end_ts", *columns, "source_file"]
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in all_columns if c != "start_ts")

    df = df.assign(source_file=source_file)[all_columns]
    df = df.astype(object).where(df.notna(), None)          # NaN -> NULL
    rows = list(df.itertuples(index=False, name=None))

    execute_values(cur, f"""
        INSERT INTO raw.{table} ({", ".join(all_columns)})
        VALUES %s
        ON CONFLICT (start_ts) DO UPDATE SET {updates}, loaded_at = now();
    """, rows)


def main() -> None:
    with connect() as conn, conn.cursor() as cur:
        for table, cfg in DATASETS.items():
            files = sorted(CSV_DIR.glob(cfg["file_pattern"]))
            if not files:
                print(f"raw.{table}: no files matching {cfg['file_pattern']} in {CSV_DIR}")
                continue

            create_table(cur, table, cfg["columns"])
            for path in files:
                df = read_smard_csv(path)
                upsert(cur, table, cfg["columns"], df, path.name)
                print(f"raw.{table}: {len(df)} rows from {path.name}")

            cur.execute(f"SELECT count(*), min(start_ts), max(start_ts) FROM raw.{table}")
            count, first, last = cur.fetchone()
            print(f"  -> table now has {count} rows, {first} to {last}")
    # leaving "with connect()" commits everything at once (or nothing, if an error happened)


if __name__ == "__main__":
    main()