"""Spor Tahmin - Flask (dunya capinda feed + canli serit)"""
from flask import Flask, render_template, request, jsonify
import json, os, sys, threading, webbrowser, time, socket, urllib.request
from datetime import datetime
from tahmin import takim_gucu
try:
    import mega_ajan as MEGA
    import mega_karar as MKARAR
    MEGA_VAR = True
except ImportError:
    MEGA_VAR = False
from olasilik import tum_olasiliklar
from ajan3 import akilli_ajan
import fs_feed as fsf

app = Flask(__name__)
BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
CACHE = {"maclar": [], "zaman": None, "ligler": {}, "yukleniyor": False, "canli": [], "canli_zaman": None, "tam": False}
_FEED_KILIT = threading.Lock()   # ayni anda tek feed cekimi

def arsiv_yukle():
    """Onceden cekilmis takim arsivleri (veri havuzu)"""
    hepsi = []
    vr = os.path.join(BASE_DIR, "veri")
    if os.path.isdir(vr):
        for f in os.listdir(vr):
            if f.startswith("arsiv_") and f.endswith(".json"):
                try:
                    with open(os.path.join(vr, f), encoding="utf-8") as fh:
                        hepsi += json.load(fh).get("maclar", [])
                except Exception: pass
    return hepsi

_LOGO_CACHE = None

def logo_sozluk():
    return _LOGO_CACHE or {}

def _logo_bul(lg, ad):
    """Bulank eslestirme: 'Fenerbahçe (Tur)' -> 'Fenerbahçe'"""
    if not ad: return None
    if ad in lg: return lg[ad]
    # Parantezli kismi at
    temiz = ad.split("(")[0].strip()
    if temiz in lg: return lg[temiz]
    # Kismi eslesme
    for k, v in lg.items():
        if k == temiz or k.startswith(temiz) or temiz.startswith(k):
            return v
    return None

def _logo_yukle():
    global _LOGO_CACHE
    try:
        with open(os.path.join(BASE_DIR, "veri", "logolar.json"), encoding="utf-8") as f:
            _LOGO_CACHE = json.load(f)
    except Exception:
        _LOGO_CACHE = {}

def _logla(mesaj):
    """Dosyaya log yaz (noconsole modda gorunmez oldugu icin)"""
    try:
        yol = os.path.join(os.path.expanduser("~"), "SporTahmin_log.txt")
        with open(yol, "a", encoding="utf-8") as f:
            f.write("[%s] %s\n" % (datetime.now().strftime("%H:%M:%S"), mesaj))
    except Exception:
        pass

def _hizli_arsiv():
    """Arsivi aninda yukle (SADECE yerel dosya, 0.1 sn) — feed'i BEKLEMEZ"""
    try:
        if CACHE["maclar"]:
            return True
        ars = arsiv_yukle()
        if not ars:
            _logla("_hizli_arsiv: arsiv bos!")
            return False
        for m in ars:
            if not m.get("lig_adi"):
                m["lig_adi"] = "Süper Lig (Arşiv)"
                m["bayrak"] = "🇹🇷"
            m["kaynak"] = "Arşiv"
        try:
            _logo_yukle(); lg0 = logo_sozluk()
            for m in ars:
                if not m.get("ev_logo"): m["ev_logo"] = _logo_bul(lg0, m["ev"])
                if not m.get("dep_logo"): m["dep_logo"] = _logo_bul(lg0, m["dep"])
        except Exception:
            pass
        CACHE["maclar"] = list(ars)
        l0 = {}
        for m in ars:
            l0.setdefault(m["lig_adi"], []).append(m)
        CACHE["ligler"] = l0
        CACHE["zaman"] = datetime.now()
        _logla("_hizli_arsiv OK: %d mac, %d lig" % (len(ars), len(l0)))
        return True
    except Exception as e:
        _logla("_hizli_arsiv HATA: %s" % e)
        return False

def veri_al(force=False):
    if not force and CACHE["maclar"] and CACHE["zaman"] and (datetime.now()-CACHE["zaman"]).seconds < 1200:
        return CACHE
    # ═══ KILIT: ayni anda TEK feed cekimi (cift thread engeli) ═══
    if not _FEED_KILIT.acquire(blocking=False):
        _logla("veri_al: zaten calisiyor, atlandi")
        return CACHE
    try:
        if CACHE["tam"] and CACHE["maclar"]:
            return CACHE
        CACHE["yukleniyor"] = True
        CACHE["hata"] = None
        # 0) Arsiv: zaten yuklu ise tekrar yukleme (hizli baslangic)
        if not CACHE["maclar"]:
            _hizli_arsiv()
        _logla("arsiv=%d mac (BASE_DIR=%s)" % (len(CACHE["maclar"]), BASE_DIR))
        # 1) Canli feed (yavas - 15 gun) — hata olsa bile arsiv kalir
        try:
            maclar = fsf.tum_gunler(gunler=(-7,-6,-5,-4,-3,-2,-1,0,1,2,3,4,5,6,7), sadece_onemli=False)
            _logla("feed=%d mac" % len(maclar))
            _logo_yukle()
            lg = logo_sozluk()
            ars = CACHE["maclar"] if CACHE["maclar"] else []
            for m in ars:
                if not m.get("ev_logo"): m["ev_logo"] = _logo_bul(lg, m["ev"])
                if not m.get("dep_logo"): m["dep_logo"] = _logo_bul(lg, m["dep"])
                if not m.get("lig_adi"):
                    m["lig_adi"] = "Süper Lig (Arşiv)"
                    m["bayrak"] = "🇹🇷"
                m["kaynak"] = "Arşiv"
            maclar += ars
            CACHE["maclar"] = maclar
            CACHE["zaman"] = datetime.now()
            ligler = {}
            for m in maclar:
                ligler.setdefault(m["lig_adi"], []).append(m)
            CACHE["ligler"] = ligler
            CACHE["tam"] = True
            _logla("TAM HAZIR: %d mac, %d lig" % (len(maclar), len(ligler)))
        except Exception as fe:
            _logla("FEED HATA (arsiv korundu): %s" % fe)
            CACHE["feed_hata"] = str(fe)[:200]
            if not CACHE["zaman"]:
                CACHE["zaman"] = datetime.now()
            CACHE["tam"] = True   # arsivle devam et
    except Exception as e:
        import traceback
        _logla("KRITIK HATA: %s\n%s" % (e, traceback.format_exc()))
        CACHE["hata"] = str(e)
    finally:
        CACHE["yukleniyor"] = False
        _FEED_KILIT.release()
    return CACHE

def canli_al():
    if CACHE["canli_zaman"] and (datetime.now()-CACHE["canli_zaman"]).seconds < 25:
        return CACHE["canli"]
    try:
        CACHE["canli"] = fsf.canli_maclar()
        CACHE["canli_zaman"] = datetime.now()
    except Exception:
        pass
    return CACHE["canli"]

def _lig_oynanmis(lig):
    ms = CACHE["ligler"].get(lig, [])
    return [{"ev":m["ev"],"dep":m["dep"],"ev_gol":m["ev_gol"],"dep_gol":m["dep_gol"],
             "tarih":m["tarih"]} for m in ms if m["oynandi"] and m["ev_gol"] is not None]

@app.route("/")
def ana():
    return render_template("index.html")

@app.route("/api/surum")
def api_surum():
    """Surum damgasi - hangi exe calisiyor kesin tespit icin"""
    import os as _os
    return jsonify({
        "surum": "14.0",
        "derleme": "14.0",
        "ozellik_takilma_korumasi": True,
        "ozellik_feed_tekrar_deneme": True,
        "ozellik_hizli_arsiv": True,
        "dosya": _os.path.abspath(__file__),
        "calisma_dizini": _os.getcwd(),
        "tam": CACHE.get("tam"),
        "mac": len(CACHE.get("maclar", [])),
        "yukleniyor": CACHE.get("yukleniyor"),
        "feed_deneme": CACHE.get("feed_deneme"),
        "yuk_baslangic": CACHE.get("yuk_baslangic")
    })


@app.route("/api/durum")
def api_durum():
    # ═══ ACILIS: arsiv ANINDA + feed PARALEL (0 saniye bekleme) ═══
    if not CACHE["maclar"]:
        _hizli_arsiv()          # 0.07 sn
    # Feed: takilma korumasi + hemen baslat
    bas = CACHE.get("yuk_baslangic")
    if CACHE["yukleniyor"] and bas and (time.time() - bas) > 25:
        _logla("TAKILMA: 25 sn+ -> sifirlandi")
        CACHE["yukleniyor"] = False
        CACHE["feed_deneme"] = None
    if not CACHE["tam"] and not CACHE["yukleniyor"]:
        son = CACHE.get("feed_deneme")
        simdi = time.time()
        if son is None or (simdi - son) > 3:      # 3 sn'de bir dene (hizli)
            CACHE["feed_deneme"] = simdi
            CACHE["yuk_baslangic"] = simdi
            threading.Thread(target=veri_al, kwargs={"force": True}, daemon=True).start()
    if not CACHE["maclar"]:
        return jsonify({"hazir": False, "yukleniyor": True, "tam": False})
    ligler = []
    for ad, ms in sorted(CACHE["ligler"].items(), key=lambda x: str(x[0])):
        oyn = len([m for m in ms if m["oynandi"] and m["ev_gol"] is not None])
        gelecek = len([m for m in ms if not m["oynandi"] and m.get("tarih")])
        bayrak = next((m["bayrak"] for m in ms if m.get("bayrak")), "⚽")
        # Ulke adi (lig adindan: "ENGLAND — Premier League" -> "ENGLAND")
        if "—" in ad:
            ulke = ad.split("—")[0].strip()
        elif " - " in ad:
            ulke = ad.split(" - ")[0].strip()
        else:
            ulke = "DIGER"
        ligler.append({"ad": ad, "mac": len(ms), "oynanmis": oyn, "gelecek": gelecek,
                       "bayrak": bayrak, "ulke": ulke})
    ligler = [l for l in ligler if l["mac"] >= 2]
    ligler.sort(key=lambda x: (-x["oynanmis"], x["ad"]))
    return jsonify({"hazir": True, "toplam": len(CACHE["maclar"]), "ligler": ligler,
                    "tam": CACHE.get("tam", False),
                    "feed_hata": CACHE.get("feed_hata", ""),
                    "zaman": CACHE["zaman"].strftime("%H:%M") if CACHE["zaman"] else ""})

@app.route("/api/test_feed")
def api_test_feed():
    """Feed erisim testi - kullanici hangi adimda takildigini gorur"""
    import time as _t
    sonuc = {"test": "feed erisim testi", "adimlar": []}
    # 1) DNS
    try:
        t = _t.time()
        import socket
        ip = socket.gethostbyname("global.flashscore.ninja")
        sonuc["adimlar"].append({"ad": "DNS cozumleme", "ok": True, "bilgi": ip, "sn": round(_t.time()-t, 2)})
    except Exception as e:
        sonuc["adimlar"].append({"ad": "DNS cozumleme", "ok": False, "bilgi": str(e)[:100]})
        return jsonify(sonuc)
    # 2) Baglanti + veri
    for domain in ["global.flashscore.ninja", "www.flashscore.com"]:
        try:
            t = _t.time()
            url = "https://%s/2/x/feed/f_1_0_3_en_1" % domain
            istek = urllib.request.Request(url, headers={"x-fsign": "SW9D1eZo",
                                                          "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(istek, timeout=8) as r:
                v = r.read()
            sonuc["adimlar"].append({"ad": "Feed " + domain, "ok": True,
                                      "bilgi": "%s bayt" % format(len(v), ","),
                                      "sn": round(_t.time()-t, 2)})
        except Exception as e:
            sonuc["adimlar"].append({"ad": "Feed " + domain, "ok": False,
                                      "bilgi": "%s: %s" % (type(e).__name__, str(e)[:80])})
    # 3) PARSE TESTI (KRITIK: feed -> mac listesi)
    try:
        t = _t.time()
        ham = ""
        try:
            ham = fsf.feed_cek(0)
        except Exception:
            ham = ""
        maclar = fsf.parse(ham, False) if ham else []
        sonuc["adimlar"].append({"ad": "PARSE (feed -> mac listesi)", "ok": len(maclar) > 0,
                                  "bilgi": "%d mac" % len(maclar), "sn": round(_t.time()-t, 2)})
        sonuc["mac_ornek"] = [{k: m.get(k) for k in ("ev", "dep", "tarih", "saat", "lig_adi")} for m in maclar[:3]]
    except Exception as e:
        sonuc["adimlar"].append({"ad": "PARSE (feed -> mac listesi)", "ok": False,
                                  "bilgi": "%s: %s" % (type(e).__name__, str(e)[:80])})

    # 4) Cok gunlu cekim (asil kullanim)
    try:
        t = _t.time()
        tum = fsf.tum_gunler(gunler=(-1, 0, 1), sadece_onemli=False)
        sonuc["adimlar"].append({"ad": "3 gunluk cekim (asil kullanim)", "ok": len(tum) > 0,
                                  "bilgi": "%d mac" % len(tum), "sn": round(_t.time()-t, 2)})
    except Exception as e:
        sonuc["adimlar"].append({"ad": "3 gunluk cekim (asil kullanim)", "ok": False,
                                  "bilgi": "%s: %s" % (type(e).__name__, str(e)[:80])})

    # 5) Ozet
    ok_sayisi = sum(1 for a in sonuc["adimlar"] if a.get("ok"))
    sonuc["ozet"] = "%d/%d adim basarili" % (ok_sayisi, len(sonuc["adimlar"]))
    sonuc["karar"] = ("Feed + PARSE calisiyor" if ok_sayisi == len(sonuc["adimlar"])
                       else "SORUN VAR - yukaridaki basarisiz adima bak")
    return jsonify(sonuc)

@app.route("/api/tumliglerde")
def api_tumliglerde():
    """Takimlari tum liglerde ara (kayan seritten gelen maclar icin)"""
    ev = request.args.get("ev","").strip()
    dep = request.args.get("dep","").strip()
    if not ev or not dep: return jsonify({"bulundu": False})
    for ad, ms in CACHE["ligler"].items():
        for m in ms:
            if ev.lower() in m["ev"].lower() and dep.lower() in m["dep"].lower():
                return jsonify({"bulundu": True, "lig": ad})
    return jsonify({"bulundu": False})

@app.route("/api/ulkeler")
def api_ulkeler():
    """Ligleri ulkeye gore gruplu dondur"""
    if not CACHE["maclar"]:
        return jsonify({"hazir": False})
    ulkeler = {}
    for ad, ms in CACHE["ligler"].items():
        oyn = len([m for m in ms if m["oynandi"] and m["ev_gol"] is not None])
        gelecek = len([m for m in ms if not m["oynandi"] and m.get("tarih")])
        if len(ms) < 2: continue
        bayrak = next((m["bayrak"] for m in ms if m.get("bayrak")), "⚽")
        if "—" in ad: ulke = ad.split("—")[0].strip()
        elif " - " in ad: ulke = ad.split(" - ")[0].strip()
        else: ulke = "DIGER"
        ulkeler.setdefault(ulke, {"ad": ulke, "ligler": [], "mac": 0, "oynanmis": 0})
        ulkeler[ulke]["ligler"].append({"ad": ad, "mac": len(ms), "oynanmis": oyn,
                                        "gelecek": gelecek, "bayrak": bayrak})
        ulkeler[ulke]["mac"] += len(ms)
        ulkeler[ulke]["oynanmis"] += oyn
    # Her ulkede ligleri sirala
    for u in ulkeler.values():
        u["ligler"].sort(key=lambda x: (-x["oynanmis"], x["ad"]))
    # Ulkeleri mac sayisina gore sirala
    liste = sorted(ulkeler.values(), key=lambda x: (-x["oynanmis"], -x["mac"]))
    return jsonify({"hazir": True, "ulkeler": liste, "toplam_ulke": len(liste),
                    "toplam_lig": sum(len(u["ligler"]) for u in liste)})

@app.route("/canli")
def canli_sayfa():
    return render_template("canli.html")

@app.route("/api/takimlar/<path:lig>")
def api_takimlar(lig):
    ms = CACHE["ligler"].get(lig, [])
    t = set()
    for m in ms:
        if m["oynandi"]:
            t.add(m["ev"]); t.add(m["dep"])
    return jsonify(sorted(t))

@app.route("/api/maclarlogoslar/<path:lig>")
def api_logolar(lig):
    ev = request.args.get("ev",""); dep = request.args.get("dep","")
    ms = CACHE["ligler"].get(lig, [])
    out = {"ev": None, "dep": None}
    for m in ms:
        if m["ev"]==ev and out["ev"] is None: out["ev"] = m.get("ev_logo")
        if m["dep"]==dep and out["dep"] is None: out["dep"] = m.get("dep_logo")
        if out["ev"] and out["dep"]: break
    return jsonify(out)

@app.route("/api/canli")
def api_canli():
    c = canli_al()
    return jsonify([{"ev":m["ev"],"dep":m["dep"],"ev_gol":m["ev_gol"],"dep_gol":m["dep_gol"],
                     "dakika":m["dakika"],"lig":m["lig_adi"],"bayrak":m.get("bayrak","⚽")} for m in c])

@app.route("/api/yukle")
def api_yukle():
    threading.Thread(target=veri_al, kwargs={"force": True}, daemon=True).start()
    return jsonify({"basladi": True})

@app.route("/api/maclar/<path:lig>")
def api_maclar(lig):
    ms = CACHE["ligler"].get(lig, [])
    gelecek = [m for m in ms if not m["oynandi"] and m.get("tarih")]
    gelecek.sort(key=lambda x: (x.get("tarih") or "", x.get("saat") or ""))
    oyn = [m for m in ms if m["oynandi"]]
    oyn.sort(key=lambda x: x.get("tarih") or "", reverse=True)
    return jsonify({"gelecek": gelecek[:30], "sonuclar": oyn[:10]})

@app.route("/api/tahmin", methods=["POST"])
def api_tahmin():
    try:
        j = request.get_json(silent=True)
        if not j: return jsonify({"hata": "Gecersiz istek (JSON bekleniyor)"})
        ev = (j.get("ev") or "").strip()
        dep = (j.get("dep") or "").strip()
        lig = (j.get("lig") or "").strip()
        if not ev or not dep or not lig:
            return jsonify({"hata": "Takim ve lig secilmelidir"})
        if ev == dep:
            return jsonify({"hata": "Ayni takim secilemez"})
        if not CACHE["maclar"]:
            return jsonify({"hata": "Veri henuz hazir degil, birkac saniye bekleyin"})
        oyn = _lig_oynanmis(lig)
        if len(oyn) < 5:
            return jsonify({"hata": f"Bu ligde yeterli veri yok ({len(oyn)} mac)"})
        # ═══ MEGA MOTOR (1.000.000 simulasyon) ═══
        if MEGA_VAR:
            gm, lm = MEGA.takim_gucu(oyn)
            if ev not in gm:
                return jsonify({"hata": f"{ev} — bu lig kayitlarinda yok"})
            if dep not in gm:
                return jsonify({"hata": f"{dep} — bu lig kayitlarinda yok"})
            o = MEGA.mega_simulasyon(ev, dep, gm, lm, 1000000)
            if not o:
                return jsonify({"hata": "Hesaplama yapilamadi, farkli takim deneyin"})
            o["ajan"] = MKARAR.karar_motoru(o, ev, dep, gm, oyn)
            o["kullanilan_mac"] = len(oyn)
            o["motor"] = "mega-v6"
            return jsonify(o)
        # Yedek: eski motor
        guc, lig_ort = takim_gucu(oyn)
        if ev not in guc:
            return jsonify({"hata": f"{ev} — bu lig kayitlarinda yok"})
        if dep not in guc:
            return jsonify({"hata": f"{dep} — bu lig kayitlarinda yok"})
        o = tum_olasiliklar(ev, dep, guc, lig_ort, 30000)
        if not o:
            return jsonify({"hata": "Hesaplama yapilamadi, farkli takim deneyin"})
        o["ajan"] = akilli_ajan(o, guc, ev, dep, oyn)
        o["kullanilan_mac"] = len(oyn)
        o["motor"] = "eski"
        return jsonify(o)
    except Exception as ex:
        print("[TAHMIN HATA]", ex)
        return jsonify({"hata": f"Hesaplama hatasi: {str(ex)[:80]}"}), 500

def port_bul(bas=8090):
    p = bas
    while p < bas+60:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", p)); s.close(); return p
        except OSError:
            s.close(); p += 1
    return bas

if __name__ == "__main__":
    p = port_bul(8090)
    def ac():
        time.sleep(3)
        try: webbrowser.open(f"http://127.0.0.1:{p}")
        except Exception: pass
    threading.Thread(target=ac, daemon=True).start()
    app.run(host="127.0.0.1", port=p, debug=False, use_reloader=False)
