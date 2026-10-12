# /3d-asset-verify - Visual Inspection & Verification

Asset entegrasyonu sonrası görsel denetim ve Play Mode doğrulaması.

## Doğrulama Adımları

1. `AssetDatabase.Refresh()` ile asset tanımayı zorla.
2. `Cardiv/Setup Prototype Scene` menü öğesi ile prefabları sahneye instantiate et.
3. `Unity_ManageEditor` ile `Play` moduna geç.
4. Scene view'da `PlayerCar` üzerinde `FrameSelected` çalıştır ve ekran görüntüsü yakala.

## Referans Dokümanlar
- [`visual_aesthetics_polish.md`](../researches/visual_aesthetics_polish.md)
- [`low_poly_aesthetics.md`](../researches/low_poly_aesthetics.md)
