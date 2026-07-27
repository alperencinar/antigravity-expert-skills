# Low-Poly Görsel Estetik ve Unity URP Grafik Rehberi

Bu araştırma dökümanı, Cardiv mobil oyununun görselliğini amatör görünümden kurtarıp referans görsellerdeki gibi **profesyonel, premium ve atmosferik** bir seviyeye taşımak için gerekli olan grafik, ışıklandırma ve rendering tekniklerini içermektedir.

---

## 1. Referans Görsellerin Estetik Analizi

Kullanıcı tarafından paylaşılan ekran görüntülerinde yakalanan atmosfer, rastgele bir low-poly tasarımın ötesinde, belirli sanatsal kurallara dayanmaktadır:

*   **Renk Paleti (Color Palette):** Sahnede baskın olan renkler, gün batımı/şafak vaktini andıran sıcak tonlar (turuncu, sarı, şeftali rengi) ile zıt soğuk tonların (mavi, lacivert) birleşimidir. Renkler çiğ (doygun kırmızı, yeşil gibi) değildir, pastel ve uyumludur.
*   **Gökyüzü Gradyanı (Atmospheric Gradient):** Gökyüzü tek bir renk yerine yukarıdan aşağıya lacivertten sarıya/turuncuya uzanan bir gradyana sahiptir.
*   **Işık ve Gölgeler (Lighting & Shadows):** Sahneyi aydınlatan ana yönsel ışık (Directional Light), yatay bir açıyla (50-60 derece) gelerek arabaların ve engellerin arkasına doğru uzun, yumuşak gölgeler düşürür. Işık rengi sıcak sarı/turuncudur.
*   **Derinlik ve Sis (Fog):** Ufuk çizgisine doğru gidildikçe yoğunlaşan ve gökyüzü rengiyle bütünleşen bir atmosfer sisi (Atmosphere Fog) derinlik algısını artırmaktadır.
*   **Parıltı Efekti (Bloom / Glow):** Arabaların farları, kalkan (shield) efekti ve gökyüzündeki küçük yıldız parçacıkları hafifçe parlamaktadır (Bloom).
*   **Kartoon Outlines / Toon Shading:** Objelerin kenarlarında çok ince, stilize siyah çizgiler (Outlines) veya gölgelerin keskin geçişli olmasını sağlayan Toon Shader kullanımı mevcuttur.

---

## 2. Unity URP'de Görsel Kaliteyi Artırma Adımları

Geliştirdiğimiz oyunda bu görünümü yakalamak için uygulamanız gereken teknik adımlar:

### A. Ambient Light (Ortam Işığı) & Gökyüzü Ayarları
1.  **URP Skybox:** Hazır gradyan üreten bir gökyüzü materyali (Skybox) veya URP için ücretsiz olan *Procedural Sky* kullanılmalıdır.
2.  **Ambient Mode:** `Lighting` panelinde `Ambient Source` olarak `Gradient` seçilmelidir:
    *   **Sky Color (Gök):** Koyu Lacivert / Mavi
    *   **Equator Color (Ufuk):** Sıcak Turuncu / Sarı
    *   **Ground Color (Yer):** Gri / Kahverengi

### B. Post-Processing Volume Ayarları
Post-processing, low-poly sahneleri birleştiren en önemli unsurdur. Sahnede bir `Volume` oluşturup aşağıdaki override'ları eklemelisiniz:
*   **Color Adjustments / Tonemapping:** Tonemapping modunu **ACES** yapın. Bu, renklere sinematik bir kontrast ve doygunluk kazandırır.
*   **Bloom:** `Intensity` değerini `0.5 - 1.2` arasına ayarlayın. Parlama eşiğini (`Threshold`) `0.9` civarında tutun, böylece sadece farlar ve parlayan efektler parlar.
*   **SSAO (Screen Space Ambient Occlusion):** URP Renderer özelliklerine SSAO ekleyin. Bu, low-poly köşelerin ve arabanın tekerlek altlarının birleştiği yerlerde hafif gölgeler oluşturarak derinlik katar.
*   **Vignette:** Ekranın köşelerini hafifçe karartarak odağı merkezdeki araca çeker.

### C. Sis (Fog) Ayarları
*   `RenderSettings.fog` özelliğini açın.
*   Sis rengini gökyüzü ufuk çizgisi rengiyle (sıcak turuncu/sarı) eşleyin.
*   Sis modunu `Exponential` veya `Linear` yaparak araba ilerledikçe ufkun yumuşakça silinmesini sağlayın.

---

## 3. Shaders (Materyal ve Gölgelendiriciler)

Stilize görünümü tamamlamak için standart URP Lit shader yerine şu gölgelendiriciler tercih edilmelidir:
1.  **Simple Lit:** Mobil cihazlarda performans dostudur ve düz stilize renklendirmeyi en iyi yansıtan modeldir.
2.  **Toon / Cel Shader:** Işığın objeler üzerindeki geçişini keskinleştirerek çizgi roman/anime tarzı gölgelendirme sağlar. (Shader Graph ile kolayca yapılabilir).
3.  **Outline Shader:** Objelerin kenarlarını çizmek için Renderer Feature olarak eklenen *Sobel Outline* veya çift geçişli (double pass) vertex extrusion shader'ı kullanılmalıdır.

---

## 4. Efektler ve Parçacık Sistemleri (VFX)

Referans görsellerdeki premium hissi veren efektler:
*   **Shield (Kalkan) Efekti:** Yarım şeffaf mavi küre materyali üzerine, Shader Graph ile kayan bir grid (ızgara) veya chevron deseni eklenerek yapılır. `Emission` değeri yüksek tutularak Bloom ile parlaması sağlanır.
*   **Trail Renderer:** Tekerleklerin arkasında kalan lastik izleri veya rüzgar çizgileri için şerit efektleri.
*   **Speed Sparks:** Araba hızlandığında ekrana doğru uçuşan küçük sarı yıldız/kıvılcım parçacıkları (Particle System).
