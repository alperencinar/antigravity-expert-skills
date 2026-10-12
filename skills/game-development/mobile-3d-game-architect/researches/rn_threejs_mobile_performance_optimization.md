# React Native + Three.js Mobile Performance Optimization

> **Date:** July 2026  
> **Scope:** General-purpose reference for 60fps game rendering in React Native with Three.js / React Three Fiber  
> **Target audience:** Mobile game developers building 3D experiences with RN + R3F

---

## Table of Contents

1. [Render Loop Optimization](#1-render-loop-optimization)
2. [60fps Target Strategies](#2-60fps-target-strategies)
3. [Mutable Ref Pattern — Avoiding React Re-renders](#3-mutable-ref-pattern--avoiding-react-re-renders)
4. [InstancedMesh and Draw Call Minimization](#4-instancedmesh-and-draw-call-minimization)
5. [Conditional Matrix and Color Updates](#5-conditional-matrix-and-color-updates)
6. [Shader Pre-compilation](#6-shader-pre-compilation)
7. [Metro Bundler — Dual Three.js Instance Prevention](#7-metro-bundler--dual-threejs-instance-prevention)
8. [Hermes Engine Optimizations for Game Loops](#8-hermes-engine-optimizations-for-game-loops)
9. [React.memo and Component Isolation](#9-reactmemo-and-component-isolation)
10. [Frame-Rate Independent Smoothing](#10-frame-rate-independent-smoothing)
11. [Performance Profiling Tools and Techniques](#11-performance-profiling-tools-and-techniques)
12. [Genre Patterns](#12-genre-patterns)
13. [Sources](#13-sources)

---

## 1. Render Loop Optimization

### useFrame — The Heart of the Game Loop

React Three Fiber exposes `useFrame`, a hook that fires on every animation frame **outside** the React reconciliation cycle. This is the single most important API for performance in R3F games.

```typescript
import { useFrame } from '@react-three/fiber/native';

function GameEntity() {
  const ref = useRef<THREE.Mesh>(null!);

  useFrame((state, delta) => {
    // state.clock — high-res elapsed time
    // delta — seconds since last frame (frame-rate independent)
    ref.current.rotation.y += delta * 0.5;
  });

  return <mesh ref={ref} />;
}
```

**Key rules:**

- **Never call `setState` inside `useFrame`** — this triggers React reconciliation at 60fps, destroying performance.
- **Use `useFrame` for all per-frame mutations** — position, rotation, scale, material uniforms.
- **Multiple `useFrame` hooks are fine** — R3F batches them into a single rAF loop.
- **Use `useFrame` priority parameter** — lower priority runs first; use for ordering dependencies (e.g., physics before render).

### useLayoutEffect vs useEffect for Initial Setup

For 3D scenes, `useLayoutEffect` is critical to prevent visual flickering:

```typescript
useLayoutEffect(() => {
  // Set initial transforms BEFORE the browser paints
  meshRef.current.matrix.copy(initialMatrix);
  meshRef.current.matrixWorldNeedsUpdate = true;
}, []);

useEffect(() => {
  // Non-visual setup can happen after paint
  loadGameAssets();
}, []);
```

**Why it matters:** `useEffect` runs asynchronously after paint. If you set initial positions/scales there, the user sees one frame at origin (0,0,0) before the snap — a visible "flicker." `useLayoutEffect` runs synchronously before paint, preventing this.

### Frame Budget Math

| Target FPS | Frame Budget | Headroom after render |
|-----------|-------------|----------------------|
| 60fps | 16.67ms | ~3-4ms on mid-range devices |
| 30fps | 33.33ms | Comfortable for puzzle games |
| 120fps | 8.33ms | Only flagship devices |

**Rule of thumb:** Budget 12ms for your game logic + render on a 16.67ms frame. The remaining ~4ms absorbs OS overhead, GC pauses, and thermal throttling spikes.

---

## 2. 60fps Target Strategies

### The Performance Budget Checklist

```
┌─────────────────────────────────────────────────┐
│            60fps PERFORMANCE BUDGET              │
├─────────────────────────────────────────────────┤
│ JS Thread (Hermes)    │ ≤ 8ms per frame         │
│ Shadow/Draw calls     │ ≤ 50 draw calls          │
│ Triangle count        │ ≤ 50K on-screen          │
│ Texture memory        │ ≤ 128MB total            │
│ React re-renders      │ 0 per frame (use refs)   │
│ Allocations per frame │ 0 (zero-GC loop)         │
└─────────────────────────────────────────────────┘
```

### Strategy 1: Separate Fast and Slow Paths

The fundamental architecture for RN + Three.js games:

| Data Type | Storage | Update Mechanism | Frequency |
|-----------|---------|-----------------|-----------|
| Camera position | Mutable ref | `useFrame` direct mutation | Every frame |
| Entity transforms | Mutable ref | `useFrame` direct mutation | Every frame |
| Score / combo | Zustand/Redux | `setState` (triggers re-render) | On event |
| UI text | React state | `setState` | On event |
| Game mode | Mutable ref | Direct assignment | On transition |

### Strategy 2: Minimize Bridge Crossings

React Native's JS-to-native bridge is a bottleneck. For Three.js games:

- **Keep game logic in JS** — Hermes is fast enough for game logic at 60fps.
- **Keep rendering in GL** — Three.js draws directly to the GL context.
- **Cross the bridge only for:** user input events, ad display, audio playback, persistence.

### Strategy 3: Thermal Throttling Awareness

Mobile GPUs throttle after sustained load. A scene that runs at 60fps on a development machine can drop to 20fps after 5-10 minutes on a real mobile device as thermal limits kick in ([source](https://www.intelligentgraphicandcode.com/development/threejs-interfaces/performance)).

**Mitigation strategies:**

- Monitor frame times over a rolling window; if average exceeds 20ms for 30 consecutive frames, reduce quality.
- Cap pixel ratio at 2 — one line of code that can **double mobile frame rate** (modern phones render at 3x = 9x pixels).
- Disable shadow mapping and post-processing on thermal throttling detection.
- Implement a "quality tier" system that downgrades gracefully.

```typescript
// Adaptive quality based on frame time rolling average
// Rule: if avg > 20ms for 30 consecutive frames → reduce quality
const frameTimes: number[] = [];
const QUALITY_TIERS = ['low', 'medium', 'high'] as const;

function adaptQuality(delta: number) {
  frameTimes.push(delta);
  if (frameTimes.length > 60) frameTimes.shift();
  const avg = frameTimes.reduce((a, b) => a + b, 0) / frameTimes.length;
  
  if (avg > 0.020) return 'low';    // >20ms → drop to low
  if (avg > 0.014) return 'medium'; // >14ms → medium
  return 'high';
}

// Cap pixel ratio — single biggest mobile win
// renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
```

---

## 3. Mutable Ref Pattern — Avoiding React Re-renders

### The Core Problem

React re-renders are expensive. At 60fps, calling `setState` 60 times per second for position/rotation data will:

1. Trigger React's reconciliation algorithm 60 times/sec
2. Diff the virtual DOM tree
3. Potentially re-render hundreds of components
4. Cause frame drops and jank

### The Solution: Mutable Refs for High-Frequency Data

Store per-frame data in plain mutable objects accessed via `useRef`. These bypass React entirely:

```typescript
// Define the mutable ref shape
interface CubeState {
  yaw: number;
  yawVel: number;
  snapVel: number;
  quaternion: THREE.Quaternion;
}

// Create as a module-level mutable object
const cubeRef: { current: CubeState } = {
  current: {
    yaw: 0,
    yawVel: 0,
    snapVel: 0,
    quaternion: new THREE.Quaternion(),
  },
};

// In useFrame — direct mutation, zero React involvement
useFrame((_, delta) => {
  cubeRef.current.yaw += cubeRef.current.yawVel * delta;
  cubeRef.current.quaternion.setFromAxisAngle(UP, cubeRef.current.yaw);
});
```

### What Belongs in Refs vs State

| Put in Mutable Ref | Put in React State |
|-------------------|-------------------|
| Entity positions/rotations | Score, combo, lives |
| Camera transforms | Game mode (menu/playing/gameover) |
| Drag state (active, position) | Current theme/level |
| Particle system state | Settings (sound on/off) |
| Physics velocities | High score (persisted) |
| Animation progress (0-1) | UI visibility flags |

### Pattern: Ref + State Hybrid

For data that's mostly mutable but occasionally needs to trigger a re-render:

```typescript
const dragRef = useRef({
  active: false,
  position: new THREE.Vector3(),
  shape: null as PieceDef | null,
});

// Only trigger React re-render when drag ENDS (infrequent)
const [lastPlaced, setLastPlaced] = useState<Cell3[] | null>(null);

useFrame(() => {
  if (dragRef.current.active) {
    // Smooth follow — no React involvement
    lerpPosition(dragRef.current.position, targetPosition);
  }
});

function onDragEnd() {
  dragRef.current.active = false;
  setLastPlaced(committedCells); // This triggers re-render — OK, it's infrequent
}
```

> ### Example: Blocube Implementation
> Blocube uses four mutable ref objects (`cubeRef`, `dragRef`, `fxRef`, `modeRef`) to keep all 60fps data out of React. Only score, combo, theme changes, and game-over trigger Zustand state updates. This separation is the single biggest performance win in the architecture.

---

## 4. InstancedMesh and Draw Call Minimization

### Why Draw Calls Matter

Each draw call has CPU overhead (~5-15μs on mobile). With 100 individual meshes, you're spending 0.5-1.5ms just on draw call setup — before any triangles are rasterized.

**InstancedMesh** renders N objects with **1 draw call** by sending per-instance transforms via a buffer attribute.

### Basic InstancedMesh Setup

```typescript
const COUNT = 25; // 25 tiles per face
const meshRef = useRef<THREE.InstancedMesh>(null!);
const dummy = useMemo(() => new THREE.Object3D(), []);

useLayoutEffect(() => {
  const mesh = meshRef.current;
  for (let i = 0; i < COUNT; i++) {
    const row = Math.floor(i / 5);
    const col = i % 5;
    dummy.position.set(col - 2, row - 2, 0);
    dummy.updateMatrix();
    mesh.setMatrixAt(i, dummy.matrix);
  }
  mesh.instanceMatrix.needsUpdate = true;
}, []);

return (
  <instancedMesh ref={meshRef} args={[TILE_GEO, tileMaterial, COUNT]}>
  </instancedMesh>
);
```

### Draw Call Budget for a Typical Scene

| Element | Without Instancing | With Instancing |
|---------|-------------------|-----------------|
| 100 tiles (4 faces × 25) | 100 draw calls | 4 draw calls |
| 84 fragment particles | 84 draw calls | 1 draw call |
| 48 spark particles | 48 draw calls | 1 draw call |
| **Total** | **232 draw calls** | **~10 draw calls** |

This is a **~23x reduction** in draw calls, directly translating to smoother frame rates on mobile GPUs.

### Real-World Impact (Production Benchmarks)

From [IGC Three.js Performance Lab](https://www.intelligentgraphicandcode.com/development/threejs-interfaces/performance) — measured on a typical Three.js scene with 10,000 objects:

| Metric | Before (Naive) | After (InstancedMesh) |
|--------|---------------|----------------------|
| Draw calls | 10,000 per frame | 3 per frame |
| Frame rate (laptop) | 12-15 fps | 60 fps |
| Frame rate (mobile) | ~8 fps | 45+ fps |
| Memory after 1 hour | 1.2 GB (leaking) | 180 MB (stable) |
| Initial load | 4.2 seconds | 0.8 seconds |

**Key takeaway:** Instanced rendering alone can improve frame rates by **10x or more** for large object counts on integrated/mobile GPUs. The visual output is identical — only the rendering strategy changes.

Also consider **BatchedMesh** (Three.js r159+) for objects that differ in geometry but share a material — it batches different geometries into one draw call while keeping each individually addressable.

### Per-Instance Color

```typescript
const colorArray = new Float32Array(COUNT * 3);
const colorAttr = new THREE.InstancedBufferAttribute(colorArray, 3);
meshRef.current.instanceColor = colorAttr;

// Update color for instance i
const color = new THREE.Color(palette[colorIndex]);
color.toArray(colorArray, i * 3);
colorAttr.needsUpdate = true;
```

### Instancing Limitations

- All instances share the same geometry and material
- Per-instance variation limited to: transform matrix, color (via `instanceColor`)
- For varied materials, use multiple InstancedMesh groups or custom shader attributes via `InstancedBufferAttribute`

---

## 5. Conditional Matrix and Color Updates

### The Problem with Unconditional Updates

Setting `instanceMatrix.needsUpdate = true` every frame uploads the entire transform buffer to the GPU — even if nothing changed. For 25 instances, that's 25 × 16 floats = 1600 bytes uploaded unnecessarily.

### The Solution: Dirty Tracking

```typescript
const lastScale = useRef(new Float32Array(COUNT).fill(1));

useFrame(() => {
  let matrixChanged = false;
  let colorChanged = false;

  for (let i = 0; i < COUNT; i++) {
    const targetScale = faces[faceIdx][row][col] ? placedScale : emptyScale;
    
    // Only update if changed
    if (Math.abs(lastScale.current[i] - targetScale) > 0.001) {
      lastScale.current[i] = targetScale;
      dummy.position.set(...);
      dummy.scale.setScalar(targetScale);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
      matrixChanged = true;
    }

    // Only update color if changed
    const targetColor = getColorForCell(faceIdx, row, col);
    tmpColor.set(targetColor);
    if (!currentColors[i].equals(tmpColor)) {
      tmpColor.toArray(colorArray, i * 3);
      currentColors[i].copy(tmpColor);
      colorChanged = true;
    }
  }

  if (matrixChanged) mesh.instanceMatrix.needsUpdate = true;
  if (colorChanged) (mesh.instanceColor as InstancedBufferAttribute).needsUpdate = true;
});
```

### Performance Impact

| Scenario | Unconditional | Conditional |
|----------|--------------|-------------|
| Static scene (no changes) | Full buffer upload every frame | Zero GPU uploads |
| 1 cell changed | Full buffer upload | 1 matrix + 1 color update |
| All cells changing | Full buffer upload | Full buffer upload (same) |

For puzzle games where the board is static 90% of the time, conditional updates eliminate **~90% of unnecessary GPU buffer uploads**.

---

## 6. Shader Pre-compilation

### The First-Frame Stutter Problem

Three.js lazily compiles shaders on first use. The first time a material is rendered, WebGL must:

1. Compile the GLSL vertex shader
2. Compile the GLSL fragment shader
3. Link the program
4. Validate state

This takes 50-200ms per material — an visible stutter on the first frame.

### Solution: Force Compilation on Canvas Mount

```typescript
import { Canvas } from '@react-three/fiber/native';

function App() {
  return (
    <Canvas
      onCreated={(state) => {
        // Force-compile all shaders before first visible frame
        state.gl.compile(state.scene, state.camera);
      }}
    >
      <GameScene />
    </Canvas>
  );
}
```

The `gl.compile()` call (exposed by Three.js) traverses the scene graph and pre-compiles every material's shader program synchronously.

### When to Use

- **Always** for game scenes with multiple materials
- Especially important when materials are created dynamically (theme changes, procedural materials)
- Combine with a loading screen that hides the compilation frame

### Advanced: Async Compilation (Three.js r150+)

```typescript
// For non-blocking compilation on supported devices
if (state.gl.extensions.has('KHR_parallel_shader_compile')) {
  state.gl.compile(state.scene, state.camera);
  // Shaders compile in background; first frames use fallback
}
```

> ### Example: Blocube Implementation
> Blocube calls `state.gl.compile(state.scene, state.camera)` in the Canvas `onCreated` callback. This pre-compiles shaders for all tile materials, FX materials (additive blending sparks, shockwave rings), and backdrop elements before the user sees the first frame.

---

## 7. Metro Bundler — Dual Three.js Instance Prevention

### The Problem

React Three Fiber internally uses `require('three')` (CommonJS), while application code uses `import * as THREE from 'three'` (ESM). Metro's module resolver may treat these as **different modules**, bundling Two copies of Three.js:

- **Bundle size:** +600KB gzipped (Three.js is large)
- **Runtime:** `instanceof THREE.Object3D` checks fail across instances, causing silent rendering bugs
- **Memory:** Two sets of internal state, two WebGL state managers

### Solution: Metro Resolver Alias

```javascript
// metro.config.js
const { getDefaultConfig } = require('expo/metro-config');
const config = getDefaultConfig(__dirname);

config.resolver.resolveRequest = (context, moduleName, platform) => {
  // Force all 'three' imports to the CJS build
  if (moduleName === 'three' || moduleName.startsWith('three/')) {
    return {
      filePath: require.resolve('three/build/three.cjs'),
      type: 'sourceFile',
    };
  }
  return context.resolveRequest(context, moduleName, platform);
};

module.exports = config;
```

### Verification

After applying the fix, verify with:

```bash
# Check bundle for duplicate Three.js
npx react-native-bundle-visualizer | grep three

# Should show only ONE instance of three/build/three.cjs
```

### Symptoms of Dual Instances

- `mesh.material` is not an `instanceof THREE.Material`
- R3F internals throw "Expected Object3D" errors
- Bundle size is unexpectedly large (>5MB for a simple scene)
- `scene.traverse()` doesn't find meshes created by R3F

---

## 8. Hermes Engine Optimizations for Game Loops

> **Real-world benchmarks (Meta, Callstack, community data 2024-2026):**
> - Cold start: **25-40% faster** TTI (e.g., Pixel 4a: 3.2s → 1.9s)
> - Runtime memory: **30-50MB reduction** after Hermes migration
> - APK size: JavaScript payload **15-25% smaller** (bytecode vs source)
> - OOM crash rate: **15-20% fewer** crashes on 2-3GB RAM devices
> - Sources: [Meta Engineering Blog](https://reactnative.dev/blog/2021/10/26/toward-hermes-being-the-default), [MetaDesign Solutions](https://metadesignsolutions.com/blog/optimizing-react-native-apps-with-the-hermes-javascript-engine)

### What is Hermes?

Hermes is Meta's JavaScript engine optimized for React Native. Key features for games:

| Feature | Benefit for Games |
|---------|------------------|
| **AOT compilation** | JS → bytecode at build time; faster startup |
| **Memory-mapped bytecode** | OS pages out unused segments under memory pressure |
| **Optimized interpreter** | Lower memory usage than JSC/V8 |
| **Generational GC (GenGC)** | Short-lived objects collected efficiently in young gen |
| **Lazy function compilation** | Functions compiled only when first called — reduces initial footprint |
| **No JIT (iOS)** | Consistent frame times (no JIT compilation pauses) |

### Hermes-Specific Game Loop Tips

**1. Avoid string operations in hot paths**

```typescript
// BAD — creates garbage every frame
const key = `${col},${row}`;
set.has(key);

// GOOD — numeric encoding, zero allocation
const key = col * 100 + row;
set.has(key);
```

**2. Prefer typed arrays for bulk data**

```typescript
// Grid data as typed array — cache-friendly, no object overhead
const grid = new Int8Array(25); // 25 cells, 1 byte each

// vs. object array — 25 object headers + property lookups
const grid = [{ filled: false }, { filled: true }, ...];
```

**3. Pre-compute at module load**

```typescript
// Module-level computation runs once, not per-frame
const THEME_OBJS = THEMES.map((t) => ({
  blocks: t.palette.map((hex) => new THREE.Color(hex)),
}));

// Pre-computed transform matrices
const FACE_TF = FACE_DEFS.map((f) => {
  const m = new THREE.Matrix4().makeBasis(f.right, f.up, f.normal);
  const quat = new THREE.Quaternion().setFromRotationMatrix(m);
  return { quat, pos: f.normal.clone().multiplyScalar(FACE_DIST) };
});
```

### Hermes GC Behavior

Hermes uses a **generational garbage collector**:

- **Young generation:** Frequently collected (every ~100ms). Short-lived objects (loop temporaries) are collected here.
- **Old generation:** Less frequently collected. Long-lived objects (game state, refs) are promoted here.

**Implication:** Creating small temporary objects in `useFrame` is not catastrophic — they'll be collected in the young generation. But **avoid creating objects that survive** (closures capturing state, growing arrays) as they'll be promoted to old gen.

---

## 9. React.memo and Component Isolation

### The Re-render Cascade Problem

When a parent component's state changes, ALL children re-render by default. In a game scene:

```
App (score changes)
├── Canvas → re-renders (unnecessary)
│   ├── Scene → re-renders (unnecessary)
│   │   ├── FaceTiles x4 → re-render (unnecessary)
│   │   ├── ClearFX → re-renders (unnecessary)
│   │   └── CameraRig → re-renders (unnecessary)
├── ScoreDisplay → re-renders (NEEDED)
└── TrayUI → re-renders (unnecessary)
```

### Solution: Component Isolation with React.memo

```typescript
// ScoreDisplay is the ONLY component that needs score updates
const ScoreDisplay = React.memo(({ score }: { score: number }) => {
  return <Text style={styles.score}>{score}</Text>;
});

// FaceTiles doesn't receive score as prop — it reads from Zustand selectively
const FaceTiles = React.memo(({ faceIdx }: { faceIdx: number }) => {
  // Select only the data this face needs
  const faceData = useGame((s) => s.faces[faceIdx]);
  // ...
});
```

### Zustand Selectors for Fine-Grained Subscriptions

```typescript
// BAD — subscribes to entire store; re-renders on ANY state change
const { score, theme, faces } = useGame();

// GOOD — subscribes only to 'score'; re-renders only when score changes
const score = useGame((s) => s.score);

// GOOD — shallow comparison for object selectors
const { theme, gameOver } = useGame(
  (s) => ({ theme: s.theme, gameOver: s.gameOver }),
  shallow,
);
```

### Subscription Pattern for Side Effects

```typescript
// Trigger sound effect on clear — WITHOUT re-rendering App
useEffect(() => {
  const unsub = useGame.subscribe((state, prev) => {
    if (state.clearEvent.id !== prev.clearEvent.id) {
      playClearSound(state.clearEvent.combo);
    }
  });
  return unsub;
}, []);
```

> ### Example: Blocube Implementation
> Blocube isolates the `ScoreCounter` into its own component so score updates don't re-render the 3D scene. Sound effects are triggered via `useGame.subscribe()` — a Zustand subscription outside React's render cycle — preventing unnecessary App re-renders.

---

## 10. Frame-Rate Independent Smoothing

> **Reference:** [Frame Rate Independent Damping using Lerp](https://www.rorydriscoll.com/2016/03/07/frame-rate-independent-damping-using-lerp/) — Rory Driscoll

### The Problem with Naive Lerp

```typescript
// BAD — frame-rate dependent
position.lerp(target, 0.1); // Different speed at 30fps vs 60fps vs 120fps
```

At 30fps, `lerp(target, 0.1)` moves 3 units/sec. At 60fps, it moves 6 units/sec. At 120fps, 12 units/sec. The smoothing is **coupled to frame rate**.

**Why `lerp(a, b, r * deltaTime)` is also wrong:** The interpolation parameter can exceed 1 when deltaTime is large (e.g., after a GC pause), producing undefined behavior.

### The Mathematical Foundation

The naive lerp `a(t+1) = lerp(b, a(t), r)` is a discrete exponential decay. Generalizing to arbitrary time steps:

```
a(t + n) = lerp(a(t), b, 1 - Pow(r, n))
```

Converting to continuous exponential decay form (`r = e^(-λ)`):

```
a(t + dt) = lerp(a(t), b, 1 - e^(-λ · dt))
```

This is the **mathematically exact** frame-rate independent damping function. It produces identical results at any frame rate.

### The Exponential Decay Formula

```typescript
useFrame((_, delta) => {
  // k = smoothing factor, independent of frame rate
  const k = 1 - Math.exp(-delta * SPEED);
  
  // Apply to any interpolation
  position.lerp(targetPosition, k);
  quaternion.slerp(targetQuaternion, k);
  currentValue += (targetValue - currentValue) * k;
});
```

**How it works:**

- `SPEED` (λ) controls how fast the value converges — range is 0 to ∞
- `1 - Math.exp(-delta * SPEED)` produces the same smoothing regardless of delta
- At any frame rate, the value reaches ~95% of target in `3/SPEED` seconds
- **Clamp delta** to avoid spikes: `Math.min(delta, 0.05)` prevents huge jumps after GC pauses

### Choosing the SPEED Parameter

| SPEED Value | Time to 95% | Use Case |
|------------|-------------|----------|
| 7 | ~0.43s | Slow camera follow |
| 12 | ~0.25s | UI element smoothing |
| 19 | ~0.16s | Drag follow (responsive) |
| 30 | ~0.10s | Snappy feedback |
| 50 | ~0.06s | Near-instant snap |

### Common Applications

```typescript
// Camera distance smoothing
cameraDistance += (targetDistance - cameraDistance) * (1 - Math.exp(-delta * 8));

// Position follow (drag preview)
const k = 1 - Math.exp(-delta * 19);
previewPosition.lerp(targetPosition, k);

// Rotation smoothing
quaternion.slerp(targetQuaternion, 1 - Math.exp(-delta * 12));

// UI opacity fade
opacity += (targetOpacity - opacity) * (1 - Math.exp(-delta * 15));
```

> ### Example: Blocube Implementation
> Blocube uses `k = 1 - Math.exp(-dt * 19)` for drag preview position following, providing responsive but smooth tracking that feels identical on 60Hz and 120ProMotion displays.

---

## 11. Performance Profiling Tools and Techniques

### Tool Stack for RN + Three.js Games

| Tool | What It Measures | Platform |
|------|-----------------|----------|
| **React DevTools Profiler** | Component re-renders, commit times | All |
| **Hermes CPU Profiler** | JS execution time, function hotspots | All |
| **Xcode Instruments (Time Profiler)** | Native thread activity, main thread stalls | iOS |
| **Android GPU Inspector** | GPU frame time, draw calls, overdraw | Android |
| **Flipper** | Network, layout, JS thread monitoring | All |
| **R3F built-in stats** | Draw calls, triangles, FPS | All |
| **Custom frame timer** | Per-frame delta tracking | All |

### Custom FPS Monitor Pattern

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

### Diagnostic Decision Tree

**Start with draw calls every time** — they are the cheapest metric to read and the most common cause of poor performance ([source](https://www.intelligentgraphicandcode.com/development/threejs-interfaces/performance)):

| What you see | Likely bottleneck | Where to look |
|-------------|-------------------|---------------|
| High draw calls, low FPS | CPU-bound on submission overhead | Instancing, BatchedMesh, material reuse |
| Low draw calls, still slow | GPU-bound on fill rate or shaders | Simpler materials, lower pixel ratio |
| Long JS blocks per frame | CPU-bound on update logic | Pre-allocate objects, throttle raycasting |
| Regular GC spikes and stutter | Allocation churn in render loop | Reuse vectors/matrices, zero-alloc loop |
| Memory climbing over time | Missing dispose() calls | Audit disposal sequence, check renderer.info |
| Fine at first, degrades after minutes | Thermal throttling on mobile | Adaptive quality, rolling frame-time monitor |

```
Frame drops detected
├── Is JS thread at 100%?
│   ├── YES → Hermes profiler → find hot function
│   │   ├── React re-renders? → Add React.memo, fix selectors
│   │   ├── GC pauses? → Zero-allocation loop (see Memory doc)
│   │   └── Game logic? → Optimize algorithm, pre-compute
│   └── NO → GPU bound
│       ├── Too many draw calls? → InstancedMesh
│       ├── Too many triangles? → LOD, simpler geometry
│       ├── Overdraw? → Reduce transparent materials
│       └── Shader complexity? → Simplify materials
├── Is it periodic (every N seconds)?
│   ├── YES → GC pause or ad loading
│   └── NO → Thermal throttling or background task
└── Is it on specific actions?
    ├── On scene mount → Shader compilation (pre-compile!)
    ├── On state change → Unnecessary re-renders
    └── On touch → Bridge congestion
```

### React DevTools Profiler Setup

```typescript
// Enable profiling in development
import { Profiler } from 'react';

function onRender(id: string, phase: string, actualDuration: number) {
  if (actualDuration > 5) {
    console.warn(`[Slow Render] ${id} took ${actualDuration.toFixed(1)}ms in ${phase}`);
  }
}

<Profiler id="GameScene" onRender={onRender}>
  <Scene3D />
</Profiler>
```

---

## 12. Genre Patterns

### 12.1 Puzzle Games (Grid-Based)

**Render pattern:** Static grid with event-driven updates. The board is idle 90% of the time — between player moves, zero GPU work should happen.

```typescript
// Puzzle grid: only update changed cells
useFrame(() => {
  let changed = false;
  for (let i = 0; i < GRID_SIZE; i++) {
    if (grid[i] !== lastGrid[i]) {
      updateTileVisual(i, grid[i]);
      lastGrid[i] = grid[i];
      changed = true;
    }
  }
  if (changed) mesh.instanceMatrix.needsUpdate = true;
});
```

**Key optimizations:**
- InstancedMesh for grid cells (1 draw call for entire board)
- Conditional updates — grid is static between moves
- React.memo for tray/piece selector (only updates on new pieces)
- Pre-compute all piece geometries at load time
- Use `useLayoutEffect` for grid initialization (no flicker)
- Clear animations use a pre-allocated particle pool with circular buffer
- Theme transitions: swap `Color` references, don't create new materials
- Drag preview: frame-rate independent lerp (`1 - Math.exp(-dt * 19)`)
- Score display: isolated component so score changes don't re-render the 3D scene

**Draw call budget:** 4-6 for the board (1 per face InstancedMesh) + 1-2 for effects + 1 for preview = ~10 total.

**Performance target:** 60fps with zero per-frame allocations when idle. During clear animations, only the affected cells update matrices.

**Common pitfalls:**
- Creating new `THREE.Color` objects per cell per frame → GC stutter
- Not using `useLayoutEffect` for initial matrix setup → white flicker on first frame
- Subscribing to entire Zustand store instead of selecting specific fields → cascade re-renders

### 12.2 Runner Games (Endless Scroll)

**Render pattern:** Continuous camera/world movement with chunk recycling. Unlike puzzle games, every frame requires work — the world never stops moving.

```typescript
// Chunk-based infinite scroll
const CHUNK_COUNT = 5;
const chunks = useRef(
  Array.from({ length: CHUNK_COUNT }, (_, i) => ({
    position: new THREE.Vector3(0, 0, -i * CHUNK_LENGTH),
    active: true,
  }))
);

useFrame((_, delta) => {
  const cameraZ = camera.position.z;
  for (const chunk of chunks.current) {
    // Recycle chunks that fall behind camera
    if (chunk.position.z > cameraZ + CHUNK_LENGTH) {
      chunk.position.z -= CHUNK_COUNT * CHUNK_LENGTH;
      regenerateChunk(chunk);
    }
  }
});
```

**Key optimizations:**
- Object pool for obstacles/enemies (see Memory doc)
- Chunk recycling — never create/destroy meshes at runtime
- Frustum culling enabled (unlike puzzle FX) — only render visible chunks
- LOD system: detailed meshes within 20m, simplified beyond
- Scroll speed in a mutable ref, not React state
- Stagger obstacle generation: don't regenerate all chunks in one frame
- Cap `delta` to prevent teleporting after GC pauses: `Math.min(delta, 0.05)`
- Use `BatchedMesh` (r159+) for obstacles that share material but differ in shape

**Performance-critical pattern — staggered chunk regeneration:**
```typescript
// Don't regenerate all chunks in one frame — spread the work
let regenIndex = 0;
useFrame(() => {
  if (pendingRegen.length > 0) {
    const chunk = pendingRegen[regenIndex % pendingRegen.length];
    regenerateChunk(chunk); // One chunk per frame — spreads CPU cost
    regenIndex++;
    if (regenIndex >= pendingRegen.length) pendingRegen.length = 0;
  }
});
```

**Draw call budget:** 5-8 for chunks + 1-2 for player + 1 for projectiles/pickups = ~15 total.

**Performance target:** Consistent 60fps during continuous movement. Watch for allocation spikes during chunk regeneration — stagger work across frames. Thermal throttling is the #1 enemy on mobile after 5-10 minutes of sustained rendering.

### 12.3 Idle Games (Background Performance)

**Render pattern:** Minimal animation, background-friendly. The game must be kind to battery and CPU since sessions can last hours.

```typescript
// Idle game: reduce work when backgrounded
useFrame((state, delta) => {
  if (document.hidden || state.clock.elapsedTime - lastInteraction > 60) {
    // Reduce to 10fps when idle
    if (frameSkip++ % 6 !== 0) return;
  }
  // Background animations (floating, rotation)
  updateAmbientAnimations(delta);
});
```

**Key optimizations:**
- Frame skipping when no user interaction (60fps → 10fps after 60s idle)
- Batch resource accumulation into periodic ticks (not per-frame)
- Use `AppState` listener to pause rendering when app backgrounded
- Minimal draw calls — most idle games are 2.5D or simple 3D
- Consider switching to a static screenshot when fully idle (zero GPU cost)
- Ambient animations: simple sine-wave floating, no physics
- Use `MeshBasicMaterial` instead of `MeshStandardMaterial` for idle decorations (no lighting calculations)
- Particle effects: use Points (GPU point sprites) instead of InstancedMesh for very large counts

**Adaptive rendering pipeline:**
```typescript
// Progressive quality reduction for idle
const IDLE_THRESHOLDS = {
  immediate: 10,   // 10s: reduce to 30fps
  short: 30,       // 30s: reduce to 15fps, disable particles
  medium: 60,      // 60s: reduce to 10fps, simplify materials
  long: 300,       // 5min: static screenshot mode
};
```

**Draw call budget:** 2-5 total (background + a few animated elements).

**Performance target:** 30fps is acceptable; battery life > visual fidelity. Target < 5% CPU usage in idle mode.

### 12.4 Tower Defense (Entity Batching)

**Render pattern:** Many heterogeneous entities with periodic updates. The challenge is hundreds of moving entities with different behaviors, all needing to render efficiently.

```typescript
// Batch similar entities into InstancedMesh groups
const ENEMY_TYPES = 4;
const MAX_PER_TYPE = 50;

// Pre-create one InstancedMesh per enemy type
const enemyMeshes = enemyTypes.map((type, idx) => (
  <instancedMesh
    key={idx}
    ref={enemyRefs.current[idx]}
    args={[type.geometry, type.material, MAX_PER_TYPE]}
    count={0} // starts empty
  />
));

useFrame(() => {
  for (let t = 0; t < ENEMY_TYPES; t++) {
    const mesh = enemyRefs.current[t];
    let count = 0;
    for (const enemy of enemiesByType[t]) {
      dummy.position.copy(enemy.position);
      dummy.rotation.y = enemy.facing;
      dummy.scale.setScalar(enemy.health / enemy.maxHealth);
      dummy.updateMatrix();
      mesh.setMatrixAt(count, dummy.matrix);
      count++;
    }
    mesh.count = count;
    mesh.instanceMatrix.needsUpdate = true;
  }
});
```

**Key optimizations:**
- Batch enemies by type into InstancedMesh (4 draw calls for 200 enemies)
- Projectiles: single InstancedMesh with small sphere geometry (1 draw call for 100+)
- Tower range indicators: shared material, reuse geometry, toggle `visible`
- Pathfinding: compute on staggered intervals (not every frame for every tower)
- Use spatial hashing for collision detection instead of brute force O(n²)
- Health bars: use a single InstancedMesh with thin box geometry, scale by health %
- Tower attack animations: reuse a single "beam" or "projectile" pool
- Wave spawning: pre-allocate all enemy slots, activate/deactivate via `mesh.count`

**Staggered AI updates:**
```typescript
// Don't update all tower AI every frame — stagger across frames
const towersPerFrame = Math.ceil(towers.length / 3); // Update 1/3 each frame
useFrame((state) => {
  const frameIdx = Math.floor(state.clock.elapsedTime * 60) % 3;
  const start = frameIdx * towersPerFrame;
  const end = Math.min(start + towersPerFrame, towers.length);
  for (let i = start; i < end; i++) {
    updateTowerAI(towers[i]); // Target acquisition, firing logic
  }
});
```

**Draw call budget:** 4 for enemies (by type) + 1 for projectiles + 1 for health bars + 2-3 for towers + 1 for terrain = ~10-12 total.

**Performance target:** 60fps with 100+ entities. The key is batching by type and staggering AI/pathfinding updates across frames. Pathfinding for 50 towers at 20fps (staggered 3x) is imperceptible to the player but saves 66% of AI CPU time.

---

## 13. Sources

1. React Three Fiber — Scaling Performance — https://r3f.docs.pmnd.rs/advanced/scaling-performance
2. Three.js InstancedMesh Guide — https://threejs.org/docs/#api/en/objects/InstancedMesh
3. Hermes Engine — https://hermesengine.dev/
4. React Native Performance Profiler — https://reactnative.dev/docs/profiling
5. Metro Bundler Configuration — https://metrobundler.dev/docs/configuration/
6. Frame Rate Independent Damping using Lerp — Rory Driscoll — https://www.rorydriscoll.com/2016/03/07/frame-rate-independent-damping-using-lerp/
7. Three.js Shader Pre-compilation — https://threejs.org/docs/#api/en/renderers/WebGLRenderer.compile
8. React.memo Performance — https://react.dev/reference/react/memo
9. Zustand Selectors and Subscriptions — https://docs.pmnd.rs/zustand/getting-started/introduction
10. Mobile GPU Architecture (TBDR) — https://developer.apple.com/library/archive/documentation/3DDrawing/Conceptual/MTLBestPracticesGuide/
11. Three.js Performance Optimisation: 60fps Patterns — IGC — https://www.intelligentgraphicandcode.com/development/threejs-interfaces/performance
12. Expo GL View Documentation — https://docs.expo.dev/versions/latest/sdk/gl-view/
13. Generational GC in Hermes — https://github.com/facebook/hermes/blob/main/doc/GC.md
14. Toward Hermes Being the Default — Meta Engineering Blog — https://reactnative.dev/blog/2021/10/26/toward-hermes-being-the-default
15. Optimizing React Native Apps with Hermes — MetaDesign Solutions — https://metadesignsolutions.com/blog/optimizing-react-native-apps-with-the-hermes-javascript-engine
16. Improved Lerp Smoothing — Game Developer — https://www.gamedeveloper.com/programming/improved-lerp-smoothing-
17. React Native Performance Optimization: 2026 Playbook — https://www.rapidnative.com/blogs/react-native-performance-optimization-2026-playbook
18. WebGL Best Practices — MDN — https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API/WebGL_best_practices
