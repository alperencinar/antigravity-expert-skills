# /game-ui-button - 7-State Button Lifecycle, Spring Juice & Haptics

## Buton Mühendislik Kuralları

1. **7 Buton Durumu**: Normal, Hover, Pressed, Selected, Disabled, Cooldown Overlay, Loading Spinner.
2. **Spring Physics Mikro Etkileşimleri**
   - Sönümlü harmonik osilatör ölçekleme (basışta `0.94x`, bırakışta yay sıçraması): `m*x'' + c*x' + k*x = 0`
   - Y-translation offset (-4px) ve dinamik gölge offset kayması.
3. **Ses & Haptics**
   - iOS `UIImpactFeedbackGenerator` & Android `VibrationEffect` — `MobileHapticBridge.cs`.
   - Kulak yorgunluğunu önlemek için ses pitch varyasyonu (`±0.05`).
4. **Yeniden Kullanılabilir UI Bileşenleri**
   - Modal Card, Virtualized ScrollRect (`O(1)` pool), Juicy Damage Ghost Progress Bar, Radial Selection Wheel.

## Referans Dokümanlar
- [`button_systems_micro_interactions_and_juice.md`](../researches/button_systems_micro_interactions_and_juice.md)
