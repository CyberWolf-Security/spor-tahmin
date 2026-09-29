"""Spor Tahmin - Masaustu (gomulu pencere)"""
import sys, os, threading, time, socket

if hasattr(sys, "_MEIPASS"):
    BASE = sys._MEIPASS
else:
    BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)
sys.path.insert(0, BASE)

os.environ["FLASK_ENV"] = "production"
import logging
logging.getLogger("werkzeug").setLevel(logging.ERROR)

from app import app

def port_bul(bas=8090):
    p = bas
    while p < bas + 60:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", p)); s.close(); return p
        except OSError:
            s.close(); p += 1
    return bas

def main():
    p = port_bul(8090)
    t = threading.Thread(target=lambda: app.run(host="127.0.0.1", port=p, debug=False,
                                                use_reloader=False, threaded=True), daemon=True)
    t.start()

    for _ in range(80):
        try:
            s = socket.create_connection(("127.0.0.1", p), timeout=1); s.close(); break
        except OSError: time.sleep(0.25)

    url = f"http://127.0.0.1:{p}"
    try:
        import webview
        webview.create_window("Spor Tahmin — Mac Analiz", url, width=1400, height=900,
                              min_size=(1000, 650), background_color="#0a0e14")
        webview.start()
    except Exception:
        import webbrowser
        webbrowser.open(url)
        try:
            while True: time.sleep(60)
        except KeyboardInterrupt: pass

if __name__ == "__main__":
    main()
