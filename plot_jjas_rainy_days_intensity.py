"""
IMD 0.25 deg gridded rainfall, 1901-2020: climatological mean number of rainy
days in JJAS (shaded), with mean rainfall intensity on rainy days (contours),
and the three sub-India analysis regions outlined.

"Rainy day" = daily rainfall >= 2.5 mm, the standard IMD threshold.

Intensity contours use a single dark color with increasing linewidth per level
(not grayscale), matching plot_jjas_climatology.py and
plot_jjas_rainfall_fraction.py: pale/white lines would vanish over pale
shading, and a fixed 10-30 mm/day color scale would misleadingly imply that's
the data's range when cells go higher (true max reported as text instead).

Region boxes are APPROXIMATE, commonly-cited literature boundaries, not a
specific paper's exact definition - check these against whatever source your
study is actually using before relying on them:
  - Central Monsoon Zone: 74-86E, 16-26N   (Gadgil & Gadgil 2006; Rajeevan et al.)
  - Western Ghats:        73-77E, 8-21N
  - Southeastern India:   78-84E, 8-16N    (Tamil Nadu / coastal Andhra Pradesh)
"""
import xarray as xr
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import cartopy.crs as ccrs
import cartopy.feature as cfeature

ds = xr.open_dataset('data/rainfall/imd_rain_daily_0p25_monsoon-masked_1901-2020.nc')
precip = ds['precip']
jjas = precip.sel(time=precip['time.month'].isin([6, 7, 8, 9]))
n_years = len(np.unique(jjas['time.year'].values))

RAINY_DAY_THRESHOLD = 2.5  # mm/day, standard IMD "rainy day" definition
rainy_mask = jjas >= RAINY_DAY_THRESHOLD

# Mean number of rainy days per JJAS season: total rainy-day occurrences across
# all years divided by number of years (equivalent to averaging each year's own
# count, since this is a simple sum - unlike the pooled-ratio approach needed
# for fractions in plot_jjas_rainfall_fraction.py).
mean_rainy_days = rainy_mask.sum(dim='time') / n_years

# Mean intensity on rainy days, pooled across all years directly (the 'time'
# dimension already spans all 120 years' JJAS days).
mean_intensity = jjas.where(rainy_mask).mean(dim='time')

print(f"{n_years} years | mean rainy days range: {float(mean_rainy_days.min()):.1f}-{float(mean_rainy_days.max()):.1f} days "
      f"| mean intensity range: {float(mean_intensity.min()):.1f}-{float(mean_intensity.max()):.1f} mm/day")

DATA_EXTENT = [67.0, 90.0, 7.25, 32.75]  # matches other figures in this project

REGIONS = [
    # name, lon_min, lon_max, lat_min, lat_max, color
    ('Central Monsoon Zone', 74, 86, 16, 26, '#d62728'),
    ('Western Ghats',        73, 77,  8, 21, '#ff7f0e'),
    ('Southeastern India',   78, 84,  8, 16, '#2ca02c'),
]

fig, ax = plt.subplots(figsize=(8, 9), subplot_kw={'projection': ccrs.PlateCarree()})
ax.set_facecolor('#eaf2f8')

mean_rainy_days.plot.contourf(
    ax=ax, transform=ccrs.PlateCarree(),
    levels=np.arange(0, 115, 10), extend='neither', cmap='BuPu',
    add_colorbar=True,
    cbar_kwargs={'label': 'Mean number of rainy days in JJAS (days, ≥2.5 mm/day)', 'shrink': 0.75, 'pad': 0.08},
)

intensity_levels = [10, 15, 20, 25, 30]
intensity_linewidths = [0.6, 1.0, 1.4, 1.8, 2.2]
cs = mean_intensity.plot.contour(
    ax=ax, transform=ccrs.PlateCarree(),
    levels=intensity_levels, colors='#333333', linewidths=intensity_linewidths,
)
ax.clabel(cs, inline=True, fontsize=8, fmt='%d')

for name, lon_min, lon_max, lat_min, lat_max, color in REGIONS:
    ax.add_patch(mpatches.Rectangle(
        (lon_min, lat_min), lon_max - lon_min, lat_max - lat_min,
        transform=ccrs.PlateCarree(), fill=False, edgecolor=color, linewidth=2.0, zorder=4,
    ))

ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
ax.set_extent(DATA_EXTENT, crs=ccrs.PlateCarree())

gl = ax.gridlines(draw_labels=True, linewidth=0.3, linestyle='--')
gl.top_labels = False
gl.right_labels = False
gl.xlabel_style = {'size': 8}
gl.ylabel_style = {'size': 8}

year0, year1 = int(precip['time.year'].values[0]), int(precip['time.year'].values[-1])
ax.set_title(
    f'IMD 0.25° JJAS Rainy Days & Intensity, {year0}-{year1}\n'
    'Shading: mean rainy days · Contours: mean intensity on rainy days (mm/day)',
    fontsize=11,
)

max_intensity = float(mean_intensity.max())
ax.text(
    0.015, 0.02,
    f'Rainy day: ≥{RAINY_DAY_THRESHOLD} mm/day. Intensity contours: 10-30 mm/day (thin→thick). '
    f'Max mean intensity: {max_intensity:.1f} mm/day',
    transform=ax.transAxes, fontsize=7, va='bottom', ha='left',
    bbox=dict(facecolor='white', alpha=0.75, edgecolor='none', pad=2),
)

legend_handles = [
    mlines.Line2D([], [], color=color, linewidth=2.0, label=name)
    for name, *_, color in REGIONS
]
ax.legend(handles=legend_handles, loc='upper right', fontsize=7, framealpha=0.85)

plt.tight_layout()
plt.savefig('figures/jjas_rainy_days_intensity.png', dpi=200, bbox_inches='tight')
print('Saved figures/jjas_rainy_days_intensity.png')
