"""
Detrended mean JJAS rainfall anomalies for 3 sub-India regions: Central
Monsoon Zone (CMZ), Western Ghats (WG), and Southeast India (SEI).

Region definitions (from the user, not independently derived):
  - CMZ: the band between two irregular north/south boundary curves from
    Gadgil et al. (2019) Fig. 3(a), each varying with longitude (not a
    lat/lon box). At each grid point's longitude, the north and south limits
    are linearly interpolated from the boundary vertices below. This band
    does NOT extend into northeast India - it's explicitly capped at
    CMZ_LON_MAX = 88.5E (a grid point east of that is never in CMZ,
    regardless of latitude), rather than holding the north curve's last
    vertex flat past its endpoint. The WEST side has no such cap: west of
    the curves' first vertices (72.2E south / 73.2E north), their
    interpolated latitude limits hold flat at each curve's westernmost
    value, and the region is bounded there only by the dataset's own
    `valid` (monsoon_mask) domain - i.e. India's actual western border with
    Pakistan and the Arabian Sea coastline in Rajasthan/Gujarat, not an
    arbitrary straight longitude cutoff. A grid point is in CMZ if its
    longitude is <= CMZ_LON_MAX AND its latitude falls between the
    interpolated south and north limits, intersected with `valid`.
  - WG: grid points with climatological mean JJAS rainy days (>1mm/day,
    matching this project's threshold convention) exceeding 100 days.
    Checked empirically (see conversation) that this threshold alone, with
    no additional geographic restriction, is already confined entirely to
    the Western Ghats coastal strip (lon 73-76.75E, lat 9.5-19N) - no
    separate central-India cluster - so no extra bounding box was needed.
  - SEI: east of the WG boundary and south of 18N. Operationalized as: for
    each latitude row, find WG's easternmost longitude at that row (the
    coastal band's inland edge); SEI is every valid grid point east of that
    edge, south of 18N. Rows south of 18N with no WG cells (shouldn't occur
    given WG's actual extent above, but handled defensively) fall back to
    the westernmost longitude in the valid domain, so SEI doesn't silently
    drop that row.

"Mean JJAS rainfall anomaly" for each region = the region's unweighted
spatial average of the per-gridpoint JJAS seasonal-mean anomaly
(seasonal_mean - climatological mean, same quantities as compute_airi_indices.py),
detrended. Detrending commutes with (linear) spatial averaging and with
subtracting a per-point constant climatology, so this is computed as: average
the raw per-year regional series first (simpler, avoids NaN issues in
per-gridpoint detrending), then detrend that single 120-value series - exactly
equivalent to detrending each grid point first, then averaging.
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
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from scipy.signal import detrend as scipy_detrend

_orig_create_default_context = ssl.create_default_context


def _certifi_default_context(*args, **kwargs):
    if 'cafile' not in kwargs and 'capath' not in kwargs and 'cadata' not in kwargs:
        kwargs['cafile'] = certifi.where()
    return _orig_create_default_context(*args, **kwargs)


ssl.create_default_context = _certifi_default_context

RAINY_DAY_THRESHOLD = 1  # mm/day, matches compute_airi_indices.py
WG_RAINY_DAYS_THRESHOLD = 100
DATA_EXTENT = [67.0, 90.0, 7.25, 32.75]

# (lon, lat) pairs, Gadgil et al. (2019) Fig. 3(a). Capped east of CMZ_LON_MAX
# (does not extend into northeast India); open on the west, bounded only by
# `valid` (India's actual border) - see CMZ_LON_MAX below.
NORTH_BOUNDARY = [
    (73.2, 29.5), (73.5, 29.4), (73.9, 29.2), (74.3, 29.0), (74.6, 28.8), (74.9, 28.7),
    (75.2, 28.5), (75.7, 28.3), (76.0, 28.0), (76.3, 27.8), (76.9, 27.6), (77.2, 27.4),
    (77.5, 27.1), (77.8, 26.9), (78.2, 26.8), (78.5, 26.6), (79.0, 26.4), (79.6, 26.1),
    (79.9, 26.0), (80.4, 25.8), (80.9, 25.4), (81.3, 25.2), (81.7, 25.0), (82.0, 24.8),
    (82.3, 24.6), (82.7, 24.5), (83.0, 24.4), (83.3, 24.3), (83.6, 24.2), (84.1, 24.0),
    (84.5, 24.0), (85.8, 23.9), (86.2, 23.8), (86.5, 23.8), (86.9, 23.9), (87.5, 23.9),
    (87.8, 23.9), (88.1, 23.9), (88.5, 23.9),
]
SOUTH_BOUNDARY = [
    (72.2, 22.0), (72.5, 22.2), (73.8, 22.3), (74.2, 22.1), (74.5, 21.9), (74.8, 21.7),
    (75.1, 21.3), (75.4, 21.0), (75.7, 20.7), (76.1, 20.4), (76.7, 20.2), (77.0, 20.0),
    (77.4, 19.9), (77.7, 19.7), (78.2, 19.5), (78.5, 19.4), (78.8, 19.2), (79.5, 19.0),
    (79.8, 19.0), (80.7, 18.8), (81.1, 18.8), (81.5, 18.8), (81.8, 18.8), (83.1, 18.7),
    (83.9, 18.8), (84.5, 19.0), (84.9, 19.2), (87.4, 21.6), (87.7, 21.7), (88.3, 21.8),
]
CMZ_LON_MAX = 88.5  # east cap only; west side bounded by `valid` (India's own border)
SEI_LAT_LIMIT = 18.0

ds = xr.open_dataset('data/rainfall/imd_rain_daily_0p25_monsoon-masked_1901-2020.nc')
precip = ds['precip']
jjas = precip.sel(time=precip['time.month'].isin([6, 7, 8, 9]))
valid = ds['monsoon_mask'].notnull()
n_years = len(np.unique(jjas['time.year'].values))

seasonal_mean = jjas.groupby('time.year').mean('time')  # (year, lat, lon)

lat2d, lon2d = xr.broadcast(ds.lat, ds.lon)

# --- CMZ ---------------------------------------------------------------------
north_lons, north_lats = zip(*sorted(NORTH_BOUNDARY))
south_lons, south_lats = zip(*sorted(SOUTH_BOUNDARY))
north_limit = xr.apply_ufunc(np.interp, lon2d, kwargs={'xp': north_lons, 'fp': north_lats})
south_limit = xr.apply_ufunc(np.interp, lon2d, kwargs={'xp': south_lons, 'fp': south_lats})
cmz_mask = valid & (lon2d <= CMZ_LON_MAX) & (lat2d >= south_limit) & (lat2d <= north_limit)

# --- WG ------------------------------------------------------------------
rainy_mask = jjas > RAINY_DAY_THRESHOLD
mean_rainy_days = (rainy_mask.sum(dim='time') / n_years).where(valid)
wg_mask = valid & (mean_rainy_days > WG_RAINY_DAYS_THRESHOLD)

# --- SEI: east of WG's per-latitude eastern edge, south of 18N -----------
wg_lon_where_true = lon2d.where(wg_mask)
wg_east_edge_per_lat = wg_lon_where_true.max(dim='lon', skipna=True)  # (lat,), NaN where WG has no cells that row
fallback_lon = float(lon2d.where(valid).min())
wg_east_edge_per_lat = wg_east_edge_per_lat.fillna(fallback_lon)
sei_mask = valid & (lat2d < SEI_LAT_LIMIT) & (lon2d > wg_east_edge_per_lat)

MASKS = {'CMZ': cmz_mask, 'WG': wg_mask, 'SEI': sei_mask}
for name, mask in MASKS.items():
    print(f"{name}: {int(mask.sum())} grid points")

# --- Regional indices: raw mean JJAS anomaly per year, then detrended ----
clim_mean = seasonal_mean.mean('year', skipna=True)
anomaly = seasonal_mean - clim_mean

years = seasonal_mean['year'].values
results = {'year': years}
for name, mask in MASKS.items():
    raw_series = anomaly.where(mask).mean(dim=['lat', 'lon'], skipna=True).values
    detrended_series = scipy_detrend(raw_series, type='linear')
    results[f'{name.lower()}_mean_anomaly_mm_day'] = raw_series
    results[f'{name.lower()}_mean_anomaly_mm_day_detrended'] = detrended_series

df = pd.DataFrame(results)
os.makedirs('data/indices', exist_ok=True)
df.to_csv('data/indices/subregion_indices.csv', index=False)
print(f"Saved data/indices/subregion_indices.csv ({len(df)} years)")

# --- Diagnostic map: verify the 3 masks look right ------------------------
fig, ax = plt.subplots(figsize=(8, 9), subplot_kw={'projection': ccrs.PlateCarree()})
ax.set_facecolor('#eaf2f8')

region_id = xr.zeros_like(lat2d, dtype=float)
region_id = region_id.where(~cmz_mask, 1)
region_id = region_id.where(~wg_mask, 2)
region_id = region_id.where(~sei_mask, 3)
region_id = region_id.where(valid)

from matplotlib.colors import ListedColormap, BoundaryNorm
cmap = ListedColormap(['#f0f0f0', '#d62728', '#ff7f0e', '#2ca02c'])
norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5], cmap.N)
region_id.plot(
    ax=ax, transform=ccrs.PlateCarree(), cmap=cmap, norm=norm,
    add_colorbar=False,
)
ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
ax.set_extent(DATA_EXTENT, crs=ccrs.PlateCarree())
gl = ax.gridlines(draw_labels=True, linewidth=0.3, linestyle='--')
gl.top_labels = False
gl.right_labels = False
ax.set_xlabel('')
ax.set_ylabel('')

import matplotlib.patches as mpatches
legend_handles = [
    mpatches.Patch(color='#f0f0f0', label='Rest of valid domain', ec='black', linewidth=0.3),
    mpatches.Patch(color='#d62728', label='CMZ'),
    mpatches.Patch(color='#ff7f0e', label='WG'),
    mpatches.Patch(color='#2ca02c', label='SEI'),
]
ax.legend(handles=legend_handles, loc='upper right', fontsize=8, framealpha=0.9)
ax.set_title('Sub-India Region Masks: CMZ, WG, SEI', fontsize=12, fontweight='bold')

plt.tight_layout()
plt.savefig('figures/subregion_masks.png', dpi=200, bbox_inches='tight')
print('Saved figures/subregion_masks.png')
