"""
Compare original 10m data with super-resolved 1m results.
Run: python compare_results.py
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
ORIGINAL_DIR = os.path.join(PROJECT_ROOT, "Data")
SR_DIR = os.path.join(PROJECT_ROOT, "S2DR4_Khartoum_1m", "SD", "T36PVC", "T36PVC-9a3aee44d")

print("=" * 80)
print("COMPARISON: Original 10m vs Super-Resolved 1m")
print("=" * 80)

# ── Original 10m data ──
print("\n── ORIGINAL 10m DATA ──")
for fname in sorted(os.listdir(ORIGINAL_DIR)):
    if not fname.endswith('.tif'):
        continue
    fpath = os.path.join(ORIGINAL_DIR, fname)
    with rasterio.open(fpath) as ds:
        size_mb = os.path.getsize(fpath) / (1024 * 1024)
        print(f"  {fname}")
        print(f"    {ds.width}x{ds.height} px | {ds.count} bands | {abs(ds.transform.a):.0f}m/px | {size_mb:.1f} MB")

# ── Super-resolved 1m data ──
print("\n── SUPER-RESOLVED 1m DATA ──")
for fname in sorted(os.listdir(SR_DIR)):
    if not fname.endswith('.tif'):
        continue
    fpath = os.path.join(SR_DIR, fname)
    with rasterio.open(fpath) as ds:
        size_mb = os.path.getsize(fpath) / (1024 * 1024)
        print(f"  {fname}")
        print(f"    {ds.width}x{ds.height} px | {ds.count} bands | {abs(ds.transform.a):.1f}m/px | {size_mb:.1f} MB")
        print(f"    CRS: {ds.crs} | Dtype: {ds.dtypes[0]}")
        b = ds.bounds
        print(f"    Bounds: L={b.left:.1f} B={b.bottom:.1f} R={b.right:.1f} T={b.top:.1f}")
        print(f"    Extent: {b.right-b.left:.0f} x {b.top-b.bottom:.0f} m")
        if ds.descriptions and any(ds.descriptions):
            print(f"    Bands: {ds.descriptions}")

        # Stats
        print(f"    Band Statistics (NaN-safe):")
        total_px = ds.width * ds.height
        for i in range(1, ds.count + 1):
            data = ds.read(i)
            nan_count = np.isnan(data).sum() if np.issubdtype(data.dtype, np.floating) else 0
            valid = total_px - nan_count
            name = ds.descriptions[i-1] if ds.descriptions and ds.descriptions[i-1] else f"B{i}"
            if valid > 0:
                print(f"      {name:>5}: min={np.nanmin(data):.4f} max={np.nanmax(data):.4f} "
                      f"mean={np.nanmean(data):.4f} | {valid}/{total_px} valid")
            else:
                print(f"      {name:>5}: ALL NaN")
        print()

# ── Direct comparison on MS product ──
print("── RESOLUTION COMPARISON ──")
orig_ms = os.path.join(ORIGINAL_DIR, "S2_Khartoum_khartoum_center_20260204_10bands.tif")
sr_ms = os.path.join(SR_DIR, "S2L3Ax10_T36PVC-9a3aee44d-20260131_MS.tif")

with rasterio.open(orig_ms) as o, rasterio.open(sr_ms) as s:
    print(f"  {'':>20} {'Original':>15} {'Super-Resolved':>15} {'Factor':>10}")
    print(f"  {'Width (px)':>20} {o.width:>15} {s.width:>15} {s.width/o.width:>10.1f}x")
    print(f"  {'Height (px)':>20} {o.height:>15} {s.height:>15} {s.height/o.height:>10.1f}x")
    print(f"  {'Pixel size (m)':>20} {abs(o.transform.a):>15.1f} {abs(s.transform.a):>15.1f} {abs(o.transform.a)/abs(s.transform.a):>10.1f}x")
    print(f"  {'Bands':>20} {o.count:>15} {s.count:>15}")
    print(f"  {'Total pixels':>20} {o.width*o.height:>15,} {s.width*s.height:>15,} {(s.width*s.height)/(o.width*o.height):>10.1f}x")

print(f"\n{'=' * 80}")
print("DONE. Copy and paste ALL output above back to Claude.")
print("=" * 80)
