"""
IMD 0.25 deg gridded rainfall, 1901-2020: climatological mean number of rainy
days in JJAS (shaded), with mean rainfall intensity on rainy days (contours),
using a >0 mm/day threshold (i.e. any day with measurable rain).

Companion to plot_jjas_rainy_days_1mm.py and plot_jjas_rainy_days_intensity.py
(which uses the standard IMD >=2.5 mm/day threshold) - see
compare_rainy_day_thresholds.py for how much the threshold choice matters. Uses
the same intensity contour levels (10-30 mm/day) as that script so the three
are directly comparable at a glance.
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
jjas = precip.sel(time=precip['time.month'].isin([6, 7, 8, 9]))
n_years = len(np.unique(jjas['time.year'].values))

RAINY_DAY_THRESHOLD = 0  # mm/day - any measurable (nonzero) rainfall
rainy_mask = jjas > RAINY_DAY_THRESHOLD
mean_rainy_days = rainy_mask.sum(dim='time') / n_years
mean_intensity = jjas.where(rainy_mask).mean(dim='time')

print(f"{n_years} years | threshold >{RAINY_DAY_THRESHOLD} mm/day | "
      f"mean rainy days range: {float(mean_rainy_days.min()):.1f}-{float(mean_rainy_days.max()):.1f} days "
      f"| mean intensity range: {float(mean_intensity.min()):.1f}-{float(mean_intensity.max()):.1f} mm/day")

DATA_EXTENT = [67.0, 90.0, 7.25, 32.75]  # matches other figures in this project

fig, ax = plt.subplots(figsize=(8, 9), subplot_kw={'projection': ccrs.PlateCarree()})
ax.set_facecolor('#eaf2f8')

mean_rainy_days.plot.contourf(
    ax=ax, transform=ccrs.PlateCarree(),
    levels=np.arange(0, 125, 10), extend='neither', cmap='BuPu',
    add_colorbar=True,
    cbar_kwargs={'label': f'Mean number of rainy days in JJAS (days, >{RAINY_DAY_THRESHOLD} mm/day)',
                 'shrink': 0.75, 'pad': 0.08},
)

intensity_levels = [10, 15, 20, 25, 30]
intensity_linewidths = [0.6, 1.0, 1.4, 1.8, 2.2]
cs = mean_intensity.plot.contour(
    ax=ax, transform=ccrs.PlateCarree(),
    levels=intensity_levels, colors='#333333', linewidths=intensity_linewidths,
)
ax.clabel(cs, inline=True, fontsize=8, fmt='%d')

ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
ax.set_extent(DATA_EXTENT, crs=ccrs.PlateCarree())

gl = ax.gridlines(draw_labels=True, linewidth=0.3, linestyle='--')
gl.top_labels = False
gl.right_labels = False
gl.xlabel_style = {'size': 8}
gl.ylabel_style = {'size': 8}

year0, year1 = int(precip['time.year'].values[0]), int(precip['time.year'].values[-1])
ax.set_title(
    f'IMD 0.25° JJAS Rainy Days & Intensity, {year0}-{year1} (threshold: >{RAINY_DAY_THRESHOLD} mm/day)\n'
    'Shading: mean rainy days · Contours: mean intensity on rainy days (mm/day)',
    fontsize=11,
)

max_intensity = float(mean_intensity.max())
ax.text(
    0.015, 0.02,
    f'Rainy day: >{RAINY_DAY_THRESHOLD} mm/day. Intensity contours: 10-30 mm/day (thin→thick). '
    f'Max mean intensity: {max_intensity:.1f} mm/day',
    transform=ax.transAxes, fontsize=7, va='bottom', ha='left',
    bbox=dict(facecolor='white', alpha=0.75, edgecolor='none', pad=2),
)

plt.tight_layout()
plt.savefig('figures/jjas_rainy_days_0mm.png', dpi=200, bbox_inches='tight')
print('Saved figures/jjas_rainy_days_0mm.png')
