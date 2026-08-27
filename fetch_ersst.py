"""
One-time data download: NOAA ERSSTv5 (Extended Reconstructed SST v5), monthly,
global, 2x2 degree, from NOAA PSL:
https://downloads.psl.noaa.gov/Datasets/noaa.ersst.v5/sst.mnmean.nc

The full record as distributed (1854-present) is kept intact - downstream
scripts should subset to the 1901-2020 period this project needs, rather than
trimming here, matching how the IMD rainfall file is handled (kept whole,
subset by each analysis script).
"""
import ssl
import certifi
import os
import urllib.request

# Same Windows-cert-store SSL workaround used throughout this project.
_orig_create_default_context = ssl.create_default_context


def _certifi_default_context(*args, **kwargs):
    if 'cafile' not in kwargs and 'capath' not in kwargs and 'cadata' not in kwargs:
        kwargs['cafile'] = certifi.where()
    return _orig_create_default_context(*args, **kwargs)


ssl.create_default_context = _certifi_default_context

URL = 'https://downloads.psl.noaa.gov/Datasets/noaa.ersst.v5/sst.mnmean.nc'
OUT_PATH = 'data/sst/ersst.v5.mnmean.nc'

os.makedirs('data/sst', exist_ok=True)
print(f'Downloading {URL} ...')
ctx = ssl.create_default_context(cafile=certifi.where())
with urllib.request.urlopen(URL, timeout=120, context=ctx) as resp, open(OUT_PATH, 'wb') as f:
    total = int(resp.headers.get('Content-Length', 0))
    downloaded = 0
    chunk_size = 1024 * 1024
    while True:
        chunk = resp.read(chunk_size)
        if not chunk:
            break
        f.write(chunk)
        downloaded += len(chunk)
        if total:
            print(f'\r  {downloaded / 1e6:.1f} / {total / 1e6:.1f} MB', end='', flush=True)
print()
print(f'Saved {OUT_PATH}')

import xarray as xr
ds = xr.open_dataset(OUT_PATH)
print(ds)
print(f"Time range: {ds.time.values[0]} to {ds.time.values[-1]}")
