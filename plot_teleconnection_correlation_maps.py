"""
Grid-point-by-grid-point Pearson correlation maps between 2 SST teleconnection
indices (-NINO3.4, and DMI with the NINO3.4 signal regressed out - see
compute_enso_iod_indices.py) and 3 JJAS rainfall fields (amount, rainy-day
frequency, mean intensity - same per-gridpoint definitions as
compute_airi_indices.py / compute_moron_eof_analysis.py), laid out as a 2x3
grid of maps sharing one colorbar, with the CMZ/WG/SEI sub-India region
boundaries (see compute_subregion_indices.py) outlined on top.

Each rainfall field is linearly detrended per grid point (matching this
project's convention elsewhere) before correlating - NOT standardized, since
Pearson r is invariant to that additional step (standardizing would just
rescale each grid point's series by a positive constant, which cannot change
its correlation with anything). The two index series are already detrended in
enso_iod_indices.csv.

The shared colorbar range is NOT fixed to [-1, 1] - it's set to
[-vmax, vmax] where vmax is the largest |r| actually plotted across all 6
panels, so the color scale isn't wasted on correlation magnitudes that never
occur (these grid-point teleconnection correlations rarely exceed ~0.6-0.7),
which makes spatial contrast between regions easier to see.

Recomputes the region masks (see compute_subregion_indices.py /
plot_eof_comparison_with_regions.py) independently rather than importing
them, consistent with this project's standalone-script convention.
"""
import xarray as xr
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from scipy.signal import detrend as scipy_detrend

RAINY_DAY_THRESHOLD = 1  # mm/day, matches compute_airi_indices.py
WG_RAINY_DAYS_THRESHOLD = 100
DATA_EXTENT = [67.0, 90.0, 7.25, 32.75]

# (lon, lat) pairs, Gadgil et al. (2019) Fig. 3(a) - see compute_subregion_indices.py.
# Capped east of CMZ_LON_MAX (does not extend into northeast India); open on
# the west, bounded only by `valid` (India's actual border with Pakistan and
# the Arabian Sea coastline in Rajasthan/Gujarat).
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
REGION_COLORS = {'CMZ': '#2ca02c', 'WG': '#ff7f0e', 'SEI': '#9467bd'}

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
cmz_mask = valid & (lon2d <= CMZ_LON_MAX) & (lat2d >= south_limit) & (lat2d <= north_limit)

rainy_mask_all = jjas > RAINY_DAY_THRESHOLD
mean_rainy_days = (rainy_mask_all.sum(dim='time') / n_years).where(valid)
wg_mask = valid & (mean_rainy_days > WG_RAINY_DAYS_THRESHOLD)

wg_lon_where_true = lon2d.where(wg_mask)
wg_east_edge_per_lat = wg_lon_where_true.max(dim='lon', skipna=True)
fallback_lon = float(lon2d.where(valid).min())
wg_east_edge_per_lat = wg_east_edge_per_lat.fillna(fallback_lon)
sei_mask = valid & (lat2d < SEI_LAT_LIMIT) & (lon2d > wg_east_edge_per_lat)

REGION_MASKS = {'CMZ': cmz_mask, 'WG': wg_mask, 'SEI': sei_mask}

# --- Rainfall fields --------------------------------------------------------
seasonal_mean = jjas.groupby('time.year').mean('time')
rainy_days_per_gridpoint = rainy_mask_all.groupby('time.year').sum('time').where(valid)
intensity_per_gridpoint = jjas.where(rainy_mask_all).groupby('time.year').mean('time').where(valid)


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

# --- Compute all 6 correlation fields up front, so the shared colorbar can
# be scaled to the actual range of |r| plotted instead of the full [-1, 1]. --
CORRS = {}
for index_name, index_series in INDICES.items():
    index_da = xr.DataArray(
        index_series.values, dims='year', coords={'year': index_series.index.values}
    )
    for field_name, field in FIELDS.items():
        CORRS[(index_name, field_name)] = xr.corr(field, index_da, dim='year')

vmax = max(float(np.abs(c).max()) for c in CORRS.values())

fig, axes = plt.subplots(
    2, 3, figsize=(17, 11), subplot_kw={'projection': ccrs.PlateCarree()}
)

im = None
for i, index_name in enumerate(INDICES):
    for j, field_name in enumerate(FIELDS):
        ax = axes[i, j]
        ax.set_facecolor('#eaf2f8')

        corr = CORRS[(index_name, field_name)]
        im = corr.plot(
            ax=ax, transform=ccrs.PlateCarree(), cmap='RdBu_r',
            vmin=-vmax, vmax=vmax, add_colorbar=False,
        )

        for name, mask in REGION_MASKS.items():
            mask.astype(float).plot.contour(
                ax=ax, transform=ccrs.PlateCarree(), levels=[0.5],
                colors=REGION_COLORS[name], linewidths=1.4, add_colorbar=False,
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

legend_handles = [
    mlines.Line2D([], [], color=REGION_COLORS[name], linewidth=1.4, label=name)
    for name in REGION_MASKS
]
fig.legend(handles=legend_handles, loc='upper center', ncol=3, fontsize=9,
           bbox_to_anchor=(0.5, 0.93), frameon=False)

fig.subplots_adjust(right=0.9, wspace=0.15, hspace=0.1)
cbar_ax = fig.add_axes([0.92, 0.15, 0.015, 0.7])
cbar = fig.colorbar(im, cax=cbar_ax)
cbar.set_label('Pearson correlation coefficient (r)')

fig.suptitle(
    'Grid-Point Correlation: SST Teleconnection Indices vs. JJAS Rainfall Fields\n'
    '1901-2020, detrended',
    fontsize=14, fontweight='bold', y=0.99,
)
plt.savefig('figures/teleconnection_correlation_maps.png', dpi=200, bbox_inches='tight')
print(f'Saved figures/teleconnection_correlation_maps.png (color scale: -{vmax:.2f} to {vmax:.2f})')
