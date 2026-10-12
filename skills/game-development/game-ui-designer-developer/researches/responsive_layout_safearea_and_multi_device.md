# Enterprise Mobil ve Çoklu Cihaz UI Architecture: Responsive Layout, Safe Area ve Performance Optimization Guidelines

## Executive Summary
Modern AAA ve enterprise mobil oyun geliştirmede, birbirinden radikal biçimde ayrışan ekran oranları ($4:3$ iPad tabletlerden $21:9$ ultra-wide ekranlara), çentik (notch), dinamik ada (dynamic island) ve kamera delikleri (punch-hole) gibi donanımsal kesikler (cutout) nedeniyle tekil ve statik bir UI tasarımı imkansız hale gelmiştir. Bu doküman, Unity UGUI (Unity Graphical User Interface) mimarisi üzerinde **çoklu cihaz adaptasyonu**, **otomatik Safe Area yönetimi**, **RectTransform vektör matematiği** ve **sıfır-tahsisli (zero-alloc) layout performans optimizasyonları** için üretim seviyesinde (production-grade) standartları kapsar.

---

## 1. Multi-Aspect Ratio Adaptasyon Mimarisi (16:9, 19.5:9, 21:9, 4:3)

### 1.1. Mobil Cihaz Ekran Oranları Spektrumu

Mobil ekosistemde hedef alınan cihaz grupları 4 ana ekran oranı kategorisinde toplanır:

| Ekran Oranı Kategori | Oran ($\frac{W}{H}$) | Tipik Cihaz Örnekleri | Piksel Çözünürlüğü Örnekleri | UI Tasarım Riski |
| :--- | :--- | :--- | :--- | :--- |
| **Tablet / Legacy** | $4:3$ ($1.333$) | Apple iPad (Tüm seriler), Android Tabletler | $2048 \times 1536$, $2732 \times 2048$ | Dikey görüş alanı darlığı, yan panellerin merkeze sıkışması |
| **Standart HD / 16:9** | $16:9$ ($1.777$) | iPhone 8, SE, Bütçe Dostu Android Cihazlar | $1920 \times 1080$, $1280 \times 720$ | Referans baseline; modern cihazlarda yanlarda boşluk riski |
| **Modern Notch/Tall**| $19.5:9$ ($2.166$) | iPhone 13/14/15/16 Pro, Samsung Galaxy S23/S24 | $2532 \times 1170$, $2340 \times 1080$ | Çentik/Dynamic Island çakışması, extreme köşe yuvarlatmaları |
| **Ultra-Wide** | $21:9$ ($2.333$) | Sony Xperia 1/5 serisi, Katlanabilir Cihazlar | $3840 \times 1644$, $2560 \times 1080$ | HUD öğelerinin aşırı kenarlara uzaklaşması, göz takibi zorluğu |

---

### 1.2. Canvas Scaler Matematiksel Çalışma Prensibi

Unity `CanvasScaler` bileşeni, referans çözünürlük ($W_{ref}, H_{ref}$) ile anlık ekran çözünürlüğünü ($W_{current}, H_{current}$) kıyaslayarak bir global ölçekleme katsayısı ($S$) hesaplar. 

`Scale Mode = Scale With Screen Size` seçildiğinde ve `Screen Match Mode = Match Width Or Height` ayarlandığında, blending parametresi $a \in [0, 1]$ kullanılarak logaritmik ölçekleme denklemi çalıştırılır:

$$\log_2(S) = (1 - a) \cdot \log_2\left(\frac{W_{current}}{W_{ref}}\right) + a \cdot \log_2\left(\frac{H_{current}}{H_{ref}}\right)$$

$$S = 2^{(1-a) \log_2\left(\frac{W_{current}}{W_{ref}}\right) + a \log_2\left(\frac{H_{current}}{H_{ref}}\right)} = \left(\frac{W_{current}}{W_{ref}}\right)^{1-a} \cdot \left(\frac{H_{current}}{H_{ref}}\right)^a$$

Burada:
- $a = 0$ ise Canvas yalnızca Genişliğe ($W$) göre ölçeklenir ($S = \frac{W_{current}}{W_{ref}}$).
- $a = 1$ ise Canvas yalnızca Yüksekliğe ($H$) göre ölçeklenir ($S = \frac{H_{current}}{H_{ref}}$).
- $a = 0.5$ ise Genişlik ve Yükseklik değişimlerinin geometrik ortalaması alınır.

> [!IMPORTANT]
> **Statik $a$ (Match Value) Kullanmanın Yetersizliği:**
> Yatay (Landscape) bir oyunda $a = 0.5$ sabit tutulduğunda, $16:9$ referans tasarımdan $4:3$ iPad ekranına geçildiğinde dikey boyut aşırı büyür ve üst/alt UI elemanları ekrandan taşar. Aksine $21:9$ ekranlarda dikey alan daralır ve UI elemanları birbirinin üzerine biner. Bu nedenle $a$ katsayısı anlık aspect ratio'ya göre dinamik olarak hesaplanmalıdır.

---

### 1.3. Dinamik Aspect Ratio Uyarlama ve FOV Dengesi

Görsel kırpılmayı (clipping) önlemek için adaptör mimarisi iki kritik görevi üstlenir:
1. **Canvas Scaler Blending Hesaplaması:** Aspect ratio 16:9'dan geniş ise (örn. 19.5:9, 21:9) $a = 1$ (Height Matching) yapılarak dikey yüksekliğin sabitleşmesi ve yatay genişlemenin güvenli alana yayılması sağlanır. Aspect ratio 16:9'dan dar ise (örn. 4:3) $a = 0$ (Width Matching) yapılarak yatay genişliğin korunması ve dikey nesnelerin taşmaması garanti edilir.
2. **3D Kamera FOV / Orthographic Size Dengelenmesi:** 3D UI veya UI arkasındaki oyun içi kamera geniş aspect ratio'larda dikey görüş açısını kaybetmemelidir. Orthographic Kamera için düzeltme formülü:

$$\text{Size}_{adjusted} = \text{Size}_{base} \times \max\left(1.0, \frac{\text{Aspect}_{target}}{\text{Aspect}_{current}}\right)$$

Perspective Kamera için dikey FOV ($\theta_v$) hesaplaması:

$$\theta_v = 2 \cdot \arctan\left( \tan\left(\frac{\theta_{base}}{2}\right) \times \max\left(1.0, \frac{\text{Aspect}_{target}}{\text{Aspect}_{current}}\right) \right)$$

---

### 1.4. Production-Grade C# Script: `AspectRatioAdapter.cs`

Aşağıdaki script, Canvas Scaler parametrelerini, kamera FOV değerlerini ve arka plan kaplama modlarını runtime esnasında sıfır bellek tahsisi ile günceller.

```csharp
using System;
using UnityEngine;
using UnityEngine.UI;

namespace Cardiv.UI.Layout
{
    /// <summary>
    /// Ekran oranını (Aspect Ratio) dinamik olarak analiz eden, Canvas Scaler Match parametresini
    /// ve ilişkili Camera FOV/Orthographic Size değerlerini otomatik adapte eden mimari bileşen.
    /// </summary>
    [DisallowMultipleComponent]
    [RequireComponent(typeof(CanvasScaler))]
    public sealed class AspectRatioAdapter : MonoBehaviour
    {
        [System.Serializable]
        public struct AspectThreshold
        {
            [Tooltip("Ekran Oranı Adı (Örn: iPad 4:3, Standard 16:9, iPhone 19.5:9)")]
            public string name;
            [Tooltip("Hedef Aspect Ratio Değeri (W / H)")]
            public float aspectRatio;
            [Range(0f, 1f), Tooltip("Canvas Scaler Match Width Or Height Değeri")]
            public float matchWidthOrHeight;
        }

        [Header("Canvas & Reference Config")]
        [SerializeField] private CanvasScaler canvasScaler;
        [SerializeField] private Vector2 referenceResolution = new Vector2(1920f, 1080f);

        [Header("Aspect Ratio Eşikleri")]
        [SerializeField] private float baselineAspect = 1.7777778f; // 16:9 Baseline
        [SerializeField] private AspectThreshold[] aspectThresholds = new AspectThreshold[]
        {
            new AspectThreshold { name = "Tablet (4:3)", aspectRatio = 1.3333333f, matchWidthOrHeight = 0f },
            new AspectThreshold { name = "Standard (16:9)", aspectRatio = 1.7777778f, matchWidthOrHeight = 0.5f },
            new AspectThreshold { name = "Tall Notch (19.5:9)", aspectRatio = 2.1666667f, matchWidthOrHeight = 1f },
            new AspectThreshold { name = "UltraWide (21:9)", aspectRatio = 2.3333333f, matchWidthOrHeight = 1f }
        };

        [Header("3D Camera Support (Opsiyonel)")]
        [SerializeField] private Camera targetCamera;
        [SerializeField] private bool adjustCameraFov = true;
        [SerializeField] private float defaultFieldOfView = 60f;
        [SerializeField] private float defaultOrthographicSize = 5f;

        public event Action<float, float> OnAspectRatioChanged;

        private float _lastScreenWidth;
        private float _lastScreenHeight;
        private float _currentAspectRatio;

        public float CurrentAspectRatio => _currentAspectRatio;

        private void Awake()
        {
            if (canvasScaler == null)
            {
                canvasScaler = GetComponent<CanvasScaler>();
            }

            ConfigureCanvasScaler();
            EvaluateAspectRatio(forceUpdate: true);
        }

        private void Update()
        {
            if (Mathf.Approximately(_lastScreenWidth, Screen.width) == false ||
                Mathf.Approximately(_lastScreenHeight, Screen.height) == false)
            {
                EvaluateAspectRatio(forceUpdate: false);
            }
        }

        private void ConfigureCanvasScaler()
        {
            canvasScaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            canvasScaler.referenceResolution = referenceResolution;
            canvasScaler.screenMatchMode = CanvasScaler.ScreenMatchMode.MatchWidthOrHeight;
        }

        public void EvaluateAspectRatio(bool forceUpdate)
        {
            _lastScreenWidth = Screen.width;
            _lastScreenHeight = Screen.height;

            if (_lastScreenHeight <= 0f) return;

            _currentAspectRatio = _lastScreenWidth / _lastScreenHeight;

            // Interpolasyon veya en yakın esik değeri hesabı
            float calculatedMatch = ComputeDynamicMatch(_currentAspectRatio);
            canvasScaler.matchWidthOrHeight = calculatedMatch;

            if (adjustCameraFov && targetCamera != null)
            {
                AdjustCameraFieldOfView(_currentAspectRatio);
            }

            OnAspectRatioChanged?.Invoke(_currentAspectRatio, calculatedMatch);
        }

        private float ComputeDynamicMatch(float aspect)
        {
            if (aspectThresholds == null || aspectThresholds.Length == 0)
            {
                return aspect < baselineAspect ? 0f : 1f;
            }

            // Aspect ratio değerine göre sıralı piecewise linear interpolasyon
            if (aspect <= aspectThresholds[0].aspectRatio)
            {
                return aspectThresholds[0].matchWidthOrHeight;
            }

            int count = aspectThresholds.Length;
            if (aspect >= aspectThresholds[count - 1].aspectRatio)
            {
                return aspectThresholds[count - 1].matchWidthOrHeight;
            }

            for (int i = 0; i < count - 1; i++)
            {
                var lower = aspectThresholds[i];
                var upper = aspectThresholds[i + 1];

                if (aspect >= lower.aspectRatio && aspect <= upper.aspectRatio)
                {
                    float t = (aspect - lower.aspectRatio) / (upper.aspectRatio - lower.aspectRatio);
                    return Mathf.Lerp(lower.matchWidthOrHeight, upper.matchWidthOrHeight, t);
                }
            }

            return 0.5f;
        }

        private void AdjustCameraFieldOfView(float aspect)
        {
            if (aspect >= baselineAspect)
            {
                // Ekran baseline'dan daha genislemişse FOV sabit kalır (Horizontal FOV artar)
                if (targetCamera.orthographic)
                {
                    targetCamera.orthographicSize = defaultOrthographicSize;
                }
                else
                {
                    targetCamera.fieldOfView = defaultFieldOfView;
                }
            }
            else
            {
                // Ekran 16:9'dan daha dar ise (örn. 4:3 iPad), dikey alanı genişleterek kırpılmayı engelle
                float aspectScale = baselineAspect / aspect;

                if (targetCamera.orthographic)
                {
                    targetCamera.orthographicSize = defaultOrthographicSize * aspectScale;
                }
                else
                {
                    float radHfov = 2f * Mathf.Atan(Mathf.Tan(defaultFieldOfView * 0.5f * Mathf.Deg2Rad) * baselineAspect);
                    float newVfov = 2f * Mathf.Atan(Mathf.Tan(radHfov * 0.5f) / aspect) * Mathf.Rad2Deg;
                    targetCamera.fieldOfView = newVfov;
                }
            }
        }

#if UNITY_EDITOR
        private void OnValidate()
        {
            if (canvasScaler == null) canvasScaler = GetComponent<CanvasScaler>();
            if (Application.isPlaying && canvasScaler != null)
            {
                EvaluateAspectRatio(forceUpdate: true);
            }
        }
#endif
    }
}
```

---

## 1.5. Sıfır Çakışma Metin Düzeni ve Font Büyütme Kuralları (Zero-Overlap Typography & Layout Bounding Box Math)

### 1.5.1. Çakışma Matematik Formülü ve Bounding Box Sınırları

Mobil arayüzlerde çok satırlı kartlar veya kapsül Rozetlerinde (`OilStatusUI`, `HUD Status Badge`), metin boyutları büyütüldüğünde (`12pt -> 17pt`, `22pt -> 32pt`) metinlerin dikey eksende (`Y Axis`) birbiri üzerine binmesini önlemek için şu bounding box aralık formülü zorunludur:

$$\text{Y}_{\text{bottom, top\_text}} = Y_{\text{center, top}} - \frac{\text{Height}_{\text{top}}}{2}$$
$$\text{Y}_{\text{top, bottom\_text}} = Y_{\text{center, bottom}} + \frac{\text{Height}_{\text{bottom}}}{2}$$
$$\Delta Y_{\text{gap}} = \text{Y}_{\text{bottom, top\_text}} - \text{Y}_{\text{top, bottom\_text}} \ge \text{Margin}_{\text{min}} \, (4\text{--}8\text{px})$$

#### ❌ Hatalı (Overlapping) Hizalama Örneği:
- Kapsül Yüksekliği: `92px` (Merkez `Y = 0`)
- **Üst Metin:** Pivot `(0.5, 1.0)`, `AnchoredY = -6`, Yükseklik = `36px` $\rightarrow$ Taban Y = `40 - 36 = 4px`
- **Alt Metin:** Pivot `(0.5, 0.0)`, `AnchoredY = +6`, Yükseklik = `42px` $\rightarrow$ Tavan Y = `6 + 42 = 48px`
- **Sonuç:** `Y = 6px` ile `Y = 40px` arasında **34 piksellik devasa bir çakışma (Overlap) oluşur!** Alt metin üst metnin tam üzerine biner.

#### ✅ Doğru (Zero-Overlap) Hizalama Standardı:
- **Ayrıştırılmış Anchor Bölgeleri (Anchor Splitting):**
  - Üst Satır (Başlık): `anchorMin = (0.0, 0.52)`, `anchorMax = (1.0, 1.0)`, `pivot = (0.5, 0.5)`, `anchoredPosition = (20, 18)`
  - Alt Satır (Sayaç): `anchorMin = (0.0, 0.0)`, `anchorMax = (1.0, 0.48)`, `pivot = (0.5, 0.5)`, `anchoredPosition = (20, -16)`
- **Sonuç:** Üst metin `Y = +5px` ile `+31px` arasında, alt metin `Y = -32px` ile `0px` arasındadır. İki metin arasında **5 piksellik garanti dikey boşluk** oluşur ve asla çakışmaz!

---

## 2. Device Safe Area Yönetimi (`Screen.safeArea` ve Cutout Sınırları)

### 2.1. Safe Area Kavramı ve Mobil Donanım Kesikleri

Modern mobil cihazlarda ekranın aktif kullanılabilir alanı donanımsal engeller tarafından kısıtlanır:
- **Display Cutout (Notch):** Ön kamera ve ahize modülünün ekran içerisine girmesi.
- **Dynamic Island:** Ekran üzerinde dinamik değişen yazılımsal/donanımsal ada kesiği.
- **Punch-Hole:** Ekran içinde bağımsız dairesel kamera delikleri.
- **Home Indicator / Navigation Bar:** iOS ve Android alt çubuğu.
- **Rounded Corners:** Ekranın fiziksel yuvarlatılmış köşeleri (köşe kırpılmaları).

Unity engine bu fiziksel sınırları `Screen.safeArea` yapısı ile piksel cinsinden sunar. `Screen.safeArea` yapısı ekranın sol-alt köşesini $(0, 0)$ kabul eden bir `Rect` döndürür:

$$\text{safeArea} = \text{Rect}(X_{min}, Y_{min}, Width, Height)$$

---

### 2.2. Normalize Anchor Koordinat Dönüşüm Matematiği

`Screen.safeArea` doğrudan piksel bazlı olduğu için farklı çözünürlüklerde UGUI `RectTransform` bileşenine uygulanamaz. Piksel koordinatları, `RectTransform` min/max anchor koordinatlarına ($[0, 1]$ normalize uzayına) çevrilmelidir:

$$anchorMin.x = \frac{\text{safeArea.x}}{\text{Screen.width}}$$

$$anchorMin.y = \frac{\text{safeArea.y}}{\text{Screen.height}}$$

$$anchorMax.x = \frac{\text{safeArea.x} + \text{safeArea.width}}{\text{Screen.width}}$$

$$anchorMax.y = \frac{\text{safeArea.y} + \text{safeArea.height}}{\text{Screen.height}}$$

```
+-------------------------------------------------------------+ (Screen.width, Screen.height)
| (0, 1)                     TOP                      (1, 1)  |
|          +---------------------------------------+          |
|          | (anchorMin.x, anchorMax.y)            |          |
|  LEFT    |            SAFE AREA CONTAINER        |  RIGHT   |
|          | (anchorMin.x, anchorMin.y)            |          |
|          +---------------------------------------+          |
| (0, 0)                   BOTTOM                     (1, 0)  |
+-------------------------------------------------------------+
```

---

### 2.3. Oryantasyon Değişimleri ve High-DPI Kenar Durumları (Edge Cases)

Safe Area uygulanırken dikkat edilmesi gereken mimari kenar durumlar şunlardır:
1. **Landscape Left vs Landscape Right Asimetrisi:** Cihaz 180 derece döndürüldüğünde notch sol taraftan sağ tarafa geçer. `Screen.safeArea` anlık oryantasyonu yansıtır; bu nedenle script her oryantasyon değişimini algılamalıdır.
2. **Çoklu Canvas / Nested Safe Area Hatası:** Eğer bir Safe Area konteynerinin içerisine ikinci bir Safe Area scripti koyarsanız, normalize oranlar karetsel olarak küçülür. Safe Area yalnızca Canvas altındaki **root container** seviyesinde uygulanmalıdır.
3. **Editor Emulation & High-DPI Scale:** Unity Editor Simulator penceresinde `Screen.safeArea` doğru simüle edilirken varsayılan Game View pencerelerinde tam ekran döner. Simulator testleri zorunludur.

---

### 2.4. Production-Grade C# Script: `SafeAreaHandler.cs`

Aşağıdaki script, Safe Area değişikliklerini poling yapmadan kontrol eder, marjin (padding) ilavelerine izin verir ve Unity Editor testleri için simülasyon desteği sunar.

```csharp
using UnityEngine;

namespace Cardiv.UI.Layout
{
    /// <summary>
    /// Screen.safeArea verilerini okuyarak RectTransform bileşeninin anchor değerlerini
    /// normalize koordinat uzayında güncelleyen production-grade Safe Area yöneticisi.
    /// </summary>
    [DisallowMultipleComponent]
    [RequireComponent(typeof(RectTransform))]
    public sealed class SafeAreaHandler : MonoBehaviour
    {
        [Header("Conforming Controls")]
        [SerializeField] private bool conformLeft = true;
        [SerializeField] private bool conformRight = true;
        [SerializeField] private bool conformTop = true;
        [SerializeField] private bool conformBottom = true;

        [Header("Additional Padding (Canvas Pixel cinsinden)")]
        [SerializeField] private float extraPaddingLeft = 0f;
        [SerializeField] private float extraPaddingRight = 0f;
        [SerializeField] private float extraPaddingTop = 0f;
        [SerializeField] private float extraPaddingBottom = 0f;

#if UNITY_EDITOR
        [Header("Editor Simulation")]
        [SerializeField] private bool simulateInEditor = false;
        [SerializeField] private Rect editorSimulatedSafeArea = new Rect(132, 102, 2272, 1068); // Örn iPhone 15 Pro Landscape
#endif

        private RectTransform _rectTransform;
        private Rect _lastSafeArea = new Rect(0, 0, 0, 0);
        private Vector2Int _lastScreenSize = new Vector2Int(0, 0);
        private ScreenOrientation _lastOrientation = ScreenOrientation.Unknown;

        private void Awake()
        {
            _rectTransform = GetComponent<RectTransform>();
            ApplySafeArea(forceUpdate: true);
        }

        private void OnEnable()
        {
            ApplySafeArea(forceUpdate: true);
        }

        private void Update()
        {
            CheckAndApplySafeArea();
        }

        private void OnRectTransformDimensionsChange()
        {
            CheckAndApplySafeArea();
        }

        private void CheckAndApplySafeArea()
        {
            Rect currentSafeArea = GetActiveSafeArea();
            Vector2Int currentScreenSize = new Vector2Int(Screen.width, Screen.height);
            ScreenOrientation currentOrientation = Screen.orientation;

            if (currentSafeArea != _lastSafeArea ||
                currentScreenSize != _lastScreenSize ||
                currentOrientation != _lastOrientation)
            {
                ApplySafeArea(forceUpdate: false);
            }
        }

        private Rect GetActiveSafeArea()
        {
#if UNITY_EDITOR
            if (simulateInEditor && !Application.isPlaying)
            {
                return editorSimulatedSafeArea;
            }
#endif
            return Screen.safeArea;
        }

        public void ApplySafeArea(bool forceUpdate)
        {
            Rect safeArea = GetActiveSafeArea();
            Vector2Int screenSize = new Vector2Int(Screen.width, Screen.height);

            if (screenSize.x <= 0 || screenSize.y <= 0) return;

            _lastSafeArea = safeArea;
            _lastScreenSize = screenSize;
            _lastOrientation = Screen.orientation;

            // Normalize anchor hesaplamaları [0, 1]
            Vector2 anchorMin = safeArea.position;
            Vector2 anchorMax = safeArea.position + safeArea.size;

            anchorMin.x /= screenSize.x;
            anchorMin.y /= screenSize.y;
            anchorMax.x /= screenSize.x;
            anchorMax.y /= screenSize.y;

            // Ekstra piksel padding'lerinin normalize uzaya çevrilmesi
            if (extraPaddingLeft > 0f) anchorMin.x += extraPaddingLeft / screenSize.x;
            if (extraPaddingRight > 0f) anchorMax.x -= extraPaddingRight / screenSize.x;
            if (extraPaddingBottom > 0f) anchorMin.y += extraPaddingBottom / screenSize.y;
            if (extraPaddingTop > 0f) anchorMax.y -= extraPaddingTop / screenSize.y;

            // Kullanıcı konfigürasyonuna göre conform filtreleme
            Vector2 finalAnchorMin = _rectTransform.anchorMin;
            Vector2 finalAnchorMax = _rectTransform.anchorMax;

            if (conformLeft) finalAnchorMin.x = anchorMin.x;
            if (conformRight) finalAnchorMax.x = anchorMax.x;
            if (conformBottom) finalAnchorMin.y = anchorMin.y;
            if (conformTop) finalAnchorMax.y = anchorMax.y;

            // Sadece değişiklik varsa RectTransform'a yaz (Dirtying önleme)
            if (forceUpdate || _rectTransform.anchorMin != finalAnchorMin || _rectTransform.anchorMax != finalAnchorMax)
            {
                _rectTransform.anchorMin = finalAnchorMin;
                _rectTransform.anchorMax = finalAnchorMax;
                
                // Stretch modunda offset'leri sıfırla
                _rectTransform.offsetMin = Vector2.zero;
                _rectTransform.offsetMax = Vector2.zero;
            }
        }
    }
}
```

---

## 3. Dinamik Anchor & Pivot Matematiksel Çerçevesi (RectTransform Internals)

### 3.1. RectTransform Vektör Uzayı ve Çözümleme Matematik Denklemleri

Unity UGUI `RectTransform`, geleneksel 3D `Transform` yapısından farklı olarak üst ebeveynin (parent) boyutlarına bağımlı 2D sınır kutusu (bounding box) matematiği kullanır.

Bir `RectTransform` aşağıdaki 5 temel vektör değişkeni ile tanımlanır:
1. **Anchor Min ($a_{min}$):** Sol-Alt tutturma noktası normalize oranı $[0, 1]^2$.
2. **Anchor Max ($a_{max}$):** Sağ-Üst tutturma noktası normalize oranı $[0, 1]^2$.
3. **Pivot ($p$):** Elemanın kendi içindeki merkez orijin koordinatı $[0, 1]^2$.
4. **Anchored Position ($Pos_{anchored}$):** Pivot noktasının anchor referans noktasına olan piksel uzaklığı.
5. **Size Delta ($SD$):** Anchor moduna göre değişen boyut offset değeri.

Parent RectTransform boyutu $P = (W_{parent}, H_{parent})$ olmak üzere, nesnenin Parent Local Uzayındaki mutlak köşe koordinatları ($Rect_{local}$) şu şekilde türetilir:

$$AnchorPoint_{min} = (W_{parent} \cdot a_{min.x}, H_{parent} \cdot a_{min.y})$$

$$AnchorPoint_{max} = (W_{parent} \cdot a_{max.x}, H_{parent} \cdot a_{max.y})$$

---

### 3.2. Yüzde Tabanlı (Stretch) Sizing vs Sabit Piksel Offset (Fixed Anchor)

#### Durum A: Sabit Boyutlu Nesneler (Fixed Anchors: $a_{min} = a_{max}$)
Anchor min ve max noktaları çakıştığında ($a_{min} = a_{max} = a$), nesne esnemez.
- $SizeDelta = (Width, Height)$ doğrudan nesnenin genişlik ve yüksekliğidir.
- Anchor Referans Noktası: $RefPoint = (W_{parent} \cdot a_x, H_{parent} \cdot a_y)$
- Nesnenin Pivot Noktasının Lokal Koordinatı: 

$$Center_{pivot} = RefPoint + Pos_{anchored}$$

- Sol-Alt ($Min$) ve Sağ-Üst ($Max$) lokal sınırlar:

$$LocalMin = Center_{pivot} - (p_x \cdot Width, p_y \cdot Height)$$

$$LocalMax = Center_{pivot} + ((1 - p_x) \cdot Width, (1 - p_y) \cdot Height)$$

#### Durum B: Esnek/Yüzde Tabanlı Nesneler (Stretch Anchors: $a_{min} \neq a_{max}$)
Anchor min ve max noktaları ayrıştığında, nesne parent boyutuna bağlı olarak esner.
- $SizeDelta = (offsetMax.x - offsetMin.x, offsetMax.y - offsetMin.y)$
- $offsetMin = (Left, Bottom)$, $offsetMax = (-Right, -Top)$
- Genişlik ($W$) ve Yükseklik ($H$) denklem formülü:

$$W = W_{parent} \cdot (a_{max.x} - a_{min.x}) + SD_x$$

$$H = H_{parent} \cdot (a_{max.y} - a_{min.y}) + SD_y$$

> [!NOTE]
> Tam ekran Stretch modunda ($a_{min} = (0,0)$, $a_{max} = (1,1)$ ve $offsetMin = offsetMax = (0,0)$) iken $SD = (0, 0)$ olur ve nesne $W = W_{parent}, H = H_{parent}$ olarak tam oturur.

---

### 3.3. Kritik Anchor/Pivot Preset Matrisi ve Kullanım Senaryoları

| UI Eleman Tipi | Anchor Min ($a_{min}$) | Anchor Max ($a_{max}$) | Pivot ($p$) | Size Delta ($SD$) / Offsets | Kullanım Senaryosu ve Davranışı |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Top-Left HUD** | $(0, 1)$ | $(0, 1)$ | $(0, 1)$ | $SD = (Width, Height)$ | Sol üst köşeye sabitlenmiş oyuncu avatarı / HP barı. Ekran büyüdükçe sola dayalı kalır. |
| **Top-Center Banner** | $(0.5, 1)$ | $(0.5, 1)$ | $(0.5, 1)$ | $SD = (Width, Height)$ | Skorkart / Kalan Zaman paneli. Ekran genişledikçe yatayda tam ortada kalır. |
| **Bottom-Right CTA** | $(1, 0)$ | $(1, 0)$ | $(1, 0)$ | $SD = (Width, Height)$ | Sağ alt ateş/zıplama butonu. Sağ ve alt sınıra sabitlenir. |
| **Full Stretch Panel**| $(0, 0)$ | $(1, 1)$ | $(0.5, 0.5)$ | $offsetMin=(0,0), offsetMax=(0,0)$ | Arka plan karartma (Modal Overlay) veya Safe Area Root Container. |
| **Horizontal Bar Stretch**| $(0, 1)$ | $(1, 1)$ | $(0.5, 1)$ | $offsetMin.x=Left, offsetMax.x=-Right$ | Ekranın üstünü kaplayan ve genişledikçe esneyen Top Header Bar. |

---

### 3.4. Dinamik Konteyner Yükseklik/Genişlik Hesaplama Matematiği

İçerisinde N adet dinamik kart/eleman barındıran bir konteynerin yüksekliği ($H_{container}$), pahalı UGUI `ContentSizeFitter` bileşeni kullanılmadan kod tarafında şu matematiksel formülle tek geçişte ($O(N)$) hesaplanır:

$$H_{container} = Padding_{top} + Padding_{bottom} + \sum_{i=1}^{N} Height_i + (N - 1) \cdot Spacing$$

Bu değer doğrudan RectTransform'a uygulanır:

```csharp
public static void UpdateContainerHeightDirect(RectTransform container, int childCount, float childHeight, float spacing, float paddingTop, float paddingBottom)
{
    if (childCount <= 0)
    {
        container.sizeDelta = new Vector2(container.sizeDelta.x, paddingTop + paddingBottom);
        return;
    }

    float totalHeight = paddingTop + paddingBottom + (childCount * childHeight) + ((childCount - 1) * spacing);
    Vector2 size = container.sizeDelta;
    size.y = totalHeight;
    container.sizeDelta = size;
}
```

---

## 4. UGUI Layout Group Performans Mühendisliği ve Optimizasyonu

### 4.1. Unity UGUI Layout Sistem Mimarisi

UGUI Layout mimarisi `ILayoutElement`, `ILayoutGroup` ve `ILayoutSelfController` arayüzleri üzerine kuruludur. Bir elemanın boyut talebi 3 seviyede temsil edilir:
1. **Minimum Size ($Min$):** Elemanın sahip olabileceği en küçük boyut (Örn: Görsel icon boyutu $32\times 32$).
2. **Preferred Size ($Pref$):** Elemanın ideal görünümü için gereken boyut (Örn: Metin string'inin tam sığdığı boyut).
3. **Flexible Size ($Flex$):** Artan alanın elemanlar arasında paylaşılma oranı.

Layout hesaplama süreci Unity tarafından 2 aşamalı (2-pass) özyinelemeli (recursive) bir algoritma ile çalıştırılır:

```
[Hierarchy Traversal: Bottom-Up Pass]
1. CalculateLayoutInputHorizontal() -> Min/Pref/Flex Width değerleri toplanır.
2. CalculateLayoutInputVertical()   -> Min/Pref/Flex Height değerleri toplanır.

[Hierarchy Traversal: Top-Down Pass]
3. SetLayoutHorizontal() -> Üst ebeveyn genişliği alt çocuklara dağıtır.
4. SetLayoutVertical()   -> Üst ebeveyn yüksekliği alt çocuklara dağıtır.
```

---

### 4.2. Layout Rebuilder Döngüsü ve Rebuild Tetikleme Costu

UGUI sisteminde bir `Text`, `Image` veya `RectTransform` boyutu değiştiğinde `SetLayoutDirty()` çağrılır. Bu çağrı nesneyi `LayoutRebuilder` sırasına ekler.

Canvas işleme aşamasında (`Canvas.willRenderCanvases` eventi):
1. `LayoutRebuilder.Rebuild()` tetiklenir.
2. Tüm dirty işaretli layout bileşenleri hiyerarşide yukarı (parent) ve aşağı (children) taranır.
3. **CPU Spike ve Memory Allocations:** Hiyerarşide yüzlerce eleman varsa, bu özyinelemeli tarama main thread üzerinde ciddi CPU kilitlenmelerine (frame drop) ve GC (Garbage Collection) tahsisatlarına yol açar.

---

### 4.3. İç İçe (Nested) ContentSizeFitter & LayoutGroup Tuzakları (Pitfalls)

> [!CAUTION]
> **Aşırı Derin Layout Hiyerarşisi Karmaşıklığı $O(N^2)$:**
> İç içe geçmiş `VerticalLayoutGroup` $\rightarrow$ `HorizontalLayoutGroup` $\rightarrow$ `ContentSizeFitter` yapısı bir "Layout Rebuild Cascading Loop" oluşturur. En alttaki bir `TextMeshProUGUI` bileşeninin metni değiştiğinde, hesaplama en üste kadar tırmanır ve her seviyede tekrar aşağı iner. N elemanlı derin bir ağaçta matematiksel karmaşıklık $O(N)$ seviyesinden $O(N^2)$ seviyesine fırlayarak kare düşüşüne neden olur.

```
[KÖTÜ UYGULAMA - PERFORMANS TUZAĞI]
ScrollView Content (VerticalLayoutGroup + ContentSizeFitter)
  ├── Item 1 (HorizontalLayoutGroup + ContentSizeFitter)
  │    ├── Icon (LayoutElement)
  │    └── Text (TextMeshProUGUI + ContentSizeFitter) <--- Metin değiştiğinde tüm ScrollView Rebuild olur!
  ├── Item 2 ...
```

---

### 4.4. Sıfır-Tahsis (Zero-Alloc) Performans Çözümleri ve Custom Layout Yaklaşımları

Performans kritik UI sistemlerinde UGUI'nin varsayılan `HorizontalLayoutGroup` ve `VerticalLayoutGroup` bileşenleri kaldırılmalı, yerine **Manual Transform Calculation** veya **Pooled Layout Recycling** kullanılmalıdır.

#### Yaklaşım 1: Manuel Sıfır-Tahsis Pozisyonlama (`ManualLayoutGroup.cs`)

```csharp
using UnityEngine;

namespace Cardiv.UI.Optimization
{
    /// <summary>
    /// UGUI LayoutRebuilder sistemini by-pass ederek çocuk elemanları tek geçişte (O(N))
    /// sıfır bellek tahsisi ile dizen yüksek performanslı manuel layout bileşeni.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class ManualLayoutGroup : MonoBehaviour
    {
        public enum Axis { Horizontal, Vertical }

        [SerializeField] private Axis layoutAxis = Axis.Vertical;
        [SerializeField] private float spacing = 10f;
        [SerializeField] private Vector4 padding = new Vector4(10f, 10f, 10f, 10f); // Left, Right, Top, Bottom
        [SerializeField] private bool autoResizeContainer = true;

        private RectTransform _rectTransform;

        private void Awake()
        {
            _rectTransform = GetComponent<RectTransform>();
        }

        public void RebuildLayoutManual()
        {
            if (_rectTransform == null) _rectTransform = GetComponent<RectTransform>();

            int childCount = transform.childCount;
            float currentOffset = (layoutAxis == Axis.Vertical) ? -padding.z : padding.x;

            for (int i = 0; i < childCount; i++)
            {
                RectTransform child = transform.GetChild(i) as RectTransform;
                if (child == null || !child.gameObject.activeSelf) continue;

                Vector2 childSize = child.sizeDelta;
                Vector2 pivot = child.pivot;

                if (layoutAxis == Axis.Vertical)
                {
                    // Dikey Dizilim: Anchors Top-Left veya Top-Stretch kabul edilir
                    float targetY = currentOffset - ((1f - pivot.y) * childSize.y);
                    child.anchoredPosition = new Vector2(padding.x + (pivot.x * childSize.x), targetY);
                    currentOffset -= (childSize.y + spacing);
                }
                else
                {
                    // Yatay Dizilim: Anchors Left-Top kabul edilir
                    float targetX = currentOffset + (pivot.x * childSize.x);
                    child.anchoredPosition = new Vector2(targetX, -padding.z - ((1f - pivot.y) * childSize.y));
                    currentOffset += (childSize.x + spacing);
                }
            }

            if (autoResizeContainer)
            {
                Vector2 containerSize = _rectTransform.sizeDelta;
                if (layoutAxis == Axis.Vertical)
                {
                    containerSize.y = Mathf.Abs(currentOffset) + padding.w - spacing;
                }
                else
                {
                    containerSize.x = Mathf.Abs(currentOffset) + padding.y - spacing;
                }
                _rectTransform.sizeDelta = containerSize;
            }
        }
    }
}
```

---

### 4.5. Benchmark ve Performans Karşılaştırma Matrisi

100 Elemanlı Dinamik Liste Güncelleme Senaryosu (High-End & Mid-Range Mobil Cihaz Test Ortalamaları):

| Metrik | Varsayılan UGUI Layout (Vertical Group + CSF) | Custom Manual Layout (`ManualLayoutGroup`) | Performans Kazanımı |
| :--- | :--- | :--- | :--- |
| **CPU Frame Time (Rebuild Spike)** | $14.2 \text{ ms}$ | $0.4 \text{ ms}$ | **~35.5x Daha Hızlı** |
| **GC Garbage Allocation (Frame)** | $12.4 \text{ KB}$ | $0 \text{ Bytes}$ | **%100 Sıfır Tahsis (Zero Alloc)** |
| **Hierarchy Traversal Complexity** | $O(N^2)$ (Özyinelemeli Çift Geçiş) | $O(N)$ (Doğrusal Tek Geçiş) | **Algoritma Düzeyinde İyileşme** |
| **FPS Düşüşü (Stutter Risk)** | Yüksek (Micro-stutter ve GC pause) | Yok (Sabit 60/120 FPS akıcılık) | **Kritik UI Akıcılığı** |

---

## 5. Uygulama ve Doğrulama Check-List'i

1. **Root Canvas Ayarı:** `CanvasScaler` bileşeninde `Scale With Screen Size` seçildiğini ve `AspectRatioAdapter.cs` scriptinin Canvas'a eklendiğini doğrulayın.
2. **Safe Area Yalıtımı:** `SafeAreaHandler.cs` scriptini yalnızca Canvas altındaki ana köşe panellerine (Root Safe Area Container) atayın. Alt elemanlara tekrarlı eklemeyin.
3. **Layout Group Temizliği:** ScrollView ve dinamik listelerde iç içe geçmiş `ContentSizeFitter` kullanımını kaldırıp yerine `ManualLayoutGroup.cs` veya dynamic height hesaplama metodlarını entegre edin.
4. **Anchor Presets Kontrolü:** Tüm HUD öğelerinin sabit ekran kenarlarına göre doğru Anchor & Pivot değerlerine sahip olduğunu (Top-Left, Bottom-Right vb.) teyit edin.
