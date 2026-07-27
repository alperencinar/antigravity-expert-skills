# /game-ui-hud - Dynamic Gameplay HUD & World-Space Damage Text

## Gameplay HUD Standartları

1. **Radyal Hız Göstergesi & Gauge'lar**: Non-lineer açı eşlemesi `θ(v)` + `Mathf.SmoothDamp` jitter azaltma.
2. **3D World-Space Floating Damage Numbers**: Bezier eğrili floating text pool (`DamageNumberPool.cs`) + `Z <= 0` kamera arka frustum filtreleme.
3. **Off-Screen Objective Pins**: Dikdörtgen kenar clamping (`α_clamp = min(α_x, α_y)`) + dinamik ok rotasyonu (`WorldToScreenTracker.cs`).
4. **Juice Animasyonları**: DOTween elastic punch scale ve düşük can vinyet nabzı (vignette pulse).
5. **Kapsül Rozet & Durum Göstergesi Yerleşimi**: Dinamik 3D floating rozetler (`OilStatusUI.cs`) engellenmemiş bir offsette süzülmeli (`worldOffset = Vector3(0, 2.6f, 0.2f)`).

## Cardiv Production Scriptleri
- `Assets/Cardiv/Scripts/UI/Widgets/ScoreWidget.cs`, `ComboWidget.cs`, `PauseFABWidget.cs`, `OilHazardWidget.cs`

## Referans Dokümanlar
- [`dynamic_gameplay_hud_and_worldspace_ui.md`](../researches/dynamic_gameplay_hud_and_worldspace_ui.md)
