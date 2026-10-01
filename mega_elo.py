"""MEGA AJAN v7 — ELO + ENSEMBLE
Yeni yetenekler:
1. Elo Rating (satranc/futbol rating — kanitlanmis)
2. Ensemble: Poisson + Elo + Form birlestirme
3. H2H (gecmis karsilasma) etkisi
4. Dinlenme gunu (yorgunluk)
"""
import math
import numpy as np
from collections import defaultdict
from datetime import datetime

# ═══════════════════════════════════════════════
#  ELO RATING SISTEMI
# ═══════════════════════════════════════════════
ELO_BASLANGIC = 1500.0
ELO_K = 24.0           # guncelleme katsayisi (futbol icin ~20-30)
ELO_EV_AVANTAJ = 65.0  # ev sahibi rating bonusu

def elo_hesapla(maclar):
    """
    Tarih sirali maclardan Elo rating hesapla.
    Futbol icin: gol farki bazli K carpani (Margin of Victory)
    """
    elo = defaultdict(lambda: ELO_BASLANGIC)
    # Tarihe gore sirala
    sirali = sorted([m for m in maclar if m.get("ev_gol") is not None
                     and m.get("ev") and m.get("dep")],
                    key=lambda x: x.get("tarih") or "")
    for m in sirali:
        ev, dep = m["ev"], m["dep"]
        g_ev, g_dep = m["ev_gol"], m["dep_gol"]
        # Beklenen skor
        r_ev = elo[ev] + ELO_EV_AVANTAJ
        r_dep = elo[dep]
        beklenen = 1.0 / (1.0 + 10 ** ((r_dep - r_ev) / 400.0))
        # Gercek sonuc (1 = ev kazandi, 0.5 = berabere, 0 = dep)
        if g_ev > g_dep: gercek = 1.0
        elif g_ev == g_dep: gercek = 0.5
        else: gercek = 0.0
        # Margin of Victory (gol farki buyukse daha cok puan degisir)
        fark = abs(g_ev - g_dep)
        if fark <= 1: mov = 1.0
        elif fark == 2: mov = 1.5
        else: mov = (11.0 + fark) / 8.0
        # Guncelle
        degisim = ELO_K * mov * (gercek - beklenen)
        elo[ev] += degisim
        elo[dep] -= degisim
    return elo

def elo_olasilik(ev, dep, elo):
    """Elo'dan 1X2 olasiligi uret (beraberlik ayri modellenir)"""
    r_ev = elo.get(ev, ELO_BASLANGIC) + ELO_EV_AVANTAJ
    r_dep = elo.get(dep, ELO_BASLANGIC)
    # Ev kazanma olasiligi (Elo formulu)
    p_ev_ham = 1.0 / (1.0 + 10 ** ((r_dep - r_ev) / 400.0))
    # Beraberlik: rating farki kucukse artar
    fark = abs(r_ev - r_dep)
    p_ber = 0.28 * math.exp(-fark / 320.0) + 0.10
    p_ber = max(0.08, min(0.32, p_ber))
    # Normalize
    kalan = 1.0 - p_ber
    p_ev = kalan * p_ev_ham
    p_dep = kalan * (1.0 - p_ev_ham)
    return {"ev": round(100.0*p_ev,1), "ber": round(100.0*p_ber,1), "dep": round(100.0*p_dep,1)}

# ═══════════════════════════════════════════════
#  TAKIM GUCU (mevcut, iyilestirilmis)
# ═══════════════════════════════════════════════
def takim_gucu(maclar, yari_omur=250, MIN_MAC=6):
    tg=egt=dgt=n=0
    for m in maclar:
        if m.get("ev_gol") is None: continue
        tg+=m["ev_gol"]+m["dep_gol"]; egt+=m["ev_gol"]; dgt+=m["dep_gol"]; n+=1
    if not n: return {}, {"lig_ev_ort":1.45,"lig_dep_ort":1.15,"lig_ort":2.6,"mac_sayisi":0}
    leo=egt/n; ldo=dgt/n; lo=tg/n

    guc=defaultdict(lambda:{"em":0.0,"ea":0.0,"ey":0.0,"dm":0.0,"da":0.0,"dy":0.0,"t":0.0,
                             "ev_say":0,"dep_say":0})
    T=len(maclar)
    for i,m in enumerate(maclar):
        if m.get("ev_gol") is None: continue
        w=math.exp(-(T-i)/yari_omur)
        e,d=m["ev"],m["dep"]; eg,dg=m["ev_gol"],m["dep_gol"]
        guc[e]["em"]+=w; guc[e]["ea"]+=eg*w; guc[e]["ey"]+=dg*w; guc[e]["t"]+=w; guc[e]["ev_say"]+=1
        guc[d]["dm"]+=w; guc[d]["da"]+=dg*w; guc[d]["dy"]+=eg*w; guc[d]["t"]+=w; guc[d]["dep_say"]+=1

    out={}
    for k,v in guc.items():
        if v["t"]<0.5: continue
        mac_s = v["ev_say"] + v["dep_say"]
        guv = min(1.0, mac_s / (MIN_MAC*2.0))
        em=max(0.5,v["em"]); dm=max(0.5,v["dm"])
        ev_h = (v["ea"]/em)/leo if leo else 1.0
        ev_s = (v["ey"]/em)/ldo if ldo else 1.0
        dp_h = (v["da"]/dm)/ldo if ldo else 1.0
        dp_s = (v["dy"]/dm)/leo if leo else 1.0
        ev_h = 1.0 + (ev_h-1.0)*guv
        ev_s = 1.0 + (ev_s-1.0)*guv
        dp_h = 1.0 + (dp_h-1.0)*guv
        dp_s = 1.0 + (dp_s-1.0)*guv
        # FORM: son 5 mac puani (0-1 arasi)
        gecmis = [m for m in maclar if m.get("ev")==k or m.get("dep")==k]
        son5 = gecmis[-5:] if len(gecmis)>=5 else gecmis
        puan = 0
        for m in son5:
            if m.get("ev_gol") is None: continue
            if m.get("ev")==k:
                if m["ev_gol"]>m["dep_gol"]: puan+=3
                elif m["ev_gol"]==m["dep_gol"]: puan+=1
            else:
                if m["dep_gol"]>m["ev_gol"]: puan+=3
                elif m["dep_gol"]==m["ev_gol"]: puan+=1
        form = (puan/(3.0*max(1,len(son5)))) if son5 else 0.5
        out[k]={"ev_huc":max(0.45,min(2.5,ev_h)),
                "ev_sav":max(0.45,min(2.5,ev_s)),
                "dep_huc":max(0.45,min(2.5,dp_h)),
                "dep_sav":max(0.45,min(2.5,dp_s)),
                "form": form,
                "toplam_mac":v["t"],"mac_sayisi":mac_s}
    return out, {"lig_ev_ort":leo,"lig_dep_ort":ldo,"lig_ort":lo,"mac_sayisi":n}

# ═══════════════════════════════════════════════
#  BEKLENEN GOL (Elo + form dahil)
# ═══════════════════════════════════════════════
def beklenen_gol(ev, dep, guc, lig):
    g1=guc.get(ev); g2=guc.get(dep)
    if not g1 or not g2: return lig["lig_ev_ort"], lig["lig_dep_ort"]

    EV_AVANTAJ_HUC = 1.13
    EV_AVANTAJ_SAV = 0.94

    mac1 = g1.get("mac_sayisi", 0) or 0
    mac2 = g2.get("mac_sayisi", 0) or 0
    guv = min(1.0, ((mac1 + mac2) / 2.0) / 10.0)
    guv = 0.35 + 0.65 * guv

    e = g1["ev_huc"] * g2["dep_sav"] * lig["lig_ev_ort"] * EV_AVANTAJ_HUC
    d = g2["dep_huc"] * g1["ev_sav"] * lig["lig_dep_ort"] / EV_AVANTAJ_SAV

    # FORM ayarlamasi: form yuksekse +%8, dusukse -%8
    f1 = g1.get("form", 0.5); f2 = g2.get("form", 0.5)
    e *= (0.92 + 0.16 * f1)
    d *= (0.92 + 0.16 * f2)

    leo, ldo = lig["lig_ev_ort"], lig["lig_dep_ort"]
    e = leo + (e - leo) * guv
    d = ldo + (d - ldo) * guv

    return max(0.2, min(4.5, e)), max(0.2, min(4.5, d))
