# Unity URP Mobile Performance & Zero-GC Architecture Guide (2025–2026 Standards)

## Overview
High-performance mobile game development on modern iOS and Android devices (utilizing Apple Silicon, Qualcomm Adreno, and ARM Mali GPUs) requires strict adherence to memory control and rendering pipelines. For real-time, fast-paced genres like endless runners, reaching a consistent 60–120 FPS without thermal throttling or garbage collection (GC) micro-stutters demands zero-allocation runtime code, efficient GPU batching, and high-refresh time-step synchronization.

---

## 1. Zero-GC Memory Patterns

### 1.1 Custom Object Pooling Strategies
Calling `Object.Instantiate()` or `Object.Destroy()` during active gameplay introduces severe heap allocation overhead, fragmenting memory and forcing mono/IL2CPP Garbage Collector sweeps.

#### Native vs. Custom Poolers
While Unity 2021+ provides `UnityEngine.Pool.ObjectPool<T>`, a low-overhead, custom lock-free struct/array pooler optimized for endless runners avoids delegate allocations and internal `HashSet` checks in production release builds.

```csharp
using System;
using UnityEngine;

/// <summary>
/// A zero-allocation, pre-allocated stack-based Object Pool.
/// Designed for high-frequency endless runner spawning (coins, obstacles, traffic).
/// </summary>
public sealed class FastGameObjectPool
{
    private readonly GameObject[] _pool;
    private readonly GameObject _prefab;
    private readonly Transform _parent;
    private int _top;

    public FastGameObjectPool(GameObject prefab, int initialCapacity, Transform parent = null)
    {
        _prefab = prefab;
        _parent = parent;
        _pool = new GameObject[initialCapacity];
        _top = 0;

        for (int i = 0; i < initialCapacity; i++)
        {
            GameObject instance = UnityEngine.Object.Instantiate(_prefab, _parent);
            instance.SetActive(false);
            _pool[_top++] = instance;
        }
    }

    public GameObject Spawn(Vector3 position, Quaternion rotation)
    {
        GameObject instance;
        if (_top > 0)
        {
            instance = _pool[--_top];
        }
        else
        {
            // Fallback expansion - should be avoided by proper pre-allocation sizing
            instance = UnityEngine.Object.Instantiate(_prefab, _parent);
        }

        Transform t = instance.transform;
        t.SetPositionAndRotation(position, rotation);
        instance.SetActive(true);
        return instance;
    }

    public void Despawn(GameObject instance)
    {
        instance.SetActive(false);
        if (_top < _pool.Length)
        {
            _pool[_top++] = instance;
        }
    }
}
```

#### Warm-Up & Pre-Allocation Rules
1. **Pre-instantiate 100% of maximum capacity** during scene loading/warm-up transitions.
2. Disable scene objects via `GameObject.SetActive(false)` rather than reparenting offscreen, avoiding transform matrix recalculations.
3. Reset object state via custom `IResettable` interfaces or lightweight parameter setters instead of calling `GetComponent` on spawn.

---

### 1.2 Structs vs. Classes & Boxing Elimination

#### Heap vs. Stack Allocation
* **Classes (Reference Types):** Allocated on the managed heap. Tracked by the GC. Trigger GC sweep passes when dereferenced.
* **Structs (Value Types):** Allocated on the CPU stack or inline within parent structures. Zero GC overhead when passed correctly.

```csharp
// BAD: Class allocation every frame or event
public class TrafficObstacleState // Heap allocation!
{
    public Vector3 Position;
    public float Speed;
}

// GOOD: Readonly Struct passed by reference
public readonly struct TrafficObstacleData // Stack / Inline Memory
{
    public readonly Vector3 Position;
    public readonly float Speed;

    public TrafficObstacleData(Vector3 position, float speed)
    {
        Position = position;
        Speed = speed;
    }
}
```

#### Pass-by-Reference Modifiers (`ref`, `in`, `out`)
When passing large structs (>16 bytes), passing by value copies bytes across stack frames. Use `in` for read-only references to eliminate copying overhead without heap allocation.

```csharp
public void UpdateVehiclePosition(in TrafficObstacleData data, ref Vector3 currentVelocity)
{
    // Zero copy overhead, zero heap allocation
}
```

#### Eliminating Implicit Boxing
Boxing occurs whenever a value type is implicitly converted to an `object` reference or an interface type.

| Common Boxing Trap | Cause | Zero-GC Solution |
| :--- | :--- | :--- |
| `Debug.Log($"Score: {score}")` | String formatting & boxing `int` | Pre-allocated string buffers or `ZString` |
| `Dictionary<EnumKey, T>` | Default EqualityComparer boxes Enum | Custom `IEqualityComparer<TKey>` or integer keys |
| Interface call on Struct | Casting struct to Interface | Generic constraint: `where T : struct, IComponent` |
| Coroutines `yield return new WaitForSeconds(0.1f)` | Instantiate yield instruction | Cache static instances or use `UniTask` / manual timers |
| Action / Lambda Closures | Capturing local variables in lambda | Static methods or stateful static delegates |

```csharp
// BAD: Delegate capturing local variable creates hidden heap class (closure)
float speedMultiplier = 1.5f;
runnerEvents.OnSpeedChange += () => MultiplySpeed(speedMultiplier);

// GOOD: Pass parameters explicitly or use static delegates
runnerEvents.OnSpeedChange += StaticSpeedHandler;
```

---

### 1.3 NativeArray, C# Job System, & Burst Compiler

Unity's Data-Oriented Technology Stack (DOTS) lower-level primitives allow C# code to allocate memory outside the C# managed heap via `NativeArray<T>`, executing across multiple worker threads with LLVM Burst compilation.

#### Allocation Lifetimes
* `Allocator.Temp`: Ultra-fast stack-like allocation. Single-frame lifetime (must be disposed within 1 frame).
* `Allocator.TempJob`: Fast allocation for background jobs. Maximum 4-frame lifetime.
* `Allocator.Persistent`: Heap-like unmanaged allocation. Must be explicitly freed via `.Dispose()`.

#### High-Performance Burst Job Example
```csharp
using Unity.Burst;
using Unity.Collections;
using Unity.Jobs;
using UnityEngine;

[BurstCompile(CompileSynchronously = true, FloatMode = FloatMode.Fast, FloatPrecision = FloatPrecision.Standard)]
public struct ParallelVehicleMovementJob : IJobParallelFor
{
    [ReadOnly] public NativeArray<Vector3> Directions;
    [ReadOnly] public float DeltaTime;
    [ReadOnly] public float BaseSpeed;
    
    public NativeArray<Vector3> Positions;

    public void Execute(int index)
    {
        Vector3 pos = Positions[index];
        pos += Directions[index] * (BaseSpeed * DeltaTime);
        Positions[index] = pos;
    }
}
```

---

## 2. SRP Batcher & GPU Instancing Rules for Mobile

Mobile GPUs employ **Tile-Based Rendering (TBR)** or **Tile-Based Deferred Rendering (TBDR)**. Minimizing CPU submit overhead and state switches is critical to prevent thermal throttling on devices like Apple A-Series / M-Series, Qualcomm Adreno, and ARM Mali.

```
       +-------------------------------------------------------------+
       |                     RENDER PATH SELECTION                   |
       +-------------------------------------------------------------+
                                      |
                    Are meshes identical and high-count?
                                      |
                     +----------------+----------------+
                     |                                 |
                  [ YES ]                           [ NO ]
                     |                                 |
       +---------------------------+     +---------------------------+
       |       GPU INSTANCING      |     |        SRP BATCHER        |
       |  - Instanced Property Buffers|  - Shared Shader Passes     |
       |  - Single Draw Call       |     |  - Material CBUFFERs      |
       +---------------------------+     +---------------------------+
```

### 2.1 SRP Batcher Mechanics & Requirements

The SRP Batcher reduces CPU render-thread overhead between draw calls by persisting Material data in GPU Constant Buffers (CBUFFERs). Instead of binding material parameters every draw call, the CPU only updates per-draw uniform offsets (`UnityPerDraw`).

#### HLSL Shader CBUFFER Structure Requirements
To make a custom URP shader SRP Batcher compatible:
1. Every material property must be declared inside a single `CBUFFER_START(UnityPerMaterial)` block.
2. Mesh transform properties must be declared inside `CBUFFER_START(UnityPerDraw)`.

```hlsl
Shader "Custom/URPMobileTrafficShader"
{
    Properties
    {
        _BaseMap ("Base Texture", 2D) = "white" {}
        _BaseColor ("Base Color", Color) = (1, 1, 1, 1)
        _Smoothness ("Smoothness", Range(0, 1)) = 0.5
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" }

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode"="UniversalForward" }

            HLSLPROGRAM
            #pragma vertex Vertex
            #pragma fragment Fragment

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            // SRP BATCHER COMPATIBILITY BLOCK
            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;
                half4 _BaseColor;
                half _Smoothness;
            CBUFFER_END

            TEXTURE2D(_BaseMap);
            SAMPLER(sampler_BaseMap);

            struct Attributes
            {
                float4 positionOS : POSITION;
                float2 uv         : TEXCOORD0;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv         : TEXCOORD0;
            };

            Varyings Vertex(Attributes input)
            {
                Varyings output;
                VertexPositionInputs vertexInput = GetVertexPositionInputs(input.positionOS.xyz);
                output.positionCS = vertexInput.positionCS;
                output.uv = TRANSFORM_TEX(input.uv, _BaseMap);
                return output;
            }

            half4 Fragment(Varyings input) : SV_Target
            {
                half4 albedo = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv) * _BaseColor;
                return albedo;
            }
            ENDHLSL
        }
    }
}
```

> **WARNING:** Calling `MaterialPropertyBlock` at runtime breaks SRP Batcher compatibility for that draw call, dropping back to standard draw commands. Use GPU Instancing if per-instance properties via `MaterialPropertyBlock` are mandatory.

---

### 2.2 GPU Instancing Rules & APIs

GPU Instancing renders multiple identical meshes with the same material in a single draw call by passing instance property arrays to the GPU.

#### GPU Instancing Shader Declaration
```hlsl
#pragma multi_compile_instancing

struct Attributes
{
    float4 positionOS : POSITION;
    float2 uv         : TEXCOORD0;
    UNITY_VERTEX_INPUT_INSTANCE_ID
};

struct Varyings
{
    float4 positionCS : SV_POSITION;
    float2 uv         : TEXCOORD0;
    UNITY_VERTEX_INPUT_INSTANCE_ID
};

UNITY_INSTANCING_BUFFER_START(Props)
    UNITY_DEFINE_INSTANCED_PROP(half4, _InstanceColor)
UNITY_INSTANCING_BUFFER_END(Props)

Varyings Vertex(Attributes input)
{
    Varyings output;
    UNITY_SETUP_INSTANCE_ID(input);
    UNITY_TRANSFER_INSTANCE_ID(input, output);

    VertexPositionInputs vertexInput = GetVertexPositionInputs(input.positionOS.xyz);
    output.positionCS = vertexInput.positionCS;
    output.uv = input.uv;
    return output;
}

half4 Fragment(Varyings input) : SV_Target
{
    UNITY_SETUP_INSTANCE_ID(input);
    half4 color = UNITY_ACCESS_INSTANCED_PROP(Props, _InstanceColor);
    return color;
}
```

#### Decision Matrix: SRP Batcher vs. GPU Instancing vs. GPU Resident Drawer (Unity 6+)

| Criterion | SRP Batcher | GPU Instancing | GPU Resident Drawer (Unity 6+) |
| :--- | :--- | :--- | :--- |
| **Primary Goal** | Minimize CPU state switch overhead | Minimize draw call count | Fully GPU-driven culling & draw submission |
| **Mesh Requirement** | Diverse, varied meshes | Identical mesh geometry | Mixed/Varied static & dynamic meshes |
| **Material Requirement**| Shared shader pass (different materials OK) | Exact same material | BatchRendererGroup compatible materials |
| **Best Mobile Use-case** | Entire vehicle traffic, environment assets | Coins, road barriers, trees, foliage | High-density scenes with tens of thousands of instances |

---

### 2.3 Mobile GPU Architecture Nuances (TBDR)

Mobile GPUs process graphics using on-chip Tile Memory (SRAM):

```
       +-------------------------------------------------------------+
       |               TBDR GPU RENDERING PIPELINE                   |
       +-------------------------------------------------------------+
       | 1. Geometry Pass: Tiler processes vertices -> Tile Lists    |
       | 2. Binning: Frame divided into 16x16 / 32x32 pixel tiles    |
       | 3. On-Chip Shading: Rasterize & shade completely inside SRAM|
       | 4. Writeback: Flush finalized tile color buffer to VRAM     |
       +-------------------------------------------------------------+
```

#### Architectural Rules for Mobile Architecture

1. **Precision Modifiers (`half` vs `float`):**
   * Use `half` (16-bit FP) for colors, normals, light vectors, and general calculations.
   * Use `float` (32-bit FP) only for vertex positions and UV coordinates requiring high precision over distance.
   * On Mali and Adreno GPUs, `half` utilizes dual-issue 16-bit ALU pipelines, delivering **2x ALU throughput** and reducing register pressure.

2. **Avoid `clip()` and `discard` in Fragment Shaders:**
   * Apple Silicon (HSR), Qualcomm Adreno (Early-Z), and ARM Mali (Forward Pixel Kill) rely on early depth testing before executing fragment shaders.
   * `discard` / `clip()` disables Early-Z, forcing the GPU to execute pixel shaders for hidden geometry and causing tile buffer stalls.

3. **Minimize Alpha Testing & Overdraw:**
   * Overdraw destroys mobile fill rate. Prefer low-poly geometry cutouts over transparent alpha-tested foliage cards on mobile assets.

---

## 3. Draw Call Reduction & Texture Atlasing for Traffic Runner Assets

To keep total draw calls below **100–150 per frame** on mobile endless runners, geometry and textures must be consolidated.

### 3.1 Sprite & Texture Atlasing vs. Texture Arrays

#### Texture Atlases (Packed UVs)
Packing environment and vehicle textures into single 2048x2048 or 4048x4048 atlases allows multiple environment meshes to share a single material.

* **Mipmap Bleeding Mitigation:** Apply 8px to 16px padding between sub-textures in the atlas to prevent filtering artifacts at low LOD levels.

#### Texture Arrays (`Texture2DArray`)
For advanced custom shaders, 2D Texture Arrays eliminate UV atlas coordinate math and mipmap bleeding entirely:

```hlsl
TEXTURE2D_ARRAY(_TrafficTextures);
SAMPLER(sampler_TrafficTextures);

half4 Fragment(Varyings input, float textureIndex) : SV_Target
{
    // textureIndex selects slice without UV bleeding
    return SAMPLE_TEXTURE2D_ARRAY(_TrafficTextures, sampler_TrafficTextures, input.uv, textureIndex);
}
```

---

### 3.2 Material Variant & Shader Keyword Control

Shader variants explode build sizes and increase render state changes. 

```
                          +-----------------------+
                          |   SHADER KEYWORDS     |
                          +-----------------------+
                                      |
                     +----------------+----------------+
                     |                                 |
        [ #pragma multi_compile ]             [ #pragma shader_feature ]
                     |                                 |
        - All variants compiled into         - Only variants used in scene
          build binary.                        materials compiled.
        - Toggled at runtime via             - Unused variants stripped 
          Global Shader Keywords.              during build.
```

#### Guidelines for Mobile Keyword Budget
* **Limit Global Keywords:** Keep total active keywords per shader pass under 16.
* **Prefer Static Properties over Keywords:** Use parameter multipliers (e.g., `_UseGlossiness` float `0.0` or `1.0`) inside HLSL instead of `#pragma shader_feature _GLOSSINESS_ON` branches to preserve SRP batching across materials.
* **Shared Materials:** Use `Renderer.sharedMaterial` in C# scripts. Accessing `Renderer.material` instantiates a copy of the material on the heap, permanently breaking SRP Batcher pairing.

---

## 4. FixedUpdate vs. Update Time-Step Synchronization for High-Refresh Mobile Screens

Modern mobile devices operate at high refresh rates (90Hz, 120Hz LTPO, 144Hz). A mismatch between the fixed physics tick rate (e.g., 50Hz / 20ms) and the visual frame rate causes micro-stutter (temporal jitter).

```
Display (120Hz):  |---|---|---|---|---|---|---|---|---|---|---|---|  (8.33ms)
Physics (50Hz):   |-------|-------|-------|-------|-------|      (20.0ms)
Render Jitter:    ^   *   ^   *   ^   *   ^   *   ^   *   ^
                  (* Render frame rendered without a physics update tick)
```

---

### 4.1 Physics vs. Render Frame Synchronization

#### Solution A: Rigidbody Interpolation
For physics-driven entities, enable `Rigidbody.interpolation = RigidbodyInterpolation.Interpolate`. Unity automatically stores the previous (`t-1`) and current (`t`) physics states, interpolating the visual transform inside `Update()`:

$$\text{VisualPosition} = \text{Pos}_{t-1} \times (1 - \alpha) + \text{Pos}_t \times \alpha$$

$$\text{where } \alpha = \frac{\text{Time.time} - \text{Time.fixedTime}}{\text{Time.fixedDeltaTime}}$$

#### Solution B: Zero-Allocation Manual Transform Interpolator
For custom non-Rigidbody endless runner movement (e.g., transform-driven track scrolling), implement a manual frame-interpolation wrapper to prevent stutter:

```csharp
using UnityEngine;

/// <summary>
/// Smooths visual movement across high-refresh screens (90Hz/120Hz/144Hz) 
/// when underlying movement logic runs on a fixed time-step.
/// </summary>
public class FixedToRenderInterpolators : MonoBehaviour
{
    private Vector3 _previousPosition;
    private Vector3 _currentPosition;
    private Quaternion _previousRotation;
    private Quaternion _currentRotation;

    public void Initialize(Vector3 startPosition, Quaternion startRotation)
    {
        _previousPosition = _currentPosition = startPosition;
        _previousRotation = _currentRotation = startRotation;
    }

    /// <summary>
    /// Call inside custom FixedUpdate logic loop.
    /// </summary>
    public void TickFixedUpdate(Vector3 nextPosition, Quaternion nextRotation)
    {
        _previousPosition = _currentPosition;
        _previousRotation = _currentRotation;

        _currentPosition = nextPosition;
        _currentRotation = nextRotation;
    }

    /// <summary>
    /// Call inside MonoBehaviour Update() or late render step.
    /// </summary>
    public void TickRenderUpdate(Transform visualTransform)
    {
        float interpolationAlpha = (Time.time - Time.fixedTime) / Time.fixedDeltaTime;
        interpolationAlpha = Mathf.Clamp01(interpolationAlpha);

        visualTransform.position = Vector3.Lerp(_previousPosition, _currentPosition, interpolationAlpha);
        visualTransform.rotation = Quaternion.Slerp(_previousRotation, _currentRotation, interpolationAlpha);
    }
}
```

---

### 4.2 Input Pacing & High-Refresh Frame Pacing

#### Input Collection Rules
1. **Always sample touch/swipe input in `Update()`:** Sampling input inside `FixedUpdate()` risks missing touch events on 120Hz displays when multiple render frames occur between physics ticks.
2. **Buffer input state:** Store input events in lightweight value structs and process them during the subsequent `FixedUpdate()` step.

```csharp
public struct PlayerInputState
{
    public bool LaneSwitchLeftRequested;
    public bool LaneSwitchRightRequested;
    public bool JumpRequested;
}

public class HighRefreshInputManager : MonoBehaviour
{
    private PlayerInputState _bufferedInput;

    private void Update()
    {
        // Sample frame-accurate touch input on 120Hz displays
        if (Input.GetKeyDown(KeyCode.LeftArrow)) 
            _bufferedInput.LaneSwitchLeftRequested = true;
        
        if (Input.GetKeyDown(KeyCode.RightArrow)) 
            _bufferedInput.LaneSwitchRightRequested = true;
    }

    private void FixedUpdate()
    {
        // Process buffered input synchronously with physics
        ProcessMovement(_bufferedInput);
        
        // Clear buffer
        _bufferedInput = default;
    }

    private void ProcessMovement(in PlayerInputState input) { /* Logic */ }
}
```

#### Target Frame Rate & Mobile Swappy Setup
* Set `Application.targetFrameRate = -1` when using Android Swappy / Optimized Frame Pacing or iOS DisplayLink to allow adaptive display synchronization (ProMotion/LTPO).
* Enable **Optimized Frame Pacing** in Unity Android Player Settings to sync frame presentation queues directly with display VSync.

---

## 5. Architectural Checklist for Production

- [ ] **Zero-GC Enforcement:** All in-game spawner pools pre-allocated during loading screen.
- [ ] **No Hidden Allocations:** LINQ removed from `Update()`, strings replaced with cached formats/buffers, physics queries converted to `NonAlloc` methods (`Physics.OverlapSphereNonAlloc`).
- [ ] **SRP Batcher Compatibility:** Custom URP shaders declare properties inside matching `CBUFFER_START(UnityPerMaterial)` blocks; zero runtime `MaterialPropertyBlock` usage on batch-targeted assets.
- [ ] **Mobile Shader Precision:** Fragment shaders utilize `half` precision for vectors and colors; no `clip()` or `discard` statements in opacity passes.
- [ ] **Texture Packing:** Mobile traffic runner assets combined into 2048x2048 ASTC-compressed texture atlases or `Texture2DArray` containers.
- [ ] **120Hz Synchronization:** All moving objects use Rigidbody Interpolation or custom `FixedToRenderInterpolators` blending to eliminate visual micro-stutters.
