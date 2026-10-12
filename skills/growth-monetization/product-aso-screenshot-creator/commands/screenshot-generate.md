# Command: /screenshot-generate

Guide the image generator or external designer to render high-fidelity screenshots using structured prompts, mockup scales, and color themes.

---

## 1. Mockup Design Specifications
*   **Tablet/Device Scale:** Mockups must fill **80% to 85%** of the screenshot area to ensure the screen contents remain readable at small thumbnail sizes.
*   **Wrapper Placement:** Headers must be pushed close to the top edge (safe margin ~5-8% padding) with clean, wide layouts.
*   **UI Language Consistency:** The embedded application mockup screen must be in **English**, while the surrounding header/caption text is localized to the target store language.

---

## 2. Structured Prompt Engineering
When generating screenshots, use the following exact prompt structure to achieve premium layouts:

```markdown
A premium [Device Mockup Type, e.g., iPad Pro / iPhone 15 Pro] App Store screenshot in portrait layout.
The background is a sleek [Primary Brand Color, e.g. emerald green] gradient.
At the very top, close to the upper edge, there is a large, bold, white sans-serif title: '[Header Title]'.
The title is wide and spreads horizontally to minimize vertical lines.
A very large, high-fidelity [Device Mockup Type] mockup dominates the center and bottom of the image (filling 85% of the frame size) so that the app interface from the reference image is showcased in high resolution and all text inside the app screen is clearly readable.
```

---

## 3. Aspect Ratio Control
To ensure direct export capability, request the exact aspect ratio from the generator:
*   Use `3:4` for standard Tablet/iPad screenshots (e.g. `2064x2752` px).
*   Use `9:19.5` aspect ratio for Phone screenshots (exact target: `1242x2688` px).
