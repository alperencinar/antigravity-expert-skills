# /game-ui-responsive - Safe Area, Aspect Ratio Adapters & Layout Math

## Layout Standartları

1. **Çoklu Aspect Ratio Desteği**: 16:9, 19.5:9, 21:9 ve 4:3 (iPad) dinamik anchor ölçekleme.
2. **Hardware Notch / Safe Area**: `Screen.safeArea` piksellerini `[0,1]` RectTransform anchor uzayına normalize et; `offsetMin/Max = Vector2.zero` (`SafeAreaPanel.cs`).
3. **Tek Safe Area Kaynağı & Double-Notch Shift Önleme Kuralı**
   - **Parent SafeArea Ancestor Kontrolü**: Üst header widget'ları (`TopBarWidget.cs`) özel notch offset uygulamadan önce MUTLAKA `GetComponentInParent<SafeAreaPanel>()` kontrol etmeli.
   - Parent `SafeAreaPanel` varsa `anchoredPosition.y` `0` kalmalı → **Double Notch Shifting** (`2x notch`) engellenir.
   - **Birleşik Header-Card Parent Hiyerarşisi**: `TopBar` rozetleri (`Y = -6px`) ve üst `CardsContainer` (`Y = -60px`) AYNI root header paneli içinde parent-child sibling olmalı; her cihazda (Foldable 960x2658, Tablet 2048x2732) %100 senkron kayma, sıfır dikey overlap.
4. **UGUI Layout Optimizasyonu**
   - İç içe `ContentSizeFitter` + `Horizontal/VerticalLayoutGroup` kullanma (`O(N^2)` Rebuild cezası).
   - 35x daha hızlı CPU layout için zero-alloc `ManualLayoutGroup.cs`.
5. **Sıfır Overlap Tipografi & Bounding Box Matematiği**
   - Dikey boşluk formülü: `Gap = (Y_top - H_top/2) - (Y_bottom + H_bottom/2) >= Margin_min (4-8px)`
   - **Açık Anchor Bölme & Sıfır Double-Offset Kuralı**:
     - Üst satır: `anchorMin=(0,0.5)`, `anchorMax=(1,1.0)`, `pivot=(0.5,0.5)`, `anchoredPosition.y=-2px`
     - Alt satır: `anchorMin=(0,0.0)`, `anchorMax=(1,0.5)`, `pivot=(0.5,0.5)`, `anchoredPosition.y=+2px`
   - **`bestFit` Tuzağı**: Statü başlıkları/timer'larda ASLA `resizeTextForBestFit = true` yapma (8-10pt'a küçültür). Daima `false` + `Overflow` + net font boyutu (`18pt-30pt Bold`).
   - **%100 Opak & Koyu Outline Kuralı (3D Floating HUD)**: Floating rozetler (`OilStatusUI.cs`) %100 opak koyu arka plan (`Color32(10,12,18,255)`) + koyu `Outline` (`Color32(0,0,0,220)`, `effectDistance=(1.5,-1.5)`) kullanmalı.

## Cardiv Production Scriptleri
- `Assets/Cardiv/Scripts/UI/Layout/SafeAreaPanel.cs`

## Referans Dokümanlar
- [`responsive_layout_safearea_and_multi_device.md`](../researches/responsive_layout_safearea_and_multi_device.md)
