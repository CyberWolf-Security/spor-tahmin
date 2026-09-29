"""
Tum onemli liglerin takim arsivini cek (veri havuzu buyutme)
Cron'la gunluk calistirilabilir.
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import takim_arsiv as ta

LIGLER = {
    "superlig": ("https://www.flashscore.com.tr/futbol/turkiye/super-lig/", 20),
    "premier":  ("https://www.flashscore.com.tr/futbol/ingiltere/premier-league/", 20),
    "laliga":   ("https://www.flashscore.com.tr/futbol/ispanya/laliga/", 20),
    "seriea":   ("https://www.flashscore.com.tr/futbol/italya/serie-a/", 20),
    "bundes":   ("https://www.flashscore.com.tr/futbol/almanya/bundesliga/", 18),
    "ligue1":   ("https://www.flashscore.com.tr/futbol/fransa/ligue-1/", 18),
    "ucl":      ("https://www.flashscore.com.tr/futbol/avrupa/sampiyonlar-ligi/", 20),
    "uel":      ("https://www.flashscore.com.tr/futbol/avrupa/avrupa-ligi/", 20),
}

def cek(ligler=None, ilerleme=None):
    ligler = ligler or LIGLER
    toplam = {}
    for kod, (url, max_t) in ligler.items():
        try:
            ms = ta.lig_arsivi(url, max_takim=max_t)
            oyn = [m for m in ms if m["oynandi"]]
            for m in ms:
                m["lig_adi"] = kod
                m["bayrak"] = "⚽"
                m["kaynak"] = "Arşiv"
            vr = os.path.join(os.path.dirname(os.path.abspath(__file__)), "veri")
            os.makedirs(vr, exist_ok=True)
            with open(os.path.join(vr, f"arsiv_{kod}.json"), "w", encoding="utf-8") as f:
                json.dump({"maclar": ms}, f, ensure_ascii=False)
            toplam[kod] = len(oyn)
            if ilerleme: ilerleme(kod, len(ms), len(oyn))
        except Exception as e:
            if ilerleme: ilerleme(kod, 0, 0, str(e)[:50])
    return toplam

if __name__ == "__main__":
    def iler(kod, n, oyn, hata=None):
        if hata: print(f"  {kod:10s} HATA: {hata}")
        else: print(f"  {kod:10s} {n:4d} mac ({oyn} oynanmis)")
    print("=== ARSIV CEKIMI ===")
    t = cek(ilerleme=iler)
    print()
    print("TOPLAM:", sum(t.values()), "oynanmis mac")
