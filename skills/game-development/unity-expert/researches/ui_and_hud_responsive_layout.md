# Responsive Mobile UI & UGUI Performance Optimization in Unity

## Executive Summary

Designing a mobile UI in Unity uGUI requires balancing **visual flexibility across diverse display hardware** (notches, punch-holes, Dynamic Islands, tablet/foldable aspect ratios) with **rigorous CPU/GPU performance optimization**. 

In uGUI, naive implementations frequently cause severe CPU frame spikes due to full-canvas mesh re-batching, high Garbage Collection (GC) pressure from string allocations, and broken draw call batching caused by improperly configured texture atlases or instantiated materials.

This technical guide details production-grade architecture and mathematical frameworks for building high-performance, fully responsive mobile UIs and HUDs in Unity.

---

## 1. Device Safe Area Auto-Fitting Architecture

Modern mobile displays feature hardware cutouts—such as top/bottom notches, camera punch-holes, rounded display corners, and Apple's Dynamic Island—as well as software navigation bars. Standard full-screen canvases render UI elements under these cutouts unless explicitly constrained within the device's **Safe Area**.

```
+---------------------------------------------------+
|               UNSAFE AREA (Hardware Notch)       |
|  [ Camera ]                 [ Dynamic Island ]    |
| +-----------------------------------------------+ |
| |                                               | |
| |                  SAFE AREA                    | |
| |             Interactive Mobile UI             | |
| |                                               | |
| +-----------------------------------------------+ |
|               UNSAFE AREA (Home Indicator)        |
+---------------------------------------------------+
```

### 1.1 Safe Area Normalization & RectTransform Anchor Math

Unity provides the hardware safe area in pixel coordinates via `Screen.safeArea`, anchored from the bottom-left of the physical screen `(0, 0)`. 

To apply `Screen.safeArea` to a uGUI `RectTransform`, pixel coordinates must be mapped into **normalized anchor space** ($[0.0, 1.0]$):

$$\text{anchorMin.x} = \frac{\text{safeArea.x}}{\text{Screen.width}}$$

$$\text{anchorMin.y} = \frac{\text{safeArea.y}}{\text{Screen.height}}$$

$$\text{anchorMax.x} = \frac{\text{safeArea.x} + \text{safeArea.width}}{\text{Screen.width}}$$

$$\text{anchorMax.y} = \frac{\text{safeArea.y} + \text{safeArea.height}}{\text{Screen.height}}$$

Once `anchorMin` and `anchorMax` are assigned to the root container `RectTransform`, setting `offsetMin = Vector2.zero` and `offsetMax = Vector2.zero` forces the panel to match the safe area bounds without hardcoded offsets.

### 1.2 Production Safe Area Handler Component (`SafeAreaHandler.cs`)

Below is a zero-allocation, orientation-aware C# implementation that dynamically listens for resolution and safe area changes (e.g., screen rotation, foldable state changes, or Dynamic Island expansions):

```csharp
using UnityEngine;

namespace UnityExpert.UI
{
    /// <summary>
    /// Automatically fits a RectTransform panel within the hardware device safe area.
    /// Resilient to device orientation changes, foldables, and notch variations.
    /// </summary>
    [RequireComponent(typeof(RectTransform))]
    [DisallowMultipleComponent]
    public class SafeAreaHandler : MonoBehaviour
    {
        [Header("Padding Customization (Normalized 0..1)")]
        [SerializeField] private bool applyTopPadding = true;
        [SerializeField] private bool applyBottomPadding = true;
        [SerializeField] private bool applyLeftPadding = true;
        [SerializeField] private bool applyRightPadding = true;

        private RectTransform targetRectTransform;
        private Rect lastSafeArea = Rect.zero;
        private Vector2Int lastScreenSize = Vector2Int.zero;
        private DeviceOrientation lastOrientation = DeviceOrientation.Unknown;

        private void Awake()
        {
            targetRectTransform = GetComponent<RectTransform>();
            ApplySafeArea();
        }

        private void Update()
        {
            // Detect orientation, resolution, or safe area shifts at runtime
            if (HasScreenStateChanged())
            {
                ApplySafeArea();
            }
        }

        private bool HasScreenStateChanged()
        {
            return lastSafeArea != Screen.safeArea ||
                   lastScreenSize.x != Screen.width ||
                   lastScreenSize.y != Screen.height ||
                   lastOrientation != Input.deviceOrientation;
        }

        public void ApplySafeArea()
        {
            Rect safeArea = Screen.safeArea;
            int screenWidth = Screen.width;
            int screenHeight = Screen.height;

            // Guard against uninitialized screen metrics during initialization
            if (screenWidth <= 0 || screenHeight <= 0) return;

            // Cache current state
            lastSafeArea = safeArea;
            lastScreenSize = new Vector2Int(screenWidth, screenHeight);
            lastOrientation = Input.deviceOrientation;

            // Convert Screen.safeArea (pixels) into Normalized Anchor Coordinates (0.0 to 1.0)
            Vector2 anchorMin = safeArea.position;
            Vector2 anchorMax = safeArea.position + safeArea.size;

            anchorMin.x /= screenWidth;
            anchorMin.y /= screenHeight;
            anchorMax.x /= screenWidth;
            anchorMax.y /= screenHeight;

            // Selectively ignore paddings if disabled
            if (!applyLeftPadding) anchorMin.x = 0f;
            if (!applyBottomPadding) anchorMin.y = 0f;
            if (!applyRightPadding) anchorMax.x = 1f;
            if (!applyTopPadding) anchorMax.y = 1f;

            // Apply normalized anchors
            targetRectTransform.anchorMin = anchorMin;
            targetRectTransform.anchorMax = anchorMax;

            // Reset offsets to stretch completely within the new anchors
            targetRectTransform.offsetMin = Vector2.zero;
            targetRectTransform.offsetMax = Vector2.zero;
        }

#if UNITY_EDITOR
        private void OnValidate()
        {
            if (targetRectTransform == null)
                targetRectTransform = GetComponent<RectTransform>();
        }
#endif
    }
}
```

---

## 2. Canvas Splitting Architecture

### 2.1 The uGUI Canvas Rebuild Bottleneck

In Unity uGUI, a `Canvas` acts as the fundamental batching and rendering unit. When any single `Graphic` element inside a Canvas (Image, TextMeshProUGUI, RawImage) updates its visual parameters—such as text string modification, position change, color shift, or alpha fade—the entire Canvas is flagged as **Dirty**.

```
[ Canvas Dirty Flag Triggered ]
               │
               ▼
[ CanvasUpdateRegistry.PerformUpdate() ]
               │
               ▼
[ Rebuild VBO (Vertex Buffer Object) ] ──► Recalculate Vertices, UVs, & Colors for ALL Canvas Elements
               │
               ▼
[ Canvas.BuildBatch() ]               ──► Re-generate Draw Calls & Sort Depth across Full Canvas
```

If static UI elements (background panels, frame borders, static labels) reside on the same Canvas as dynamic elements (speedometer needle, rapidly changing score counters, animated health bars), Unity is forced to rebuild the mesh geometry for **every static element** on every frame the dynamic element updates. This causes severe CPU spikes.

### 2.2 Multi-Canvas Segmentation Strategy

To eliminate unnecessary VBO rebuilds, group UI elements into separate Canvases based on their **update frequency**:

```
                              UI Root Hierarchy
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         ▼                            ▼                            ▼
┌─────────────────┐          ┌─────────────────┐          ┌─────────────────┐
│ Static HUD      │          │ Dynamic HUD     │          │ Overlay / Modal │
│ Canvas          │          │ Canvas          │          │ Canvas          │
├─────────────────┤          ├─────────────────┤          ├─────────────────┤
│ • Backgrounds   │          │ • Speedometer   │          │ • Pause Menu    │
│ • Health Frame  │          │ • Score Counter │          │ • Popups        │
│ • Button Icons  │          │ • Health Bar    │          │ • Dialog Boxes  │
├─────────────────┤          ├─────────────────┤          ├─────────────────┤
│ Rebuild: RARE   │          │ Rebuild: FREQ   │          │ Rebuild: ON-DEM │
└─────────────────┘          └─────────────────┘          └─────────────────┘
```

#### Canvas Classification Matrix

| Canvas Type | Components Included | Update Frequency | Batching Behavior |
| :--- | :--- | :--- | :--- |
| **Static Canvas** | Backgrounds, frame graphics, static text labels, static icons | Zero during gameplay | Geometry cached once on GPU; zero CPU VBO recalculation cost. |
| **Dynamic Canvas** | Speedometer needles, health fill bars, timer text, score text | Every frame / Frequent | Rebuilds only its lightweight vertex count; leaves static mesh untouched. |
| **Sub-Canvas (Nested)** | Individual health bars, mini-map indicators, floating damage text | High / Intermittent | A child `Canvas` component attached to a child GameObject acts as an isolated rebuild boundary. |
| **Overlay Canvas** | Modal dialogs, pause screens, victory menus | On-demand (rare) | Disabled entirely via `Canvas.enabled = false` when inactive. |

### 2.3 Nested Canvases for Isolated Rebuild Boundaries

Attaching a `Canvas` component to a child GameObject within an existing Canvas hierarchy creates a **Nested Canvas**:
*   A nested canvas inherits screen-space layout positioning and scaling from its parent.
*   **Dirty State Isolation**: Geometry updates inside the nested canvas do **not** trigger a VBO rebuild on the parent Canvas, nor does parent dirtying rebuild the child Canvas.

> [!TIP]
> **Draw Call Overhead vs Rebuild Cost**: Every additional Canvas component incurs a minor overhead of **+1 Draw Call** (or more depending on atlas batching). Do not over-split into dozens of micro-canvases. Group elements by update frequency: 1 Static Root, 1 Dynamic Root, and isolated Sub-Canvases for dynamic lists or complex dynamic widgets.

### 2.4 Raycast Target Optimization

By default, every new uGUI `Image` and `TextMeshProUGUI` component has `Raycast Target = true`. When a user touches the screen, `GraphicRaycaster.Raycast()` performs a depth-first traversal over **all** graphics with `Raycast Target` enabled.

**Optimization Rules:**
1. Disable `Raycast Target` on all decorative images, static frames, backgrounds, and non-interactive text components.
2. Uncheck `Raycast Target` on parent container panels.
3. If an entire Canvas contains no interactive buttons (e.g., Dynamic Score HUD), **remove the `GraphicRaycaster` component** entirely from the Canvas GameObject.

---

## 3. TextMeshPro Font Atlas Optimization & Zero-GC Score Updates

### 3.1 Static vs Dynamic Font Atlases

TextMeshPro (TMP) renders text using Signed Distance Field (SDF) textures generated into a **Font Atlas**. Choosing between Static and Dynamic atlases directly impacts runtime memory and CPU frame stability.

```
                  ┌─────────────────────────────────────────┐
                  │       Font Atlas Configuration          │
                  └────────────────────┬────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
        ┌──────────────────────┐              ┌──────────────────────┐
        │  Static Font Atlas   │              │  Dynamic Font Atlas  │
        ├──────────────────────┤              ├──────────────────────┤
        │ • Pre-rendered glyphs│              │ • On-the-fly glyph   │
        │ • Fixed character set│              │   rasterization      │
        │ • Zero runtime atlas │              │ • Memory spikes on   │
        │   re-packing         │              │   missing glyphs     │
        ├──────────────────────┤              ├──────────────────────┤
        │ Best for: Standard   │              │ Best for: User Chat, │
        │ Western HUDs, fixed  │              │ Localization with    │
        │ numeric counters     │              │ huge character sets  │
        └──────────────────────┘              └──────────────────────┘
```

#### Best Practices for Font Atlases:
1. **Static Atlas for HUD Numeric & Standard Text**: Create a dedicated static TMP Font Asset containing standard ASCII numbers (`0-9`), mathematical symbols (`+ - . , : / %`), and core HUD text. Pre-render at a high SDF resolution ($512\times 512$ or $1024\times 1024$).
2. **Multi-Atlas & Fallback Setup**: Configure secondary fallback font assets under TMP Font Asset Settings for localized characters (e.g., CJK font fallbacks).
3. **Dynamic Atlas Multi-Padding**: When using Dynamic Font Atlases for unknown user text, set atlas texture size to $1024\times 1024$ or $2048\times 2048$ with adequate glyph padding (e.g., 5px–9px) to prevent SDF bleeding artifacts during scaling.

### 3.2 Zero-GC Score Updates with `SetText`

Setting `textComponent.text = "Score: " + scoreValue;` allocates temporary `string` objects every frame. In C#, string concatenation creates heap garbage, triggering the Garbage Collector (GC) and inducing micro-stutters during high-speed mobile gameplay.

TextMeshPro provides non-allocating string updates via **`SetText()` overloads**:

```csharp
using UnityEngine;
using TMPro;

namespace UnityExpert.UI
{
    /// <summary>
    /// High-performance, Zero-GC Score Counter for mobile HUDs.
    /// Eliminates string allocation overhead during high-frequency text updates.
    /// </summary>
    public class ZeroGCScoreCounter : MonoBehaviour
    {
        [SerializeField] private TextMeshProUGUI scoreText;
        [SerializeField] private string prefixLabel = "SCORE: ";

        private int cachedScore = -1;

        // Custom char array buffer for custom zero-alloc formatting
        private readonly char[] charBuffer = new char[32];

        private void Awake()
        {
            if (scoreText == null)
                scoreText = GetComponent<TextMeshProUGUI>();
        }

        /// <summary>
        /// Updates the HUD score text with zero heap allocations.
        /// </summary>
        public void UpdateScore(int newScore)
        {
            if (newScore == cachedScore) return;
            cachedScore = newScore;

            // TMP SetText overload formats integer values directly without string creation
            // Format string: "SCORE: {0:D6}" yields "SCORE: 001250"
            scoreText.SetText("{0}{1:D8}", prefixLabel, newScore);
        }

        /// <summary>
        /// Example updating two float values (e.g. Speedometer) with zero allocation.
        /// </summary>
        public void UpdateSpeedometer(float currentSpeed, int gear)
        {
            // Format: "SPEED: 142.5 KM/H | GEAR: 4"
            scoreText.SetText("SPEED: {0:F1} KM/H | GEAR: {1}", currentSpeed, gear);
        }
    }
}
```

### 3.3 Material Preset Pooling & Batch Preservation

Accessing `textMeshPro.fontMaterial` at runtime creates a **cloned material instance** (`fontMaterial (Instance)`), which causes two critical issues:
1. **Memory Leaks**: The cloned material remains in memory until manually destroyed via `Destroy(material)`.
2. **Broken Draw Call Batching**: Elements using different material instances cannot be batched together by uGUI, adding unnecessary draw calls.

#### Material Presets Solution:
Create pre-configured **TMP Material Presets** in your project assets (e.g., `HUD_Font_Outline`, `HUD_Font_Glow`). 

To switch visual styles without instantiating materials or breaking batching, assign the pre-created asset using **`fontSharedMaterial`**:

```csharp
// BAD: Instantiates a cloned material, breaks batching, leaks memory!
// textMeshPro.fontMaterial.SetColor("_OutlineColor", Color.red);

// GOOD: Assigns pre-created shared material asset, preserves batching, ZERO GC!
[SerializeField] private Material outlineMaterialPreset;

public void ApplyOutlinePreset()
{
    scoreText.fontSharedMaterial = outlineMaterialPreset;
}
```

---

## 4. Draw Call Batching & Sprite Atlas Architecture

### 4.1 uGUI Draw Call Batching Rules

Unity batches multiple UI graphic elements into a single GPU draw call **only** when all of the following criteria are met:

```
                              Draw Call Batching Checklist
                                          │
    ┌───────────────────────────┬─────────┴───────────┬───────────────────────────┐
    ▼                           ▼                     ▼                           ▼
┌───────────────┐       ┌───────────────┐     ┌───────────────┐           ┌───────────────┐
│ Same Material │       │ Same Texture  │     │ Hierarchy Z-  │           │ Same Canvas   │
│ & Shader      │       │ (Sprite Atlas)│     │ Order Coherence│          │ Context       │
└───────────────┘       └───────────────┘     └───────────────┘           └───────────────┘
```

1. **Shared Texture Source**: All images must reside within the exact same **Sprite Atlas** texture.
2. **Identical Shader & Material**: All elements must share the exact same Material reference (or use default UI Material).
3. **No Interleaved Depth Sorting**: Elements using Texture A and Texture B must not be interleaved in the Hierarchy depth order.

### 4.2 Hierarchy Interleaving & Depth Batch Breaking

Hierarchy order determines rendering order in uGUI. Interleaving UI elements that draw from different atlases breaks batching:

```
BAD (3 Draw Calls due to Interleaving):
Hierarchy View                     Atlas Used         Draw Call Batch
├── Background Image               [Atlas_A]   ────►  Batch 1 (Draw Call 1)
├── Dynamic Icon                   [Atlas_B]   ────►  Batch 2 (Draw Call 2)
└── Border Frame Image             [Atlas_A]   ────►  Batch 3 (Draw Call 3)

GOOD (2 Draw Calls via Re-ordering):
Hierarchy View                     Atlas Used         Draw Call Batch
├── Background Image               [Atlas_A]  ──┐
├── Border Frame Image             [Atlas_A]  ──┴──►  Batch 1 (Draw Call 1)
└── Dynamic Icon                   [Atlas_B]  ─────►  Batch 2 (Draw Call 2)
```

### 4.3 Sprite Atlas Configuration & Management

Use Unity's **SpriteAtlas** asset system (v2) to pack individual UI sprites into shared master textures.

```
Assets/UI/Atlases/
├── HUD_Atlas.spriteatlas       (Contains: speedometer, health_bar, score_icon)
├── MainMenu_Atlas.spriteatlas  (Contains: menu_bg, settings_icon, play_button)
└── Common_Atlas.spriteatlas    (Contains: generic_button, checkmark, close_x)
```

#### Recommended Sprite Atlas Inspector Settings:

| Setting | Value | Rationale |
| :--- | :--- | :--- |
| **Type** | Master | Primary texture atlas container. |
| **Include in Build** | Enabled | Ensures atlas is packaged with the application build. |
| **Allow Rotation** | Disabled (UI) / Enabled (2D) | Disable for UI sprites to simplify UV rectangle math. |
| **Tight Packing** | Disabled | Must be disabled for uGUI to prevent overlapping quad transparent boundaries. |
| **Padding** | 4 or 8 pixels | Prevents texture bleeding/filtering artifacts between packed sprites at lower mip levels. |
| **Compression** | ASTC 6x6 (Mobile) / ETC2 | Provides optimal memory efficiency on iOS/Android with high visual fidelity. |

---

## 5. Responsive UI Layout Scaling & Dynamic Aspect Ratio Adaptation

Mobile devices encompass a vast spectrum of display aspect ratios:
*   **4:3 / 3:2**: Tablets (iPad, Android Tablets).
*   **16:9**: Older smartphones, landscape mobile standard.
*   **19.5:9 / 20:9**: Modern flagship smartphones (iPhone 14/15/16, Samsung Galaxy S series).
*   **21:9**: Ultrawide smartphones (Xperia series, gaming phones).
*   **Foldables**: Dynamic aspect ratio transitions between folded (narrow ~23:9) and unfolded (square ~4:3).

### 5.1 Canvas Scaler Configuration

To maintain UI proportion across varying display densities and dimensions, configure the top-level **Canvas Scaler**:

```
[ Canvas Scaler Settings ]
• UI Scale Mode:           Scale With Screen Size
• Reference Resolution:    1920 x 1080 (or 2400 x 1080 for wide mobile)
• Screen Match Mode:       Match Width Or Height
• Match:                   Dynamic Calculation (via Script)
```

### 5.2 Dynamic Aspect Ratio Adaptor (`ResponsiveCanvasAdapter.cs`)

Using a fixed `Match = 0.5` setting can cause UI clipping on extremely tall screens (21:9) or excessive squishing on wide tablet screens (4:3).

The following production script dynamically calculates the ideal `matchWidthOrHeight` value based on the current aspect ratio:

$$\text{Current Aspect Ratio} = \frac{\text{Screen.width}}{\text{Screen.height}}$$

*   If the current aspect ratio is **narrower/taller** than reference (e.g. 4:3 Tablets), match **Width** ($0.0$) to prevent UI elements from overflowing screen edges vertically.
*   If the current aspect ratio is **wider** than reference (e.g. 21:9 Ultrawide), match **Height** ($1.0$) to protect top/bottom HUD elements.

```csharp
using UnityEngine;
using UnityEngine.UI;

namespace UnityExpert.UI
{
    /// <summary>
    /// Dynamically adjusts CanvasScaler match value across tablets (4:3), 
    /// standard phones (16:9), ultrawide (21:9), and foldables.
    /// </summary>
    [RequireComponent(typeof(CanvasScaler))]
    [DisallowMultipleComponent]
    public class ResponsiveCanvasAdapter : MonoBehaviour
    {
        [Header("Reference Dimensions")]
        [SerializeField] private Vector2 referenceResolution = new Vector2(1920f, 1080f);

        [Header("Aspect Ratio Bounds")]
        [Tooltip("Narrow aspect ratio (e.g. 4:3 = 1.333)")]
        [SerializeField] private float tabletAspect = 1.333f;

        [Tooltip("Ultrawide aspect ratio (e.g. 21:9 = 2.333)")]
        [SerializeField] private float ultrawideAspect = 2.333f;

        private CanvasScaler canvasScaler;
        private Vector2Int lastScreenSize = Vector2Int.zero;

        private void Awake()
        {
            canvasScaler = GetComponent<CanvasScaler>();
            ConfigureCanvasScaler();
            UpdateMatchValue();
        }

        private void Update()
        {
            if (lastScreenSize.x != Screen.width || lastScreenSize.y != Screen.height)
            {
                UpdateMatchValue();
            }
        }

        private void ConfigureCanvasScaler()
        {
            canvasScaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            canvasScaler.referenceResolution = referenceResolution;
            canvasScaler.screenMatchMode = CanvasScaler.ScreenMatchMode.MatchWidthOrHeight;
        }

        public void UpdateMatchValue()
        {
            int width = Screen.width;
            int height = Screen.height;

            if (width <= 0 || height <= 0) return;

            lastScreenSize = new Vector2Int(width, height);
            float currentAspect = (float)width / height;
            float targetAspect = referenceResolution.x / referenceResolution.y;

            // Interpolate match value based on aspect ratio drift
            if (currentAspect < targetAspect)
            {
                // Screen is narrower/taller than reference (e.g., 4:3 Tablet in landscape)
                // Match Width (0.0) to preserve horizontal layout boundaries
                float t = Mathf.InverseLerp(targetAspect, tabletAspect, currentAspect);
                canvasScaler.matchWidthOrHeight = Mathf.Lerp(0.5f, 0.0f, t);
            }
            else
            {
                // Screen is wider than reference (e.g., 21:9 Ultrawide)
                // Match Height (1.0) to preserve vertical HUD boundaries
                float t = Mathf.InverseLerp(targetAspect, ultrawideAspect, currentAspect);
                canvasScaler.matchWidthOrHeight = Mathf.Lerp(0.5f, 1.0f, t);
            }
        }
    }
}
```

### 5.3 Layout Group Performance Pitfalls

Unity uGUI layout groups (`HorizontalLayoutGroup`, `VerticalLayoutGroup`, `GridLayoutGroup`, `ContentSizeFitter`) calculate element bounds on the CPU using `ILayoutElement` interfaces.

#### Critical Pitfalls:
1. **Recursive Re-layout Cost**: Modifying any child element inside a deeply nested layout group hierarchy forces parent layout components to traverse the tree and re-calculate minimum, preferred, and flexible sizes up to the root canvas.
2. **Frame Spikes in Dynamic Lists**: Animating or instantiating list items inside a `VerticalLayoutGroup` every frame causes massive CPU overhead.

#### Optimization Alternatives:
*   **Manual Anchor & Pivot Layouts**: For static HUDs, use explicit uGUI `Anchors` and `Pivots` instead of layout groups.
*   **Recycling Scroll Views**: For long dynamic lists (inventory, leaderboards), use recycled scroll view patterns (e.g., Unity's `SuperScrollView` or custom pooled UI items) rather than active layout groups containing hundreds of children.
*   **Disable Layout Group after Initialization**: If a list layout is static once populated, disable the `LayoutGroup` and `ContentSizeFitter` components via script after the first frame (`layoutGroup.enabled = false`) to prevent future recalculations.

---

## 6. Comprehensive Performance Verification Checklist

| Optimization Domain | Verification Standard / Metric | Unity Diagnostic Tool |
| :--- | :--- | :--- |
| **Safe Area Fitting** | Zero visual overlap under notches or Dynamic Island on iPhone/Android cutouts across rotations. | Unity Device Simulator |
| **Canvas Rebuilds** | VBO Rebuild occurs **only** on Dynamic HUD Canvas when score/speedometer updates. Static Canvas VBO rebuild = 0. | Profiler: `Canvas.SendWillRenderCanvases` |
| **Draw Calls** | Total HUD draw calls $\le 5$. Static Canvas achieves 1 batching call via Sprite Atlas. | Unity Frame Debugger |
| **Garbage Collection (GC)** | Zero bytes allocated per frame (`0 B`) during continuous score/speedometer HUD text updates. | Profiler: `GC Alloc` column |
| **Font Atlas** | Numeric HUD uses Static TMP SDF Font Asset; zero dynamic atlas re-packing spikes. | Memory Profiler / Texture Inspector |
| **Material Instances** | Zero instantiated `(Instance)` materials created dynamically at runtime for TMP texts. | Hierarchy search: `(Instance)` |
| **Aspect Scaling** | UI scales cleanly without edge clipping or bad stretching on 4:3, 16:9, 19.5:9, and 21:9 aspect ratios. | Game View Aspect Ratio Switcher |
