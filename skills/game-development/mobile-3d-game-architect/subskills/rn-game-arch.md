# /rn-game-arch — Mimari & Durum Yönetimi

Zustand + mutable ref hibrit pattern, FSM, component izolasyonu ve oyun akışı.

## A. Zustand + Mutable Ref Hibrit Pattern

Tüm veri React re-render'ı tetiklememeli. Güncelleme sıklığına göre ikiye ayır:

```typescript
// Zustand — düşük frekans (score, combo, game-over)
export const useGame = create<GameState>((set) => ({
  faces: number[][][],
  score: number,
  combo: number,
  gameOver: boolean,
  theme: number,
  commitPlacement: (cells, trayIndex, colorIndex) => void,
  reset: () => void,
}));

// Mutable Ref — yüksek frekans (60fps pozisyon, rotasyon, drag)
export const cubeRef = {
  yaw: 0,
  yawVel: 0,
  snapVel: 0,
  dragging: false,
  quat: new THREE.Quaternion(),
};

export const dragRef = {
  active: false,
  shape: null as PieceDef | null,
  position: [0, 0],
  hoverResult: null as HoverResult | null,
};
```

## B. Karar Kuralı

| Soru | Cevap | Nerede |
|------|-------|--------|
| >30x/sn değişiyor mu? | Evet | Mutable ref |
| UI component gösteriyor mu? | Evet | Zustand store |
| Shader/matrix güncelliyor mu? | Evet | Mutable ref |
| `useFrame` içinde okunuyor mu? | Evet | Mutable ref |
| React `render()` içinde okunuyor mu? | Evet | Zustand store |

## C. Game State Machine (FSM)

```typescript
type GamePhase = 'loading' | 'menu' | 'enter' | 'gameplay' | 'paused' | 'gameover' | 'revive' | 'results';

const validTransitions: Record<GamePhase, GamePhase[]> = {
  loading:  ['menu'],
  menu:     ['enter'],
  enter:    ['gameplay'],
  gameplay: ['paused', 'gameover'],
  paused:   ['gameplay', 'menu'],
  gameover: ['revive', 'results', 'menu'],
  revive:   ['gameplay'],
  results:  ['menu'],
};

function canTransition(from: GamePhase, to: GamePhase): boolean {
  return validTransitions[from]?.includes(to) ?? false;
}
```

## D. Component İzolasyonu

```typescript
// ScoreCounter — sadece score değiştiğinde re-render
const ScoreCounter = React.memo(function ScoreCounter() {
  const score = useGame((s) => s.score);
  return <Text>{score}</Text>;
});

// FaceTiles — sadece ilgili face'in verisi değiştiğinde
const FaceTiles = React.memo(({ faceIdx }: { faceIdx: number }) => {
  const faceData = useGame((s) => s.faces[faceIdx]);
  // ...
});
```

## E. Subscription-Based Side Effects

```typescript
// Audio trigger — re-render olmadan
useEffect(() => {
  const unsub = useGame.subscribe((state, prev) => {
    if (state.clearEvent.id !== prev.clearEvent.id) {
      playClearSound(state.clearEvent.combo);
    }
  });
  return unsub;
}, []);
```

## F. Persistence Layer

```typescript
import { File, Paths } from 'expo-file-system';

export function loadSave(): SaveData {
  try {
    const f = new File(Paths.document, 'game-save.json');
    if (!f.exists) return { ...DEFAULTS };
    return { ...DEFAULTS, ...JSON.parse(f.textSync()) };
  } catch {
    return { ...DEFAULTS };
  }
}

export function writeSave(data: SaveData) {
  try {
    const f = new File(Paths.document, 'game-save.json');
    if (!f.exists) f.create();
    f.write(JSON.stringify(data));
  } catch { /* sessiz hata */ }
}
```

## G. Oyun Akışı

```
LOADING → MENU → ENTER (cinematic) → GAMEPLAY → GAMEOVER → REVIVE/RESULTS
                      ↑                                      │
                      └──────────────────────────────────────┘
```

## H. Yaygın Tuzaklar

- Tüm Zustand store'a abone olma → cascade re-render
- `useGame()` yerine `useGame((s) => s.score)` kullan
- Ref → Store bridge eksik → drag sonucu kaybolur
- setTimeout cleanup yok → animation state kalır

## Referans Doküman
- [`rn_game_architecture_state_management.md`](../researches/rn_game_architecture_state_management.md)
