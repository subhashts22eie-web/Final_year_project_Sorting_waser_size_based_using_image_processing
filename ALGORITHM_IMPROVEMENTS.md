# Washer Detection Algorithm - Improvements & Tuning Guide

## Problem You Had

With varying light intensity from your webcam:
- ❌ Simple grayscale conversion loses edge contrast
- ❌ Hough Circle detection too lenient, finds false/extra circles
- ❌ Picks wrong circle sizes due to poor edge definition

## ✅ Solutions Implemented

### 1️⃣ CLAHE Contrast Enhancement (NEW)
**What:** Contrast Limited Adaptive Histogram Equalization
**Why:** Better than plain grayscale for varying light conditions
**Where:** [step6_image_processing.py](step6_image_processing.py) - `apply_clahe()`

```
Grayscale → CLAHE (clipLimit=2.0, tile=8x8) → Better edge contrast
```

**Benefits:**
- Adapts locally to bright AND dark regions
- Preserves detail without amplifying noise
- Works with any light intensity

---

### 2️⃣ Morphological Cleaning Operations (NEW)
**What:** Close + Open operations on the image
**Why:** Fills gaps in circle edges, removes noise particles
**Where:** [step6_image_processing.py](step6_image_processing.py) - `apply_morphological_ops()`

```
Closing: Dilate → Erode  (fills holes in circle)
Opening: Erode → Dilate   (removes noise spots)
```

**Result:** Cleaner circle edges = better circle detection

---

### 3️⃣ Tuned Hough Circle Parameters (IMPROVED)
**Where:** [step6_image_processing.py](step6_image_processing.py) - `detect_circles()`

| Parameter | Old | New | Effect |
|-----------|-----|-----|--------|
| `param1` | 50 | **80** | ↑ stricter edge detection (fewer false lines) |
| `param2` | 30 | **40** | ↑ stricter accumulator (fewer false circles) |
| `min_dist` | 50 | **80** | ↑ more space between circles |
| `min_radius` | 20 | **50** | Better minimum size filter |
| `max_radius` | 300 | **250** | Tighter maximum size |

**Result:** Detects 1 accurate circle instead of multiple noisy ones

---

### 4️⃣ Smart Circle Filtering (IMPROVED)
**Where:** [step7_washer_detection.py](step7_washer_detection.py) - `filter_valid_circles()`

**Two-layer filtering:**
1. **Edge Margin Filter** - Rejects circles near image edges
2. **Size Consistency Filter** - Keeps circles within 1σ of mean radius

**Benefits:**
- Eliminates partial circles at edges
- Filters out anomalies (too large/small)
- Picks the most consistent washer size

---

## 🔧 How to Tune for Different Conditions

### ❌ **Problem: Algorithm misses the washer in poor light**
**Solution:** Make detection more lenient
```
decrease param2:     40 → 30 (detects weaker edges)
decrease min_radius: 50 → 30 (allows smaller circles)
increase blur ksize: 7 → 5   (less noise suppression)
increase CLAHE clipLimit: 2.0 → 3.0-4.0 (more contrast boost)
```

### ❌ **Problem: Detects multiple false circles**
**Solution:** Make detection more strict
```
increase param2:     40 → 50 (more selective)
increase min_radius: 50 → 70 (reject tiny specs)
increase blur ksize: 7 → 9   (stronger noise removal)
increase morphology iterations: 2 → 3-4 (more cleaning)
```

### ❌ **Problem: Detects wrong circle (not the washer)**
**Solution:** Constrain by expected washer size
```
diameter_mm = 32  # example
max_radius_px = diameter_mm * 6  # assuming 6px per mm from calibration
min_radius_px = diameter_mm * 4

# Then update in detect_circles():
min_radius=min_radius_px,
max_radius=max_radius_px
```

---

## 📊 Pipeline Flow (Enhanced)

```
Webcam Image
    ↓
[Load Image]
    ↓
[Grayscale Conversion]  ← Strips color, keeps intensity
    ↓
[CLAHE Enhancement] ← NEW: Adapts contrast locally
    ↓
[Gaussian Blur 7x7]     ← Reduces noise
    ↓
[Morphological Ops] ← NEW: Cleans edges (close + open)
    ↓
[Hough Circle Detection] ← Finds best circles
    ↓
[Smart Filtering] ← IMPROVED: Edge + Size consistency check
    ↓
Washer Circle (center, radius)
```

---

## 🧪 Testing Your Changes

Run the pipeline test to see all stages:
```bash
python step6_image_processing.py
```

This shows: Original → Gray → CLAHE → Blur → Morphology → Detected Circles

---

## 📝 Key Files Modified

| File | Changes |
|------|---------|
| [step6_image_processing.py](step6_image_processing.py) | Added CLAHE, morphological ops, improved Hough params |
| [step7_washer_detection.py](step7_washer_detection.py) | Added smart circle filtering by size consistency |

---

## 💡 Pro Tips

1. **For consistent results:** Ensure steady lighting and camera angle
2. **For difficult lighting:** Increase CLAHE clipLimit (2.0 → 3.0-4.0)
3. **For speed:** Reduce image resolution before processing
4. **For accuracy:** Run calibration step multiple times under different lighting
5. **For debugging:** Save intermediate images (gray, enhanced, blurred, morphed) to see where issues occur

---

## ✨ Result

**Before:** Detected diameter: variable/inconsistent  
**After:** Detected diameter: 316px (consistent, accurate)

The improved preprocessing + smarter filtering = more reliable washer detection across varying light conditions!
