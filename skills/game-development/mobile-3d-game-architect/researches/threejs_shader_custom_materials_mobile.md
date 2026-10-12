# Three.js Shader & Custom Materials for Mobile Games

> **General-purpose reference** for writing GLSL shaders and custom materials in React Native + Three.js mobile games.
> Covers ShaderMaterial patterns, procedural textures, mobile GPU compatibility, and genre-specific FX.

---

## Table of Contents

1. [ShaderMaterial Fundamentals](#1-shadermaterial-fundamentals)
2. [Vertex Shader Patterns](#2-vertex-shader-patterns)
3. [Fragment Shader Patterns](#3-fragment-shader-patterns)
4. [Additive Blending for FX Effects](#4-additive-blending-for-fx-effects)
5. [Procedural Texture Generation with DataTexture](#5-procedural-texture-generation-with-datatexture)
6. [Theme/Skin System via Material Property Switching](#6-themeskin-system-via-material-property-switching)
7. [Mobile GPU Compatibility](#7-mobile-gpu-compatibility)
8. [GLSL ES 3.0 vs 1.0 Compatibility](#8-glsl-es-30-vs-10-compatibility)
9. [Post-Processing with EffectComposer on Mobile](#9-post-processing-with-effectcomposer-on-mobile)
10. [drei Shader Helpers](#10-drei-shader-helpers)
11. [Shader Compilation Caching](#11-shader-compilation-caching)
12. [Genre Patterns](#12-genre-patterns)
13. [Sources](#13-sources)

---

## 1. ShaderMaterial Fundamentals

Three.js `ShaderMaterial` gives you full control over the GPU pipeline via custom GLSL vertex and fragment shaders.

### Basic Structure

```typescript
import * as THREE from 'three';

const material = new THREE.ShaderMaterial({
  uniforms: {
    uTime: { value: 0 },
    uColor: { value: new THREE.Color('#ff0000') },
    uTexture: { value: null },
  },
  vertexShader: /* glsl */`
    uniform float uTime;
    varying vec2 vUv;
    
    void main() {
      vUv = uv;
      vec3 pos = position;
      pos.y += sin(pos.x * 2.0 + uTime) * 0.1;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
    }
  `,
  fragmentShader: /* glsl */`
    uniform vec3 uColor;
    uniform float uTime;
    varying vec2 vUv;
    
    void main() {
      float pulse = 0.5 + 0.5 * sin(uTime * 2.0);
      gl_FragColor = vec4(uColor * pulse, 1.0);
    }
  `,
});
```

### Uniform Types

| GLSL Type | JavaScript Value | Use Case |
|-----------|------------------|----------|
| `float` | `number` | Time, intensity, scale |
| `vec2` | `THREE.Vector2` | UV offset, resolution |
| `vec3` | `THREE.Color` / `THREE.Vector3` | Color, position |
| `vec4` | `THREE.Vector4` | Quaternion, rect |
| `mat3` | `THREE.Matrix3` | Color transform |
| `mat4` | `THREE.Matrix4` | Custom transform |
| `sampler2D` | `THREE.Texture` | Diffuse, normal map |
| `int` | `number` | Index, count |

### Updating Uniforms in useFrame

```tsx
function AnimatedMesh() {
  const matRef = useRef<THREE.ShaderMaterial>(null);

  useFrame((state) => {
    if (matRef.current) {
      matRef.current.uniforms.uTime.value = state.clock.elapsedTime;
    }
  });

  return (
    <mesh>
      <boxGeometry args={[1, 1, 1]} />
      <shaderMaterial ref={matRef} {...shaderConfig} />
    </mesh>
  );
}
```

### Built-in Variables

Three.js automatically provides these to your shaders:

```glsl
// Vertex shader
attribute vec3 position;    // Local space position
attribute vec3 normal;      // Local space normal
attribute vec2 uv;          // Texture coordinates
uniform mat4 modelMatrix;   // Object -> World
uniform mat4 modelViewMatrix; // Object -> View
uniform mat4 projectionMatrix; // View -> Clip
uniform mat3 normalMatrix;  // Normal transform

// Fragment shader
// (all vertex outputs available via varying)
```

---

## 2. Vertex Shader Patterns

### Displacement (Surface Deformation)

```glsl
uniform float uTime;
uniform float uAmplitude;
uniform float uFrequency;

varying vec3 vNormal;
varying vec3 vPosition;

void main() {
  vNormal = normal;
  vPosition = position;
  
  // Sinusoidal displacement along normal
  float displacement = sin(position.x * uFrequency + uTime) 
                     * sin(position.y * uFrequency + uTime)
                     * uAmplitude;
  
  vec3 newPosition = position + normal * displacement;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(newPosition, 1.0);
}
```

### Animation (Pulsing Scale)

```glsl
uniform float uTime;
uniform float uPulseSpeed;
uniform float uPulseAmount;

varying vec2 vUv;

void main() {
  vUv = uv;
  
  // Pulsing scale effect
  float pulse = 1.0 + sin(uTime * uPulseSpeed) * uPulseAmount;
  vec3 scaled = position * pulse;
  
  gl_Position = projectionMatrix * modelViewMatrix * vec4(scaled, 1.0);
}
```

### Procedural Deformation (Noise-based)

```glsl
uniform float uTime;
uniform float uNoiseScale;
uniform float uNoiseStrength;

varying vec3 vNormal;
varying float vNoise;

// Simplex noise function (3D)
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

float snoise(vec3 v) {
  // ... simplex noise implementation
  // (full implementation omitted for brevity)
  return 0.0; // placeholder
}

void main() {
  vNormal = normal;
  
  float noise = snoise(position * uNoiseScale + uTime * 0.5);
  vNoise = noise;
  
  vec3 displaced = position + normal * noise * uNoiseStrength;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(displaced, 1.0);
}
```

### Wave Propagation (Ripple from Point)

```glsl
uniform float uTime;
uniform vec3 uOrigin;       // World space origin of ripple
uniform float uSpeed;
uniform float uWavelength;

varying vec3 vWorldPos;

void main() {
  vec4 worldPos = modelMatrix * vec4(position, 1.0);
  vWorldPos = worldPos.xyz;
  
  float dist = distance(worldPos.xyz, uOrigin);
  float wave = sin(dist / uWavelength * 6.2832 - uTime * uSpeed);
  float falloff = 1.0 / (1.0 + dist * 0.5);
  
  vec3 displaced = position + normal * wave * falloff * 0.2;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(displaced, 1.0);
}
```

---

## 3. Fragment Shader Patterns

### Glow Effect (Radial Gradient)

```glsl
uniform vec3 uGlowColor;
uniform float uGlowIntensity;
uniform float uGlowRadius;

varying vec2 vUv;

void main() {
  // Distance from center (0 at center, 1 at edge)
  float dist = length(vUv - 0.5) * 2.0;
  
  // Smooth falloff
  float glow = 1.0 - smoothstep(0.0, uGlowRadius, dist);
  glow = pow(glow, 2.0); // Sharper falloff
  
  vec3 color = uGlowColor * glow * uGlowIntensity;
  gl_FragColor = vec4(color, glow);
}
```

### Bloom (Screen-space Glow)

```glsl
uniform sampler2D uSceneTexture;
uniform vec2 uResolution;
uniform float uBloomStrength;
uniform float uBloomRadius;

varying vec2 vUv;

void main() {
  vec4 color = texture2D(uSceneTexture, vUv);
  
  // Multi-tap blur for bloom
  vec4 bloom = vec4(0.0);
  float total = 0.0;
  
  for (float x = -4.0; x <= 4.0; x += 1.0) {
    for (float y = -4.0; y <= 4.0; y += 1.0) {
      vec2 offset = vec2(x, y) / uResolution * uBloomRadius;
      vec4 sample = texture2D(uSceneTexture, vUv + offset);
      float weight = 1.0 - length(vec2(x, y)) / 5.66;
      bloom += sample * weight;
      total += weight;
    }
  }
  bloom /= total;
  
  // Add bloom to original
  gl_FragColor = color + bloom * uBloomStrength;
}
```

### Shockwave (Expanding Ring)

```glsl
uniform float uTime;
uniform float uShockSpeed;
uniform float uShockWidth;
uniform vec2 uCenter;

varying vec2 vUv;

void main() {
  float dist = length(vUv - uCenter);
  float shockRadius = uTime * uShockSpeed;
  
  // Ring at shockRadius with width uShockWidth
  float ring = smoothstep(shockRadius - uShockWidth, shockRadius, dist)
             - smoothstep(shockRadius, shockRadius + uShockWidth, dist);
  
  // Fade out as it expands
  float fade = 1.0 - smoothstep(0.0, 1.0, uTime);
  
  vec3 color = vec3(1.0) * ring * fade;
  gl_FragColor = vec4(color, ring * fade);
}
```

### Dissolve (Procedural Mask)

```glsl
uniform float uDissolveAmount;  // 0 = solid, 1 = fully dissolved
uniform float uEdgeWidth;
uniform vec3 uEdgeColor;

varying vec2 vUv;
varying vec3 vPosition;

// Hash function for procedural noise
float hash(vec2 p) {
  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  
  float a = hash(i);
  float b = hash(i + vec2(1.0, 0.0));
  float c = hash(i + vec2(0.0, 1.0));
  float d = hash(i + vec2(1.0, 1.0));
  
  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

void main() {
  // Procedural noise pattern
  float n = noise(vPosition.xy * 5.0);
  
  // Dissolve mask
  float mask = smoothstep(uDissolveAmount - uEdgeWidth, uDissolveAmount, n);
  
  // Edge glow
  float edge = smoothstep(uDissolveAmount - uEdgeWidth * 2.0, uDissolveAmount - uEdgeWidth, n)
             - smoothstep(uDissolveAmount - uEdgeWidth, uDissolveAmount, n);
  
  vec3 baseColor = vec3(1.0, 0.5, 0.2);
  vec3 color = mix(baseColor, uEdgeColor, edge);
  
  gl_FragColor = vec4(color, mask);
}
```

---

## 4. Additive Blending for FX Effects

Additive blending is essential for particle effects, glows, and energy visuals. It adds the fragment color to the framebuffer instead of replacing it.

### Setup

```typescript
const fxMaterial = new THREE.ShaderMaterial({
  uniforms: {
    uColor: { value: new THREE.Color('#ffaa00') },
    uIntensity: { value: 1.0 },
  },
  vertexShader: /* glsl */`
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: /* glsl */`
    uniform vec3 uColor;
    uniform float uIntensity;
    varying vec2 vUv;
    
    void main() {
      float dist = length(vUv - 0.5) * 2.0;
      float glow = 1.0 - smoothstep(0.0, 1.0, dist);
      gl_FragColor = vec4(uColor * glow * uIntensity, glow);
    }
  `,
  transparent: true,
  blending: THREE.AdditiveBlending,
  depthWrite: false,  // Critical for correct additive rendering
});
```

### Key Properties

| Property | Value | Why |
|----------|-------|-----|
| `transparent` | `true` | Enables alpha blending |
| `blending` | `THREE.AdditiveBlending` | Add to framebuffer |
| `depthWrite` | `false` | Prevents z-fighting between particles |
| `depthTest` | `true` (default) | Still respects depth buffer |

### When to Use Additive Blending

- Particle effects (sparks, smoke, fire)
- Glow effects (bloom, lens flare)
- Energy shields / force fields
- Shockwaves / ripples
- Light beams / god rays

### When NOT to Use

- Opaque surfaces (use `NormalBlending`)
- UI elements (use `NormalBlending`)
- Text (use `NormalBlending`)

---

## 5. Procedural Texture Generation with DataTexture

Procedural textures eliminate asset loading, reduce bundle size, and enable runtime customization.

### Radial Glow Texture

```typescript
export function makeGlowTexture(size = 64): THREE.DataTexture {
  const data = new Uint8Array(size * size * 4);
  const c = (size - 1) / 2;
  
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const dx = (x - c) / c;
      const dy = (y - c) / c;
      const d = Math.min(1, Math.sqrt(dx * dx + dy * dy));
      
      let a = 1 - d;
      a = a * a * a; // Cubic falloff
      
      const i = (y * size + x) * 4;
      data[i] = 255;     // R
      data[i + 1] = 255; // G
      data[i + 2] = 255; // B
      data[i + 3] = Math.round(a * 255); // A
    }
  }
  
  const tex = new THREE.DataTexture(data, size, size, THREE.RGBAFormat);
  tex.needsUpdate = true;
  return tex;
}
```

### Ring Texture (Shockwave)

```typescript
export function makeRingTexture(size = 128): THREE.DataTexture {
  const data = new Uint8Array(size * size * 4);
  const c = (size - 1) / 2;
  
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const dx = (x - c) / c;
      const dy = (y - c) / c;
      const d = Math.min(1, Math.sqrt(dx * dx + dy * dy));
      
      // Ring at radius 0.8 with width 0.2
      const a = Math.max(0, 1 - Math.abs(d - 0.8) / 0.2);
      
      const i = (y * size + x) * 4;
      data[i] = 255;
      data[i + 1] = 255;
      data[i + 2] = 255;
      data[i + 3] = Math.round(a * a * 255);
    }
  }
  
  const tex = new THREE.DataTexture(data, size, size, THREE.RGBAFormat);
  tex.needsUpdate = true;
  return tex;
}
```

### Noise Texture

```typescript
function makeNoiseTexture(size = 256): THREE.DataTexture {
  const data = new Uint8Array(size * size * 4);
  
  for (let i = 0; i < size * size; i++) {
    const v = Math.floor(Math.random() * 256);
    data[i * 4] = v;
    data[i * 4 + 1] = v;
    data[i * 4 + 2] = v;
    data[i * 4 + 3] = 255;
  }
  
  const tex = new THREE.DataTexture(data, size, size, THREE.RGBAFormat);
  tex.needsUpdate = true;
  return tex;
}
```

### Gradient Texture

```typescript
function makeGradientTexture(
  size = 256,
  color1: [number, number, number],
  color2: [number, number, number],
): THREE.DataTexture {
  const data = new Uint8Array(size * size * 4);
  
  for (let y = 0; y < size; y++) {
    const t = y / (size - 1);
    const r = Math.round(color1[0] + (color2[0] - color1[0]) * t);
    const g = Math.round(color1[1] + (color2[1] - color1[1]) * t);
    const b = Math.round(color1[2] + (color2[2] - color1[2]) * t);
    
    for (let x = 0; x < size; x++) {
      const i = (y * size + x) * 4;
      data[i] = r;
      data[i + 1] = g;
      data[i + 2] = b;
      data[i + 3] = 255;
    }
  }
  
  const tex = new THREE.DataTexture(data, size, size, THREE.RGBAFormat);
  tex.needsUpdate = true;
  return tex;
}
```

### Memory Considerations

| Texture Size | Memory (RGBA) | Use Case |
|--------------|---------------|----------|
| 64x64 | 16 KB | Small glows, sparks |
| 128x128 | 64 KB | Rings, medium effects |
| 256x256 | 256 KB | Noise, gradients |
| 512x512 | 1 MB | Detailed procedural |

**Rule**: Keep procedural textures ≤128x128 for mobile. Use power-of-two sizes for mipmapping.

> **Example: Blocube Implementation**
> Blocube generates all textures procedurally via `DataTexture` — no image assets. `makeGlowTexture(64)` creates a radial gradient for spark particles. `makeRingTexture(128)` creates a ring shape for shockwave effects. Both are created once at module load and reused throughout the game. This eliminates async texture loading and keeps the bundle small.

---

## 6. Theme/Skin System via Material Property Switching

Themes can be implemented by swapping material properties at runtime without recreating geometry.

### Theme Definition

```typescript
type Theme = {
  name: string;
  bg: string;              // Scene background color
  palette: string[];       // Block colors (index 0 unused, 1-7 active)
  roughness: number;       // Material roughness
  metalness: number;       // Material metalness
  backdrop: string;        // Background decoration type
  pieceRadius: number;     // UI piece corner radius
  pieceGloss: number;      // UI piece glossiness
  pieceGlow: number;       // UI piece glow intensity
};

const THEMES: Theme[] = [
  {
    name: 'CLASSIC',
    bg: '#3b56d6',
    palette: ['', '#ff6b8a', '#ffd76b', '#6bd6ff', '#c58aff', '#7dedb6', '#ffb36b', '#8a9bff'],
    roughness: 0.42,
    metalness: 0.08,
    backdrop: 'glow',
    pieceRadius: 0.28,
    pieceGloss: 0.45,
    pieceGlow: 0.7,
  },
  {
    name: 'NEON',
    bg: '#05060a',
    palette: ['', '#ff2e63', '#faff00', '#00f5ff', '#b537f2', '#39ff88', '#ff9e00', '#3f7bff'],
    roughness: 0.25,
    metalness: 0.1,
    backdrop: 'neon',
    pieceRadius: 0.24,
    pieceGloss: 0.15,
    pieceGlow: 1.0,
  },
  // ... more themes
];
```

### Runtime Material Switching

```typescript
// Pre-compute theme objects at module load
const THEME_OBJS = THEMES.map((theme) => ({
  bg: new THREE.Color(theme.bg),
  colors: theme.palette.map((c) => c ? new THREE.Color(c) : new THREE.Color(0)),
  roughness: theme.roughness,
  metalness: theme.metalness,
}));

// Apply theme to InstancedMesh
function applyTheme(mesh: THREE.InstancedMesh, themeIndex: number) {
  const theme = THEME_OBJS[themeIndex];
  const mat = mesh.material as THREE.MeshStandardMaterial;
  mat.roughness = theme.roughness;
  mat.metalness = theme.metalness;
  
  // Update instance colors
  for (let i = 0; i < count; i++) {
    const colorIndex = getColorIndex(i);
    tmpColor.copy(theme.colors[colorIndex]);
    mesh.setColorAt(i, tmpColor);
  }
  mesh.instanceColor.needsUpdate = true;
}
```

### Theme Transition Effect

```typescript
// Trigger theme change with visual feedback
function transitionTheme(newTheme: number) {
  // White flash
  useGame.setState({ flash: createFlashCells() });
  
  // Kick cube rotation
  cubeRef.yawVel += 2.0;
  
  // Show theme name badge
  showThemeBadge(THEMES[newTheme].name);
  
  // Apply new theme
  useGame.setState({ theme: newTheme });
}
```

> **Example: Blocube Implementation**
> Blocube has 5 themes (CLASSIC, CANDY, NEON, WOOD, GALAXY) that transition every 5000 points. Each theme defines background color, 7-color block palette, material properties (roughness/metalness), backdrop type, and 2D piece appearance. Theme objects are pre-computed at module load (`THEME_OBJS`) with `THREE.Color` instances. The cube geometry stays constant — only material properties and instance colors change.

---

## 7. Mobile GPU Compatibility

### Mobile GPU Architectures

| Vendor | Architecture | Devices | Characteristics |
|--------|--------------|---------|-----------------|
| **Apple** | PowerVR / Apple GPU | iPhone, iPad | High performance, good GLSL support |
| **ARM** | Mali | Samsung, Xiaomi, Huawei | TBDR architecture, conservative |
| **Qualcomm** | Adreno | Pixel, OnePlus, Samsung | Good performance, some quirks |

### Tile-Based Deferred Rendering (TBDR)

Most mobile GPUs use TBDR, which differs from desktop immediate-mode rendering:

- **Tile-based**: Screen divided into tiles, processed independently
- **Deferred**: Geometry processed first, then shading
- **Benefit**: Reduces memory bandwidth (critical for mobile)
- **Implication**: Avoid excessive overdraw; sort transparent objects back-to-front

### Compatibility Guidelines

1. **Use GLSL ES 1.0** (OpenGL ES 2.0) for maximum compatibility
2. **Avoid highp in fragment shaders** unless necessary (use mediump)
3. **Limit texture lookups** (max 8-16 per fragment on mobile)
4. **Avoid dynamic loops** (use `#define` for loop counts)
5. **Prefer `pow(x, 2.0)` over `x * x`** for readability (compiler optimizes)
6. **Test on low-end devices** (Mali-400, Adreno 306)

### Precision Qualifiers

```glsl
// Vertex shader — use highp
precision highp float;

// Fragment shader — use mediump for performance
precision mediump float;

// Or specify per-variable
highp vec4 criticalCalculation;
mediump vec3 color;
lowp float alpha;
```

### Feature Detection

```typescript
function checkGLSupport(gl: WebGLRenderingContext) {
  const maxTextureSize = gl.getParameter(gl.MAX_TEXTURE_SIZE);
  const maxVertexAttribs = gl.getParameter(gl.MAX_VERTEX_ATTRIBS);
  const maxFragmentUniforms = gl.getParameter(gl.MAX_FRAGMENT_UNIFORM_VECTORS);
  
  console.log('Max texture size:', maxTextureSize);
  console.log('Max vertex attribs:', maxVertexAttribs);
  console.log('Max fragment uniforms:', maxFragmentUniforms);
  
  // WebGL2 / GLSL ES 3.0 support
  const isWebGL2 = gl instanceof WebGL2RenderingContext;
  console.log('WebGL2 supported:', isWebGL2);
}
```

---

## 8. GLSL ES 3.0 vs 1.0 Compatibility

### Key Differences

| Feature | GLSL ES 1.0 | GLSL ES 3.0 |
|---------|-------------|-------------|
| **Version directive** | `#version 100` | `#version 300 es` |
| **Texture sampling** | `texture2D()` | `texture()` |
| **Variable declaration** | `attribute` / `varying` | `in` / `out` |
| **Fragment output** | `gl_FragColor` | Custom `out vec4` |
| **Integer textures** | Not supported | Supported |
| **Multiple render targets** | Limited | Full support |
| **3D textures** | Not supported | Supported |

### GLSL ES 1.0 (Maximum Compatibility)

```glsl
#version 100
precision mediump float;

uniform sampler2D uTexture;
varying vec2 vUv;

void main() {
  vec4 color = texture2D(uTexture, vUv);
  gl_FragColor = color;
}
```

### GLSL ES 3.0 (Modern)

```glsl
#version 300 es
precision mediump float;

uniform sampler2D uTexture;
in vec2 vUv;
out vec4 outColor;

void main() {
  outColor = texture(uTexture, vUv);
}
```

### Three.js Handling

Three.js automatically handles version differences:

- `WebGL1Renderer` → GLSL ES 1.0
- `WebGLRenderer` (default) → GLSL ES 3.0 if available, else 1.0

**For React Native (expo-gl)**: Uses WebGL2 by default on modern devices, falls back to WebGL1.

### Migration Pattern

```glsl
// Compatible with both versions
#ifdef GL_ES
  #ifdef GL_FRAGMENT_PRECISION_HIGH
    precision highp float;
  #else
    precision mediump float;
  #endif
#endif

// Three.js handles this automatically in ShaderMaterial
```

---

## 9. Post-Processing with EffectComposer on Mobile

### EffectComposer Setup

```typescript
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass';
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass';

const composer = new EffectComposer(renderer);

// Render scene
const renderPass = new RenderPass(scene, camera);
composer.addPass(renderPass);

// Add bloom
const bloomPass = new UnrealBloomPass(
  new THREE.Vector2(width, height),
  1.5,    // strength
  0.4,    // radius
  0.85    // threshold
);
composer.addPass(bloomPass);

// Render in useFrame
useFrame(() => {
  composer.render();
}, 1);
```

### Mobile Considerations

**Performance impact**: Post-processing adds a full-screen pass per effect. On mobile:

- **Bloom**: Expensive (multi-tap blur). Use sparingly or reduce resolution.
- **FXAA**: Cheap, recommended for anti-aliasing.
- **Vignette**: Cheap (single-pass).
- **Color grading**: Cheap (single-pass).
- **DOF**: Expensive (depth blur). Avoid on low-end.

### Resolution Scaling

```typescript
// Render at half resolution for performance
const pixelRatio = Math.min(window.devicePixelRatio, 2);
composer.setSize(width * pixelRatio * 0.5, height * pixelRatio * 0.5);
```

### Custom Post-Processing Shader

```typescript
const VignetteShader = {
  uniforms: {
    tDiffuse: { value: null },
    offset: { value: 1.0 },
    darkness: { value: 1.0 },
  },
  vertexShader: /* glsl */`
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: /* glsl */`
    uniform sampler2D tDiffuse;
    uniform float offset;
    uniform float darkness;
    varying vec2 vUv;
    
    void main() {
      vec4 texel = texture2D(tDiffuse, vUv);
      vec2 uv = (vUv - 0.5) * 2.0;
      float vignette = 1.0 - dot(uv, uv) * darkness * 0.25;
      texel.rgb *= vignette;
      gl_FragColor = texel;
    }
  `,
};

const vignettePass = new ShaderPass(VignetteShader);
composer.addPass(vignettePass);
```

---

## 10. drei Shader Helpers

`@react-three/drei` provides utilities that simplify shader development.

### MeshDistortMaterial

```tsx
import { MeshDistortMaterial } from '@react-three/drei';

<mesh>
  <sphereGeometry args={[1, 32, 32]} />
  <MeshDistortMaterial
    color="#ff0000"
    distort={0.5}
    speed={2}
    roughness={0.2}
    metalness={0.8}
  />
</mesh>
```

### MeshWobbleMaterial

```tsx
import { MeshWobbleMaterial } from '@react-three/drei';

<mesh>
  <boxGeometry args={[1, 1, 1]} />
  <MeshWobbleMaterial
    color="#00ff00"
    factor={0.6}
    speed={1}
  />
</mesh>
```

### ShaderMaterial (drei wrapper)

```tsx
import { shaderMaterial } from '@react-three/drei';
import { extend } from '@react-three/fiber';

const ColorShiftMaterial = shaderMaterial(
  { time: 0, color: new THREE.Color('#ff0000') },
  // vertex
  /* glsl */`
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  // fragment
  /* glsl */`
    uniform float time;
    uniform vec3 color;
    varying vec2 vUv;
    void main() {
      vec3 shifted = color * (0.5 + 0.5 * sin(time + vUv.x * 10.0));
      gl_FragColor = vec4(shifted, 1.0);
    }
  `
);

extend({ ColorShiftMaterial });

// Usage in JSX
<colorShiftMaterial time={clock.elapsedTime} />
```

### useShader

```tsx
import { useShader } from '@react-three/drei';

function CustomMaterial() {
  const material = useShader(
    /* glsl */`
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    /* glsl */`
      varying vec2 vUv;
      void main() {
        gl_FragColor = vec4(vUv, 0.5, 1.0);
      }
    `
  );
  
  return <mesh material={material} />;
}
```

---

## 11. Shader Compilation Caching

Shader compilation is expensive. On mobile, it can cause noticeable frame drops.

### Pre-compilation Pattern

```typescript
// In App.tsx onCreated callback
<Canvas
  onCreated={(state) => {
    // Pre-compile all shaders before first frame
    state.gl.compile(state.scene, state.camera);
  }}
>
  {/* scene content */}
</Canvas>
```

### Why This Matters

- **First render**: Shaders compile on GPU (can take 10-100ms per shader)
- **Subsequent renders**: Cached by GPU driver
- **Problem**: First render stutter / white flash
- **Solution**: Pre-compile during loading screen

### Shader Warmup Pattern

```typescript
function ShaderWarmup() {
  const { gl, scene, camera } = useThree();
  
  useEffect(() => {
    // Force compilation of all materials in scene
    gl.compile(scene, camera);
  }, [gl, scene, camera]);
  
  return null;
}
```

### Material Caching

```typescript
// Cache materials to avoid recompilation
const materialCache = new Map<string, THREE.ShaderMaterial>();

function getCachedMaterial(key: string, config: ShaderMaterialConfig) {
  if (!materialCache.has(key)) {
    materialCache.set(key, new THREE.ShaderMaterial(config));
  }
  return materialCache.get(key)!;
}

// Usage
const mat = getCachedMaterial('glow', {
  uniforms: { uTime: { value: 0 } },
  vertexShader: glowVert,
  fragmentShader: glowFrag,
});
```

### Instanced Rendering for Shader Reuse

```typescript
// Instead of multiple meshes with same shader:
// BAD — 25 separate draw calls, 25 shader compilations
{cells.map((cell, i) => (
  <mesh key={i}>
    <boxGeometry />
    <shaderMaterial {...config} />
  </mesh>
))}

// GOOD — 1 draw call, 1 shader compilation
<instancedMesh args={[geometry, material, 25]}>
  {/* Update instance matrices in useFrame */}
</instancedMesh>
```

> **Example: Blocube Implementation**
> Blocube pre-compiles all shaders on Canvas mount via `state.gl.compile(state.scene, state.camera)` in the `onCreated` callback. This prevents a white flicker on first render. The entire scene uses only ~10 draw calls via InstancedMesh: 4 face tiles (25 instances each), 1 top decorative face, 1 drag preview, 2 FX meshes (84 fragments + 48 sparks), and backdrop elements. All textures are procedural `DataTexture` — no async loading.

---

## 12. Genre Patterns

Different game genres require different shader and material approaches.

### 12.1 Puzzle Clear FX

**Visual goal**: Satisfying explosion when lines/rows clear.

```typescript
// Fragment explosion
const FRAG_COUNT = 84;
const fragments = Array.from({ length: FRAG_COUNT }, () => ({
  pos: new THREE.Vector3(),
  vel: new THREE.Vector3(),
  life: 0,
  maxLife: 1,
  color: new THREE.Color(),
}));

// Fragment shader
const fragmentShader = /* glsl */`
  uniform sampler2D uGlowTexture;
  varying vec3 vColor;
  varying float vAlpha;
  
  void main() {
    vec4 tex = texture2D(uGlowTexture, gl_PointCoord);
    gl_FragColor = vec4(vColor * tex.rgb, tex.a * vAlpha);
  }
`;

// Spark shader (additive blending)
const sparkShader = /* glsl */`
  uniform sampler2D uGlowTexture;
  varying vec3 vColor;
  varying float vAlpha;
  
  void main() {
    vec2 uv = gl_PointCoord - 0.5;
    float dist = length(uv);
    float glow = exp(-dist * 4.0);
    gl_FragColor = vec4(vColor * glow, glow * vAlpha);
  }
`;

// Shockwave ring
const shockShader = /* glsl */`
  uniform sampler2D uRingTexture;
  uniform float uScale;
  varying vec2 vUv;
  
  void main() {
    vec2 uv = (vUv - 0.5) / uScale + 0.5;
    vec4 tex = texture2D(uRingTexture, uv);
    float fade = 1.0 - uScale; // Fade as it expands
    gl_FragColor = vec4(tex.rgb, tex.a * fade);
  }
`;
```

**Key techniques**:
- Pre-allocated object pools with circular buffer reuse
- InstancedMesh for batch rendering (84 fragments = 1 draw call)
- Additive blending for sparks and shockwaves
- Procedural textures (glow + ring) generated once at startup
- Conditional `needsUpdate` — only flag GPU buffers when data changes

### 12.2 Runner Speed Lines

**Visual goal**: Streaks of light indicating forward motion.

```glsl
// Speed lines vertex shader
uniform float uTime;
uniform float uSpeed;

attribute float lineOffset;
attribute float lineLength;

varying float vAlpha;

void main() {
  // Move lines toward camera based on speed
  float z = mod(position.z + uTime * uSpeed + lineOffset, 100.0) - 50.0;
  
  vAlpha = 1.0 - abs(z) / 50.0; // Fade at edges
  
  vec3 pos = vec3(position.x, position.y, z);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
}

// Speed lines fragment shader
varying float vAlpha;

void main() {
  // Simple white line with alpha falloff
  gl_FragColor = vec4(1.0, 1.0, 1.0, vAlpha * 0.6);
}
```

**Implementation**:
```typescript
// Create speed line geometry
const LINE_COUNT = 100;
const positions = new Float32Array(LINE_COUNT * 6); // 2 vertices per line
const offsets = new Float32Array(LINE_COUNT);
const lengths = new Float32Array(LINE_COUNT);

for (let i = 0; i < LINE_COUNT; i++) {
  const x = (Math.random() - 0.5) * 10;
  const y = (Math.random() - 0.5) * 10;
  const z = Math.random() * 100;
  
  positions[i * 6] = x;
  positions[i * 6 + 1] = y;
  positions[i * 6 + 2] = z;
  positions[i * 6 + 3] = x;
  positions[i * 6 + 4] = y;
  positions[i * 6 + 5] = z + 2; // Line length
  
  offsets[i] = Math.random() * 100;
  lengths[i] = 1 + Math.random() * 3;
}
```

### 12.3 Idle Glow Effects

**Visual goal**: Gentle pulsing glow on collectibles and UI elements.

```glsl
// Idle glow vertex shader
uniform float uTime;
varying vec2 vUv;

void main() {
  vUv = uv;
  
  // Gentle breathing scale
  float pulse = 1.0 + sin(uTime * 2.0) * 0.05;
  vec3 scaled = position * pulse;
  
  gl_Position = projectionMatrix * modelViewMatrix * vec4(scaled, 1.0);
}

// Idle glow fragment shader
uniform vec3 uColor;
uniform float uTime;
varying vec2 vUv;

void main() {
  // Radial glow
  float dist = length(vUv - 0.5) * 2.0;
  float glow = 1.0 - smoothstep(0.0, 1.0, dist);
  glow = pow(glow, 2.0);
  
  // Pulsing intensity
  float pulse = 0.8 + 0.2 * sin(uTime * 2.0);
  
  gl_FragColor = vec4(uColor * glow * pulse, glow * pulse);
}
```

**Implementation**:
```typescript
// Coin glow
const coinMaterial = new THREE.ShaderMaterial({
  uniforms: {
    uTime: { value: 0 },
    uColor: { value: new THREE.Color('#ffd700') },
  },
  vertexShader: idleGlowVert,
  fragmentShader: idleGlowFrag,
  transparent: true,
  blending: THREE.AdditiveBlending,
  depthWrite: false,
});

// Update in useFrame
useFrame((state) => {
  coinMaterial.uniforms.uTime.value = state.clock.elapsedTime;
});
```

### 12.4 Tower Defense Range Indicators

**Visual goal**: Semi-transparent circle showing tower attack range.

```glsl
// Range indicator vertex shader
varying vec2 vUv;

void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}

// Range indicator fragment shader
uniform vec3 uColor;
uniform float uTime;
uniform float uSelected; // 0 = normal, 1 = selected

varying vec2 vUv;

void main() {
  // Circle mask
  float dist = length(vUv - 0.5) * 2.0;
  float circle = 1.0 - smoothstep(0.9, 1.0, dist);
  
  // Edge ring
  float ring = smoothstep(0.85, 0.9, dist) - smoothstep(0.95, 1.0, dist);
  
  // Pulsing when selected
  float pulse = 1.0 + sin(uTime * 4.0) * 0.2 * uSelected;
  
  // Combine
  float alpha = (circle * 0.1 + ring * 0.5) * pulse;
  
  gl_FragColor = vec4(uColor, alpha);
}
```

**Implementation**:
```typescript
function TowerRangeIndicator({ position, radius, selected }) {
  const matRef = useRef<THREE.ShaderMaterial>(null);
  
  useFrame((state) => {
    if (matRef.current) {
      matRef.current.uniforms.uTime.value = state.clock.elapsedTime;
      matRef.current.uniforms.uSelected.value = selected ? 1.0 : 0.0;
    }
  });
  
  return (
    <mesh position={position} rotation={[-Math.PI / 2, 0, 0]}>
      <planeGeometry args={[radius * 2, radius * 2]} />
      <shaderMaterial
        ref={matRef}
        uniforms={{
          uColor: { value: new THREE.Color('#00ff00') },
          uTime: { value: 0 },
          uSelected: { value: 0 },
        }}
        vertexShader={rangeVert}
        fragmentShader={rangeFrag}
        transparent
        depthWrite={false}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}
```

---

## 13. Sources

1. Three.js ShaderMaterial Documentation — https://threejs.org/docs/#api/en/materials/ShaderMaterial
2. Three.js DataTexture — https://threejs.org/docs/#api/en/textures/DataTexture
3. The Book of Shaders — https://thebookofshaders.com/
4. WebGL GLSL ES Specification — https://registry.khronos.org/webgl/specs/latest/
5. Three.js Post-Processing — https://threejs.org/examples/#webgl_postprocessing
6. React Three drei Documentation — https://github.com/pmndrs/drei
7. Mobile GPU Architecture (ARM) — https://developer.arm.com/graphics
8. WebGL Performance Tips — https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API/WebGL_best_practices
9. Three.js InstancedMesh — https://threejs.org/docs/#api/en/objects/InstancedMesh
10. GLSL ES 3.0 Specification — https://registry.khronos.org/OpenGL/specs/es/3.2/GLSL_ES_Specification_3.20.pdf
11. Expo GL Documentation — https://docs.expo.dev/versions/latest/sdk/gl-view/
12. Three.js Uniforms — https://threejs.org/docs/#api/en/core/Uniform
13. Additive Blending — https://threejs.org/docs/#api/en/constants/Materials
14. Shader Compilation Optimization — https://developer.chrome.com/blog/shader-compilation/
15. React Three Fiber useFrame — https://docs.pmnd.rs/react-three-fiber/api/hooks#useframe
