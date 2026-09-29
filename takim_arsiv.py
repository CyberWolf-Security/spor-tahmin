"""
Takim Arsivi v3 — DOGRU alan eslesmesi
WM/AE/PX = ev sahibi (AG = ev gol)
WN/AF/PY = deplasman (AH = dep gol)
"""
import urllib.request, re
from datetime import datetime

HDR = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
       "Accept-Language":"tr-TR,tr;q=0.9,en;q=0.8"}

def _get(url, timeout=30):
    return urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=timeout).read().decode("utf-8", errors="ignore")

def _slug(ad):
    tr = str.maketrans("çğıöşüÇĞİÖŞÜé", "cgiosuCGIOSUe")
    return re.sub(r'[^a-z0-9]+', '-', ad.lower().translate(tr)).strip('-')

def takim_id_ara(lig_url):
    try:
        ic = _get(lig_url)
    except Exception:
        return {}
    t = {}
    for m in re.finditer(r'PX÷([A-Za-z0-9]{6,10})¬AE÷([^¬]+)', ic):
        tid, ad = m.group(1), m.group(2).strip()
        if len(ad) > 2: t[ad] = tid
    return t

def _parse(ic):
    """WM=ev (AG gol), WN=dep (AH gol)"""
    maclar = []
    for b in re.split(r'~?AA÷', ic)[1:]:
        try:
            # EV: WM blogu → AE isim
            ev_m = re.search(r'¬WM÷[A-Z]{2,4}¬AE÷([^¬]+)', b)
            # DEP: WN blogu → AF isim
            dep_m = re.search(r'¬WN÷[A-Z]{2,4}¬AF÷([^¬]+)', b)
            if not ev_m or not dep_m:
                # Yedek: AF=ev, AE=dep (lig sayfasi formati)
                ae = re.search(r'¬AE÷([^¬]+)', b)
                af = re.search(r'¬AF÷([^¬]+)', b)
                if not ae or not af: continue
                ev, dep = af.group(1).strip(), ae.group(1).strip()
            else:
                ev, dep = ev_m.group(1).strip(), dep_m.group(1).strip()
            if len(ev) < 2 or len(dep) < 2: continue

            ab = re.search(r'¬AB÷(\d+)¬', b)
            durum = int(ab.group(1)) if ab else 1
            # AG = ev gol, AH = dep gol
            ag = re.search(r'¬AG÷(\d+)¬', b)
            ah = re.search(r'¬AH÷(\d+)¬', b)
            eg = int(ag.group(1)) if ag else None
            dg = int(ah.group(1)) if ah else None

            tr = re.search(r'¬AD÷(\d{9,11})¬', b)
            tarih = saat = ""
            if tr:
                try:
                    dt = datetime.fromtimestamp(int(tr.group(1)))
                    tarih = dt.strftime("%Y-%m-%d"); saat = dt.strftime("%H:%M")
                except Exception: pass

            maclar.append({
                "ev": ev, "dep": dep, "ev_gol": eg, "dep_gol": dg,
                "durum": durum, "canli": durum == 2, "dakika": None,
                "tarih": tarih, "saat": saat,
                "oynandi": durum == 3 and eg is not None,
                "lig_adi": None, "lig_ham": None, "bayrak": "⚽",
                "kaynak": "Arşiv"
            })
        except Exception:
            continue
    gor=set(); tz=[]
    for m in maclar:
        k=(m["ev"],m["dep"],m["tarih"])
        if k in gor: continue
        gor.add(k); tz.append(m)
    return tz

def takim_maclari(takim_adi, takim_id):
    slug = _slug(takim_adi)
    for yol in ["sonuclar", ""]:
        try:
            ic = _get(f"https://www.flashscore.com.tr/takim/{slug}/{takim_id}/{yol}".rstrip("/"))
            ms = _parse(ic)
            if ms: return ms
        except Exception:
            continue
    return []

def lig_arsivi(lig_url, max_takim=30, ilerleme=None):
    tak = takim_id_ara(lig_url)
    hepsi = []
    hedef = list(tak.items())[:max_takim]
    for i, (ad, tid) in enumerate(hedef):
        ms = takim_maclari(ad, tid)
        hepsi += ms
        if ilerleme: ilerleme(i+1, len(hedef), ad, len(ms))
    gor=set(); tz=[]
    for m in hepsi:
        k=(m["ev"],m["dep"],m["tarih"])
        if k in gor: continue
        gor.add(k); tz.append(m)
    return tz

if __name__ == "__main__":
    ms = takim_maclari("Fenerbahçe", "MsbmracL")
    oyn = [m for m in ms if m["oynandi"]]
    print(f"Fenerbahce: {len(ms)} mac ({len(oyn)} oynanmis)")
    for m in oyn[:8]:
        print(f"  {m['tarih']} {m['ev'][:22]:24s} {m['ev_gol']}-{m['dep_gol']} {m['dep'][:22]}")
