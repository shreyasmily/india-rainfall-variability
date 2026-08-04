"""
IMD 0.25 deg gridded rainfall, 1901-2020: climatological fraction of annual-mean
rainfall that falls during JJAS (shaded), with surface elevation (contours).

This metric is computed from rainfall TOTALS (sums), not a rainy-day count, so
it has no "rainy day threshold" to keep in sync with
plot_jjas_rainy_days_*.py/compare_rainy_day_thresholds.py - nothing to update
there when that threshold changes.

Generates 2 color-scheme variants for side-by-side comparison:
  1. jjas_rainfall_fraction_elevation.png       - YlOrRd (original)
  2. jjas_rainfall_fraction_elevation_bupu.png  - BuPu, matching the rainy-days
                                                   figures' color scheme

Map framing (tight extent to the data domain, no political borders) matches the
"optimal" variant chosen in plot_jjas_climatology.py. Elevation contours use a
single dark color with increasing linewidth per level (not grayscale) for the
same reason as the std-dev contours there: white/pale lines would vanish over
pale shading, and a color ramp fixed at 100-900m would misleadingly imply
that's the data's range when cells go higher.

Elevation comes from fetch_elevation.py (AWS-hosted Terrarium terrain tiles,
area-averaged onto this dataset's exact 0.25deg grid) - run that first if
data/elevation/india_elevation_0p25deg.nc doesn't exist yet.
"""
import xarray as xr
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

ds = xr.open_dataset('data/rainfall/imd_rain_daily_0p25_monsoon-masked_1901-2020.nc')
precip = ds['precip']

# Daily values are already mm for that day, so summing over a period gives that
# period's total rainfall (mm). Fraction = pooled JJAS totals / pooled annual
# totals across all 120 years, rather than averaging each year's own ratio -
# this avoids a handful of near-zero-rainfall years in dry cells producing wild
# per-year ratios that would otherwise skew a simple average.
jjas = precip.sel(time=precip['time.month'].isin([6, 7, 8, 9]))
annual_total = precip.groupby('time.year').sum('time', skipna=True, min_count=300)
jjas_total = jjas.groupby('time.year').sum('time', skipna=True, min_count=100)
fraction_pct = 100 * jjas_total.sum('year') / annual_total.sum('year')

print(f"JJAS rainfall fraction range: {float(fraction_pct.min()):.1f}% to {float(fraction_pct.max()):.1f}%")

# Elevation, regridded to this dataset's exact lat/lon grid (see fetch_elevation.py),
# restricted to the same India domain as the rainfall data, and floored at 0m -
# small negative values near the coast/river deltas are an artifact of area-
# averaging a finer DEM onto this grid, not real below-sea-level land.
elevation = xr.open_dataset('data/elevation/india_elevation_0p25deg.nc')['elevation']
elevation = elevation.where(ds['monsoon_mask'].notnull()).clip(min=0)
max_elev = float(elevation.max())
print(f"Max elevation in domain: {max_elev:.0f} m")

DATA_EXTENT = [67.0, 90.0, 7.25, 32.75]  # matches plot_jjas_climatology.py
year0, year1 = int(precip['time.year'].values[0]), int(precip['time.year'].values[-1])


def render(filename, cmap):
    fig, ax = plt.subplots(figsize=(8, 9), subplot_kw={'projection': ccrs.PlateCarree()})
    ax.set_facecolor('#eaf2f8')

    fraction_pct.plot.contourf(
        ax=ax, transform=ccrs.PlateCarree(),
        levels=np.arange(0, 101, 5), extend='neither', cmap=cmap,
        add_colorbar=True,
        cbar_kwargs={'label': 'JJAS share of annual-mean rainfall (%)', 'shrink': 0.75, 'pad': 0.08},
    )

    elev_levels = [100, 300, 500, 700, 900]
    elev_linewidths = [0.6, 1.0, 1.4, 1.8, 2.2]
    cs = elevation.plot.contour(
        ax=ax, transform=ccrs.PlateCarree(),
        levels=elev_levels, colors='#333333', linewidths=elev_linewidths,
    )
    ax.clabel(cs, inline=True, fontsize=8, fmt='%d')

    ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
    ax.set_extent(DATA_EXTENT, crs=ccrs.PlateCarree())

    gl = ax.gridlines(draw_labels=True, linewidth=0.3, linestyle='--')
    gl.top_labels = False
    gl.right_labels = False
    gl.xlabel_style = {'size': 8}
    gl.ylabel_style = {'size': 8}

    ax.set_title(
        f'IMD 0.25° JJAS Share of Annual Rainfall, {year0}-{year1}\n'
        'Shading: % of annual rainfall falling in JJAS · Contours: elevation (m)',
        fontsize=11,
    )

    ax.text(
        0.015, 0.02,
        f'Elevation contours: 100-900 m (thin→thick). Max elevation in domain: {max_elev:.0f} m',
        transform=ax.transAxes, fontsize=7, va='bottom', ha='left',
        bbox=dict(facecolor='white', alpha=0.75, edgecolor='none', pad=2),
    )

    plt.tight_layout()
    plt.savefig(f'figures/{filename}', dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved figures/{filename}')


render('jjas_rainfall_fraction_elevation.png', cmap='YlOrRd')
render('jjas_rainfall_fraction_elevation_bupu.png', cmap='BuPu')
