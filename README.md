# India Rainfall Variability

Understanding the summer-mean relationships among the All-India Rainfall Index (AIRI), sub-India
regional rainfall, El Niño–Southern Oscillation (ENSO), and the Indian Ocean Dipole (IOD), using a
120-year sea surface temperature (SST) record and a high-resolution gridded rainfall dataset.

This project is a companion to [enso-sst-analysis](https://github.com/shreyasmily/enso-sst-analysis),
reusing similar tools (xarray/EOF-based climate analysis) applied to the India summer monsoon /
teleconnection problem.

## Status

Early stage — rainfall climatology figures done, SST/index data still to come.

## Data

| Dataset | Status | Location |
|---|---|---|
| IMD gridded daily rainfall, 0.25°, monsoon-masked, 1901–2020 | On hand | `data/rainfall/imd_rain_daily_0p25_monsoon-masked_1901-2020.nc` |
| Surface elevation, regridded to the IMD 0.25° grid | On hand — built by `fetch_elevation.py` from AWS-hosted Terrarium terrain tiles | `data/elevation/india_elevation_0p25deg.nc` |
| 120-year SST record (e.g. HadISST / ERSSTv5) | Not yet obtained | will go in `data/sst/` |
| ENSO index (e.g. Niño 3.4) | Not yet obtained — likely computed from the SST record | will go in `data/indices/` |
| IOD index (Dipole Mode Index) | Not yet obtained — likely computed from the SST record | will go in `data/indices/` |
| AIRI + 6 alternate measures | On hand — computed by `compute_airi_indices.py` | `data/indices/airi_indices.csv` |

Raw and intermediate data files are not committed to this repository (see `.gitignore`) — they're too
large for GitHub. Only code, figures, and documentation are tracked.

## Scripts

- `fetch_elevation.py` — one-time data prep. Downloads AWS-hosted Terrarium elevation tiles and
  area-averages them onto the IMD rainfall grid's exact lat/lon coordinates. Run once before any script
  that needs `data/elevation/india_elevation_0p25deg.nc`.
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
- `compute_airi_correlation_matrix.py` — cross-correlation (Pearson r) among all 7 AIRI measures above,
  computed on the **detrended** series (matching the source paper's stated methodology), as a heatmap
  (`figures/airi_indices_correlation_matrix.png`) and CSV (`data/indices/airi_correlation_matrix.csv`).
  AIRI/standardized-anomaly/N-positive-gridpoints/mean-rainy-days are all tightly correlated (r≥0.93,
  largely the same signal); mean intensity and mean positive/negative anomaly are more independent.
  We're still chasing a specific discrepancy against the source paper's published matrix for the
  AIRI-vs-mean-intensity cell (paper reports r=0.77; ours currently gives 0.63 detrended, 0.58 raw) —
  see git history / conversation log for what's been ruled out (aggregation order, rain-weighting,
  threshold choice, spatial mask artifacts) before picking this back up.

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
