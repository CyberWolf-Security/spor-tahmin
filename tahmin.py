"""
Spor Mac Tahmin — Monte Carlo Simulasyon (v2 - duzeltilmis gol modeli)
"""
import json, math, random, os
from collections import defaultdict

VERI_DOSYA = os.path.join(os.path.dirname(__file__), "veri", "maclar.json")

def veri_yukle():
    if os.path.exists(VERI_DOSYA):
        with open(VERI_DOSYA, encoding="utf-8") as f:
            return json.load(f)
    return {"maclar": []}

def takim_gucu(maclar):
    """Lig ortalamasina gore hucum/savunma katsayilari"""
    # Lig ortalamalari
    toplam_ev_gol = sum(m["ev_gol"] for m in maclar)
    toplam_dep_gol = sum(m["dep_gol"] for m in maclar)
    n = len(maclar)
    lig_ev_ort = toplam_ev_gol / n if n else 1.4      # ev sahibi ort gol
    lig_dep_ort = toplam_dep_gol / n if n else 1.1    # deplasman ort gol

    ev_at = defaultdict(float); ev_mac = defaultdict(int)
    dep_at = defaultdict(float); dep_mac = defaultdict(int)
    ev_yen = defaultdict(float); dep_yen = defaultdict(float)
    puan = defaultdict(int); mac_s = defaultdict(int)

    for m in maclar:
        ev, dep, eg, dg = m["ev"], m["dep"], m["ev_gol"], m["dep_gol"]
        ev_at[ev] += eg; ev_mac[ev] += 1; ev_yen[ev] += dg
        dep_at[dep] += dg; dep_mac[dep] += 1; dep_yen[dep] += eg
        mac_s[ev] += 1; mac_s[dep] += 1
        if eg > dg: puan[ev] += 3
        elif eg < dg: puan[dep] += 3
        else: puan[ev] += 1; puan[dep] += 1

    guc = {}
    for t in mac_s:
        # Evde atak/savunma gucu (lig ort = 1.0)
        ev_huc = (ev_at[t]/ev_mac[t]) / lig_ev_ort if ev_mac[t] else 1.0
        ev_sav = (ev_yen[t]/ev_mac[t]) / lig_dep_ort if ev_mac[t] else 1.0
        dep_huc = (dep_at[t]/dep_mac[t]) / lig_dep_ort if dep_mac[t] else 1.0
        dep_sav = (dep_yen[t]/dep_mac[t]) / lig_ev_ort if dep_mac[t] else 1.0
        guc[t] = {
            "ev_huc": ev_huc, "ev_sav": ev_sav,
            "dep_huc": dep_huc, "dep_sav": dep_sav,
            "mac": mac_s[t], "puan": puan[t],
            "ppg": puan[t]/mac_s[t] if mac_s[t] else 1.0
        }
    return guc, {"lig_ev_ort": lig_ev_ort, "lig_dep_ort": lig_dep_ort}

def beklenen_gol(ev, dep, guc, lig):
    """Ev sahibinin ve deplasmanin beklenen golleri"""
    g1, g2 = guc[ev], guc[dep]
    # Ev sahibinin hucumu x deplasmanin savunmasi x lig ev ortalamasi
    e = g1["ev_huc"] * g2["dep_sav"] * lig["lig_ev_ort"]
    d = g2["dep_huc"] * g1["ev_sav"] * lig["lig_dep_ort"]
    return max(0.2, min(5.0, e)), max(0.2, min(5.0, d))

def _poisson_uret(lam):
    """Poisson dagilimindan gol uret"""
    L = math.exp(-lam); k = 0; p = 1.0
    while True:
        k += 1; p *= random.random()
        if p <= L: return k - 1

def mac_simule(ev, dep, guc, lig, n=10000):
    if ev not in guc or dep not in guc: return None
    e_b, d_b = beklenen_gol(ev, dep, guc, lig)
    ev_kaz = ber = dep_kaz = 0
    skorlar = defaultdict(int); t_ev = t_dep = 0
    ust25 = kg = 0

    for _ in range(n):
        a = min(7, _poisson_uret(e_b))
        b = min(7, _poisson_uret(d_b))
        skorlar[f"{a}-{b}"] += 1
        t_ev += a; t_dep += b
        if a > b: ev_kaz += 1
        elif a < b: dep_kaz += 1
        else: ber += 1
        if a + b > 2.5: ust25 += 1
        if a > 0 and b > 0: kg += 1

    en_olasi = sorted(skorlar.items(), key=lambda x: -x[1])[:6]
    return {
        "ev": ev, "dep": dep,
        "ev_kazanma": round(100*ev_kaz/n, 1),
        "beraberlik": round(100*ber/n, 1),
        "dep_kazanma": round(100*dep_kaz/n, 1),
        "beklenen_skor": f"{t_ev/n:.2f} - {t_dep/n:.2f}",
        "ev_beklenen_gol": round(e_b, 2),
        "dep_beklenen_gol": round(d_b, 2),
        "en_olasi_skorlar": [(s, round(100*c/n, 1)) for s, c in en_olasi],
        "ust_25": round(100*ust25/n, 1),
        "alt_25": round(100*(n-ust25)/n, 1),
        "kg_var": round(100*kg/n, 1),
        "iy_ust_05": round(100*(1-math.exp(-(e_b+d_b)*0.45)), 1),
        "mac_sayisi": n
    }

def puan_tablosu(guc):
    liste = sorted(guc.items(), key=lambda x: (-x[1]["ppp"] if False else -x[1]["ppp"]))
    liste = sorted(guc.items(), key=lambda x: -x[1]["ppp"]) if False else sorted(guc.items(), key=lambda x: -x[1]["ppp"])
    liste = sorted(guc.items(), key=lambda x: -x[1]["ppp"])
    out = []
    for i, (t, g) in enumerate(liste, 1):
        out.append({"sira": i, "takim": t, "mac": g["mac"],
                    "puan": g["puan"], "ppg": round(g["ppg"], 2)})
    return out

if __name__ == "__main__":
    d = veri_yukle()
    guc, lig = takim_gucu(d["maclar"])
    print(f"Mac: {len(d['maclar'])} | Takim: {len(guc)}")
    print(f"Lig ort: ev {lig['lig_ev_ort']:.2f} / dep {lig['lig_dep_ort']:.2f}")
