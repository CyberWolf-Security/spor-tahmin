"""
Tum olasilik motoru + Bahis Ajani (LLM yok, saf istatistik)
"""
import math, random
from collections import defaultdict

def _poisson(lam, k):
    return (lam**k) * math.exp(-lam) / math.factorial(k)

def _uret(lam):
    L = math.exp(-lam); k = 0; p = 1.0
    while True:
        k += 1; p *= random.random()
        if p <= L: return k - 1

def beklenen_gol(ev, dep, guc, lig):
    g1, g2 = guc[ev], guc[dep]
    e = g1["ev_huc"] * g2["dep_sav"] * lig["lig_ev_ort"]
    d = g2["dep_huc"] * g1["ev_sav"] * lig["lig_dep_ort"]
    return max(0.2, min(5.0, e)), max(0.2, min(5.0, d))

def tum_olasiliklar(ev, dep, guc, lig, n=1000000):
    """Butun olasiliklari hesapla (Monte Carlo + Poisson)"""
    if ev not in guc or dep not in guc: return None
    e_b, d_b = beklenen_gol(ev, dep, guc, lig)

    ev_k=ber=dep_k=0
    skorlar=defaultdict(int)
    toplam=defaultdict(int)
    kg_v=kg_y=0
    iy_ev=iy_dep=iy_ber=0
    t_ev=t_dep=0
    # ilk yari orani
    IY = 0.46

    for _ in range(n):
        a=_uret(e_b); b=_uret(d_b)
        ev_k += 1 if a>b else 0
        dep_k += 1 if a<b else 0
        ber += 1 if a==b else 0
        skorlar[f"{a}-{b}"]+=1
        toplam[a+b]+=1
        kg_v += 1 if (a>0 and b>0) else 0
        kg_y += 1 if (a==0 or b==0) else 0
        t_ev+=a; t_dep+=b
        # ilk yari (gollerin %46'si)
        ia=_uret(e_b*IY); ib=_uret(d_b*IY)
        if ia>ib: iy_ev+=1
        elif ia<ib: iy_dep+=1
        else: iy_ber+=1

    y=_yuzde
    out = {
        "ev":ev,"dep":dep,
        "beklenen_skor": f"{t_ev/n:.2f} - {t_dep/n:.2f}",
        "ev_beklenen_gol": round(e_b,2), "dep_beklenen_gol": round(d_b,2),
        # 1X2
        "ev_kazanma": y(ev_k,n), "beraberlik": y(ber,n), "dep_kazanma": y(dep_k,n),
        # Cifte sans
        "1X": y(ev_k+ber,n), "12": y(ev_k+dep_k,n), "X2": y(ber+dep_k,n),
        # Skorlar (ilk 12)
        "skorlar": sorted([(s,y(c,n)) for s,c in skorlar.items()], key=lambda x:-x[1])[:12],
        # Toplam gol dagilimi
        "toplam_gol": {k: y(v,n) for k,v in sorted(toplam.items())[:9]},
        # Alt/Ust
        # Karşılıklı gol
        "kg_var": y(kg_v,n), "kg_yok": y(kg_y,n),
        # Ilk yari
        "iy_ev": y(iy_ev,n), "iy_ber": y(iy_ber,n), "iy_dep": y(iy_dep,n),
        # Ilk yari gol
        "iy_05_ust": None, "iy_15_ust": None,
        "mac_sayisi": n
    }
    # Alt/Ust serisi (Monte Carlo sonuclarindan)
    for eşik, ad in [(0.5,"05"),(1.5,"15"),(2.5,"25"),(3.5,"35"),(4.5,"45"),(5.5,"55")]:
        alt = sum(c for k,c in toplam.items() if k < eşik) if eşik%1==0.5 else 0
        # eşik X.5 -> k <= int(eşik)
        lim = int(eşik)
        alt = sum(c for k,c in toplam.items() if k <= lim)
        ust = n - alt
        out[f"alt_{ad}"] = y(alt,n)
        out[f"ust_{ad}"] = y(ust,n)
    # ilk yari ust
    def iy_ust(esik):
        # Poisson: ilk yari lambda = toplam*IY
        lam = (e_b+d_b)*IY
        p_alt = sum(_poisson(lam,k) for k in range(0, int(esik)+1)) if esik%1==0.5 else sum(_poisson(lam,k) for k in range(0, int(esik)+1))
        return y(1-p_alt, 1)
    out["iy_05_ust"] = y(1-sum(_poisson((e_b+d_b)*IY,k) for k in range(0,1)),1)
    out["iy_15_ust"] = y(1-sum(_poisson((e_b+d_b)*IY,k) for k in range(0,2)),1)
    out["iy_05_alt"] = y(sum(_poisson((e_b+d_b)*IY,k) for k in range(0,1)),1)
    out["iy_15_alt"] = y(sum(_poisson((e_b+d_b)*IY,k) for k in range(0,2)),1)
    # Gol araliklari (tek/cift)
    tek = sum(c for k,c in toplam.items() if k%2==1)
    out["tek_gol"] = y(tek,n); out["cift_gol"] = y(n-tek,n)
    # Ikinci yari ust 0.5 / 1.5
    lam2 = (e_b+d_b)*(1-IY)
    out["iy2_05_ust"] = y(1-sum(_poisson(lam2,k) for k in range(0,1)),1)
    out["iy2_15_ust"] = y(1-sum(_poisson(lam2,k) for k in range(0,2)),1)
    return out

def _yuzde(x, n):
    return round(100.0*x/n, 1) if n else 0.0

# ══ BAHIS AJANI (kural tabanli) ══
def ajan_analiz(olas, ev, dep):
    """Sonuclari yorumlar, tavsiye uretir"""
    tavsiyeler = []
    uyarilar = []

    ev_k = olas["ev_kazanma"]; ber = olas["beraberlik"]; dp_k = olas["dep_kazanma"]

    # 1) En yuksek olasilik
    en_y = max(ev_k, ber, dp_k)
    if en_y == ev_k:
        sonuc = "EV SAHİBİ KAZANIR"; guven = "YÜKSEK" if ev_k >= 55 else "ORTA"
    elif en_y == dp_k:
        sonuc = "DEPLASMAN KAZANIR"; guven = "YÜKSEK" if dp_k >= 55 else "ORTA"
    else:
        sonuc = "BERABERE"; guven = "YÜKSEK" if ber >= 38 else "ORTA"
    tavsiyeler.append({"tip":"1X2", "tavsiye":sonuc, "olasilik":en_y, "guven":guven})

    # 2) BANKO (cok yuksek)
    if ev_k >= 65:
        tavsiyeler.append({"tip":"BANKO","tavsiye":f"{ev} kazanır","olasilik":ev_k,"guven":"ÇOK YÜKSEK"})
    elif dp_k >= 65:
        tavsiyeler.append({"tip":"BANKO","tavsiye":f"{dep} kazanır","olasilik":dp_k,"guven":"ÇOK YÜKSEK"})
    elif ev_k >= 50 or dp_k >= 50:
        t = ev if ev_k>=50 else dep
        tavsiyeler.append({"tip":"SAĞLAM","tavsiye":f"{t} kazanır","olasilik":max(ev_k,dp_k),"guven":"YÜKSEK"})

    # 3) Cifte sans (guvenli)
    kazanan_taraf = "EV" if ev_k>=dp_k else "DEP"
    cift = max(olas["1X"], olas["X2"])
    cift_ad = "1X (Ev/Ber)" if olas["1X"]>=olas["X2"] else "X2 (Ber/Dep)"
    if cift >= 72:
        tavsiyeler.append({"tip":"ÇİFTE ŞANS","tavsiye":cift_ad,"olasilik":cift,"guven":"YÜKSEK"})

    # 4) Gol bahisleri
    if olas["ust_25"] >= 60:
        tavsiyeler.append({"tip":"GOL","tavsiye":"Üst 2.5 gol","olasilik":olas["ust_25"],"guven":"YÜKSEK" if olas["ust_25"]>=70 else "ORTA"})
    elif olas["alt_25"] >= 60:
        tavsiyeler.append({"tip":"GOL","tavsiye":"Alt 2.5 gol","olasilik":olas["alt_25"],"guven":"YÜKSEK" if olas["alt_25"]>=70 else "ORTA"})

    if olas["kg_var"] >= 65:
        tavsiyeler.append({"tip":"KG","tavsiye":"Karşılıklı gol VAR","olasilik":olas["kg_var"],"guven":"YÜKSEK"})
    elif olas["kg_yok"] >= 65:
        tavsiyeler.append({"tip":"KG","tavsiye":"Karşılıklı gol YOK","olasilik":olas["kg_yok"],"guven":"YÜKSEK"})

    # 5) Alt/ust serisi
    for ad, etiket in [("15","1.5"),("25","2.5"),("35","3.5")]:
        u = olas.get(f"ust_{ad}",0); a = olas.get(f"alt_{ad}",0)
        if u >= 75:
            tavsiyeler.append({"tip":"ALT/ÜST","tavsiye":f"Üst {etiket}","olasilik":u,"guven":"YÜKSEK"})
        elif a >= 75:
            tavsiyeler.append({"tip":"ALT/ÜST","tavsiye":f"Alt {etiket}","olasilik":a,"guven":"YÜKSEK"})

    # 6) Ilk yari
    if olas["iy_05_ust"] >= 70:
        tavsiyeler.append({"tip":"İY","tavsiye":"İlk yarı 0.5 ÜST (gol olur)","olasilik":olas["iy_05_ust"],"guven":"ORTA"})

    # RISK uyarilari
    if abs(ev_k - dp_k) < 8:
        uyarilar.append(f"⚠️ Takımlar çok yakın (Ev %{ev_k} - Dep %{dp_k}) — beraberlik riski yüksek")
    if olas["alt_25"] >= 55:
        uyarilar.append(f"⚠️ Düşük gollü maç bekleniyor (Alt 2.5: %{olas['alt_25']})")
    if ber >= 33:
        uyarilar.append(f"⚠️ Beraberlik ihtimali yüksek (%{ber})")
    if olas["ev_beklenen_gol"] + olas["dep_beklenen_gol"] < 2.0:
        uyarilar.append("⚠️ Toplam gol beklentisi düşük (2.0 altı)")

    # Genel guven skoru
    if tavsiyeler:
        en_iyi = max(tavsiyeler, key=lambda x: x["olasilik"])
        skor = en_iyi["olasilik"]
    else:
        en_iyi = None; skor = 50

    # Oneri cumlesi
    if skor >= 75:
        genel = f"🎯 NET TERCİH: {en_iyi['tavsiye']} (%{en_iyi['olasilik']})"
    elif skor >= 62:
        genel = f"👍 MAKUL TERCİH: {en_iyi['tavsiye']} (%{en_iyi['olasilik']})"
    else:
        genel = "🤔 BELİRSİZ MAÇ — yüksek riskli, bahis önerilmez"

    return {
        "tavsiyeler": sorted(tavsiyeler, key=lambda x:-x["olasilik"]),
        "uyarilar": uyarilar,
        "genel": genel,
        "guven_skoru": round(skor,1)
    }

if __name__ == "__main__":
    import sys; sys.path.insert(0,"/tmp/spor")
    from tahmin import veri_yukle, takim_gucu as tg
    import flashscore
    m = flashscore.maclari_cek()
    oyn = [{"ev":x["ev"],"dep":x["dep"],"ev_gol":x["ev_gol"],"dep_gol":x["dep_gol"]} for x in m if x["oynandi"]]
    guc, lig = tg(oyn)
    o = tum_olasiliklar("Galatasaray","Fenerbahçe", guc, lig, 1000000)
    print("=== TUM OLASILIKLAR ===")
    print(f"1X2: {o['ev_kazanma']} / {o['beraberlik']} / {o['dep_kazanma']}")
    print(f"Alt/Ust 2.5: {o['alt_25']} / {o['ust_25']}")
    print(f"KG: {o['kg_var']} / {o['kg_yok']}")
    print(f"IY: {o['iy_ev']}/{o['iy_ber']}/{o['iy_dep']} | IY 0.5 ust: {o['iy_05_ust']}")
    print(f"Toplam gol: {o['toplam_gol']}")
    print("\n=== AJAN ===")
    a = ajan_analiz(o, "Galatasaray","Fenerbahçe")
    print(a["genel"])
    for t in a["tavsiyeler"][:6]:
        print(f"  [{t['tip']}] {t['tavsiye']} — %{t['olasilik']} ({t['guven']})")
    for u in a["uyarilar"]:
        print(" ", u)
