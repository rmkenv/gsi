"""
Grid Stress Index (GSI) — Nightly ETL
IQSpatial / @rmkenv

Computes GSI for all 13 US grid operators and writes
public/data/gsi_latest.json for the Vercel dashboard.

Run: python etl.py
GitHub Actions: nightly at 06:00 UTC
"""

import os, json, warnings, requests
import numpy as np
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

# ── EIA API key (set as GitHub Actions secret: EIA_KEY) ───────────────────────
EIA_KEY  = os.environ.get('EIA_KEY', 'DEMO_KEY')

# ── Date windows ──────────────────────────────────────────────────────────────
TODAY    = datetime.utcnow().strftime('%Y-%m-%d')
WEEK_AGO = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')
HIST_START = '2023-06-01'
HIST_END   = '2023-08-31'

# ── All 13 US grid operators with representative cities ───────────────────────
GRIDS = {
    'ERCO': {
        'label': 'ERCOT', 'region': 'Texas',
        'map_center': [30.5, -97.5],
        'zones': {
            'Houston':     {'lat': 29.76, 'lon': -95.37, 'grid_zone': 'HOUSTON'},
            'Dallas':      {'lat': 32.78, 'lon': -96.80, 'grid_zone': 'NORTH'},
            'San Antonio': {'lat': 29.42, 'lon': -98.49, 'grid_zone': 'SOUTH'},
            'Austin':      {'lat': 30.27, 'lon': -97.74, 'grid_zone': 'SOUTH'},
        }
    },
    'PJM': {
        'label': 'PJM', 'region': 'Mid-Atlantic/Midwest',
        'map_center': [40.0, -77.5],
        'zones': {
            'Philadelphia': {'lat': 39.95, 'lon': -75.17, 'grid_zone': 'PECO'},
            'Baltimore':    {'lat': 39.29, 'lon': -76.61, 'grid_zone': 'BGE'},
            'Chicago':      {'lat': 41.88, 'lon': -87.63, 'grid_zone': 'ComEd'},
            'DC':           {'lat': 38.91, 'lon': -77.04, 'grid_zone': 'Pepco'},
        }
    },
    'CISO': {
        'label': 'CAISO', 'region': 'California',
        'map_center': [36.5, -119.5],
        'zones': {
            'Los Angeles':   {'lat': 34.05, 'lon': -118.25, 'grid_zone': 'LADWP'},
            'San Francisco': {'lat': 37.77, 'lon': -122.42, 'grid_zone': 'PG&E'},
            'Sacramento':    {'lat': 38.58, 'lon': -121.49, 'grid_zone': 'SMUD'},
            'San Diego':     {'lat': 32.72, 'lon': -117.16, 'grid_zone': 'SDG&E'},
        }
    },
    'MISO': {
        'label': 'MISO', 'region': 'Midwest/South',
        'map_center': [40.0, -88.0],
        'zones': {
            'Minneapolis': {'lat': 44.98, 'lon': -93.27, 'grid_zone': 'MISO-MN'},
            'Indianapolis':{'lat': 39.77, 'lon': -86.16, 'grid_zone': 'MISO-IN'},
            'New Orleans': {'lat': 29.95, 'lon': -90.07, 'grid_zone': 'MISO-LA'},
            'Detroit':     {'lat': 42.33, 'lon': -83.05, 'grid_zone': 'MISO-MI'},
        }
    },
    'SWPP': {
        'label': 'SPP', 'region': 'Great Plains',
        'map_center': [38.0, -97.0],
        'zones': {
            'Kansas City': {'lat': 39.10, 'lon': -94.58, 'grid_zone': 'SPP-KS'},
            'Oklahoma City':{'lat': 35.47, 'lon': -97.52, 'grid_zone': 'SPP-OK'},
            'Omaha':       {'lat': 41.26, 'lon': -95.94, 'grid_zone': 'SPP-NE'},
            'Wichita':     {'lat': 37.69, 'lon': -97.34, 'grid_zone': 'SPP-KS'},
        }
    },
    'NYIS': {
        'label': 'NYISO', 'region': 'New York',
        'map_center': [42.5, -75.0],
        'zones': {
            'New York City': {'lat': 40.71, 'lon': -74.01, 'grid_zone': 'NYC'},
            'Buffalo':       {'lat': 42.89, 'lon': -78.88, 'grid_zone': 'WEST'},
            'Albany':        {'lat': 42.65, 'lon': -73.75, 'grid_zone': 'CAPITAL'},
            'Long Island':   {'lat': 40.79, 'lon': -73.13, 'grid_zone': 'LI'},
        }
    },
    'ISNE': {
        'label': 'ISO-NE', 'region': 'New England',
        'map_center': [43.5, -71.5],
        'zones': {
            'Boston':     {'lat': 42.36, 'lon': -71.06, 'grid_zone': 'NEMA'},
            'Hartford':   {'lat': 41.76, 'lon': -72.68, 'grid_zone': 'CT'},
            'Providence': {'lat': 41.82, 'lon': -71.42, 'grid_zone': 'RI'},
            'Portland ME':{'lat': 43.66, 'lon': -70.26, 'grid_zone': 'ME'},
        }
    },
    'SOCO': {
        'label': 'Southern Co', 'region': 'Southeast',
        'map_center': [33.0, -86.0],
        'zones': {
            'Atlanta':     {'lat': 33.75, 'lon': -84.39, 'grid_zone': 'GA'},
            'Birmingham':  {'lat': 33.52, 'lon': -86.80, 'grid_zone': 'AL'},
            'Savannah':    {'lat': 32.08, 'lon': -81.10, 'grid_zone': 'GA'},
            'Montgomery':  {'lat': 32.37, 'lon': -86.30, 'grid_zone': 'AL'},
        }
    },
    'FPL': {
        'label': 'FPL / Florida', 'region': 'Florida',
        'map_center': [27.5, -81.5],
        'zones': {
            'Miami':       {'lat': 25.77, 'lon': -80.19, 'grid_zone': 'FPL-SE'},
            'Orlando':     {'lat': 28.54, 'lon': -81.38, 'grid_zone': 'FPL-C'},
            'Tampa':       {'lat': 27.95, 'lon': -82.46, 'grid_zone': 'TECO'},
            'Jacksonville':{'lat': 30.33, 'lon': -81.66, 'grid_zone': 'JEA'},
        }
    },
    'DUK': {
        'label': 'Duke Energy', 'region': 'Carolinas',
        'map_center': [35.5, -80.0],
        'zones': {
            'Charlotte':  {'lat': 35.23, 'lon': -80.84, 'grid_zone': 'DUK-NC'},
            'Raleigh':    {'lat': 35.78, 'lon': -78.64, 'grid_zone': 'DUK-NC'},
            'Greensboro': {'lat': 36.07, 'lon': -79.79, 'grid_zone': 'DUK-NC'},
            'Columbia SC':{'lat': 34.00, 'lon': -81.03, 'grid_zone': 'DUK-SC'},
        }
    },
    'PACE': {
        'label': 'PacifiCorp East', 'region': 'Rockies',
        'map_center': [41.0, -111.0],
        'zones': {
            'Salt Lake City': {'lat': 40.76, 'lon': -111.89, 'grid_zone': 'PACE-UT'},
            'Denver':         {'lat': 39.74, 'lon': -104.98, 'grid_zone': 'PACE-CO'},
            'Boise':          {'lat': 43.62, 'lon': -116.20, 'grid_zone': 'PACE-ID'},
            'Cheyenne':       {'lat': 41.14, 'lon': -104.82, 'grid_zone': 'PACE-WY'},
        }
    },
    'PACW': {
        'label': 'PacifiCorp West', 'region': 'Pacific Northwest',
        'map_center': [45.5, -122.5],
        'zones': {
            'Portland':  {'lat': 45.52, 'lon': -122.68, 'grid_zone': 'PACW-OR'},
            'Seattle':   {'lat': 47.61, 'lon': -122.33, 'grid_zone': 'PACW-WA'},
            'Eugene':    {'lat': 44.05, 'lon': -123.09, 'grid_zone': 'PACW-OR'},
            'Spokane':   {'lat': 47.66, 'lon': -117.43, 'grid_zone': 'PACW-WA'},
        }
    },
    'AECI': {
        'label': 'AECI', 'region': 'Missouri/Arkansas',
        'map_center': [36.5, -92.0],
        'zones': {
            'St. Louis':    {'lat': 38.63, 'lon': -90.20, 'grid_zone': 'AECI-MO'},
            'Springfield MO':{'lat': 37.21, 'lon': -93.29, 'grid_zone': 'AECI-MO'},
            'Little Rock':  {'lat': 34.75, 'lon': -92.29, 'grid_zone': 'AECI-AR'},
            'Cape Girardeau':{'lat': 37.31, 'lon': -89.52, 'grid_zone': 'AECI-MO'},
        }
    },
}

# ── GSI normalization params ──────────────────────────────────────────────────
TEMP_ANOMALY_RANGE = (-2.0, 5.0)
UHI_RANGE          = (2.0, 12.0)
RESERVE_RANGE      = (0.30, -0.10)
RENEW_SHARE_RANGE  = (0.50, 0.10)

def norm_01(val, lo, hi):
    return float(np.clip((val - lo) / (hi - lo + 1e-9), 0, 1))

def gsi_level(g):
    if g >= 0.75:   return 'CRITICAL', '#ef4444'
    elif g >= 0.55: return 'HIGH',     '#f97316'
    elif g >= 0.35: return 'MODERATE', '#eab308'
    else:           return 'LOW',      '#22c55e'

# ── Data fetchers ─────────────────────────────────────────────────────────────
def fetch_temp_anomaly(lat, lon):
    base = 'https://archive-api.open-meteo.com/v1/archive'
    # Analysis period (Summer 2023)
    r = requests.get(base, params={
        'latitude': lat, 'longitude': lon,
        'start_date': HIST_START, 'end_date': HIST_END,
        'daily': 'temperature_2m_max', 'timezone': 'auto'
    }, timeout=20)
    r.raise_for_status()
    temps = [t for t in r.json()['daily']['temperature_2m_max'] if t is not None]
    mean_temp = float(np.mean(temps)) if temps else np.nan

    # Normal from 5 representative years
    normal_years = [1995, 2000, 2005, 2010, 2015]
    all_normal = []
    for yr in normal_years:
        try:
            nr = requests.get(base, params={
                'latitude': lat, 'longitude': lon,
                'start_date': f'{yr}-06-01', 'end_date': f'{yr}-08-31',
                'daily': 'temperature_2m_max', 'timezone': 'auto'
            }, timeout=20)
            nr.raise_for_status()
            all_normal.extend([t for t in nr.json()['daily']['temperature_2m_max'] if t is not None])
        except Exception:
            continue

    normal_c = float(np.mean(all_normal)) if all_normal else np.nan
    return {
        'mean_temp_c': mean_temp,
        'normal_c':    normal_c,
        'anomaly_c':   mean_temp - normal_c
    }

def fetch_current_temp(lat, lon):
    r = requests.get('https://api.open-meteo.com/v1/forecast', params={
        'latitude': lat, 'longitude': lon,
        'daily': 'temperature_2m_max',
        'current': 'temperature_2m',
        'timezone': 'auto', 'forecast_days': 7
    }, timeout=20)
    r.raise_for_status()
    d = r.json()
    return {
        'current_temp_c': d['current']['temperature_2m'],
        'forecast_max_c': d['daily']['temperature_2m_max'],
        'forecast_dates': d['daily']['time']
    }

def fetch_eia(eia_code, data_type, start, end):
    """data_type: 'generation' or 'demand'"""
    if data_type == 'generation':
        url = 'https://api.eia.gov/v2/electricity/rto/fuel-type-data/data/'
        extra = {}
    else:
        url = 'https://api.eia.gov/v2/electricity/rto/region-data/data/'
        extra = {'facets[type][]': 'D'}

    params = {
        'api_key': EIA_KEY,
        'frequency': 'hourly',
        'data[0]': 'value',
        'facets[respondent][]': eia_code,
        'start': start, 'end': end,
        'sort[0][column]': 'period',
        'sort[0][direction]': 'asc',
        'length': 2000,
        **extra
    }
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        return r.json().get('response', {}).get('data', [])
    except Exception:
        return []

def compute_grid_metrics(eia_code):
    """Returns reserve_margin_mean, renewable_share for Summer 2023."""
    import pandas as pd
    gen_data = fetch_eia(eia_code, 'generation', HIST_START, HIST_END)
    dem_data = fetch_eia(eia_code, 'demand',      HIST_START, HIST_END)

    if not gen_data or not dem_data:
        return 0.15, 0.25  # fallback defaults

    gen_df = pd.DataFrame(gen_data)
    dem_df = pd.DataFrame(dem_data)

    gen_df['datetime'] = pd.to_datetime(gen_df['period'])
    dem_df['datetime'] = pd.to_datetime(dem_df['period'])
    gen_df['val'] = pd.to_numeric(gen_df['value'], errors='coerce')
    dem_df['val'] = pd.to_numeric(dem_df['value'], errors='coerce')

    total_gen = gen_df.groupby('datetime')['val'].sum()
    total_dem = dem_df.groupby('datetime')['val'].sum()
    merged = total_gen.align(total_dem, join='inner')
    reserve = float(((merged[0] - merged[1]) / merged[1]).mean()) if len(merged[0]) > 0 else 0.15

    fuel_col = next((c for c in ['type-name','fueltype','fuel2002'] if c in gen_df.columns), None)
    if fuel_col:
        renew = gen_df[gen_df[fuel_col].str.upper().isin(['SUN','WND'])]
        r_share = float((renew.groupby('datetime')['val'].sum() / total_gen).mean())
    else:
        r_share = 0.25

    return max(reserve, -0.5), max(min(r_share, 1.0), 0.0)

# ── UHI lookup table (pre-computed from Landsat TIRS Summer 2023) ─────────────
# Avoids re-running Planetary Computer in GitHub Actions (no auth needed)
# Update these monthly by running the Landsat cells from the notebook
UHI_LOOKUP = {
    # ERCOT
    'Houston': 8.4, 'Dallas': 7.6, 'San Antonio': 6.6, 'Austin': 6.7,
    # PJM
    'Philadelphia': 9.0, 'Baltimore': 9.9, 'Chicago': 17.3, 'DC': 7.6,
    # CAISO
    'Los Angeles': 8.4, 'San Francisco': 20.3, 'Sacramento': 6.2, 'San Diego': 23.9,
    # MISO
    'Minneapolis': 8.5, 'Indianapolis': 7.2, 'New Orleans': 6.8, 'Detroit': 9.1,
    # SPP
    'Kansas City': 6.5, 'Oklahoma City': 5.8, 'Omaha': 5.2, 'Wichita': 4.9,
    # NYISO
    'New York City': 12.4, 'Buffalo': 6.1, 'Albany': 5.8, 'Long Island': 8.2,
    # ISO-NE
    'Boston': 8.7, 'Hartford': 6.4, 'Providence': 5.9, 'Portland ME': 4.2,
    # SOCO
    'Atlanta': 7.8, 'Birmingham': 6.9, 'Savannah': 5.4, 'Montgomery': 5.1,
    # FPL
    'Miami': 7.2, 'Orlando': 6.1, 'Tampa': 5.8, 'Jacksonville': 5.3,
    # Duke
    'Charlotte': 7.4, 'Raleigh': 6.8, 'Greensboro': 5.9, 'Columbia SC': 5.3,
    # PacifiCorp East
    'Salt Lake City': 9.2, 'Denver': 8.1, 'Boise': 6.4, 'Cheyenne': 4.8,
    # PacifiCorp West
    'Portland': 7.6, 'Seattle': 6.9, 'Eugene': 5.1, 'Spokane': 5.4,
    # AECI
    'St. Louis': 7.9, 'Springfield MO': 5.3, 'Little Rock': 5.7, 'Cape Girardeau': 4.8,
}

# ── Main ETL ──────────────────────────────────────────────────────────────────
def run_etl():
    print(f'⚡ GSI ETL starting — {TODAY}')
    output = {
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'grids': {}
    }

    for eia_code, grid in GRIDS.items():
        print(f'\n🔄 {grid["label"]} ({eia_code})')

        # Grid-wide EIA metrics (shared across all zones)
        print('  [EIA grid metrics]')
        reserve_mean, renew_share = compute_grid_metrics(eia_code)
        print(f'  Reserve mean: {reserve_mean:.1%} | Renewable share: {renew_share:.1%}')

        c3 = norm_01(RESERVE_RANGE[0] - reserve_mean,
                     0, RESERVE_RANGE[0] - RESERVE_RANGE[1])
        c4 = norm_01(RENEW_SHARE_RANGE[0] - renew_share,
                     0, RENEW_SHARE_RANGE[0] - RENEW_SHARE_RANGE[1])

        zones_out = {}
        gsi_scores = []

        for zone_name, meta in grid['zones'].items():
            print(f'  📍 {zone_name}')
            try:
                # Temperature anomaly
                temp = fetch_temp_anomaly(meta['lat'], meta['lon'])
                c1   = norm_01(temp['anomaly_c'], *TEMP_ANOMALY_RANGE)

                # UHI from lookup table
                uhi  = UHI_LOOKUP.get(zone_name, 6.0)
                c2   = norm_01(uhi, *UHI_RANGE)

                # Historical GSI
                gsi_hist = c1*0.30 + c2*0.25 + c3*0.30 + c4*0.15

                # Current + forecast
                curr = fetch_current_temp(meta['lat'], meta['lon'])
                c1_curr = norm_01(curr['current_temp_c'] - temp['normal_c'],
                                  *TEMP_ANOMALY_RANGE)
                c1_fore = norm_01(max(curr['forecast_max_c']) - temp['normal_c'],
                                  *TEMP_ANOMALY_RANGE)
                gsi_curr = c1_curr*0.30 + c2*0.25 + c3*0.30 + c4*0.15
                gsi_fore = c1_fore*0.30 + c2*0.25 + c3*0.30 + c4*0.15

                lh, ch = gsi_level(gsi_hist)
                lc, cc = gsi_level(gsi_curr)
                lf, cf = gsi_level(gsi_fore)

                gsi_scores.append(gsi_fore)

                zones_out[zone_name] = {
                    'lat': meta['lat'], 'lon': meta['lon'],
                    'grid_zone': meta['grid_zone'],
                    'gsi_historical': round(gsi_hist, 3),
                    'gsi_current':    round(gsi_curr, 3),
                    'gsi_forecast':   round(gsi_fore, 3),
                    'level_hist': lh, 'color_hist': ch,
                    'level_curr': lc, 'color_curr': cc,
                    'level_fore': lf, 'color_fore': cf,
                    'components': {
                        'temp_anomaly':    round(c1, 3),
                        'uhi':             round(c2, 3),
                        'reserve_margin':  round(c3, 3),
                        'renew_shortfall': round(c4, 3)
                    },
                    'raw': {
                        'temp_anomaly_c':  round(temp['anomaly_c'], 2),
                        'uhi_intensity_c': uhi,
                        'current_temp_c':  curr['current_temp_c'],
                        'forecast_max_c':  round(max(curr['forecast_max_c']), 1),
                        'forecast_dates':  curr['forecast_dates'],
                        'forecast_temps':  curr['forecast_max_c'],
                        'normal_c':        round(temp['normal_c'], 1),
                        'mean_temp_c':     round(temp['mean_temp_c'], 1)
                    }
                }
                print(f'    GSI fore={gsi_fore:.3f} {lf}')

            except Exception as ex:
                print(f'    ⚠️  {zone_name}: {ex}')
                gsi_scores.append(0.5)
                zones_out[zone_name] = {'error': str(ex)}

        # Grid-level summary
        grid_gsi = float(np.mean(gsi_scores)) if gsi_scores else 0.5
        gl, gc   = gsi_level(grid_gsi)

        output['grids'][eia_code] = {
            'label':      grid['label'],
            'region':     grid['region'],
            'eia_code':   eia_code,
            'map_center': grid['map_center'],
            'gsi_mean':   round(grid_gsi, 3),
            'level':      gl,
            'color':      gc,
            'zones':      zones_out
        }
        print(f'  ✅ {grid["label"]} mean GSI={grid_gsi:.3f} {gl}')

    # Write output
    os.makedirs('public/data', exist_ok=True)
    with open('public/data/gsi_latest.json', 'w') as f:
        json.dump(output, f, indent=2)
    print(f'\n✅ Written to public/data/gsi_latest.json')

    # Also write a history entry
    hist_file = f'public/data/gsi_{TODAY.replace("-","")}.json'
    with open(hist_file, 'w') as f:
        json.dump(output, f, indent=2)
    print(f'✅ History snapshot: {hist_file}')

    return output

if __name__ == '__main__':
    run_etl()
