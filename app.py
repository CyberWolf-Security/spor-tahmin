"""Spor Tahmin - Flask web (canli veri + simulasyon)"""
from flask import Flask, render_template, request, jsonify
import json, os
from tahmin import takim_gucu, mac_simule
import canli_veri as cv

app = Flask(__name__)

CACHE = {"maclar": [], "zaman": None, "ligler": {}}

def veri_al():
    """Canli veriyi cek (onbellekle)"""
    from datetime import datetime
    if CACHE["maclar"] and CACHE["zaman"] and (datetime.now()-CACHE["zaman"]).seconds < 600:
        return CACHE
    maclar = cv.tum_maclar()
    CACHE["maclar"] = maclar
    CACHE["zaman"] = datetime.now()
    ligler = {}
    for m in maclar:
        ligler.setdefault(m["lig_adi"], []).append(m)
    CACHE["ligler"] = ligler
    return CACHE

@app.route("/")
def ana():
    c = veri_al()
    cekilecek = []
    for ad, ms in sorted(c["ligler"].items()):
        oyn = [m for m in ms if m["oynandi"]]
        if len(oyn) >= 3:   # en az 3 mac
            cekilecek.append({"lig": ad, "mac": len(oyn), "kaynak": oyn[0]["kaynak"] if oyn else ""})
    return render_template("index.html", ligler=cekilecek, toplam=len(c["maclar"]))

def lig_takimlari(lig_adi):
    c = veri_al()
    ms = c["ligler"].get(lig_adi, [])
    t = set()
    for m in ms:
        if m["oynandi"]: t.add(m["ev"]); t.add(m["dep"])
    return sorted(t)

@app.route("/api/takimlar/<path:lig>")
def api_takimlar(lig):
    return jsonify(lig_takimlari(lig))

@app.route("/api/tahmin", methods=["POST"])
def api_tahmin():
    j = request.json
    lig = j.get("lig",""); ev = j.get("ev","").strip(); dep = j.get("dep","").strip()
    c = veri_al()
    ms = c["ligler"].get(lig, [])
    oyn = [{"ev":m["ev"],"dep":m["dep"],"ev_gol":m["ev_gol"],"dep_gol":m["dep_gol"],
            "tarih":m["tarih"]} for m in ms if m["oynandi"] and m["ev_gol"] is not None]
    if len(oyn) < 5: return jsonify({"hata":f"Yetersiz veri ({len(oyn)} mac)"})
    guc, lig_ort = takim_gucu(oyn)
    if ev not in guc: return jsonify({"hata":f"{ev} veride yok"})
    if dep not in guc: return jsonify({"hata":f"{dep} veride yok"})
    if ev == dep: return jsonify({"hata":"Ayni takim"})
    r = mac_simule(ev, dep, guc, lig_ort, n=10000)
    r["kullanilan_mac"] = len(oyn)
    r["kaynak"] = ms[0]["kaynak"] if ms else ""
    return jsonify(r)

@app.route("/api/tablo/<path:lig>")
def api_tablo(lig):
    # OpenLigaDB ligi ise API tablosu
    c = veri_al()
    ms = c["ligler"].get(lig, [])
    if ms and ms[0]["kaynak"] == "OpenLigaDB":
        try:
            t = cv.oldb_tablo(ms[0]["lig"])
            return jsonify(t)
        except Exception: pass
    # Kendi hesapla
    oyn = [{"ev":m["ev"],"dep":m["dep"],"ev_gol":m["ev_gol"],"dep_gol":m["dep_gol"],
            "tarih":m["tarih"]} for m in ms if m["oynandi"] and m["ev_gol"] is not None]
    guc, _ = takim_gucu(oyn)
    out = sorted(guc.items(), key=lambda x:-x[1]["ppg"])
    return jsonify([{"sira":i,"takim":t,"mac":g["mac"],"puan":g["puan"],"ppg":round(g["ppg"],2)}
                    for i,(t,g) in enumerate(out,1)])


@app.route("/canli")
def canli():
    c = veri_al()
    cekilecek = []
    for ad, ms in sorted(c["ligler"].items()):
        oyn = [m for m in ms if m["oynandi"]]
        if len(oyn) >= 3:
            cekilecek.append({"lig": ad, "mac": len(oyn)})
    return render_template("canli.html", ligler=cekilecek)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8090, debug=False)
