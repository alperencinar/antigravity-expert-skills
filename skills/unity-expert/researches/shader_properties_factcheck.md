# Shader Özellikleri ve Parabolik Deplasman Doğrulama Raporu (Fact-Check)

## 1. Unity URP SRP Batcher Uyumluluğu ve Global Değişkenler

**Soru:** `_Curvature` veya `_CurvatureX` gibi global bir shader değişkeni shader'ın `Properties` bloğu içinde tanımlanmışsa, `Shader.SetGlobalFloat` çağırmak işe yarar mı, yoksa materyal özellikleri tarafından ezilir mi? URP shader'larında global değişkenleri yönetmenin doğru yolu nedir?

**Doğrulama (Fact-Check):**
- Eğer bir değişken `Properties` bloğunda tanımlanırsa ve SRP Batcher uyumluluğu için `CBUFFER_START(UnityPerMaterial)` bloğu içerisine dahil edilirse, bu değişken **per-material (materyale özel)** bir özelliğe dönüşür.
- Bu durumda, `Shader.SetGlobalFloat` ile atama yapsanız bile, materyalin kendi içerisinde Inspector üzerinden atanan veya varsayılan olarak saklanan değeri global değeri **ezecektir (override edecektir)**.
- **Doğru Kullanım:** Hem `Shader.SetGlobalFloat` metodunun çalışmasını sağlamak hem de **SRP Batcher** uyumluluğunu bozmamak için, global olarak kontrol edilecek değişkenleri (örneğin dünya eğriliği) shader'ın `Properties` bloğuna **EKLEMEYİN** ve `UnityPerMaterial` CBUFFER'ının **DIŞINDA** tanımlayın. Bu değişkenleri global alanda veya ayrı bir isimle oluşturulmuş farklı bir `CBUFFER` içerisinde (örneğin `CBUFFER_START(GlobalDeformation)`) tanımlamanız en sağlıklı yöntemdir.

## 2. Parabolik Vertex Deplasmanı ve View-Space Z-Ekseni İşaretleri

**Soru:** View-space Z-mesafesine bağlı deplasman (Z'nin karesine dayalı Y ofseti) hesaplamaları nasıl çalışır? Unity'nin view space (kamera uzayı) Z koordinatı kameranın önü için negatif bir değere mi sahiptir ve bu durum deplasmanın işaretini nasıl etkiler?

**Doğrulama (Fact-Check):**
- Unity'de World Space "Left-Handed" (sol elli) olmasına rağmen, **View Space (Kamera Uzayı) genellikle "Right-Handed" (sağ elli) olarak işlenir.** Bu sebeple kameralar standart olarak **negatif Z ekseni** yönüne doğru bakar.
- Sonuç olarak, kameranın önünde (görülebilir alanda) bulunan tüm objelerin View Space'teki `Z` koordinatları (derinlik) **negatif** bir değere sahiptir (örneğin `viewPos.z = -25.0`).
- Parabolik eğim (dünya bükülme) hesaplamalarında genellikle Z mesafesinin karesi ($z^2$) kullanılır.
- **Formüle Etkisi:** Matematiksel olarak bir sayının karesi alındığında (`viewPos.z * viewPos.z`), başlangıçtaki negatif işaret doğal olarak pozitife dönüşür. Bu nedenle Z karesi bazlı bir bükülme formülü sorunsuz çalışır. Fakat aşağıya doğru (yerçekimi yönünde) bir kıvrılma elde etmek isterseniz, Z karesinden çıkan pozitif değeri eksi bir katsayı ile çarparak Y ofsetini negatif yapmalısınız:
  `float yOffset = -curvature * (viewPos.z * viewPos.z);`
- Ek not: Eğer parabolik (karesel) yerine doğrusal (linear) bir işlem yapacaksanız, derinliği pozitif bir değer olarak alabilmek için Z'nin ters işaretini kullanmanız (`-viewPos.z`) veya mutlak değer fonksiyonundan (`abs()`) faydalanmanız gerekir.
