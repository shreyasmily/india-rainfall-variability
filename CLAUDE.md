# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A research project studying summer-mean relationships among the All-India Rainfall Index (AIRI),
sub-India regional rainfall, ENSO, and the Indian Ocean Dipole (IOD), using a 120-year SST record and
a high-resolution gridded rainfall dataset. See [README.md](README.md) for current status and data
inventory.

This is a GitHub-backed project at `github.com/shreyasmily/india-rainfall-variability` (remote `origin`,
branch `main`). Companion project: [enso-sst-analysis](../enso-sst-analysis), which this one is expected
to reuse methodology from (EOF analysis via the `eofs` library, xarray-based NetCDF handling).

## Environment

Shares the `podaac_env` conda environment with the ENSO SST project:

```
conda activate podaac_env
pip install -r requirements.txt
```

## Current state

Two datasets on hand:
- `data/rainfall/imd_rain_daily_0p25_monsoon-masked_1901-2020.nc` — IMD gridded daily rainfall, 0.25°,
  monsoon-masked, 1901–2020, covering `lat 6.5–38.5, lon 66.5–100` (dims: `time, lat, lon`, variable
  `precip`, units mm/day == mm for that day since it's daily resolution). `monsoon_mask` (1/NaN) marks
  the actual India domain; the lat/lon grid extends well beyond it (empty cells elsewhere).
- `data/elevation/india_elevation_0p25deg.nc` — surface elevation on the exact same lat/lon grid as the
  rainfall data, built by `fetch_elevation.py`. Not a precision DEM regrid — see that script's docstring.
- `data/indices/airi_indices.csv` — AIRI + 6 alternate all-India JJAS rainfall variability measures
  (one row per year, 1901-2020), built by `compute_airi_indices.py`. See that script's docstring for the
  exact definition of each column - they're not all the same kind of quantity (some are anomalies in
  mm/day, one is a unitless standardized anomaly, one is a raw grid-point count). Each measure also has
  a `_detrended` counterpart column (linear 1901-2020 trend removed); `compute_airi_correlation_matrix.py`
  always correlates the detrended versions, matching the source paper's methodology.
- `data/indices/eof_pcs.csv` — PC1+PC2 time series (one row per year) for all 3 EOF variables, built by
  `compute_moron_eof_analysis.py`. Already detrended (computed from detrended fields), so
  `compute_airi_correlation_matrix.py` uses these columns as-is, no separate `_detrended` version.
- `data/indices/subregion_indices.csv` — detrended mean JJAS rainfall anomaly for CMZ/WG/SEI, built by
  `compute_subregion_indices.py`. Region boundary definitions came from the user, not derived - see that
  script's docstring for the exact CMZ boundary curve vertices, the WG rainy-day threshold, and the SEI
  rule. Has both raw and `_detrended` columns, same convention as `airi_indices.csv`.
- `data/sst/ersst.v5.mnmean.nc` — NOAA ERSSTv5 monthly SST, global 2°, 1854-present, downloaded whole
  (not pre-subset to 1901-2020) by `fetch_ersst.py` from NOAA PSL. Longitude is 0-360°, not -180/180 -
  convert before any Pacific/Indian Ocean region selection (e.g. Nino 3.4, DMI), same gotcha as the
  companion enso-sst-analysis project's SST handling. Latitude is DESCENDING (88 -> -88) in this file -
  `.sel(lat=slice(...))` needs (north, south) order, not (south, north), or the slice silently returns
  empty.
- `data/indices/enso_iod_indices.csv` — NINO3.4 + DMI, JJAS 1901-2020, built by
  `compute_enso_iod_indices.py` from the ERSST file above. Raw + `_detrended` columns, same convention as
  `airi_indices.csv`. Validated against the source paper's reported NINO3-vs-AIRI correlation (~-0.53,
  "virtually unchanged" for NINO3.4) - ours gives -0.54 detrended, a strong match.

`compute_moron_eof_analysis.py` (and `plot_eof_comparison.py`, which recomputes the same fields for a
subset comparison figure) run EOF decomposition (cos-lat weighted, via the `eofs` library, same
convention as the companion enso-sst-analysis project) on detrended-then-standardized (per-gridpoint)
versions of the same three fields underlying measures 3/4 of the AIRI CSV (rainfall mean, rainy-day
frequency, mean intensity), extracting EOF1/PC1 and EOF2/PC2 for each. Needs
`data/indices/airi_indices.csv` to exist first (used only to fix PC1's sign convention against AIRI's
detrended index). Note `scipy.signal.detrend` solves one batched least-squares fit across every grid
point at once - a NaN anywhere fails the whole call, not just that column - so NaN cells must be
filled before detrendin2g and re-masked after, not left as NaN going in.

Still needed: the ENSO (e.g. Nino 3.4) and IOD (Dipole Mode Index) index time series computed from the
SST record (not yet derived) - this is the next step, needed to correlate against the 14-column
AIRI/EOF/sub-region matrix already built.

`data/` is gitignored — do not assume its contents are committed. Update the data table in README.md
as datasets are added or computed.

## Environment gotcha: broken SSL on this machine

Python's `ssl.create_default_context()` fails on this machine with
`ssl.SSLError: [ASN1: NOT_ENOUGH_DATA]` when it falls back to loading the Windows certificate store
(some cert in the store doesn't parse). This breaks **any** unqualified HTTPS call from Python — not
just obvious ones like `urllib.request.urlopen`, but also code paths that build an SSL context
internally, e.g. `xarray.Dataset.to_netcdf()` itself fails via a dask→distributed→tornado import chain
that constructs one at import time. `cartopy`'s shapefile auto-downloads (Natural Earth, SRTM) hit the
same wall - and so does `eofs.xarray.Eof()` whenever it's handed a lazily-loaded (dask-backed) array,
since the solver forces a `.compute()` internally, which triggers the same dask scheduler-detection path
(see `compute_moron_eof_analysis.py`). The pattern to watch for: any surprising `ssl.SSLError` deep in an
unrelated traceback almost always traces back to this, regardless of what the script was actually doing.

Workaround used throughout this project: monkeypatch `ssl.create_default_context` at the top of any
script that touches the network or calls `to_netcdf`/`to_zarr`, to inject `cafile=certifi.where()`
whenever no explicit CA source was given — see the top of `fetch_elevation.py` for the exact patch.
Separately, PowerShell/`.NET` HTTP calls are unaffected by this bug (different SSL stack), which is how
the underlying data-source reachability was diagnosed.

Also worth knowing: NOAA's own domains (`ncei.noaa.gov`, `ngdc.noaa.gov`, `psl.noaa.gov`) all timed out
from this network the first time they were checked (hence `fetch_elevation.py` using an AWS-hosted
alternative instead), but were reachable again later (`fetch_ersst.py` downloaded straight from
`downloads.psl.noaa.gov` with no issue) - this network's NOAA reachability is apparently intermittent,
not a permanent block. Check reachability fresh each time rather than assuming either outcome from a
past session.

## Environment gotcha: PATH order breaks matplotlib rendering

If `$env:Path` has been rebuilt from the Machine+User registry values in the current shell (e.g. after
installing Git, or any `git`-related command in this session that did
`$env:Path = [System.Environment]::GetEnvironmentVariable(...)`), running matplotlib afterwards can
**crash the Python process outright** (native fault, exit code shows as 127 in the harness, actual
Windows exit code `-1066598273` / `0xC0000409`) — not a Python exception, so no traceback. Root cause:
something earlier in that rebuilt PATH (observed with Git for Windows present) shadows a DLL the conda
env's own Agg/FreeType rendering stack needs, causing an ABI mismatch crash specifically when
`fig.canvas.draw()` / `savefig()` actually renders (plain `import matplotlib` and `plt.subplots()` work
fine — it's the rendering call that dies). This is a real PATH-ordering bug, not memory pressure (initially
misdiagnosed as that; confirmed by isolating PATH to just the conda env and retesting).

Fix: before running any plotting script, set PATH to put the conda env's own directories first:
```powershell
$env:Path = "C:\Users\shrey\.conda\envs\podaac_env;C:\Users\shrey\.conda\envs\podaac_env\Library\mingw-w64\bin;C:\Users\shrey\.conda\envs\podaac_env\Library\usr\bin;C:\Users\shrey\.conda\envs\podaac_env\Library\bin;C:\Users\shrey\.conda\envs\podaac_env\Scripts;C:\Windows\System32;C:\Windows"
```
If a plotting script mysteriously produces no output and no error, check `$LASTEXITCODE` for
`-1066598273` before chasing anything else — it means this, not a bug in the script.

## Open issue: AIRI-vs-mean-intensity correlation doesn't match the source paper

The project is reproducing a specific paper's ("Spencer & Hill") 6-alternate-measures methodology and
its Figure 2 cross-correlation matrix. Reproduction is good but not exact for one cell:

- Paper's Figure 2: AIRI vs. mean intensity on rainy days = **0.77** (raw AIRI, not standardized).
- Our result: **0.58** raw, **0.63** after detrending both series (paper detrends before correlating -
  see below). Still a real gap.
- Everything else matches the paper closely: the "extent" group (standardized anomaly, N-positive,
  mean rainy days vs AIRI) all reproduce the paper's ">0.9" claim almost to 2 decimal places (0.97-0.98
  vs paper's .98/.96/.91). Mean-negative-anomaly vs AIRI, detrended, comes out to 0.76 - right at the
  paper's stated "no coefficient in this group exceeds 0.77" ceiling.

What's been ruled out (don't re-try these without new evidence):
- **Aggregation order**: per-gridpoint-then-spatial average (current) vs. pooling all rainy (day,
  gridpoint) values directly (flat/rain-weighted) - mathematically these can differ, but here give 0.58
  vs 0.57, i.e. the same thing within noise. Confirmed the paper's own wording ("average across all grid
  points OF [rainfall rate on rainy days]") literally specifies the per-gridpoint-first reading anyway.
- **Rainy-day threshold**: paper confirms 1mm/day, matches what we use. A threshold sweep (0/0.1/0.5/1/
  2.5mm) moves r within 0.55-0.71, never reaches 0.77 at any threshold, so this isn't a simple threshold
  mismatch either.
- **Area/cos(lat) weighting**: negligible effect (0.58 -> 0.59).
- **NE India / Bangladesh border data artifact**: the paper's Methods section names a specific corrupted
  grid-cell cluster (Gadgil et al. 2019 mask, JJAS mean/variance jumping in 1971). Checked this dataset's
  actual NE region (our `monsoon_mask` domain caps at lon 89E, lat 8.25-31.75N) for a pre/post-1971 level
  shift: none found (means differ by ~0.2mm/day, no gridpoint jumps >2mm/day). Either this file's mask
  already differs from the raw Gadgil mask, or the bad cluster is outside our domain entirely.
- **Detrending**: real effect in the right direction (implemented, now default for the correlation
  matrix) but only closes part of the gap (0.58 -> 0.63, not -> 0.77).

Not yet tried: getting the paper's actual replication code/supplementary methods (best next step if
available), or re-examining whether the paper's own AIRI is built differently than the JJAS-seasonal-
mean-anomaly definition used here. If you pick this back up, read the full conversation history for the
detailed back-and-forth rather than re-deriving from scratch.

Note this is a DIFFERENT quantity from PC1-intensity (the EOF-based measure in `eof_pcs.csv`) - don't
conflate the two when comparing against the paper's matrix. PC1-intensity's sign was separately corrected
(see Conventions below) once it became clear the paper shows it anti-correlated with AIRI; that fix is
already applied and doesn't touch this open issue.

## Conventions

- Map figures: crop to the data's actual extent rather than the full lat/lon grid (which extends past
  India's borders into empty cells), and skip political borders — coastline alone is enough for
  orientation and avoids clutter/contested-border-line issues. See `DATA_EXTENT` in
  `plot_jjas_climatology.py`.
- Secondary contour overlays (std dev, elevation, etc.) use a single dark color with linewidth
  increasing per level, plus inline labels — not a grayscale color ramp. Grayscale contour lines get
  visually lost against pale shading at the low end, and a fixed color scale (e.g. 100–900m) can
  misleadingly imply that's the data's actual range when cells go higher; the true max is reported as a
  text annotation instead.
- Fractions/ratios over a multi-year record (e.g. JJAS share of annual rainfall) are computed from
  pooled sums across all years (`jjas_total.sum('year') / annual_total.sum('year')`), not by averaging
  each year's own ratio — a single near-zero-rainfall year in a dry cell would otherwise skew a simple
  average. Simple day-counts (e.g. mean rainy days per season) don't need this - summing over the full
  multi-year time series and dividing by n_years is already equivalent to averaging each year's count.
- Don't lean on a single spatial Pearson r to claim two gridded fields "agree" — two fields sharing the
  same dominant climatological gradient (e.g. any two rainy-day-threshold definitions over India) will
  correlate very highly almost by construction, which can hide large practical differences. See
  `compare_rainy_day_thresholds.py` for the pattern to follow: report r if asked for, but pair it with
  a difference field and/or regression slope that shows what the correlation is masking.
- `compute_airi_indices.py`'s spatial averages are deliberately UNWEIGHTED (simple grid-point mean),
  matching the literal published definitions being reproduced there - don't "fix" this to cos(lat)
  weighting to match the EOF analysis convention elsewhere without checking first, it's intentional.
- When a boolean threshold mask (e.g. `precip > threshold`) is summed/averaged over space or time, cells
  outside the valid India domain silently count as `False`/0 rather than NaN (NaN comparisons are always
  False) - explicitly `.where(monsoon_mask.notnull())` the result before spatially averaging, or invalid
  cells will quietly dilute the average instead of being excluded. See `compute_airi_indices.py` for the
  pattern. This bug was originally introduced in `plot_jjas_rainy_days_intensity.py` / `_0mm.py` / `_1mm.py`
  / `compare_rainy_day_thresholds.py` (all fixed retroactively once found) - it didn't just shift numbers
  slightly, it changed the actual conclusion: the corrected regression between the >0mm and >1mm fields
  is a roughly constant ~11-13 day offset (slope ~1.04), not the proportional/wetness-scaling bias the
  buggy version suggested (slope ~1.21). If you add another rainy-day-threshold script, apply this fix
  from the start rather than after the fact.
- EOF sign conventions are picked per-variable, not uniformly. `compute_moron_eof_analysis.py` /
  `plot_eof_comparison.py`'s `TARGET_SIGN` dict fixes rainfall-amount and rainy-day-frequency PC1 to
  correlate POSITIVELY with AIRI, but mean-intensity PC1 to correlate NEGATIVELY - matching the source
  paper's own published correlation matrix (PC1-intensity is anti-correlated with AIRI there, while the
  other two are strongly positive). An earlier version forced positive correlation uniformly for all
  three, which was backwards for intensity specifically - there's no way to know the "right" sign for an
  EOF a priori, only by checking against a reference like the paper's reported values. If you add a 4th
  EOF variable, check its sign against the paper rather than assuming uniform-positive is safe.
- Sub-India region masks (`compute_subregion_indices.py`) are irregular, data-driven regions, not simple
  lat/lon boxes - don't simplify them back to a box "for clarity" without checking with the user first.
  CMZ in particular came out much bigger than the commonly-cited simplified box used elsewhere (~64% of
  the valid domain) - this was verified as a faithful implementation of the exact boundary curves given,
  not a bug, but hasn't been independently confirmed against the source paper's actual figure. Always
  regenerate and look at `figures/subregion_masks.png` after touching region-boundary logic - it's easy
  to introduce a subtle sign/direction error (e.g. north vs south boundary swapped, east vs west of a
  per-latitude edge) that still produces a plausible-looking but wrong mask.
