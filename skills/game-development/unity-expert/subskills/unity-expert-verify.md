# /unity-expert-verify - Automated Quality Audit & Verification Workflow

Canlı doğrulama, teşhis ve ekran görüntüsü yakalama iş akışı.

## Doğrulama Adımları

1. Asset veritabanı senkronizasyonunu zorla (`AssetDatabase.Refresh()`).
2. Unity Playmode test döngüsünü çalıştır (`Unity_ManageEditor`).
3. Yüksek çözünürlüklü viewport ekran görüntüleri yakala (`Unity_Camera_Capture`).
4. Sıfır console hatası, sıfır runtime GC allocation ve stabil 60 FPS doğrula.

## Referans Araçlar
- Unity Editor Playmode & Screenshot Audit Tools (unityMCP: `manage_editor`, `manage_camera`, `read_console`, `run_tests`)
