# /rn-game-shader — Shader & Custom Materyaller

Mobil GPU'lar için GLSL shader yazımı, ShaderMaterial ve prosedürel texture'lar.

## A. ShaderMaterial Temelleri

```typescript
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

## B. Additive Blending (FX Efektleri)

Parçacık efektleri için additive blending:

```typescript
const sparkMaterial = new THREE.ShaderMaterial({
  uniforms: {
    uTexture: { value: GLOW_TEX },
    uColor: { value: new THREE.Color('#ffffff') },
  },
  vertexShader: `...`,
  fragmentShader: `...`,
  transparent: true,
  blending: THREE.AdditiveBlending,
  depthWrite: false,
});
```

## C. Prosedürel DataTexture

```typescript
function makeGlowTexture(size = 64): THREE.DataTexture {
  const data = new Uint8Array(size * size * 4);
  const center = (size - 1) / 2;
  
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const dx = (x - center) / center;
      const dy = (y - center) / center;
      const dist = Math.min(1, Math.sqrt(dx * dx + dy * dy));
      const alpha = Math.pow(1 - dist, 3); // kübik düşüş
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
```

## D. Mobil GPU Kısıtlamaları

- `precision mediump float` tercih et (`highp` değil)
- Döngü içinde texture lookup'tan kaçın
- Varying sayısı: 8-16 max (mobil)
- `gl_FragColor` kullan (GLSL ES 1.0, maksimum uyumluluk)
- Fragment shader'da branch'lerden kaçın

## E. GLSL ES 1.0 vs 3.0

| Özellik | GLSL ES 1.0 | GLSL ES 3.0 |
|---------|-------------|-------------|
| Output | `gl_FragColor` | `out vec4 fragColor` |
| Texture | `texture2D()` | `texture()` |
| Varying | `varying` | `in/out` |
| Destek | Tüm cihazlar | WebGL 2+ (iOS 14+) |

**Öneri:** Maksimum cihaz uyumluluğu için GLSL ES 1.0 kullan.

## F. Theme/Skin Sistemi

```typescript
const themeMaterials = THEMES.map((t) =>
  new THREE.MeshStandardMaterial({
    roughness: t.roughness,
    metalness: t.metalness,
    color: new THREE.Color(t.primary),
  })
);

// Referans değiştir — yeniden oluşturma değil
function getMaterial(themeIndex: number) {
  return themeMaterials[themeIndex];
}
```

## G. Shader Ön-Derleme

```typescript
<Canvas onCreated={(state) => {
  state.gl.compile(state.scene, state.camera);
}}>
```

## H. Yaygın Tuzaklar

- `highp` kullanmak → bazı mobil GPU'larda yavaş
- Texture'ı fragment'te `new` ile oluşturmak → GC stutter
- Uniform güncellemesi `useFrame` dışında → stale veri
- `depthWrite: true` additive blending ile → render hataları

## Referans Doküman
- [`threejs_shader_custom_materials_mobile.md`](../researches/threejs_shader_custom_materials_mobile.md)
