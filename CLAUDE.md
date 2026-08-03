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

Still needed: a 120-year SST dataset (for ENSO/IOD index computation), and possibly precomputed
AIRI/ENSO/IOD index time series if not deriving them locally.

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
  average.
