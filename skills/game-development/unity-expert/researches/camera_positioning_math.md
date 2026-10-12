# Kamera Pozisyonlandırma Matematiği ve Endless Runner Şerit (Lane) Düzeni

Endless runner (sonsuz koşu) tarzı bir oyunda şeritleri (lanes) Unity'nin kamera sistemini kullanarak konumlandırmak için 2D ekran uzayı (screen space) ile 3D dünya uzayı (world space) arasındaki köprüyü kurmanız gerekir. Ekran 2D ve dünya 3D olduğundan, koordinatları doğru bir şekilde dönüştürmek için bir **Z-derinliği** (Z-depth - kameradan uzaklık) sağlamalısınız.

## 1. Koordinat Eşlemesini Anlamak (Coordinate Mapping)
*   **Ekran Uzayı (Screen Space):** Piksellerle tanımlanır (örneğin, `0` ile `Screen.width` arası) [1, 2].
*   **Dünya Uzayı (World Space):** Nesnelerinizin yaşadığı 3D koordinatlardır [2, 3].
*   **Köprü (Z-Derinliği):** `ScreenToWorldPoint` dönüşümü yaparken Unity bir `Vector3` girdisi gerektirir. Buradaki `z` değeri, kamera düzleminden (camera plane) dünya birimleri cinsinden uzaklıktır [1, 3]. Eğer `camera.nearClipPlane` değerini sağlarsanız, noktayı olası en yakın mesafede dönüştürür; şerit konumlandırması için oyuncunuzun/engellerinizin gerçekten var olduğu mesafeyi kullanmalısınız.

## 2. Şerit Konumlandırma İçin Pratik Yöntemler

### A. `Camera.ViewportToWorldPoint` Kullanımı (Şeritler İçin Önerilen)
Görüş alanı (Viewport) koordinatları normalize edilmiştir (0 ile 1 arası), bu da onları ekran çözünürlüğünden bağımsız hale getirir [4]. Bu, şeritleri ekran genişliğinin belirli yüzdeleri olarak tanımlamak için idealdir.

```csharp
// Şerit pozisyonlarını viewport yüzdeleri olarak tanımlayın (0.0 ile 1.0 arası)
float leftLaneX = 0.25f;  // Ekranın %25'i (Sol Şerit)
float midLaneX  = 0.5f;   // Ekranın ortası (Orta Şerit)
float rightLaneX = 0.75f; // Ekranın %75'i (Sağ Şerit)

// Oyuncunun bulunduğu kameradan uzaklığı tanımlayın (Z-Derinliği)
float zDepth = 10f; 

Vector3 leftLaneWorld = Camera.main.ViewportToWorldPoint(new Vector3(leftLaneX, 0.5f, zDepth));
```

### B. Dinamik Konumlandırma İçin Frustum Genişliğini Hesaplama
Şeritleri matematiksel olarak aralıklandırmak için belirli bir mesafede "oyun alanınızın" tam olarak ne kadar geniş olduğunu bilmeniz gerekiyorsa, kesik chóp (frustum) matematiğini kullanın [5]:

```csharp
float distance = 10f; // Kameradan uzaklık (Z-Derinliği)
float frustumHeight = 2.0f * distance * Mathf.Tan(Camera.main.fieldOfView * 0.5f * Mathf.Deg2Rad);
float frustumWidth = frustumHeight * Camera.main.aspect;

// Artık frustumWidth'i şerit sayısına bölerek şerit genişliğini bulabilirsiniz
float laneWidth = frustumWidth / 3f;
```

## 3. Endless Runner Şerit Uygulama Stratejisi
*   **Durum Yönetimi (State Management):** `currentLane`'i (mevcut şerit) izlemek için bir `enum` veya tam sayı (integer) kullanın.
*   **Hareket (Movement):** Pozisyonları her karede (frame) hesaplamak yerine, Sol, Orta ve Sağ şeritler için hedef `x` koordinatlarını oyuncunun Z-derinliğindeki kamera frustumuna göre önceden hesaplayın.
*   **Yumuşatma (Smoothing):** Oyuncuyu anında hizalamak yerine (snapping), bu önceden hesaplanmış X pozisyonları arasında pürüzsüz bir şekilde hareket ettirmek için `Vector3.Lerp` veya bir tweening kütüphanesi kullanın.
*   **Obje Havuzu (Object Pooling):** Yol segmentlerini sürekli olarak yaratmaktan (instantiate) veya yok etmekten (destroy) kaçının. Kameranın görüş frustumunun dışına çıkan segmentleri geri dönüştürmek için bir obje havuzu kullanın.

## Faydalı Fonksiyonların Özeti
*   **`Camera.ViewportToWorldPoint(Vector3)`**: Şeritleri ekran genişliğinin yüzdesine göre yerleştirmek için en iyisidir. Parallax kaydırma (scrolling) ve dinamik ölçekleme için referans noktası sağlar [4, 5].
*   **`Camera.ScreenToWorldPoint(Vector3)`**: Kesin piksel tabanlı girdiler (fare tıklamaları veya dokunmatik girdiler gibi) kullanıyorsanız en iyisidir [1, 3].
*   **`GeometryUtility.CalculateFrustumPlanes`**: Performansı artırmak için oyuncunun görüş alanının (frustum) çok gerisinde veya dışında kalan nesneleri elemek (culling) için faydalıdır [6].

### Kaynaklar ve Alıntılar
- [1] Unity Documentation - ScreenToWorldPoint: [Unity API Reference](https://docs.unity3d.com/ScriptReference/Camera.ScreenToWorldPoint.html)
- [2] ViewportToWorldPoint vs ScreenToWorldPoint: Medium & Unity Forums Discussions.
- [3] Frustum Math and Calculations: [Unity Manual - Understanding Frustum](https://docs.unity3d.com/Manual/UnderstandingFrustum.html)
- [4] Viewport and Aspect Ratios Handling in Unity.
- [5] Endless Runner Lane Logic Patterns: GameDev StackExchange and YouTube Tutorials.
- [6] GeometryUtility Culling: Unity Scripting API.
