# /rn-game-verify — Build & Production Doğrulama

FPS izleme, debug logging, production readiness kontrol listesi.

## A. FPS İzleme ve Performans Logging

```typescript
function FrameHeartbeat() {
  const frameCount = useRef(0);
  const lastTime = useRef(performance.now());

  useFrame(() => {
    frameCount.current++;
    const now = performance.now();
    if (now - lastTime.current >= 5000) {
      const fps = (frameCount.current / ((now - lastTime.current) / 1000)).toFixed(1);
      console.log(`[Perf] avg FPS: ${fps} over 5s`);
      frameCount.current = 0;
      lastTime.current = now;
    }
  });

  return null;
}
```

## B. Three.js Bellek İzleme

```typescript
useFrame((state) => {
  const info = state.gl.info;
  if (frameCount.current++ % 60 === 0) {
    console.log(`[Three.js] Geometries: ${info.memory.geometries}`);
    console.log(`[Three.js] Textures: ${info.memory.textures}`);
    console.log(`[Three.js] Draw calls: ${info.render.calls}`);
    console.log(`[Three.js] Triangles: ${info.render.triangles}`);
  }
});
```

**Beklenen davranış:** Geometry ve texture sayıları initial load sonrası STABİL kalmalı. Zamanla artıyorsa → sızıntı.

## C. Debug Logging Pattern

```typescript
const DEBUG = __DEV__;

function log(category: string, message: string, data?: any) {
  if (!DEBUG) return;
  console.log(`[${category}] ${message}`, data ?? '');
}

// Kullanım
log('Game', 'Score updated', { score: 1000, combo: 3 });
log('Perf', 'Frame time', { delta: 0.016 });
```

## D. Adaptive Quality Sistemi

```typescript
const frameTimes: number[] = [];
const QUALITY_TIERS = ['low', 'medium', 'high'] as const;

function adaptQuality(delta: number) {
  frameTimes.push(delta);
  if (frameTimes.length > 60) frameTimes.shift();
  const avg = frameTimes.reduce((a, b) => a + b, 0) / frameTimes.length;
  
  if (avg > 0.020) return 'low';    // >20ms → düşük
  if (avg > 0.014) return 'medium'; // >14ms → orta
  return 'high';
}
```

## E. Production Readiness Checklist

- [ ] 60fps sürdürülmüş (30+ dakika, orta seviye cihaz)
- [ ] Bellek stabil (1 saatlik oturumda büyüme yok)
- [ ] GPU bellek sızıntısı yok (`renderer.info.memory` stabil)
- [ ] Ads doğru yükleniyor ve gösteriliyor (test → production ID)
- [ ] Audio silent mode'da çalıyor (iOS)
- [ ] Haptics desteklenen cihazlarda çalışıyor
- [ ] GL context loss recovery uygulandı
- [ ] Shader pre-compilation canvas mount'ta
- [ ] Pixel ratio 2 ile sınırlandırıldı
- [ ] Build boyutu < 100MB (iOS IPA, Android APK)

## F. Build Doğrulama

```bash
# iOS Simulator
npx expo run:ios --configuration Release

# Android Emulator
npx expo run:android --variant release

# Bundle analysis
npx react-native-bundle-visualizer
```

## G. Hermes Memory Snapshot

```typescript
function captureHeapSnapshot() {
  if (__DEV__ && typeof HermesInternal !== 'undefined') {
    HermesInternal.enableGCLogging?.();
    if (typeof global.gc !== 'undefined') {
      global.gc();
      const props = HermesInternal.getRuntimeProperties();
      console.log('[Heap]', JSON.stringify({
        heapSize: Math.round(props['heapSize'] / 1048576) + 'MB',
        heapUsed: Math.round(props['heapUsed'] / 1048576) + 'MB',
      }));
    }
  }
}
```

## H. Test Stratejileri

| Test Tipi | Araç | Kapsam |
|-----------|------|--------|
| Unit | Jest | Game logic, pure functions |
| Integration | Jest + RNTL | Zustand store, persistence |
| Visual | Screenshot comparison | UI regression |
| Performance | Custom FPS monitor | 60fps validation |
| Memory | Hermes heap snapshot | Leak detection |

## I. Yaygın Sorunlar

| Sorun | Belirti | Çözüm |
|-------|---------|-------|
| Thermal throttling | 5-10dk sonra FPS düşer | Adaptive quality |
| Dual Three.js | `instanceof` başarısız | Metro config alias |
| Shader compilation stutter | İlk kare takılır | `gl.compile()` |
| Memory leak | `geometries` sayısı artar | `dispose()` cleanup |
| GC pause | Periyodik stutter | Zero-alloc loop |

## Referans Doküman
- [`rn_threejs_asset_pipeline_and_verification.md`](../researches/rn_threejs_asset_pipeline_and_verification.md)
