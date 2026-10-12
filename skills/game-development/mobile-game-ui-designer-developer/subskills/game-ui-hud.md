# /game-ui-hud — Game HUD & World-Space UI

Oyun HUD sistemlerini (skor, kombo, can, para) ve 3D dünya→2D overlay köprüsünü tasarla.

## A. Animated Score Counter
- Ease-out cubic count-up: `1 - Math.pow(1 - elapsed, 3)`
- Pulse: scale 1.16 → 1, spring friction: 4, tension: 140
- Duration: `min(600, 220 + (to - from) * 1.5)` ms

## B. Combo Meter (Kademeli Görsel)
| Combo | Renk | Efekt |
|-------|------|-------|
| 2–3 | `#7fd4ff` | Spring pop |
| 4–5 | `#ffd23f` | Spring pop |
| 6–7 | `#ff8e3c` | Spring + glow |
| 8–9 | `#ff3b48` | Continuous pulse |
| 10+ | `hsl(combo*137 % 360, 100%, 62%)` | Rainbow pulse |

## C. World-Space UI (3D→2D Projection)
```typescript
// drei/Html RN'de ÇALIŞMAZ — screen-projection kullan
function useWorldToScreen(worldPos: THREE.Vector3) {
  const { camera, size } = useThree();
  useFrame(() => {
    const projected = worldPos.clone().project(camera);
    const x = (projected.x * 0.5 + 0.5) * size.width;
    const y = (-projected.y * 0.5 + 0.5) * size.height;
  });
}
```

## D. Ref-Based Communication (Three.js → RN)
- Three.js `useFrame` içinde pozisyonları ref'e yaz
- RN overlay'de `setInterval(16ms)` ile forceUpdate
- `pointerEvents="none"` ile overlay dokunuşa kapalı

## E. Genre Pattern'ları
- **Puzzle:** Üstte skor, altta piece tray
- **Runner:** Üst bar — mesafe, coin, pause
- **Idle:** Çoklu para birimi + income/s
- **Tower Defense:** Tower kartları + upgrade panel

## Referans
- [`rn_responsive_ui_game_hud.md`](../researches/rn_responsive_ui_game_hud.md) — Bölüm 3, 11, 12
