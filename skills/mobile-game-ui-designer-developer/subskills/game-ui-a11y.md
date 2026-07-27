# /game-ui-a11y — Erişilebilirlik & Lokalizasyon

Oyunları erişilebilir yap; ekran okuyucu desteği, WCAG kontrast, RTL ve i18n sağla.

## A. Screen Reader Tespiti
```typescript
import { AccessibilityInfo } from 'react-native';
function useScreenReader() {
  const [enabled, setEnabled] = useState(false);
  useEffect(() => {
    AccessibilityInfo.isScreenReaderEnabled().then(setEnabled);
    const sub = AccessibilityInfo.addEventListener('screenReaderChanged', setEnabled);
    return () => sub.remove();
  }, []);
  return enabled;
}
```

## B. Erişilebilir HUD
```typescript
<View accessibilityRole="summary"
  accessibilityLabel={`Skor: ${score}. Kombo: ${combo}x.`}
  importantForAccessibility={screenReader ? 'yes' : 'no-hide-descendants'}>
```

## C. WCAG 2.1 AA Kontrast
| Element | Minimum |
|---------|---------|
| Normal metin | **4.5:1** |
| Büyük metin | **3:1** |
| UI component | **3:1** |

## D. RTL Layout Desteği
```typescript
import { I18nManager } from 'react-native';
<View style={{ flexDirection: I18nManager.isRTL ? 'row-reverse' : 'row' }}>
// Oyun elementleri HER ZAMAN LTR (skor ilerlemesi)
```

## E. Lokalizasyon
```typescript
const STRINGS = {
  en: { score: 'SCORE', gameOver: 'GAME OVER' },
  tr: { score: 'SKOR', gameOver: 'OYUN BİTTİ' },
  ar: { score: 'النقاط', gameOver: 'انتهت اللعبة' },
};
```

## F. Reduce Motion
```typescript
AccessibilityInfo.isReduceMotionEnabled().then(setReduceMotion);
// reduceMotion true ise: spring yerine timing, shake atla
```

## G. Yaygın Tuzaklar
- ❌ Renk tek başına bilgi aktarmak
- ✅ `accessibilityRole="alert"` ile game over bildirimi
- ✅ `importantForAccessibility="no-hide-descendants"` ile görsel HUD'ı gizle

## Referans
- [`rn_responsive_ui_game_hud.md`](../researches/rn_responsive_ui_game_hud.md) — Bölüm 8, 9
