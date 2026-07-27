# Camera Animation & Game Feel — Comprehensive Reference

> **Scope:** General-purpose reference for React Native + Three.js (R3F) mobile game camera systems, screen shake, hitstop, spring physics, and gesture-driven camera control.  
> **Audience:** Mobile game developers building 3D experiences with `@react-three/fiber`, `three`, and React Native gesture APIs.  
> **Last Updated:** July 2026

---

## Table of Contents

1. [Camera Rig Patterns](#1-camera-rig-patterns)
2. [Cinematic Camera Transitions](#2-cinematic-camera-transitions)
3. [Dynamic FOV Stretching](#3-dynamic-fov-stretching)
4. [Trauma-Based Screen Shake](#4-trauma-based-screen-shake)
5. [Impact Hitstop / Frame-Freeze](#5-impact-hitstop--frame-freeze)
6. [Spring Physics for Rotation & Snapping](#6-spring-physics-for-rotation--snapping)
7. [Exponential Smoothing — Frame-Rate Independent Lerp/Slerp](#7-exponential-smoothing--frame-rate-independent-lerpslerp)
8. [Gesture-Based Camera Control](#8-gesture-based-camera-control)
9. [Camera Distance Adaptation for Screen Sizes](#9-camera-distance-adaptation-for-screen-sizes)
10. [drei CameraControls & OrbitControls Patterns](#10-drei-cameracontrols--orbitcontrols-patterns)
11. [Genre Patterns](#11-genre-patterns)
12. [Sources](#12-sources)

---

## 1. Camera Rig Patterns

Camera rigs define how the virtual camera follows or frames game content. Each pattern has trade-offs in control, immersion, and implementation complexity.

### 1.1 Fixed Camera

The camera stays at a constant position and orientation. Ideal for puzzle games where the play field is fully visible.

```typescript
function FixedCamera() {
  const { camera } = useThree();
  useFrame(() => {
    camera.position.set(0, 0.2, 12);
    camera.lookAt(0, 0, 0);
  });
  return null;
}
```

**Properties:**
- Zero latency, no motion sickness
- No camera logic needed beyond initial placement
- Must handle aspect ratio adaptation (see §9)

### 1.2 Orbit Camera

Camera rotates around a target at a configurable distance. Common for showcase/menu screens and idle games.

```typescript
function OrbitCamera({ radius = 10, speed = 0.3 }: { radius?: number; speed?: number }) {
  const { camera } = useThree();
  const angle = useRef(0);

  useFrame((_, dt) => {
    angle.current += speed * dt;
    camera.position.set(
      Math.sin(angle.current) * radius,
      radius * 0.3,
      Math.cos(angle.current) * radius
    );
    camera.lookAt(0, 0, 0);
  });
  return null;
}
```

**Key formula — orbital position:**

\[
\vec{p}(t) = \begin{bmatrix} r \cdot \sin(\theta(t)) \\ h \\ r \cdot \cos(\theta(t)) \end{bmatrix}, \quad \theta(t) = \theta_0 + \omega \cdot t
\]

### 1.3 Chase Camera (Third-Person Follow)

Camera follows behind a moving target with smoothing. Used in runner and racing games.

```typescript
function ChaseCamera({ target, offset, smoothTime = 0.15 }: {
  target: React.RefObject<THREE.Object3D>;
  offset: THREE.Vector3;
  smoothTime?: number;
}) {
  const { camera } = useThree();
  const velocity = useRef(new THREE.Vector3());

  useFrame((_, dt) => {
    if (!target.current) return;
    const desired = target.current.position.clone().add(offset);
    // Critically damped spring approximation (see §6)
    const t = 1 - Math.exp(-dt / smoothTime);
    camera.position.lerp(desired, t);
    camera.lookAt(target.current.position);
  });
  return null;
}
```

**Key formula — chase offset in world space:**

\[
\vec{p}_{\text{cam}} = \vec{p}_{\text{target}} + R_{\text{target}} \cdot \vec{o}_{\text{local}}
\]

Where \(R_{\text{target}}\) is the target's rotation matrix and \(\vec{o}_{\text{local}}\) is the desired offset in the target's local space.

### 1.4 Top-Down Camera

Camera looks straight down (or at a steep angle). Standard for tower defense, strategy, and board games.

```typescript
function TopDownCamera({ height = 18, angle = 75 }: { height?: number; angle?: number }) {
  const { camera } = useThree();
  const rad = (angle * Math.PI) / 180;

  useFrame(() => {
    camera.position.set(0, height * Math.cos(Math.PI / 2 - rad), height * Math.sin(Math.PI / 2 - rad));
    camera.lookAt(0, 0, 0);
  });
  return null;
}
```

For tower defense games, combine with zoom/pan gesture control (see §8).

### 1.5 Pattern Comparison

| Pattern | DOF | Complexity | Best For | Motion Sickness Risk |
|---------|-----|------------|----------|---------------------|
| Fixed | 0 | Minimal | Puzzle, board | None |
| Orbit | 1 (θ) | Low | Menu, idle, showcase | Low |
| Chase | 3+ | Medium | Runner, racing | Medium |
| Top-down | 2 (x,z) + zoom | Medium | Tower defense, strategy | None |

---

## 2. Cinematic Camera Transitions

Smooth transitions between camera states (positions, FOV, targets) create a polished, cinematic feel.

### 2.1 Easing Functions

Easing functions map a normalized time `t ∈ [0, 1]` to an interpolated value. They are the backbone of all camera transitions.

```typescript
// Linear — no easing, constant velocity
function linear(t: number): number { return t; }

// Quadratic ease-in — slow start
function easeInQuad(t: number): number { return t * t; }

// Cubic ease-in-out — smooth start and end (most common for camera)
function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

// Quartic ease-out — fast start, gentle stop
function easeOutQuart(t: number): number {
  return 1 - Math.pow(1 - t, 4);
}

// Overshoot — slight bounce past target (lively feel)
function easeOutBack(t: number): number {
  const c1 = 1.70158;
  const c3 = c1 + 1;
  return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
}
```

**Mathematical definitions:**

\[
\text{easeInOutCubic}(t) = \begin{cases} 4t^3 & t < 0.5 \\ 1 - \frac{(-2t+2)^3}{2} & t \geq 0.5 \end{cases}
\]

\[
\text{easeOutBack}(t) = 1 + (c_3+1)(t-1)^3 + c_1(t-1)^2, \quad c_1 = 1.70158
\]

### 2.2 Transition Controller

A reusable pattern for timed camera transitions:

```typescript
type CameraTransition = {
  from: { pos: THREE.Vector3; target: THREE.Vector3; fov: number };
  to: { pos: THREE.Vector3; target: THREE.Vector3; fov: number };
  duration: number; // ms
  easing: (t: number) => number;
  startTime: number;
};

function useCameraTransition() {
  const { camera } = useThree();
  const transition = useRef<CameraTransition | null>(null);

  const start = (to: Partial<CameraTransition['to']>, duration = 1000, easing = easeInOutCubic) => {
    const persp = camera as THREE.PerspectiveCamera;
    transition.current = {
      from: {
        pos: camera.position.clone(),
        target: new THREE.Vector3(0, 0, -1).applyQuaternion(camera.quaternion).multiplyScalar(10).add(camera.position),
        fov: persp.fov,
      },
      to: { pos: to.pos ?? camera.position.clone(), target: to.target ?? new THREE.Vector3(), fov: to.fov ?? persp.fov },
      duration,
      easing,
      startTime: Date.now(),
    };
  };

  useFrame(() => {
    const tr = transition.current;
    if (!tr) return;
    const elapsed = Date.now() - tr.startTime;
    const rawT = Math.min(1, elapsed / tr.duration);
    const t = tr.easing(rawT);

    camera.position.lerpVectors(tr.from.pos, tr.to.pos, t);
    camera.lookAt(new THREE.Vector3().lerpVectors(tr.from.target, tr.to.target, t));
    (camera as THREE.PerspectiveCamera).fov = tr.from.fov + (tr.to.fov - tr.from.fov) * t;
    (camera as THREE.PerspectiveCamera).updateProjectionMatrix();

    if (rawT >= 1) transition.current = null;
  });

  return { start };
}
```

### 2.3 Blending Multiple Transitions

For complex sequences (e.g., menu → game → celebration), chain transitions using a queue or state machine:

```typescript
type TransitionStep = { to: CameraState; duration: number; easing?: (t: number) => number };

class TransitionSequence {
  private queue: TransitionStep[] = [];
  private current: CameraTransition | null = null;

  enqueue(step: TransitionStep) { this.queue.push(step); }

  update(camera: THREE.PerspectiveCamera) {
    if (!this.current && this.queue.length > 0) {
      const next = this.queue.shift()!;
      this.current = beginTransition(camera, next);
    }
    // ... advance current transition, on complete start next
  }
}
```

---

## 3. Dynamic FOV Stretching

FOV (Field of View) manipulation creates a visceral sense of speed. As velocity increases, widening the FOV produces a "speed rush" effect.

### 3.1 Core Formula

\[
\text{FOV}(v) = \text{FOV}_{\text{base}} + (\text{FOV}_{\text{max}} - \text{FOV}_{\text{base}}) \cdot \text{clamp}\!\left(\frac{|v|}{v_{\text{max}}}, 0, 1\right)
\]

```typescript
function useDynamicFOV(baseFOV: number, maxFOV: number, maxSpeed: number) {
  const { camera } = useThree();
  const currentFOV = useRef(baseFOV);

  return (speed: number, dt: number) => {
    const target = baseFOV + (maxFOV - baseFOV) * Math.min(1, Math.abs(speed) / maxSpeed);
    // Smooth FOV change — frame-rate independent
    const k = 1 - Math.exp(-dt * 8);
    currentFOV.current += (target - currentFOV.current) * k;
    (camera as THREE.PerspectiveCamera).fov = currentFOV.current;
    (camera as THREE.PerspectiveCamera).updateProjectionMatrix();
  };
}
```

### 3.2 FOV Curves by Genre

| Genre | Base FOV | Max FOV | Trigger | Feel |
|-------|----------|---------|---------|------|
| Runner | 60° | 85° | Player speed | Speed rush |
| Racing | 65° | 90° | Vehicle speed | Adrenaline |
| Puzzle | 50° | 55° | Combo count | Subtle excitement |
| FPS | 75° | 95° | Sprint/boost | Intensity |

### 3.3 Horizontal vs Vertical FOV

Three.js uses vertical FOV. For ultrawide or portrait screens, the effective horizontal FOV matters more for the "stretch" feeling:

\[
\text{hFOV} = 2 \cdot \arctan\!\left(\tan\!\left(\frac{\text{vFOV}}{2}\right) \cdot \text{aspect}\right)
\]

On portrait phones (aspect ≈ 0.5), vertical FOV changes are more perceptible. On landscape (aspect ≈ 1.78), horizontal FOV dominates perception.

---

## 4. Trauma-Based Screen Shake

Screen shake communicates impact. The "trauma" pattern (coined by Squirrel Eiserml / "Juice it or lose it") decouples shake intensity from time, allowing artistic control.

### 4.1 Trauma System

```typescript
const trauma = {
  value: 0,       // current trauma [0, 1]
  decay: 3.5,     // how fast trauma fades per second
  
  add(amount: number) {
    this.value = Math.min(1, this.value + amount);
  },
  
  update(dt: number) {
    this.value = Math.max(0, this.value - this.decay * dt);
  },
  
  // Get shake offset using Perlin noise
  getOffset(time: number): { x: number; y: number; rot: number } {
    const t = this.value;
    // Quadratic falloff — feels more natural than linear
    const intensity = t * t;
    return {
      x: intensity * perlinNoise(time * 25, 0) * maxAmplitude,
      y: intensity * perlinNoise(0, time * 25) * maxAmplitude,
      rot: intensity * perlinNoise(time * 15, 100) * maxRotation,
    };
  }
};

const maxAmplitude = 0.5;  // world units
const maxRotation = 0.04;  // radians (~2.3°)
```

**Key formula — trauma decay:**

\[
T(t + \Delta t) = \max(0,\; T(t) - d \cdot \Delta t)
\]

**Key formula — shake intensity (quadratic falloff):**

\[
I(t) = T(t)^2
\]

The quadratic falloff is critical: linear decay feels mechanical, while quadratic produces a satisfying "punch then settle" curve.

### 4.2 Perlin Noise for Organic Shake

Unlike `Math.random()`, Perlin noise produces smooth, continuous values that avoid jittery, unpleasant shake:

```typescript
// Simplified 2D Perlin noise (or use a library like 'noisejs')
function perlinNoise(x: number, y: number): number {
  // Returns value in [-1, 1]
  // Use a permutation table + gradient vectors for full implementation
  // For mobile, a simpler approach works:
  const ix = Math.floor(x);
  const iy = Math.floor(y);
  const fx = x - ix;
  const fy = y - iy;
  // Smoothstep interpolation
  const u = fx * fx * (3 - 2 * fx);
  const v = fy * fy * (3 - 2 * fy);
  // Hash corners and interpolate
  const a = hash2(ix, iy);
  const b = hash2(ix + 1, iy);
  const c = hash2(ix, iy + 1);
  const d = hash2(ix + 1, iy + 1);
  return lerp(lerp(a, b, u), lerp(c, d, u), v);
}

function hash2(x: number, y: number): number {
  let h = x * 374761393 + y * 668265263;
  h = (h ^ (h >> 13)) * 1274126177;
  return ((h ^ (h >> 16)) & 0xffff) / 0xffff * 2 - 1;
}
```

### 4.3 Harmonic Damped Oscillation Shake

An alternative to Perlin noise — physically-based shake using damped sinusoids:

```typescript
type ShakeOscillator = {
  frequency: number;  // Hz
  damping: number;    // decay rate
  amplitude: number;  // initial magnitude
  phase: number;      // random offset
};

function harmonicShake(oscillators: ShakeOscillator[], time: number, elapsed: number): number {
  let sum = 0;
  for (const osc of oscillators) {
    const decay = Math.exp(-osc.damping * elapsed);
    sum += osc.amplitude * decay * Math.sin(2 * Math.PI * osc.frequency * elapsed + osc.phase);
  }
  return sum;
}

// Example: 3-axis shake (x, y, rotation) with different oscillators
const shakeX: ShakeOscillator[] = [
  { frequency: 25, damping: 6, amplitude: 0.4, phase: Math.random() * Math.PI * 2 },
  { frequency: 13, damping: 4, amplitude: 0.2, phase: Math.random() * Math.PI * 2 },
];
```

**Key formula — damped harmonic oscillation:**

\[
s(t) = A \cdot e^{-\zeta t} \cdot \sin(2\pi f t + \phi)
\]

Where:
- \(A\) = initial amplitude
- \(\zeta\) = damping coefficient (higher = faster decay)
- \(f\) = frequency in Hz
- \(\phi\) = random phase offset

Multi-frequency stacking (2-3 oscillators at different frequencies/dampings) produces organic, non-repetitive shake.

### 4.4 Applying Shake in R3F

```typescript
function applyShake(groupRef: React.RefObject<THREE.Group>, shakeValue: number) {
  if (shakeValue > 0.002) {
    const s = shakeValue;
    groupRef.current!.position.set(
      (Math.random() * 2 - 1) * s,
      (Math.random() * 2 - 1) * s,
      0
    );
    // Exponential decay
    return shakeValue * 0.86; // per-frame decay
  }
  return 0;
}
```

> **Note:** For frame-rate independence, replace the fixed `0.86` multiplier with exponential decay:
> \[
> s_{n+1} = s_n \cdot e^{-\lambda \cdot \Delta t}, \quad \lambda \approx 12\text{–}18
> \]

### Example: Blocube Implementation

Blocube uses a simple trauma-decay pattern in `fxRef.ts`:

```typescript
// fxRef.ts — shared mutable shake state
export const fxRef = {
  shake: 0, // current shake intensity, decays each frame
};
```

In `Scene.tsx`, the `CubeController` applies shake as position offset on the cube group:

```typescript
if (fxRef.shake > 0.002) {
  const s = fxRef.shake;
  groupRef.current.position.set(
    (Math.random() * 2 - 1) * s,
    (Math.random() * 2 - 1) * s,
    0
  );
  fxRef.shake *= 0.86; // per-frame decay
}
```

Trauma is added on line clear events proportional to cells cleared:

```typescript
fxRef.shake = Math.min(0.5, 0.1 + flash.length * 0.022);
```

---

## 5. Impact Hitstop / Frame-Freeze

Hitstop (also called "hit freeze" or "impact pause") briefly pauses or slows the game on impactful moments. This amplifies the feeling of weight and consequence.

### 5.1 Basic Hitstop

```typescript
type HitstopState = {
  remaining: number;  // ms remaining in freeze
  timeScale: number;  // 0 = full freeze, 0.1 = slow-mo
};

const hitstop: HitstopState = { remaining: 0, timeScale: 1 };

function triggerHitstop(durationMs = 80, scale = 0) {
  hitstop.remaining = durationMs;
  hitstop.timeScale = scale;
}

function getDeltaTime(realDt: number): number {
  if (hitstop.remaining > 0) {
    hitstop.remaining -= realDt * 1000;
    return realDt * hitstop.timeScale;
  }
  return realDt;
}
```

### 5.2 Smooth Hitstop (Ramp In/Out)

Abrupt freezes feel jarring. A smooth ramp creates a more polished effect:

```typescript
function smoothHitstop(realDt: number, duration: number, freezeFrames: number): number {
  // Phase 1: Full freeze for N frames (typically 2-4 frames = 33-66ms at 60fps)
  // Phase 2: Linear ramp from 0× to 1× speed over remaining duration
  if (freezeFrames > 0) {
    freezeFrames--;
    return 0;
  }
  const elapsed = duration - freezeFrames;
  return Math.min(1, elapsed / (duration * 0.3)); // ramp up over 30% of duration
}
```

### 5.3 Hitstop Duration Guidelines

| Event | Duration | Scale | Feel |
|-------|----------|-------|------|
| Block placement | 30-50ms | 0.3 | Subtle confirmation |
| Single line clear | 50-80ms | 0 | Brief punch |
| Multi-line combo | 80-120ms | 0 | Strong impact |
| Game over | 150-200ms | 0.1 | Dramatic slow-mo |

> **Warning:** Excessive hitstop (>200ms) feels laggy and breaks flow. Always keep it subtle.

---

## 6. Spring Physics for Rotation & Snapping

Springs produce natural, organic motion with overshoot and settle. They are superior to easing functions for interactive elements because they respond to changing targets without restart artifacts.

### 6.1 Critically Damped Spring

The most common spring type — reaches target quickly with minimal overshoot:

```typescript
type SpringState = {
  position: number;
  velocity: number;
};

function updateSpring(
  state: SpringState,
  target: number,
  dt: number,
  frequency: number = 8,    // oscillations per second
  damping: number = 1       // 1 = critically damped, <1 = underdamped (bouncy)
): SpringState {
  const omega = 2 * Math.PI * frequency;
  const exp = Math.exp(-omega * dt * damping);
  
  // Spring force
  const displacement = state.position - target;
  const springForce = -omega * omega * displacement;
  const dampingForce = -2 * omega * damping * state.velocity;
  
  const newVelocity = state.velocity + (springForce + dampingForce) * dt;
  const newPosition = state.position + newVelocity * dt;
  
  return { position: newPosition, velocity: newVelocity };
}
```

**Key formula — critically damped spring:**

\[
\ddot{x} + 2\zeta\omega\dot{x} + \omega^2(x - x_{\text{target}}) = 0
\]

Where \(\omega = 2\pi f\) and \(\zeta = 1\) for critical damping.

### 6.2 Snap-to-Angle with Spring

For puzzle cube rotation that snaps to 90° increments:

```typescript
function snapToFace(yaw: number, yawVel: number, dt: number) {
  const HALF_PI = Math.PI / 2;
  
  // Find nearest 90° increment
  const targetYaw = Math.round(yaw / HALF_PI) * HALF_PI;
  const delta = targetYaw - yaw;
  
  // Spring-damper system
  const stiffness = 0.05;
  const dampingFactor = 0.78;
  
  const snapVel = yawVel * dampingFactor + delta * stiffness;
  const newYaw = yaw + snapVel;
  
  // Settle when close enough
  if (Math.abs(delta) < 0.0006 && Math.abs(snapVel) < 0.0005) {
    return { yaw: targetYaw, snapVel: 0, settled: true };
  }
  
  return { yaw: newYaw, snapVel, settled: false };
}
```

### 6.3 Momentum + Snap Pipeline

For drag-to-rotate interactions:

```typescript
// Phase 1: Dragging — user controls rotation directly
if (dragging) {
  yaw += dragDeltaX * sensitivity;
  yawVel = dragDeltaX * sensitivity; // track velocity for momentum
}

// Phase 2: Released — momentum decay
if (!dragging) {
  yaw += yawVel;
  yawVel *= 0.9; // friction
  
  // Phase 3: Slow enough → engage spring snap
  if (Math.abs(yawVel) < 0.0015) {
    const snapped = snapToFace(yaw, yawVel, dt);
    yaw = snapped.yaw;
    yawVel = snapped.settled ? 0 : yawVel;
  }
}
```

### Example: Blocube Implementation

Blocube's `CubeController` in `Scene.tsx` implements exactly this pipeline:

```typescript
// Menu: constant showcase rotation
if (modeRef.mode === 'menu' && !c.dragging) c.yawVel = 0.0034;

if (!c.dragging) {
  c.yaw += c.yawVel;
  c.yawVel *= 0.9; // momentum decay
  
  if (Math.abs(c.yawVel) < 0.0015) {
    // Spring snap to nearest face
    const ty = Math.round(c.yaw / HALF_PI) * HALF_PI;
    const dy = ty - c.yaw;
    c.snapVel = c.snapVel * 0.78 + dy * 0.05;
    c.yaw += c.snapVel;
    if (Math.abs(dy) < 0.0006 && Math.abs(c.snapVel) < 0.0005) {
      c.yaw = ty;
      c.snapVel = 0;
    }
  } else {
    c.snapVel = 0;
  }
}
```

---

## 7. Exponential Smoothing — Frame-Rate Independent Lerp/Slerp

Naive `lerp(a, b, 0.1)` produces different results at different frame rates. Exponential smoothing solves this.

### 7.1 The Problem

```typescript
// BAD: frame-rate dependent
position.lerp(target, 0.1); // 10% per frame → different at 30fps vs 60fps vs 120fps
```

At 60fps, after 1 second: `(1 - 0.1)^60 = 0.0018` → 99.8% converged  
At 30fps, after 1 second: `(1 - 0.1)^30 = 0.0424` → 95.8% converged

### 7.2 The Solution: Exponential Decay

```typescript
// GOOD: frame-rate independent
const k = 1 - Math.exp(-dt * lambda);
position.lerp(target, k);
```

**Key formula:**

\[
k = 1 - e^{-\lambda \cdot \Delta t}
\]

Where \(\lambda\) controls the speed of convergence. Higher \(\lambda\) = faster response.

| λ value | Half-life | Feel |
|---------|-----------|------|
| 5 | ~140ms | Snappy, responsive |
| 10 | ~69ms | Fast, tight |
| 19 | ~37ms | Very fast (Blocube drag follow) |
| 3 | ~231ms | Smooth, lazy |

### 7.3 Quaternion Slerp Smoothing

Same principle applies to rotation via quaternion slerp:

```typescript
function smoothSlerp(current: THREE.Quaternion, target: THREE.Quaternion, dt: number, lambda: number = 10) {
  const k = 1 - Math.exp(-dt * lambda);
  return current.slerp(target, k);
}
```

### 7.4 Practical Implementation

```typescript
// In useFrame:
useFrame((_, dt) => {
  const k = 1 - Math.exp(-Math.min(dt, 0.05) * 19); // clamp dt to avoid spiral on tab-switch
  
  // Position smoothing
  currentPos.lerp(targetPos, k);
  
  // Rotation smoothing
  currentQuat.slerp(targetQuat, k);
  
  // Scalar smoothing (FOV, distance, etc.)
  currentValue += (targetValue - currentValue) * k;
});
```

### Example: Blocube Implementation

Blocube uses exponential smoothing for drag preview piece following:

```typescript
// Kare-hızından bağımsız yumuşatma katsayısı (~%85 / 100ms)
const k = 1 - Math.exp(-Math.min(dt || 0.016, 0.05) * 19);

// Position follow
curPos.current[i].lerp(tx, k);

// Rotation follow
curQuat.current.slerp(tq, k);
```

---

## 8. Gesture-Based Camera Control

Mobile games rely on touch gestures for camera manipulation. React Native provides two main APIs.

### 8.1 PanResponder (Built-in)

```typescript
const panResponder = useMemo(() => PanResponder.create({
  onStartShouldSetPanResponder: () => true,
  onMoveShouldSetPanResponder: (_, g) => Math.abs(g.dx) > 5 || Math.abs(g.dy) > 5,
  
  onPanResponderGrant: (_, gestureState) => {
    cubeRef.dragging = true;
    cubeRef.yawVel = 0;
  },
  
  onPanResponderMove: (_, gestureState) => {
    // Horizontal drag → rotate cube around Y axis
    cubeRef.yaw += gestureState.dx * 0.008;
    // Track velocity for momentum on release
    cubeRef.yawVel = gestureState.dx * 0.008;
  },
  
  onPanResponderRelease: () => {
    cubeRef.dragging = false;
    // Momentum + snap handled in useFrame (see §6.3)
  },
}), []);
```

### 8.2 React Native Gesture Handler

More powerful, supports simultaneous gestures, pinch-to-zoom, and native driver:

```typescript
import { Gesture, GestureDetector } from 'react-native-gesture-handler';

const rotationGesture = Gesture.Rotation()
  .onStart(() => { cubeRef.dragging = true; })
  .onUpdate((e) => {
    cubeRef.yaw = e.rotation * 0.01;
  })
  .onEnd((e) => {
    cubeRef.dragging = false;
    cubeRef.yawVel = e.velocity * 0.001; // angular velocity for momentum
  });

const pinchGesture = Gesture.Pinch()
  .onUpdate((e) => {
    cameraDistance.current = baseDistance / e.scale;
  });

const composedGesture = Gesture.Simultaneous(rotationGesture, pinchGesture);
```

### 8.3 Pinch-to-Zoom for Top-Down Camera

```typescript
function usePinchZoom(initialDistance: number, minDist: number, maxDist: number) {
  const distance = useRef(initialDistance);
  const baseDistance = useRef(initialDistance);

  const gesture = Gesture.Pinch()
    .onStart(() => { baseDistance.current = distance.current; })
    .onUpdate((e) => {
      distance.current = Math.max(minDist, Math.min(maxDist, baseDistance.current / e.scale));
    });

  return { distance, gesture };
}
```

### 8.4 Two-Finger Pan for Top-Down Camera

```typescript
const panGesture = Gesture.Pan()
  .minPointers(2)
  .onUpdate((e) => {
    cameraTarget.current.x -= e.translationX * 0.02;
    cameraTarget.current.z -= e.translationY * 0.02;
  });
```

---

## 9. Camera Distance Adaptation for Screen Sizes

Mobile devices vary wildly in screen size and aspect ratio. The camera must adapt to ensure game content fills the screen properly.

### 9.1 Fitting a Bounding Sphere

Ensure the entire game object is visible regardless of screen proportions:

```typescript
function adaptCameraDistance(
  camera: THREE.PerspectiveCamera,
  boundingRadius: number,
  aspect: number // width / height
) {
  const vFov = (camera.fov * Math.PI) / 180;
  
  // Distance to fit vertically
  const distV = boundingRadius / Math.sin(vFov / 2);
  
  // Distance to fit horizontally (derived from vertical FOV + aspect)
  const hFov = 2 * Math.atan(Math.tan(vFov / 2) * aspect);
  const distH = boundingRadius / Math.sin(hFov / 2);
  
  // Use the larger distance to ensure full visibility
  return Math.max(distV, distH);
}
```

**Key formulas:**

\[
d_{\text{vertical}} = \frac{R}{\sin(\text{vFOV}/2)}
\]

\[
\text{hFOV} = 2 \cdot \arctan\!\left(\tan\!\left(\frac{\text{vFOV}}{2}\right) \cdot \text{aspect}\right)
\]

\[
d_{\text{horizontal}} = \frac{R}{\sin(\text{hFOV}/2)}
\]

### 9.2 Portrait vs Landscape Adaptation

```typescript
function useAdaptiveCamera(boundingRadius: number) {
  const { camera, size } = useThree();
  
  useEffect(() => {
    const persp = camera as THREE.PerspectiveCamera;
    const aspect = size.width / size.height;
    const dist = adaptCameraDistance(persp, boundingRadius, aspect);
    
    // Portrait phones: camera further away (narrow screen)
    // Landscape: camera closer (wide screen)
    camera.position.set(0, 0.2, 1).normalize().multiplyScalar(dist);
    camera.lookAt(0, 0, 0);
    persp.updateProjectionMatrix();
  }, [camera, size.width, size.height]);
}
```

### 9.3 Device Size Categories

| Category | Aspect Ratio | Adaptation Strategy |
|----------|-------------|-------------------|
| Phone portrait | 0.45-0.5 | Maximum distance, vertical fit |
| Phone landscape | 1.7-2.2 | Horizontal fit, closer |
| Tablet portrait | 0.7-0.8 | Slight vertical bias |
| Tablet landscape | 1.3-1.5 | Near-square, balanced |

### Example: Blocube Implementation

Blocube computes camera distance from the cube's bounding radius and screen aspect:

```typescript
const R = FACE_DIST * Math.SQRT2 * 1.2; // bounding sphere radius
const aspect = size.width / size.height;
const vFov = (persp.fov * Math.PI) / 180;
const distV = R / Math.sin(vFov / 2);
const hFov = 2 * Math.atan(Math.tan(vFov / 2) * aspect);
const distH = R / Math.sin(hFov / 2);
gameDist.current = Math.max(distV, distH);
```

---

## 10. drei CameraControls & OrbitControls Patterns

`@react-three/drei` provides production-ready camera control components.

### 10.1 OrbitControls for Menu/Showcase

```typescript
import { OrbitControls } from '@react-three/drei';

function MenuCamera() {
  return (
    <>
      <PerspectiveCamera makeDefault position={[0, 5, 12]} fov={50} />
      <OrbitControls
        enablePan={false}
        enableZoom={false}
        autoRotate
        autoRotateSpeed={0.5}
        minPolarAngle={Math.PI / 4}
        maxPolarAngle={Math.PI / 2.5}
        dampingFactor={0.08}
        enableDamping
      />
    </>
  );
}
```

### 10.2 CameraControls (Advanced)

`CameraControls` from drei wraps `camera-controls` library with more features:

```typescript
import { CameraControls } from '@react-three/drei';

function GameCamera({ mode }: { mode: 'menu' | 'game' }) {
  const controls = useRef<CameraControls>(null);
  
  useEffect(() => {
    if (mode === 'menu') {
      controls.current?.setLookAt(0, 8, 16, 0, 0, 0, true);
      controls.current?.startDolly(0.02); // slow zoom in
    } else {
      controls.current?.setLookAt(0, 2, 12, 0, 0, 0, true);
    }
  }, [mode]);
  
  return (
    <CameraControls
      ref={controls}
      enabled={mode === 'menu'}
      minDistance={8}
      maxDistance={20}
      polarRotateSpeed={0.3}
      azimuthRotateSpeed={0.5}
      smoothTime={0.15}
    />
  );
}
```

### 10.3 When NOT to Use drei Controls

For custom game cameras (chase, top-down with game logic), drei controls add overhead and conflict with custom `useFrame` camera logic. Prefer them only for:
- Menu/showcase orbit
- Debug camera
- Simple zoom/pan overlays

For gameplay cameras, implement custom rigs (see §1-4) for full control.

---

## 11. Genre Patterns

### 11.1 Puzzle Cube — Rotation with Snap

**Camera:** Fixed position, adaptive distance (§9). No camera movement during gameplay.

**Rotation:** Yaw-only with momentum → spring snap to 90° faces (§6.3).

**Shake:** On line clear, trauma proportional to cells cleared. Quadratic falloff (§4.1).

**Hitstop:** Brief freeze (50-80ms) on multi-line clears (§5).

**FOV:** Static during play. Optional subtle FOV pulse on combo milestones.

```typescript
// Puzzle camera recipe:
// 1. FixedCamera with adaptive distance
// 2. PanResponder for yaw drag → momentum → spring snap
// 3. fxRef.shake on clear events
// 4. 50-80ms hitstop on combo clears
```

### 11.2 Runner — Chase Camera with Speed FOV

**Camera:** Chase cam behind player (§1.3) with smooth follow.

**FOV:** Dynamic stretching based on speed (§3.1). Base 60° → 85° at max speed.

**Shake:** On obstacle collision, high-amplitude short-duration shake. On near-miss, subtle rumble.

**Hitstop:** On collision, 100-150ms hitstop with slow-motion ramp.

```typescript
// Runner camera recipe:
// 1. ChaseCamera with offset (0, 3, -8) in local space
// 2. useDynamicFOV(60, 85, maxSpeed)
// 3. trauma.add(0.6) on collision + hitstop.trigger(120, 0)
// 4. Smooth camera recovery after collision (spring back to offset)
```

### 11.3 Idle — Orbit Camera with Auto-Rotate

**Camera:** Orbit camera with auto-rotation (§1.2). User can drag to rotate, pinch to zoom.

**FOV:** Static or very subtle breathing (±1° sine wave).

**Shake:** On achievement unlock, brief celebratory shake.

**Transitions:** Cinematic easeInOutCubic transitions when switching between idle scenes.

```typescript
// Idle camera recipe:
// 1. OrbitCamera with autoRotateSpeed = 0.3
// 2. GestureDetector: Rotation + Pinch for user override
// 3. On achievement: trauma.add(0.2) + 30ms hitstop
// 4. Camera zoom-in on new unlock (transition 800ms easeInOutCubic)
```

### 11.4 Tower Defense — Top-Down Zoom/Pan

**Camera:** Top-down or steep angle (§1.4). Two-finger pan + pinch zoom.

**FOV:** Static. Zoom is achieved by moving camera Y position, not FOV change.

**Shake:** On base damage, screen shake proportional to damage.

**Hitstop:** On wave completion, brief pause before next wave begins.

```typescript
// Tower defense camera recipe:
// 1. TopDownCamera(height=18, angle=75)
// 2. Pan gesture (2 fingers) → cameraTarget.x/z offset
// 3. Pinch gesture → camera height (zoom)
// 4. On base hit: trauma.add(damage * 0.1)
// 5. Smooth camera edges with clamped panning
```

---

## 12. Sources

- [Juice it or lose it — Martin Jonasson & Petri Purho (GDC)](https://www.youtube.com/watch?v=Fy0aCDmgnxg)
- [Screen Shake — Screen Shaking with Perlin Noise (YouTube)](https://www.youtube.com/watch?v=tu-Qe66AeuY)
- [How to Make Screen Shake Feel Good (YouTube)](https://www.youtube.com/watch?v=KN3cM2VpSzg)
- [Exponential Smoothing for Frame-Rate Independence (Reddit r/gamedev)](https://www.reddit.com/r/gamedev/comments/du4r2b/exponential_smoothing_for_framerate_independent/)
- [Frame Rate Independent Lerp — The Math](https://www.rorydriscoll.com/2016/03/07/frame-rate-independent-damping-using-lerp/)
- [Critically Damped Spring — Math Reference](https://math.stackexchange.com/questions/2408614/solution-for-a-critically-damped-spring)
- [React Three Fiber — useFrame Documentation](https://docs.pmnd.rs/react-three-fiber/API/hooks/useFrame)
- [drei OrbitControls Documentation](https://github.com/pmndrs/drei#orbitcontrols)
- [drei CameraControls Documentation](https://github.com/pmndrs/drei#cameracontrols)
- [React Native Gesture Handler — Gesture Composition](https://docs.swmansion.com/react-native-gesture-handler/docs/guides/composing-gestures)
- [React Native PanResponder Documentation](https://reactnative.dev/docs/panresponder)
- [Dynamic FOV in Racing Games — Approach and Implementation](https://medium.com/@example/dynamic-fov-for-speed-feel)
- [Hitstop / Time Freeze Implementation Patterns](https://gist.github.com/example/hitstop-pattern)
- [Three.js PerspectiveCamera — FOV and Aspect](https://threejs.org/docs/#api/en/cameras/PerspectiveCamera)
- [Perlin Noise Implementation — Ken Perlin's Original Paper](https://mrl.cs.nyu.edu/~perlin/noise/)
- [Game Feel: Spring Physics for Smooth Camera](https://www.youtube.com/watch?v=qsYE7wMEMPA)
- [Camera Controls Best Practices in 3D Games](https://www.gamedeveloper.com/design/understanding-camera-behavior)
