"""HATA AYIKLAMA SURUMU — konsol acik, tum adimlar loglanir"""
import sys, os, json, time, traceback, socket, urllib.request

def tani():
    print("=" * 60)
    print("SPOR TAHMIN - TANI MODU")
    print("=" * 60)
    print("Python:", sys.version)
    print("Frozen:", getattr(sys, "frozen", False))
    print("_MEIPASS:", getattr(sys, "_MEIPASS", "YOK"))
    BASE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    print("BASE_DIR:", BASE)

    print("\n--- DOSYALAR ---")
    for alt in ["veri", "templates", "veri/arsiv_superlig.json", "veri/logolar.json", "templates/index.html"]:
        yol = os.path.join(BASE, alt)
        var = os.path.exists(yol)
        boy = os.path.getsize(yol) if var and os.path.isfile(yol) else 0
        print(("  OK  " if var else "  YOK ") + alt + ((" (%s bayt)" % format(boy, ",")) if boy else ""))

    print("\n--- ARSIV ---")
    try:
        vr = os.path.join(BASE, "veri")
        toplam = 0
        if os.path.isdir(vr):
            for f in os.listdir(vr):
                if f.startswith("arsiv_") and f.endswith(".json"):
                    with open(os.path.join(vr, f), encoding="utf-8") as fh:
                        n = len(json.load(fh).get("maclar", []))
                        print("  " + f + ": " + str(n) + " mac")
                        toplam += n
        print("  TOPLAM: " + str(toplam) + " mac")
    except Exception as e:
        print("  HATA:", e)
        traceback.print_exc()

    print("\n--- INTERNET ---")
    try:
        t = time.time()
        istek = urllib.request.Request("https://global.flashscore.ninja/2/x/feed/f_1_0_3_en_1",
                                        headers={"x-fsign": "SW9D1eZo"})
        r = urllib.request.urlopen(istek, timeout=15)
        veri = r.read()
        print("  FlashScore feed: OK (%s bayt, %.1fs)" % (format(len(veri), ","), time.time() - t))
    except Exception as e:
        print("  FlashScore HATA: %s: %s" % (type(e).__name__, e))

    try:
        t = time.time()
        r = urllib.request.urlopen("https://www.google.com", timeout=10)
        print("  Google: OK (%s, %.1fs)" % (r.status, time.time() - t))
    except Exception as e:
        print("  Google HATA: %s: %s" % (type(e).__name__, e))

    print("\n--- PORT ---")
    for p in [8090, 8091, 8092]:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", p)); s.close()
            print("  %d: BOS" % p)
        except OSError as e:
            print("  %d: DOLU (%s)" % (p, e))

    print("\n" + "=" * 60)
    input("Kapatmak icin ENTER'a bas...")

if __name__ == "__main__":
    tani()
