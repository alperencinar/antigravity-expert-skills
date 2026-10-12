# AAA Mobil ve 3D Oyunlar İçin Modern UI/UX Shaders & Technical Art Mimarısı

> **Doküman Türü:** Production-Grade Technical Art & UI Shader Rehberi  
> **Hedef Motor/Pipeline:** Unity 2022.3 LTS / 2023.x / 6.x (UGUI & Universal Render Pipeline - URP)  
> **Dil:** Türkçe (HLSL / ShaderLab / C# kodları ve Matematiksel Formüller dahil)  
> **Konum:** `skills/game-ui-designer-developer/researches/game_ui_shaders_and_technical_art.md`

---

## 📋 İçindekiler
1. [Giriş ve Mimari Genel Bakış](#1-giri%C5%9F-ve-mimari-genel-bak%C4%B1%C5%9F)
   - UGUI Canvas Render İşleyişi & Material Modifier Altyapısı
   - Mobil GPU Mimarileri (TBDR) İçin UI Performans İlkeleri
2. [Bölüm 1: Procedural UI Shaders (URP & Canvas Uyumlu)](#b%C3%B6l%C3%BCm-1-procedural-ui-shaders-urp--canvas-uyumlu)
   - 1.1 Glassmorphic UI & Background Blur Shader (URP Camera Opaque & Downsampled Pass)
   - 1.2 Glowing Outline Shader (Procedural Rim Light & Pulsating Glow)
   - 1.3 Procedural Rounded Corners Shader (SDF Dynamic Border Radius & Antialiasing)
   - 1.4 Curved 3D/VR UI Shader (World Space Canvas Deformation)
3. [Bölüm 2: Figma to Unity Export Pipeline & Technical Art Workflows](#b%C3%B6l%C3%BCm-2-figma-to-unity-export-pipeline--technical-art-workflows)
   - 2.1 9-Slice Border Setup & Pixel Perfection
   - 2.2 Vector SVG Import Standartları & Unity Vector Graphics Altyapısı
   - 2.3 Sprite Atlas V2 Optimization & Bleeding Prevention (4px/8px Bleed Rules)
4. [Bölüm 3: UI Lighting & Particle Systems](#b%C3%B6l%C3%BCm-3-ui-lighting--particle-systems)
   - 3.1 Canvas-Space UI Light Reflections & Holographic Specular Shimmer
   - 3.2 UI Particle Systems & Stencil Masking (RectMask2D Clipping Integration)
5. [Performans Benchmarkları, Karşılaştırma Tabloları & Checklist](#5-performans-benchmarklar%C4%B1-kar%C5%9F%C4%B1la%C5%9Ft%C4%B1rma-tablolar%C4%B1--checklist)

---

## 1. Giriş ve Mimari Genel Bakış

### UGUI Canvas Render İşleyişi & Material Modifier Altyapısı
Unity UI (`UnityEngine.UI.Graphic`) bileşenleri (Image, TextMeshPro, RawImage), Canvas render döngüsünde mesh vertex verilerini (Position, UV0, UV1, Color, Normal, Tangent) toplayarak tek bir batch halinde ekran kartına gönderir. Bir shader'ın Unity Canvas ve `RectMask2D` / `Mask` sistemleriyle tam uyumlu çalışabilmesi için şu standartları sağlaması zorunludur:

1. **Stencil Buffer Entegrasyonu:** `Mask` bileşeni Stencil buffer'a yazma yapar (`Comp Always`, `Pass Replace`). Alt elemanların shader'ları bu Stencil değerini test etmelidir (`Comp Equal`).
2. **RectMask2D Clipping (`_ClipRect`):** `RectMask2D` Stencil kullanmaz; dünya uzayındaki kırpma dikdörtgenini Shader'a `_ClipRect` (Vector4: `MinX, MinY, MaxX, MaxY`) parametresi olarak aktarır. Shader'ın fragment aşamasında `UnityGet2DClipping(input.worldPosition.xy, _ClipRect)` fonksiyonu çağrılarak clip yapılmalıdır.
3. **IMaterialModifier ve Material Instancing:** Canvas, dynamic batching yaparken materyalleri birleştirir. Ancak özel shader parametreleri değiştirildiğinde (`MaterialPropertyBlock` veya CanvasRenderer vertex akışları vasıtasıyla) batch kırılmalarını engellemek için `UV1`, `UV2` veya `Tangent` kanalları üzerinden veri taşınmalıdır.

```
       [ UGUI Canvas Pipeline ]
                  │
     ┌────────────┴────────────┐
     ▼                         ▼
[ Hard Stencil Mask ]    [ RectMask2D ]
  │ Stencil Bit Ref        │ Pass World Rect Vector4
  ▼                        ▼
Shader Stencil Test     Shader UnityGet2DClipping()
  │                        │
  └────────────┬───────────┘
               ▼
   [ Pixel Shader Output ]
```

### Mobil GPU Mimarileri (TBDR) İçin UI Performans İlkeleri
Mobil GPU'lar (ARM Mali, Qualcomm Adreno, Apple Silicon) **Tile-Based Deferred Rendering (TBDR)** kullanır. TBDR mimarilerinde:
- **Overdraw (Piksel Üst Üste Binme) Ölümcüldür:** Şeffaf (Alpha Blending) UI panellerinin üst üste gelmesi GPU tile bellek bant genişliğini (Bandwidth) tüketir ve döküm ısınmasına/throtling'e yol açar.
- **Procedural Shader vs. Texture Sampling:** Mobil cihazlarda piksel shader matematiksel hesaplamaları (SDF, procedural glow), bellekten yüksek çözünürlüklü kaplama okumaya (Texture Fetch) göre daha az enerji harcar ve band genişliğini korur.
- **GrabPass Yasağı:** URP içerisinde eski `GrabPass` kullanılamaz. Bunun yerine URP Camera `_CameraOpaqueTexture` veya özel bir Downsampled Render Feature Blur pass kullanılmalıdır.

---

## Bölüm 1: Procedural UI Shaders (URP & Canvas Uyumlu)

### 1.1 Glassmorphic UI & Background Blur Shader

Glassmorphism efekti, UI arkasındaki oyun sahnesini buğulu (blurred) gösterirken yüzeyde kırılma, kromatik sapma (chromatic aberration) ve ince kenar ışığı (rim glow) oluşturur.

#### URP Arka Plan Bulanıklaştırma Mimarısı
Glassmorphic shader iki yöntemle arka planı okuyabilir:
1. **URP `_CameraOpaqueTexture` (Screen Color):** Render Pipeline Asset üzerinde *Opaque Texture* aktif edilir. UI shader'ı bu dokuyu kopyalayıp HLSL fragment shader içinde Gaussian/Kawase blur örneklemesi yapar.
2. **URP Render Feature (Önerilen Production Yaklaşımı):** Arka plan sahnesi UI render edilmeden önce `ScriptableRenderPass` içerisinde 1/4 veya 1/8 çözünürlüğe indirgenerek (Downsample) 2-pass Kawase Blur ile işlenir ve `_UIBackgroundBlurTexture` ismiyle global doku olarak atanır. Bu yöntem mobil GPU'larda fragment shader yükünü %80 azaltır.

```
[ Scene Opaque Pass ] ──► [ Downsample 1/4 ] ──► [ Kawase Blur Pass x2 ] ──► Set Global `_UIBackgroundBlurTexture`
                                                                                        │
[ UI Canvas Render Pass ] ◄──────────────────────────────────────────────────────────────┘
  └── Glassmorphism Shader Samples `_UIBackgroundBlurTexture` + Edge Rim Highlight
```

#### HLSL Shaderlab koda dökümü (`UI_Glassmorphism_URP.shader`)

```hlsl
Shader "GameUI/Procedural/Glassmorphism_URP"
{
    Properties
    {
        [PerRendererData] _MainTex ("Sprite Texture", 2D) = "white" {}
        _Color ("Tint Color", Color) = (1, 1, 1, 0.2)
        _BlurAmount ("Blur Amount / Lod", Range(0, 5)) = 2.0
        _DistortionStrength ("Refraction Distortion", Range(0, 0.1)) = 0.02
        _DistortionNoise ("Noise Texture", 2D) = "bump" {}
        _ChromaticAberration ("Chromatic Aberration", Range(0, 0.02)) = 0.005
        _RimColor ("Rim Highlight Color", Color) = (1, 1, 1, 0.8)
        _RimPower ("Rim Power", Range(0.5, 10)) = 3.0

        // Stencil Masking Properties
        _StencilComp ("Stencil Comparison", Float) = 8
        _Stencil ("Stencil ID", Float) = 0
        _StencilOp ("Stencil Operation", Float) = 0
        _StencilWriteMask ("Stencil Write Mask", Float) = 255
        _StencilReadMask ("Stencil Read Mask", Float) = 255
        _ColorMask ("Color Mask", Float) = 15
        [Toggle(UNITY_UI_ALPHACLIP)] _UseUIAlphaClip ("Use Alpha Clip", Float) = 0
    }

    SubShader
    {
        Tags
        {
            "Queue" = "Transparent"
            "IgnoreProjector" = "True"
            "RenderType" = "Transparent"
            "PreviewType" = "Plane"
            "CanSubShaderPassToBatch" = "True"
        }

        Stencil
        {
            Ref [_Stencil]
            Comp [_StencilComp]
            Pass [_StencilOp]
            ReadMask [_StencilReadMask]
            WriteMask [_StencilWriteMask]
        }

        Cull Off
        Lighting Off
        ZWrite Off
        ZTest [UNITY_UI_ALPHACLIP]
        Blend SrcAlpha OneMinusSrcAlpha
        ColorMask [_ColorMask]

        Pass
        {
            Name "UI_Glassmorphism_Pass"
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 2.0

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.core/ShaderLibrary/Color.hlsl"

            struct Attributes
            {
                float4 positionOS   : POSITION;
                float4 color        : COLOR;
                float2 uv           : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS   : SV_POSITION;
                float4 color        : COLOR;
                float2 uv           : TEXCOORD0;
                float4 screenPos    : TEXCOORD1;
                float4 worldPosition : TEXCOORD2;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            TEXTURE2D(_MainTex);
            SAMPLER(sampler_MainTex);
            TEXTURE2D(_DistortionNoise);
            SAMPLER(sampler_DistortionNoise);
            
            // URP Camera Opaque Texture veya Render Feature Blur Texture
            TEXTURE2D(_CameraOpaqueTexture);
            SAMPLER(sampler_CameraOpaqueTexture);

            CBUFFER_START(UnityPerMaterial)
                float4 _MainTex_ST;
                float4 _Color;
                float4 _RimColor;
                float _BlurAmount;
                float _DistortionStrength;
                float _ChromaticAberration;
                float _RimPower;
                float4 _ClipRect;
            CBUFFER_END

            Varyings vert(Attributes input)
            {
                Varyings output = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(output);

                output.worldPosition = input.positionOS;
                output.positionCS = TransformObjectToHClip(input.positionOS.xyz);
                output.uv = TRANSFORM_TEX(input.uv, _MainTex);
                output.color = input.color * _Color;
                output.screenPos = ComputeScreenPos(output.positionCS);
                
                return output;
            }

            // Kawase / Gaussian sampling simulation over Camera Opaque Texture
            half4 SampleBlurredBackground(float2 screenUV, float distortion)
            {
                float2 uv = screenUV + distortion;
                
                // Chromatic Aberration Sampling
                half r = SAMPLE_TEXTURE2D_LOD(_CameraOpaqueTexture, sampler_CameraOpaqueTexture, uv + float2(_ChromaticAberration, 0), _BlurAmount).r;
                half g = SAMPLE_TEXTURE2D_LOD(_CameraOpaqueTexture, sampler_CameraOpaqueTexture, uv, _BlurAmount).g;
                half b = SAMPLE_TEXTURE2D_LOD(_CameraOpaqueTexture, sampler_CameraOpaqueTexture, uv - float2(_ChromaticAberration, 0), _BlurAmount).b;
                
                return half4(r, g, b, 1.0);
            }

            half4 frag(Varyings input) : SV_Target
            {
                // UGUI RectMask2D Clipping Check
                #if defined(UNITY_UI_CLIP_RECT)
                half2 clipUV = input.worldPosition.xy;
                half clipAlpha = (clipUV.x >= _ClipRect.x && clipUV.x <= _ClipRect.z &&
                                  clipUV.y >= _ClipRect.y && clipUV.y <= _ClipRect.w) ? 1.0 : 0.0;
                if (clipAlpha <= 0.0) discard;
                #endif

                float2 screenUV = input.screenPos.xy / input.screenPos.w;

                // Distortion Normal Generation
                float2 noiseUV = input.uv * 3.0;
                half3 normalMap = SAMPLE_TEXTURE2D(_DistortionNoise, sampler_DistortionNoise, noiseUV).rgb * 2.0 - 1.0;
                float2 distortion = normalMap.xy * _DistortionStrength;

                // Sample Blurred Background
                half4 blurredBg = SampleBlurredBackground(screenUV, distortion);

                // Sprite Texture Mask
                half4 spriteTex = SAMPLE_TEXTURE2D(_MainTex, sampler_MainTex, input.uv);
                
                // Rim Light / Edge Glow Calculation
                float2 edgeDistance = abs(input.uv - float2(0.5, 0.5)) * 2.0; // 0 to 1 range from center
                float maxEdge = max(edgeDistance.x, edgeDistance.y);
                float rimFactor = pow(maxEdge, _RimPower);
                half4 rimHighlight = _RimColor * rimFactor;

                // Final Composition
                half4 finalColor = lerp(blurredBg, input.color, input.color.a);
                finalColor.rgb += rimHighlight.rgb * rimHighlight.a;
                finalColor.a = spriteTex.a * input.color.a;

                return finalColor;
            }
            ENDHLSL
        }
    }
}
```

---

### 1.2 Glowing Outline Shader (Procedural Rim Light & Pulsating Glow)

Geleneksel UI outline bileşenleri (Unity UI `Outline`), mevcuttaki mesh'i 4 ya da 8 yöne çoğaltarak (duplicate vertex) vertex sayısını ve overdraw'u inanılmaz derecede artırır. Procedural Glowing Outline shader'ımız ise piksel düzeyinde matris türevi / mesafe alanı hesaplayarak sıfır ek vertex yükü ile çalışır.

#### Matematiksel Glow & Pulsation Formülü
Pikselin kenara olan uzaklığı $\mathbf{d}$ ve dış ışıma genişliği $\mathbf{\sigma}$ olmak üzere, Soft Glow yoğunluğu Gauss veya Exponential sönümleme ile hesaplanır:

$$I_{glow}(d) = \exp\left(-\left(\frac{d}{\sigma}\right)^2\right) \cdot \left[1.0 + A \cdot \sin(\omega \cdot t)\right]$$

Burada:
- $A$: Nabız (pulsation) genliği.
- $\omega$: Nabız frekansı ($2\pi \cdot f$).
- $t$: `_Time.y` (Zaman).

#### HLSL Shaderlab koda dökümü (`UI_GlowingOutline_URP.shader`)

```hlsl
Shader "GameUI/Procedural/GlowingOutline_URP"
{
    Properties
    {
        [PerRendererData] _MainTex ("Sprite Texture", 2D) = "white" {}
        _Color ("Main Color", Color) = (1,1,1,1)
        
        [HDR] _OutlineColor ("Outline HDR Color", Color) = (0, 0.8, 1, 1)
        _OutlineWidth ("Outline Width", Range(0.0, 0.15)) = 0.03
        _GlowSoftness ("Glow Softness / Falloff", Range(0.01, 0.2)) = 0.05
        
        _PulseSpeed ("Pulsation Speed", Float) = 3.0
        _PulseAmount ("Pulsation Amount", Range(0.0, 0.5)) = 0.2

        // Canvas Masking
        _StencilComp ("Stencil Comparison", Float) = 8
        _Stencil ("Stencil ID", Float) = 0
        _StencilOp ("Stencil Operation", Float) = 0
        _StencilWriteMask ("Stencil Write Mask", Float) = 255
        _StencilReadMask ("Stencil Read Mask", Float) = 255
        _ColorMask ("Color Mask", Float) = 15
    }

    SubShader
    {
        Tags
        {
            "Queue" = "Transparent"
            "IgnoreProjector" = "True"
            "RenderType" = "Transparent"
            "PreviewType" = "Plane"
            "CanSubShaderPassToBatch" = "True"
        }

        Stencil
        {
            Ref [_Stencil]
            Comp [_StencilComp]
            Pass [_StencilOp]
            ReadMask [_StencilReadMask]
            WriteMask [_StencilWriteMask]
        }

        Cull Off
        Lighting Off
        ZWrite Off
        ZTest [UNITY_UI_ALPHACLIP]
        Blend SrcAlpha OneMinusSrcAlpha
        ColorMask [_ColorMask]

        Pass
        {
            Name "UI_GlowingOutline_Pass"
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            struct Attributes
            {
                float4 positionOS   : POSITION;
                float4 color        : COLOR;
                float2 uv           : TEXCOORD0;
            };

            struct Varyings
            {
                float4 positionCS   : SV_POSITION;
                float4 color        : COLOR;
                float2 uv           : TEXCOORD0;
                float4 worldPosition : TEXCOORD1;
            };

            TEXTURE2D(_MainTex);
            SAMPLER(sampler_MainTex);

            CBUFFER_START(UnityPerMaterial)
                float4 _MainTex_ST;
                float4 _Color;
                float4 _OutlineColor;
                float _OutlineWidth;
                float _GlowSoftness;
                float _PulseSpeed;
                float _PulseAmount;
                float4 _ClipRect;
            CBUFFER_END

            Varyings vert(Attributes input)
            {
                Varyings output;
                output.worldPosition = input.positionOS;
                output.positionCS = TransformObjectToHClip(input.positionOS.xyz);
                output.uv = TRANSFORM_TEX(input.uv, _MainTex);
                output.color = input.color * _Color;
                return output;
            }

            // Alpha Dilate via 8-Directional Texture Sampling
            float SampleAlphaOffset(float2 uv, float2 offset)
            {
                return SAMPLE_TEXTURE2D(_MainTex, sampler_MainTex, uv + offset).a;
            }

            half4 frag(Varyings input) : SV_Target
            {
                half4 mainTexColor = SAMPLE_TEXTURE2D(_MainTex, sampler_MainTex, input.uv);
                half alpha = mainTexColor.a;

                // 8-Tap Alpha Sampling for Outer Boundary Detection
                float2 w = float2(_OutlineWidth, _OutlineWidth);
                float maxAlpha = alpha;

                maxAlpha = max(maxAlpha, SampleAlphaOffset(input.uv, float2(w.x, 0)));
                maxAlpha = max(maxAlpha, SampleAlphaOffset(input.uv, float2(-w.x, 0)));
                maxAlpha = max(maxAlpha, SampleAlphaOffset(input.uv, float2(0, w.y)));
                maxAlpha = max(maxAlpha, SampleAlphaOffset(input.uv, float2(0, -w.y)));
                maxAlpha = max(maxAlpha, SampleAlphaOffset(input.uv, float2(w.x, w.y) * 0.7071));
                maxAlpha = max(maxAlpha, SampleAlphaOffset(input.uv, float2(-w.x, w.y) * 0.7071));
                maxAlpha = max(maxAlpha, SampleAlphaOffset(input.uv, float2(w.x, -w.y) * 0.7071));
                maxAlpha = max(maxAlpha, SampleAlphaOffset(input.uv, float2(-w.x, -w.y) * 0.7071));

                // Outline Alpha Extraction
                float outlineAlpha = smoothstep(0.01, _GlowSoftness, maxAlpha - alpha);

                // Sine Wave Pulsation
                float pulse = 1.0 + sin(_Time.y * _PulseSpeed) * _PulseAmount;
                half4 animatedOutline = _OutlineColor * pulse;

                // Blending Core Image + Glowing Outline
                half4 finalColor;
                finalColor.rgb = lerp(animatedOutline.rgb, mainTexColor.rgb * input.color.rgb, alpha);
                finalColor.a = max(alpha, outlineAlpha * _OutlineColor.a) * input.color.a;

                return finalColor;
            }
            ENDHLSL
        }
    }
}
```

---

### 1.3 Procedural Rounded Corners Shader (SDF Dynamic Border Radius & Antialiasing)

Vektörel dokular kullanmadan, sadece matematiksel **Signed Distance Field (SDF)** kullanarak dikdörtgen elemanların 4 köşesini birbirinden bağımsız olarak yuvarlatan shader teknolojisidir.

#### Matematiksel SDF Formülü ve Antialiasing
Merkezi köken alan bir $p \in \mathbb{R}^2$ noktası, dikdörtgen yarım-boyutu $b \in \mathbb{R}^2$ ve köşe yarıçapı $r$ için SDF formülü:

$$d(p, b, r) = \|\max(|p| - b + r, 0)\| + \min(\max(|p.x| - b.x + r, |p.y| - b.y + r), 0) - r$$

Piksel kenarlarında çözünürlükten bağımsız pürüzsüzleştirme (Antialiasing) sağlamak için GPU donanım türevi olan `fwidth()` yardımıyla `smoothstep` uygulanır:

$$\text{Alpha} = 1.0 - \text{smoothstep}\left(-fw, fw, d(p, b, r)\right), \quad \text{burada } fw = \|\nabla d\| \approx 0.5 \cdot \text{fwidth}(d)$$

```
     Corner Radius (Top-Left)               Corner Radius (Top-Right)
          ┌──────────────────────────────────────────┐
          │ r_tl                                r_tr │
          │                                          │
          │                                          │
          │ r_bl                                r_br │
          └──────────────────────────────────────────┘
    Corner Radius (Bottom-Left)          Corner Radius (Bottom-Right)
```

#### HLSL Shaderlab koda dökümü (`UI_ProceduralRoundedCorners_URP.shader`)

```hlsl
Shader "GameUI/Procedural/RoundedCorners_SDF_URP"
{
    Properties
    {
        [PerRendererData] _MainTex ("Sprite Texture", 2D) = "white" {}
        _Color ("Fill Color Tint", Color) = (1, 1, 1, 1)
        _RectSize ("Rect Size (Pixels XY)", Vector) = (200, 100, 0, 0)
        
        // 4 Bağımsız Köşe Yarıçapı (Top-Left, Top-Right, Bottom-Right, Bottom-Left)
        _Radii ("Radii (TL, TR, BR, BL)", Vector) = (20, 20, 20, 20)
        
        _StrokeWidth ("Border Stroke Width", Range(0, 20)) = 2.0
        _StrokeColor ("Border Color", Color) = (0, 0, 0, 1)

        // Canvas Masking
        _StencilComp ("Stencil Comparison", Float) = 8
        _Stencil ("Stencil ID", Float) = 0
        _StencilOp ("Stencil Operation", Float) = 0
        _StencilWriteMask ("Stencil Write Mask", Float) = 255
        _StencilReadMask ("Stencil Read Mask", Float) = 255
        _ColorMask ("Color Mask", Float) = 15
    }

    SubShader
    {
        Tags
        {
            "Queue" = "Transparent"
            "IgnoreProjector" = "True"
            "RenderType" = "Transparent"
            "PreviewType" = "Plane"
            "CanSubShaderPassToBatch" = "True"
        }

        Stencil
        {
            Ref [_Stencil]
            Comp [_StencilComp]
            Pass [_StencilOp]
            ReadMask [_StencilReadMask]
            WriteMask [_StencilWriteMask]
        }

        Cull Off
        Lighting Off
        ZWrite Off
        ZTest [UNITY_UI_ALPHACLIP]
        Blend SrcAlpha OneMinusSrcAlpha
        ColorMask [_ColorMask]

        Pass
        {
            Name "UI_RoundedCorners_SDF_Pass"
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            struct Attributes
            {
                float4 positionOS   : POSITION;
                float4 color        : COLOR;
                float2 uv           : TEXCOORD0;
            };

            struct Varyings
            {
                float4 positionCS   : SV_POSITION;
                float4 color        : COLOR;
                float2 uv           : TEXCOORD0;
                float2 pixelPos     : TEXCOORD1;
            };

            TEXTURE2D(_MainTex);
            SAMPLER(sampler_MainTex);

            CBUFFER_START(UnityPerMaterial)
                float4 _MainTex_ST;
                float4 _Color;
                float4 _StrokeColor;
                float4 _RectSize;
                float4 _Radii; // x: TL, y: TR, z: BR, w: BL
                float _StrokeWidth;
                float4 _ClipRect;
            CBUFFER_END

            // SDF for Rounded Rectangle with Variable Corner Radii
            float SDF_RoundedRect(float2 p, float2 b, float4 r)
            {
                // Select radius based on quadrant
                float radius = (p.x > 0.0) ? ((p.y > 0.0) ? r.y : r.z) : ((p.y > 0.0) ? r.x : r.w);
                float2 q = abs(p) - b + float2(radius, radius);
                return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - radius;
            }

            Varyings vert(Attributes input)
            {
                Varyings output;
                output.positionCS = TransformObjectToHClip(input.positionOS.xyz);
                output.uv = TRANSFORM_TEX(input.uv, _MainTex);
                output.color = input.color * _Color;
                
                // Centered Pixel Position Calculation (-RectSize/2 to +RectSize/2)
                output.pixelPos = (input.uv - 0.5) * _RectSize.xy;
                return output;
            }

            half4 frag(Varyings input) : SV_Target
            {
                float2 halfSize = _RectSize.xy * 0.5;
                float d = SDF_RoundedRect(input.pixelPos, halfSize, _Radii);

                // Dynamic Hardware Antialiasing
                float aa = fwidth(d) * 0.5;
                float fillAlpha = 1.0 - smoothstep(-aa, aa, d);

                if (fillAlpha <= 0.0) discard;

                // Border Stroke Calculation
                float innerDist = d + _StrokeWidth;
                float strokeAlpha = 1.0 - smoothstep(-aa, aa, innerDist);
                float borderMask = fillAlpha - strokeAlpha;

                half4 texColor = SAMPLE_TEXTURE2D(_MainTex, sampler_MainTex, input.uv) * input.color;
                
                // Mix Fill Texture + Border Color
                half4 finalColor = lerp(texColor, _StrokeColor, borderMask);
                finalColor.a *= fillAlpha;

                return finalColor;
            }
            ENDHLSL
        }
    }
}
```

#### Otomatik RectSize Aktarımı İçin C# Helper Script

```csharp
using UnityEngine;
using UnityEngine.UI;

[ExecuteAlways]
[RequireComponent(typeof(RectTransform))]
[RequireComponent(typeof(Graphic))]
public class UIRoundedCornersController : MonoBehaviour, IMaterialModifier
{
    private static readonly int RectSizeProperty = Shader.PropertyToID("_RectSize");
    private RectTransform _rectTransform;
    private Graphic _graphic;

    private void Awake()
    {
        _rectTransform = GetComponent<RectTransform>();
        _graphic = GetComponent<Graphic>();
    }

    private void OnRectTransformDimensionsChange()
    {
        if (_graphic != null)
        {
            _graphic.SetMaterialDirty();
        }
    }

    public Material GetModifiedMaterial(Material baseMaterial)
    {
        if (_rectTransform == null) _rectTransform = GetComponent<RectTransform>();
        
        Rect rect = _rectTransform.rect;
        Material modifiedMat = new Material(baseMaterial);
        modifiedMat.SetVector(RectSizeProperty, new Vector4(rect.width, rect.height, 0, 0));
        return modifiedMat;
    }
}
```

---

### 1.4 Curved 3D/VR UI Shader (World Space Canvas Deformation)

Kavisli (Curved) UI sistemleri, 3D Dünya alanındaki paneller (World Space Canvas) ve VR başlıklarında görüş açısını sarmallamak (immersion) için kritik öneme sahiptir. Mesh kırılmasını önlemek için vertex shader seviyesinde silindirik (Cylindrical) bükülme hesaplanır.

#### Silindirik Bükülme Matematiksel Modeli
Kavis Yarıçapı $R$ (Radius) ve Panel genişliği $X_{local}$ olmak üzere, silindir açısı $\theta$ ve yeni pozisyon koordinatları $P'_{local}$:

$$\theta = \frac{P_{local}.x}{R}$$

$$P'_{local}.x = R \cdot \sin(\theta)$$

$$P'_{local}.z = R \cdot (1.0 - \cos(\theta))$$

```
      View Point (Eye / Camera)
                  │
                  ▼
         /─────────────────\  <-- Curved Canvas Radius R
        /  P'(x,y,z)        \
       /   θ                 \
      └───────────┼───────────┘
               Center
```

#### HLSL Shaderlab koda dökümü (`UI_CurvedCanvas_URP.shader`)

```hlsl
Shader "GameUI/Procedural/CurvedCanvas_3D_URP"
{
    Properties
    {
        [PerRendererData] _MainTex ("Sprite Texture", 2D) = "white" {}
        _Color ("Tint Color", Color) = (1,1,1,1)
        _CurvatureRadius ("Curvature Radius R", Float) = 5.0
        [Toggle(_FLIP_CURVATURE)] _ReverseCurve ("Invert Curve", Float) = 0
    }

    SubShader
    {
        Tags
        {
            "Queue" = "Transparent"
            "IgnoreProjector" = "True"
            "RenderType" = "Transparent"
            "PreviewType" = "Plane"
        }

        Cull Off
        Lighting Off
        ZWrite Off
        ZTest LEqual
        Blend SrcAlpha OneMinusSrcAlpha

        Pass
        {
            Name "UI_CurvedCanvas_Pass"
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma shader_feature _FLIP_CURVATURE

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            struct Attributes
            {
                float4 positionOS   : POSITION;
                float4 color        : COLOR;
                float2 uv           : TEXCOORD0;
                float3 normalOS     : NORMAL;
            };

            struct Varyings
            {
                float4 positionCS   : SV_POSITION;
                float4 color        : COLOR;
                float2 uv           : TEXCOORD0;
                float3 worldNormal  : TEXCOORD1;
            };

            TEXTURE2D(_MainTex);
            SAMPLER(sampler_MainTex);

            CBUFFER_START(UnityPerMaterial)
                float4 _MainTex_ST;
                float4 _Color;
                float _CurvatureRadius;
            CBUFFER_END

            Varyings vert(Attributes input)
            {
                Varyings output;
                float3 pos = input.positionOS.xyz;

                // Cylindrical Deformation Math
                float radius = max(0.001, _CurvatureRadius);
                #if defined(_FLIP_CURVATURE)
                radius = -radius;
                #endif

                float theta = pos.x / radius;
                float sinTheta, cosTheta;
                sincos(theta, sinTheta, cosTheta);

                // Recalculate Deformed Position
                pos.x = radius * sinTheta;
                pos.z += radius * (1.0 - cosTheta);

                // Recalculate Normals for Lighting (if Lit UI is needed)
                float3 deformedNormal = input.normalOS;
                deformedNormal.x = input.normalOS.x * cosTheta - input.normalOS.z * sinTheta;
                deformedNormal.z = input.normalOS.x * sinTheta + input.normalOS.z * cosTheta;

                output.positionCS = TransformObjectToHClip(pos);
                output.uv = TRANSFORM_TEX(input.uv, _MainTex);
                output.color = input.color * _Color;
                output.worldNormal = TransformObjectToWorldNormal(deformedNormal);

                return output;
            }

            half4 frag(Varyings input) : SV_Target
            {
                half4 col = SAMPLE_TEXTURE2D(_MainTex, sampler_MainTex, input.uv) * input.color;
                return col;
            }
            ENDHLSL
        }
    }
}
```

---

## Bölüm 2: Figma to Unity Export Pipeline & Technical Art Workflows

AAA kalitesinde bir UI geliştirmede Figma'dan Unity Engine'e varlık (Asset) aktarımı sırasındaki yanlış yapılandırmalar bellek sızıntılarına, kırık çözünürlüklere ve gereksiz overdraw'a sebep olur.

```
┌─────────────────┐       Standardized       ┌──────────────────────┐
│  Figma Design   │ ───────────────────────► │ Unity Import Pipeline│
└─────────────────┘  Auto-Layout Rules & SVG └──────────────────────┘
         │                                               │
         ├─ 9-Slice Padding                              ├─ Sprite Editor 9-Slice Border
         ├─ Flatten Vectors                              ├─ Vector Graphics Tessellation
         └─ Naming Convention (Atlas_Group_Name)        └─ Sprite Atlas V2 Packing Bleed
```

### 2.1 9-Slice Border Setup & Pixel Perfection

9-slice (Dokuz Dilimli Sprite) teknolojisi, bir UI panelinin köşelerinin yarıçapını ve detaylarını korurken orta alanlarının dikey ve yatay ölçeklenmesini sağlar.

#### Figma -> Unity 9-Slice Kuralları
1. **Figma İçi Hazırlık:** Panel tasarlanırken köşe detaylarının bittiği ve düz hiza deseninin başladığı piksel sınırları tespit edilmelidir. Örn: 64x64px boyutunda bir butonun köşeleri 16px ise, 9-slice sınırları L:16, R:16, T:16, B:16 olmalıdır.
2. **Sprite Editor Ayarları:** Unity Sprite Editor içerisinde *Border* değerleri (L, R, T, B) girilir.
3. **Pixels Per Unit (PPU) Multiplier Matematiksel Formülü:**
   Canvas Scaler genişliği ile Sprite PPU eşleşmesi ekran bozulmalarını engeller:

$$\text{Effective PPU} = \text{Native Sprite PPU} \times \frac{\text{Image Rect Scale}}{\text{Canvas Scaler Reference Factor}}$$

#### 9-Slice vs Procedural SDF Karşılaştırma Tablosu

| Metrik | 9-Slice Raster Sprite | Procedural SDF Shader |
| :--- | :--- | :--- |
| **VRAM Kullanımı** | Doku Boyutuna Bağlı (Yüksek) | **İhmal Edilebilir (Sıfır Doku)** |
| **Doku Atlas Alanı** | Atlas Alanı Kaplar | **Atlas Yer Kaplamaz** |
| **Dinamik Köşe Değişimi** | İmkansız (Statik Dokudur) | **Runtime'da C# ile Dinamik Değişebilir** |
| **GPU Pixel Shader Yükü** | Çok Düşük (Tek Texture Sample) | Orta (SDF Matematiksel İfadeleri) |
| **Batched Render** | Aynı Atlaste ise Tam Batching | Material Instance Değişirse Batching Kırılabilir |

---

### 2.2 Vector SVG Import Standartları & Unity Vector Graphics Altyapısı

Unity 2021+ projelerinde vektörel `.svg` dosyalarını doğrudan GPU vertex tessellation (nirengileme) ile render etmek için `com.unity.vectorgraphics` paketi kullanılır.

#### Figma SVG Export Kuralları
- **Flatten All Curves:** Tüm *Stroke* ve *Text* bileşenleri Figma'da `Outline Stroke` (`Cmd+Shift+O` / `Ctrl+Shift+O`) yapılarak `Path` formatına dönüştürülmelidir.
- **Drop Shadows / Blur FX Yasağı:** Figma'nın ürettiği HTML/CSS bazlı SVG efekt filtreleri (`<feGaussianBlur>`) Unity Importer tarafından desteklenmez. Efektler vektörden ayrıştırılmalı ve shader ile uygulanmalıdır.
- **Precision Limits:** SVG çizim panosu integer (tamsayı) koordinatlara oturtulmalıdır (Pixel Snapping).

#### Unity Vector Graphics Importer Ayarları

```
┌─────────────────────────────────────────────────────────┐
│ SVG Importer Settings                                   │
├─────────────────────────┬───────────────────────────────┤
│ Vector Resolution (PPU) │ 100                           │
│ Generated Texture Type  │ Vector Graphic (GPU SVG)      │
│ Advanced Step           │                               │
│  ├─ Max Gradient Samples│ 64                            │
│  ├─ Max Tessellation Step│ 12 (Mobil için 8-12 idealdir) │
│  └─ Target Resolution   │ HD / Retinal Multiplier (2x)  │
└─────────────────────────┴───────────────────────────────┘
```

> [!WARNING]
> **Mobil GPU Uyarısı:** Karmaşık vektör amblemler (1000+ path noktası) SVG Importer ile GPU tessellation yapıldığında inanılmaz yüksek vertex sayısına (30.000+ tris) ulaşabilir. Karmaşık ikonlar için SVG yerine PNG Raster Atlas kullanılması performans açısından zorunludur!

---

### 2.3 Sprite Atlas V2 Optimization & Bleeding Prevention (4px/8px Bleed Rules)

UGUI performansının 1 numaralı kuralı **Draw Call Reduction (Batching)** sağlamaktır. Farklı klasörlerdeki PNG görselleri tek bir Sprite Atlas içinde toplanmalıdır.

#### Edge Bleeding (Kenar Renk Taşması) Neden Oluşur?
Görseller doku haritasına yapışık dizildiğinde, GPU **Bilinear Filtering** (Mipmapping/Sampling) esnasında komşu sprite'ın renk piksellerini çeker. Sonuç olarak UI elemanlarının etrafında ince siyah veya şeffaf çizgiler belirir.

#### Bleeding Önleme İçin 8px Bleed & Padding Standardı

```
┌───────────────────┬────────────────────────────────────────────┐
│ Atlas V2 Ayarı    │ Production Standardı                       │
├───────────────────┼────────────────────────────────────────────┤
│ Pack Method       │ Block Pack                                 │
│ Padding Power     │ 8 Pixels (Mipmap seviyesi 3 için zorunlu)  │
│ Allow Rotation    │ Disabled (UI Sprite 9-slice bozulmaması için)|
│ Tight Packing     │ Disabled (Rectangle Packing Zorunludur!)   │
│ Alpha Dilation    │ Enabled (Kenar renklerini dışa genişletir) │
└───────────────────┴────────────────────────────────────────────┘
```

```
       [ Tight Packing: YANLIŞ ]             [ Rectangle Pack + Padding: DOĞRU ]
      ┌──────────┐┌──────────┐                 ┌────────────┐  ┌────────────┐
      │ Sprite A ││ Sprite B │                 │  Sprite A  │  │  Sprite B  │
      └──────────┘└──────────┘                 └────────────┘  └────────────┘
      ◄── Kenar Renk Taşması (Bleeding)! ──►     ◄─── 8px Safe Padding Gap ───►
```

---

## Bölüm 3: UI Lighting & Particle Systems

### 3.1 Canvas-Space UI Light Reflections & Holographic Specular Shimmer

Nadir kartlar, başarım ödülleri ve UI açılış efektlerinde dinamik ışık süzülmesi (Shimmer / Specular Sweep) için hazırlanan shader programıdır.

#### Anizotropik Parıltı Matematiksel Modeli
Parıltı çizgisi $S(uv, t)$, döner bir açı $\theta$ ve geçen zaman $t$ parametrelerine bağlı dinamik bir çizgi denklemidir:

$$UV_{rot} = R(\theta) \cdot (UV - 0.5)$$

$$S(uv, t) = \text{smoothstep}\left(w, 0.0, |UV_{rot}.x - \text{fmod}(v \cdot t, D) + \frac{D}{2}|\right)$$

#### HLSL Shaderlab koda dökümü (`UI_HolographicShimmer_URP.shader`)

```hlsl
Shader "GameUI/Lighting/HolographicShimmer_URP"
{
    Properties
    {
        [PerRendererData] _MainTex ("Sprite Texture", 2D) = "white" {}
        _Color ("Tint Color", Color) = (1,1,1,1)
        
        [HDR] _ShimmerColor ("Shimmer Light Color", Color) = (2, 2, 2, 1)
        _ShimmerWidth ("Sweep Line Width", Range(0.01, 0.5)) = 0.1
        _ShimmerAngle ("Sweep Angle (Degrees)", Range(0, 360)) = 45.0
        _ShimmerSpeed ("Sweep Speed", Float) = 1.5
        _ShimmerInterval ("Repeat Delay Interval", Float) = 3.0

        // Stencil Masking
        _StencilComp ("Stencil Comparison", Float) = 8
        _Stencil ("Stencil ID", Float) = 0
        _StencilOp ("Stencil Operation", Float) = 0
        _StencilWriteMask ("Stencil Write Mask", Float) = 255
        _StencilReadMask ("Stencil Read Mask", Float) = 255
        _ColorMask ("Color Mask", Float) = 15
    }

    SubShader
    {
        Tags
        {
            "Queue" = "Transparent"
            "IgnoreProjector" = "True"
            "RenderType" = "Transparent"
            "PreviewType" = "Plane"
            "CanSubShaderPassToBatch" = "True"
        }

        Stencil
        {
            Ref [_Stencil]
            Comp [_StencilComp]
            Pass [_StencilOp]
            ReadMask [_StencilReadMask]
            WriteMask [_StencilWriteMask]
        }

        Cull Off
        Lighting Off
        ZWrite Off
        ZTest [UNITY_UI_ALPHACLIP]
        Blend SrcAlpha OneMinusSrcAlpha
        ColorMask [_ColorMask]

        Pass
        {
            Name "UI_HolographicShimmer_Pass"
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            struct Attributes
            {
                float4 positionOS   : POSITION;
                float4 color        : COLOR;
                float2 uv           : TEXCOORD0;
            };

            struct Varyings
            {
                float4 positionCS   : SV_POSITION;
                float4 color        : COLOR;
                float2 uv           : TEXCOORD0;
            };

            TEXTURE2D(_MainTex);
            SAMPLER(sampler_MainTex);

            CBUFFER_START(UnityPerMaterial)
                float4 _MainTex_ST;
                float4 _Color;
                float4 _ShimmerColor;
                float _ShimmerWidth;
                float _ShimmerAngle;
                float _ShimmerSpeed;
                float _ShimmerInterval;
                float4 _ClipRect;
            CBUFFER_END

            Varyings vert(Attributes input)
            {
                Varyings output;
                output.positionCS = TransformObjectToHClip(input.positionOS.xyz);
                output.uv = TRANSFORM_TEX(input.uv, _MainTex);
                output.color = input.color * _Color;
                return output;
            }

            half4 frag(Varyings input) : SV_Target
            {
                half4 mainColor = SAMPLE_TEXTURE2D(_MainTex, sampler_MainTex, input.uv) * input.color;

                // 2D Rotation Matrix
                float rad = radians(_ShimmerAngle);
                float sinA = sin(rad);
                float cosA = cos(rad);
                float2 rotatedUV = float2(
                    input.uv.x * cosA - input.uv.y * sinA,
                    input.uv.x * sinA + input.uv.y * cosA
                );

                // Time Animation Loop with Delay Interval
                float cycle = _ShimmerSpeed * _Time.y;
                float progress = fmod(cycle, 1.0 + _ShimmerInterval) - (_ShimmerInterval * 0.5);

                // Line Sweep Gradient Intensity
                float dist = abs(rotatedUV.x - progress);
                float shimmerIntensity = smoothstep(_ShimmerWidth, 0.0, dist);

                // Fresnel / Specular Overlay Blend
                half3 shimmerSpecular = _ShimmerColor.rgb * shimmerIntensity;
                mainColor.rgb += shimmerSpecular * mainColor.a;

                return mainColor;
            }
            ENDHLSL
        }
    }
}
```

---

### 3.2 UI Particle Systems & Stencil Masking (RectMask2D Clipping Integration)

Unity `ParticleSystem` 3D dünya objesi olduğu için Varsayılan olarak UGUI Canvas elemanlarının arkasında kalabilir veya `RectMask2D` panelleri dışına çıktığında kırpılamaz (clip olamaz).

#### Çözüm Mimarısı: Canvas UI Particle Masking Shader & Sorting Manager
1. **Sorting Order Ayarı:** Particle Renderer materyaline Canvas'ın sorting layer'ı ile eşleşen bir `Sorting Order` atanır.
2. **Stencil & ClipRect Desteği:** Particle Shader'ına Canvas Stencil ve `_ClipRect` özellikleri eklenmelidir.

#### HLSL Canvas Uyumlu Particle Shader (`UI_Particle_URP.shader`)

```hlsl
Shader "GameUI/Particles/UIParticle_Masked_URP"
{
    Properties
    {
        _MainTex ("Particle Texture", 2D) = "white" {}
        [HDR] _TintColor ("Tint Color", Color) = (1,1,1,1)

        // Canvas Masking Entegrasyonu
        _StencilComp ("Stencil Comparison", Float) = 8
        _Stencil ("Stencil ID", Float) = 0
        _StencilOp ("Stencil Operation", Float) = 0
        _StencilWriteMask ("Stencil Write Mask", Float) = 255
        _StencilReadMask ("Stencil Read Mask", Float) = 255
        _ColorMask ("Color Mask", Float) = 15
    }

    SubShader
    {
        Tags
        {
            "Queue" = "Transparent"
            "IgnoreProjector" = "True"
            "RenderType" = "Transparent"
            "PreviewType" = "Plane"
        }

        Stencil
        {
            Ref [_Stencil]
            Comp [_StencilComp]
            Pass [_StencilOp]
            ReadMask [_StencilReadMask]
            WriteMask [_StencilWriteMask]
        }

        Cull Off
        Lighting Off
        ZWrite Off
        Blend SrcAlpha One // Additive Particle Blending (veya SrcAlpha OneMinusSrcAlpha)
        ColorMask [_ColorMask]

        Pass
        {
            Name "UI_Particle_Pass"
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            struct Attributes
            {
                float4 positionOS   : POSITION;
                float4 color        : COLOR;
                float2 uv           : TEXCOORD0;
            };

            struct Varyings
            {
                float4 positionCS   : SV_POSITION;
                float4 color        : COLOR;
                float2 uv           : TEXCOORD0;
                float2 worldPos     : TEXCOORD1;
            };

            TEXTURE2D(_MainTex);
            SAMPLER(sampler_MainTex);

            CBUFFER_START(UnityPerMaterial)
                float4 _MainTex_ST;
                float4 _TintColor;
                float4 _ClipRect;
            CBUFFER_END

            Varyings vert(Attributes input)
            {
                Varyings output;
                output.positionCS = TransformObjectToHClip(input.positionOS.xyz);
                output.worldPos = input.positionOS.xy;
                output.uv = TRANSFORM_TEX(input.uv, _MainTex);
                output.color = input.color * _TintColor;
                return output;
            }

            half4 frag(Varyings input) : SV_Target
            {
                // RectMask2D Clipping Test
                #if defined(UNITY_UI_CLIP_RECT)
                if (input.worldPos.x < _ClipRect.x || input.worldPos.x > _ClipRect.z ||
                    input.worldPos.y < _ClipRect.y || input.worldPos.y > _ClipRect.w)
                {
                    discard;
                }
                #endif

                half4 tex = SAMPLE_TEXTURE2D(_MainTex, sampler_MainTex, input.uv);
                return tex * input.color;
            }
            ENDHLSL
        }
    }
}
```

#### Otomatik Particle Stencil / Sorting C# Script (`UIParticleSystemController.cs`)

```csharp
using UnityEngine;
using UnityEngine.UI;

[ExecuteAlways]
[RequireComponent(typeof(ParticleSystem))]
public class UIParticleSystemController : MonoBehaviour
{
    [SerializeField] private Canvas parentCanvas;
    private ParticleSystemRenderer _particleRenderer;
    private MaskableGraphic _maskableGraphic;

    private void OnEnable()
    {
        _particleRenderer = GetComponent<ParticleSystemRenderer>();
        if (parentCanvas == null)
        {
            parentCanvas = GetComponentInParent<Canvas>();
        }

        UpdateParticleSorting();
    }

    public void UpdateParticleSorting()
    {
        if (parentCanvas != null && _particleRenderer != null)
        {
            _particleRenderer.sortingLayerID = parentCanvas.sortingLayerID;
            _particleRenderer.sortingOrder = parentCanvas.sortingOrder + 1;
        }
    }
}
```

---

## 5. Performans Benchmarkları, Karşılaştırma Tabloları & Checklist

### UI Shader Mimari Seçim Matrix'i

| Teknik | Overdraw Etkisi | VRAM Maliyeti | GPU Pixel Shader Yükü | Önerilen Kullanım Alanı |
| :--- | :--- | :--- | :--- | :--- |
| **Glassmorphism Blur** | Yüksek (Screen Copy) | Orta (Opaque Texture Buffer) | Yüksek | Ana Menü, Pause Pop-up (Statik) |
| **Procedural SDF Corner** | Düşük | **Sıfır** | Düşük / Orta | Tüm Dinamik Panel & Butonlar |
| **Figma 9-Slice PNG** | Düşük | Orta (Atlas Boyutuna Bağlı) | **En Düşük (Sadece Sample)** | Karmaşık Desenli UI Çerçeveleri |
| **Holographic Shimmer** | Düşük | Sıfır | Düşük | Nadir Öğe/Kart Efektleri |
| **Procedural Glow Outline**| Orta (8-Tap Sampling) | Sıfır | Orta | Seçili İkonlar, Focus State |

---

### Technical Art Deploy Checklist (Mobil UI Yayını Öncesi Kontrol Listesi)

- [ ] **Canvas Sorting & Hierarchy:** Tüm dynamic Canvas'lar static Canvas'lardan ayrıldı mı? (Re-batching maaliyetini sıfırlamak için).
- [ ] **Sprite Atlas Bleeding:** Tüm Atlas V2 konfigürasyonlarında Padding $\ge 8\text{px}$ yapıldı mı ve *Allow Rotation* kapatıldı mı?
- [ ] **Shader Stencil & RectMask2D:** Yazılan tüm özel UI shader'larında `_ClipRect` ve Stencil blokları tanımlandı mı?
- [ ] **Raycast Target Optimization:** Tıklanma ihtiyacı olmayan tüm Text, Image ve Icon bileşenlerinin `Raycast Target` tıkları kaldırıldı mı? (CPU GraphicRaycaster performans gain'i için zorunlu).
- [ ] **Mobile Downsampled Blur Pass:** Glassmorphism shader'ında canlı `GrabPass` yerine URP Camera Downsampled Pass veya `_CameraOpaqueTexture` atandı mı?
- [ ] **SVG Flattening Check:** Figma'dan aktarılan tüm ikonlar `Outline Stroke` haline getirilip 1000+ tris aşımı engellendi mi?

---

> **Doküman Sonu.**  
> *Bu araştırma ve teknik standartlar belgesi Unity URP 2022.3/2023.x mimarileri ve AAA mobil oyun UI gereksinimleri temel alınarak hazırlanmıştır.*
