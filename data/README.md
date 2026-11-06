# Data

Sample data for **September 2026**, **50Hertz** control area, **15-minute resolution**.

| Folder | Content | How it was created |
|---|---|---|
| `raw/csv/` | Actual and forecasted consumption | Manual download from the [SMARD Downloadcenter](https://www.smard.de/en/downloadcenter/download-market-data/) |
| `raw/xml/` | Same data as XML | Manual download from the SMARD Downloadcenter |
| `raw/json/` | Actual consumption | SMARD API (`explore/explore_json.py`) |
| `raw/json/` | Forecasted consumption | Converted from CSV (`explore/forecast_csv_to_json.py`), because the API has no forecast data |

## Values

- Unit: **MWh per quarter hour** (multiply by 4 for average power in MW)
- Time: German local time (CET/CEST); each row covers `[Start date, End date)`
- Forecast data contains only **grid load** and **residual load**; pumped storage is published as actual data only
- Residual load = grid load − wind − solar

## SMARD API

SMARD has a public JSON API that returns the data behind its charts
(documented by [bundesAPI/smard-api](https://github.com/bundesAPI/smard-api)):

1. Index of weekly blocks: `https://www.smard.de/app/chart_data/{filter}/{region}/index_{resolution}.json`
2. One weekly block: `https://www.smard.de/app/chart_data/{filter}/{region}/{filter}_{region}_{resolution}_{timestamp}.json`

| Filter ID | Series |
|---|---|
| 410 | Grid load |
| 4359 | Residual load |
| 4387 | Hydro pumped storage |

## Source and license

Bundesnetzagentur | SMARD.de, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).