"""
IMD 0.25 deg gridded rainfall, 1901-2020: JJAS climatological mean (shaded)
and interannual standard deviation (contours).

Generates 4 variants of the same figure to compare framing choices:
  1. jjas_climatology_mean_std.png       - full India extent, country borders shown
  2. jjas_climatology_no_borders_tight.png - cropped to data extent, no borders
  3. jjas_climatology_borders_tight.png    - cropped to data extent, borders shown
  4. jjas_climatology_optimal.png          - cropped to data extent, no borders,
                                              land/ocean background for context
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
year0, year1 = int(seasonal_mean.year.values[0]), int(seasonal_mean.year.values[-1])
print(f"{n_years} years | JJAS mean range: {float(clim_mean.min()):.1f}-{float(clim_mean.max()):.1f} mm/day "
      f"| max interannual std: {max_std:.1f} mm/day")

# Bounding box of where the monsoon mask actually has valid data (computed once,
# see project notes) rather than the full lat/lon grid, which extends well
# north of where any data exists.
DATA_EXTENT = [67.0, 90.0, 7.25, 32.75]   # [lon_min, lon_max, lat_min, lat_max], 1deg padding
FULL_EXTENT = [66.0, 100.0, 6.0, 39.0]

MEAN_LEVELS = np.arange(0, 32, 2)
STD_LEVELS = [1, 2, 3, 4, 5]
STD_LINEWIDTHS = [0.6, 1.0, 1.4, 1.8, 2.2]


def render(filename, extent, show_borders, ocean_bg=False, contour_fontsize=7, title=None):
    fig, ax = plt.subplots(figsize=(8, 9), subplot_kw={'projection': ccrs.PlateCarree()})

    if ocean_bg:
        # A flat background tint reads as "outside the data domain" without needing
        # to fetch land/ocean polygon shapefiles (avoids a Natural Earth download).
        ax.set_facecolor('#eaf2f8')

    clim_mean.plot.contourf(
        ax=ax, transform=ccrs.PlateCarree(),
        levels=MEAN_LEVELS, extend='max', cmap='YlGnBu',
        add_colorbar=True,
        cbar_kwargs={'label': 'JJAS climatological mean rainfall (mm/day)', 'shrink': 0.75, 'pad': 0.08},
        zorder=1,
    )

    # Std dev shown as single-color contours with increasing linewidth (not grayscale):
    # white/light lines at low values would be invisible over the pale shading in
    # drier regions, and a grayscale ramp fixed at 1-5 would misleadingly imply that's
    # the data's range when the true max is well above it (noted as text instead).
    cs = clim_std.plot.contour(
        ax=ax, transform=ccrs.PlateCarree(),
        levels=STD_LEVELS, colors='#333333', linewidths=STD_LINEWIDTHS, zorder=2,
    )
    ax.clabel(cs, inline=True, fontsize=contour_fontsize, fmt='%d')

    ax.add_feature(cfeature.COASTLINE, linewidth=0.8, zorder=3)
    if show_borders:
        ax.add_feature(cfeature.BORDERS, linewidth=0.5, zorder=3)
    ax.set_extent(extent, crs=ccrs.PlateCarree())

    gl = ax.gridlines(draw_labels=True, linewidth=0.3, linestyle='--')
    gl.top_labels = False
    gl.right_labels = False
    gl.xlabel_style = {'size': 8}
    gl.ylabel_style = {'size': 8}

    ax.set_title(
        title or f'IMD 0.25° JJAS Rainfall Climatology, {year0}-{year1}\n'
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
    plt.savefig(f'figures/{filename}', dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved figures/{filename}')


# 1. Original: full India extent, borders shown
render('jjas_climatology_mean_std.png', FULL_EXTENT, show_borders=True)

# 2. No borders, cropped to where the data actually is
render('jjas_climatology_no_borders_tight.png', DATA_EXTENT, show_borders=False)

# 3. Borders shown, cropped to where the data actually is
render('jjas_climatology_borders_tight.png', DATA_EXTENT, show_borders=True)

# 4. Optimal: cropped extent, no borders (coastline alone is enough for orientation
# and avoids clutter/contested-border-line issues), light land/ocean tint instead of
# political lines to keep geographic context, slightly larger contour labels since
# the tighter crop leaves more room for them.
render(
    'jjas_climatology_optimal.png', DATA_EXTENT, show_borders=False, ocean_bg=True,
    contour_fontsize=8,
    title=f'IMD 0.25° JJAS Rainfall Climatology, {year0}-{year1}\n'
          'Shading: climatological mean (mm/day) · Contours: interannual std. dev. (mm/day)',
)
