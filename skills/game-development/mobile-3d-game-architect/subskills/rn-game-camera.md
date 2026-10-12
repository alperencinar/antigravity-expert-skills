# /rn-game-camera — Kamera Animasyonu & Game Feel

Kamera sistemleri oyun hissini yönlendirir. Camera rig, cinematic transition, screen shake ve spring physics.

## A. Camera Rig Pattern'leri

```typescript
// Fixed Camera — puzzle oyunları için
function FixedCamera() {
  const { camera } = useThree();
  useFrame(() => {
    camera.position.set(0, 0.2, 12);
    camera.lookAt(0, 0, 0);
  });
  return null;
}

// Orbit Camera — menü/idle oyunları için
function OrbitCamera({ radius = 10, speed = 0.3 }) {
  const { camera } = useThree();
  const angle = useRef(0);
  
  useFrame((_, dt) => {
    angle.current += speed * dt;
    camera.position.set(
      Math.cos(angle.current) * radius,
      radius * 0.5,
      Math.sin(angle.current) * radius
    );
    camera.lookAt(0, 0, 0);
  });
  return null;
}
```

## B. Cinematic Transition

Menü → oyun geçişi için kamera dalışı:

```typescript
export const modeRef = {
  mode: 'menu' as 'menu' | 'enter' | 'game',
  enterStart: 0,
};

useFrame(() => {
  if (modeRef.mode === 'enter') {
    const elapsed = (performance.now() - modeRef.enterStart) / 1000;
    const t = Math.min(1, elapsed / ENTER_DURATION);
    const eased = easeInOutCubic(t);
    
    camera.position.lerpVectors(START_POS, END_POS, eased);
    camera.fov = lerp(START_FOV, END_FOV, eased);
    camera.updateProjectionMatrix();
    
    if (t >= 1) modeRef.mode = 'game';
  }
});
```

## C. Trauma-Based Screen Shake

```typescript
const shakeRef = { intensity: 0 };

function triggerShake(amount: number) {
  shakeRef.intensity = Math.min(1, shakeRef.intensity + amount);
}

useFrame((_, delta) => {
  // Intensity decay
  shakeRef.intensity *= Math.pow(0.9, delta * 60);
  if (shakeRef.intensity < 0.01) shakeRef.intensity = 0;
  
  // Apply shake
  const offset = new THREE.Vector3(
    (Math.random() - 0.5) * 2 * shakeRef.intensity,
    (Math.random() - 0.5) * 2 * shakeRef.intensity,
    0
  );
  camera.position.add(offset);
});
```

## D. Spring Physics (Rotation Snapping)

```typescript
// Damped harmonic oscillator
useFrame((_, delta) => {
  const SPRING = 50;    // yay sertliği
  const DAMPING = 0.85; // sönümleme
  
  const force = (targetAngle - currentAngle) * SPRING;
  velocity += force * delta;
  velocity *= DAMPING;
  currentAngle += velocity * delta;
});
```

## E. Frame-Rate Bağımsız Smoothing

```typescript
useFrame((_, delta) => {
  const k = 1 - Math.exp(-delta * SPEED);
  
  // Position smoothing
  camera.position.lerp(targetPosition, k);
  
  // Rotation smoothing
  camera.quaternion.slerp(targetQuaternion, k);
  
  // FOV smoothing
  camera.fov += (targetFov - camera.fov) * k;
  camera.updateProjectionMatrix();
});
```

**SPEED Parametreleri:**
| SPEED | %95'e Ulaşma | Kullanım |
|-------|--------------|----------|
| 7 | ~0.43s | Yavaş kamera takibi |
| 12 | ~0.25s | UI element yumuşatma |
| 19 | ~0.16s | Drag follow (responsive) |
| 30 | ~0.10s | Hızlı feedback |
| 50 | ~0.06s | Anlık snap |

## F. Dynamic FOV Stretching

Hız hissi için FOV değişimi:

```typescript
useFrame((_, delta) => {
  const targetFov = BASE_FOV + speed * FOV_STRETCH_FACTOR;
  camera.fov += (targetFov - camera.fov) * (1 - Math.exp(-delta * 8));
  camera.updateProjectionMatrix();
});
```

## G. Ekran Boyutuna Göre Kamera Mesafesi

```typescript
function useAdaptiveCameraDistance() {
  const { size } = useThree();
  const aspect = size.width / size.height;
  
  // Portrait: daha uzak, landscape: daha yakın
  const distance = aspect < 1 ? 14 : 10;
  return distance;
}
```

## H. Yaygın Tuzaklar

- `camera.lookAt()` her frame çağrılır → quaternion slerp daha performanslı
- Screen shake offset'i biriktirme → her frame sıfırla
- Delta clamp yoksa → GC pause sonrası büyük jump
- Cinematic transition'da `updateProjectionMatrix()` unutulursa → FOV değişmez

## Referans Doküman
- [`camera_animation_and_game_feel.md`](../researches/camera_animation_and_game_feel.md)
