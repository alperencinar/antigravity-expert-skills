# /3d-asset-sync - Unity Textures & PBR Materials

Texture'ları `Assets/Cardiv/Textures/` altına kopyala ve CurvedWorld Lit materyallerine dinamik ata.

## A. Texture Ayarları
Normal map importunu C# Editor scriptinde garanti et:
```csharp
TextureImporter importer = AssetImporter.GetAtPath(normalPath) as TextureImporter;
if (importer != null && importer.textureType != TextureImporterType.NormalMap)
{
    importer.textureType = TextureImporterType.NormalMap;
    importer.SaveAndReimport();
}
```

## B. Custom/CurvedWorldLit Materyal Kurulumu
URP Lit property adlarını (`_MetallicGlossMap` vb.) KULLANMA; custom shader property'lerini kullan:
- `_BaseMap` = `meshy_basecolor.png`
- `_BumpMap` = `meshy_normal.png` (`_NORMALMAP` aktif)
- `_MetallicMap` = `meshy_metallic_smoothness.png` (`_Metallic = 0.35`, `_Smoothness = 0.55`)
- `_EmissionMap` = `meshy_emission.png` (`_EMISSION` aktif, `_EmissionColor = Color.white`)

## C. Görünmez Trigger Collider Kuralı
- Trigger alt objelerinde primitive `MeshFilter`/`MeshRenderer` ASLA bırakma.
- Yardımcı triggerlar (rampa jump trigger, pickup alanı) sade GameObject + `BoxCollider (isTrigger = true)` olmalı.

## D. Zorunlu Unity Editor Çalıştırma Kuralı
- `[MenuItem("Cardiv/...")]` scripti yazmak/değiştirmek `.prefab` dosyalarını otomatik güncellemez.
- Script sonrası MUTLAKA `Unity_ManageMenuItem` ile `Cardiv/<MenuItemName>` çalıştır ve prefabları diske kaydettir.

## E. Bounds Genişletme & Dinamik Ölçekleme Standardı
Keyfi ölçek çarpanı hardcode etme; native FBX bounds uzunluğunu kategori gerçek dünya metrelerine eşle:

| Kategori | Hedef Boyut | Pivot Standardı |
|---|---|---|
| Sedan / Sports / Police | Uzunluk `4.5m`, Genişlik `1.9m` | Geometrik bounds merkez |
| SUV / Van / Pickup | Uzunluk `5.2m`, Genişlik `2.1m` | Geometrik bounds merkez |
| Semi-Truck / Tanker | Uzunluk `14.0m`, Genişlik `2.6m` | Geometrik bounds merkez |
| Tren / Lokomotif | Uzunluk `22.0m`, Yükseklik `4.2m` | Ray merkez pivot |
| Üst Geçit / Kemer | Clearance `6.5m`, Genişlik `18.0m` | 3 şerit + banket |
| Bina / Dükkan | Yükseklik `12.0m - 25.0m` | Alt taban pivot (`Y=0`) |
| Ağaç / Bitki | Yükseklik `4.0m - 8.0m` | Alt taban pivot (`Y=0`) |
| Küçük Engeller | Yükseklik `0.8m - 1.2m` | Zemin taban pivot |

```csharp
float scaleFactor = targetLength / nativeLength;
fbxInstance.transform.localScale = Vector3.one * scaleFactor;
// Otomatik Y-Grounding: birleşik bounds min Y → localPosition.y = -minY
fbxInstance.transform.localPosition = new Vector3(0f, -combinedBounds.min.y, 0f);
```

## Referans Dokümanlar
- [`unity_robust_asset_architecture_research.md`](../researches/unity_robust_asset_architecture_research.md)
- [`stylized_unlit_shader.md`](../researches/stylized_unlit_shader.md)
- [`ai_3d_asset_ingestion_and_normalization.md`](../researches/ai_3d_asset_ingestion_and_normalization.md)
