"""
Canli Veri - Coklu kaynak (Bundesliga acik + Super Lig API)
"""
import json, urllib.request, urllib.error, os
from datetime import datetime

BASE_OLDB = "https://api.openligadb.de"
BASE_AF   = "https://v3.football.api-sports.io"
VERI_DIZIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "veri")
AYAR_DOSYA = os.path.join(VERI_DIZIN, "ayarlar.json")

# Acik ligler (OpenLigaDB - anahtarsiz)
OLDB_LIGLER = {
    "bl1": "Bundesliga",
    "bl2": "Bundesliga 2",
    "bl3": "3. Liga",
    "dfb": "DFB Pokal",
    "ucl": "Sampiyonlar Ligi",
    "uel": "Avrupa Ligi",
}

# API-Football ligleri (anahtar gerekir)
AF_LIGLER = {
    203: "Super Lig (Turkiye)",
    39:  "Premier League",
    140: "La Liga",
    135: "Serie A",
    78:  "Bundesliga",
    61:  "Ligue 1",
    2:   "Sampiyonlar Ligi",
    3:   "Avrupa Ligi",
}

def ayar_yukle():
    if os.path.exists(AYAR_DOSYA):
        try:
            with open(AYAR_DOSYA, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"api_anahtar": ""}

def ayar_kaydet(d):
    os.makedirs(VERI_DIZIN, exist_ok=True)
    with open(AYAR_DOSYA, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)

def _get(url, basliklar=None, timeout=25):
    h = {"User-Agent":"SporTahmin/1.0","Accept":"application/json"}
    if basliklar: h.update(basliklar)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

# ── OpenLigaDB (anahtarsiz) ──
def oldb_maclar(lig="bl1"):
    d = _get(f"{BASE_OLDB}/getmatchdata/{lig}")
    out = []
    for m in d:
        eg = dg = None
        for s in (m.get("matchResults") or []):
            if s.get("resultTypeID") == 2:
                eg, dg = s["pointsTeam1"], s["pointsTeam2"]
        out.append({
            "ev": m["team1"]["teamName"], "dep": m["team2"]["teamName"],
            "ev_gol": eg, "dep_gol": dg,
            "tarih": (m.get("matchDateTime") or "")[:10],
            "saat": (m.get("matchDateTime") or "")[11:16],
            "oynandi": bool(m.get("matchIsFinished")),
            "kaynak": "OpenLigaDB", "lig": lig, "lig_adi": OLDB_LIGLER.get(lig, lig)
        })
    return out

def oldb_tablo(lig="bl1"):
    d = _get(f"{BASE_OLDB}/getbltable/{lig}/{datetime.now().year}")
    return [{"sira":i+1,"takim":t.get("teamName",""),"mac":t.get("matches",0),
             "puan":t.get("points",0),"atilan":t.get("goals",0),
             "yenilen":t.get("opponentGoals",0)} for i,t in enumerate(d)]

# ── API-Football (anahtar gerekir) ──
def af_anahtar_gecerli():
    a = ayar_yukle().get("api_anahtar","").strip()
    if not a: return False, "Anahtar yok"
    try:
        d = _get(f"{BASE_AF}/status", {"x-apisports-key": a})
        r = d.get("response", {})
        acc = r.get("account", {})
        return True, f"{acc.get('email','?')} | Limit: {r.get('requests',{}).get('current',0)}/{r.get('requests',{}).get('limit_day',0)}"
    except Exception as e:
        return False, str(e)[:60]

def af_maclar(lig=203, sezon=2026):
    a = ayar_yukle().get("api_anahtar","").strip()
    if not a: return {"hata":"API anahtari gerekli (Ayarlar)"}
    try:
        # Gecmis + gelecek tum fikstur
        d = _get(f"{BASE_AF}/fixtures?league={lig}&season={sezon}", {"x-apisports-key": a})
        out = []
        for m in d.get("response", []):
            f = m["fixture"]; t = m["teams"]; g = m["goals"]
            out.append({
                "ev": t["home"]["name"], "dep": t["away"]["name"],
                "ev_gol": g.get("home"), "dep_gol": g.get("away"),
                "tarih": (f.get("date") or "")[:10],
                "saat": (f.get("date") or "")[11:16],
                "oynandi": f.get("status",{}).get("short") in ("FT","AET","PEN"),
                "kaynak":"API-Football", "lig":lig, "lig_adi": AF_LIGLER.get(lig,str(lig))
            })
        return {"hata": None, "maclar": out}
    except Exception as e:
        return {"hata": str(e)[:80]}

def tum_maclar():
    """Tum kaynaklardan mac cek"""
    maclar = []
    # FlashScore — Super Lig (anahtarsiz scraping)
    try:
        import flashscore
        maclar += flashscore.maclari_cek()
    except Exception as e:
        pass
    for lig in OLDB_LIGLER:
        try: maclar += oldb_maclar(lig)
        except Exception: pass
    a = ayar_yukle().get("api_anahtar","").strip()
    if a:
        for lig in (203, 39, 78):   # Super Lig + EPL + Bundesliga
            r = af_maclar(lig)
            if not r.get("hata"): maclar += r["maclar"]
    return maclar

if __name__ == "__main__":
    print("=== CIKTI TESTI ===")
    m = tum_maclar()
    print("Toplam mac:", len(m))
    oyn = [x for x in m if x["oynandi"] and x["ev_gol"] is not None]
    print("Oynanmis:", len(oyn))
    for x in oyn[:5]:
        print(f"  {x['lig_adi'][:18]:20s} {x['ev'][:18]:20s} {x['ev_gol']}-{x['dep_gol']} {x['dep'][:18]}")
    print()
    print("Bundesliga tablosu (ilk 3):")
    for t in oldb_tablo("bl1")[:3]:
        print(f"  {t['sira']}. {t['takim'][:22]:24s} {t['mac']}m {t['puan']}p")
