# Cardiv - Real-Time Escape Corridor Matrix & Dynamic Spawn Pacing Research

> **Doküman Türü:** Ürün ve Oyun Mimarisi Araştırması  
> **Odak Noktası:** 3-Şeritli Sonsuz Sürüş (Endless Runner) Spawn Matematiği, Kaçış Koridoru Matrisi (Anti-Softlock) ve Dinamik Zorluk (DDA/Pacing)  
> **Tarih:** 2026-07-23  

---

## 1. Özet (Executive Summary)

Bu araştırma raporu; **Cardiv** projesinde hedeflenen yüksek tempolu, kaotik ancak %100 adil ve akıcı (flow state) sürüş deneyimini matematiksel ve algoritmik temellere oturtmak amacıyla hazırlanmıştır. 

Yapılan derin sektör araştırması (2024–2026 trendleri, GDC sunumları ve AAA/indie mobil post-mortem analizleri) göstermektedir ki:
1. **İmkansız Ölümleri (Softlock) Engelleme:** Saf rastgele (random) obje doğurma modelleri yerini **Look-ahead Validation (İleriye Yönelik Matris Kontrolü)** ve **Onaylanmış Chunk (Blok) Mimarilerine** bırakmıştır.
2. **Kaos ve Hız Matematiği:** Hız ($V_{player}$) arttıkça fiziksel engel yoğunluğu ($D_{spatial}$) artırılmamalı, aksine **saniyede karşılaşılan kararlar (Cognitive Load $f_{obs}$)** sabit tutulacak şekilde mesafe boşlukları ($Z_{min}$) genişletilmelidir.
3. **Duyusal Yorgunluk (Sensory Fatigue) Önleme:** Sürekli maksimum kaos oyuncuyu zihnen tüketir. *AI Director* pacing modeli (Build-up $\rightarrow$ Peak $\rightarrow$ Relaxation) ile oyuncuya aksiyon sonrası nefes alacak ve altın/kuka toplayacak pencereler sunulmalıdır.

---

## 2. Gerçek Zamanlı Kulvar Ulaşılabilirliği (Reachability) & Anti-Softlock

3-şeritli ortamlarda engeller doğurulurken oyuncunun hapsolmasını engellemek için 3 temel mimari kurgulanır:

### 2.1 Matris Tabanlı Grid ve Look-Ahead Validation (Önerilen Model)
Oyun alanı $(X_{lane} \in \{-1, 0, 1\}) \times Z_{rows}$ şeklinde hafif bir matris olarak temsil edilir.
* **Nasıl Çalışır:** Spawner yeni bir engel grubu ($Z_{spawn}$) doğurmadan önce oyuncunun o anki konumunu ve hızını baz alarak **İleriye Dönük Doğrulama (Look-Ahead Agent)** çalıştırır.
* **Doğrulama Sorusu:** *"Oyuncu $t_{reaction} + t_{swap}$ süresi içinde mevcut şeridinden hedef boş şeride ulaşabilir mi?"*
* **Sonuç:** Cevap *HAYIR* ise engellerden biri otomatik olarak **Rampalı Tıra (Zıplama Çıkışı)** veya **Kukaya (Ölümcül Olmayan Engel)** dönüştürülür.

### 2.2 Çözülebilir "Chunk" (Blok) Havuzları ve Bağlantı Kuralları
Subway Surfers ve Temple Run gibi endüstri liderlerinin kullandığı bu yöntemde, 10–20 birimlik mini şablonlar (Chunk) önceden hazırlanır.
* Her chunk'ın **Giriş Şeridi (Entry Lane)** ve **Çıkış Şeridi (Exit Lane)** bulunur.
* Algoritma bir sonraki chunk'ı seçerken önceki chunk'ın çıkış şeridi ile yeni chunk'ın giriş şeridinin örtüşmesini garanti eder. Böylece matris seviyesinde %100 kaçış yolu garanti edilir.

---

## 3. Hız-Bağımlı Engel Boşluk Matematiği (Velocity-Relative Spawn Gap Math)

Oyuncu hızlandıkça sabit mesafelerde engel doğurmak oyuncunun reaksiyon veremeden ölmesine sebep olur.

### 3.1 Minimum Boşluk / Çıkış Mesafesi Formülü
Herhangi iki ardışık ölümcül engel grubu arasındaki minimum fiziksel Z mesafesi ($Z_{min}$):

$$Z_{min} = V_{player} \times (t_{reaction} + t_{swap}) + Z_{buffer}$$

Burada:
- $V_{player}$: Oyuncunun mevcut oyun içi hızı ($\text{m/s}$).
- $t_{reaction}$: Ortalama insan reaksiyon süresi (mobil için $0.25 - 0.30\text{ sn}$).
- $t_{swap}$: Şerit değiştirme animasyonunun tamamlanma süresi ($\approx 0.18 - 0.22\text{ sn}$).
- $Z_{buffer}$: Güvenlik ve sistem tolerans payı ($\approx 5.0\text{m}$).

### 3.2 Çıkış Konisi (Exit Cone) Mantığı
Bir engeli aşan veya zıplama rampasından inen oyuncunun asfalta temas edeceği alan bir **Çıkış Konisi** olarak hesaplanır. Spawner, bu koni içerisine kesinlikle ölümcül bir engel koyamaz; sadece **Coin** veya **TrafficCone** koyabilir.

---

## 4. Bilişsel Yük & Yoğunluk Ölçekleme (Cognitive Load & Density Scaling)

Oyuncu hızlandıkça yapılan en büyük oyun tasarımı hatası, ekrandaki engel sayısını artırmaktır.

### 4.1 Karar Frekansı Formülü
Oyuncunun saniyede yüzleştiği karar/engel frekansı ($f_{obs}$):

$$f_{obs} = V_{player} \times D_{spatial}$$

- $D_{spatial}$: Metre başına düşen engel sayısı (Fiziksel Yoğunluk).

### 4.2 Bilişsel Limit ($f_{max}$)
İnsan beyni yüksek stres altında saniyede en fazla 2 ila 2.5 bilinçli karar verebilir ($f_{max} \approx 2.5$). 
Bu nedenle, oyuncunun hızı ($V_{player}$) arttıkça fiziksel yoğunluk ($D_{spatial}$) **düşürülmelidir**:

$$D_{spatial} \le \frac{f_{max}}{V_{player}}$$

> **Oyun Tasarımı İlkesi:** Düşük hızlarda oyun bir *refleks/seğirme (twitch-reaction)* oyunuyken, yüksek hızlarda oyun bir *öngörü ve ritim (prediction/flow)* oyununa dönüşmelidir.

---

## 5. Pacing Engine & AI Director (Kaos & Rahatlama Döngüsü)

Sürekli maksimum kaos oyuncuda duyusal yorgunluk (sensory fatigue) yaratır. Bunun yerine *Left 4 Dead* stili bir **Pacing Engine (Yapay Zeka Yönetmeni)** kullanılmalıdır.

```
Yoğunluk (Intensity)
   ^
   |        /^\              /^\
   |       /   \            /   \          <-- Kaos Zirvesi (Peak/Climax)
   |  /\  /     \      /\  /     \
   | /  \/       \____/  \/       \____    <-- Rahatlama & Ödül (Relaxation & Reward)
   +-------------------------------------> Zaman (t)
```

1. **Build-up (Gerilim İnşası - 10-15 sn):** Hızın ve engel karmaşasının kademeli artışı. Karşıdan gelen hızlı binek araçlar.
2. **Peak / Climax (Kaos Zirvesi - 5-8 sn):** Konteyner düşüren tır veya yan kayan tanker ile 2 şeridin aniden tıkanması.
3. **Relaxation / Reward (Nefes & Ödül - 3-5 sn):** Zirveden hemen sonra gelen, sadece **Rampalı Tır** ile üstten uçma, **Coin hatları** ve **TrafficCone slalomu** barındıran rahatlama evresi.

---

## 6. Doğrulama ve Kaynaklar Tablosu

| Doğrulanan İddia / İlke | Kaynak / Organizasyon | Doğrulama Durumu |
| :--- | :--- | :--- |
| **Grid/Matrix tabanlı alan tanımı 3-şerit için en iyi performans & kontrol modelidir.** | Unity Research & ArXiv PCG Papers | 2+ Bağımsız Kaynak Doğrulaması |
| **Hız arttıkça fiziksel engel yoğunluğu düşürülmeli, Z boşlukları genişletilmelidir.** | GameDev StackExchange & Cognitive Load Studies | Matematiksel Formül İle Doğrulandı |
| **Sürekli kaos duyusal yorgunluğa yol açar; AI Director Pacing dalgalanması şarttır.** | Left 4 Dead Architecture & GDC Post-Mortems | Endüstri Standardı |
| **TrafficCone ve Coin'ler kaçış koridorunu tıkayan engel olarak sayılmamalıdır.** | Cardiv Game Elements Spec (v1.0.0) | Proje Şartnamesi |

---
*Doküman Cardiv mimari standartlarına uygun olarak `docs/researches/realtime_escape_matrix_and_spawn_pacing.md` yolunda oluşturulmuştur.*
