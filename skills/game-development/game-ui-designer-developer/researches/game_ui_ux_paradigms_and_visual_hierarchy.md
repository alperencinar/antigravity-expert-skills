# AAA Oyun UI Paradigmları, Görsel Hiyerarşi ve Tipografi Mühendisliği

> **Doküman Türü:** Mimari ve Teknik Araştırma Raporu  
> **Hedef Platform:** AAA & Mobile 3D Oyun Sistemleri (Unity / UGUI & UI Toolkit)  
> **Hazırlayan:** Senior Game UI/UX Research Specialist & Technical Art Architect  
> **Tarih:** 2026-07-24  
> **Dosya Konumu:** `docs/gameuidesigner/game_ui_ux_paradigms_and_visual_hierarchy.md`

---

## Özet ve Mimari Vizyon

Modern AAA oyun geliştirmede Kullanıcı Arayüzü (UI) ve Kullanıcı Deneyimi (UX), oyuncunun sanal evrenle kurduğu temel bilişsel köprüdür. Geleneksel 2D düzlemsel HUD katmanlarından, 3D oyun dünyasına entegre diegetik ve mekânsal (spatial) arayüzlere geçiş; bellek yönetimi, render komut yükü (draw call budget), renk erişilebilirliği ve tipografi mühendisliği alanlarında karmaşık mühendislik zorluklarını beraberinde getirmektedir.

Bu doküman; **UI Paradigmları**, **Renk Teorisi & Palet Mühendisliği** ve **Tipografi & Font Mühendisliği** olmak üzere 3 ana sütunda teknik standartları, matematiksel formülleri, C# script mimarilerini ve HLSL shader çözümlerini kapsar.

---

## 1. AAA Game UI Paradigmları Derin İnceleme

Oyun UI mimarisinde temel sınıflandırma, **Erik Fagerholt ve Lorens Bach (2009)** tarafından ortaya koyulan matrise dayanır. Arayüz elemanları iki eksende değerlendirilir:
1. **Oyun Hikayesine (Diegesis/Lore) Ait mi?** (Oyun karakterleri arayüzü görüyor/duyuyor mu?)
2. **Oyunun 3D Uzamında (Spatial World) Yer Alıyor mu?** (Fiziksel 3D dünyada mı, ekran düzleminde mi?)

```
                     GEOMETRİK UZAMDA MI? (3D World Space)
                             EVET                     HAYIR
                   +------------------------+------------------------+
             EVET  |      DIEGETIC UI       |        META UI         |
KARAKTER           |  (Dead Space RIG,      |  (GTA V Akıllı Telefon,|
ALGILIYOR MU?      |   Cyberpunk Ammo Mesh) |   Ekran Çamur/Kan)     |
(Diegetic Scope)   +------------------------+------------------------+
             HAYIR |       SPATIAL UI       |      NON-DIEGETIC      |
                   |  (Düşman Can Barı,     |  (Geleneksel HUD,      |
                   |   Hedef İşaretçileri)  |   Skor Tablosu)        |
                   +------------------------+------------------------+
```

### 1.1 Diegetic UI (Dünya İçi Arayüzler)

#### Tanım ve Daldırma (Immersion) Mekaniği
Diegetik UI, oyun dünyası ve hikayesi içerisinde fiziksel varlığı olan, oyun karakterlerinin de oyuncu gibi görebildiği ve etkileşime geçebildiği arayüzlerdir. Oyuncunun dikkatini ekrandaki 2D HUD simgelerinden çıkarıp 3D sahnenin merkezine çekerek "daldırma" (immersion) etkisini en üst düzeye çıkarır.

*   **Dead Space (RIG Health Bar):** Isaac Clarke'ın zırhının omurgasında yer alan segmented LED ışık çubuğu ve sırtındaki stasis göstergesi. Karakterin canı azaldığında zırhtaki LED renk değiştirir ve çubuk kısalır.
*   **Cyberpunk 2077:** Silahların üzerine entegre holografik mermi sayaçları, akıllı göz implanti (Kiroshi Optics) arayüzlerinin silah retiküllerine diegetik olarak yansıtılması.
*   **The Division:** Karakterin omuz çantasından yansıtılan holografik 3D harita ve envanter sistemi.

#### Unity C# Uygulama Mimarisi: Dynamic Material Property Block (MPB)
Diegetik UI elemanları Canvas UI yerine doğrudan 3D Mesh Material parametrelerini güncelleyerek çalışmalıdır. `MaterialPropertyBlock` kullanımı, GPU instancing yeteneğini bozmadan ve bellek allocation'ı yaratmadan hızlı renk/oran değişimleri sağlar.

```csharp
using UnityEngine;

[DisallowMultipleComponent]
public class DiegeticHealthMesh : MonoBehaviour
{
    [SerializeField] private Renderer meshRenderer;
    [SerializeField] private string colorPropName = "_EmissionColor";
    [SerializeField] private string fillPropName = "_HealthFill";
    
    [GradientUsage(true)]
    [SerializeField] private Gradient healthGradient;

    private MaterialPropertyBlock _mpb;
    private int _colorPropId;
    private int _fillPropId;

    private void Awake()
    {
        _mpb = new MaterialPropertyBlock();
        _colorPropId = Shader.PropertyToID(colorPropName);
        _fillPropId = Shader.PropertyToID(fillPropName);

        if (meshRenderer == null)
            meshRenderer = GetComponent<Renderer>();
    }

    public void UpdateHealth(float currentHealth, float maxHealth)
    {
        float fillRatio = Mathf.Clamp01(currentHealth / maxHealth);
        Color targetColor = healthGradient.Evaluate(fillRatio);

        meshRenderer.GetPropertyBlock(_mpb);
        _mpb.SetFloat(_fillPropId, fillRatio);
        _mpb.SetColor(_colorPropId, targetColor);
        meshRenderer.SetPropertyBlock(_mpb);
    }
}
```

---

### 1.2 Non-Diegetic UI (Geleneksel HUD Katmanları)

#### Tanım ve Performans Metrikleri
Non-Diegetic UI, oyun evreninde var olmayan, karakterlerin algılayamadığı, doğrudan oyuncunun bilgilendirilmesi için ekrana 2D overlay olarak çizdirilen elemanlardır (Mini-map, hız göstergesi, crosshair, skor panosu).

#### Canvas Architecture & Draw Call Optimization
Unity UGUI veya UI Toolkit mimarisinde Non-Diegetic UI performansını belirleyen ana unsur **Canvas Rebuild** maliyetidir.
*   **Statik ve Dinamik Canvas Ayrımı:** Her karede değişen can barları veya hız göstergeleri ile hiç değişmeyen çerçeveler ve ikonlar ayrı Canvas objelerine bölünmelidir. Dinamik bir elemanda `SetVerticesDirty()` çağrıldığında, o Canvas altındaki *tüm* mesh re-batch edilir.
*   **Raycast Target Optimization:** Etkileşimi olmayan `Text` veya `Image` bileşenlerinde `Raycast Target` opsiyonu kapatılmalıdır. Aksi halde graphic raycaster her tıklamada CPU tarafında bounding-box testleri yürütür.

---

### 1.3 Spatial UI (3D Dünyaya Çıpalı Arayüzler)

#### Tanım ve Koordinat Dönüşüm Mühendisliği
Spatial UI, oyun karakterinin algılamadığı ancak 3D dünya uzamında belirli obje/karakter koordinatlarına sabitlenen arayüzlerdir. Örneğin: Düşman tepesindeki 3D Can Barları, Quest İkonları, World Indicators.

Spatial UI için 2 farklı teknik yaklaşım mevcuttur:
1.  **World Space Canvas:** UI objesini 3D dünyada konumlandırmak (Yüksek canvas re-batch maliyeti, fazla GPU DrawCall).
2.  **Screen Space - Overlay / Camera Canvas + WorldToScreenPoint Math:** 3D objenin dünya pozisyonunu Matematiksel olarak ekran koordinatına çevirip tek bir 2D Overlay Canvas üzerinde yönetmek (**Önerilen Standart**).

#### Spatial UI Matematiksel Formülü: Off-Screen Clamping & Frustum Test
Bir 3D hedef noktası \( P_{world} = (x, y, z) \) verildiğinde, kamera görünüm matrisi \( V \) ve projeksiyon matrisi \( P \) ile klip uzayı koordinatı \( P_{clip} \) hesaplanır:

$$P_{clip} = P \times V \times P_{world}$$

Ekran koordinatı \( P_{screen} \):

$$X_{screen} = \frac{W}{2} \left(1 + \frac{P_{clip}.x}{P_{clip}.w}\right), \quad Y_{screen} = \frac{H}{2} \left(1 + \frac{P_{clip}.y}{P_{clip}.w}\right)$$

Eğer \( P_{clip}.w < 0 \) ise obje kameranın arkasındadır. Ekran sınırlarına kelepçeleme (Off-screen Clamping) için merkez odaklı açısal vektör hesaplaması yapılır:

$$\vec{V}_{center} = P_{screen} - P_{center}$$

$$\theta = \arctan2(V_y, V_x)$$

#### Production-Grade C# Spatial UI Manager

```csharp
using UnityEngine;
using UnityEngine.UI;

public class SpatialMarkerUI : MonoBehaviour
{
    [Header("Target & Camera")]
    [SerializeField] private Transform target3D;
    [SerializeField] private Vector3 worldOffset = new Vector3(0, 2.0f, 0);
    [SerializeField] private Camera mainCamera;

    [Header("UI Elements")]
    [SerializeField] private RectTransform markerRect;
    [SerializeField] private CanvasGroup canvasGroup;
    [SerializeField] private RectTransform offscreenArrow;

    [Header("Screen Edge Padding")]
    [SerializeField] private float edgeMarginPixels = 50f;

    private Transform _camTransform;

    private void Start()
    {
        if (mainCamera == null) mainCamera = Camera.main;
        _camTransform = mainCamera.transform;
    }

    private void LateUpdate()
    {
        if (target3D == null || markerRect == null) return;

        Vector3 targetWorldPos = target3D.position + worldOffset;
        Vector3 screenPos = mainCamera.WorldToScreenPoint(targetWorldPos);

        // Obje kameranın arkasında mı?
        bool isBehind = Vector3.Dot(targetWorldPos - _camTransform.position, _camTransform.forward) <= 0;

        Vector2 screenCenter = new Vector2(Screen.width * 0.5f, Screen.height * 0.5f);
        Vector2 screenBounds = screenCenter - new Vector2(edgeMarginPixels, edgeMarginPixels);

        if (isBehind)
        {
            screenPos.x = Screen.width - screenPos.x;
            screenPos.y = Screen.height - screenPos.y;
        }

        Vector2 projectedPos = new Vector2(screenPos.x, screenPos.y) - screenCenter;
        bool isOffscreen = isBehind || 
                           Mathf.Abs(projectedPos.x) > screenBounds.x || 
                           Mathf.Abs(projectedPos.y) > screenBounds.y;

        if (isOffscreen)
        {
            // Sınırlara kelepçeleme (Clamp to Screen Edge)
            float angle = Mathf.Atan2(projectedPos.y, projectedPos.x);
            float slope = Mathf.Tan(angle);

            if (Mathf.Abs(projectedPos.x) * screenBounds.y > Mathf.Abs(projectedPos.y) * screenBounds.x)
            {
                // Dikey kenara çarpar
                float xSign = Mathf.Sign(projectedPos.x);
                projectedPos.x = xSign * screenBounds.x;
                projectedPos.y = xSign * screenBounds.x * slope;
            }
            else
            {
                // Yatay kenara çarpar
                float ySign = Mathf.Sign(projectedPos.y);
                projectedPos.y = ySign * screenBounds.y;
                projectedPos.x = ySign * screenBounds.y / slope;
            }

            if (offscreenArrow != null)
            {
                offscreenArrow.gameObject.SetActive(true);
                offscreenArrow.rotation = Quaternion.Euler(0, 0, angle * Mathf.Rad2Deg - 90f);
            }
        }
        else
        {
            if (offscreenArrow != null) offscreenArrow.gameObject.SetActive(false);
        }

        markerRect.position = projectedPos + screenCenter;
        canvasGroup.alpha = isOffscreen ? 0.7f : 1.0f;
    }
}
```

---

### 1.4 Meta UI (Oyun İçi Sanal Ekranlar ve Dördüncü Duvar Arayüzleri)

#### Tanım ve Kullanım Alanları
Meta UI, oyun hikayesine dahil olan ancak oyuncu için 2D/3D düzlemleri kıran sanal cihazlar veya doğrudan lens efektleridir.
*   **GTA V / Cyberpunk 2077 Akıllı Telefonları:** Karakter telefonunu çıkardığında telefon ekranının bir Render Texture olarak çizilmesi ve oyuncunun bunu manipüle etmesi.
*   **Lens Efektleri (Fourth Wall Breaks):** *Splinter Cell: Conviction* veya *Call of Duty* oyunlarında karakter yaralandığında ekrana sıçrayan kan/çamur damlaları, visor vizöründeki nemlenme veya ekran çatlaması.

#### Render Texture UI Pipeline
Meta UI ekranları (örneğin araç içi bilgisayar ekranı veya akıllı telefon), ikincil bir UI Canvas'ın `Render Texture` hedefine çizdirilmesi ve bu texture'ın 3D nesnenin `Unlit/PBR Material` dokusu olarak atanmasıyla oluşturulur.

---

## 2. Color Theory & Palette Systems in Games

### 2.1 Erişilebilirlik ve Kontrast Oranları (Accessibility & WCAG 2.1)

Oyun içi arayüzlerde okunabilirlik, dinamik olarak değişen 3D arka plan ışık koşullarından (aydınlık gündüz sahnelerinden karanlık mağaralara) doğrudan etkilenir. Standardize edilmiş **WCAG 2.1 AAA** seviyesi, metin ile arka plan arasında en az **7:1** (küçük metinler) ve **4.5:1** (büyük metinler) kontrast oranı gerektirir.

#### Lümine (Luminance) ve Kontrast Formülleri
sRGB renk uzayındaki lineer göreceli lümine \( L \):

$$L = 0.2126 \times R_{lin} + 0.7152 \times G_{lin} + 0.0722 \times B_{lin}$$

Burada \( C_{lin} \) dönüşümü gamma düzeltmesine dayanır:

$$C_{lin} = \begin{cases} \frac{C}{12.92}, & C \le 0.04045 \\ \left(\frac{C + 0.055}{1.055}\right)^{2.4}, & C > 0.04045 \end{cases}$$

İki renk arasındaki kontrast oranı \( CR \):

$$CR = \frac{L_1 + 0.05}{L_2 + 0.05} \quad (L_1 > L_2)$$

#### Dinamik Arka Plan Kontrast Kontrolörü C# Scripti
Aşağıdaki C# sınıfı, UI arkasındaki alanın parlaklığını ölçerek UI metin rengini otomatik olarak Siyah veya Beyaza adapte eder.

```csharp
using UnityEngine;
using TMPro;

public class DynamicAdaptiveContrast : MonoBehaviour
{
    [SerializeField] private TextMeshProUGUI targetText;
    [SerializeField] private Camera uiCamera;
    [SerializeField] private Color lightTextColor = Color.white;
    [SerializeField] private Color darkTextColor = new Color(0.05f, 0.05f, 0.05f, 1f);

    public static float CalculateLuminance(Color color)
    {
        float R = (color.r <= 0.04045f) ? color.r / 12.92f : Mathf.Pow((color.r + 0.055f) / 1.055f, 2.4f);
        float G = (color.g <= 0.04045f) ? color.g / 12.92f : Mathf.Pow((color.g + 0.055f) / 1.055f, 2.4f);
        float B = (color.b <= 0.04045f) ? color.b / 12.92f : Mathf.Pow((color.b + 0.055f) / 1.055f, 2.4f);

        return 0.2126f * R + 0.7152f * G + 0.0722f * B;
    }

    public static float CalculateContrastRatio(Color color1, Color color2)
    {
        float l1 = CalculateLuminance(color1);
        float l2 = CalculateLuminance(color2);

        float brightest = Mathf.Max(l1, l2);
        float darkest = Mathf.Min(l1, l2);

        return (brightest + 0.05f) / (darkest + 0.05f);
    }

    public void AdaptToBackgroundColor(Color sampledBackgroundColor)
    {
        float bgLuminance = CalculateLuminance(sampledBackgroundColor);
        
        // Eğer arka plan aydınlıksa koyu metin, karanlıksa açık metin seç
        if (bgLuminance > 0.45f)
        {
            targetText.color = darkTextColor;
        }
        else
        {
            targetText.color = lightTextColor;
        }
    }
}
```

---

### 2.2 Renk Körlüğü Paletleri ve Matris Matematiği (Colorblind Modes)

Oyun nüfusunun yaklaşık %8'i erkeklerde ve %0.5'i kadınlarda renk körlüğü (Daltonizm) taşımaktadır. AAA UI tasarımında 3 ana renk körlüğü tipi için renk matrisi dönüşümleri desteklenmelidir:

1.  **Deuteranopia:** Yeşil koni eksikliği (Kırmızı-Yeşil ayırımı zor).
2.  **Protanopia:** Kırmızı koni eksikliği (Kırmızı renkler parlaklığını kaybeder).
3.  **Tritanopia:** Mavi koni eksikliği (Mavi-Sarı ayırımı zor, nadir).

```
               LMS KONİ HASSASİYETİ VE RENK KÖRÜĞÜ TİPLERİ
  +------------------+-----------------------+------------------------+
  | Renk Körlüğü     | Eksik / Hatalı Koni   | Kritik Karışan Renkler |
  +------------------+-----------------------+------------------------+
  | Protanopia       | L-Koni (Long Wave/Red)| Kırmızı -> Siyah/Kahve |
  | Deuteranopia     | M-Koni (Medium/Green) | Yeşil -> Bej/Gri       |
  | Tritanopia       | S-Koni (Short/Blue)   | Mavi -> Yeşil, Sarı->Pembe|
  +------------------+-----------------------+------------------------+
```

#### Colorblind Simulation Matrix Transformation
RGB vektörü \(\mathbf{C} = [R, G, B]^T\), renk körlüğü simülasyon/düzeltme matrisi \(\mathbf{M}_{cb}\) ile çarpılarak yeni dönüştürülmüş renk elde edilir:

$$\begin{bmatrix} R' \\ G' \\ B' \end{bmatrix} = \mathbf{M}_{cb} \times \begin{bmatrix} R \\ G \\ B \end{bmatrix}$$

##### Deuteranopia Simülasyon Matrisi:

$$\mathbf{M}_{deut} = \begin{bmatrix} 0.625 & 0.375 & 0.0 \\ 0.70 & 0.30 & 0.0 \\ 0.0 & 0.30 & 0.70 \end{bmatrix}$$

##### Protanopia Simülasyon Matrisi:

$$\mathbf{M}_{prot} = \begin{bmatrix} 0.56667 & 0.43333 & 0.0 \\ 0.55833 & 0.44167 & 0.0 \\ 0.0 & 0.24167 & 0.75833 \end{bmatrix}$$

##### Tritanopia Simülasyon Matrisi:

$$\mathbf{M}_{trit} = \begin{bmatrix} 0.95 & 0.05 & 0.0 \\ 0.0 & 0.43333 & 0.56667 \\ 0.0 & 0.475 & 0.525 \end{bmatrix}$$

#### Colorblind Simulation HLSL UI Shader Pass

```hlsl
Shader "UI/ColorblindFilter"
{
    Properties
    {
        [HideInInspector] _MainTex ("Texture", 2D) = "white" {}
        _Mode ("Colorblind Mode (0:None, 1:Deut, 2:Prot, 3:Trit)", Int) = 0
    }

    SubShader
    {
        Tags { "Queue"="Transparent" "IgnoreProjector"="True" "RenderType"="Transparent" }
        Cull Off ZWrite Off Blend SrcAlpha OneMinusSrcAlpha

        Pass
        {
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"

            struct appdata_t
            {
                float4 vertex : POSITION;
                float2 texcoord : TEXCOORD0;
                float4 color : COLOR;
            };

            struct v2f
            {
                float4 vertex : SV_POSITION;
                float2 texcoord : TEXCOORD0;
                float4 color : COLOR;
            };

            sampler2D _MainTex;
            int _Mode;

            v2f vert(appdata_t v)
            {
                v2f o;
                o.vertex = UnityObjectToClipPos(v.vertex);
                o.texcoord = v.texcoord;
                o.color = v.color;
                return o;
            }

            float3 ApplyColorblindMatrix(float3 rgb, int mode)
            {
                // Mode 1: Deuteranopia
                if (mode == 1)
                {
                    float3x3 deutMat = float3x3(
                        0.625, 0.375, 0.0,
                        0.700, 0.300, 0.0,
                        0.000, 0.300, 0.700
                    );
                    return mul(deutMat, rgb);
                }
                // Mode 2: Protanopia
                else if (mode == 2)
                {
                    float3x3 protMat = float3x3(
                        0.56667, 0.43333, 0.0,
                        0.55833, 0.44167, 0.0,
                        0.00000, 0.24167, 0.75833
                    );
                    return mul(protMat, rgb);
                }
                // Mode 3: Tritanopia
                else if (mode == 3)
                {
                    float3x3 tritMat = float3x3(
                        0.950, 0.050, 0.000,
                        0.000, 0.43333, 0.56667,
                        0.000, 0.475, 0.525
                    );
                    return mul(tritMat, rgb);
                }
                return rgb;
            }

            fixed4 frag(v2f i) : SV_Target
            {
                fixed4 col = tex2D(_MainTex, i.texcoord) * i.color;
                col.rgb = ApplyColorblindMatrix(col.rgb, _Mode);
                return col;
            }
            ENDHLSL
        }
    }
}
```

#### AAA Erişilebilir Palet Standartları Tablosu

| Rol / Kullanım Amacı | Standart (Normal) Hex | Protanopia / Deuteranopia Güvenli Hex | Tritanopia Güvenli Hex |
| :--- | :--- | :--- | :--- |
| **Düşman / Kritik Tehlike** | `#FF2A2A` (Kırmızı) | `#D55E00` (Vermillion / Koyu Turuncu) | `#FF0055` (Parlak Macenta) |
| **Müttefik / Şifa / Başarı**| `#00E676` (Yeşil) | `#0072B2` (Saf Mavi) | `#009E73` (Cam Göbeği Yeşil) |
| **Etkileşim / Görev / Loot**| `#FFD700` (Altın Sarı) | `#F0E442` (Açık Limon Sarı) | `#E69F00` (Amber Sarı) |
| **Nötr / Statik UI Pasif**  | `#808080` (Gri) | `#999999` (Açık Nötr Gri) | `#666666` (Koyu Nötr Gri) |

---

### 2.3 Görsel Ağırlık Hiyerarşisi ve Odak Yönetimi

Oyuncunun gözünü ekrandaki kritik bilgiye yönlendirmek için **Görsel Ağırlık Hiyerarşisi (Visual Weight Hierarchy)** kullanılır. Görsel ağırlık 4 ana bileşenin kombinasyonu ile oluşturulur:

1.  **Lüminesans ve Kontrast:** Yüksek parlaklığa sahip elemanlar odak çeker.
2.  **Renk Doygunluğu (Saturation):** Doygun (vibrant) renkler nötr tonlara göre daha "ağır" görünür.
3.  **Ölçek ve Alan (Scale & Mass):** Ekranda kaplanan alan doğrudan önem derecesini belirler.
4.  **Hareket Frekansı (Motion Frequency):** Animasyonlu, puls yapan veya titreşen elemanlar insan beyninde (periferik görüş) anında öncelik kazanır.

```
       GÖRSEL AĞIRLIK PİRAMİDİ (Visual Weight Pyramid)
                         /\
                        /  \  [SEVİYE 1: Kritik Tehdit & Can < 10%]
                       /    \  (Pulsating Crimson Red + Scale Lock)
                      /------\
                     /        \  [SEVİYE 2: Hedef & Etkileşim]
                    /          \  (High Saturation Amber / Blue)
                   /------------\
                  /              \  [SEVİYE 3: İkincil HUD]
                 /                \  (Low Saturation Gray/White)
                /------------------\
               /                    \  [SEVİYE 4: Arka Plan Panelleri]
              /                      \  (Dark Tint 30% Alpha Blur)
             +------------------------+
```

---

### 2.4 Dark / Light Tema Tasarım Token Sistemleri (Design Tokens)

Modern AAA oyun UI geliştirmede renkler ve stiller hardcoded olarak bileşenlere verilmez. bunun yerine **Design Token System** mimarisi uygulanır.

#### ScriptableObject UI Theme System C# Kodu

```csharp
using System;
using UnityEngine;

[CreateAssetMenu(fileName = "UIThemeToken", menuName = "UI/Theme Token Asset")]
public class UIThemeTokenAsset : ScriptableObject
{
    [System.Serializable]
    public struct ColorTokens
    {
        public Color primaryBackground;
        public Color secondaryBackground;
        public Color accentPrimary;
        public Color textPrimary;
        public Color textSecondary;
        public Color warningDanger;
        public Color successAlly;
    }

    public ColorTokens darkTheme;
    public ColorTokens lightTheme;
    public ColorTokens colorblindTheme;
}

public class UIThemeManager : MonoBehaviour
{
    public enum ThemeMode { Dark, Light, Colorblind }

    public static UIThemeManager Instance { get; private set; }
    
    [SerializeField] private UIThemeTokenAsset themeAsset;
    [SerializeField] private ThemeMode currentMode = ThemeMode.Dark;

    public event Action OnThemeChanged;

    private void Awake()
    {
        if (Instance != null && Instance != this) Destroy(gameObject);
        else Instance = this;
    }

    public UIThemeTokenAsset.ColorTokens GetCurrentTheme()
    {
        return currentMode switch
        {
            ThemeMode.Light => themeAsset.lightTheme,
            ThemeMode.Colorblind => themeAsset.colorblindTheme,
            _ => themeAsset.darkTheme
        };
    }

    public void SwitchTheme(ThemeMode newMode)
    {
        currentMode = newMode;
        OnThemeChanged?.Invoke();
    }
}
```

---

## 3. Typography & Font Engineering

### 3.1 SDF ve MSDF (Signed Distance Field) Renderer Mekanizmaları

Geleneksel raster fontlar (Bitmap Fonts), yüksek çözünürlüklü 4K veya mobil ekranlarda ölçeklendiğinde pikselleşme ve bulanıklaşma yaşarlar. Modern oyun motorlarında (Unity TextMeshPro / Unreal Slate) **Signed Distance Field (SDF)** ve **Multi-channel SDF (MSDF)** rendering standarttır.

#### SDF Çalışma Prensibi ve Matematiksel Formülü
SDF atlasında her piksel, fontun karakter sınırına (edge/contour) olan en yakın uzaklığı saklar. Mesafe \( d \), karakterin içindeyse pozitif, dışındaysa negatiftir:

$$f(p) = \begin{cases} +d(p, \partial \Omega), & p \in \text{İç Alan} \\ 0, & p \in \text{Sınır (Contour)} \\ -d(p, \partial \Omega), & p \in \text{Dış Alan} \end{cases}$$

Shader piksel çizerken uzaklık değerini test eder:

$$\text{Alpha} = \text{smoothstep}\left(0.5 - \text{smoothing}, 0.5 + \text{smoothing}, \text{SDFValue}\right)$$

#### MSDF (Multi-Channel SDF) Avantajı
Tek kanallı (Single-channel) SDF, karakterin keskin köşe (sharp corners) detaylarında yuvarlanma (rounding artifact) sorunu yaşar. **MSDF**, RGB 3 farklı kanala farklı yön türevlerini saklayarak ultra keskin köşeler oluşturur.

```
       SINGLE-CHANNEL SDF vs MULTI-CHANNEL SDF (MSDF)
  +--------------------------------+--------------------------------+
  | Single-Channel SDF (1 Channel) | Multi-Channel MSDF (RGB 3 Ch)  |
  +--------------------------------+--------------------------------+
  | Soft/Rounded Corners           | Ultra-Sharp Sharp Corners      |
  | Düşük Bellek (Grayscale Atlas) | 3-Katı Bellek (RGB Atlas)      |
  | Büyük Başlıklar için Yetersiz  | AAA Tipografi & Logo İçin İdeal|
  +--------------------------------+--------------------------------+
```

#### Atlas Generation Parameters & Shader Performance Rules
1.  **Padding:** Font atlasındaki karakterler arası güvenlik marjıdır. Outlining (Dış çizgi) veya Glow (Işıma) efektleri verilecekse Padding en az **8-12px** ayarlanmalıdır. Aksi halde karakter kenarlarında "bleeding" oluşur.
2.  **Sampling Point Size:** Statik atlas için varsayılan **72pt** veya **90pt** seçilmelidir.
3.  **Atlas Resolution:** AAA oyunlarda ana karakter kümesi için **2048x2048 (4MB)** atlaslar tercih edilir.

---

### 3.2 Çoklu Çözünürlük ve Dinamik Ölçekleme (Dynamic Text Scaling)

Mobil cihazlardan (örn. 720p / 1080p) 4K TV/Monitör ortamına kadar tutarlı okunabilirlik sağlamak için `Canvas Scaler` yapılandırması kritik öneme sahiptir.

#### Canvas Scaler Reference Resolution Formülü
Canvas Scaler `Scale With Screen Size` modundayken ölçekleme faktörü \( S \):

$$S = \left(\frac{W_{screen}}{W_{ref}}\right)^{1 - m} \times \left(\frac{H_{screen}}{H_{ref}}\right)^m$$

Burada \( m \in [0, 1] \) `Match Width Or Height` katsayısıdır. Yatay oyunlarda (Landscape Mode) \( m = 0.5 \) veya \( m = 1.0 \) (Height Match) seçilmelidir.

#### Layout Rebuild Maliyetini Önleme Rules
*   TextMeshPro bileşenlerinde `Auto Size` seçeneği **zorunlu olmadıkça kapatılmalıdır**. `Auto Size` her karede metin sığdırma hesabı yürüterek CPU tarafında string layout parse yükü yaratır.
*   Metin değişiklikleri esnasında `LayoutRebuilder.ForceRebuildLayoutImmediate()` çağrısı zincirleme olarak tüm ata Canvas elementlerini re-layout eder. Bu işlem yalnızca UI penceresi açıldığında 1 defa çalıştırılmalıdır.

---

### 3.3 Lokalizasyon Font Mühendisliği (CJK, Arabic RTL, Cyrillic)

Çok dilli AAA projelerinde font yönetimi bellek ve alfabe karmaşıklığı nedeniyle 3 ana zorluk barındırır.

#### 1. Fallback Font Chain Mimarisi
İngilizce fontlar genellikle CJK (Çince, Japonca, Korece) veya Arapça karakterleri barındırmaz. TextMeshPro `Fallback Font Assets` listesi hiyerarşik olarak kurgulanmalıdır:

```
[ Primary Font Asset (Roboto-Bold.asset) ]  ---> (Latin, Numbers, Basic Symbols)
                   |
                   v (Missing Glyph)
[ Secondary Fallback (NotoSansCJK-Regular.asset) ] ---> (Kanji, Hanzi, Hangul)
                   |
                   v (Missing Glyph)
[ Tertiary Fallback (NotoSansArabic-Regular.asset) ] ---> (Arabic Ligatures)
```

#### 2. Arapça ve İbranice RTL (Right-to-Left) Text Shaping
Arapça kelimeler harflerin başlangıç, orta ve son konumlarına göre bitişik (ligature) yazılır. TextMeshPro tek başına doğru glyph bağlamasını yapamaz; `Arabic Support Plugin` veya `GNU FriBidi / HarfBuzz` entegrasyonu ile metin ilk önce **BiDi (Bidirectional)** biçimlendirmesinden geçirilip ardından TMP'ye aktarılmalıdır.

#### 3. CJK Karakter Atölyesi Yönetimi (Dynamic Atlas vs Static Glyphs)
Geleneksel Latin alfabesinde 256 karakter yeterliyken, Çince (Hanzi) alfabesinde 20,000+ karakter mevcuttur.
*   **Yanlış Yaklaşım:** 20.000 karakterin hepsini statik atlasa aktarmak (Bellek 100MB+ olur).
*   **Doğru Yaklaşım (Dynamic Atlas):** TextMeshPro `Dynamic Font` modunda başlatılır. Yalnızca ekranda beliren CJK glifleri çalışma zamanında (runtime) boş 2048x2048 atlas sayfasına çizilir.

---

### 3.4 Kerning, Tracking ve Dinamik 3D Arka Plan Okunabilirliği

Dinamik 3D sahnelerin üstüne bindirilen metinlerde (özellikle hızlı hareket eden aksiyon ve yarış oyunlarında) okunabilirliği korumak için tipografik kontur teknikleri şarttır.

```
                  DİNAMİK OKUNABİLİRLİK TEKNİKLERİ
  +-----------------------+---------------------------------------+
  | Teknik                | Açıklama ve Performans Etkisi         |
  +-----------------------+---------------------------------------+
  | Multi-pass SDF Outline| Ekstra GPU geçişi ile kalın dış çizgi |
  | Drop Shadow (Gölge)   | Karakterin altına 2D ofsetli koyu kopyası|
  | Backdrop Blur Shader  | UI panelinin arkasını dikey blurlama  |
  | Dynamic Vignette      | Ekran kenarlarına gradyan karartma    |
  +-----------------------+---------------------------------------+
```

#### C# Dynamic TMP Font Customizer Script
Aşağıdaki C# scripti, arkadaki sahne parlaklığına veya mesafeye göre TextMeshPro materyalinin SDF Outline (Dış Çizgi) kalınlığını dinamik olarak ayarlar.

```csharp
using UnityEngine;
using TMPro;

[RequireComponent(typeof(TextMeshProUGUI))]
public class DynamicTMPLegibilityController : MonoBehaviour
{
    [SerializeField] private TextMeshProUGUI tmpComponent;
    [Range(0f, 1f)] [SerializeField] private float defaultOutlineThickness = 0.2f;
    [Range(0f, 1f)] [SerializeField] private float highContrastOutlineThickness = 0.6f;
    [SerializeField] private Color outlineColor = Color.black;

    private Material _localMaterialInstance;

    private void Awake()
    {
        if (tmpComponent == null) tmpComponent = GetComponent<TextMeshProUGUI>();

        // Material kopyası oluşturarak diğer metinleri etkilemesini önlüyoruz
        _localMaterialInstance = new Material(tmpComponent.fontMaterial);
        tmpComponent.fontMaterial = _localMaterialInstance;
        
        _localMaterialInstance.SetColor(ShaderUtilities.ID_OutlineColor, outlineColor);
    }

    public void SetHighContrastMode(bool enableHighContrast)
    {
        float targetThickness = enableHighContrast ? highContrastOutlineThickness : defaultOutlineThickness;
        _localMaterialInstance.SetFloat(ShaderUtilities.ID_OutlineWidth, targetThickness);
    }

    private void OnDestroy()
    {
        if (_localMaterialInstance != null)
        {
            Destroy(_localMaterialInstance);
        }
    }
}
```

---

## 4. Özet & AAA UI/UX Teknik Standartlar Checklist

AAA seviyesinde üretim yapacak bir oyun UI/UX ekibinin doğrulaması gereken mimari ve teknik kontrol listesi:

### 🚀 Performans Checklist
* [ ] **Canvas Splitting:** Statik ve dinamik UI elemanları tamamen ayrı Canvas'lara bölündü mü?
* [ ] **Raycast Optimization:** Tıklanmayan tüm `Image` ve `Text` nesnelerinde `Raycast Target = false` yapıldı mı?
* [ ] **Layout Rebuild Limit:** `LayoutGroup` (Horizontal/Vertical) kullanımı minimize edildi mi? Dynamic layout rebuild'ler saniyede 1 kereden az mı?
* [ ] **Font Atlas Budget:** Statik font atlasları 2048x2048 boyutunu geçmiyor mu? CJK dilleri için Dynamic Atlas aktifleştirildi mi?

### 👁️ Görsel Hiyerarşı & Renk Checklist
* [ ] **WCAG Kontrast Testi:** Tüm kritik bilgilendirme metinleri arkasındaki 3D sahneye karşı en az **4.5:1** kontrast oranını koruyor mu?
* [ ] **Colorblind Matrix:** Oyunda Deuteranopia, Protanopia ve Tritanopia modları için HLSL matris post-process testi yapıldı mı?
* [ ] **Gameplay Color Logic:** Düşman (Kırmızı/Vermillion), Müttefik (Mavi/Yeşil) ve Etkileşim (Altın/Sarı) renk kodları oyun genelinde tutarlı mı?

### 🌐 Tipografi & Lokalizasyon Checklist
* [ ] **MSDF / SDF Texturing:** Metinler pikselleşmeyi önlemek için TMP SDF/MSDF shader'ları ile mi işleniyor?
* [ ] **Fallback Chain:** CJK ve Kiril alfabeleri için eksiksiz Fallback Font Hiyerarşisi tanımlandı mı?
* [ ] **RTL Text Shaping:** Arapça/İbranice metinler için BiDi ve Ligature şekillendiriciler aktif mi?
