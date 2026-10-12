# Frontend Clean Architecture: Çalışma Zamanı Performansı, Core Web Vitals ve Çapraz Platform Ergonomisi
## 2025–2026 Endüstriyel Araştırma ve Standartlar Raporu

---

## 1. Yönetici Özeti (Executive Summary)

Modern web ve mobil mimarilerinde performans ve ergonomi; yalnızca "hızlı kod yazmak" değil, **kullanıcı etkileşim gecikmesini (Interaction to Next Paint - INP)** bütçe altında tutmak, **60/120 Hz kare hızını kilitlemek**, bellek ayak izini minimize etmek ve dokunmatik işletim sistemlerinin modern kurallarına (Android 15 Edge-to-Edge, iOS ProMotion) tam uyum sağlamaktır.

2025–2026 standartlarında iki temel paradigma değişimi gerçekleşmiştir:
1. **Web Tarafında React 19 Compiler ve INP:** Google, FID'yi kaldırıp INP'yi (< 200 ms) temel metrik haline getirmiştir. LoAF (Long Animation Frames API) ile main thread blokajları milisaniyelik script bazında izlenmekte; `scheduler.yield()` ve Web Worker'lar ile görevler bölünmektedir. React 19 Compiler (`useMemoCache`), manuel `useMemo`/`useCallback` pratiklerini gereksiz kılmış; katı "Rules of React" saflığını zorunlu hale getirmiştir.
2. **Mobil Tarafında Fabric ve Android 15 Zorunlulukları:** React Native New Architecture (Fabric) ile liste sanallaştırmasında `FlatList`'in windowing modeli terk edilmiş; **`@shopify/flash-list v2`'nin Hücre Geri Dönüşümü (Cell Recycling)** mimarisine geçilmiştir. Android 15'te zorunlu hale gelen Edge-to-Edge kuralı nedeniyle eski `KeyboardAvoidingView` ve `<SafeAreaView>` kırılmış; **`react-native-safe-area-context`** ve **`react-native-keyboard-controller`** zorunlu kılınmıştır.

---

## 2. Interaction to Next Paint (INP) ve Main Thread Optimizasyonu

### 2.1 INP Bütçesi (< 200 ms) Anatomisi
INP, sayfanın tüm yaşam döngüsü boyunca gerçekleşen kullanıcı etkileşimlerini (tıklama, dokunma, tuş vuruşu) P75 persentilinde ölçer:

$$\text{INP Toplam Süresi} = \text{Input Delay (< 50 ms)} + \text{Processing Duration (< 50 ms)} + \text{Presentation Delay (< 100 ms)}$$

- **Input Delay:** Main thread'deki uzun görevler (Long Tasks > 50 ms) yüzünden olayın kuyrukta bekleme süresi.
- **Processing Duration:** JavaScript event listener kodunun CPU çalışma süresi.
- **Presentation Delay:** DOM mutasyonu sonrası tarayıcının render adımı (Style -> Layout -> Paint -> Composite). Büyük DOM ve Layout Thrashing burayı şişirir.

### 2.2 Long Animation Frames API (LoAF) ile Teşhis
Chrome 123+ ile gelen LoAF API, 50 ms'yi aşan her görsel kareden telemetri toplar:
```typescript
const observer = new PerformanceObserver((list) => {
  for (const entry of list.getEntries() as any[]) {
    if (entry.duration > 50) {
      console.warn('[LoAF Alert]', {
        totalDuration: entry.duration,
        blockingDuration: entry.blockingDuration,
        scripts: entry.scripts.map((s: any) => ({
          invoker: s.invoker,
          fn: s.sourceFunctionName,
          url: s.sourceURL,
          duration: s.duration,
          forcedReflow: s.forcedStyleAndLayoutDuration,
        })),
      });
    }
  }
});
observer.observe({ type: 'long-animation-frame', buffered: true });
```

### 2.3 `scheduler.yield()` ile Görev Parçalama (Cooperative Multitasking)
`setTimeout(fn, 0)` HTML standardı gereği iç içe çağrılarda 4 ms ceza uygular ve görev önceliğini kaybeder. Chrome 129+ `scheduler.yield()` ise tarayıcının bekleyen girdi ve paint işlerini yapmasına izin verip göreve öncelikli devam eder:

```typescript
export async function yieldToMain(): Promise<void> {
  if ('scheduler' in window && typeof (window as any).scheduler.yield === 'function') {
    return (window as any).scheduler.yield();
  }
  // Fallback: 0-clamp MessageChannel macrotask devri
  return new Promise((resolve) => {
    const channel = new MessageChannel();
    channel.port1.onmessage = () => resolve();
    channel.port2.postMessage(null);
  });
}
```

### 2.4 Ağır İşleri Main Thread Dışına Taşıma: Comlink + Web Workers
CPU-yoğun analiz ve filtreleme işleri Comlink RPC ile Web Worker'a; karmaşık grafik çizimleri ise `OffscreenCanvas`'a taşınmalıdır.

---

## 3. Production Ortamında React 19 Compiler

### 3.1 Otomatik Memoization Motoru (`useMemoCache`)
React 19 Compiler (Forget), kodu High-Level Intermediate Representation (HIR) ve SSA formundaki kontrol akış grafiğine çevirir. Değişkenlerin reaktif kapsamlarını ispatlayarak `_c(slotSize)` dizisi üzerinden otomatik önbellekler.

### 3.2 Manuel Memoization Anti-Pattern'ı
Compiler devredeyken elle `useMemo`, `useCallback` ve `React.memo` yazmak:
- Closure ve runtime dizi karşılaştırma ek yükü (overhead) yaratır.
- Stale closure hatalarına zemin hazırlar.
- **Kural:** Idiomatic, saf JavaScript yazılmalı; derleyici optimizasyonu alt-ifade bazında kendisi yönetmelidir.

### 3.3 "Rules of React" Zorunluluğu:
1. **Bileşen Saflığı:** Render anında sıfır yan etki.
2. **Sıfır Render Mutasyonu:** Prop veya modül seviyesi nesneleri render içinde doğrudan değiştirmek (in-place mutation) yasaktır; derleyici optimizasyonu anında iptal eder.

---

## 4. Kaynak ve Bundle Optimizasyonu (LCP & CLS)

1. **Route-Based Splitting & `<link rel="modulepreload">`:** Dinamik import'lar sayfa seviyesinde tutulmalı; bağlantı üzerine gelindiğinde `modulepreload` ile JS önceden derlenmelidir.
2. **Görsel Formatları & LCP:** En üstteki Hero görseline kesinlikle `fetchpriority="high"` verilmeli ve `loading="lazy"` verilmemelidir! Format olarak AVIF ve WebP kullanılmalıdır.
3. **Cumulative Layout Shift (CLS < 0.1) Sıfırlama:** CSS `aspect-ratio` veya BlurHash yer tutucuları kullanılarak görsel inmeden önce kutu geometrisi rezerve edilmelidir.

---

## 5. Çapraz Platform Liste Sanallaştırması (Virtualization)

### 5.1 Neden `FlatList` Kesinlikle Yasaktır?
- **FlatList Windowing Çöküşü:** Ekranda olmayan elemanları yok eder (`unmount`) ve tekrar oluşturur (`mount`). 120 Hz ProMotion ekranlarda bellek tahsis baskısı (memory churn), GC duraklamaları ve beyaz alan patlamaları üretir.
- **FlashList v2 Cell Recycling:** Hücreleri yok etmek yerine yerel görünüm havuzunda (cell pool) tutar; sadece yeni verinin props'larını enjekte eder. Native View tahsis maliyeti $O(1)$'dir.

### 5.2 FlashList v2 ile Gelen Fabric Standartları:
- **`estimatedItemSize` Kaldırıldı:** Fabric'in senkron layout ölçümü sayesinde artık yaklaşık boyut tahminlerine gerek kalmamıştır.
- **Boş Alanları Engelleme:** `drawDistance={SCREEN_HEIGHT * 1.5}` tamponu ile hızlı kaydırmada dahi sıfır beyaz alan elde edilir.
- **İç `key` Yasağı:** `renderItem` içinde dinamik `key` kullanılamaz; hücre havuzu çökertilmemelidir.

### 5.3 Web Headless Sanallaştırma: TanStack Virtual v3
Web tarafında DOM'u binlerce düğümle boğmamak için headless matematik motoru TanStack Virtual kullanılır. `virtualizer.measureElement` ile `ResizeObserver` üzerinden dinamik eleman yükseklikleri otomatik ölçülür.

---

## 6. Mobil Ergonomi Standartları (Android 15 & Klavye)

### 6.1 Android 15 Edge-to-Edge Zorunluluğu:
- Android 15 (SDK 35+) ile Status Bar ve Navigation Bar şeffaf hale getirilmiştir (`windowOptOutEdgeToEdgeEnforcement` kaldırıldı).
- React Native'in eski `<SafeAreaView>` bileşeni Android'de bu çubukları doğru algılayamaz.
- **Zorunlu Standart:** Kök dizinde `SafeAreaProvider` ve ekran bileşenlerinde dinamik `useSafeAreaInsets()` kullanımıdır.

### 6.2 `KeyboardAvoidingView` Çöküşü & `react-native-keyboard-controller`
- Standart `KeyboardAvoidingView` Android 15 Edge-to-Edge altında alt çubuk yüksekliğini yanlış hesaplayarak input'u klavyenin arkasında bırakır ve jank üretir.
- **Çözüm:** C++ yerel insets dinleyicisi ve Reanimated worklet'leri ile çalışan `react-native-keyboard-controller`. 120 FPS akıcı animasyon ve parmakla interaktif kapatma (`keyboardDismissMode="interactive"`) sağlar.

### 6.3 Dokunma ve Haptic Ergonomisi:
- **Dokunma Hedefi:** WCAG 2.2 AA gereği web'de asgari $24\times24\text{ px}$, mobil iOS/Android'de asgari $44\times44\text{ pt}$ / $48\times48\text{ dp}$. Küçük ikonlar `hitSlop` ile genişletilmelidir.
- **Haptic Geri Bildirim:** Tab geçişlerinde `selectionAsync`, buton tıklamasında `impactAsync(Light)`, silme/onay işlemlerinde `notificationAsync` ile kullanıcıya fiziksel temas hissi sunulmalıdır.

---

## 7. Doğrulama ve Kabul Kriterleri (Checklist)

- [ ] Web INP skoru 200 ms altında; uzun döngüler `scheduler.yield()` ile parçalanmış.
- [ ] React 19 Compiler aktif projelerde manuel `useMemo`/`useCallback` kullanılmıyor; render saflığı korunuyor.
- [ ] LCP görselinde `fetchpriority="high"` aktif; `loading="lazy"` kaldırılmış.
- [ ] Tüm görsellerde CLS'i sıfırlamak için CSS `aspect-ratio` tanımlı.
- [ ] React Native listelerinde `FlatList` kesinlikle yok; `@shopify/flash-list v2` kullanılıyor.
- [ ] Android 15 için `edgeToEdgeEnabled: true` ve `useSafeAreaInsets()` aktif.
- [ ] Form ve chat ekranlarında `react-native-keyboard-controller` kullanılıyor.
- [ ] Dokunma hedefleri asgari $44\times44\text{ pt}$ ($hitSlop$ dahil) ve `expo-haptics` ile destekleniyor.
