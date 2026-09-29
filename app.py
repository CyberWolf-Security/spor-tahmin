"""Spor Tahmin - Flask (dunya capinda feed + canli serit)"""
from flask import Flask, render_template, request, jsonify
import json, os, sys, threading, webbrowser, time, socket
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

def veri_al(force=False):
    if not force and CACHE["maclar"] and CACHE["zaman"] and (datetime.now()-CACHE["zaman"]).seconds < 1200:
        return CACHE
    if CACHE["yukleniyor"]: return CACHE
    CACHE["yukleniyor"] = True
    CACHE["tam"] = False
    CACHE["hata"] = None
    try:
        # 1) Takim arsivleri (yerel dosya - ANINDA)
        ars = arsiv_yukle()
        _logla("arsiv=%d mac (BASE_DIR=%s)" % (len(ars), BASE_DIR))
        # Hemen erisilebilir yap (arayuz bos kalmasin)
        if ars:
            for m in ars:
                if not m.get("lig_adi"):
                    m["lig_adi"] = "Süper Lig (Arşiv)"; m["bayrak"] = "🇹🇷"
                m["kaynak"] = "Arşiv"
            _logo_yukle(); lg0 = logo_sozluk()
            for m in ars:
                if not m.get("ev_logo"): m["ev_logo"] = _logo_bul(lg0, m["ev"])
                if not m.get("dep_logo"): m["dep_logo"] = _logo_bul(lg0, m["dep"])
            CACHE["maclar"] = list(ars)
            l0 = {}
            for m in ars: l0.setdefault(m["lig_adi"], []).append(m)
            CACHE["ligler"] = l0
            _logla("ON HAZIR: %d mac, %d lig" % (len(ars), len(l0)))
        # 2) Canli feed (yavas - 15 gun) — hata olsa bile arsiv kalir
        try:
            maclar = fsf.tum_gunler(gunler=(-7,-6,-5,-4,-3,-2,-1,0,1,2,3,4,5,6,7), sadece_onemli=False)
            _logla("feed=%d mac" % len(maclar))
            _logo_yukle()
            lg = logo_sozluk()
            for m in ars:
                if not m.get("ev_logo"): m["ev_logo"] = _logo_bul(lg, m["ev"])
                if not m.get("dep_logo"): m["dep_logo"] = _logo_bul(lg, m["dep"])
                if not m.get("lig_adi"):
                    m["lig_adi"] = "Süper Lig (Arşiv)"
                    m["bayrak"] = "🇹🇷"
                m["kaynak"] = "Arşiv"
            maclar += ars
            CACHE["maclar"] = maclar
            ligler = {}
            for m in maclar:
                ligler.setdefault(m["lig_adi"], []).append(m)
            CACHE["ligler"] = ligler
            CACHE["tam"] = True
            _logla("TAM HAZIR: %d mac, %d lig" % (len(maclar), len(ligler)))
        except Exception as fe:
            _logla("FEED HATA (arsiv korundu): %s" % fe)
            CACHE["tam"] = True   # arsivle devam et
    except Exception as e:
        import traceback
        _logla("KRITIK HATA: %s\n%s" % (e, traceback.format_exc()))
        CACHE["hata"] = str(e)
    finally:
        CACHE["yukleniyor"] = False
        if not CACHE["maclar"]:
            _logla("UYARI: maclar bos kaldi!")
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

@app.route("/api/durum")
def api_durum():
    if not CACHE["maclar"]:
        # Otomatik baslat (frontend bekliyorsa kendiliginden yuklensin)
        if not CACHE["yukleniyor"]:
            threading.Thread(target=veri_al, kwargs={"force": True}, daemon=True).start()
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
                    "zaman": CACHE["zaman"].strftime("%H:%M") if CACHE["zaman"] else ""})

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
