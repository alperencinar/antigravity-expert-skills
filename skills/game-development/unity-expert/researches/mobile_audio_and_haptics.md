# Dynamic Mobile Vehicle Audio & Haptic Feedback Systems in Unity

## Overview & Architecture

Modern mobile driving and runner games require highly responsive visual, auditory, and tactile feedback to deliver an immersive player experience. This technical guide outlines the implementation of a high-performance **Dynamic Vehicle Audio & Haptics Engine** in Unity tailored for mobile platforms (iOS and Android).

```
 +-----------------------------------------------------------------------------------+
 |                             VEHICLE TELEMETRY & STATE                             |
 |       - Speed (V) / RPM         - Collision / Crash Event    - Bullet-Time       |
 +-------------------+-------------------------+------------------------+------------+
                     |                         |                        |
                     v                         v                        v
 +-------------------+---+         +-----------+----------+   +---------+----------+
 | DYNAMIC ENGINE AUDIO  |         |   HAPTIC FEEDBACK    |   | AUDIO MIXER / LPF  |
 | - Pitch Modulation    |         | - iOS Taptic Engine  |   | - Audio Ducking    |
 | - RPM Crossfading     |         | - Android Vibrator   |   | - Low-Pass Filter  |
 +-------------------+---+         +----------------------+   +---------+----------+
                     |                                                  |
                     +-------------------------+------------------------+
                                               |
                                               v
                                   +-----------+----------+
                                   | 3D SPATIAL AUDIO     |
                                   | - Distance Atten.    |
                                   | - Doppler Effect     |
                                   +----------------------+
```

---

## 1. Dynamic Engine Audio Pitch Modulation

### 1.1 Mathematical Formulation
The foundational model for pitch modulation maps normalized vehicle speed $V / V_{max}$ or normalized engine RPM $RPM / RPM_{max}$ to the `AudioSource.pitch` property:

$$Pitch = P_{min} + (P_{max} - P_{min}) \cdot \frac{V}{V_{max}}$$

Where:
* $P_{min}$: Baseline pitch multiplier at idle speed ($V = 0$), typically `0.65` to `0.8`.
* $P_{max}$: Maximum pitch multiplier at top speed ($V = V_{max}$), typically `1.5` to `2.2`.
* $V$: Current vehicle forward velocity magnitude ($\text{m/s}$ or $\text{km/h}$).
* $V_{max}$: Maximum design speed of the vehicle.

#### Simulated RPM & Gear Shift Variance
In arcade runners with automatic simulated transmission, engine RPM resets periodically per gear. The gear-aware pitch formula is:

$$RPM_{norm} = \frac{V - V_{gear\_min}}{V_{gear\_max} - V_{gear\_min}}$$

$$Pitch = P_{idle} + (P_{redline} - P_{idle}) \cdot \text{Clamp01}(RPM_{norm})$$

### 1.2 Multi-Clip RPM Crossfading & Smoothing
Pitching a single engine audio clip over a wide range ($>1.5\times$) results in unnatural "chipmunk" distortion. Production setups combine **multi-clip crossfading** (Idle, Low, Mid, High RPM) with pitch adjustments, using `Mathf.Lerp` or `AnimationCurve` evaluation to prevent audio popping.

```csharp
using UnityEngine;

namespace UnityExpert.Audio
{
    [RequireComponent(typeof(AudioSource))]
    public class VehicleEngineAudio : MonoBehaviour
    {
        [Header("Telemetry Input")]
        [SerializeField] private Rigidbody vehicleRigidbody;
        [SerializeField] private float maxSpeed = 50f; // m/s (~180 km/h)

        [Header("Pitch Settings")]
        [SerializeField] private float minPitch = 0.7f;
        [SerializeField] private float maxPitch = 2.0f;
        [SerializeField] private float pitchSmoothTime = 0.08f;
        [SerializeField] private AnimationCurve pitchCurve = AnimationCurve.Linear(0f, 0f, 1f, 1f);

        [Header("Gear Simulation (Optional)")]
        [SerializeField] private bool enableSimulatedGears = true;
        [SerializeField] private int totalGears = 5;

        [Header("Audio Sources (Crossfade Layering)")]
        [SerializeField] private AudioSource idleSource;
        [SerializeField] private AudioSource highRpmSource;

        private AudioSource primarySource;
        private float currentPitchVelocity;
        private float targetPitch;

        private void Awake()
        {
            primarySource = GetComponent<AudioSource>();
            if (vehicleRigidbody == null)
                vehicleRigidbody = GetComponentInParent<Rigidbody>();
        }

        private void Update()
        {
            float currentSpeed = vehicleRigidbody != null ? vehicleRigidbody.velocity.magnitude : 0f;
            float normalizedSpeed = Mathf.Clamp01(currentSpeed / maxSpeed);

            if (enableSimulatedGears)
            {
                normalizedSpeed = CalculateGearNormalizedRPM(normalizedSpeed);
            }

            // Curve evaluation allows non-linear pitch growth matching real combustion engines
            float evaluatedFactor = pitchCurve.Evaluate(normalizedSpeed);
            targetPitch = Mathf.Lerp(minPitch, maxPitch, evaluatedFactor);

            // Smooth pitch transitions to prevent audio frame jitter
            primarySource.pitch = Mathf.SmoothDamp(
                primarySource.pitch, 
                targetPitch, 
                ref currentPitchVelocity, 
                pitchSmoothTime
            );

            // Multi-clip volume crossfade
            if (idleSource != null && highRpmSource != null)
            {
                idleSource.volume = Mathf.Lerp(1.0f, 0.1f, evaluatedFactor);
                highRpmSource.volume = Mathf.Lerp(0.0f, 1.0f, evaluatedFactor);
                idleSource.pitch = primarySource.pitch;
                highRpmSource.pitch = primarySource.pitch;
            }
        }

        private float CalculateGearNormalizedRPM(float rawSpeedNormalized)
        {
            float gearStep = 1.0f / totalGears;
            int currentGear = Mathf.Min(Mathf.FloorToInt(rawSpeedNormalized / gearStep), totalGears - 1);
            float gearMinSpeed = currentGear * gearStep;
            float gearMaxSpeed = (currentGear + 1) * gearStep;
            
            return Mathf.Clamp01((rawSpeedNormalized - gearMinSpeed) / (gearMaxSpeed - gearMinSpeed));
        }
    }
}
```

---

## 2. 3D Spatial Audio & Doppler Effect for Oncoming Traffic

### 2.1 Spatial Attenuation Configuration
In high-speed traffic runners, oncoming vehicles rapidly approach and pass the player. Proper 3D Spatial Audio settings ensure realistic distance attenuation and directional clarity:

1. **Spatial Blend**: Set to `1.0` (100% 3D sound positioning).
2. **Rolloff Mode**: Use **Logarithmic** for localized mechanical sounds or **Custom Curve** to maintain audibility until an abrupt drop-off.
3. **Min / Max Distance**:
   - `Min Distance` ($5\text{m}$): Sound maintains maximum volume within 5 meters of the player camera/listener.
   - `Max Distance` ($120\text{m}$): Sound volume drops to zero beyond 120 meters.
4. **Spread Angle**: Set to `40°–60°` for stereo vehicle loops to widen stereo imaging as traffic passes close to the camera.

### 2.2 Doppler Effect Implementation
The Doppler Effect simulates pitch shifts when relative velocity changes rapidly between the `AudioListener` (Player Camera) and an `AudioSource` (Oncoming Vehicle):

$$f_{perceived} = f_{source} \cdot \left( \frac{c + v_{listener}}{c + v_{source}} \right)$$

In Unity:
- Set `AudioSource.dopplerLevel` between `1.0` and `2.5`. Higher values exaggerate the pitch drop as cars pass by.
- Both Player and Traffic GameObjects must possess a `Rigidbody` so Unity's audio engine calculates correct relative velocities.

```csharp
using UnityEngine;

namespace UnityExpert.Audio
{
    [RequireComponent(typeof(AudioSource), typeof(Rigidbody))]
    public class TrafficSpatialAudio : MonoBehaviour
    {
        [Header("3D Spatial Settings")]
        [SerializeField] private float minDistance = 5f;
        [SerializeField] private float maxDistance = 120f;
        [Range(0f, 5f)] [SerializeField] private float dopplerLevel = 1.8f;
        [Range(0f, 180f)] [SerializeField] private float spread = 45f;

        [Header("Performance Optimization")]
        [SerializeField] private float cullDistance = 130f;
        
        private AudioSource trafficAudioSource;
        private Transform listenerTransform;

        private void Awake()
        {
            trafficAudioSource = GetComponent<AudioSource>();
            ConfigureSpatialAudio();
        }

        private void Start()
        {
            if (AudioListener.pause == false && Camera.main != null)
            {
                listenerTransform = Camera.main.transform;
            }
        }

        private void ConfigureSpatialAudio()
        {
            trafficAudioSource.spatialBlend = 1.0f; // Pure 3D Spatial
            trafficAudioSource.rolloffMode = AudioRolloffMode.Logarithmic;
            trafficAudioSource.minDistance = minDistance;
            trafficAudioSource.maxDistance = maxDistance;
            trafficAudioSource.dopplerLevel = dopplerLevel;
            trafficAudioSource.spread = spread;
            trafficAudioSource.playOnAwake = true;
            trafficAudioSource.loop = true;
        }

        private void Update()
        {
            if (listenerTransform == null) return;

            // Distance Culling to optimize CPU audio processing on mobile
            float distSqr = (transform.position - listenerTransform.position).sqrMagnitude;
            bool shouldBeActive = distSqr <= (cullDistance * cullDistance);

            if (trafficAudioSource.enabled != shouldBeActive)
            {
                trafficAudioSource.enabled = shouldBeActive;
            }
        }
    }
}
```

---

## 3. Audio Ducking & Low-Pass Filter (LPF) Transitions

### 3.1 Audio Mixer Routing & Ducking Architecture
To create dramatic audio shifts during **Bullet-Time** (slow-motion) or **Crash States**, routing via the **Unity Audio Mixer** is required.

```
                    +------------------------------------+
                    |         MASTER AUDIO MIXER         |
                    +-----------------+------------------+
                                      |
         +----------------------------+----------------------------+
         |                                                         |
         v                                                         v
 +-------+--------+                                       +--------+-------+
 |  ENGINE GROUP  |                                       | TRAFFIC GROUP  |
 |  (Audio Mixer) |                                       | (Audio Mixer)  |
 +-------+--------+                                       +--------+-------+
         |                                                         |
         v                                                         v
 +-------+--------+                                       +--------+-------+
 | LOW-PASS FILTER| <--- Cutoff: 22000Hz -> 600Hz           | DUCKING COMPR. |
 | (Bullet-Time)  |      (During Slow-Mo / Crash)         | (Sidechain)    |
 +----------------+                                       +----------------+
```

1. **Audio Ducking**: Temporarily lowers background music/traffic volume when a high-priority sound (e.g., crash impact) occurs.
2. **Low-Pass Filter (LPF)**: Attenuates high frequencies above a specified cutoff threshold ($800\text{Hz} - 1200\text{Hz}$), mimicking underwater or muffled interior states during bullet-time.

```csharp
using System.Collections;
using UnityEngine;
using UnityEngine.Audio;

namespace UnityExpert.Audio
{
    public class AudioStateMixerController : MonoBehaviour
    {
        [Header("Audio Mixer Reference")]
        [SerializeField] private AudioMixer masterMixer;

        [Header("Mixer Exposed Parameters")]
        [SerializeField] private string lpfCutoffParam = "MasterLPFCutoff";
        [SerializeField] private string musicVolumeParam = "MusicVolume";
        [SerializeField] private string trafficVolumeParam = "TrafficVolume";

        [Header("Transition Settings")]
        [SerializeField] private float normalCutoff = 22000f;
        [SerializeField] private float bulletTimeCutoff = 800f;
        [SerializeField] private float normalMusicDb = 0f;
        [SerializeField] private float duckedMusicDb = -18f;
        [SerializeField] private float transitionDuration = 0.25f;

        private Coroutine activeTransition;

        public void EnterBulletTime()
        {
            StartTransition(bulletTimeCutoff, duckedMusicDb);
        }

        public void ExitBulletTime()
        {
            StartTransition(normalCutoff, normalMusicDb);
        }

        public void TriggerCrashState()
        {
            // Severe ducking and extreme muffling
            StartTransition(400f, -24f);
        }

        private void StartTransition(float targetLPF, float targetMusicDb)
        {
            if (activeTransition != null)
                StopCoroutine(activeTransition);

            activeTransition = StartCoroutine(AnimateMixerState(targetLPF, targetMusicDb));
        }

        private IEnumerator AnimateMixerState(float targetLPF, float targetMusicDb)
        {
            masterMixer.GetFloat(lpfCutoffParam, out float startLPF);
            masterMixer.GetFloat(musicVolumeParam, out float startMusicDb);

            float elapsed = 0f;
            while (elapsed < transitionDuration)
            {
                elapsed += Time.unscaledDeltaTime; // Unscaled delta time for slow-mo accuracy
                float t = elapsed / transitionDuration;

                float currentLPF = Mathf.Lerp(startLPF, targetLPF, t);
                float currentMusicDb = Mathf.Lerp(startMusicDb, targetMusicDb, t);

                masterMixer.SetFloat(lpfCutoffParam, currentLPF);
                masterMixer.SetFloat(musicVolumeParam, currentMusicDb);
                masterMixer.SetFloat(trafficVolumeParam, currentMusicDb);

                yield return null;
            }

            masterMixer.SetFloat(lpfCutoffParam, targetLPF);
            masterMixer.SetFloat(musicVolumeParam, targetMusicDb);
            masterMixer.SetFloat(trafficVolumeParam, targetMusicDb);
        }
    }
}
```

---

## 4. Cross-Platform Haptic Feedback Integration

### 4.1 Native Platform Architecture
Mobile platforms handle haptic feedback differently:

- **iOS (Taptic Engine)**: Utilizes `UIImpactFeedbackGenerator` (Light, Medium, Heavy, Rigid, Soft), `UINotificationFeedbackGenerator` (Success, Warning, Error), and `UISelectionFeedbackGenerator`.
- **Android (`VibrationEffect` & `Vibrator`)**: Uses `AndroidJavaClass` to invoke Android API level 26+ `VibrationEffect.createOneShot()` and `VibrationEffect.createWaveform()`, falling back to `Handheld.Vibrate()` on legacy hardware.

### 4.2 Haptic Profile Matrix for Vehicle Events

| Vehicle Event | iOS Haptic Type | Android Vibration Pattern / Amplitude | Duration |
| :--- | :--- | :--- | :--- |
| **Engine Idle Rumble** | Subtle Continuous / Soft | `VibrationEffect.createWaveform` (Low Amp) | Continuous |
| **Gear Shift** | `UIImpactFeedbackGenerator(Light)` | `createOneShot(20ms, Amplitude: 60)` | $20\text{ms}$ |
| **Drift / Tire Slip** | `UIImpactFeedbackGenerator(Medium)` | `createWaveform` (Pulse 40ms ON / 40ms OFF) | Variable |
| **Barrier Scratch** | `UIImpactFeedbackGenerator(Rigid)` | `createOneShot(80ms, Amplitude: 150)` | $80\text{ms}$ |
| **Major Collision / Crash** | `UIImpactFeedbackGenerator(Heavy)` | `createOneShot(300ms, Amplitude: 255)` | $300\text{ms}$ |
| **UI Button Tap** | `UISelectionFeedbackGenerator` | `createOneShot(10ms, Amplitude: 40)` | $10\text{ms}$ |

### 4.3 Unified Cross-Platform Haptics Bridge (C# Production Script)

```csharp
using System.Runtime.InteropServices;
using UnityEngine;

namespace UnityExpert.Haptics
{
    public enum HapticType
    {
        Selection,
        LightImpact,
        MediumImpact,
        HeavyImpact,
        RigidImpact,
        SoftImpact,
        SuccessNotification,
        WarningNotification,
        FailureNotification
    }

    public static class MobileHapticsBridge
    {
#if UNITY_IOS && !UNITY_EDITOR
        [DllImport("__Internal")]
        private static extern void _playiOSHaptic(int hapticType);
#endif

#if UNITY_ANDROID && !UNITY_EDITOR
        private static AndroidJavaObject vibrator;
        private static AndroidJavaClass vibrationEffectClass;
        private static int apiLevel;

        static MobileHapticsBridge()
        {
            InitializeAndroidVibrator();
        }

        private static void InitializeAndroidVibrator()
        {
            try
            {
                using (AndroidJavaClass versionClass = new AndroidJavaClass("android.os.Build$VERSION"))
                {
                    apiLevel = versionClass.GetStatic<int>("SDK_INT");
                }

                using (AndroidJavaClass unityPlayer = new AndroidJavaClass("com.unity3d.player.UnityPlayer"))
                {
                    AndroidJavaObject currentActivity = unityPlayer.GetStatic<AndroidJavaObject>("currentActivity");
                    vibrator = currentActivity.Call<AndroidJavaObject>("getSystemService", "vibrator");
                }

                if (apiLevel >= 26)
                {
                    vibrationEffectClass = new AndroidJavaClass("android.os.VibrationEffect");
                }
            }
            catch (System.Exception ex)
            {
                Debug.LogWarning($"Android Haptics Initialization Failed: {ex.Message}");
            }
        }
#endif

        public static void Trigger(HapticType type)
        {
#if UNITY_EDITOR
            // No-op in Editor
            return;
#elif UNITY_IOS
            _playiOSHaptic((int)type);
#elif UNITY_ANDROID
            PlayAndroidHaptic(type);
#endif
        }

#if UNITY_ANDROID && !UNITY_EDITOR
        private static void PlayAndroidHaptic(HapticType type)
        {
            if (vibrator == null || !vibrator.Call<bool>("hasVibrator")) return;

            long duration = 20;
            int amplitude = 128; // Default strength (1-255)

            switch (type)
            {
                case HapticType.Selection: duration = 10; amplitude = 40; break;
                case HapticType.LightImpact: duration = 20; amplitude = 80; break;
                case HapticType.MediumImpact: duration = 40; amplitude = 150; break;
                case HapticType.HeavyImpact: duration = 150; amplitude = 255; break;
                case HapticType.RigidImpact: duration = 60; amplitude = 200; break;
                case HapticType.SoftImpact: duration = 30; amplitude = 60; break;
                case HapticType.SuccessNotification: duration = 50; amplitude = 120; break;
                case HapticType.WarningNotification: duration = 100; amplitude = 180; break;
                case HapticType.FailureNotification: duration = 250; amplitude = 255; break;
            }

            if (apiLevel >= 26 && vibrationEffectClass != null)
            {
                // VibrationEffect.createOneShot(long milliseconds, int amplitude)
                int DEFAULT_AMPLITUDE = vibrationEffectClass.GetStatic<int>("DEFAULT_AMPLITUDE");
                int ampToUse = (amplitude > 0) ? amplitude : DEFAULT_AMPLITUDE;

                AndroidJavaObject effect = vibrationEffectClass.CallStatic<AndroidJavaObject>(
                    "createOneShot", duration, ampToUse
                );
                vibrator.Call("vibrate", effect);
            }
            else
            {
                // Legacy fallback
                vibrator.Call("vibrate", duration);
            }
        }
#endif
    }
}
```

---

## Technical Summary & Best Practices Checklist

1. **Audio Performance on Mobile**:
   - Always force mono on 3D spatial sounds (e.g. traffic cars) to cut spatialization CPU overhead in half.
   - Use dynamic culling (`enabled = false`) on `AudioSource` components for off-screen traffic beyond $100\text{m}$.
2. **Audio Mixer Overhead**:
   - Use `Time.unscaledDeltaTime` when animating Mixer parameters so slow-motion / bullet-time effects transition smoothly without stalling.
3. **Haptic Feedback User Experience**:
   - Always provide an in-game toggle in UI options allowing players to disable haptic feedback.
   - Limit continuous rumble (e.g., off-road driving or engine idle) to short bursts to conserve mobile battery life.
