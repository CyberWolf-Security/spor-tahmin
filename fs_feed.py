"""
FlashScore Feed Parser v2 — DUNYA CAPINDA TUM LIGLER
Kendi veri kaynagi: global.flashscore.ninja
"""
import urllib.request, json, time
from datetime import datetime

FEED_BASE = "https://global.flashscore.ninja/2/x/feed"
FSIGN = "SW9D1eZo"
HDR = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
       "x-fsign": FSIGN, "Accept":"*/*"}

# Onemli ligler (Turkce adlar + bayrak)
ONEMLI = {
    "TURKEY: Super Lig": ("Süper Lig","🇹🇷"),
    "TURKEY: 1. Lig": ("1. Lig","🇹🇷"),
    "TURKEY: Cup": ("Türkiye Kupası","🇹🇷"),
    "ENGLAND: Premier League": ("Premier League","🏴󠁧󠁢󠁥󠁮󠁧󠁿"),
    "ENGLAND: Championship": ("Championship","🏴󠁧󠁢󠁥󠁮󠁧󠁿"),
    "ENGLAND: League One": ("League One","🏴󠁧󠁢󠁥󠁮󠁧󠁿"),
    "ENGLAND: FA Cup": ("FA Cup","🏴󠁧󠁢󠁥󠁮󠁧󠁿"),
    "SPAIN: LaLiga": ("La Liga","🇪🇸"),
    "SPAIN: LaLiga 2": ("La Liga 2","🇪🇸"),
    "SPAIN: Copa del Rey": ("Kral Kupası","🇪🇸"),
    "ITALY: Serie A": ("Serie A","🇮🇹"),
    "ITALY: Serie B": ("Serie B","🇮🇹"),
    "ITALY: Coppa Italia": ("İtalya Kupası","🇮🇹"),
    "GERMANY: Bundesliga": ("Bundesliga","🇩🇪"),
    "GERMANY: Bundesliga 2": ("Bundesliga 2","🇩🇪"),
    "GERMANY: DFB Pokal": ("DFB Pokal","🇩🇪"),
    "FRANCE: Ligue 1": ("Ligue 1","🇫🇷"),
    "FRANCE: Ligue 2": ("Ligue 2","🇫🇷"),
    "NETHERLANDS: Eredivisie": ("Eredivisie","🇳🇱"),
    "PORTUGAL: Liga Portugal": ("Primeira Liga","🇵🇹"),
    "BELGIUM: Jupiler Pro League": ("Belçika Ligi","🇧🇪"),
    "SCOTLAND: Premiership": ("İskoçya Ligi","🏴󠁧󠁢󠁳󠁣󠁴󠁿"),
    "RUSSIA: Premier League": ("Rusya Ligi","🇷🇺"),
    "UKRAINE: Premier League": ("Ukrayna Ligi","🇺🇦"),
    "GREECE: Super League": ("Yunanistan Ligi","🇬🇷"),
    "SWITZERLAND: Super League": ("İsviçre Ligi","🇨🇭"),
    "AUSTRIA: Bundesliga": ("Avusturya Ligi","🇦🇹"),
    "EUROPE: Champions League": ("Şampiyonlar Ligi","🏆"),
    "EUROPE: Europa League": ("Avrupa Ligi","🥈"),
    "EUROPE: Conference League": ("Konferans Ligi","🥉"),
    "EUROPE: UEFA Nations League - League A": ("Uluslar Ligi A","🇪🇺"),
    "EUROPE: UEFA Nations League - League B": ("Uluslar Ligi B","🇪🇺"),
    "EUROPE: UEFA Nations League - League C": ("Uluslar Ligi C","🇪🇺"),
    "WORLD: World Cup": ("Dünya Kupası","🌍"),
    "WORLD: World Cup - Qualification Europe": ("DK Elemeleri (Avrupa)","🌍"),
    "WORLD: Club Friendly Games": ("Hazırlık Maçları","🤝"),
    "USA: MLS": ("MLS","🇺🇸"),
    "MEXICO: Liga MX": ("Liga MX","🇲🇽"),
    "BRAZIL: Serie A": ("Brezilya Serie A","🇧🇷"),
    "BRAZIL: Serie B": ("Brezilya Serie B","🇧🇷"),
    "ARGENTINA: Liga Profesional": ("Arjantin Ligi","🇦🇷"),
    "SAUDI ARABIA: Saudi Pro League": ("Suudi Ligi","🇸🇦"),
    "JAPAN: J1 League": ("Japonya J1","🇯🇵"),
    "SOUTH KOREA: K League 1": ("Kore Ligi","🇰🇷"),
    "CHINA: Super League": ("Çin Süper Ligi","🇨🇳"),
    "AUSTRALIA: A-League": ("A-Ligi","🇦🇺"),
}

def _get(url, timeout=6):  # 30 -> 6 sn (yavas agda takilmasin)
    return urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=timeout).read().decode("utf-8", errors="ignore")

def _al(blok, kod):
    a = f"¬{kod}÷"
    i = blok.find(a)
    if i < 0: return None
    j = blok.find("¬", i + len(a))
    return blok[i+len(a):j if j > 0 else len(blok)].strip()

def feed_cek(gun=0):
    try:
        return _get(f"{FEED_BASE}/f_1_{gun}_3_en_1")
    except Exception:
        return ""

def parse(icerik, sadece_onemli=True):
    if not icerik: return []
    maclar = []
    for bolum in icerik.split("~ZA÷")[1:]:
        lig_ham = bolum.split("¬")[0].strip()
        bilgi = ONEMLI.get(lig_ham)
        if sadece_onemli and not bilgi:
            continue
        if bilgi:
            lig_adi, bayrak = bilgi
        else:
            lig_adi = lig_ham.replace(":", " —").strip()
            bayrak = "⚽"

        for b in bolum.split("~AA÷")[1:]:
            try:
                ev_m = _al(b, "AE"); dep_m = _al(b, "AF")
                if not ev_m or not dep_m or len(ev_m) < 2 or len(dep_m) < 2: continue

                ab = _al(b, "AB")
                durum = int(ab) if ab and ab.isdigit() else 1
                ac = _al(b, "AC")
                dakika_feed = int(ac) if ac and ac.isdigit() else None
                # ═══ DAKIKA: feed'in AC alani GUNCELLENMIYOR!
                # Gercek dakikayi mac baslama zamanindan (AD) HESAPLA
                dakika = None
                ad_ham = _al(b, "AD")
                if durum == 2 and ad_ham and ad_ham.isdigit():
                    try:
                        gecen = (time.time() - int(ad_ham)) / 60.0
                        # Devre arasi/uzatma icin sinirla
                        if gecen < 0:
                            gecen = 0
                        d = int(gecen)
                        if d > 45 and d < 60:
                            d = 45        # devre arasi
                        elif d >= 60:
                            d = min(d - 15, 90)   # 2. yari (15 dk ara cikarilir)
                        dakika = d
                    except Exception:
                        dakika = dakika_feed
                elif dakika_feed is not None:
                    dakika = dakika_feed

                ag = _al(b, "AG"); ah = _al(b, "AH")
                eg = int(ag) if ag and ag.isdigit() else None
                dg = int(ah) if ah and ah.isdigit() else None

                ad = _al(b, "AD")
                tarih = saat = ""
                if ad and ad.isdigit():
                    try:
                        dt = datetime.fromtimestamp(int(ad))
                        tarih = dt.strftime("%Y-%m-%d"); saat = dt.strftime("%H:%M")
                    except Exception: pass

                # Logo kodlari (OA=ev logo kodu, OB=dep logo kodu)
                oa = _al(b, "OA"); ob = _al(b, "OB")
                ev_logo = f"https://static.flashscore.com/res/image/data/{oa}" if oa else None
                dep_logo = f"https://static.flashscore.com/res/image/data/{ob}" if ob else None

                maclar.append({
                    "ev": ev_m, "dep": dep_m,
                    "ev_logo": ev_logo, "dep_logo": dep_logo,
                    "ev_gol": eg, "dep_gol": dg,
                    "durum": durum, "canli": durum == 2, "dakika": dakika,
                    "tarih": tarih, "saat": saat,
                    "oynandi": durum == 3 and eg is not None,
                    "lig_adi": lig_adi, "lig_ham": lig_ham, "bayrak": bayrak,
                    "kaynak": "FlashScore"
                })
            except Exception:
                continue
    return maclar

def gun_maclari(gun=0, sadece_onemli=True):
    return parse(feed_cek(gun), sadece_onemli)

def tum_gunler(gunler=(-3,-2,-1,0,1,2,3,4,5,6,7), sadece_onemli=True, ilerleme=None):
    hepsi = []
    hata_sayisi = 0
    for i, g in enumerate(gunler):
        try:
            m = gun_maclari(g, sadece_onemli)
            hepsi += m
            if ilerleme: ilerleme(i+1, len(gunler), g, len(m))
        except Exception as e:
            hata_sayisi += 1
            if ilerleme: ilerleme(i+1, len(gunler), g, 0)
            continue                      # bu gunu atla, digerlerine devam
    gor = set(); tz = []
    for m in hepsi:
        k = (m["ev"], m["dep"], m["tarih"])
        if k in gor: continue
        gor.add(k); tz.append(m)
    return tz

def canli_maclar():
    """Canli maclar — 3 gunu PARALEL cek (hizli)"""
    from concurrent.futures import ThreadPoolExecutor
    gunler = (-1, 0, 1)

    def _cek(g):
        try:
            return [m for m in gun_maclari(g, False) if m["canli"]]
        except Exception:
            return []

    hepsi = []
    with ThreadPoolExecutor(max_workers=3) as ex:
        for r in ex.map(_cek, gunler):
            hepsi += r
    return hepsi

if __name__ == "__main__":
    print("=== TUM DUNYA (onemli ligler, 11 gun) ===")
    def ilerle(i, n, gun, adet):
        print(f"  [{i:2d}/{n}] gun {gun:+d}: {adet:4d} mac")
    hepsi = tum_gunler(ilerleme=ilerle)
    print()
    print(f"TOPLAM: {len(hepsi)} mac")
    from collections import Counter
    c = Counter(x["lig_adi"] for x in hepsi)
    print("\nLig dagilimi (ilk 20):")
    for ad, n in c.most_common(20):
        print(f"  {ad:24s} {n:4d}")
    print()
    oyn = [x for x in hepsi if x["oynandi"]]
    print(f"Oynanmis: {len(oyn)} | Gelecek: {len(hepsi)-len(oyn)}")
    c2 = canli_maclar()
    print(f"\nCANLI ({len(c2)}):")
    for m in c2[:6]:
        print(f"  {m['dakika']}' {m['ev']} {m['ev_gol']}-{m['dep_gol']} {m['dep']} [{m['lig_adi']}]")
