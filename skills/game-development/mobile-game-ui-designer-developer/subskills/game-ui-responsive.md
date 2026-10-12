# /game-ui-responsive — Responsive Layout & Safe Area

Tüm cihaz form faktörlerinde (telefon/tablet, 16:9–21:9) piksel-mükemmel layout garantile.

## A. Safe Area Handling
```typescript
import { useSafeAreaInsets } from 'react-native-safe-area-context';
const insets = useSafeAreaInsets();
// paddingTop: insets.top      → Notch/Dynamic Island
// paddingBottom: insets.bottom → Home indicator
```

## B. Device Tier Sınıflandırma
| Tier | Kısa Kenar | Örnek |
|------|-----------|-------|
| `phone-small` | < 375px | iPhone SE |
| `phone` | 375–599px | Standart |
| `tablet` | 600–899px | iPad Mini |
| `tablet-large` | ≥ 900px | iPad Pro |

## C. useGameLayout Hook
```typescript
function useGameLayout() {
  const insets = useSafeAreaInsets();
  const { width, height } = useWindowDimensions();
  const scale = Math.min(width / 390, height / 844);
  return {
    width, height, insets, scale,
    isTablet: Math.min(width, height) >= 600,
    hudTop: insets.top + 8,
    trayHeight: scale > 1.3 ? 180 : 150,
  };
}
```

## D. Aspect Ratio Adaptasyonu (16:9 → 21:9)
```typescript
const isUltraWide = ratio > 2.1;
const contentWidth = isUltraWide ? width * 0.85 : width;
```

## E. Responsive Style Helper
```typescript
function responsive(base: number, scale: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, base * scale));
}
```

## F. Yaygın Tuzaklar
- ❌ Hardcoded padding/margin kullanma
- ✅ Her boyutu `responsive()` ile scale et, min/max ile sınırla
- ✅ DPR'yi 2x ile sınırla: `Math.min(PixelRatio.get(), 2)`

## Referans
- [`rn_responsive_ui_game_hud.md`](../researches/rn_responsive_ui_game_hud.md) — Bölüm 1, 2
