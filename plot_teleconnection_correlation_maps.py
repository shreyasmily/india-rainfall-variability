"""
Grid-point-by-grid-point Pearson correlation maps between 2 SST teleconnection
indices (-NINO3.4, and DMI with the NINO3.4 signal regressed out - see
compute_enso_iod_indices.py) and 3 JJAS rainfall fields (amount, rainy-day
frequency, mean intensity - same per-gridpoint definitions as
compute_airi_indices.py / compute_moron_eof_analysis.py), laid out as a 2x3
grid of maps sharing one colorbar.

Each rainfall field is linearly detrended per grid point (matching this
project's convention elsewhere) before correlating - NOT standardized, since
Pearson r is invariant to that additional step (standardizing would just
rescale each grid point's series by a positive constant, which cannot change
its correlation with anything). The two index series are already detrended in
enso_iod_indices.csv.
"""
import xarray as xr
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from scipy.signal import detrend as scipy_detrend

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


def detrend_field(field):
    # Same NaN-handling pattern as compute_moron_eof_analysis.py: scipy's
    # detrend solves one batched fit across every grid point at once, so NaN
    # cells must be filled before detrending and re-masked after.
    detrended_vals = scipy_detrend(field.fillna(0).values, axis=0, type='linear')
    return xr.DataArray(detrended_vals, dims=field.dims, coords=field.coords).where(valid)


FIELDS = {
    'Amount': detrend_field(seasonal_mean),
    'Frequency': detrend_field(rainy_days_per_gridpoint),
    'Intensity': detrend_field(intensity_per_gridpoint),
}

enso_iod = pd.read_csv('data/indices/enso_iod_indices.csv').set_index('year')
INDICES = {
    '-NINO3.4': enso_iod['neg_nino34_jjas_detrended'],
    'DMI (N3.4 residual)': enso_iod['dmi_n34_residual_detrended'],
}

fig, axes = plt.subplots(
    2, 3, figsize=(17, 11), subplot_kw={'projection': ccrs.PlateCarree()}
)

im = None
for i, (index_name, index_series) in enumerate(INDICES.items()):
    index_da = xr.DataArray(
        index_series.values, dims='year', coords={'year': index_series.index.values}
    )
    for j, (field_name, field) in enumerate(FIELDS.items()):
        ax = axes[i, j]
        ax.set_facecolor('#eaf2f8')

        corr = xr.corr(field, index_da, dim='year')
        im = corr.plot(
            ax=ax, transform=ccrs.PlateCarree(), cmap='RdBu_r',
            vmin=-1, vmax=1, add_colorbar=False,
        )

        ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
        ax.set_extent(DATA_EXTENT, crs=ccrs.PlateCarree())
        gl = ax.gridlines(draw_labels=True, linewidth=0.3, linestyle='--')
        gl.top_labels = False
        gl.right_labels = False
        gl.xlabel_style = {'size': 6}
        gl.ylabel_style = {'size': 6}
        ax.set_xlabel('')
        ax.set_ylabel('')

        if i == 0:
            ax.set_title(field_name, fontsize=12, fontweight='bold')
        else:
            ax.set_title('')
        if j == 0:
            ax.text(
                -0.12, 0.5, index_name, transform=ax.transAxes, fontsize=12,
                fontweight='bold', va='center', ha='center', rotation=90,
            )

fig.subplots_adjust(right=0.9, wspace=0.15, hspace=0.1)
cbar_ax = fig.add_axes([0.92, 0.15, 0.015, 0.7])
cbar = fig.colorbar(im, cax=cbar_ax)
cbar.set_label('Pearson correlation coefficient (r)')

fig.suptitle(
    'Grid-Point Correlation: SST Teleconnection Indices vs. JJAS Rainfall Fields\n'
    '1901-2020, detrended',
    fontsize=14, fontweight='bold',
)
plt.savefig('figures/teleconnection_correlation_maps.png', dpi=200, bbox_inches='tight')
print('Saved figures/teleconnection_correlation_maps.png')
