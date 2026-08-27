"""
Cross-correlation matrix (Pearson r) among the 7 all-India JJAS rainfall
variability measures in data/indices/airi_indices.csv (AIRI + 6 alternates,
see compute_airi_indices.py - run that first if the CSV doesn't exist yet),
4 EOF principal components from compute_moron_eof_analysis.py
(data/indices/eof_pcs.csv - run that first too): PC1 and PC2 of rainfall
amount, PC1 of rainy-day frequency, and PC1 of mean intensity, 3 sub-India
regional mean JJAS rainfall anomalies from compute_subregion_indices.py
(data/indices/subregion_indices.csv - run that first too): CMZ, WG, SEI, and
3 SST teleconnection indices from compute_enso_iod_indices.py
(data/indices/enso_iod_indices.csv - run that first too): -NINO3.4, DMI, and
DMI with the linear NINO3.4 signal regressed out ("DMI, N34 resids").
Matches the extra rows/columns in the source paper's own published matrix.

Each measure is a different unit (mm/day anomaly, unitless standardized
anomaly, a raw grid-point count, a day count), so comparing them directly only
makes sense via a unitless statistic like r - hence this matrix, not e.g. a
shared-axis overlay of the time series themselves.

Uses the "_detrended" columns from airi_indices.csv and subregion_indices.csv
(each series' 1901-2020 linear trend removed before correlating), matching
the source paper's stated methodology - not the raw columns. The PCs from
eof_pcs.csv and the 3 SST-derived columns from enso_iod_indices.csv are
already computed from detrended fields (see compute_moron_eof_analysis.py /
compute_enso_iod_indices.py respectively), so they're used as-is, no further
detrending needed.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

df = pd.read_csv('data/indices/airi_indices.csv')
pcs = pd.read_csv('data/indices/eof_pcs.csv')
subregions = pd.read_csv('data/indices/subregion_indices.csv')
enso_iod = pd.read_csv('data/indices/enso_iod_indices.csv')
df = (
    df.merge(pcs, on='year', how='inner')
    .merge(subregions, on='year', how='inner')
    .merge(enso_iod, on='year', how='inner')
)

LABELS = {
    'airi_raw_anomaly_mm_day': 'AIRI\n(raw anomaly)',
    'airi_standardized_anomaly': 'Standardized\nanomaly',
    'n_positive_anomaly_gridpoints': 'N positive\ngridpoints',
    'mean_rainy_days': 'Mean\nrainy days',
    'mean_intensity_rainy_days_mm_day': 'Mean\nintensity',
    'mean_positive_anomaly_mm_day': 'Mean pos.\nanomaly',
    'mean_negative_anomaly_mm_day': 'Mean neg.\nanomaly',
}
PC_LABELS = {
    'pc1_rainfall_mean': 'PC1\namount',
    'pc1_rainy_day_frequency': 'PC1\nfreq.',
    'pc2_rainfall_mean': 'PC2\namount',
    'pc1_mean_intensity': 'PC1\nintens.',
}
SUBREGION_LABELS = {
    'cmz_mean_anomaly_mm_day': 'CMZ',
    'wg_mean_anomaly_mm_day': 'WG',
    'sei_mean_anomaly_mm_day': 'SEI',
}
ENSO_IOD_LABELS = {
    'neg_nino34_jjas_detrended': '-NINO3.4',
    'dmi_jjas_detrended': 'DMI',
    'dmi_n34_residual_detrended': 'DMI, N34\nresids',
}
base_cols = list(LABELS.keys())
pc_cols = list(PC_LABELS.keys())
subregion_cols = list(SUBREGION_LABELS.keys())
enso_iod_cols = list(ENSO_IOD_LABELS.keys())  # already detrended, use as-is
detrended_cols = (
    [f'{c}_detrended' for c in base_cols] + pc_cols
    + [f'{c}_detrended' for c in subregion_cols] + enso_iod_cols
)
all_cols = base_cols + pc_cols + subregion_cols + enso_iod_cols
all_labels = {**LABELS, **PC_LABELS, **SUBREGION_LABELS, **ENSO_IOD_LABELS}

corr = df[detrended_cols].corr(method='pearson')
corr.index = all_cols
corr.columns = all_cols
corr.to_csv('data/indices/airi_correlation_matrix.csv')
print('Pearson correlation matrix (detrended series + EOF PCs):')
print(corr.round(2).to_string())

n = len(all_cols)
fig, ax = plt.subplots(figsize=(16, 15))
im = ax.imshow(corr.values, cmap='RdBu_r', vmin=-1, vmax=1)

ax.set_xticks(range(n))
ax.set_yticks(range(n))
ax.set_xticklabels([all_labels[c] for c in all_cols], rotation=45, ha='right', fontsize=8)
ax.set_yticklabels([all_labels[c] for c in all_cols], fontsize=8)

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
    'Cross-Correlation: AIRI + 6 Alternate Measures + 4 EOF PCs + 3 Sub-India Regions + 3 SST Indices\n'
    '1901-2020, detrended, unitless Pearson r',
    fontsize=11,
)

plt.tight_layout()
plt.savefig('figures/airi_indices_correlation_matrix.png', dpi=200, bbox_inches='tight')
print('Saved figures/airi_indices_correlation_matrix.png')
print('Saved data/indices/airi_correlation_matrix.csv')
