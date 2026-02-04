"""
Inspect GeoTIFF files - NaN-safe version.
Run: python inspect_data_v2.py
"""
import os, sys

try:
    import rasterio
    import numpy as np
except ImportError:
    os.system(f"{sys.executable} -m pip install rasterio numpy")
    import rasterio
    import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "Data")

tif_files = sorted(f for f in os.listdir(DATA_DIR) if f.lower().endswith(('.tif', '.tiff')))
print("=" * 80)
print(f"Found {len(tif_files)} GeoTIFF files in: {DATA_DIR}")
print("=" * 80)

for fname in tif_files:
    fpath = os.path.join(DATA_DIR, fname)
    print(f"\n{'─' * 80}")
    print(f"FILE: {fname}  ({os.path.getsize(fpath) / (1024*1024):.2f} MB)")
    print(f"{'─' * 80}")

    with rasterio.open(fpath) as ds:
        print(f"  Dimensions:  {ds.width} x {ds.height} px, {ds.count} bands")
        print(f"  Dtype:       {ds.dtypes[0]}")
        print(f"  CRS:         {ds.crs}  (EPSG:{ds.crs.to_epsg()})")
        print(f"  Pixel size:  {abs(ds.transform.a):.2f} m")
        b = ds.bounds
        print(f"  Bounds:      L={b.left:.1f} B={b.bottom:.1f} R={b.right:.1f} T={b.top:.1f}")
        print(f"  Extent:      {b.right-b.left:.0f} x {b.top-b.bottom:.0f} m")
        if ds.descriptions and any(ds.descriptions):
            print(f"  Band names:  {ds.descriptions}")

        total_px = ds.width * ds.height
        data_all = ds.read()

        # Count NaN vs valid
        nan_per_band = np.isnan(data_all).sum(axis=(1, 2))
        valid_per_band = total_px - nan_per_band
        all_nan = np.isnan(data_all).all()
        any_valid = not all_nan

        print(f"\n  Total pixels per band: {total_px}")
        print(f"  ALL data is NaN:       {all_nan}")

        if any_valid:
            print(f"\n  Band Statistics (NaN-safe):")
            print(f"  {'Band':>6} {'Name':>6} {'Valid':>8} {'NaN':>8} {'Min':>12} {'Max':>12} {'Mean':>12} {'Std':>12}")
            for i in range(ds.count):
                band = data_all[i]
                name = ds.descriptions[i] if ds.descriptions and ds.descriptions[i] else f"B{i+1}"
                v = valid_per_band[i]
                n = nan_per_band[i]
                if v > 0:
                    print(f"  {i+1:>6} {name:>6} {v:>8} {n:>8} "
                          f"{np.nanmin(band):>12.6f} {np.nanmax(band):>12.6f} "
                          f"{np.nanmean(band):>12.6f} {np.nanstd(band):>12.6f}")
                else:
                    print(f"  {i+1:>6} {name:>6} {v:>8} {n:>8}  ** ALL NaN **")

            # Percentiles for band 1 (sample)
            sample = data_all[0]
            valid_vals = sample[~np.isnan(sample)]
            if len(valid_vals) > 0:
                pcts = np.percentile(valid_vals, [1, 5, 25, 50, 75, 95, 99])
                print(f"\n  Percentiles for Band 1 ({ds.descriptions[0] if ds.descriptions else 'B1'}):")
                print(f"    P1={pcts[0]:.6f}  P5={pcts[1]:.6f}  P25={pcts[2]:.6f}  "
                      f"P50={pcts[3]:.6f}  P75={pcts[4]:.6f}  P95={pcts[5]:.6f}  P99={pcts[6]:.6f}")
        else:
            print("\n  *** WARNING: ALL pixels are NaN - this file contains NO valid data! ***")

print(f"\n{'=' * 80}")
print("DONE. Copy and paste ALL output above back to Claude.")
print("=" * 80)
