"""
Gelismis Ajan v2 — cok katmanli analiz
LLM yok, saf istatistik + sezgisel kurallar

Katmanlar:
1. Poisson/Monte Carlo (mevcut)
2. FORM analizi (son 5 mac agirlikli)
3. Ev/Deplasman uzmanligi
4. H2H (karsilikli mac gecmisi)
5. Motivasyon/sezon konumu (puan tablosu)
6. Guven skoru (kac bagimsiz sinyal ayni yonu gosteriyor)
"""
import math, random
from collections import defaultdict

def _uret(lam):
    L = math.exp(-lam); k = 0; p = 1.0
    while True:
        k += 1; p *= random.random()
        if p <= L: return k - 1

# ═══ 1. FORM ANALIZI ═══
def form_analizi(maclar, takim, son=6):
    """Takimin son N macindaki performansi (agirlikli)"""
    ms = [m for m in maclar if (m["ev"]==takim or m["dep"]==takim)]
    ms.sort(key=lambda x: x.get("tarih") or "")
    ms = ms[-son:]
    if not ms: return None
    puan = 0; agirlik_top = 0; atilan = 0; yenilen = 0; w = 1.0
    form_dizisi = []
    for m in ms:
        ev_mi = m["ev"] == takim
        a = m["ev_gol"] if ev_mi else m["dep_gol"]
        y = m["dep_gol"] if ev_mi else m["ev_gol"]
        atilan += a; yenilen += y
        if a > y: p = 3; form_dizisi.append("G")
        elif a < y: p = 0; form_dizisi.append("M")
        else: p = 1; form_dizisi.append("B")
        puan += p * w; agirlik_top += w
        w *= 0.82   # eski maclar daha az onemli
    return {
        "mac": len(ms), "puan_ort": puan/agirlik_top if agirlik_top else 0,
        "atilan_ort": atilan/len(ms), "yenilen_ort": yenilen/len(ms),
        "dizi": form_dizisi[::-1]  # en yeni basta
    }

# ═══ 2. EV/DEPLASMAN UZMANLIGI ═══
def saha_analizi(maclar, takim):
    ev_ms = [m for m in maclar if m["ev"]==takim]
    dep_ms = [m for m in maclar if m["dep"]==takim]
    def ozet(ms, ev_mi):
        if not ms: return None
        a = sum(m["ev_gol"] if ev_mi else m["dep_gol"] for m in ms)/len(ms)
        y = sum(m["dep_gol"] if ev_mi else m["ev_gol"] for m in ms)/len(ms)
        p = sum(3 if (m["ev_gol"]>m["dep_gol"])==ev_mi and m["ev_gol"]!=m["dep_gol"] else (1 if m["ev_gol"]==m["dep_gol"] else 0) for m in ms)
        return {"mac":len(ms),"atilan":round(a,2),"yenilen":round(y,2),"puan_ort":round(p/len(ms),2)}
    return {"ev": ozet(ev_ms, True), "dep": ozet(dep_ms, False)}

# ═══ 3. H2H ═══
def h2h_analizi(maclar, a, b, son=8):
    ms = [m for m in maclar if (m["ev"]==a and m["dep"]==b) or (m["ev"]==b and m["dep"]==a)]
    ms.sort(key=lambda x: x.get("tarih") or "")
    ms = ms[-son:]
    if not ms: return None
    a_k = b_k = 0; gol_a = gol_b = 0
    for m in ms:
        if m["ev"] == a:
            ga, gb = m["ev_gol"], m["dep_gol"]
        else:
            ga, gb = m["dep_gol"], m["ev_gol"]
        gol_a += ga; gol_b += gb
        if ga > gb: a_k += 1
        elif ga < gb: b_k += 1
    return {"mac":len(ms),"a_kazanma":a_k,"b_kazanma":b_k,"beraberlik":len(ms)-a_k-b_k,
            "gol_a":round(gol_a/len(ms),2),"gol_b":round(gol_b/len(ms),2)}

# ═══ 4. BAGIMSIZ SINYALLER ═══
def sinyaller(olas, guc, ev, dep, maclar):
    """Kac bagimsiz sinyal ayni yonu gosteriyor?"""
    s = []
    g1, g2 = guc[ev], guc[dep]

    # 1. Beklenen gol farki
    fark = olas["ev_beklenen_gol"] - olas["dep_beklenen_gol"]
    if fark > 0.45: s.append(("ev", f"Gol beklentisi (+{fark:.2f})"))
    elif fark < -0.45: s.append(("dep", f"Gol beklentisi ({fark:.2f})"))

    # 2. Guc katsayisi (hucum x savunma)
    ev_guc = g1["ev_huc"] / max(0.4, g2["dep_sav"])
    dep_guc = g2["dep_huc"] / max(0.4, g1["ev_sav"])
    if ev_guc > dep_guc*1.25: s.append(("ev", f"Ev gücü üstün ({ev_guc:.2f} vs {dep_guc:.2f})"))
    elif dep_guc > ev_guc*1.25: s.append(("dep", f"Dep gücü üstün ({dep_guc:.2f} vs {ev_guc:.2f})"))

    # 3. FORM
    fe = form_analizi(maclar, ev); fd = form_analizi(maclar, dep)
    if fe and fd:
        if fe["puan_ort"] > fd["puan_ort"] + 0.55: s.append(("ev", f"Form üstün ({''.join(fe['dizi'])} vs {''.join(fd['dizi'])})"))
        elif fd["puan_ort"] > fe["puan_ort"] + 0.55: s.append(("dep", f"Form üstün ({''.join(fd['dizi'])} vs {''.join(fe['dizi'])})"))

    # 4. EV SAHIBI AVANTAJI (yapisal, dusuk agirlik)
    s.append(("ev", "Ev sahibi avantajı (yapısal)"))

    # 5. H2H
    h = h2h_analizi(maclar, ev, dep)
    if h and h["mac"] >= 3:
        if h["a_kazanma"] > h["b_kazanma"]+1: s.append(("ev", f"H2H üstün ({h['a_kazanma']}-{h['b_kazanma']})"))
        elif h["b_kazanma"] > h["a_kazanma"]+1: s.append(("dep", f"H2H üstün ({h['b_kazanma']}-{h['a_kazanma']})"))

    # 6. Saha uzmanligi
    sa_e = saha_analizi(maclar, ev); sa_d = saha_analizi(maclar, dep)
    if sa_e["ev"] and sa_d["dep"]:
        if sa_e["ev"]["puan_ort"] > sa_d["dep"]["puan_ort"]+0.5: s.append(("ev","Ev saha gücü"))
        elif sa_d["dep"]["puan_ort"] > sa_e["ev"]["puan_ort"]+0.5: s.append(("dep","Deplasman saha gücü"))

    return s, {"form_ev":fe, "form_dep":fd, "h2h":h, "saha_ev":sa_e, "saha_dep":sa_d}

# ═══ 5. GELISMIS AJAN ═══
def gelismis_ajan(olas, guc, ev, dep, maclar):
    sn, ek = sinyaller(olas, guc, ev, dep, maclar)

    # Sinyal konsensusu
    ev_sig = len([1 for y,_ in sn if y=="ev"])
    dep_sig = len([1 for y,_ in sn if y=="dep"])

    tav = []; uy = []
    ev_k, ber, dep_k = olas["ev_kazanma"], olas["beraberlik"], olas["dep_kazanma"]

    # ANA TAHMIN: olasilik + sinyal konsensusu
    puanlar = {"ev": ev_k + ev_sig*5, "ber": ber + (3 if abs(ev_k-dep_k)<10 else 0)*4, "dep": dep_k + dep_sig*5}
    ana = max(puanlar, key=puanlar.get)
    ana_ad = {"ev": f"{ev} kazanır", "ber": "Berabere", "dep": f"{dep} kazanır"}[ana]
    ana_olas = {"ev": ev_k, "ber": ber, "dep": dep_k}[ana]

    # Guven: kac sinyal + olasilik
    konsensus = max(ev_sig, dep_sig)
    guven_puan = ana_olas*0.5 + konsensus*9 + (10 if ana!="ber" else 0)
    if guven_puan >= 55: guven = "YÜKSEK"
    elif guven_puan >= 40: guven = "ORTA"
    else: guven = "DÜŞÜK"

    tav.append({"tip":"ANA TAHMİN","tavsiye":ana_ad,"olasilik":ana_olas,
                "guven":guven,"sinyal":konsensus})

    # Sinyal dokumu
    sinyal_ozet = []
    for yon, ad in sn:
        sinyal_ozet.append(f"{'🟢' if yon=='ev' else '🔴'} {ad}")

    # BANKO (guclu sinyal)
    if ev_k >= 62 and ev_sig >= 3:
        tav.append({"tip":"BANKO","tavsiye":f"{ev} kazanır","olasilik":ev_k,"guven":"ÇOK YÜKSEK"})
    elif dep_k >= 62 and dep_sig >= 3:
        tav.append({"tip":"BANKO","tavsiye":f"{dep} kazanır","olasilik":dep_k,"guven":"ÇOK YÜKSEK"})

    # CIFTE SANS (guvenli bahis)
    if max(olas["1X"], olas["X2"]) >= 70:
        ad = "1X (Ev/Ber)" if olas["1X"] >= olas["X2"] else "X2 (Ber/Dep)"
        tav.append({"tip":"ÇİFTE ŞANS","tavsiye":ad,"olasilik":max(olas["1X"],olas["X2"]),"guven":"YÜKSEK"})

    # GOL
    if olas["ust_25"] >= 62:
        tav.append({"tip":"GOL","tavsiye":"Üst 2.5 gol","olasilik":olas["ust_25"],"guven":"YÜKSEK"})
    elif olas["alt_25"] >= 62:
        tav.append({"tip":"GOL","tavsiye":"Alt 2.5 gol","olasilik":olas["alt_25"],"guven":"YÜKSEK"})

    if olas["kg_var"] >= 62:
        tav.append({"tip":"KG","tavsiye":"Karşılıklı gol VAR","olasilik":olas["kg_var"],"guven":"YÜKSEK"})
    elif olas["kg_yok"] >= 62:
        tav.append({"tip":"KG","tavsiye":"Karşılıklı gol YOK","olasilik":olas["kg_yok"],"guven":"YÜKSEK"})

    # Alt/ust serisi en yuksek
    for ad, et in [("15","1.5"),("25","2.5"),("35","3.5")]:
        u, a = olas.get(f"ust_{ad}",0), olas.get(f"alt_{ad}",0)
        if u >= 78: tav.append({"tip":"ALT/ÜST","tavsiye":f"Üst {et}","olasilik":u,"guven":"YÜKSEK"})
        elif a >= 78: tav.append({"tip":"ALT/ÜST","tavsiye":f"Alt {et}","olasilik":a,"guven":"YÜKSEK"})

    # RISK UYARILARI
    if abs(ev_k-dep_k) < 9: uy.append(f"⚠️ Takımlar çok denk (Ev %{ev_k} / Dep %{dep_k})")
    if ber >= 32: uy.append(f"⚠️ Beraberlik riski yüksek (%{ber})")
    if olas["alt_25"] >= 58: uy.append(f"⚠️ Düşük gollü maç beklentisi (Alt 2.5: %{olas['alt_25']})")
    if ek["h2h"] and ek["h2h"]["mac"] >= 3:
        h = ek["h2h"]
        if h["beraberlik"] >= h["mac"]*0.4: uy.append(f"⚠️ H2H'de çok beraberlik ({h['beraberlik']}/{h['mac']})")
    if ev_sig >= 4 and dep_sig >= 4: uy.append("⚠️ Sinyaller çelişkili — dikkatli ol")

    # ORNEK CUMLESI
    fe, fd = ek["form_ev"], ek["form_dep"]
    form_txt = ""
    if fe and fd:
        form_txt = f"Form: {ev} {''.join(fe['dizi'])} ({fe['puan_ort']:.1f} p/m) — {dep} {''.join(fd['dizi'])} ({fd['puan_ort']:.1f} p/m)"

    return {
        "tavsiyeler": sorted(tav, key=lambda x:-x["olasilik"]),
        "uyarilar": uy,
        "genel": f"{'🎯' if guven=='YÜKSEK' else '👍' if guven=='ORTA' else '🤔'} {ana_ad} (%{ana_olas}) — Güven: {guven}",
        "guven": guven, "guven_puan": round(guven_puan,1),
        "konsensus": {"ev": ev_sig, "dep": dep_sig, "toplam": len(sn)},
        "sinyaller": sinyal_ozet,
        "form": form_txt,
        "form_ev": fe, "form_dep": fd,
        "h2h": ek["h2h"],
        "saha_ev": ek["saha_ev"], "saha_dep": ek["saha_dep"]
    }

if __name__ == "__main__":
    import sys; sys.path.insert(0,"/tmp/spor")
    from tahmin import takim_gucu
    from olasilik import tum_olasiliklar
    import fs_feed as fsf
    ms = fsf.tum_gunler(sadece_onemli=False)
    oyn = [{"ev":m["ev"],"dep":m["dep"],"ev_gol":m["ev_gol"],"dep_gol":m["dep_gol"],
            "tarih":m["tarih"]} for m in ms if m["oynandi"] and m["ev_gol"] is not None]
    print("Oynanmis mac:", len(oyn))
    if len(oyn) >= 6:
        guc, lig = takim_gucu(oyn)
        # Ornek mac
        import random
        m = random.choice([x for x in ms if x["oynandi"]])
        o = tum_olasiliklar(m["ev"], m["dep"], guc, lig, 10000)
        a = gelismis_ajan(o, guc, m["ev"], m["dep"], oyn)
        print(f"\n=== {m['ev']} vs {m['dep']} ===")
        print("GENEL:", a["genel"])
        print("KONSENSUS:", a["konsensus"])
        print("FORM:", a["form"])
        print("\nSINYALLER:")
        for s in a["sinyaller"]: print(" ", s)
        print("\nTAVSIYELER:")
        for t in a["tavsiyeler"][:6]: print(f"  [{t['tip']}] {t['tavsiye']} %{t['olasilik']}")
        print("\nUYARILAR:")
        for u in a["uyarilar"]: print(" ", u)
