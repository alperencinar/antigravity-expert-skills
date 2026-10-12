# /3d-asset-generate - Meshy AI Generation Loop

`meshy-ai` MCP server wrapper ile yüksek kaliteli 3D asset üretimi.

## A. Preview Generation (Taslak Mesh)
`create_text_to_3d_task` çağrısı:
- `prompt`: `"low poly stylized [asset_name], vibrant colors, game ready asset, clean topology"`
- `mode`: `"preview"`, `ai_model`: `"latest"`, `art_style`: `"realistic"`, `topology`: `"triangle"`, `symmetry_mode`: `"auto"`

## B. Polling & Monitoring
`retrieve_text_to_3d_task` ile `task_id` durumunu `status == "SUCCEEDED"` olana kadar izle.

## C. Refinement & Texturing (Yüksek Kalite)
`create_text_to_3d_task` çağrısı: `mode: "refine"`, `preview_task_id: <preview_task_id>`.
Başarı sonrası indirme URL'lerini çıkar:
- FBX/GLB model dosyası
- Texture'lar (Diffuse/Albedo, Normal Map, Metallic, Roughness, Emission)

## Referans Dokümanlar
- [`3d_asset_pipeline.md`](../researches/3d_asset_pipeline.md)
- [`meshy_ai_asset_pipeline_guide.md`](../researches/meshy_ai_asset_pipeline_guide.md)
