"""
Cross-correlation matrix (Pearson r) among the 7 all-India JJAS rainfall
variability measures in data/indices/airi_indices.csv (AIRI + 6 alternates,
see compute_airi_indices.py - run that first if the CSV doesn't exist yet).

Each measure is a different unit (mm/day anomaly, unitless standardized
anomaly, a raw grid-point count, a day count), so comparing them directly only
makes sense via a unitless statistic like r - hence this matrix, not e.g. a
shared-axis overlay of the time series themselves.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

df = pd.read_csv('data/indices/airi_indices.csv')

LABELS = {
    'airi_raw_anomaly_mm_day': 'AIRI\n(raw anomaly)',
    'airi_standardized_anomaly': 'Standardized\nanomaly',
    'n_positive_anomaly_gridpoints': 'N positive\ngridpoints',
    'mean_rainy_days': 'Mean\nrainy days',
    'mean_intensity_rainy_days_mm_day': 'Mean\nintensity',
    'mean_positive_anomaly_mm_day': 'Mean pos.\nanomaly',
    'mean_negative_anomaly_mm_day': 'Mean neg.\nanomaly',
}
cols = list(LABELS.keys())

corr = df[cols].corr(method='pearson')
corr.to_csv('data/indices/airi_correlation_matrix.csv')
print('Pearson correlation matrix:')
print(corr.round(2).to_string())

n = len(cols)
fig, ax = plt.subplots(figsize=(9, 8))
im = ax.imshow(corr.values, cmap='RdBu_r', vmin=-1, vmax=1)

ax.set_xticks(range(n))
ax.set_yticks(range(n))
ax.set_xticklabels([LABELS[c] for c in cols], rotation=45, ha='right', fontsize=8)
ax.set_yticklabels([LABELS[c] for c in cols], fontsize=8)

# Recessive white gridlines between cells (imshow has no native cell grid)
ax.set_xticks(np.arange(-0.5, n, 1), minor=True)
ax.set_yticks(np.arange(-0.5, n, 1), minor=True)
ax.grid(which='minor', color='white', linewidth=2)
ax.tick_params(which='minor', bottom=False, left=False)

for i in range(n):
    for j in range(n):
        val = corr.values[i, j]
        text_color = 'white' if abs(val) > 0.6 else 'black'
        ax.text(j, i, f'{val:.2f}', ha='center', va='center', color=text_color, fontsize=8)

cbar = fig.colorbar(im, ax=ax, shrink=0.8)
cbar.set_label('Pearson correlation coefficient (r)')

ax.set_title(
    'Cross-Correlation: AIRI + 6 Alternate All-India JJAS Rainfall Measures\n'
    '1901-2020, unitless Pearson r',
    fontsize=11,
)

plt.tight_layout()
plt.savefig('figures/airi_indices_correlation_matrix.png', dpi=200, bbox_inches='tight')
print('Saved figures/airi_indices_correlation_matrix.png')
print('Saved data/indices/airi_correlation_matrix.csv')
