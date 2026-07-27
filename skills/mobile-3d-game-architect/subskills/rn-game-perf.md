# /rn-game-perf — Render Döngüsü & 60fps Performans

React Native + Three.js mobil oyunlarda 60fps render döngüsü optimizasyonu.

## A. useFrame — Oyun Döngüsünün Kalbi

`useFrame`, React reconciliaton döngüsünün DIŞINDA her animasyon karesinde tetiklenir.

```typescript
import { useFrame } from '@react-three/fiber/native';

function GameEntity() {
  const ref = useRef<THREE.Mesh>(null!);
  
  useFrame((state, delta) => {
    // state.clock — yüksek çözünürlüklü geçen süre
    // delta — son kareden bu yana geçen saniye
    ref.current.rotation.y += delta * 0.5;
  });
  
  return <mesh ref={ref} />;
}
```

**Temel Kurallar:**
- `useFrame` içinde ASLA `setState` çağırma — 60fps React reconciliation tetikler
- Tüm per-frame mutasyonlar için `useFrame` kullan (pozisyon, rotasyon, scale)
- Birden fazla `useFrame` kancası sorun değil — R3F bunları tek rAF döngüsünde birleştirir
- `useFrame` öncelik parametresi ile sıralama kontrolü (fizik → render)

## B. InstancedMesh — Draw Call Optimizasyonu

N nesneyi 1 draw call ile render eder. Mobil GPU'da 10x+ FPS artışı.

```typescript
const COUNT = 25;
const meshRef = useRef<THREE.InstancedMesh>(null!);
const dummy = useMemo(() => new THREE.Object3D(), []);

useLayoutEffect(() => {
  const mesh = meshRef.current;
  for (let i = 0; i < COUNT; i++) {
    dummy.position.set(col - 2, row - 2, 0);
    dummy.updateMatrix();
    mesh.setMatrixAt(i, dummy.matrix);
  }
  mesh.instanceMatrix.needsUpdate = true;
}, []);

return <instancedMesh ref={meshRef} args={[GEO, MAT, COUNT]} />;
```

## C. Koşullu Matrix Güncellemeleri

Değişmediğinde GPU buffer upload'ını sıfırla:

```typescript
let matrixChanged = false;
for (let i = 0; i < COUNT; i++) {
  if (Math.abs(lastScale[i] - targetScale) > 0.001) {
    dummy.scale.setScalar(targetScale);
    dummy.updateMatrix();
    mesh.setMatrixAt(i, dummy.matrix);
    matrixChanged = true;
  }
}
if (matrixChanged) mesh.instanceMatrix.needsUpdate = true;
```

## D. Shader Ön-Derleme

İlk kare takılmayı önle:

```typescript
<Canvas onCreated={(state) => {
  state.gl.compile(state.scene, state.camera); // Tüm shader'ları önceden derle
}}>
```

## E. Frame-Rate Bağımsız Yumuşatma

```typescript
useFrame((_, delta) => {
  const k = 1 - Math.exp(-delta * SPEED); // SPEED: 7-50 arası
  position.lerp(targetPosition, k);
});
```

## F. Performans Bütçesi (60fps)

| Metrik | Hedef |
|--------|-------|
| JS Thread (Hermes) | ≤ 8ms/kare |
| Draw calls | ≤ 50 |
| Üçgen sayısı | ≤ 50K ekranda |
| Texture belleği | ≤ 128MB |
| React re-render | 0/kare (ref kullan) |
| Alloc/kare | 0 (zero-GC döngü) |

## G. Yaygın Tuzaklar

- `useFrame` içinde `new THREE.Vector3()` → GC stutter
- `useLayoutEffect` yerine `useEffect` → ilk karede flicker
- Tüm Zustand store'a abone olma → cascade re-render
- Pixel ratio cap yok → mobil cihazlarda 3x render = 9x piksel

## Referans Doküman
- [`rn_threejs_mobile_performance_optimization.md`](../researches/rn_threejs_mobile_performance_optimization.md)
