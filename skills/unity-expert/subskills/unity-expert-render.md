# /unity-expert-render - URP CurvedWorld Shader & Mobile Lighting Pipeline

Stilize eğri ufuk (curved horizon) görselleri + %100 doğru dinamik gölgeler.

## Shader & Lighting Standartları

1. **2-Eksenli Eğrilik HLSL Formülü**
   - `ΔY = -K_z * (Z_vertex - Z_camera)^2`
   - `ΔX =  K_x * (Z_vertex - Z_camera)^2`
2. **Pass Parity**: Aynı vertex displacement matematiği hem `ForwardLit` hem `ShadowCaster` pass'lerinde birebir uygulanmalı.
3. **CPU Frustum Culling Genişletme**: `CurvedWorldBoundsExpander.cs` ile `renderer.localBounds` genişlet; statik AABB culling'in bükülmüş meshleri kırpmasını önle.
4. **Forward+ Lighting**: Araç spot ışıkları için URP Forward+ kullan; SRP Batcher uyumluluğunu tüm mobil GPU'larda (Mali, Adreno, Apple Silicon) koru.

## Referans Dokümanlar
- [`urp_curved_world_and_lighting_mastery.md`](../researches/urp_curved_world_and_lighting_mastery.md)
- [`curved_world_urp_rendering_guide.md`](../researches/curved_world_urp_rendering_guide.md)
- [`curved_world_shader.md`](../researches/curved_world_shader.md)
- [`shader_properties_factcheck.md`](../researches/shader_properties_factcheck.md)
- [`visual_flatness_research.md`](../researches/visual_flatness_research.md)
- [`aaa_environment_techniques.md`](../researches/aaa_environment_techniques.md)
