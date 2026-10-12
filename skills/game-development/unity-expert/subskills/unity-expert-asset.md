# /unity-expert-asset - AI 3D Model Ingestion & Normalization Pipeline

Meshy AI / Tripo AI / Rodin gibi AI mesh üreticilerinden gelen ham modelleri, sıfır manuel müdahale ile oyuna hazır prefablara dönüştüren normalizasyon hattı.

## Zorunlu Asset Standartları

1. **Scale Baking & Kategori Bazlı Gerçek Dünya Ölçekleme**
   - FBX importta `globalScale = 1.0f`, `bakeAxisConversion = true`, `useFileScale = false`.
   - Dinamik ölçek: `scaleFactor = L_target / L_FBXnative`
   - Kategoriler: Araba `4.5m`, SUV/Van `5.2m`, Tır `14.0m`, Tren `22.0m`, Üst Geçit `6.5m` clearance, Bina `12-25m`, Ağaç `4-8m`.
2. **Pivot & Otomatik Y-Grounding**
   - Araçlar: Geometrik bounds merkez pivot + otomatik `-minY` grounding.
   - Çevre propları: Alt taban pivot (Blender `min_z`) ile `Y = 0` yerleşim.
   - **KRİTİK SPAWNER Y-OFFSET KORUMA KURALI**: Spawner/pool/yerleşim mantığı `childModel.localPosition.y` değerini ASLA `0f` yapmamalı; root `Y=0` yol seviyesinde dururken child model zemin ofsetini korur.
3. **CurvedWorld Bounds Genişletme**: Büyük çevre proplarına (köprü, bina) `CurvedWorldBoundsExpander.cs` uygula (SRP frustum culling'e karşı).
4. **Tangent & Normal**: Smooth normal yeniden hesaplama + MikkTSpace tangent (`importTangents = ModelImporterTangents.CalculateMikk`).
5. **Otomatik Yön Skorlama**: `Z_length > X_width > Y_height` olacak rotasyonu bul; ileri yön çevirmede DAİMA world-space pre-multiply: `bestRot = Quaternion.Euler(0f, 180f, 0f) * bestRot;`
6. **Geometrik Tekerlek Tespiti & Pivot Merkezleme**
   - Submesh bounds merkezlerini root uzayına çevir: `root.transform.InverseTransformPoint(mf.transform.TransformPoint(mf.sharedMesh.bounds.center))`
   - `posInRoot.x >= 0` (sağ/sol) ve `posInRoot.z >= 0` (ön/arka) ile `wheel-front-left` vb. sınıflandır.
   - Local pivot normalizasyonu: `verts[i] -= center` + `mf.transform.localPosition += center` (aks etrafında dönme, orbital sallanma yok).
7. **Güvenli Tag & Layer Atama**: `int layer = LayerMask.NameToLayer(...)` bounds-check et; tag atamayı `try/catch (UnityException)` ile sar.
8. **PBR Texture & Materyal**: `Custom/CurvedWorldLit` shader üzerinde `_BaseMap`, `_BumpMap` (`_NORMALMAP`), `_MetallicMap` (`_Metallic=0.35`, `_Smoothness=0.55`), `_EmissionMap` (`_EMISSION`, beyaz).
9. **Görünmez Trigger Collider Kuralı**: Yardımcı triggerlar `MeshFilter`/`MeshRenderer` OLMADAN sade `BoxCollider (isTrigger)` GameObject'i olmalı.
10. **Data-Driven Registry**: Tüm araç metadata'sı `VehicleDataSO` + `VehicleRegistry.asset` üzerinden; 100+ araç için 0 C# değişikliği.

## Referans Dokümanlar
- [`ai_3d_asset_ingestion_and_normalization.md`](../researches/ai_3d_asset_ingestion_and_normalization.md)
- [`meshy_ai_asset_pipeline_guide.md`](../researches/meshy_ai_asset_pipeline_guide.md)
