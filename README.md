# ⚽ Spor Tahmin — Maç Analiz ve Tahmin Programı

**CyberWolfSec** tarafından geliştirilen, tamamen **yerel çalışan** (internet bağlantısı gerektirmeyen tahmin motoru) futbol maç analiz ve tahmin programı.

![Sürüm](https://img.shields.io/badge/sürüm-16.8-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![Lisans](https://img.shields.io/badge/lisans-MIT-green)

---

## 🎬 Tanıtım Videosu

Programın tanıtım videosunu izleyin (2:21):

[![Tanıtım Videosu](https://img.shields.io/badge/▶_Tanıtım_Videosu-izle-red?style=for-the-badge)](https://github.com/CyberWolf-Security/spor-tahmin/releases/download/v16.8/tanitim_video.mp4)

**İçerik:** Program tanıtımı • Algoritma detayları (Poisson, Elo, Ensemble) • Özellikler • Veri havuzu • Kurulum

---

## 📌 Nedir?

**Spor Tahmin**, futbol maçlarını istatistiksel modellerle analiz eden ve sonuç tahmini üreten bir masaüstü programıdır.

- 🖥️ Windows'ta tek kurulumla çalışır (kurulum sihirbazı dahil)
- 🔌 **Tamamen yerel** — maç tahmini için internet gerekmez
- 📊 **1.000.000 (1 milyon) maç simülasyonu** ile olasılık hesabı
- 🌍 **32 lig, 757 maç, 21 ülke** veri havuzu
- ⚡ Hızlı: 1M simülasyon saniyeler içinde tamamlanır

---


## 📸 Ekran Goruntuleri

<table>
<tr>
<td width="50%"><b>Ana Sayfa - Takim Secimi</b><br><img src="https://raw.githubusercontent.com/CyberWolf-Security/spor-tahmin/main/ekran-goruntuleri/01-ana-sayfa.png"></td>
<td width="50%"><b>Canli Serit</b><br><img src="https://raw.githubusercontent.com/CyberWolf-Security/spor-tahmin/main/ekran-goruntuleri/02-canli-serit.png"></td>
</tr>
<tr>
<td><b>Laptop Gorunumu (1280x800)</b><br><img src="https://raw.githubusercontent.com/CyberWolf-Security/spor-tahmin/main/ekran-goruntuleri/03-ana-laptop.png"></td>
<td><b>Tablet Gorunumu (1024x768)</b><br><img src="https://raw.githubusercontent.com/CyberWolf-Security/spor-tahmin/main/ekran-goruntuleri/04-ana-tablet.png"></td>
</tr>
<tr>
<td><b>Full HD Gorunum (1920x1080)</b><br><img src="https://raw.githubusercontent.com/CyberWolf-Security/spor-tahmin/main/ekran-goruntuleri/05-ana-fhd.png"></td>
<td><b>Canli - Laptop</b><br><img src="https://raw.githubusercontent.com/CyberWolf-Security/spor-tahmin/main/ekran-goruntuleri/06-canli-laptop.png"></td>
</tr>
<tr>
<td><b>Canli - Full HD</b><br><img src="https://raw.githubusercontent.com/CyberWolf-Security/spor-tahmin/main/ekran-goruntuleri/07-canli-fhd.png"></td>
<td><b>Mobil Gorunum (480px)</b><br><img src="https://raw.githubusercontent.com/CyberWolf-Security/spor-tahmin/main/ekran-goruntuleri/08-mobil.png"></td>
</tr>
<tr>
<td><b>Ana Sayfa - Tam Sayfa</b><br><img src="https://raw.githubusercontent.com/CyberWolf-Security/spor-tahmin/main/ekran-goruntuleri/09-ana-tam-sayfa.png"></td>
<td><b>Canli - Tam Sayfa</b><br><img src="https://raw.githubusercontent.com/CyberWolf-Security/spor-tahmin/main/ekran-goruntuleri/10-canli-tam-sayfa.png"></td>
</tr>
</table>

---

## 🎯 Ne Yapar?

| Özellik | Açıklama |
|---|---|
| **1X2 Tahmini** | Ev kazanır / Beraberlik / Deplasman kazanır olasılıkları |
| **Skor Tahmini** | En olası skorlar (örn. 1-1 %11.6, 2-1 %9.5) |
| **Beklenen Gol** | Ev ve deplasman için beklenen gol sayısı |
| **Alt/Üst 2.5** | 2.5 gol üstü/altı olasılığı |
| **Karşılıklı Gol (KG)** | İki takımın da gol atma olasılığı |
| **Güven Seviyesi** | Veri yeterliliğine göre YÜKSEK / ORTA / DÜŞÜK |
| **Canlı Şerit** | O an oynanan maçlar (skor + dakika) |
| **Son Aramalar** | Daha önce baktığın maçlar (tek tıkla geri dön) |

---

## 🧠 Nasıl Çalışır? (Algoritma)

Program üç katmanlı bir **ensemble (topluluk)** modeli kullanır:

### 1. Poisson Dağılımı (Dixon-Coles düzeltmeli)
Her takımın hücum/savunma gücü hesaplanır, beklenen gol sayısı çıkarılır. Poisson dağılımı ile skor olasılıkları üretilir.

### 2. Elo Rating Sistemi
Satranç kökenli, futbola uyarlanmış rating:
- Başlangıç: **1500 puan**
- K katsayısı: **24** (gol farkına göre ağırlıklı)
- Ev sahibi avantajı: **+65 puan bonus**

### 3. Form + Zaman Ağırlığı
- Maçlar **tarih sıralı** işlenir (veri sızıntısı yok)
- **Yarı ömür 250 maç** — yeni maçlar daha ağır
- Az veri durumunda **lig ortalamasına regresyon** (güvenilirlik katsayısı)

### Ensemble Birleştirme
```
Nihai Olasılık = %65 × Poisson  +  %35 × Elo/Form
```

### Ek Faktörler
- **H2H (Head-to-Head):** Geçmiş karşılaşmaların etkisi
- **Dinlenme Günü:** Yorgunluk/kondisyon analizi
- **Beraberlik Karar Motoru:** Beraberlik oranını kalibre eder (model ~%23, gerçek ~%27)

### Simülasyon
Her maç için **1.000.000 kez** Monte Carlo simülasyonu çalıştırılır → olasılıklar ve skor dağılımı bu simülasyondan üretilir.

---

## 🌍 Veri Havuzu

**32 lig, 757 maç, 21 ülke** — popüler ligler önceliklidir:

- 🇹🇷 Türkiye (Süper Lig)
- 🏴 England (Premier League)
- 🇪🇸 İspanya (La Liga)
- 🇮🇹 İtalya (Serie A)
- 🇩🇪 Almanya (Bundesliga)
- 🇫🇷 Fransa (Ligue 1)
- 🇧🇷 Brezilya, 🇦🇷 Arjantin
- 🇵🇹 Portekiz, 🇳🇱 Hollanda
- 🌍 Arap ligleri (Suudi, Katar, BAE, Mısır, Fas, Tunus, Cezayir, Irak, Ürdün, Lübnan)
- 👩 Kadın ligleri
- 🏆 Uluslararası turnuvalar (UEFA, WORLD)

---

## 💻 Kurulum

### Windows
1. `SporTahmin_Kurulum.exe` dosyasını indir
2. Çalıştır → kurulum sihirbazı açılır
3. "İleri" → "Kur" → "Bitir"
4. Masaüstündeki **Spor Tahmin** kısayolundan aç

**Not:** Program imzasızdır — Windows SmartScreen uyarı verebilir. "Daha fazla bilgi" → "Yine de çalıştır" ile geçilir.

### Sistem Gereksinimleri
- Windows 10/11 (64-bit)
- 2 GB RAM (önerilen 4 GB)
- 200 MB disk alanı
- İnternet **gerekmez** (tahmin için)

---

## 🚀 Kullanım

1. Programı aç → ana ekran gelir
2. **Takım seç** (ev + deplasman)
3. **Tahmin Et** butonuna bas
4. Sonuçlar:
   - 1X2 olasılıkları (yeşil = en olası)
   - En olası skorlar tablosu
   - Beklenen gol, alt/üst 2.5, KG
   - Güven seviyesi

**Canlı sekmesi:** O an oynanan maçların canlı skoru.

**Kopyala:** Sonucu panoya kopyalar (paylaşmak için).

---

## 🛠️ Teknik Detaylar

| | |
|---|---|
| **Dil** | Python 3.12 |
| **Arayüz** | Flask (WSGI) + pywebview (gömülü tarayıcı) |
| **Hesaplama** | NumPy (vektörel Poisson) |
| **Paketleme** | PyInstaller `--onedir` (antivirüs uyumlu) |
| **Kurulum** | Inno Setup |
| **Sürümleme** | 16.8.0.0 |

### Dosya Yapısı
```
├── main.py            # Giriş noktası (Flask + pywebview başlatır)
├── app.py             # Flask uygulaması, API endpoint'leri
├── mega_ajan.py       # Poisson + takım gücü + beklenen gol
├── mega_elo.py        # Elo rating + ensemble
├── mega_karar.py      # Beraberlik odaklı karar motoru
├── olasilik.py        # Tüm olasılık hesapları
├── hazir_tahmin.py    # Hazır tahmin üretimi (1M sim)
├── fs_feed.py         # Canlı skor feed'i
├── templates/
│   ├── index.html     # Ana arayüz
│   └── canli.html     # Canlı şerit
└── veri/
    ├── hazir_tahminler.json   # 757 maç tahmini
    ├── arsiv_superlig.json    # Süper Lig arşivi
    └── takim_web.json         # Takım bilgileri
```

---

## 🔄 Otomatik Derleme (CI/CD)

Program **GitHub Actions** ile otomatik derlenir:

1. `main` branch'ine push yapılır
2. GitHub Actions (windows-latest) tetiklenir
3. PyInstaller `--onedir` ile derlenir
4. Inno Setup ile kurulum paketi oluşturulur
5. **Otomatik release** yayınlanır

**Son sürümü indir:**
→ [Releases](../../releases/latest) → `SporTahmin_Kurulum.exe`

---

## ⚠️ Yasal Uyarı

Bu program **istatistiksel analiz** amaçlıdır. Tahminler **kesin değildir** — futbol doğası gereği belirsizlik içerir. Hiçbir tahmin %100 doğru olamaz. Program **bahis tavsiyesi vermez**; çıktılar yalnızca istatistiksel olasılıklardır.

---

## 🏢 Geliştirici

**CyberWolfSec** — Profesyonel Siber Güvenlik Hizmetleri
🌐 [cyberwolfsec.com](https://cyberwolfsec.com)

---

## 📄 Lisans

MIT License — Copyright (c) 2026 CyberWolfSec
