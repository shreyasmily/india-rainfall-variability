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
| AIRI (All-India Rainfall Index) | Not yet obtained — likely computed by area-averaging the IMD rainfall grid | will go in `data/indices/` |

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
  the r-value alone (~0.996) is misleadingly reassuring here; the difference map is the more informative
  result (up to ~39 days/season difference in the wettest cells).

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
