# /unity-expert-audio - Mobile Engine Audio & Haptics Pipeline

Gerçekçi motor akustiği ve platformlar arası dokunsal (haptic) his.

## Audio & Haptic Standartları

1. **Motor Pitch Modülasyonu**: `Pitch = P_min + (P_max - P_min) * (V / V_max)` + RPM vites eğrileri ve `Mathf.SmoothDamp`.
2. **3D Spatial Audio & Doppler**: 3D spatial blend (1.0), özel mesafe attenuation eğrileri, geçen trafik için Doppler seviyesi ayarı.
3. **Audio Mixer Ducking**: Bullet-time ve crash sekanslarında low-pass filtre süpürmesi (`22kHz → 800Hz`).
4. **Cross-Platform Haptics**: iOS `UIImpactFeedbackGenerator` & Android `VibrationEffect` — `MobileHapticBridge.cs` üzerinden.

## Referans Dokümanlar
- [`mobile_audio_and_haptics.md`](../researches/mobile_audio_and_haptics.md)
- [`aaa_audio_satisfaction_research.md`](../researches/aaa_audio_satisfaction_research.md)
