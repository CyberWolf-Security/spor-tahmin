"""
Spor Tahmin - Masaustu Program (WebView2 gomulu penceresi)
Flask arka planda calisir, pywebview ile gercek program penceresi acilir.
"""
import sys, os, threading, time, socket, json

# ── PyInstaller icin yol cozumu ──
def kaynak_yolu(rel):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, rel)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), rel)

# Flask app'i import et
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])) if not hasattr(sys,"_MEIPASS") else sys._MEIPASS)

from app import app

# ═══ AÇILIŞTA OTOMATİK: arşiv ANINDA + feed PARALEL (arayüzü bekleme!) ═══
def _acilis_baslat():
    import threading, time
    def isle():
        time.sleep(0.5)
        try:
            app_module = __import__("app")
            app_module._hizli_arsiv()                    # 0.07 sn — arşiv
            app_module.CACHE["feed_deneme"] = None       # temiz başlangıç
            app_module.CACHE["yukleniyor"] = False
            app_module.veri_al(force=True)               # feed (arka planda)
        except Exception:
            pass
    threading.Thread(target=isle, daemon=True).start()
_acilis_baslat()

PORT = 8090

def port_bos(p):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", p)); s.close(); return True
    except OSError:
        s.close(); return False

def port_bul(bas=8090):
    p = bas
    while not port_bos(p) and p < bas + 50:
        p += 1
    return p

def sunucu_calistir(port):
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False, threaded=True)

def main():
    global PORT
    PORT = port_bul(8090)

    t = threading.Thread(target=sunucu_calistir, args=(PORT,), daemon=True)
    t.start()

    # Sunucu hazir olana kadar bekle
    for _ in range(60):
        try:
            s = socket.create_connection(("127.0.0.1", PORT), timeout=1)
            s.close(); break
        except OSError:
            time.sleep(0.3)

    url = f"http://127.0.0.1:{PORT}"

    try:
        import webview
        webview.create_window("Spor Tahmin", url, width=1100, height=720,
                              min_size=(820, 560), background_color="#0d1117")
        webview.start()
    except Exception as e:
        # WebView2 yoksa tarayiciya dus
        import webbrowser
        webbrowser.open(url)
        print(f"WebView acilamadi ({e}); tarayicida acildi: {url}")
        try:
            while True: time.sleep(60)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()
