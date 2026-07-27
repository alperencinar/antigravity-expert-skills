# Mobile Runner Camera Juicing, Screenshake & Dynamic Camera Behavior

High-speed mobile endless runners rely heavily on camera feedback to communicate speed, weight, lateral momentum, and impact urgency. When camera movement is static or rigid, movement feels flat. Conversely, excessive or poorly damped camera motion causes motion sickness and degrades frame rates on mobile GPUs/CPUs.

This guide provides deep technical synthesis, mathematical foundations, and production-ready Unity C# implementations for mobile camera juicing—including dynamic FOV warping, trauma-based screenshake, impact hitstop, and responsive lane-switching banking.

---

## 1. Dynamic Speed FOV Stretching & Smooth Lerp Math

### 1.1 Mathematical Formulation
Field of View (FOV) expansion visually simulates speed perception through radial optic flow distortion (tunnel vision / motion warp).

#### Linear FOV Speed Formula
At its simplest, camera FOV scales linearly with player velocity magnitude ($V_{\text{player}}$):

$$FOV_{\text{target}} = FOV_{\text{base}} + k \cdot V_{\text{player}}$$

Where:
- $FOV_{\text{base}}$ is the resting Field of View at base speed (e.g., $60^\circ$).
- $k$ is the speed scaling coefficient.
- $V_{\text{player}}$ is the current forward velocity ($m/s$).

#### Bounded Normalized Interpolation
To prevent visual artifacts or camera clipping at hyper-speeds, clamp velocity into a normalized $[0, 1]$ ratio using `InverseLerp` and interpolate between min/max FOV bounds:

$$t_{\text{speed}} = \text{Clamp01}\left( \frac{V_{\text{player}} - V_{\text{min}}}{V_{\text{max}} - V_{\text{min}}} \right)$$

$$FOV_{\text{target}} = FOV_{\text{min}} + (FOV_{\text{max}} - FOV_{\text{min}}) \cdot f(t_{\text{speed}})$$

Where $f(t)$ is an easing function (e.g., quadratic smoothstep $3t^2 - 2t^3$ or an `AnimationCurve`) that provides progressive FOV expansion during nitro/speed boosts.

```
  FOV (deg)
    90 |                                      /---------- (FOV_max)
       |                                    /
       |                                  /  <-- Non-linear / Eased Stretch
    60 |--------------------------------- (FOV_base)
       +-------------------------------------------------->
       0                              V_min           V_max    Player Speed (m/s)
```

---

### 1.2 SmoothDamp vs. Exponential Lerp for Frame-Rate Independence

Interpolating FOV in `LateUpdate()` must remain strictly frame-rate independent across 30 FPS, 60 FPS, and 120 FPS display panels.

#### Linear Interpolation (`Mathf.Lerp`)
Standard `Mathf.Lerp(current, target, rate * Time.deltaTime)` is frame-rate dependent because the decay constant varies with step size. To make exponential decay frame-rate invariant, use exact exponential dampening:

$$FOV(t + \Delta t) = FOV_{\text{target}} + (FOV(t) - FOV_{\text{target}}) \cdot e^{-\lambda \cdot \Delta t}$$

In C#:
```csharp
// Exact frame-rate independent smooth lerp factor
float lerpFactor = 1f - Mathf.Exp(-speedDamping * Time.deltaTime);
currentFOV = Mathf.Lerp(currentFOV, targetFOV, lerpFactor);
```

#### Critically Damped Spring (`Mathf.SmoothDamp`)
`Mathf.SmoothDamp` uses a critically damped spring-mass model. It eliminates overshooting while maintaining continuous acceleration and velocity, providing natural inertia when braking or boosting.

$$x(t) = (A + B t) e^{-\omega t}$$

---

### 1.3 Production C# Implementation: `DynamicRunnerFOV.cs`

```csharp
using UnityEngine;

[DisallowMultipleComponent]
[RequireComponent(typeof(Camera))]
public class DynamicRunnerFOV : MonoBehaviour
{
    [Header("Speed Thresholds")]
    [SerializeField] private float minSpeed = 10f;
    [SerializeField] private float maxSpeed = 35f;

    [Header("FOV Bounds (Degrees)")]
    [SerializeField] private float baseFOV = 60f;
    [SerializeField] private float maxFOV = 88f;

    [Header("Smoothing")]
    [Tooltip("Time to reach target FOV during speed transitions.")]
    [SerializeField] private float smoothTime = 0.2f;

    [Header("Easing Curve")]
    [SerializeField] private AnimationCurve speedCurve = AnimationCurve.EaseInOut(0f, 0f, 1f, 1f);

    private Camera targetCamera;
    private float currentVelocity;
    private float targetFOV;

    private void Awake()
    {
        targetCamera = GetComponent<Camera>();
        targetFOV = baseFOV;
        targetCamera.fieldOfView = baseFOV;
    }

    /// <summary>
    /// Call this from your player controller or camera update manager.
    /// </summary>
    public void UpdateFOV(float currentSpeed)
    {
        // 1. Calculate normalized speed ratio [0, 1]
        float speedRatio = Mathf.Clamp01(Mathf.InverseLerp(minSpeed, maxSpeed, currentSpeed));

        // 2. Evaluate custom easing curve
        float easedRatio = speedCurve.Evaluate(speedRatio);

        // 3. Determine target FOV
        targetFOV = Mathf.Lerp(baseFOV, maxFOV, easedRatio);

        // 4. Critically damped smoothing to eliminate frame rate dependency
        targetCamera.fieldOfView = Mathf.SmoothDamp(
            targetCamera.fieldOfView,
            targetFOV,
            ref currentVelocity,
            smoothTime,
            Mathf.Infinity,
            Time.deltaTime
        );
    }
}
```

---

## 2. Screenshake Algorithms: Perlin Noise vs. Harmonic Decay

Screenshake communicates physical weight during obstacle collisions, near-miss triggers, and explosions. Simple uniform random displacement (`Random.insideUnitSphere`) produces jittery, erratic camera movement that degrades visual readability. Modern juicing relies on **Trauma-Based Perlin Noise** or **Harmonic Damped Sine Oscillations**.

```
                           SCREENSHAKE ALGORITHM COMPARISON
 ┌─────────────────────────────────────────┬─────────────────────────────────────────┐
 │       Perlin Noise Oscillations         │       Harmonic Damped Oscillations      │
 ├─────────────────────────────────────────┼─────────────────────────────────────────┤
 │ • Smooth, organic, continuous rumble    │ • Sharp impulse with exponential decay  │
 │ • Ideal for continuous surface vibration│ • Ideal for instantaneous hard impacts  │
 │ • Multi-frequency 2D/3D noise sampling │ • Trigonometric math (Sin/Cos * e^-λt)  │
 │ • Non-repetitive procedural paths      │ • Predictable directional spring recoil │
 └─────────────────────────────────────────┴─────────────────────────────────────────┘
```

---

### 2.1 The Trauma Model

Introduced by squirrel eiserloh (GDC 2016), the **Trauma Model** models shake stress as a scalar quantity $T \in [0, 1]$.

#### Non-Linear Power Mapping
Mapping shake intensity directly to trauma ($Intensity = T$) makes small hits feel overly dominant. Elevating trauma to a power ($T^2$ or $T^3$) provides high control contrast: minor near-misses produce subtle movement, while hard crashes produce violent recoil.

$$\text{Shake Intensity} = S(T) = T^p \quad (p \approx 2.0 \text{ to } 3.0)$$

#### Exponential Decay
Trauma decays continuously over time:

$$\frac{dT}{dt} = -\delta_{\text{decay}} \implies T(t) = \max\left(0, T_0 - \delta_{\text{decay}} \cdot \Delta t\right)$$

```
 Trauma (T)
  1.0 |*\
      |  \  (T^2 Mapping amplifies initial impact)
  0.5 |   \
      |    \*---\
  0.0 +-------------------------> Time (s)
      0.0   0.1  0.2  0.3  0.4
```

---

### 2.2 Perlin Noise vs. Harmonic Decay Math

#### Perlin Noise Shake Formula
Offset coordinates are sampled along procedural noise tracks over time $t$ using unique seed coordinates:

$$\text{Offset}_X = \text{MaxTranslation}_X \cdot S(T) \cdot \left( 2 \cdot \text{Noise}(\text{seed}_x, f \cdot t) - 1 \right)$$

$$\text{Pitch}_{\text{rot}} = \text{MaxAngle}_{\text{pitch}} \cdot S(T) \cdot \left( 2 \cdot \text{Noise}(\text{seed}_{\text{pitch}}, f \cdot t) - 1 \right)$$

#### Harmonic Damped Sine Oscillations
For sharp directional hits (e.g., clipped on the right wing), a spring-damped oscillator provides immediate directional impact followed by decaying back-and-forth settlement:

$$x(t) = A \cdot e^{-\gamma t} \cdot \cos(\omega t + \phi)$$

Where $\gamma$ is the damping coefficient and $\omega$ is the oscillation frequency.

---

### 2.3 Production C# Implementation: `RunnerCameraShake.cs`

```csharp
using UnityEngine;

public class RunnerCameraShake : MonoBehaviour
{
    [Header("Trauma Settings")]
    [Range(0f, 1f)] private float trauma;
    [SerializeField] private float traumaDecayRate = 1.5f;
    [SerializeField] private float traumaExponent = 2f;

    [Header("Translational Shake Max Bounds")]
    [SerializeField] private Vector3 maxTranslationOffset = new Vector3(0.5f, 0.5f, 0.2f);

    [Header("Rotational Shake Max Bounds (Degrees)")]
    [SerializeField] private Vector3 maxAngularOffset = new Vector3(4f, 4f, 6f);

    [Header("Noise Frequencies")]
    [SerializeField] private float frequency = 25f;

    private float noiseSeedX;
    private float noiseSeedY;
    private float noiseSeedZ;
    private float noiseSeedRoll;

    private void Awake()
    {
        noiseSeedX = Random.Range(0f, 100f);
        noiseSeedY = Random.Range(100f, 200f);
        noiseSeedZ = Random.Range(200f, 300f);
        noiseSeedRoll = Random.Range(300f, 400f);
    }

    /// <summary>
    /// Add trauma stress [0, 1]. Clamped to max 1.0.
    /// </summary>
    public void AddTrauma(float amount)
    {
        trauma = Mathf.Clamp01(trauma + amount);
    }

    /// <summary>
    /// Calculate current combined offset vectors. Call in LateUpdate.
    /// </summary>
    public void CalculateShake(out Vector3 positionOffset, out Quaternion rotationOffset)
    {
        if (trauma <= 0f)
        {
            positionOffset = Vector3.zero;
            rotationOffset = Quaternion.identity;
            return;
        }

        // 1. Calculate non-linear shake magnitude
        float shakeFactor = Mathf.Pow(trauma, traumaExponent);
        float timeStep = Time.unscaledTime * frequency; // Use unscaledTime so shake continues during Hitstop!

        // 2. Sample Perlin noise [-1, 1] range
        float offsetX = (Mathf.PerlinNoise(noiseSeedX, timeStep) * 2f - 1f) * maxTranslationOffset.x * shakeFactor;
        float offsetY = (Mathf.PerlinNoise(noiseSeedY, timeStep) * 2f - 1f) * maxTranslationOffset.y * shakeFactor;
        float offsetZ = (Mathf.PerlinNoise(noiseSeedZ, timeStep) * 2f - 1f) * maxTranslationOffset.z * shakeFactor;

        positionOffset = new Vector3(offsetX, offsetY, offsetZ);

        // 3. Sample Angular offsets
        float pitch = (Mathf.PerlinNoise(noiseSeedY, timeStep + 10f) * 2f - 1f) * maxAngularOffset.x * shakeFactor;
        float yaw   = (Mathf.PerlinNoise(noiseSeedX, timeStep + 20f) * 2f - 1f) * maxAngularOffset.y * shakeFactor;
        float roll  = (Mathf.PerlinNoise(noiseSeedRoll, timeStep + 30f) * 2f - 1f) * maxAngularOffset.z * shakeFactor;

        rotationOffset = Quaternion.Euler(pitch, yaw, roll);

        // 4. Decay Trauma over unscaled delta time
        trauma = Mathf.Clamp01(trauma - traumaDecayRate * Time.unscaledDeltaTime);
    }
}
```

---

## 3. Impact Hitstop / Frame-Freeze (Micro TimeScale Pause)

### 3.1 Cinematic Impact Weight & Human Perception
Hitstop (or frame-freeze) pauses simulation execution for a micro-duration ($0.03\text{s} - 0.08\text{s}$ or $2 - 5$ frames at 60 FPS) upon hitting an obstacle. This brief pause gives the human eye time to register collision contact, magnifying perceived physical weight without breaking gameplay flow.

```
 Normal Gameplay (timeScale = 1.0)
 ───► Collision Event
       ├──► Hitstop Freeze (timeScale = 0.0f or 0.05f) ───► 0.05s Duration
       │     └─► Camera Shake samples Time.unscaledTime (Active Shake)
       └──► Smooth Ease-out Unfreeze ───► Resume Normal Speed
```

---

### 3.2 Global TimeScale vs. Selective Entity Pause

| Approach | Mechanics | Advantages | Disadvantages / Mobile Risks |
| :--- | :--- | :--- | :--- |
| **Global `Time.timeScale = 0`** | Modifies global engine time. Coroutines require `WaitForSecondsRealtime`. | Pauses entire physics/animation ecosystem seamlessly. | Can break UI animations, audio timing, or particle systems unless using unscaled DeltaTime. |
| **Selective Entity Pause** | Disables velocity & Animator speeds on specific entities (`animator.speed = 0`). | Full control over UI, active background particle effects, and camera movement. | Requires manual tracking of game entity components; higher script complexity. |

---

### 3.3 Production C# Implementation: `HitstopManager.cs`

This pattern combines micro `Time.timeScale` suspension with smooth ease-back recovery, ensuring camera shake and UI remain active via unscaled updates.

```csharp
using System.Collections;
using UnityEngine;

public class HitstopManager : MonoBehaviour
{
    public static HitstopManager Instance { get; private set; }

    private bool isHitstopping = false;
    private Coroutine activeHitstopRoutine;

    private void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }
        Instance = this;
    }

    /// <summary>
    /// Triggers a micro hitstop pause with specified duration and freeze scale.
    /// </summary>
    /// <param name="duration">Duration in real-time seconds (e.g. 0.05s for 50ms freeze).</param>
    /// <param name="timeScale">Micro scale during freeze (0.0f for full stop, 0.05f for heavy slow-mo).</param>
    /// <param name="easeOutDuration">Time taken to smoothly recover timeScale back to 1.0.</param>
    public void TriggerHitstop(float duration = 0.05f, float timeScale = 0.0f, float easeOutDuration = 0.05f)
    {
        if (isHitstopping && activeHitstopRoutine != null)
        {
            StopCoroutine(activeHitstopRoutine);
        }

        activeHitstopRoutine = StartCoroutine(ExecuteHitstop(duration, timeScale, easeOutDuration));
    }

    private IEnumerator ExecuteHitstop(float duration, float targetScale, float easeOutDuration)
    {
        isHitstopping = true;

        // 1. Freeze time
        Time.timeScale = targetScale;
        Time.fixedDeltaTime = 0.02f * Time.timeScale; // Keep fixed update scale aligned!

        // 2. Wait for real-time duration
        yield return new WaitForSecondsRealtime(duration);

        // 3. Smooth ease-out back to 1.0 to prevent visual snapping
        if (easeOutDuration > 0f)
        {
            float elapsed = 0f;
            while (elapsed < easeOutDuration)
            {
                elapsed += Time.unscaledDeltaTime;
                float t = elapsed / easeOutDuration;
                Time.timeScale = Mathf.Lerp(targetScale, 1.0f, t * t); // Smooth quadratic ease-out
                Time.fixedDeltaTime = 0.02f * Time.timeScale;
                yield return null;
            }
        }

        // 4. Restore state completely
        Time.timeScale = 1.0f;
        Time.fixedDeltaTime = 0.02f;
        isHitstopping = false;
    }

    private void OnDestroy()
    {
        // Safety guard: ensure timeScale is restored if scene changes during hitstop
        Time.timeScale = 1.0f;
        Time.fixedDeltaTime = 0.02f;
    }
}
```

---

## 4. Dynamic Camera Pitch & Lateral Offset During Lane Switches

In 3-lane mobile endless runners (e.g., Subway Surfers, Temple Run), direct rigid tracking of lane switches causes harsh camera snapping. Adding **dynamic roll/banking**, **lateral offset tracking**, and **vertical pitch dynamics** creates natural movement weight transfer.

```
       LEFT LANE SWERVE                      RIGHT LANE SWERVE
    ┌──────────────────────┐              ┌──────────────────────┐
    │ Camera Banks Right   │              │ Camera Banks Left    │
    │ (Roll = +Z Offset)   │              │ (Roll = -Z Offset)   │
    │                      │              │                      │
    │   /                  │              │                  \   │
    │  /                   │              │                   \  │
    └──────────────────────┘              └──────────────────────┘
```

---

### 4.1 Weight Transfer Mechanics

1. **Lateral Offset Softening ($\alpha$):** The camera only follows a percentage (e.g., $65\%$) of lateral lane displacement instantly, letting the player character visually lead the swerve.
2. **Dynamic Roll / Banking ($\theta_{\text{roll}}$):** Swerving left tilts the camera body slightly right (clockwise roll), counter-acting angular force.
3. **Jump / Slide Vertical Pitching:**
   - **Jump:** Camera pitches downward ($\theta_{\text{pitch}} < 0$) to keep target landing zones visible ahead.
   - **Slide:** Camera pitches upward slightly ($\theta_{\text{pitch}} > 0$) or drops camera elevation to emphasize low obstacle clearance.

---

### 4.2 Production C# Implementation: `RunnerCameraController.cs`

This comprehensive controller combines target tracking, dynamic lane-switch banking, dynamic FOV, and trauma screenshake in a single, memory-optimized script.

```csharp
using UnityEngine;

[DisallowMultipleComponent]
public class RunnerCameraController : MonoBehaviour
{
    [Header("Tracking Target")]
    [SerializeField] private Transform playerTransform;
    [SerializeField] private Vector3 baseOffset = new Vector3(0f, 3.5f, -7f);

    [Header("Damping Parameters")]
    [SerializeField] private float positionSmoothTime = 0.12f;
    [SerializeField] private float rotationSmoothSpeed = 10f;

    [Header("Lane Switch Banking & Offsets")]
    [Tooltip("Percentage of player X position camera follows (0.6 = 60%).")]
    [SerializeField] private float lateralFollowRatio = 0.65f;
    [Tooltip("Max roll angle during hard lane switches (degrees).")]
    [SerializeField] private float maxRollAngle = 3.5f;
    [SerializeField] private float rollDamping = 8f;

    [Header("Vertical Pitch Dynamics")]
    [SerializeField] private float jumpPitchOffset = -4.0f; // Pitch down on jump
    [SerializeField] private float slidePitchOffset = 2.5f;   // Pitch up on slide

    [Header("Sub-Systems")]
    [SerializeField] private DynamicRunnerFOV fovSystem;
    [SerializeField] private RunnerCameraShake shakeSystem;

    // Internal tracking state
    private Vector3 currentVelocity;
    private float currentRollAngle;
    private float targetPitchOffset;
    private float currentPitchOffset;

    private void LateUpdate()
    {
        if (playerTransform == null) return;

        // 1. Calculate desired target position with damped lateral follow
        Vector3 targetPosition = playerTransform.position + baseOffset;
        targetPosition.x = playerTransform.position.x * lateralFollowRatio;

        // 2. Smooth position tracking using SmoothDamp
        Vector3 smoothedPosition = Vector3.SmoothDamp(
            transform.position,
            targetPosition,
            ref currentVelocity,
            positionSmoothTime
        );

        // 3. Compute Lane Switch Velocity for Roll Banking
        float lateralVelocity = currentVelocity.x;
        float targetRoll = -Mathf.Clamp(lateralVelocity * 0.5f, -maxRollAngle, maxRollAngle);
        currentRollAngle = Mathf.Lerp(currentRollAngle, targetRoll, Time.deltaTime * rollDamping);

        // 4. Smooth pitch offsets (Jump/Slide state handling)
        currentPitchOffset = Mathf.Lerp(currentPitchOffset, targetPitchOffset, Time.deltaTime * rotationSmoothSpeed);

        // 5. Build base rotation (Look towards player horizon + pitch/roll dynamics)
        Quaternion targetRotation = Quaternion.Euler(
            12.0f + currentPitchOffset, // Base pitch angle
            0f,
            currentRollAngle
        );

        // 6. Apply Trauma Shake offsets
        Vector3 shakePosOffset = Vector3.zero;
        Quaternion shakeRotOffset = Quaternion.identity;
        if (shakeSystem != null)
        {
            shakeSystem.CalculateShake(out shakePosOffset, out shakeRotOffset);
        }

        // 7. Final Transform Assembly
        transform.position = smoothedPosition + shakePosOffset;
        transform.rotation = targetRotation * shakeRotOffset;

        // 8. Update FOV based on current player velocity magnitude
        if (fovSystem != null)
        {
            fovSystem.UpdateFOV(currentVelocity.magnitude);
        }
    }

    /// <summary>
    /// Notify camera of player jump state to pitch down.
    /// </summary>
    public void SetJumpState(bool isJumping)
    {
        targetPitchOffset = isJumping ? jumpPitchOffset : 0f;
    }

    /// <summary>
    /// Notify camera of player slide state to adjust pitch.
    /// </summary>
    public void SetSlideState(bool isSliding)
    {
        targetPitchOffset = isSliding ? slidePitchOffset : 0f;
    }
}
```

---

## 5. Mobile Performance & Optimization Checklist

Mobile runners run across high-refresh rates ($90-120\text{ Hz}$) on flagship hardware while needing consistent $60\text{ FPS}$ on lower-end devices. Camera code runs every single frame in `LateUpdate()`; any performance waste impacts frame pacing and battery life.

```
                   MOBILE PERFORMANCE ARCHITECTURE
 ┌─────────────────────────────────────────────────────────────────┐
 │                      LateUpdate Loop Execution                  │
 ├─────────────────────────────────────────────────────────────────┤
 │  [Zero Heap Allocations] ──► Pre-allocated Vector3/Quaternion  │
 │  [Direct Transform Sync] ──► Bypasses GetComponent Calls        │
 │  [Frame-rate Invariant]  ──► Uses SmoothDamp / Exp Damping      │
 └─────────────────────────────────────────────────────────────────┘
```

### 5.1 Memory & Garbage Collection (GC) Rules
- **Zero Allocations in `LateUpdate`:** Avoid calling `new Vector3()`, `new Quaternion()`, or array instantiation inside camera update pipelines.
- **Cache Components in `Awake`:** Pre-cache `Camera`, `Transform`, `Rigidbody`, and sub-system scripts. Never use `GetComponent<T>()` or `FindObjectOfType<T>()` in loop iterations.

### 5.2 Cinemachine vs. Procedural C# Math Trade-offs

| Optimization Axis | Custom Procedural C# Pipeline | Cinemachine Package |
| :--- | :--- | :--- |
| **CPU Overhead** | **Extremely Low (~0.02ms / frame)**. Direct transform math with minimal stack overhead. | **Moderate (~0.15ms - 0.40ms / frame)**. Pipeline evaluates virtual camera state machine and extensions. |
| **Memory Footprint** | Zero GC allocations, near-zero memory footprint. | Small allocation during vcam transitions; larger code binary. |
| **Customization Ease** | Direct math access for custom curve math, trauma, and custom lane banking. | Highly configurable via inspector; complex custom extensions require custom `CinemachineExtension` scripts. |
| **Mobile Recommendation** | **Preferred for core runner gameplay camera** where CPU budget is tightly constrained. | **Recommended for cinematic state transitions** (e.g., Main Menu to Gameplay transition). |

### 5.3 Frame Pacing & Physics Synchronization Checklist
- [x] **Always Update Camera in `LateUpdate()`:** Player movement occurs in `Update()` or `FixedUpdate()`. Updating camera transforms in `LateUpdate()` guarantees the camera renders target positions after all movement calculations settle for the frame.
- [x] **Rigidbody Interpolation:** If the player character moves via Rigidbody physics (`FixedUpdate`), enable **Interpolate** on the player `Rigidbody`. This prevents camera stutter caused by mismatched `FixedUpdate` (50 Hz) and `LateUpdate` (60/120 Hz) update frequencies.
- [x] **Unscaled Delta Time for Camera Juicing:** Always use `Time.unscaledDeltaTime` and `Time.unscaledTime` for camera shake decay and hitstop timers so camera effects remain smooth when timeScale is paused.
