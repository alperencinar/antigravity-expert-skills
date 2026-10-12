# Frontend Clean Architecture: Domain Katmanı, Tip Güvenli Değişmezler ve Deterministik Durum Makineleri
## 2025–2026 Endüstriyel Araştırma ve Standartlar Raporu

---

## 1. Yönetici Özeti (Executive Summary)

Modern kurumsal frontend mühendisliğinde (Shopify, Stripe, Coinbase, Linear, Netflix), ön yüz uygulamaları basit birer veri görüntüleme (dumb view) katmanı olmaktan çıkmış; karmaşık istemci taraflı iş kurallarını (client-side business invariants), yerel veri tutarlılığını (local-first state), finansal hesaplama doğruluklarını ve eşzamanlı durum geçişlerini yöneten **dağıtık istemciler (thick clients)** haline gelmiştir.

Geleneksel React uygulamalarındaki "Hook Spaghetti", kontrolsüz `useEffect` bağımlılıkları, $2^N$ kombinasyonel patlamaya yol açan "Boolean Soup" (`isLoading`, `isError`, `isSuccess`) ve `throw new Error()` ile gizlenen hatalar; üretim ortamında yarış durumlarına (race conditions), mükerrer finansal işlemlere ve kırılgan test süreçlerine neden olmaktadır.

Bu araştırma raporu;
1. **Saf TypeScript Varlıkları ve Değer Nesneleri (Pure Entities & Value Objects):** Branded Types ile nominal tip güvenliği ve Primitive Obsession'ın ortadan kaldırılması.
2. **Çalışma Zamanı Validasyon Karşılaştırması:** Zod v3/v4 (`@zod/mini`), ArkType ve TypeBox performans ve paket boyutu kıyaslaması.
3. **Demiryolu Yönelimli Programlama (Railway-Oriented Programming):** `Result<T, E>` / Neverthrow kalıbı ve Discriminated Union tipli domain hataları.
4. **Framework-Agnostic Use Case & IoC Mimarisi:** React ve DOM'dan tamamen izole edilmiş, Repository arayüzleri tüketen interactor'lar.
5. **Saf Hesaplama Motorları & JSDOM'suz Vitest:** Sıfır JSDOM bağımlılığı ile saf Node.js ortamında milisaniyeler içinde çalışan birim testler.
6. **Deterministik Durum Makineleri (FSM & XState v5):** Actor modeli, imkansız durumların engellenmesi ve hafif sıklet Discriminated Union durum makineleri.

başlıklarını ele alarak kurumsal frontend domain katmanı standartlarını belirler.

---

## 2. Saf TypeScript Varlıkları ve Değer Nesneleri (Entities & Value Objects)

### 2.1 Anemic Domain Model vs. Rich Domain Model
Geleneksel frontend mimarilerinde modeller sadece API'den gelen veriyi temsil eden anemic arayüzlerden (`interface UserDto`) ibarettir. İş kuralları ise rastgele bileşenlere veya util dosyalarına dağılır. 

Modern kurumsal mimaride ise:
* **Anti-Corruption Layer (ACL):** Ağdan gelen ham JSON/DTO, sınırda (Transport layer) doğrulanır ve zengin domain entity'sine dönüştürülür.
* **Domain Layer (En İç Çekirdek):** Branded tipler, Value Object'ler ve Rich Entity'ler içerir. İş kuralları ve değişmezler (invariants) nesne içinde enkapsüle edilir.
* **Değişmezlik (Immutability):** Nesneler `Object.freeze` veya immutable veri yapılarıyla korunur; her durum değişimi yeni bir kopya üretir.

### 2.2 Primitive Obsession ve Branded Types (Nominal Typing)
TypeScript yapısal (structural) bir tip sistemine sahiptir. İki tipin yapısı aynıysa (örneğin hepsi `string`), TypeScript bunların birbirinin yerine geçmesine izin verir:

```typescript
// ❌ TEHLİKELİ: Structural typing hatası yakalayamaz
type UserId = string;
type OrderId = string;

function cancelOrder(userId: UserId, orderId: OrderId) { /* ... */ }

const userId: UserId = "usr_123";
const orderId: OrderId = "ord_999";
cancelOrder(orderId, userId); // TypeScript hata vermez!
```

#### Çözüm: `unique symbol` Tabanlı Branded Types
Derleme zamanında var olan fakat çalışma zamanında sıfır maliyet (zero runtime overhead) oluşturan damgalama mekanizması:

```typescript
// domain/shared/brand.ts
declare const __brand: unique symbol;

export type Brand<T, TBrand extends string> = T & {
  readonly [__brand]: TBrand;
};

export type UserId = Brand<string, 'UserId'>;
export type OrderId = Brand<string, 'OrderId'>;
export type UsdCents = Brand<number, 'UsdCents'>;

// Smart Constructors (Invariants)
export function createUserId(raw: string): UserId {
  if (!raw.startsWith('usr_') || raw.length < 10) {
    throw new Error(`Geçersiz UserId formatı: ${raw}`);
  }
  return raw as UserId;
}

export function createUsdCents(raw: number): UsdCents {
  if (!Number.isInteger(raw) || raw < 0) {
    throw new Error(`Sent değeri negatif olamaz ve tam sayı olmalıdır: ${raw}`);
  }
  return raw as UsdCents;
}
```

### 2.3 Value Object Kalıbı: Finansal Hassasiyet (Money Object)
Finansal işlemlerde kayan nokta (floating point IEEE 754: `0.1 + 0.2 === 0.30000000000000004`) hassasiyetsizliğini önlemek için para değerleri daima en küçük birimde (sent/kuruş) tam sayı olarak tutulmalıdır.

```typescript
// domain/money/Money.ts
import { UsdCents, createUsdCents } from '../shared/brand';

export type Currency = 'USD' | 'EUR' | 'TRY';

export class Money {
  readonly amount: UsdCents;
  readonly currency: Currency;

  private constructor(amount: UsdCents, currency: Currency) {
    this.amount = amount;
    this.currency = currency;
    Object.freeze(this);
  }

  public static fromCents(cents: number, currency: Currency = 'USD'): Money {
    return new Money(createUsdCents(cents), currency);
  }

  public add(other: Money): Money {
    if (this.currency !== other.currency) {
      throw new Error(`Farklı para birimleri toplanamaz: ${this.currency} !== ${other.currency}`);
    }
    return new Money((this.amount + other.amount) as UsdCents, this.currency);
  }

  public subtract(other: Money): Money {
    if (this.currency !== other.currency) {
      throw new Error(`Farklı para birimleri çıkartılamaz: ${this.currency} !== ${other.currency}`);
    }
    const result = this.amount - other.amount;
    if (result < 0) {
      throw new Error(`İşlem bakiyeyi negatife düşüremez.`);
    }
    return new Money(result as UsdCents, this.currency);
  }

  public equals(other: Money): boolean {
    return this.amount === other.amount && this.currency === other.currency;
  }
}
```

---

## 3. Çalışma Zamanı Şema Validasyonu: Zod vs. ArkType vs. TypeBox

Dış dünyadan (API yanıtı, URL query, LocalStorage) gelen verilerin domain sınırında doğrulanması gerekir.

### 3.1 2025–2026 Kütüphane Kıyaslama Matrisi

| Kriter | Zod v3 | Zod v4 (Standard / Mini) | ArkType (v2) | TypeBox | Valibot |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Yürütme Mimarisi** | Recursive AST Interpreter | Direct Evaluation | Set-Theoretic Dynamic JIT | JSON Schema AOT/JIT Compiler | Modular Functional Pipe |
| **Throughput (Ops/Sec)** | ~100k - 250k | ~1.2M - 2.5M | ~2.5M - 4.5M | **~5M - 10M+** | ~1.5M - 3M |
| **Paket Boyutu (Min+Gzip)** | ~13.4 kB | Standart: ~5.8 kB<br>**Mini: ~2.1 kB** | ~18.5 kB | ~8.2 kB – 12 kB | **~1.1 kB** |
| **Tree-Shaking** | Düşük | Mükemmel (`zod/mini`) | Orta | İyi | Mükemmel |
| **Tip Çıkarımı** | `z.infer<typeof S>` | `z.infer<typeof S>` | `typeof S.infer` | `Static<typeof S>` | `InferOutput<typeof S>` |
| **Ekosistem Uyumu** | Geniş (De-facto) | Tam geriye dönük uyum | Gelişmekte | OpenAPI / Fastify | Modüler formlar |

### 3.2 Mimari Karar:
- **Standart Kurumsal Frontend:** **Zod v4 (`@zod/mini`)** — Form kütüphaneleri (React Hook Form) ve tRPC ile kusursuz entegrasyon, ~2 kB paket boyutu.
- **Yüksek Hacimli Veri / Websocket Akışları:** **TypeBox** — V8 JIT derlemesi ile maksimum throughput.

---

## 4. Demiryolu Yönelimli Programlama (Result Pattern) ve Tipli Hatalar

### 4.1 Neden `throw new Error()` Terk Edilmelidir?
1. **Tip Sisteminde Görünmezdir:** `async function checkout(): Promise<Order>` imzası hatayı gizler. `catch(e: unknown)` tip güvenliğini sıfırlar.
2. **Beklenen İş Mantığı Dallanmaları ile Çökmeleri Birbirine Karıştırır:** "Yetersiz Bakiye" veya "Kupon Süresi Doldu" birer sistem çökmesi (exception) değil, iş akışının doğal dallanmalarıdır.

### 4.2 Discriminated Union Domain Hataları ve `neverthrow`
İş hataları açık bir etiket alanı (`_tag`) içeren discriminated union tipleri olarak tanımlanır:

```typescript
// domain/errors/CheckoutErrors.ts
import { Money } from '../money/Money';

export type CheckoutDomainError =
  | { readonly _tag: 'InsufficientFundsError'; readonly currentBalance: Money; readonly requiredAmount: Money }
  | { readonly _tag: 'CouponExpiredError'; readonly couponCode: string; readonly expiredAt: Date }
  | { readonly _tag: 'ProductOutOfStockError'; readonly productId: string; readonly availableQuantity: number }
  | { readonly _tag: 'NetworkTimeoutError'; readonly endpoint: string; readonly retryAfterMs: number };
```

#### Railway-Oriented Use Case Akışı:
```typescript
import { Result, ResultAsync, ok, err, safeTry } from 'neverthrow';

export class ProcessCheckoutUseCase {
  constructor(
    private readonly paymentGateway: PaymentGatewayPort,
    private readonly inventory: InventoryPort
  ) {}

  public execute(order: Order, couponCode?: string): ResultAsync<Order, CheckoutDomainError> {
    return safeTry(async function* (this: ProcessCheckoutUseCase) {
      if (order.status !== 'DRAFT') {
        return err<Order, CheckoutDomainError>({
          _tag: 'InsufficientFundsError',
          currentBalance: order.total,
          requiredAmount: order.total,
        });
      }

      // Asenkron demiryolu adımları (Rust `?` operatörü benzeri early return)
      yield* this.inventory.reserveStock(order.id);
      yield* this.paymentGateway.charge(order.customerId, order.total);

      order.pay();
      return ok(order);
    }.bind(this));
  }
}
```

---

## 5. Framework-Agnostic Use Case & Saf Hesaplama Motorları

### 5.1 Inversion of Control (IoC) ve Repository Arayüzleri
Domain katmanı React hook'larını, `fetch`/`axios` kütüphanelerini veya tarayıcı API'lerini bilmez. İhtiyaç duyduğu veri erişimini arayüzler (Ports) üzerinden talep eder:

```typescript
export interface OrderRepository {
  getById(id: OrderId): Promise<Result<Order, DomainError>>;
  save(order: Order): Promise<Result<void, DomainError>>;
}
```

### 5.2 JSDOM'suz Vitest ile Saf Hesaplama Motoru Testleri
Vergi, indirim ve fiyatlandırma hesaplamaları saf fonksiyonlar/motorlar halinde yazılır. Bu sayede testler tarayıcı ortamı (JSDOM) simülasyonuna ihtiyaç duymadan saf Node.js ortamında saniyede 10.000+ assertion hızında çalışır.

```typescript
// domain/pricing/pricingEngine.ts
export class PricingEngine {
  public static calculate(input: CartCalculationInput): CartCalculationResult {
    // Kademeli indirim, kupon indirimi, vergi politikası hesaplama mantığı
    // ...
  }
}
```

---

## 6. Deterministik Durum Makineleri (FSM & XState v5)

### 6.1 "Boolean Soup" Anti-Pattern'ı ve $2^N$ Problemi
Birden fazla bağımsız boolean değişkeni (`isLoading`, `isSubmitting`, `isError`, `isSuccess`) $2^N$ olası durum yaratır. 6 boolean bayrak için 64 durum kombinasyonu oluşur ve bunların büyük çoğunluğu imkansızdır (örneğin hem `isLoading: true` hem `isSuccess: true`).

### 6.2 XState v5 Actor Modeli
XState v5 ile her makine olay mesajları ile haberleşen bir aktördür. Yan etkiler `fromPromise` veya `fromCallback` aktörlerine delege edilir. React tarafında `useSelector` kullanılarak yalnızca ilgilenilen durum parçası dinlenir ve gereksiz re-render'lar engellenir.

### 6.3 Hafif Sıklet (Zero-Dependency) Discriminated Union FSM
Basit durum geçişleri için kütüphane bağımlılığı olmadan TypeScript Discriminated Union ve `useReducer` kullanılır:

```typescript
export type AuthState =
  | { readonly status: 'unauthenticated' }
  | { readonly status: 'authenticating'; readonly email: string }
  | { readonly status: 'authenticated'; readonly token: string; readonly user: User }
  | { readonly status: 'error'; readonly message: string };

export type AuthEvent =
  | { readonly type: 'LOGIN_SUBMIT'; readonly email: string }
  | { readonly type: 'LOGIN_SUCCESS'; readonly token: string; readonly user: User }
  | { readonly type: 'LOGIN_FAILURE'; readonly error: string }
  | { readonly type: 'LOGOUT' };
```

---

## 7. Gerçek Hayat Vaka Analizleri

- **Stripe & Checkout (3D Secure Yarış Durumları):** Mükerrer form gönderimi ve 3D Secure modal açılışlarındaki ağ kopmalarına karşı FSM kurgulanarak mükerrer çekim riski sıfıra indirilmiştir.
- **Netflix (Video Oynatıcı Yaşam Döngüsü):** Scrubbing, tamponlama, ABR kalite değişimi ve reklam araları paralel statechart bölgeleri (parallel states) ile yönetilmiş, desekronizasyonlar çözülmüştür.
- **Shopify (Bölgesel Vergi & İndirim Motoru):** Sepet hesaplama mantığı saf TypeScript `PricingEngine` motoruna taşınarak aynı kod tabanı hem Web hem POS mobil uygulamasında %100 paylaşıma kavuşmuştur.

---

## 8. 2025–2026 Doğrulama Kontrol Listesi (Checklist)

- [ ] **Sıfır React Bağımlılığı:** Domain ve Use Case dosyalarında `import React` veya `use...` hook referansı bulunmaz.
- [ ] **Branded ID'ler:** Tüm varlık kimlikleri (`UserId`, `OrderId`) `Brand<string, 'Name'>` ile nominal hale getirilmiştir.
- [ ] **Tamsayı Finans:** Para hesaplamaları sent/kuruş cinsinden tam sayı `Money` Value Object ile modellenmiştir.
- [ ] **Hata Fırlatmama Kuralı:** Use case fonksiyonları exception fırlatmaz; `neverthrow` (`Result<T, E>`) döndürür.
- [ ] **Hafif Şema Validasyonu:** Sınır doğrulamalarında Zod v4 (`@zod/mini`) veya TypeBox tercih edilir.
- [ ] **Deterministik Durum:** 3+ birbiriyle ilişkili boolean bayrak yerine FSM (XState v5 veya Discriminated Union) kullanılır.
- [ ] **Hızlı Test Koşumu:** Domain birim testleri Vitest ile saf Node.js ortamında (JSDOM olmadan) çalışır.
