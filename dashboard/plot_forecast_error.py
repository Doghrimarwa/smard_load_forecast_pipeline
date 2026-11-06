"""Plot the dbt result: forecast error per hour of the day.
Reads the dbt mart analytics_marts.agg_forecast_error_by_hour from PostgreSQL.
"""
import logging
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                     # draw into a file, no window needed
import matplotlib.pyplot as plt
import pandas as pd
import psycopg2
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUT_FILE = PROJECT_DIR / "docs" / "images" / "forecast_error_by_hour.png"
load_dotenv(PROJECT_DIR / ".env")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)   # no warnings for missing fonts

# Colours (light theme): one colour per series, quiet greys for text and grid
GRID_LOAD = "#2a78d6"       # blue
RESIDUAL_LOAD = "#eb6834"   # orange
INK, MUTED, GRID, BASE = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7"

QUERY = """
    SELECT hour_local, grid_load_mae_mwh, residual_load_mae_mwh, grid_load_bias_mwh
    FROM analytics_marts.agg_forecast_error_by_hour
    ORDER BY hour_local
"""


def read_mart() -> pd.DataFrame:
    """Run the query and return the 24 rows as a table."""
    with psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    ) as conn, conn.cursor() as cur:
        cur.execute(QUERY)
        columns = [c.name for c in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=columns).astype(float)


def style(ax) -> None:
    """Quiet axes: no box, light horizontal grid, grey tick labels."""
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(BASE)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED, length=0, labelsize=9)


def plot(df: pd.DataFrame) -> None:
    plt.rcParams["font.family"] = ["Inter", "Segoe UI", "DejaVu Sans"]
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(9, 6.4), sharex=True, gridspec_kw={"height_ratios": [3, 2], "hspace": 0.35}
    )
    hours = df["hour_local"]

    # Top: how big is the error? (mean absolute error)
    top.plot(hours, df["residual_load_mae_mwh"], color=RESIDUAL_LOAD, linewidth=2,
             marker="o", markersize=4, label="Residual load")
    top.plot(hours, df["grid_load_mae_mwh"], color=GRID_LOAD, linewidth=2,
             marker="o", markersize=4, label="Grid load")
    top.set_ylim(0, df["residual_load_mae_mwh"].max() * 1.15)
    top.set_title("Mean absolute error (MWh per quarter hour)", loc="left",
                  fontsize=10, color=MUTED, pad=8)
    top.legend(loc="upper left", frameon=False, fontsize=9, labelcolor=INK, ncol=2)
    style(top)

    # Bottom: in which direction? (bias of the grid load forecast)
    bottom.bar(hours, df["grid_load_bias_mwh"], color=GRID_LOAD, width=0.7)
    bottom.axhline(0, color=BASE, linewidth=1)
    bottom.set_title("Grid load bias (MWh per quarter hour): above 0 = forecast too high, below 0 = too low",
                     loc="left", fontsize=10, color=MUTED, pad=8)
    bottom.set_xticks(range(0, 24, 2))
    bottom.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 2)])
    bottom.set_xlabel("Hour of day (German time)", color=MUTED, fontsize=9)
    style(bottom)

    fig.suptitle("The load forecast misses most in the morning and runs too low at midday",
                 x=0.06, y=0.98, ha="left", fontsize=13, fontweight="semibold", color=INK)
    fig.text(0.06, 0.925, "50Hertz control area, September 2026 · forecast vs. actual · source: SMARD.de (CC BY 4.0)",
             ha="left", fontsize=9, color=MUTED)
    fig.subplots_adjust(left=0.06, right=0.98, top=0.84, bottom=0.09)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_FILE, dpi=150, facecolor="white")
    print(f"Saved {OUT_FILE.relative_to(PROJECT_DIR)}")


if __name__ == "__main__":
    plot(read_mart())