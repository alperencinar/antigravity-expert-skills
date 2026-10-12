# /game-ui-a11y - Unity Localization, CJK/RTL & Automated UI Auditors

## Erişilebilirlik & Denetim Kuralları

1. **Unity Localization**: Key bazlı lookup, Smart Format çoğullama, `StringBuilderPool` zero-alloc localizer.
2. **Çok Dilli Hizalama**: RTL layout aynalama (`RTLRectTransformMirror.cs`) ve CJK Kinsoku Shori satır kırma kuralları.
3. **Renk Körlüğü Filtreleri**: Gerçek zamanlı Deuteranopia, Protanopia, Tritanopia URP simülasyon shader filtresi (`UI/ColorblindFilter`).
4. **Otomatik UI Kalite Denetçileri**: Draw call denetimi (`UIDrawCallAuditor.cs`), atanmamış TMP fontlar (`TMPFontAndOverflowAuditor.cs`), çoklu cihaz aspect ratio (`DeviceAspectRatioSimulator.cs`), RectTransform overlap (`RectTransformOverlapAuditor.cs`).

## Referans Dokümanlar
- [`localization_accessibility_and_ui_auditing.md`](../researches/localization_accessibility_and_ui_auditing.md)
