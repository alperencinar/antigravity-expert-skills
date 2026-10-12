# Unity URP'de Curved World (Dünya Bükülme) Shader'ı ve Matematiksel Temelleri

Klasik Subway Surfers veya Mario Kart gibi "Endless Runner" (sonsuz koşu) oyunlarında sıklıkla gördüğümüz dinamik ufuk bükülme (Curved World) efekti, Unity URP'de Shader Graph aracılığıyla Vertex Shader seviyesinde oldukça performanslı bir şekilde yapılabilir.

## Bu Efekt Oyuna Neden Değer Katar?
1. **Görsel Estetik ve Oyuncu Odaklanması:** Ufuk çizgisinin bükülmesi, oyuncunun ileriye doğru hız hissiyatını artırır. Aynı zamanda ileriden gelecek olan engellerin daha organik bir şekilde (sanki dünyanın eğiminden çıkıyormuş gibi) belirmesini sağlar.
2. **Performans Optimizasyonu İlizyonu:** Sis (Fog) kullanımına güçlü bir alternatiftir. Uzak mesafedeki objelerin keskin bir şekilde ("popping") belirmesini veya yok olmasını, kameranın görüş açısının (frustum) altında kalarak gizler.
3. **Sanat Yönetimi:** Premium ve stilize edilmiş bir "Low-Poly" hissi vermek için idealdir; dünya küçük bir gezegenin veya silindirin üzerindeymiş hissi uyandırır.

## Vertex Displacement (Köşe Öteleme) Matematik Formülü

Dünya bükülme efekti temelinde, bir köşenin (vertex) kameraya olan Z uzaklığına (derinliğine) bağlı olarak Y ekseninde (veya istenilen eksende) aşağı doğru itilmesi prensibine dayanır. En yaygın kullanılan formül ikinci dereceden (kuadratik) parabolik bir denklemdir:

**Formül:**
$$Y_{offset} = -(Distance_{Z})^2 \times Strength$$

Burada:
*   **$Distance_{Z}$**: Kameranın ve objenin (vertex'in) arasındaki Z ekseni (derinlik) mesafesidir.
*   **$Strength$**: Eğimin şiddetini belirleyen küçük bir çarpan değeridir (örn. 0.001 veya 0.005).

## URP Shader Graph ile Uygulama Adımları

1.  **Vertex Pozisyonunu Alın:** Bir `Position` node'u oluşturun ve Space ayarını **World** (Dünya) olarak seçin.
2.  **Kamera Uzaklığını Hesaplayın:** Dünyadaki Vertex pozisyonundan, Kameranın Dünya pozisyonunu (`Camera` node'u üzerinden) çıkararak (`Subtract` node) mesafeyi bulun. (Alternatif olarak doğrudan View Space/Camera Space pozisyonu da kullanılabilir).
3.  **Z Eksenini İzole Edin:** `Split` node'u kullanarak bu mesafe vektörünün yalnızca **Z** veya **B** bileşenini alın.
4.  **Parabolik Eğimi Uygulayın:** Z değerini bir `Power` node'u ile **2. kuvvete** yükseltin. (Bu sayede uzaktaki objeler çok daha hızlı bir şekilde aşağı doğru eğilir).
5.  **Şiddet ve Yön:** Çıkan sonucu bir özellik (Property - Float) ile (`Curvature Strength`) çarpın (`Multiply`). Dünyanın aşağı bükülmesi için sonucu `Negate` node'u ile negatife çevirin (veya eksi bir strength değeri kullanın).
6.  **Y Eksenine Uygulama:** Elde edilen sonucu, orijinal World Position'ın Y (Green) kanalına bir `Add` node'u ile ekleyin.
7.  **Çıktı:** Yeniden yapılandırılmış X, yeni Y ve Z koordinatlarını bir `Vector 3` node'u ile birleştirin ve sonucu Master Stack'in **Vertex Position** (Object space'e geri çevirerek veya uygun Master Node formatında) portuna bağlayın.

## Dikkat Edilmesi Gerekenler ve Sınırlar

*   **Frustum Culling Hataları:** Unity'nin CPU tabanlı Culling (görüş alanı dışı objeleri gizleme) sistemi, Shader içindeki vertex hareketlerinden habersizdir. Eğilen ufkun en ucunda objeler aniden kaybolabilir. Bunu çözmek için Mesh'lerin bounds (sınır) değerlerini kod üzerinden büyütmek gerekebilir.
*   **Gölge Hesaplamaları:** Benzer şekilde Unity'nin varsayılan gölgeleri (Shadow Casters), orijinal pozisyona göre hesaplanabilir. Shader'da gölge pass'leri için de aynı bükme fonksiyonunun uygulanması zorunludur.
*   **Mesh Çözünürlüğü:** Efekt sadece köşeleri (vertex) eğer. Eğer devasa tek bir kare plane (sadece 4 vertex) kullanırsanız bükülme gerçekleşmez. Zeminlerin ve yolların Z ekseni boyunca yeterli poligon yoğunluğuna (subdivisions) sahip olması gerekir.

## Kaynaklar
- [Curved World Shader in Unity Shader Graph (Sunny Valley Studio)](https://www.sunnyvalleystudio.com)
- [Unity Shader Graph Mathematics](https://docs.unity3d.com/Packages/com.unity.shadergraph@12.1/manual/Math-Nodes.html)
