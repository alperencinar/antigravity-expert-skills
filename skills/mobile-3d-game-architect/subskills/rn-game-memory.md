# /rn-game-memory — Bellek Yönetimi & Zero-GC Desenleri

Mobil cihazlarda RAM kullanımını minimize etme ve GC baskısını azaltma.

## A. Zero-Allocation useFrame Kuralı

**Kural:** `useFrame` callback'i SIFIR nesne allocate etmeli.

```typescript
// ❌ KÖTÜ — her kare yeni Vector3 oluşturur
useFrame((_, delta) => {
  const direction = new THREE.Vector3(1, 0, 0); // ALLOC!
  mesh.position.add(direction.multiplyScalar(delta));
});

// ✅ İYİ — modül seviyesi singleton kullanır
const _direction = new THREE.Vector3(1, 0, 0); // bir kez allocate

useFrame((_, delta) => {
  mesh.position.add(_direction.multiplyScalar(delta)); // zero alloc
});
```

## B. Singleton Vector3/Color/Matrix4 Deseni

Modül scope'unda ön-allocation, her frame'de yeniden kullanım:

```typescript
// Modül seviyesi — BİR KEZ allocate, SONSUZ kez kullan
const _tmpVec3 = new THREE.Vector3();
const _tmpColor = new THREE.Color();
const _tmpMatrix = new THREE.Matrix4();
const _tmpQuat = new THREE.Quaternion();
const _tmpObj3D = new THREE.Object3D();

useFrame(() => {
  _tmpVec3.set(1, 2, 3);
  _tmpColor.set('#ff0000');
  _tmpMatrix.makeTranslation(_tmpVec3.x, _tmpVec3.y, _tmpVec3.z);
  meshRef.current.applyMatrix4(_tmpMatrix);
});
```

**İsimlendirme:** Underscore prefix (`_tmpVec3`) — "paylaşımlı mutable, referans saklama"

## C. Object Pool — Dairesel Buffer

Parçacık sistemleri için en basit ve en hızlı pattern:

```typescript
const FRAG_COUNT = 84;
const frags = Array.from({ length: FRAG_COUNT }, () => ({
  pos: new THREE.Vector3(),
  vel: new THREE.Vector3(),
  life: 0,
  max: 1,
}));

let fCur = 0; // dairesel index

function spawnFragment(x: number, y: number, z: number) {
  const fr = frags[fCur];
  fCur = (fCur + 1) % FRAG_COUNT; // dairesel yeniden kullanım
  fr.pos.set(x, y, z);
  fr.vel.set(Math.random() - 0.5, Math.random() + 1, Math.random() - 0.5);
  fr.life = 0;
  fr.max = 0.4 + Math.random() * 0.3;
}
```

## D. Geometry/Material/Texture Yeniden Kullanımı

```typescript
// ❌ KÖTÜ — her tile için yeni geometry
const geo = useMemo(() => new THREE.BoxGeometry(1, 1, 1), []);

// ✅ İYİ — tek geometry tüm tile'lar tarafından paylaşılır
const SHARED_GEO = new THREE.BoxGeometry(1, 1, 1);
```

## E. DataTexture vs Yüklenmiş Texture

| Yaklaşım | RAM | GPU | Toplam | Kontrol |
|----------|-----|-----|--------|---------|
| DataTexture 64×64 | 16KB | ~21KB | ~37KB | Tam |
| PNG 512×512 | 1MB | ~1.3MB | ~1.1MB | Düşük |

## F. dispose() Sırası

```typescript
function disposeObject(obj: THREE.Object3D) {
  obj.traverse((child) => {
    if (child instanceof THREE.Mesh) {
      child.geometry?.dispose();
      if (child.material) {
        if (Array.isArray(child.material)) {
          child.material.forEach(m => { m.map?.dispose(); m.dispose(); });
        } else {
          child.material.map?.dispose();
          child.material.dispose();
        }
      }
    }
  });
  obj.parent?.remove(obj);
}
```

**Önemli:** Paylaşımlı singleton'ları dispose ETMEYİN (TILE_GEO, tileMaterial).

## G. Bellek Bütçesi

| Cihaz Seviyesi | Kullanılabilir RAM | Three.js Bütçesi |
|----------------|-------------------|------------------|
| Düşük Android (2-3GB) | ~300MB | 128MB |
| Orta Android (4-6GB) | ~500MB | 192MB |
| iPhone SE (3GB) | ~400MB | 150MB |
| iPhone 15 Pro (8GB) | ~1.2GB | 256MB |

## H. Yaygın Bellek Sızıntıları

| Sızıntı Kaynağı | Belirti | Çözüm |
|-----------------|---------|-------|
| Geometry dispose edilmemiş | `gl.info.memory.geometries` artar | Cleanup'ta `geo.dispose()` |
| Event listener kaldırılmamış | Callback closure'ı tutar | `useEffect` cleanup |
| Zustand subscription bırakılmamış | Store subscriber'ı tutar | Unsubscribe return |
| Render'da texture oluşturulur | Texture sayısı artar | Modül scope veya `useMemo` |

## Referans Doküman
- [`mobile_memory_management_zero_gc_patterns.md`](../researches/mobile_memory_management_zero_gc_patterns.md)
