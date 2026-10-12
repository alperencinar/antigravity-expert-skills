# Blender'da Vertex Renklerine Ambient Occlusion (AO) Pişirme ve Unity URP'de Kullanımı

Oyun grafik araştırmalarımız doğrultusunda, özellikle mobil ve düşük poligonlu (low-poly) oyunlarda performansı artırmak ve kaliteli gölgelendirme elde etmek için Ambient Occlusion (AO) bilgisini kaplamalar (texture) yerine doğrudan Vertex Renklerine (Vertex Colors) pişirme (baking) yöntemi incelenmiştir.

## Neden Vertex Color AO? (Texture Tabanlı AO ile Karşılaştırma)

**Avantajları:**
1. **Hafıza (Memory) Tasarrufu:** Texture tabanlı AO, ekstra bir veya birkaç doku dosyası (örn. 1024x1024 boyutlarında) gerektirir. Vertex rengi ise her köşe için fazladan sadece birkaç byte (RGB) veri tutar. Bu, mobil cihazlarda bellek bant genişliğini ve depolama alanını önemli ölçüde korur.
2. **Performans:** Doku okuma (texture sampling) işlemi GPU için maliyetlidir. Vertex renkleri doğrudan vertex shader üzerinden okunup fragment shader'a aktarıldığı için (interpolasyon ile) render süresini ciddi şekilde düşürür.
3. **UV Açılımı (Unwrapping) Gerektirmez:** Karmaşık UV haritalarına ihtiyaç duymadan doğrudan geometrinin köşeleri üzerinden hesaplama yapılabilir.

**Dezavantajları (Texture AO'ya Kıyasla):**
1. **Geometriye Bağımlılık:** Kalite doğrudan mesh'in vertex yoğunluğuna bağlıdır. Çok düşük poligonlu geniş yüzeylerde AO geçişleri bloklu (blocky) görünebilir. Vertex yoğunluğunun gölgelerin yoğun olduğu köşe bölgelerinde artırılması gerekebilir.
2. **Yüksek Detay Eksikliği:** İnce çatlaklar veya çok küçük detaylar için kaplama tabanlı AO hala en iyi çözümdür.

## Blender'da AO'yu Vertex Renklerine Pişirme

Blender'ın güncel (3.x / 4.x) sürümlerinde doğrudan vertex rengine AO pişirmek için eklentiler (add-ons) kullanmak en verimli yoldur.

**Adımlar:**
1. Objeyi seçin ve **Object Data Properties > Color Attributes** altından yeni bir Color Attribute (Vertex Color katmanı) oluşturun.
2. Yerleşik Render ayarlarından (Cycles) *Bake Type* olarak *Ambient Occlusion* seçilip *Bake Target* *Vertex Colors* olarak ayarlanabilir, ancak bu her zaman tutarlı sonuç vermeyebilir.
3. **Önerilen Eklentiler:** [Vertex Oven (GitHub)](https://github.com/the-m-w/vertex-oven) veya Gumroad üzerindeki çeşitli ücretsiz Bake to Vertex Color eklentileri kullanarak doğrudan AO verisini seçili objenin Vertex Color katmanına yazdırabilirsiniz.
4. Modeli **FBX** veya **glTF** formatında, vertex color verilerini dahil edecek şekilde dışa aktarın (export).

## Unity URP'de Vertex Color AO Okuma (Shader Graph)

1. FBX modelini Unity'e aktarın. Modelin Import ayarlarında `Import Vertex Colors` seçeneğinin aktif olduğundan emin olun.
2. Yeni bir **URP Unlit** veya **Lit Shader Graph** oluşturun.
3. Graph içerisine bir **Vertex Color** node'u ekleyin. Bu node modelin köşe renklerini okur.
4. AO genelde gri tonlamalıdır. Bir **Split** node'u ile tek bir kanalı (örneğin Red kanalını) ayırın veya doğrudan RGB'yi kullanın.
5. Base Color (Albedo renginiz veya texture'ınız) ile Vertex Color çıktısını bir **Multiply** node'u ile çarpın.
6. Sonucu Master Stack'in **Base Color** girişine bağlayın.
7. *İpucu:* Eğer AO çok karanlık görünüyorsa, Color Space (Gamma/Linear) ayarlarını veya shader içerisinde küçük bir matematik işlemi (örneğin bir Power veya Lerp node) kullanarak AO şiddetini kontrol edebilirsiniz.

## Kaynaklar ve İleri Okuma
- [Unity URP Shader Graph Vertex Color Node](https://docs.unity3d.com/Packages/com.unity.shadergraph@12.1/manual/Vertex-Color-Node.html)
- [Blender Vertex Baking Workflow](https://docs.blender.org/manual/en/latest/render/cycles/baking.html)
- [Performance comparison of Textures vs Vertex Colors](https://forum.unity.com/)
