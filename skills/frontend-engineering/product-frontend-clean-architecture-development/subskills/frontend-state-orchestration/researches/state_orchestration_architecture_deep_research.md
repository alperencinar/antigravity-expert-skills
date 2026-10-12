# Frontend Clean Architecture: Durum Yönetimi Orkestrasyonu, Zustand v5 Slice Mimarisi ve Durum Ayrışması (State Unbundling)
## 2025–2026 Endüstriyel Araştırma ve Standartlar Raporu

---

## 1. Yönetici Özeti (Executive Summary)

Modern frontend ve mobil mühendisliğinde (React 19, Next.js App Router, React Native ve Expo Router), durum yönetimi (state management) monolitik tekil depo (Redux/MobX) yaklaşımından radikal bir şekilde uzaklaşmıştır. Bu paradigma değişimi sektörde **"The Great State Unbundling" (Büyük Durum Ayrışması)** olarak adlandırılmaktadır.

Uzak sunucudan gelen verilerin (Server State) `TanStack Query v5` tarafından devralınmasıyla, istemcide kalan durum hacmi %80 oranında küçülmüştür. Kalan durumlar ise paylaşılabilirlik, yaşam döngüsü ve reaktivite ihtiyaçlarına göre 5 katmanlı bir taksonomiye ayrılmıştır:
1. **Server State:** TanStack Query v5 (Asenkron API verileri, caching, deduplication, invalidation).
2. **URL State:** `nuqs` (Web) ve Expo Router `useLocalSearchParams` (Filtreler, arama, sayfalama, sekmeler, modallar).
3. **Form State:** React 19 Actions (`useActionState`), TanStack Form veya React Hook Form + Zod (Girdi yaşam döngüsü, validasyon).
4. **Global Client State:** Zustand v5 (Kullanıcı oturumu, tema, global bildirim kuyrukları, audio oynatıcı).
5. **Local Component State:** `useState`, `useReducer` (Dropdown açık/kapalı, hover, lokal animasyonlar).

Bu rapor; kurumsal projelerde Zustand v5'in neden fiili standart olduğunu, type-safe **Slice Pattern** mimarisini, re-render şelalelerini önleyen `useShallow` kuralını ve "Sync-State" anti-pattern'ının çözümlerini sunmaktadır.

---

## 2. Durum Yönetimi Paradigma Kıyaslaması (2025–2026)

### 2.1 Paradigma Matrisi: Zustand v5 vs. Jotai vs. Signals vs. Redux Toolkit

| Metrik / Nitelik | Zustand v5 | Jotai (v2) | Signals (Preact / TC39) | Redux Toolkit (RTK) |
| :--- | :--- | :--- | :--- | :--- |
| **Temel Paradigma** | Centralized Flux-lite, Hook & Selector | Atomic (Bottom-up), Reaktif graf | Fine-grained Push Observables | Centralized Strict Flux |
| **Paket Boyutu** | **~1.2 kB** (Tree-shakeable) | ~3.5 kB | ~1.6 kB (React adapter ile ~3 kB) | ~12–15 kB |
| **Boilerplate Yükü** | **Yok denecek kadar az** | Düşük | Minimal | Orta - Yüksek |
| **React Dışı Kullanım** | **Mükemmel** (`getState()`, `setState()`) | Kısıtlı (`createStore`) | Mükemmel (Doğası gereği) | İyi |
| **Re-render Modeli** | Seçici (`useSyncExternalStore`) | Atomik Abonelik | VDOM Bypass | Seçici (`useSelector`) |
| **2025–2026 Kabulü** | **De-facto Standart (Global UI State)** | Canvas / Grafik arayüzleri | Borsa / Ticker / Oyun HUD | Eski finans sistemleri |

#### Neden Zustand Kurumsal Standarttır?
1. **Context API Çöküşü:** Saf `createContext` bir dependency injection aracıdır; durum değiştiğinde tüm alt ağaçta kontrolsüz re-render patlamasına (re-render waterfall) yol açar.
2. **Sıfır Provider Mimarisi (Zero-Provider):** `<Provider>` sarmalaması gerektirmez; React ağacının dışındaki servislerden (Axios/Fetch interceptors, WebSocket yöneticileri, telemetry) doğrudan okunabilir.
3. **Eşzamanlı Güvenlik:** React 18/19 `useSyncExternalStore` entegrasyonu ile "tearing" (yırtılma) hatalarını sıfırlar.

---

## 3. Zustand v5 Ölçeklenebilir Mimari: Domain-Driven Slice Pattern

Büyük ölçekli uygulamalarda tek dosyalık monolithic store "God Object" anti-pattern'i üretir. Kurumsal çözüm modüler **Slice Pattern**'dir.

### 3.1 Type-Safe Slice Creator (Immer Mutator Tuple)
Zustand v5'te Immer middleware'i ile tam tip güvenliği sağlamak için mutator tuple (`[["zustand/immer", never]]`) tanımı şarttır:

```typescript
// store/slices/authSlice.ts
import { StateCreator } from 'zustand';
import type { AppStore } from '../types';

export interface AuthSlice {
  user: UserProfile | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  setSession: (user: UserProfile, token: string) => void;
  clearSession: () => void;
}

export const createAuthSlice: StateCreator<
  AppStore,
  [['zustand/immer', never]],
  [],
  AuthSlice
> = (set) => ({
  user: null,
  accessToken: null,
  isAuthenticated: false,
  setSession: (user, token) =>
    set((draft) => {
      draft.user = user;
      draft.accessToken = token;
      draft.isAuthenticated = true;
    }),
  clearSession: () =>
    set((draft) => {
      draft.user = null;
      draft.accessToken = null;
      draft.isAuthenticated = false;
    }),
});
```

### 3.2 Store Kompozisyonu ve Güvenli Kalıcılık (`partialize`)
```typescript
// store/index.ts
import { create } from 'zustand';
import { devtools, persist, createJSONStorage } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import { createAuthSlice, type AuthSlice } from './slices/authSlice';
import { createUISlice, type UISlice } from './slices/uiSlice';
import { appStorage } from './storage';

export type AppStore = AuthSlice & UISlice;

export const useAppStore = create<AppStore>()(
  devtools(
    persist(
      immer((...args) => ({
        ...createAuthSlice(...args),
        ...createUISlice(...args),
      })),
      {
        name: '@app_global_store',
        storage: createJSONStorage(() => appStorage),
        partialize: (state) => ({
          accessToken: state.accessToken,
          user: state.user,
          // Geçici UI durumları (modal, sidebar) diske yazılmaz!
        }),
      }
    ),
    { enabled: process.env.NODE_ENV === 'development' }
  )
);
```

---

## 4. Re-render Optimizasyonu ve Seçici Abonelikler

### 4.1 Selector Anti-Pattern'leri ve Zustand v5 Kritik Uyarısı
- **Tüm Store'u Destructure Etmek:** `const { user } = useAppStore();` store'daki alakasız bir sayaç değiştiğinde bile tüm bileşeni yeniden render eder.
- **Inline Nesne Dönmek:** `useAppStore(s => ({ a: s.a, b: s.b }))` her render'da yeni bir referans ürettiği için Zustand v5'te **sonsuz render döngüsüne (Infinite Loop)** girer!

### 4.2 Doğru Tüketim Standartları:
1. **Atomik Primitif Seçici:** `const fullName = useAppStore(s => s.user?.fullName);`
2. **Çoklu Değerlerde `useShallow` Zorunluluğu:**
```tsx
import { useShallow } from 'zustand/react/shallow';

function UserHeader() {
  const { user, theme } = useAppStore(
    useShallow((s) => ({ user: s.user, theme: s.theme }))
  );
  return <div>{user?.fullName} ({theme})</div>;
}
```

---

## 5. URL State Mimarisi (`nuqs` ve Expo Router)

Kullanıcı sayfayı yenilediğinde (F5), linki başkasıyla paylaştığında veya donanımsal geri tuşuna bastığında korunması gereken tüm durumlar URL State'e aittir.

### 5.1 Web: `nuqs` Standardı
```tsx
import { useQueryState, parseAsString, parseAsInteger, debounce } from 'nuqs';

export function ProductFilters() {
  const [search, setSearch] = useQueryState('q', parseAsString.withDefault('').withOptions({
    limitUrlUpdates: debounce(300),
    history: 'replace',
    shallow: true,
  }));
  const [page, setPage] = useQueryState('page', parseAsInteger.withDefault(1));
  // ...
}
```

### 5.2 Mobil: Expo Router `useLocalSearchParams` & `router.setParams`
```tsx
const params = useLocalSearchParams<{ q?: string; page?: string }>();
router.setParams({ q: searchVal || undefined, page: '1' });
```
- Modalların `isOpen` boolean yerine URL query param (`?modal=detail&id=123`) ile açılması, kullanıcının fiziksel geri tuşuna bastığında sayfadan çıkmak yerine modalı kapatmasını sağlar.

---

## 6. "The Great State Unbundling" ve Sync-State Anti-Pattern

### 6.1 Sync-State Felaketi: Server Verisini Store'a Kopyalama Hatası
Sunucudan gelen veriyi `useEffect` ile alıp Zustand'a kopyalamak (`setUsers(data)`); çift gerçek kaynağı (dual sources of truth), bayat veri (stale data), kaskad render dalgaları ve bellek sızıntılarına (GC engelleme) yol açar.

### 6.2 Altın Kural: "Don't Sync State — Derive It" (TkDodo)
İstemci tarafında yalnızca **tanımlayıcı (ID)** saklanır; veri render anında TanStack Query `select` opsiyonu ile doğrudan önbellekten türetilir:

```typescript
const selectedId = useUIStore((s) => s.selectedUserId);
const { data: selectedUser } = useQuery({
  queryKey: ['users'],
  queryFn: fetchUsers,
  select: (users) => users.find((u) => u.id === selectedId),
  enabled: Boolean(selectedId),
});
```

---

## 7. 5 Katmanlı Durum Karar Matrisi (Decision Matrix)

| Katman | Kapsam | Araç Seti | Yaşam Döngüsü |
| :--- | :--- | :--- | :--- |
| **1. Server State** | API verileri, listeler, profiller | TanStack Query v5 | Sunucuya aittir; RAM'de `gcTime` kadar yaşar. |
| **2. URL State** | Filtreler, arama, sayfalama, sekmeler, modallar | `nuqs`, Expo Router `useLocalSearchParams` | Kalıcıdır; linkle paylaşılabilir, F5 ve geri tuşuna dayanıklıdır. |
| **3. Form State** | Girdi değerleri, touched/dirty, anlık validasyon | React 19 `useActionState`, TanStack Form, RHF + Zod | Geçicidir; form gönderilince yok olur. |
| **4. Global Client State** | Oturum token'ı, UI teması, audio player | Zustand v5 (Slices + MMKV) | Oturum boyunca bellekte yaşar; linkte paylaşılmaz. |
| **5. Local Component State** | Dropdown toggle, hover, lokal animasyonlar | `useState`, `useReducer`, `useRef` | Bileşen unmount olunca yok olur. |

---

## 8. Doğrulama ve Kabul Kriterleri (Checklist)

- [ ] Hiçbir `useQuery` sunucu verisi `useEffect` ile Zustand veya `useState` içine kopyalanmıyor.
- [ ] Paylaşılabilir tüm filtre, sayfalama ve sekme durumları URL State (`nuqs` / `useLocalSearchParams`) ile yönetiliyor.
- [ ] Zustand store tek bir monolithic dosya yerine type-safe **Slice Pattern** ile modülerleştirilmiş.
- [ ] Zustand v5 içinde birden çok alan seçilen yerlerde `useShallow` kullanılıyor (inline object selector yok).
- [ ] Mobilde (Expo/React Native) Zustand persist middleware senkron `react-native-mmkv` ile entegre.
- [ ] Form durumları genel store yerine React 19 Actions veya form kütüphanelerinde izole edilmiş.
