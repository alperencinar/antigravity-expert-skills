# /game-ui-perf - UGUI vs UI Toolkit & Zero-GC Optimization

## Performans Kuralları

1. **Canvas Splitting**: Statik arka plan Canvas'ını yüksek frekanslı dinamik HUD Canvas'ından ayır; global VBO re-batching'i önle.
2. **SpriteAtlas v2**: UI sprite'larını 8px bleed padding ile paketle; bilinear filtreleme altında kenar kanamasını (edge bleeding) önle.
3. **Masking Performansı**: `Stencil Mask` yerine `RectMask2D` tercih et (Stencil ekstra draw call pass'i ekler).
4. **Zero-GC Text Güncellemeleri**: `FastStringFormat` veya `TMP_Text.SetText()` numeric/StringBuilder overload'ları kullan. `Update()` içinde ASLA string birleştirme yapma (`score.text = "Score: " + val`).

## Referans Dokümanlar
- [`ugui_vs_ui_toolkit_and_performance_optimization.md`](../researches/ugui_vs_ui_toolkit_and_performance_optimization.md)
- [`ui_ux_design_system_optimization_report.md`](../researches/ui_ux_design_system_optimization_report.md)
