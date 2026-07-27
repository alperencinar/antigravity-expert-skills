# URP Curved World Shader & Mobile Rendering Optimization Guide

---

## 1. Executive Summary & Architectural Overview

The **Curved World** effect is an iconic visual technique used in endless runners, stylized arcade racers (e.g., *Subway Surfers*, *Mario Kart Arcade*), and mobile driving games. It simulates a spherical horizon or winding road by deforming vertex positions inside the vertex shader without altering underlying physics meshes or game logic.

In Unity’s **Universal Render Pipeline (URP)**, implementing Curved World presents specific rendering challenges:
- **Shadow Parity**: Modifying geometry in `ForwardLit` without equivalent modification in `ShadowCaster` causes severe shadow detachment and visual popping.
- **Frustum Culling**: CPU culling tests static bounding boxes (`Mesh.bounds` / `Renderer.localBounds`). Deformed geometry near screen edges will pop out of existence when its unbent bounding box leaves the camera frustum.
- **SRP Batcher & GPU Instancing**: Custom shaders must maintain strict `CBUFFER` layout compatibility (`UnityPerMaterial`) to prevent breaking the URP SRP Batcher, which is vital for mobile CPU/GPU throughput.
- **Mobile Light Performance**: Vehicle headlights utilizing URP Additional Lights must be optimized for tile/cluster rendering or per-vertex evaluation on low-end mobile GPUs (Adreno, Mali).

This document establishes the mathematical foundations, HLSL vertex shader implementation, URP pass integration, C# bounds expansion, and mobile optimization strategies for production-grade URP Curved World rendering.

---

## 2. Mathematical Formulation of 2-Axis Curvature

### 2.1 Coordinate Space Selection

Curvature can be calculated in **Object Space**, **View/Camera Space**, or **World Space**:

| Space | Pros | Cons | Decision |
| :--- | :--- | :--- | :--- |
| **Object Space** | Simple matrix transforms | Curvature varies per object rotation; non-uniform scaling distorts curve | ❌ Rejected |
| **View (Camera) Space** | Naturally aligns with camera forward vector | Pitching or rolling the camera rotates the curvature axis | ⚠️ Conditional |
| **World Space** | Consistent global curvature regardless of camera rotation or object transform | Requires world position reconstruction | ✅ **Recommended Standard** |

World-space deformation ensures that all objects bend uniformly relative to the camera's position along the main Z-axis (forward travel direction).

---

### 2.2 Quadratic Formula Derivation

Let $P_{ws} = (x_{ws}, y_{ws}, z_{ws})^T$ be the original vertex position in World Space, and $C_{ws} = (x_{cam}, y_{cam}, z_{cam})^T$ be the main camera position.

#### 1. Distance Metric ($\Delta Z$)
The distance along the primary axis of motion (Z-axis) beyond an optional flat threshold distance $Z_{flat}$:

$$\Delta Z = \max\left(0, (z_{ws} - z_{cam}) - Z_{flat}\right)$$

Alternatively, using Euclidean distance in the XZ plane:

$$D_{xz} = \sqrt{(x_{ws} - x_{cam})^2 + (z_{ws} - z_{cam})^2}$$
$$\Delta Z = \max\left(0, D_{xz} - Z_{flat}\right)$$

For forward-facing endless racers, $(z_{ws} - z_{cam})$ is computationally cheaper (1 subtraction vs 1 square root).

#### 2. Y-Downward Curvature (Vertical Horizon Bending)
Vertical curvature depresses vertices downward as distance increases using a parabolic quadratic relation:

$$\Delta Y = K_y \cdot (\Delta Z)^2$$
$$y'_{ws} = y_{ws} - \Delta Y = y_{ws} - K_y \cdot (\Delta Z)^2$$

Where $K_y$ is the vertical curvature coefficient (typically $10^{-4}$ to $10^{-3}$).

#### 3. X-Lateral Curvature (Horizontal Road Winding)
Horizontal curvature shifts vertices laterally left or right to simulate winding tracks:

$$\Delta X = K_x \cdot (\Delta Z)^2$$
$$x'_{ws} = x_{ws} + \Delta X = x_{ws} + K_x \cdot (\Delta Z)^2$$

Where $K_x$ is the lateral curvature coefficient (positive bends right, negative bends left).

#### 4. Combined 2-Axis Deformed Position
$$P'_{ws} = \begin{pmatrix} x_{ws} + K_x \cdot \max\left(0, z_{ws} - z_{cam} - Z_{flat}\right)^2 \\ y_{ws} - K_y \cdot \max\left(0, z_{ws} - z_{cam} - Z_{flat}\right)^2 \\ z_{ws} \end{pmatrix}$$

---

### 2.3 HLSL Core Implementation (`CurvedWorld.hlsl`)

Save the following file at `Assets/Shaders/Include/CurvedWorld.hlsl`:

```hlsl
#ifndef CURVED_WORLD_INCLUDED
#define CURVED_WORLD_INCLUDED

// Uniforms must reside inside UnityPerMaterial or global buffer for SRP Batcher compatibility
CBUFFER_START(CurvedWorldParams)
    float _CurveY;
    float _CurveX;
    float _CurveOffset;
CBUFFER_END

// Fallback uniform declarations if not using CBUFFER
#ifndef CurvedWorldParams
    uniform float _CurveY;
    uniform float _CurveX;
    uniform float _CurveOffset;
#endif

/// <summary>
/// Applies 2-axis (Y-downward, X-lateral) world-space curvature to a vertex position.
/// </summary>
/// <param name="positionWS">In/Out World Space position of vertex</param>
inline void ApplyCurvedWorld(inout float3 positionWS)
{
    // Compute distance relative to camera along world Z-axis
    float dist = positionWS.z - _WorldSpaceCameraPos.z - _CurveOffset;
    
    // Apply curvature only ahead of the curvature offset distance
    dist = max(0.0, dist);
    float distSq = dist * dist;

    // Apply quadratic offsets
    positionWS.y -= _CurveY * distSq;
    positionWS.x += _CurveX * distSq;
}

/// <summary>
/// Helper function to transform Object Space vertex position to HClip with Curvature applied.
/// </summary>
float4 TransformObjectToHClipCurved(float3 positionOS)
{
    float3 positionWS = TransformObjectToWorld(positionOS);
    ApplyCurvedWorld(positionWS);
    return TransformWorldToHClip(positionWS);
}

#endif // CURVED_WORLD_INCLUDED
```

---

### 2.4 Camera Movement & Pitch Origin Handling

When the camera tilts up or down (pitch), world-space Z distance remains unchanged, but visual perspective can distort if curvature originates behind or directly at the camera pivot.

To prevent visual artifacts:
1. **Set `_CurveOffset`**: Keep curvature flat for $10-15$ meters in front of the vehicle so the immediate road plane near the car retains accurate contact shadows and alignment.
2. **Camera Rotation Independence**: By using `positionWS.z - _WorldSpaceCameraPos.z`, camera pitch/yaw changes will not distort the global curvature axis.

---

## 3. URP Pass Parity & Shadow Mapping (`ForwardLit` & `ShadowCaster`)

### 3.1 The Dynamic Shadow Disconnect Problem

In URP, dynamic shadow maps are rendered via the `ShadowCaster` pass from the perspective of light sources (e.g., Directional Sun Light or Local Spotlights).

If `ApplyCurvedWorld` is applied **only** in the `ForwardLit` pass:
1. The camera sees the mesh bent downwards in `ForwardLit`.
2. The directional light renders the shadow map using the **unbent** mesh in `ShadowCaster`.
3. **Result**: Shadows float in mid-air above bent meshes or detach completely from vehicles and environment structures.

```
       [Sun Light]
           \
            \ Unbent Shadow Position (ShadowCaster)
             v  [Floating Shadow]
  -----------------------------  <-- Ground Level
           \
            \ Bent Geometry Position (ForwardLit)
             v
```

**Rule**: *Every pass that reads vertex position data (`ForwardLit`, `ShadowCaster`, `DepthOnly`, `DepthNormals`, `Meta`) MUST apply identical vertex displacement logic before clipping.*

---

### 3.2 HLSL Pass Integration Strategy

#### `ForwardLit` Vertex Pass
```hlsl
Varyings VertexForwardLit(Attributes input)
{
    Varyings output = (Varyings)0;

    UNITY_SETUP_INSTANCE_ID(input);
    UNITY_TRANSFER_INSTANCE_ID(input, output);
    UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(output);

    // 1. Transform to World Space
    VertexPositionInputs vertexInput = GetVertexPositionInputs(input.positionOS);
    float3 positionWS = vertexInput.positionWS;

    // 2. Apply World Curvature
    ApplyCurvedWorld(positionWS);

    // 3. Output transformed clip and world positions
    output.positionCS = TransformWorldToHClip(positionWS);
    output.positionWS = positionWS;
    
    // Normal / Tangent transformations
    VertexNormalInputs normalInput = GetVertexNormalInputs(input.normalOS, input.tangentOS);
    output.normalWS = TransformObjectToWorldNormal(input.normalOS);
    
    return output;
}
```

#### `ShadowCaster` Vertex Pass (With Shadow Bias)
```hlsl
Varyings VertexShadowCaster(Attributes input)
{
    Varyings output;
    UNITY_SETUP_INSTANCE_ID(input);
    UNITY_TRANSFER_INSTANCE_ID(input, output);

    // 1. Transform to World Space
    float3 positionWS = TransformObjectToWorld(input.positionOS);

    // 2. Apply World Curvature
    ApplyCurvedWorld(positionWS);

    // 3. Transform Normal to World Space
    float3 normalWS = TransformObjectToWorldNormal(input.normalOS);

    // 4. Apply URP Shadow Bias in World Space
    #if defined(APPLY_WORLD_SPACE_SHADOW_BIAS)
        positionWS = ApplyShadowBias(positionWS, normalWS, _LightDirection);
    #endif

    // 5. Transform to Shadow Clip Space
    output.positionCS = TransformWorldToHClip(positionWS);

    #if UNITY_REVERSED_Z
        output.positionCS.z = min(output.positionCS.z, UNITY_NEAR_CLIP_VALUE);
    #else
        output.positionCS.z = max(output.positionCS.z, UNITY_NEAR_CLIP_VALUE);
    #endif

    return output;
}
```

---

### 3.3 Complete Production URP Custom Shader (`CurvedWorldURPLit.shader`)

Below is a production-ready URP Lit shader supporting `ForwardLit` and `ShadowCaster` pass parity:

```hlsl
Shader "Custom/URP_CurvedWorld_Lit"
{
    Properties
    {
        [MainTexture] _BaseMap("Base Map", 2D) = "white" {}
        [MainColor] _BaseColor("Base Color", Color) = (1,1,1,1)
        _Smoothness("Smoothness", Range(0, 1)) = 0.5
        _Metallic("Metallic", Range(0, 1)) = 0.0
        
        [Header(Curved World Settings)]
        _CurveY("Curve Y (Downward)", Float) = 0.0005
        _CurveX("Curve X (Lateral)", Float) = 0.0
        _CurveOffset("Curve Offset", Float) = 10.0
    }

    SubShader
    {
        Tags 
        { 
            "RenderType" = "Opaque" 
            "RenderPipeline" = "UniversalPipeline" 
            "Queue" = "Geometry"
        }
        LOD 300

        // ------------------------------------------------------------------
        // ForwardLit Pass
        // ------------------------------------------------------------------
        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }

            HLSLPROGRAM
            #pragma vertex VertexForwardLit
            #pragma fragment FragmentForwardLit

            // URP Keywords
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile _ _ADDITIONAL_LIGHT_SHADOWS
            #pragma multi_compile_fragment _ _SHADOWS_SOFT
            #pragma multi_compile_instancing

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            #include "Assets/Shaders/Include/CurvedWorld.hlsl"

            struct Attributes
            {
                float4 positionOS   : POSITION;
                float3 normalOS     : NORMAL;
                float2 uv           : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS   : SV_POSITION;
                float3 positionWS   : TEXCOORD0;
                float3 normalWS     : TEXCOORD1;
                float2 uv           : TEXCOORD2;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            TEXTURE2D(_BaseMap);
            SAMPLER(sampler_BaseMap);

            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;
                half4 _BaseColor;
                half _Smoothness;
                half _Metallic;
                float _CurveY;
                float _CurveX;
                float _CurveOffset;
            CBUFFER_END

            Varyings VertexForwardLit(Attributes input)
            {
                Varyings output = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_TRANSFER_INSTANCE_ID(input, output);

                float3 positionWS = TransformObjectToWorld(input.positionOS.xyz);
                ApplyCurvedWorld(positionWS);

                output.positionCS = TransformWorldToHClip(positionWS);
                output.positionWS = positionWS;
                output.normalWS = TransformObjectToWorldNormal(input.normalOS);
                output.uv = TRANSFORM_TEX(input.uv, _BaseMap);

                return output;
            }

            half4 FragmentForwardLit(Varyings input) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(input);

                half4 albedo = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv) * _BaseColor;
                
                InputData inputData = (InputData)0;
                inputData.positionWS = input.positionWS;
                inputData.normalWS = normalize(input.normalWS);
                inputData.shadowCoord = TransformWorldToShadowCoord(input.positionWS);

                SurfaceData surfaceData = (SurfaceData)0;
                surfaceData.albedo = albedo.rgb;
                surfaceData.alpha = albedo.a;
                surfaceData.metallic = _Metallic;
                surfaceData.smoothness = _Smoothness;

                return UniversalFragmentPBR(inputData, surfaceData);
            }
            ENDHLSL
        }

        // ------------------------------------------------------------------
        // ShadowCaster Pass
        // ------------------------------------------------------------------
        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode" = "ShadowCaster" }

            ZWrite On
            ZTest LEqual
            ColorMask 0

            HLSLPROGRAM
            #pragma vertex VertexShadowCaster
            #pragma fragment FragmentShadowCaster
            #pragma multi_compile_instancing

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Shadows.hlsl"
            #include "Assets/Shaders/Include/CurvedWorld.hlsl"

            struct Attributes
            {
                float4 positionOS   : POSITION;
                float3 normalOS     : NORMAL;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS   : SV_POSITION;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            float3 _LightDirection;

            Varyings VertexShadowCaster(Attributes input)
            {
                Varyings output = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_TRANSFER_INSTANCE_ID(input, output);

                float3 positionWS = TransformObjectToWorld(input.positionOS.xyz);
                ApplyCurvedWorld(positionWS);

                float3 normalWS = TransformObjectToWorldNormal(input.normalOS);
                positionWS = ApplyShadowBias(positionWS, normalWS, _LightDirection);

                output.positionCS = TransformWorldToHClip(positionWS);

                #if UNITY_REVERSED_Z
                    output.positionCS.z = min(output.positionCS.z, UNITY_NEAR_CLIP_VALUE);
                #else
                    output.positionCS.z = max(output.positionCS.z, UNITY_NEAR_CLIP_VALUE);
                #endif

                return output;
            }

            half4 FragmentShadowCaster(Varyings input) : SV_Target
            {
                return 0;
            }
            ENDHLSL
        }
    }
}
```

---

## 4. CPU Frustum Culling & Bounds Expansion

### 4.1 Root Cause of Disappearing Meshes

Unity’s CPU culling pipeline tests an object’s bounding box (`Renderer.bounds`) against the camera’s 6 frustum planes **before** rendering.

```
       [Camera Frustum Top Plane]
      /                            \
     /   [Mesh Original AABB]       \   <-- CPU test passes
    /            |                   \
   /             v (Bent by Vertex Shader)
  /       [Deformed Mesh]             \ <-- Still inside frustum
 /                                     \
------------------------------------------------- [Camera Bottom Plane]
               |
               v (Farther Object)
   [Mesh Original AABB Out of Frustum] <-- CPU Culls Object!
               |
               v (Bent Geometry SHOULD be visible in frame bottom)
          -> DISAPPEARS INSTANTLY! <-
```

When geometry is bent downwards or sideways in the GPU vertex shader:
1. The CPU is unaware of GPU vertex shader displacement.
2. An object far away has an unbent AABB that exits the top or side frustum plane.
3. The CPU culls the renderer, causing visible objects to instantly vanish from the screen.

---

### 4.2 Mathematical Bound Expansion Calculation

To prevent CPU culling artifacts, we must expand `Mesh.bounds` or `Renderer.localBounds` on the CPU by the maximum possible vertex displacement $\Delta Y_{max}$ and $\Delta X_{max}$.

#### Maximum Vertical Expansion ($\Delta Y_{max}$)
For a camera far clipping plane $Z_{far}$ (e.g. 150m):

$$\Delta Y_{max} = K_y \cdot (Z_{far} - Z_{offset})^2$$

*Example*: If $K_y = 0.0005$, $Z_{far} = 150$, $Z_{offset} = 10$:
$$\Delta Y_{max} = 0.0005 \cdot (140)^2 = 0.0005 \cdot 19600 = 9.8 \text{ meters}$$

#### Bounds Expansion Vector
The bounding box local size must extend:
- **Y axis**: Extend lower bound down by $\Delta Y_{max}$.
- **X axis**: Extend left/right bounds by $\Delta X_{max} = K_x \cdot (Z_{far} - Z_{offset})^2$.

---

### 4.3 Production C# Script (`CurvedWorldBoundsExpander.cs`)

Attach this component to environmental prefabs, terrain blocks, or road segments:

```csharp
using UnityEngine;

namespace Cardiv.Rendering
{
    [ExecuteAlways]
    [RequireComponent(typeof(MeshFilter))]
    public class CurvedWorldBoundsExpander : MonoBehaviour
    {
        [Header("Curvature Parameters (Must match Shader)")]
        [SerializeField] private float _curveY = 0.0005f;
        [SerializeField] private float _curveX = 0.0000f;
        [SerializeField] private float _curveOffset = 10.0f;
        [SerializeField] private float _maxDistance = 150.0f;

        [Header("Padding Margin")]
        [SerializeField] private float _safetyMarginMultiplier = 1.25f;

        private Mesh _instancedMesh;

        private void OnEnable()
        {
            ExpandBounds();
        }

        private void OnValidate()
        {
            ExpandBounds();
        }

        [ContextMenu("Recompute Bounds")]
        public void ExpandBounds()
        {
            MeshFilter meshFilter = GetComponent<MeshFilter>();
            if (meshFilter == null || meshFilter.sharedMesh == null) return;

            // Instantiate a fresh mesh reference to prevent overwriting asset on disk
            if (Application.isPlaying)
            {
                _instancedMesh = meshFilter.mesh;
            }
            else
            {
                // In edit mode, create copy for display
                _instancedMesh = Instantiate(meshFilter.sharedMesh);
                meshFilter.sharedMesh = _instancedMesh;
            }

            // Calculate max displacements
            float effectiveDist = Mathf.Max(0f, _maxDistance - _curveOffset);
            float distSq = effectiveDist * effectiveDist;

            float maxOffsetY = _curveY * distSq * _safetyMarginMultiplier;
            float maxOffsetX = _curveX * distSq * _safetyMarginMultiplier;

            // Get original bounds
            Bounds orig = _instancedMesh.bounds;

            // Compute expanded bounds center and size
            Vector3 center = orig.center;
            Vector3 size = orig.size;

            // Shift center down by half maxOffsetY, increase size by maxOffsetY
            center.y -= maxOffsetY * 0.5f;
            size.y += maxOffsetY;

            // Expand X size symmetrically
            size.x += maxOffsetX * 2.0f;

            // Re-assign expanded bounds
            _instancedMesh.bounds = new Bounds(center, size);
        }
    }
}
```

---

### 4.4 Occlusion Culling & Performance Considerations

- **Unity Occlusion Culling**: Hardware/Bake Occlusion Culling (Umbra) uses static scene geometry. Because curved world distorts spatial occluder relationships, **baked Occlusion Culling should be disabled** for curved world scenes.
- **Frustum Culling Overhead**: Expanding mesh bounds slightly increases the number of rendered draw calls by keeping distant meshes in the frustum longer. This is intentional and necessary for visual completeness.

---

## 5. URP Lighting, SRP Batcher & Mobile GPU Optimization

### 5.1 Vehicle Headlights & URP Additional Lights Configuration

Mobile racing games rely heavily on vehicle headlights (Spot Lights) and streetlights (Point Lights).

#### URP Light Rendering Modes
1. **Per-Pixel Additional Lights**: High visual quality, but expensive on mobile GPUs when multiple light cones overlap.
2. **Per-Vertex Additional Lights**: Calculates lighting in the vertex shader. **Extremely fast** for mobile, ideal for streetlights and environment props.
3. **Forward+ Rendering Path (URP 14+ / Unity 2022.3+)**: Uses tiled/clustered light grid allocations on GPU. Supports hundreds of lights with minimal overhead compared to standard Forward additional light passes.

#### Recommended URP Asset Settings for Mobile
- **Additional Lights**: Set to `Per Pixel` (Limit: 4) or `Forward+`.
- **Additional Light Shadows**: Disable for low-end mobile; enable for High tier (`Shadow Atlas Resolution`: 1024x1024).
- **Spot Light Headlights**: Use custom projected textures or light cookie billboards on low-end devices instead of realtime shadow-casting spot lights.

---

### 5.2 SRP Batcher Compatibility Rules

The **SRP Batcher** reduces CPU draw call submission overhead by persisting material data in GPU VRAM across frames.

To ensure custom HLSL Curved World shaders are **SRP Batcher Compatible**:

1. **Strict `CBUFFER` Layout**: All material properties MUST be enclosed inside `CBUFFER_START(UnityPerMaterial)` and `CBUFFER_END`.
2. **Identical Buffer Order**: Do not declare uniforms outside the `UnityPerMaterial` block.
3. **Check Shader Inspector**: In Unity, select the shader file and verify that the Inspector reads:
   > `SRP Batcher: Compatible`

```hlsl
// ✅ SRP BATCHER COMPATIBLE
CBUFFER_START(UnityPerMaterial)
    float4 _BaseMap_ST;
    half4 _BaseColor;
    half _Smoothness;
    half _Metallic;
    float _CurveY;
    float _CurveX;
    float _CurveOffset;
CBUFFER_END
```

---

### 5.3 GPU Instancing Integration

For repetitive scene elements (trees, light poles, road barriers), **GPU Instancing** merges identical meshes into a single draw call.

```hlsl
#pragma multi_compile_instancing

struct Attributes
{
    float4 positionOS : POSITION;
    UNITY_VERTEX_INPUT_INSTANCE_ID
};

struct Varyings
{
    float4 positionCS : SV_POSITION;
    UNITY_VERTEX_INPUT_INSTANCE_ID
};

Varyings vert(Attributes input)
{
    Varyings output;
    UNITY_SETUP_INSTANCE_ID(input);
    UNITY_TRANSFER_INSTANCE_ID(input, output);

    float3 positionWS = TransformObjectToWorld(input.positionOS.xyz);
    ApplyCurvedWorld(positionWS);

    output.positionCS = TransformWorldToHClip(positionWS);
    return output;
}
```

---

### 5.4 Mobile Architecture Optimization Matrix

| GPU Architecture | Target Devices | Recommended Settings | Key Bottlenecks |
| :--- | :--- | :--- | :--- |
| **ARM Mali (Midgard/Bifrost)** | Low-end Android | - Per-Vertex Additional Lights<br>- Max 1 Main Directional Light Shadow<br>- Flat Texture Splatting | Bandwidth & Fragment ALU |
| **ARM Mali (Valhall)** | Mid-tier Android | - Forward+ Light Pipeline<br>- 4x MSAA<br>- Curved World Lit Shader | Tile Memory Spill |
| **Qualcomm Adreno 6xx/7xx** | Mid/High Android | - Per-Pixel Spot Headlights<br>- Soft Shadows enabled<br>- SRP Batching active | Driver Overhead (Solved by SRP Batcher) |
| **Apple Silicon (A13+)** | iOS Devices | - Full Forward+ Lighting<br>- High Resolution Cascades<br>- Post-Processing (Bloom/Color Grading) | Minimal (Highly Optimized TBDR) |

#### Instruction Cost Analysis of `ApplyCurvedWorld`
- 1 Subtraction (`positionWS.z - _WorldSpaceCameraPos.z`)
- 1 `max(0, d)` (1 ALU cycle)
- 1 Multiplication (`dist * dist`)
- 2 Multiply-Subtract/Add (`MAD` instructions)
- **Total Overhead**: ~5 ALU instructions per vertex. Negligible on all modern mobile GPUs.

---

## 6. Production Implementation & Verification Checklist

- [ ] **HLSL Include**: `CurvedWorld.hlsl` created and placed under `Assets/Shaders/Include/`.
- [ ] **Pass Parity**: Verified that `ApplyCurvedWorld` is called inside both `ForwardLit` and `ShadowCaster` vertex stages.
- [ ] **Shadow Bias**: Confirmed `ApplyShadowBias` is executed **after** vertex deformation in `ShadowCaster`.
- [ ] **SRP Batcher**: Checked Shader Inspector to ensure `SRP Batcher: Compatible` is active.
- [ ] **Bounds Expansion**: Added `CurvedWorldBoundsExpander.cs` to environment prefabs and verified meshes do not pop out at screen boundaries.
- [ ] **Lighting Validation**: Tested vehicle headlights in URP using Forward+ or max 4 per-pixel additional lights.
- [ ] **Mobile Profiling**: Profiled draw call counts with RenderDoc / Xcode Frame Capture to confirm SRP Batching and GPU Instancing performance.

---
*Documented for URP 12+ / 14+ / 17+ Mobile Rendering Standard.*
