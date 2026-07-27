# Mobil Oyun UI/UX Tasarım Sistemleri, Topoloji ve Unity Optimizasyon Raporu

Bu araştırma dökümanı, modern mobil oyunlarda (özellikle Subway Surfers, Brawl Stars ve Blocky Highway gibi başarılı yapımlar özelinde) arayüz tasarım teorilerini, Figma-Unity varlık aktarım hatlarını ve Unity motoru içerisinde teknik UI (uGUI ve UI Toolkit) performans optimizasyon yöntemlerini analiz etmektedir.

---

## 1. Özet (Executive Summary)
Mobil oyun arayüzleri, kısıtlı ekran alanında oyuncunun bilişsel yükünü azaltırken, saniyelerle ölçülen oyun döngülerinde en yüksek duyusal geri bildirimi ("juice") sağlamak üzere tasarlanmalıdır. Sektör standardı pratikler; görsel hiyerarşi kuralları, 60-30-10 renk dağılımı ve 9-slicing gibi hafıza dostu tekniklerin kullanımını zorunlu kılmaktadır. Unity ekosisteminde uGUI hala aktif olarak güncellenmekte ve desteklenmektedir. Ancak performansın korunması, Canvas bölünmesi (Static/Dynamic Canvas) ve CPU yükü yüksek olan Layout Group'ların doğru yönetimine bağlıdır. Font teknolojisinde TextMeshPro SDF (Signed Distance Field) sınırsız ölçeklenebilirlik sunarken, animasyon tarafında PrimeTween ve LitMotion gibi sıfır çöp toplama (Zero GC Allocation) prensibiyle çalışan tween kütüphaneleri 2026 yılı itibarıyla standart haline gelmiştir.

---

## 2. Bulgular (Key Findings)

### 2.1. Tasarım Sistemleri ve Görsel Hiyerarşi Kuramları
*   **Thumb Zone (Başparmak Bölgesi) ve Ergonomi:** Mobil cihazların alt köşeleri birincil aksiyon alanlarıdır (Örn: Subway Surfers'taki *Garage* veya *Play* butonları). Üst alanlar pasif bilgi gösterimi (skor, coin capsule) için ayrılır.
*   **60-30-10 Renk Uyum Kuralı:** 
    *   **%60 Dominant Renk:** Genellikle nötr paneller ve arka planlar (Koyu lacivert/antrasit tonları).
    *   **%30 İkincil Renk:** Buton çerçeveleri, ikincil sekmeler ve bilgi kartı gövdeleri.
    *   **%10 Vurgu (Accent) Rengi:** Sadece ana CTAs (Call-To-Action) butonları için saklanır (Örn: "Tap to Play" veya "Claim Reward" butonlarında kullanılan canlı sarı/turuncu).
*   **Örnek Vaka Analizleri:**
    *   *Subway Surfers (SYBO):* Başlangıç ekranında tam ekranı kaplayan devasa bir "Tap to Play" tetikleyicisiyle etkileşim sürtünmesini sıfıra indirir.
    *   *Brawl Stars (Supercell):* Ekranın sağ altına konumlandırılmış, yüksek kontrastlı dev sarı "PLAY" butonuyla oyuncuyu doğrudan oyuna yönlendirir.

### 2.2. Arayüz Hataları ve Figma-Unity Asset Boru Hatları
*   **Touch Target (Dokunma Alanı):** Yanlış tıklamaları önlemek için mobil cihazlarda interaktif butonların minimum dokunma alanı **48x48 piksel** olmalıdır.
*   **9-Slicing (Dokuz Dilimli Ölçekleme):** Dokuz parçaya bölünen görsel varlıklarda köşeler sabit kalırken kenarlar yatay ve dikey, merkez ise her iki yönde ölçeklenir. Bu sayede 128x128px boyutundaki küçük bir doku, devasa arayüz panellerini çözünürlük kaybı olmadan kaplayabilir. Asset isimlendirmesinde `ui_panel_card_9s.png` gibi belirteçler kullanılır.
*   **Adlandırma Standartları:** Pipeline karmaşasını önlemek adına `Kategori_Tip_Açıklama_Durum` (Örn: `ui_btn_play_pressed`) taksonomisi uygulanmalıdır.

### 2.3. Unity Arayüz Sistemleri: uGUI vs. UI Toolkit (2025/2026)
*   **uGUI (Unity UI):** GameObject tabanlı bir RectTransform hiyerarşisi kullanır. Günümüzde hala desteklenmektedir ve Shader Graph ile uyumludur. 
*   **UI Toolkit (UITK):** Flexbox (Yoga kütüphanesi tabanlı) layout motoru ve USS (CSS benzeri) stil şablonları kullanır. 
*   **Performans Farkı:** UI Toolkit, **Uber-Shader** ve otomatik **Dynamic Atlasing** sayesinde metinleri ve görselleri tek bir draw call ile batchleyebilir. Ancak derin hiyerarşilerde stil çözümleme (style resolution) adımları CPU yükü oluşturabilir. uGUI ise malzeme veya derinlik çakışmalarında batching'i kolayca kırabilir.

### 2.4. Canvas Optimizasyonu ve Rebuild Yönetimi
uGUI'de herhangi bir alt öğe değiştiğinde tüm Canvas "dirty" olarak işaretlenir ve örgü (mesh) yeniden oluşturulur. Bunu önlemek için:
*   **Static vs. Dynamic Canvas Ayrımı:** Değişmeyen arka planları ve başlıkları `Static Canvas` içinde tutun. Dinamik olarak değişen sağlık barları, coin sayaçları gibi elemanları ise `Dynamic Canvas (Sub-Canvas)` altına yerleştirin. Böylece sadece değişen alt Canvas rebuild tetikler.
*   **Layout Group Optimizasyonu:** `Vertical` veya `HorizontalLayoutGroup` bileşenleri $O(N^2)$ işlem yüküyle CPU tıkanmalarına neden olur. Toplu değişiklik yapılmadan önce layout bileşenleri deaktif edilmeli, güncellemeler yapıldıktan sonra re-aktif edilip `LayoutRebuilder.ForceRebuildLayoutImmediate` ile zorlanmalıdır.
*   **CanvasGroup Kullanımı:** UI elemanlarını kapatıp açarken `SetActive(false)` kullanmak yerine `CanvasGroup.alpha = 0` yapmak, hiyerarşinin tamamen yeniden hesaplanmasını önler.

### 2.5. SDF Tipografi ve TextMeshPro Optimizasyonu
*   **Signed Distance Field (SDF):** Yazı karakterlerini mesafe gradyanı olarak saklar. Sonsuz yakınlaştırmada bile GPU tabanlı bilinear interpolasyon sayesinde keskin vektörel kenarlar sunar. Outlines, gölgeler ve parlamalar GPU shader parametreleri üzerinden sıfır performans kaybıyla çizilir.
*   **Dynamic Atlas Sorunu:** Dinamik SDF fontlarında atlas dolduğunda tüm doku baştan oluşturulur ve CPU'da donmalara yol açar. Çözüm olarak sık kullanılan karakterler için statik bir atlas tanımlanmalı, fallback zinciriyle dinamik atlasa yönlendirme yapılmalıdır.

### 2.6. Juice, Mikro-Animasyonlar ve UI Parçacıkları
*   **Tween Kütüphaneleri:** DOTween popüler olsa da GC (Garbage Collection) üretimi yapabilir. 2026 standartlarında **PrimeTween** ve **LitMotion** sıfır GC (Zero-Allocation) prensibiyle çalışarak mobil cihazlardaki FPS donmalarını tamamen engeller.
*   **UI Parçacık Efektleri:** Canvas içinde parçacık sistemleri (ParticleSystem) maskeleme ve katmanlama sorunlarına yol açar. **mob-sakai'nin ParticleEffectForUGUI** kütüphanesi, parçacıkları uGUI elemanına dönüştürerek bu problemi çözer.
*   **UI Ses Tasarımı:** Kullanıcı algısını artırmak için buton seslerinde hafif pitch/volume varyasyonları ($\pm \%5-\%10$) uygulanarak işitsel yorgunluk (ear fatigue) önlenmelidir.

---

## 3. Doğrulama ve Kaynaklar (Sources & Verification)

| Doğrulanan İddia | Kaynak Kuruluş | Doğrulama Bağlantısı | Durum / Metot |
| :--- | :--- | :--- | :--- |
| uGUI Deprecation & Destek Durumu | Unity Technologies | [Unity UI Toolkit Manual](https://docs.unity3d.com/Manual/UIElements.html) | Resmi Doküman Doğrulaması |
| Canvas Rebuild & Optimizasyon Metotları | Unity Technologies | [Optimizing Canvas Performance Guide](https://docs.unity3d.com/Manual/UILearn.html) | 2+ Kaynaktan Doğrulandı |
| SDF Tipografi ve Performans Avantajları | Unity Technologies | [TextMeshPro Documentation](https://docs.unity3d.com/Packages/com.unity.textmeshpro@3.0/manual/index.html) | Resmi Doküman Doğrulaması |
| Safe Area & Aspect Ratio Yönetimi | Unity Technologies | [Unity Screen.safeArea API](https://docs.unity3d.com/ScriptReference/Screen-safeArea.html) | Kod Seviyesinde Doğrulandı |
| UI Tweening & Zero-Allocation Performansı | PrimeTween Developer | [PrimeTween Performance Benchmarks](https://github.com/KyryloKuzyk/PrimeTween) | GitHub Testleri ile Doğrulandı |

---

## 4. Açık Noktalar / Belirsizlikler (Uncertainties/Gaps)
*   **UI Toolkit Spatial UI:** UI Toolkit'in 2026 yılı itibarıyla 3D dünyada (World Space Canvas) renderlanma performansı uGUI'ye kıyasla halen bazı cihaz gruplarında stabilite sorunları barındırmaktadır. Cardiv'deki 3D showroom içi butonlarda uGUI kullanımı şimdilik daha güvenlidir.
