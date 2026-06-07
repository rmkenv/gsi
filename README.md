# ⚡ Grid Stress Index Dashboard

**IQSpatial / @rmkenv**

Composite satellite + weather + grid signal for all 13 US grid operators.
Live dashboard: [gsi.vercel.app](https://gsi.vercel.app)

## GSI Components
| Signal | Weight | Source |
|--------|--------|--------|
| Temperature anomaly vs 30yr normal | 30% | Open-Meteo ERA5 archive |
| Urban Heat Island intensity | 25% | Landsat 8/9 TIRS (pre-computed) |
| Reserve margin tightness | 30% | EIA API v2 |
| Renewable generation shortfall | 15% | EIA API v2 |

## GSI Scale
| Score | Level |
|-------|-------|
| 0.00 – 0.35 | 🟢 LOW |
| 0.35 – 0.55 | 🟡 MODERATE |
| 0.55 – 0.75 | 🟠 HIGH |
| 0.75 – 1.00 | 🔴 CRITICAL |

## Deploy to Vercel

```bash
# 1. Fork this repo
# 2. Install Vercel CLI
npm i -g vercel

# 3. Deploy
vercel --prod
```

## GitHub Actions Setup

1. Go to repo Settings → Secrets → Actions
2. Add secret: `EIA_KEY` = your free EIA API key from [eia.gov/opendata](https://www.eia.gov/opendata/register.php)
3. The nightly workflow runs at 06:00 UTC and commits updated JSON to `public/data/`
4. Vercel auto-deploys on each commit

## Run ETL Locally

```bash
pip install -r requirements.txt
export EIA_KEY=your_key_here
python etl.py
```

Output: `public/data/gsi_latest.json` + `public/data/gsi_YYYYMMDD.json`

## Update UHI Values

The `UHI_LOOKUP` table in `etl.py` contains pre-computed Landsat TIRS values.
To refresh, run the GSI notebook (`grid_stress_index.ipynb`) for each grid
and update the table with new P80-P20 LST spread values. Refresh monthly.

## Project Structure

```
gsi-dashboard/
├── etl.py                          # Nightly ETL — all 13 grids
├── requirements.txt
├── vercel.json                     # Vercel static deploy config
├── .github/workflows/nightly.yml  # GitHub Actions schedule
└── public/
    ├── index.html                  # Dashboard UI
    └── data/
        ├── gsi_latest.json         # Latest GSI (auto-updated)
        └── gsi_YYYYMMDD.json       # Daily snapshots
```

## Grids Covered

| EIA Code | Grid | Region |
|----------|------|--------|
| ERCO | ERCOT | Texas |
| PJM | PJM | Mid-Atlantic/Midwest |
| CISO | CAISO | California |
| MISO | MISO | Midwest/South |
| SWPP | SPP | Great Plains |
| NYIS | NYISO | New York |
| ISNE | ISO-NE | New England |
| SOCO | Southern Co | Southeast |
| FPL | FPL/Florida | Florida |
| DUK | Duke Energy | Carolinas |
| PACE | PacifiCorp East | Rockies |
| PACW | PacifiCorp West | Pacific Northwest |
| AECI | AECI | Missouri/Arkansas |

---
Built by [IQSpatial](https://github.com/rmkenv) | Open source | Zero cost data
