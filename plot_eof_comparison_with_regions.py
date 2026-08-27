"""
Same 4-panel EOF spatial pattern comparison as plot_eof_comparison.py
(rainfall mean EOF1+EOF2, rainy-day-frequency EOF1, mean-intensity EOF1),
with the CMZ/WG/SEI sub-India region boundaries (see
compute_subregion_indices.py) outlined on top, so a reader can see how each
mode's spatial pattern lines up with the 3 analysis regions.

Saved as a SEPARATE figure (figures/eof_comparison_with_regions.png) rather
than overwriting eof_comparison.png, so both the plain and region-annotated
versions are available to choose between.

Recomputes the EOF fields (see plot_eof_comparison.py) and the region masks
(see compute_subregion_indices.py) independently rather than importing them,
consistent with this project's standalone-script convention.
"""
import ssl
import certifi
import xarray as xr
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from eofs.xarray import Eof
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

# (lon, lat) pairs, Gadgil et al. (2019) Fig. 3(a) - see compute_subregion_indices.py
NORTH_BOUNDARY = [
    (74.4, 31.8), (75.6, 31.5), (76.4, 30.8), (77.1, 30.3), (77.6, 29.6), (78.2, 29.2),
    (78.7, 28.7), (79.5, 28.2), (80.3, 27.7), (80.9, 27.2), (81.5, 26.5), (82.3, 26.0),
    (83.1, 25.8), (83.9, 25.4), (84.7, 25.3), (85.5, 25.1), (86.3, 25.0), (87.1, 25.1),
    (87.9, 25.1), (88.3, 25.2), (88.6, 25.9), (89.1, 27.1), (92.2, 27.1), (92.6, 26.8),
    (93.0, 26.6), (93.4, 26.3), (93.8, 26.1), (94.2, 25.8), (94.6, 25.5), (94.9, 25.4),
]
SOUTH_BOUNDARY = [
    (72.2, 22.0), (72.5, 22.2), (73.8, 22.3), (74.2, 22.1), (74.5, 21.9), (74.8, 21.7),
    (75.1, 21.3), (75.4, 21.0), (75.7, 20.7), (76.1, 20.4), (76.7, 20.2), (77.0, 20.0),
    (77.4, 19.9), (77.7, 19.7), (78.2, 19.5), (78.5, 19.4), (78.8, 19.2), (79.5, 19.0),
    (79.8, 19.0), (80.7, 18.8), (81.1, 18.8), (81.5, 18.8), (81.8, 18.8), (83.1, 18.7),
    (83.9, 18.8), (84.5, 19.0), (84.9, 19.2), (87.4, 21.6), (87.7, 21.7), (88.3, 21.8),
]
SEI_LAT_LIMIT = 18.0
REGION_COLORS = {'CMZ': '#d62728', 'WG': '#ff7f0e', 'SEI': '#2ca02c'}

ds = xr.open_dataset('data/rainfall/imd_rain_daily_0p25_monsoon-masked_1901-2020.nc')
precip = ds['precip']
jjas = precip.sel(time=precip['time.month'].isin([6, 7, 8, 9]))
valid = ds['monsoon_mask'].notnull()
n_years = len(np.unique(jjas['time.year'].values))

lat2d, lon2d = xr.broadcast(ds.lat, ds.lon)

# --- Region masks (see compute_subregion_indices.py for full explanation) ---
north_lons, north_lats = zip(*sorted(NORTH_BOUNDARY))
south_lons, south_lats = zip(*sorted(SOUTH_BOUNDARY))
north_limit = xr.apply_ufunc(np.interp, lon2d, kwargs={'xp': north_lons, 'fp': north_lats})
south_limit = xr.apply_ufunc(np.interp, lon2d, kwargs={'xp': south_lons, 'fp': south_lats})
cmz_mask = valid & (lat2d >= south_limit) & (lat2d <= north_limit)

rainy_mask_all = jjas > RAINY_DAY_THRESHOLD
mean_rainy_days = (rainy_mask_all.sum(dim='time') / n_years).where(valid)
wg_mask = valid & (mean_rainy_days > WG_RAINY_DAYS_THRESHOLD)

wg_lon_where_true = lon2d.where(wg_mask)
wg_east_edge_per_lat = wg_lon_where_true.max(dim='lon', skipna=True)
fallback_lon = float(lon2d.where(valid).min())
wg_east_edge_per_lat = wg_east_edge_per_lat.fillna(fallback_lon)
sei_mask = valid & (lat2d < SEI_LAT_LIMIT) & (lon2d > wg_east_edge_per_lat)

REGION_MASKS = {'CMZ': cmz_mask, 'WG': wg_mask, 'SEI': sei_mask}

# --- EOF fields (see plot_eof_comparison.py) ------------------------------
seasonal_mean = jjas.groupby('time.year').mean('time')
rainy_days_per_gridpoint = rainy_mask_all.groupby('time.year').sum('time').where(valid)
intensity_per_gridpoint = jjas.where(rainy_mask_all).groupby('time.year').mean('time').where(valid)


def standardize(field):
    detrended_vals = scipy_detrend(field.fillna(0).values, axis=0, type='linear')
    detrended = xr.DataArray(detrended_vals, dims=field.dims, coords=field.coords).where(valid)
    clim_mean = detrended.mean('year', skipna=True)
    clim_std = detrended.std('year', ddof=1, skipna=True)
    return (detrended - clim_mean) / clim_std


FIELDS = {
    'rainfall_mean': standardize(seasonal_mean),
    'rainy_day_frequency': standardize(rainy_days_per_gridpoint),
    'mean_intensity': standardize(intensity_per_gridpoint),
}

airi = pd.read_csv('data/indices/airi_indices.csv').set_index('year')['airi_raw_anomaly_mm_day_detrended']
TARGET_SIGN = {'rainfall_mean': 1, 'rainy_day_frequency': 1, 'mean_intensity': -1}

lat_vals = ds.lat.values
lon_vals = ds.lon.values
weights_2d = np.cos(np.deg2rad(lat_vals))
weights_2d = np.tile(weights_2d[:, np.newaxis], (1, len(lon_vals)))


def solve(field, varname):
    field_filled = field.where(valid).fillna(0).rename({'year': 'time'})
    solver = Eof(field_filled, weights=weights_2d)
    eofs_ = solver.eofs(neofs=2)
    pcs = solver.pcs(npcs=2)
    variance = solver.varianceFraction(neigs=2)
    r = np.corrcoef(pcs[:, 0].values, airi.reindex(field_filled['time'].values).values)[0, 1]
    natural_sign = 1 if r >= 0 else -1
    sign1 = natural_sign * TARGET_SIGN[varname]
    return eofs_[0] * sign1, float(variance[0]), eofs_[1], float(variance[1])


rf_eof1, rf_var1, rf_eof2, rf_var2 = solve(FIELDS['rainfall_mean'], 'rainfall_mean')
freq_eof1, freq_var1, _, _ = solve(FIELDS['rainy_day_frequency'], 'rainy_day_frequency')
int_eof1, int_var1, _, _ = solve(FIELDS['mean_intensity'], 'mean_intensity')

panels = [
    (rf_eof1, rf_var1, 'Rainfall Mean — EOF1'),
    (rf_eof2, rf_var2, 'Rainfall Mean — EOF2'),
    (freq_eof1, freq_var1, 'Rainy Day Frequency — EOF1'),
    (int_eof1, int_var1, 'Mean Intensity — EOF1'),
]

fig, axes = plt.subplots(2, 2, figsize=(13, 12), subplot_kw={'projection': ccrs.PlateCarree()})

for ax, (eof_data, var, title) in zip(axes.flat, panels):
    ax.set_facecolor('#eaf2f8')
    eof_plot = eof_data.where(valid)
    vmax = float(np.abs(eof_plot).quantile(0.99))
    eof_plot.plot(
        ax=ax, transform=ccrs.PlateCarree(), cmap='RdBu_r',
        vmin=-vmax, vmax=vmax, add_colorbar=True,
        cbar_kwargs={'label': 'EOF loading (unitless)', 'shrink': 0.8},
    )

    for name, mask in REGION_MASKS.items():
        mask_float = mask.astype(float)
        mask_float.plot.contour(
            ax=ax, transform=ccrs.PlateCarree(), levels=[0.5],
            colors=REGION_COLORS[name], linewidths=1.6, add_colorbar=False,
        )

    ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
    ax.set_extent(DATA_EXTENT, crs=ccrs.PlateCarree())
    gl = ax.gridlines(draw_labels=True, linewidth=0.3, linestyle='--')
    gl.top_labels = False
    gl.right_labels = False
    gl.xlabel_style = {'size': 7}
    gl.ylabel_style = {'size': 7}
    ax.set_xlabel('')
    ax.set_ylabel('')
    ax.set_title(f'{title} ({var * 100:.1f}% variance)', fontsize=10)

legend_handles = [
    mlines.Line2D([], [], color=REGION_COLORS[name], linewidth=1.6, label=name)
    for name in REGION_MASKS
]
fig.legend(handles=legend_handles, loc='upper center', ncol=3, fontsize=9,
           bbox_to_anchor=(0.5, 0.965), frameon=False)

fig.suptitle(
    'JJAS Standardized Anomaly EOF Patterns, 1901-2020 (detrended)\n'
    '(Moron et al. 2017 style, cos-lat weighted) — with CMZ/WG/SEI region outlines',
    fontsize=13, fontweight='bold', y=1.0,
)
plt.tight_layout(rect=[0, 0, 1, 0.92])
plt.savefig('figures/eof_comparison_with_regions.png', dpi=200, bbox_inches='tight')
print('Saved figures/eof_comparison_with_regions.png')
