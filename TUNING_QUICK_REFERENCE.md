# Quick Tuning Reference Card

## When Detection Fails

### Scenario 1: "Misses the washer in dim light"
The algorithm can't find the circle because edges are too weak.

**Quick Fix:** Lower the param2 threshold
```python
# In step6_image_processing.py, detect_circles() function:
param2=30  # was 40, make more lenient
```

**Full tuning checklist:**
- [ ] Decrease `param2` from 40 → 35/30
- [ ] Increase CLAHE `clipLimit` from 2.0 → 3.0/4.0
- [ ] Decrease `min_radius` if washer might be small
- [ ] Reduce blur `ksize` from 7 → 5 (keep more edge detail)

---

### Scenario 2: "Detects 5+ circles, picks wrong one"
Noisy image or too many false edges detected.

**Quick Fix:** Raise the param2 threshold
```python
# In step6_image_processing.py, detect_circles() function:
param2=50  # was 40, be more selective
```

**Full tuning checklist:**
- [ ] Increase `param2` from 40 → 45/50
- [ ] Increase blur `ksize` from 7 → 9
- [ ] Increase morphology `iterations` from 2 → 3
- [ ] Increase `min_radius` to filter small noise
- [ ] Increase CLAHE `clipLimit` to reduce noise in enhancement

---

### Scenario 3: "Detects circle way too large/small"
Expected washer size is 340px but detected as 500px or 150px.

**Quick Fix:** Constrain the radius range
```python
# In step6_image_processing.py, detect_circles() function:
min_radius=100,  # was 50
max_radius=200,  # was 250
```

**Formula to calculate bounds:**
```
From your calibration step:
- If washer is ~340px diameter observed
- Set min_radius = 150, max_radius = 200
```

---

## Parameter Quick Reference

```python
def detect_circles(blurred, 
                   dp=1.0,           # resolution ratio (1=same, higher=faster)
                   min_dist=80,      # min spacing between circles
                   param1=80,        # canny edge threshold (higher=stricter)
                   param2=40,        # accumulator threshold (MOST IMPORTANT)
                   min_radius=50,    # minimum circle radius pixels
                   max_radius=250):  # maximum circle radius pixels
```

### param2 is the MASTER TUNING KNOB
- **30-35**: Lenient, finds weak circles (for poor lighting)
- **40-45**: Balanced (default, good for normal conditions)
- **50+**: Strict, finds only strong circles (noisy images)

### Tuning Progression
```
Too many false circles?  → increase param2 by 5-10
Missing the real circle? → decrease param2 by 5-10
```

---

## CLAHE Tuning (Contrast Enhancement)

```python
def apply_clahe(gray):
    clahe = cv2.createCLAHE(clipLimit=2.0,      # ← tune this
                             tileGridSize=(8, 8))
```

- **clipLimit=1.0-2.0**: Conservative, minimal enhancement
- **clipLimit=2.0-3.0**: Balanced (default, recommended)
- **clipLimit=3.0-5.0**: Aggressive, strong contrast (risky in noise)

### When to increase clipLimit:
- Very dim lighting conditions → 3.0-4.0
- Very bright (washed out) lighting → 2.5-3.0
- Normal lighting → keep at 2.0

---

## Morphological Operations Tuning

```python
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
closed = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel, iterations=2)  # adjust this
opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel, iterations=1)  # adjust this
```

- **iterations=1**: Light cleaning, preserves detail
- **iterations=2**: Moderate cleaning (default)
- **iterations=3+**: Aggressive cleaning, may lose small features

### When to increase iterations:
- Lots of noise/artifacts → 3-4
- Many broken circle edges → 2-3
- Clean image already → 1

---

## Recommended Presets for Different Scenarios

### ☀️ Bright, well-lit conditions
```python
param2=50,
min_radius=50,
max_radius=250,
clipLimit=2.0,
ksize=7,
morpho_iterations=1
```

### 🌙 Dim/low-light conditions
```python
param2=30,
min_radius=30,
max_radius=300,
clipLimit=3.5,
ksize=5,
morpho_iterations=2
```

### 📦 Industrial/noisy shadows
```python
param2=55,
min_radius=60,
max_radius=240,
clipLimit=2.5,
ksize=9,
morpho_iterations=3
```

---

## Testing Your Changes

Save one of the presets above into [step6_image_processing.py](step6_image_processing.py), then test:

```bash
cd "d:\Waser Size Identifier"
python step6_image_processing.py
# Check the results/step6_pipeline.jpg to see all preprocessing stages
```

Check which stage loses the circle:
- Lost in CLAHE? → Reduce clipLimit
- Lost in Blur? → Reduce ksize
- Lost in Morphology? → Reduce iterations
- Lost in Hough? → Lower param2

---

## Common Mistakes to Avoid

❌ **Don't:** Maximize all parameters at once
✅ **Do:** Change ONE parameter at a time, test, observe result

❌ **Don't:** Assume same parameters work in all lighting
✅ **Do:** Calibrate params for your specific environment

❌ **Don't:** Ignore the output images
✅ **Do:** Check [results/step6_pipeline.jpg](results/step6_pipeline.jpg) to see where detection fails

❌ **Don't:** Use min_radius=20, max_radius=300 (too wide range)
✅ **Do:** Constrain to your known washer size range
