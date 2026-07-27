# React Native Game Architecture & State Management

> **General-purpose reference** for building mobile games with React Native + Three.js.
> Covers state management patterns, game flow, persistence, ad integration, and genre-specific architectures.

---

## Table of Contents

1. [Zustand + Mutable Ref Hybrid Pattern](#1-zustand--mutable-ref-hybrid-pattern)
2. [Game State Machine (FSM) Implementation](#2-game-state-machine-fsm-implementation)
3. [Component Isolation & Re-render Minimization](#3-component-isolation--re-render-minimization)
4. [Subscription-Based Side Effects](#4-subscription-based-side-effects)
5. [Game Flow Patterns](#5-game-flow-patterns)
6. [Persistence Layer Patterns](#6-persistence-layer-patterns)
7. [Ad Integration Architecture](#7-ad-integration-architecture)
8. [ECS Patterns in React Native](#8-ecs-patterns-in-react-native)
9. [Score / Combo / State Separation](#9-score--combo--state-separation)
10. [Genre Patterns](#10-genre-patterns)
11. [Sources](#11-sources)

---

## 1. Zustand + Mutable Ref Hybrid Pattern

The core architectural insight for React Native games: **not all state deserves to trigger re-renders**. Split data by update frequency into two tiers.

### Low-Frequency State → Zustand Store

State that changes on user actions (placements, score updates, game-over events) belongs in Zustand. These changes are infrequent relative to frame rate and often need to drive UI components.

```typescript
import { create } from 'zustand';

type GameState = {
  faces: number[][][];        // grid data
  tray: (PieceDef | null)[];  // available pieces
  score: number;
  combo: number;
  highScore: number;
  gameOver: boolean;
  theme: number;
  flash: FlashCell[];         // clear animation triggers
  placed: Cell3[];            // pop animation triggers
  commitPlacement: (cells: Cell3[], trayIndex: number, colorIndex: number) => void;
  revive: () => void;
  reset: () => void;
};

export const useGame = create<GameState>((set) => ({
  // ... initial state + actions
}));
```

### High-Frequency Data → Mutable Refs

Data that changes every frame (60fps) — rotation velocities, drag positions, shake intensity — must live in plain mutable objects. Reading/writing these in `useFrame` causes **zero React re-renders**.

```typescript
// cubeRef.ts — rotation state updated every frame
export const cubeRef = {
  yaw: 0,
  yawVel: 0,
  snapVel: 0,      // spring snap velocity
  dragging: false,
  quat: new THREE.Quaternion(),
};

// fxRef.ts — visual effects state
export const fxRef = {
  shake: 0,  // screen shake intensity, decays each frame
};

// dragRef.ts — drag operation state
export const dragRef = {
  active: false,
  shape: null as PieceDef | null,
  position: [0, 0],
  hoverResult: null as HoverResult | null,
};

// modeRef.ts — screen mode (read by 3D layer useFrame)
export const modeRef = {
  mode: 'menu' as 'menu' | 'enter' | 'game',
  enterStart: 0,
};
```

### The Decision Rule

| Question | Answer | Where |
|----------|--------|-------|
| Does this data change >30x/sec? | Yes | Mutable ref |
| Does a UI component need to display this? | Yes | Zustand store |
| Does this drive a shader/matrix update? | Yes | Mutable ref |
| Is this read inside `useFrame`? | Yes | Mutable ref |
| Is this read inside a React `render()`? | Yes | Zustand store |

### Pattern: Reading Refs in useFrame

```tsx
function CubeController() {
  const groupRef = useRef<THREE.Group>(null);

  useFrame((_, dt) => {
    // Read mutable ref — no re-render
    const { yaw, yawVel, snapVel } = cubeRef;
    cubeRef.yaw += yawVel * dt;
    cubeRef.yawVel *= 0.92; // damping

    // Apply to Three.js object directly
    if (groupRef.current) {
      updateCubeQuat();
      groupRef.current.quaternion.copy(cubeRef.quat);
    }
  });

  return <group ref={groupRef} />;
}
```

### Pattern: Bridging Ref to Store

When a high-frequency action produces a low-frequency result, write to the store:

```typescript
// In useFrame, when drag ends with a valid placement:
if (!dragRef.active && dragRef.hoverResult) {
  const { cells, trayIndex, colorIndex } = dragRef.hoverResult;
  useGame.getState().commitPlacement(cells, trayIndex, colorIndex);
  dragRef.hoverResult = null;
}
```

> **Example: Blocube Implementation**
> Blocube uses four mutable refs (`cubeRef`, `dragRef`, `fxRef`, `modeRef`) alongside a single Zustand store (`useGame`). The Zustand store holds grid state, score, combo, theme, and tray — all updated on player actions. The refs handle yaw rotation at 60fps, drag hover results, screen shake decay, and menu/game mode transitions — all without triggering a single React re-render during gameplay.

---

## 2. Game State Machine (FSM) Implementation

Games are inherently state machines. In React/TypeScript, implement FSMs at two levels:

### Application-Level FSM

The top-level game mode transitions:

```typescript
type GamePhase =
  | 'loading'
  | 'menu'
  | 'enter'       // cinematic transition
  | 'gameplay'
  | 'paused'
  | 'gameover'
  | 'revive'
  | 'results';

// Implementation via Zustand
type AppFSM = {
  phase: GamePhase;
  transition: (to: GamePhase) => void;
};

const validTransitions: Record<GamePhase, GamePhase[]> = {
  loading:    ['menu'],
  menu:       ['enter'],
  enter:      ['gameplay'],
  gameplay:   ['paused', 'gameover'],
  paused:     ['gameplay', 'menu'],
  gameover:   ['revive', 'results', 'menu'],
  revive:     ['gameplay'],
  results:    ['menu'],
};
```

### Guard Function

```typescript
function canTransition(from: GamePhase, to: GamePhase): boolean {
  return validTransitions[from]?.includes(to) ?? false;
}

// Usage in store
transition: (to) => set((state) => {
  if (!canTransition(state.phase, to)) {
    console.warn(`Invalid transition: ${state.phase} → ${to}`);
    return {};
  }
  return { phase: to };
}),
```

### Sub-State Machines

Each phase can have its own sub-states:

```typescript
// Menu sub-states
type MenuPhase = 'attract' | 'idle' | 'buttonPressed';

// Gameplay sub-states
type GameplayPhase = 'waiting' | 'dragging' | 'resolving' | 'clearing';
```

### Time-Based Transitions

For cinematic transitions (menu → gameplay dive), use timestamps:

```typescript
export const modeRef = {
  mode: 'menu' as 'menu' | 'enter' | 'game',
  enterStart: 0,  // performance.now() when enter began
};

// In useFrame:
useFrame(() => {
  if (modeRef.mode === 'enter') {
    const elapsed = (performance.now() - modeRef.enterStart) / 1000;
    const t = Math.min(1, elapsed / ENTER_DURATION);
    const eased = easeInOutCubic(t);
    // Interpolate camera position...
    if (t >= 1) {
      modeRef.mode = 'game';
    }
  }
});
```

---

## 3. Component Isolation & Re-render Minimization

### The Problem

In React, any state change in a parent causes the entire subtree to re-render. For a game running at 60fps, this is catastrophic.

### Strategy 1: Zustand Selectors

Only subscribe to the specific slices you need:

```tsx
// BAD — re-renders on ANY state change
const state = useGame();

// GOOD — re-renders only when score changes
const score = useGame((s) => s.score);

// GOOD — re-renders only when gameOver changes
const isOver = useGame((s) => s.gameOver);
```

### Strategy 2: Isolated UI Components

Split the UI into small components that each subscribe to their own data:

```tsx
// ScoreCounter — only re-renders when score changes
function ScoreCounter() {
  const score = useGame((s) => s.score);
  return <Text>{score}</Text>;
}

// ComboDisplay — only re-renders when combo changes
function ComboDisplay() {
  const combo = useGame((s) => s.combo);
  if (combo < 2) return null;
  return <Text>x{combo}</Text>;
}

// GameOverScreen — only re-renders when gameOver changes
function GameOverScreen() {
  const gameOver = useGame((s) => s.gameOver);
  if (!gameOver) return null;
  return <Overlay>...</Overlay>;
}
```

### Strategy 3: Memoization

```tsx
const ScoreCounter = React.memo(function ScoreCounter() {
  const score = useGame((s) => s.score);
  return <Text>{score}</Text>;
});
```

### Strategy 4: Keep 3D Layer Ref-Driven

The Three.js scene should read from mutable refs, not Zustand, for per-frame data:

```tsx
function FaceTiles({ faceIndex }: { faceIndex: number }) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const lastScale = useRef(new Float32Array(25).fill(0));

  useFrame(() => {
    // Read from store ONLY for structural changes (new pieces placed)
    const faces = useGame.getState().faces[faceIndex];
    const flash = useGame.getState().flash;

    // Update instance matrices conditionally
    let changed = false;
    for (let i = 0; i < 25; i++) {
      const targetScale = faces[Math.floor(i/5)][i%5] ? 1 : 0;
      if (Math.abs(lastScale.current[i] - targetScale) > 0.01) {
        lastScale.current[i] = targetScale;
        changed = true;
      }
    }
    if (changed && meshRef.current) {
      meshRef.current.instanceMatrix.needsUpdate = true;
    }
  });

  return <instancedMesh ref={meshRef} args={[TILE_GEO, undefined, 25]} />;
}
```

### Strategy 5: Conditional needsUpdate

Only flag GPU buffers as dirty when data actually changed:

```typescript
// Track previous values to avoid unnecessary GPU uploads
let colorChanged = false;
for (let i = 0; i < count; i++) {
  const newColor = getColor(i);
  if (!tmpColor.equals(newColor)) {
    colorArray.set(newColor.toArray(), i * 3);
    colorChanged = true;
  }
}
if (colorChanged) {
  instanceColor.needsUpdate = true;
}
```

---

## 4. Subscription-Based Side Effects

Zustand's `subscribe` method enables side effects that react to state changes **without causing re-renders**. This is ideal for audio, haptics, and analytics.

### Audio Trigger Pattern

```typescript
// In App.tsx — subscribe once on mount
useEffect(() => {
  let prevClearId = 0;

  const unsub = useGame.subscribe((state) => {
    // Detect new clear event
    if (state.clearEvent.id > prevClearId) {
      prevClearId = state.clearEvent.id;
      playClearSound(state.clearEvent.combo);
    }
  });

  return () => unsub();
}, []);
```

### Analytics Tracking Pattern

```typescript
useEffect(() => {
  const unsub = useGame.subscribe((state) => {
    if (state.gameOver) {
      analytics.track('game_over', {
        score: state.score,
        combo: state.bestCombo,
        theme: state.theme,
      });
    }
  });
  return () => unsub();
}, []);
```

### Cleanup Pattern (setTimeout-based)

For transient animation triggers, use `setTimeout` to clear them:

```typescript
// After commitPlacement, schedule flash cleanup
const fl = useGame.getState().flash;
if (fl.length) {
  const maxDelay = fl.reduce((m, f) => Math.max(m, f.delay), 0);
  setTimeout(() => useGame.setState({ flash: [] }), maxDelay * 1000 + 320);
}

// Schedule placed animation cleanup
if (useGame.getState().placed.length) {
  setTimeout(() => useGame.setState({ placed: [] }), 320);
}
```

---

## 5. Game Flow Patterns

### Standard Mobile Puzzle Game Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  LOADING │────▶│   MENU   │────▶│  ENTER   │
│          │     │ (attract)│     │(cinematic)│
└──────────┘     └──────────┘     └──────────┘
                       ▲                │
                       │                ▼
                  ┌──────────┐     ┌──────────┐
                  │ RESULTS  │◀────│ GAMEPLAY │
                  │          │     │          │
                  └──────────┘     └──────────┘
                       ▲                │
                       │          ┌─────┴─────┐
                       │          ▼           ▼
                  ┌──────────┐  ┌──────────┐
                  │  REVIVE  │  │ GAMEOVER │
                  │(rewarded)│  │          │
                  └──────────┘  └──────────┘
                       │
                       ▼
                  ┌──────────┐
                  │ GAMEPLAY │  (continue)
                  └──────────┘
```

### Menu / Attract Mode

When idle on the menu, run a demo to attract players:

```typescript
// Seed initial board state for demo
function seedDemo() {
  const { faces, cells } = seededFaces();
  useGame.setState({ faces, placed: cells, score: 0 });
}

// Periodic auto-blast for visual interest
const demoInterval = setInterval(() => {
  if (modeRef.mode === 'menu') {
    demoBlast(); // trigger a fake clear with FX
  }
}, 4000);
```

### Cinematic Enter Transition

```typescript
function startGame() {
  modeRef.mode = 'enter';
  modeRef.enterStart = performance.now();
  // useFrame handles camera dive animation
  // When complete, modeRef.mode = 'game'
  useGame.getState().reset();
}
```

### Revive Flow

```typescript
function onGameOver() {
  // Show revive offer (rewarded ad)
  showRevive(
    () => {
      // Reward earned — restore board
      useGame.getState().revive();
    },
    () => {
      // No reward — show results
      setPhase('results');
    }
  );
}

// revive() in store:
revive: () => set((state) => ({
  faces: state.overFaces ?? state.faces,  // restore pre-gameover board
  overFaces: null,
  tray: easyTray(3),   // give easy pieces to fit tight board
  gameOver: false,
  reviveUsed: true,     // only once per run
  clearedThisSet: false,
  flash: [],
  placed: [],
})),
```

> **Example: Blocube Implementation**
> Blocube's game flow: Menu (attract demo with `seedDemo()` + periodic `demoBlast()`) → "CLASSIC" button triggers cinematic camera dive (`modeRef.mode = 'enter'`) → Gameplay (drag pieces onto 4 cube faces, rows/columns clear) → Game Over (all cells explode in staggered wave) → Revive offer (rewarded ad restores board + gives easy pieces) or Results screen (interstitial ad). Theme transitions every 5000 points with a white flash effect.

---

## 6. Persistence Layer Patterns

### JSON File Persistence (expo-file-system)

For casual games, a single JSON file is sufficient. No database needed.

```typescript
import { File, Paths } from 'expo-file-system';

export type SaveData = {
  highScore: number;
  // Future: totalGames, totalClears, dailyStreak, settings, ...
};

const DEFAULTS: SaveData = { highScore: 0 };

function getFile(): File {
  return new File(Paths.document, 'game-save.json');
}

// Synchronous read (called once at startup)
export function loadSave(): SaveData {
  try {
    const f = getFile();
    if (!f.exists) return { ...DEFAULTS };
    const raw = f.textSync();
    return { ...DEFAULTS, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULTS };
  }
}

// Async write (called on game-over, settings change)
export function writeSave(data: SaveData) {
  try {
    const f = getFile();
    if (!f.exists) f.create();
    f.write(JSON.stringify(data));
  } catch {
    // Silent failure — game continues normally
  }
}
```

### Key Design Principles

1. **Defaults merging**: Always spread `DEFAULTS` first — forward-compatible when you add fields
2. **Error tolerance**: Never crash on save/load failure
3. **Sync read, async write**: Read at startup (blocks nothing), write at natural breakpoints
4. **Single write point**: Write only on game-over, not every score change

> **Example: Blocube Implementation**
> Blocube uses `expo-file-system` new API (`File`, `Paths`) to store a single JSON file (`cubeblast-save.json`) in the document directory. Currently only `{ highScore: number }` is persisted. Synchronous read (`textSync()`) at startup, async write on game-over. Defaults are merged with saved data for forward-compatibility. Any failure returns defaults silently.

### Expanding the Save Schema

```typescript
export type SaveData = {
  highScore: number;
  totalGames: number;
  totalClears: number;
  dailyStreak: number;
  lastPlayDate: string;      // ISO date for streak calculation
  settings: {
    sfxVolume: number;
    musicVolume: number;
    hapticsEnabled: boolean;
  };
  purchases: {
    noAdsRemoved: boolean;
    themesUnlocked: string[];
  };
};
```

### Zustand + Persistence Middleware

For more complex needs, use Zustand's `persist` middleware:

```typescript
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export const useSettings = create(
  persist<SettingsState>(
    (set) => ({
      sfxVolume: 1,
      musicVolume: 0.5,
      setSfxVolume: (v) => set({ sfxVolume: v }),
    }),
    {
      name: 'game-settings',
      storage: createJSONStorage(() => AsyncStorage),
    }
  )
);
```

---

## 7. Ad Integration Architecture

### Ad Types for Mobile Games

| Ad Type | When to Show | Revenue | User Impact |
|---------|-------------|---------|-------------|
| **Rewarded** | Game-over revive | High | Positive (user chooses) |
| **Interstitial** | Between games | Medium | Negative (forced) |
| **Banner** | During gameplay | Low | Moderate (persistent) |

### Initialization Flow

```
App Launch
    │
    ▼
┌─────────────────────┐
│ ATT Permission (iOS) │  ← IDFA for personalized ads
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ UMP/GDPR Consent    │  ← EU user consent form
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ SDK Initialize      │  ← MobileAds().initialize()
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ Preload Both Ads    │  ← loadRewarded() + loadInterstitial()
└─────────────────────┘
```

### Graceful Degradation Pattern

The ad module must never block gameplay. If ads are unavailable (Expo Go, network error, SDK failure), skip ads and call the callback directly:

```typescript
let gma: any = null;
try {
  gma = require('react-native-google-mobile-ads');
} catch {
  gma = null;
}

export const adsAvailable = !!(gma && gma.default);

// Show rewarded ad — always calls a callback
export function showRevive(onReward: () => void, onNoReward: () => void) {
  if (!adsAvailable || !rewardedReady) {
    onReward();  // Skip ad, don't punish user
    return;
  }

  let earned = false;
  rewarded.addAdEventListener('earned_reward', () => { earned = true; });
  rewarded.addAdEventListener('closed', () => {
    loadRewarded();  // Preload next ad
    earned ? onReward() : onNoReward();
  });
  rewarded.addAdEventListener('error', () => {
    loadRewarded();
    onReward();  // Error → favor the user
  });
  rewarded.show();
}
```

### Preloading Strategy

After each ad is shown, immediately load the next one:

```typescript
function loadRewarded() {
  rewardedReady = false;
  rewarded = RewardedAd.createForAdRequest(REWARDED_ID);
  rewarded.addAdEventListener('loaded', () => { rewardedReady = true; });
  rewarded.addAdEventListener('error', () => { rewardedReady = false; });
  rewarded.load();
}
```

### Test vs Production

```typescript
const USE_TEST_ADS = __DEV__;
const REWARDED_ID = USE_TEST_ADS && TestIds
  ? TestIds.REWARDED
  : 'ca-app-pub-XXXXX/YYYYY';
```

> **Warning**: Never click your own real ads — your AdMob account will be suspended.

> **Example: Blocube Implementation**
> Blocube uses `react-native-google-mobile-ads` (no mediation) with two ad types: Rewarded (revive) and Interstitial (game-over retry). The SDK is loaded via `require()` with try/catch — if unavailable (Expo Go), `adsAvailable=false` and all show functions skip ads, calling callbacks directly. Initialization flow: ATT permission (iOS) → UMP/GDPR consent → SDK init → preload both ad types. After each ad shown, the next one is immediately preloaded. `__DEV__` flag auto-selects test ad IDs vs real AdMob IDs. Every ad operation is wrapped in try/catch; errors always favor the user (skip ad, continue game).

---

## 8. ECS Patterns in React Native

Pure ECS (Entity-Component-System) is rare in React Native games, but ECS-inspired patterns emerge naturally.

### Entity as Index

Instead of entity objects, use array indices:

```typescript
// Grid cells are entities indexed by (face, col, row)
type Cell3 = [face: number, col: number, row: number];

// Components are data arrays
type TileColor = number;    // 0 = empty, 1-7 = color index
type TileScale = number;    // animation scale
```

### System as Pure Function

Systems operate on entities without owning state:

```typescript
// Clearing system — pure function
export function faceClears(grid: number[][]): {
  cells: [number, number][];
  lines: number;
} {
  const toClear = new Set<string>();
  let lines = 0;

  // Check rows
  for (let r = 0; r < GRID_N; r++) {
    if (grid[r].every((c) => c !== 0)) {
      for (let c = 0; c < GRID_N; c++) toClear.add(`${c},${r}`);
      lines++;
    }
  }
  // Check columns
  for (let c = 0; c < GRID_N; c++) {
    if (grid.every((row) => row[c] !== 0)) {
      for (let r = 0; r < GRID_N; r++) toClear.add(`${c},${r}`);
      lines++;
    }
  }

  return {
    cells: [...toClear].map((k) => k.split(',').map(Number) as [number, number]),
    lines,
  };
}

// Game-over system — pure function
export function isGameOver(faces: number[][][], tray: (PieceDef | null)[]): boolean {
  for (const piece of tray) {
    if (!piece) continue;
    for (let f = 0; f < FACE_COUNT; f++) {
      for (const [pc, pr] of piece.cells) {
        if (isValidPlacement(faces[f], piece.cells.map(([c, r]) => [c + pc, r + pr]))) {
          return false;  // At least one piece fits somewhere
        }
      }
    }
  }
  return true;
}
```

### Object Pool as Pre-Allocated Arrays

```typescript
// Pre-allocated FX pools (module-level singletons)
const FRAG_COUNT = 84;
const SPARK_COUNT = 48;
const SHOCK_COUNT = 3;

interface FXObj {
  pos: THREE.Vector3;
  vel: THREE.Vector3;
  life: number;
  maxLife: number;
  color: THREE.Color;
  scale: number;
}

const fragments: FXObj[] = Array.from({ length: FRAG_COUNT }, () => ({
  pos: new THREE.Vector3(),
  vel: new THREE.Vector3(),
  life: 0,
  maxLife: 1,
  color: new THREE.Color(),
  scale: 1,
}));

let fCur = 0;  // circular buffer index

function spawnFragment(pos: THREE.Vector3, color: THREE.Color) {
  const f = fragments[fCur];
  fCur = (fCur + 1) % FRAG_COUNT;
  f.pos.copy(pos);
  f.vel.set((Math.random() - 0.5) * 4, Math.random() * 3 + 1, (Math.random() - 0.5) * 4);
  f.life = 0;
  f.maxLife = 0.6 + Math.random() * 0.4;
  f.color.copy(color);
}
```

> **Example: Blocube Implementation**
> Blocube uses ECS-inspired patterns: Grid cells are entities indexed by `[face, col, row]` tuples. Systems are pure functions (`faceClears()`, `isGameOver()`) that operate on grid data without owning state. The `ClearFX` component uses pre-allocated pools: 84 fragments, 48 sparks, 3 shockwaves — all module-level singletons with circular buffer reuse (`fCur = (fCur + 1) % FRAG_COUNT`). This reduces FX from 132 individual meshes to just 2 draw calls via InstancedMesh.

---

## 9. Score / Combo / State Separation

### Score vs Combo vs High Score

Separate scoring concerns to avoid coupling:

```typescript
type ScoreState = {
  score: number;        // current run score
  combo: number;        // current clear multiplier
  bestCombo: number;    // peak combo this run
  highScore: number;    // all-time record (persisted)
};
```

### Combo Mechanics

Combo increments on consecutive clears and resets when a full tray cycle passes without a clear:

```typescript
// In commitPlacement:
const didClear = flash.length > 0;
let combo = state.combo;
if (didClear) combo += 1;

// Tray refill — check if this set produced any clears
const refilling = next.every((p) => p === null);
if (refilling) {
  if (!clearedThisSet) combo = 0;  // No clears this set → reset
  clearedThisSet = false;
}

// Points formula: lineCount * 10 * max(1, combo)
const clearPoints = lineCount * 10 * Math.max(1, combo);
const score = state.score + gained + clearPoints;
```

### Theme Transition on Score Milestones

```typescript
// Every 5000 points → switch to a random different theme
let theme = state.theme;
if (Math.floor(score / 5000) > Math.floor(state.score / 5000)) {
  const opts = THEMES.map((_, i) => i).filter((i) => i !== state.theme);
  theme = opts[Math.floor(Math.random() * opts.length)];
}
```

### Clear Event as Trigger

Use an incrementing ID to trigger one-shot effects:

```typescript
type ClearEvent = { id: number; points: number; combo: number };

// Subscribe to clear events without re-rendering
useGame.subscribe((state) => {
  if (state.clearEvent.id > lastClearId) {
    lastClearId = state.clearEvent.id;
    showClearPopup(state.clearEvent.points, state.clearEvent.combo);
    playClearSound(state.clearEvent.combo);
  }
});
```

> **Example: Blocube Implementation**
> Blocube's scoring: `score += gained + lineCount * 10 * max(1, combo)`. Combo increments on each clear and resets when a full tray cycle (3 pieces) passes without any clear. `bestCombo` tracks the peak combo for the run. Theme transitions every 5000 points to a random different theme. The `clearEvent` object uses an incrementing `id` field to trigger one-shot popup and sound effects via Zustand subscription — no re-render of the entire App needed.

---

## 10. Genre Patterns

Different game genres demand different architectural approaches. Below are proven patterns for four major mobile game genres.

### 10.1 Puzzle Game Loop

**Core loop**: Place pieces → check clears → update score → check game-over → repeat.

```typescript
type PuzzlePhase = 'waiting' | 'dragging' | 'resolving' | 'clearing' | 'gameover';

// State machine for puzzle games
const puzzleTransitions = {
  waiting:    ['dragging'],
  dragging:   ['resolving', 'waiting'],     // valid drop or cancel
  resolving:  ['clearing', 'waiting'],       // clear found or no clear
  clearing:   ['waiting'],                   // animation done
  gameover:   ['waiting'],                   // after revive/reset
};

// Key characteristics:
// - Turn-based feel (even in real-time)
// - Player controls pace
// - Score = function of efficiency (lines cleared per piece)
// - Difficulty via piece complexity, not speed
// - Session: 3-8 minutes
```

**State separation**: Grid state (persistent across turns), piece queue (lookahead), score (accumulated).

**Persistence**: Save grid state + piece queue for session resumption.

### 10.2 Runner State Machine

**Core loop**: Auto-scroll → dodge obstacles → collect items → increase speed → crash → revive/restart.

```typescript
type RunnerPhase =
  | 'intro'
  | 'gameplay'
  | 'bulletTime'   // slow-mo on near-miss
  | 'crash'
  | 'revive'
  | 'results';

// Runner-specific state
type RunnerState = {
  phase: RunnerPhase;
  distance: number;       // meters traveled
  speed: number;          // current scroll speed (increases over time)
  lane: 0 | 1 | 2;       // current lane
  coins: number;
  multiplier: number;     // combo from near-misses
};

// Key characteristics:
// - Continuous forward motion (useFrame-driven)
// - Floating origin reset at large distances (IEEE 754 precision)
// - Object pooling for obstacles, scenery, collectibles
// - Procedural generation with solvability guarantees
// - Speed ramp: base + distance * coefficient
```

**Floating Origin Pattern**:
```typescript
const FLOAT_ORIGIN_THRESHOLD = 1000; // meters

useFrame((_, dt) => {
  state.distance += state.speed * dt;

  if (state.distance > FLOAT_ORIGIN_THRESHOLD) {
    // Reset all objects relative to player
    resetWorldOrigin(state.distance);
    state.distance = 0;
  }
});
```

### 10.3 Idle Tick System

**Core loop**: Tick → produce resources → spend on upgrades → unlock new producers → prestige.

```typescript
type IdlePhase = 'playing' | 'upgrading' | 'prestiging';

// Idle games need an offline progress calculator
function calculateOfflineProgress(
  lastTick: number,
  now: number,
  producers: Producer[],
): { resources: number; ticks: number } {
  const elapsed = (now - lastTick) / 1000; // seconds offline
  const maxOffline = 8 * 3600; // cap at 8 hours
  const dt = Math.min(elapsed, maxOffline);

  let totalProduction = 0;
  for (const p of producers) {
    totalProduction += p.rate * p.count;
  }

  return {
    resources: totalProduction * dt,
    ticks: Math.floor(dt / TICK_INTERVAL),
  };
}

// Key characteristics:
// - Tick-based updates (not frame-based)
// - Offline progress calculation on resume
// - Exponential cost scaling: cost = baseCost * growthRate^count
// - Prestige resets with permanent multiplier
// - Persistence is critical (players expect progress saved)
```

**Tick System**:
```typescript
const TICK_INTERVAL = 100; // ms

useEffect(() => {
  const interval = setInterval(() {
    const dt = TICK_INTERVAL / 1000;
    for (const producer of producers) {
      resources += producer.rate * producer.count * dt;
    }
  }, TICK_INTERVAL);

  return () => clearInterval(interval);
}, [producers]);
```

### 10.4 Tower Defense Wave Management

**Core loop**: Place towers → start wave → enemies path → towers attack → wave clear → earn gold → repeat.

```typescript
type TDPhase =
  | 'placement'     // player places towers
  | 'combat'        // wave is active
  | 'waveClear'     // animation + rewards
  | 'betweenWaves'  // prep time
  | 'gameover';

type WaveManager = {
  currentWave: number;
  enemiesRemaining: number;
  spawnQueue: EnemyDef[];
  spawnTimer: number;
  spawnInterval: number;
  waveConfig: WaveConfig[];
};

type WaveConfig = {
  enemies: { type: string; count: number; interval: number }[];
  bossWave: boolean;
  reward: number;
};

// Key characteristics:
// - Wave-based progression (discrete rounds)
// - Pathfinding for enemies (A* or waypoint-based)
// - Tower targeting logic (closest, strongest, weakest)
// - Gold economy: earn from kills → spend on towers
// - Difficulty curve: more enemies, faster, more HP per wave
```

**Wave Spawner**:
```typescript
function updateWaveSpawner(wm: WaveManager, dt: number) {
  if (wm.spawnQueue.length === 0) return;

  wm.spawnTimer -= dt;
  if (wm.spawnTimer <= 0) {
    const enemy = wm.spawnQueue.shift()!;
    spawnEnemy(enemy);
    wm.spawnTimer = wm.spawnInterval;
  }
}

// Check wave completion
useFrame(() => {
  if (phase === 'combat' && activeEnemies.length === 0 && wm.spawnQueue.length === 0) {
    setPhase('waveClear');
    gold += waveConfig[currentWave].reward;
    setTimeout(() => {
      currentWave++;
      startWave(currentWave);
      setPhase('combat');
    }, 2000);
  }
});
```

---

## 11. Sources

1. Zustand Documentation — https://docs.pmnd.rs/zustand/getting-started/introduction
2. React Three Fiber Documentation — https://docs.pmnd.rs/react-three-fiber/getting-started/introduction
3. Expo File System — https://docs.expo.dev/versions/latest/sdk/file-system/
4. React Native Google Mobile Ads — https://docs.page/invertase/react-native-google-mobile-ads/
5. Three.js InstancedMesh — https://threejs.org/docs/#api/en/objects/InstancedMesh
6. Three.js DataTexture — https://threejs.org/docs/#api/en/textures/DataTexture
7. React Native Performance — https://reactnative.dev/docs/performance
8. Hermes JavaScript Engine — https://hermesengine.dev/
9. Zustand Subscribe Pattern — https://docs.pmnd.rs/zustand/api/store#subscribe
10. React.memo Optimization — https://react.dev/reference/react/memo
11. Expo GL Documentation — https://docs.expo.dev/versions/latest/sdk/gl-view/
12. Three.js ShaderMaterial — https://threejs.org/docs/#api/en/materials/ShaderMaterial
13. Object Pool Pattern in Games — https://gameprogrammingpatterns.com/object-pool.html
14. Finite State Machine in Games — https://gameprogrammingpatterns.com/state.html
15. Mobile Game Monetization (Google) — https://developer.android.com/google/play/billing
