# Mobile Memory Management & Zero-GC Patterns for React Native + Three.js

> **Date:** July 2026  
> **Scope:** General-purpose reference for minimizing RAM usage and GC pressure in mobile 3D games built with React Native and Three.js  
> **Target audience:** Mobile game developers building memory-efficient 3D experiences with RN + R3F

---

## Table of Contents

1. [RAM Bloat Prevention in RN + Three.js](#1-ram-bloat-prevention-in-rn--threejs)
2. [GC Pressure Reduction — Zero-Allocation Game Loops](#2-gc-pressure-reduction--zero-allocation-game-loops)
3. [Pre-Allocated Object Pooling](#3-pre-allocated-object-pooling)
4. [Geometry / Material / Texture Reuse](#4-geometry--material--texture-reuse)
5. [Singleton Vector3 / Color / Matrix4 Pattern](#5-singleton-vector3--color--matrix4-pattern)
6. [DataTexture vs Loaded Texture Memory Comparison](#6-datatexture-vs-loaded-texture-memory-comparison)
7. [WeakRef and FinalizationRegistry Patterns](#7-weakref-and-finalizationregistry-patterns)
8. [Memory Leak Detection Tools](#8-memory-leak-detection-tools)
9. [Expo GL Context Loss Recovery](#9-expo-gl-context-loss-recovery)
10. [Three.js dispose() Patterns](#10-threejs-dispose-patterns)
11. [Module-Level Singleton Allocation](#11-module-level-singleton-allocation)
12. [Genre Patterns](#12-genre-patterns)
13. [Sources](#13-sources)

---

## 1. RAM Bloat Prevention in RN + Three.js

> **Key insight from production data:** E-commerce apps report **30-50MB memory reduction** after migrating to Hermes. Budget Android devices (Redmi Note series) show the largest improvements. OOM kills reduce crash rates by 15-20%. ([source](https://metadesignsolutions.com/blog/optimizing-react-native-apps-with-the-hermes-javascript-engine))

### The Mobile Memory Landscape

Mobile devices have significantly less available RAM than desktop:

| Device Tier | Total RAM | Available for App | Three.js Budget |
|------------|-----------|-------------------|-----------------|
| Low-end Android | 2-3GB | ~300MB | 128MB |
| Mid-range Android | 4-6GB | ~500MB | 192MB |
| iPhone SE | 3GB | ~400MB | 150MB |
| iPhone 15 Pro | 8GB | ~1.2GB | 256MB |

**Key insight:** Your app doesn't get all the RAM. The OS, other apps, and system services consume 40-60% of total memory. Exceeding your app's budget triggers the OS low-memory killer.

### Memory Consumers in a RN + Three.js Game

| Layer | Typical Usage | Notes |
|-------|--------------|-------|
| React Native runtime | 30-50MB | JS engine, bridge, native views |
| Three.js scene graph | 20-80MB | Meshes, materials, textures |
| Texture memory (GPU) | 40-120MB | Largest consumer; mipmaps multiply |
| Audio buffers | 5-20MB | Pre-loaded sound effects |
| JavaScript heap | 20-60MB | Game state, object pool, closures |
| **Total target** | **120-330MB** | Varies by device tier |

### Prevention Strategies

**1. Set explicit memory budgets per category**

```typescript
const MEMORY_BUDGET = {
  textures: 80 * 1024 * 1024,   // 80MB GPU texture memory
  geometry: 20 * 1024 * 1024,   // 20MB vertex/index buffers
  audio: 10 * 1024 * 1024,      // 10MB decoded audio
  jsHeap: 40 * 1024 * 1024,     // 40MB JavaScript objects
};

// Track usage at runtime
let textureMemoryUsed = 0;

function trackTexture(width: number, height: number, format: number): number {
  const bytesPerPixel = format === THREE.RGBAFormat ? 4 : 3;
  const size = width * height * bytesPerPixel;
  // Include mipmap chain: total = base * 1.33
  const totalWithMips = Math.floor(size * 1.33);
  textureMemoryUsed += totalWithMips;
  return totalWithMips;
}
```

**2. Prefer procedural generation over asset loading**

Loading image textures requires decoding bitmaps into memory. Procedural `DataTexture` generation uses a typed array that's exactly the right size — no waste.

**3. Monitor memory at runtime**

```typescript
// Hermes exposes memory info
function logMemoryUsage() {
  if (typeof HermesInternal !== 'undefined') {
    const props = HermesInternal.getRuntimeProperties();
    console.log(`[Memory] Heap: ${Math.round(props['heapSize'] / 1048576)}MB`);
  }
  // React Native exposes Process memory
  if (typeof performance !== 'undefined' && 'memory' in performance) {
    const mem = (performance as any).memory;
    console.log(`[Memory] JS Heap: ${Math.round(mem.usedJSHeapSize / 1048576)}MB`);
  }
}
```

**4. Respond to OS memory warnings**

```typescript
import { AppState } from 'react-native';

// iOS sends memory warnings; clear caches when received
AppState.addEventListener('memoryWarning', () => {
  // Dispose non-essential textures
  releaseCachedTextures();
  // Reduce pool sizes
  shrinkObjectPools();
  // Force GC if possible
  if (typeof global.gc !== 'undefined') global.gc();
});
```

---

## 2. GC Pressure Reduction — Zero-Allocation Game Loops

> **Hermes GC behavior:** Hermes uses a **generational, moving garbage collector** (GenGC). Short-lived objects (common in React renders and per-frame allocations) are collected quickly in the young generation. Long-lived objects promote to the old generation with less frequent collection cycles. Memory-mapped bytecode can be paged out by the OS under memory pressure without re-parsing. ([source](https://github.com/facebook/hermes/blob/main/doc/GC.md))

### Why GC Pauses Matter

Every time the garbage collector runs, it pauses JavaScript execution. On Hermes:

- **Young generation GC:** ~1-3ms pause (acceptable)
- **Old generation GC:** ~5-20ms pause (visible frame drop)
- **Full GC:** ~30-100ms pause (major stutter)

At 60fps, you have 16.67ms per frame. A 20ms GC pause drops an entire frame.

### The Zero-Allocation Principle

**Rule: The `useFrame` callback must allocate ZERO objects.**

```typescript
// ❌ BAD — allocates a new Vector3 every frame
useFrame((_, delta) => {
  const direction = new THREE.Vector3(1, 0, 0); // ALLOCATION!
  mesh.position.add(direction.multiplyScalar(delta));
});

// ✅ GOOD — reuses a pre-allocated singleton
const _direction = new THREE.Vector3(1, 0, 0); // allocated once at module load

useFrame((_, delta) => {
  mesh.position.add(_direction.multiplyScalar(delta)); // zero allocation
});
```

### Common Allocation Traps

| Pattern | Allocation? | Fix |
|---------|------------|-----|
| `new THREE.Vector3()` in useFrame | YES — 48 bytes each | Module-level singleton |
| `new THREE.Color('#fff')` in useFrame | YES — ~32 bytes | Pre-compute at module level |
| `array.slice()` in useFrame | YES — new array | Mutate in-place or use ring buffer |
| `${x},${y}` template literal | YES — new string | Numeric encoding: `x * 1000 + y` |
| `{ ...state, score: n }` spread | YES — new object | Mutate ref directly |
| `array.map(fn)` in useFrame | YES — new array | In-place for-loop |
| `array.filter(fn)` in useFrame | YES — new array | Swap-and-pop pattern |
| `closure capturing variables` | Potentially | Avoid closures in hot paths |

### Zero-Allocation Game Loop Template

```typescript
// All temporaries allocated at module level — NEVER inside useFrame
const _tmpVec = new THREE.Vector3();
const _tmpQuat = new THREE.Quaternion();
const _tmpMatrix = new THREE.Matrix4();
const _tmpColor = new THREE.Color();

function GameLoop() {
  useFrame((state, delta) => {
    // All operations reuse pre-allocated objects
    _tmpVec.set(0, 1, 0);
    _tmpQuat.setFromAxisAngle(_tmpVec, state.clock.elapsedTime);
    _tmpMatrix.makeRotationFromQuaternion(_tmpQuat);
    _tmpColor.setHSL((state.clock.elapsedTime * 0.1) % 1, 0.5, 0.5);
    
    // Apply to mesh — no new objects created
    meshRef.current.applyMatrix4(_tmpMatrix);
  });
  
  return null;
}
```

### String Allocation in Game Logic

```typescript
// ❌ BAD — creates a new string every lookup
const key = `${col},${row}`;
const value = myMap.get(key);

// ✅ GOOD — numeric key, zero allocation
const key = col * 100 + row; // for grids < 100x100
const value = myMap.get(key);

// ✅ GOOD — pre-allocated string pool for complex keys
const KEY_POOL_SIZE = 256;
const keyPool = Array.from({ length: KEY_POOL_SIZE }, () => ({ key: '', used: false }));
let keyIdx = 0;

function getKey(col: number, row: number): string {
  const entry = keyPool[keyIdx];
  entry.key = `${col},${row}`;
  keyIdx = (keyIdx + 1) % KEY_POOL_SIZE;
  return entry.key;
}
```

> ### Example: Blocube Implementation
> Blocube's `FaceTiles.useFrame` iterates 25 cells per face with zero allocations. The `_tileObj` Object3D, `tmpColor` Color, and `_fxObj` Object3D are all module-level singletons. The grid uses numeric indices (`i = row * GRID_N + col`) instead of string keys. Conditional `needsUpdate` flags ensure no GPU buffer uploads when the board is static.

---

## 3. Pre-Allocated Object Pooling

> **Reference:** [Object Pool Pattern — Game Programming Patterns](https://gameprogrammingpatterns.com/object-pool.html) by Robert Nystrom. "A pool is an array of reusable objects. You activate one, use it, and return it to the pool." This is the foundational pattern for zero-GC game loops across all game engines.

### The Problem with Dynamic Allocation in Games

Creating and destroying objects during gameplay causes:

1. **GC pressure** — each allocation adds to the heap that must be collected
2. **Memory fragmentation** — freed memory may not be contiguous
3. **Unpredictable pauses** — GC can trigger at any time, causing frame drops

### Object Pool Pattern

```typescript
interface Poolable {
  active: boolean;
  reset(): void;
}

class ObjectPool<T extends Poolable> {
  private items: T[];
  private activeCount = 0;

  constructor(factory: () => T, initialSize: number) {
    this.items = Array.from({ length: initialSize }, () => factory());
    this.activeCount = 0;
  }

  acquire(): T | null {
    for (let i = 0; i < this.items.length; i++) {
      if (!this.items[i].active) {
        this.items[i].active = true;
        this.activeCount++;
        return this.items[i];
      }
    }
    return null; // Pool exhausted — consider expanding or returning null
  }

  release(item: T): void {
    item.active = false;
    item.reset();
    this.activeCount--;
  }

  releaseAll(): void {
    for (const item of this.items) {
      item.active = false;
      item.reset();
    }
    this.activeCount = 0;
  }
}
```

### Circular Buffer Pool (Simpler, Faster)

For particle systems and effects where you don't need to individually release items, a circular buffer is simpler and faster:

```typescript
// Pre-allocate fixed-size array with circular index
const FRAG_COUNT = 84;

interface Fragment {
  pos: THREE.Vector3;
  vel: THREE.Vector3;
  rot: THREE.Vector3;
  life: number;
  max: number;
}

// All fragments allocated once at module load
const frags: Fragment[] = Array.from({ length: FRAG_COUNT }, () => ({
  pos: new THREE.Vector3(),
  vel: new THREE.Vector3(),
  rot: new THREE.Vector3(),
  life: 0,
  max: 1,
}));

// Circular index — wraps around, oldest particles get overwritten
let fCur = 0;

function spawnFragment(x: number, y: number, z: number) {
  const fr = frags[fCur];
  fCur = (fCur + 1) % FRAG_COUNT; // Circular reuse — no allocation, no GC
  
  fr.pos.set(x, y, z);
  fr.vel.set(Math.random() - 0.5, Math.random() + 1, Math.random() - 0.5);
  fr.life = 0;
  fr.max = 0.4 + Math.random() * 0.3;
}
```

**Why circular buffers win for particles:**

- No search for free slot (O(1) acquire)
- Oldest particles naturally expire and get overwritten
- Fixed memory footprint — never grows
- No release call needed — automatic recycling

### Pool Sizing Guidelines

| Entity Type | Typical Pool Size | Sizing Strategy |
|------------|------------------|-----------------|
| Particles (fragments) | 64-128 | Max simultaneous on screen |
| Projectiles | 32-64 | Fire rate × projectile lifetime |
| Enemies | 20-50 | Max concurrent + buffer |
| UI popups | 5-10 | Max visible at once |
| Sound players | 8-16 | Max overlapping sounds |

> ### Example: Blocube Implementation
> Blocube uses three circular buffer pools for clear effects: fragments (84 items, 5 per cell), sparks (48 items, 3 per cell), and shockwaves (3 items). Each pool has a circular cursor (`fCur`, `sCur`, `shCur`) that wraps with modulo arithmetic. When a cell clears, it spawns particles by overwriting the oldest ones — no allocation, no GC, fixed memory.

---

## 4. Geometry / Material / Texture Reuse

### The Singleton Resource Pattern

Three.js resources (Geometry, Material, Texture) are expensive to create and consume significant memory. Create them once, reuse everywhere.

```typescript
// ❌ BAD — creates new geometry for every tile (100+ geometries)
function Tile({ position }: { position: [number, number, number] }) {
  const geo = useMemo(() => new THREE.BoxGeometry(1, 1, 1), []);
  return <mesh geometry={geo} position={position} />;
}

// ✅ GOOD — single geometry shared by all tiles (1 geometry)
const SHARED_GEO = new THREE.BoxGeometry(1, 1, 1);

function Tile({ position }: { position: [number, number, number] }) {
  return <mesh geometry={SHARED_GEO} position={position} />;
}
```

### Memory Cost of Three.js Resources

| Resource | Memory Cost | Notes |
|----------|------------|-------|
| `BoxGeometry(1,1,1)` | ~2KB | 24 vertices, 36 indices |
| `ExtrudeGeometry` (complex) | ~10-50KB | Depends on curveSegments/bevelSegments |
| `MeshStandardMaterial` | ~5KB | Uniforms, shader program |
| `DataTexture(64×64)` RGBA | ~16KB + GPU | 64×64×4 = 16KB RAM, ~21KB GPU with mips |
| `DataTexture(128×128)` RGBA | ~64KB + GPU | 128×128×4 = 64KB RAM, ~85KB GPU with mips |
| Loaded PNG (512×512) | ~1MB + GPU | Decoded bitmap in memory |

### Material Sharing with Per-Instance Variation

```typescript
// Single material shared across all tiles
const tileMaterial = new THREE.MeshStandardMaterial({
  roughness: 0.4,
  metalness: 0.1,
});

// Per-instance color via InstancedMesh.instanceColor
// Per-instance transform via InstancedMesh.instanceMatrix
// → 1 material for N instances
```

### Theme-Switching Without Re-creating Resources

```typescript
// Pre-create all theme materials at startup
const themeMaterials = THEMES.map((t) =>
  new THREE.MeshStandardMaterial({
    roughness: t.roughness,
    metalness: t.metalness,
  })
);

// Switch by reference — no allocation
function getMaterial(themeIndex: number) {
  return themeMaterials[themeIndex];
}
```

> ### Example: Blocube Implementation
> Blocube creates `TILE_GEO` (rounded ExtrudeGeometry) and `PREVIEW_GEO` once at module load — shared across all 100+ tile instances via InstancedMesh. FX geometries (`FRAG_GEO`, `SPARK_GEO`) are similarly singleton. Textures (`GLOW_TEX`, `RING_TEX`) are procedural DataTextures created once. Five theme materials are pre-created in `THEME_OBJS` with their Color objects.

---

## 5. Singleton Vector3 / Color / Matrix4 Pattern

### The Pattern

Declare temporary math objects at module scope and reuse them across all frames:

```typescript
// Module level — allocated ONCE, reused FOREVER
const _tmpVec3 = new THREE.Vector3();
const _tmpColor = new THREE.Color();
const _tmpMatrix = new THREE.Matrix4();
const _tmpQuat = new THREE.Quaternion();
const _tmpObj3D = new THREE.Object3D();

// In useFrame — mutate, use, never store references
useFrame(() => {
  _tmpVec3.set(1, 2, 3);
  _tmpColor.set('#ff0000');
  _tmpMatrix.makeTranslation(_tmpVec3.x, _tmpVec3.y, _tmpVec3.z);
  
  meshRef.current.applyMatrix4(_tmpMatrix);
  // _tmpVec3, _tmpColor, etc. are "dirty" now — that's fine,
  // they'll be overwritten next frame before use
});
```

### Rules for Singleton Temporaries

1. **Name with underscore prefix** (`_tmpVec3`) — signals "shared mutable, don't store references"
2. **Never return a singleton from a function** — callers might store the reference
3. **Always `.set()` or `.copy()` before use** — don't assume previous frame's values
4. **One per purpose is enough** — you don't need separate Vector3 for each entity
5. **Module scope, not component scope** — shared across all component instances

### How Much Memory This Saves

```typescript
// Without singletons: each useFrame call allocates
useFrame(() => {
  const pos = new THREE.Vector3();    // 48 bytes × 60fps = 2.8KB/sec
  const col = new THREE.Color();      // 32 bytes × 60fps = 1.9KB/sec
  const mat = new THREE.Matrix4();    // 80 bytes × 60fps = 4.8KB/sec
  // Total: ~9.5KB/sec → triggers GC every ~2 seconds
});

// With singletons: zero per-frame allocation
// Total: 0 bytes/sec → GC never triggered by frame loop
```

### Naming Convention for Multiple Temporaries

When you need multiple temporaries in the same frame (e.g., computing distance between two points):

```typescript
const _v1 = new THREE.Vector3();
const _v2 = new THREE.Vector3();
// Usage: _v1.set(a); _v2.set(b); const dist = _v1.distanceTo(_v2);

// Or descriptive names for clarity
const _tileObj = new THREE.Object3D();  // Used to compute tile matrices
const _fxObj = new THREE.Object3D();    // Used to compute FX matrices
const _cw = new THREE.Vector3();        // Cell world position
const _tgt = new THREE.Vector3();       // Target position for lerping
```

> ### Example: Blocube Implementation
> Blocube declares five module-level singletons: `_tileObj` (Object3D for tile matrix computation), `_fxObj` (Object3D for FX matrix computation), `_cw` (Vector3 for cell world position), `_tgt` (Vector3 for lerp targets), and `tmpColor` (Color for per-instance color updates). These are reused across all 60fps frames with zero allocation.

---

## 6. DataTexture vs Loaded Texture Memory Comparison

### DataTexture Advantages

`DataTexture` generates pixel data procedurally in a typed `Uint8Array` — no image decoding, no file I/O, exact memory control.

```typescript
// Procedural glow texture — 64×64 RGBA = exactly 16KB
function makeGlowTexture(size = 64): THREE.DataTexture {
  const data = new Uint8Array(size * size * 4); // 16,384 bytes — exact
  const center = (size - 1) / 2;
  
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const dx = (x - center) / center;
      const dy = (y - center) / center;
      const dist = Math.min(1, Math.sqrt(dx * dx + dy * dy));
      const alpha = Math.pow(1 - dist, 3); // Cubic falloff
      const i = (y * size + x) * 4;
      data[i] = 255;       // R
      data[i + 1] = 255;   // G
      data[i + 2] = 255;   // B
      data[i + 3] = Math.round(alpha * 255); // A
    }
  }
  
  const tex = new THREE.DataTexture(data, size, size, THREE.RGBAFormat);
  tex.needsUpdate = true;
  return tex;
}
```

### Memory Comparison Table

| Approach | RAM (source) | RAM (decoded) | GPU | Total | Control |
|----------|-------------|--------------|-----|-------|---------|
| DataTexture 64×64 RGBA | 16KB | 16KB | ~21KB | ~37KB | Exact |
| DataTexture 128×128 RGBA | 64KB | 64KB | ~85KB | ~149KB | Exact |
| PNG 64×64 (file) | ~1KB (compressed) | 16KB (decoded) | ~21KB | ~38KB | Partial |
| PNG 512×512 (file) | ~50KB (compressed) | 1MB (decoded) | ~1.3MB | ~1.1MB | Low |
| PNG 1024×1024 (file) | ~200KB | 4MB (decoded) | ~5.3MB | ~4.2MB | Low |

**Key insight:** File size on disk is irrelevant — what matters is the **decoded bitmap** in memory. A 1KB compressed PNG still becomes 16KB when decoded. DataTexture eliminates the compressed source entirely and gives you exact control over dimensions.

### When to Use DataTexture

- Procedural effects (glow, noise, gradient, rings)
- Small utility textures (< 128×128)
- Dynamic textures that change at runtime
- When you want to avoid asset loading pipeline

### When to Use Loaded Textures

- Photo-realistic textures (PBR maps, normal maps)
- Art assets created by artists (illustrations, icons)
- Large textures where procedural generation would be too slow
- Texture atlases (SpriteAtlas pattern)

> ### Example: Blocube Implementation
> Blocube uses two procedural DataTextures: `makeGlowTexture(64)` for spark particles (radial gradient with cubic falloff) and `makeRingTexture(128)` for shockwave rings (bright ring at 80% radius). Both are created once at module load. This eliminates all texture asset loading — zero network/file I/O, exact memory control, and no async decoding stalls.

---

## 7. WeakRef and FinalizationRegistry Patterns

> **Reference:** [Weak references and finalizers — V8](https://v8.dev/features/weak-references), [TC39 Proposal](https://github.com/tc39/proposal-weakrefs), [javascript.info](https://javascript.info/weakref-finalizationregistry)  
> **Caveat:** "Their correct use takes careful thought, and they are best avoided if possible." — TC39. Use these for **caches and resource tracking only**, never as core data structures.

### WeakRef — Hold Without Preventing GC

`WeakRef` lets you reference an object without preventing its garbage collection:

```typescript
// Cache expensive computations, but allow GC to reclaim if memory is tight
const computationCache = new Map<string, WeakRef<ComputedResult>>();

function getExpensiveResult(key: string): ComputedResult {
  const weak = computationCache.get(key);
  if (weak) {
    const cached = weak.deref();
    if (cached) return cached; // Still alive — use it
  }
  
  // Compute fresh
  const result = computeExpensiveResult(key);
  computationCache.set(key, new WeakRef(result));
  return result;
}
```

### FinalizationRegistry — Cleanup on GC

`FinalizationRegistry` runs a callback when an object is garbage collected:

```typescript
// Track when Three.js resources are GC'd (leak detection)
const resourceRegistry = new FinalizationRegistry((label: string) => {
  console.log(`[GC] Resource collected: ${label}`);
  trackedResourceCount--;
});

function createTrackedGeometry(label: string): THREE.BufferGeometry {
  const geo = new THREE.BoxGeometry(1, 1, 1);
  trackedResourceCount++;
  resourceRegistry.register(geo, label, geo); // Third arg = holder (prevent self-reference)
  return geo;
}
```

### Practical Pattern: Auto-Disposing Cache

```typescript
class DisposableCache<K, V extends { dispose(): void }> {
  private map = new Map<K, WeakRef<V>>();
  private registry: FinalizationRegistry<K>;

  constructor() {
    this.registry = new FinalizationRegistry((key: K) => {
      // Object was GC'd — clean up the cache entry
      this.map.delete(key);
    });
  }

  get(key: K): V | undefined {
    const ref = this.map.get(key);
    return ref?.deref();
  }

  set(key: K, value: V): void {
    this.map.set(key, new WeakRef(value));
    this.registry.register(value, key, value);
  }
}
```

### Caveats

- `WeakRef.deref()` may return `undefined` at any time — always check
- FinalizationRegistry callbacks are **not guaranteed** to run
- Don't use WeakRef for objects you **need** — only for caches/optimizations
- Hermes support: WeakRef available since Hermes 0.11+ (Expo SDK 49+)

---

## 8. Memory Leak Detection Tools

> **From the Three.js community:** "GPU memory grows linearly with session length. After an hour, the tab crashes." This is the #1 cause of long-session crashes in Three.js apps. The disposal sequence (geometry → material → textures → null references) must be followed for **every** removed object, or GPU memory accumulates silently. ([source](https://discourse.threejs.org/t/webgl-memory-management-puzzlers/24583), [source](https://ritik-chopra28.medium.com/why-your-three-js-app-is-secretly-eating-gpu-memory-and-how-to-stop-it-fe8ca6b2f72d))

### Tool Stack

| Tool | What It Detects | Platform |
|------|----------------|----------|
| **Xcode Instruments (Allocations)** | Object allocation tracking, leaked objects | iOS |
| **Android Studio Profiler** | Heap dumps, allocation tracking | Android |
| **Hermes Heap Snapshot** | JS heap analysis, retained objects | All |
| **Chrome DevTools (Memory tab)** | Heap snapshots, allocation timeline | Debug builds |
| **FinalizationRegistry logging** | Custom GC tracking for Three.js resources | All |
| **Three.js Memory Inspector** | `renderer.info.memory` — geometry/texture count | All |

### Three.js Built-in Memory Tracking

```typescript
// Three.js tracks resource counts internally
useFrame((state) => {
  const info = state.gl.info;
  // Log every 60 frames
  if (frameCount.current++ % 60 === 0) {
    console.log(`[Three.js] Geometries: ${info.memory.geometries}`);
    console.log(`[Three.js] Textures: ${info.memory.textures}`);
    console.log(`[Three.js] Draw calls: ${info.render.calls}`);
    console.log(`[Three.js] Triangles: ${info.render.triangles}`);
  }
});
```

**Expected behavior:** Geometry and texture counts should be **stable** after initial load. If they grow over time, you have a leak.

### Leak Detection Pattern

```typescript
// Track resource creation/disposal
const resourceTracker = {
  geometries: new Set<THREE.BufferGeometry>(),
  materials: new Set<THREE.Material>(),
  textures: new Set<THREE.Texture>(),
};

function trackGeo(geo: THREE.BufferGeometry) {
  resourceTracker.geometries.add(geo);
  return geo;
}

function disposeGeo(geo: THREE.BufferGeometry) {
  geo.dispose();
  resourceTracker.geometries.delete(geo);
}

// Periodic audit
function auditResources() {
  console.log(`[Audit] Tracked geometries: ${resourceTracker.geometries.size}`);
  console.log(`[Audit] Tracked materials: ${resourceTracker.materials.size}`);
  console.log(`[Audit] Tracked textures: ${resourceTracker.textures.size}`);
  
  // If counts grow unbounded → leak
  if (resourceTracker.geometries.size > EXPECTED_MAX_GEO) {
    console.error('[LEAK] Geometry count exceeds expected maximum!');
  }
}
```

### Hermes Heap Snapshot (Debug Builds)

```typescript
// In development, capture heap snapshots
function captureHeapSnapshot() {
  if (__DEV__ && typeof HermesInternal !== 'undefined') {
    HermesInternal.enableGCLogging?.();
    // Force GC and log stats
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

### Common Leak Sources in RN + Three.js

| Leak Source | Symptom | Fix |
|------------|---------|-----|
| Geometry not disposed on unmount | `gl.info.memory.geometries` grows | Call `geo.dispose()` in cleanup |
| Event listener not removed | Callback retains component closure | Return cleanup from `useEffect` |
| Zustand subscription not unsubscribed | Store retains subscriber closures | Return unsubscribe from `useEffect` |
| Texture created in render | Texture count grows on re-render | Move to module scope or `useMemo` |
| setInterval not cleared | Interval callback retains references | Clear in cleanup function |
| Three.js scene not cleared | Old meshes retained in scene graph | Remove children + dispose on unmount |

---

## 9. Expo GL Context Loss Recovery

> **From Khronos WebGL spec:** When the GL context is lost, **all** GPU resources (textures, buffers, programs, render targets) are destroyed. The application must call `event.preventDefault()` in the `webglcontextlost` handler to signal it wants restoration, then re-upload all resources in the `webglcontextrestored` handler. ([source](https://www.khronos.org/webgl/wiki/HandlingContextLost))

### The Problem

On mobile, the OpenGL context can be lost when:

- App is backgrounded and the GPU reclaims resources
- Device runs low on memory
- Phone receives a call (on some Android devices)
- Thermal throttling forces GPU reset

When the GL context is lost, **all textures, buffers, and programs are destroyed**. The screen goes blank or shows corrupted rendering.

### Detection

```typescript
import { useThree } from '@react-three/fiber/native';

function GLContextWatcher() {
  const gl = useThree((s) => s.gl);

  useEffect(() => {
    const canvas = gl.domElement;
    
    const onLost = (event: Event) => {
      event.preventDefault(); // Required to allow restoration
      console.warn('[GL] Context lost — pausing render');
      // Pause game loop
      modeRef.mode = 'paused';
    };

    const onRestored = () => {
      console.log('[GL] Context restored — rebuilding resources');
      // Re-upload textures, recompile shaders
      rebuildGLResources();
    };

    canvas.addEventListener('webglcontextlost', onLost);
    canvas.addEventListener('webglcontextrestored', onRestored);
    
    return () => {
      canvas.removeEventListener('webglcontextlost', onLost);
      canvas.removeEventListener('webglcontextrestored', onRestored);
    };
  }, [gl]);

  return null;
}
```

### Recovery Strategy

```typescript
// Track all disposable resources for rebuild
const glResources = {
  textures: [] as THREE.Texture[],
  geometries: [] as THREE.BufferGeometry[],
  materials: [] as THREE.Material[],
};

function registerTexture(tex: THREE.Texture) {
  glResources.textures.push(tex);
  return tex;
}

function rebuildGLResources() {
  // 1. Re-upload textures (DataTexture needs needsUpdate = true)
  for (const tex of glResources.textures) {
    if (tex instanceof THREE.DataTexture) {
      tex.needsUpdate = true; // Re-uploads pixel data to GPU
    }
  }
  
  // 2. Recompile shaders
  // R3F handles this automatically on next render,
  // but you can force it:
  // gl.compile(scene, camera);
  
  // 3. Resume game
  modeRef.mode = 'game';
}
```

### Expo GL Patch Considerations

Expo's GL implementation may require patches for specific device issues. For example, iOS simulator may need retained backing enabled for the first frame to render correctly. Always test GL context loss on real devices.

### Prevention

```typescript
// Reduce context loss risk
import { AppState } from 'react-native';

AppState.addEventListener('change', (state) => {
  if (state === 'background') {
    // Reduce GL pressure before backgrounding
    // Dispose large render targets
    // Keep essential textures
  } else if (state === 'active') {
    // Check if context survived
    // If not, rebuild
  }
});
```

---

## 10. Three.js dispose() Patterns

> **Critical:** GPU resources are **not** garbage collected by JavaScript's GC. Unlike JS objects, Three.js geometries, materials, and textures occupy GPU memory that must be **explicitly freed**. Failing to call `.dispose()` creates memory leaks that accumulate over the user's session. A typical Three.js app without proper disposal can consume **1.2GB+ in one hour** vs. **180MB stable** with proper disposal. ([source](https://www.intelligentgraphicandcode.com/development/threejs-interfaces/performance))

### What dispose() Does

Every Three.js resource holds GPU memory (WebGL buffers, textures, programs). `dispose()` releases this GPU memory:

| Resource | What dispose() Frees |
|----------|---------------------|
| `BufferGeometry` | Vertex buffer, index buffer on GPU |
| `Material` | Shader program, uniform locations |
| `Texture` / `DataTexture` | GPU texture memory (including mipmaps) |
| `RenderTarget` | Color + depth buffers on GPU |
| `InstancedMesh` | Instance buffer (calls geometry.dispose + own buffer) |

### The Dispose Sequence

```typescript
// Correct disposal order for a scene subtree
function disposeObject(obj: THREE.Object3D) {
  // 1. Traverse and dispose children first
  obj.traverse((child) => {
    if (child instanceof THREE.Mesh) {
      // 2. Dispose geometry
      child.geometry?.dispose();
      
      // 3. Dispose material(s)
      if (child.material) {
        if (Array.isArray(child.material)) {
          child.material.forEach((m) => disposeMaterial(m));
        } else {
          disposeMaterial(child.material);
        }
      }
    }
  });
  
  // 4. Remove from parent
  obj.parent?.remove(obj);
}

function disposeMaterial(material: THREE.Material) {
  // Dispose material textures
  const mat = material as THREE.MeshStandardMaterial;
  mat.map?.dispose();
  mat.normalMap?.dispose();
  mat.roughnessMap?.dispose();
  mat.metalnessMap?.dispose();
  mat.emissiveMap?.dispose();
  mat.aoMap?.dispose();
  
  // Dispose the material itself
  material.dispose();
}
```

### React Component Cleanup Pattern

```typescript
function GameScene() {
  const groupRef = useRef<THREE.Group>(null);
  
  useEffect(() => {
    return () => {
      // Cleanup on unmount — prevent GPU memory leak
      if (groupRef.current) {
        disposeObject(groupRef.current);
      }
    };
  }, []);
  
  return <group ref={groupRef}>...</group>;
}
```

### What NOT to Dispose

```typescript
// ❌ DON'T dispose shared singleton resources
const SHARED_GEO = new THREE.BoxGeometry(1, 1, 1);

function TileA() {
  useEffect(() => {
    return () => {
      SHARED_GEO.dispose(); // WRONG! Other components still use this
    };
  }, []);
  return <mesh geometry={SHARED_GEO} />;
}

// ✅ DO dispose only resources you exclusively own
function DynamicEffect() {
  const geo = useMemo(() => new THREE.SphereGeometry(0.5), []);
  
  useEffect(() => {
    return () => {
      geo.dispose(); // Correct — this geometry is owned by this component
    };
  }, [geo]);
  
  return <mesh geometry={geo} />;
}
```

### Dispose Checklist for Scene Transitions

```typescript
function cleanupScene() {
  // 1. Stop all animations / useFrame callbacks
  
  // 2. Dispose all dynamic resources
  dynamicGeometries.forEach(g => g.dispose());
  dynamicMaterials.forEach(m => m.dispose());
  dynamicTextures.forEach(t => t.dispose());
  
  // 3. Clear object pools
  fragmentPool.length = 0;
  sparkPool.length = 0;
  
  // 4. Clear resource tracking
  glResources.textures.length = 0;
  glResources.geometries.length = 0;
  
  // 5. Reset renderer info
  renderer.info.reset();
  
  // 6. Do NOT dispose shared singletons (TILE_GEO, tileMaterial, etc.)
}
```

> ### Example: Blocube Implementation
> Blocube's singleton resources (`TILE_GEO`, `PREVIEW_GEO`, `FRAG_GEO`, `SPARK_GEO`, `GLOW_TEX`, `RING_TEX`) are created at module load and intentionally never disposed — they live for the entire app lifecycle. Only the pre-allocated object pools (fragments, sparks, shockwaves) are reset between game sessions by clearing their circular cursors (`fCur = 0`, `sCur = 0`, `shCur = 0`) without disposing the underlying InstancedMesh resources.

---

## 11. Module-Level Singleton Allocation

### The Pattern

Allocate all game resources at module load time, not at component mount time:

```typescript
// Module scope — runs once when the file is imported
// These objects live for the entire app lifecycle

// Geometries
const TILE_GEO = createRoundedTileGeometry(0.82, 0.16, 0.16, 0.055);
const FRAG_GEO = new THREE.BoxGeometry(1, 1, 0.5);
const SPARK_GEO = new THREE.PlaneGeometry(1, 1);

// Textures
const GLOW_TEX = makeGlowTexture(64);
const RING_TEX = makeRingTexture(128);

// Colors (pre-computed for all theme × block combinations)
const THEME_COLORS = THEMES.map((t) =>
  t.palette.map((hex) => new THREE.Color(hex || '#000000'))
);

// Temporaries (reused every frame)
const _tileObj = new THREE.Object3D();
const _fxObj = new THREE.Object3D();
const _tmpColor = new THREE.Color();

// Object pools (pre-allocated, circular buffer)
const FRAG_COUNT = 84;
const fragments = Array.from({ length: FRAG_COUNT }, () => ({
  pos: new THREE.Vector3(),
  vel: new THREE.Vector3(),
  life: 0,
  max: 1,
}));
```

### Why Module Level?

| Aspect | Module Level | Component Level (useMemo) |
|--------|-------------|--------------------------|
| Allocated when | App starts (once) | Component mounts (may re-mount) |
| Survives re-renders | Yes — always | Yes — but may be recreated |
| Survives hot reload | No (module re-evaluated) | No (component re-mounts) |
| GC-able | Never (module scope) | Potentially (on unmount) |
| Predictable timing | Yes — at import | No — depends on render order |

### Memory Cost of Module-Level Singletons

```
Module-level allocations (one-time cost):
  TILE_GEO (ExtrudeGeometry):    ~30KB
  PREVIEW_GEO:                   ~30KB
  FRAG_GEO (BoxGeometry):        ~2KB
  SPARK_GEO (PlaneGeometry):     ~1KB
  GLOW_TEX (64×64 DataTexture):  ~16KB RAM + ~21KB GPU
  RING_TEX (128×128 DataTexture): ~64KB RAM + ~85KB GPU
  84 Fragment pool objects:      ~12KB (84 × ~140 bytes each)
  48 Spark pool objects:         ~7KB
  3 Shockwave pool objects:      ~1KB
  THEME_OBJS (5 themes × 7 colors): ~2KB
  Singleton temporaries:         ~0.5KB
  ─────────────────────────────────────
  Total one-time cost:           ~165KB RAM + ~106KB GPU
```

This is a **fixed, predictable** memory footprint that never grows — the foundation of zero-GC game architecture.

### Module-Level vs Lazy Initialization

```typescript
// Eager — everything at module load (simpler, predictable)
const GEO = new THREE.BoxGeometry(1, 1, 1);
const MAT = new THREE.MeshStandardMaterial();

// Lazy — create on first use (saves startup time, same memory)
let _expensiveGeo: THREE.BoxGeometry | null = null;
function getExpensiveGeo() {
  if (!_expensiveGeo) {
    _expensiveGeo = new THREE.BoxGeometry(1, 1, 1);
  }
  return _expensiveGeo;
}
```

**Recommendation:** Use eager initialization for small resources (< 100KB). Use lazy for expensive resources (complex geometry generation, large DataTexture computation).

---

## 12. Genre Patterns

### 12.1 Puzzle Games (Piece Cache & Grid Memory)

**Memory pattern:** Fixed grid + piece cache, minimal dynamic allocation. The grid is the core data structure — it must be as compact as possible.

```typescript
// Pre-allocate all piece geometries at startup
const PIECE_GEOS: Map<string, THREE.BufferGeometry> = new Map();

function initPieceCache() {
  for (const pieceDef of ALL_PIECE_DEFINITIONS) {
    const geo = buildPieceGeometry(pieceDef);
    PIECE_GEOS.set(pieceDef.id, geo);
  }
}

// During gameplay — zero allocation piece retrieval
function getPieceMesh(pieceId: string): THREE.BufferGeometry {
  return PIECE_GEOS.get(pieceId)!; // Cached, never allocated at runtime
}

// Grid as typed array — minimal memory footprint
const GRID_SIZE = 8;
const grid = new Int8Array(GRID_SIZE * GRID_SIZE); // 64 bytes for 8×8
// vs. number[][] = 8 arrays × 8 objects = 64 object headers + properties
```

**Key memory strategies:**
- Fixed-size grid as `Int8Array` (1 byte per cell vs. ~100 bytes for object)
- Pre-computed piece geometries (create once, reference by ID)
- No texture loading — use DataTexture or vertex colors
- Flash/clear animations reuse a pool of effect objects
- Theme changes swap color references, not new materials
- Pre-allocated `THEME_OBJS` array: `Color` objects for every theme × block combination at module load
- `setTimeout` for animation cleanup (flash/placed arrays cleared after animation completes — not polled per-frame)

**Memory breakdown:**
| Component | Memory |
|-----------|--------|
| Grid (4 faces × 5×5 Int8Array) | ~100 bytes |
| Piece geometries (shared) | ~30KB |
| Tile InstancedMesh (×4 faces) | ~20KB |
| FX pools (84 frags + 48 sparks) | ~20KB |
| DataTextures (glow + ring) | ~80KB RAM + ~106KB GPU |
| Theme color objects | ~2KB |
| **Total** | **~150KB + 106KB GPU** |

**Typical memory budget:** 30-60MB total including RN runtime, JS heap, and GPU (grid + pieces + effects + UI).

### 12.2 Runner Games (Obstacle Pooling)

**Memory pattern:** Large pool of recyclable obstacles, chunk-based streaming. Memory must remain flat during gameplay — no growth over long sessions.

```typescript
// Obstacle pool — pre-allocate maximum simultaneous obstacles
const MAX_OBSTACLES = 40;
const obstaclePool = Array.from({ length: MAX_OBSTACLES }, () => ({
  mesh: new THREE.Group(),
  type: 0,
  speed: 0,
  active: false,
  bounds: new THREE.Box3(),
}));

// Chunk pool — recycle world segments
const CHUNK_COUNT = 6;
const chunkPool = Array.from({ length: CHUNK_COUNT }, () => ({
  meshes: [] as THREE.Mesh[],
  zPosition: 0,
  active: false,
}));

function recycleChunk(oldIndex: number, newZ: number) {
  const chunk = chunkPool[oldIndex];
  // Reset positions, regenerate content — no new meshes
  chunk.zPosition = newZ;
  for (const mesh of chunk.meshes) {
    mesh.position.z = 0; // Relative to chunk
  }
}
```

**Key memory strategies:**
- Fixed-size obstacle pool (never create/destroy meshes during gameplay)
- Chunk recycling — move old chunks ahead instead of creating new ones
- Shared geometry for all obstacles of the same type (InstancedMesh per type)
- LOD: detailed meshes within 20m, simplified beyond
- Dispose distant chunks' high-res textures, keep low-res always loaded
- Collision bounds as struct-of-arrays (typed arrays) instead of per-object Box3
- Audio: 2-3 short pre-loaded WAV clips, seekTo(0) + play() for low-latency restart

**Pool sizing formula:**
```typescript
// Obstacle pool size = max simultaneous on screen × safety margin
// For a runner at 10m/s with 50m view distance and 2 obstacles per 10m:
const MAX_OBSTACLES = Math.ceil(VIEW_DISTANCE / OBSTACLE_SPACING) * 1.5;
// = Math.ceil(50 / 10) * 1.5 = 8 → round up to 16 for burst spawns
```

**Memory breakdown:**
| Component | Memory |
|-----------|--------|
| Obstacle pool (40 groups) | ~200KB |
| Chunk meshes (6 chunks × ~10 meshes) | ~500KB |
| Shared geometries (5 types) | ~50KB |
| Streaming textures (2 LOD levels) | ~2-4MB |
| Player mesh + animations | ~100KB |
| **Total** | **~3-5MB scene** |

**Typical memory budget:** 80-150MB (obstacle meshes + chunk geometry + streaming textures + RN runtime).

**Critical:** Memory must remain flat over 30+ minute sessions. If `renderer.info.memory.geometries` grows, chunks are leaking.

### 12.3 Idle Games (Entity Management)

**Memory pattern:** Many long-lived entities with periodic state updates. The entity list grows over time as the player progresses — must handle growth without unbounded memory.

```typescript
// Entity pool with fixed capacity — never grows
const MAX_ENTITIES = 200;
const entities = Array.from({ length: MAX_ENTITIES }, () => ({
  active: false,
  type: 0,
  level: 1,
  position: new THREE.Vector3(),
  production: 0,
  lastCollected: 0,
}));

// Batch state updates — not per-frame
let lastBatchUpdate = 0;
const BATCH_INTERVAL = 1.0; // Update economy every 1 second

useFrame((state) => {
  if (state.clock.elapsedTime - lastBatchUpdate >= BATCH_INTERVAL) {
    lastBatchUpdate = state.clock.elapsedTime;
    batchUpdateEntities(); // Single pass, no per-entity allocation
  }
});
```

**Key memory strategies:**
- Fixed entity array with active/inactive flags (pre-allocated, never grows)
- Batch updates (economy tick every 1s) instead of per-frame per-entity
- Background mode: reduce to static screenshot or 10fps
- Persist entity state to disk periodically (not every change)
- Minimal 3D — most idle games are 2D with occasional 3D elements
- Audio: use short, pre-loaded clips; avoid long music tracks in memory
- Save data as compact JSON (not full entity serialization)
- Use `WeakRef` for cached computation results (allow GC under memory pressure)

**Entity state persistence:**
```typescript
// Save only essential state — not the full entity objects
type SaveState = {
  entities: Array<{ type: number; level: number; pos: [number, number, number] }>;
  lastTick: number;
  resources: number;
};

// Compact serialization: ~20 bytes per entity vs ~200 bytes for full object
function serializeEntities(): SaveState {
  return {
    entities: entities
      .filter(e => e.active)
      .map(e => ({ type: e.type, level: e.level, pos: [e.position.x, e.position.y, e.position.z] })),
    lastTick: Date.now(),
    resources: totalResources,
  };
}
```

**Typical memory budget:** 40-80MB (mostly UI textures; 3D is minimal). Save file should be < 50KB.

### 12.4 Tower Defense (Projectile Pooling)

**Memory pattern:** Many projectiles + enemies, all pooled and recycled. The most memory-intensive genre due to simultaneous entity counts.

```typescript
// Projectile pool — shared InstancedMesh for all projectile types
const MAX_PROJECTILES = 100;
const projectileGeo = new THREE.SphereGeometry(0.15, 4, 4); // Low-poly
const projectileMat = new THREE.MeshBasicMaterial({ color: 0xffff00 });
const projectileMesh = new THREE.InstancedMesh(projectileGeo, projectileMat, MAX_PROJECTILES);

const projectileData = Array.from({ length: MAX_PROJECTILES }, () => ({
  active: false,
  pos: new THREE.Vector3(),
  vel: new THREE.Vector3(),
  target: -1, // Enemy index, -1 = free
  damage: 0,
}));

let projCursor = 0;

function fireProjectile(from: THREE.Vector3, targetIdx: number, dmg: number) {
  const p = projectileData[projCursor];
  projCursor = (projCursor + 1) % MAX_PROJECTILES;
  
  p.active = true;
  p.pos.copy(from);
  p.target = targetIdx;
  p.damage = dmg;
  // vel computed in useFrame toward target
}

// Enemy pool — InstancedMesh per enemy type
const MAX_ENEMIES_PER_TYPE = 30;
const enemyTypes = ['basic', 'fast', 'tank', 'flying'];
const enemyPools = enemyTypes.map((type) => ({
  mesh: new THREE.InstancedMesh(
    getEnemyGeo(type),
    getEnemyMat(type),
    MAX_ENEMIES_PER_TYPE,
  ),
  data: Array.from({ length: MAX_ENEMIES_PER_TYPE }, () => ({
    active: false,
    pos: new THREE.Vector3(),
    health: 0,
    maxHealth: 0,
    speed: 0,
    pathIndex: 0,
  })),
}));
```

**Key memory strategies:**
- All projectiles in a single InstancedMesh (1 draw call for 100 projectiles)
- Enemies batched by type into InstancedMesh (4 draw calls for 120 enemies)
- Circular buffer for projectiles (oldest overwritten when pool full)
- Tower range indicators: shared geometry, toggled via `visible` flag
- Pathfinding data: typed arrays, not object graphs
- Wave spawning: reuse enemy pool slots, never create new meshes
- Health bars: single InstancedMesh with thin box, scale by health %
- Tower models: pre-allocated at level start, not created/destroyed per wave

**Pool sizing for tower defense:**
```typescript
// Projectile pool = max towers × fire rate × projectile lifetime × safety
// 20 towers × 2 shots/sec × 1.5s flight time × 1.5 safety = 90 → round to 100
const MAX_PROJECTILES = TOWER_COUNT * FIRE_RATE * FLIGHT_TIME * SAFETY_MARGIN;

// Enemy pool per type = max enemies in wave / type count × safety
// 30 enemies per wave / 4 types × 1.5 safety = ~12 → round to 30 for burst waves
const MAX_PER_TYPE = Math.ceil(MAX_WAVE_SIZE / ENEMY_TYPES.length * 1.5);
```

**Memory breakdown:**
| Component | Memory |
|-----------|--------|
| Projectile InstancedMesh (100) | ~50KB |
| Enemy InstancedMeshes (4 × 30) | ~200KB |
| Tower models (20 pre-allocated) | ~500KB |
| Terrain + path mesh | ~200KB |
| Shared geometries (5-6 types) | ~50KB |
| Health bar InstancedMesh | ~10KB |
| **Total scene** | **~1MB** |

**Typical memory budget:** 60-120MB (enemy geometries + projectile pool + tower models + terrain + RN runtime).

**Critical:** Pool exhaustion must be handled gracefully — when all 100 projectile slots are active, the circular buffer overwrites the oldest. This is invisible to the player (old projectiles are already far away).

---

## 13. Sources

1. Three.js — How to Dispose of Objects — https://threejs.org/docs/#manual/en/introduction/How-to-dispose-of-objects
2. Hermes JavaScript Engine — https://hermesengine.dev/
3. React Native Performance — https://reactnative.dev/docs/performance#memory
4. WebGL Context Loss Handling — Khronos — https://www.khronos.org/webgl/wiki/HandlingContextLost
5. Expo GL View Documentation — https://docs.expo.dev/versions/latest/sdk/gl-view/
6. Three.js InstancedMesh — https://threejs.org/docs/#api/en/objects/InstancedMesh
7. DataTexture API — https://threejs.org/docs/#api/en/textures/DataTexture
8. Weak References and Finalizers — V8 — https://v8.dev/features/weak-references
9. TC39 WeakRefs Proposal — https://github.com/tc39/proposal-weakrefs
10. WeakRef and FinalizationRegistry — javascript.info — https://javascript.info/weakref-finalizationregistry
11. Xcode Instruments Allocations — https://developer.apple.com/documentation/xcode/gathering-information-about-memory-use
12. Android Studio Memory Profiler — https://developer.android.com/studio/profile/memory-profiler
13. Object Pool Pattern — Game Programming Patterns (R. Nystrom) — https://gameprogrammingpatterns.com/object-pool.html
14. Mobile Memory Best Practices — Apple — https://developer.apple.com/documentation/xcode/reducing-your-app-s-memory-use
15. Generational GC in Hermes — https://github.com/facebook/hermes/blob/main/doc/GC.md
16. Three.js Renderer Info — https://threejs.org/docs/#api/en/renderers/WebGLRenderer.info
17. Three.js Performance Optimisation: 60fps Patterns — IGC — https://www.intelligentgraphicandcode.com/development/threejs-interfaces/performance
18. WebGL Memory Management Puzzlers — Three.js Forum — https://discourse.threejs.org/t/webgl-memory-management-puzzlers/24583
19. Why Your Three.js App is Eating GPU Memory — Medium — https://ritik-chopra28.medium.com/why-your-three-js-app-is-secretly-eating-gpu-memory-and-how-to-stop-it-fe8ca6b2f72d
20. Optimizing React Native Apps with Hermes — MetaDesign Solutions — https://metadesignsolutions.com/blog/optimizing-react-native-apps-with-the-hermes-javascript-engine
21. Toward Hermes Being the Default — Meta Blog — https://reactnative.dev/blog/2021/10/26/toward-hermes-being-the-default
22. React Three Fiber — Scaling Performance — https://r3f.docs.pmnd.rs/advanced/scaling-performance
