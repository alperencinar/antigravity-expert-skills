# React Native + Three.js: Asset Pipeline, Verification & Production Readiness

> **Scope:** General-purpose reference for building 3D mobile games with React Native, Expo, and Three.js. Covers procedural geometry, asset loading, texture management, build configuration, performance monitoring, debug logging, patching native modules, testing strategies, and genre-specific patterns.
>
> **Audience:** Mobile game developers targeting iOS and Android with a shared React Native + Three.js codebase.

---

## Table of Contents

1. [Procedural Geometry Generation](#1-procedural-geometry-generation)
2. [GLTF/GLB Loading with drei/useGLTF](#2-gltfglb-loading-with-dreiusetgltf)
3. [Texture Loading, Caching, and Disposal Patterns](#3-texture-loading-caching-and-disposal-patterns)
4. [Metro Config for Three.js (Preventing Dual-Bundle)](#4-metro-config-for-threejs-preventing-dual-bundle)
5. [EAS Build Optimization for Mobile Games](#5-eas-build-optimization-for-mobile-games)
6. [FPS Monitoring and Performance Logging](#6-fps-monitoring-and-performance-logging)
7. [Debug Logging Patterns](#7-debug-logging-patterns)
8. [Production Readiness Checklist](#8-production-readiness-checklist)
9. [patch-package for Native Module Fixes](#9-patch-package-for-native-module-fixes)
10. [Testing Strategies for RN+Three.js Games](#10-testing-strategies-for-rnthreejs-games)
11. [Genre Patterns](#11-genre-patterns)
12. [Sources](#12-sources)

---

## 1. Procedural Geometry Generation

Procedural geometry eliminates asset file dependencies, reduces bundle size, and enables runtime customization — critical for mobile games where every MB counts.

### ExtrudeGeometry

`ExtrudeGeometry` creates 3D shapes from 2D paths with optional beveling. Ideal for puzzle pieces, tiles, and architectural elements.

```typescript
import * as THREE from 'three';

function createRoundedTile(
  size: number,
  radius: number,
  depth: number,
  bevel: number
): THREE.ExtrudeGeometry {
  const w = size;
  const x = -w / 2;
  const r = radius;
  const shape = new THREE.Shape();

  // Rounded rectangle path
  shape.moveTo(x + r, x);
  shape.lineTo(x + w - r, x);
  shape.quadraticCurveTo(x + w, x, x + w, x + r);
  shape.lineTo(x + w, x + w - r);
  shape.quadraticCurveTo(x + w, x + w, x + w - r, x + w);
  shape.lineTo(x + r, x + w);
  shape.quadraticCurveTo(x, x + w, x, x + w - r);
  shape.lineTo(x, x + r);
  shape.quadraticCurveTo(x, x, x + r, x);

  const geo = new THREE.ExtrudeGeometry(shape, {
    depth,
    bevelEnabled: true,
    bevelThickness: bevel,
    bevelSize: bevel,
    bevelSegments: 1,     // Keep low for mobile perf
    steps: 1,
    curveSegments: 3,     // Lower = fewer triangles
  });

  geo.center();
  geo.computeVertexNormals();
  return geo;
}

// Cache at module level — generate once, reuse everywhere
const TILE_GEO = createRoundedTile(0.82, 0.16, 0.16, 0.055);
```

**Performance tips for ExtrudeGeometry on mobile:**
- Keep `curveSegments` at 3–6 (visible difference is minimal)
- Keep `bevelSegments` at 1–2
- Cache geometry at module scope; never recreate per-render
- Use `geo.center()` once at creation, not per-frame

### LatheGeometry

`LatheGeometry` rotates a 2D profile around the Y-axis. Perfect for vases, bottles, columns, and organic shapes.

```typescript
function createVaseGeometry(segments = 12): THREE.LatheGeometry {
  const points: THREE.Vector2[] = [];

  // Define profile curve (bottom to top)
  points.push(new THREE.Vector2(0, 0));       // center bottom
  points.push(new THREE.Vector2(0.4, 0.1));   // base flare
  points.push(new THREE.Vector2(0.3, 0.3));   // narrow waist
  points.push(new THREE.Vector2(0.35, 0.5));  // belly
  points.push(new THREE.Vector2(0.5, 0.7));   // widest point
  points.push(new THREE.Vector2(0.45, 0.85)); // neck taper
  points.push(new THREE.Vector2(0.2, 0.95));  // narrow neck
  points.push(new THREE.Vector2(0.25, 1.0));  // lip

  const geo = new THREE.LatheGeometry(points, segments);
  geo.computeVertexNormals();
  return geo;
}

// For mobile: 8-16 segments is usually sufficient
const vaseGeo = createVaseGeometry(12);
```

### BufferGeometry (Custom Vertices)

For maximum control and performance, build geometry from raw vertex data.

```typescript
function createHexGrid(cols: number, rows: number, hexRadius: number): THREE.BufferGeometry {
  const positions: number[] = [];
  const normals: number[] = [];
  const uvs: number[] = [];

  const hexHeight = hexRadius * Math.sqrt(3);
  const horizSpacing = hexRadius * 1.5;
  const vertSpacing = hexHeight;

  for (let col = 0; col < cols; col++) {
    for (let row = 0; row < rows; row++) {
      const cx = col * horizSpacing;
      const cy = row * vertSpacing + (col % 2 === 0 ? 0 : vertSpacing / 2);

      // 6 vertices per hexagon (2 triangles)
      for (let i = 0; i < 6; i++) {
        const angle1 = (Math.PI / 3) * i + Math.PI / 6;
        const angle2 = (Math.PI / 3) * ((i + 1) % 6) + Math.PI / 6;

        positions.push(cx, cy, 0);
        positions.push(cx + hexRadius * Math.cos(angle1), cy + hexRadius * Math.sin(angle1), 0);
        positions.push(cx + hexRadius * Math.cos(angle2), cy + hexRadius * Math.sin(angle2), 0);

        normals.push(0, 0, 1, 0, 0, 1, 0, 0, 1);
        uvs.push(0.5, 0.5, Math.cos(angle1) * 0.5 + 0.5, Math.sin(angle1) * 0.5 + 0.5,
                 Math.cos(angle2) * 0.5 + 0.5, Math.sin(angle2) * 0.5 + 0.5);
      }
    }
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geo.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
  geo.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  return geo;
}
```

### InstancedMesh for Repeated Geometry

When rendering many copies of the same geometry (grid cells, particles, debris), `InstancedMesh` reduces draw calls from N to 1.

```typescript
import { useRef } from 'react';
import { useFrame } from '@react-three/fiber/native';
import * as THREE from 'three';

const CELL_COUNT = 25; // 5×5 grid
const _obj = new THREE.Object3D();

function GridCells({ grid }: { grid: number[][] }) {
  const meshRef = useRef<THREE.InstancedMesh>(null);

  useLayoutEffect(() => {
    const mesh = meshRef.current;
    if (!mesh) return;
    for (let i = 0; i < CELL_COUNT; i++) {
      const col = i % 5;
      const row = Math.floor(i / 5);
      _obj.position.set(col - 2, row - 2, 0.06);
      _obj.scale.setScalar(1);
      _obj.updateMatrix();
      mesh.setMatrixAt(i, _obj.matrix);
    }
    mesh.instanceMatrix.needsUpdate = true;
  }, []);

  return (
    <instancedMesh ref={meshRef} args={[TILE_GEO, undefined, CELL_COUNT]}>
      <meshStandardMaterial roughness={0.4} metalness={0.1} />
    </instancedMesh>
  );
}
```

---

## 2. GLTF/GLB Loading with drei/useGLTF

For games that need authored 3D models (characters, vehicles, environment props), GLTF/GLB is the standard format.

### Basic Loading with useGLTF

```typescript
import { useGLTF } from '@react-three/drei/native';
import { useFrame } from '@react-three/fiber/native';
import { useRef } from 'react';
import * as THREE from 'three';

function CharacterModel({ url, animIndex = 0 }: { url: string; animIndex?: number }) {
  const { scene, animations } = useGLTF(url);
  const mixer = useRef<THREE.AnimationMixer | null>(null);

  // Set up animation mixer
  if (!mixer.current && animations.length > 0) {
    mixer.current = new THREE.AnimationMixer(scene);
    const action = mixer.current.clipAction(animations[animIndex]);
    action.play();
  }

  useFrame((_, delta) => {
    mixer.current?.update(delta);
  });

  return <primitive object={scene} scale={0.01} />;
}
```

### Suspense-Based Preloading

```typescript
import { Suspense } from 'react';
import { useLoader } from '@react-three/fiber/native';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader';

// Preload all models before showing the game scene
function preloadModels(urls: string[]) {
  return Promise.all(
    urls.map(url => new Promise((resolve, reject) => {
      new GLTFLoader().load(url, resolve, undefined, reject);
    }))
  );
}

// Usage in app startup
async function warmUpAssets() {
  await preloadModels([
    require('./assets/models/character.glb'),
    require('./assets/models/enemy.glb'),
  ]);
}
```

### Draco Compression for Mobile

Draco-compressed GLTFs reduce file size by 50-90%. Use `useGLTF` with the Draco decoder path:

```typescript
import { useGLTF } from '@react-three/drei/native';

function OptimizedModel() {
  // drei handles Draco decoder setup
  const gltf = useGLTF('./model_draco.glb', '/draco-gltf/');
  return <primitive object={gltf.scene} />;
}
```

> **Note:** For Expo managed projects, Draco WASM decoders must be bundled or served from a CDN. Consider pre-decoded GLB files to avoid the WASM overhead entirely.

---

## 3. Texture Loading, Caching, and Disposal Patterns

### Procedural Textures (Zero Asset Dependencies)

Procedural textures generated via `DataTexture` eliminate network/asset loading entirely.

```typescript
import * as THREE from 'three';

function makeGlowTexture(size = 64): THREE.DataTexture {
  const data = new Uint8Array(size * size * 4);
  const center = (size - 1) / 2;

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const dx = (x - center) / center;
      const dy = (y - center) / center;
      const dist = Math.min(1, Math.sqrt(dx * dx + dy * dy));
      let alpha = 1 - dist;
      alpha = alpha * alpha * alpha; // Cubic falloff

      const i = (y * size + x) * 4;
      data[i] = 255;
      data[i + 1] = 255;
      data[i + 2] = 255;
      data[i + 3] = Math.round(alpha * 255);
    }
  }

  const tex = new THREE.DataTexture(data, size, size, THREE.RGBAFormat);
  tex.needsUpdate = true;
  return tex;
}

// Module-level singleton — created once, shared across all materials
const GLOW_TEX = makeGlowTexture(64);
```

### Texture Caching Strategy

```typescript
class TextureCache {
  private cache = new Map<string, THREE.Texture>();

  get(key: string): THREE.Texture | undefined {
    return this.cache.get(key);
  }

  set(key: string, texture: THREE.Texture): void {
    this.cache.set(key, texture);
  }

  dispose(): void {
    for (const tex of this.cache.values()) {
      tex.dispose();
    }
    this.cache.clear();
  }
}

// Singleton for the game session
export const textureCache = new TextureCache();
```

### Proper Disposal on Unmount

```typescript
import { useEffect } from 'react';
import * as THREE from 'three';

function useDisposableTexture(url: string) {
  const textureRef = useRef<THREE.Texture | null>(null);

  useEffect(() => {
    const loader = new THREE.TextureLoader();
    loader.load(url, (tex) => {
      textureRef.current = tex;
    });

    return () => {
      textureRef.current?.dispose();
      textureRef.current = null;
    };
  }, [url]);

  return textureRef;
}
```

> **Critical:** Always dispose textures, geometries, and materials when components unmount or when switching game scenes. Memory leaks on mobile cause OOM crashes.

---

## 4. Metro Config for Three.js (Preventing Dual-Bundle)

Three.js ships both ESM and CJS builds. Metro may resolve both, causing duplicate module instances and "renderer is not a function" errors.

### metro.config.js

```javascript
const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

// Prevent Three.js dual-bundle: force resolution to ESM only
config.resolver.resolveRequest = (context, moduleName, platform) => {
  // Redirect three to its ESM entry
  if (moduleName === 'three') {
    return {
      filePath: require.resolve('three/build/three.module.js'),
      type: 'sourceFile',
    };
  }

  // Default resolution for everything else
  return context.resolveRequest(context, moduleName, platform);
};

// Exclude heavy dev-only modules from production bundle
config.resolver.assetExts = config.resolver.assetExts.filter(
  (ext) => ext !== 'blender' && ext !== 'blend'
);

module.exports = config;
```

### Common Pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| `renderer is not a function` | Dual Three.js bundle | Add resolveRequest redirect |
| `THREE is not defined` | CJS/ESM mismatch | Ensure all imports use `import * as THREE` |
| Metro cache errors | Stale resolution cache | `npx expo start --clear` |
| `expo-gl` context null | GL not initialized before use | Add `onCreated` guard in Canvas |

---

## 5. EAS Build Optimization for Mobile Games

### eas.json Configuration

```json
{
  "cli": {
    "version": ">= 5.0.0"
  },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal",
      "ios": {
        "simulator": true
      }
    },
    "preview": {
      "distribution": "internal",
      "ios": {
        "simulator": false
      },
      "android": {
        "buildType": "apk"
      }
    },
    "production": {
      "ios": {
        "autoIncrement": true,
        "resourceClass": "m-medium"
      },
      "android": {
        "autoIncrement": true,
        "resourceClass": "m-medium"
      }
    }
  }
}
```

### app.json Build Properties

```json
{
  "expo": {
    "plugins": [
      ["expo-build-properties", {
        "ios": {
          "useFrameworks": "static"
        },
        "android": {
          "kotlinVersion": "2.3.0"
        }
      }]
    ]
  }
}
```

### Bundle Size Optimization Checklist

- [ ] Enable Hermes (default in Expo SDK 56+) — reduces JS startup by ~40%
- [ ] Use `expo-asset` for bundled assets with caching headers
- [ ] Tree-shake Three.js: import only what you use (`three/src/...`)
- [ ] Strip debug symbols in production builds
- [ ] Use `patch-package` to remove unused native code paths
- [ ] Prefer procedural geometry over GLB files where possible
- [ ] Compress textures to ETC2 (Android) / ASTC (iOS) at build time

### Prebuild Strategy

```bash
# Generate native projects with all plugins applied
npx expo prebuild --clean

# Build for specific platform
eas build --platform ios --profile production
eas build --platform android --profile production

# Submit to stores
eas submit --platform ios
eas submit --platform android
```

---

## 6. FPS Monitoring and Performance Logging

### In-Scene FPS Heartbeat

```typescript
import { useRef } from 'react';
import { useFrame } from '@react-three/fiber/native';

function FrameHeartbeat() {
  const frames = useRef(0);
  const lastReport = useRef(Date.now());
  const firstFrame = useRef(false);

  useFrame(() => {
    const now = Date.now();

    if (!firstFrame.current) {
      firstFrame.current = true;
      console.log('[PERF] First frame rendered — GL loop active');
    }

    frames.current++;

    if (now - lastReport.current >= 5000) {
      const fps = (frames.current / (now - lastReport.current)) * 1000;
      console.log(`[PERF] ~${fps.toFixed(1)} fps`);

      if (fps < 20) {
        console.warn('[PERF] Low FPS detected — investigate draw calls');
      }

      frames.current = 0;
      lastReport.current = now;
    }
  });

  return null;
}
```

### React Native Side FPS Overlay (Dev Only)

```typescript
import { useEffect, useRef, useState } from 'react';
import { Text, View } from 'react-native';

function FPSOverlay() {
  const [fps, setFps] = useState(60);
  const frames = useRef(0);
  const lastTime = useRef(Date.now());

  useEffect(() => {
    let raf: number;
    const tick = () => {
      frames.current++;
      const now = Date.now();
      if (now - lastTime.current >= 1000) {
        setFps(frames.current);
        frames.current = 0;
        lastTime.current = now;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  if (!__DEV__) return null;

  return (
    <View style={{
      position: 'absolute', top: 50, right: 10,
      backgroundColor: fps < 30 ? '#ff0000' : '#00cc00',
      paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6
    }}>
      <Text style={{ color: '#fff', fontWeight: '900', fontSize: 14 }}>
        {fps} FPS
      </Text>
    </View>
  );
}
```

### Performance Budget Targets

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Frame time | < 16.6ms (60fps) | > 33ms (30fps) |
| First frame | < 2s from app launch | > 5s |
| Memory usage | < 300MB | > 500MB |
| JS bundle size | < 15MB | > 25MB |
| Draw calls per frame | < 50 | > 100 |

---

## 7. Debug Logging Patterns

### Centralized Tag-Based Logger

A centralized logger with tag-based filtering prevents log spam and enables production-safe debugging.

```typescript
import { Platform } from 'react-native';

// Master kill-switch: set to false for production builds
export const LOG_ENABLED = __DEV__;

const t0 = Date.now();
const os = Platform.OS;

function stamp(tag: string): string {
  return `[Game][+${Date.now() - t0}ms][${os}][${tag}]`;
}

export function log(tag: string, ...args: unknown[]) {
  if (!LOG_ENABLED) return;
  console.log(stamp(tag), ...args);
}

export function warn(tag: string, ...args: unknown[]) {
  if (!LOG_ENABLED) return;
  console.warn(stamp(tag), ...args);
}

export function logError(tag: string, err: unknown, ...extra: unknown[]) {
  if (!LOG_ENABLED) return;
  const e = err as { message?: string; code?: string | number; stack?: string };
  console.error(
    stamp(tag),
    'ERROR:',
    e?.message ?? String(err),
    e?.code != null ? `code=${e.code}` : '',
    ...extra,
  );
  if (e?.stack) {
    console.error(stamp(tag), 'STACK:', e.stack.split('\n').slice(0, 8).join('\n'));
  }
}
```

### Global Error Handlers

```typescript
export function installGlobalErrorHandlers() {
  if (!LOG_ENABLED) return;

  const g = globalThis as any;

  // Log runtime environment
  log('GLOBAL', `Platform=${Platform.OS} Version=${String(Platform.Version)} __DEV__=${String(__DEV__)} hermes=${!!g.HermesInternal}`);

  // React Native fatal error handler
  const eu = g.ErrorUtils;
  if (eu?.getGlobalHandler && eu?.setGlobalHandler) {
    const prev = eu.getGlobalHandler();
    eu.setGlobalHandler((error: unknown, isFatal?: boolean) => {
      logError('UNCAUGHT', error, `isFatal=${String(isFatal)}`);
      prev?.(error, isFatal);
    });
  }

  // Unhandled promise rejections
  if (typeof g.addEventListener === 'function') {
    g.addEventListener('unhandledrejection', (ev: any) => {
      logError('UNHANDLED-REJECTION', ev?.reason ?? ev);
    });
  }
}
```

### Usage Pattern

```typescript
// At module load
log('SCENE', 'Scene.tsx loaded — generating geometries');

// At component mount
useEffect(() => {
  log('SCENE', `Scene mounted (theme=${theme})`);
  return () => log('SCENE', 'Scene unmounted');
}, []);

// At critical game events
log('STORE', `commitPlacement → score=${score} combo=${combo} flash=${flash.length}`);

// At GL context creation
log('GL', `renderer=${gl.getParameter(gl.RENDERER)} version=${gl.getParameter(gl.VERSION)}`);
log('GL', `drawingBuffer=${gl.drawingBufferWidth}x${gl.drawingBufferHeight}`);
```

---

## 8. Production Readiness Checklist

### Code Quality

- [ ] `LOG_ENABLED` set to `false` or gated behind `__DEV__`
- [ ] All `console.log` calls go through centralized logger
- [ ] Error boundaries wrap Canvas and critical UI components
- [ ] Global error handlers installed before app mount
- [ ] No hardcoded development URLs (API endpoints, ad test IDs)

### Performance

- [ ] FPS monitoring confirms stable 60fps on target devices
- [ ] No memory leaks: textures/geometries disposed on scene change
- [ ] InstancedMesh used for repeated objects (grid cells, particles)
- [ ] Shader pre-compilation on Canvas `onCreated`
- [ ] No unnecessary re-renders: Zustand selectors are granular
- [ ] `React.memo` on pure components, `useMemo` for expensive computations

### Native / Build

- [ ] `patch-package` patches applied and committed
- [ ] `expo prebuild` runs cleanly without conflicts
- [ ] EAS Build succeeds for both iOS and Android production profiles
- [ ] AdMob IDs are production (not test) IDs
- [ ] Privacy policy URL is live and accessible
- [ ] App icons and splash screen configured for all platforms

### Store Compliance

- [ ] ATT prompt implemented for iOS (if using ads)
- [ ] UMP consent flow implemented for EU users
- [ ] Privacy manifest (`PrivacyInfo.xcprivacy`) included for iOS
- [ ] Android adaptive icon with all layers configured
- [ ] Orientation lock set (portrait/landscape as appropriate)

### Error Recovery

- [ ] GL context failure shows user-friendly message (not white screen)
- [ ] Ad load failure gracefully falls back to no-ads experience
- [ ] Audio initialization failure doesn't crash the game
- [ ] Persistence read/write failure handled with defaults

---

## 9. patch-package for Native Module Fixes

When native modules have bugs that haven't been merged upstream, `patch-package` lets you apply and persist fixes.

### Setup

```bash
npm install patch-package --save-dev
```

Add to `package.json` scripts:

```json
{
  "scripts": {
    "postinstall": "patch-package"
  }
}
```

### Creating a Patch

```bash
# 1. Edit the file in node_modules
# e.g., node_modules/expo-gl/ios/GLView.swift

# 2. Generate the patch
npx patch-package expo-gl

# 3. Commit the patch file
git add patches/expo-gl+56.0.5.patch
git commit -m "fix: expo-gl simulator rendering freeze"
```

### Example: iOS Simulator GL Fix

A common issue: the iOS simulator's software renderer drops frames between presents, causing a frozen first frame. The fix enables retained backing on simulator only:

```diff
diff --git a/node_modules/expo-gl/ios/GLView.swift b/node_modules/expo-gl/ios/GLView.swift
--- a/node_modules/expo-gl/ios/GLView.swift
+++ b/node_modules/expo-gl/ios/GLView.swift
@@ -49,8 +49,16 @@
     if let eaglLayer = layer as? CAEAGLLayer {
       eaglLayer.isOpaque = false
+      #if targetEnvironment(simulator)
+      let retainedBacking = true
+      #else
+      let retainedBacking = false
+      #endif
       eaglLayer.drawableProperties = [
-        kEAGLDrawablePropertyRetainedBacking: false,
+        kEAGLDrawablePropertyRetainedBacking: retainedBacking,
         kEAGLDrawablePropertyColorFormat: kEAGLColorFormatRGBA8
       ]
     }
```

### Best Practices

- Name patches descriptively: `expo-gl+56.0.5.patch`
- Add comments in the patch explaining WHY it's needed
- Check if the fix has been merged upstream before each library upgrade
- Re-run `patch-package` after every `npm install` (handled by `postinstall`)
- Keep patches minimal — only change what's broken

---

## 10. Testing Strategies for RN+Three.js Games

### Unit Testing Game Logic (No Three.js)

Game logic (state machines, scoring, collision) should be tested independently of rendering.

```typescript
// __tests__/store.test.ts
import { create } from 'zustand';

describe('Game Store', () => {
  it('should reset to initial state', () => {
    const { reset, getState } = useGame;
    reset();
    expect(getState().score).toBe(0);
    expect(getState().combo).toBe(0);
    expect(getState().gameOver).toBe(false);
  });

  it('should increment combo on consecutive clears', () => {
    // Test the clearing logic without rendering
    const result = faceClears(createTestGrid([
      [1, 1, 1, 1, 1],
      [0, 0, 0, 0, 0],
      [0, 0, 0, 0, 0],
      [0, 0, 0, 0, 0],
      [0, 0, 0, 0, 0],
    ]));
    expect(result.lines).toBe(1);
    expect(result.cells.length).toBe(5);
  });

  it('should detect game over when no piece fits', () => {
    const fullGrid = createFullGrid();
    expect(isGameOver(fullGrid, [largePiece])).toBe(true);
  });
});
```

### Snapshot Testing Components

```typescript
// __tests__/App.snapshot.test.tsx
import renderer from 'react-test-renderer';
import App from '../App';

// Mock Three.js Canvas to avoid GL context
jest.mock('@react-three/fiber/native', () => ({
  Canvas: ({ children }: any) => <>{children}</>,
  useFrame: () => {},
  useThree: () => ({ camera: {}, size: { width: 400, height: 800 } }),
}));

it('renders menu screen initially', () => {
  const tree = renderer.create(<App />);
  expect(tree.root.findAllByProps({ testID: 'menu-screen' })).toHaveLength(1);
});
```

### Integration Testing with Mock GL

```typescript
// __tests__/scene.integration.test.tsx
jest.mock('../src/three/glowTexture', () => ({
  makeGlowTexture: () => ({ needsUpdate: true, dispose: jest.fn() }),
  makeRingTexture: () => ({ needsUpdate: true, dispose: jest.fn() }),
}));

// Test that scene components initialize correctly
describe('Scene initialization', () => {
  it('creates face tiles for all 4 faces', () => {
    // Verify InstancedMesh setup without actual GL rendering
    const { FACE_COUNT } = require('../src/game/constants');
    expect(FACE_COUNT).toBe(4);
  });
});
```

### E2E Testing with Detox/Maestro

```yaml
# .maestro/game-flow.yaml
appId: com.keremerol.blocube
---
- launchApp
- assertVisible: "CLASSIC"
- tapOn: "CLASSIC"
- assertVisible: "⚙︎"  # Settings gear appears in game screen
- tapOn: "⚙︎"
- assertVisible: "Settings"
- tapOn: "Back"
- assertVisible: "CLASSIC"  # Back to menu
```

---

## 11. Genre Patterns

### Puzzle: Piece Procedural Generation

Puzzle games (Block Blast, Tetris variants) generate piece shapes procedurally from cell arrays.

```typescript
// Piece definitions as cell coordinates [col, row]
type Cell = [number, number];
type PieceDef = { cells: Cell[]; colorIndex: number; id: number };

const SHAPES: Cell[][] = [
  [[0, 0]],                           // Single
  [[0, 0], [1, 0]],                   // Domino
  [[0, 0], [1, 0], [2, 0]],          // Line-3
  [[0, 0], [1, 0], [0, 1], [1, 1]], // Square
  [[0, 0], [1, 0], [2, 0], [1, 1]], // T-shape
  // ... more shapes
];

function randomPiece(): PieceDef {
  const cells = SHAPES[Math.floor(Math.random() * SHAPES.length)];
  return {
    cells,
    colorIndex: 1 + Math.floor(Math.random() * 7),
    id: Date.now() + Math.random(),
  };
}

// Generate a tray of N random pieces
function randomTray(count: number): (PieceDef | null)[] {
  return Array.from({ length: count }, () => randomPiece());
}

// Easy pieces for revive/power-up scenarios (single cells and dominoes)
function easyTray(count: number): (PieceDef | null)[] {
  const easyShapes = SHAPES.filter(s => s.length <= 2);
  return Array.from({ length: count }, () => ({
    cells: easyShapes[Math.floor(Math.random() * easyShapes.length)],
    colorIndex: 1 + Math.floor(Math.random() * 7),
    id: Date.now() + Math.random(),
  }));
}
```

### Runner: Obstacle Creation

Endless runners generate obstacles in segments with difficulty curves.

```typescript
type ObstacleDef = {
  type: 'barrier' | 'gap' | 'moving' | 'collectible';
  lane: number;
  zOffset: number;
  width: number;
  height: number;
  speed: number;
};

class ObstacleGenerator {
  private difficulty = 0;
  private segmentLength = 20;

  generateSegment(distanceTraveled: number): ObstacleDef[] {
    this.difficulty = Math.min(1, distanceTraveled / 5000);
    const obstacles: ObstacleDef[] = [];
    const count = 2 + Math.floor(this.difficulty * 4);

    for (let i = 0; i < count; i++) {
      const z = this.segmentLength * (i / count);
      const lane = Math.floor(Math.random() * 3);
      const type = this.pickType();

      obstacles.push({
        type,
        lane,
        zOffset: z,
        width: 1 + Math.random() * this.difficulty,
        height: type === 'barrier' ? 1.5 : 0.5,
        speed: type === 'moving' ? 2 + this.difficulty * 3 : 0,
      });
    }
    return obstacles;
  }

  private pickType(): ObstacleDef['type'] {
    const r = Math.random();
    if (r < 0.4) return 'barrier';
    if (r < 0.6) return 'gap';
    if (r < 0.8) return 'collectible';
    return 'moving';
  }
}
```

### Idle: Character Loading

Idle/tycoon games load character models with animation states and swap them based on progression.

```typescript
type CharacterConfig = {
  modelUrl: string;
  idleAnim: number;
  workAnim: number;
  scale: number;
  unlockLevel: number;
};

const CHARACTERS: CharacterConfig[] = [
  { modelUrl: './models/worker_basic.glb', idleAnim: 0, workAnim: 1, scale: 0.01, unlockLevel: 1 },
  { modelUrl: './models/worker_advanced.glb', idleAnim: 0, workAnim: 2, scale: 0.012, unlockLevel: 5 },
  { modelUrl: './models/worker_elite.glb', idleAnim: 0, workAnim: 3, scale: 0.011, unlockLevel: 15 },
];

function useCharacter(level: number) {
  const config = useMemo(
    () => CHARACTERS.filter(c => c.unlockLevel <= level).pop()!,
    [level]
  );
  const gltf = useGLTF(config.modelUrl);
  return { scene: gltf.scene, config };
}
```

### Tower Defense: Enemy Spawning

Tower defense games spawn enemies in waves with increasing complexity.

```typescript
type EnemyWave = {
  enemies: { type: string; count: number; interval: number; hp: number; speed: number }[];
  reward: number;
};

function generateWave(waveNumber: number): EnemyWave {
  const baseCount = 5 + waveNumber * 2;
  const types = ['grunt', 'fast', 'tank'];
  const available = types.slice(0, Math.min(types.length, 1 + Math.floor(waveNumber / 3)));

  return {
    enemies: available.map(type => ({
      type,
      count: Math.floor(baseCount / available.length),
      interval: Math.max(0.3, 1.5 - waveNumber * 0.05),
      hp: getBaseHP(type) * (1 + waveNumber * 0.15),
      speed: getBaseSpeed(type) * (1 + waveNumber * 0.02),
    })),
    reward: 50 + waveNumber * 10,
  };
}

// Procedural enemy mesh (no GLB needed)
function createEnemyMesh(type: string): THREE.BufferGeometry {
  switch (type) {
    case 'grunt': return new THREE.SphereGeometry(0.3, 8, 6);
    case 'fast':  return new THREE.ConeGeometry(0.2, 0.6, 6);
    case 'tank':  return new THREE.BoxGeometry(0.5, 0.5, 0.5);
    default:      return new THREE.SphereGeometry(0.3, 8, 6);
  }
}
```

---

## Example: Blocube Implementation

> Blocube is a 3D puzzle game built with Expo SDK 56, React Three Fiber, and Three.js. It demonstrates several patterns from this document in production:
>
> **Procedural Geometry:** All game geometry is procedural — `roundedTile()` uses `ExtrudeGeometry` with bevel for premium-looking blocks. No GLB files in the entire project.
>
> **InstancedMesh:** Each cube face uses a single `InstancedMesh` for 25 cells (1 draw call per face instead of 25). Fragment effects use 2 InstancedMesh for 132 particles total.
>
> **Procedural Textures:** `makeGlowTexture()` and `makeRingTexture()` generate `DataTexture` at module load — zero image assets for VFX.
>
> **Debug Logging:** `src/debug/log.ts` implements the tag-based logger pattern with `LOG_ENABLED` kill-switch, global error handlers, and Hermes promise rejection tracking.
>
> **patch-package:** `patches/expo-gl+56.0.5.patch` fixes iOS simulator rendering freeze by conditionally enabling retained backing and routing `presentRenderbuffer` through the main thread.
>
> **State Management:** Zustand store (`src/game/store.ts`) manages all game state with granular selectors to prevent unnecessary re-renders.

---

## 12. Sources

- [Three.js ExtrudeGeometry Documentation](https://threejs.org/docs/#api/en/geometries/ExtrudeGeometry)
- [Three.js LatheGeometry Documentation](https://threejs.org/docs/#api/en/geometries/LatheGeometry)
- [Three.js BufferGeometry Documentation](https://threejs.org/docs/#api/en/core/BufferGeometry)
- [Three.js InstancedMesh Documentation](https://threejs.org/docs/#api/en/objects/InstancedMesh)
- [Three.js DataTexture Documentation](https://threejs.org/docs/#api/en/textures/DataTexture)
- [React Three Fiber Native (Expo)](https://docs.pmnd.rs/react-three-fiber/getting-started/installation#expo)
- [drei useGLTF](https://github.com/pmndrs/drei#usegltf)
- [Expo GL Library](https://docs.expo.dev/versions/latest/sdk/gl-view/)
- [EAS Build Configuration](https://docs.expo.dev/build-reference/eas-json/)
- [Metro Bundler Configuration](https://metrobundler.dev/docs/configuration/)
- [patch-package](https://github.com/ds300/patch-package)
- [Zustand Documentation](https://docs.pmnd.rs/zustand/getting-started/introduction)
- [React Native Performance](https://reactnative.dev/docs/performance)
- [Expo Build Properties Plugin](https://docs.expo.dev/versions/latest/sdk/build-properties/)
- [Draco Compression for GLTF](https://google.github.io/draco/)
- [Three.js Memory Management](https://threejs.org/docs/#manual/en/introduction/How-to-dispose-of-objects)
