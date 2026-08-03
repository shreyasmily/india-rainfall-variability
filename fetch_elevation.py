"""
One-time data prep: build a surface elevation grid matching the IMD 0.25deg
rainfall grid, from AWS-hosted "Terrarium" elevation tiles (Mapzen's public
terrain tile set, now distributed as an AWS Open Data set at
s3://elevation-tiles-prod, no auth required):
https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png

NOAA's own DEM hosts (ncei.noaa.gov, ngdc.noaa.gov, psl.noaa.gov) were all
unreachable (timed out) from this network when this was written, hence using
this AWS-hosted alternative instead.

Terrarium tiles are 256x256px, Web Mercator, zoom levels like standard slippy
map tiles. Elevation (m) is encoded in the RGB channels as:
    elevation = (R * 256 + G + B / 256) - 32768
Zoom 7 gives ~0.011deg/pixel, i.e. roughly 22x22 sub-pixels per output 0.25deg
cell, which is fine resolution for a simple area-average onto the coarser grid
(this is a rough approximation, not a precision DEM regrid).

Output: data/elevation/india_elevation_0p25deg.nc, an xarray Dataset with
'elevation' (m) on lat/lon coordinates matching the IMD rainfall grid exactly.
"""
import io
import os
import ssl
import urllib.request

import certifi
import numpy as np
import xarray as xr
from PIL import Image

# This machine's Windows certificate store has a cert ssl.create_default_context()
# can't parse (ssl.SSLError: [ASN1: NOT_ENOUGH_DATA]). That breaks not just our own
# downloads but ANY code path that calls ssl.create_default_context() without an
# explicit cafile - including, surprisingly, xarray.to_netcdf() itself (it probes
# for an active dask distributed client, which imports tornado, which builds an SSL
# context at import time). Patch the stdlib function process-wide to fall back to
# certifi's CA bundle instead of the broken Windows store.
_orig_create_default_context = ssl.create_default_context


def _certifi_default_context(*args, **kwargs):
    # `purpose` is commonly passed positionally (e.g. tornado does this), but
    # cafile/capath/cadata are not - safe to inject cafile whenever none of the
    # three were explicitly given as keywords.
    if 'cafile' not in kwargs and 'capath' not in kwargs and 'cadata' not in kwargs:
        kwargs['cafile'] = certifi.where()
    return _orig_create_default_context(*args, **kwargs)


ssl.create_default_context = _certifi_default_context

SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

ZOOM = 7
TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"

# Match the IMD grid's cell centers/edges exactly.
ds_rain = xr.open_dataset('data/rainfall/imd_rain_daily_0p25_monsoon-masked_1901-2020.nc')
lat_centers = ds_rain.lat.values
lon_centers = ds_rain.lon.values
lat_edges = np.concatenate([lat_centers - 0.125, lat_centers[-1:] + 0.125])
lon_edges = np.concatenate([lon_centers - 0.125, lon_centers[-1:] + 0.125])


def lonlat_to_tile(lon, lat, z):
    n = 2 ** z
    x = int(np.floor((lon + 180.0) / 360.0 * n))
    lat_rad = np.radians(lat)
    y = int(np.floor((1.0 - np.arcsinh(np.tan(lat_rad)) / np.pi) / 2.0 * n))
    return x, y


def tile_pixel_lonlat(x, y, z):
    """Return (256,256) lon/lat arrays for every pixel center in tile (x,y,z)."""
    n = 2 ** z
    px = np.arange(256) + 0.5
    lon = (x + px / 256.0) / n * 360.0 - 180.0
    py = np.arange(256) + 0.5
    merc_y = 1.0 - 2.0 * (y + py / 256.0) / n
    lat = np.degrees(np.arctan(np.sinh(np.pi * merc_y)))
    lon2d, lat2d = np.meshgrid(lon, lat)
    return lon2d, lat2d


# Tile range covering the rainfall grid's extent, with a 1-tile margin.
lon_min, lon_max = float(lon_edges.min()), float(lon_edges.max())
lat_min, lat_max = float(lat_edges.min()), float(lat_edges.max())

x0, y0 = lonlat_to_tile(lon_min, lat_max, ZOOM)  # top-left (max lat, min lon)
x1, y1 = lonlat_to_tile(lon_max, lat_min, ZOOM)  # bottom-right (min lat, max lon)
x_range = range(x0 - 1, x1 + 2)
y_range = range(y0 - 1, y1 + 2)
n_tiles = len(list(x_range)) * len(list(y_range))
print(f"Fetching {n_tiles} tiles at zoom {ZOOM}...")

elev_sum = np.zeros((len(lat_centers), len(lon_centers)))
elev_count = np.zeros((len(lat_centers), len(lon_centers)))

os.makedirs('data/elevation', exist_ok=True)

for xi in x_range:
    for yi in y_range:
        url = TILE_URL.format(z=ZOOM, x=xi, y=yi)
        try:
            with urllib.request.urlopen(url, timeout=20, context=SSL_CONTEXT) as resp:
                img = Image.open(io.BytesIO(resp.read())).convert('RGB')
        except Exception as e:
            print(f"  skipped tile {xi},{yi}: {e}")
            continue

        arr = np.array(img).astype(np.float64)
        r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
        elev = (r * 256 + g + b / 256) - 32768

        lon2d, lat2d = tile_pixel_lonlat(xi, yi, ZOOM)

        lat_idx = np.searchsorted(lat_edges, lat2d.ravel()) - 1
        lon_idx = np.searchsorted(lon_edges, lon2d.ravel()) - 1
        elev_flat = elev.ravel()

        valid = (
            (lat_idx >= 0) & (lat_idx < len(lat_centers)) &
            (lon_idx >= 0) & (lon_idx < len(lon_centers))
        )
        np.add.at(elev_sum, (lat_idx[valid], lon_idx[valid]), elev_flat[valid])
        np.add.at(elev_count, (lat_idx[valid], lon_idx[valid]), 1)

    print(f"  column x={xi} done")

with np.errstate(invalid='ignore'):
    elevation = elev_sum / elev_count
elevation[elev_count == 0] = np.nan

out = xr.Dataset(
    {'elevation': (('lat', 'lon'), elevation)},
    coords={'lat': lat_centers, 'lon': lon_centers},
)
out['elevation'].attrs['units'] = 'm'
out['elevation'].attrs['source'] = 'AWS Terrarium terrain tiles (s3://elevation-tiles-prod), zoom 7, area-averaged to 0.25deg'

out.to_netcdf('data/elevation/india_elevation_0p25deg.nc')
print(f"Saved data/elevation/india_elevation_0p25deg.nc | "
      f"elevation range: {np.nanmin(elevation):.1f} to {np.nanmax(elevation):.1f} m")
