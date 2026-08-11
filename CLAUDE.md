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
  mm/day, one is a unitless standardized anomaly, one is a raw grid-point count).

Still needed: a 120-year SST dataset (for ENSO/IOD index computation), and the ENSO/IOD index time
series themselves (not yet derived).

`data/` is gitignored — do not assume its contents are committed. Update the data table in README.md
as datasets are added or computed.

## Environment gotcha: broken SSL on this machine

Python's `ssl.create_default_context()` fails on this machine with
`ssl.SSLError: [ASN1: NOT_ENOUGH_DATA]` when it falls back to loading the Windows certificate store
(some cert in the store doesn't parse). This breaks **any** unqualified HTTPS call from Python — not
just obvious ones like `urllib.request.urlopen`, but also code paths that build an SSL context
internally, e.g. `xarray.Dataset.to_netcdf()` itself fails via a dask→distributed→tornado import chain
that constructs one at import time. `cartopy`'s shapefile auto-downloads (Natural Earth, SRTM) hit the
same wall.

Workaround used throughout this project: monkeypatch `ssl.create_default_context` at the top of any
script that touches the network or calls `to_netcdf`/`to_zarr`, to inject `cafile=certifi.where()`
whenever no explicit CA source was given — see the top of `fetch_elevation.py` for the exact patch.
Separately, PowerShell/`.NET` HTTP calls are unaffected by this bug (different SSL stack), which is how
the underlying data-source reachability was diagnosed.

Also worth knowing: NOAA's own domains (`ncei.noaa.gov`, `ngdc.noaa.gov`, `psl.noaa.gov`) all timed out
from this network when checked; other hosts (GitHub, AWS S3, USGS, GEBCO, OpenTopography) were reachable.
If a script needs NOAA-hosted data (e.g. HadISST/ERSST mirrors), check reachability first rather than
assuming the NOAA host will respond.

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
  pattern.
