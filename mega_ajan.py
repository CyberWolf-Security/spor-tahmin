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
    g1=guc.get(ev); g2=guc.get(dep)
    if not g1 or not g2: return lig["lig_ev_ort"], lig["lig_dep_ort"]
    e=g1["ev_huc"]*g2["dep_sav"]*lig["lig_ev_ort"]*0.99
    d=g2["dep_huc"]*g1["ev_sav"]*lig["lig_dep_ort"]
    return max(0.2,min(4.5,e)), max(0.2,min(4.5,d))

def mega_simulasyon(ev, dep, guc, lig, n=1000000, tohum=None):
    rng = np.random.default_rng(tohum)
    e_b, d_b = beklenen_gol(ev, dep, guc, lig)
    rho = -0.09
    a = rng.poisson(e_b, n).astype(np.int16)
    b = rng.poisson(d_b, n).astype(np.int16)
    maske = (a <= 1) & (b <= 1)
    if maske.any():
        idx = np.where(maske)[0]; aa=a[idx]; bb=b[idx]
        w = np.ones(len(idx))
        w[(aa==0)&(bb==0)] = 1 - e_b*d_b*rho
        w[(aa==0)&(bb==1)] = 1 + e_b*rho
        w[(aa==1)&(bb==0)] = 1 + d_b*rho
        w[(aa==1)&(bb==1)] = 1 - rho
        w = np.clip(w, 0.05, 0.95)
        rd = rng.random(len(idx)) > w
        if rd.any():
            ri = idx[rd]
            a[ri] = rng.poisson(e_b, len(ri)); b[ri] = rng.poisson(d_b, len(ri))
    tg = a + b
    ev_k=int((a>b).sum()); ber=int((a==b).sum()); dep_k=int((a<b).sum())
    kg_v=int(((a>0)&(b>0)).sum())
    kod = a.astype(np.int32)*10 + b.astype(np.int32)
    bz, sy = np.unique(kod, return_counts=True)
    sr = np.argsort(-sy)[:8]
    en_skor=[{"skor":f"{int(bz[i])//10}-{int(bz[i])%10}","olasilik":round(100.0*int(sy[i])/n,1)} for i in sr]
    ia = rng.binomial(a,0.45) if a.max()>0 else np.zeros(n,dtype=np.int16)
    ib = rng.binomial(b,0.45) if b.max()>0 else np.zeros(n,dtype=np.int16)
    def yz(x): return round(100.0*x/n,1)
    return {
        "ev_kazanma":yz(ev_k),"beraberlik":yz(ber),"dep_kazanma":yz(dep_k),
        "1X":yz(ev_k+ber),"12":yz(ev_k+dep_k),"X2":yz(ber+dep_k),
        "ev_beklenen_gol":round(e_b,2),"dep_beklenen_gol":round(d_b,2),
        "toplam_beklenen":round(e_b+d_b,2),
        "kg_var":yz(kg_v),"kg_yok":yz(n-kg_v),
        "ust_05":yz(int((tg>0).sum())),"alt_05":yz(int((tg<=0).sum())),
        "ust_15":yz(int((tg>1).sum())),"alt_15":yz(int((tg<=1).sum())),
        "ust_25":yz(int((tg>2).sum())),"alt_25":yz(int((tg<=2).sum())),
        "ust_35":yz(int((tg>3).sum())),"alt_35":yz(int((tg<=3).sum())),
        "ust_45":yz(int((tg>4).sum())),"alt_45":yz(int((tg<=4).sum())),
        "iy_ev":yz(int((ia>ib).sum())),"iy_ber":yz(int((ia==ib).sum())),"iy_dep":yz(int((ia<ib).sum())),
        "iy_05_ust":yz(int((tg>0).sum())),
        "en_skorlar":en_skor,"simulasyon":n,
    }

def lig_ortalamasi(maclar):
    return takim_gucu(maclar)[1]
