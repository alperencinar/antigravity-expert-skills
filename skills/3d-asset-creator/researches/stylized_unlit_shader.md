# Özel Stilize Edilmiş Düşük Poligonlu (Low-Poly) Unlit Shader (Vertex Color AO + Gradient Ramp)

Premium hissiyatlı, "hand-painted" veya stilize (örneğin Zelda: Breath of the Wild, Genshin Impact tarzı) oyun görselliği elde etmek için modern mobil projelerde sıklıkla özel Unlit (Işıksız) shaderlar kullanılır. Bu yaklaşım, sıfır gerçek zamanlı ışıklandırma hesaplaması (Zero Real-Time Lighting Calculations) ile maksimum performansı hedefler.

## Sistem Bileşenleri

Bu tarz bir shader üç temel estetik bileşene dayanır:

1. **Unlit Temel (Performans):** Unity'nin yerleşik ışık, gölge ve yansıma (PBR) hesaplamaları tamamen atlanır. Malzeme ışığa tepki vermez, performansı maksimum seviyeye çıkarır.
2. **Vertex Color Ambient Occlusion (Derinlik):** `vertex_color_ao.md` belgesinde detaylandırıldığı üzere, objenin kuytu köşeleri, Blender gibi bir programda önceden hesaplanıp Vertex renklerine gömülmüştür. Bu bize statik ama çok organik bir gölge hissiyatı verir.
3. **Gradient Ramp (Stilize Renklendirme):** Modele düz bir renk veya texture vermek yerine, Y ekseni (yükseklik) baz alınarak veya sahte bir ışık açısına (Fake Light Direction) göre renklendirilmiş bir gradyan (renk geçişi) uygulanır.

## Unity URP Shader Graph İçerisinde Kurgulama

Bu efektleri bir araya getirmek Shader Graph ile son derece pratiktir.

### 1. Vertex Rengi ve AO Okuma
*   **Vertex Color Node:** Bu node grafiğe eklenir. Objenin mesh verisinden gelen R, G, B veya Grayscale AO değerini temsil eder.

### 2. Yükseklik Tabanlı Gradient Ramp (Height Gradient)
Çevre objeleri (ağaçlar, dağlar, kayalar) için objenin altından üstüne doğru bir renk geçişi (örneğin kayanın altında koyu mavi, üstünde açık gri) çok hoş bir stilize etki yaratır.
*   **Position Node:** `Object Space` olarak ayarlanır.
*   **Split Node:** Y eksenini (Green kanalı) izole edilir.
*   **Remap Node:** Objenin alt ve üst sınırlarını (örneğin -1 ile 1 arası), 0 ile 1 aralığına sıkıştırır (Normalize eder).
*   **Sample Gradient Node:** Remap edilmiş Y değeri, Gradient'in "Time" girişine bağlanır. Bu node'un içerisine Inspector üzerinden ayarlanabilen bir Gradient özelliği (Property) atanır.

### 3. Işık Yönlü Gradient (Toon/Ramp Shading - Opsiyonel)
Karakterler veya dinamik hissiyat istenen objeler için sahte bir ışık yönü simüle edilebilir.
*   **Normal Vector Node (World Space)** ile **Vector3 (Fake Light Direction)** arasında bir **Dot Product** alınır.
*   Sonuç (genelde -1 ile 1 arasındadır) 0-1 aralığına re-map edilir ve **Sample Gradient** node'una bağlanır. Böylece ışığın vurduğu yerler Gradient'in sağ tarafındaki renkleri, arkada kalan yerler sol tarafındaki renkleri alır.

### 4. Düğümleri Birleştirme (Compositing)
Nihai görseli elde etmek için bu bileşenler matematiksel olarak birleştirilir:

`Nihai Renk = (Gradient Ramp Çıktısı) * (Vertex Color AO Çıktısı) * (Base Texture / Albedo Rengi)`

Tüm bu işlemler bir dizi **Multiply** node'u ile birbirine çarpılarak elde edilir.
*   **AO Katkısı:** AO değeri siyah(0) ile beyaz(1) arasında olduğu için, renkle çarpıldığında beyaz yerler olduğu gibi kalır, siyah yerler rengi koyulaştırır. Eğer AO çok koyu ise bir Lerp node'u ile etkisi yumuşatılabilir.
*   **Çıktı:** En son elde edilen RGB değeri Master Node'un **Base Color** girişine bağlanır.

## Görsel Kaliteyi Zirveye Taşımak: Post-Processing

Sadece shader ile bitmez, oyunun premium gözükmesini sağlayan anahtarlar Post-Processing katmanında gizlidir:
*   **Soft Color Grading (Renk Paleti):** Pastel tonları ve kontrast ayarları. Tonlama (Tonemapping) olarak "ACES" kullanımı.
*   **Slight Bloom:** Parlak alanların hafifçe taşıp parlaması, büyülü bir atmosfer katar.
*   **Depth of Field (DoF):** Odak dışındaki nesnelerin hafif bulanıklaşması, sahneye minyatür/tilt-shift veya sinematik bir kalite katar.

## Kaynaklar
- [Stylized Shading in Unity URP](https://learn.unity.com/)
- [Shader Graph Gradient Node Documentation](https://docs.unity3d.com/Packages/com.unity.shadergraph@12.1/manual/Sample-Gradient-Node.html)
- [Minimizing Draw Calls and Real-time Lighting in Mobile Games](https://developer.arm.com/solutions/graphics-and-gaming)
