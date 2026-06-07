"""
Grid Stress Index (GSI) — Nightly ETL
IQSpatial / @rmkenv

Run: python scripts/etl.py
GitHub Actions: nightly at 06:00 UTC
"""

import os, json, math, warnings, requests
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta

warnings.filterwarnings('ignore')

EIA_KEY    = os.environ.get('EIA_KEY', 'DEMO_KEY')
_now       = datetime.now(timezone.utc)
TODAY      = _now.strftime('%Y-%m-%d')
WEEK_AGO   = (_now - timedelta(days=7)).strftime('%Y-%m-%d')
HIST_START = '2023-06-01'
HIST_END   = '2023-08-31'

GRIDS = {
    'ERCO': {'label':'ERCOT','region':'Texas','map_center':[30.5,-97.5],'zones':{'Houston':{'lat':29.76,'lon':-95.37,'grid_zone':'HOUSTON'},'Dallas':{'lat':32.78,'lon':-96.80,'grid_zone':'NORTH'},'San Antonio':{'lat':29.42,'lon':-98.49,'grid_zone':'SOUTH'},'Austin':{'lat':30.27,'lon':-97.74,'grid_zone':'SOUTH'}}},
    'PJM':  {'label':'PJM','region':'Mid-Atlantic/Midwest','map_center':[40.0,-77.5],'zones':{'Philadelphia':{'lat':39.95,'lon':-75.17,'grid_zone':'PECO'},'Baltimore':{'lat':39.29,'lon':-76.61,'grid_zone':'BGE'},'Chicago':{'lat':41.88,'lon':-87.63,'grid_zone':'ComEd'},'DC':{'lat':38.91,'lon':-77.04,'grid_zone':'Pepco'}}},
    'CISO': {'label':'CAISO','region':'California','map_center':[36.5,-119.5],'zones':{'Los Angeles':{'lat':34.05,'lon':-118.25,'grid_zone':'LADWP'},'San Francisco':{'lat':37.77,'lon':-122.42,'grid_zone':'PG&E'},'Sacramento':{'lat':38.58,'lon':-121.49,'grid_zone':'SMUD'},'San Diego':{'lat':32.72,'lon':-117.16,'grid_zone':'SDG&E'}}},
    'MISO': {'label':'MISO','region':'Midwest/South','map_center':[40.0,-88.0],'zones':{'Minneapolis':{'lat':44.98,'lon':-93.27,'grid_zone':'MISO-MN'},'Indianapolis':{'lat':39.77,'lon':-86.16,'grid_zone':'MISO-IN'},'New Orleans':{'lat':29.95,'lon':-90.07,'grid_zone':'MISO-LA'},'Detroit':{'lat':42.33,'lon':-83.05,'grid_zone':'MISO-MI'}}},
    'SWPP': {'label':'SPP','region':'Great Plains','map_center':[38.0,-97.0],'zones':{'Kansas City':{'lat':39.10,'lon':-94.58,'grid_zone':'SPP-KS'},'Oklahoma City':{'lat':35.47,'lon':-97.52,'grid_zone':'SPP-OK'},'Omaha':{'lat':41.26,'lon':-95.94,'grid_zone':'SPP-NE'},'Wichita':{'lat':37.69,'lon':-97.34,'grid_zone':'SPP-KS'}}},
    'NYIS': {'label':'NYISO','region':'New York','map_center':[42.5,-75.0],'zones':{'New York City':{'lat':40.71,'lon':-74.01,'grid_zone':'NYC'},'Buffalo':{'lat':42.89,'lon':-78.88,'grid_zone':'WEST'},'Albany':{'lat':42.65,'lon':-73.75,'grid_zone':'CAPITAL'},'Long Island':{'lat':40.79,'lon':-73.13,'grid_zone':'LI'}}},
    'ISNE': {'label':'ISO-NE','region':'New England','map_center':[43.5,-71.5],'zones':{'Boston':{'lat':42.36,'lon':-71.06,'grid_zone':'NEMA'},'Hartford':{'lat':41.76,'lon':-72.68,'grid_zone':'CT'},'Providence':{'lat':41.82,'lon':-71.42,'grid_zone':'RI'},'Portland ME':{'lat':43.66,'lon':-70.26,'grid_zone':'ME'}}},
    'SOCO': {'label':'Southern Co','region':'Southeast','map_center':[33.0,-86.0],'zones':{'Atlanta':{'lat':33.75,'lon':-84.39,'grid_zone':'GA'},'Birmingham':{'lat':33.52,'lon':-86.80,'grid_zone':'AL'},'Savannah':{'lat':32.08,'lon':-81.10,'grid_zone':'GA'},'Montgomery':{'lat':32.37,'lon':-86.30,'grid_zone':'AL'}}},
    'FPL':  {'label':'FPL / Florida','region':'Florida','map_center':[27.5,-81.5],'zones':{'Miami':{'lat':25.77,'lon':-80.19,'grid_zone':'FPL-SE'},'Orlando':{'lat':28.54,'lon':-81.38,'grid_zone':'FPL-C'},'Tampa':{'lat':27.95,'lon':-82.46,'grid_zone':'TECO'},'Jacksonville':{'lat':30.33,'lon':-81.66,'grid_zone':'JEA'}}},
    'DUK':  {'label':'Duke Energy','region':'Carolinas','map_center':[35.5,-80.0],'zones':{'Charlotte':{'lat':35.23,'lon':-80.84,'grid_zone':'DUK-NC'},'Raleigh':{'lat':35.78,'lon':-78.64,'grid_zone':'DUK-NC'},'Greensboro':{'lat':36.07,'lon':-79.79,'grid_zone':'DUK-NC'},'Columbia SC':{'lat':34.00,'lon':-81.03,'grid_zone':'DUK-SC'}}},
    'PACE': {'label':'PacifiCorp East','region':'Rockies','map_center':[41.0,-111.0],'zones':{'Salt Lake City':{'lat':40.76,'lon':-111.89,'grid_zone':'PACE-UT'},'Denver':{'lat':39.74,'lon':-104.98,'grid_zone':'PACE-CO'},'Boise':{'lat':43.62,'lon':-116.20,'grid_zone':'PACE-ID'},'Cheyenne':{'lat':41.14,'lon':-104.82,'grid_zone':'PACE-WY'}}},
    'PACW': {'label':'PacifiCorp West','region':'Pacific Northwest','map_center':[45.5,-122.5],'zones':{'Portland':{'lat':45.52,'lon':-122.68,'grid_zone':'PACW-OR'},'Seattle':{'lat':47.61,'lon':-122.33,'grid_zone':'PACW-WA'},'Eugene':{'lat':44.05,'lon':-123.09,'grid_zone':'PACW-OR'},'Spokane':{'lat':47.66,'lon':-117.43,'grid_zone':'PACW-WA'}}},
    'AECI': {'label':'AECI','region':'Missouri/Arkansas','map_center':[36.5,-92.0],'zones':{'St. Louis':{'lat':38.63,'lon':-90.20,'grid_zone':'AECI-MO'},'Springfield MO':{'lat':37.21,'lon':-93.29,'grid_zone':'AECI-MO'},'Little Rock':{'lat':34.75,'lon':-92.29,'grid_zone':'AECI-AR'},'Cape Girardeau':{'lat':37.31,'lon':-89.52,'grid_zone':'AECI-MO'}}},
}

UHI_LOOKUP = {
    'Houston':8.4,'Dallas':7.6,'San Antonio':6.6,'Austin':6.7,
    'Philadelphia':9.0,'Baltimore':9.9,'Chicago':17.3,'DC':7.6,
    'Los Angeles':8.4,'San Francisco':20.3,'Sacramento':6.2,'San Diego':23.9,
    'Minneapolis':8.5,'Indianapolis':7.2,'New Orleans':6.8,'Detroit':9.1,
    'Kansas City':6.5,'Oklahoma City':5.8,'Omaha':5.2,'Wichita':4.9,
    'New York City':12.4,'Buffalo':6.1,'Albany':5.8,'Long Island':8.2,
    'Boston':8.7,'Hartford':6.4,'Providence':5.9,'Portland ME':4.2,
    'Atlanta':7.8,'Birmingham':6.9,'Savannah':5.4,'Montgomery':5.1,
    'Miami':7.2,'Orlando':6.1,'Tampa':5.8,'Jacksonville':5.3,
    'Charlotte':7.4,'Raleigh':6.8,'Greensboro':5.9,'Columbia SC':5.3,
    'Salt Lake City':9.2,'Denver':8.1,'Boise':6.4,'Cheyenne':4.8,
    'Portland':7.6,'Seattle':6.9,'Eugene':5.1,'Spokane':5.4,
    'St. Louis':7.9,'Springfield MO':5.3,'Little Rock':5.7,'Cape Girardeau':4.8,
}

TEMP_ANOMALY_RANGE = (-2.0, 5.0)
UHI_RANGE          = (2.0, 12.0)
RESERVE_RANGE      = (0.30, -0.10)
RENEW_SHARE_RANGE  = (0.50, 0.10)

def safe_float(val, default=0.0):
    try:
        f = float(val)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return default

def sanitize(obj):
    """Replace NaN/Inf with None — prevents invalid JSON output."""
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(i) for i in obj]
    return obj

def norm_01(val, lo, hi):
    v = safe_float(val)
    return float(np.clip((v - lo) / (hi - lo + 1e-9), 0, 1))

def gsi_level(g):
    g = safe_float(g, 0.5)
    if g >= 0.75:   return 'CRITICAL', '#ef4444'
    elif g >= 0.55: return 'HIGH',     '#f97316'
    elif g >= 0.35: return 'MODERATE', '#eab308'
    else:           return 'LOW',      '#22c55e'

def fetch_temp_anomaly(lat, lon):
    base = 'https://archive-api.open-meteo.com/v1/archive'
    r = requests.get(base, params={
        'latitude': lat, 'longitude': lon,
        'start_date': HIST_START, 'end_date': HIST_END,
        'daily': 'temperature_2m_max', 'timezone': 'auto'
    }, timeout=20)
    r.raise_for_status()
    temps = [t for t in r.json()['daily']['temperature_2m_max'] if t is not None]
    mean_temp = safe_float(np.mean(temps)) if temps else 30.0

    all_normal = []
    for yr in [1995, 2000, 2005, 2010, 2015]:
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

    normal_c  = safe_float(np.mean(all_normal)) if all_normal else mean_temp
    anomaly_c = safe_float(mean_temp - normal_c)
    return {'mean_temp_c': round(mean_temp,1), 'normal_c': round(normal_c,1), 'anomaly_c': round(anomaly_c,2)}

def fetch_current_temp(lat, lon):
    r = requests.get('https://api.open-meteo.com/v1/forecast', params={
        'latitude': lat, 'longitude': lon,
        'daily': 'temperature_2m_max', 'current': 'temperature_2m',
        'timezone': 'auto', 'forecast_days': 7
    }, timeout=20)
    r.raise_for_status()
    d = r.json()
    return {
        'current_temp_c': safe_float(d['current']['temperature_2m']),
        'forecast_max_c': [safe_float(t) for t in d['daily']['temperature_2m_max']],
        'forecast_dates': d['daily']['time']
    }

def fetch_eia(eia_code, data_type, start, end):
    if data_type == 'generation':
        url, extra = 'https://api.eia.gov/v2/electricity/rto/fuel-type-data/data/', {}
    else:
        url, extra = 'https://api.eia.gov/v2/electricity/rto/region-data/data/', {'facets[type][]': 'D'}
    try:
        r = requests.get(url, params={'api_key':EIA_KEY,'frequency':'hourly','data[0]':'value',
            'facets[respondent][]':eia_code,'start':start,'end':end,
            'sort[0][column]':'period','sort[0][direction]':'asc','length':2000,**extra}, timeout=20)
        r.raise_for_status()
        return r.json().get('response', {}).get('data', [])
    except Exception:
        return []

def compute_grid_metrics(eia_code):
    gen_data = fetch_eia(eia_code, 'generation', HIST_START, HIST_END)
    dem_data = fetch_eia(eia_code, 'demand',      HIST_START, HIST_END)
    if not gen_data or not dem_data:
        return 0.15, 0.25

    gen_df = pd.DataFrame(gen_data)
    dem_df = pd.DataFrame(dem_data)
    gen_df['datetime'] = pd.to_datetime(gen_df['period'])
    dem_df['datetime'] = pd.to_datetime(dem_df['period'])
    gen_df['val'] = pd.to_numeric(gen_df['value'], errors='coerce').fillna(0)
    dem_df['val'] = pd.to_numeric(dem_df['value'], errors='coerce').fillna(0)

    total_gen = gen_df.groupby('datetime')['val'].sum()
    total_dem = dem_df.groupby('datetime')['val'].sum()
    ag, ad = total_gen.align(total_dem, join='inner')

    with np.errstate(divide='ignore', invalid='ignore'):
        reserve = safe_float(((ag - ad) / ad.replace(0, np.nan)).mean(), 0.15)
    reserve = max(min(reserve, 2.0), -0.5)

    fuel_col = next((c for c in ['type-name','fueltype','fuel2002'] if c in gen_df.columns), None)
    if fuel_col:
        renew = gen_df[gen_df[fuel_col].str.upper().isin(['SUN','WND'])]
        with np.errstate(divide='ignore', invalid='ignore'):
            r_share = safe_float((renew.groupby('datetime')['val'].sum() / total_gen.replace(0,np.nan)).mean(), 0.25)
    else:
        r_share = 0.25
    return reserve, max(min(r_share, 1.0), 0.0)

def run_etl():
    print(f'⚡ GSI ETL starting — {TODAY}')
    output = {'generated_at': datetime.now(timezone.utc).isoformat(), 'grids': {}}

    for eia_code, grid in GRIDS.items():
        print(f'\n🔄 {grid["label"]} ({eia_code})')
        reserve_mean, renew_share = compute_grid_metrics(eia_code)
        print(f'  Reserve: {reserve_mean:.1%} | Renewable: {renew_share:.1%}')

        c3 = norm_01(RESERVE_RANGE[0] - reserve_mean, 0, RESERVE_RANGE[0] - RESERVE_RANGE[1])
        c4 = norm_01(RENEW_SHARE_RANGE[0] - renew_share, 0, RENEW_SHARE_RANGE[0] - RENEW_SHARE_RANGE[1])

        zones_out, gsi_scores = {}, []

        for zone_name, meta in grid['zones'].items():
            print(f'  📍 {zone_name}')
            try:
                temp    = fetch_temp_anomaly(meta['lat'], meta['lon'])
                c1      = norm_01(temp['anomaly_c'], *TEMP_ANOMALY_RANGE)
                uhi     = safe_float(UHI_LOOKUP.get(zone_name, 6.0))
                c2      = norm_01(uhi, *UHI_RANGE)
                gsi_hist = safe_float(c1*0.30 + c2*0.25 + c3*0.30 + c4*0.15)

                curr    = fetch_current_temp(meta['lat'], meta['lon'])
                c1_curr = norm_01(curr['current_temp_c'] - temp['normal_c'], *TEMP_ANOMALY_RANGE)
                c1_fore = norm_01(max(curr['forecast_max_c']) - temp['normal_c'], *TEMP_ANOMALY_RANGE)
                gsi_curr = safe_float(c1_curr*0.30 + c2*0.25 + c3*0.30 + c4*0.15)
                gsi_fore = safe_float(c1_fore*0.30 + c2*0.25 + c3*0.30 + c4*0.15)

                lh,ch = gsi_level(gsi_hist)
                lc,cc = gsi_level(gsi_curr)
                lf,cf = gsi_level(gsi_fore)
                gsi_scores.append(gsi_fore)

                zones_out[zone_name] = {
                    'lat': meta['lat'], 'lon': meta['lon'], 'grid_zone': meta['grid_zone'],
                    'gsi_historical': round(gsi_hist,3), 'gsi_current': round(gsi_curr,3), 'gsi_forecast': round(gsi_fore,3),
                    'level_hist':lh,'color_hist':ch,'level_curr':lc,'color_curr':cc,'level_fore':lf,'color_fore':cf,
                    'components': {'temp_anomaly':round(c1,3),'uhi':round(c2,3),'reserve_margin':round(c3,3),'renew_shortfall':round(c4,3)},
                    'raw': {'temp_anomaly_c':temp['anomaly_c'],'uhi_intensity_c':uhi,'current_temp_c':curr['current_temp_c'],
                            'forecast_max_c':round(max(curr['forecast_max_c']),1),'forecast_dates':curr['forecast_dates'],
                            'forecast_temps':curr['forecast_max_c'],'normal_c':temp['normal_c'],'mean_temp_c':temp['mean_temp_c']}
                }
                print(f'    GSI={gsi_fore:.3f} {lf}')
            except Exception as ex:
                print(f'    ⚠️  {zone_name}: {ex}')
                gsi_scores.append(0.5)
                zones_out[zone_name] = {'error': str(ex), 'lat': meta['lat'], 'lon': meta['lon']}

        grid_gsi = safe_float(np.mean(gsi_scores), 0.5) if gsi_scores else 0.5
        gl, gc   = gsi_level(grid_gsi)
        output['grids'][eia_code] = {
            'label':grid['label'],'region':grid['region'],'eia_code':eia_code,
            'map_center':grid['map_center'],'gsi_mean':round(grid_gsi,3),
            'level':gl,'color':gc,'zones':zones_out
        }
        print(f'  ✅ {grid["label"]} GSI={grid_gsi:.3f} {gl}')

    # ── Sanitize before writing — eliminates NaN from JSON output ─────────────
    clean = sanitize(output)
    os.makedirs('public/data', exist_ok=True)

    with open('public/data/gsi_latest.json', 'w') as f:
        json.dump(clean, f, indent=2)
    print(f'\n✅ public/data/gsi_latest.json written')

    hist = f'public/data/gsi_{TODAY.replace("-","")}.json'
    with open(hist, 'w') as f:
        json.dump(clean, f, indent=2)
    print(f'✅ History: {hist}')

    return clean

if __name__ == '__main__':
    run_etl()
