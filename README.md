# India Rainfall Variability

Understanding the summer-mean relationships among the All-India Rainfall Index (AIRI), sub-India
regional rainfall, El Niño–Southern Oscillation (ENSO), and the Indian Ocean Dipole (IOD), using a
120-year sea surface temperature (SST) record and a high-resolution gridded rainfall dataset.

This project is a companion to [enso-sst-analysis](https://github.com/shreyasmily/enso-sst-analysis),
reusing similar tools (xarray/EOF-based climate analysis) applied to the India summer monsoon /
teleconnection problem.

## Status

Rainfall climatology figures, AIRI/EOF/sub-region indices, the SST record, the NINO3.4/DMI indices (in
the main correlation matrix), and grid-point teleconnection correlation maps are all done.

## Data

| Dataset | Status | Location |
|---|---|---|
| IMD gridded daily rainfall, 0.25°, monsoon-masked, 1901–2020 | On hand | `data/rainfall/imd_rain_daily_0p25_monsoon-masked_1901-2020.nc` |
| Surface elevation, regridded to the IMD 0.25° grid | On hand — built by `fetch_elevation.py` from AWS-hosted Terrarium terrain tiles | `data/elevation/india_elevation_0p25deg.nc` |
| ERSSTv5 monthly SST, global 2°, 1854-present | On hand — downloaded by `fetch_ersst.py` from NOAA PSL | `data/sst/ersst.v5.mnmean.nc` |
| NINO3.4 + DMI, JJAS 1901–2020 | On hand — computed by `compute_enso_iod_indices.py` | `data/indices/enso_iod_indices.csv` |
| AIRI + 6 alternate measures | On hand — computed by `compute_airi_indices.py` | `data/indices/airi_indices.csv` |
| CMZ / WG / SEI regional indices | On hand — computed by `compute_subregion_indices.py` | `data/indices/subregion_indices.csv` |

Raw and intermediate data files are not committed to this repository (see `.gitignore`) — they're too
large for GitHub. Only code, figures, and documentation are tracked.

## Scripts

- `fetch_elevation.py` — one-time data prep. Downloads AWS-hosted Terrarium elevation tiles and
  area-averages them onto the IMD rainfall grid's exact lat/lon coordinates. Run once before any script
  that needs `data/elevation/india_elevation_0p25deg.nc`.
- `fetch_ersst.py` — one-time data download. NOAA ERSSTv5 monthly SST, global 2°, from NOAA PSL
  (`downloads.psl.noaa.gov`) — a single ~157MB file covering 1854-present (not just 1901-2020; kept
  whole, subset by whatever script computes ENSO/IOD indices next). Longitude is 0-360°, not -180/180 —
  convert before any Pacific/Indian Ocean region selection, same gotcha handled in the companion
  enso-sst-analysis project.
- `compute_enso_iod_indices.py` — NINO3.4 (120-170°W, 5°S-5°N) and DMI (west box 50-70°E,10°S-0° minus
  east box 90-110°E,10°S-10°N, Saji et al. 1999), area(cos-lat)-weighted box averages of the monthly SST
  anomaly (deviation from each grid point's 1901-2020 monthly climatology), restricted to JJAS and
  averaged within each year. Also derives `neg_nino34_jjas_detrended` (-1x detrended NINO3.4) and
  `dmi_n34_residual_detrended` (DMI detrended, linear NINO3.4 signal regressed out via OLS - the part of
  IOD variability independent of ENSO), matching the extra rows in the source paper's own correlation
  matrix (`-NINO3.4`, `DMI, N34 resids`). Outputs `data/indices/enso_iod_indices.csv` (120 years) and
  `figures/enso_iod_indices_timeseries.png`. Validated against the source paper: r(NINO3.4 detrended,
  AIRI detrended) = **-0.54**, matching their reported ~-0.53 for NINO3 ("virtually unchanged" for
  NINO3.4) almost exactly. NINO3.4's two clearest peaks land on 1997 and 2015, the two strongest
  observed El Niño events - another good sanity check.
- `plot_jjas_climatology.py` — climatological JJAS mean rainfall (shaded) and interannual std. dev.
  (contoured), in 4 framing variants. See `figures/`.
- `plot_jjas_rainfall_fraction.py` — climatological % of annual rainfall falling in JJAS (shaded), with
  elevation (contoured). Computed from rainfall totals, not a rainy-day count, so it has no threshold to
  keep in sync with the rainy-day scripts below. Generates 2 color-scheme variants (YlOrRd and BuPu) for
  side-by-side comparison.
- `plot_jjas_rainy_days_intensity.py` — climatological mean number of rainy days in JJAS (shaded,
  ≥2.5 mm/day IMD threshold), mean rainfall intensity on rainy days (contoured).
- `plot_jjas_rainy_days_0mm.py` / `plot_jjas_rainy_days_1mm.py` — same rainy-days + intensity figure at
  two other thresholds (>0 and >1 mm/day, same 10-30 mm/day intensity contour levels), for comparison
  against the IMD-standard 2.5mm figure above.
- `compare_rainy_day_thresholds.py` — quantifies how much the >0mm vs >1mm threshold choice actually
  matters: spatial Pearson r, a difference map, and a per-cell scatter/regression. Read the docstring —
  the r-value alone (~0.986) is misleadingly reassuring here; the difference map (a roughly constant
  ~11-13 day offset across most of India) is the more informative result.
- `compute_airi_indices.py` — AIRI (avg raw JJAS rainfall anomaly, all-India) plus 6 alternate all-India
  measures of JJAS rainfall variability (standardized anomaly; count of positive-anomaly grid points;
  avg rainy days/season; avg intensity on rainy days; mean anomaly restricted to positive-only /
  negative-only grid points) — see the script docstring for exact definitions. Outputs a 120-year time
  series CSV (`data/indices/airi_indices.csv`, each measure plus a `_detrended` version with its
  1901-2020 linear trend removed) and a 7-panel figure (`figures/airi_indices_timeseries.png`, raw
  values). Unlike the other scripts here, these are *unweighted* spatial averages (matching the literal
  definitions), not area/cos(lat)-weighted.
- `compute_moron_eof_analysis.py` — EOF analysis (Moron et al. 2017 style) of JJAS standardized
  anomalies for rainfall mean, rainy-day frequency, and mean intensity (same per-gridpoint definitions
  as `compute_airi_indices.py`, each grid point linearly detrended then standardized instead of
  spatially averaged - matches the source paper's stated methodology, same as
  `compute_airi_correlation_matrix.py`). cos(lat)-weighted, matching the companion enso-sst-analysis
  project's EOF convention. Outputs one 4-panel figure per variable (EOF1/PC1, EOF2/PC2) —
  `figures/eof_rainfall_mean.png`, `figures/eof_rainy_day_frequency.png`,
  `figures/eof_mean_intensity.png` — plus all 6 PC time series (PC1+PC2 x 3 variables) to
  `data/indices/eof_pcs.csv`, for `compute_airi_correlation_matrix.py` to fold in. PC1's sign convention
  is **not** uniform across variables (`TARGET_SIGN` in the script): rainfall amount and rainy-day
  frequency are fixed to correlate POSITIVELY with AIRI, but mean intensity is fixed to correlate
  NEGATIVELY - matching the source paper's own published matrix, where PC1-intensity is anti-correlated
  with AIRI while the other two are strongly positive. (An earlier version of this script forced positive
  correlation for all three, which was backwards for intensity specifically - EOF sign is arbitrary, so
  there was no way to know without checking against the paper's actual reported signs.) Rainfall-mean
  and rainy-day-frequency EOF1 explain 18.0%/31.8% of variance and correlate strongly with AIRI
  (r=0.96/0.93) — mean intensity's EOF1 explains far less (6.0%) and now correlates only weakly
  negatively with AIRI once detrended (r=-0.05) — sign now matches the paper's reported anti-correlation,
  though we don't have their exact magnitude to check against (this is a different, EOF-based quantity
  from the spatially-averaged "mean intensity" measure in the correlation-matrix discrepancy noted below,
  which is still open).
- `plot_eof_comparison.py` — the 4 headline spatial patterns from the above (rainfall mean EOF1+EOF2,
  rainy-day-frequency EOF1, mean-intensity EOF1) laid out together in one figure
  (`figures/eof_comparison.png`), maps only (no PC time series). Recomputes the same EOFs rather than
  loading saved output — see this script if you need to change what the comparison shows.
- `compute_subregion_indices.py` — detrended mean JJAS rainfall anomaly for 3 sub-India regions: CMZ
  (Central Monsoon Zone, the band between two irregular north/south boundary curves digitized from
  Gadgil et al. 2019 Fig. 3(a). Capped at `CMZ_LON_MAX = 88.5°E` on the east — the band does not extend
  into northeast India, unlike an earlier version that held the curve's endpoint flat past its covered
  range and ended up covering ~64% of India's valid domain. The WEST side has no such cap: rather than a
  straight longitude cutoff, it's bounded only by the dataset's own `valid` domain, i.e. India's actual
  border with Pakistan and the Arabian Sea coastline in Rajasthan/Gujarat — 1839 grid points, following
  the real jagged border shape rather than a vertical line), WG (Western
  Ghats — grid points with >100 climatological mean JJAS rainy days; checked empirically that this
  threshold alone, no extra geographic restriction needed, is already confined to the coastal strip
  lon 73-76.75°E, lat 9.5-19°N), and SEI (Southeast India — east of WG's per-latitude eastern edge, south
  of 18°N). Outputs
  `data/indices/subregion_indices.csv` and a mask-verification map (`figures/subregion_masks.png`) —
  look at that figure before trusting the indices, since region boundaries are easy to get subtly wrong.
- `compute_airi_correlation_matrix.py` — cross-correlation (Pearson r) among the 7 AIRI measures, 4 EOF
  PCs (PC1/PC2 rainfall amount, PC1 rainy-day frequency, PC1 mean intensity), the 3 sub-India regional
  indices, and 3 SST teleconnection indices from `compute_enso_iod_indices.py` (-NINO3.4, DMI, and DMI
  with the linear NINO3.4 signal regressed out) — matching the extra rows/columns in the source paper's
  own published matrix. All on **detrended** series, as a 17x17 heatmap
  (`figures/airi_indices_correlation_matrix.png`) and CSV (`data/indices/airi_correlation_matrix.csv`).
  Needs `eof_pcs.csv`, `subregion_indices.csv`, and `enso_iod_indices.csv` to exist first.
  AIRI/standardized-anomaly/N-positive-gridpoints/mean-rainy-days/PC1-amount/PC1-freq are all tightly
  correlated (r≥0.93, largely the same signal, PC1-freq vs mean-rainy-days=1.00 exactly since EOF1
  dominates that field's variance); mean intensity and mean positive/negative anomaly are more
  independent. CMZ correlates very strongly with AIRI (r=0.93, expected given its size); SEI is the most
  distinct region, anti-correlating with both PC2-amount (r=-0.57) and PC1-intensity (r=-0.58) —
  consistent with SEI being governed more by the northeast monsoon than the southwest-monsoon signal
  everything else here measures. -NINO3.4 vs AIRI = 0.54 (matches the standalone sanity check in
  `compute_enso_iod_indices.py`); raw DMI barely relates to AIRI directly (r=0.04), and DMI vs its own
  NINO3.4-residual is r=0.96 (expected — only a modest ENSO-shared component was removed, consistent
  with DMI-NINO3.4's own r=0.28). We're still chasing a specific magnitude discrepancy against the source
  paper's published matrix for the AIRI-vs-mean-intensity cell (the spatially-averaged measure, not the
  PC1 above - paper reports r=0.77; ours currently gives 0.63 detrended, 0.58 raw) — see git history /
  conversation log for what's been ruled out (aggregation order, rain-weighting, threshold choice,
  spatial mask artifacts) before picking this back up.
- `plot_eof_comparison_with_regions.py` — the same 4-panel EOF comparison as `plot_eof_comparison.py`,
  with the CMZ/WG/SEI region boundaries outlined on top (`figures/eof_comparison_with_regions.png`,
  saved separately so both the plain and annotated versions are available to choose between). Makes the
  SEI anti-correlation finding above visually obvious: SEI sits almost entirely in the negative/blue
  lobe of both rainfall-mean EOF2 and mean-intensity EOF1, while CMZ sits in the positive/red lobe.
- `plot_teleconnection_correlation_maps.py` — grid-point-by-grid-point Pearson r between the 2 SST
  indices (-NINO3.4, DMI N3.4-residual) and the 3 JJAS rainfall fields (amount, frequency, intensity —
  same per-gridpoint definitions used throughout this project), as a shared-colorbar 2x3 map grid
  (`figures/teleconnection_correlation_maps.png`). Each rainfall field is detrended per grid point but
  NOT standardized before correlating (Pearson r is invariant to per-point rescaling, so this doesn't
  change results, just skips an unneeded step). -NINO3.4 shows broad, spatially coherent positive
  correlation with amount and frequency across nearly all of India (the classic ENSO-monsoon
  teleconnection) but a much weaker, noisier pattern for intensity; DMI's residual shows a patchier,
  overall weaker signal across all three, consistent with its near-zero AIRI correlation in the matrix.

## Setup

```
conda activate podaac_env
pip install -r requirements.txt
```

## Repository structure

```
data/            (gitignored) raw + intermediate datasets
figures/         result figures
docs/            write-ups / notes
```
