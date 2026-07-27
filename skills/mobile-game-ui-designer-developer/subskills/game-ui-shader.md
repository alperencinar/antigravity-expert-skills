# /game-ui-shader — Görsel Efektler & Post-Processing

RN ve Three.js render pipeline'larını kullanarak görsel efektler uygula.

## A. Meta Efektler (Ekran-Uzayı)
| Efekt | Tetikleyici | Implementasyon |
|-------|-------------|----------------|
| Kırmızı vignette | Hasar | RN View + opacity animasyonu |
| Blur | Duraklatma | `expo-blur` BlurView |
| Screen shake | Büyük combo | Animated offset |
| Combo flash | Clear | White overlay 0.3→0 |

## B. RN Animated ile Efektler
```typescript
const vignetteOpacity = useRef(new Animated.Value(0)).current;
Animated.timing(vignetteOpacity, { toValue: 0.4, duration: 100, useNativeDriver: true }).start(() => {
  Animated.timing(vignetteOpacity, { toValue: 0, duration: 400, useNativeDriver: true }).start();
});
```

## C. react-native-reanimated (Worklet)
```typescript
const shakeX = useSharedValue(0);
shakeX.value = withSequence(
  withTiming(-8, { duration: 50 }),
  withTiming(8, { duration: 50 }),
  withTiming(0, { duration: 50 }),
);
```

## D. Three.js Post-Processing
```typescript
<EffectComposer>
  <Bloom luminanceThreshold={0.8} intensity={0.5} />
  <ChromaticAberration offset={[0.002, 0.002]} />
</EffectComposer>
```

## E. Performans Kuralları
- DPR'yi **2x ile sınırla**
- `useNativeDriver: true` her zaman
- Post-processing'i sadece gerektiğinde aktif et

## Referans
- [`rn_responsive_ui_game_hud.md`](../researches/rn_responsive_ui_game_hud.md) — Bölüm 6, 10
