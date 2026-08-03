# India Rainfall Variability

Understanding the summer-mean relationships among the All-India Rainfall Index (AIRI), sub-India
regional rainfall, El Niño–Southern Oscillation (ENSO), and the Indian Ocean Dipole (IOD), using a
120-year sea surface temperature (SST) record and a high-resolution gridded rainfall dataset.

This project is a companion to [enso-sst-analysis](https://github.com/shreyasmily/enso-sst-analysis),
reusing similar tools (xarray/EOF-based climate analysis) applied to the India summer monsoon /
teleconnection problem.

## Status

Early stage — data collection in progress, no analysis scripts yet.

## Data

| Dataset | Status | Location |
|---|---|---|
| IMD gridded daily rainfall, 0.25°, monsoon-masked, 1901–2020 | On hand | `data/rainfall/imd_rain_daily_0p25_monsoon-masked_1901-2020.nc` |
| 120-year SST record (e.g. HadISST / ERSSTv5) | Not yet obtained | will go in `data/sst/` |
| ENSO index (e.g. Niño 3.4) | Not yet obtained — likely computed from the SST record | will go in `data/indices/` |
| IOD index (Dipole Mode Index) | Not yet obtained — likely computed from the SST record | will go in `data/indices/` |
| AIRI (All-India Rainfall Index) | Not yet obtained — likely computed by area-averaging the IMD rainfall grid | will go in `data/indices/` |

Raw and intermediate data files are not committed to this repository (see `.gitignore`) — they're too
large for GitHub. Only code, figures, and documentation are tracked.

## Setup

```
conda activate podaac_env
pip install -r requirements.txt
```

## Repository structure

```
data/            (gitignored) raw + intermediate datasets
figures/         result figures, once produced
docs/            write-ups / notes
```

Analysis scripts will be added at the project root as the pipeline develops.
