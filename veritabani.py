"""
Spor Tahmin - Veri Yoneticisi
Yerel veritabani (JSON dosya) - program kendi verisini tutar
"""
import json, os, csv
from datetime import datetime

VERI_DIZIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "veri")
DB_DOSYA = os.path.join(VERI_DIZIN, "maclar.json")
AYAR_DOSYA = os.path.join(VERI_DIZIN, "ayarlar.json")

def _olustur_dizin():
    os.makedirs(VERI_DIZIN, exist_ok=True)

def db_yukle():
    _olustur_dizin()
    if os.path.exists(DB_DOSYA):
        try:
            with open(DB_DOSYA, encoding="utf-8") as f:
                d = json.load(f)
                if "maclar" not in d: d["maclar"] = []
                if "takimlar" not in d: d["takimlar"] = []
                return d
        except Exception:
            pass
    return {"maclar": [], "takimlar": [], "son_guncelleme": ""}

def db_kaydet(db):
    _olustur_dizin()
    db["son_guncelleme"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Yedek al
    if os.path.exists(DB_DOSYA):
        try:
            os.replace(DB_DOSYA, DB_DOSYA + ".yedek")
        except Exception:
            pass
    with open(DB_DOSYA, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=1)

def mac_ekle(ev, dep, ev_gol, dep_gol, tarih=None, lig="Süper Lig"):
    """Mac ekle (mukerrer kontrolu ile)"""
    db = db_yukle()
    tarih = tarih or datetime.now().strftime("%Y-%m-%d")
    # Mukerrer kontrol
    for m in db["maclar"]:
        if m["ev"] == ev and m["dep"] == dep and m["tarih"] == tarih:
            m["ev_gol"] = ev_gol; m["dep_gol"] = dep_gol
            db_kaydet(db)
            return False   # guncellendi
    db["maclar"].append({
        "ev": ev, "dep": dep, "ev_gol": int(ev_gol), "dep_gol": int(dep_gol),
        "tarih": tarih, "lig": lig
    })
    for t in (ev, dep):
        if t not in db["takimlar"]:
            db["takimlar"].append(t)
    db_kaydet(db)
    return True

def takim_ekle(ad):
    db = db_yukle()
    if ad not in db["takimlar"]:
        db["takimlar"].append(ad)
        db_kaydet(db)
        return True
    return False

def csv_ice_aktar(yol, ayirici=";", baslik_var=True):
    """CSV'den maclari ice aktar (ev;dep;ev_gol;dep_gol;tarih)"""
    eklendi = 0; guncellendi = 0
    with open(yol, encoding="utf-8-sig") as f:
        satirlar = [s.rstrip("\n").rstrip("\r") for s in f if s.strip()]
    if baslik_var and satirlar:
        # Basligi ayiriciya gore kontrol et
        ilk = satirlar[0].split(ayirici)
        if any(x.strip().lower() in ("ev","tarih","ev_gol","skor") for x in ilk):
            satirlar = satirlar[1:]
    for s in satirlar:
        p = s.split(ayirici)
        if len(p) < 4: continue
        try:
            ev, dep = p[0].strip(), p[1].strip()
            eg, dg = int(p[2].strip()), int(p[3].strip())
            trh = p[4].strip() if len(p) > 4 else None
            if mac_ekle(ev, dep, eg, dg, trh): eklendi += 1
            else: guncellendi += 1
        except (ValueError, IndexError):
            continue
    return eklendi, guncellendi

def istatistik():
    db = db_yukle()
    return {
        "mac_sayisi": len(db["maclar"]),
        "takim_sayisi": len(db["takimlar"]),
        "son_guncelleme": db.get("son_guncelleme",""),
        "dosya": DB_DOSYA,
        "boyut_kb": round(os.path.getsize(DB_DOSYA)/1024, 1) if os.path.exists(DB_DOSYA) else 0
    }

def mac_listesi(limit=50):
    db = db_yukle()
    return sorted(db["maclar"], key=lambda x: x.get("tarih",""), reverse=True)[:limit]

def temizle():
    """Tum veriyi sil (yedek alarak)"""
    db = db_yukle()
    if os.path.exists(DB_DOSYA):
        os.replace(DB_DOSYA, DB_DOSYA + ".yedek-" + datetime.now().strftime("%Y%m%d%H%M%S"))
    return True

if __name__ == "__main__":
    print(json.dumps(istatistik(), ensure_ascii=False, indent=2))
