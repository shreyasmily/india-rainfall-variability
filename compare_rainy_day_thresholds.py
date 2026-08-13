"""
How sensitive is the JJAS "mean rainy days" climatology (see
plot_jjas_rainy_days_0mm.py / _1mm.py / plot_jjas_rainy_days_intensity.py's
>=2.5 mm/day) to the exact rainy-day threshold chosen? Compares the >0 mm/day
and >1 mm/day definitions directly.

On using a correlation (r) to compare the two fields
---------------------------------------------------
A single spatial Pearson r between the two threshold's rainy-day-count maps is
NOT a great primary metric here, even though it's a common first instinct for
"how similar are these two fields". The problem: both fields are dominated by
the same underlying climatological wet/dry gradient (Western Ghats wet,
NW India dry, etc.), so they will correlate very highly almost by
construction, regardless of how much the threshold choice actually changes
the day count. Run this script and you'll see r ~ 0.99 - technically true,
but it mostly just confirms both maps recognize the Western Ghats as wet,
which was never in question.

What actually answers "does the threshold choice matter" is the DIFFERENCE
between the two fields (by construction, days(>0mm) - days(>1mm) = the mean
number of light/drizzle days per JJAS season with 0 < rain <= 1mm at that
grid point) and the regression slope (is the bias constant, or does it scale
with how wet a location is?). This script reports both r AND the difference
field, plus a scatter/regression, so the r-value sits alongside the numbers
that show what it's hiding.
"""
import xarray as xr
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from scipy import stats

ds = xr.open_dataset('data/rainfall/imd_rain_daily_0p25_monsoon-masked_1901-2020.nc')
precip = ds['precip']
jjas = precip.sel(time=precip['time.month'].isin([6, 7, 8, 9]))
n_years = len(np.unique(jjas['time.year'].values))
valid = ds['monsoon_mask'].notnull()

# .where(valid): a boolean mask's .sum() doesn't propagate NaN for cells outside
# India (NaN > threshold is False, not NaN) - without this, ~13,800 non-India
# cells would read as "0 rainy days" for both thresholds and get pulled into
# the correlation/regression below as thousands of trivially-agreeing (0,0)
# points, inflating r and distorting the fitted slope. See CLAUDE.md.
days_0mm = ((jjas > 0).sum(dim='time') / n_years).where(valid)
days_1mm = ((jjas > 1).sum(dim='time') / n_years).where(valid)
diff = days_0mm - days_1mm  # = mean days/season with 0 < rain <= 1mm

a = days_0mm.values.ravel()
b = days_1mm.values.ravel()
valid = ~np.isnan(a) & ~np.isnan(b)
r, p = stats.pearsonr(a[valid], b[valid])
slope, intercept, r2, p2, se = stats.linregress(b[valid], a[valid])

print(f"{n_years} years, {valid.sum()} grid cells")
print(f"Pearson r (>0mm vs >1mm spatial pattern): {r:.4f} (p={p:.2e})")
print(f"Regression >0mm = {slope:.3f} * >1mm + {intercept:.3f}  (R^2={r2**2:.4f})")
print(f"Difference (>0mm minus >1mm) range: {float(diff.min()):.1f} to {float(diff.max()):.1f} days/season")
print(f"Difference mean/median: {float(diff.mean()):.1f} / {float(diff.median()):.1f} days/season")

DATA_EXTENT = [67.0, 90.0, 7.25, 32.75]
COUNT_LEVELS = np.arange(0, 125, 10)

fig = plt.figure(figsize=(14, 13))
gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.25, top=0.88, bottom=0.04)


def plot_map(ax, field, title, levels, cmap, cbar_label):
    ax.set_facecolor('#eaf2f8')
    field.plot.contourf(
        ax=ax, transform=ccrs.PlateCarree(), levels=levels, extend='neither', cmap=cmap,
        add_colorbar=True, cbar_kwargs={'label': cbar_label, 'shrink': 0.8, 'pad': 0.05},
    )
    ax.add_feature(cfeature.COASTLINE, linewidth=0.7)
    ax.set_extent(DATA_EXTENT, crs=ccrs.PlateCarree())
    gl = ax.gridlines(draw_labels=True, linewidth=0.3, linestyle='--')
    gl.top_labels = False
    gl.right_labels = False
    gl.xlabel_style = {'size': 7}
    gl.ylabel_style = {'size': 7}
    ax.set_title(title, fontsize=10)


ax1 = fig.add_subplot(gs[0, 0], projection=ccrs.PlateCarree())
plot_map(ax1, days_0mm, 'Mean rainy days, threshold >0 mm/day', COUNT_LEVELS, 'BuPu', 'days')

ax2 = fig.add_subplot(gs[0, 1], projection=ccrs.PlateCarree())
plot_map(ax2, days_1mm, 'Mean rainy days, threshold >1 mm/day', COUNT_LEVELS, 'BuPu', 'days')

ax3 = fig.add_subplot(gs[1, 0], projection=ccrs.PlateCarree())
plot_map(ax3, diff, 'Difference: (>0mm) − (>1mm)\n= mean days/season with 0 < rain ≤ 1mm',
         np.arange(0, 42, 2), 'OrRd', 'days')

ax4 = fig.add_subplot(gs[1, 1])
ax4.scatter(b[valid], a[valid], s=3, alpha=0.15, color='#4c72b0', edgecolors='none')
lims = [0, max(a[valid].max(), b[valid].max()) * 1.02]
ax4.plot(lims, lims, '--', color='#888888', linewidth=1, label='1:1 line')
x_fit = np.array(lims)
ax4.plot(x_fit, slope * x_fit + intercept, color='#d62728', linewidth=1.5,
          label=f'fit: y={slope:.2f}x+{intercept:.1f}')
ax4.set_xlim(lims)
ax4.set_ylim(lims)
ax4.set_xlabel('Mean rainy days, threshold >1 mm/day')
ax4.set_ylabel('Mean rainy days, threshold >0 mm/day')
ax4.set_title(f'Per-cell comparison (r = {r:.3f})', fontsize=10)
ax4.legend(fontsize=8, loc='upper left')
ax4.grid(True, alpha=0.3)
ax4.set_aspect('equal')

fig.suptitle(
    'Sensitivity of "rainy day" count to threshold choice, JJAS 1901-2020\n'
    f'r={r:.3f} looks like near-perfect agreement, but the two definitions differ by up to '
    f'{float(diff.max()):.0f} days/season in the wettest cells',
    fontsize=12, fontweight='bold',
)

plt.savefig('figures/compare_rainy_day_thresholds.png', dpi=200, bbox_inches='tight')
print('Saved figures/compare_rainy_day_thresholds.png')
