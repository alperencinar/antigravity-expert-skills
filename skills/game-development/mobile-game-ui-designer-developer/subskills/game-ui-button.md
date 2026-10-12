# /game-ui-button — Butonlar, Dokunuş & Geri Bildirim

Oyun butonlarını spring animasyonlu, haptic+audio geri bildirimli ve cooldown korumalı tasarla.

## A. Pressable + Spring Animasyon
```typescript
function GameButton({ onPress, label, icon }: ButtonProps) {
  const scale = useRef(new Animated.Value(1)).current;
  const handlePressIn = () => {
    Animated.spring(scale, { toValue: 0.92, friction: 5, useNativeDriver: true }).start();
  };
  const handlePressOut = () => {
    Animated.spring(scale, { toValue: 1, friction: 5, tension: 120, useNativeDriver: true }).start();
  };
  return (
    <Pressable onPressIn={handlePressIn} onPressOut={handlePressOut} onPress={onPress}
      hitSlop={8} accessibilityRole="button" accessibilityLabel={label}>
      <Animated.View style={{ transform: [{ scale }] }}>
        <Text>{icon}</Text><Text>{label}</Text>
      </Animated.View>
    </Pressable>
  );
}
```

## B. Haptic Geri Bildirim
```typescript
import * as Haptics from 'expo-haptics';
Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light); // Buton basımı
Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success); // Başarı
Haptics.selectionAsync(); // Kaydırma
```

## C. Cooldown State
```typescript
const [cooldown, setCooldown] = useState(false);
const handlePress = () => {
  if (cooldown) return;
  setCooldown(true); onPress();
  setTimeout(() => setCooldown(false), 300);
};
```

## D. Touch Target Kuralları
- Minimum **44×44pt** (Apple HIG) / **48×48dp** (Material)
- `hitSlop={8}` ile görsel boyuttan bağımsız dokunuş alanı

## E. Yaygın Tuzaklar
- ❌ `TouchableOpacity` yerine `Pressable` kullan
- ❌ `useNativeDriver: true` unutma
- ✅ `accessibilityRole="button"` MUTLAKA

## Referans
- [`rn_responsive_ui_game_hud.md`](../researches/rn_responsive_ui_game_hud.md) — Bölüm 6, 8
