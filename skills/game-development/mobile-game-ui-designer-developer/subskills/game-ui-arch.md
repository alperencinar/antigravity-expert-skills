# /game-ui-arch — Navigasyon & Ekran Mimarisi

Oyun ekran akışını phase-based state machine ile tasarla; tam navigation stack yerine hafif modal pattern kullan.

## A. Phase State Machine
```typescript
type GamePhase = 'menu' | 'playing' | 'paused' | 'settings' | 'gameover' | 'revive' | 'result';

function useGamePhase() {
  const [phase, setPhase] = useState<GamePhase>('menu');
  const prevPhase = useRef<GamePhase>('menu');
  const transition = useCallback((next: GamePhase) => {
    prevPhase.current = phase;
    setPhase(next);
  }, [phase]);
  const goBack = useCallback(() => setPhase(prevPhase.current), []);
  return { phase, transition, goBack, prevPhase: prevPhase.current };
}
```

## B. Modal Overlay Pattern
- Scrim (yarı-saydam siyah arka plan) + panel animasyonu
- AnimatedModal: opacity 0→1 (200ms) + scale 0.9→1 (spring)

## C. Android Back Handler
```typescript
import { BackHandler } from 'react-native';
// playing fazdayken back → paused'a al
// paused/settings fazdan back → playing'e dön
// menu fazdan back → çıkış onayı göster
```

## D. Gesture Navigation
- Swipe-to-dismiss modal pattern (Reanimated `useSharedValue` + `runOnJS`)
- Edge swipe ile önceki faza dönüş

## E. Durum Yönetimi Kuralları
- Her faz için ayrı render; `phase === 'settings' && <SettingsPanel />`
- Phase geçişlerinde Canvas re-render OLMAMALI (React.memo ile koru)

## F. Yaygın Tuzaklar
- ❌ Navigation stack kullanma (oyun için fazla ağır)
- ✅ Phase state machine + conditional render
- ✅ Canvas'ı memo ile koru, sadece HUD/modal re-render olsun

## Referans
- [`rn_responsive_ui_game_hud.md`](../researches/rn_responsive_ui_game_hud.md) — Bölüm 4, 5
