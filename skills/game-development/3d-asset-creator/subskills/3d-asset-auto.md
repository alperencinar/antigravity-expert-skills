# /3d-asset-auto - Zero-Code Data-Driven Vehicle Pipeline (`GenericVehicleAssetImporter`)

Cardiv'e yeni araç eklerken özel C# Editor scripti YAZMA, `PlayerVisualRig.cs` / `MainMenuScreen.cs` DEĞİŞTİRME. Sistem %100 Data-Driven çalışır.

## İş Akışı

1. **Unity Menü**: `Cardiv -> Generic Vehicle Asset Importer Window` aç (veya `GenericVehicleAssetImporter.ProcessAndImportVehicle()` çağır).
2. **Girdiler**: `importFolderPath` (örn. `Assets/MeshyImports/NewCarFolder`), `vehicleId` (örn. `AudiR8`), `category` (örn. `Sportscar`).
3. **Otomatik Pipeline**:
   - Texture'ları otomatik yapılandırır (`meshy_normal.png` → NormalMap).
   - Blender CLI ile +90° Z döndürür, 4 tekerleği partisyonlar, `Assets/Cardiv/Models/[vehicleId]Car/[vehicleId]_processed.fbx` üretir.
   - `Assets/Cardiv/Materials/[vehicleId]CarMat.mat` konumunda URP `Custom/CurvedWorldLit` materyal oluşturur.
   - Birleşik bounds ile Y-ground offset hesaplar (`groundOffsetY = -combinedBounds.min.y`).
   - `Assets/Cardiv/Data/Vehicles/[vehicleId]Data.asset` konumunda `VehicleDataSO` üretir/günceller ve `VehicleRegistry.asset` içine kaydeder.
   - `Model_[vehicleId]` container'ını `PlayerCar.prefab`'a bağlar.
4. **Sıfır Kod Değişikliği**: `PlayerVisualRig` ve `MainMenuScreen` runtime'da `VehicleRegistry`'yi dinamik sorgular; 100+ araç eklemek **0 C# değişikliği** gerektirir.

## Referans Dokümanlar
- [`unity_robust_asset_architecture_research.md`](../researches/unity_robust_asset_architecture_research.md)
- [`meshy_ai_asset_pipeline_guide.md`](../researches/meshy_ai_asset_pipeline_guide.md)
