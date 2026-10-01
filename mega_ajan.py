"""MEGA AJAN v6 — DUZELTILMIS
1. Tarih sirali test (veri sizintisi YOK)
2. Az veri durumunda lig ortalamasina cekilme (regresyon)
3. Ev sahibi avantaji kalibre
"""
import math
import numpy as np
from collections import defaultdict

def takim_gucu(maclar, yari_omur=250, MIN_MAC=6):
    """
    GELISMIS takim gucu
    - Tarih sirali (sizinti yok)
    - MIN_MAC altinda veri varsa lig ortalamasina cekilir
    - Zaman agirlikli
    """
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
        # AZ VERI DUZELTMESI: kac mac oynadi?
        mac_s = v["ev_say"] + v["dep_say"]
        # Guvenilirlik: MIN_MAC'e kadar 0, sonra 1'e yaklasir
        guv = min(1.0, mac_s / (MIN_MAC*2.0))
        em=max(0.5,v["em"]); dm=max(0.5,v["dm"])
        # Ham oranlar
        ev_h = (v["ea"]/em)/leo if leo else 1.0
        ev_s = (v["ey"]/em)/ldo if ldo else 1.0
        dp_h = (v["da"]/dm)/ldo if ldo else 1.0
        dp_s = (v["dy"]/dm)/leo if leo else 1.0
        # Lig ortalamasina cekilme (regresyon): az veri = 1.0'a yaklas
        ev_h = 1.0 + (ev_h-1.0)*guv
        ev_s = 1.0 + (ev_s-1.0)*guv
        dp_h = 1.0 + (dp_h-1.0)*guv
        dp_s = 1.0 + (dp_s-1.0)*guv
        out[k]={"ev_huc":max(0.45,min(2.5,ev_h)),
                "ev_sav":max(0.45,min(2.5,ev_s)),
                "dep_huc":max(0.45,min(2.5,dp_h)),
                "dep_sav":max(0.45,min(2.5,dp_s)),
                "toplam_mac":v["t"],"mac_sayisi":mac_s}
    return out, {"lig_ev_ort":leo,"lig_dep_ort":ldo,"lig_ort":lo,"mac_sayisi":n}

def beklenen_gol(ev, dep, guc, lig):
    """Gelismis beklenen gol — ev avantaji + zaman agirligi + veri guveni"""
    g1=guc.get(ev); g2=guc.get(dep)
    if not g1 or not g2: return lig["lig_ev_ort"], lig["lig_dep_ort"]

    # 1) EV AVANTAJI (gercek futbol katsayisi: ~%15 hucum, ~%5 savunma)
    EV_AVANTAJ_HUC = 1.13
    EV_AVANTAJ_SAV = 0.94

    # 2) VERI GUVENI: veri yoksa lig ortalamasina yaklas
    mac1 = g1.get("mac_sayisi", 0) or 0
    mac2 = g2.get("mac_sayisi", 0) or 0
    guv = min(1.0, ((mac1 + mac2) / 2.0) / 10.0)   # 10 mac = tam guven
    guv = 0.35 + 0.65 * guv                         # en az %35 guven

    # 3) BEKLENEN GOL (ev avantaji dahil)
    e = g1["ev_huc"] * g2["dep_sav"] * lig["lig_ev_ort"] * EV_AVANTAJ_HUC
    d = g2["dep_huc"] * g1["ev_sav"] * lig["lig_dep_ort"] / EV_AVANTAJ_SAV

    # 4) Lig ortalamasina dogru yumusat (az veri varsa)
    leo, ldo = lig["lig_ev_ort"], lig["lig_dep_ort"]
    e = leo + (e - leo) * guv
    d = ldo + (d - ldo) * guv

    return max(0.2, min(4.5, e)), max(0.2, min(4.5, d))

def mega_simulasyon(ev, dep, guc, lig, n=10000000, tohum=None, elo=None):
    """
    ENSEMBLE simulasyon — Poisson + Elo birlesimi
    elo verilirse: %60 Poisson + %40 Elo karisimi
    """
    rng = np.random.default_rng(tohum)
    e_b, d_b = beklenen_gol(ev, dep, guc, lig)

    # ═══ ELO KATMANI (varsa) ═══
    if elo:
        try:
            import mega_elo as ELO_M
            eo = ELO_M.elo_olasilik(ev, dep, elo)
            # Elo olasiligi -> beklenen gol ayari
            # Elo ev/dep dengesini Poisson'a yansit
            p_ev_e = eo["ev"]/100.0; p_dep_e = eo["dep"]/100.0
            # Poisson'dan gelen denge
            tot_b = e_b + d_b
            if (p_ev_e + p_dep_e) > 0:
                # Elo'ya gore gol dagilimini ayarla (yumusak: %35 etki)
                oran_e = p_ev_e / (p_ev_e + p_dep_e)
                oran_p = e_b / (e_b + d_b) if (e_b+d_b) > 0 else 0.5
                yeni_oran = 0.65 * oran_p + 0.35 * oran_e
                e_b = tot_b * yeni_oran
                d_b = tot_b * (1.0 - yeni_oran)
        except Exception:
            pass

    rho = -0.09
    a = rng.poisson(e_b, n).astype(np.int16)
    b = rng.poisson(d_b, n).astype(np.int16)

    # ═══ DIXON-COLES DUZELTMESI (VEKTOREL — hizli) ═══
    # Dusuk skorlu maclarda (0-0, 1-0, 0-1, 1-1) olasiligi duzelt
    # Eski yontem: np.where + tek tek atama (10M'de ~40 sn!)
    # Yeni: tum dizi uzerinde tek gecis (vektorel)
    maske = (a <= 1) & (b <= 1)
    if maske.any():
        # Agirlik dizisi (tum n icin)
        w = np.ones(n, dtype=np.float32)
        m00 = maske & (a == 0) & (b == 0)
        m01 = maske & (a == 0) & (b == 1)
        m10 = maske & (a == 1) & (b == 0)
        m11 = maske & (a == 1) & (b == 1)
        w[m00] = 1.0 - e_b * d_b * rho
        w[m01] = 1.0 + e_b * rho
        w[m10] = 1.0 + d_b * rho
        w[m11] = 1.0 - rho
        np.clip(w, 0.05, 0.95, out=w)
        # Reddetme: yalniz maskeli bolgede
        rd = np.zeros(n, dtype=bool)
        rd[maske] = rng.random(int(maske.sum())) > w[maske]
        if rd.any():
            ri = np.where(rd)[0]
            a[ri] = rng.poisson(e_b, len(ri))
            b[ri] = rng.poisson(d_b, len(ri))
    tg = a + b
    ev_k=int((a>b).sum()); ber=int((a==b).sum()); dep_k=int((a<b).sum())
    kg_v=int(((a>0)&(b>0)).sum())
    kod = a.astype(np.int32)*10 + b.astype(np.int32)
    ia = rng.binomial(np.maximum(a, 0), 0.45) if a.max()>0 else np.zeros(n,dtype=np.int16)
    ib = rng.binomial(np.maximum(b, 0), 0.45) if b.max()>0 else np.zeros(n,dtype=np.int16)
    del a, b            # bellek bosalt (10M'de onemli)
    bz, sy = np.unique(kod, return_counts=True)
    del kod
    sr = np.argsort(-sy)[:8]
    en_skor=[{"skor":f"{int(bz[i])//10}-{int(bz[i])%10}","olasilik":round(100.0*int(sy[i])/n,1)} for i in sr]
    def yz(x): return round(100.0*x/n,1)

    # ═══ ARAYUZUN BEKLEDIGI EK ALANLAR ═══
    # Toplam gol dagilimi {0: %, 1: %, ...}
    tg_deger, tg_sayi = np.unique(tg, return_counts=True)
    toplam_gol = {int(k): round(100.0*int(v)/n, 1) for k, v in zip(tg_deger, tg_sayi)}
    # Skor listesi (olasiliga gore sirali) [[skor, %], ...]
    skorlar = [[f"{int(bz[i])//10}-{int(bz[i])%10}", round(100.0*int(sy[i])/n, 1)] for i in np.argsort(-sy)]
    # Tek/Cift
    tek_gol = yz(int((tg % 2 == 1).sum()))
    cift_gol = yz(int((tg % 2 == 0).sum()))
    # Ilk yari 1.5 ust
    iy_tg = ia + ib
    iy_15_ust = yz(int((iy_tg > 1).sum()))

    return {
        "ev_kazanma":yz(ev_k),"beraberlik":yz(ber),"dep_kazanma":yz(dep_k),
        "1X":yz(ev_k+ber),"12":yz(ev_k+dep_k),"X2":yz(ber+dep_k),
        "ev_beklenen_gol":round(e_b,2),"dep_beklenen_gol":round(d_b,2),
        "toplam_beklenen":round(e_b+d_b,2),
        "beklenen_skor":f"{round(e_b,2)}-{round(d_b,2)}",
        "kg_var":yz(kg_v),"kg_yok":yz(n-kg_v),
        "ust_05":yz(int((tg>0).sum())),"alt_05":yz(int((tg<=0).sum())),
        "ust_15":yz(int((tg>1).sum())),"alt_15":yz(int((tg<=1).sum())),
        "ust_25":yz(int((tg>2).sum())),"alt_25":yz(int((tg<=2).sum())),
        "ust_35":yz(int((tg>3).sum())),"alt_35":yz(int((tg<=3).sum())),
        "ust_45":yz(int((tg>4).sum())),"alt_45":yz(int((tg<=4).sum())),
        "iy_ev":yz(int((ia>ib).sum())),"iy_ber":yz(int((ia==ib).sum())),"iy_dep":yz(int((ia<ib).sum())),
        "iy_05_ust":yz(int((iy_tg>0).sum())),
        "iy_15_ust":iy_15_ust,
        "tek_gol":tek_gol,"cift_gol":cift_gol,
        "toplam_gol":toplam_gol,
        "skorlar":skorlar,
        "en_skorlar":en_skor,"simulasyon":n,
    }

def lig_ortalamasi(maclar):
    return takim_gucu(maclar)[1]
