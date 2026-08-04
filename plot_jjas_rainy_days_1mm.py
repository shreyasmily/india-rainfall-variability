"""
IMD 0.25 deg gridded rainfall, 1901-2020: climatological mean number of rainy
days in JJAS, using a >1 mm/day threshold.

Companion to plot_jjas_rainy_days_0mm.py and plot_jjas_rainy_days_intensity.py
(which uses the standard IMD >=2.5 mm/day threshold) - see
compare_rainy_day_thresholds.py for how much the threshold choice matters.
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

RAINY_DAY_THRESHOLD = 1  # mm/day
rainy_mask = jjas > RAINY_DAY_THRESHOLD
mean_rainy_days = rainy_mask.sum(dim='time') / n_years

print(f"{n_years} years | threshold >{RAINY_DAY_THRESHOLD} mm/day | "
      f"mean rainy days range: {float(mean_rainy_days.min()):.1f}-{float(mean_rainy_days.max()):.1f} days")

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

ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
ax.set_extent(DATA_EXTENT, crs=ccrs.PlateCarree())

gl = ax.gridlines(draw_labels=True, linewidth=0.3, linestyle='--')
gl.top_labels = False
gl.right_labels = False
gl.xlabel_style = {'size': 8}
gl.ylabel_style = {'size': 8}

year0, year1 = int(precip['time.year'].values[0]), int(precip['time.year'].values[-1])
ax.set_title(
    f'IMD 0.25° JJAS Rainy Days, {year0}-{year1} (threshold: >{RAINY_DAY_THRESHOLD} mm/day)',
    fontsize=11,
)

plt.tight_layout()
plt.savefig('figures/jjas_rainy_days_1mm.png', dpi=200, bbox_inches='tight')
print('Saved figures/jjas_rainy_days_1mm.png')
