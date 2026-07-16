# Command: /screenshot-process

Enforce exact dimensions, format conversion (JPEG/PNG), and sequential clean naming conventions on the generated screenshot assets.

---

## 1. Automated Processing
Use the built-in script `scripts/process_screenshots.sh` inside the skill directory to process raw images:

```bash
# Executing from project root:
./.agents/skills/product-aso-screenshot-creator/scripts/process_screenshots.sh <input_directory> <output_directory> [width] [height] [format]
```

### Script Execution Parameters:
*   `input_directory`: Path containing raw screenshot outputs.
*   `output_directory`: Path where optimized files are saved (e.g. `store_screenshots_ready`).
*   `width`: Target width in pixels (e.g. `2064` for 13" iPad, `1242` for 6.5" iPhone).
*   `height`: Target height in pixels (e.g. `2752` for 13" iPad, `2688` for 6.5" iPhone).
*   `format`: Target output format (strictly `jpeg` or `png`).

---

## 2. Manual Commands (Using macOS sips)
If you need to process a single file manually, use:

```bash
# Resize and convert to JPEG format:
sips -z <height> <width> -s format <format> <input_file> --out <output_file>

# Example:
sips -z 2752 2064 -s format jpeg input_img.png --out output_img.jpg
```

---

## 3. Formatting & Naming Verification
Before submitting assets to the app store, verify:
*   [ ] **Correct Dimensions:** Run `file <image_path>` and check if output matches target dimensions exactly.
*   [ ] **No Alpha Channel (Transparency):** Run `sips -g hasAlpha <image_path>` (should return `no` for JPEG and non-alpha PNG). Apple rejects screenshots with alpha transparency.
*   [ ] **Clean Naming:** Ensure filenames start with double digit prefix numbers (`01_`, `02_`, etc.) and use lowercase alphanumeric names with underscores.
