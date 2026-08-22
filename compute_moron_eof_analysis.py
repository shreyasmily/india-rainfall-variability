"""
EOF analysis (Moron et al. 2017 style) of JJAS standardized anomalies for
three fields: rainfall mean, rainy-day frequency, and mean rainfall intensity
on rainy days. Extracts and plots the first two modes (EOF1/PC1, EOF2/PC2)
for each field.

Field definitions match compute_airi_indices.py exactly (same per-gridpoint,
per-year quantities, same >1mm/day rainy-day threshold). Each grid point's
1901-2020 series is linearly detrended (least-squares trend removed) before
standardizing, matching the source paper's stated methodology (same
detrending already applied for compute_airi_correlation_matrix.py):
    detrended(year, lat, lon) = value(year, lat, lon) - linear_trend(year, lat, lon)
    standardized(year, lat, lon) = (detrended - its mean) / its std
computed separately at each grid point across the record (the mean after
detrending is ~0 by construction, kept explicit for clarity).

EOF decomposition uses cos(latitude) area weighting and fills the invalid
(non-India) domain with 0 before solving, matching the convention in the
companion enso-sst-analysis project's eofAnalysis_fixed.py.

PC1's sign for each variable is flipped, if needed, so it correlates
positively with AIRI's detrended raw-anomaly index
(data/indices/airi_indices.csv, airi_raw_anomaly_mm_day_detrended) - EOF sign
is mathematically arbitrary, so this just fixes the physically intuitive
convention (positive PC1 = wetter/more frequent/more intense than normal).
EOF2 has no equally natural anchor, so its raw solver sign is kept.
"""
import ssl
import certifi
import xarray as xr
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from eofs.xarray import Eof
from scipy.signal import detrend as scipy_detrend

# This machine's Windows certificate store has a cert ssl.create_default_context()
# can't parse. That breaks dask's scheduler-detection (triggered here when the EOF
# solver forces a .compute() on a lazily-loaded array), which imports distributed ->
# tornado, which builds an SSL context at import time. Same fix as fetch_elevation.py.
_orig_create_default_context = ssl.create_default_context


def _certifi_default_context(*args, **kwargs):
    if 'cafile' not in kwargs and 'capath' not in kwargs and 'cadata' not in kwargs:
        kwargs['cafile'] = certifi.where()
    return _orig_create_default_context(*args, **kwargs)


ssl.create_default_context = _certifi_default_context

RAINY_DAY_THRESHOLD = 1  # mm/day, matches compute_airi_indices.py
DATA_EXTENT = [67.0, 90.0, 7.25, 32.75]  # matches other figures in this project

ds = xr.open_dataset('data/rainfall/imd_rain_daily_0p25_monsoon-masked_1901-2020.nc')
precip = ds['precip']
jjas = precip.sel(time=precip['time.month'].isin([6, 7, 8, 9]))
valid = ds['monsoon_mask'].notnull()

seasonal_mean = jjas.groupby('time.year').mean('time')  # rainfall mean, (year, lat, lon)

rainy_mask = jjas > RAINY_DAY_THRESHOLD
rainy_days_per_gridpoint = rainy_mask.groupby('time.year').sum('time').where(valid)          # frequency
intensity_per_gridpoint = jjas.where(rainy_mask).groupby('time.year').mean('time').where(valid)  # intensity


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
    'rainfall_mean': ('Rainfall Mean', standardize(seasonal_mean)),
    'rainy_day_frequency': ('Rainy Day Frequency', standardize(rainy_days_per_gridpoint)),
    'mean_intensity': ('Mean Rainfall Intensity', standardize(intensity_per_gridpoint)),
}

airi = pd.read_csv('data/indices/airi_indices.csv').set_index('year')['airi_raw_anomaly_mm_day_detrended']

lat_vals = ds.lat.values
lon_vals = ds.lon.values
weights_2d = np.cos(np.deg2rad(lat_vals))
weights_2d = np.tile(weights_2d[:, np.newaxis], (1, len(lon_vals)))


def render(varname, label, field):
    field_filled = field.where(valid).fillna(0).rename({'year': 'time'})
    solver = Eof(field_filled, weights=weights_2d)
    eofs_ = solver.eofs(neofs=2)
    pcs = solver.pcs(npcs=2)
    variance = solver.varianceFraction(neigs=2)

    pc1_vals = pcs[:, 0].values
    r = np.corrcoef(pc1_vals, airi.reindex(field_filled['time'].values).values)[0, 1]
    sign1 = 1 if r >= 0 else -1
    print(f"{varname}: EOF1 {float(variance[0]) * 100:.1f}% var (r with AIRI: {r * sign1:+.2f} after sign fix), "
          f"EOF2 {float(variance[1]) * 100:.1f}% var")

    eof_data = [eofs_[0] * sign1, eofs_[1]]
    pc_data = [pcs[:, 0] * sign1, pcs[:, 1]]
    var_data = [float(variance[0]), float(variance[1])]
    years = field_filled['time'].values

    fig = plt.figure(figsize=(14, 9))
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.4, wspace=0.3)

    for i in range(2):
        ax_map = fig.add_subplot(gs[i, 0], projection=ccrs.PlateCarree())
        ax_map.set_facecolor('#eaf2f8')

        eof_plot = eof_data[i].where(valid)
        vmax = float(np.abs(eof_plot).quantile(0.99))
        eof_plot.plot(
            ax=ax_map, transform=ccrs.PlateCarree(), cmap='RdBu_r',
            vmin=-vmax, vmax=vmax, add_colorbar=True,
            cbar_kwargs={'label': 'EOF loading (unitless)', 'shrink': 0.8},
        )
        ax_map.add_feature(cfeature.COASTLINE, linewidth=0.8)
        ax_map.set_extent(DATA_EXTENT, crs=ccrs.PlateCarree())
        gl = ax_map.gridlines(draw_labels=True, linewidth=0.3, linestyle='--')
        gl.top_labels = False
        gl.right_labels = False
        gl.xlabel_style = {'size': 7}
        gl.ylabel_style = {'size': 7}
        ax_map.set_xlabel('')
        ax_map.set_ylabel('')
        ax_map.set_title(f'EOF{i + 1} — {var_data[i] * 100:.1f}% variance', fontsize=10)

        ax_ts = fig.add_subplot(gs[i, 1])
        pc = pc_data[i].values
        ax_ts.plot(years, pc, color='steelblue', linewidth=0.9)
        ax_ts.axhline(0, color='black', linewidth=0.5)
        ax_ts.fill_between(years, pc, 0, where=(pc > 0), color='red', alpha=0.3)
        ax_ts.fill_between(years, pc, 0, where=(pc < 0), color='blue', alpha=0.3)
        ax_ts.set_title(f'PC{i + 1} Time Series', fontsize=10)
        ax_ts.set_ylabel('Amplitude')
        ax_ts.grid(True, alpha=0.3)

    fig.suptitle(
        f'EOF Analysis: JJAS Standardized {label} Anomalies, 1901-2020 (detrended)\n'
        f'(cos-lat weighted, {RAINY_DAY_THRESHOLD}mm/day rainy-day threshold where applicable)',
        fontsize=12, fontweight='bold',
    )
    plt.savefig(f'figures/eof_{varname}.png', dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved figures/eof_{varname}.png')


for varname, (label, field) in FIELDS.items():
    render(varname, label, field)
