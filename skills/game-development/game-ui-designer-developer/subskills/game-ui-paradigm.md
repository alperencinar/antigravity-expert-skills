# /game-ui-paradigm - AAA UI Paradigms, Color Theory & SDF Typography

## Temel Tasarım Kuralları

1. **4 UI Paradigması**
   - **Diegetic**: Oyun dünyası geometrisine gömülü UI (örn. `MaterialPropertyBlock` mesh health bar).
   - **Non-Diegetic**: Dünya fiziğinden bağımsız screen-space HUD overlay'leri.
   - **Spatial**: Frustum ve derinlik kontrolüyle ekran koordinatlarına projekte edilen 3D world-space markerlar.
   - **Meta**: Dördüncü duvar arayüzleri (oyun içi telefon, glitch HUD, render texture monitörler).
2. **Renk Teorisi & Erişilebilirlik**
   - WCAG 2.1 AAA kontrast oranları: normal metin `CR >= 7:1`, büyük başlık `4.5:1`.
   - Dinamik adaptif metin kontrastı (sRGB linear luminance): `L = 0.2126*R_lin + 0.7152*G_lin + 0.0722*B_lin`
   - Deuteranopia / Protanopia / Tritanopia için LMS Cone Transformation matrisleri.
3. **SDF & MSDF Tipografi Motoru**
   - Aşırı zoom seviyelerinde keskin köşeler için TextMeshPro SDF / MSDF.
   - Fallback Font Zinciri: Ana Font → CJK Fallback → Arapça RTL BiDi shaping.

## Referans Dokümanlar
- [`game_ui_ux_paradigms_and_visual_hierarchy.md`](../researches/game_ui_ux_paradigms_and_visual_hierarchy.md)
- [`professional_game_ui_development.md`](../researches/professional_game_ui_development.md)
