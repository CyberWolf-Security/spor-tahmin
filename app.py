"""Spor Tahmin - Flask web (mac listesi + tüm olasiliklar + ajan)"""
from flask import Flask, render_template, request, jsonify
import json, os, threading, webbrowser, time
from tahmin import takim_gucu
from olasilik import tum_olasiliklar, ajan_analiz
import canli_veri as cv

app = Flask(__name__)
CACHE = {"maclar": [], "zaman": None, "ligler": {}}

def veri_al():
    from datetime import datetime
    if CACHE["maclar"] and CACHE["zaman"] and (datetime.now()-CACHE["zaman"]).seconds < 900:
        return CACHE
    maclar = cv.tum_maclar()
    CACHE["maclar"] = maclar
    CACHE["zaman"] = datetime.now()
    ligler = {}
    for m in maclar:
        ligler.setdefault(m["lig_adi"], []).append(m)
    CACHE["ligler"] = ligler
    return CACHE

def _lig_verisi(lig):
    c = veri_al()
    ms = c["ligler"].get(lig, [])
    oyn = [{"ev":m["ev"],"dep":m["dep"],"ev_gol":m["ev_gol"],"dep_gol":m["dep_gol"],
            "tarih":m["tarih"]} for m in ms if m["oynandi"] and m["ev_gol"] is not None]
    return oyn, ms

@app.route("/")
def ana():
    c = veri_al()
    gelecek = [m for m in c["maclar"] if not m["oynandi"] and m.get("tarih")]
    gelecek.sort(key=lambda x: (x.get("tarih") or "", x.get("saat") or ""))
    oyn = [m for m in c["maclar"] if m["oynandi"]]
    oyn.sort(key=lambda x: x.get("tarih") or "", reverse=True)
    lig_say = {ad: len([m for m in ms if m["oynandi"] and m["ev_gol"] is not None])
               for ad, ms in c["ligler"].items()}
    gecerli = [m for m in gelecek if lig_say.get(m["lig_adi"],0) >= 5]
    return render_template("index.html", gelecek=gecerli[:40], oynanan=oyn[:12],
                           toplam=len(c["maclar"]))

@app.route("/api/tahmin", methods=["POST"])
def api_tahmin():
    j = request.json
    ev, dep, lig = j.get("ev","").strip(), j.get("dep","").strip(), j.get("lig","").strip()
    oyn, ms = _lig_verisi(lig)
    if len(oyn) < 5: return jsonify({"hata": f"Yetersiz veri ({len(oyn)} maç)"})
    guc, lig_ort = takim_gucu(oyn)
    if ev not in guc: return jsonify({"hata": f"{ev} — kayıtlarda yok"})
    if dep not in guc: return jsonify({"hata": f"{dep} — kayıtlarda yok"})
    o = tum_olasiliklar(ev, dep, guc, lig_ort, 30000)
    a = ajan_analiz(o, ev, dep)
    o["ajan"] = a
    o["kullanilan_mac"] = len(oyn)
    return jsonify(o)

@app.route("/api/maclar")
def api_maclar():
    c = veri_al()
    gelecek = [m for m in c["maclar"] if not m["oynandi"] and m.get("tarih")]
    gelecek.sort(key=lambda x: (x.get("tarih") or "", x.get("saat") or ""))
    lig_say = {ad: len([m for m in ms if m["oynandi"] and m["ev_gol"] is not None])
               for ad, ms in c["ligler"].items()}
    return jsonify([m for m in gelecek if lig_say.get(m["lig_adi"],0) >= 5][:40])

if __name__ == "__main__":
    def ac():
        time.sleep(2.5)
        try: webbrowser.open("http://127.0.0.1:8090")
        except Exception: pass
    threading.Thread(target=ac, daemon=True).start()
    app.run(host="127.0.0.1", port=8090, debug=False)
