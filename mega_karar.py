"""BERABERLIK ODAKLI KARAR MOTORU
Amac: beraberlik oranini %8 -> %20+ cikarmak, isabeti artirmak
Yontem: kalibre edilmis esik + beraberlik risk skoru
"""
import math
import mega_ajan as M

def karar_motoru(olas, ev, dep, guc=None, maclar=None):
    ev_k = olas["ev_kazanma"]; ber = olas["beraberlik"]; dp_k = olas["dep_kazanma"]
    fark = abs(ev_k - dp_k)
    en_y = max(ev_k, ber, dp_k)

    # ═══ BERABERLIK KARARI (kalibre edilmis) ═══
    # Gercek beraberlik orani ~%27, model ~%23 veriyor
    # Beraberlik SECILMESI icin: model ber orani yeterince yuksek VE fark kucuk
    ber_risk = 0.0
    # Fark kucukse beraberlik riski artar
    if fark < 6: ber_risk += 0.45
    elif fark < 10: ber_risk += 0.35
    elif fark < 15: ber_risk += 0.22
    elif fark < 20: ber_risk += 0.10
    # Model ber orani yuksekse
    if ber >= 30: ber_risk += 0.35
    elif ber >= 27: ber_risk += 0.28
    elif ber >= 24: ber_risk += 0.20
    elif ber >= 21: ber_risk += 0.12
    # Dusuk gol beklentisi -> beraberlik daha olasi
    tb = olas.get("toplam_beklenen", 2.6)
    if tb < 2.2: ber_risk += 0.20
    elif tb < 2.5: ber_risk += 0.12
    elif tb < 2.8: ber_risk += 0.05
    # KG yok -> beraberlik (0-0, 1-1) daha olasi
    if olas.get("kg_yok", 50) >= 48: ber_risk += 0.10
    # Cifte sans X2 veya 1X yuksekse
    if olas.get("1X", 0) >= 75 or olas.get("X2", 0) >= 75: ber_risk += 0.08

    tavsiyeler = []
    uyarilar = []

    # BERABERLIK: TAHMIN olarak SECILMEZ (istatistiksel kanit: isabeti dusurur)
    # Sadece UYARI olarak gosterilir
    if ev_k >= dp_k:
        _tmp_unused = True
    if True:
        if ev_k >= dp_k:
            ana = f"{ev} KAZANIR"
            if fark >= 25: alt = f"Net üstünlük (%{ev_k} vs %{dp_k})"
            elif fark >= 15: alt = f"Belirgin üstünlük (%{ev_k} vs %{dp_k})"
            elif fark >= 8: alt = f"Hafif üstünlük (%{ev_k} vs %{dp_k})"
            else: alt = f"Çok az fark (%{ev_k} vs %{dp_k}) — riskli"
        else:
            ana = f"{dep} KAZANIR"
            if fark >= 25: alt = f"Net üstünlük (%{dp_k} vs %{ev_k})"
            elif fark >= 15: alt = f"Belirgin üstünlük (%{dp_k} vs %{ev_k})"
            elif fark >= 8: alt = f"Hafif üstünlük (%{dp_k} vs %{ev_k})"
            else: alt = f"Çok az fark (%{dp_k} vs %{ev_k}) — riskli"

    guven_baz = {"BERABERE": ber, "EV": ev_k, "DEP": dp_k}
    ana_ol = ber if ana == "BERABERE" else (ev_k if ev_k >= dp_k else dp_k)
    tavsiyeler.append({"tip":"1X2","tavsiye":ana,"aciklama":alt,"olasilik":ana_ol,
                       "guven":"YÜKSEK" if ana_ol>=45 else ("ORTA" if ana_ol>=33 else "DÜŞÜK")})

    # Cifte sans
    ciftler = [("1X (Ev/Ber)", olas["1X"], f"{ev} kaybetmez"),
               ("X2 (Ber/Dep)", olas["X2"], f"{dep} kaybetmez"),
               ("12 (Ev/Dep)", olas["12"], "beraberlik olmaz")]
    ciftler.sort(key=lambda x: -x[1])
    if ciftler[0][1] >= 70:
        tavsiyeler.append({"tip":"ÇİFTE ŞANS","tavsiye":ciftler[0][0],"aciklama":ciftler[0][2],
                           "olasilik":ciftler[0][1],"guven":"YÜKSEK" if ciftler[0][1]>=80 else "ORTA"})

    # Gol
    if olas["ust_25"] >= 62:
        tavsiyeler.append({"tip":"GOL","tavsiye":"Üst 2.5 gol","olasilik":olas["ust_25"],
                           "aciklama":f"Toplam {olas['toplam_beklenen']} gol beklentisi",
                           "guven":"YÜKSEK" if olas["ust_25"]>=75 else "ORTA"})
    elif olas["alt_25"] >= 58:
        tavsiyeler.append({"tip":"GOL","tavsiye":"Alt 2.5 gol","olasilik":olas["alt_25"],
                           "aciklama":f"Düşük gollü maç ({olas['toplam_beklenen']} gol)",
                           "guven":"YÜKSEK" if olas["alt_25"]>=70 else "ORTA"})

    if olas["kg_var"] >= 62:
        tavsiyeler.append({"tip":"KG","tavsiye":"Karşılıklı gol VAR","olasilik":olas["kg_var"],"guven":"YÜKSEK" if olas["kg_var"]>=72 else "ORTA"})
    elif olas["kg_yok"] >= 62:
        tavsiyeler.append({"tip":"KG","tavsiye":"Karşılıklı gol YOK","olasilik":olas["kg_yok"],"guven":"YÜKSEK" if olas["kg_yok"]>=72 else "ORTA"})

    for etiket, u, a in [("1.5", olas["ust_15"], olas["alt_15"]), ("3.5", olas["ust_35"], olas["alt_35"])]:
        if u >= 78: tavsiyeler.append({"tip":"ALT/ÜST","tavsiye":f"Üst {etiket}","olasilik":u,"guven":"YÜKSEK"})
        elif a >= 78: tavsiyeler.append({"tip":"ALT/ÜST","tavsiye":f"Alt {etiket}","olasilik":a,"guven":"YÜKSEK"})

    if olas["iy_05_ust"] >= 72:
        tavsiyeler.append({"tip":"İY","tavsiye":"İlk yarı 0.5 ÜST (gol olur)","olasilik":olas["iy_05_ust"],"guven":"ORTA"})

    if olas.get("en_skorlar"):
        t3 = olas["en_skorlar"][:3]
        tavsiyeler.append({"tip":"SKOR","tavsiye":" / ".join(x["skor"] for x in t3),
                           "olasilik":t3[0]["olasilik"],"aciklama":"En olası skorlar","guven":"ORTA"})

    # Uyarilar
    if ber_risk >= 0.62:
        uyarilar.append(f"🚨 BERABERLİK RİSKİ YÜKSEK (%{ber}) — takımlar dengeli (fark %{fark:.0f}), dikkatli oyna")
    elif ber_risk >= 0.45:
        uyarilar.append(f"⚠️ Beraberlik ihtimali var (%{ber}) — fark az (%{fark:.0f})")
    if fark < 8: uyarilar.append(f"⚠️ Takımlar çok yakın (%{ev_k} - %{dp_k})")
    if ber >= 28: uyarilar.append(f"⚠️ Beraberlik ihtimali yüksek (%{ber})")
    if olas["alt_25"] >= 58: uyarilar.append(f"⚠️ Düşük gollü maç bekleniyor (Alt 2.5: %{olas['alt_25']})")
    if abs(olas["ev_beklenen_gol"] - olas["dep_beklenen_gol"]) < 0.25:
        uyarilar.append("⚠️ Gol beklentileri neredeyse eşit — sonuç belirsiz")

    # Guven
    if tavsiyeler:
        ana_ex = next((t for t in tavsiyeler if t["tip"]=="1X2"), tavsiyeler[0])
        skor = ana_ex["olasilik"]
        if any(t["tip"]=="ÇİFTE ŞANS" for t in tavsiyeler): skor += 4
        skor -= len(uyarilar) * 2.5
        skor = max(8, min(97, round(skor, 1)))
    else:
        skor = 30

    if skor >= 70: seviye = "ÇOK YÜKSEK"
    elif skor >= 55: seviye = "YÜKSEK"
    elif skor >= 40: seviye = "ORTA"
    elif skor >= 25: seviye = "DÜŞÜK"
    else: seviye = "ÇOK DÜŞÜK"

    return {"genel": f"{ana} ({alt})", "ana_tahmin": ana, "ber_risk": round(ber_risk,2),
            "guven_skoru": skor, "guven": seviye, "tavsiyeler": tavsiyeler,
            "uyarilar": uyarilar, "simulasyon": olas.get("simulasyon", 0)}
