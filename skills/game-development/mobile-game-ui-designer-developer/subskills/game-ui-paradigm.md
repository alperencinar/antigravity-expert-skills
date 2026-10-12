# /game-ui-paradigm — UI Paradigmaları & Görsel Hiyerarşi

Oyun UI öğelerini dört paradigma sınıfına ayır ve her birinin RN + Three.js implementasyonunu uygula.

## A. UI Paradigma Sınıfları

| Paradigma | Tanım | RN Implementasyonu |
|-----------|-------|---------------------|
| **Diegetic** | Oyun dünyasının içinde var (3D hologram skor, dünya üzerinde can barı) | `drei/Html` yerine screen-projection ile 3D→2D koordinat |
| **Spatial** | 3D uzayda konumlanmış ama oyun dünyasının parçası değil (hasar sayıları, waypoint) | `useWorldToScreen()` hook ile dünya pozisyonunu RN overlay'e yansıt |
| **Meta** | Ekran-uzayı efektleri (hasarda kırmızı vignette, duraklatmada blur) | RN `Animated` opacity/blur, CSS `filter` |
| **Non-diegetic** | Geleneksel 2D overlay (skor sayacı, kombo metre, butonlar) | `position: 'absolute'` RN View katmanı |

## B. Görsel Hiyerarşi Kuralları
- **Birincil:** Skor/her zaman görünür — en büyük, en kontrast
- **İkincil:** Kombo/can — orta boy, dinamik renk
- **Üçüncül:** Para birimi/pause — küçük, pasif konum
- Glanceability: Oyuncu 0.3 saniyede tüm durumu okuyabilmeli

## C. WCAG Kontrast Gereksinimleri
- Normal metin: minimum **4.5:1** kontrast oranı
- Büyük metin (≥18pt bold): minimum **3:1**

## D. Renk Körlüğü Güvenliği
- Kırmızı-yeşil (deuteranopia) çiftlerini KULLANMA
- Renk + şekil/icon kombinasyonu kullan
- HSL hue rotation ile güvenli palet üret

## E. Katman Mimarisi (pointerEvents Stratejisi)
```
Layer 0: Canvas (absoluteFill)         → 3D sahne
Layer 1: HUD (pointerEvents="none")    → Görsel, dokunuş geçer
Layer 2: Modals (pointerEvents="auto") → Etkileşimli
Layer 3: Gesture overlay              → Tüm dokunuşları yakalar
```

## Referans
- [`rn_responsive_ui_game_hud.md`](../researches/rn_responsive_ui_game_hud.md) — Bölüm 1, 10, 12
