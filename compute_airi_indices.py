"""
All-India Rainfall Index (AIRI) and six alternate all-India measures of JJAS
rainfall variability, following the definitions below (the 1st, 3rd, and 4th
were introduced by Moron et al.):

  0. AIRI            - average raw JJAS rainfall anomaly across all grid points
  1. Standardized    - average STANDARDIZED anomaly (raw anomaly / local std)
  2. N positive      - number of grid points with a positive local anomaly
  3. Mean rainy days - avg across grid points of that year's rainy-day count
  4. Mean intensity  - avg across grid points of that year's mean rainfall
                        rate on rainy days
  5. Mean pos anomaly - mean anomaly, restricted to grid points where the
                         anomaly is positive (varies which points each year)
  6. Mean neg anomaly - mean anomaly, restricted to grid points where the
                         anomaly is negative

All are per-year values (a 120-year time series each), not spatial maps -
they measure how JJAS rainfall variability expresses itself at the all-India
scale, year to year.

"Anomaly" = a year's JJAS seasonal mean (mm/day) at a grid point, minus that
grid point's 1901-2020 climatological JJAS mean (same quantities computed in
plot_jjas_climatology.py). Rainy-day threshold for measures 3-4: >1 mm/day.

All "average across grid points" is a SIMPLE (unweighted) mean over valid
India grid points, matching the literal definitions above - not area/cos(lat)
weighted like the EOF analysis in the companion enso-sst-analysis project.

Each measure also gets a "_detrended" column: the same 120-year series with
its 1901-2020 linear least-squares trend subtracted off, matching the source
paper's stated methodology of detrending each series before cross-correlating
them (see compute_airi_correlation_matrix.py, which correlates these columns,
not the raw ones).
"""
import os
import xarray as xr
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.signal import detrend

RAINY_DAY_THRESHOLD = 1  # mm/day, for measures 3 and 4

ds = xr.open_dataset('data/rainfall/imd_rain_daily_0p25_monsoon-masked_1901-2020.nc')
precip = ds['precip']
jjas = precip.sel(time=precip['time.month'].isin([6, 7, 8, 9]))
valid = ds['monsoon_mask'].notnull()

# --- Anomaly-based measures -------------------------------------------------
seasonal_mean = jjas.groupby('time.year').mean('time')          # (year, lat, lon), mm/day
clim_mean = seasonal_mean.mean('year')
clim_std = seasonal_mean.std('year', ddof=1)
anomaly = seasonal_mean - clim_mean                              # (year, lat, lon)
standardized_anomaly = anomaly / clim_std

airi_raw = anomaly.mean(dim=['lat', 'lon'], skipna=True)
airi_standardized = standardized_anomaly.mean(dim=['lat', 'lon'], skipna=True)
n_positive = (anomaly > 0).sum(dim=['lat', 'lon'])
mean_pos_anomaly = anomaly.where(anomaly > 0).mean(dim=['lat', 'lon'], skipna=True)
mean_neg_anomaly = anomaly.where(anomaly < 0).mean(dim=['lat', 'lon'], skipna=True)

# --- Rainy-day-based measures -----------------------------------------------
# .sum()/.mean() over a boolean mask don't propagate NaN for out-of-domain
# cells (False.sum() = 0, not NaN), so those grid points must be masked out
# explicitly before spatially averaging - otherwise they'd silently count as
# "0 rainy days" instead of being excluded.
rainy_mask = jjas > RAINY_DAY_THRESHOLD
rainy_days_per_gridpoint = rainy_mask.groupby('time.year').sum('time').where(valid)
intensity_per_gridpoint = jjas.where(rainy_mask).groupby('time.year').mean('time').where(valid)

mean_rainy_days = rainy_days_per_gridpoint.mean(dim=['lat', 'lon'], skipna=True)
mean_intensity = intensity_per_gridpoint.mean(dim=['lat', 'lon'], skipna=True)

# --- Assemble ----------------------------------------------------------------
years = seasonal_mean['year'].values
df = pd.DataFrame({
    'year': years,
    'airi_raw_anomaly_mm_day': airi_raw.values,
    'airi_standardized_anomaly': airi_standardized.values,
    'n_positive_anomaly_gridpoints': n_positive.values,
    'mean_rainy_days': mean_rainy_days.values,
    'mean_intensity_rainy_days_mm_day': mean_intensity.values,
    'mean_positive_anomaly_mm_day': mean_pos_anomaly.values,
    'mean_negative_anomaly_mm_day': mean_neg_anomaly.values,
})

index_cols = [c for c in df.columns if c != 'year']
for col in index_cols:
    df[f'{col}_detrended'] = detrend(df[col].values, type='linear')

os.makedirs('data/indices', exist_ok=True)
df.to_csv('data/indices/airi_indices.csv', index=False)
print(f"Saved data/indices/airi_indices.csv ({len(df)} years, {len(index_cols)} measures + detrended versions)")
print(df[index_cols].describe().loc[['mean', 'std', 'min', 'max']].round(2))

# --- Plot ----------------------------------------------------------------
fig, axes = plt.subplots(4, 2, figsize=(13, 14), sharex=True)

panels = [
    ('airi_raw_anomaly_mm_day', 'AIRI: avg raw anomaly (mm/day)', True),
    ('airi_standardized_anomaly', 'Avg standardized anomaly (unitless)', True),
    ('n_positive_anomaly_gridpoints', 'N grid points with positive anomaly', False),
    ('mean_rainy_days', f'Avg rainy days/season (>{RAINY_DAY_THRESHOLD}mm/day)', False),
    ('mean_intensity_rainy_days_mm_day', 'Avg intensity on rainy days (mm/day)', False),
    ('mean_positive_anomaly_mm_day', 'Mean anomaly, positive-anomaly points (mm/day)', True),
    ('mean_negative_anomaly_mm_day', 'Mean anomaly, negative-anomaly points (mm/day)', True),
]

for ax, (col, title, zero_line) in zip(axes.flat, panels):
    ax.plot(df['year'], df[col], color='#4c72b0', linewidth=1)
    if zero_line:
        ax.axhline(0, color='black', linewidth=0.6)
    ax.set_title(title, fontsize=10)
    ax.grid(True, alpha=0.3)

axes.flat[-1].axis('off')
axes.flat[-1].text(
    0.02, 0.8,
    f'Rainy-day threshold: >{RAINY_DAY_THRESHOLD} mm/day (measures 3-4 only)\n'
    'All spatial averages are simple (unweighted) means\n'
    'over valid India grid points.',
    fontsize=8, va='top', transform=axes.flat[-1].transAxes,
)

fig.suptitle('All-India JJAS Rainfall Variability: AIRI + 6 Alternate Measures, 1901-2020', fontsize=13, fontweight='bold')
plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig('figures/airi_indices_timeseries.png', dpi=200, bbox_inches='tight')
print('Saved figures/airi_indices_timeseries.png')
