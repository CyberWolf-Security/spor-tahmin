"""Spor Tahmin - Flask (dunya capinda feed + canli serit)"""
from flask import Flask, render_template, request, jsonify
import json, os, sys, threading, webbrowser, time, socket
from datetime import datetime
from tahmin import takim_gucu
from olasilik import tum_olasiliklar
from ajan3 import akilli_ajan
import fs_feed as fsf

app = Flask(__name__)
BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
CACHE = {"maclar": [], "zaman": None, "ligler": {}, "yukleniyor": False, "canli": [], "canli_zaman": None}

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

def veri_al(force=False):
    if not force and CACHE["maclar"] and CACHE["zaman"] and (datetime.now()-CACHE["zaman"]).seconds < 1200:
        return CACHE
    if CACHE["yukleniyor"]: return CACHE
    CACHE["yukleniyor"] = True
    try:
        # 1) Canli feed (tum dunya, 15 gun)
        maclar = fsf.tum_gunler(gunler=(-7,-6,-5,-4,-3,-2,-1,0,1,2,3,4,5,6,7), sadece_onemli=False)
        # 2) Takim arsivleri (gecmis veri havuzu)
        ars = arsiv_yukle()
        print(f"[VERI] feed={len(maclar)} arsiv={len(ars)}")
        _logo_yukle()
        lg = logo_sozluk()
        for m in ars:
            if not m.get("ev_logo"): m["ev_logo"] = _logo_bul(lg, m["ev"])
            if not m.get("dep_logo"): m["dep_logo"] = _logo_bul(lg, m["dep"])
            if not m.get("lig_adi"):
                m["lig_adi"] = "Süper Lig (Arşiv)" if "Fenerbah" in str(m) or True else "Arşiv"
                m["bayrak"] = "🇹🇷"
            m["kaynak"] = "Arşiv"
        maclar += ars
        CACHE["maclar"] = maclar
        CACHE["zaman"] = datetime.now()
        ligler = {}
        for m in maclar:
            ligler.setdefault(m["lig_adi"], []).append(m)
        CACHE["ligler"] = ligler
    finally:
        CACHE["yukleniyor"] = False
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
        return jsonify({"hazir": False, "yukleniyor": CACHE["yukleniyor"]})
    ligler = []
    for ad, ms in sorted(CACHE["ligler"].items(), key=lambda x: str(x[0])):
        oyn = len([m for m in ms if m["oynandi"] and m["ev_gol"] is not None])
        gelecek = len([m for m in ms if not m["oynandi"] and m.get("tarih")])
        bayrak = next((m["bayrak"] for m in ms if m.get("bayrak")), "⚽")
        ligler.append({"ad": ad, "mac": len(ms), "oynanmis": oyn, "gelecek": gelecek, "bayrak": bayrak})
    ligler = [l for l in ligler if l["oynanmis"] >= 5 or l["gelecek"] >= 3]
    ligler.sort(key=lambda x: (-x["oynanmis"], x["ad"]))
    return jsonify({"hazir": True, "toplam": len(CACHE["maclar"]), "ligler": ligler,
                    "zaman": CACHE["zaman"].strftime("%H:%M") if CACHE["zaman"] else ""})

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
    j = request.json
    ev, dep, lig = j.get("ev","").strip(), j.get("dep","").strip(), j.get("lig","").strip()
    oyn = _lig_oynanmis(lig)
    if len(oyn) < 5: return jsonify({"hata": f"Bu ligde yeterli veri yok ({len(oyn)} maç)"})
    guc, lig_ort = takim_gucu(oyn)
    if ev not in guc: return jsonify({"hata": f"{ev} — kayıtlarda yok"})
    if dep not in guc: return jsonify({"hata": f"{dep} — kayıtlarda yok"})
    o = tum_olasiliklar(ev, dep, guc, lig_ort, 30000)
    o["ajan"] = akilli_ajan(o, guc, ev, dep, oyn)
    o["kullanilan_mac"] = len(oyn)
    return jsonify(o)

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
