# Frontend Clean Architecture: Altyapı, Ağ İstemcileri, Önbellek ve Güvenli Depolama Mimarisi
## 2025–2026 Endüstriyel Araştırma ve Standartlar Raporu

---

## 1. Yönetici Özeti (Executive Summary)

Modern kurumsal frontend ve mobil (React Native / Expo) uygulamalarında **Altyapı ve Veri Katmanı (Infrastructure / Data Layer)**; uygulamanın dış dünyayla (REST/GraphQL API'leri, WebSocket bağlantıları, yerel veritabanları, donanımsal anahtarlıklar) etkileşim kurduğu sınır bölgesidir.

Clean Architecture ve Domain-Driven Design (DDD) ilkelerine göre bu katmanın temel misyonu; dış dünyanın getirdiği istikrarsızlıkları (şema değişiklikleri, ağ kopmaları, 401 yetkilendirme yarış durumları, XSS saldırıları) filtrelemek ve iç dünyaya (Domain ve UI katmanlarına) saf, tip güvenli, tahmin edilebilir veriler sunmaktır.

Bu araştırma raporu;
1. **Modern HTTP İstemcileri ve Tip Güvenli Ağ Mimarisi:** Axios'un 12 KB'lık gerilemesi, yerel `fetch` sarmalayıcıları, `openapi-fetch` ve soğan modeli middleware boru hatları.
2. **JWT Refresh Token 401 Yarış Durumları:** Single-Flight Promise Memoization kalıbıyla tek uçuşlu token yenileme ve oturum koruması.
3. **Ağ Dayanıklılığı (Resilience):** AWS Full Jitter algoritması, exponential backoff ve `AbortSignal.any` ile zaman aşımı/unmount koordinasyonu.
4. **Anti-Corruption Layer (ACL) ve DTO-Domain Dönüştürücüleri:** Zod tabanlı "Parse, Don't Validate" iki yönlü haritalama (`toDomain` ve `toDTO`) ve HTTP hata kodlarının domain modellerine eşlenmesi.
5. **Clean Architecture'da TanStack Query v5:** Query Key Factory piramidi, `queryOptions` standardı, `staleTime` vs `gcTime` ve 4 fazlı deterministik Optimistic Update & Rollback döngüsü.
6. **Web ve Mobil Güvenlik / Depolama Mimarisi:** Web'de `localStorage` yasağı, BFF (Backend-For-Frontend) HttpOnly çerezleri; Mobil/Expo'da `expo-secure-store` (Keychain/Keystore) ve `react-native-mmkv` hibrit savunma modeli.

başlıklarını detaylı teknik referanslar ve üretim kodlarıyla ele almaktadır.

---

## 2. Modern HTTP İstemcileri ve Tip Güvenli Ağ Mimarisi

### 2.1 İstemci Karşılaştırma Matrisi (2025–2026)

| Kriter / İstemci | **Axios (v1.7+)** | **Ky / ofetch** | **openapi-fetch (v0.13+)** | **tRPC (v11+)** | **Native fetch + Custom Pipeline** |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Temel Altyapı** | XHR / Node http adaptörü | Native `fetch` API | Native `fetch` API | HTTP / WebSocket Batching | Web Standard `fetch` |
| **Paket Boyutu (Gzip)** | ~11 – 13 KB | ~1.5 – 2 KB | **< 1 KB** (Yalnızca types) | ~3 – 5 KB (Client core) | **0 KB** (Zero overhead) |
| **Tip Güvenliği** | Manuel Generic (`axios.get<T>`) | Manuel Generic | **Tam Otomatik / Derleme Zamanı** | **End-to-End Strict Inferred** | Manuel veya Zod ile çıkarım |
| **Runtime Doğrulama** | Yok | Yok | Opsiyonel middleware | Zod / ArkType entegre | Geliştiriciye bağlı |
| **Hata Davranışı** | Non-2xx'de otomatik reject | `HTTPError` fırlatır | `{ data, error }` döner (fırlatmaz) | `TRPCClientError` fırlatır | `ok: false` döner |
| **React Native (Fabric)** | Adaptör gerekebilir | Mükemmel (Hermes) | Mükemmel | Mükemmel | Mükemmel |

#### Trend & Değerlendirme:
- **Axios Anti-Pattern'ı:** Modern tarayıcılar, Hermes (React Native) ve Edge ortamlarında (Cloudflare, Vercel) yerel `fetch` standardı yerleştiği için Axios'un yüksek boyutu ve generic tip sızıntıları tercih edilmemektedir.
- **REST için Standart:** OpenAPI şeması mevcutsa `openapi-fetch`, yoksa `Ky` veya ince yerel `fetch` pipeline'ı kullanılmalıdır.

### 2.2 JWT Refresh Token Race Condition (Single-Flight Promise Memoization)

Birden çok paralel istek (örneğin sayfa açılışında 5 bileşenin sorgusu) aynı anda `401 Unauthorized` aldığında, 5 ayrı yenileme isteği fırlatılırsa backend'in Refresh Token Rotation (RTR) mekanizması bunu token hırsızlığı olarak algılayıp oturumu kapatabilir.

#### Çözüm: Tek Uçuşlu Promise Kilidi
```typescript
class TokenManager {
  private refreshPromise: Promise<string> | null = null;

  async getValidToken(): Promise<string> {
    if (this.refreshPromise) {
      return this.refreshPromise; // Devam eden tek isteğe abone ol
    }

    this.refreshPromise = (async () => {
      try {
        const refreshToken = await storage.getRefreshToken();
        const res = await fetch('/api/auth/refresh', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refreshToken }),
        });
        if (!res.ok) throw new Error('Oturum süresi doldu');
        const data = await res.json();
        await storage.saveTokens(data);
        return data.accessToken;
      } finally {
        this.refreshPromise = null; // İşlem bitince kilidi sıfırla
      }
    })();

    return this.refreshPromise;
  }
}
```

### 2.3 Ağ Dayanıklılığı (Resilience): Full Jitter & AbortSignal

Ağ istikrarsızlıklarında sunucuyu thundering herd etkisinden korumak için AWS Full Jitter algoritması ve ECMAScript standartlarındaki `AbortSignal.any` birleşimi uygulanmalıdır:

```typescript
export async function fetchWithResilience(url: string, init: RequestInit, config: RetryConfig): Promise<Response> {
  const combinedSignal = AbortSignal.any([
    config.userSignal ?? new AbortController().signal,
    AbortSignal.timeout(config.timeoutMs ?? 8000),
  ]);

  let attempt = 0;
  while (true) {
    attempt++;
    try {
      const response = await fetch(url, { ...init, signal: combinedSignal });
      if (response.ok || !config.retryableStatuses.includes(response.status)) return response;
      if (attempt > config.maxRetries) return response;

      // AWS Full Jitter: Sleep = random(0, min(MaxDelay, BaseDelay * 2^attempt))
      const delay = Math.random() * Math.min(config.maxDelayMs, config.baseDelayMs * Math.pow(2, attempt - 1));
      await new Promise((r) => setTimeout(r, delay));
    } catch (err) {
      if (attempt > config.maxRetries) throw err;
    }
  }
}
```

---

## 3. Anti-Corruption Layer (ACL) ve DTO Haritalama

Backend'in `snake_case` alanları veya ilişkisel ID modelleri doğrudan UI bileşenine veya Domain katmanına sızdırılamaz. 

### 3.1 Çift Yönlü Haritalama (`toDomain` ve `toDTO`)
```typescript
import { z } from 'zod';

export const UserDtoSchema = z.object({
  user_id: z.string().uuid(),
  first_name: z.string(),
  last_name: z.string(),
  is_active: z.union([z.literal(1), z.literal(0)]),
});
export type UserDto = z.infer<typeof UserDtoSchema>;

export class UserMapper {
  public static toDomain(raw: unknown): UserProfile {
    const dto = UserDtoSchema.parse(raw);
    return {
      id: dto.user_id as UserId,
      fullName: `${dto.first_name} ${dto.last_name}`.trim(),
      isActive: dto.is_active === 1,
    };
  }

  public static toDTO(domain: UserProfile): Record<string, unknown> {
    return {
      user_id: domain.id,
      first_name: domain.fullName.split(' ')[0],
      last_name: domain.fullName.split(' ').slice(1).join(' '),
      is_active: domain.isActive ? 1 : 0,
    };
  }
}
```

---

## 4. TanStack Query v5 in Clean Architecture

### 4.1 Katman Konumlandırması
- **Domain Katmanı:** Sıfır TanStack Query referansı. Yalnızca saf modeller ve Repository arayüzleri.
- **Altyapı (Infrastructure):** Repository sınıfları (`TodoRepository.getTodos()`). Saf `Promise<Todo[]>` döner.
- **Presentation Adapters:** `queryOptions` ve Query Key Factory tanımları.
- **Presentation UI:** Custom React hook'ları (`useTodos()`).

### 4.2 Query Key Factory & `queryOptions` Deseni
```typescript
export const todoKeys = {
  all: ['todos'] as const,
  lists: () => [...todoKeys.all, 'list'] as const,
  list: (filters: TodoFilters) => [...todoKeys.lists(), { filters }] as const,
  detail: (id: string) => [...todoKeys.all, 'detail', id] as const,
};

export const todoQueries = {
  list: (filters: TodoFilters) =>
    queryOptions({
      queryKey: todoKeys.list(filters),
      queryFn: ({ signal }) => todoRepository.getTodos(filters, signal),
      staleTime: 1000 * 60 * 2,
    }),
  detail: (id: string) =>
    queryOptions({
      queryKey: todoKeys.detail(id),
      queryFn: ({ signal }) => todoRepository.getTodoById(id, signal),
      staleTime: 1000 * 60 * 5,
    }),
};
```

### 4.3 4 Fazlı Deterministik Optimistic Update Döngüsü
1. **`cancelQueries`:** Devam eden eski fetch isteklerinin iyimser veriyi ezmesini önler.
2. **`onMutate`:** Önbelleğin anlık kopyasını (**Snapshot**) alır ve UI'ı anında günceller.
3. **`onError`:** Ağ/sunucu hatasında snapshot verisini önbelleğe geri yükler (**Rollback**).
4. **`onSettled`:** Nihai tutarlılık için `invalidateQueries` ile sunucudaki son durumu senkronize eder.

---

## 5. Depolama ve Güvenlik Mimarisi (Web vs. Mobil)

### 5.1 Web: `localStorage` Yasağı ve BFF Modeli
- `localStorage` ve `sessionStorage` XSS saldırılarına karşı tamamen savunmasızdır; herhangi bir 3. parti script `localStorage.getItem('token')` ile token'ı çalabilir.
- **Kurumsal Standart:** Backend-For-Frontend (BFF) mimarisi ile `__Host-` prefixed `HttpOnly; Secure; SameSite=Strict` çerezleri kullanılmalıdır. JavaScript bu çerezleri okuyamaz.

### 5.2 Mobil (React Native / Expo): MMKV vs. SecureStore Hibrit Mimarisi
- `AsyncStorage` (Bridge tabanlı, metin SQLite) 2025 standartlarında yavaşlığı nedeniyle terk edilmiştir.
- **`expo-secure-store`:** Donanımsal koruma (iOS Keychain / Android Keystore) sağlar ancak Android'de 2 KB boyut limiti vardır. Sadece Refresh Token ve şifreleme anahtarları için kullanılmalıdır.
- **`react-native-mmkv`:** C++ JSI / Memory-Mapped Files (`mmap`) ile AsyncStorage'dan **~20-100x daha hızlıdır** ve senkrondur.
- **Hibrit Model:** Donanımsal anahtarlıkta üretilen 32-byte rastgele AES anahtarı ile `react-native-mmkv` şifrelenir; offline cache ve dehydration bu güvenli alanda tutulur.

---

## 6. Doğrulama ve Kabul Kriterleri (Checklist)

- [ ] **DTO Sızıntı Yasağı:** Backend JSON nesneleri doğrudan UI'a geçirilmez; ACL Data Mapper'dan geçer.
- [ ] **İstemci Bağımsızlığı:** UI bileşenleri `fetch` veya Axios çağırmaz; Repository arayüzlerini kullanır.
- [ ] **Single-Flight 401 Koruması:** Paralel 401 durumlarında tek bir refresh isteği tetiklenir.
- [ ] **Query Key Factory:** TanStack Query key'leri merkezi factory ve `queryOptions` ile tanımlanır.
- [ ] **Rollback Garantisi:** Optimistic güncellemeler `onMutate (snapshot)` ve `onError (rollback)` içerir.
- [ ] **Güvenli Depolama:** Web'de `localStorage`'da token tutulmaz (HttpOnly cookie zorunludur); mobilde donanımsal Keychain/Keystore + şifreli MMKV hibrit modeli kullanılır.
