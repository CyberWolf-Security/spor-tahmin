"""Spor Tahmin - Flask (coklu lig + tum olasiliklar + ajan)"""
from flask import Flask, render_template, request, jsonify
import json, os, threading, webbrowser, time, socket
from tahmin import takim_gucu
from olasilik import tum_olasiliklar, ajan_analiz
import flashscore_multi as fsm

app = Flask(__name__)
CACHE = {"maclar": [], "zaman": None, "ligler": {}, "yukleniyor": False}

def veri_al(force=False):
    from datetime import datetime
    if not force and CACHE["maclar"] and CACHE["zaman"] and (datetime.now()-CACHE["zaman"]).seconds < 900:
        return CACHE
    if CACHE["yukleniyor"]: return CACHE
    CACHE["yukleniyor"] = True
    try:
        maclar = fsm.tum_ligler()
        CACHE["maclar"] = maclar
        CACHE["zaman"] = datetime.now()
        ligler = {}
        for m in maclar:
            ligler.setdefault(m["lig_adi"], []).append(m)
        CACHE["ligler"] = ligler
    finally:
        CACHE["yukleniyor"] = False
    return CACHE

def _lig_oynanmis(lig):
    c = CACHE
    ms = c["ligler"].get(lig, [])
    return [{"ev":m["ev"],"dep":m["dep"],"ev_gol":m["ev_gol"],"dep_gol":m["dep_gol"],
             "tarih":m["tarih"]} for m in ms if m["oynandi"] and m["ev_gol"] is not None]

@app.route("/")
def ana():
    return render_template("index.html")

@app.route("/api/durum")
def api_durum():
    """Veri hazir mi?"""
    if not CACHE["maclar"]:
        return jsonify({"hazir": False, "yukleniyor": CACHE["yukleniyor"]})
    ligler = []
    for ad, ms in sorted(CACHE["ligler"].items()):
        oyn = len([m for m in ms if m["oynandi"] and m["ev_gol"] is not None])
        gelecek = len([m for m in ms if not m["oynandi"] and m.get("tarih")])
        if oyn >= 5:
            ligler.append({"ad": ad, "mac": len(ms), "oynanmis": oyn, "gelecek": gelecek})
    return jsonify({
        "hazir": True, "toplam": len(CACHE["maclar"]),
        "ligler": ligler,
        "zaman": CACHE["zaman"].strftime("%H:%M") if CACHE["zaman"] else ""
    })

@app.route("/api/yukle")
def api_yukle():
    """Veriyi yukle (arka planda)"""
    threading.Thread(target=veri_al, kwargs={"force": True}, daemon=True).start()
    return jsonify({"basladi": True})

@app.route("/api/maclar/<path:lig>")
def api_maclar(lig):
    c = CACHE
    ms = c["ligler"].get(lig, [])
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
    o["ajan"] = ajan_analiz(o, ev, dep)
    o["kullanilan_mac"] = len(oyn)
    return jsonify(o)

def port_bul(bas=8090):
    p = bas
    while p < bas+50:
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
