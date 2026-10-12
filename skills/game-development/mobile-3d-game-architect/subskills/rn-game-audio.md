# /rn-game-audio — Ses & Haptik Geri Bildirim

expo-audio, haptik feedback, pitch modülasyonu ve ses-haptic senkronizasyonu.

## A. expo-audio Kurulum

```typescript
import { createAudioPlayer, setAudioModeAsync, type AudioPlayer } from 'expo-audio';

// Audio session yapılandırması
await setAudioModeAsync({
  playsInSilentMode: true,        // iOS: silent switch'i yoksay
  interruptionMode: 'mixWithOthers', // Diğer uygulamalarla karıştır
});
```

## B. Player Pooling Pattern

Düşük gecikme için ses player'larını ön-hazırla:

```typescript
const SFX = {
  place: require('../assets/sfx/place.wav'),
  clear: require('../assets/sfx/clear.wav'),
  combo: require('../assets/sfx/combo.wav'),
  gameover: require('../assets/sfx/gameover.wav'),
};

// Player pool — her ses tipi için
const players: Map<string, AudioPlayer[]> = new Map();

function getPlayer(soundName: string): AudioPlayer | null {
  const pool = players.get(soundName);
  if (!pool) return null;
  
  // Boşta olan player'ı bul
  for (const p of pool) {
    if (!p.playing) return p;
  }
  return null;
}

function playSound(name: string, rate = 1.0) {
  const player = getPlayer(name);
  if (!player) return;
  
  player.seekTo(0);
  player.setPlaybackRate(rate);
  player.play();
}
```

## C. Pitch/Rate Modülasyonu

Combo feedback için ascending pitch:

```typescript
function playClearSound(combo: number) {
  // Combo arttıkça pitch artar → başarı hissi
  const rate = 1.0 + Math.min(combo - 1, 4) * 0.1; // 1.0 → 1.4
  playSound('clear', rate);
}
```

## D. Haptic Feedback (expo-haptics)

```typescript
import * as Haptics from 'expo-haptics';

// Selection feedback — drag/place
Haptics.selectionAsync();

// Impact feedback — clear/combo
Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);

// Notification feedback — game over/achievement
Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
```

## E. Ses-Haptic Senkronizasyonu

Eşzamanlı tetikleme için aynı anda çağır:

```typescript
function onPiecePlaced() {
  playSound('place');
  Haptics.selectionAsync(); // Aynı anda
}

function onLineClear(combo: number) {
  playClearSound(combo);
  Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
}
```

## F. Graceful Degradation

Ses/haptic yoksa oyunu engelleme:

```typescript
let audioAvailable = false;

try {
  await setAudioModeAsync({ playsInSilentMode: true });
  audioAvailable = true;
} catch {
  audioAvailable = false;
}

function safePlaySound(name: string, rate = 1.0) {
  if (!audioAvailable) return;
  try {
    playSound(name, rate);
  } catch {
    // Sessizce devam et
  }
}
```

## G. Ses Gecikmesi Hedefleri

| Kütüphane | İlk Çalma | Sonraki |
|-----------|-----------|---------|
| `expo-av` | ~50-100ms | ~20-50ms |
| `expo-audio` | ~10-30ms | ~5-15ms |

**Öneri:** Expo SDK 55+ için `expo-audio` kullan.

## H. iOS vs Android Farkları

| Özellik | iOS | Android |
|---------|-----|---------|
| Haptic Engine | Taptic Engine (precise) | VibrationEffect (vary by device) |
| Silent Mode | `playsInSilentMode: true` | N/A |
| Interruption | `mixWithOthers` | `mixWithOthers` |
| Feedback Style | Light/Medium/Heavy | Light/Medium/Heavy |

## I. Yaygın Tuzaklar

- Her ses için yeni `Sound` objesi → yüksek gecikme, bellek sızıntısı
- `seekTo(0)` unutulursa → ses çalmaz (sondan başlar)
- Haptic önceden hazırlanmaz → ilk çağrıda gecikme
- Audio session yapılandırılmaz → iOS'ta sessiz modda ses yok
- Player pool boyutu küçük → eşzamanlı sesler atlanır

## Referans Doküman
- [`mobile_audio_haptics_game_feel.md`](../researches/mobile_audio_haptics_game_feel.md)
