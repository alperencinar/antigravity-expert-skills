# /game-ui-perf — UI Performans & Render Isolasyonu

60fps oyun ortamında gereksiz re-render'ları önle; render izolasyonu uygula.

## A. React.memo ile Component Koruması
```typescript
const MemoizedCanvas = React.memo(function MemoizedCanvas() {
  return <Canvas camera={{ position: [0, -2.2, 6.2], fov: 45 }}><Scene /></Canvas>;
});
```

## B. Zustand Selector Isolasyonu
```typescript
// ❌ KÖTÜ: const { score, combo } = useGame();
// ✅ İYİ:
const score = useGame((s) => s.score);
const combo = useGame((s) => s.combo);
// ✅ EN İYİ (side-effect, re-render YOK):
useEffect(() => useGame.subscribe((state, prev) => {
  if (state.flash !== prev.flash) playClearSound(state.combo);
}), []);
```

## C. useMemo ile Pahalı Hesaplamalar
```typescript
const panResponder = useMemo(() => PanResponder.create({
  onStartShouldSetPanResponderCapture: () => true,
  onPanResponderGrant: handleGrant,
  onPanResponderMove: handleMove,
  onPanResponderRelease: handleRelease,
}), []); // Boş deps: ref ile güncel değerlere eriş
```

## D. Component-Level State
- ScoreCounter kendi display state'ini yönetir → sadece bu component re-render
- `requestAnimationFrame` ile smooth count-up, `setInterval` DEĞİL
- `useNativeDriver: true` her zaman

## E. Yaygın Tuzaklar
- ❌ `useGame()` ile tüm state'i destructuring
- ❌ PanResponder'ı her render'da yeniden oluşturma
- ❌ Animated value'yu state'te tutma (ref kullan)

## Referans
- [`rn_responsive_ui_game_hud.md`](../researches/rn_responsive_ui_game_hud.md) — Bölüm 6
