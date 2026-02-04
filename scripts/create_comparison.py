"""
Create interactive HTML comparison: 10m vs 1m Super-Resolution.
Generates a self-contained HTML file with a full-viewport drag slider.
Uses the FULL SR extent; pads original 10m with black where it doesn't cover.
Run: python create_comparison.py
"""
import os, sys, base64, io, webbrowser

# ── Step 1: Auto-install dependencies ──
for pkg in ["rasterio", "numpy", "Pillow"]:
    try:
        __import__(pkg if pkg != "Pillow" else "PIL")
    except ImportError:
        os.system(f'"{sys.executable}" -m pip install {pkg}')

import rasterio
import numpy as np
from rasterio.windows import from_bounds
from PIL import Image

# ── Paths ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(SCRIPT_DIR)
ORIG_DIR = os.path.join(BASE, "Data")
SR_DIR = os.path.join(BASE, "S2DR4_Khartoum_1m", "SD", "T36PVC", "T36PVC-9a3aee44d")

ORIG_10BANDS = os.path.join(ORIG_DIR, "S2_Khartoum_khartoum_center_20260204_10bands.tif")
SR_TCI = os.path.join(SR_DIR, "S2L3Ax10_T36PVC-9a3aee44d-20260131_TCI.tif")
SR_IRP = os.path.join(SR_DIR, "S2L3Ax10_T36PVC-9a3aee44d-20260131_IRP.tif")
SR_NDVI = os.path.join(SR_DIR, "S2L3Ax10_T36PVC-9a3aee44d-20260131_NDVI.tif")

OUTPUT_HTML = os.path.join(BASE, "comparison.html")
MAX_DIM = 2048
JPEG_QUALITY = 88


def get_info(path):
    with rasterio.open(path) as ds:
        return ds.bounds, ds.crs, abs(ds.transform.a), ds.width, ds.height


def read_full(path, bands=None):
    """Read full raster."""
    with rasterio.open(path) as ds:
        if bands is None:
            bands = list(range(1, ds.count + 1))
        return ds.read(bands), ds.bounds, ds.transform


def read_within_bounds(path, target_bounds, target_w, target_h, bands=None):
    """Read raster data, placing it correctly within target_bounds.
    Pixels outside the source extent are filled with 0 (black).
    Returns (C, target_h, target_w) uint8 or float array.
    """
    with rasterio.open(path) as ds:
        if bands is None:
            bands = list(range(1, ds.count + 1))
        nbands = len(bands)
        src_bounds = ds.bounds
        src_res = abs(ds.transform.a)

        # Target pixel grid
        tgt_res_x = (target_bounds.right - target_bounds.left) / target_w
        tgt_res_y = (target_bounds.top - target_bounds.bottom) / target_h

        # Compute overlap in target pixel coordinates
        ol_left = max(src_bounds.left, target_bounds.left)
        ol_bottom = max(src_bounds.bottom, target_bounds.bottom)
        ol_right = min(src_bounds.right, target_bounds.right)
        ol_top = min(src_bounds.top, target_bounds.top)

        if ol_left >= ol_right or ol_bottom >= ol_top:
            # No overlap at all
            return np.zeros((nbands, target_h, target_w), dtype=np.float32)

        # Target pixel positions for the overlap region
        col_start = int(round((ol_left - target_bounds.left) / tgt_res_x))
        col_end = int(round((ol_right - target_bounds.left) / tgt_res_x))
        row_start = int(round((target_bounds.top - ol_top) / tgt_res_y))
        row_end = int(round((target_bounds.top - ol_bottom) / tgt_res_y))

        col_start = max(0, min(col_start, target_w))
        col_end = max(0, min(col_end, target_w))
        row_start = max(0, min(row_start, target_h))
        row_end = max(0, min(row_end, target_h))

        # Read the overlap region from source
        window = from_bounds(ol_left, ol_bottom, ol_right, ol_top, transform=ds.transform)
        data = ds.read(bands, window=window)

        # Resize source data to match the target pixel dimensions of the overlap
        overlap_w = col_end - col_start
        overlap_h = row_end - row_start

        if overlap_w <= 0 or overlap_h <= 0:
            return np.zeros((nbands, target_h, target_w), dtype=data.dtype)

        # Place into output
        output = np.zeros((nbands, target_h, target_w), dtype=data.dtype)
        # Resize each band to overlap dimensions
        for b in range(nbands):
            band_img = Image.fromarray(data[b])
            band_resized = band_img.resize((overlap_w, overlap_h), Image.NEAREST)
            output[b, row_start:row_end, col_start:col_end] = np.array(band_resized)

        return output


def float_to_uint8(arr, percentile_low=2, percentile_high=98):
    valid = arr[(~np.isnan(arr)) & (arr != 0)]
    if len(valid) == 0:
        return np.zeros_like(arr, dtype=np.uint8)
    low = np.percentile(valid, percentile_low)
    high = np.percentile(valid, percentile_high)
    if high <= low:
        high = low + 1
    stretched = (arr - low) / (high - low) * 255
    result = np.clip(stretched, 0, 255).astype(np.uint8)
    # Keep black where original was 0/NaN (no data)
    result[np.isnan(arr) | (arr == 0)] = 0
    return result


def ndvi_colormap(ndvi):
    ndvi_norm = np.clip((ndvi + 1) / 2, 0, 1)
    r = np.zeros_like(ndvi_norm, dtype=np.float64)
    g = np.zeros_like(ndvi_norm, dtype=np.float64)
    b = np.zeros_like(ndvi_norm, dtype=np.float64)

    mask = ndvi_norm < 0.3
    r[mask] = 140; g[mask] = 90; b[mask] = 50

    mask = (ndvi_norm >= 0.3) & (ndvi_norm < 0.5)
    t = (ndvi_norm[mask] - 0.3) / 0.2
    r[mask] = 140 + t * 80; g[mask] = 90 + t * 110; b[mask] = 50 + t * 30

    mask = (ndvi_norm >= 0.5) & (ndvi_norm < 0.7)
    t = (ndvi_norm[mask] - 0.5) / 0.2
    r[mask] = 220 - t * 170; g[mask] = 200 - t * 40; b[mask] = 80 - t * 50

    mask = ndvi_norm >= 0.7
    t = (ndvi_norm[mask] - 0.7) / 0.3
    r[mask] = 50 - t * 40; g[mask] = 160 - t * 30; b[mask] = 30 + t * 10

    nan_mask = np.isnan(ndvi)
    r[nan_mask] = 0; g[nan_mask] = 0; b[nan_mask] = 0

    return np.stack([np.clip(r, 0, 255).astype(np.uint8),
                     np.clip(g, 0, 255).astype(np.uint8),
                     np.clip(b, 0, 255).astype(np.uint8)])


def array_to_image(arr_3band):
    return Image.fromarray(np.transpose(arr_3band, (1, 2, 0)))


def upsample_nearest(img, factor):
    w, h = img.size
    return img.resize((w * factor, h * factor), Image.NEAREST)


def encode_image(img, max_dim=MAX_DIM, quality=JPEG_QUALITY):
    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode("ascii")


print("=" * 60)
print("Creating interactive 10m vs 1m comparison...")
print("=" * 60)

# ── Step 2: Get extents — use FULL SR extent as reference ──
print("\n[1/7] Reading extents...")
orig_bounds, orig_crs, pixel_size_orig, _, _ = get_info(ORIG_10BANDS)
sr_bounds, sr_crs, pixel_size_sr, sr_w, sr_h = get_info(SR_TCI)

print(f"  Original 10m: L={orig_bounds.left:.0f} B={orig_bounds.bottom:.0f} "
      f"R={orig_bounds.right:.0f} T={orig_bounds.top:.0f} ({pixel_size_orig:.0f}m/px)")
print(f"  SR 1m:        L={sr_bounds.left:.0f} B={sr_bounds.bottom:.0f} "
      f"R={sr_bounds.right:.0f} T={sr_bounds.top:.0f} ({pixel_size_sr:.1f}m/px)")
print(f"  SR image size: {sr_w} x {sr_h} px")
print(f"  SR extent: {sr_bounds.right - sr_bounds.left:.0f} x {sr_bounds.top - sr_bounds.bottom:.0f} m")

# Use the FULL SR extent — original will be padded with black where it doesn't cover
ref_bounds = sr_bounds
ref_w = sr_w
ref_h = sr_h

upsample_factor = int(round(pixel_size_orig / pixel_size_sr))
print(f"  Upsample factor: {upsample_factor}x")

# ── Step 3: Read band info ──
print("\n[2/7] Reading band information...")
with rasterio.open(ORIG_10BANDS) as ds:
    band_names = ds.descriptions
    band_map = {}
    for i, name in enumerate(band_names):
        if name:
            band_map[name.strip()] = i + 1
    print(f"  Band names: {band_names}")

def find_band(bmap, candidates):
    for c in candidates:
        if c in bmap:
            return bmap[c]
    return None

b2_idx = find_band(band_map, ["B2", "B02", "Blue"])
b3_idx = find_band(band_map, ["B3", "B03", "Green"])
b4_idx = find_band(band_map, ["B4", "B04", "Red"])
b8_idx = find_band(band_map, ["B8", "B08", "NIR"])

if any(x is None for x in [b2_idx, b3_idx, b4_idx, b8_idx]):
    print("  Using fallback band order: B2=1, B3=2, B4=3, B8=7")
    b2_idx, b3_idx, b4_idx, b8_idx = 1, 2, 3, 7

print(f"  B2={b2_idx}, B3={b3_idx}, B4={b4_idx}, B8={b8_idx}")

# We need original at same pixel grid as SR for the left side
# Original pixels in the SR grid:
orig_grid_w = ref_w  # same pixel count, same extent
orig_grid_h = ref_h

# ── Step 4: Build composites — FULL SR extent ──
print("\n[3/7] Building original 10m composites (full SR extent)...")

# Read original bands within SR bounds (will be padded with black outside original extent)
rgb_orig_data = read_within_bounds(ORIG_10BANDS, ref_bounds, ref_w, ref_h,
                                    bands=[b4_idx, b3_idx, b2_idx])
rgb_orig_u8 = np.stack([float_to_uint8(rgb_orig_data[i]) for i in range(3)])
rgb_orig_img = array_to_image(rgb_orig_u8)
print(f"  RGB original: {rgb_orig_img.size}")

fc_orig_data = read_within_bounds(ORIG_10BANDS, ref_bounds, ref_w, ref_h,
                                   bands=[b8_idx, b4_idx, b3_idx])
fc_orig_u8 = np.stack([float_to_uint8(fc_orig_data[i]) for i in range(3)])
fc_orig_img = array_to_image(fc_orig_u8)
print(f"  False Color original: {fc_orig_img.size}")

nir_data = read_within_bounds(ORIG_10BANDS, ref_bounds, ref_w, ref_h, bands=[b8_idx])
red_data = read_within_bounds(ORIG_10BANDS, ref_bounds, ref_w, ref_h, bands=[b4_idx])
nir = nir_data[0].astype(np.float64)
red = red_data[0].astype(np.float64)
denom = nir + red
ndvi_orig = np.where((denom != 0) & (nir != 0), (nir - red) / denom, np.nan)
ndvi_orig_rgb = ndvi_colormap(ndvi_orig)
ndvi_orig_img = array_to_image(ndvi_orig_rgb)
print(f"  NDVI original: {ndvi_orig_img.size}")

print("\n[4/7] Building super-resolved 1m composites (full extent)...")

rgb_sr_data, _, _ = read_full(SR_TCI)
rgb_sr_img = array_to_image(rgb_sr_data[:3])
print(f"  RGB SR: {rgb_sr_img.size}")

fc_sr_data, _, _ = read_full(SR_IRP)
fc_sr_img = array_to_image(fc_sr_data[:3])
print(f"  False Color SR: {fc_sr_img.size}")

ndvi_sr_data, _, _ = read_full(SR_NDVI)
ndvi_sr_img = array_to_image(ndvi_sr_data[:3])
print(f"  NDVI SR: {ndvi_sr_img.size}")

# ── Step 5: Encode as base64 ──
print("\n[5/7] Encoding images...")
images = {
    "rgb_orig": encode_image(rgb_orig_img),
    "rgb_sr": encode_image(rgb_sr_img),
    "fc_orig": encode_image(fc_orig_img),
    "fc_sr": encode_image(fc_sr_img),
    "ndvi_orig": encode_image(ndvi_orig_img),
    "ndvi_sr": encode_image(ndvi_sr_img),
}
total_kb = sum(len(v) * 3 / 4 for v in images.values()) / 1024
print(f"  Total image data: {total_kb:.0f} KB ({total_kb/1024:.1f} MB)")

# ── Step 6: Compute display info ──
sr_extent_m = f"{sr_bounds.right - sr_bounds.left:.0f} x {sr_bounds.top - sr_bounds.bottom:.0f}"

# ── Step 7: Generate HTML ──
print("\n[6/7] Generating HTML...")

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Khartoum Super-Resolution: 10m vs 1m</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: #0a0e17; color: #e0e6f0; overflow: hidden;
    width: 100vw; height: 100vh;
  }}

  .compare-wrap {{
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    display: flex; align-items: center; justify-content: center;
    background: #0a0e17; overflow: hidden;
  }}
  .compare-container {{
    position: relative;
    width: 100vw; height: 100vh;
    overflow: hidden;
    transform-origin: center center;
  }}
  .compare-container img {{
    position: absolute; top: 0; left: 0;
    width: 100%; height: 100%;
    object-fit: contain;
    user-select: none; -webkit-user-drag: none;
  }}
  .img-left-wrap {{
    position: absolute; top: 0; left: 0; bottom: 0;
    width: 50%; overflow: hidden; z-index: 2;
  }}
  .img-left-wrap img {{
    position: absolute; top: 0; left: 0;
    width: 100vw; height: 100vh;
    min-width: 100vw;
    object-fit: contain;
  }}
  .img-right {{ z-index: 1; }}

  .slider-line {{
    position: absolute; top: 0; bottom: 0; width: 3px;
    background: rgba(255,255,255,0.8); z-index: 10;
    left: 50%; transform: translateX(-50%);
    pointer-events: none;
    box-shadow: 0 0 8px rgba(0,0,0,0.6);
  }}
  .slider-handle {{
    position: absolute; top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    width: 48px; height: 48px; border-radius: 50%; z-index: 11;
    background: rgba(99,140,255,0.9); border: 3px solid #fff;
    box-shadow: 0 0 24px rgba(99,140,255,0.5);
    cursor: ew-resize; display: flex; align-items: center; justify-content: center;
  }}
  .slider-handle svg {{ width: 24px; height: 24px; fill: #fff; }}

  .tabs {{
    position: absolute; top: 16px; left: 50%; transform: translateX(-50%);
    z-index: 100; display: flex; gap: 4px;
    background: rgba(10,14,23,0.88); backdrop-filter: blur(12px);
    padding: 5px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);
  }}
  .tab {{
    padding: 8px 22px; border: none; border-radius: 7px; cursor: pointer;
    font-size: 13px; font-weight: 600; color: #8892a4;
    background: transparent; transition: all 0.2s;
  }}
  .tab:hover {{ color: #c0c8d8; background: rgba(255,255,255,0.06); }}
  .tab.active {{ color: #fff; background: rgba(99,140,255,0.3); }}

  .label {{
    position: absolute; top: 72px; z-index: 100;
    padding: 6px 14px; border-radius: 6px; font-size: 12px; font-weight: 700;
    letter-spacing: 0.6px; text-transform: uppercase;
    background: rgba(10,14,23,0.82); backdrop-filter: blur(8px);
    border: 1px solid rgba(255,255,255,0.1);
  }}
  .label-left {{ left: 16px; color: #f0a050; }}
  .label-right {{ right: 16px; color: #50d0a0; }}

  .info-panel {{
    position: absolute; bottom: 20px; left: 16px; z-index: 100;
    padding: 14px 18px; border-radius: 10px; font-size: 12px;
    background: rgba(10,14,23,0.88); backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.08); line-height: 1.8;
    max-width: 340px;
  }}
  .info-panel h3 {{ font-size: 15px; margin-bottom: 8px; color: #fff; }}
  .dim {{ color: #5a6478; }}
  .val {{ color: #b0b8c8; }}
  .hl {{ color: #6ea8ff; font-weight: 600; }}

  .zoom-controls {{
    position: absolute; bottom: 20px; right: 16px; z-index: 100;
    display: flex; flex-direction: column; gap: 6px;
  }}
  .zoom-btn {{
    width: 40px; height: 40px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.12);
    background: rgba(10,14,23,0.88); backdrop-filter: blur(8px);
    color: #c0c8d8; font-size: 20px; cursor: pointer; display: flex;
    align-items: center; justify-content: center; transition: all 0.15s;
  }}
  .zoom-btn:hover {{ background: rgba(99,140,255,0.2); color: #fff; }}
</style>
</head>
<body>

<div class="compare-wrap" id="compareWrap">
  <div class="compare-container" id="container">
    <img class="img-right" id="imgRight" draggable="false" />
    <div class="img-left-wrap" id="leftWrap">
      <img id="imgLeft" draggable="false" />
    </div>
    <div class="slider-line" id="sliderLine"></div>
    <div class="slider-handle" id="sliderHandle">
      <svg viewBox="0 0 24 24"><path d="M8 5l-5 7 5 7V5zm8 0v14l5-7-5-7z"/></svg>
    </div>
  </div>
</div>

<div class="tabs" id="tabs">
  <button class="tab active" data-mode="rgb">RGB</button>
  <button class="tab" data-mode="fc">False Color</button>
  <button class="tab" data-mode="ndvi">NDVI</button>
</div>

<div class="label label-left">Original 10m</div>
<div class="label label-right">Super-Resolved 1m</div>

<div class="info-panel">
  <h3>Khartoum, Sudan</h3>
  <span class="dim">Original:</span> <span class="val">Sentinel-2 &mdash; {pixel_size_orig:.0f}m/px</span><br>
  <span class="dim">Enhanced:</span> <span class="hl">S2DR4 &mdash; {pixel_size_sr:.0f}m/px ({upsample_factor}x)</span><br>
  <span class="dim">Area:</span> <span class="val">{sr_extent_m} m</span><br>
  <span class="dim">Image:</span> <span class="val">{sr_w} &times; {sr_h} px</span><br>
  <span class="dim">Dates:</span> <span class="val">2026-02-04 / 2026-01-31</span>
</div>

<div class="zoom-controls">
  <button class="zoom-btn" id="zoomIn" title="Zoom in">+</button>
  <button class="zoom-btn" id="zoomOut" title="Zoom out">&minus;</button>
  <button class="zoom-btn" id="zoomReset" title="Reset view" style="font-size:14px;">&#8634;</button>
</div>

<script>
const DATA = {{
  rgb_orig:  "data:image/jpeg;base64,{images['rgb_orig']}",
  rgb_sr:    "data:image/jpeg;base64,{images['rgb_sr']}",
  fc_orig:   "data:image/jpeg;base64,{images['fc_orig']}",
  fc_sr:     "data:image/jpeg;base64,{images['fc_sr']}",
  ndvi_orig: "data:image/jpeg;base64,{images['ndvi_orig']}",
  ndvi_sr:   "data:image/jpeg;base64,{images['ndvi_sr']}"
}};

const container = document.getElementById('container');
const leftWrap = document.getElementById('leftWrap');
const imgLeft = document.getElementById('imgLeft');
const imgRight = document.getElementById('imgRight');
const sliderLine = document.getElementById('sliderLine');
const sliderHandle = document.getElementById('sliderHandle');

let sliderPos = 0.5;
let dragging = false;
let scale = 1, panX = 0, panY = 0;
let isPanning = false, panStart = {{x:0, y:0}};

function updateSlider() {{
  const pct = (sliderPos * 100) + '%';
  leftWrap.style.width = pct;
  sliderLine.style.left = pct;
  sliderHandle.style.left = pct;
}}

function updateTransform() {{
  container.style.transform = `scale(${{scale}}) translate(${{panX}}px, ${{panY}}px)`;
}}

// Slider drag
sliderHandle.addEventListener('mousedown', e => {{ dragging = true; e.preventDefault(); }});
sliderHandle.addEventListener('touchstart', e => {{ dragging = true; e.preventDefault(); }}, {{passive:false}});

window.addEventListener('mousemove', e => {{
  if (!dragging) return;
  const r = container.getBoundingClientRect();
  sliderPos = Math.max(0.02, Math.min(0.98, (e.clientX - r.left) / r.width));
  updateSlider();
}});
window.addEventListener('touchmove', e => {{
  if (!dragging) return;
  const r = container.getBoundingClientRect();
  sliderPos = Math.max(0.02, Math.min(0.98, (e.touches[0].clientX - r.left) / r.width));
  updateSlider();
}}, {{passive:false}});
window.addEventListener('mouseup', () => {{ dragging = false; }});
window.addEventListener('touchend', () => {{ dragging = false; }});

// Pan
container.addEventListener('mousedown', e => {{
  if (e.target === sliderHandle || e.target.closest('.slider-handle')) return;
  if (scale <= 1) return;
  isPanning = true;
  panStart = {{x: e.clientX - panX * scale, y: e.clientY - panY * scale}};
  container.style.cursor = 'grabbing';
  e.preventDefault();
}});
window.addEventListener('mousemove', e => {{
  if (!isPanning) return;
  panX = (e.clientX - panStart.x) / scale;
  panY = (e.clientY - panStart.y) / scale;
  updateTransform();
}});
window.addEventListener('mouseup', () => {{ isPanning = false; container.style.cursor = ''; }});

// Zoom
container.addEventListener('wheel', e => {{
  e.preventDefault();
  scale = Math.max(1, Math.min(10, scale * (e.deltaY > 0 ? 0.9 : 1.1)));
  if (scale === 1) {{ panX = 0; panY = 0; }}
  updateTransform();
}}, {{passive:false}});

document.getElementById('zoomIn').onclick = () => {{ scale = Math.min(10, scale * 1.4); updateTransform(); }};
document.getElementById('zoomOut').onclick = () => {{
  scale = Math.max(1, scale / 1.4);
  if (scale === 1) {{ panX = 0; panY = 0; }}
  updateTransform();
}};
document.getElementById('zoomReset').onclick = () => {{ scale = 1; panX = 0; panY = 0; updateTransform(); }};

// Tabs
function switchMode(mode) {{
  imgLeft.src = DATA[mode + '_orig'];
  imgRight.src = DATA[mode + '_sr'];
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.mode === mode));
}}
document.querySelectorAll('.tab').forEach(btn => btn.addEventListener('click', () => switchMode(btn.dataset.mode)));

// Init
switchMode('rgb');
updateSlider();
</script>
</body>
</html>"""

with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write(html)

file_size_mb = os.path.getsize(OUTPUT_HTML) / (1024 * 1024)
print(f"\n  Output: {OUTPUT_HTML}")
print(f"  Size: {file_size_mb:.1f} MB")

print("\nOpening in default browser...")
webbrowser.open(f"file:///{OUTPUT_HTML.replace(os.sep, '/')}")

print("\n" + "=" * 60)
print("DONE! Interactive comparison is ready.")
print("  - Drag slider left/right to compare")
print("  - Scroll to zoom, drag to pan when zoomed")
print("  - Click tabs for RGB / False Color / NDVI")
print("=" * 60)
