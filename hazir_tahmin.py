"""
HAZIR TAHMINLER MOTORU
Tum gelecek maclari ajanla tahmin eder, lig/ulke bazli gruplar.
- Arka planda calisir (thread)
- Sonuc: veri/hazir_tahminler.json
- Her mac: en iyi tahmin (1/X/2) + olasilik + skor + guven
"""
import json, os, time, threading, math
from datetime import datetime
from collections import defaultdict

VERI_DIZIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "veri")
HAZIR_DOSYA = os.path.join(VERI_DIZIN, "hazir_tahminler.json")

# Mega motor referansi (lig_yeterli_mi icin)
try:
    import mega_ajan as _MEGA
except ImportError:
    _MEGA = None

# Simulasyon sayisi (B secenegi: 1M = dogru sonuc)
SIM = 10_000_000

# Veri yetersiz maclar listeye DAHIL EDILMEZ (B secenegi)
VERI_YOK_DAHIL = False

# Bir macin listeye girmesi icin minimum takim mac sayisi (esik)
MIN_TAKIM_MAC = 2

# LIG FILTRESI: bu ortalamanin altindaki ligler listeye ALINMAZ
# (takim basi ortalama mac sayisi)
MIN_LIG_ORT = 1.8


def lig_yeterli_mi(lig_maclar):
    """Lig yeterli veriye sahip mi? (takimlarin ort. mac sayisi)"""
    gelecek = [m for m in lig_maclar if not m.get("oynandi") and m.get("tarih")]
    if not gelecek:
        return False
    try:
        g, _ = _MEGA.takim_gucu(lig_maclar)
    except Exception:
        return False
    sayilar = []
    for m in gelecek:
        ge = g.get(m["ev"]) or {}
        gd = g.get(m["dep"]) or {}
        sayilar.append(min(ge.get("mac_sayisi", 0), gd.get("mac_sayisi", 0)))
    if not sayilar:
        return False
    return (sum(sayilar) / len(sayilar)) >= MIN_LIG_ORT


def yeterli_ligler(maclar):
    """Yeterli verisi olan ligleri dondur"""
    lig_ms = {}
    for m in maclar:
        la = m.get("lig_adi") or "DIGER"
        lig_ms.setdefault(la, []).append(m)
    ok = set()
    for la, ms in lig_ms.items():
        if lig_yeterli_mi(ms):
            ok.add(la)
    return ok


def _guven_bul(p1, px, p2, ev_mac=0, dep_mac=0):
    """Guven seviyesi: olasilik baskınligi + veri varligi"""
    en = max(p1, px, p2)
    ikinci = sorted([p1, px, p2], reverse=True)[1]
    fark = en - ikinci
    # Veri az ama web'den arastirildi -> dusuk guven (elenmez)
    if ev_mac < 2 or dep_mac < 2:
        return "DUSUK"
    if en >= 55 and fark >= 20:
        return "YUKSEK"
    if en >= 45 and fark >= 12:
        return "ORTA"
    return "DUSUK"


def _web_guc(web_veri, ev_mi):
    """
    Internetten bulunan maclari TAKIM GUCUNE cevir.
    mega_ajan.takim_gucu ile ayni format dondurur.
    """
    maclar = web_veri.get("maclar") or []
    ad = web_veri.get("ad") or ""
    n = len(maclar)
    if n == 0:
        return {}

    # Bu takimin attigi/yedigi goller
    atilan = yenilen = 0
    ev_say = dep_say = 0
    for m in maclar:
        # Takim ev sahibi mi?
        ev_ad = (m.get("ev") or "").lower()
        dep_ad = (m.get("dep") or "").lower()
        kisa = ad.lower()[:5]
        takim_ev = bool(kisa) and kisa in ev_ad
        eg, dg = m.get("ev_gol", 0), m.get("dep_gol", 0)
        if takim_ev:
            atilan += eg; yenilen += dg; ev_say += 1
        else:
            atilan += dg; yenilen += eg; dep_say += 1

    ort_at = atilan / max(n, 1)
    ort_ye = yenilen / max(n, 1)

    # mega_ajan formatina cevir (lig ortalamasi 1.45/1.15 varsayimi)
    # ev_huc: evde mac basi atilan / lig ort
    # dep_huc: deplasmanda atilan / lig ort
    lig_ev, lig_dep = 1.45, 1.15
    if ev_say:
        ev_at = atilan / ev_say if ev_mi else ort_at
    else:
        ev_at = ort_at
    guc = {
        "ev_huc": max(0.45, min(2.5, (ort_at / lig_ev) if ort_at > 0 else 1.0)),
        "ev_sav": max(0.45, min(2.5, (ort_ye / lig_dep) if ort_ye > 0 else 1.0)),
        "dep_huc": max(0.45, min(2.5, (ort_at / lig_dep) if ort_at > 0 else 1.0)),
        "dep_sav": max(0.45, min(2.5, (ort_ye / lig_ev) if ort_ye > 0 else 1.0)),
        "toplam_mac": float(n),
        "mac_sayisi": n,
    }
    return guc


def mac_tahmin(m, guc, lig_bilgi, mega):
    """Tek mac tahmini — veri yoksa INTERNETTEN ARASTIRIP ogrenir, sonra tahmin eder"""
    ev, dep = m["ev"], m["dep"]
    g_ev = guc.get(ev) or {}
    g_dep = guc.get(dep) or {}
    ev_mac = g_ev.get("mac_sayisi", 0)
    dep_mac = g_dep.get("mac_sayisi", 0)

    # ═══ VERI YETERSIZSE: TUM INTERNETTEN ARASTIR ═══
    web_ev = web_dep = None
    if ev_mac < MIN_TAKIM_MAC or dep_mac < MIN_TAKIM_MAC:
        try:
            import web_arastir as WA
            web_ev = WA.takim_arastir(ev)
            web_dep = WA.takim_arastir(dep)
        except Exception:
            pass

    # Web maclari VARSA: gucu web verisiyle GENISLET
    guc2 = dict(guc)
    if web_ev and web_ev.get("mac_sayisi", 0) >= 2:
        guc2[ev] = _web_guc(web_ev, True)
        ev_mac = max(ev_mac, web_ev["mac_sayisi"])
    if web_dep and web_dep.get("mac_sayisi", 0) >= 2:
        guc2[dep] = _web_guc(web_dep, False)
        dep_mac = max(dep_mac, web_dep["mac_sayisi"])

    try:
        r = mega.mega_simulasyon(ev, dep, guc2, lig_bilgi, n=SIM)
    except Exception as e:
        return None

    p1, px, p2 = r["ev_kazanma"], r["beraberlik"], r["dep_kazanma"]
    # En iyi tahmin
    if p1 >= px and p1 >= p2:
        tahmin, kod, olas = "1", "EV KAZANIR", p1
    elif p2 >= p1 and p2 >= px:
        tahmin, kod, olas = "2", "DEPLASMAN KAZANIR", p2
    else:
        tahmin, kod, olas = "X", "BERABERE", px

    guven = _guven_bul(p1, px, p2, ev_mac, dep_mac)

    return {
        "ev": ev, "dep": dep,
        "tarih": m.get("tarih"), "saat": m.get("saat"),
        "lig": m.get("lig_adi") or "",
        "ev_logo": m.get("ev_logo"), "dep_logo": m.get("dep_logo"),
        "bayrak": m.get("bayrak", "⚽"),
        "tahmin": tahmin, "tahmin_metin": kod, "olasilik": olas,
        "p1": p1, "px": px, "p2": p2,
        "beklenen_skor": r.get("beklenen_skor") or ("%s-%s" % (r.get("ev_beklenen_gol"), r.get("dep_beklenen_gol"))),
        "ev_beklenen_gol": r.get("ev_beklenen_gol"),
        "dep_beklenen_gol": r.get("dep_beklenen_gol"),
        "ust_25": r.get("ust_25"), "kg_var": r.get("kg_var"),
        "en_skorlar": r.get("en_skorlar", [])[:3],
        "guven": guven,
        "veri_var": guven != "VERI_YOK",
        "ev_mac": ev_mac, "dep_mac": dep_mac,
    }


def tahminleri_uret(maclar, guc, lig_bilgi, mega, ilerleme=None):
    """Tum gelecek maclari tahmin et"""
    gelecek = [m for m in maclar if not m.get("oynandi") and m.get("tarih")]
    # Tarihe gore sirala
    gelecek.sort(key=lambda x: (x.get("tarih") or "", x.get("saat") or ""))

    sonuc = []
    for i, m in enumerate(gelecek):
        t = mac_tahmin(m, guc, lig_bilgi.get(m.get("lig_adi"), {}), mega)
        if t:
            sonuc.append(t)
        if ilerleme and i % 20 == 0:
            ilerleme(i + 1, len(gelecek))
    return sonuc


def ulke_lig_grupla(tahminler):
    """Ulke -> Lig -> Maclar seklinde grupla"""
    gruplar = defaultdict(lambda: defaultdict(list))
    for t in tahminler:
        # Lig adi: "SPAIN — La Liga" -> ulke=SPAIN, lig=La Liga
        lig_adi = t.get("lig") or "DIGER"
        if "—" in lig_adi:
            ulke, lig = lig_adi.split("—", 1)
            ulke, lig = ulke.strip(), lig.strip()
        elif " - " in lig_adi:
            ulke, lig = lig_adi.split(" - ", 1)
            ulke, lig = ulke.strip(), lig.strip()
        else:
            ulke, lig = "DIGER", lig_adi
        gruplar[ulke][lig].append(t)

    # ═══ SIRALAMA: POPULER LIGLER USTTE ═══
    # Oncelik listesi (kucuk numara = daha ustte)
    def _oncelik(ulke, lig):
        u = (ulke or "").upper(); l = (lig or "").lower()
        lu = (lig or "").upper()
        # 1) Turkiye (arsiv dahil)
        if "TURKEY" in u or "TÜRK" in u or "SÜPER LİG" in lu or "1. LİG" in lu:
            return 1
        if "arşiv" in l or "arsiv" in l:
            return 1
        # 2) Avrupa kupalari
        if any(x in l for x in ["champions league", "europa league", "conference league", "şampiyonlar"]):
            return 2
        # 3) Buyuk 5 lig
        if any(x in l for x in ["premier league", "la liga", "laliga", "serie a", "bundesliga"]) and "women" not in l:
            if "premier league" in l and u not in ("ENGLAND",): return 6
            if "championship" in l or "league one" in l or "league two" in l: return 7
            if "serie b" in l or "bundesliga 2" in l or "2. bundesliga" in l: return 7
            return 3
        if "ligue 1" in l and "women" not in l: return 3
        # 4) Milli maclar
        if any(x in l for x in ["nations league", "uluslar", "world cup", "dünya kupası", "euro ", "friendly international"]):
            return 4
        # 5) Populer diger Avrupa
        if any(x in l for x in ["eredivisie", "primeira", "pro league", "premiership", "super lig", "eliteserien"]):
            return 5
        # 6) Arap ligleri
        if any(x in u for x in ["SAUDI", "QATAR", "UAE", "KUWAIT", "EGYPT", "MOROCCO", "TUNISIA", "ALGERIA", "IRAQ", "JORDAN", "LEBANON"]):
            return 6
        # 7) Diger
        return 9

    out = []
    for ulke, ligler in gruplar.items():
        lig_listesi = []
        toplam = 0
        for lig, ms in ligler.items():
            ms.sort(key=lambda x: (x.get("tarih") or "", x.get("saat") or ""))
            lig_listesi.append({"lig": lig, "maclar": ms, "adet": len(ms),
                                "oncelik": _oncelik(ulke, lig)})
            toplam += len(ms)
        # Once oncelik, sonra mac sayisi
        lig_listesi.sort(key=lambda x: (x["oncelik"], -x["adet"]))
        out.append({"ulke": ulke, "ligler": lig_listesi, "toplam": toplam})
    # Ulkeleri de en iyi onceligine gore sirala
    out.sort(key=lambda g: (min((l["oncelik"] for l in g["ligler"]), default=9), -g["toplam"]))
    return out


def kaydet(veri):
    os.makedirs(VERI_DIZIN, exist_ok=True)
    gecici = HAZIR_DOSYA + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(gecici, HAZIR_DOSYA)


def yukle():
    if not os.path.exists(HAZIR_DOSYA):
        return None
    try:
        with open(HAZIR_DOSYA, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# ═══════════════ URETIM DURUMU (thread guvenli) ═══════════════
DURUM = {
    "calisiyor": False,
    "ilerleme": 0,
    "toplam": 0,
    "basladi": None,
    "bitti": None,
    "hata": "",
}


def uretim_baslat(maclar, guc_lig, mega, zorla=False):
    """Arka planda tahmin uretimi baslat (zaten calisiyorsa atla)"""
    if DURUM["calisiyor"]:
        return False
    if not zorla:
        v = yukle()
        if v and v.get("bitti"):
            # Son 6 saat icinde uretilmisse yeniden uretme
            try:
                bt = datetime.fromisoformat(v["bitti"])
                if (datetime.now() - bt).total_seconds() < 6 * 3600:
                    return False
            except Exception:
                pass

    def isle():
        DURUM.update({"calisiyor": True, "ilerleme": 0, "hata": "",
                      "basladi": datetime.now().isoformat(), "bitti": None})
        try:
            # ═══ TUM MACLAR ═══
            gelecek = [m for m in maclar if not m.get("oynandi") and m.get("tarih")]
            gelecek.sort(key=lambda x: (x.get("tarih") or "", x.get("saat") or ""))
            DURUM["toplam"] = len(gelecek)

            # ═══ 1) TAKIMLARI TOPLU ARASTIR (PARALEL — hizli) ═══
            try:
                import web_arastir as WA
                from concurrent.futures import ThreadPoolExecutor, as_completed
                takimlar = set()
                for m in gelecek:
                    takimlar.add(m["ev"]); takimlar.add(m["dep"])
                takimlar = list(takimlar)

                # Onbellekte olanlari atla
                bellek = WA._yukle_bellek()
                eksik = [t for t in takimlar if t not in bellek]

                DURUM["asama"] = "takim_arastirma"
                DURUM["takim_toplam"] = len(takimlar)
                DURUM["takim_arastirilan"] = len(takimlar) - len(eksik)

                # Paralel arastir (24 thread — en hizli)
                def _ar(tk):
                    try:
                        return WA.takim_arastir(tk)
                    except Exception:
                        return None

                with ThreadPoolExecutor(max_workers=32) as ex:
                    isler = {ex.submit(_ar, t): t for t in eksik}
                    n = 0
                    for f in as_completed(isler):
                        n += 1
                        DURUM["takim_arastirilan"] = len(takimlar) - len(eksik) + n
                DURUM["asama"] = "tahmin"
            except Exception as e:
                DURUM["asama"] = "tahmin"

            # ═══ 2) TAHMINLER ═══
            sonuc = []
            for i, m in enumerate(gelecek):
                la = m.get("lig_adi") or "DIGER"
                g, bilgi = guc_lig.get(la, ({}, {}))
                t = mac_tahmin(m, g, bilgi, mega)
                if t:
                    sonuc.append(t)
                DURUM["ilerleme"] = i + 1

            veri = {
                "bitti": datetime.now().isoformat(),
                "sim": SIM,
                "mac_sayisi": len(sonuc),
                "lig_sayisi": len(sonuc),
                "gruplar": ulke_lig_grupla(sonuc),
                "tahminler": sonuc,
            }
            kaydet(veri)
            DURUM["bitti"] = veri["bitti"]
        except Exception as e:
            DURUM["hata"] = str(e)
        finally:
            DURUM["calisiyor"] = False

    threading.Thread(target=isle, daemon=True).start()
    return True
