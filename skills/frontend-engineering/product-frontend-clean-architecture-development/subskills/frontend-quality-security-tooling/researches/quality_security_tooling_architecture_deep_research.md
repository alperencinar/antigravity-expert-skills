# Frontend Clean Architecture: Test Mimarisi, İstemci Güvenliği, Derleme Araçları ve Monorepo Yönetişimi
## 2025–2026 Endüstriyel Araştırma ve Standartlar Raporu

---

## 1. Yönetici Özeti (Executive Summary)

Modern frontend ve fullstack web/mobil mühendisliğinde **Kalite, Güvenlik ve Araç Zinciri (Quality, Security & Tooling)**; bir uygulamanın üretim ortamındaki dayanıklılığını, geliştirici hızını (Developer Velocity) ve kurumsal mimari sürdürülebilirliğini belirleyen temel omurgadır.

2025–2026 döneminde bu alanda dört büyük tektonik dönüşüm yaşanmıştır:
1. **Testing Trophy ve Vitest v2 Hakimiyeti:** Jest'in CommonJS/Babel mirasından kaynaklanan CI yavaşlığı ve bellek sızıntıları nedeniyle Vitest v2 (~6x daha hızlı, native Vite ESM) standart hale gelmiştir. React Testing Library ile kullanıcı erişilebilirlik rolleri (`getByRole`) üzerinden davranış odaklı test yazımı ve MSW v2 (Mock Service Worker) ile ağ seviyesinde mocklama zorunlu kılınmıştır.
2. **Hermetik E2E ve Görsel Regresyon:** Playwright'ın 6 adımlı Actionability kontrolleri (auto-waiting), `storageState` ile oturum önbellekleme ve Docker tabanlı Pixelmatch görsel regresyon testleri Cypress ve Selenium'u tamamen geride bırakmıştır.
3. **OWASP Frontend Güvenliği & CSP v3:** DOMPurify'ı W3C standardı **Trusted Types API** ile birleştiren yapı; Next.js App Router'da nonce-tabanlı Strict CSP v3 (sıfır `'unsafe-inline'`), React 19 Taint API (`server-only`, `experimental_taintObjectReference`) ile RSC veri sızıntılarını önleme ve `__Host-` çerez prefiksleri standartlaştırılmıştır.
4. **Rust-Tabanlı Toolchain & Monorepo:** ESLint ve Prettier yerine Rust ile yazılan **Biome 2.x** (~25x-35x hızlanma, tek `biome.json`), Turborepo Docker `turbo prune`, `@size-limit/preset-app` ile PR blocking ve mimari kararların versiyonlanması için **MADR 4.x** benimsenmiştir.

---

## 2. Testing Trophy & Modern Frontend Test Mimarisi

### 2.1 Testing Trophy Katmanları ve ROI Dağılımı

```
           / \
          /   \        4. E2E & Görsel Regresyon (Playwright) - Kritik akışlar
         /-----\
        /       \      3. Entegrasyon (RTL + MSW v2 + Vitest) - [TATLI NOKTA]
       /---------\
      /           \    2. Birim Testler (Vitest v2) - Saf domain mantığı
     /-------------\
    /               \  1. Statik Analiz (TypeScript, Biome) - Anlık kalkan
   /_________________\
```

- **Entegrasyon Katmanı (Tatlı Nokta):** Bileşen ağaçlarının, hook'ların ve API etkileşimlerinin kullanıcı bakış açısıyla test edildiği yerdir. En yüksek ROI'yi sunar.
- **Altın İlke:** *"Testleriniz uygulamanızın gerçekte kullanılma biçimine ne kadar benzerse, size o kadar çok güven sağlar."* (Kent C. Dodds).

### 2.2 Vitest v2 vs. Jest: Neden Jest Artık Legacy?
1. **Babel / ts-jest Yavaşlığı:** Jest, her test worker'ında dosyaları baştan derlerken; Vitest doğrudan Vite'ın modül grafiğini ve esbuild/Rolldown derleyicisini paylaşır.
2. **ESM Desteği:** Jest CommonJS tabanlı olduğundan Pure ESM paketlerinde patlar; Vitest yerel ESM motoruyla sıfır konfigürasyonla çalışır.
3. **CI Performansı:** 1200 testlik pakette Vitest soğuk başlatmada **~6 kat daha hızlıdır** (48s vs 8s) ve %60 daha az bellek tüketir. Watch modunda tepki süresi 280 ms'dir.

---

## 3. React Testing Library & MSW v2 Standartları

### 3.1 RTL Sorgu Öncelik Hiyerarşisi (Query Priority)
1. **`getByRole(role, { name: /.../i })`:** Herkese ve ekran okuyucuya erişilebilir semantik rol ve isim. (Altın Standart).
2. **`getByLabelText`:** Form alanları için etiket eşleşmesi.
3. **`getByText`:** Buton harici statik metinler.
4. **`getByTestId`:** Yalnızca rolü olmayan çok dinamik durumlarda son çare olarak kullanılır; aşırı kullanımı a11y açıklarını gizler.

> [!CAUTION]
> **Anti-Pattern:** `wrapper.state()` veya bileşenin dahili props/state'ini test etmek ile `fireEvent` kullanımı yasaktır. Daima gerçek kullanıcı girdisini simüle eden `userEvent.setup()` kullanılmalıdır.

### 3.2 MSW v2: Ağ Seviyesinde Mocklama & `global.fetch` Yasağı
- `global.fetch = vi.fn()` yazmak HTTP durum kodlarını, header'ları ve istek serileştirmesini doğrulamadığı için zehirli bir anti-pattern'dir.
- **MSW v2:** Service Worker (tarayıcı) ve Interceptors (Node.js) seviyesinde ağı dinler. Tek bir `handlers.ts` dosyası Vitest, Storybook ve Playwright arasında %100 paylaşılır.

---

## 4. Playwright E2E & Görsel Regresyon (Visual Regression)

### 4.1 6 Adımlı Otomatik Bekleme (Actionability Checks)
Playwright `click()` veya `type()` öncesinde 6 kontrolü otomatik tamamlar:
1. Attached (DOM'da var mı?)
2. Visible (Görünür mü?)
3. Stable (Animasyon bitti mi?)
4. Enabled (Disabled değil mi?)
5. Editable (Yazılabilir mi?)
6. Receives Events (Üzerinde spinner/overlay var mı?)

*Kural:* `waitForTimeout(3000)` gibi keyfi beklemeler kesinlikle yasaktır; her bekleme web assertion'ı (`expect(locator).toBeVisible()`) olmalıdır.

### 4.2 `storageState` ile Kimlik Doğrulama Önbellekleme
Her E2E testinde UI'dan form doldurmak yerine `setup-auth` projesiyle bir kez login olup `storageState: 'e2e/.auth/user.json'` dosyası test projeleri arasında salt-okunur paylaşılır.

### 4.3 Görsel Regresyon Testleri (Pixelmatch)
- Ekran görüntüleri işletim sistemi font farklarından etkilenmemesi için **daima CI veya resmi Playwright Docker imajında** çalıştırılır.
- Dinamik avatarlar ve zaman damgaları `mask` parametresi ile gizlenir; `animations: 'disabled'` ile animasyonlar dondurulur.

---

## 5. Modern Frontend Güvenliği (OWASP SPA & SSR)

### 5.1 DOMPurify + W3C Trusted Types API
- Tarayıcı seviyesinde `require-trusted-types-for 'script'` CSP başlığı ile düz string'lerin `innerHTML`'e enjekte edilmesi engellenir.
- DOMPurify bir `trustedTypes.createPolicy('dompurify-policy', ...)` içerisine bağlanarak yalnızca `TrustedHTML` nesnesi üretir.

### 5.2 Strict CSP v3 (Nonce Tabanlı)
Next.js App Router middleware katmanında her istek için kriptografik bir `nonce` üretilir; `'unsafe-inline'` tamamen kaldırılarak `'strict-dynamic'` ile güvenli script yüklemeleri sağlanır.

### 5.3 SSR ve RSC Uçtan Uca Veri Sızıntısı Koruması
- **`server-only`:** Veritabanı ve gizli anahtar içeren modüllerin client bundle'a girmesini derleme anında engeller.
- **React 19 Taint API:** `experimental_taintObjectReference` ve `experimental_taintUniqueValue` ile hassas nesnelerin client Flight stream'e serialize edilmesi çalışma anında engellenir.
- **`__Host-` Çerezleri:** `__Host-session-token` çerezleri HTTPS zorunlu, `Path=/`, `HttpOnly` ve subdomain spoofing korumalıdır.

---

## 6. Modern Toolchain, Monorepo ve Mimari Liderlik

### 6.1 Biome 2.x vs. ESLint 9 + Prettier
- Rust ile yazılan Biome, 10.000 dosyada linting ve formatting işlemlerini **~1.5 saniyede** tamamlayarak ESLint/Prettier'a göre **25x-35x hızlanma** ve %80 daha az bellek tüketimi sağlar.
- Tek bir `biome.json` ile tüm kurallar yönetilir.

### 6.2 Turborepo ve Docker `turbo prune`
- Monorepolarda Docker build alırken `turbo prune <app> --docker` ile sadece hedef uygulamanın `package.json` ve kaynak kodları izole edilir; Docker layer cache'leri korunur.
- Remote Cache ile CI derleme süreleri %60-80 oranında kısalır.

### 6.3 CI Bundle Guardrail (`size-limit`) & MADR Yönetişimi
- `@size-limit/preset-app` ile her PR'da JavaScript chunk boyutları denetlenir; bütçeyi aşan PR'lar CI'da bloklanır.
- Büyük mimari kararlar kod reposunda **MADR (Markdown Architectural Decision Records)** formatında versiyonlanır (`docs/decisions/000X-*.md`).

---

## 7. Doğrulama ve Kabul Kriterleri (Checklist)

- [ ] Projede Jest bağımlılığı kalmadı; tüm test suite Vitest v2 üzerinde çalışıyor.
- [ ] RTL testlerinde `data-testid` ve `fireEvent` yerine `getByRole` ve `userEvent.setup()` kullanılıyor.
- [ ] Ağ mocklamalarında `global.fetch = vi.fn()` yasaklandı; MSW v2 handler'ları kullanılıyor.
- [ ] Playwright E2E testlerinde keyfi `waitForTimeout` yok; `storageState` ile oturum önbellekleniyor.
- [ ] Dinamik HTML render edilen yerlerde DOMPurify + Trusted Types politikası uygulanıyor.
- [ ] Next.js SSR'da nonce-tabanlı Strict CSP v3 aktif (`'unsafe-inline'` yok).
- [ ] Gizli sunucu anahtarları `server-only` ve React 19 Taint API ile korunuyor.
- [ ] Kod formatlama ve linting Biome 2.x ile yürütülüyor.
- [ ] PR'lar `@size-limit/preset-app` paket boyutu bütçe denetiminden geçiyor.
- [ ] Kritik mimari değişiklikler MADR formatında belgelenmiş.
