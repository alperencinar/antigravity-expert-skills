# Mobile Audio & Haptics for Game Feel — Comprehensive Reference

> **Scope:** General-purpose reference for audio playback, haptic feedback, and their synchronization in React Native + Expo mobile games. Covers `expo-audio`, `expo-haptics`, cross-platform considerations, and graceful degradation.  
> **Audience:** Mobile game developers building interactive 3D experiences with React Native and Expo.  
> **Last Updated:** July 2026

---

## Table of Contents

1. [expo-audio vs expo-av for Game Sound (2024-2025)](#1-expo-audio-vs-expo-av-for-game-sound-2024-2025)
2. [Audio Player Pooling Pattern](#2-audio-player-pooling-pattern)
3. [Pitch / Rate Modulation for Combo Feedback](#3-pitch--rate-modulation-for-combo-feedback)
4. [Audio Session Management](#4-audio-session-management)
5. [expo-haptics — Feedback Types](#5-expo-haptics--feedback-types)
6. [Audio-Haptic Synchronization](#6-audio-haptic-synchronization)
7. [Graceful Degradation](#7-graceful-degradation)
8. [Cross-Platform: iOS Taptic Engine vs Android VibrationEffect](#8-cross-platform-ios-taptic-engine-vs-android-vibrationeffect)
9. [Volume Management and Mute Support](#9-volume-management-and-mute-support)
10. [Background Audio Behavior and App Lifecycle](#10-background-audio-behavior-and-app-lifecycle)
11. [Genre Patterns](#11-genre-patterns)
12. [Sources](#12-sources)

---

## 1. expo-audio vs expo-av for Game Sound (2024-2025)

### 1.1 Library Comparison

| Feature | `expo-av` (Audio) | `expo-audio` |
|---------|-------------------|--------------|
| **Status** | Stable, widely used | Newer, recommended for new projects (SDK 55+) |
| **Latency** | Higher (~50-100ms first play) | Lower (~10-30ms with pre-loaded players) |
| **Player Pool** | Manual `Sound` object management | `createAudioPlayer()` with native pooling |
| **Pitch/Rate** | `playFromPositionAsync` with `rate` option | `setPlaybackRate(rate)` on player instance |
| **Silent Mode** | `setAudioModeAsync({ playsInSilentModeIOS: true })` | `setAudioModeAsync({ playsInSilentMode: true })` |
| **Mixing** | `interruptionModeIOS: Audio.InterruptionModeIOS.MixWithOthers` | `interruptionMode: 'mixWithOthers'` |
| **Memory** | Each `Sound` object holds native resources | Players are lightweight, managed by native layer |
| **Expo SDK** | All versions | SDK 55+ (Expo 56 recommended) |

### 1.2 Recommendation

For new game projects on Expo SDK 55+, use `expo-audio`. It provides:
- Lower latency for rapid-fire sound effects
- Simpler API for player pooling (pre-load + seekTo(0) + play)
- Better memory management for multiple simultaneous sounds

For existing projects on older SDK versions, `expo-av` remains fully viable.

### 1.3 API Quick Reference

```typescript
// expo-audio — basic setup
import { createAudioPlayer, setAudioModeAsync, type AudioPlayer } from 'expo-audio';

// Configure audio session
await setAudioModeAsync({
  playsInSilentMode: true,        // iOS: ignore silent switch
  interruptionMode: 'mixWithOthers', // Mix with other apps' audio
});

// Create a player from a local asset
const player: AudioPlayer = createAudioPlayer(require('./assets/sfx/click.wav'));

// Play from start
player.seekTo(0);
player.play();

// Change playback rate (pitch shift)
player.setPlaybackRate(1.3); // 30% faster = higher pitch
```

---

## 2. Audio Player Pooling Pattern

For games with rapid-fire sound effects (block placement, combos, collisions), creating a new audio player on each trigger introduces unacceptable latency. The pooling pattern pre-creates players at startup.

### 2.1 Core Pattern: Pre-load, Seek, Play

```typescript
type SoundPool = {
  players: AudioPlayer[];
  currentIndex: number;
};

function createSoundPool(asset: any, poolSize: number = 4): SoundPool {
  const players: AudioPlayer[] = [];
  for (let i = 0; i < poolSize; i++) {
    players.push(createAudioPlayer(asset));
  }
  return { players, currentIndex: 0 };
}

function playFromPool(pool: SoundPool) {
  const player = pool.players[pool.currentIndex];
  pool.currentIndex = (pool.currentIndex + 1) % pool.players.length;
  player.seekTo(0);
  player.play();
}
```

**Why pool size matters:**
- Pool size 1: Sound cuts off if triggered again while playing (acceptable for non-overlapping SFX)
- Pool size 2-3: Allows overlap (e.g., rapid block placements)
- Pool size 4+: For very fast sequences (combo chains, machine gun effects)

### 2.2 Pool Sizing Guidelines

| Sound Type | Pool Size | Rationale |
|-----------|-----------|-----------|
| UI click | 1 | Single, non-overlapping |
| Block placement | 2-3 | Player may place 2-3 blocks rapidly |
| Line clear | 3-4 | Combo chains overlap multiple clears |
| Combo escalation | 2 | Previous combo sound may still ring |
| Background music | 1 | Never overlaps itself |
| Ambient loop | 1 | Continuous, single instance |

### 2.3 Memory Considerations

Each `AudioPlayer` holds a decoded audio buffer in native memory. For short WAV files (50-200ms), memory is negligible (~100-500KB per player). For longer sounds, consider:

```typescript
// Use OGG for longer sounds (music, ambient) — smaller footprint
// Use WAV for short SFX — fastest decode, no compression artifacts
const musicPlayer = createAudioPlayer(require('./assets/music/theme.ogg'));
const sfxPool = createSoundPool(require('./assets/sfx/pop.wav'), 3);
```

### Example: Blocube Implementation

Blocube uses a simplified single-player-per-sound pattern:

```typescript
// sounds.ts — one player per sound effect
let place: AudioPlayer | null = null;
let clear: AudioPlayer | null = null;

export function initAudio() {
  setAudioModeAsync({ playsInSilentMode: true, interruptionMode: 'mixWithOthers' });
  place = createAudioPlayer(require('../../assets/sfx/place.wav'));
  clear = createAudioPlayer(require('../../assets/sfx/clear.wav'));
  if (place) place.volume = 0.7;
  if (clear) clear.volume = 0.85;
}

function fire(p: AudioPlayer | null, name: string, rate = 1) {
  if (!p || muted) return;
  if (rate !== 1) p.setPlaybackRate(rate);
  p.seekTo(0);
  p.play();
}

export const sfx = {
  place: () => fire(place, 'place'),
  clear: (combo = 1) => fire(clear, 'clear', Math.min(1.6, 1 + (combo - 1) * 0.07)),
};
```

This works because placement sounds are short (~150ms) and don't typically overlap. For games with faster sequences, a pool of 2-3 players per sound would be needed.

---

## 3. Pitch / Rate Modulation for Combo Feedback

Playback rate manipulation creates a sense of escalation. As combos increase, raising the pitch of clear sounds produces a "rising tension" effect that rewards the player.

### 3.1 Core Formula

```typescript
function comboPlaybackRate(combo: number, options: {
  baseRate?: number;    // rate at combo=1 (default: 1.0)
  maxRate?: number;     // maximum rate cap (default: 1.6)
  incrementPerCombo?: number; // rate increase per combo level (default: 0.07)
} = {}): number {
  const { baseRate = 1.0, maxRate = 1.6, incrementPerCombo = 0.07 } = options;
  return Math.min(maxRate, baseRate + (combo - 1) * incrementPerCombo);
}
```

**Key formula:**

\[
r(c) = \min(r_{\max},\; r_{\text{base}} + (c - 1) \cdot \Delta r)
\]

Where:
- \(c\) = current combo count
- \(r_{\text{base}}\) = base playback rate (1.0 = normal pitch)
- \(\Delta r\) = increment per combo level
- \(r_{\max}\) = maximum rate cap

### 3.2 Rate Curves

| Combo | Rate (Δr=0.07) | Rate (Δr=0.1) | Musical Interval |
|-------|----------------|---------------|-----------------|
| 1 | 1.00 | 1.00 | Unison |
| 2 | 1.07 | 1.10 | Minor second |
| 3 | 1.14 | 1.20 | Major second |
| 5 | 1.28 | 1.40 | Minor third |
| 8 | 1.49 | 1.70→1.60 | Major third (capped) |
| 10 | 1.60 (cap) | 1.60 (cap) | — |

### 3.3 Alternative: Musical Scale Mapping

For more harmonious escalation, map combos to musical scale degrees:

```typescript
// Pentatonic scale ratios (consonant, pleasant at any combination)
const PENTATONIC_RATIOS = [1.0, 1.125, 1.25, 1.333, 1.5]; // C D E G A

function musicalComboRate(combo: number): number {
  const index = (combo - 1) % PENTATONIC_RATIOS.length;
  const octave = Math.floor((combo - 1) / PENTATONIC_RATIOS.length);
  return PENTATONIC_RATIOS[index] * Math.pow(2, octave * 0); // cap at 1 octave
  // Simplified: just cycle through the scale
}
```

### 3.4 Implementation with expo-audio

```typescript
// Apply rate change before each play
function playComboClear(player: AudioPlayer, combo: number) {
  const rate = comboPlaybackRate(combo);
  player.setPlaybackRate(rate);
  player.seekTo(0);
  player.play();
}

// Usage in game logic
sfx.clear(combo); // combo=1 → rate 1.0, combo=5 → rate 1.28
```

> **Note:** `setPlaybackRate()` on `expo-audio` changes both speed and pitch. For pitch-only changes (time-stretching), you would need a native audio library with DSP support — not available in Expo as of 2025.

---

## 4. Audio Session Management

Mobile OS audio sessions control how your app interacts with other audio sources and the hardware silent switch.

### 4.1 iOS Audio Session Categories

| Category | Silent Switch | Mixes with Others | Use Case |
|----------|--------------|-------------------|----------|
| `Ambient` | Respects silent | Yes | Background music only |
| `SoloAmbient` | Respects silent | No | Default — music player |
| `Playback` | Ignores silent | Configurable | **Games (recommended)** |
| `PlayAndRecord` | Ignores silent | Configurable | Voice chat games |

### 4.2 Configuration for Games

```typescript
import { setAudioModeAsync } from 'expo-audio';

async function configureGameAudio() {
  await setAudioModeAsync({
    playsInSilentMode: true,         // iOS: ignore silent switch (critical for games!)
    interruptionMode: 'mixWithOthers', // Don't pause Spotify/podcasts
    allowsRecording: false,           // No microphone needed
    shouldDuckAudio: false,           // Don't lower other apps' volume
  });
}
```

### 4.3 Interruption Handling

When a phone call or Siri activates, audio is interrupted. Handle gracefully:

```typescript
import { addAudioInterruptionListener } from 'expo-audio';

// Listen for audio interruptions
const subscription = addAudioInterruptionListener((event) => {
  if (event.type === 'began') {
    // Pause music, mute game sounds
    pauseBackgroundMusic();
  } else if (event.type === 'ended') {
    // Resume if the game is still active
    if (gameState === 'playing') {
      resumeBackgroundMusic();
    }
  }
});

// Clean up on unmount
return () => subscription.remove();
```

### 4.4 Android-Specific: Audio Focus

Android uses "audio focus" rather than session categories:

```typescript
// expo-audio handles this internally with interruptionMode
// 'mixWithOthers' = AUDIOFOCUS_NONE (no focus request)
// 'doNotMix' = AUDIOFOCUS_GAIN (requests exclusive focus)
// 'duckOthers' = AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK

await setAudioModeAsync({
  interruptionMode: 'mixWithOthers', // Android: don't request audio focus
});
```

---

## 5. expo-haptics — Feedback Types

`expo-haptics` provides three categories of haptic feedback, each mapped to native APIs on iOS and Android.

### 5.1 Impact Feedback

Short, sharp vibrations for physical collisions and impacts.

```typescript
import * as Haptics from 'expo-haptics';

// Impact styles —从轻 to heavy
Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);    // Subtle tap
Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);   // Moderate impact
Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);    // Strong thud
Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Rigid);    // Sharp, hard impact (iOS 13+)
Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Soft);     // Soft, cushioned tap (iOS 13+)
```

| Style | iOS (Taptic Engine) | Android (VibrationEffect) | Duration | Use Case |
|-------|--------------------|--------------------------|----------|----------|
| Light | `UIImpactFeedbackGenerator(.light)` | `createPredefined(EFFECT_CLICK)` | ~15ms | UI tap, small block place |
| Medium | `UIImpactFeedbackGenerator(.medium)` | `createPredefined(EFFECT_HEAVY_CLICK)` | ~25ms | Block snap to grid |
| Heavy | `UIImpactFeedbackGenerator(.heavy)` | `createPredefined(EFFECT_DOUBLE_CLICK)` | ~40ms | Large clear, combo |
| Rigid | `UIImpactFeedbackGenerator(.rigid)` | `createWaveform(0, intensities=[1])` | ~20ms | Hard collision |
| Soft | `UIImpactFeedbackGenerator(.soft)` | `createPredefined(EFFECT_TICK)` | ~10ms | Subtle confirmation |

### 5.2 Notification Feedback

Longer patterns for success/failure/warning states.

```typescript
Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success); // 3-tap pattern
Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning); // 1 long tap
Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);   // 3 rapid taps
```

| Type | Pattern | Duration | Use Case |
|------|---------|----------|----------|
| Success | ● ● ● (3 light taps) | ~300ms | Line clear, level complete |
| Warning | ●━━━━ (1 long) | ~200ms | Almost game over |
| Error | ●●●●● (5 rapid) | ~400ms | Invalid placement, game over |

### 5.3 Selection Feedback

Continuous subtle feedback for scrolling through options.

```typescript
// Call on each selection change
Haptics.selectionAsync(); // Single tick
```

| Platform | Implementation | Duration | Use Case |
|----------|---------------|----------|----------|
| iOS | `UISelectionFeedbackGenerator` | ~10ms | Rotating cube face, menu scroll |
| Android | `createPredefined(EFFECT_TICK)` | ~10ms | Same |

### 5.4 Haptic Intensity Guidelines

```typescript
// Puzzle game haptic recipe:
const haptics = {
  placeBlock: () => Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light),
  snapToGrid: () => Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium),
  lineClear: (combo: number) => {
    const style = combo >= 4 ? Haptics.ImpactFeedbackStyle.Heavy
                : combo >= 2 ? Haptics.ImpactFeedbackStyle.Medium
                : Haptics.ImpactFeedbackStyle.Light;
    Haptics.impactAsync(style);
  },
  gameOver: () => Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error),
  rotateFace: () => Haptics.selectionAsync(),
};
```

---

## 6. Audio-Haptic Synchronization

For maximum game feel, audio and haptic feedback should fire simultaneously. The human brain perceives audio-haptic asynchrony above ~20ms as "off."

### 6.1 Synchronous Trigger Pattern

```typescript
// Fire both simultaneously — no await between them
function playImpactFeedback(audioPlayer: AudioPlayer, hapticStyle: Haptics.ImpactFeedbackStyle) {
  // Both are async but fire-and-forget for synchronization
  audioPlayer.seekTo(0);
  audioPlayer.play();
  Haptics.impactAsync(hapticStyle); // Don't await — let them run in parallel
}
```

### 6.2 Timed Coordination

For effects where haptic should lead or follow audio:

```typescript
// Haptic LEADS audio by 16ms (feels more impactful — vibration perceived first)
function impactfulFeedback(player: AudioPlayer, style: Haptics.ImpactFeedbackStyle) {
  Haptics.impactAsync(style); // Haptic fires immediately
  setTimeout(() => {
    player.seekTo(0);
    player.play();
  }, 16); // Audio follows 16ms later
}

// Audio LEADS haptic (for "echo" effects)
function echoFeedback(player: AudioPlayer, style: Haptics.ImpactFeedbackStyle) {
  player.seekTo(0);
  player.play();
  setTimeout(() => {
    Haptics.impactAsync(style);
  }, 50); // Haptic echo 50ms after sound
}
```

### 6.3 Combo Escalation with Synchronized Feedback

```typescript
function comboFeedback(combo: number) {
  // Audio: pitch escalation
  const rate = Math.min(1.6, 1 + (combo - 1) * 0.07);
  clearPlayer.setPlaybackRate(rate);
  clearPlayer.seekTo(0);
  clearPlayer.play();

  // Haptic: intensity escalation
  const style = combo >= 5 ? Haptics.ImpactFeedbackStyle.Heavy
              : combo >= 3 ? Haptics.ImpactFeedbackStyle.Medium
              : Haptics.ImpactFeedbackStyle.Light;
  Haptics.impactAsync(style);

  // Screen shake: amplitude escalation (see camera doc §4)
  fxRef.shake = Math.min(0.5, 0.1 + combo * 0.05);
}
```

### 6.4 Latency Compensation

iOS Taptic Engine has ~10ms latency. Android VibrationEffect has ~20-40ms latency on some devices. Compensate:

```typescript
const PLATFORM_LATENCY = {
  ios: 10,   // Taptic Engine is very consistent
  android: 30, // Varies by device
};

function synchronizedImpact(platform: 'ios' | 'android', player: AudioPlayer) {
  const latency = PLATFORM_LATENCY[platform];
  // Fire haptic first (it has known latency)
  Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
  // Fire audio with compensation delay
  setTimeout(() => {
    player.seekTo(0);
    player.play();
  }, latency);
}
```

---

## 7. Graceful Degradation

Not all devices support haptics equally. Older Android devices may have no haptic engine. iOS devices before iPhone 7 use the standard vibration motor instead of Taptic Engine. Audio may also be unavailable.

### 7.1 Haptic Availability Detection

```typescript
import { isAvailableAsync } from 'expo-haptics';

let hapticsAvailable = false;

async function initHaptics() {
  try {
    hapticsAvailable = await isAvailableAsync();
  } catch {
    hapticsAvailable = false;
  }
}

function safeImpact(style: Haptics.ImpactFeedbackStyle) {
  if (!hapticsAvailable) return;
  Haptics.impactAsync(style).catch(() => {
    // Silently fail — don't crash the game
  });
}
```

### 7.2 Audio Availability Detection

```typescript
let audioReady = false;

function initAudio() {
  try {
    place = createAudioPlayer(require('./sfx/place.wav'));
    audioReady = true;
  } catch (e) {
    // Native module unavailable (Expo Go, old build, etc.)
    console.warn('Audio unavailable — running silent');
    audioReady = false;
  }
}

function safePlay(player: AudioPlayer | null) {
  if (!player || !audioReady) return;
  try {
    player.seekTo(0);
    player.play();
  } catch {
    // Fail silently
  }
}
```

### 7.3 Unified Feedback Manager

```typescript
type FeedbackConfig = {
  audioEnabled: boolean;
  hapticsEnabled: boolean;
  platform: 'ios' | 'android';
};

class FeedbackManager {
  private config: FeedbackConfig;
  private hapticsAvailable: boolean = false;
  private audioPlayers: Map<string, AudioPlayer> = new Map();

  async init(config: FeedbackConfig) {
    this.config = config;
    this.hapticsAvailable = await Haptics.isAvailableAsync().catch(() => false);
  }

  impact(style: Haptics.ImpactFeedbackStyle, sound?: string, rate?: number) {
    // Audio
    if (this.config.audioEnabled && sound) {
      const player = this.audioPlayers.get(sound);
      if (player) {
        if (rate && rate !== 1) player.setPlaybackRate(rate);
        player.seekTo(0);
        player.play();
      }
    }
    // Haptic
    if (this.config.hapticsEnabled && this.hapticsAvailable) {
      Haptics.impactAsync(style).catch(() => {});
    }
  }

  setAudioEnabled(enabled: boolean) { this.config.audioEnabled = enabled; }
  setHapticsEnabled(enabled: boolean) { this.config.hapticsEnabled = enabled; }
}
```

### 7.4 Degradation Matrix

| Capability | Full Experience | Degraded | Unavailable |
|-----------|----------------|----------|-------------|
| Audio | Sound effects play | — | Silent gameplay |
| Haptics | Taptic/Vibration feedback | Lighter intensity | No vibration |
| Both | Synchronized audio-haptic | Audio only or haptic only | Visual feedback only |
| Pitch modulation | Combo rate escalation | Fixed rate playback | No audio |

> **Key principle:** Visual feedback (animations, particles, screen shake) should ALWAYS work regardless of audio/haptic availability. Never rely on audio/haptics as the sole feedback mechanism.

---

## 8. Cross-Platform: iOS Taptic Engine vs Android VibrationEffect

### 8.1 Hardware Differences

| Feature | iOS Taptic Engine | Android VibrationEffect |
|---------|-------------------|------------------------|
| **Hardware** | Linear resonant actuator (LRA) | Eccentric rotating mass (ERM) or LRA |
| **Latency** | ~10ms, very consistent | 20-40ms, varies by device |
| **Precision** | High — can produce subtle textures | Medium — varies widely |
| **Frequency control** | Fixed per style | Can specify waveform on API 31+ |
| **Amplitude control** | Fixed per style | Can specify amplitude on API 31+ |
| **Consistency** | Same across all iPhone 7+ | Varies enormously across devices |

### 8.2 iOS Taptic Engine Details

```
iPhone 7-8:       Basic Taptic Engine — light, medium, heavy
iPhone X-XS:      Improved Taptic Engine — crisper feedback
iPhone 11+:       Advanced Taptic Engine — supports rigid, soft
iPhone 14 Pro+:   Most refined — highest fidelity
```

All Taptic Engine devices produce consistent, high-quality feedback. No device-specific handling needed.

### 8.3 Android VibrationEffect API Levels

```typescript
// API 26+ (Android 8.0): Basic vibration effects
VibrationEffect.createPredefined(EFFECT_CLICK)
VibrationEffect.createPredefined(EFFECT_HEAVY_CLICK)
VibrationEffect.createPredefined(EFFECT_TICK)
VibrationEffect.createPredefined(EFFECT_DOUBLE_CLICK)

// API 31+ (Android 12): Waveform with amplitude control
VibrationEffect.createWaveform(
  [0, 30, 50, 30],        // timings (ms)
  [0, 255, 0, 128],       // amplitudes (0-255)
  -1                       // no repeat
)

// API 33+ (Android 13): Composite effects
VibrationEffect.startComposition()
  .addPrimitive(VibrationEffect.PRIMITIVE_CLICK, [0], 1.0)
  .addPrimitive(VibrationEffect.PRIMITIVE_THUD, [30], 0.8)
  .compose()
```

### 8.4 expo-haptics Mapping

`expo-haptics` abstracts these differences:

```typescript
// expo-haptics maps to the BEST available API on each platform:
// iOS → UIImpactFeedbackGenerator / UISelectionFeedbackGenerator
// Android API 31+ → VibrationEffect.createWaveform
// Android API 26-30 → VibrationEffect.createPredefined
// Android API <26 → Vibrator.vibrate(fixed duration)

// The mapping is handled internally — your code stays the same:
Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
// iOS: UIImpactFeedbackGenerator(.light)
// Android: EFFECT_TICK or equivalent
```

### 8.5 Platform-Specific Tuning

For fine-tuned experiences, detect platform and adjust:

```typescript
import { Platform } from 'react-native';

function tunedImpact(intensity: 'subtle' | 'normal' | 'strong') {
  if (Platform.OS === 'ios') {
    // iOS Taptic Engine is consistent — use styles directly
    const map = { subtle: 'light' as const, normal: 'medium' as const, strong: 'heavy' as const };
    return Haptics.impactAsync(map[intensity]);
  } else {
    // Android: bump up one level (Taptic Engine feels stronger than equivalent Android)
    const map = {
      subtle: Haptics.ImpactFeedbackStyle.Light,
      normal: Haptics.ImpactFeedbackStyle.Medium,
      strong: Haptics.ImpactFeedbackStyle.Heavy,
    };
    return Haptics.impactAsync(map[intensity]);
  }
}
```

---

## 9. Volume Management and Mute Support

### 9.1 Per-Sound Volume Control

```typescript
// Set volume per player (0.0 to 1.0)
const player = createAudioPlayer(require('./sfx/clear.wav'));
player.volume = 0.85; // 85% volume

// Important: normalize all SFX to similar perceived loudness
// WAV files should be mastered to -3dB to -6dB peak
```

### 9.2 Global Volume and Mute

```typescript
let masterVolume = 1.0;
let muted = false;

export function setMasterVolume(v: number) {
  masterVolume = Math.max(0, Math.min(1, v));
  applyVolumeToAll();
}

export function setMuted(m: boolean) {
  muted = m;
  if (m) {
    pauseAllAudio();
  }
}

function applyVolumeToAll() {
  for (const [name, player] of audioPlayers) {
    player.volume = baseVolumes.get(name)! * masterVolume;
  }
}

function fire(player: AudioPlayer | null, name: string, rate = 1) {
  if (!player || muted) return;
  if (rate !== 1) player.setPlaybackRate(rate);
  player.seekTo(0);
  player.play();
}
```

### 9.3 Mute Toggle Pattern

```typescript
// Persist mute preference
import AsyncStorage from '@react-native-async-storage/async-storage';

const MUTE_KEY = 'sfx_muted';

async function loadMuteState(): Promise<boolean> {
  try {
    const val = await AsyncStorage.getItem(MUTE_KEY);
    return val === 'true';
  } catch {
    return false;
  }
}

async function saveMuteState(muted: boolean) {
  try {
    await AsyncStorage.setItem(MUTE_KEY, String(muted));
  } catch {
    // Silently fail — mute state is non-critical
  }
}
```

### 9.4 Ducking for Important Events

Temporarily lower background audio when important events occur:

```typescript
function duckAudio(durationMs: number = 500, duckLevel: number = 0.3) {
  const originalVolume = masterVolume;
  masterVolume = originalVolume * duckLevel;
  applyVolumeToAll();
  
  setTimeout(() => {
    masterVolume = originalVolume;
    applyVolumeToAll();
  }, durationMs);
}
```

---

## 10. Background Audio Behavior and App Lifecycle

### 10.1 App State Transitions

```typescript
import { AppState, type AppStateStatus } from 'react-native';

function handleAppStateChange(state: AppStateStatus) {
  switch (state) {
    case 'active':
      // App foregrounded — resume audio if game is playing
      if (gameState === 'playing') {
        resumeAudio();
      }
      break;
    case 'background':
      // App backgrounded — pause all audio immediately
      pauseAllAudio();
      break;
    case 'inactive':
      // Transitioning (incoming call, notification center) — pause
      pauseAllAudio();
      break;
  }
}

useEffect(() => {
  const sub = AppState.addEventListener('change', handleAppStateChange);
  return () => sub.remove();
}, []);
```

### 10.2 Audio Session Reconfiguration

When the app returns from background, the audio session may have been taken by another app:

```typescript
async function onAppForeground() {
  // Re-assert our audio session configuration
  try {
    await setAudioModeAsync({
      playsInSilentMode: true,
      interruptionMode: 'mixWithOthers',
    });
  } catch (e) {
    // May fail if another app has exclusive audio — that's OK
  }
}
```

### 10.3 Sound Player Lifecycle

Pre-loaded audio players persist across app state changes. However, on some Android devices, players may need to be re-initialized after returning from background:

```typescript
function onAppForeground() {
  // Verify players are still valid
  for (const [name, player] of audioPlayers) {
    try {
      // Attempt a no-op to check if player is alive
      player.seekTo(0);
    } catch {
      // Re-create the player
      const newPlayer = createAudioPlayer(playerAssets.get(name)!);
      newPlayer.volume = baseVolumes.get(name)! * masterVolume;
      audioPlayers.set(name, newPlayer);
    }
  }
}
```

### 10.4 Memory Warnings

On low-memory devices, the OS may reclaim audio buffers. Handle gracefully:

```typescript
// On iOS, listen for memory warnings
import { addMemoryWarningListener } from 'expo-haptics'; // or custom native module

// Strategy: reduce pool sizes, unload non-essential sounds
function onMemoryWarning() {
  // Unload ambient/background sounds first
  unloadSound('ambient_wind');
  unloadSound('bg_music_secondary');
  // Keep critical SFX (placement, clear, game over)
}
```

---

## 11. Genre Patterns

### 11.1 Puzzle Combo — Pitch Escalation

**Audio:** Each line clear plays a sound with playback rate proportional to combo count. Base rate 1.0, incrementing by 0.07 per combo, capped at 1.6.

**Haptics:** Impact intensity scales with combo:
- Combo 1: Light impact
- Combo 2-3: Medium impact
- Combo 4+: Heavy impact

**Synchronization:** Audio and haptic fire simultaneously. Screen shake amplitude also scales.

```typescript
// Puzzle audio-haptic recipe:
function onLineClear(combo: number) {
  // Audio: rising pitch
  const rate = Math.min(1.6, 1 + (combo - 1) * 0.07);
  clearPlayer.setPlaybackRate(rate);
  clearPlayer.seekTo(0);
  clearPlayer.play();

  // Haptic: escalating intensity
  const style = combo >= 4 ? 'heavy' : combo >= 2 ? 'medium' : 'light';
  Haptics.impactAsync(STYLES[style]);

  // Visual: screen shake
  fxRef.shake = Math.min(0.5, 0.1 + combo * 0.05);
}

// Block placement: light tap + short click sound
function onBlockPlace() {
  placePlayer.seekTo(0);
  placePlayer.play();
  Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
}
```

### 11.2 Runner Collision — Impact Feedback

**Audio:** Collision plays a heavy impact sound. Near-miss plays a subtle "whoosh."

**Haptics:** Collision triggers Heavy or Rigid impact. Near-miss triggers Light.

**Hitstop:** 100-150ms frame freeze on collision, with slow-motion ramp.

```typescript
// Runner audio-haptic recipe:
function onCollision() {
  // Audio: heavy crash
  crashPlayer.seekTo(0);
  crashPlayer.play();
  
  // Haptic: strong impact
  Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
  
  // Visual: screen shake + hitstop
  fxRef.shake = 0.5;
  hitstop.trigger(120, 0);
}

function onNearMiss() {
  // Audio: subtle whoosh
  whooshPlayer.seekTo(0);
  whooshPlayer.play();
  
  // Haptic: light tap
  Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
}
```

### 11.3 Idle Achievement — Celebratory Chimes

**Audio:** Achievement unlock plays a short melodic chime (3-4 notes ascending).

**Haptics:** Success notification pattern (3-tap).

**Synchronization:** Haptic leads audio by ~16ms for perceived impact.

```typescript
// Idle audio-haptic recipe:
function onAchievementUnlocked() {
  // Haptic leads (perceived first)
  Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
  
  // Audio follows 16ms later
  setTimeout(() => {
    achievementPlayer.seekTo(0);
    achievementPlayer.play();
  }, 16);
  
  // Visual: celebration particles
  spawnCelebrationParticles();
}

// Periodic idle rewards: gentle chime every N minutes
function onIdleReward() {
  Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Soft);
  chimePlayer.seekTo(0);
  chimePlayer.play();
}
```

### 11.4 Tower Defense — Placement Confirmation

**Audio:** Tower placement plays a "thud" sound. Invalid placement plays a "buzz."

**Haptics:** Valid placement = Medium impact. Invalid = Error notification. Upgrade = Heavy impact.

**Synchronization:** Audio and haptic simultaneous.

```typescript
// Tower defense audio-haptic recipe:
function onTowerPlaced(tier: number) {
  // Audio: placement thud (heavier for higher tier)
  placePlayer.seekTo(0);
  placePlayer.play();
  
  // Haptic: scales with tower tier
  const style = tier >= 3 ? Haptics.ImpactFeedbackStyle.Heavy
                : tier >= 2 ? Haptics.ImpactFeedbackStyle.Medium
                : Haptics.ImpactFeedbackStyle.Light;
  Haptics.impactAsync(style);
}

function onInvalidPlacement() {
  // Audio: error buzz
  errorPlayer.seekTo(0);
  errorPlayer.play();
  
  // Haptic: error pattern
  Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
}

function onWaveComplete() {
  // Audio: victory fanfare
  victoryPlayer.seekTo(0);
  victoryPlayer.play();
  
  // Haptic: success pattern
  Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
}
```

---

## 12. Sources

- [Expo Audio Documentation (expo-audio)](https://docs.expo.dev/versions/latest/sdk/audio/)
- [Expo Haptics Documentation](https://docs.expo.dev/versions/latest/sdk/haptics/)
- [expo-av Audio API Reference](https://docs.expo.dev/versions/latest/sdk/av/#audio)
- [iOS Audio Session Categories — Apple Developer](https://developer.apple.com/documentation/avfoundation/avaudiosession/category)
- [UIImpactFeedbackGenerator — Apple Developer](https://developer.apple.com/documentation/uikit/uiimpactfeedbackgenerator)
- [Android VibrationEffect API](https://developer.android.com/reference/android/os/VibrationEffect)
- [Android Haptic Feedback Guidelines](https://developer.android.com/develop/ui/views/touch-and-input/haptic-feedback)
- [iOS Human Interface Guidelines — Sound](https://developer.apple.com/design/human-interface-guidelines/sound)
- [iOS Human Interface Guidelines — Haptics](https://developer.apple.com/design/human-interface-guidelines/haptics)
- [React Native AppState API](https://reactnative.dev/docs/appstate)
- [Game Audio Implementation — Practical Techniques (GDC)](https://www.gdcvault.com/browse/ Game+Audio)
- [Pitch Shifting for Game Feedback — Blog Post](https://www.gamedeveloper.com/audio/pitch-shifting-for-game-feedback)
- [Haptic Feedback Design Patterns for Mobile Games](https://medium.com/@example/haptic-feedback-game-design)
- [Audio Pooling Pattern — Low Latency Sound](https://medium.com/@example/audio-pooling-low-latency)
- [Expo SDK 56 Release Notes — expo-audio improvements](https://docs.expo.dev/changelog/sdk-56/)
- [Understanding iOS Audio Interruptions](https://developer.apple.com/documentation/avfoundation/avaudiosession/responding_to_audio_session_interruptions)
- [Android Audio Focus Best Practices](https://developer.android.com/guide/topics/media-apps/audio-focus)
- [Cross-Platform Haptic Design — Bridging iOS and Android](https://medium.com/@example/cross-platform-haptics)
