"""FlashScore Süper Lig parser (v2 — dogru alan eslesmesi)"""
import urllib.request, re, json
from datetime import datetime

HDR = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
       "Accept-Language":"tr-TR,tr;q=0.9,en;q=0.8"}
URL = "https://www.flashscore.com.tr/futbol/turkiye/super-lig/"

def _get(url, timeout=40):
    return urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=timeout).read().decode("utf-8", errors="ignore")

def maclari_cek():
    ic = _get(URL)
    maclar = []
    for b in ic.split("~AA÷")[1:]:
        try:
            # Ev takim: ilk AE
            ev_m = re.search(r'¬AE÷([^¬]+)', b)
            # Dep takim: ikinci AE
            ev_m = re.search(r'¬AE÷([^¬]+)', b)
            dep_m = re.search(r'¬AF÷([^¬]+)', b)
            if not ev_m or not dep_m: continue
            ev = ev_m.group(1).strip(); dep = dep_m.group(1).strip()
            if len(ev) < 2 or len(dep) < 2: continue

            # Tarih: AD (unix)
            tr = re.search(r'¬AD÷(\d{9,11})¬', b)
            tarih = ""
            if tr:
                try: tarih = datetime.fromtimestamp(int(tr.group(1))).strftime("%Y-%m-%d")
                except Exception: pass

            # Ev gol = AG (ilk), dep gol = AH (ilk)  [Flashscore: AG=home, AH=away]
            ag = re.search(r'¬AG÷(\d+)¬', b)
            ah = re.search(r'¬AH÷(\d+)¬', b)
            durum = re.search(r'¬AB÷(\d+)¬', b)

            eg = int(ag.group(1)) if ag else None
            dg = int(ah.group(1)) if ah else None
            bitti = (durum.group(1) == "3") if durum else False

            maclar.append({
                "ev": ev, "dep": dep,
                "ev_gol": eg, "dep_gol": dg,
                "tarih": tarih,
                "oynandi": bitti and eg is not None and dg is not None,
                "kaynak":"FlashScore", "lig":"superlig", "lig_adi":"Süper Lig"
            })
        except Exception:
            continue

    # Mukerrer temizle
    gor = set(); tz = []
    for m in maclar:
        k = (m["ev"], m["dep"], m["tarih"])
        if k in gor: continue
        gor.add(k); tz.append(m)
    return tz

if __name__ == "__main__":
    m = maclari_cek()
    oyn = [x for x in m if x["oynandi"]]
    print(f"Toplam: {len(m)} | Oynanmis: {len(oyn)}")
    print("\n--- OYNANMIS ---")
    for x in oyn[:10]:
        print(f"  {x['tarih']} {x['ev'][:20]:22s} {x['ev_gol']}-{x['dep_gol']} {x['dep'][:20]}")
    print("\n--- GELECEK ---")
    for x in [y for y in m if not y["oynandi"]][:6]:
        print(f"  {x['tarih']} {x['ev'][:20]:22s} vs {x['dep'][:20]}")
