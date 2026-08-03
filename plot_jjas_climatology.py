"""
IMD 0.25 deg gridded rainfall, 1901-2020: JJAS climatological mean (shaded)
and interannual standard deviation (contours).
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

# Restrict to JJAS (June-Sep), then take each year's JJAS seasonal mean before
# averaging across years — this gives the interannual std of the *seasonal*
# mean (the quantity of interest), not the std of individual days.
jjas = precip.sel(time=precip['time.month'].isin([6, 7, 8, 9]))
seasonal_mean = jjas.groupby('time.year').mean(dim='time')

clim_mean = seasonal_mean.mean(dim='year')
clim_std = seasonal_mean.std(dim='year', ddof=1)

n_years = seasonal_mean.sizes['year']
max_std = float(clim_std.max())
print(f"{n_years} years | JJAS mean range: {float(clim_mean.min()):.1f}-{float(clim_mean.max()):.1f} mm/day "
      f"| max interannual std: {max_std:.1f} mm/day")

fig, ax = plt.subplots(figsize=(8, 9), subplot_kw={'projection': ccrs.PlateCarree()})

mean_levels = np.arange(0, 32, 2)
clim_mean.plot.contourf(
    ax=ax, transform=ccrs.PlateCarree(),
    levels=mean_levels, extend='max', cmap='YlGnBu',
    add_colorbar=True,
    cbar_kwargs={'label': 'JJAS climatological mean rainfall (mm/day)', 'shrink': 0.75, 'pad': 0.08},
)

# Std dev shown as single-color contours with increasing linewidth (not grayscale):
# white/light lines at low values would be invisible over the pale shading in
# drier regions, and a grayscale ramp fixed at 1-5 would misleadingly imply that's
# the data's range when the true max is well above it (noted as text instead).
std_levels = [1, 2, 3, 4, 5]
std_linewidths = [0.6, 1.0, 1.4, 1.8, 2.2]
cs = clim_std.plot.contour(
    ax=ax, transform=ccrs.PlateCarree(),
    levels=std_levels, colors='#333333', linewidths=std_linewidths,
)
ax.clabel(cs, inline=True, fontsize=7, fmt='%d')

ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
ax.add_feature(cfeature.BORDERS, linewidth=0.5)
ax.set_extent([66, 100, 6, 39], crs=ccrs.PlateCarree())

gl = ax.gridlines(draw_labels=True, linewidth=0.3, linestyle='--')
gl.top_labels = False
gl.right_labels = False
gl.xlabel_style = {'size': 8}
gl.ylabel_style = {'size': 8}

ax.set_title(
    f'IMD 0.25° JJAS Rainfall Climatology, {seasonal_mean.year.values[0]}-{seasonal_mean.year.values[-1]}\n'
    'Shading: climatological mean · Contours: interannual std. dev. (mm/day)',
    fontsize=11,
)

ax.text(
    0.015, 0.02,
    f'Contours: 1-5 mm/day (thin→thick). Max std. dev.: {max_std:.1f} mm/day (off contour scale)',
    transform=ax.transAxes, fontsize=7, va='bottom', ha='left',
    bbox=dict(facecolor='white', alpha=0.75, edgecolor='none', pad=2),
)

plt.tight_layout()
plt.savefig('figures/jjas_climatology_mean_std.png', dpi=200, bbox_inches='tight')
print('Saved figures/jjas_climatology_mean_std.png')
