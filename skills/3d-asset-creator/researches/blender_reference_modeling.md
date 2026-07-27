# Blender Görsel Referanstan Model Üretimi ve AI Workflow

Bu araştırma dökümanı, kullanıcının paylaştığı ekran görüntülerindeki (örneğin mavi kaslı spor araba, beyaz kamyon, demiryolu, köprü, bariyer vb.) objeleri **referans alarak Blender'da profesyonelce nasıl modelleyeceğimizi**, **AI araçlarını nasıl entegre edeceğimizi** ve **elimizdeki Blender MCP araçlarını** nasıl kullanabileceğimizi açıklar.

---

## 1. Blender MCP ve Yapay Zeka Entegrasyonu

Şu anki geliştirme ortamımızda **Blender MCP** sunucusu yüklüdür. Bu sunucu aracılığıyla doğrudan yapay zeka modelleri ve Sketchfab entegrasyonu ile 3D model üretebilir ve sahneye aktarabiliriz:

### A. Sketchfab Entegrasyonu (Hazır Modelleri Çekme)
Elimizdeki `blender` MCP sunucusu üzerinden şu araçları kullanarak referans görsele en yakın modelleri aratabilir ve Blender sahnemize otomatik olarak indirebiliriz:
*   `search_sketchfab_models(query="low poly muscle car")`
*   `get_sketchfab_model_preview(model_id)`
*   `download_sketchfab_model(model_id)`

### B. Hyper3D ve Hunyuan3D Entegrasyonu (Yapay Zeka ile Görselden Model Üretimi)
Referans görselini (örneğin tır veya bariyer görüntüsünü) doğrudan 3D modele dönüştürmek için Blender MCP sunucumuzdaki şu araçları kullanabiliriz:
*   `generate_hyper3d_model_via_images(image_paths)`: Referans aldığımız araç görsellerini vererek Hyper3D Rodin modeli oluştururuz.
*   `generate_hunyuan3d_model(prompt="low poly blue muscle car with white stripes")`: Metin veya görsel girdisiyle Hunyuan3D modeli üretiriz.
*   `import_generated_asset_hunyuan(...)`: Üretilen modeli doğrudan Blender içine aktarırız.

---

## 2. Görsel Referanstan Manuel Low-Poly Modelleme Adımları

Yapay zekanın ürettiği modelleri temizlemek veya sıfırdan referans görsele bakarak Blender'da modelleme yapmak için takip edilecek profesyonel iş akışı:

### Adım 1: Referans Görseli Blender'a Ekleme
1.  Blender'da `Numpad 1` (Ön), `Numpad 3` (Yan) veya `Numpad 7` (Üst) görünümüne geçin.
2.  `Shift + A` > `Image` > `Reference` yolunu izleyerek referans ekran görüntüsünü sahneye aktarın.
3.  Görselin opaklığını (Opacity) `0.3 - 0.5` arasına düşürün ve kazara seçilmemesi için yan menüden seçilebilirlik filtresini (`Selectable`) kapatın.

### Adım 2: Temel Geometriyi Bloklama (Blocking)
1.  Bir `Cube` (Küp) veya `Cylinder` (Silindir) oluşturarak aracın veya köprünün ana kütlesini oluşturun.
2.  `Edit Mode` (`Tab`) içinde `Loop Cut` (`Ctrl + R`) atarak objeyi referanstaki eğimlere göre şekillendirin.
3.  **Ayna (Mirror) Modifikatörü:** Arabalar simetrik olduğundan, objenin yarısını silip `Mirror` modifikatörü uygulayarak sadece tek tarafı modelleyin. Bu, iş yükünü yarıya indirir ve simetriyi garanti eder.

### Adım 3: Low-Poly Detayları ve Keskin Köşeler
1.  Low-poly stilinde pah kırma (`Bevel` - `Ctrl + B`) işlemlerini çok az veya hiç uygulamayın. Köşelerin keskin ve sert görünmesini sağlayın.
2.  Objeyi seçip Object Mode'da sağ tıklayın ve **`Shade Flat`** seçeneğini seçin. Bu, pürüzsüzleştirme (smoothing) algoritmasını kapatarak yüzeylerin (polygon/face) tek tek görünmesini sağlar ve klasik low-poly stilini oluşturur.

---

## 3. AI ile Üretilen Modelleri "Game-Ready" Hale Getirme (Optimization)

Yapay zeka (Hunyuan3D veya Hyper3D) ile üretilen modeller genellikle çok yüksek poligonludur ve dağınık bir ağ (topology) yapısına sahiptir. Bu modelleri Unity'de çalışacak seviyeye getirmek için Blender optimizasyon adımları:

1.  **Decimate Modifikatörü (Hızlı Poligon Düşürme):**
    *   AI modelini seçin.
    *   `Modifiers` panelinden **`Decimate`** modifikatörünü ekleyin.
    *   `Ratio` değerini `0.1` ile `0.3` arasına çekerek poligon sayısını agresif bir şekilde azaltın. Bu işlem, modeli otomatik olarak low-poly geometrisine dönüştürür.
2.  **Remesh (Yeniden Yapılandırma):**
    *   Eğer modelin yüzeylerinde delikler veya karmaşık üçgenler varsa, `Remesh` modifikatörünü (veya `Voxel Remesher`) kullanarak objeyi temiz, eşit boyutlu dörtgenlere (quads) dönüştürün, ardından Decimate uygulayın.
3.  **Material & Color Atlas Eşleme:**
    *   AI modelinin karmaşık kaplamasını silin.
    *   Tüm model için tek bir stilize renk paleti materyali tanımlayın.
    *   Modelin UV haritasını (`Edit Mode` > `U` > `Smart UV Project`) açarak renk paletindeki düz renk kutucuklarına hizalayın.
