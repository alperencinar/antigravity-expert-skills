# /game-ui-arch - Layered Canvas Architecture & FSM Navigation

## Mimari Standartlar

1. **4 Katmanlı Canvas Hiyerarşisi**
   - Layer 0 (BaseScreens): Tam ekran ekranlar (`MainMenuScreen`, `GameHUD`).
   - Layer 1 (Modals): Pencere popupları (`PausePopup`, `SettingsPopup`, `ShopWindow`).
   - Layer 2 (Dimmer Overlay): Otomatik %50 siyah backdrop + Raycast Blocker.
   - Layer 3 (Toasts): Bildirim toastları (`OilHazardWidget`, `FloatingText`).
2. **Stack Bazlı Modal Navigasyon**
   - `UIManager.cs` üzerinden `Stack<IUIScreen>` (`PushScreen`, `PopScreen`, `ClearAll`).
   - Birleşik geri tuşu: Android hardware back, iOS edge swipe, Esc (`OnBackButtonPressed()`).
3. **Gamepad & Focus Navigasyonu**
   - Modal popuplar için otomatik focus highlight trap'leri.
   - `Mathf.SmoothDamp` ile odaklanan UI elemanına otomatik `ScrollRect` kaydırma.
   - Minimum dokunma hedefi: Apple 44x44pt / Google 48x48dp + görünmez Raycast padding.

## Cardiv Production Scriptleri
- `Assets/Cardiv/Scripts/UI/Navigation/UIManager.cs`, `IUIScreen.cs`

## Referans Dokümanlar
- [`game_ui_architecture_and_navigation_fsm.md`](../researches/game_ui_architecture_and_navigation_fsm.md)
- [`ui_ux_design_system_optimization_report.md`](../researches/ui_ux_design_system_optimization_report.md)
