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

No analysis scripts exist yet. One dataset is on hand:
`data/rainfall/imd_rain_daily_0p25_monsoon-masked_1901-2020.nc` — IMD gridded daily rainfall, 0.25°,
monsoon-masked, 1901–2020, covering `lat 6.5–38.5, lon 66.5–100` (dims: `time, lat, lon`, variable
`precip`). Still needed: a 120-year SST dataset (for ENSO/IOD index computation), and possibly
precomputed AIRI/ENSO/IOD index time series if not deriving them locally.

`data/` is gitignored — do not assume its contents are committed. Update the data table in README.md
as datasets are added or computed.

## Conventions

None established yet — this section should be filled in once the first analysis scripts exist (data
loading patterns, index computation methodology, sign conventions, etc.), following the pattern used in
`enso-sst-analysis/CLAUDE.md`.
