# /rn-game-asset — Asset Pipeline & Prosedürel Geometri

Prosedürel geometry, texture yönetimi, Metro yapılandırması ve build optimizasyonu.

## A. Prosedürel Geometri — ExtrudeGeometry

Asset dosya bağımlılığını sıfırla, bundle boyutunu minimize et:

```typescript
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

  // Yuvarlatılmış dikdörtgen path
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
    bevelSegments: 3,
    curveSegments: 8,
  });

  geo.center();
  return geo;
}
```

## B. GLTF/GLB Yükleme

```typescript
import { useGLTF } from '@react-three/drei/native';

function Model({ url }: { url: string }) {
  const { scene } = useGLTF(url);
  return <primitive object={scene} />;
}
```

**Öneri:** Mümkünse prosedürel geometry kullan (daha küçük bundle).

## C. Texture Yükleme ve Önbellekleme

```typescript
import { useTexture } from '@react-three/drei/native';

function TexturedModel() {
  const texture = useTexture(require('./texture.png'));
  
  return (
    <mesh>
      <boxGeometry />
      <meshStandardMaterial map={texture} />
    </mesh>
  );
}
```

## D. Metro Config — Dual Three.js Önleme

```javascript
// metro.config.js
const { getDefaultConfig } = require('expo/metro-config');
const config = getDefaultConfig(__dirname);

config.resolver.resolveRequest = (context, moduleName, platform) => {
  // Tüm 'three' importlarını CJS build'e zorla
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

**Belirtiler (dual instance varsa):**
- `mesh.material instanceof THREE.Material` başarısız
- Bundle boyutu beklenenden büyük (>5MB)
- R3F "Expected Object3D" hataları

## E. EAS Build Optimizasyonu

```json
// eas.json
{
  "build": {
    "production": {
      "ios": {
        "simulator": false,
        "autoIncrement": true
      },
      "android": {
        "autoIncrement": true
      }
    }
  }
}
```

## F. patch-package ile Native Module Düzeltmeleri

```bash
# expo-gl patch örneği
npx patch-package expo-gl
```

Patch dosyası `patches/` klasöründe saklanır, `postinstall` ile otomatik uygulanır.

## G. Asset Doğrulama

```typescript
// Build öncesi kontrol
function validateAssets() {
  console.log(`[Asset] Geometries: ${THREE.Cache.keys().length}`);
  console.log(`[Asset] Textures loaded: ${textureCount}`);
  console.log(`[Asset] Total memory: ~${estimateMemory()}MB`);
}
```

## H. Prosedürel vs Yüklenmiş Asset

| Yaklaşım | Bundle | Bellek | Kontrol | Kullanım |
|----------|--------|--------|---------|----------|
| Prosedürel | Sıfır | Tam | Full | Tile, parçacık, FX |
| GLTF | +1-10MB | Değişken | Partial | Karmaşık model |
| DataTexture | Sıfır | Tam | Full | Glow, noise |
| PNG/JPG | +100KB-2MB | Decode | Low | Art asset, UI |

## I. Yaygın Tuzaklar

- Metro config yoksa → dual Three.js instance, sessiz render hataları
- `useGLTF` async → loading state yönetimi gerekli
- Texture dispose edilmez → GPU bellek sızıntısı
- Prosedürel geometry pahalı → modül seviyesinde bir kez oluştur
- Asset boyutu kontrolsüz → bundle > 100MB

## Referans Doküman
- [`rn_threejs_asset_pipeline_and_verification.md`](../researches/rn_threejs_asset_pipeline_and_verification.md)
