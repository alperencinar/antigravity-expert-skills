# Unity URP 3D Sonsuz Koşu Oyunlarında Görsel Derinlik ve Dünya Eğimi Araştırması

Bu rapor, Unity URP kullanarak 3D sonsuz koşu (endless runner) oyunları geliştirirken karşılaşılan "düzlük" (flatness) hissini giderme, kamera ayarları, dünya eğimi (world curvature) ve vertex shader üzerinden bükülme (bending) tekniklerini üç ana açıdan (Angle) incelemektedir.

## Açı A: Neden Düşük Poligonlu 3D Koşu Oyunları Düz/2D Görünür ve Nasıl Çözülür?

Düşük poligonlu oyunların düz (flat) görünmesinin temel sebepleri arasında gölgelerin eksikliği, atmosferik derinlik hissinin (sis/fog) olmaması ve yanlış kamera açıları bulunur. *Subway Surfers* gibi oyunlarda bu durum doğru kamera açıları ile çözülmüştür:

*   **Field of View (FOV):** Standart 60° FOV, bu tür oyunlarda objeleri fazla uzakta hissettirip "balık gözü" etkisi yaratabilir. Bunun yerine **25° ila 45° arasında daraltılmış bir FOV** kullanılır. Bu ayar, perspektifi hafifçe düzleştirip yolu ve engelleri daha okunaklı hale getiren sinematik / telephoto bir etki yaratır.
*   **Pitch Angle (Eğim Açısı):** Kameranın aşağıya doğru **15° ile 30° arasında** bir eğimle (pitch) bakması standarttır. Böylece ufuk çizgisi ekranın üst kısmında kalır, oyuncunun önündeki engeller ve zemin çok daha net algılanır.
*   **Derinlik Algısı:** Sadece kamera yetmez; sis (fog) efekti, yönlü ışık gölgeleri ve en önemlisi "dünyayı bükme" (world bending) shader'ları kullanılarak statik bir 3D algısından çıkıp dinamik bir derinlik yaratılır.
*   [Kaynak 1](https://www.reddit.com/r/Unity3D/comments/1df5gsw/how_to_achieve_cinematic_look_in_unity_urp/)
*   [Kaynak 2](https://littlepolygon.com/blog/2021/stylized-low-poly-graphics/)

## Açı B: Yol Eğimi (Curvature) Yönü, Şiddeti ve Bound (Sınır) Problemleri

### Eğimin Yönü (Convex vs Concave)
Sonsuz koşu oyunlarının endüstri standardı **aşağı doğru (convex - dışbükey)** bir eğimdir. Tıpkı *Animal Crossing* veya *Subway Surfers* oyunlarındaki gibi, dünya ufka doğru yuvarlanıyor hissi verir. Bu sadece görsel bir estetik sunmakla kalmaz, aynı zamanda objelerin uzaktan aniden belirmesini (pop-in) maskeleyerek ufuk çizgisinin altına gizler. Yukarı doğru (concave) eğim ise "Inception" tarzı baş döndürücü spesifik sekanslar dışında tercih edilmez.

### Standart Eğrilik Katsayıları
Vertex shader'larda standart bükülme formülü kuadratiktir: `Y_Offset = - (Z_Mesafe * Z_Mesafe) * Eğim_Katsayısı`
*   **Katsayı (Coefficient):** Geliştiriciler genelde **0.001 ile 0.05** arasında çok küçük değerler kullanır. Çünkü mesafenin karesi alındığından, 0.1 gibi değerler dünyayı anında 90 derece büker. En standart kullanım `0.001` veya `0.002` civarıdır.

### Parent Scaling ve Bounding Box Sorunları
Bükülme (bending) sadece GPU'da, yani shader düzeyinde gerçekleşir. Unity CPU'su nesnenin fiziksel olarak büküldüğünden habersizdir.
*   **Frustum Culling Sorunu:** Vertex shader nesneyi aşağıya büktüğünde, CPU nesnenin hala orijinal (düz) yerinde olduğunu sanır. Kamera orijinal yeri görmediğinde (örneğin nesne eğrilikten dolayı kameranın görüş açısına yeni girmişse) CPU objeyi "Görünmüyor" sanıp render etmeyi keser (Culling).
*   **Çözüm:** Mesh sınırlarını (`mesh.bounds`) kod üzerinden yapay olarak büyütmek (`mesh.bounds = new Bounds(Vector3.zero, new Vector3(100, 100, 100))`) gerekir.
*   **Parent Scaling (Ölçekleme):** Eğer obje bir Parent altında scale edilmişse (örneğin Z ekseninde uzatılmışsa), Shader içindeki Local-to-World veya Object-to-Clip matrix dönüşümlerinde Z mesafesi farklı hesaplanabilir. Bu yüzden eğrilik uygulanan objelerin veya parent'larının scale değerlerinin (1,1,1) tutulması endüstri standardıdır.
*   [Kaynak 3](https://notslot.com/blog/curved-world)
*   [Kaynak 4](https://docs.unity3d.com/Manual/FrustumCulling.html)

## Açı C: Mesh Altbölümleme (Subdivision) ve Bükülme Çözünürlüğü

Vertex shader üzerinden uygulanan bükülme efekti, sihirli bir şekilde düzlemleri eğmez; sadece var olan vertex (köşe) noktalarının pozisyonunu değiştirir.

*   **Subdivision Zorunluluğu:** Uzun köprüler, trenler, raylar veya düz yol FBX modelleri, Z ekseni boyunca bükülecekse **kesinlikle vertex altbölümlemelerine (subdivision) ihtiyaç duyarlar.**
*   **Yetersiz Subdivision Sonucu:** Eğer uzun bir tren vagonunun sadece başı ve sonu varsa (ortasında vertex yoksa), shader sadece bu iki uç noktayı aşağı çeker. Aradaki bağlantı dümdüz kalır ve eğri bir dünya üzerinde köşe kapmaca gibi düz, kırık çizgiler oluşur.
*   **Çözüm:** Blender veya Maya gibi 3D modelleme programlarında objelerin Z ekseni boyunca `Loop Cut` veya `Subdivide` işlemiyle kesilmiş olması gerekir. Çok fazla poligon performans somunu yaratacağından, sadece eğriliğin fark edileceği büyüklükteki uzun objelere (örn. trenler, binalar, uzun yollar) yeterli seviyede subdivision atılmalıdır.
*   [Kaynak 5](https://gamedevbill.com/curved-world-shader-breakdown/)
*   [Kaynak 6](https://docs.unity3d.com/Manual/LevelOfDetail.html)
