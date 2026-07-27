# Mobil Oyunlar için Low-Poly Grafik Stratejileri ve Görsel Cila (Visual Polish)

Mobil cihazlarda yüksek performans sağlarken profesyonel bir görünüm elde etmek için "gerçek zamanlı hesaplamalardan kaçınmak ve her şeyi fırınlamak (bake)" endüstri standardıdır. Amatör görünümlü oyunlar ile profesyonel oyunlar arasındaki temel fark, ışıklandırma ve gölge tekniklerinin optimizasyonudur.

## 1. Temel Strateji: "Her Şeyi Fırınla" (Bake Everything)
Mobil cihazlarda gerçek zamanlı ışıklar (real-time lights) ve gölgeler çok masraflıdır ve batarya ömrünü hızla tüketir.
*   **Fırınlanmış Işıklandırma (Baked Lighting):** Işık ve gölgeleri önceden hesaplayıp "lightmap" (ışık haritası) olarak kaydetmek için Unity'nin lightmapper aracını kullanın. Bu, çalışma zamanında (runtime) neredeyse sıfır maliyetle karmaşık, yumuşak ve detaylı ışıklandırmaya sahip olmanızı sağlar.
*   **Işık Modları:** Sabit nesnelerin Unity'de **Static** olarak ayarlandığından emin olun, böylece fırınlanmış ışık haritalarına dahil edilebilirler. **Mixed** (Karışık) ışıklandırmayı yalnızca kesinlikle gerekli olduğunda kullanın.
*   **Universal Render Pipeline (URP):** Mobil projeler için her zaman URP kullanın. Mobil GPU'lar için optimize edilmiştir ve ışıklandırmayı verimli bir şekilde yönetmek için gerekli araçları sağlar.

## 2. Çevresel Perdeleme (Ambient Occlusion - AO) En İyi Uygulamaları
AO, düşük poligonlu (low-poly) modellere derinlik katar; aksi takdirde bu modeller düz (flat) ve amatör görünür.
*   **Dokulara Fırınlamak (Bake into Textures):** Mobilde çok ağır olan gerçek zamanlı Ekran Uzayı Çevresel Perdeleme (SSAO) kullanmak yerine, AO'yu doğrudan Blender veya Substance Painter gibi yazılımlarda diffuse/albedo dokularınıza (textures) fırınlayın.
*   **Multiply Blend:** Dokularınızı boyarken, fırınlanmış AO'nuzu temel renklerinizin üzerinde "Multiply" olarak ayarlanmış bir katmana yerleştirin. Bu, yarıklardaki gölgelerin yoğunluğu üzerinde manuel kontrol sağlar.
*   **Unity'de Fırınlanmış AO:** Çevresel ışık haritalarınıza küresel temas gölgeleri (contact shadows) eklemek için Unity'nin Işıklandırma (Lighting) ayarlarında "Baked Ambient Occlusion"u da etkinleştirebilirsiniz.

## 3. Işıklandırma ve Gölge Hileleri (Cheats)
Her şeyi fırınlayamadığınızda (örneğin, dinamik karakterler veya hareket eden nesneler için), şu teknikleri kullanın:
*   **Sahte Gölgeler (Fake Shadows):** Karakterler gibi dinamik nesneler için, gerçek zamanlı gölge dökümü (shadow casting) yerine altlarındaki zemine yansıtılan basit bir "blob" gölge (karanlık, yarı saydam bir daire çıkartması/decal) kullanın.
*   **Köşe Işıklandırması (Vertex Lighting):** Dinamik ışıklara ihtiyacınız varsa, piksel tabanlı ışıklandırmadan çok daha ucuz olan vertex lighting (köşe ışıklandırması) kullanan gölgelendiricileri (shaders) değerlendirin.
*   **Işık Probları (Light Probes):** Dinamik nesnelerin (oyuncunuz gibi) fırınlanmış ışık haritalarınızdan ışık bilgisi almasını sağlamak için Light Probes kullanın. Bu, gerçek zamanlı gölgelerin maliyeti olmadan hareketli nesnelerin sahneye aitmiş gibi hissettirmesini sağlar.
*   **Gradyan Dokular (Gradient Textures):** "Stilize" bir low-poly görünümü için birçok geliştirici, ışık motorlarına olan ihtiyacı tamamen atlayarak bir model boyunca aydınlıktan karanlığa geçişleri simüle etmek için gradyanları doğrudan dokularına boyar.

## 4. Optimizasyon Kontrol Listesi
*   **Gerçek Zamanlı Işıkları Sınırla:** Piksel başına ışık sayısını (per-pixel lights) mutlak minimumda tutun.
*   **Gölge Kalitesi:** Gerçek zamanlı gölgeler kullanmanız gerekiyorsa, gölge çözünürlüğünü düşük tutun, yumuşak gölgeler yerine sert (hard) gölgeler kullanın ve "Gölge Mesafesini" (Shadow Distance) sınırlandırın, böylece gölgeler uzaktaki nesneler için oluşturulmaz.
*   **Post-Processing'den Kaçının:** Üst düzey post-processing (Bloom, SSAO, Alan Derinliği) standart mobil cihazlar için çok ağırdır. Bunları idareli kullanın veya "sahte" versiyonlar oluşturun (örneğin, ışıklar için basit bir bloom sprite'ı).
*   **Shader Graph:** Belirli bir low-poly "görünüm" (stilize vurgular gibi) için, Unity'nin standart PBR shader'larının yükü olmadan sahne ayarlarınıza tepki veren özel, unlit (ışıksız) veya basit lit (ışıklı) shader'lar oluşturmak üzere Shader Graph kullanın.

### Kaynaklar ve Alıntılar:
- Unity URP ve Performans Optimizasyonları: [Unity URP Documentation](https://unity.com/srp/universal-render-pipeline)
- Low Poly Modelleme ve Fırınlama Teknikleri: [Vertex AI Grounding Search Results] (Web Araması Derlemeleri)
- Çevresel Perdeleme ve Doku Hileleri Uygulamaları: Bağımsız Geliştirici Forumları ve Unity Optimizasyon Rehberleri.
