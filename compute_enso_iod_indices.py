"""
NINO3.4 and DMI (Dipole Mode Index, Saji et al. 1999) from NOAA ERSSTv5
monthly SST, 1901-2020, following the source paper's stated definitions:

  NINO3.4 = SST anomaly averaged over 120-170W, 5S-5N
  DMI     = SST anomaly averaged over 50-70E, 10S-0  (west box)
            minus SST anomaly averaged over 90-110E, 10S-10N  (east box)

Anomaly = deviation at each grid point from that grid point's local monthly
climatology over the 1901-2020 base period (i.e. all Januaries averaged
together, all Februaries, etc., same convention as the rainfall-side
scripts in this project). Box averages are area (cos-latitude) weighted -
not specified explicitly in the source text, but standard practice for SST
indices like these and the boxes span high-enough latitudes (up to 10-20
degrees) that it's not negligible the way it was for the narrow near-
equatorial rainy-day work elsewhere in this project.

Monthly index values are then restricted to JJAS (Jun-Sep) and averaged
within each year to give one JJAS value per index per year, matching the
paper's stated final step.

ERSSTv5 longitude is 0-360, not -180/180: 120-170W becomes 190-240E.
"""
import ssl
import certifi
import os
import xarray as xr
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.signal import detrend as scipy_detrend

_orig_create_default_context = ssl.create_default_context


def _certifi_default_context(*args, **kwargs):
    if 'cafile' not in kwargs and 'capath' not in kwargs and 'cadata' not in kwargs:
        kwargs['cafile'] = certifi.where()
    return _orig_create_default_context(*args, **kwargs)


ssl.create_default_context = _certifi_default_context

ds = xr.open_dataset('data/sst/ersst.v5.mnmean.nc')
sst = ds['sst'].sel(time=slice('1901-01-01', '2020-12-31'))
print(f"SST record: {sst.time.values[0]} to {sst.time.values[-1]} ({sst.sizes['time']} months)")

climatology = sst.groupby('time.month').mean('time', skipna=True)
anomaly = sst.groupby('time.month') - climatology


def box_mean(field, lon_range, lat_range):
    # lat is descending (88 -> -88) in this file, so slice(north, south).
    box = field.sel(lon=slice(*lon_range), lat=slice(*lat_range))
    weights = np.cos(np.deg2rad(box.lat))
    return box.weighted(weights).mean(dim=['lat', 'lon'], skipna=True)


nino34_monthly = box_mean(anomaly, (190, 240), (5, -5))
dmi_west_monthly = box_mean(anomaly, (50, 70), (0, -10))
dmi_east_monthly = box_mean(anomaly, (90, 110), (10, -10))
dmi_monthly = dmi_west_monthly - dmi_east_monthly


def to_jjas_yearly(monthly):
    jjas = monthly.sel(time=monthly['time.month'].isin([6, 7, 8, 9]))
    return jjas.groupby('time.year').mean('time', skipna=True)


nino34_jjas = to_jjas_yearly(nino34_monthly)
dmi_jjas = to_jjas_yearly(dmi_monthly)

years = nino34_jjas['year'].values
df = pd.DataFrame({
    'year': years,
    'nino34_jjas': nino34_jjas.values,
    'dmi_jjas': dmi_jjas.values,
})
df['nino34_jjas_detrended'] = scipy_detrend(df['nino34_jjas'].values, type='linear')
df['dmi_jjas_detrended'] = scipy_detrend(df['dmi_jjas'].values, type='linear')

os.makedirs('data/indices', exist_ok=True)
df.to_csv('data/indices/enso_iod_indices.csv', index=False)
print(f"Saved data/indices/enso_iod_indices.csv ({len(df)} years)")
print(df.describe().loc[['mean', 'std', 'min', 'max']].round(2))

# Sanity check against the source paper: Nino3 vs AIRI ~ -0.53, "virtually
# unchanged" for Nino3.4, so this should land in a similar ballpark.
try:
    airi = pd.read_csv('data/indices/airi_indices.csv').set_index('year')['airi_raw_anomaly_mm_day_detrended']
    common_years = df['year'][df['year'].isin(airi.index)]
    r = np.corrcoef(
        df.set_index('year').loc[common_years, 'nino34_jjas_detrended'],
        airi.loc[common_years],
    )[0, 1]
    print(f"\nSanity check: r(NINO3.4 detrended, AIRI detrended) = {r:.2f} "
          f"(paper reports ~-0.53 for NINO3, 'virtually unchanged' for NINO3.4)")
except FileNotFoundError:
    print("\n(Skipping AIRI sanity check - airi_indices.csv not found)")

# --- Plot ------------------------------------------------------------------
fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)

axes[0].plot(df['year'], df['nino34_jjas'], color='#d62728', linewidth=1)
axes[0].axhline(0, color='black', linewidth=0.6)
axes[0].set_title('NINO3.4 JJAS anomaly (°C)', fontsize=11)
axes[0].grid(True, alpha=0.3)

axes[1].plot(df['year'], df['dmi_jjas'], color='#1f77b4', linewidth=1)
axes[1].axhline(0, color='black', linewidth=0.6)
axes[1].set_title('DMI JJAS anomaly (°C)', fontsize=11)
axes[1].grid(True, alpha=0.3)
axes[1].set_xlabel('Year')

fig.suptitle('NINO3.4 and DMI, JJAS 1901-2020 (from ERSSTv5)', fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig('figures/enso_iod_indices_timeseries.png', dpi=200, bbox_inches='tight')
print('Saved figures/enso_iod_indices_timeseries.png')
