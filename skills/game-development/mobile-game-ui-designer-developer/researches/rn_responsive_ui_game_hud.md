# React Native + Three.js: Responsive UI, Game HUD & Input Handling

> **Scope:** General-purpose reference for building responsive game UIs, HUD systems, modal navigation, gesture handling, accessibility, and overlay patterns in React Native + Three.js mobile games.
>
> **Audience:** Mobile game developers building cross-device experiences (phone/tablet, 16:9 to 21:9) with React Native overlays on Three.js canvases.

---

## Table of Contents

1. [SafeArea, Dimensions, and PixelRatio for Game HUD](#1-safearea-dimensions-and-pixelratio-for-game-hud)
2. [Multi-Device Responsive Layout](#2-multi-device-responsive-layout)
3. [HUD Architecture: Score, Combo, Health, Currency](#3-hud-architecture-score-combo-health-currency)
4. [Modal Navigation Stack Implementation](#4-modal-navigation-stack-implementation)
5. [StatusBar Handling in Fullscreen Games](#5-statusbar-handling-in-fullscreen-games)
6. [Performance Isolation: React.memo, useMemo, useCallback](#6-performance-isolation-reactmemo-usememo-usecallback)
7. [Gesture Handling with 3D Scenes](#7-gesture-handling-with-3d-scenes)
8. [Accessibility: Screen Readers, WCAG Contrast](#8-accessibility-screen-readers-wcag-contrast)
9. [RTL Layout Support and i18n](#9-rtl-layout-support-and-i18n)
10. [Overlay Patterns: RN Views over Three.js Canvas](#10-overlay-patterns-rn-views-over-threejs-canvas)
11. [drei/Html for World-Space UI](#11-dreihtml-for-world-space-ui)
12. [Genre Patterns](#12-genre-patterns)
13. [Sources](#13-sources)

---

## 1. SafeArea, Dimensions, and PixelRatio for Game HUD

### Safe Area Handling

Games must account for notches, dynamic islands, and home indicators. Use `react-native-safe-area-context` for reliable insets.

```typescript
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { View, StyleSheet } from 'react-native';

function GameHUD() {
  const insets = useSafeAreaInsets();

  return (
    <View style={[
      styles.hud,
      {
        paddingTop: insets.top,     // Avoid notch/dynamic island
        paddingBottom: insets.bottom, // Avoid home indicator
        paddingLeft: insets.left,    // Landscape safe area
        paddingRight: insets.right,
      }
    ]}>
      <ScoreDisplay />
      <ComboMeter />
    </View>
  );
}

const styles = StyleSheet.create({
  hud: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    zIndex: 10,
  },
});
```

### Dimensions API

```typescript
import { Dimensions, useWindowDimensions } from 'react-native';

// Static (use at module level for constants)
const { width: SCREEN_W, height: SCREEN_H } = Dimensions.get('window');

// Dynamic (reactive to rotation/fold)
function ResponsiveLayout() {
  const { width, height } = useWindowDimensions();
  const isTablet = width >= 768;
  const isLandscape = width > height;
  const aspectRatio = width / height;

  return (
    <View style={{
      flex: 1,
      padding: isTablet ? 24 : 12,
      flexDirection: isLandscape ? 'row' : 'column',
    }}>
      {/* Game content */}
    </View>
  );
}
```

### PixelRatio for Crisp Rendering

```typescript
import { PixelRatio } from 'react-native';

// Round to nearest pixel for crisp 1px borders
function pixelPerfect(value: number): number {
  return Math.round(value * PixelRatio.get());
}

// Get optimal image size for asset loading
function optimalAssetSize(logicalSize: number): number {
  return Math.round(logicalSize * PixelRatio.get());
}

// For Three.js canvas: match device pixel ratio
const dpr = Math.min(PixelRatio.get(), 2); // Cap at 2x for mobile perf
```

### Combined Hook for Game Layout

```typescript
function useGameLayout() {
  const insets = useSafeAreaInsets();
  const { width, height } = useWindowDimensions();
  const dpr = PixelRatio.get();

  const isTablet = Math.min(width, height) >= 600;
  const isLandscape = width > height;
  const aspectRatio = width / height;

  // Scale factors relative to iPhone 14 (390×844)
  const scaleX = width / 390;
  const scaleY = height / 844;
  const scale = Math.min(scaleX, scaleY);

  return {
    width, height, dpr,
    insets,
    isTablet, isLandscape, aspectRatio,
    scale,
    // HUD-specific computed values
    hudTop: insets.top + 8,
    trayHeight: isTablet ? 180 : 150,
    canvasHeight: height - insets.top - insets.bottom - (isTablet ? 180 : 150),
  };
}
```

---

## 2. Multi-Device Responsive Layout

### Device Tier Classification

```typescript
type DeviceTier = 'phone-small' | 'phone' | 'tablet' | 'tablet-large';

function getDeviceTier(width: number, height: number): DeviceTier {
  const shortest = Math.min(width, height);
  if (shortest < 375) return 'phone-small';  // iPhone SE, small Android
  if (shortest < 600) return 'phone';         // Standard phones
  if (shortest < 900) return 'tablet';        // iPad Mini, small tablets
  return 'tablet-large';                       // iPad Pro, large tablets
}
```

### Aspect Ratio Adaptation (16:9 to 21:9)

```typescript
function useAspectRatio() {
  const { width, height } = useWindowDimensions();
  const ratio = width / height;

  // Common ratios:
  // 16:9 = 1.778  (standard)
  // 18:9 = 2.0    (Samsung)
  // 19.5:9 = 2.167 (iPhone 14+)
  // 21:9 = 2.333  (ultrawide)

  const isUltraWide = ratio > 2.1;
  const isNarrow = ratio < 1.7;

  return {
    ratio,
    isUltraWide,
    isNarrow,
    // Content width as fraction of screen (leave margins on ultrawide)
    contentWidth: isUltraWide ? width * 0.85 : width,
    contentOffset: isUltraWide ? width * 0.075 : 0,
  };
}
```

### Responsive Style Helper

```typescript
function responsive(base: number, scale: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, base * scale));
}

// Usage
const fontSize = responsive(44, layout.scale, 32, 64);
const padding = responsive(16, layout.scale, 10, 28);
const trayHeight = responsive(150, layout.scale, 120, 220);
```

### Canvas Sizing for 3D Scene

```typescript
function useCanvasSize() {
  const { width, height } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const layout = useGameLayout();

  return {
    // Canvas fills remaining space after HUD and tray
    width: width,
    height: height - insets.top - layout.trayHeight - layout.hudTop,
    // Three.js camera adjustments
    aspect: width / (height - insets.top - layout.trayHeight - layout.hudTop),
  };
}
```

---

## 3. HUD Architecture: Score, Combo, Health, Currency

### Score Display with Animated Counter

An animated score counter prevents jarring jumps and provides satisfying feedback.

```typescript
import { useEffect, useRef, useState } from 'react';
import { Animated, Text } from 'react-native';

function ScoreCounter({ score }: { score: number }) {
  const [display, setDisplay] = useState(0);
  const prevRef = useRef(0);
  const rafRef = useRef(0);
  const pulse = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    const from = prevRef.current;
    const to = score;
    if (to === from) return;

    // Pulse animation on score change
    pulse.setValue(1.16);
    Animated.spring(pulse, {
      toValue: 1, useNativeDriver: true, friction: 4, tension: 140,
    }).start();

    // Smooth count-up animation
    const start = Date.now();
    const duration = Math.min(600, 220 + (to - from) * 1.5);
    let last = -1;

    const tick = () => {
      const elapsed = Math.min(1, (Date.now() - start) / duration);
      // Ease-out cubic
      const value = Math.round(from + (to - from) * (1 - Math.pow(1 - elapsed, 3)));
      if (value !== last) {
        last = value;
        prevRef.current = value;
        setDisplay(value);
      }
      if (elapsed < 1) rafRef.current = requestAnimationFrame(tick);
    };

    cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [score, pulse]);

  return (
    <Animated.Text style={[
      styles.score,
      { transform: [{ scale: pulse }] },
    ]}>
      {display}
    </Animated.Text>
  );
}
```

### Combo Meter with Escalating Visuals

```typescript
function comboColor(combo: number): string {
  if (combo >= 10) return `hsl(${(combo * 137) % 360}, 100%, 62%)`;
  if (combo >= 8) return '#ff3b48';
  if (combo >= 6) return '#ff8e3c';
  if (combo >= 4) return '#ffd23f';
  return '#7fd4ff';
}

function ComboMeter({ combo }: { combo: number }) {
  const scale = useRef(new Animated.Value(0)).current;
  const loopRef = useRef<Animated.CompositeAnimation | null>(null);

  useEffect(() => {
    if (combo > 1) {
      scale.setValue(1.35 + Math.min(combo, 10) * 0.07);
      Animated.spring(scale, {
        toValue: 1, useNativeDriver: true, friction: 4, tension: 110,
      }).start();
    } else {
      scale.setValue(0);
    }

    // Continuous pulse at high combos
    loopRef.current?.stop();
    if (combo >= 8) {
      loopRef.current = Animated.loop(Animated.sequence([
        Animated.timing(scale, { toValue: 1.09, duration: 380, useNativeDriver: true }),
        Animated.timing(scale, { toValue: 1, duration: 380, useNativeDriver: true }),
      ]));
      loopRef.current.start();
    }
  }, [combo, scale]);

  if (combo <= 1) return null;

  return (
    <Animated.Text style={{
      color: comboColor(combo),
      fontSize: 30 + Math.min(combo, 14) * 3,
      fontWeight: '900',
      textShadowColor: comboColor(combo),
      textShadowRadius: 10 + Math.min(combo, 12) * 2,
      transform: [{ scale }],
    }}>
      {combo}×
    </Animated.Text>
  );
}
```

### Health Bar Component

```typescript
function HealthBar({ current, max, width = 200 }: { current: number; max: number; width?: number }) {
  const ratio = current / max;
  const barColor = ratio > 0.5 ? '#4cd964' : ratio > 0.25 ? '#ffd23f' : '#ff3b30';

  return (
    <View style={[styles.healthBarBg, { width }]}>
      <Animated.View style={{
        width: width * ratio,
        height: '100%',
        backgroundColor: barColor,
        borderRadius: 4,
      }} />
      <Text style={styles.healthText}>{current}/{max}</Text>
    </View>
  );
}
```

### Currency Display

```typescript
function CurrencyDisplay({ amount, icon }: { amount: number; icon: string }) {
  const [animated, setAnimated] = useState(false);
  const scale = useRef(new Animated.Value(1)).current;

  // Bounce on change
  useEffect(() => {
    scale.setValue(1.2);
    Animated.spring(scale, {
      toValue: 1, useNativeDriver: true, friction: 5, tension: 120,
    }).start();
  }, [amount, scale]);

  return (
    <Animated.View style={{
      flexDirection: 'row', alignItems: 'center',
      transform: [{ scale }],
      backgroundColor: 'rgba(0,0,0,0.3)',
      borderRadius: 16, paddingHorizontal: 12, paddingVertical: 6,
    }}>
      <Text style={{ fontSize: 18, marginRight: 6 }}>{icon}</Text>
      <Text style={{ color: '#fff', fontSize: 18, fontWeight: '900' }}>
        {amount.toLocaleString()}
      </Text>
    </Animated.View>
  );
}
```

---

## 4. Modal Navigation Stack Implementation

### Phase-Based Modal State Machine

For games, a full navigation stack is overkill. A phase-based state machine is simpler and more performant.

```typescript
type GamePhase = 'menu' | 'playing' | 'paused' | 'settings' | 'gameover' | 'revive' | 'result';

function useGamePhase() {
  const [phase, setPhase] = useState<GamePhase>('menu');
  const prevPhase = useRef<GamePhase>('menu');

  const transition = useCallback((next: GamePhase) => {
    prevPhase.current = phase;
    setPhase(next);
  }, [phase]);

  const goBack = useCallback(() => {
    setPhase(prevPhase.current);
  }, []);

  return { phase, transition, goBack, prevPhase: prevPhase.current };
}
```

### Modal Overlay Pattern

```typescript
function GameModals({ phase, transition }: { phase: GamePhase; transition: (p: GamePhase) => void }) {
  return (
    <>
      {/* Settings modal */}
      {phase === 'settings' && (
        <View style={styles.scrim} pointerEvents="box-none">
          <View style={styles.modalPanel}>
            <SettingsContent onClose={() => transition('playing')} />
          </View>
        </View>
      )}

      {/* Game over with revive option */}
      {phase === 'revive' && (
        <View style={styles.fullOverlay}>
          <RevivePanel
            onContinue={() => transition('playing')}
            onDecline={() => transition('result')}
          />
        </View>
      )}

      {/* Final result screen */}
      {phase === 'result' && (
        <View style={styles.fullOverlay}>
          <ResultScreen
            onReplay={() => transition('playing')}
            onHome={() => transition('menu')}
          />
        </View>
      )}
    </>
  );
}
```

### Animated Modal Transitions

```typescript
function AnimatedModal({ visible, children }: { visible: boolean; children: React.ReactNode }) {
  const opacity = useRef(new Animated.Value(0)).current;
  const scale = useRef(new Animated.Value(0.9)).current;

  useEffect(() => {
    if (visible) {
      Animated.parallel([
        Animated.timing(opacity, { toValue: 1, duration: 200, useNativeDriver: true }),
        Animated.spring(scale, { toValue: 1, friction: 6, tension: 100, useNativeDriver: true }),
      ]).start();
    } else {
      Animated.timing(opacity, { toValue: 0, duration: 150, useNativeDriver: true }).start();
    }
  }, [visible, opacity, scale]);

  if (!visible && opacity.__getValue() === 0) return null;

  return (
    <Animated.View style={{ opacity, transform: [{ scale }] }}>
      {children}
    </Animated.View>
  );
}
```

---

## 5. StatusBar Handling in Fullscreen Games

### Expo StatusBar Configuration

```typescript
import { StatusBar } from 'expo-status-bar';

function GameStatusBar({ isMenu }: { isMenu: boolean }) {
  return (
    <StatusBar
      style="light"          // Light text on dark background
      hidden={false}         // Keep visible for games (hide for cinematic)
      translucent            // Allow content behind status bar
      backgroundColor="transparent"
    />
  );
}
```

### Immersive Mode (Android)

```typescript
import { Platform } from 'react-native';

function enableImmersiveMode() {
  if (Platform.OS === 'android') {
    // Hide system UI for fullscreen gameplay
    // Use expo-system-ui or native module
    // SystemUI.setNavigationBarVisibility(false);
    // SystemUI.setStatusBarVisibility(false);
  }
}
```

### Dynamic StatusBar Based on Screen

```typescript
function useStatusBarConfig(screen: string) {
  useEffect(() => {
    // Menu: light content (dark bg)
    // Game: light content (varies by theme)
    // Result: light content (dark overlay)
  }, [screen]);

  return <StatusBar style="light" />;
}
```

---

## 6. Performance Isolation: React.memo, useMemo, useCallback

### Preventing Unnecessary Re-renders

In a game with frequent state updates (60fps animations, score changes), preventing cascading re-renders is critical.

```typescript
// BAD: This component re-renders on EVERY state change
function BadHUD({ score, combo, theme }: { score: number; combo: number; theme: number }) {
  return (
    <View>
      <Text>{score}</Text>
      <Text>{combo}×</Text>
    </View>
  );
}

// GOOD: Memoized, only re-renders when its own props change
const GoodHUD = React.memo(function GoodHUD({ score, combo }: { score: number; combo: number }) {
  return (
    <View>
      <ScoreCounter score={score} />
      <ComboMeter combo={combo} />
    </View>
  );
});
```

### Zustand Selector Isolation

```typescript
// BAD: Subscribes to entire state → re-renders on any change
const { score, combo, theme } = useGame();

// GOOD: Granular selectors → only re-renders when selected value changes
const score = useGame((s) => s.score);
const combo = useGame((s) => s.combo);
const theme = useGame((s) => s.theme);

// EVEN BETTER: Subscribe to side effects without re-render
useEffect(
  () => useGame.subscribe((state, prev) => {
    if (state.flash !== prev.flash && state.flash.length) {
      playClearSound(state.combo);
    }
  }),
  [],
);
```

### Expensive Computation Memoization

```typescript
// Memoize piece bounds calculation
const { w, h } = useMemo(() => pieceBounds(piece.cells), [piece.cells]);

// Memoize PanResponder (expensive to create)
const panResponder = useMemo(
  () => PanResponder.create({
    onStartShouldSetPanResponderCapture: () => true,
    onMoveShouldSetPanResponderCapture: () => true,
    onPanResponderGrant: handleGrant,
    onPanResponderMove: handleMove,
    onPanResponderRelease: handleRelease,
  }),
  [], // Empty deps: created once, handlers use refs for current values
);
```

### Component-Level State for Local Updates

```typescript
// PERF: Score counter manages its own display state.
// When score changes, ONLY this small component re-renders,
// not the entire App tree.
function ScoreCounter({ score }: { score: number }) {
  const [display, setDisplay] = useState(0);
  // ... animation logic
  return <Animated.Text>{display}</Animated.Text>;
}
```

---

## 7. Gesture Handling with 3D Scenes

### PanResponder for Drag + Rotate

The key challenge: distinguishing between piece dragging and cube rotation on the same touch surface.

```typescript
type DragMode = 'piece' | 'rotate' | null;

function useGameGestures(canvasRect: Rect, trayRects: Record<number, Rect>) {
  const dragMode = useRef<DragMode>(null);
  const lastRot = useRef({ x: 0, y: 0 });
  const ROTATION_SENSITIVITY = 0.009; // radians per pixel

  const panResponder = useMemo(
    () => PanResponder.create({
      onStartShouldSetPanResponderCapture: () => true,
      onMoveShouldSetPanResponderCapture: () => true,

      onPanResponderGrant: (e: GestureResponderEvent) => {
        const { pageX: px, pageY: py } = e.nativeEvent;

        // Check if touch is on a tray piece
        for (const [index, rect] of Object.entries(trayRects.current)) {
          const HIT_PAD = 22; // Enlarged hit area for touch
          const within =
            px >= rect.x - HIT_PAD && px <= rect.x + rect.w + HIT_PAD &&
            py >= rect.y - HIT_PAD && py <= rect.y + rect.h + HIT_PAD;

          if (within) {
            dragMode.current = 'piece';
            // Set up drag state...
            return;
          }
        }

        // Empty area → rotate mode
        dragMode.current = 'rotate';
        lastRot.current = { x: px, y: py };
      },

      onPanResponderMove: (_e, gesture) => {
        if (dragMode.current === 'piece') {
          // Update drag position
          dragRef.pageX = gesture.moveX;
          dragRef.pageY = gesture.moveY;
        } else if (dragMode.current === 'rotate') {
          // Horizontal drag → yaw rotation
          const dx = gesture.moveX - lastRot.current.x;
          cubeRef.yaw += dx * ROTATION_SENSITIVITY;
          cubeRef.yawVel = dx * ROTATION_SENSITIVITY * 0.6 + cubeRef.yawVel * 0.4;
          lastRot.current = { x: gesture.moveX, y: gesture.moveY };
        }
      },

      onPanResponderRelease: () => {
        if (dragMode.current === 'rotate') {
          cubeRef.dragging = false; // Enable momentum + snap
        }
        dragMode.current = null;
      },

      onPanResponderTerminate: () => {
        dragMode.current = null;
      },
    }),
    [], // Stable: use refs for mutable state
  );

  return panResponder;
}
```

### Touch Overlay Pattern

The gesture layer must sit ABOVE the Canvas but be transparent:

```typescript
function GameScreen() {
  const panResponder = useGameGestures(canvasRect, trayRects);

  return (
    <View style={{ flex: 1 }}>
      {/* 3D Canvas layer */}
      <View style={{ flex: 1 }}>
        <Canvas camera={{ position: [0, -2.2, 6.2], fov: 45 }}>
          <Scene />
        </Canvas>
      </View>

      {/* HUD layer (pointerEvents="none" — touches pass through) */}
      <View style={[styles.hud, { pointerEvents: 'none' }]}>
        <ScoreCounter score={score} />
      </View>

      {/* Gesture capture layer (transparent, catches ALL touches) */}
      <View
        style={StyleSheet.absoluteFill}
        pointerEvents="box-only"
        {...panResponder.panHandlers}
      />
    </View>
  );
}
```

### react-native-gesture-handler Integration

For complex gesture combinations (pinch + pan, simultaneous gestures):

```typescript
import { GestureDetector, Gesture } from 'react-native-gesture-handler';

function GameGestureLayer() {
  const panGesture = Gesture.Pan()
    .onStart((e) => handleTouchStart(e.absoluteX, e.absoluteY))
    .onUpdate((e) => handleTouchMove(e.absoluteX, e.absoluteY))
    .onEnd(() => handleTouchEnd());

  const pinchGesture = Gesture.Pinch()
    .onUpdate((e) => handleZoom(e.scale));

  const composed = Gesture.Simultaneous(panGesture, pinchGesture);

  return (
    <GestureDetector gesture={composed}>
      <View style={StyleSheet.absoluteFill} />
    </GestureDetector>
  );
}
```

### Canvas Layout Measurement

```typescript
function useCanvasMeasurement() {
  const canvasRef = useRef<View>(null);
  const [rect, setRect] = useState({ x: 0, y: 0, w: 0, h: 0 });

  const onLayout = useCallback(() => {
    canvasRef.current?.measureInWindow((x, y, width, height) => {
      if (!width || !height) {
        console.warn('Canvas measured 0 — scene may not render');
        return;
      }
      setRect({ x, y, w: width, h: height });
      // Store for gesture coordinate conversion
      dragRef.canvas = { x, y, w: width, h: height };
    });
  }, []);

  return { canvasRef, rect, onLayout };
}
```

---

## 8. Accessibility: Screen Readers, WCAG Contrast

### AccessibilityInfo for Screen Reader Detection

```typescript
import { AccessibilityInfo, findNodeHandle } from 'react-native';

function useScreenReader() {
  const [screenReaderEnabled, setScreenReaderEnabled] = useState(false);

  useEffect(() => {
    AccessibilityInfo.isScreenReaderEnabled().then(setScreenReaderEnabled);

    const subscription = AccessibilityInfo.addEventListener(
      'screenReaderChanged',
      setScreenReaderEnabled,
    );

    return () => subscription.remove();
  }, []);

  return screenReaderEnabled;
}
```

### Accessible Game HUD

```typescript
function AccessibleHUD({ score, combo, gameOver }: { score: number; combo: number; gameOver: boolean }) {
  const screenReader = useScreenReader();

  return (
    <View
      accessibilityRole="summary"
      accessibilityLabel={`Score: ${score}. Combo: ${combo}x.`}
      accessibilityHint="Game status display"
      importantForAccessibility={screenReader ? 'yes' : 'no-hide-descendants'}
    >
      {/* Visual elements (hidden from screen reader) */}
      <ScoreCounter score={score} />
      <ComboMeter combo={combo} />

      {/* Announce game over */}
      {gameOver && (
        <Text
          accessibilityRole="alert"
          accessibilityLabel="Game over"
        >
          GAME OVER
        </Text>
      )}
    </View>
  );
}
```

### WCAG Color Contrast

Game text must meet WCAG 2.1 AA standards (4.5:1 for normal text, 3:1 for large text).

```typescript
// Contrast ratio calculation
function luminance(r: number, g: number, b: number): number {
  const [rs, gs, bs] = [r, g, b].map(c => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

function contrastRatio(fg: [number, number, number], bg: [number, number, number]): number {
  const l1 = luminance(...fg);
  const l2 = luminance(...bg);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

// Ensure text is readable against game background
function ensureContrast(textColor: string, bgColor: string): string {
  // If contrast is insufficient, lighten/darken text
  const ratio = contrastRatio(hexToRgb(textColor), hexToRgb(bgColor));
  if (ratio >= 4.5) return textColor;
  // Adjust...
  return ratio < 4.5 ? '#ffffff' : textColor;
}
```

### Accessible Buttons

```typescript
function AccessibleButton({ onPress, label, icon }: { onPress: () => void; label: string; icon: string }) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityHint={`Activates ${label}`}
      hitSlop={8} // Minimum 44×44pt touch target
      style={({ pressed }) => [
        styles.button,
        pressed && { opacity: 0.8 },
      ]}
    >
      <Text style={styles.buttonIcon} aria-hidden="true">{icon}</Text>
      <Text style={styles.buttonLabel}>{label}</Text>
    </Pressable>
  );
}
```

---

## 9. RTL Layout Support and i18n

### RTL-Aware Layout

```typescript
import { I18nManager } from 'react-native';

function RTLAwareRow({ children, style }: { children: React.ReactNode; style?: any }) {
  return (
    <View style={[
      { flexDirection: I18nManager.isRTL ? 'row-reverse' : 'row' },
      style,
    ]}>
      {children}
    </View>
  );
}
```

### Force LTR for Game Elements

Some game elements should NOT flip in RTL (e.g., score progression left-to-right):

```typescript
function GameScoreBar({ score }: { score: number }) {
  return (
    <View style={{ flexDirection: 'row' }} // Always LTR for score progression
      collapsable={false}
    >
      <Text>0</Text>
      <View style={{ flex: 1 }}>
        <View style={{ width: `${Math.min(100, score / 100)}%` }} />
      </View>
      <Text>100</Text>
    </View>
  );
}
```

### Localization Pattern

```typescript
const STRINGS = {
  en: { score: 'SCORE', combo: 'COMBO', gameOver: 'GAME OVER', tryAgain: 'TRY AGAIN' },
  tr: { score: 'SKOR', combo: 'KOMBO', gameOver: 'OYUN BİTTİ', tryAgain: 'TEKRAR DENE' },
  ar: { score: 'النقاط', combo: 'كومبو', gameOver: 'انتهت اللعبة', tryAgain: 'حاول مرة أخرى' },
};

function useStrings() {
  const locale = I18nManager.isRTL ? 'ar' : 'en';
  return STRINGS[locale] || STRINGS.en;
}
```

---

## 10. Overlay Patterns: RN Views over Three.js Canvas

### Layer Architecture

The standard pattern layers RN views on top of the Three.js Canvas:

```typescript
function GameScreen() {
  return (
    <View style={{ flex: 1, backgroundColor: '#000' }}>
      {/* Layer 0: 3D Canvas (fills entire screen) */}
      <View style={StyleSheet.absoluteFill}>
        <Canvas>
          <Scene />
        </Canvas>
      </View>

      {/* Layer 1: HUD (absolute positioned, pointerEvents="none") */}
      <View style={[StyleSheet.absoluteFill, { pointerEvents: 'none' }]}>
        <GameHUD />
      </View>

      {/* Layer 2: Interactive overlays (settings, modals) */}
      {settingsOpen && <SettingsPanel />}

      {/* Layer 3: Gesture capture (transparent, catches all input) */}
      <View style={StyleSheet.absoluteFill} {...panResponder.panHandlers} />
    </View>
  );
}
```

### Pointer Events Strategy

| Layer | pointerEvents | Purpose |
|-------|--------------|---------|
| Canvas | `box-only` | Receives no direct touches (gestures via overlay) |
| HUD | `none` | Visual only, touches pass through |
| Modals | `auto` | Interactive, blocks touches to layers below |
| Gesture overlay | `box-only` | Captures all touches for game input |
| Buttons | `auto` | Individual interactive elements |

### Performance: Avoid Re-rendering Canvas

```typescript
// The Canvas component should NOT re-render when HUD state changes.
// Wrap in React.memo and pass only 3D-relevant props.
const MemoizedCanvas = React.memo(function MemoizedCanvas() {
  return (
    <Canvas camera={{ position: [0, -2.2, 6.2], fov: 45 }}>
      <Scene />
    </Canvas>
  );
});
```

---

## 11. drei/Html for World-Space UI

### Limitations in React Native

`drei/Html` renders DOM elements positioned in 3D space. However, in React Native (Expo), the DOM is not available.

**What works:**
- `@react-three/drei/native` — limited native-compatible subset
- `Html` component is NOT available in `@react-three/drei/native`

**Alternative approaches for RN:**

### Screen-Projected Positioning

Convert 3D world positions to 2D screen coordinates for RN overlay positioning:

```typescript
import { useThree, useFrame } from '@react-three/fiber/native';
import * as THREE from 'three';

function useWorldToScreen(worldPos: THREE.Vector3) {
  const { camera, size } = useThree();
  const [screen, setScreen] = useState({ x: 0, y: 0, visible: false });

  useFrame(() => {
    const projected = worldPos.clone().project(camera);
    const x = (projected.x * 0.5 + 0.5) * size.width;
    const y = (-projected.y * 0.5 + 0.5) * size.height;
    const visible = projected.z < 1; // Behind camera check

    setScreen({ x, y, visible });
  });

  return screen;
}
```

### Ref-Based Communication (3D → RN)

```typescript
// Shared ref for 3D scene to communicate positions to RN overlay
const overlayPositions = useRef<Record<string, { x: number; y: number }>>({});

// In Three.js scene (useFrame):
function UpdateOverlayPosition({ id, worldPos }: { id: string; worldPos: THREE.Vector3 }) {
  const { camera, size } = useThree();

  useFrame(() => {
    const projected = worldPos.clone().project(camera);
    overlayPositions.current[id] = {
      x: (projected.x * 0.5 + 0.5) * size.width,
      y: (-projected.y * 0.5 + 0.5) * size.height,
    };
  });

  return null;
}

// In RN overlay:
function FloatingLabels() {
  const [, forceUpdate] = useState(0);

  useEffect(() => {
    const iv = setInterval(() => forceUpdate(n => n + 1), 16); // ~60fps
    return () => clearInterval(iv);
  }, []);

  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      {Object.entries(overlayPositions.current).map(([id, pos]) => (
        <Text key={id} style={{ position: 'absolute', left: pos.x, top: pos.y }}>
          {id}
        </Text>
      ))}
    </View>
  );
}
```

---

## 12. Genre Patterns

### Puzzle: Score/Tray HUD

Puzzle games (Block Blast, Tetris) feature a minimal HUD: score at top, piece tray at bottom.

```typescript
function PuzzleHUD({ score, combo, tray, onPiecePress }: PuzzleHUDProps) {
  const layout = useGameLayout();

  return (
    <>
      {/* Score: centered top, large and bold */}
      <View style={[styles.puzzleScore, { top: layout.hudTop }]}>
        <ScoreCounter score={score} />
        {combo > 1 && <ComboMeter combo={combo} />}
      </View>

      {/* Piece tray: bottom, horizontal, fixed height */}
      <View style={[
        styles.pieceTray,
        {
          height: layout.trayHeight,
          bottom: layout.insets.bottom + 8,
        }
      ]}>
        {tray.map((piece, i) => (
          piece ? (
            <TrayPiece
              key={piece.id}
              piece={piece}
              onPress={() => onPiecePress(i)}
              cellSize={layout.isTablet ? 28 : 23}
            />
          ) : (
            <View key={`empty-${i}`} style={styles.emptySlot} />
          )
        ))}
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  puzzleScore: {
    position: 'absolute',
    left: 0, right: 0,
    alignItems: 'center',
  },
  pieceTray: {
    position: 'absolute',
    left: 0, right: 0,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
    paddingHorizontal: 16,
  },
  emptySlot: { width: 60, height: 60 },
});
```

### Runner: Distance/Coin Display

Endless runners show distance traveled and collected coins in a compact top bar.

```typescript
function RunnerHUD({ distance, coins, isPaused, onPause }: RunnerHUDProps) {
  const layout = useGameLayout();

  return (
    <View style={[styles.runnerBar, { top: layout.hudTop }]}>
      {/* Distance: left side */}
      <View style={styles.runnerStat}>
        <Text style={styles.runnerIcon}>🏃</Text>
        <Text style={styles.runnerValue}>{Math.floor(distance)}m</Text>
      </View>

      {/* Coins: center */}
      <View style={styles.runnerStat}>
        <Text style={styles.runnerIcon}>🪙</Text>
        <Text style={styles.runnerValue}>{coins}</Text>
      </View>

      {/* Pause button: right side */}
      <Pressable onPress={onPause} hitSlop={8}>
        <Text style={styles.pauseBtn}>⏸</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  runnerBar: {
    position: 'absolute',
    left: 16, right: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  runnerStat: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.4)',
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  runnerIcon: { fontSize: 16, marginRight: 6 },
  runnerValue: { color: '#fff', fontSize: 18, fontWeight: '900' },
  pauseBtn: {
    fontSize: 24,
    backgroundColor: 'rgba(0,0,0,0.4)',
    borderRadius: 20,
    width: 40, height: 40,
    textAlign: 'center',
    lineHeight: 40,
  },
});
```

### Idle: Currency Panel

Idle/tycoon games display multiple currencies and income rates in a persistent panel.

```typescript
function IdleCurrencyPanel({ currencies, incomePerSec }: IdleCurrencyProps) {
  return (
    <View style={styles.currencyPanel}>
      {currencies.map((c) => (
        <View key={c.type} style={styles.currencyRow}>
          <Text style={styles.currencyIcon}>{c.icon}</Text>
          <View style={{ flex: 1 }}>
            <Text style={styles.currencyAmount}>{formatNumber(c.amount)}</Text>
            {incomePerSec[c.type] > 0 && (
              <Text style={styles.currencyRate}>
                +{formatNumber(incomePerSec[c.type])}/s
              </Text>
            )}
          </View>
        </View>
      ))}
    </View>
  );
}

function formatNumber(n: number): string {
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)}B`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return Math.floor(n).toString();
}
```

### Tower Defense: Build Menu

Tower defense games need a build/upgrade menu with tower selection, cost display, and placement mode.

```typescript
function TowerBuildMenu({
  towers, coins, selectedTower, onSelect, onUpgrade,
}: TowerBuildMenuProps) {
  const layout = useGameLayout();

  return (
    <View style={[styles.buildMenu, { bottom: layout.insets.bottom }]}>
      {/* Available towers */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
        {towers.map((tower) => {
          const canAfford = coins >= tower.cost;
          const isSelected = selectedTower === tower.id;

          return (
            <Pressable
              key={tower.id}
              onPress={() => onSelect(tower.id)}
              style={[
                styles.towerCard,
                isSelected && styles.towerCardSelected,
                !canAfford && styles.towerCardDisabled,
              ]}
              accessibilityRole="button"
              accessibilityLabel={`${tower.name}, costs ${tower.cost} coins`}
            >
              <Text style={styles.towerIcon}>{tower.icon}</Text>
              <Text style={styles.towerName}>{tower.name}</Text>
              <View style={styles.towerCost}>
                <Text style={styles.coinIcon}>🪙</Text>
                <Text style={styles.costValue}>{tower.cost}</Text>
              </View>
            </Pressable>
          );
        })}
      </ScrollView>

      {/* Upgrade panel for selected tower */}
      {selectedTower && (
        <View style={styles.upgradePanel}>
          <Text style={styles.upgradeTitle}>Upgrade</Text>
          <Pressable
            onPress={onUpgrade}
            style={[
              styles.upgradeBtn,
              coins < upgradeCost && styles.upgradeBtnDisabled,
            ]}
          >
            <Text style={styles.upgradeBtnText}>
              Upgrade (🪙 {upgradeCost})
            </Text>
          </Pressable>
        </View>
      )}
    </View>
  );
}
```

---

## Example: Blocube Implementation

> Blocube demonstrates several responsive UI patterns in production:
>
> **HUD Architecture:** Score counter (`ScoreCounter`) uses `requestAnimationFrame` for smooth count-up animation with pulse effect. Combo meter (`ComboMeter`) escalates color through tiers and adds continuous pulse animation at 8+ combo.
>
> **Gesture Handling:** A single transparent `View` with `PanResponder` sits above the Canvas. It distinguishes between piece dragging (touch on tray piece) and cube rotation (touch on empty space) using `measureInWindow` rects.
>
> **Modal Navigation:** Phase-based state machine: `'menu' | 'game'` for screens, `'none' | 'revive' | 'result'` for game-over flow. Settings panel is a scrim overlay.
>
> **Performance Isolation:** `ScoreCounter` manages its own display state to prevent full-App re-renders. Zustand selectors are granular (`useGame((s) => s.score)`). Flash sound uses `useGame.subscribe()` to avoid re-rendering App on clear events.
>
> **StatusBar:** Uses `expo-status-bar` with `style="light"` for consistent light text on dark backgrounds.
>
> **Canvas Measurement:** `onCanvasLayout` callback measures the Canvas via `measureInWindow` and stores the rect in `dragRef.canvas` for gesture-to-3D coordinate conversion.

---

## 13. Sources

- [React Native Safe Area Context](https://github.com/AppAndMusic/react-native-safe-area-context)
- [React Native Dimensions API](https://reactnative.dev/docs/dimensions)
- [React Native PixelRatio](https://reactnative.dev/docs/pixelratio)
- [React Native PanResponder](https://reactnative.dev/docs/panresolver)
- [React Native Gesture Handler](https://docs.swmansion.com/react-native-gesture-handler/)
- [React Native AccessibilityInfo](https://reactnative.dev/docs/accessibilityinfo)
- [WCAG 2.1 Color Contrast Requirements](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html)
- [React Native I18nManager](https://reactnative.dev/docs/i18nmanager)
- [Expo Status Bar](https://docs.expo.dev/versions/latest/sdk/status-bar/)
- [React Three Fiber Native](https://docs.pmnd.rs/react-three-fiber/getting-started/installation#expo)
- [drei Html Component](https://github.com/pmndrs/drei#html)
- [Zustand Subscribe Pattern](https://docs.pmnd.rs/zustand/getting-started/introduction)
- [React.memo Documentation](https://react.dev/reference/react/memo)
- [React Native LayoutAnimation](https://reactnative.dev/docs/layoutanimation)
