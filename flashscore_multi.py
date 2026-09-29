"""FlashScore coklu lig cekici — tum buyuk ligler (anahtarsiz)"""
import urllib.request, re, json
from datetime import datetime

HDR = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
       "Accept-Language":"tr-TR,tr;q=0.9,en;q=0.8"}

# Lig listesi (kod, ad, ulke, url)
LIGLER = [
    ("superlig",  "Süper Lig",          "Türkiye",   "https://www.flashscore.com.tr/futbol/turkiye/super-lig/"),
    ("premier",   "Premier League",     "İngiltere", "https://www.flashscore.com.tr/futbol/ingiltere/premier-league/"),
    ("laliga",    "La Liga",            "İspanya",   "https://www.flashscore.com.tr/futbol/ispanya/laliga/"),
    ("seriea",    "Serie A",            "İtalya",    "https://www.flashscore.com.tr/futbol/italya/serie-a/"),
    ("bundes",    "Bundesliga",         "Almanya",   "https://www.flashscore.com.tr/futbol/almanya/bundesliga/"),
    ("ligue1",    "Ligue 1",            "Fransa",    "https://www.flashscore.com.tr/futbol/fransa/ligue-1/"),
    ("eredivisie","Eredivisie",         "Hollanda",  "https://www.flashscore.com.tr/futbol/hollanda/eredivisie/"),
    ("primeira",  "Primeira Liga",      "Portekiz",  "https://www.flashscore.com.tr/futbol/portekiz/liga-nos/"),
    ("champ",     "Championship",       "İngiltere", "https://www.flashscore.com.tr/futbol/ingiltere/championship/"),
    ("bundes2",   "Bundesliga 2",       "Almanya",   "https://www.flashscore.com.tr/futbol/almanya/2-bundesliga/"),
    ("ucl",       "Şampiyonlar Ligi",   "Avrupa",    "https://www.flashscore.com.tr/futbol/avrupa/sampiyonlar-ligi/"),
    ("uel",       "Avrupa Ligi",        "Avrupa",    "https://www.flashscore.com.tr/futbol/avrupa/avrupa-ligi/"),
    ("uelc",      "Konferans Ligi",     "Avrupa",    "https://www.flashscore.com.tr/futbol/avrupa/konferans-ligi/"),
    ("mls",       "MLS",                "ABD",       "https://www.flashscore.com.tr/futbol/abd/mls/"),
]

def _get(url, timeout=35):
    return urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=timeout).read().decode("utf-8", errors="ignore")

def lig_maclari(kod, ad, ulke, url):
    """Tek ligin maclarini cek"""
    try:
        ic = _get(url)
    except Exception:
        return []
    maclar = []
    for b in ic.split("~AA÷")[1:]:
        try:
            ev_m = re.search(r'¬AE÷([^¬]+)', b)
            dep_m = re.search(r'¬AF÷([^¬]+)', b)
            if not ev_m or not dep_m: continue
            ev = ev_m.group(1).strip(); dep = dep_m.group(1).strip()
            if len(ev) < 2 or len(dep) < 2: continue

            tr = re.search(r'¬AD÷(\d{9,11})¬', b)
            tarih = saat = ""
            if tr:
                try:
                    dt = datetime.fromtimestamp(int(tr.group(1)))
                    tarih = dt.strftime("%Y-%m-%d"); saat = dt.strftime("%H:%M")
                except Exception: pass

            ag = re.search(r'¬AG÷(\d+)¬', b)   # ev gol
            ah = re.search(r'¬AH÷(\d+)¬', b)   # dep gol
            ab = re.search(r'¬AB÷(\d+)¬', b)   # durum (3=bitmis)

            eg = int(ag.group(1)) if ag else None
            dg = int(ah.group(1)) if ah else None
            bitti = (ab.group(1) == "3") if ab else False

            maclar.append({
                "ev": ev, "dep": dep, "ev_gol": eg, "dep_gol": dg,
                "tarih": tarih, "saat": saat,
                "oynandi": bitti and eg is not None and dg is not None,
                "kaynak":"FlashScore", "lig":kod, "lig_adi":ad, "ulke":ulke
            })
        except Exception:
            continue
    # Mukerrer temizle
    gor=set(); tz=[]
    for m in maclar:
        k=(m["ev"],m["dep"],m["tarih"])
        if k in gor: continue
        gor.add(k); tz.append(m)
    return tz

def tum_ligler(ilerleme=None):
    """Tum ligleri cek"""
    hepsi = []
    for i, (kod, ad, ulke, url) in enumerate(LIGLER):
        m = lig_maclari(kod, ad, ulke, url)
        hepsi += m
        if ilerleme: ilerleme(i+1, len(LIGLER), ad, len(m))
    return hepsi

if __name__ == "__main__":
    print("=== TUM LIGLER ===")
    toplam = 0
    def ilerle(i, n, ad, miktar):
        oyn = 0
        print(f"  [{i}/{n}] {ad:20s} {miktar:4d} mac")
    hepsi = tum_ligler(ilerle)
    print()
    print("TOPLAM:", len(hepsi))
    from collections import Counter
    c = Counter(x["lig_adi"] for x in hepsi)
    for ad, n in c.most_common():
        print(f"  {ad:20s} {n:4d}")
