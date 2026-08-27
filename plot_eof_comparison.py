"""
Side-by-side comparison of 4 EOF spatial patterns from the Moron et al. (2017)
style analysis in compute_moron_eof_analysis.py: rainfall mean EOF1 and EOF2,
plus rainy-day-frequency EOF1 and mean-intensity EOF1 (their dominant modes).

Recomputes the same standardized (linearly detrended per grid point, then
standardized - see compute_moron_eof_analysis.py) fields and EOF solves as
compute_moron_eof_analysis.py (see that script for full methodology notes) -
this one just lays out a specific subset of spatial patterns together for
direct visual comparison, without the PC time series panels.
"""
import ssl
import certifi
import xarray as xr
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
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
DATA_EXTENT = [67.0, 90.0, 7.25, 32.75]

ds = xr.open_dataset('data/rainfall/imd_rain_daily_0p25_monsoon-masked_1901-2020.nc')
precip = ds['precip']
jjas = precip.sel(time=precip['time.month'].isin([6, 7, 8, 9]))
valid = ds['monsoon_mask'].notnull()

seasonal_mean = jjas.groupby('time.year').mean('time')
rainy_mask = jjas > RAINY_DAY_THRESHOLD
rainy_days_per_gridpoint = rainy_mask.groupby('time.year').sum('time').where(valid)
intensity_per_gridpoint = jjas.where(rainy_mask).groupby('time.year').mean('time').where(valid)


def standardize(field):
    # scipy.signal.detrend solves a single batched least-squares fit across
    # every (lat,lon) column at once - a NaN anywhere fails the whole batch,
    # not just that column. Fill NaN cells with a placeholder to detrend
    # (their output is meaningless but gets discarded next), then restore NaN
    # outside India so climatological mean/std below stay correct.
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

# Target sign of PC1's correlation with AIRI, per variable - see
# compute_moron_eof_analysis.py for why mean_intensity is negative (matches
# the source paper's published matrix, where PC1-intensity anti-correlates
# with AIRI while the other two are strongly positively correlated).
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

fig.suptitle(
    'JJAS Standardized Anomaly EOF Patterns, 1901-2020 (detrended)\n(Moron et al. 2017 style, cos-lat weighted)',
    fontsize=13, fontweight='bold',
)
plt.tight_layout(rect=[0, 0, 1, 0.94])
plt.savefig('figures/eof_comparison.png', dpi=200, bbox_inches='tight')
print('Saved figures/eof_comparison.png')
