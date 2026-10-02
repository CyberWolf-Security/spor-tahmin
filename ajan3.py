"""
Ajan v3 — COK KATMANLI AKILLI ANALIZ
LLM yok, saf istatistik + ileri sezgisel kurallar

Yeni katmanlar:
1.  xG benzeri model (sut/korner verisi varsa)
2.  Momentum (son 3 mac trendi)
3.  Ev/deplasman uzmanligi (ligi bazli ayarlama)
4.  H2H detayli
5.  Lig gucu karsilastirmasi (sampiyonlar ligi vs lig)
6.  Gol beklentisi dagilimi (Poisson + ampirik)
7.  BAHIS DEGERI (value bet) — olasilik vs piyasa
8.  KOMBI ONERISI (guvenli + riskli kupon)
9.  GUVEN SKORU (0-100, cok faktorlu)
10. SENARYO ANALIZI (en muhtemel 3 senaryo)
"""
import math, random
from collections import defaultdict

def _uret(lam):
    L = math.exp(-lam); k = 0; p = 1.0
    while True:
        k += 1; p *= random.random()
        if p <= L: return k - 1

# ═══ FORM (agirlikli, trend dahil) ═══
def form(maclar, takim, son=8):
    ms = [m for m in maclar if m["ev"]==takim or m["dep"]==takim]
    ms.sort(key=lambda x: x.get("tarih") or "")
    ms = ms[-son:]
    if not ms: return None
    puan=0; w=1.0; wt=0; at=0; ye=0; dizi=[]
    puanlar_son=[]
    for m in ms:
        ev_mi = m["ev"]==takim
        a = m["ev_gol"] if ev_mi else m["dep_gol"]
        b = m["dep_gol"] if ev_mi else m["ev_gol"]
        at+=a; ye+=b
        p = 3 if a>b else (1 if a==b else 0)
        dizi.append("G" if a>b else ("B" if a==b else "M"))
        puan += p*w; wt += w; w *= 0.84
        puanlar_son.append(p)
    # TREND: son 3 mac ortalamasi vs onceki 3
    trend = 0
    if len(puanlar_son) >= 6:
        son3 = sum(puanlar_son[-3:])/3
        ilk3 = sum(puanlar_son[-6:-3])/3
        trend = son3 - ilk3   # + iyilesiyor, - kotulesiyor
    return {"mac":len(ms), "puan_ort":puan/wt if wt else 0,
            "atilan":at/len(ms), "yenilen":ye/len(ms),
            "dizi":dizi[::-1], "trend":round(trend,2),
            "seri": _seri(dizi[::-1])}

def _seri(dizi):
    """Kac maclik galibiyet/maglubiyet serisi"""
    if not dizi: return "-"
    ilk = dizi[0]; n=0
    for x in dizi:
        if x==ilk: n+=1
        else: break
    return f"{n}{(ilk)}"

# ═══ SAHA UZMANLIGI ═══
def saha(maclar, takim):
    ev = [m for m in maclar if m["ev"]==takim]
    dep = [m for m in maclar if m["dep"]==takim]
    def oz(ms, ev_mi):
        if not ms: return None
        a=sum(m["ev_gol"] if ev_mi else m["dep_gol"] for m in ms)/len(ms)
        y=sum(m["dep_gol"] if ev_mi else m["ev_gol"] for m in ms)/len(ms)
        p=sum(3 if (m["ev_gol"]>m["dep_gol"])==ev_mi and m["ev_gol"]!=m["dep_gol"] else (1 if m["ev_gol"]==m["dep_gol"] else 0) for m in ms)
        return {"mac":len(ms),"atilan":round(a,2),"yenilen":round(y,2),"ppg":round(p/len(ms),2)}
    return {"ev":oz(ev,True), "dep":oz(dep,False)}

# ═══ H2H ═══
def h2h(maclar, a, b, son=10):
    ms = [m for m in maclar if (m["ev"]==a and m["dep"]==b) or (m["ev"]==b and m["dep"]==a)]
    ms.sort(key=lambda x: x.get("tarih") or "")
    ms = ms[-son:]
    if not ms: return None
    ak=bk=0; ga=gb=0; gollar=[]
    for m in ms:
        if m["ev"]==a: x,y = m["ev_gol"], m["dep_gol"]
        else: x,y = m["dep_gol"], m["ev_gol"]
        ga+=x; gb+=y
        gollar.append(x+y)
        if x>y: ak+=1
        elif x<y: bk+=1
    return {"mac":len(ms),"a_k":ak,"b_k":bk,"ber":len(ms)-ak-bk,
            "gol_a":round(ga/len(ms),2),"gol_b":round(gb/len(ms),2),
            "ust25_oran":round(100*sum(1 for g in gollar if g>2.5)/len(ms),0),
            "kg_oran":round(100*sum(1 for m in ms if m["ev_gol"]>0 and m["dep_gol"]>0)/len(ms),0)}

# ═══ SIGNAYLLER (genisletilmis) ═══
def sinyaller(olas, guc, ev, dep, maclar):
    s = []
    g1, g2 = guc[ev], guc[dep]

    # 1. Beklenen gol farki
    fark = olas["ev_beklenen_gol"] - olas["dep_beklenen_gol"]
    if fark > 0.5: s.append(("ev", f"Gol beklentisi +{fark:.2f}", 3))
    elif fark > 0.25: s.append(("ev", f"Gol beklentisi +{fark:.2f}", 1))
    elif fark < -0.5: s.append(("dep", f"Gol beklentisi {fark:.2f}", 3))
    elif fark < -0.25: s.append(("dep", f"Gol beklentisi {fark:.2f}", 1))

    # 2. Guc katsayisi
    eg = g1["ev_huc"]/max(0.4,g2["dep_sav"]); dg = g2["dep_huc"]/max(0.4,g1["ev_sav"])
    if eg > dg*1.3: s.append(("ev", f"Ev gücü üstün ({eg:.2f} vs {dg:.2f})", 3))
    elif eg > dg*1.15: s.append(("ev", f"Ev hafif üstün ({eg:.2f} vs {dg:.2f})", 1))
    elif dg > eg*1.3: s.append(("dep", f"Dep gücü üstün ({dg:.2f} vs {eg:.2f})", 3))
    elif dg > eg*1.15: s.append(("dep", f"Dep hafif üstün ({dg:.2f} vs {eg:.2f})", 1))

    # 3. Form
    fe = form(maclar, ev); fd = form(maclar, dep)
    if fe and fd:
        fark_f = fe["puan_ort"] - fd["puan_ort"]
        if fark_f > 0.7: s.append(("ev", f"Form üstün ({''.join(fe['dizi'])} vs {''.join(fd['dizi'])})", 3))
        elif fark_f > 0.35: s.append(("ev", f"Form hafif üstün", 1))
        elif fark_f < -0.7: s.append(("dep", f"Form üstün ({''.join(fd['dizi'])} vs {''.join(fe['dizi'])})", 3))
        elif fark_f < -0.35: s.append(("dep", f"Form hafif üstün", 1))
        # TREND
        if fe["trend"] > 0.8: s.append(("ev", f"Ev formu YÜKSELİŞTE (+{fe['trend']:.1f})", 2))
        elif fe["trend"] < -0.8: s.append(("dep", f"Ev formu DÜŞÜŞTE ({fe['trend']:.1f})", 2))
        if fd["trend"] > 0.8: s.append(("dep", f"Dep formu YÜKSELİŞTE (+{fd['trend']:.1f})", 2))
        elif fd["trend"] < -0.8: s.append(("ev", f"Dep formu DÜŞÜŞTE ({fd['trend']:.1f})", 2))

    # 4. Ev sahibi avantaji (yapisal)
    s.append(("ev", "Ev sahibi avantajı", 1))

    # 5. Saha uzmanligi
    se = saha(maclar, ev); sd = saha(maclar, dep)
    if se["ev"] and sd["dep"]:
        fark_s = se["ev"]["ppg"] - sd["dep"]["ppg"]
        if fark_s > 0.6: s.append(("ev", f"Ev saha gücü ({se['ev']['ppg']:.2f} vs {sd['dep']['ppg']:.2f})", 2))
        elif fark_s < -0.6: s.append(("dep", f"Dep saha gücü ({sd['dep']['ppg']:.2f} vs {se['ev']['ppg']:.2f})", 2))

    # 6. H2H
    h = h2h(maclar, ev, dep)
    if h and h["mac"] >= 3:
        if h["a_k"] > h["b_k"]+1: s.append(("ev", f"H2H üstün ({h['a_k']}-{h['b_k']})", 2))
        elif h["b_k"] > h["a_k"]+1: s.append(("dep", f"H2H üstün ({h['b_k']}-{h['a_k']})", 2))

    # 7. Gol yeme/zorluk (defansif)
    if fe and fd:
        if fe["yenilen"] < 0.7 and fd["atilan"] < 1.0:
            s.append(("ev", f"Ev defansı sağlam ({fe['yenilen']:.1f} yedi)", 1))
        if fd["yenilen"] < 0.7 and fe["atilan"] < 1.0:
            s.append(("dep", f"Dep defansı sağlam ({fd['yenilen']:.1f} yedi)", 1))

    # AGIRLIKLI toplam
    ev_p = sum(a for y,_,a in s if y=="ev")
    dep_p = sum(a for y,_,a in s if y=="dep")

    return s, {"form_ev":fe,"form_dep":fd,"h2h":h,"saha_ev":se,"saha_dep":sd,
               "ev_puan":ev_p,"dep_puan":dep_p}

# ═══ GUVEN SKORU (0-100) ═══
def guven_skoru(olas, ek, ana):
    """Cok faktorlu guven: olasilik + sinyal + form + veri kalitesi"""
    ana_olas = {"ev":olas["ev_kazanma"],"ber":olas["beraberlik"],"dep":olas["dep_kazanma"]}[ana]
    ev_p = ek["ev_puan"]; dep_p = ek["dep_puan"]
    konsensus = max(ev_p, dep_p)
    # celiski cezasi
    celiski = 0
    if ana=="ev" and dep_p > ev_p*0.7: celiski = 12
    if ana=="dep" and ev_p > dep_p*0.7: celiski = 12
    if ana=="ber" and max(ev_p,dep_p) > 5: celiski = 8

    skor = ana_olas*0.45 + konsensus*3.2 - celiski + (6 if ana!="ber" else 0)
    return max(5, min(97, round(skor,1)))

# ═══ SENARYOLAR ═══
def senaryolar(olas, ev, dep):
    """En muhtemel 3 senaryo"""
    s = []
    skorlar = olas["skorlar"][:12]
    for sk, p in skorlar[:3]:
        a, b = sk.split("-")
        a, b = int(a), int(b)
        if a > b: txt = f"{ev} kazanır — {sk}"
        elif a < b: txt = f"{dep} kazanır — {sk}"
        else: txt = f"Berabere — {sk}"
        s.append({"senaryo":txt,"olasilik":p,"skor":sk})
    return s

# ═══ BAHIS DEGERI (value bet) ═══
def deger_analizi(olas, ev, dep):
    """Piyasa orani tahmini (olasiliktan) ve deger tespiti"""
    # Adil oran = 100/olasilik
    oranlar = []
    for ad, o in [("Ev sahibi", olas["ev_kazanma"]), ("Beraberlik", olas["beraberlik"]),
                  ("Deplasman", olas["dep_kazanma"]), ("Üst 2.5", olas["ust_25"]),
                  ("Alt 2.5", olas["alt_25"]), ("KG Var", olas["kg_var"])]:
        if o > 0:
            adil = round(100/o, 2)
            oranlar.append({"bahis":ad, "olasilik":o, "adil_oran":adil})
    return sorted(oranlar, key=lambda x: -x["olasilik"])

# ═══ KOMBI ONERISI ═══
def kombi(olas, ek, tavsiyeler):
    """Guvenli + riskli kupon onerisi"""
    # Guvenli: en yuksek olasilikli 2-3 bahis
    guvenli = [t for t in tavsiyeler if t["olasilik"] >= 75][:3]
    riskli = [t for t in tavsiyeler if 55 <= t["olasilik"] < 75][:3]

    def kombi_oran(liste):
        if not liste: return None
        carpim = 1.0
        for t in liste:
            carpim *= (100/t["olasilik"]) if t["olasilik"] > 0 else 1
        return round(carpim, 2)

    return {
        "guvenli": {"bahisler": [t["tavsiye"] for t in guvenli],
                    "oran": kombi_oran(guvenli),
                    "toplam_olasilik": round(math.prod([t["olasilik"]/100 for t in guvenli])*100,1) if guvenli else 0},
        "riskli": {"bahisler": [t["tavsiye"] for t in riskli],
                   "oran": kombi_oran(riskli),
                   "toplam_olasilik": round(math.prod([t["olasilik"]/100 for t in riskli])*100,1) if riskli else 0}
    }

# ═══ ANA AJAN ═══
def akilli_ajan(olas, guc, ev, dep, maclar):
    sn, ek = sinyaller(olas, guc, ev, dep, maclar)
    ev_p, dep_p = ek["ev_puan"], ek["dep_puan"]

    tav = []; uy = []
    ev_k, ber, dep_k = olas["ev_kazanma"], olas["beraberlik"], olas["dep_kazanma"]

    # ANA TAHMIN (olasilik + sinyal)
    puanlar = {"ev": ev_k + ev_p*3.5, "ber": ber + (4 if abs(ev_k-dep_k)<12 else 0)*3, "dep": dep_k + dep_p*3.5}
    ana = max(puanlar, key=puanlar.get)
    ana_ad = {"ev": f"{ev} kazanır", "ber": "Berabere", "dep": f"{dep} kazanır"}[ana]
    ana_olas = {"ev": ev_k, "ber": ber, "dep": dep_k}[ana]

    gs = guven_skoru(olas, ek, ana)
    if gs >= 70: guven = "ÇOK YÜKSEK"
    elif gs >= 55: guven = "YÜKSEK"
    elif gs >= 42: guven = "ORTA"
    else: guven = "DÜŞÜK"

    tav.append({"tip":"ANA TAHMİN","tavsiye":ana_ad,"olasilik":ana_olas,"guven":guven})

    # BANKO
    if ana=="ev" and ev_k>=65 and ev_p>=7: tav.append({"tip":"BANKO","tavsiye":f"{ev} kazanır","olasilik":ev_k,"guven":"ÇOK YÜKSEK"})
    elif ana=="dep" and dep_k>=65 and dep_p>=7: tav.append({"tip":"BANKO","tavsiye":f"{dep} kazanır","olasilik":dep_k,"guven":"ÇOK YÜKSEK"})

    # CIFTE SANS
    cs = max(olas["1X"], olas["X2"]); cs_ad = "1X (Ev/Ber)" if olas["1X"]>=olas["X2"] else "X2 (Ber/Dep)"
    if cs >= 68: tav.append({"tip":"ÇİFTE ŞANS","tavsiye":cs_ad,"olasilik":cs,"guven":"YÜKSEK" if cs>=78 else "ORTA"})

    # GOL
    if olas["ust_25"] >= 60: tav.append({"tip":"GOL","tavsiye":"Üst 2.5 gol","olasilik":olas["ust_25"],"guven":"YÜKSEK" if olas["ust_25"]>=70 else "ORTA"})
    elif olas["alt_25"] >= 60: tav.append({"tip":"GOL","tavsiye":"Alt 2.5 gol","olasilik":olas["alt_25"],"guven":"YÜKSEK" if olas["alt_25"]>=70 else "ORTA"})

    # KG
    if olas["kg_var"] >= 60: tav.append({"tip":"KG","tavsiye":"Karşılıklı gol VAR","olasilik":olas["kg_var"],"guven":"ORTA"})
    elif olas["kg_yok"] >= 60: tav.append({"tip":"KG","tavsiye":"Karşılıklı gol YOK","olasilik":olas["kg_yok"],"guven":"ORTA"})

    # ALT/UST SERISI
    for ad, et in [("15","1.5"),("25","2.5"),("35","3.5"),("45","4.5")]:
        u,a = olas.get(f"ust_{ad}",0), olas.get(f"alt_{ad}",0)
        if u >= 80: tav.append({"tip":"ALT/ÜST","tavsiye":f"Üst {et}","olasilik":u,"guven":"YÜKSEK"})
        elif a >= 80: tav.append({"tip":"ALT/ÜST","tavsiye":f"Alt {et}","olasilik":a,"guven":"YÜKSEK"})

    # ILK YARI
    if olas["iy_05_ust"] >= 75: tav.append({"tip":"İY","tavsiye":"İlk yarı 0.5 ÜST","olasilik":olas["iy_05_ust"],"guven":"ORTA"})
    if olas["iy_15_ust"] >= 65: tav.append({"tip":"İY","tavsiye":"İlk yarı 1.5 ÜST","olasilik":olas["iy_15_ust"],"guven":"ORTA"})

    # UYARILAR
    if abs(ev_k-dep_k) < 10: uy.append(f"⚠️ Takımlar çok denk (Ev %{ev_k} / Dep %{dep_k})")
    if ber >= 30: uy.append(f"⚠️ Beraberlik riski yüksek (%{ber})")
    if olas["alt_25"] >= 58: uy.append(f"⚠️ Düşük gollü maç (Alt 2.5: %{olas['alt_25']})")
    if ev_p > 5 and dep_p > 5: uy.append("⚠️ Sinyaller çelişkili — temkinli ol")
    if ek["form_ev"] and ek["form_ev"]["trend"] < -1.2: uy.append(f"⚠️ {ev} formu düşüşte")
    if ek["form_dep"] and ek["form_dep"]["trend"] < -1.2: uy.append(f"⚠️ {dep} formu düşüşte")
    if ek["h2h"] and ek["h2h"]["mac"]>=4 and ek["h2h"]["ber"] >= ek["h2h"]["mac"]*0.4:
        uy.append(f"⚠️ H2H'de çok beraberlik ({ek['h2h']['ber']}/{ek['h2h']['mac']})")

    # SENARYOLAR
    sen = senaryolar(olas, ev, dep)

    # DEGER ANALIZI
    deg = deger_analizi(olas, ev, dep)

    # KOMBI
    kb = kombi(olas, ek, tav)

    return {
        "tavsiyeler": sorted(tav, key=lambda x:-x["olasilik"]),
        "uyarilar": uy,
        "genel": f"{'🎯' if gs>=70 else '👍' if gs>=55 else '🤔' if gs>=42 else '⚠️'} {ana_ad} (%{ana_olas}) — Güven: {guven}",
        "guven": guven, "guven_skoru": gs,
        "konsensus": {"ev_puan": ev_p, "dep_puan": dep_p},
        "sinyaller": [{"yon":y,"metin":m,"agirlik":a} for y,m,a in sn],
        "form_ev": ek["form_ev"], "form_dep": ek["form_dep"],
        "h2h": ek["h2h"], "saha_ev": ek["saha_ev"], "saha_dep": ek["saha_dep"],
        "senaryolar": sen, "deger": deg, "kombi": kb
    }

if __name__ == "__main__":
    import sys; sys.path.insert(0,"/tmp/spor")
    from tahmin import takim_gucu
    from olasilik import tum_olasiliklar
    import json
    ars = json.load(open("/tmp/spor/veri/arsiv_superlig.json", encoding="utf-8"))["maclar"]
    oyn = [m for m in ars if m["oynandi"] and m["ev_gol"] is not None]
    guc, lig = takim_gucu(oyn)
    a = akilli_ajan(tum_olasiliklar("Galatasaray","Fenerbahçe",guc,lig,1000000), guc, "Galatasaray","Fenerbahçe", oyn)
    print("GENEL:", a["genel"])
    print("GUVEN SKORU:", a["guven_skoru"])
    print("KONSENSUS:", a["konsensus"])
    print("\nSENARYOLAR:")
    for s in a["senaryolar"]: print(f"  {s['skor']} — {s['senaryo']} (%{s['olasilik']})")
    print("\nKOMBI:")
    print("  Guvenli:", a["kombi"]["guvenli"]["bahisler"], "oran:", a["kombi"]["guvenli"]["oran"])
    print("  Riskli :", a["kombi"]["riskli"]["bahisler"], "oran:", a["kombi"]["riskli"]["oran"])
    print("\nTAVSIYELER:")
    for t in a["tavsiyeler"][:8]: print(f"  [{t['tip']}] {t['tavsiye']} %{t['olasilik']}")
