# /unity-expert-ui - Responsive UI Layout & UGUI Performance

Tüm ekran oranları ve notch'larda mobil HUD optimizasyonu.

## UI Standartları

1. **Device Safe Area**: `Screen.safeArea` ile `RectTransform` anchor'larını otomatik hizala; notch ve punch-hole desteği (`SafeAreaHandler.cs`).
2. **Canvas Splitting**: Statik HUD canvas'ını dinamik Skor/Hız göstergesi canvas'larından ayır; full-canvas VBO re-batching'i önle.
3. **Zero-GC Text Güncellemeleri**: `TMP_Text.SetText()` overload'ları ve paylaşımlı materyal preset'leri kullan.
4. **Aspect Ratio Adapters**: 16:9, 19.5:9, 21:9 ve tablet 4:3 için dinamik ölçekleme.

## Referans Dokümanlar
- [`ui_and_hud_responsive_layout.md`](../researches/ui_and_hud_responsive_layout.md)
