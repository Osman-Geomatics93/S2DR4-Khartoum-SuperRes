"""
S2DR4 Super-Resolution Inference for Khartoum, Sudan
Run inside WSL2 with the s2dr4_env activated:
    source ~/s2dr4_env/bin/activate
    python /mnt/d/Udemy_Cour/Gamma\ Earth\ S2DR4/run_s2dr4.py
"""
import os
import sys
import shutil

# Output directory — results saved here
OUTPUT_DIR = os.path.expanduser("~/s2dr4_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# S2DR4 expects output at /content/output (Google Colab convention)
# Create a symlink so it works locally
COLAB_OUTPUT = "/content/output"
if not os.path.exists("/content"):
    os.makedirs("/content", exist_ok=True)
if os.path.islink(COLAB_OUTPUT):
    os.unlink(COLAB_OUTPUT)
if not os.path.exists(COLAB_OUTPUT):
    os.symlink(OUTPUT_DIR, COLAB_OUTPUT)

print("=" * 60)
print("S2DR4 Super-Resolution Inference")
print("=" * 60)

# Import S2DR4
try:
    import s2dr4.inferutils
except ImportError:
    print("ERROR: s2dr4 not installed. Run setup_wsl.sh first.")
    sys.exit(1)

# ─── Configuration ───────────────────────────────────────────
# Khartoum center coordinates (lon, lat) — NOTE: X, Y format!
# Derived from your data: EPSG:32636 center (452800, 1713760)
LONLAT = (32.53, 15.50)

# Target date — matching your data filename date
DATE = "2026-02-04"

print(f"  Location:  Khartoum, Sudan")
print(f"  Lon/Lat:   {LONLAT}")
print(f"  Date:      {DATE}")
print(f"  Output:    {OUTPUT_DIR}")
print(f"  Area:      4 x 4 km")
print(f"  Target:    1 m/px (10x super-resolution)")
print()

# ─── Run Inference ───────────────────────────────────────────
print("Starting S2DR4 inference...")
print("This will:")
print("  1. Fetch Sentinel-2 data from Copernicus for this location/date")
print("  2. Preprocess multiple nearby dates for the model")
print("  3. Run deep learning super-resolution (10m → 1m)")
print("  4. Generate output GeoTIFFs")
print()

s2dr4.inferutils.test(LONLAT, DATE)

# ─── Copy results to Windows-accessible folder ──────────────
WIN_OUTPUT = "/mnt/d/Udemy_Cour/Gamma Earth S2DR4/output"
os.makedirs(WIN_OUTPUT, exist_ok=True)

print(f"\nCopying results to Windows folder: D:\\Udemy_Cour\\Gamma Earth S2DR4\\output")
for f in os.listdir(OUTPUT_DIR):
    if f.endswith(".tif"):
        src = os.path.join(OUTPUT_DIR, f)
        dst = os.path.join(WIN_OUTPUT, f)
        shutil.copy2(src, dst)
        size_mb = os.path.getsize(dst) / (1024 * 1024)
        print(f"  Copied: {f} ({size_mb:.1f} MB)")

print("\n" + "=" * 60)
print("DONE! Super-resolved 1m GeoTIFFs are in:")
print(f"  WSL:     {OUTPUT_DIR}")
print(f"  Windows: D:\\Udemy_Cour\\Gamma Earth S2DR4\\output")
print("=" * 60)
